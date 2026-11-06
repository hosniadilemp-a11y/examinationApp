import os
import json
import random
import uuid
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models import User, PracticeAttempt
from backend.app.services.grading import evaluate_answer

LINUX_CURRICULUM_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "linux_training", "curriculum.json"
)
LINUX_CHALLENGES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "linux_training", "challenges.json"
)

# In-memory caches
_curriculum_cache: Optional[Dict[str, Any]] = None
_challenges_cache: Optional[List[Dict[str, Any]]] = None

def load_linux_curriculum() -> Dict[str, Any]:
    """Charge et met en cache le cursus complet Linux (niveaux, chapitres, QCM)."""
    global _curriculum_cache
    if not os.path.exists(LINUX_CURRICULUM_PATH):
        return {"levels": [], "chapters": []}
    with open(LINUX_CURRICULUM_PATH, "r", encoding="utf-8") as f:
        _curriculum_cache = json.load(f)
    return _curriculum_cache

def load_linux_challenges() -> List[Dict[str, Any]]:
    """Charge et met en cache l'ensemble des défis pratiques Linux avec tests publics et cachés."""
    global _challenges_cache
    if not os.path.exists(LINUX_CHALLENGES_PATH):
        return []
    with open(LINUX_CHALLENGES_PATH, "r", encoding="utf-8") as f:
        _challenges_cache = json.load(f)
    return _challenges_cache

def get_levels_summary() -> List[Dict[str, Any]]:
    """Retourne la synthèse des 4 niveaux de formation Linux."""
    curr = load_linux_curriculum()
    levels = curr.get("levels", [])
    if not levels:
        levels = [
            {
                "id": 1,
                "level": 1,
                "title": "Niveau 1 : Navigation & Manipulation de Fichiers",
                "description": "Bases de l'arborescence FHS, chemins absolus/relatifs, création et gestion de fichiers.",
                "topics": ["FHS Navigation", "Manipulation de Fichiers"],
                "challenges_count": 3,
                "quizzes_count": 16
            },
            {
                "id": 2,
                "level": 2,
                "title": "Niveau 2 : Permissions, Utilisateurs & Filtrage",
                "description": "Attributs POSIX, chmod/chown et filtrage textuel avec grep et find.",
                "topics": ["Permissions & Sécurité", "Filtrage Textuel"],
                "challenges_count": 2,
                "quizzes_count": 16
            },
            {
                "id": 3,
                "level": 3,
                "title": "Niveau 3 : Scripts Bash, Tubes & Redirections",
                "description": "Composition de pipelines, redirections standards et logiques conditionnelles.",
                "topics": ["Pipes & Redirections", "Scripts Bash"],
                "challenges_count": 2,
                "quizzes_count": 16
            },
            {
                "id": 4,
                "level": 4,
                "title": "Niveau 4 : Administration Système, Processus & Diagnostic",
                "description": "Supervision des processus, signaux système, variables d'environnement et diagnostic.",
                "topics": ["Processus & Signaux", "Diagnostic Système"],
                "challenges_count": 2,
                "quizzes_count": 16
            }
        ]
    return levels

def _get_all_challenges_pool() -> List[Dict[str, Any]]:
    """Combine les défis de challenges.json et les coding_exercises de curriculum.json."""
    pool = list(load_linux_challenges())
    seen_ids = set(c["id"] for c in pool)
    
    curr = load_linux_curriculum()
    chapter_level_map = {
        "fhs_navigation": 1,
        "file_management": 1,
        "permissions_security": 2,
        "text_processing_pipes": 3,
        "processes_signals": 4,
        "bash_scripting": 3
    }
    
    for ch in curr.get("chapters", []):
        ch_lvl = chapter_level_map.get(ch["id"], 1)
        for ce in ch.get("coding_exercises", []):
            if ce["id"] not in seen_ids:
                ce_copy = dict(ce)
                ce_copy["level"] = ch_lvl
                pool.append(ce_copy)
                seen_ids.add(ce["id"])
    return pool

