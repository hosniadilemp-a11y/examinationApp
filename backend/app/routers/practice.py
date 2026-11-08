import os
import json
import random
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Module, Exam, Question, User, PracticeAttempt
from backend.app.schemas import (
    QuestionStudentView, PracticeSubmitPayload, 
    PracticeExamResult, PracticeQuestionResult
)
from backend.app.services.grading import evaluate_answer
from backend.app.services.training_service import get_level, get_level_title
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/api/practice", tags=["Tests de Niveau (24h/24)"])

PRACTICE_MODULES_CONFIG = [
    {
        "code": "PYTHON_PROG",
        "title": "Programmation Python & Algorithmique",
        "seed_file": "seed_python_prog_100.json",
        "desc": "Algorithmique fondamentale, structures de données, POO et syntaxe Python."
    },
    {
        "code": "SYS_EXPLOIT",
        "title": "Systèmes d'Exploitation (Linux & Shell)",
        "seed_file": "seed_sys_exploit_100.json",
        "desc": "Système de fichiers FHS, permissions, processus, signaux, scripting Bash et réseau."
    },
    {
        "code": "CYBER_CRYPTO",
        "title": "Cybersécurité & Cryptographie",
        "seed_file": "seed_cyber_crypto_100.json",
        "desc": "Chiffrements sym/asym, RSA, AES, hachage, PKI, cyberattaques web et protocoles sécurisés."
    }
]

LEGACY_MODULE_MAP = {
    "ALGO": "PYTHON_PROG",
    "PYTHON_INIT": "PYTHON_PROG",
    "LINUX_ADMIN": "SYS_EXPLOIT",
    "CRYPTO": "CYBER_CRYPTO"
}

MODULE_ALIASES = {
    "PYTHON_PROG": ["PYTHON_PROG", "ALGO", "PYTHON_INIT"],
    "SYS_EXPLOIT": ["SYS_EXPLOIT", "LINUX_ADMIN"],
    "CYBER_CRYPTO": ["CYBER_CRYPTO", "CRYPTO"]
}

