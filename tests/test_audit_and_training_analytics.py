import pytest
import json
from pathlib import Path
from backend.app.models import TrainingAttempt
from backend.app.services.training_service import build_progression_state

def test_curriculum_question_ids_uniqueness():
    """Vérifie que les 414 questions du curriculum ont des identifiants 100% uniques."""
    curr_file = Path("backend/app/data/python_training/curriculum.json")
    assert curr_file.exists(), "curriculum.json introuvable"
    with open(curr_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    seen = {}
    duplicates = []
    for topic in data.get("topics", []):
        t_id = topic.get("id")
        for diff_name, diff_data in topic.get("difficulties", {}).items():
            for mcq in diff_data.get("mcqs", []):
                qid = mcq.get("id")
                if qid in seen:
                    duplicates.append((qid, seen[qid], f"{t_id}:{diff_name}"))
                else:
                    seen[qid] = f"{t_id}:{diff_name}"
    
    assert len(duplicates) == 0, f"Doublons d'ID détectés dans curriculum.json : {duplicates}"

def test_guided_progression_unlock_rules(db_session):
    """
    Vérifie la règle pédagogique :
    - Facile + Intermédiaire validés (>= 14/20) suffisent pour valider le chapitre en guidé et débloquer Chapitre N+1 Facile.
    - Avancé et Expert sont des paliers de maîtrise optionnels (déblocables en mode personnalisé).
    """
    user_id = "ETU-001"
    
    # 1. Étudiant a validé facile (16) et moyen (15) sur ch1 (python_basics)
    att1 = TrainingAttempt(
        user_id=user_id,
        assessment_type="practical",
        target_topic="python_basics",
        target_difficulty="easy",
        final_mark=16.0,
        percentage=80.0,
        total_questions=5,
        correct_count=4,
        topic_marks_json=json.dumps({"python_basics": {"mark": 16.0, "total": 20.0}})
    )
    att2 = TrainingAttempt(
        user_id=user_id,
        assessment_type="practical",
        target_topic="python_basics",
        target_difficulty="medium",
        final_mark=15.0,
        percentage=75.0,
        total_questions=5,
        correct_count=4,
        topic_marks_json=json.dumps({"python_basics": {"mark": 15.0, "total": 20.0}})
    )
    db_session.add_all([att1, att2])
    db_session.commit()
    
    prog = build_progression_state(user_id, db_session)
    
    # Chapitre 1 doit avoir guided_completed = True
    ch1 = prog["topics"][0]
    assert ch1["id"] == "python_basics"
    assert ch1["guided_completed"] is True
    
    # Chapitre 2 (python_data_types) doit être débloqué
    ch2 = prog["topics"][1]
    assert ch2["id"] == "python_data_types"
    assert ch2["unlocked"] is True
    
    # Le palier facile de Ch2 doit être débloqué
    ch2_easy = next(d for d in ch2["difficulties"] if d["name"] == "easy")
    assert ch2_easy["unlocked"] is True
    
    # L'étape active guidée doit pointer sur le Chapitre 2 en Facile
    assert prog["active_step"]["chapter_id"] == "python_data_types"
    assert prog["active_step"]["difficulty"] == "easy"
    
    # Sur Chapitre 1, Avancé est débloqué en mode personnalisé (car medium validé)
    ch1_hard = next(d for d in ch1["difficulties"] if d["name"] == "hard")
    assert ch1_hard["unlocked"] is True
    
    # Mais Expert (very_hard) reste verrouillé tant qu'Avancé n'est pas validé
    ch1_expert = next(d for d in ch1["difficulties"] if d["name"] in ["expert", "very_hard"])
    assert ch1_expert["unlocked"] is False

def test_student_python_analytics_endpoint(client, student_headers, db_session):
    """Vérifie que l'endpoint de synthèse statistique renvoie la structure KPI + Faiblesses + Recommandations."""
    # Créer un entraînement pour l'étudiant
    att = TrainingAttempt(
        user_id="ETU-001",
        assessment_type="practical",
        target_topic="python_basics",
        target_difficulty="easy",
        final_mark=12.0, # Faiblesse (< 14)
        percentage=60.0,
        total_questions=5,
        correct_count=3,
        topic_marks_json=json.dumps({"python_basics": {"mark": 12.0, "total": 20.0}})
    )
    db_session.add(att)
    db_session.commit()
    
    res = client.get("/api/training/python/student-analytics", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    
    assert data["total_sessions"] >= 1
    assert data["average_mark"] == 12.0
    assert data["success_rate_percent"] == 0.0
    assert "badges_count" in data
    assert len(data["weaknesses"]) >= 1
    assert data["weaknesses"][0]["chapter_id"] == "python_basics"
    assert data["weaknesses"][0]["avg_score"] == 12.0
    assert len(data["recommendations"]) >= 1

def test_proctor_overview_404_handling(client, teacher_headers):
    """Vérifie que la requête d'une session introuvable retourne un statut HTTP 404 propre."""
    res = client.get("/api/proctor/sessions/SESS-NON-EXISTENT-9999/overview", headers=teacher_headers)
    assert res.status_code == 404
    assert "introuvable" in res.json().get("detail", "").lower()
