import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, Base
from backend.app.models import User, Group, Exam, Question, StudentAttempt
from backend.app.security import hash_password

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_security_data():
    db = next(get_db())
    
    # 1. Groupe
    grp = db.query(Group).filter(Group.id == "GRP-SEC-1").first()
    if not grp:
        grp = Group(id="GRP-SEC-1", name="Groupe Sécurité 2025")
        db.add(grp)
        db.commit()

    # 2. Utilisateurs : Admin, Enseignant, Étudiant 1 (Promotion 2024-2025), Étudiant 2 (Promotion 2025-2026)
    adm = db.query(User).filter(User.username == "admin_sec_test").first()
    if not adm:
        adm = User(
            id="ADM-SEC-01",
            username="admin_sec_test",
            password_hash=hash_password("admin123"),
            full_name="Admin Securite",
            role="admin"
        )
        db.add(adm)

    prof = db.query(User).filter(User.username == "prof_sec_test").first()
    if not prof:
        prof = User(
            id="PRF-SEC-01",
            username="prof_sec_test",
            password_hash=hash_password("prof123"),
            full_name="Professeur Securite",
            role="teacher"
        )
        db.add(prof)

    etu1 = db.query(User).filter(User.username == "etu_promo_2024").first()
    if not etu1:
        etu1 = User(
            id="ETU-2024-01",
            username="etu_promo_2024",
            password_hash=hash_password("etu123"),
            full_name="Etudiant Promo 2024",
            role="student",
            group_id="GRP-SEC-1",
            enrollment_year="2024-2025"
        )
        db.add(etu1)

    etu2 = db.query(User).filter(User.username == "etu_promo_2025").first()
    if not etu2:
        etu2 = User(
            id="ETU-2025-01",
            username="etu_promo_2025",
            password_hash=hash_password("etu123"),
            full_name="Etudiant Promo 2025",
            role="student",
            group_id="GRP-SEC-1",
            enrollment_year="2025-2026"
        )
        db.add(etu2)

    db.commit()
    return {"admin": "admin_sec_test", "teacher": "prof_sec_test", "student": "etu_promo_2024"}

def test_enrollment_year_filtering_and_distinct_years(setup_security_data):
    """Vérifie que les administrateurs et enseignants peuvent lister et filtrer par promotion."""
    # Login Admin
    res_login = client.post("/api/auth/login", json={"username": "admin_sec_test", "password": "admin123"})
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Endpoint distinct enrollment years
    res_years = client.get("/api/users/enrollment-years", headers=headers)
    assert res_years.status_code == 200
    years = res_years.json()
    assert isinstance(years, list)
    assert "2024-2025" in years or "2025-2026" in years

    # 2. Filtrer les étudiants de la promotion 2024-2025
    res_filter_2024 = client.get("/api/users?role=student&enrollment_year=2024-2025", headers=headers)
    assert res_filter_2024.status_code == 200
    students_2024 = res_filter_2024.json()
    assert all(s["enrollment_year"] == "2024-2025" for s in students_2024)
    assert any(s["username"] == "etu_promo_2024" for s in students_2024)
    assert not any(s["username"] == "etu_promo_2025" for s in students_2024)

    # 3. Filtrer les étudiants de la promotion 2025-2026
    res_filter_2025 = client.get("/api/users?role=student&enrollment_year=2025-2026", headers=headers)
    assert res_filter_2025.status_code == 200
    students_2025 = res_filter_2025.json()
    assert all(s["enrollment_year"] == "2025-2026" for s in students_2025)
    assert any(s["username"] == "etu_promo_2025" for s in students_2025)
    assert not any(s["username"] == "etu_promo_2024" for s in students_2025)

def test_security_rbac_blocks_student_from_admin_and_teacher_endpoints(setup_security_data):
    """Vérifie qu'un étudiant reçoit rigoureusement HTTP 403 Forbidden sur toute route enseignant/admin."""
    # Login Étudiant
    res_login = client.post("/api/auth/login", json={"username": "etu_promo_2024", "password": "etu123"})
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {token}"}

    # Tentative d'accès aux statistiques administratives
    res_admin_stats = client.get("/api/admin/statistics/overview", headers=student_headers)
    assert res_admin_stats.status_code == 403

    # Tentative de création d'examen (réservé enseignant/admin)
    res_create_exam = client.post("/api/exams", json={
        "title": "Hacked Exam",
        "module_code": "PYTHON_INIT",
        "duration_minutes": 30
    }, headers=student_headers)
    assert res_create_exam.status_code == 403

    # Tentative de suppression d'utilisateur
    res_del_user = client.delete("/api/users/ADM-SEC-01", headers=student_headers)
    assert res_del_user.status_code == 403

    # Tentative de surveillance proctor
    res_proctor = client.get("/api/proctor/sessions", headers=student_headers)
    assert res_proctor.status_code == 403

def test_security_score_tampering_impossible(setup_security_data):
    """Vérifie que même si un étudiant tente d'injecter une fausse note dans sa copie, le serveur calcule la note réelle."""
    db = next(get_db())
    
    # Création d'un examen de test
    grp = db.query(Group).filter(Group.id == "GRP-SEC-1").first()
    exam_id = "EXAM-SEC-GRADE-TEST"
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        exam = Exam(
            id=exam_id,
            title="Épreuve Sécurité Notation",
            module_code="PYTHON_INIT",
            exam_type="theoretical",
            duration_minutes=30,
            global_points=20.0
        )
        exam.groups.append(grp)
        db.add(exam)
        db.flush()
        
        # Question avec réponse 'A' (correcte)
        q = Question(
            id="Q-SEC-01",
            exam_id=exam_id,
            ordering=1,
            type="single_choice",
            points=20.0,
            prompt_markdown="Question Test Sécurité",
            options_json='[{"id":"A","text":"Choix Correct"},{"id":"B","text":"Choix Faux"}]',
            correct_answers_json='["A"]'
        )
        db.add(q)
        db.commit()
    elif grp not in exam.groups:
        exam.groups.append(grp)
        db.commit()

    # Nettoyage préventif des tentatives antérieures pour assurer l'idempotence des tests répétés
    for old_att in db.query(StudentAttempt).filter(StudentAttempt.student_id == "ETU-2024-01").all():
        db.delete(old_att)
    db.commit()

    # Login Étudiant
    res_login = client.post("/api/auth/login", json={"username": "etu_promo_2024", "password": "etu123"})
    token = res_login.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {token}"}

    # Démarrage de l'épreuve
    res_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    attempt_id = res_start.json()["attempt_id"]

    # L'étudiant répond FAUX ('B') mais tente d'injecter "final_mark": 20.0 et "raw_score": 20.0
    payload_tampered = {
        "answers": {"Q-SEC-01": "B"},
        "final_mark": 20.0,
        "score": 20.0,
        "is_passed": True
    }
    res_submit = client.post(f"/api/student/attempts/{attempt_id}/submit", json=payload_tampered, headers=student_headers)
    assert res_submit.status_code == 200
    res_json = res_submit.json()

    # La note attribuée DOIT être 0.0 et NON 20.0 car le serveur a évalué la fausse réponse 'B'
    assert res_json["final_mark"] == 0.0
    
    # Vérification directe en base SQLite : la note est 0.0
    att = db.query(StudentAttempt).filter(StudentAttempt.id == attempt_id).first()
    assert att.final_mark == 0.0
