import os
import pytest
from backend.app.services.training_service import (
    get_level,
    get_level_title,
    get_progression_stats,
    get_topic_historical_averages,
    load_curriculum
)

def test_evolution_level_ladder():
    """Vérifie l'échelle stricte des 6 niveaux officiels (REV-11)."""
    # 1. Insuffisant (0,00 à < 7,00)
    assert get_level(0.0) == 1
    assert get_level(6.99) == 1
    assert get_level_title(1) == "Insuffisant"
    assert get_level_title("insufficient") == "Insuffisant"

    # 2. Sous la moyenne (7,00 à < 10,00)
    assert get_level(7.0) == 2
    assert get_level(9.99) == 2
    assert get_level_title(2) == "Sous la moyenne"

    # 3. Limite (10,00 à < 12,00)
    assert get_level(10.0) == 3
    assert get_level(11.99) == 3
    assert get_level_title(3) == "Limite"

    # 4. Moyen (12,00 à < 14,00)
    assert get_level(12.0) == 4
    assert get_level(13.99) == 4
    assert get_level_title(4) == "Moyen"

    # 5. Bon (14,00 à < 16,00)
    assert get_level(14.0) == 5
    assert get_level(15.99) == 5
    assert get_level_title(5) == "Bon"

    # 6. Excellent (16,00 à 20,00)
    assert get_level(16.0) == 6
    assert get_level(20.0) == 6
    assert get_level_title(6) == "Excellent"

def test_curriculum_loaded_and_chapters_count():
    """Vérifie que les 10 chapitres pédagogiques complets sont bien chargés."""
    curriculum = load_curriculum()
    assert len(curriculum["chapters"]) == 10
    assert curriculum["total_mcqs"] >= 400
    assert curriculum["total_coding"] >= 150

    chapter_ids = [c["id"] for c in curriculum["chapters"]]
    assert "python_basics" in chapter_ids
    assert "control_flow" in chapter_ids
    assert "numpy" in chapter_ids
    assert "pandas" in chapter_ids
    assert "oop" in chapter_ids

