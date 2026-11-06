import json
import random
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User, TrainingAttempt, ChapterProgress
from backend.app.dependencies import get_current_user
from backend.app.services.grading import evaluate_answer
from backend.app.services.training_service import (
    load_curriculum,
    list_chapters_with_progress,
    get_chapter_exercises,
    get_progression_stats,
    get_topic_historical_averages,
    get_level,
    build_progression_state,
    calculate_gamification,
    PASSING_MARK
)
from backend.app.services.sandbox_runner import (
    execute_user_code_with_input,
    execute_user_code_against_tests
)

router = APIRouter(prefix="/api/training/python", tags=["Entraînement Évolutif Python"])

# Schémas Pydantic
class ChapterSummary(BaseModel):
    id: str
    title: str
    order: int
    description: str
    mcq_count: int
    coding_count: int
    status: str
    best_mark: float
    completed_exercises: int
    total_exercises: int

class SessionGenerationRequest(BaseModel):
    topics: Optional[List[str]] = None
    difficulties: Optional[List[str]] = None
    target_topic: Optional[str] = None
    target_difficulty: Optional[str] = None
    count: int = 10
    assessment_type: str = "training"  # 'theoretical' | 'practical' | 'training' | 'evolution'

class SubmitAnswerItem(BaseModel):
    id: Any
    type: str  # 'mcq' | 'coding' | 'boolean' | 'single_choice' | 'multi_choice' | 'fill_blank' | 'matching'
    topic: str
    difficulty: Optional[str] = "medium"
    student_answer: Any  # option ID, boolean, text, dict, or code string
    hints_used: Optional[int] = 0
    is_correct: Optional[bool] = None  # evaluated by client (Pyodide) for coding, or server for MCQ

class SessionSubmitRequest(BaseModel):
    assessment_type: str = "training"
    selected_topics: List[str]
    selected_difficulties: List[str]
    target_topic: Optional[str] = None
    target_difficulty: Optional[str] = None
    answers: List[SubmitAnswerItem]

class RunCodeRequest(BaseModel):
    code: str
    stdin: Optional[str] = ""
    timeout: Optional[float] = 3.0

class RunTestsRequest(BaseModel):
    exercise_id: Optional[Any] = None
    code: str
    tests: Optional[List[Dict[str, Any]]] = None
    run_all: Optional[bool] = False
    timeout: Optional[float] = 3.0

