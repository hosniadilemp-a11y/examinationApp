import os
import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models import TrainingAttempt, ChapterProgress, User

CURRICULUM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "python_training", "curriculum.json")

def load_curriculum() -> Dict[str, Any]:
    if not os.path.exists(CURRICULUM_PATH):
        return {"chapters": [], "total_mcqs": 0, "total_coding": 0}
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

OFFICIAL_LEVELS = [
    {
        "rank": 1,
        "code": "insufficient",
        "title": "Insuffisant",
        "min_score": 0.0,
        "max_score": 7.0,
        "meaning": "Très loin du niveau requis"
    },
    {
        "rank": 2,
        "code": "below_average",
        "title": "Sous la moyenne",
        "min_score": 7.0,
        "max_score": 10.0,
        "meaning": "En dessous de la moyenne"
    },
    {
        "rank": 3,
        "code": "borderline",
        "title": "Limite",
        "min_score": 10.0,
        "max_score": 12.0,
        "meaning": "Moyenne atteinte de justesse"
    },
    {
        "rank": 4,
        "code": "average",
        "title": "Moyen",
        "min_score": 12.0,
        "max_score": 14.0,
        "meaning": "Acquis acceptables, des lacunes subsistent"
    },
    {
        "rank": 5,
        "code": "good",
        "title": "Bon",
        "min_score": 14.0,
        "max_score": 16.0,
        "meaning": "Acquis solides, lacunes mineures"
    },
    {
        "rank": 6,
        "code": "excellent",
        "title": "Excellent",
        "min_score": 16.0,
        "max_score": 20.0,
        "meaning": "Maîtrise complète du contenu"
    }
]

def get_level(average_score: float) -> int:
    """Détermine le niveau (1 à 6) basé sur la moyenne sur 20 selon la grille officielle (REV-11)."""
    if average_score < 7.0: return 1
    if average_score < 10.0: return 2
    if average_score < 12.0: return 3
    if average_score < 14.0: return 4
    if average_score < 16.0: return 5
    return 6

def get_level_code(average_or_level: Any) -> str:
    """Retourne le code interne du niveau ('insufficient', 'good', etc.)."""
    if isinstance(average_or_level, float):
        lvl = get_level(average_or_level)
    else:
        lvl = int(average_or_level)
    codes = {
        1: "insufficient",
        2: "below_average",
        3: "borderline",
        4: "average",
        5: "good",
        6: "excellent"
    }
    return codes.get(lvl, "insufficient")

def get_level_title(level: Any) -> str:
    """Retourne le libellé officiel affiché pour un niveau."""
    if isinstance(level, float):
        level = get_level(level)
    titles = {
        1: "Insuffisant",
        2: "Sous la moyenne",
        3: "Limite",
        4: "Moyen",
        5: "Bon",
        6: "Excellent",
        "insufficient": "Insuffisant",
        "below_average": "Sous la moyenne",
        "borderline": "Limite",
        "average": "Moyen",
        "good": "Bon",
        "excellent": "Excellent"
    }
    return titles.get(level, str(level))

def get_level_meaning(level: Any) -> str:
    """Retourne la signification pédagogique officielle."""
    if isinstance(level, float):
        level = get_level(level)
    meanings = {
        1: "Très loin du niveau requis",
        2: "En dessous de la moyenne",
        3: "Moyenne atteinte de justesse",
        4: "Acquis acceptables, des lacunes subsistent",
        5: "Acquis solides, lacunes mineures",
        6: "Maîtrise complète du contenu",
        "insufficient": "Très loin du niveau requis",
        "below_average": "En dessous de la moyenne",
        "borderline": "Moyenne atteinte de justesse",
        "average": "Acquis acceptables, des lacunes subsistent",
        "good": "Acquis solides, lacunes mineures",
        "excellent": "Maîtrise complète du contenu"
    }
    return meanings.get(level, "")

