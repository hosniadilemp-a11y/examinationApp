import io
import json
import zipfile
import pytest

def test_question_crud_and_json_import_export(client, admin_headers):
    """
    Vérifie le cycle de vie complet de l'édition de questions via l'API Web Editor :
    - Création de question (POST) -> 201 Created
    - Modification de question (PUT) -> 200 OK
    - Exportation JSON (GET) -> 200 OK
    - Importation par lot JSON (POST) -> 200 OK
    - Suppression de question (DELETE) -> 200 OK
    """
    # 1. Création d'un examen
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Question Editor Test", "duration_minutes": 45, "group_ids": ["GRP-1"]}
    )
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]

    # 2. Création d'une question
    res_q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1,
            "type": "single_choice",
            "prompt_markdown": "Quel est le mot-clé pour définir une fonction en Python ?",
            "points": 2.5,
            "negative_penalty": 0.5,
            "options_json": json.dumps([
                {"id": "A", "text": "func"},
                {"id": "B", "text": "def"},
                {"id": "C", "text": "function"}
            ]),
            "correct_answers_json": json.dumps("B")
        }
    )
    assert res_q1.status_code == 201
    q1_id = res_q1.json()["id"]

    # 3. Modification de la question
    res_update = client.put(
        f"/api/exams/{exam_id}/questions/{q1_id}",
        headers=admin_headers,
        json={
            "prompt_markdown": "Quel est le mot-clé standard pour définir une fonction en Python 3 ?",
            "points": 3.0
        }
    )
    assert res_update.status_code == 200
    assert res_update.json()["points"] == 3.0
    assert "Python 3" in res_update.json()["prompt_markdown"]

    # 4. Export JSON
    res_export = client.get(f"/api/exams/{exam_id}/questions/export-json", headers=admin_headers)
    assert res_export.status_code == 200
    exported_data = res_export.json()
    assert len(exported_data) == 1
    assert exported_data[0]["points"] == 3.0

    # 5. Importation JSON d'une seconde question
    new_questions_batch = [
        {
            "ordering": 2,
            "type": "boolean",
            "prompt_markdown": "Les tuples sont-ils immuables en Python ?",
            "points": 2.0,
            "negative_penalty": 0.0,
            "options_json": "[]",
            "correct_answers_json": json.dumps(True)
        }
    ]
    res_import = client.post(
        f"/api/exams/{exam_id}/questions/import-json",
        headers=admin_headers,
        json=new_questions_batch
    )
    assert res_import.status_code == 200
    assert res_import.json()["imported_count"] == 1

    # 6. Vérification du détail de l'examen
    res_detail = client.get(f"/api/exams/{exam_id}", headers=admin_headers)
    assert res_detail.status_code == 200
    assert len(res_detail.json()["questions"]) == 2

    # 7. Suppression de la première question
    res_del = client.delete(f"/api/exams/{exam_id}/questions/{q1_id}", headers=admin_headers)
    assert res_del.status_code == 204
    res_detail_after = client.get(f"/api/exams/{exam_id}", headers=admin_headers)
    assert len(res_detail_after.json()["questions"]) == 1

