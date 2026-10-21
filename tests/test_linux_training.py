import pytest
from backend.app.models import PracticeAttempt, StudentAttempt
from backend.app.services.linux_training_service import (
    load_linux_curriculum,
    load_linux_challenges,
    get_levels_summary
)

# ==============================================================================
# 1. Curriculum & Challenges Structure and Mandatory Test Case Counts
# ==============================================================================

def test_linux_curriculum_structure_and_levels():
    """Vérifie la présence des 4 niveaux de formation et la validité du schéma curriculum.json."""
    curriculum = load_linux_curriculum()
    levels = curriculum.get("levels", [])
    assert len(levels) == 4, "Le cursus Linux doit comporter exactement 4 niveaux."

    level_ids = [lvl["level"] for lvl in levels]
    assert level_ids == [1, 2, 3, 4]

    expected_titles = [
        "Navigation",
        "Permissions",
        "Scripts",
        "Sysadmin"
    ]
    for lvl in levels:
        assert "title" in lvl
        assert "description" in lvl
        assert lvl.get("challenges_count", 0) > 0
        assert lvl.get("quizzes_count", 0) > 0

def test_linux_challenges_public_and_hidden_tests_counts():
    """
    Règle obligatoire R3 / DISPATCH :
    Chaque défi pratique Linux DOIT comporter AU MOINS 2 tests publics et AU MOINS 5 tests cachés !
    """
    challenges = load_linux_challenges()
    assert len(challenges) >= 8, "Le dataset doit comporter au moins 8 défis pratiques progressifs."

    for ch in challenges:
        c_id = ch.get("id")
        pub_tests = ch.get("public_tests", [])
        hid_tests = ch.get("hidden_tests", [])

        assert len(pub_tests) >= 2, f"Défi {c_id} : requiert >= 2 tests publics, trouvé {len(pub_tests)}"
        assert len(hid_tests) >= 5, f"Défi {c_id} : requiert >= 5 tests cachés, trouvé {len(hid_tests)}"
        assert ch.get("points", 0) > 0, f"Défi {c_id} doit avoir des points strictement positifs."
        assert ch.get("level") in (1, 2, 3, 4), f"Défi {c_id} doit appartenir à l'un des niveaux 1-4."
        assert "initial_fs" in ch, f"Défi {c_id} doit définir un initial_fs."

# ==============================================================================
# 2. Endpoints Sécurisés & Masquage Absolu des Réponses (Student View)
# ==============================================================================

def test_linux_curriculum_endpoint_student_view_secrecy(client, student_headers):
    """Vérifie que GET /api/training/linux/curriculum et /challenges masquent tout secret."""
    # 1. Endpoint Cursus
    res_curr = client.get("/api/training/linux/curriculum", headers=student_headers)
    assert res_curr.status_code == 200
    data_curr = res_curr.json()
    assert "levels" in data_curr
    assert len(data_curr["levels"]) == 4

    # 2. Endpoint Liste des Défis
    res_ch = client.get("/api/training/linux/challenges", headers=student_headers)
    assert res_ch.status_code == 200
    challenges = res_ch.json()
    assert len(challenges) >= 8

    for c in challenges:
        # Confidentialité absolue : aucun test caché ni solution dans la liste
        assert "hidden_tests" not in c
        assert "solution" not in c
        assert "status" in c
        assert c["status"] in ("unsolved", "in_progress", "solved")

def test_linux_challenge_detail_endpoint(client, student_headers):
    """Vérifie la consultation d'un défi individuel avec initial_fs et tests publics uniquement."""
    res = client.get("/api/training/linux/challenges/LINUX-101", headers=student_headers)
    assert res.status_code == 200
    detail = res.json()

    assert detail["id"] == "LINUX-101"
    assert detail["level"] == 1
    assert "initial_fs" in detail
    assert "public_tests" in detail
    assert len(detail["public_tests"]) >= 2

    # Secret absolu
    assert "hidden_tests" not in detail
    assert "solution" not in detail

    # Test 404 pour ID inexistant
    res_404 = client.get("/api/training/linux/challenges/LINUX-UNKNOWN-999", headers=student_headers)
    assert res_404.status_code == 404

