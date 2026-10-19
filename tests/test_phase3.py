import pytest
import json
from backend.app.models import Exam, Question, Group, User, ExamSession, StudentAttempt

# ==============================================================================
# TESTS PHASE 3 : INTERFACE ÉTUDIANT & ANTI-TRICHE
# ==============================================================================

def test_frontend_static_serving(client):
    """Vérifie que les fichiers de l'interface frontend sont correctement distribués."""
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "<!DOCTYPE html>" in res_index.text
    assert "Platform" in res_index.text
    assert "overlay-suspension" in res_index.text

    res_css = client.get("/css/style.css")
    assert res_css.status_code == 200
    assert "--bg-primary" in res_css.text

    res_js = client.get("/js/anticheat.js")
    assert res_js.status_code == 200
    assert "AntiCheatManager" in res_js.text

def test_student_available_exams_by_group(client, admin_headers, student_headers, db_session):
    """Vérifie que les étudiants ne voient que les examens affectés à leur propre groupe."""
    # Création d'un examen pour le groupe GRP-1 (auquel appartient l'étudiant de test)
    res_exam1 = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Python Groupe 1",
            "duration_minutes": 60,
            "group_ids": ["GRP-1"]
        }
    )
    assert res_exam1.status_code == 201

    # Création d'un examen pour le groupe GRP-2 (auquel l'étudiant n'appartient pas)
    res_exam2 = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "CRYPTO",
            "title": "Examen Crypto Groupe 2",
            "duration_minutes": 60,
            "group_ids": ["GRP-2"]
        }
    )
    assert res_exam2.status_code == 201

    # L'étudiant consulte ses examens
    res_avail = client.get("/api/student/exams/available", headers=student_headers)
    assert res_avail.status_code == 200
    available_titles = [e["title"] for e in res_avail.json()]
    assert "Examen Python Groupe 1" in available_titles
    assert "Examen Crypto Groupe 2" not in available_titles

def test_exam_start_dual_shuffling_and_answer_secrecy(client, admin_headers, student_headers):
    """Vérifie le démarrage de l'épreuve, le secret absolu des corrigés et le double brassage."""
    # 1. Création de l'examen et de 3 questions avec corrigés secrets
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Secret & Shuffling",
            "duration_minutes": 45,
            "group_ids": ["GRP-1"],
            "shuffle_questions": True,
            "shuffle_options": True
        }
    )
    exam_id = res_exam.json()["id"]

    for i in range(1, 4):
        client.post(
            f"/api/exams/{exam_id}/questions",
            headers=admin_headers,
            json={
                "ordering": i,
                "type": "single_choice",
                "prompt_markdown": f"Question secrète numéro {i}",
                "points": 2.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "Option A"},
                    {"id": "b", "text": "Option B"},
                    {"id": "c", "text": "Option C"}
                ]),
                "correct_answers_json": json.dumps("b")  # Corrigé confidentiel !
            }
        )

    # 2. L'étudiant démarre l'épreuve
    res_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert res_start.status_code == 200
    data = res_start.json()

    assert "attempt_id" in data
    assert data["attempt_status"] == "in_progress"
    assert data["remaining_seconds"] > 0
    assert len(data["questions"]) == 3

    # VÉRIFICATION DU SECRET ABSOLU DES CORRIGÉS
    for q in data["questions"]:
        assert "correct_answers_json" not in q
        assert "correct_answer" not in q
        assert "correct" not in q

    # 3. Test de reprise après rafraîchissement (Stabilité du brassage déterministe)
    res_resume = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert res_resume.status_code == 200
    data_resume = res_resume.json()
    assert data_resume["attempt_id"] == data["attempt_id"]

    # L'ordre des questions doit être strictement identique lors de la reprise
    resume_q_ids = [q["id"] for q in data_resume["questions"]]
    original_q_ids = [q["id"] for q in data["questions"]]
    assert resume_q_ids == original_q_ids

def test_autosave_and_attempt_recovery(client, admin_headers, student_headers):
    """Vérifie l'auto-sauvegarde en temps réel et la persistance lors de la reprise de session."""
    # Création d'un examen avec 1 question
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Test Autosave", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    res_q = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1,
            "type": "fill_blank",
            "prompt_markdown": "Quel est le mot-clé pour définir une fonction ?",
            "points": 2.0,
            "options_json": "[]",
            "correct_answers_json": json.dumps(["def"])
        }
    )
    q_id = res_q.json()["id"]

    # Démarrage
    res_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    attempt_id = res_start.json()["attempt_id"]

    # L'étudiant tape une réponse -> déclenchement de l'auto-sauvegarde
    res_save = client.post(
        f"/api/student/attempts/{attempt_id}/save-answer",
        headers=student_headers,
        json={"question_id": q_id, "answer": "def"}
    )
    assert res_save.status_code == 200
    assert res_save.json()["success"] is True

    # Simulation d'un crash de navigateur / rafraîchissement : Reconnexion
    res_reconnect = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert res_reconnect.status_code == 200
    saved = res_reconnect.json()["saved_answers"]
    assert q_id in saved
    assert saved[q_id] == "def"