def get_progression_stats(history: List[Dict[str, Any]], latest_attempt: Dict[str, Any]) -> Dict[str, Any]:
    """Calcule l'évolution du score, du niveau et les métriques de progression."""
    if not history:
        mark = latest_attempt.get("final_mark", 0.0)
        curr_lvl = get_level(mark)
        return {
            "prev_avg": 0.0,
            "new_avg": round(mark, 2),
            "delta": round(mark, 2),
            "prev_level": 1,
            "curr_level": curr_lvl,
            "initial_level": curr_lvl,
            "level_up": False,
            "level_title": get_level_title(curr_lvl)
        }

    previous_attempts = history[:-1] if len(history) > 1 else []
    
    if not previous_attempts:
        prev_avg = 0.0
        new_avg = latest_attempt.get("final_mark", 0.0)
    else:
        prev_marks = [a.get("final_mark", 0.0) for a in previous_attempts]
        prev_avg = sum(prev_marks) / len(prev_marks)
        all_marks = [a.get("final_mark", 0.0) for a in history]
        new_avg = sum(all_marks) / len(all_marks)

    delta = new_avg - prev_avg if previous_attempts else new_avg
    prev_level = get_level(prev_avg) if previous_attempts else 1
    curr_level = get_level(new_avg)
    initial_level = get_level(history[0].get("final_mark", 0.0))

    return {
        "prev_avg": round(prev_avg, 2),
        "new_avg": round(new_avg, 2),
        "delta": round(delta, 2),
        "prev_level": prev_level,
        "curr_level": curr_level,
        "initial_level": initial_level,
        "level_up": curr_level > prev_level,
        "level_title": get_level_title(curr_level)
    }

