import pytest
from datetime import datetime, timezone
from backend.app.database import SessionLocal
from backend.app.models import Exam, ExamSession, User, StudentAttempt, StudentAnswer
from backend.app.services.python_exam_generator import normalize_curriculum_question
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_normalize_curriculum_question_types():
    """Vérifie la normalisation rigoureuse de tous les types de questions."""
    # 1. code / coding -> code_python
    q_code = {"type": "code", "text": "Écrire une fonction `f`", "starter_code": "def f(): pass", "tests": []}
    norm_code = normalize_curriculum_question(q_code, 1)
    assert norm_code["type"] == "code_python"
    assert "starter_code" in norm_code["options"]

    # 2. boolean -> boolean
    q_bool = {"type": "boolean", "text": "Python est compilé ?", "correct": False}
    norm_bool = normalize_curriculum_question(q_bool, 2)
    assert norm_bool["type"] == "boolean"
    assert norm_bool["correct_answers"] is False

    # 3. matching -> matching
    q_match = {"type": "matching", "text": "Associer", "pairs": {"len": "taille", "str": "chaine"}}
    norm_match = normalize_curriculum_question(q_match, 3)
    assert norm_match["type"] == "matching"
    assert norm_match["correct_answers"] == {"len": "taille", "str": "chaine"}

    # 4. mcq with list of answers -> multi_choice
    q_mcq_multi = {"type": "mcq", "text": "Quels sont les itérables ?", "options": ["list", "int", "tuple"], "correct": [0, 2]}
    norm_multi = normalize_curriculum_question(q_mcq_multi, 4)
    assert norm_multi["type"] == "multi_choice"
    assert norm_multi["correct_answers"] == [0, 2]

    # 5. mcq with single answer -> single_choice
    q_mcq_single = {"type": "mcq", "text": "Type de 42 ?", "options": ["int", "str", "float"], "correct": 0}
    norm_single = normalize_curriculum_question(q_mcq_single, 5)
    assert norm_single["type"] == "single_choice"
    assert norm_single["correct_answers"] == 0

def test_proctor_overview_total_questions_and_anticheat_suspension():
    db = SessionLocal()
    try:
        # Check seeded Python theoretical exam has 40 questions in DB
        exam = db.query(Exam).filter(Exam.id == "EXAM-THEO-PYTHON").first()
        assert exam is not None
        assert len(exam.questions) == 40
        assert "CONFIG_RANDOM_STUDENT_QUESTIONS=20" in exam.instructions
        exam_id = str(exam.id)

        # Ensure we have an active in_progress session with fresh started_at
        session = db.query(ExamSession).filter(ExamSession.exam_id == exam_id, ExamSession.status == "in_progress").first()
        if not session:
            session = ExamSession(
                id=f"SESS-TEST-FIX-{int(datetime.now().timestamp())}",
                exam_id=exam_id,
                room_id="SALLE-TEST",
                status="in_progress",
                started_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.commit()
        else:
            session.started_at = datetime.now(timezone.utc)
            db.commit()

        session_id = str(session.id)

        # Delete any previous attempt for etu_dev1
        etu = db.query(User).filter(User.username == "etu_dev1").first()
        if etu:
            prev_attempts = db.query(StudentAttempt).filter(StudentAttempt.student_id == etu.id).all()
            for att in prev_attempts:
                db.query(StudentAnswer).filter(StudentAnswer.attempt_id == att.id).delete()
                db.delete(att)
            db.commit()
    finally:
        db.close()

    # Login as teacher
    login_res = client.post("/api/auth/login", json={"username": "prof_python", "password": "ProfPython1!"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check proctor overview endpoint
    res = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    
    # Verify that total_questions in the overview cards is 20 (not 40!)
    for card in data.get("student_cards", []):
        if card.get("total_questions"):
            assert card["total_questions"] == 20, f"Expected 20 questions in proctor overview, got {card['total_questions']}"

    # Login as student etu_dev1
    s_login = client.post("/api/auth/login", json={"username": "etu_dev1", "password": "StudentDev1!"})
    assert s_login.status_code == 200
    s_token = s_login.json()["access_token"]
    s_headers = {"Authorization": f"Bearer {s_token}"}

    # Start student attempt
    start_res = client.post(f"/api/student/exams/{exam_id}/start", headers=s_headers)
    assert start_res.status_code == 200
    s_data = start_res.json()
    attempt_id = s_data.get("attempt_id")
    assert attempt_id is not None

    # Report 4 security warnings
    warn_res = client.post(
        f"/api/student/attempts/{attempt_id}/security-event",
        headers=s_headers,
        json={
            "event_type": "SECURITY_WARNING",
            "details": {
                "reason": "Sortie d'écran répétée",
                "warning_number": 4
            }
        }
    )
    assert warn_res.status_code == 200
    warn_data = warn_res.json()
    assert warn_data["is_suspended"] is True
    assert warn_data["status"] == "suspended"
    assert warn_data["suspension_remaining_seconds"] == 300

    # Check attempt status via student polling
    status_res = client.get(f"/api/student/attempts/{attempt_id}/status", headers=s_headers)
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["status"] == "suspended"
    assert 295 <= st_data["suspension_remaining_seconds"] <= 300

    # Teacher unlocks the student
    unlock_res = client.post(f"/api/proctor/sessions/{session_id}/attempts/{attempt_id}/unlock", headers=headers)
    assert unlock_res.status_code == 200

    # Verify student is now in_progress
    status_res2 = client.get(f"/api/student/attempts/{attempt_id}/status", headers=s_headers)
    assert status_res2.status_code == 200
    assert status_res2.json()["status"] == "in_progress"
    assert status_res2.json()["suspension_remaining_seconds"] == 0