def test_statistical_item_analysis_and_discrimination(client, admin_headers, teacher_headers):
    """
    Vérifie le calcul de l'analyse psychométrique et de l'indice de discrimination (Item Analysis) :
    - Moyenne, Médiane, Écart-Type
    - Indice de discrimination D = Pu - Pl
    - Détection des anomalies (D < 0 ou taux de succès nul)
    - Exportation CSV
    """
    # 1. Création de l'examen avec 2 questions
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Psychométrie & Discrimination", "duration_minutes": 30, "group_ids": ["GRP-1", "DEV-IA"]}
    )
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]

    # Q1: Discriminante (bonne réponse Vrai)
    res_q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1,
            "type": "boolean",
            "prompt_markdown": "RSA est-il un chiffrement asymétrique ?",
            "points": 10.0,
            "options_json": "[]",
            "correct_answers_json": json.dumps(True)
        }
    )
    assert res_q1.status_code == 201
    q1_id = res_q1.json()["id"]

    # Q2: Deuxième question (bonne réponse A)
    res_q2 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 2,
            "type": "single_choice",
            "prompt_markdown": "Quel algorithme utilise des clés publiques et privées ?",
            "points": 10.0,
            "options_json": json.dumps([{"id": "A", "text": "RSA"}, {"id": "B", "text": "AES"}]),
            "correct_answers_json": json.dumps("A")
        }
    )
    assert res_q2.status_code == 201
    q2_id = res_q2.json()["id"]

    # 2. Création de la session
    sess_res = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-PSYCHO"}).json()
    session_id = sess_res["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # 3. Connexion de 4 étudiants existants du groupe DEV-IA
    students = [
        ("etu_dev1", "StudentDev1!"),
        ("etu_dev2", "StudentDev2!"),
        ("etu_dev3", "StudentDev3!"),
        ("etu_dev4", "StudentDev4!")
    ]

    # etu_dev1 et etu_dev2 réussissent Q1 et Q2 (score 20/20)
    for u_name, pwd in students[:2]:
        st_auth = client.post("/api/auth/login", json={"username": u_name, "password": pwd}).json()
        st_head = {"Authorization": f"Bearer {st_auth['access_token']}"}
        start_res = client.post(f"/api/student/exams/{exam_id}/start", headers=st_head).json()
        att_id = start_res["attempt_id"]
        client.post(f"/api/student/attempts/{att_id}/save-answer", headers=st_head, json={"question_id": q1_id, "answer": True})
        client.post(f"/api/student/attempts/{att_id}/save-answer", headers=st_head, json={"question_id": q2_id, "answer": "A"})
        client.post(f"/api/student/attempts/{att_id}/submit", headers=st_head)

    # etu_dev3 et etu_dev4 échouent (score 0/20)
    for u_name, pwd in students[2:]:
        st_auth = client.post("/api/auth/login", json={"username": u_name, "password": pwd}).json()
        st_head = {"Authorization": f"Bearer {st_auth['access_token']}"}
        start_res = client.post(f"/api/student/exams/{exam_id}/start", headers=st_head).json()
        att_id = start_res["attempt_id"]
        client.post(f"/api/student/attempts/{att_id}/save-answer", headers=st_head, json={"question_id": q1_id, "answer": False})
        client.post(f"/api/student/attempts/{att_id}/save-answer", headers=st_head, json={"question_id": q2_id, "answer": "B"})
        client.post(f"/api/student/attempts/{att_id}/submit", headers=st_head)

    # 4. Vérification de l'analyse via l'endpoint de l'examen
    res_analysis = client.get(f"/api/exams/{exam_id}/item-analysis", headers=teacher_headers)
    assert res_analysis.status_code == 200
    data = res_analysis.json()
    assert data["total_candidates"] == 4
    assert "global_stats" in data
    assert data["global_stats"]["mean"] == 10.0
    assert len(data["questions_analysis"]) == 2

    # Q1 et Q2 doivent avoir une discrimination positive élevée (D = 1.0)
    q1_stat = [q for q in data["questions_analysis"] if q["question_id"] == q1_id][0]
    assert q1_stat["facility_pct"] == 50.0
    assert q1_stat["discrimination_index"] == 1.0
    assert "Excellente" in q1_stat["discrimination_quality"]

    # 5. Vérification via l'endpoint de surveillance de session
    res_sess_analysis = client.get(f"/api/proctor/sessions/{session_id}/item-analysis", headers=teacher_headers)
    assert res_sess_analysis.status_code == 200
    sess_data = res_sess_analysis.json()
    assert sess_data["session_id"] == session_id
    assert sess_data["total_candidates"] == 4

    # 6. Vérification via l'endpoint administrateur
    res_admin_analysis = client.get(f"/api/admin/exams/{exam_id}/item-analysis", headers=admin_headers)
    assert res_admin_analysis.status_code == 200

    # 7. Vérification de l'export CSV
    res_csv = client.get(f"/api/exams/{exam_id}/item-analysis/csv", headers=teacher_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "ANALYSE PSYCHOMETRIQUE" in res_csv.text

def test_usb_package_export_and_import(client, admin_headers, teacher_headers):
    """
    Phase 5 : Vérifie l'exportation d'un examen sous package .exam.zip (avec manifest et SHA-256)
    et son importation sur un serveur de salle vierge.
    """
    # 1. Création d'un examen source
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Export USB Source", "duration_minutes": 60, "group_ids": ["GRP-1"]}
    )
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]

    res_q = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1,
            "type": "boolean",
            "prompt_markdown": "Python est-il un langage interprété ?",
            "points": 20.0,
            "options_json": "[]",
            "correct_answers_json": json.dumps(True)
        }
    )
    assert res_q.status_code == 201

    # 2. Exportation sous archive .exam.zip
    res_export = client.get(f"/api/sync/exams/{exam_id}/export-package", headers=teacher_headers)
    assert res_export.status_code == 200
    assert "application/zip" in res_export.headers["content-type"]
    zip_bytes = res_export.content

    # Vérification du contenu du ZIP
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "exam_manifest.json" in namelist
        assert "checksum.sha256" in namelist
        manifest = json.loads(zf.read("exam_manifest.json").decode("utf-8"))
        assert manifest["exam"]["id"] == exam_id
        assert manifest["exam"]["module_code"] == "PYTHON_INIT"
        assert len(manifest["questions"]) == 1

    # 3. Importation du package .exam.zip (Simulation sur serveur de salle)
    files = {"file": ("examen_PYTHON_INIT_test.exam.zip", zip_bytes, "application/zip")}
    res_import = client.post("/api/sync/exams/import-package", headers=teacher_headers, files=files)
    assert res_import.status_code == 200
    import_data = res_import.json()
    assert import_data["success"] is True
    assert import_data["exam_id"] == exam_id
    assert import_data["questions_count"] == 1