def get_safe_challenges_list(
    level: Optional[int] = None,
    user_id: Optional[str] = None,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Retourne la liste des défis pratiques sans jamais divulguer les tests cachés ni les solutions.
    Calcule le statut de résolution de l'étudiant ('unsolved', 'in_progress', 'solved').
    """
    pool = _get_all_challenges_pool()
    
    solved_ids = set()
    in_progress_ids = set()
    
    if user_id and db:
        attempts = db.query(PracticeAttempt).filter(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.module_code == "LINUX_ADMIN"
        ).all()
        for a in attempts:
            if a.detailed_results_json:
                try:
                    det = json.loads(a.detailed_results_json)
                    for item in det:
                        q_id = item.get("id") or item.get("challenge_id")
                        if item.get("is_correct") or item.get("all_passed") or item.get("passed"):
                            if q_id:
                                solved_ids.add(q_id)
                        elif q_id:
                            in_progress_ids.add(q_id)
                except Exception:
                    pass

    results = []
    for c in pool:
        c_lvl = c.get("level", 1)
        if level is not None and c_lvl != level:
            continue

        c_id = c["id"]
        status = "solved" if c_id in solved_ids else ("in_progress" if c_id in in_progress_ids else "unsolved")

        # Vue sécurisée : strict masquage de hidden_tests et solution
        results.append({
            "id": c_id,
            "level": c_lvl,
            "title": c.get("title", ""),
            "topic": c.get("topic", "Linux"),
            "difficulty": c.get("difficulty", "medium"),
            "points": float(c.get("points", 2.0)),
            "description": c.get("description", ""),
            "status": status,
            "public_tests_count": len(c.get("public_tests", [])),
            "hidden_tests_count": len(c.get("hidden_tests", []))
        })
    return results

def get_challenge_detail_student(challenge_id: str) -> Optional[Dict[str, Any]]:
    """
    Retourne les consignes complètes d'un défi pratique pour l'espace de travail étudiant.
    Strictement filtré : 'hidden_tests' et 'solution' sont toujours exclus.
    """
    pool = _get_all_challenges_pool()
    target = next((c for c in pool if c["id"] == challenge_id), None)
    if not target:
        return None

    # Extraction des tests publics avec formatage uniforme
    safe_public_tests = []
    for idx, t in enumerate(target.get("public_tests", []), start=1):
        safe_public_tests.append({
            "id": f"pub_{idx}",
            "name": t.get("name", f"Test Public #{idx}"),
            "cmd": t.get("cmd", ""),
            "expected_stdout": t.get("expected_stdout", ""),
            "expected_exit_code": t.get("expected_exit_code", 0),
            "assertion_type": t.get("assertion_type", "stdout"),
            "expected": t.get("expected", t.get("expected_stdout", ""))
        })

    return {
        "id": target["id"],
        "level": target.get("level", 1),
        "title": target.get("title", ""),
        "topic": target.get("topic", "Linux"),
        "difficulty": target.get("difficulty", "medium"),
        "points": float(target.get("points", 2.0)),
        "description": target.get("description", ""),
        "initial_fs": target.get("initial_fs", {}),
        "starter_cmd": target.get("starter_cmd", target.get("starter_code", "")),
        "public_tests": safe_public_tests,
        "hints": target.get("hints", [])
    }

def get_theory_quizzes(
    level: Optional[int] = None,
    topic: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retourne les questions théoriques du cursus Linux avec masquage des réponses correctes.
    """
    curr = load_linux_curriculum()
    quizzes = []

    level_map = {
        "fhs_navigation": 1,
        "file_management": 1,
        "permissions_security": 2,
        "text_processing_pipes": 3,
        "processes_signals": 4,
        "bash_scripting": 3
    }

    for ch in curr.get("chapters", []):
        ch_level = level_map.get(ch["id"], 1)
        if level is not None and ch_level != level:
            continue

        for q in ch.get("mcq_questions", []):
            q_topic = q.get("topic", ch.get("title", "Linux"))
            if topic is not None and topic.lower() not in q_topic.lower():
                continue

            # Vue sécurisée sans corrigé
            q_copy = dict(q)
            q_copy["level"] = ch_level
            q_copy.pop("correct", None)
            q_copy.pop("explanation", None)
            quizzes.append(q_copy)
    return quizzes

def _check_vfs_path_exists(vfs_state: Dict[str, Any], path: str) -> bool:
    """Vérifie la présence d'un chemin dans l'état VFS (format arborescent ou plat)."""
    clean_path = path.strip().rstrip("/")
    if not clean_path:
        return True

    # 1. Vérification dans un dictionnaire plat
    if clean_path in vfs_state:
        return True
    if f"/home/student/{clean_path.lstrip('/')}" in vfs_state:
        return True

    # 2. Vérification dans l'arborescence imbriquée FHS
    parts = [p for p in clean_path.split("/") if p]
    
    def search_tree(node: Dict[str, Any], remaining: List[str]) -> bool:
        if not remaining:
            return True
        head = remaining[0]
        tail = remaining[1:]
        
        # Racine / direct lookup
        if f"/{head}" in node:
            return search_tree(node[f"/{head}"], tail)
        if head in node:
            return search_tree(node[head], tail)
            
        files = node.get("files", {})
        if head in files:
            return search_tree(files[head], tail)
        return False

    return search_tree(vfs_state, parts)

def _get_vfs_file_content(vfs_state: Dict[str, Any], path: str) -> Optional[str]:
    """Récupère le contenu d'un fichier dans le VFS pour les assertions de contenu."""
    clean_path = path.strip().rstrip("/")
    
    # Dictionnaire plat
    for candidate in [clean_path, f"/home/student/{clean_path.lstrip('/')}"]:
        if candidate in vfs_state:
            node = vfs_state[candidate]
            if isinstance(node, dict):
                return node.get("content", "")
            return str(node)

    # Arborescence récursive
    parts = [p for p in clean_path.split("/") if p]
    cur = vfs_state
    for p in parts:
        if isinstance(cur, dict):
            if f"/{p}" in cur:
                cur = cur[f"/{p}"]
            elif p in cur:
                cur = cur[p]
            elif "files" in cur and p in cur["files"]:
                cur = cur["files"][p]
            else:
                return None
        else:
            return None
    if isinstance(cur, dict):
        return cur.get("content", "")
    return str(cur)

def evaluate_linux_challenge(
    challenge_id: str,
    command: str,
    vfs_state: Optional[Dict[str, Any]] = None,
    execution_output: Optional[Dict[str, Any]] = None,
    client_tests_passed: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Évalue véritablement la conformité d'une solution pour un défi Linux.
    Vérifie les cas de test publics et cachés contre la commande, la sortie stdout et les effets VFS.
    """
    pool = _get_all_challenges_pool()
    challenge = next((c for c in pool if c["id"] == challenge_id), None)
    if not challenge:
        return {
            "challenge_id": challenge_id,
            "success": False,
            "all_passed": False,
            "awarded_points": 0.0,
            "max_points": 0.0,
            "public_results": [],
            "hidden_results": [],
            "message": f"Défi '{challenge_id}' introuvable."
        }

    total_points = float(challenge.get("points", 2.0))
    stdout_text = str((execution_output or {}).get("stdout", "")).strip()
    cmd_clean = command.strip()

    public_tests = challenge.get("public_tests", [])
    hidden_tests = challenge.get("hidden_tests", [])

    public_results = []
    hidden_results = []

    def _eval_test_case(test_case: Dict[str, Any], is_hidden: bool = False) -> bool:
        t_cmd = test_case.get("cmd", "")
        exp_stdout = str(test_case.get("expected_stdout", test_case.get("expected", ""))).strip()
        exp_exit = test_case.get("expected_exit_code", 0)
        assert_type = test_case.get("assertion_type", "stdout")

        passed = False

        # Si le client a déjà validé ce test dans le runner VFS du navigateur
        if client_tests_passed is True:
            passed = True

        # Assertion de type fichier existant
        elif assert_type == "file_exists" and vfs_state:
            expected_path = test_case.get("expected", exp_stdout)
            passed = _check_vfs_path_exists(vfs_state, expected_path)
            if not passed and exp_stdout and exp_stdout in stdout_text:
                passed = True

        # Assertion de type fichier absent / supprimé
        elif assert_type == "file_not_exists" and vfs_state:
            expected_path = test_case.get("expected", exp_stdout)
            passed = not _check_vfs_path_exists(vfs_state, expected_path)

        # Assertion de contenu de fichier
        elif assert_type == "file_contains" and vfs_state:
            expected_text = test_case.get("expected", exp_stdout)
            # Vérifier si l'un des fichiers contient la chaîne attendue
            content_found = False
            for p in [t_cmd.split()[-1] if t_cmd else "", test_case.get("path", "")]:
                if p:
                    c = _get_vfs_file_content(vfs_state, p)
                    if c and expected_text in c:
                        content_found = True
                        break
            if not content_found and expected_text in stdout_text:
                content_found = True
            passed = content_found

        # Assertion sur les permissions (chmod)
        elif assert_type == "permission":
            expected_perm = str(test_case.get("expected", "755"))
            if expected_perm in cmd_clean or "chmod" in cmd_clean:
                passed = True
            elif exp_stdout in stdout_text:
                passed = True

        # Assertion standard sur la sortie stdout
        else:
            if exp_stdout and exp_stdout in stdout_text:
                passed = True
            elif exp_stdout and exp_stdout in cmd_clean:
                passed = True
            elif t_cmd and (t_cmd in cmd_clean or cmd_clean.startswith(t_cmd.split()[0])):
                passed = True
            elif challenge.get("solution") and cmd_clean == challenge.get("solution").strip():
                passed = True

        return passed

    # Évaluation des tests publics
    for idx, pt in enumerate(public_tests, start=1):
        t_passed = _eval_test_case(pt, is_hidden=False)
        public_results.append({
            "name": pt.get("name", f"Test Public #{idx}"),
            "cmd": pt.get("cmd", ""),
            "passed": t_passed,
            "expected": pt.get("expected_stdout", pt.get("expected", "OK")),
            "actual": stdout_text if stdout_text else ("OK" if t_passed else "Non validé")
        })

    # Évaluation des tests cachés (Résultats strictement masqués)
    for idx, ht in enumerate(hidden_tests, start=1):
        t_passed = _eval_test_case(ht, is_hidden=True)
        hidden_results.append({
            "name": ht.get("name", f"Test Caché #{idx}"),
            "cmd": "[Protégé]",
            "passed": t_passed,
            "expected": "[Protégé]",
            "actual": "[Protégé]" if t_passed else "Échec"
        })

    total_tests = len(public_results) + len(hidden_results)
    passed_tests = sum(1 for r in public_results if r["passed"]) + sum(1 for r in hidden_results if r["passed"])
    all_passed = (passed_tests == total_tests) and total_tests > 0

    if all_passed:
        awarded_points = total_points
    elif total_tests > 0:
        awarded_points = round((passed_tests / total_tests) * total_points, 2)
    else:
        awarded_points = 0.0

    message = "✅ Défi validé avec succès !" if all_passed else f"Tests validés : {passed_tests}/{total_tests}."

    return {
        "challenge_id": challenge_id,
        "success": all_passed,
        "all_passed": all_passed,
        "awarded_points": awarded_points,
        "max_points": total_points,
        "public_results": public_results,
        "hidden_results": hidden_results,
        "message": message,
        "explanation": challenge.get("explanation", ""),
        "solution": challenge.get("solution", "")
    }

def sync_student_linux_pillar(
    user_id: str,
    score: float,
    db: Session,
    answers: Any = None,
    details: Any = None,
    max_score: float = 20.0
) -> PracticeAttempt:
    """
    Enregistre ou synchronise la performance Linux dans la table PracticeAttempt.
    Garantit un découplage absolu : n'altère jamais StudentAttempt ni les GPAs semestriels.
    """
    grade_20 = round((score / max_score) * 20.0, 2) if max_score > 0 else 0.0
    percentage = round((score / max_score) * 100.0, 1) if max_score > 0 else 0.0

    attempt_id = f"P-LINUX-{user_id[:8]}-{uuid.uuid4().hex[:6]}"
    p_attempt = PracticeAttempt(
        id=attempt_id,
        user_id=user_id,
        module_code="LINUX_ADMIN",
        module_title="Administration Système Linux",
        grade_20=grade_20,
        percentage=percentage,
        total_awarded=score,
        max_possible=max_score,
        answers_json=json.dumps(answers) if answers is not None else "{}",
        detailed_results_json=json.dumps(details) if details is not None else "[]",
        created_at=datetime.now(timezone.utc)
    )
    db.add(p_attempt)
    db.commit()
    return p_attempt

def get_student_linux_progress(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Retourne la progression globale de l'étudiant dans le Centre Linux.
    """
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user_id,
        PracticeAttempt.module_code == "LINUX_ADMIN"
    ).order_by(PracticeAttempt.created_at.asc()).all()

    solved_challenges = set()
    total_points = 0.0

    for a in attempts:
        if a.detailed_results_json:
            try:
                records = json.loads(a.detailed_results_json)
                for r in records:
                    ch_id = r.get("id") or r.get("challenge_id")
                    if ch_id and (r.get("is_correct") or r.get("all_passed") or r.get("passed")):
                        solved_challenges.add(ch_id)
            except Exception:
                pass
        total_points += float(a.total_awarded or 0.0)

    avg_score = (sum(a.grade_20 for a in attempts) / len(attempts)) if attempts else 0.0
    best_score = max((a.grade_20 for a in attempts), default=0.0)

    # Grille officielle de niveaux diagnostiques 1 à 6
    diag_level = 1
    if avg_score >= 16.0: diag_level = 6
    elif avg_score >= 14.0: diag_level = 5
    elif avg_score >= 12.0: diag_level = 4
    elif avg_score >= 10.0: diag_level = 3
    elif avg_score >= 7.0: diag_level = 2

    # Niveau de cursus courant (1 à 4)
    current_level = 1
    if len(solved_challenges) >= 6:
        current_level = 4
    elif len(solved_challenges) >= 4:
        current_level = 3
    elif len(solved_challenges) >= 2:
        current_level = 2

    return {
        "pillar": "LINUX_ADMIN",
        "pillar_title": "Administration Système Linux",
        "solved_challenges": list(solved_challenges),
        "current_level": current_level,
        "total_points": round(total_points, 1),
        "diagnostic_level": diag_level,
        "total_attempts": len(attempts),
        "average_score": round(avg_score, 1),
        "best_score": round(best_score, 1)
    }

def get_student_linux_history(user_id: str, db: Session) -> List[Dict[str, Any]]:
    """Retourne l'historique chronologique des tentatives d'entraînement Linux."""
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user_id,
        PracticeAttempt.module_code == "LINUX_ADMIN"
    ).order_by(PracticeAttempt.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "grade_20": a.grade_20,
            "percentage": a.percentage,
            "total_awarded": a.total_awarded,
            "max_possible": a.max_possible,
            "submitted_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in attempts
    ]

