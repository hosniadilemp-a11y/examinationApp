import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app import models
from backend.app.security import hash_password, create_access_token

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_group(db, gid="GRP-1"):
    grp = db.query(models.Group).filter(models.Group.id == gid).first()
    if not grp:
        grp = models.Group(id=gid, name="Groupe Test", description="Test Group")
        db.add(grp)
        db.commit()
    return gid

def get_auth_headers(db, username: str, role: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        gid = ensure_group(db) if role == "student" else None
        user = models.User(
            id=f"test-id-{username}",
            username=username,
            password_hash=hash_password("Secret123!"),
            plain_password="Secret123!",
            role=role,
            group_id=gid,
            full_name=f"Test {username}",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif role == "student" and not user.group_id:
        user.group_id = ensure_group(db)
        db.commit()
        db.refresh(user)
    token = create_access_token(data={"sub": str(user.id), "role": user.role, "username": user.username})
    return {"Authorization": f"Bearer {token}"}

def ensure_module(db, code: str, teacher_username: str = None):
    mod = db.query(models.Module).filter(models.Module.code == code).first()
    if not mod:
        mod = models.Module(code=code, title=f"Module {code}", description="Test module")
        db.add(mod)
        db.commit()
        db.refresh(mod)
    if teacher_username:
        user = db.query(models.User).filter(models.User.username == teacher_username).first()
        if user and mod not in user.assigned_modules:
            user.assigned_modules.append(mod)
            db.commit()

def test_exam_deletion_lifecycle_and_roles(db_session):
    admin_headers = get_auth_headers(db_session, "superadmin_test", "admin")
    teacher_headers = get_auth_headers(db_session, "teacher_test", "teacher")
    ensure_module(db_session, "TEST101", teacher_username="teacher_test")
    
    # 1. Create an exam before start
    exam_payload = {
        "title": "Lifecycle Test Exam",
        "description": "Lifecycle testing",
        "module_code": "TEST101",
        "duration_minutes": 10,
        "is_active": True,
        "is_published": True,
        "target_audience": "TEST_SPECIALITE"
    }
    r = client.post("/api/exams", json=exam_payload, headers=teacher_headers)
    assert r.status_code == 201, r.text
    exam_id = r.json()["id"]

    # Teacher creates session
    r = client.post("/api/proctor/sessions", json={"exam_id": exam_id, "room_id": "Lab 1"}, headers=teacher_headers)
    assert r.status_code == 200, r.text
    sess_id = r.json()["session_id"]

    # Status is waiting / not_started -> Deletion by teacher should succeed
    # Let's test deleting session / exam
    r_del_before = client.delete(f"/api/exams/{exam_id}", headers=teacher_headers)
    assert r_del_before.status_code in [200, 204], r_del_before.text

    # Recreate exam for in_progress test
    r2 = client.post("/api/exams", json=exam_payload, headers=teacher_headers)
    assert r2.status_code == 201
    exam2_id = r2.json()["id"]
    r_sess2 = client.post("/api/proctor/sessions", json={"exam_id": exam2_id, "room_id": "Lab 1"}, headers=teacher_headers)
    assert r_sess2.status_code == 200
    sess2_id = r_sess2.json()["session_id"]

    # Start session -> status = in_progress
    r_start = client.post(f"/api/proctor/sessions/{sess2_id}/launch", headers=teacher_headers)
    assert r_start.status_code == 200

    # In progress: Neither teacher nor admin can delete
    r_del_in_progress_teacher = client.delete(f"/api/exams/{exam2_id}", headers=teacher_headers)
    assert r_del_in_progress_teacher.status_code == 400
    assert "en cours" in r_del_in_progress_teacher.json()["detail"].lower()

    r_del_in_progress_admin = client.delete(f"/api/exams/{exam2_id}", headers=admin_headers)
    assert r_del_in_progress_admin.status_code == 400

    # Close session -> status = completed
    r_close = client.post(f"/api/proctor/sessions/{sess2_id}/close", headers=teacher_headers)
    assert r_close.status_code == 200

    # When closed/completed:
    # Teacher deletion should be forbidden (403)
    r_del_closed_teacher = client.delete(f"/api/exams/{exam2_id}", headers=teacher_headers)
    assert r_del_closed_teacher.status_code == 403
    assert "super administrateur" in r_del_closed_teacher.json()["detail"].lower()

    # Admin deletion should be allowed (200 or 204)
    r_del_closed_admin = client.delete(f"/api/exams/{exam2_id}", headers=admin_headers)
    assert r_del_closed_admin.status_code in [200, 204]

def test_expired_exam_auto_close_and_access_block(db_session):
    teacher_headers = get_auth_headers(db_session, "teacher_expired_test", "teacher")
    student_headers = get_auth_headers(db_session, "student_expired_test", "student")
    ensure_module(db_session, "EXP101", teacher_username="teacher_expired_test")
    
    # Create exam with 1 minute duration
    exam_payload = {
        "title": "Expired Test Exam",
        "description": "Expiration testing",
        "module_code": "EXP101",
        "duration_minutes": 1,
        "is_active": True,
        "is_published": True,
        "target_audience": "ALL"
    }
    r = client.post("/api/exams", json=exam_payload, headers=teacher_headers)
    assert r.status_code == 201
    exam_id = r.json()["id"]

    # Associer le groupe de l'étudiant à l'examen
    grp = db_session.query(models.Group).filter(models.Group.id == "GRP-1").first()
    exam_obj = db_session.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if grp and exam_obj and grp not in exam_obj.groups:
        exam_obj.groups.append(grp)
        db_session.commit()

    # Create session
    r_sess = client.post("/api/proctor/sessions", json={"exam_id": exam_id, "room_id": "Lab Exp"}, headers=teacher_headers)
    assert r_sess.status_code == 200
    sess_id = r_sess.json()["session_id"]

    # Start session
    client.post(f"/api/proctor/sessions/{sess_id}/launch", headers=teacher_headers)

    # Manually backdate started_at to simulate expiration (> 1 minute ago)
    session_obj = db_session.query(models.ExamSession).filter(models.ExamSession.id == sess_id).first()
    session_obj.started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    # Student attempts to start or resume exam after expiration -> Must be blocked (403)
    r_student = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert r_student.status_code == 403
    assert "terminée" in r_student.json()["detail"].lower() or "clôturée" in r_student.json()["detail"].lower()

    # Check that session was marked as completed
    db_session.refresh(session_obj)
    assert session_obj.status == "completed"

def test_frontend_ui_contracts_for_teacher_and_admin():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    with open("frontend/js/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    with open("frontend/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # 1. Check HTML admin table columns
    assert "Titre de l'Épreuve" in html
    assert "Statut Session" in html
    assert "<th>Module</th>" not in html  # Deleted standalone module column in exam tables

    # 2. Check CSS for dropdown menu and compact column
    assert ".row-menu-wrapper" in css
    assert ".btn-row-menu-toggle" in css
    assert ".row-actions-dropdown" in css
    assert ".col-specialite-compact" in css

    # 3. Check JS implementation for loadTeacherExams
    assert "Titre de l'Épreuve" in js
    assert "Statut Session" in js
    assert "Spécialité" in js
    assert "btn-row-menu-toggle" in js
    assert "row-actions-dropdown" in js
    assert "isCompleted" in js
    assert "isInProgress" in js