def _resolve_module_config(code: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    clean = code.upper().strip()
    clean = LEGACY_MODULE_MAP.get(clean, clean)
    cfg = next((m for m in PRACTICE_MODULES_CONFIG if m["code"].upper() == clean), None)
    if not cfg:
        return None
    res = dict(cfg)
    if db is not None:
        mod = db.query(Module).filter(Module.code == clean).first()
        if mod and mod.title:
            res["title"] = mod.title
            if mod.description:
                res["desc"] = mod.description
    return res

def _get_seed_path(filename: str) -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seeds", filename)

def load_seed_questions(filename: str) -> List[Dict[str, Any]]:
    path = _get_seed_path(filename)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fichier de questions '{filename}' introuvable."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _compute_module_stats(user_id: str, db: Session) -> Dict[str, Any]:
    """Calcule pour chacun des 3 tests de niveau le nombre de tentatives, les 4 dernières notes et le niveau."""
    summary = {}
    for m in PRACTICE_MODULES_CONFIG:
        code = m["code"]
        resolved = _resolve_module_config(code, db) or m
        aliases = MODULE_ALIASES.get(code, [code])
        attempts = db.query(PracticeAttempt).filter(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.module_code.in_(aliases)
        ).order_by(PracticeAttempt.created_at.desc()).all()
        
        count = len(attempts)
        last_4 = attempts[:4]
        last_4_scores = [round(a.grade_20, 2) for a in last_4]
        last_4_avg = round(sum(last_4_scores) / len(last_4_scores), 2) if last_4_scores else 0.0
        best_grade = max([a.grade_20 for a in attempts]) if attempts else 0.0
        lvl = get_level(last_4_avg)
        
        summary[code] = {
            "module_code": code,
            "module_title": resolved["title"],
            "attempts_count": count,
            "last_4_scores": last_4_scores,
            "last_4_average": last_4_avg,
            "best_grade": round(best_grade, 2),
            "level": lvl,
            "level_title": get_level_title(lvl)
        }
        
    overall_avg = round(sum(v["last_4_average"] for v in summary.values()) / 3.0, 2) if summary else 0.0
    overall_lvl = get_level(overall_avg)
    
    # Rétrocompatibilité : inclure aussi les clés d'anciens modules
    for leg_code, new_code in LEGACY_MODULE_MAP.items():
        if new_code in summary and leg_code not in summary:
            leg_stat = dict(summary[new_code])
            leg_stat["module_code"] = leg_code
            summary[leg_code] = leg_stat

    return {
        "modules": summary,
        "overall_last_4_average": overall_avg,
        "overall_level": overall_lvl,
        "overall_level_title": get_level_title(overall_lvl)
    }

@router.get("/modules")
def list_practice_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste les 3 modules de test de niveau avec métriques des 4 dernières tentatives et niveau."""
    stats = _compute_module_stats(current_user.id, db)
    results = []
    for m in PRACTICE_MODULES_CONFIG:
        resolved = _resolve_module_config(m["code"], db) or m
        mod_stat = stats["modules"].get(m["code"], {})
        results.append({
            "code": m["code"],
            "title": resolved["title"],
            "description": resolved["desc"],
            "question_count": 100,
            "total_questions": 100,
            "availability": "Permanent (24h/24)",
            "allowed_attempts": "Illimité",
            "attempts_count": mod_stat.get("attempts_count", 0),
            "last_4_scores": mod_stat.get("last_4_scores", []),
            "last_4_average": mod_stat.get("last_4_average", 0.0),
            "best_grade": mod_stat.get("best_grade", 0.0),
            "level": mod_stat.get("level", 1),
            "level_title": mod_stat.get("level_title", "Grand Débutant (Niveau 1)")
        })
    return results

@router.get("/history")
def get_practice_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne l'historique complet de toutes les tentatives de test de niveau de l'étudiant."""
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == current_user.id
    ).order_by(PracticeAttempt.created_at.desc()).all()
    
    history_list = []
    for a in attempts:
        history_list.append({
            "id": a.id,
            "module_code": a.module_code,
            "module_title": a.module_title,
            "grade_20": a.grade_20,
            "percentage": a.percentage,
            "total_awarded": a.total_awarded,
            "max_possible": a.max_possible,
            "warnings_count": a.warnings_count,
            "passed": a.grade_20 >= 14.0,
            "created_at": a.created_at.isoformat()
        })
        
    stats = _compute_module_stats(current_user.id, db)
    
    return {
        "attempts": history_list,
        "total_attempts": len(history_list),
        "pillars": stats["modules"],
        "overall_last_4_average": stats["overall_last_4_average"],
        "overall_level": stats["overall_level"],
        "overall_level_title": stats["overall_level_title"]
    }

