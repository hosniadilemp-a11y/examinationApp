import pytest
import json
from backend.app.models import Exam, Question, User, ExamSession, StudentAttempt

# ==============================================================================
# TESTS PHASE 4 : SURVEILLANCE EN DIRECT & PROCTORING (ALGOEXAMINATION)
# ==============================================================================

def test_open_session_and_listing(client, teacher_headers, admin_headers):
    # Création d'un examen pour le module PYTHON_INIT
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Session Test Examen", "duration_minutes": 60}
    )
    exam_id = res_exam.json()["id"]

    # L'enseignant ouvre une session pour la SALLE-TP-A
    res_session = client.post(
        "/api/proctor/sessions",
        headers=teacher_headers,
        json={"exam_id": exam_id, "room_id": "SALLE-TP-A"}
    )
    assert res_session.status_code == 200
    session_id = res_session.json()["session_id"]
    assert res_session.json()["status"] == "waiting"

    # Liste des sessions
    res_list = client.get("/api/proctor/sessions", headers=teacher_headers)
    assert res_list.status_code == 200
    s_ids = [s["session_id"] for s in res_list.json()]
    assert session_id in s_ids

def test_synchronized_exam_launch(client, admin_headers, teacher_headers, student_headers, db_session):
    # 1. Création de l'examen et affectation au groupe GRP-1
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Lancement Synchronisé Test", "duration_minutes": 45, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    # 2. Ouverture de la session de salle en attente
    res_session = client.post(
        "/api/proctor/sessions",
        headers=teacher_headers,
        json={"exam_id": exam_id, "room_id": "SALLE-TP-1"}
    )
    session_id = res_session.json()["session_id"]

    # 3. L'étudiant 1 rejoint la salle et attend dans le lobby
    res_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert res_start.status_code == 200
    attempt_id = res_start.json()["attempt_id"]
    assert res_start.json()["attempt_status"] == "waiting"

    # 4. L'enseignant clique sur "Lancer l'Épreuve" sur son dashboard
    res_launch = client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)
    assert res_launch.status_code == 200
    assert res_launch.json()["success"] is True
    assert res_launch.json()["status"] == "in_progress"

    # 5. Vérification que l'étudiant est automatiquement débloqué et passe en 'in_progress'
    res_check = client.get(f"/api/student/attempts/{attempt_id}/status", headers=student_headers)
    assert res_check.status_code == 200
    assert res_check.json()["status"] == "in_progress"

def test_proctor_telemetry_grid_overview(client, admin_headers, teacher_headers, student_headers):
    # Création d'un examen avec 2 questions
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Grille Télémétrie", "duration_minutes": 60, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Q1", "points": 1.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    q2 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 2, "type": "boolean", "prompt_markdown": "Q2", "points": 1.0, "options_json": "[]", "correct_answers_json": json.dumps(False)}
    ).json()

    # Session
    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-1"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # L'étudiant démarre et répond à Q1 (50% de progression)
    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q1["id"], "answer": True})

    # L'enseignant consulte la grille de télémétrie en direct
    res_overview = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=teacher_headers)
    assert res_overview.status_code == 200
    data = res_overview.json()

    assert data["session_id"] == session_id
    assert len(data["student_cards"]) == 1
    card = data["student_cards"][0]
    assert card["username"] == "etudiant1"
    assert card["status"] == "in_progress"
    assert card["answered_count"] == 1
    assert card["total_questions"] == 2
    assert card["progress_pct"] == 50

def test_proctor_extend_time(client, admin_headers, teacher_headers):
    # Création session
    res_exam = client.post("/api/exams", headers=admin_headers, json={"module_code": "PYTHON_INIT", "title": "Test Extra Time", "duration_minutes": 30})
    exam_id = res_exam.json()["id"]
    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-1"}).json()["session_id"]

    # Prolongation collective de +10 minutes
    res_extend = client.post(
        f"/api/proctor/sessions/{session_id}/extend-time",
        headers=teacher_headers,
        json={"extra_minutes": 10}
    )
    assert res_extend.status_code == 200
    assert res_extend.json()["success"] is True
    assert res_extend.json()["extra_minutes"] == 10

def test_proctor_force_submit(client, admin_headers, teacher_headers, student_headers):
    # Création examen & session
    res_exam = client.post("/api/exams", headers=admin_headers, json={"module_code": "PYTHON_INIT", "title": "Test Force Submit", "duration_minutes": 30, "group_ids": ["GRP-1"]})
    exam_id = res_exam.json()["id"]

    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Q1", "points": 10.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-1"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # L'étudiant commence et répond
    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q1["id"], "answer": True})

    # Le surveillant force la soumission de la copie
    res_force = client.post(
        f"/api/proctor/sessions/{session_id}/attempts/{attempt_id}/force-submit",
        headers=teacher_headers
    )
    assert res_force.status_code == 200
    assert res_force.json()["success"] is True
    assert res_force.json()["final_mark"] == 20.0  # 10/10 points ramené sur 20.0

    # L'étudiant est maintenant marqué comme soumis
    res_status = client.get(f"/api/student/attempts/{attempt_id}/status", headers=student_headers)
    assert res_status.json()["status"] == "submitted"

def test_student_forbidden_from_proctor_actions(client, student_headers):
    # Un étudiant ne peut pas lancer une épreuve ni soumettre de force une copie
    res = client.post("/api/proctor/sessions/SESS-FAKE/launch", headers=student_headers)
    assert res.status_code == 403