def test_chapters_list_endpoint(client, student_headers):
    """Vérifie l'endpoint GET /api/training/python/chapters pour un étudiant."""
    res = client.get("/api/training/python/chapters", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 10
    
    first = data[0]
    assert first["id"] == "python_basics"
    assert first["status"] == "not_started"
    assert first["total_exercises"] > 0

def test_chapter_detail_student_secrecy(client, student_headers):
    """Vérifie que la consultation d'un chapitre ne divulgue pas la solution aux étudiants."""
    res = client.get("/api/training/python/chapters/python_basics", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "python_basics"
    assert len(data["coding_exercises"]) > 0

    for ex in data["coding_exercises"]:
        assert "solution" not in ex
        assert "hidden_tests" not in ex
        assert "starter_code" in ex

def test_generate_session_with_filters(client, student_headers):
    """Vérifie la génération d'une session d'entraînement mixte avec filtres de sujets."""
    payload = {
        "topics": ["python_basics", "control_flow"],
        "difficulties": ["easy", "medium"],
        "count": 6,
        "assessment_type": "training"
    }
    res = client.post("/api/training/python/generate-session", headers=student_headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["questions_count"] == 6
    assert len(data["items"]) == 6

    # Aucun flag de bonne réponse divulgué dans la session
    for item in data["items"]:
        assert "correct" not in item
        assert "solution" not in item

def test_submit_session_and_evolution_progression(client, student_headers):
    """Vérifie la soumission d'une session, le calcul de note et l'évolution de niveau."""
    # 1. Génération
    gen_res = client.post(
        "/api/training/python/generate-session",
        headers=student_headers,
        json={"topics": ["python_basics"], "count": 4}
    )
    items = gen_res.json()["items"]

    # 2. Soumission : simule 3 bonnes réponses sur 4
    answers = []
    for idx, item in enumerate(items):
        if item["type"] == "coding":
            answers.append({
                "id": item["id"],
                "type": "coding",
                "topic": item["topic"],
                "student_answer": "print('ok')",
                "is_correct": idx < 3  # Validé par Pyodide
            })
        else:
            answers.append({
                "id": item["id"],
                "type": "mcq",
                "topic": item["topic"],
                "student_answer": 0,
                "is_correct": idx < 3
            })

    submit_payload = {
        "assessment_type": "evolution",
        "selected_topics": ["python_basics"],
        "selected_difficulties": ["easy", "medium"],
        "answers": answers
    }

    sub_res = client.post("/api/training/python/submit-session", headers=student_headers, json=submit_payload)
    assert sub_res.status_code == 200
    res_data = sub_res.json()

    assert "final_mark" in res_data
    assert "progression" in res_data
    prog = res_data["progression"]
    assert "curr_level" in prog
    assert "level_title" in prog

    # 3. Vérification de l'historique de l'étudiant
    hist_res = client.get("/api/training/python/history", headers=student_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data["attempts"]) >= 1
    assert len(hist_data["marks_history"]) >= 1

def test_pyodide_offline_assets_served():
    """Vérifie que les fichiers WebAssembly et Workers Pyodide sont présents et servis en local hors-ligne."""
    pyodide_dir = os.path.join("frontend", "vendor", "pyodide")
    assert os.path.exists(os.path.join(pyodide_dir, "pyodide.js"))
    assert os.path.exists(os.path.join(pyodide_dir, "pyodide.asm.wasm"))
    assert os.path.exists(os.path.join(pyodide_dir, "pyodide.asm.mjs"))
    assert os.path.exists(os.path.join(pyodide_dir, "python_stdlib.zip"))

    assert os.path.exists(os.path.join("frontend", "js", "pyodide-worker.js"))
    assert os.path.exists(os.path.join("frontend", "js", "pyodide-runner.js"))

def test_practice_history_and_last_4_attempts_and_warnings(client, student_headers):
    """Vérifie la persistance de l'historique des tests de niveau, la moyenne des 4 dernières tentatives et les avertissements."""
    # 1. Récupérer les 30 questions de ALGO
    q_res = client.get("/api/practice/exams/ALGO/questions", headers=student_headers)
    assert q_res.status_code == 200
    questions = q_res.json()["questions"]
    assert len(questions) == 30

    # 2. Soumettre 5 tentatives consécutives sur ALGO avec différentes réponses et avertissements
    for i in range(1, 6):
        # Répondre à quelques questions avec true/false ou options
        ans = {}
        for q in questions:
            if q["type"] == "boolean":
                ans[q["id"]] = True
            elif q["type"] == "single_choice" and q["options"]:
                ans[q["id"]] = q["options"][0]["id"]
            else:
                ans[q["id"]] = "test"
                
        submit_res = client.post(
            "/api/practice/exams/ALGO/submit",
            headers=student_headers,
            json={"answers": ans, "warnings_count": (i % 4)}
        )
        assert submit_res.status_code == 200

    # 3. Vérifier l'historique complet
    hist_res = client.get("/api/practice/history", headers=student_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()

    assert "attempts" in hist_data
    assert len(hist_data["attempts"]) >= 5
    assert "pillars" in hist_data
    algo_stat = hist_data["pillars"]["ALGO"]
    assert algo_stat["attempts_count"] >= 5
    # Les 4 dernières tentatives sont conservées
    assert len(algo_stat["last_4_scores"]) == 4
    # La moyenne des 4 dernières tentatives détermine le niveau
    assert algo_stat["last_4_average"] > 0
    assert algo_stat["level"] >= 1
    assert "level_title" in algo_stat

def test_python_progression_gamification_and_badges(client, student_headers):
    """Vérifie l'endpoint GET /api/training/python/progression (10 chapitres, active step, 68 badges)."""
    res = client.get("/api/training/python/progression", headers=student_headers)
    assert res.status_code == 200
    data = res.json()

    assert "progression" in data
    assert "gamification" in data

    prog = data["progression"]
    assert len(prog["topics"]) == 10
    assert "active_step" in prog
    assert prog["active_step"]["chapter_id"] == "python_basics"
    assert prog["active_step"]["difficulty"] == "easy"

    gamif = data["gamification"]
    assert gamif["level"] >= 1
    assert gamif["total_badges"] == 68
    assert len(gamif["all_milestones"]) == 68
    assert "progress_percent" in gamif

