import pytest
import io
import zipfile
import json
import hashlib
from backend.app.models import Exam, Question, User, Group, ExamSession, StudentAttempt

# ==============================================================================
# TESTS PHASE 5 : SYNCHRONISATION MANUELLE PAR CLÉ USB & MASTER (OPTION B)
# ==============================================================================

def test_export_exam_package_and_sha256(client, admin_headers):
    # 1. Création d'un examen avec 2 questions
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Export Package Test",
            "duration_minutes": 60,
            "group_ids": ["GRP-1"],
            "shuffle_questions": True,
            "shuffle_options": True
        }
    )
    exam_id = res_exam.json()["id"]

    client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1,
            "type": "boolean",
            "prompt_markdown": "Python est un langage interprété ?",
            "points": 1.0,
            "options_json": "[]",
            "correct_answers_json": json.dumps(True)
        }
    )

    # 2. Téléchargement du package .exam.zip
    res_export = client.get(f"/api/sync/exams/{exam_id}/export-package", headers=admin_headers)
    assert res_export.status_code == 200
    assert "application/zip" in res_export.headers["content-type"]

    # 3. Vérification du contenu de l'archive ZIP
    zip_bytes = io.BytesIO(res_export.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert "exam_manifest.json" in namelist
        assert "checksum.sha256" in namelist

        manifest_bytes = zf.read("exam_manifest.json")
        sha = zf.read("checksum.sha256").decode("utf-8")
        assert hashlib.sha256(manifest_bytes).hexdigest() == sha

        manifest = json.loads(manifest_bytes.decode("utf-8"))
        assert manifest["exam"]["id"] == exam_id
        assert len(manifest["questions"]) == 1

def test_import_exam_package_into_room_server(client, admin_headers, teacher_headers):
    # Création d'une archive zip valide en mémoire
    manifest = {
        "schema_version": "1.0.0",
        "exam": {
            "id": "EXAM-IMPORT-TEST-99",
            "module_code": "CRYPTO",
            "title": "Examen Importé Clé USB",
            "duration_minutes": 90,
            "global_points": 20.0,
            "navigation_mode": "free",
            "shuffle_questions": True,
            "shuffle_options": True,
            "partial_credit_enabled": True,
            "default_negative_penalty": 0.5,
            "assigned_groups": ["GRP-1"]
        },
        "questions": [{
            "id": "Q-IMP-1",
            "ordering": 1,
            "type": "single_choice",
            "prompt_markdown": "Chiffre de César : décalage de combien ?",
            "points": 2.0,
            "negative_penalty": 0.5,
            "time_limit_seconds": 60,
            "options_json": json.dumps([{"id": "a", "text": "3"}, {"id": "b", "text": "10"}]),
            "correct_answers_json": json.dumps("a")
        }]
    }

    manifest_bytes = json.dumps(manifest).encode("utf-8")
    sha = hashlib.sha256(manifest_bytes).hexdigest()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("exam_manifest.json", manifest_bytes)
        zf.writestr("checksum.sha256", sha)

    zip_buffer.seek(0)
    files = {"file": ("examen_crypto.exam.zip", zip_buffer.getvalue(), "application/zip")}

    # L'enseignant importe le package sur le serveur de salle
    res_import = client.post("/api/sync/exams/import-package", headers=teacher_headers, files=files)
    assert res_import.status_code == 200
    assert res_import.json()["success"] is True
    assert res_import.json()["exam_id"] == "EXAM-IMPORT-TEST-99"
    assert res_import.json()["questions_count"] == 1

    # Vérification que l'examen et sa question sont bien présents en base
    res_detail = client.get("/api/exams/EXAM-IMPORT-TEST-99", headers=teacher_headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["title"] == "Examen Importé Clé USB"

def test_export_results_and_master_consolidation_idempotence(client, admin_headers, teacher_headers, student_headers):
    # 1. Mise en place d'un examen et d'une session avec 1 copie soumise
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Résultats Sync", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Q1 ?", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-3"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # L'étudiant passe et soumet l'épreuve
    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q1["id"], "answer": True})
    client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)

    # 2. Exportation de l'archive .results.zip par l'enseignant de salle
    res_export = client.get(f"/api/sync/sessions/{session_id}/export-results", headers=teacher_headers)
    assert res_export.status_code == 200
    results_zip_bytes = io.BytesIO(res_export.content)

    # Vérification des fichiers internes du ZIP
    with zipfile.ZipFile(results_zip_bytes, "r") as zf:
        namelist = zf.namelist()
        assert "session_metadata.json" in namelist
        assert "student_submissions.csv" in namelist
        assert "question_answers.csv" in namelist
        assert "audit_logs.json" in namelist

    # 3. Import & Réconciliation sur l'instance Master
    results_zip_bytes.seek(0)
    files = {"file": ("resultats.results.zip", results_zip_bytes, "application/zip")}
    res_master_import = client.post("/api/sync/master/import-results", headers=admin_headers, files=files)
    assert res_master_import.status_code == 200
    assert res_master_import.json()["success"] is True

    # 4. TEST DE L'IDEMPOTENCE : Ré-import de la même archive de résultats
    results_zip_bytes.seek(0)
    files_again = {"file": ("resultats.results.zip", results_zip_bytes, "application/zip")}
    res_reimport = client.post("/api/sync/master/import-results", headers=admin_headers, files=files_again)
    assert res_reimport.status_code == 200
    # Aucune création de doublon : 0 nouvelle tentative insérée, 1 mise à jour idempotente
    assert res_reimport.json()["imported_attempts"] == 0
    assert res_reimport.json()["updated_attempts"] == 1

    # 5. Export du tableur de notes consolidé multi-salles
    res_gradebook = client.get("/api/sync/master/consolidated-gradebook", headers=admin_headers)
    assert res_gradebook.status_code == 200
    assert "text/csv" in res_gradebook.headers["content-type"]
    assert "SALLE-TP-3" in res_gradebook.text
    assert "etudiant1" in res_gradebook.text
