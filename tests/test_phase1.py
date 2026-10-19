import pytest
import io
from backend.app.security import hash_password, verify_password
from backend.app.models import User, Group, Module

# --- 1. Test Contrôle de Santé ---
def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "ExaminationQuiz" in data["app"]

# --- 2. Test Hachage Argon2id ---
def test_argon2_hashing():
    raw_pass = "Secret123!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

# --- 3. Tests Authentification & Cycle de Vie des Mots de Passe ---
def test_login_success_and_token(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"
    assert data["must_change_password"] is False

def test_login_failure_invalid_credentials(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "badpassword"})
    assert res.status_code == 401
    assert "incorrect" in res.json()["detail"].lower()

def test_student_first_login_flag_and_password_change(client):
    # L'étudiant se connecte pour la première fois avec son matricule
    res = client.post("/api/auth/login", json={"username": "etudiant1", "password": "ETU-001"})
    assert res.status_code == 200
    data = res.json()
    assert data["must_change_password"] is True
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Changement obligatoire du mot de passe
    res_change = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "ETU-001", "new_password": "MonNouveauMotDePasse2026!"}
    )
    assert res_change.status_code == 200
    assert res_change.json()["success"] is True
    
    # Nouvelle connexion avec le nouveau mot de passe
    res_relogin = client.post(
        "/api/auth/login",
        json={"username": "etudiant1", "password": "MonNouveauMotDePasse2026!"}
    )
    assert res_relogin.status_code == 200
    assert res_relogin.json()["must_change_password"] is False

def test_admin_resets_student_password(client, admin_headers, db_session):
    # L'administrateur réinitialise le mot de passe d'Alice
    res = client.post(
        "/api/auth/reset-password",
        headers=admin_headers,
        json={"user_id": "ETU-001"}
    )
    assert res.status_code == 200
    assert res.json()["must_change_password"] is True
    
    # L'étudiant peut se reconnecter avec son ID étudiant initial
    res_login = client.post("/api/auth/login", json={"username": "etudiant1", "password": "ETU-001"})
    assert res_login.status_code == 200
    assert res_login.json()["must_change_password"] is True

# --- 4. Tests Contrôle d'Accès par Rôles (RBAC) ---
def test_rbac_restrictions(client, student_headers, teacher_headers):
    # Un étudiant ne peut pas créer de groupe
    res_student = client.post(
        "/api/groups",
        headers=student_headers,
        json={"id": "GRP-HACK", "name": "Groupe Hack"}
    )
    assert res_student.status_code == 403
    
    # Un enseignant ne peut pas créer de module (réservé à l'administrateur)
    res_teacher = client.post(
        "/api/modules",
        headers=teacher_headers,
        json={"code": "MATH101", "title": "Mathématiques"}
    )
    assert res_teacher.status_code == 403

# --- 5. Tests Gestion des Groupes ---
def test_groups_crud(client, admin_headers):
    # 1. Création d'un groupe
    res_create = client.post(
        "/api/groups",
        headers=admin_headers,
        json={"id": "TD-C", "name": "Travaux Dirigés C", "description": "Promotion 2026"}
    )
    assert res_create.status_code == 201
    assert res_create.json()["id"] == "TD-C"
    
    # 2. Liste des groupes
    res_list = client.get("/api/groups", headers=admin_headers)
    assert res_list.status_code == 200
    group_ids = [g["id"] for g in res_list.json()]
    assert "TD-C" in group_ids
    
    # 3. Mise à jour du groupe
    res_update = client.put(
        "/api/groups/TD-C",
        headers=admin_headers,
        json={"name": "Travaux Dirigés C - Modifié"}
    )
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Travaux Dirigés C - Modifié"
    
    # 4. Suppression du groupe
    res_del = client.delete("/api/groups/TD-C", headers=admin_headers)
    assert res_del.status_code == 204

# --- 6. Tests Gestion des Modules & Affectation Enseignants ---
def test_modules_and_teacher_assignment(client, admin_headers, teacher_headers):
    # Création d'un module par l'admin
    res_mod = client.post(
        "/api/modules",
        headers=admin_headers,
        json={"code": "LINUX_ADMIN", "title": "Administration Linux", "description": "Bash et serveurs"}
    )
    assert res_mod.status_code == 201
    
    # Affectation du professeur Martin au module LINUX_ADMIN
    res_assign = client.post(
        "/api/modules/LINUX_ADMIN/teachers",
        headers=admin_headers,
        json={"teacher_id": "prof-01", "module_code": "LINUX_ADMIN"}
    )
    assert res_assign.status_code == 200
    
    # Vérification que le professeur est bien dans la liste des enseignants du module
    res_teachers = client.get("/api/modules/LINUX_ADMIN/teachers", headers=teacher_headers)
    assert res_teachers.status_code == 200
    teacher_ids = [t["id"] for t in res_teachers.json()]
    assert "prof-01" in teacher_ids