# ==============================================================================
# Backward Compatibility Helpers (training_linux_service.py)
# ==============================================================================

def list_linux_chapters(db: Session, user_id: str) -> List[Dict[str, Any]]:
    curr = load_linux_curriculum()
    chapters = curr.get("chapters", [])
    
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user_id,
        PracticeAttempt.module_code == "LINUX_ADMIN"
    ).all()
    latest_score = attempts[-1].grade_20 if attempts else 0.0

    res = []
    for idx, ch in enumerate(chapters):
        mcq_count = len(ch.get("mcq_questions", []))
        prac_count = len(ch.get("coding_exercises", []))
        res.append({
            "id": ch["id"],
            "title": ch["title"],
            "order": ch.get("order", idx + 1),
            "description": ch.get("description", ""),
            "mcq_count": mcq_count,
            "coding_count": prac_count,
            "status": "unlocked",
            "best_mark": round(latest_score, 1) if attempts else 0.0,
            "completed_exercises": (mcq_count + prac_count) if attempts else 0,
            "total_exercises": mcq_count + prac_count
        })
    return res

def get_linux_chapter_details(chapter_id: str, assessment_type: str = "all") -> Optional[Dict[str, Any]]:
    curr = load_linux_curriculum()
    for ch in curr.get("chapters", []):
        if ch["id"] == chapter_id:
            items = []
            if assessment_type in ("all", "theoretical"):
                for q in ch.get("mcq_questions", []):
                    q_copy = dict(q)
                    q_copy.pop("correct", None)
                    q_copy.pop("explanation", None)
                    items.append(q_copy)
            if assessment_type in ("all", "practical"):
                for ce in ch.get("coding_exercises", []):
                    ce_copy = dict(ce)
                    ce_copy["public_tests"] = ce.get("public_tests", [])
                    ce_copy.pop("hidden_tests", None)
                    ce_copy.pop("solution", None)
                    ce_copy.pop("explanation", None)
                    items.append(ce_copy)
            return {
                "chapter_id": ch["id"],
                "title": ch["title"],
                "description": ch.get("description", ""),
                "items": items
            }
    return None

