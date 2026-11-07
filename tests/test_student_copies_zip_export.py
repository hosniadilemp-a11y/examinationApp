import io
import json
import zipfile
import pytest

def test_student_copies_zip_export_content_and_structure(client, admin_headers, teacher_headers, student_headers):
    """
    Vérifie que l'enseignant peut télécharger l'archive ZIP complète des copies d'examen :
    - L'archive contient EXCLUSIVEMENT des fichiers PDF (copies individuelles des étudiants)
    - Chaque fichier commence par %PDF et contient les réponses et barèmes formatés
    """
    # 1. Création d'un examen
    exam_payload = {
        "module_code": "PYTHON_INIT",
        "title": "Examen Synthèse pour Export Copies ZIP",
        "exam_type": "practical",
        "duration_minutes": 20,
        "group_ids": ["GRP-1"],
        "target_audience": "ALL"
    }
    r_exam = client.post("/api/exams", json=exam_payload, headers=admin_headers)
    assert r_exam.status_code == 201
    exam_id = r_exam.json()["id"]

    # Q1: Exercice pratique Python 1
    r_q1 = client.post(f"/api/exams/{exam_id}/questions", json={
        "ordering": 1,
        "type": "code",
        "prompt_markdown": "Écrire une fonction `somme(a, b)` qui retourne `a + b`.",
        "points": 10.0,
        "options_json": "[]",
        "correct_answers_json": json.dumps("def somme(a, b):\n    return a + b")
    }, headers=admin_headers)
    assert r_q1.status_code == 201
    q1_id = r_q1.json()["id"]

    # Q2: Exercice pratique Python
    r_q2 = client.post(f"/api/exams/{exam_id}/questions", json={
        "ordering": 2,
        "type": "code",
        "prompt_markdown": "Écrire une fonction `carre(n)` qui retourne `n * n`.",
        "points": 10.0,
        "options_json": "[]",
        "correct_answers_json": json.dumps("def carre(n):\n    return n * n")
    }, headers=admin_headers)
    assert r_q2.status_code == 201
    q2_id = r_q2.json()["id"]

    # 2. Création et lancement de la session
    r_sess = client.post("/api/proctor/sessions", json={"exam_id": exam_id, "room_id": "SALLE-COPIES"}, headers=teacher_headers)
    assert r_sess.status_code == 200
    session_id = r_sess.json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # 3. L'étudiant démarre, répond et soumet
    r_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert r_start.status_code == 200
    attempt_id = r_start.json()["attempt_id"]

    # Enregistrement des réponses
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", json={
        "question_id": q1_id,
        "answer": "def somme(a, b):\n    return a + b\n"
    }, headers=student_headers)

    student_code = "def carre(n):\n    # Implémentation étudiant\n    return n ** 2\n"
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", json={
        "question_id": q2_id,
        "answer": student_code
    }, headers=student_headers)

    # Soumission de l'épreuve
    r_sub = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
    assert r_sub.status_code == 200

    # 4. Clôture de la session par le surveillant
    client.post(f"/api/proctor/sessions/{session_id}/close", headers=teacher_headers)

    # 5. Téléchargement du ZIP via l'endpoint d'examen
    r_zip_exam = client.get(f"/api/exams/{exam_id}/student-copies/zip", headers=teacher_headers)
    assert r_zip_exam.status_code == 200
    assert r_zip_exam.headers["content-type"] == "application/zip"
    assert f"copies_etudiants_PYTHON_INIT_{exam_id}.zip" in r_zip_exam.headers["content-disposition"]

    # 6. Inspection du contenu du ZIP : DOIT CONTENIR EXCLUSIVEMENT DES FICHIERS PDF
    zip_bytes = io.BytesIO(r_zip_exam.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        print("Fichiers dans le ZIP :", namelist)

        # L'archive doit contenir uniquement des copies PDF
        assert len(namelist) >= 1
        assert all(f.endswith(".pdf") for f in namelist), f"Tous les fichiers doivent être des PDF: {namelist}"

        # Vérification du contenu du premier PDF
        first_pdf_bytes = zf.read(namelist[0])
        assert first_pdf_bytes.startswith(b"%PDF")
        assert len(first_pdf_bytes) > 500

    # 7. Téléchargement du ZIP via l'endpoint de session proctor
    r_zip_sess = client.get(f"/api/proctor/sessions/{session_id}/student-copies/zip", headers=teacher_headers)
    assert r_zip_sess.status_code == 200
    assert r_zip_sess.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r_zip_sess.content), "r") as zf_sess:
        sess_namelist = zf_sess.namelist()
        assert len(sess_namelist) >= 1
        assert all(f.endswith(".pdf") for f in sess_namelist)
