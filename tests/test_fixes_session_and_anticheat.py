import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SessionLocal
from backend.app.models import User, Group, Exam, Question, ExamSession, StudentAttempt
from backend.app.security import hash_password
from backend.app.services.python_exam_generator import normalize_curriculum_question

client = TestClient(app)

def test_normalize_curriculum_question_types():
    # 1. yesno -> boolean
    q_yesno = {"type": "yesno", "text": "Python est un langage interprété ?", "correct": True, "penalty": 0.5}
    norm_yn = normalize_curriculum_question(q_yesno, 1)
    assert norm_yn["type"] == "boolean"
    assert norm_yn["correct_answers"] is True
    assert norm_yn["negative_penalty"] == 0.5

    # 2. simple_blank -> fill_blank with code block
    q_blank = {"type": "simple_blank", "text": "Complétez le mot-clé manquant", "code": "def func():\n    ____ 42", "answer": "return"}
    norm_blank = normalize_curriculum_question(q_blank, 2)
    assert norm_blank["type"] == "fill_blank"
    assert "```python" in norm_blank["prompt_markdown"]
    assert "return" in norm_blank["correct_answers"]

    # 3. matching -> matching with pairs
    q_match = {"type": "matching", "text": "Associez les fonctions", "pairs": {"len": "taille", "str": "chaine"}}
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

        # Get or create an exam session
        session = db.query(ExamSession).filter(ExamSession.exam_id == exam.id).first()
        if not session:
            session = ExamSession(
                id="SESS-TEST-FIX",
                exam_id=exam.id,
                room_id="SALLE-TEST",
                status="in_progress",
                started_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.commit()

        # Login as teacher
        login_res = client.post("/api/auth/login", json={"username": "prof_python", "password": "ProfPython1!"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check proctor overview endpoint
        res = client.get(f"/api/proctor/sessions/{session.id}/overview", headers=headers)
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
        start_res = client.post(f"/api/student/exams/{exam.id}/start", headers=s_headers)
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
        unlock_res = client.post(f"/api/proctor/sessions/{session.id}/attempts/{attempt_id}/unlock", headers=headers)
        assert unlock_res.status_code == 200

        # Verify student is now in_progress
        status_res2 = client.get(f"/api/student/attempts/{attempt_id}/status", headers=s_headers)
        assert status_res2.status_code == 200
        assert status_res2.json()["status"] == "in_progress"
        assert status_res2.json()["suspension_remaining_seconds"] == 0

    finally:
        db.close()