# --- 7. Tests Gestion des Utilisateurs ---
def test_users_crud_and_filters(client, admin_headers):
    # Création d'un étudiant avec mot de passe automatique = ID
    res_create = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "id": "ETU-002",
            "username": "bob_marley",
            "full_name": "Bob Marley",
            "email": "bob@test.com",
            "role": "student",
            "group_id": "GRP-1"
        }
    )
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["id"] == "ETU-002"
    assert data["must_change_password"] is True
    
    # Filtrer les utilisateurs par rôle 'student'
    res_filter = client.get("/api/users?role=student", headers=admin_headers)
    assert res_filter.status_code == 200
    usernames = [u["username"] for u in res_filter.json()]
    assert "bob_marley" in usernames
    assert "admin" not in usernames

# --- 8. Tests Imports & Exports CSV ---
def test_csv_import_and_export_students(client, admin_headers):
    csv_content = """student_id,username,full_name,email,group_id,group_name
ETU-100,jean_valjean,Jean Valjean,jean@test.com,GRP-99,Groupe Spécial
ETU-101,cosette,Cosette,cosette@test.com,GRP-99,Groupe Spécial
"""
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    res_import = client.post("/api/admin/csv/import/students", headers=admin_headers, files=files)
    assert res_import.status_code == 200
    result = res_import.json()
    assert result["success"] is True
    assert result["imported_count"] == 2
    
    # Vérifier que le groupe GRP-99 a été créé automatiquement
    res_group = client.get("/api/groups/GRP-99", headers=admin_headers)
    assert res_group.status_code == 200
    assert res_group.json()["student_count"] == 2
    
    # Vérifier que Jean Valjean peut se connecter avec son matricule 'ETU-100'
    res_login = client.post("/api/auth/login", json={"username": "jean_valjean", "password": "ETU-100"})
    assert res_login.status_code == 200
    assert res_login.json()["must_change_password"] is True
    
    # Test export CSV des étudiants
    res_export = client.get("/api/admin/csv/export/students", headers=admin_headers)
    assert res_export.status_code == 200
    assert "jean_valjean" in res_export.text
    assert "cosette" in res_export.text

def test_csv_import_teachers(client, admin_headers):
    csv_content = """teacher_id,username,full_name,email,assigned_modules
PROF-99,prof_durand,Professeur Durand,durand@test.com,PYTHON_INIT,CRYPTO
"""
    files = {"file": ("teachers.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    res_import = client.post("/api/admin/csv/import/teachers", headers=admin_headers, files=files)
    assert res_import.status_code == 200
    result = res_import.json()
    assert result["success"] is True
    assert result["imported_count"] == 1
    
    # Vérifier que Durand peut se connecter avec son matricule 'PROF-99'
    res_login = client.post("/api/auth/login", json={"username": "prof_durand", "password": "PROF-99"})
    assert res_login.status_code == 200


def test_specialties_and_students_seeding(client, admin_headers):
    """Vérifie l'amorçage des 3 spécialités et de leurs 4 étudiants respectifs (REV-14)."""
    # 1. Vérification des 3 spécialités
    res_groups = client.get("/api/groups", headers=admin_headers)
    assert res_groups.status_code == 200
    group_ids = [g["id"] for g in res_groups.json()]
    assert "DEV-IA" in group_ids
    assert "SYS-ADMIN" in group_ids
    assert "CYBER-SEC" in group_ids

    # 2. Vérification des 4 étudiants par groupe (12 étudiants)
    res_students = client.get("/api/users?role=student", headers=admin_headers)
    assert res_students.status_code == 200
    students_by_group = {}
    for s in res_students.json():
        gid = s.get("group_id")
        students_by_group.setdefault(gid, []).append(s["username"])

    assert len(students_by_group.get("DEV-IA", [])) == 4
    assert len(students_by_group.get("SYS-ADMIN", [])) == 4
    assert len(students_by_group.get("CYBER-SEC", [])) == 4

    # 3. Vérification de l'authentification d'un étudiant de chaque spécialité
    assert client.post("/api/auth/login", json={"username": "etu_dev1", "password": "StudentDev1!"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "etu_sys1", "password": "StudentSys1!"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "etu_sec1", "password": "StudentSec1!"}).status_code == 200