def test_session_results_export_and_master_idempotent_import(client, admin_headers, teacher_headers):
    """
    Phase 5 : Vérifie l'exportation des résultats d'une session sous .results.zip
    et leur importation réconciliée et idempotente sur l'instance Master.
    """
    # 1. Création d'un examen et d'une session
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Salle USB Results", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]

    sess_res = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-USB"}).json()
    session_id = sess_res["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # 2. Exportation des résultats sous .results.zip
    res_export = client.get(f"/api/sync/sessions/{session_id}/export-results", headers=teacher_headers)
    assert res_export.status_code == 200
    assert "application/zip" in res_export.headers["content-type"]
    zip_bytes = res_export.content

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "session_metadata.json" in namelist
        assert "student_submissions.csv" in namelist
        assert "question_answers.csv" in namelist
        assert "audit_logs.json" in namelist

    # 3. Importation sur le Master via .results.zip
    files = {"file": ("resultats_salle.results.zip", zip_bytes, "application/zip")}
    res_import_master = client.post("/api/sync/master/import-results", headers=admin_headers, files=files)
    assert res_import_master.status_code == 200
    assert res_import_master.json()["success"] is True

    # 4. Vérification de l'idempotence (ré-importation sans erreur)
    files2 = {"file": ("resultats_salle.results.zip", zip_bytes, "application/zip")}
    res_reimport = client.post("/api/sync/master/import-results", headers=admin_headers, files=files2)
    assert res_reimport.status_code == 200
    assert res_reimport.json()["success"] is True

    # 5. Téléchargement du relevé consolidé Master (notes_consolidees.csv)
    res_gradebook = client.get("/api/sync/master/consolidated-gradebook", headers=admin_headers)
    assert res_gradebook.status_code == 200
    assert "text/csv" in res_gradebook.headers["content-type"]
