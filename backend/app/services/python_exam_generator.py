"""
Service de génération automatisée d'épreuves officielles Python.
Permet d'extraire des questions de la banque d'exercices du Centre d'Entraînement Python :
- Volet Théorique : Sélection de 30 questions (priorité aux questions marquées Exams=True, complétées si besoin),
  avec distribution aléatoire de 20 questions par étudiant lors de l'épreuve.
- Volet Pratique : Sélection de 10 défis (priorité aux défis marqués is_exam=True, complétés si besoin),
  avec distribution aléatoire de 5 défis par étudiant lors de l'épreuve.
"""

import os
import json
import random
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models import Exam, Question, Group, Module

CURRICULUM_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "python_training", "curriculum.json"
)
CODING_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "python_training", "coding_challenges.json"
)

def _load_curriculum_data() -> Dict[str, Any]:
    if not os.path.exists(CURRICULUM_PATH):
        return {"chapters": []}
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_coding_challenges() -> List[Dict[str, Any]]:
    if not os.path.exists(CODING_PATH):
        return []
    with open(CODING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_python_bank_stats() -> Dict[str, Any]:
    """
    Retourne la synthèse détaillée des questions disponibles dans la base de données :
    - Répartition des QCM par chapitre et par difficulté (Facile, Moyen, Difficile, Très Difficile)
    - Compteur des questions explicitement marquées pour examen (Exams=True)
    - Répartition des défis de code pratiques
    """
    curr = _load_curriculum_data()
    coding = _load_coding_challenges()

    chapters_stats = []
    total_mcqs = 0
    total_mcqs_exam = 0
    diff_totals_mcq = {"easy": 0, "medium": 0, "hard": 0, "very hard": 0}

    for ch in curr.get("chapters", []):
        ch_id = ch.get("id")
        ch_title = ch.get("title", ch_id)
        mcqs = ch.get("mcq_questions", [])
        ch_diffs = {"easy": 0, "medium": 0, "hard": 0, "very hard": 0}
        ch_exam_count = 0

        for q in mcqs:
            total_mcqs += 1
            d = q.get("difficulty", "medium").lower()
            if d not in ch_diffs:
                d = "medium"
            ch_diffs[d] += 1
            diff_totals_mcq[d] += 1
            if q.get("Exams") or q.get("is_exam"):
                ch_exam_count += 1
                total_mcqs_exam += 1

        chapters_stats.append({
            "chapter_id": ch_id,
            "title": ch_title,
            "total_questions": len(mcqs),
            "difficulties": ch_diffs,
            "exam_marked_count": ch_exam_count
        })

    # Statistiques des défis pratiques
    coding_stats = {
        "total_challenges": len(coding),
        "exam_marked_count": sum(1 for c in coding if c.get("is_exam") or c.get("Exams")),
        "difficulties": {"easy": 0, "medium": 0, "hard": 0, "very hard": 0},
        "by_topic": {}
    }

    for c in coding:
        d = c.get("difficulty", "medium").lower()
        if d not in coding_stats["difficulties"]:
            d = "medium"
        coding_stats["difficulties"][d] += 1

        topic = c.get("topic", "Général")
        if topic not in coding_stats["by_topic"]:
            coding_stats["by_topic"][topic] = {"total": 0, "exam_marked": 0}
        coding_stats["by_topic"][topic]["total"] += 1
        if c.get("is_exam") or c.get("Exams"):
            coding_stats["by_topic"][topic]["exam_marked"] += 1

    return {
        "theoretical": {
            "total_mcqs": total_mcqs,
            "total_exam_marked": total_mcqs_exam,
            "difficulties": diff_totals_mcq,
            "chapters": chapters_stats
        },
        "practical": coding_stats
    }

def generate_python_exam(
    db: Session,
    title: str,
    exam_type: str = "theoretical",
    duration_minutes: int = 45,
    chapter_ids: Optional[List[str]] = None,
    difficulty_counts: Optional[Dict[str, int]] = None,
    assigned_groups: Optional[List[str]] = None,
    created_by: Optional[str] = None,
    target_count: Optional[int] = None
) -> Exam:
    """
    Génère un examen officiel Python en sélectionnant les questions selon les règles spécifiées :
    - Épreuve Théorique : Sélection de 40 questions par défaut (ou target_count / somme difficulty_counts),
      avec tag autoritaire [CONFIG_RANDOM_STUDENT_QUESTIONS=20] pour que chaque étudiant reçoive 20 questions aléatoires.
    - Épreuve Pratique : Sélection de 10 défis de programmation (priorité à is_exam=True),
      avec tag [CONFIG_RANDOM_STUDENT_QUESTIONS=5] pour que chaque étudiant reçoive 5 défis.
    """
    # Assurer que le module PYTHON_INIT existe
    mod = db.query(Module).filter(Module.code == "PYTHON_INIT").first()
    if not mod:
        mod = Module(code="PYTHON_INIT", title="Programmation Python Fondamentale")
        db.add(mod)
        db.flush()

    exam_id = f"EXAM-PY-{'THEO' if exam_type == 'theoretical' else 'PRAC'}-{uuid.uuid4().hex[:6].upper()}"

    if exam_type == "theoretical":
        requested_by_diff = sum(difficulty_counts.values()) if difficulty_counts else 0
        target_total = target_count if target_count else (requested_by_diff if requested_by_diff > 0 else 40)
        questions_per_student = 20
        tag = f"[CONFIG_RANDOM_STUDENT_QUESTIONS={questions_per_student}]"
        instructions = f"Épreuve Officielle Théorique Python. QCM et questions de compréhension. Tirage au sort de 20 questions parmi {target_total} pour chaque candidat. {tag}"

        curr = _load_curriculum_data()
        all_mcqs = []
        for ch in curr.get("chapters", []):
            if chapter_ids and ch.get("id") not in chapter_ids:
                continue
            for q in ch.get("mcq_questions", []):
                q_copy = dict(q)
                q_copy["chapter_id"] = ch.get("id")
                all_mcqs.append(q_copy)

        # Filtrage / priorisation : questions marquées Exams=True en premier
        exam_flagged = [q for q in all_mcqs if q.get("Exams") or q.get("is_exam")]
        other_questions = [q for q in all_mcqs if not (q.get("Exams") or q.get("is_exam"))]

        # Si des quotas de difficulté sont demandés
        selected_pool = []
        if difficulty_counts:
            for diff, target_count in difficulty_counts.items():
                diff_norm = diff.lower()
                # Priorité aux questions marquées examen
                flagged_for_diff = [q for q in exam_flagged if q.get("difficulty", "medium").lower() == diff_norm]
                other_for_diff = [q for q in other_questions if q.get("difficulty", "medium").lower() == diff_norm]

                random.shuffle(flagged_for_diff)
                random.shuffle(other_for_diff)

                combined_for_diff = flagged_for_diff + other_for_diff
                selected_pool.extend(combined_for_diff[:target_count])

        # Compléter si le quota demandé n'atteint pas 30 ou si difficulty_counts n'est pas fourni
        random.shuffle(exam_flagged)
        random.shuffle(other_questions)
        candidates = exam_flagged + other_questions

        seen_ids = set(q.get("id") for q in selected_pool)
        for c in candidates:
            if len(selected_pool) >= target_total:
                break
            if c.get("id") not in seen_ids:
                selected_pool.append(c)
                seen_ids.add(c.get("id"))

        # Si la base contient moins de 30 questions, prendre le maximum
        final_questions_data = selected_pool[:target_total]

        new_exam = Exam(
            id=exam_id,
            module_code="PYTHON_INIT",
            title=title.strip() if title else "Épreuve Théorique Python (Générée)",
            exam_type="theoretical",
            instructions=instructions,
            duration_minutes=duration_minutes,
            global_points=20.0,
            navigation_mode="free",
            shuffle_questions=True,
            shuffle_options=True,
            partial_credit_enabled=True,
            default_negative_penalty=0.0,
            created_by=created_by
        )
        db.add(new_exam)
        db.flush()

        # Attribution des points par question : 1 point par question pour l'étudiant
        pts_per_q = round(20.0 / questions_per_student, 2)
        for idx, q_data in enumerate(final_questions_data, start=1):
            q_id = f"Q-PY-THEO-{uuid.uuid4().hex[:8].upper()}"
            opts = q_data.get("options", [])
            corr = q_data.get("correct")

            # Normalisation options
            opts_clean = []
            for o in opts:
                if isinstance(o, dict):
                    opts_clean.append(o.get("text", str(o)))
                else:
                    opts_clean.append(str(o))

            new_q = Question(
                id=q_id,
                exam_id=new_exam.id,
                ordering=idx,
                type="single_choice",
                prompt_markdown=q_data.get("text") or q_data.get("prompt") or f"Question Python #{idx}",
                points=pts_per_q,
                negative_penalty=float(q_data.get("penalty") or 0.0),
                options_json=json.dumps(opts_clean),
                correct_answers_json=json.dumps([corr] if isinstance(corr, int) else (corr or [0]))
            )
            db.add(new_q)

    else:
        # Épreuve Pratique
        target_total = 10
        challenges_per_student = 5
        tag = f"[CONFIG_RANDOM_STUDENT_QUESTIONS={challenges_per_student}]"
        instructions = f"Épreuve Officielle Pratique sur Machine Python. Défis d'algorithmique et manipulation de données. Sandbox sécurisé. 5 exercices assignés parmi 10. {tag}"

        all_coding = _load_coding_challenges()
        exam_flagged = [c for c in all_coding if c.get("is_exam") or c.get("Exams")]
        other_challenges = [c for c in all_coding if not (c.get("is_exam") or c.get("Exams"))]

        random.shuffle(exam_flagged)
        random.shuffle(other_challenges)

        # Priorité aux défis marqués is_exam=True, complétés si pas assez
        candidates = exam_flagged + other_challenges
        final_challenges = candidates[:target_total]

        new_exam = Exam(
            id=exam_id,
            module_code="PYTHON_INIT",
            title=title.strip() if title else "Épreuve Pratique Python (Générée)",
            exam_type="practical",
            instructions=instructions,
            duration_minutes=duration_minutes,
            global_points=20.0,
            navigation_mode="free",
            shuffle_questions=True,
            shuffle_options=False,
            partial_credit_enabled=True,
            default_negative_penalty=0.0,
            created_by=created_by
        )
        db.add(new_exam)
        db.flush()

        pts_per_challenge = round(20.0 / challenges_per_student, 2)
        for idx, c_data in enumerate(final_challenges, start=1):
            q_id = f"Q-PY-PRAC-{uuid.uuid4().hex[:8].upper()}"

            # Construction des options et tests
            public_tests = c_data.get("public_tests", [])
            hidden_tests = c_data.get("hidden_tests", [])
            starter_code = c_data.get("starter_code", "# Écrivez votre code Python ici\n")

            options_dict = {
                "starter_code": starter_code,
                "public_tests": public_tests,
                "hints": [c_data.get("hint1"), c_data.get("hint2")] if c_data.get("hint1") else []
            }
            correct_dict = {
                "public_tests": public_tests,
                "hidden_tests": hidden_tests
            }

            desc = c_data.get("description", "")
            title_chal = c_data.get("title", f"Défi #{idx}")
            prompt_md = f"### {title_chal}\n\n{desc}"

            new_q = Question(
                id=q_id,
                exam_id=new_exam.id,
                ordering=idx,
                type="coding",
                prompt_markdown=prompt_md,
                points=pts_per_challenge,
                negative_penalty=0.0,
                options_json=json.dumps(options_dict),
                correct_answers_json=json.dumps(correct_dict)
            )
            db.add(new_q)

    # Assigner les groupes demandés ou tous les groupes par défaut
    if assigned_groups:
        for gid in assigned_groups:
            grp = db.query(Group).filter(Group.id == gid).first()
            if grp and grp not in new_exam.groups:
                new_exam.groups.append(grp)
    else:
        all_groups = db.query(Group).all()
        for grp in all_groups:
            if grp not in new_exam.groups:
                new_exam.groups.append(grp)

    db.commit()
    db.refresh(new_exam)
    return new_exam

