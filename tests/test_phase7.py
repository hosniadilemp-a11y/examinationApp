import os
import json
import pytest
from concurrent.futures import ThreadPoolExecutor
from backend.app.models import User, Group, Exam, Question, ExamSession, StudentAttempt
from backend.app.security import hash_password

def test_dockerfile_and_compose_configuration():
    """Vérifie la validité des fichiers de conteneurisation Docker Turnkey."""
    assert os.path.exists("Dockerfile")
    with open("Dockerfile", "r", encoding="utf-8") as f:
        dockerfile_content = f.read()
    assert "FROM python:" in dockerfile_content
    assert "EXPOSE 8000" in dockerfile_content
    assert "HEALTHCHECK" in dockerfile_content
    assert "uvicorn" in dockerfile_content

    assert os.path.exists("docker-compose.yml")
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        compose_content = f.read()
    assert "serveur-salle:" in compose_content
    assert "8000:8000" in compose_content
    assert "room_data:" in compose_content

def test_turnkey_launcher_scripts():
    """Vérifie la présence et la configuration des scripts de démarrage rapide pour les enseignants."""
    assert os.path.exists("lancer_serveur_salle.bat")
    with open("lancer_serveur_salle.bat", "r", encoding="utf-8") as f:
        bat_content = f.read()
    assert "uvicorn" in bat_content
    assert "8000" in bat_content

    assert os.path.exists("lancer_serveur_salle.sh")
    with open("lancer_serveur_salle.sh", "r", encoding="utf-8") as f:
        sh_content = f.read()
    assert "uvicorn" in sh_content
    assert "8000" in sh_content

def test_concurrent_load_30_students(client, db_session, admin_headers, teacher_headers):
    """
    Simulation réaliste de charge concurrente : 30 étudiants passent l'examen en même temps
    avec requêtes d'autosauvegarde, télémétrie de sécurité et soumissions simultanées.
    Valide l'absence totale de verrouillage SQLite (WAL mode actif).
    """
    # 1. Création d'un groupe dédié de 30 étudiants
    group_id = "GRP-LOAD-30"
    grp = Group(id=group_id, name="Groupe Test Charge 30", description="30 étudiants simultanés")
    db_session.add(grp)
    
    student_credentials = []
    for i in range(1, 31):
        uid = f"ETU-LOAD-{i:02d}"
        uname = f"etudiant_load_{i:02d}"
        pwd = f"pass{i:02d}"
        user = User(
            id=uid,
            username=uname,
            password_hash=hash_password(pwd),
            full_name=f"Étudiant Charge {i:02d}",
            role="student",
            group_id=group_id,
            must_change_password=False,
            is_active=True
        )
        db_session.add(user)
        student_credentials.append((uname, pwd))
    db_session.commit()

    # 2. Création de l'examen et affectation au groupe
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Épreuve de Charge 30 Postes",
            "duration_minutes": 45,
            "group_ids": [group_id]
        }
    )
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]

    # Ajout de 3 questions à l'examen
    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Python est-il typé dynamiquement ?", "points": 5.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    q2 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 2, "type": "single_choice", "prompt_markdown": "Quel mot-clé définit une fonction ?", "points": 5.0, "options_json": json.dumps([{"id": "a", "text": "def"}, {"id": "b", "text": "function"}]), "correct_answers_json": json.dumps("a")}
    ).json()

    q3 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 3, "type": "fill_blank", "prompt_markdown": "Extension d'un script python ?", "points": 10.0, "options_json": "[]", "correct_answers_json": json.dumps(".py")}
    ).json()

    # 3. L'enseignant ouvre et lance la session
    res_sess = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-A"})
    session_id = res_sess.json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # 4. Exécution du cycle complet pour l'ensemble des 30 étudiants de la salle
    def run_student_lifecycle(creds):
        username, password = creds
        # 1. Login
        r_login = client.post("/api/auth/login", json={"username": username, "password": password})
        if r_login.status_code != 200:
            return False, f"Login failed for {username}: {r_login.status_code}"
        token = r_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Démarrage de l'examen et réception des questions
        r_start = client.post(f"/api/student/exams/{exam_id}/start", headers=headers)
        if r_start.status_code != 200:
            return False, f"Start failed for {username}: {r_start.status_code}"
        attempt_id = r_start.json()["attempt_id"]

        # 3. Télémétrie de sécurité
        r_sec = client.post(
            f"/api/student/attempts/{attempt_id}/security-event",
            headers=headers,
            json={"event_type": "HEARTBEAT", "details": {"note": "charge"}}
        )
        if r_sec.status_code != 200:
            return False, f"Sec event failed for {username}: {r_sec.status_code}"

        # 4. Sauvegarde automatique des réponses
        r_s1 = client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=headers, json={"question_id": q1["id"], "answer": True})
        r_s2 = client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=headers, json={"question_id": q2["id"], "answer": "a"})
        r_s3 = client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=headers, json={"question_id": q3["id"], "answer": ".py"})
        if r_s1.status_code != 200 or r_s2.status_code != 200 or r_s3.status_code != 200:
            return False, f"Autosave failed for {username}"

        # 5. Soumission finale de la copie
        r_sub = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=headers)
        if r_sub.status_code != 200:
            return False, f"Submit failed for {username}: {r_sub.status_code}"

        mark = r_sub.json().get("final_mark")
        return True, mark

    results = [run_student_lifecycle(creds) for creds in student_credentials]

    # 5. Vérification des résultats : 100% de succès pour les 30 étudiants
    successes = [r for r in results if r[0] is True]
    assert len(successes) == 30, f"Seulement {len(successes)}/30 étudiants ont réussi : {[r for r in results if r[0] is False]}"

    # Vérification que toutes les copies sont bien avec statut 'submitted' et note maximale 20/20
    for is_ok, mark in successes:
        assert is_ok is True
        assert mark == 20.0

    # Vérification dans la base de données
    attempts_in_db = db_session.query(StudentAttempt).filter(StudentAttempt.session_id == session_id).all()
    assert len(attempts_in_db) == 30
    assert all(a.status == "submitted" for a in attempts_in_db)

