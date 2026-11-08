import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models import User, Module, PracticeAttempt
from backend.app.database import get_db, SessionLocal
from backend.app.security import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_headers():
    db = SessionLocal()
    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        admin = User(
            username="test_super_admin",
            full_name="Super Admin",
            role="admin",
            hashed_password="fake"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = create_access_token(data={"sub": str(admin.id), "role": admin.role})
    db.close()
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def student_headers():
    db = SessionLocal()
    student = db.query(User).filter(User.role == "student").first()
    if not student:
        student = User(
            username="test_student_spec",
            full_name="Student Spec",
            role="student",
            speciality="DEV-IA",
            hashed_password="fake"
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    token = create_access_token(data={"sub": str(student.id), "role": student.role})
    db.close()
    return {"Authorization": f"Bearer {token}"}

def test_get_level_tests_configs(client, admin_headers):
    res = client.get("/api/admin/level-tests/configs", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    codes = [d["code"] for d in data]
    assert "PYTHON_PROG" in codes
    assert "SYS_EXPLOIT" in codes
    assert "CYBER_CRYPTO" in codes
    for item in data:
        assert item["total_questions"] >= 100

def test_update_level_test_name_and_persistence(client, admin_headers, student_headers):
    # Rename PYTHON_PROG
    new_title = "Programmation Python & Algorithmes Avancés"
    new_desc = "Conception d'algorithmes, structures de données et syntaxe Python."
    res = client.put(
        "/api/admin/level-tests/PYTHON_PROG",
        headers=admin_headers,
        json={"title": new_title, "description": new_desc}
    )
    assert res.status_code == 200
    assert res.json()["config"]["title"] == new_title

    # Verify student practice modules returns updated title
    res_student = client.get("/api/practice/modules", headers=student_headers)
    assert res_student.status_code == 200
    modules = res_student.json()
    py_mod = next((m for m in modules if m["code"] == "PYTHON_PROG"), None)
    assert py_mod is not None
    assert py_mod["title"] == new_title
    assert py_mod["description"] == new_desc
    assert py_mod["total_questions"] >= 100

def test_export_level_tests_pdf(client, admin_headers):
    res = client.get("/api/admin/level-tests/export-pdf?speciality=DEV-IA", headers=admin_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000
    # Also test ALL specialities
    res_all = client.get("/api/admin/level-tests/export-pdf?speciality=ALL", headers=admin_headers)
    assert res_all.status_code == 200
    assert res_all.headers["content-type"] == "application/pdf"

def test_purge_scores_endpoints(client, admin_headers):
    # Test practice purge
    res_practice = client.post("/api/admin/purge-practice-scores", headers=admin_headers)
    assert res_practice.status_code == 200
    assert "purgés" in res_practice.json()["message"]

    # Test exam purge
    res_exam = client.post("/api/admin/purge-exam-scores", headers=admin_headers)
    assert res_exam.status_code == 200
    assert "purgés" in res_exam.json()["message"]