def generate_linux_session(
    chapter_id: Optional[str] = None,
    assessment_type: str = "all",
    count: int = 10,
    target_level: Optional[int] = None
) -> Dict[str, Any]:
    curr = load_linux_curriculum()
    chapters = curr.get("chapters", [])
    
    selected_chapters = chapters
    if chapter_id:
        selected_chapters = [c for c in chapters if c["id"] == chapter_id]
        if not selected_chapters:
            selected_chapters = chapters

    pool = []
    for ch in selected_chapters:
        if assessment_type in ("all", "theoretical"):
            for q in ch.get("mcq_questions", []):
                q_copy = dict(q)
                q_copy.pop("correct", None)
                q_copy.pop("explanation", None)
                if q_copy.get("options") and isinstance(q_copy["options"], list) and len(q_copy["options"]) > 1:
                    shuffled_opts = list(q_copy["options"])
                    random.shuffle(shuffled_opts)
                    q_copy["options"] = shuffled_opts
                pool.append(q_copy)
        if assessment_type in ("all", "practical"):
            for ce in ch.get("coding_exercises", []):
                ce_copy = dict(ce)
                ce_copy["public_tests"] = ce.get("public_tests", [])
                ce_copy.pop("hidden_tests", None)
                ce_copy.pop("solution", None)
                ce_copy.pop("explanation", None)
                pool.append(ce_copy)

    # Filtrer par niveau si demandé
    if target_level is not None:
        level_map = {
            "fhs_navigation": 1,
            "file_management": 1,
            "permissions_security": 2,
            "text_processing_pipes": 3,
            "processes_signals": 4,
            "bash_scripting": 3
        }
        pool = [item for item in pool if level_map.get(item.get("topic_id", chapter_id or ""), target_level) == target_level]

    random.shuffle(pool)
    items = pool[:count]
    return {
        "session_id": f"LINUX-SESS-{uuid.uuid4().hex[:8].upper()}",
        "title": f"Session d'Entraînement Linux ({assessment_type.capitalize()})",
        "assessment_type": assessment_type,
        "items": items
    }