@router.get("/progression")
def get_progression(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne l'état de déblocage pédagogique complet et les 68 badges de gamification (XP)."""
    prog = build_progression_state(current_user.id, db)
    gamif = calculate_gamification(current_user.id, db)
    return {
        "progression": prog,
        "gamification": gamif
    }

@router.get("/student-analytics")
def get_student_training_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne l'analyse statistique complète des entraînements de l'étudiant, ses points faibles et les tests à repasser."""
    curriculum = load_curriculum()
    chapters = curriculum.get("chapters", [])
    ch_dict = {c["id"]: c["title"] for c in chapters}
    
    attempts = db.query(TrainingAttempt).filter(
        TrainingAttempt.user_id == current_user.id
    ).order_by(TrainingAttempt.created_at.desc()).all()
    
    total_sessions = len(attempts)
    gamif = calculate_gamification(current_user.id, db)
    if total_sessions == 0:
        return {
            "has_data": False,
            "total_sessions": 0,
            "average_mark": 0.0,
            "success_rate_percent": 0.0,
            "badges_count": 0,
            "gamification": {
                "level": gamif.get("level", 1),
                "level_name": gamif.get("level_name", "Niveau 1 : Débutant"),
                "total_xp": gamif.get("total_xp", 0),
                "xp_next_threshold": gamif.get("xp_next_threshold", 100),
                "progress_percent": gamif.get("progress_percent", 0.0)
            },
            "summary": {
                "total_sessions": 0,
                "average_mark": 0.0,
                "success_rate": 0.0,
                "best_mark": 0.0,
                "xp_badges_count": 0,
                "current_level_title": gamif.get("level_name", "Niveau 1 : Débutant")
            },
            "weaknesses": [],
            "recommendations": [
                {
                    "chapter_id": chapters[0]["id"] if chapters else "python_basics",
                    "chapter_title": chapters[0]["title"] if chapters else "Bases de Python & Syntaxe",
                    "difficulty": "easy",
                    "difficulty_label": "Facile",
                    "reason": "Test de positionnement initial recommandé"
                }
            ]
        }
        
    marks = [float(a.final_mark or 0.0) for a in attempts]
    avg_mark = round(sum(marks) / len(marks), 2)
    passed_count = sum(1 for a in attempts if float(a.final_mark or 0.0) >= PASSING_MARK)
    success_rate = round((passed_count / total_sessions) * 100.0, 1)
    best_mark = round(max(marks), 2) if marks else 0.0
    
    gamif = calculate_gamification(current_user.id, db)
    xp_count = sum(1 for m in gamif.get("all_milestones", []) if m.get("unlocked"))
    
    # Agrégation par chapitre
    chapter_stats = {}
    for a in attempts:
        topic = a.target_topic
        if not topic:
            try:
                top_list = json.loads(a.selected_topics_json or "[]")
                if top_list:
                    topic = top_list[0]
            except Exception:
                pass
        if not topic:
            continue
            
        if topic not in chapter_stats:
            chapter_stats[topic] = {
                "attempts": [],
                "latest_mark": float(a.final_mark or 0.0),
                "latest_diff": a.target_difficulty or "easy",
                "latest_date": a.created_at.isoformat() if a.created_at else ""
            }
        chapter_stats[topic]["attempts"].append(float(a.final_mark or 0.0))
        
    weaknesses = []
    recommendations = []
    diff_labels = {"easy": "Facile", "medium": "Intermédiaire", "hard": "Avancé", "expert": "Expert"}
    
    for ch_id, stats in chapter_stats.items():
        ch_title = ch_dict.get(ch_id, ch_id)
        att_marks = stats["attempts"]
        ch_avg = round(sum(att_marks) / len(att_marks), 2)
        latest_mark = stats["latest_mark"]
        latest_diff = stats["latest_diff"]
        
        if latest_mark < PASSING_MARK or ch_avg < PASSING_MARK:
            weaknesses.append({
                "chapter_id": ch_id,
                "chapter_title": ch_title,
                "difficulty": latest_diff,
                "difficulty_label": diff_labels.get(latest_diff, latest_diff),
                "average_mark": ch_avg,
                "avg_score": ch_avg,
                "latest_mark": latest_mark,
                "status": "À renforcer" if latest_mark < 10.0 else "Moyen (lacunes)",
                "attempts_count": len(att_marks)
            })
            recommendations.append({
                "chapter_id": ch_id,
                "chapter_title": ch_title,
                "difficulty": latest_diff,
                "difficulty_label": diff_labels.get(latest_diff, latest_diff),
                "latest_mark": latest_mark,
                "reason": f"Dernier score : {latest_mark}/20 (Seuil requis : {PASSING_MARK}/20)"
            })
            
    weaknesses.sort(key=lambda w: w["latest_mark"])
    recommendations.sort(key=lambda r: r.get("latest_mark", 20))
    
    if not recommendations:
        prog = build_progression_state(current_user.id, db)
        act = prog.get("active_step")
        if act:
            recommendations.append({
                "chapter_id": act.get("chapter_id"),
                "chapter_title": act.get("chapter_title"),
                "difficulty": act.get("difficulty"),
                "difficulty_label": act.get("difficulty_label"),
                "reason": "Prochain palier officiel à conquérir dans votre cursus"
            })
            
    return {
        "has_data": True,
        "total_sessions": total_sessions,
        "average_mark": avg_mark,
        "success_rate_percent": success_rate,
        "badges_count": xp_count,
        "gamification": {
            "level": gamif.get("level", 1),
            "level_name": gamif.get("level_name", "Niveau 1 : Débutant"),
            "total_xp": gamif.get("total_xp", 0),
            "xp_next_threshold": gamif.get("xp_next_threshold", 100),
            "progress_percent": gamif.get("progress_percent", 0.0)
        },
        "summary": {
            "total_sessions": total_sessions,
            "average_mark": avg_mark,
            "success_rate": success_rate,
            "best_mark": best_mark,
            "xp_badges_count": xp_count,
            "current_level_title": gamif.get("level_name", "Niveau 1 : Débutant")
        },
        "weaknesses": weaknesses[:4],
        "recommendations": recommendations[:3]
    }

@router.get("/chapters", response_model=List[ChapterSummary])
def get_chapters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste tous les chapitres Python avec les métriques de progression de l'étudiant."""
    return list_chapters_with_progress(current_user.id, db)

@router.get("/chapters/{chapter_id}")
def get_chapter(
    chapter_id: str,
    current_user: User = Depends(get_current_user)
):
    """Détails et exercices d'un chapitre spécifique."""
    details = get_chapter_exercises(chapter_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Chapitre '{chapter_id}' introuvable.")
    return details

@router.post("/generate-session")
def generate_training_session(
    payload: SessionGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Génère une série d'entraînement adaptée au niveau et aux filtres choisis."""
    curriculum = load_curriculum()
    all_chapters = curriculum.get("chapters", [])
    
    selected_topics = payload.topics or ([payload.target_topic] if payload.target_topic else [c["id"] for c in all_chapters])
    selected_difficulties = payload.difficulties or ([payload.target_difficulty] if payload.target_difficulty else ["easy", "medium", "hard", "very_hard"])
    
    # Collecte des items éligibles avec typage précis
    pool_mcq = []
    pool_coding = []
    
    for ch in all_chapters:
        if ch["id"] in selected_topics or ch["title"] in selected_topics:
            for m in ch.get("mcq_questions", []):
                diff = m.get("difficulty", "medium").lower()
                if diff in selected_difficulties:
                    raw_type = m.get("type", "mcq")
                    pts = float(m.get("points", 1.0))
                    
                    if raw_type == "yesno":
                        pool_mcq.append({
                            "id": m["id"],
                            "raw_type": "yesno",
                            "type": "boolean",
                            "topic": ch["title"],
                            "topic_id": ch["id"],
                            "difficulty": diff,
                            "prompt_markdown": m.get('text', ''),
                            "options": [
                                {"id": "true", "text": "Vrai"},
                                {"id": "false", "text": "Faux"}
                            ],
                            "points": pts
                        })
                    elif raw_type == "intruder":
                        raw_opts = m.get("options", [])
                        opts_list = [{"id": str(idx), "text": str(opt)} for idx, opt in enumerate(raw_opts)]
                        shuffled_opts = list(opts_list)
                        random.shuffle(shuffled_opts)
                        pool_mcq.append({
                            "id": m["id"],
                            "raw_type": "intruder",
                            "type": "single_choice",
                            "topic": ch["title"],
                            "topic_id": ch["id"],
                            "difficulty": diff,
                            "prompt_markdown": m.get('text', ''),
                            "options": shuffled_opts,
                            "points": pts
                        })
                    elif raw_type == "simple_blank":
                        code_snippet = m.get("code", "")
                        prompt_md = m.get('text', '')
                        if code_snippet:
                            prompt_md += f"\n\n```python\n{code_snippet}\n```"
                        pool_mcq.append({
                            "id": m["id"],
                            "raw_type": "simple_blank",
                            "type": "fill_blank",
                            "topic": ch["title"],
                            "topic_id": ch["id"],
                            "difficulty": diff,
                            "prompt_markdown": prompt_md,
                            "options": [],
                            "points": pts
                        })
                    elif raw_type == "matching":
                        pairs = m.get("pairs", {})
                        left_items = list(pairs.keys())
                        right_items = list(pairs.values())
                        random.shuffle(right_items)
                        pool_mcq.append({
                            "id": m["id"],
                            "raw_type": "matching",
                            "type": "matching",
                            "topic": ch["title"],
                            "topic_id": ch["id"],
                            "difficulty": diff,
                            "prompt_markdown": m.get('text', ''),
                            "options": {"left": left_items, "right": right_items},
                            "points": pts
                        })
                    else:  # mcq
                        raw_opts = m.get("options", [])
                        opts_list = [{"id": str(idx), "text": str(opt)} for idx, opt in enumerate(raw_opts)]
                        shuffled_opts = list(opts_list)
                        random.shuffle(shuffled_opts)
                        is_multi = len(m.get("correct", [])) > 1
                        pool_mcq.append({
                            "id": m["id"],
                            "raw_type": "mcq",
                            "type": "multi_choice" if is_multi else "single_choice",
                            "topic": ch["title"],
                            "topic_id": ch["id"],
                            "difficulty": diff,
                            "prompt_markdown": m.get('text', ''),
                            "options": shuffled_opts,
                            "points": pts
                        })

            for c in ch.get("coding_exercises", []):
                diff = c.get("difficulty", "medium").lower()
                if diff in selected_difficulties:
                    pts = 2.0 if diff == "easy" else (3.0 if diff == "medium" else (4.0 if diff == "hard" else 5.0))
                    pool_coding.append({
                        "id": c["id"],
                        "raw_type": "coding",
                        "type": "coding",
                        "topic": ch["title"],
                        "topic_id": ch["id"],
                        "difficulty": diff,
                        "title": c.get("title", ""),
                        "prompt_markdown": c.get("description", ""),
                        "description": c.get("description", ""),
                        "starter_code": c.get("starter_code", ""),
                        "public_tests": c.get("public_tests", []),
                        "hint1": c.get("hint1", ""),
                        "hint2": c.get("hint2", ""),
                        "points": pts
                    })
                    
    random.shuffle(pool_mcq)
    random.shuffle(pool_coding)
    
    chosen = []
    time_limit_seconds = 900  # Default 15 min
    
    primary_diff = selected_difficulties[0] if len(selected_difficulties) == 1 else "medium"
    
    if payload.assessment_type == "theoretical":
        # Mode théorique : QCM uniquement (10 à 20 questions, 15 min)
        target_count = min(max(payload.count, 2), len(pool_mcq) or 10)
        chosen = pool_mcq[:target_count]
        time_limit_seconds = 15 * 60  # 15 minutes
    elif payload.assessment_type in ("practical", "coding"):
        # Mode pratique : Coding labs uniquement selon règles training_logic.txt
        if primary_diff == "easy":
            target_count = 3
            time_limit_seconds = 30 * 60  # 30 min (10 min / q)
        elif primary_diff == "medium":
            target_count = 2
            time_limit_seconds = 20 * 60  # 20 min (10 min / q)
        else:
            target_count = 1
            time_limit_seconds = 10 * 60  # 10 min
        
        target_count = min(target_count, len(pool_coding) or target_count)
        chosen = pool_coding[:target_count]
    else:
        # Mode mixte (évolution / entraînement standard)
        target_count = min(max(payload.count, 2), 30)
        half = target_count // 2
        chosen.extend(pool_coding[:half])
        chosen.extend(pool_mcq[:(target_count - len(chosen))])
        if len(chosen) < target_count:
            remaining_coding = [c for c in pool_coding if c not in chosen]
            chosen.extend(remaining_coding[:(target_count - len(chosen))])
        if len(chosen) < target_count:
            remaining_mcq = [m for m in pool_mcq if m not in chosen]
            chosen.extend(remaining_mcq[:(target_count - len(chosen))])
        time_limit_seconds = 20 * 60

    random.shuffle(chosen)
    
    # Numérotation ordonnée
    for idx, item in enumerate(chosen, start=1):
        item["ordering"] = idx
    
    return {
        "assessment_type": payload.assessment_type,
        "selected_topics": selected_topics,
        "selected_difficulties": selected_difficulties,
        "target_topic": payload.target_topic or (selected_topics[0] if len(selected_topics) == 1 else None),
        "target_difficulty": payload.target_difficulty or (selected_difficulties[0] if len(selected_difficulties) == 1 else None),
        "time_limit_seconds": time_limit_seconds,
        "questions_count": len(chosen),
        "items": chosen
    }

@router.post("/submit-session")
def submit_training_session(
    payload: SessionSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soumet les réponses d'un entraînement, calcule la note sur 20 selon training_logic.txt."""
    curriculum = load_curriculum()
    
    # Snapshot gamification initiale pour détecter nouveaux badges débloqués
    prev_gamif = calculate_gamification(current_user.id, db)
    prev_unlocked = set(m["id"] for m in prev_gamif["all_milestones"] if m["unlocked"])
    
    # Cartographie exhaustive des questions et exercices par ID et clé composite
    all_curriculum_items = {}
    for ch in curriculum.get("chapters", []):
        ch_id = ch.get("id", "")
        for m in ch.get("mcq_questions", []):
            qid_str = str(m["id"])
            all_curriculum_items[qid_str] = (m, ch)
            if ch_id:
                all_curriculum_items[f"{ch_id}::{qid_str}"] = (m, ch)
        for c in ch.get("coding_exercises", []):
            cid_str = str(c["id"])
            all_curriculum_items[cid_str] = (c, ch)
            if ch_id:
                all_curriculum_items[f"{ch_id}::{cid_str}"] = (c, ch)
            
    total_items = len(payload.answers)
    if total_items == 0:
        raise HTTPException(status_code=400, detail="Aucune réponse fournie.")
        
    total_awarded_points = 0.0
    total_max_points = 0.0
    correct_count = 0
    total_hints = 0
    topic_scores: Dict[str, Dict[str, float]] = {}
    detailed_feedback = []
    
    for ans in payload.answers:
        topic = ans.topic
        if topic not in topic_scores:
            topic_scores[topic] = {"awarded": 0.0, "max": 0.0, "correct": 0, "total": 0}
        topic_scores[topic]["total"] += 1
        
        is_item_correct = False
        solution_info = None
        user_answer_display = ""
        awarded_pts = 0.0
        
        item_entry = (
            all_curriculum_items.get(f"{topic}::{ans.id}")
            or all_curriculum_items.get(str(ans.id))
        )
        if not item_entry:
            detailed_feedback.append({
                "id": ans.id,
                "type": ans.type,
                "topic": topic,
                "is_correct": False,
                "awarded_points": 0.0,
                "max_points": 1.0,
                "user_answer": str(ans.student_answer or ""),
                "solution": "N/A",
                "explanation": "Question non répertoriée dans le cursus."
            })
            continue

        raw_item, ch_info = item_entry
        item_raw_type = raw_item.get("type", ans.type)
        
        if item_raw_type == "coding":
            diff = ans.difficulty or raw_item.get("difficulty", "medium")
            max_pts = 2.0 if diff == "easy" else (3.0 if diff == "medium" else (4.0 if diff == "hard" else 5.0))
            hints_used = ans.hints_used or 0
            total_hints += hints_used
            hint_mult = 1.0 if hints_used == 0 else (0.5 if hints_used == 1 else 0.0)

            clean_student = str(ans.student_answer or "").strip()
            clean_sol = str(raw_item.get("solution", "")).strip()

            if ans.is_correct is True:
                is_item_correct = True
                awarded_pts = max_pts * hint_mult
                explanation = "✅ Exercice validé avec succès !"
            elif clean_student and clean_sol and clean_student == clean_sol:
                is_item_correct = True
                awarded_pts = max_pts * hint_mult
                explanation = "✅ Exercice validé avec succès (solution identique à la référence) !"
            elif clean_student:
                # Évaluation dynamique et autoritaire via le bac à sable Python
                test_cases_to_run = []
                pub_tests = raw_item.get("public_tests") or []
                hid_tests = raw_item.get("hidden_tests") or []
                for idx, t in enumerate(pub_tests):
                    test_cases_to_run.append({
                        "id": f"pub_{idx+1}",
                        "input": str(t.get("input", "")),
                        "output": str(t.get("output", t.get("expected_output", ""))),
                        "is_public": True
                    })
                for idx, t in enumerate(hid_tests):
                    test_cases_to_run.append({
                        "id": f"hid_{idx+1}",
                        "input": str(t.get("input", "")),
                        "output": str(t.get("output", t.get("expected_output", ""))),
                        "is_public": False
                    })
                if not test_cases_to_run and "test_cases" in raw_item:
                    for idx, t in enumerate(raw_item["test_cases"]):
                        test_cases_to_run.append({
                            "id": f"tc_{idx+1}",
                            "input": str(t.get("input", "")),
                            "output": str(t.get("output", t.get("expected_output", ""))),
                            "is_public": t.get("is_public", True)
                        })

                if test_cases_to_run:
                    exec_res = execute_user_code_against_tests(
                        clean_student,
                        test_cases_to_run,
                        timeout_seconds=3.0,
                        mask_hidden_output=True
                    )
                    if exec_res.get("all_passed") is True:
                        is_item_correct = True
                        awarded_pts = max_pts * hint_mult
                        explanation = f"✅ Exercice validé avec succès ({exec_res.get('passed_count')}/{exec_res.get('total_count')} tests réussis) !"
                    else:
                        is_item_correct = False
                        awarded_pts = 0.0
                        passed_c = exec_res.get("passed_count", 0)
                        tot_c = exec_res.get("total_count", len(test_cases_to_run))
                        explanation = f"❌ Tests non validés ({passed_c}/{tot_c} réussis). Voir corrigé de référence ci-dessous."
                else:
                    is_item_correct = False
                    awarded_pts = 0.0
                    explanation = "Solution de référence : voir corrigé ci-dessous."
            else:
                is_item_correct = False
                awarded_pts = 0.0
                explanation = "Aucun code soumis."

            pedagogical_exp = str(raw_item.get("explanation") or "").strip()
            if pedagogical_exp:
                explanation += f"\n\n💡 Analyse pédagogique :\n{pedagogical_exp}"

            solution_info = raw_item.get("solution", "")
            user_answer_display = ans.student_answer or "(Code non soumis)"
        else:
            max_pts = float(raw_item.get("points", 1.0))
            if item_raw_type in ("yesno", "boolean"):
                q_eval_type = "boolean"
                correct_ref = raw_item.get("correct")
                if correct_ref is None and "correct_answers_json" in raw_item:
                    correct_ref = raw_item["correct_answers_json"]
                solution_info = "Vrai" if str(correct_ref).lower() in ("true", "1", "vrai") else "Faux"
                user_answer_display = "Vrai" if ans.student_answer in (True, 'true', 'True', 1, '1') else ("Faux" if ans.student_answer in (False, 'false', 'False', 0, '0') else str(ans.student_answer or "Non répondu"))

            elif item_raw_type in ("simple_blank", "fill_blank"):
                q_eval_type = "fill_blank"
                correct_ref = raw_item.get("answer") or raw_item.get("correct") or raw_item.get("correct_answers_json", "")
                solution_info = str(correct_ref)
                user_answer_display = str(ans.student_answer or "Non répondu")

            elif item_raw_type == "matching":
                q_eval_type = "matching"
                correct_ref = raw_item.get("pairs") or raw_item.get("correct_answers_json", {})
                if isinstance(correct_ref, str):
                    try: correct_ref = json.loads(correct_ref)
                    except: pass
                solution_info = ", ".join(f"{k} ➔ {v}" for k, v in correct_ref.items()) if isinstance(correct_ref, dict) else str(correct_ref)
                if isinstance(ans.student_answer, dict):
                    user_answer_display = ", ".join(f"{k} ➔ {v}" for k, v in ans.student_answer.items())
                else:
                    user_answer_display = str(ans.student_answer or "Non répondu")

            elif item_raw_type in ("multi_choice",) or (item_raw_type == "mcq" and isinstance(raw_item.get("correct"), list) and len(raw_item.get("correct", [])) > 1):
                q_eval_type = "multi_choice"
                opts = raw_item.get("options", [])
                correct_list = raw_item.get("correct", [])
                correct_ref = [str(c) for c in correct_list]
                if isinstance(opts, list) and opts and isinstance(opts[0], dict):
                    opt_dict = {str(o.get("id")): o.get("text", "") for o in opts}
                    solution_info = ", ".join(opt_dict.get(str(c), str(c)) for c in correct_list)
                    if isinstance(ans.student_answer, list):
                        user_answer_display = ", ".join(opt_dict.get(str(c), str(c)) for c in ans.student_answer)
                    else:
                        user_answer_display = str(ans.student_answer or "Non répondu")
                elif isinstance(opts, list) and opts and isinstance(opts[0], str):
                    solution_info = ", ".join(opts[int(c)] for c in correct_list if str(c).isdigit() and 0 <= int(c) < len(opts))
                    if isinstance(ans.student_answer, list):
                        user_answer_display = ", ".join(opts[int(c)] for c in ans.student_answer if str(c).isdigit() and 0 <= int(c) < len(opts))
                    else:
                        user_answer_display = str(ans.student_answer or "Non répondu")
                else:
                    solution_info = str(correct_ref)
                    user_answer_display = str(ans.student_answer or "Non répondu")

            else:  # single_choice, intruder, or simple mcq
                q_eval_type = "single_choice"
                opts = raw_item.get("options", [])
                c_val = raw_item.get("correct", 0)
                if isinstance(c_val, list):
                    c_val = c_val[0] if c_val else 0
                correct_ref = str(c_val)
                if isinstance(opts, list) and opts and isinstance(opts[0], dict):
                    opt_dict = {str(o.get("id")): o.get("text", "") for o in opts}
                    solution_info = opt_dict.get(str(c_val), str(c_val))
                    user_answer_display = opt_dict.get(str(ans.student_answer), str(ans.student_answer or "Non répondu"))
                elif isinstance(opts, list) and opts and isinstance(opts[0], str):
                    try:
                        c_idx = int(c_val)
                        solution_info = opts[c_idx] if 0 <= c_idx < len(opts) else str(c_val)
                    except Exception:
                        solution_info = str(c_val)
                    try:
                        u_idx = int(ans.student_answer)
                        user_answer_display = opts[u_idx] if 0 <= u_idx < len(opts) else str(ans.student_answer)
                    except Exception:
                        user_answer_display = str(ans.student_answer or "Non répondu")
                else:
                    solution_info = str(correct_ref)
                    user_answer_display = str(ans.student_answer or "Non répondu")

            awarded_pts, is_item_correct, _ = evaluate_answer(
                q_type=q_eval_type,
                user_answer=ans.student_answer,
                correct_answers=correct_ref,
                points=max_pts,
                negative_penalty=0.0
            )
            explanation = raw_item.get("explanation") or ("✅ Réponse exacte !" if is_item_correct else f"Corrigé attendu : {solution_info}")

        total_awarded_points += awarded_pts
        total_max_points += max_pts

        if is_item_correct:
            correct_count += 1
            topic_scores[topic]["correct"] += 1
        topic_scores[topic]["awarded"] += awarded_pts
        topic_scores[topic]["max"] += max_pts

        detailed_feedback.append({
            "id": ans.id,
            "type": item_raw_type,
            "topic": topic,
            "prompt_text": raw_item.get("text") or raw_item.get("title") or "",
            "is_correct": is_item_correct,
            "awarded_points": round(awarded_pts, 2),
            "max_points": round(max_pts, 2),
            "user_answer": user_answer_display,
            "solution": solution_info,
            "explanation": explanation
        })
        
    final_mark = round((total_awarded_points / total_max_points) * 20.0, 2) if total_max_points > 0 else 0.0
    percentage = round((total_awarded_points / total_max_points) * 100.0, 1) if total_max_points > 0 else 0.0
    passed = final_mark >= PASSING_MARK
    
    # Calcul des notes par sujet normalisées sur 20
    topic_marks = {}
    for t, scores in topic_scores.items():
        t_mark = round((scores["awarded"] / scores["max"]) * 20.0, 2) if scores["max"] > 0 else 0.0
        topic_marks[t] = t_mark
        
    # Enregistrement dans l'historique
    attempt = TrainingAttempt(
        user_id=current_user.id,
        assessment_type=payload.assessment_type,
        selected_topics_json=json.dumps(payload.selected_topics),
        selected_difficulties_json=json.dumps(payload.selected_difficulties),
        target_topic=payload.target_topic or (payload.selected_topics[0] if len(payload.selected_topics) == 1 else None),
        target_difficulty=payload.target_difficulty or (payload.selected_difficulties[0] if len(payload.selected_difficulties) == 1 else None),
        passed=passed,
        final_mark=final_mark,
        percentage=percentage,
        total_questions=total_items,
        correct_count=correct_count,
        hints_used=total_hints,
        topic_marks_json=json.dumps(topic_marks)
    )
    db.add(attempt)
    db.commit()
    
    # Calcul de la nouvelle gamification et des nouveaux badges
    new_gamif = calculate_gamification(current_user.id, db)
    new_badges = [m for m in new_gamif["all_milestones"] if m["unlocked"] and m["id"] not in prev_unlocked]
    level_up = new_gamif["level"] > prev_gamif["level"]
    
    # Récupérer l'historique complet pour stats
    history_records = db.query(TrainingAttempt).filter(TrainingAttempt.user_id == current_user.id).order_by(TrainingAttempt.created_at.asc()).all()
    history_list = [{
        "final_mark": h.final_mark,
        "assessment_type": h.assessment_type,
        "topic_marks": json.loads(h.topic_marks_json) if h.topic_marks_json else {},
        "created_at": h.created_at.isoformat()
    } for h in history_records]
    
    progression = get_progression_stats(history_list, history_list[-1])
    topic_rankings = get_topic_historical_averages(history_list)
    
    # Mettre à jour les chapitres correspondants
    for topic_id in payload.selected_topics:
        ch_prog = db.query(ChapterProgress).filter(
            ChapterProgress.user_id == current_user.id,
            ChapterProgress.chapter_id == topic_id
        ).first()
        if not ch_prog:
            ch_prog = ChapterProgress(
                user_id=current_user.id,
                chapter_id=topic_id,
                status="completed" if passed else "in_progress",
                best_mark=final_mark,
                completed_exercises=correct_count
            )
            db.add(ch_prog)
        else:
            if final_mark > ch_prog.best_mark:
                ch_prog.best_mark = final_mark
            if passed:
                ch_prog.status = "completed"
            ch_prog.completed_exercises += correct_count
    db.commit()
    
    return {
        "final_mark": final_mark,
        "percentage": percentage,
        "passed": passed,
        "passing_mark": PASSING_MARK,
        "total_questions": total_items,
        "correct_count": correct_count,
        "progression": progression,
        "topic_marks": topic_marks,
        "topic_rankings": topic_rankings,
        "feedback": detailed_feedback,
        "gamification": new_gamif,
        "new_badges": new_badges,
        "level_up": level_up
    }

@router.get("/history")
def get_training_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne l'historique d'entraînement de l'étudiant avec courbe d'évolution et badges de niveau."""
    history_records = db.query(TrainingAttempt).filter(TrainingAttempt.user_id == current_user.id).order_by(TrainingAttempt.created_at.asc()).all()
    if not history_records:
        return {
            "attempts": [],
            "stats": None,
            "topic_rankings": {},
            "marks_history": []
        }
        
    history_list = [{
        "id": h.id,
        "assessment_type": h.assessment_type,
        "final_mark": h.final_mark,
        "percentage": h.percentage,
        "correct_count": h.correct_count,
        "total_questions": h.total_questions,
        "topic_marks": json.loads(h.topic_marks_json) if h.topic_marks_json else {},
        "created_at": h.created_at.isoformat()
    } for h in history_records]
    
    latest = history_list[-1]
    progression = get_progression_stats(history_list, latest)
    topic_rankings = get_topic_historical_averages(history_list)
    marks_history = [h["final_mark"] for h in history_list]
    
    return {
        "attempts": history_list,
        "stats": progression,
        "topic_rankings": topic_rankings,
        "marks_history": marks_history
    }

@router.post("/run-code")
def run_custom_code(
    payload: RunCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """Exécute un script Python arbitraire avec stdin personnalisé (Console E/S interactive)."""
    return execute_user_code_with_input(payload.code, payload.stdin or "", payload.timeout or 3.0)

@router.post("/run-tests")
def run_code_against_tests(
    payload: RunTestsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Exécute le code d'un exercice contre les cas de test.
    - Si payload.tests est fourni directement : exécute sur ces tests sans lookup.
    - Sinon : recherche l'exercice par exercise_id dans curriculum ou coding_challenges.json.
    - Si run_all=False : teste uniquement les cas publics avec entrées et sorties détaillées.
    - Si run_all=True : soumission complète validant les tests publics et cachés.
    """
    if payload.tests and len(payload.tests) > 0:
        all_tests = []
        for i, t in enumerate(payload.tests):
            all_tests.append({
                "id": t.get("id", f"test_{i+1}"),
                "input": t.get("input", ""),
                "output": t.get("output", t.get("expected_output", "")),
                "is_public": t.get("is_public", True)
            })
        return execute_user_code_against_tests(
            payload.code,
            all_tests,
            timeout_seconds=payload.timeout or 3.0,
            mask_hidden_output=True
        )

    curriculum = load_curriculum()
    ex_id_str = str(payload.exercise_id)
    
    target_exercise = None
    for ch in curriculum.get("chapters", []):
        for ex in ch.get("coding_exercises", []):
            if str(ex.get("id")) == ex_id_str:
                target_exercise = ex
                break
        if target_exercise:
            break
            
    if not target_exercise:
        # Recherche dans coding_challenges.json
        import os
        challenges_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "python_training", "coding_challenges.json")
        if os.path.exists(challenges_path):
            with open(challenges_path, "r", encoding="utf-8") as f:
                challenges = json.load(f)
                for ch in challenges:
                    if str(ch.get("id")) == ex_id_str:
                        target_exercise = ch
                        break
                        
    if not target_exercise:
        raise HTTPException(status_code=404, detail=f"Exercice Python #{payload.exercise_id} introuvable.")
        
    public_tests = [{"id": f"pub_{i+1}", "input": t.get("input", ""), "output": t.get("output", t.get("expected_output", "")), "is_public": True} for i, t in enumerate(target_exercise.get("public_tests", []))]
    hidden_tests = [{"id": f"hid_{i+1}", "input": t.get("input", ""), "output": t.get("output", t.get("expected_output", "")), "is_public": False} for i, t in enumerate(target_exercise.get("hidden_tests", []))]
    
    if payload.run_all:
        all_tests = public_tests + hidden_tests
    else:
        all_tests = public_tests
        
    return execute_user_code_against_tests(
        payload.code,
        all_tests,
        timeout_seconds=payload.timeout or 3.0,
        mask_hidden_output=True
    )