def test_linux_theory_quizzes_endpoint(client, student_headers):
    """Vérifie la consultation des QCM théoriques avec réponses masquées."""
    res = client.get("/api/training/linux/theory/quizzes", headers=student_headers)
    assert res.status_code == 200
    quizzes = res.json()
    assert len(quizzes) > 0

    for q in quizzes:
        assert "correct" not in q
        assert "explanation" not in q

# ==============================================================================
# 3. Génération Dynamique & Évaluation de Session
# ==============================================================================

def test_linux_generate_session_with_level_filters(client, student_headers):
    """Vérifie la génération dynamique de sessions théoriques ou pratiques filtrées."""
    # Session filtrée par niveau 1
    res = client.post(
        "/api/training/linux/generate-session",
        json={"chapter_id": "fhs_navigation", "assessment_type": "all", "count": 5},
        headers=student_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert len(data["items"]) <= 5
    for item in data["items"]:
        assert "hidden_tests" not in item
        assert "correct" not in item

def test_linux_submit_challenge_success_evaluation(client, student_headers):
    """Vérifie la soumission et l'évaluation d'un défi pratique réussi."""
    payload = {
        "challenge_id": "LINUX-101",
        "command": "pwd && ls -la",
        "execution_output": {
            "stdout": "/home/student\n.bashrc\n.profile\ndocuments\nnotes.txt",
            "exit_code": 0
        },
        "vfs_state": {
            "/home/student": {
                "type": "dir",
                "files": {
                    ".bashrc": {"type": "file", "content": "# ok"},
                    "notes.txt": {"type": "file", "content": "Bienvenue sur Linux"}
                }
            }
        }
    }

    res = client.post("/api/training/linux/submit-challenge", json=payload, headers=student_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["challenge_id"] == "LINUX-101"
    assert data["success"] is True
    assert data["all_passed"] is True
    assert data["awarded_points"] == 2.0
    assert len(data["public_results"]) >= 2
    assert len(data["hidden_results"]) >= 5

def test_linux_submit_challenge_hidden_tests_masking(client, student_headers):
    """Vérifie que le rapport de soumission masque strictement le contenu secret des tests cachés."""
    payload = {
        "challenge_id": "LINUX-101",
        "command": "pwd",
        "execution_output": {"stdout": "/home/student", "exit_code": 0}
    }
    res = client.post("/api/training/linux/submit-challenge", json=payload, headers=student_headers)
    assert res.status_code == 200
    data = res.json()

    # Vérification du masquage des tests cachés
    for ht in data["hidden_results"]:
        assert ht["expected"] == "[Protégé]"
        assert ht["cmd"] == "[Protégé]"
        assert "expected_stdout" not in ht

def test_linux_progress_and_history_persistence(client, student_headers):
    """Vérifie la persistance de la progression et de l'historique de l'étudiant."""
    # Soumission préalable
    client.post("/api/training/linux/submit-challenge", json={
        "challenge_id": "LINUX-101",
        "command": "pwd && ls -la",
        "client_tests_passed": True
    }, headers=student_headers)

    # Consultation de la progression
    res_prog = client.get("/api/training/linux/progress", headers=student_headers)
    assert res_prog.status_code == 200
    prog = res_prog.json()
    assert "LINUX-101" in prog["solved_challenges"]
    assert prog["total_points"] >= 2.0
    assert prog["pillar"] == "LINUX_ADMIN"

    # Consultation de l'historique
    res_hist = client.get("/api/training/linux/history", headers=student_headers)
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert len(hist) >= 1
    assert "grade_20" in hist[0]
    assert "submitted_at" in hist[0]

# ==============================================================================
# 4. Intégration Pilier Diagnostique & Découplage Strict des Examens Officiels
# ==============================================================================

def test_linux_training_links_to_diagnostic_placement_pillar(client, student_headers, db_session):
    """Vérifie la synchronisation automatique avec le pilier LINUX_ADMIN dans practice_attempts."""
    res_submit = client.post("/api/training/linux/submit-challenge", json={
        "challenge_id": "LINUX-101",
        "command": "pwd && ls -la",
        "client_tests_passed": True
    }, headers=student_headers)
    assert res_submit.status_code == 200

    # Vérification en base de données
    attempt = db_session.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == "ETU-001",
        PracticeAttempt.module_code == "LINUX_ADMIN"
    ).order_by(PracticeAttempt.created_at.desc()).first()

    assert attempt is not None
    assert attempt.module_code == "LINUX_ADMIN"
    assert attempt.grade_20 == 20.0

    # Vérification via l'API de diagnostic existante
    res_pillar = client.get("/api/practice/history?module_code=LINUX_ADMIN", headers=student_headers)
    assert res_pillar.status_code == 200
    p_data = res_pillar.json()
    assert len(p_data["attempts"]) >= 1
    assert p_data["pillars"]["LINUX_ADMIN"]["attempts_count"] >= 1

def test_linux_training_strict_decoupling_from_semester_gpa(client, student_headers, db_session):
    """
    Règle fondamentale de découplage (R2 / R4 / survey report § 2.3) :
    Les tentatives et défis du Centre d'Entraînement Linux ne doivent JAMAIS modifier
    la moyenne générale officielle (general_average), la moyenne d'examens ni le verdict (ADMIS/AJOURNÉ).
    """
    # 1. Bulletin initial avant entraînement Linux
    res_before = client.get("/api/student/bulletin", headers=student_headers)
    assert res_before.status_code == 200
    b_before = res_before.json()

    avg_before = b_before.get("general_average")
    verdict_before = b_before.get("verdict")
    exam_avg_before = b_before.get("exams_average")

    # 2. L'étudiant effectue plusieurs soumissions avec des scores variés dans le Centre Linux
    client.post("/api/training/linux/submit-challenge", json={
        "challenge_id": "LINUX-101",
        "command": "pwd",
        "client_tests_passed": False  # Échec partiel
    }, headers=student_headers)

    client.post("/api/training/linux/submit-challenge", json={
        "challenge_id": "LINUX-102",
        "command": "mkdir -p project/src",
        "client_tests_passed": True   # Réussite
    }, headers=student_headers)

    # 3. Bulletin après entraînement Linux
    res_after = client.get("/api/student/bulletin", headers=student_headers)
    assert res_after.status_code == 200
    b_after = res_after.json()

    avg_after = b_after.get("general_average")
    verdict_after = b_after.get("verdict")
    exam_avg_after = b_after.get("exams_average")

    # 4. Vérification mathématique du découplage strict
    assert avg_after == avg_before, "La moyenne générale officielle a été modifiée par l'entraînement Linux !"
    assert verdict_after == verdict_before, "Le verdict du jury a été modifié par l'entraînement Linux !"
    assert exam_avg_after == exam_avg_before, "La moyenne des épreuves officielles a été altérée !"

    # Seul le pilier diagnostique LINUX_ADMIN est actualisé
    fund = b_after.get("fundamentals", {})
    assert "LINUX_ADMIN" in fund
    assert fund["LINUX_ADMIN"]["score"] is not None

def test_linux_training_rbac_unauthenticated_forbidden(client):
    """Vérifie que les endpoints protégés du Centre Linux rejettent les accès anonymes avec un code 401."""
    endpoints = [
        ("GET", "/api/training/linux/curriculum"),
        ("GET", "/api/training/linux/challenges"),
        ("GET", "/api/training/linux/challenges/LINUX-101"),
        ("GET", "/api/training/linux/progress"),
        ("GET", "/api/training/linux/history"),
        ("POST", "/api/training/linux/submit-challenge")
    ]
    for method, url in endpoints:
        if method == "GET":
            res = client.get(url)
        else:
            res = client.post(url, json={"challenge_id": "LINUX-101", "command": "pwd"})
        assert res.status_code == 401, f"{method} {url} devrait renvoyer 401 Unauthorized"

# ==============================================================================
# 5. Tests de Rétrocompatibilité (Chapitres & Sessions Mixtes)
# ==============================================================================

def test_linux_chapters_listing(client, student_headers):
    """Vérifie la disponibilité des 6 chapitres Linux avec métadonnées."""
    res = client.get("/api/training/linux/chapters", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6
    assert data[0]["id"] == "fhs_navigation"
    assert data[0]["mcq_count"] >= 5
    assert data[0]["coding_count"] >= 1
    assert "status" in data[0]

def test_linux_chapter_detail_secrecy(client, student_headers):
    """Vérifie que les corrigés et tests cachés ne sont jamais transmis au client."""
    res = client.get("/api/training/linux/chapters/fhs_navigation?assessment_type=all", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["chapter_id"] == "fhs_navigation"
    assert len(data["items"]) > 0

    for item in data["items"]:
        assert "correct" not in item
        assert "explanation" not in item
        assert "hidden_tests" not in item
        if item.get("type") in ("linux_cmd", "coding"):
            assert "public_tests" in item

def test_linux_session_generation(client, student_headers):
    """Vérifie la génération dynamique de sessions théoriques ou pratiques."""
    # Session théorique
    res_theo = client.post(
        "/api/training/linux/generate-session",
        json={"chapter_id": "fhs_navigation", "assessment_type": "theoretical", "count": 4},
        headers=student_headers
    )
    assert res_theo.status_code == 200
    d_theo = res_theo.json()
    assert len(d_theo["items"]) <= 4
    for q in d_theo["items"]:
        assert q["type"] not in ("linux_cmd", "coding")

    # Session pratique
    res_prac = client.post(
        "/api/training/linux/generate-session",
        json={"chapter_id": "fhs_navigation", "assessment_type": "practical", "count": 2},
        headers=student_headers
    )
    assert res_prac.status_code == 200
    d_prac = res_prac.json()
    assert len(d_prac["items"]) >= 1
    for ce in d_prac["items"]:
        assert ce["type"] in ("linux_cmd", "coding")

def test_linux_session_evaluation_and_progression(client, student_headers):
    """Vérifie l'évaluation des réponses et la persistance dans le pilier LINUX_ADMIN."""
    payload = {
        "answers": [
            {
                "id": "LIN-THEO-101",
                "type": "single_choice",
                "topic": "FHS Navigation",
                "student_answer": 0  # /etc (correct)
            },
            {
                "id": "LIN-THEO-104",
                "type": "boolean",
                "topic": "FHS Navigation",
                "student_answer": 0  # Vrai (correct)
            },
            {
                "id": "LIN-PRAC-101",
                "type": "linux_cmd",
                "topic": "FHS Navigation",
                "student_answer": "pwd && ls -la",
                "is_correct": True
            }
        ]
    }

    res = client.post("/api/training/linux/submit-session", json=payload, headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["grade_20"] == 20.0
    assert data["percentage"] == 100.0
    assert data["pillar"] == "LINUX_ADMIN"
    assert len(data["item_results"]) == 3
    assert all(r["is_correct"] is True for r in data["item_results"])

    # Vérification de la progression mise à jour
    prog_res = client.get("/api/training/linux/progression", headers=student_headers)
    assert prog_res.status_code == 200
    prog = prog_res.json()
    assert prog["total_attempts"] >= 1
    assert prog["best_score"] >= 15.0
    assert prog["pillar"] == "LINUX_ADMIN"