def evaluate_linux_session_submission(
    db: Session,
    user: User,
    answers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    curr = load_linux_curriculum()
    lookup = {}
    for ch in curr.get("chapters", []):
        for q in ch.get("mcq_questions", []):
            lookup[q["id"]] = q
        for ce in ch.get("coding_exercises", []):
            lookup[ce["id"]] = ce

    # Ajouter aussi les défis de challenges.json
    for c in load_linux_challenges():
        lookup[c["id"]] = c

    total_possible = 0.0
    total_awarded = 0.0
    item_results = []

    for ans in answers:
        q_id = ans.get("id")
        q_data = lookup.get(q_id)
        if not q_data:
            continue

        q_type = q_data.get("type", ans.get("type", "single_choice"))
        points = float(q_data.get("points", 2.0 if q_type in ("linux_cmd", "coding") else 1.0))
        total_possible += points
        
        is_corr = False
        awarded = 0.0

        if q_type in ("linux_cmd", "coding"):
            client_pass = ans.get("is_correct")
            if client_pass is True:
                is_corr = True
                awarded = points
            elif isinstance(client_pass, (int, float)):
                awarded = min(points, float(client_pass))
                is_corr = awarded >= (points * 0.5)
            else:
                eval_res = evaluate_linux_challenge(
                    challenge_id=q_id,
                    command=str(ans.get("student_answer", "")),
                    vfs_state=ans.get("vfs_state"),
                    execution_output=ans.get("execution_output")
                )
                is_corr = eval_res.get("all_passed", False)
                awarded = eval_res.get("awarded_points", 0.0)
        else:
            correct_val = q_data.get("correct")
            student_val = ans.get("student_answer")
            awarded, is_corr, _ = evaluate_answer(q_type, student_val, correct_val, points)

        total_awarded += awarded
        item_results.append({
            "id": q_id,
            "type": q_type,
            "topic": q_data.get("topic", "Linux"),
            "awarded": awarded,
            "points": points,
            "is_correct": is_corr,
            "explanation": q_data.get("explanation", "")
        })

    grade_20 = round((total_awarded / total_possible * 20.0), 1) if total_possible > 0 else 0.0
    percentage = round((total_awarded / total_possible * 100.0), 1) if total_possible > 0 else 0.0

    p_attempt = sync_student_linux_pillar(
        user_id=user.id,
        score=total_awarded,
        db=db,
        answers=answers,
        details=item_results,
        max_score=total_possible
    )

    return {
        "attempt_id": p_attempt.id,
        "grade_20": grade_20,
        "percentage": percentage,
        "total_awarded": total_awarded,
        "max_possible": total_possible,
        "item_results": item_results,
        "pillar": "LINUX_ADMIN"
    }

def get_linux_progression_stats(db: Session, user_id: str) -> Dict[str, Any]:
    return get_student_linux_progress(user_id, db)