@router.get("/exams/{module_code}/questions")
def get_practice_questions(
    module_code: str,
    count: Optional[int] = Query(None, description="Nombre de questions à tirer aléatoirement (défaut: toutes ou 20)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les questions d'un module de test de niveau.
    - Double brassage : ordre des questions et ordre des options aléatoires avec préservation des IDs de réponses.
    - Les réponses correctes sont strictement MASQUÉES pour garantir l'intégrité de l'évaluation.
    """
    mod_config = _resolve_module_config(module_code, db)
    if not mod_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module de test de niveau '{module_code}' inconnu."
        )
        
    raw_questions = load_seed_questions(mod_config["seed_file"])
    
    # Échantillonnage si count spécifié (ex: count=20)
    if count is not None and 0 < count < len(raw_questions):
        shuffled_questions = random.sample(raw_questions, count)
    else:
        shuffled_questions = list(raw_questions)
        random.shuffle(shuffled_questions)

    student_view_questions = []
    
    for q in shuffled_questions:
        raw_opts = json.loads(q["options_json"]) if isinstance(q["options_json"], str) else q["options_json"]
        
        # Double brassage des options avec préservation de l'identifiant pour la correction
        if isinstance(raw_opts, list) and q["type"] in ("single_choice", "multi_choice"):
            opts_copy = []
            for idx, opt in enumerate(raw_opts):
                if isinstance(opt, dict):
                    opts_copy.append({
                        "id": str(opt.get("id", idx)),
                        "text": str(opt.get("text", ""))
                    })
                else:
                    opts_copy.append({
                        "id": str(idx),
                        "text": str(opt)
                    })
            random.shuffle(opts_copy)
        elif isinstance(raw_opts, dict) and q["type"] == "matching":
            left_list = list(raw_opts.get("left", []))
            right_list = list(raw_opts.get("right", []))
            random.shuffle(left_list)
            random.shuffle(right_list)
            opts_copy = {"left": left_list, "right": right_list}
        else:
            opts_copy = raw_opts

        orig_order = q["ordering"]
        display_order = orig_order

        student_view_questions.append({
            "id": f"PRACTICE-{module_code.upper()}-{display_order}",
            "ordering": display_order,
            "type": q["type"],
            "prompt_markdown": q["prompt_markdown"],
            "points": q["points"],
            "options": opts_copy
        })
        
    return {
        "module_code": module_code.upper(),
        "module_title": mod_config["title"],
        "total_questions": len(student_view_questions),
        "questions": student_view_questions
    }

@router.post("/exams/{module_code}/submit", response_model=PracticeExamResult)
def submit_practice_exam(
    module_code: str,
    payload: PracticeSubmitPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soumet les réponses à un test de niveau par module.
    Enregistre la tentative en base de données pour l'historique et le calcul des niveaux.
    Retourne instantanément le score global, la note sur 20, le corrigé complet et les explications détaillées.
    """
    mod_config = _resolve_module_config(module_code, db)
    if not mod_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module de test de niveau '{module_code}' inconnu."
        )
        
    raw_questions = load_seed_questions(mod_config["seed_file"])
    user_answers = payload.answers or {}
    
    # Si la session a présenté une sélection spécifique de questions (ex: 20 questions tirées au sort sur 100)
    req_code = module_code.upper()
    resolved_code = mod_config["code"]
    if payload.question_ids:
        active_ids_set = set(payload.question_ids)
        target_questions = [
            q for q in raw_questions
            if f"PRACTICE-{resolved_code}-{q['ordering']}" in active_ids_set
            or f"PRACTICE-{req_code}-{q['ordering']}" in active_ids_set
        ]
    else:
        target_questions = raw_questions
    
    total_awarded = 0.0
    max_possible = 0.0
    detailed_results = []
    
    for q in target_questions:
        orig_order = q["ordering"]
        display_order = orig_order

        q_id = f"PRACTICE-{req_code}-{display_order}"
        alt_q_id = f"PRACTICE-{resolved_code}-{orig_order}"

        q_points = float(q["points"])
        max_possible += q_points
        
        user_ans = user_answers.get(q_id)
        if user_ans is None:
            user_ans = user_answers.get(alt_q_id)
        correct_ans = json.loads(q["correct_answers_json"]) if isinstance(q["correct_answers_json"], str) else q["correct_answers_json"]
        
        awarded, is_correct, explanation = evaluate_answer(
            q_type=q["type"],
            user_answer=user_ans,
            correct_answers=correct_ans,
            points=q_points,
            negative_penalty=float(q.get("negative_penalty", 0.5)),
            floor_score=0.0
        )
        
        total_awarded += awarded
        
        detailed_results.append(PracticeQuestionResult(
            question_id=q_id,
            prompt_markdown=q["prompt_markdown"],
            type=q["type"],
            user_answer=user_ans,
            correct_answer=correct_ans,
            awarded_points=round(awarded, 2),
            max_points=round(q_points, 2),
            is_correct=is_correct,
            explanation=explanation
        ))
        
    grade_20 = round((total_awarded / max_possible) * 20.0, 2) if max_possible > 0 else 0.0
    percentage = round((total_awarded / max_possible) * 100.0, 1) if max_possible > 0 else 0.0
    
    # Enregistrement persistant de la tentative
    attempt = PracticeAttempt(
        user_id=current_user.id,
        module_code=req_code,
        module_title=mod_config["title"],
        grade_20=grade_20,
        percentage=percentage,
        total_awarded=round(total_awarded, 2),
        max_possible=round(max_possible, 2),
        answers_json=json.dumps(user_answers),
        detailed_results_json=json.dumps([r.model_dump() for r in detailed_results]),
        warnings_count=payload.warnings_count or 0
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    return PracticeExamResult(
        attempt_id=attempt.id,
        module_code=req_code,
        module_title=mod_config["title"],
        total_awarded=round(total_awarded, 2),
        max_possible=round(max_possible, 2),
        grade_20=grade_20,
        percentage=percentage,
        warnings_count=attempt.warnings_count,
        detailed_results=detailed_results
    )