def get_topic_historical_averages(history: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calcule la moyenne historique par sujet pour établir le classement des points forts/faibles."""
    topic_totals: Dict[str, float] = {}
    topic_counts: Dict[str, int] = {}
    
    for attempt in history:
        raw_marks = attempt.get("topic_marks", {})
        if isinstance(raw_marks, str):
            try:
                raw_marks = json.loads(raw_marks)
            except Exception:
                raw_marks = {}
        for topic, mark in raw_marks.items():
            topic_totals[topic] = topic_totals.get(topic, 0.0) + float(mark)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
    averages = {}
    for topic, total in topic_totals.items():
        averages[topic] = round(total / topic_counts[topic], 2)
    return averages

def list_chapters_with_progress(user_id: str, db: Session) -> List[Dict[str, Any]]:
    curriculum = load_curriculum()
    progress_rows = db.query(ChapterProgress).filter(ChapterProgress.user_id == user_id).all()
    progress_map = {p.chapter_id: p for p in progress_rows}
    
    result = []
    for ch in curriculum.get("chapters", []):
        ch_id = ch["id"]
        prog = progress_map.get(ch_id)
        result.append({
            "id": ch_id,
            "title": ch["title"],
            "order": ch["order"],
            "description": ch["description"],
            "mcq_count": ch["mcq_questions_count"],
            "coding_count": ch["coding_exercises_count"],
            "status": prog.status if prog else "not_started",
            "best_mark": prog.best_mark if prog else 0.0,
            "completed_exercises": prog.completed_exercises if prog else 0,
            "total_exercises": ch["coding_exercises_count"] + ch["mcq_questions_count"]
        })
    return result

def get_chapter_exercises(chapter_id: str) -> Optional[Dict[str, Any]]:
    curriculum = load_curriculum()
    chapter = next((c for c in curriculum.get("chapters", []) if c["id"] == chapter_id), None)
    if not chapter:
        return None
    
    # Masquer les solutions et les tests cachés dans la vue de travail de l'étudiant
    safe_coding = []
    for item in chapter.get("coding_exercises", []):
        safe_coding.append({
            "id": item["id"],
            "type": "coding",
            "topic": item.get("topic", chapter["title"]),
            "difficulty": item.get("difficulty", "medium"),
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "starter_code": item.get("starter_code", ""),
            "public_tests": item.get("public_tests", []),
            "points": item.get("points", 1),
            "hint1": item.get("hint1", ""),
            "hint2": item.get("hint2", "")
            # solution et hidden_tests exclus
        })
        
    return {
        "id": chapter["id"],
        "title": chapter["title"],
        "description": chapter["description"],
        "coding_exercises": safe_coding,
        "mcq_questions": chapter.get("mcq_questions", [])
    }

# ==============================================================================
# PROGRESSION & UNLOCK ENGINE (selon training_logic.txt)
# ==============================================================================

PASSING_MARK = 14.0
DIFFICULTY_ORDER = ["easy", "medium", "hard", "very_hard"]
DIFFICULTY_LABELS = {
    "easy": "Facile",
    "medium": "Intermédiaire",
    "hard": "Avancé",
    "very_hard": "Expert"
}

# 10 Niveaux XP
LEVEL_XP_THRESHOLDS = [0, 100, 200, 400, 700, 1000, 1400, 1800, 2300, 2760]
LEVEL_NAMES = [
    "Débutant",       # 1
    "Apprenti",       # 2
    "Initié",         # 3
    "Intermédiaire",  # 4
    "Avancé",         # 5
    "Expert",         # 6
    "Maître",         # 7
    "Grand Maître",   # 8
    "Champion",       # 9
    "Légendaire",     # 10
]

def _compute_xp_level(total_xp: int) -> int:
    lvl = 1
    for i, thresh in enumerate(LEVEL_XP_THRESHOLDS):
        if total_xp >= thresh:
            lvl = i + 1
    return min(lvl, 10)

def build_progression_state(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Calcule l'état de déblocage pédagogique des 10 chapitres et 4 difficultés.
    Règles (training_logic.txt) :
    - Note de validation : >= 14.0/20
    - Chapitre 1 (Bases de Python) toujours débloqué
    - Chapitre N débloqué si Chapitre N-1 a validé Easy ET Medium (>= 14/20)
    - Dans un chapitre débloqué : Easy toujours débloqué, Medium requiert Easy validé, etc.
    """
    curriculum = load_curriculum()
    chapters = curriculum.get("chapters", [])
    
    # Récupération de tous les succès de l'étudiant
    attempts = db.query(TrainingAttempt).filter(TrainingAttempt.user_id == user_id).all()
    
    # Set of (chapter_id, difficulty) completed with mark >= 14
    completed_pairs = set()
    best_marks: Dict[str, float] = {}
    
    for a in attempts:
        mark = float(a.final_mark or 0)
        topic = a.target_topic
        diff = a.target_difficulty
        
        if not topic or not diff:
            try:
                top_list = json.loads(a.selected_topics_json or "[]")
                diff_list = json.loads(a.selected_difficulties_json or "[]")
                if len(top_list) == 1 and len(diff_list) == 1:
                    topic = top_list[0]
                    diff = diff_list[0]
            except Exception:
                pass
                
        if topic and diff:
            key = f"{topic}_{diff}"
            best_marks[key] = max(best_marks.get(key, 0.0), mark)
            if mark >= PASSING_MARK:
                completed_pairs.add((topic, diff))

    topic_states = []
    active_step = None  # Le prochain pas dans le parcours guidé
    
    for i, ch in enumerate(chapters):
        ch_id = ch["id"]
        
        # Règle de déblocage du sujet :
        if i == 0:
            topic_unlocked = True
        else:
            prev_ch = chapters[i - 1]["id"]
            # Exige easy ET medium validés sur le chapitre précédent
            topic_unlocked = (prev_ch, "easy") in completed_pairs and (prev_ch, "medium") in completed_pairs
            
        difficulties_state = []
        for diff_idx, diff_name in enumerate(DIFFICULTY_ORDER):
            completed = (ch_id, diff_name) in completed_pairs
            best_score = best_marks.get(f"{ch_id}_{diff_name}", 0.0)
            
            if not topic_unlocked:
                unlocked = False
            elif diff_idx == 0:
                unlocked = True
            else:
                prev_diff = DIFFICULTY_ORDER[diff_idx - 1]
                unlocked = (ch_id, prev_diff) in completed_pairs
                
            is_current = False
            if unlocked and not completed and active_step is None:
                is_current = True
                active_step = {
                    "chapter_id": ch_id,
                    "chapter_title": ch["title"],
                    "difficulty": diff_name,
                    "difficulty_label": DIFFICULTY_LABELS.get(diff_name, diff_name)
                }
                
            difficulties_state.append({
                "name": diff_name,
                "label": DIFFICULTY_LABELS.get(diff_name, diff_name),
                "unlocked": unlocked,
                "completed": completed,
                "current": is_current,
                "best_mark": round(best_score, 2)
            })
            
        completed_count = sum(1 for d in difficulties_state if d["completed"])
        topic_states.append({
            "id": ch_id,
            "title": ch["title"],
            "order": ch["order"],
            "description": ch["description"],
            "unlocked": topic_unlocked,
            "completed": completed_count == len(DIFFICULTY_ORDER),
            "completed_count": completed_count,
            "total_count": len(DIFFICULTY_ORDER),
            "difficulties": difficulties_state
        })
        
    return {
        "topics": topic_states,
        "active_step": active_step or {
            "chapter_id": chapters[0]["id"] if chapters else "python_basics",
            "chapter_title": chapters[0]["title"] if chapters else "Bases de Python & Syntaxe",
            "difficulty": "easy",
            "difficulty_label": "Facile"
        },
        "passing_mark": PASSING_MARK
    }

def calculate_gamification(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Calcule les 68 badges (Milestones), les points d'XP et le rang du joueur (Niveau 1 à 10).
    """
    curriculum = load_curriculum()
    chapters = curriculum.get("chapters", [])
    
    attempts = db.query(TrainingAttempt).filter(TrainingAttempt.user_id == user_id).all()
    
    theo_attempts = [a for a in attempts if a.assessment_type == "theoretical"]
    prac_attempts = [a for a in attempts if a.assessment_type in ("practical", "coding")]
    
    passed_theo = sum(1 for a in theo_attempts if (a.final_mark or 0) >= PASSING_MARK)
    passed_prac = sum(1 for a in prac_attempts if (a.final_mark or 0) >= PASSING_MARK)
    
    # Meilleure note par chapitre pour MCQ et pour Pratique
    best_theo = {ch["id"]: 0.0 for ch in chapters}
    best_prac = {ch["id"]: 0.0 for ch in chapters}
    
    for a in attempts:
        atype = a.assessment_type
        mark = float(a.final_mark or 0)
        ch_id = a.target_topic
        if not ch_id:
            try:
                top_list = json.loads(a.selected_topics_json or "[]")
                if top_list: ch_id = top_list[0]
            except Exception:
                pass
                
        if ch_id in best_theo and atype == "theoretical":
            best_theo[ch_id] = max(best_theo[ch_id], mark)
        elif ch_id in best_prac and atype in ("practical", "coding"):
            best_prac[ch_id] = max(best_prac[ch_id], mark)
            
    # 1. Milestones volume théorique (4)
    theo_milestones = [
        {"id": "theo_1", "emoji": "📖", "name": "Théoricien Apprenti", "desc": "Réussir 1 quiz théorique (≥ 14/20)", "target": 1, "actual": passed_theo, "points": 10, "unlocked": passed_theo >= 1},
        {"id": "theo_5", "emoji": "📚", "name": "Théoricien Confirmé", "desc": "Réussir 5 quiz théoriques (≥ 14/20)", "target": 5, "actual": passed_theo, "points": 20, "unlocked": passed_theo >= 5},
        {"id": "theo_20", "emoji": "🧠", "name": "Théoricien Expert", "desc": "Réussir 20 quiz théoriques (≥ 14/20)", "target": 20, "actual": passed_theo, "points": 50, "unlocked": passed_theo >= 20},
        {"id": "theo_40", "emoji": "🎓", "name": "Théoricien Légendaire", "desc": "Réussir 40 quiz théoriques (≥ 14/20)", "target": 40, "actual": passed_theo, "points": 100, "unlocked": passed_theo >= 40},
    ]

    # 2. Milestones volume pratique (4)
    prac_milestones = [
        {"id": "prac_1", "emoji": "💻", "name": "Codeur Novice", "desc": "Réussir 1 laboratoire pratique (≥ 14/20)", "target": 1, "actual": passed_prac, "points": 10, "unlocked": passed_prac >= 1},
        {"id": "prac_5", "emoji": "🛠️", "name": "Codeur Agile", "desc": "Réussir 5 laboratoires pratiques (≥ 14/20)", "target": 5, "actual": passed_prac, "points": 20, "unlocked": passed_prac >= 5},
        {"id": "prac_20", "emoji": "⚡", "name": "Codeur Élite", "desc": "Réussir 20 laboratoires pratiques (≥ 14/20)", "target": 20, "actual": passed_prac, "points": 50, "unlocked": passed_prac >= 20},
        {"id": "prac_40", "emoji": "🛡️", "name": "Codeur Suprême", "desc": "Réussir 40 laboratoires pratiques (≥ 14/20)", "target": 40, "actual": passed_prac, "points": 100, "unlocked": passed_prac >= 40},
    ]

    # 3. Maîtrise Théorique (30 : 10 chapitres x Bronze >=16, Silver >=18, Gold 20/20)
    theo_topic_milestones = []
    for ch in chapters:
        c_id = ch["id"]
        c_title = ch["title"]
        score = best_theo.get(c_id, 0.0)
        theo_topic_milestones.append({
            "id": f"{c_id}_theo_bronze", "emoji": "🥉", "name": f"{c_title} (Bronze QCM)", "desc": f"Score ≥ 16/20 en QCM sur {c_title}", "target": 16.0, "actual": score, "points": 10, "unlocked": score >= 16.0
        })
        theo_topic_milestones.append({
            "id": f"{c_id}_theo_silver", "emoji": "🥈", "name": f"{c_title} (Argent QCM)", "desc": f"Score ≥ 18/20 en QCM sur {c_title}", "target": 18.0, "actual": score, "points": 20, "unlocked": score >= 18.0
        })
        theo_topic_milestones.append({
            "id": f"{c_id}_theo_gold", "emoji": "🥇", "name": f"{c_title} (Or QCM)", "desc": f"Score parfait 20/20 en QCM sur {c_title}", "target": 20.0, "actual": score, "points": 50, "unlocked": score >= 20.0
        })

    # 4. Maîtrise Pratique (30 : 10 chapitres x Bronze >=16, Silver >=18, Gold 20/20)
    prac_topic_milestones = []
    for ch in chapters:
        c_id = ch["id"]
        c_title = ch["title"]
        score = best_prac.get(c_id, 0.0)
        prac_topic_milestones.append({
            "id": f"{c_id}_prac_bronze", "emoji": "🥉", "name": f"{c_title} (Bronze Code)", "desc": f"Score ≥ 16/20 en code sur {c_title}", "target": 16.0, "actual": score, "points": 10, "unlocked": score >= 16.0
        })
        prac_topic_milestones.append({
            "id": f"{c_id}_prac_silver", "emoji": "🥈", "name": f"{c_title} (Argent Code)", "desc": f"Score ≥ 18/20 en code sur {c_title}", "target": 18.0, "actual": score, "points": 20, "unlocked": score >= 18.0
        })
        prac_topic_milestones.append({
            "id": f"{c_id}_prac_gold", "emoji": "🥇", "name": f"{c_title} (Or Code)", "desc": f"Score parfait 20/20 en code sur {c_title}", "target": 20.0, "actual": score, "points": 50, "unlocked": score >= 20.0
        })

    all_milestones = theo_milestones + prac_milestones + theo_topic_milestones + prac_topic_milestones
    total_xp = sum(m["points"] for m in all_milestones if m["unlocked"])
    unlocked_badges_count = sum(1 for m in all_milestones if m["unlocked"])
    total_badges = len(all_milestones)  # 68
    
    level = _compute_xp_level(total_xp)
    level_name = LEVEL_NAMES[level - 1]
    xp_current_threshold = LEVEL_XP_THRESHOLDS[level - 1]
    xp_next_threshold = LEVEL_XP_THRESHOLDS[level] if level < 10 else LEVEL_XP_THRESHOLDS[-1]
    xp_in_level = total_xp - xp_current_threshold
    level_range = max(1, xp_next_threshold - xp_current_threshold)
    progress_percent = min(100.0, round((xp_in_level / level_range) * 100.0, 1)) if level < 10 else 100.0

    return {
        "level": level,
        "level_name": level_name,
        "total_xp": total_xp,
        "xp_current_threshold": xp_current_threshold,
        "xp_next_threshold": xp_next_threshold,
        "xp_in_level": xp_in_level,
        "progress_percent": progress_percent,
        "unlocked_badges_count": unlocked_badges_count,
        "total_badges": total_badges,
        "theo_milestones": theo_milestones,
        "prac_milestones": prac_milestones,
        "theo_topic_milestones": theo_topic_milestones,
        "prac_topic_milestones": prac_topic_milestones,
        "all_milestones": all_milestones
    }
