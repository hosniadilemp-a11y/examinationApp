import json
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import (
    Exam, Question, ExamSession, StudentAttempt, 
    StudentAnswer, User, AuditLog, Module, TrainingAttempt, PracticeAttempt
)
from backend.app.schemas import QuestionStudentView
from backend.app.services.grading import evaluate_answer
from backend.app.services.training_service import get_level, get_level_title
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/api/student", tags=["Interface d'Examen Étudiant"])

@router.get("/exams/available")
def get_available_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des examens officiels disponibles pour le groupe de l'étudiant.
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Réservé aux étudiants.")
        
    if not current_user.group_id:
        return []

    # Examens affectés au groupe de l'étudiant
    exams = db.query(Exam).filter(Exam.groups.any(id=current_user.group_id)).all()
    results = []

    for ex in exams:
        # Vérifier si une session active en salle existe pour cet examen
        active_session = db.query(ExamSession).filter(
            ExamSession.exam_id == ex.id,
            ExamSession.status.in_(["waiting", "in_progress"])
        ).order_by(ExamSession.started_at.desc()).first()

        # Vérifier si l'étudiant a déjà une tentative
        attempt = None
        if active_session:
            attempt = db.query(StudentAttempt).filter(
                StudentAttempt.session_id == active_session.id,
                StudentAttempt.student_id == current_user.id
            ).first()
        if not attempt:
            attempt = db.query(StudentAttempt).join(ExamSession).filter(
                ExamSession.exam_id == ex.id,
                StudentAttempt.student_id == current_user.id
            ).order_by(StudentAttempt.started_at.desc()).first()

        results.append({
            "exam_id": ex.id,
            "title": ex.title,
            "module_code": ex.module_code,
            "instructions": ex.instructions,
            "duration_minutes": ex.duration_minutes,
            "global_points": ex.global_points,
            "question_count": len(ex.questions),
            "session_id": active_session.id if active_session else None,
            "session_status": active_session.status if active_session else "no_active_session",
            "attempt_status": attempt.status if attempt else "not_started",
            "final_mark": attempt.final_mark if attempt else None,
            "raw_score": attempt.raw_score if attempt else None
        })

    return results