def test_anticheat_10_seconds_away_suspension_and_remote_unlock(client, admin_headers, teacher_headers, student_headers):
    """Vérifie la règle des 10 secondes d'absence : suspension automatique et déblocage à distance."""
    # Création d'un examen
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Test Anti-Triche 10s", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    res_q = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1, "type": "boolean", "prompt_markdown": "Q1 ?",
            "points": 1.0, "options_json": "[]", "correct_answers_json": json.dumps(True)
        }
    )
    q_id = res_q.json()["id"]

    res_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    attempt_id = res_start.json()["attempt_id"]

    # 1. Alerte simple de moins de 10 secondes (ne suspend pas encore)
    res_alert = client.post(
        f"/api/student/attempts/{attempt_id}/security-event",
        headers=student_headers,
        json={"event_type": "FOCUS_LOST", "details": {"duration_seconds": 3}}
    )
    assert res_alert.status_code == 200
    assert res_alert.json()["is_suspended"] is False

    # 2. Dépassement de la règle des 10 secondes d'absence -> SUSPENSION IMMÉDIATE
    res_suspend = client.post(
        f"/api/student/attempts/{attempt_id}/security-event",
        headers=student_headers,
        json={"event_type": "AWAY_10S", "details": {"duration_seconds": 11}}
    )
    assert res_suspend.status_code == 200
    assert res_suspend.json()["is_suspended"] is True
    assert res_suspend.json()["status"] == "suspended"

    # Vérification que la tentative est bloquée en base
    res_check = client.get(f"/api/student/attempts/{attempt_id}/status", headers=student_headers)
    assert res_check.status_code == 200
    assert res_check.json()["status"] == "suspended"

    # Tentative d'auto-sauvegarde pendant la suspension -> REJETÉE (403 Forbidden)
    res_blocked = client.post(
        f"/api/student/attempts/{attempt_id}/save-answer",
        headers=student_headers,
        json={"question_id": q_id, "answer": True}
    )
    assert res_blocked.status_code == 403
    assert "suspendue" in res_blocked.json()["detail"].lower()

    # 3. DÉBLOCAGE À DISTANCE (1-Clic par le surveillant / enseignant)
    res_unlock = client.post(
        f"/api/student/attempts/{attempt_id}/unlock",
        headers=teacher_headers
    )
    assert res_unlock.status_code == 200
    assert res_unlock.json()["success"] is True
    assert res_unlock.json()["status"] == "in_progress"

    # Vérification que l'étudiant peut à nouveau répondre
    res_save_again = client.post(
        f"/api/student/attempts/{attempt_id}/save-answer",
        headers=student_headers,
        json={"question_id": q_id, "answer": True}
    )
    assert res_save_again.status_code == 200
    assert res_save_again.json()["success"] is True

def test_official_exam_submission_and_immediate_score(client, admin_headers, student_headers):
    """Vérifie la soumission définitive, le calcul de la note officielle et l'impossibilité de resoumettre."""
    # Création d'un examen avec 2 questions de 10 points chacune (total 20 points)
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Notation Immédiate",
            "duration_minutes": 60,
            "global_points": 20.0,
            "group_ids": ["GRP-1"]
        }
    )
    exam_id = res_exam.json()["id"]

    # Q1 : Bonne réponse "a" (10 pts)
    res_q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 1, "type": "single_choice", "prompt_markdown": "Q1 ?",
            "points": 10.0, "negative_penalty": 0.0,
            "options_json": json.dumps([{"id": "a", "text": "A"}, {"id": "b", "text": "B"}]),
            "correct_answers_json": json.dumps("a")
        }
    )
    q1_id = res_q1.json()["id"]

    # Q2 : Bonne réponse True (10 pts)
    res_q2 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={
            "ordering": 2, "type": "boolean", "prompt_markdown": "Q2 ?",
            "points": 10.0, "negative_penalty": 0.0,
            "options_json": "[]", "correct_answers_json": json.dumps(True)
        }
    )
    q2_id = res_q2.json()["id"]

    # L'étudiant commence
    res_start = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    attempt_id = res_start.json()["attempt_id"]

    # L'étudiant répond correctement à Q1 et fait une faute à Q2 (répond False)
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q1_id, "answer": "a"})
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q2_id, "answer": False})

    # Soumission finale de l'épreuve
    res_submit = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
    assert res_submit.status_code == 200
    data = res_submit.json()

    assert data["status"] == "submitted"
    assert data["raw_score"] == 10.0
    assert data["max_score"] == 20.0
    assert data["final_mark"] == 10.0
    assert data["global_points"] == 20.0
    assert "10.0 / 20.0" in data["message"]

    # Tentative de resoumission ultérieure
    res_resubmit = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
    assert res_resubmit.status_code == 200
    assert "déjà été soumis" in res_resubmit.json()["message"]


def test_student_statistics_and_fundamental_level(client, student_headers):
    """Vérifie le calcul des statistiques de l'étudiant et de son niveau sur les 4 modules fondamentaux."""
    res_stats = client.get("/api/student/statistics", headers=student_headers)
    assert res_stats.status_code == 200
    data = res_stats.json()

    assert "student_name" in data
    assert "global_level" in data
    assert 1 <= data["global_level"] <= 8
    assert "global_level_title" in data
    assert "fundamental_average" in data
    assert "overall_average" in data
    assert "modules_breakdown" in data
    assert len(data["modules_breakdown"]) >= 4

    # Vérification de la présence des 4 modules fondamentaux
    codes = [m["code"] for m in data["modules_breakdown"]]
    assert "ALGO" in codes
    assert "PYTHON_INIT" in codes
    assert "CRYPTO" in codes
    assert "LINUX_ADMIN" in codes

    fund_modules = [m for m in data["modules_breakdown"] if m["is_fundamental"]]
    assert len(fund_modules) == 4
    for fm in fund_modules:
        assert "best_mark" in fm
        assert "average_mark" in fm
        assert "mastery_level" in fm
        assert "passed" in fm