@router.post("/exams/{exam_id}/start")
def start_or_resume_exam(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Démarre ou reprend une épreuve officielle pour l'étudiant connecté.
    Garantit le secret des réponses et le brassage (Dual Shuffling).
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Réservé aux étudiants.")

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examen introuvable.")

    # Vérification d'affectation au groupe
    if not current_user.group_id or not any(g.id == current_user.group_id for g in exam.groups):
        raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à passer cet examen (groupe non affecté).")

    # Si l'étudiant a déjà une tentative pour cet examen, réutiliser sa session
    existing_attempt = db.query(StudentAttempt).join(ExamSession).filter(
        ExamSession.exam_id == exam.id,
        StudentAttempt.student_id == current_user.id
    ).order_by(StudentAttempt.started_at.desc()).first()

    if existing_attempt:
        session = existing_attempt.session
    else:
        # Recherche de la session de salle active (priorité à in_progress puis waiting)
        session = db.query(ExamSession).filter(
            ExamSession.exam_id == exam.id,
            ExamSession.status == "in_progress"
        ).first()
        if not session:
            session = db.query(ExamSession).filter(
                ExamSession.exam_id == exam.id,
                ExamSession.status == "waiting"
            ).first()

    # Si aucune session n'est encore créée, en générer une automatique pour la salle locale
    if not session:
        session = ExamSession(
            id=f"SESS-{uuid.uuid4().hex[:8].upper()}",
            exam_id=exam.id,
            room_id="SALLE-LOCALE",
            status="in_progress",
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Recherche d'une tentative existante (reprise après crash / rafraîchissement)
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.session_id == session.id,
        StudentAttempt.student_id == current_user.id
    ).first()

    now = datetime.now(timezone.utc)

    # REV-25 : Si la session de salle est en attente du lancement par l'enseignant
    if session.status == "waiting":
        if not attempt:
            attempt = StudentAttempt(
                id=f"ATT-{uuid.uuid4().hex[:8].upper()}",
                session_id=session.id,
                student_id=current_user.id,
                status="waiting",
                suspension_count=0
            )
            db.add(attempt)
            db.commit()
            db.refresh(attempt)

        return {
            "status": "waiting",
            "session_id": session.id,
            "session_status": "waiting",
            "attempt_id": attempt.id,
            "attempt_status": "waiting",
            "exam_title": exam.title,
            "module_code": exam.module_code,
            "duration_minutes": exam.duration_minutes,
            "room_id": session.room_id,
            "message": "Veuillez patienter dans la salle d'attente. L'épreuve démarrera dès que l'enseignant aura validé le départ pour la salle."
        }

    if not attempt:
        # Création d'une nouvelle tentative
        attempt = StudentAttempt(
            id=f"ATT-{uuid.uuid4().hex[:8].upper()}",
            session_id=session.id,
            student_id=current_user.id,
            status="in_progress",
            started_at=now,
            suspension_count=0
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        
        db.add(AuditLog(
            session_id=session.id,
            student_id=current_user.id,
            event_type="EXAM_STARTED",
            details_json=f'{{"exam_id": "{exam.id}", "attempt_id": "{attempt.id}"}}'
        ))
        db.commit()

    elif attempt.status == "submitted" or attempt.status == "timed_out":
        raise HTTPException(status_code=400, detail="Vous avez déjà soumis cet examen. Nouvelle tentative interdite.")

    # Calcul du temps restant (en secondes)
    total_seconds = exam.duration_minutes * 60
    # On calcule l'écart avec started_at
    start_time = attempt.started_at or now
    # Rendre start_time timezone-aware si nécessaire
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    elapsed_seconds = int((now - start_time).total_seconds())
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    # Récupération des questions de l'examen
    questions = list(exam.questions)

    # Double Brassage (Dual Shuffling) déterministe basé sur l'identifiant de l'étudiant
    # pour garantir la stabilité de l'ordre en cas de rafraîchissement !
    rng = random.Random(f"{attempt.id}-{current_user.id}")

    if exam.shuffle_questions:
        rng.shuffle(questions)

    student_questions = []
    for idx, q in enumerate(questions, start=1):
        opts = json.loads(q.options_json) if isinstance(q.options_json, str) else q.options_json

        # Brassage des options QCM
        if exam.shuffle_options and q.type in ["single_choice", "multi_choice"] and isinstance(opts, list):
            shuffled_opts = list(opts)
            rng.shuffle(shuffled_opts)
            opts = shuffled_opts

        student_questions.append({
            "id": q.id,
            "display_order": idx,
            "type": q.type,
            "prompt_markdown": q.prompt_markdown,
            "points": q.points,
            "negative_penalty": q.negative_penalty,
            "time_limit_seconds": q.time_limit_seconds,
            "options": opts
            # SECRET ABSOLU : correct_answers_json n'est JAMAIS inclus !
        })

    # Récupération des réponses déjà saisies (reprise fluide)
    saved_answers = db.query(StudentAnswer).filter(StudentAnswer.attempt_id == attempt.id).all()
    answers_map = {a.question_id: json.loads(a.answer_payload_json) for a in saved_answers}

    return {
        "attempt_id": attempt.id,
        "session_id": session.id,
        "session_status": session.status,
        "attempt_status": attempt.status,
        "suspension_reason": attempt.suspension_reason,
        "exam_title": exam.title,
        "module_code": exam.module_code,
        "duration_minutes": exam.duration_minutes,
        "remaining_seconds": remaining_seconds,
        "total_questions": len(student_questions),
        "questions": student_questions,
        "saved_answers": answers_map
    }

@router.post("/attempts/{attempt_id}/save-answer")
def save_student_answer(
    attempt_id: str,
    payload: Dict[str, Any],  # {"question_id": "Q-1", "answer": ...}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-sauvegarde en temps réel d'une réponse d'étudiant."""
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    if attempt.status == "suspended":
        raise HTTPException(status_code=403, detail="Votre épreuve est suspendue. Déblocage surveillant requis.")

    if attempt.status in ["submitted", "timed_out"]:
        raise HTTPException(status_code=400, detail="Épreuve déjà soumise.")

    question_id = payload.get("question_id")
    answer_data = payload.get("answer")

    if not question_id:
        raise HTTPException(status_code=400, detail="question_id obligatoire.")

    # Vérification que la question appartient bien à l'examen de cette session
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question or question.exam_id != attempt.session.exam_id:
        raise HTTPException(status_code=400, detail="Question invalide pour cette épreuve.")

    # Enregistrement ou mise à jour de la réponse
    answer_record = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id == attempt.id,
        StudentAnswer.question_id == question_id
    ).first()

    payload_str = json.dumps(answer_data)

    if answer_record:
        answer_record.answer_payload_json = payload_str
    else:
        answer_record = StudentAnswer(
            attempt_id=attempt.id,
            question_id=question_id,
            answer_payload_json=payload_str
        )
        db.add(answer_record)

    db.commit()

    # Calcul authoritaire du temps restant côté serveur (REV-28)
    now = datetime.now(timezone.utc)
    exam = attempt.session.exam
    start_time = attempt.started_at or now
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    total_seconds = exam.duration_minutes * 60 if exam else 3600
    elapsed_seconds = int((now - start_time).total_seconds())
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    return {
        "success": True, 
        "saved_at": now.isoformat(),
        "remaining_seconds": remaining_seconds
    }

@router.post("/attempts/{attempt_id}/security-event")
def report_security_event(
    attempt_id: str,
    payload: Dict[str, Any],  # {"event_type": "AWAY_10S" | "FULLSCREEN_EXIT" | "BLUR", "details": ...}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Signale un événement de sécurité (ex: sortie de plein écran, absence >10s).
    Si l'absence dépasse 10 secondes, suspend automatiquement l'épreuve.
    """
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    event_type = payload.get("event_type", "SECURITY_ALERT")
    details = payload.get("details", {})

    # Règle des 10 secondes d'absence : déclenche la suspension automatique
    is_suspended = False
    if event_type == "AWAY_10S" or details.get("duration_seconds", 0) >= 10:
        attempt.status = "suspended"
        attempt.suspension_count += 1
        attempt.suspension_reason = "Sortie de plein écran ou changement d'onglet (>10 secondes)"
        is_suspended = True

    db.add(AuditLog(
        session_id=attempt.session_id,
        student_id=current_user.id,
        event_type=event_type,
        details_json=json.dumps(details)
    ))
    db.commit()

    return {
        "status": attempt.status,
        "is_suspended": is_suspended,
        "suspension_count": attempt.suspension_count,
        "message": "Épreuve suspendue. Contactez votre surveillant pour déblocage." if is_suspended else "Alerte de sécurité enregistrée."
    }

@router.get("/attempts/{attempt_id}/status")
def check_attempt_status(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permet au client étudiant de vérifier en temps réel si le surveillant a levé la suspension."""
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    now = datetime.now(timezone.utc)
    exam = attempt.session.exam if attempt.session else None
    start_time = attempt.started_at or now
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    total_seconds = exam.duration_minutes * 60 if exam else 3600
    elapsed_seconds = int((now - start_time).total_seconds())
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    return {
        "status": attempt.status,
        "session_status": attempt.session.status if attempt.session else "unknown",
        "suspension_reason": attempt.suspension_reason,
        "suspension_count": attempt.suspension_count,
        "remaining_seconds": remaining_seconds,
        "final_mark": attempt.final_mark,
        "raw_score": attempt.raw_score
    }

@router.post("/attempts/{attempt_id}/submit")
def submit_official_exam(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soumission finale de l'examen par l'étudiant.
    Calcule immédiatement le score officiel et retourne la note sur 20.
    """
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    if attempt.status in ["submitted", "timed_out"]:
        return {
            "status": attempt.status,
            "raw_score": attempt.raw_score,
            "final_mark": attempt.final_mark,
            "message": "Cet examen a déjà été soumis."
        }

    exam = attempt.session.exam
    questions = exam.questions
    answers = {a.question_id: a for a in attempt.answers}

    total_awarded = 0.0
    total_possible = 0.0

    for q in questions:
        total_possible += q.points
        ans_record = answers.get(q.id)
        user_ans = json.loads(ans_record.answer_payload_json) if ans_record else None
        correct_ans = json.loads(q.correct_answers_json) if isinstance(q.correct_answers_json, str) else q.correct_answers_json

        awarded, is_corr, _ = evaluate_answer(
            q_type=q.type,
            user_answer=user_ans,
            correct_answers=correct_ans,
            points=q.points,
            negative_penalty=q.negative_penalty,
            floor_score=0.0
        )

        total_awarded += awarded

        # Mise à jour de l'enregistrement de réponse
        if ans_record:
            ans_record.is_correct = is_corr
            ans_record.awarded_points = awarded

    # Calcul de la note finale sur le barème global de l'examen (par défaut 20.0)
    final_mark = 0.0
    if total_possible > 0:
        final_mark = round((total_awarded / total_possible) * exam.global_points, 2)

    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.raw_score = round(total_awarded, 2)
    attempt.final_mark = final_mark

    db.add(AuditLog(
        session_id=attempt.session_id,
        student_id=current_user.id,
        event_type="EXAM_SUBMITTED",
        details_json=f'{{"final_mark": {final_mark}, "raw_score": {total_awarded}}}'
    ))
    db.commit()

    return {
        "status": "submitted",
        "raw_score": attempt.raw_score,
        "max_score": total_possible,
        "final_mark": attempt.final_mark,
        "global_points": exam.global_points,
        "submitted_at": attempt.submitted_at.isoformat(),
        "message": f"Votre épreuve a été enregistrée avec succès. Note obtenue : {final_mark} / {exam.global_points}"
    }

# --- Action d'administration : Déblocage Surveillant (1-Clic) ---

@router.post("/attempts/{attempt_id}/unlock")
def unlock_suspended_attempt(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permet à l'enseignant ou à l'administrateur de débloquer en 1 clic un étudiant suspendu.
    """
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Réservé aux enseignants et administrateurs.")

    attempt = db.query(StudentAttempt).filter(StudentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    if attempt.status != "suspended":
        return {"success": True, "status": attempt.status, "message": "L'étudiant n'est pas suspendu."}

    attempt.status = "in_progress"
    attempt.suspension_reason = None

    db.add(AuditLog(
        session_id=attempt.session_id,
        student_id=attempt.student_id,
        event_type="UNLOCKED",
        details_json=f'{{"unlocked_by": "{current_user.username}"}}'
    ))
    db.commit()

    return {
        "success": True,
        "status": "in_progress",
        "message": f"L'épreuve de l'étudiant {attempt.student.full_name} a été débloquée avec succès."
    }

@router.get("/statistics")
def get_student_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne la synthèse et les statistiques complètes de l'étudiant :
    - Moyenne générale (/20), taux de réussite et nombre d'épreuves
    - Niveau calculé sur les 4 modules fondamentaux (ALGO, PYTHON_INIT, CRYPTO, LINUX_ADMIN)
    - Tableau détaillé par module avec notes moyennes, meilleures notes et statuts d'acquisition
    - Courbe d'évolution chronologique des notes
    """
    fundamental_codes = ["ALGO", "PYTHON_INIT", "CRYPTO", "LINUX_ADMIN"]
    all_modules = db.query(Module).all()

    # Récupération des épreuves officielles soumises par l'étudiant
    official_attempts = db.query(StudentAttempt).join(ExamSession).join(Exam).filter(
        StudentAttempt.student_id == current_user.id,
        StudentAttempt.status == "submitted"
    ).order_by(StudentAttempt.submitted_at.asc()).all()

    # Récupération des entraînements de l'étudiant
    training_attempts = db.query(TrainingAttempt).filter(
        TrainingAttempt.user_id == current_user.id
    ).order_by(TrainingAttempt.created_at.asc()).all()

    # Récupération de tous les tests de niveau fondamentaux
    practice_attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == current_user.id
    ).order_by(PracticeAttempt.created_at.asc()).all()

    # Statistiques par module
    fundamental_definitions = {
        "ALGO": "Algorithmique & Structures de Données",
        "PYTHON_INIT": "Python & Programmation Fondamentale",
        "CRYPTO": "Cryptographie & Sécurité des Données",
        "LINUX_ADMIN": "Administration Systèmes & Réseaux Linux"
    }

    # Créer un dictionnaire de modules pour s'assurer que les 4 fondamentaux sont toujours présents
    modules_map = {m.code: {"code": m.code, "title": m.title} for m in all_modules}
    for f_code, f_title in fundamental_definitions.items():
        if f_code not in modules_map:
            modules_map[f_code] = {"code": f_code, "title": f_title}

    modules_stats = []
    fundamental_best_marks = {}

    for code, m_info in modules_map.items():
        m_official = [a.final_mark for a in official_attempts if a.session and a.session.exam and a.session.exam.module_code == code and a.final_mark is not None]
        m_practice = [p.grade_20 for p in practice_attempts if p.module_code == code and p.grade_20 is not None]
        m_training = []
        if code == "PYTHON_INIT":
            m_training = [t.final_mark for t in training_attempts if t.final_mark is not None]

        all_m_marks = m_official + m_practice + m_training
        best_mark = max(all_m_marks) if all_m_marks else 0.0
        avg_mark = round(sum(all_m_marks) / len(all_m_marks), 2) if all_m_marks else 0.0

        if code in fundamental_codes:
            fundamental_best_marks[code] = best_mark

        mastery = "Non commencé"
        if len(all_m_marks) > 0:
            if best_mark < 7.0: mastery = "En découverte"
            elif best_mark < 10.0: mastery = "En progression"
            elif best_mark < 14.0: mastery = "Compétence acquise"
            elif best_mark < 17.0: mastery = "Niveau Avancé"
            else: mastery = "Maîtrise Experte"

        modules_stats.append({
            "code": code,
            "title": m_info["title"],
            "is_fundamental": code in fundamental_codes,
            "best_mark": round(best_mark, 2),
            "average_mark": avg_mark,
            "attempts_count": len(all_m_marks),
            "passed": best_mark >= 10.0,
            "mastery_level": mastery
        })

    # Calcul du niveau global sur les 4 modules fondamentaux selon les 4 dernières tentatives
    from backend.app.routers.practice import _compute_module_stats
    p_stats = _compute_module_stats(current_user.id, db)
    fund_average = p_stats["overall_last_4_average"]
    global_level = p_stats["overall_level"]
    global_level_title = p_stats["overall_level_title"]

    # Historique chronologique global de TOUTES les évaluations (Officielles + Tests de Niveau + Labs)
    timeline = []
    for a in official_attempts:
        if a.final_mark is not None:
            m_title = a.session.exam.title if a.session and a.session.exam else "Examen"
            timeline.append({
                "type": "officiel",
                "title": m_title,
                "module_code": a.session.exam.module_code if a.session and a.session.exam else "",
                "mark": a.final_mark,
                "date": a.submitted_at.strftime("%d/%m/%Y %H:%M") if a.submitted_at else ""
            })
    for p in practice_attempts:
        if p.grade_20 is not None:
            timeline.append({
                "type": "test_niveau",
                "title": f"Test de Niveau : {p.module_title}",
                "module_code": p.module_code,
                "mark": p.grade_20,
                "date": p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else ""
            })
    for t in training_attempts:
        if t.final_mark is not None:
            timeline.append({
                "type": "test_niveau",
                "title": f"Entraînement Python ({t.assessment_type})",
                "module_code": "PYTHON_INIT",
                "mark": t.final_mark,
                "date": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else ""
            })

    all_final_marks = [item["mark"] for item in timeline]
    overall_avg = round(sum(all_final_marks) / len(all_final_marks), 2) if all_final_marks else 0.0
    success_rate = round(len([m for m in all_final_marks if m >= 10.0]) / len(all_final_marks) * 100, 1) if all_final_marks else 0.0

    return {
        "student_name": current_user.full_name,
        "group_id": current_user.group_id or "Sans groupe",
        "global_level": global_level,
        "global_level_title": global_level_title,
        "fundamental_average": fund_average,
        "overall_average": overall_avg,
        "total_evaluations_count": len(timeline),
        "success_rate_percent": success_rate,
        "validated_modules_count": sum(1 for m in modules_stats if m["passed"]),
        "total_modules_count": len(modules_stats),
        "modules_breakdown": modules_stats,
        "recent_timeline": timeline[-10:]
    }

@router.get("/bulletin")
def get_my_bulletin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permet à l'étudiant connecté de consulter son propre bulletin académique officiel."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Réservé aux étudiants.")
    from backend.app.routers.admin import _build_student_bulletin
    return _build_student_bulletin(current_user, db)

@router.get("/bulletin/export-pdf")
def export_my_bulletin_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permet à l'étudiant de télécharger son bulletin officiel en PDF."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Réservé aux étudiants.")
    from backend.app.routers.admin import _build_student_bulletin
    from backend.app.services.document_export import generate_student_bulletin_pdf
    b = _build_student_bulletin(current_user, db)
    pdf_bytes = generate_student_bulletin_pdf(b)
    filename = f"bulletin_officiel_{current_user.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/bulletin/export-docx")
def export_my_bulletin_docx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permet à l'étudiant de télécharger son bulletin officiel au format Word (.docx)."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Réservé aux étudiants.")
    from backend.app.routers.admin import _build_student_bulletin
    from backend.app.services.document_export import generate_student_bulletin_docx
    b = _build_student_bulletin(current_user, db)
    docx_bytes = generate_student_bulletin_docx(b)
    filename = f"bulletin_officiel_{current_user.id}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



