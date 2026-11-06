import json
import uuid
import random
from datetime import datetime, timezone, timedelta
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
from backend.app.services.sandbox_runner import execute_user_code_against_tests, execute_user_code_with_input
from backend.app.services.websocket_manager import ws_manager
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
            "exam_type": getattr(ex, "exam_type", "theoretical") or "theoretical",
            "module_code": ex.module_code,
            "instructions": ex.instructions,
            "duration_minutes": ex.duration_minutes,
            "global_points": ex.global_points,
            "passing_score": getattr(ex, "passing_score", 10.0) or 10.0,
            "question_count": len(ex.questions),
            "total_question_points": round(sum(q.points for q in ex.questions), 2),
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
        # Horloge unique de la salle : alignée sur session.started_at
        unified_start = session.started_at or now
        attempt = StudentAttempt(
            id=f"ATT-{uuid.uuid4().hex[:8].upper()}",
            session_id=session.id,
            student_id=current_user.id,
            status="in_progress",
            started_at=unified_start,
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

    # Calcul du temps restant sur l'horloge unique du serveur (session.started_at ou attempt.started_at si prolongation individuelle)
    total_seconds = exam.duration_minutes * 60
    start_time = attempt.started_at or session.started_at or now
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    elapsed_seconds = int((now - start_time).total_seconds())
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    # Récupération des questions de l'examen
    questions = list(exam.questions)

    # Double Brassage (Dual Shuffling) déterministe basé sur l'identifiant de l'étudiant
    # pour garantir la stabilité de l'ordre en cas de rafraîchissement !
    rng = random.Random(f"{attempt.id}-{current_user.id}")

    # Échantillonnage aléatoire authoritaire par étudiant :
    # - 20 questions parmi 40 (ou 30) pour le volet théorique Python
    # - 5 défis parmi 10 pour le volet pratique Python
    instr = exam.instructions or ""
    if "CONFIG_RANDOM_STUDENT_QUESTIONS=" in instr:
        try:
            target_k = int(instr.split("CONFIG_RANDOM_STUDENT_QUESTIONS=")[1].split("]")[0])
            if 0 < target_k < len(questions):
                questions = rng.sample(questions, target_k)
        except Exception:
            pass
    elif getattr(exam, "exam_type", "") == "theoretical" and "PYTHON" in (exam.module_code or "") and len(questions) > 20:
        questions = rng.sample(questions, 20)
    elif getattr(exam, "exam_type", "") == "practical" and "PYTHON" in (exam.module_code or "") and len(questions) > 5:
        questions = rng.sample(questions, 5)

    # Mélange systématique de l'ordre des questions pour chaque étudiant
    if exam.shuffle_questions or True:
        rng.shuffle(questions)

    student_questions = []
    for idx, q in enumerate(questions, start=1):
        opts = json.loads(q.options_json) if isinstance(q.options_json, str) else q.options_json
        corr_raw = json.loads(q.correct_answers_json) if isinstance(q.correct_answers_json, str) else q.correct_answers_json

        # Normalisation & Brassage des options QCM (single_choice / multi_choice) sans décalage d'indice
        if q.type in ["single_choice", "multi_choice"] and isinstance(opts, list):
            # Déterminer si correct_answers utilise des indices numériques (0, 1, 2...) ou les textes des options
            uses_index = False
            if isinstance(corr_raw, int):
                uses_index = True
            elif isinstance(corr_raw, str) and corr_raw.strip().isdigit():
                uses_index = True
            elif isinstance(corr_raw, list) and len(corr_raw) > 0 and all(isinstance(x, int) or (isinstance(x, str) and x.strip().isdigit()) for x in corr_raw):
                uses_index = True

            normalized_opts = []
            for opt_idx, opt_val in enumerate(opts):
                if isinstance(opt_val, dict) and "id" in opt_val:
                    normalized_opts.append(dict(opt_val))
                else:
                    opt_id = str(opt_idx) if uses_index else str(opt_val)
                    normalized_opts.append({"id": opt_id, "text": str(opt_val)})
            rng.shuffle(normalized_opts)
            opts = normalized_opts

        # Normalisation & Brassage de la colonne de droite pour les questions d'Appariement (matching)
        elif q.type == "matching":
            if isinstance(opts, list):
                left_list = [str(item.get("left", "")) for item in opts if isinstance(item, dict) and "left" in item]
                right_list = [str(item.get("right", "")) for item in opts if isinstance(item, dict) and "right" in item]
                rng.shuffle(right_list)
                opts = {"left": left_list, "right": right_list}
            elif isinstance(opts, dict):
                left_list = list(opts.get("left", []))
                right_list = list(opts.get("right", []))
                rng.shuffle(right_list)
                opts = {"left": left_list, "right": right_list}

        q_item = {
            "id": q.id,
            "display_order": idx,
            "type": q.type,
            "prompt_markdown": q.prompt_markdown,
            "points": q.points,
            "negative_penalty": q.negative_penalty,
            "time_limit_seconds": q.time_limit_seconds,
            "options": opts
            # SECRET ABSOLU : correct_answers_json n'est JAMAIS inclus !
        }
        if q.type in ["coding", "code", "code_python"] and isinstance(opts, dict):
            q_item["starter_code"] = opts.get("starter_code", "# Écrivez votre solution ici\n")
            q_item["tests"] = opts.get("public_tests", opts.get("tests", []))
            q_item["hint1"] = opts.get("hint1", "")
            q_item["hint2"] = opts.get("hint2", "")
            q_item["difficulty"] = opts.get("difficulty", "")
            q_item["topic"] = opts.get("chapter", "")
        student_questions.append(q_item)

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
        "server_time_iso": now.isoformat(),
        "server_time_hms": datetime.now().strftime("%H:%M:%S"),
        "server_epoch_ms": int(now.timestamp() * 1000),
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

    if remaining_seconds <= 0:
        attempt.status = "timed_out"
        if not attempt.submitted_at:
            attempt.submitted_at = now
        db.commit()
        return {
            "status": "timed_out",
            "session_status": attempt.session.status if attempt.session else "unknown",
            "timed_out": True,
            "message": "Le temps imparti pour cette épreuve est écoulé. Clôture automatique effectuée.",
            "suspension_remaining_seconds": 0,
            "remaining_seconds": 0,
            "server_time_hms": now.strftime("%H:%M:%S"),
            "server_epoch_ms": int(now.timestamp() * 1000),
            "final_mark": attempt.final_mark,
            "raw_score": attempt.raw_score
        }

    return {
        "success": True, 
        "saved_at": now.isoformat(),
        "remaining_seconds": remaining_seconds,
        "server_time_hms": datetime.now().strftime("%H:%M:%S"),
        "server_epoch_ms": int(now.timestamp() * 1000)
    }

@router.post("/attempts/{attempt_id}/security-event")
async def report_security_event(
    attempt_id: str,
    payload: Dict[str, Any],  # {"event_type": "AWAY_10S" | "FULLSCREEN_EXIT" | "BLUR", "details": ...}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Signale un événement de sécurité (ex: sortie de plein écran, absence >10s, avertissement répétitif).
    Règles disciplinaires :
    - 4 avertissements cumulés OU absence > 10 secondes = Suspension de 5 minutes (300 secondes).
    - Diffusion en direct de l'événement aux surveillants via WebSocket.
    """
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    event_type = payload.get("event_type", "SECURITY_ALERT")
    details = payload.get("details", {})
    now = datetime.now(timezone.utc)

    warning_number = details.get("warning_number", attempt.suspension_count + 1 if "WARNING" in event_type else attempt.suspension_count)
    reason = details.get("reason") or payload.get("reason", "Alerte de sécurité anti-triche")

    is_suspended = False
    suspension_duration_sec = 300  # 5 minutes

    if event_type in ["AWAY_10S", "SUSPENDED_4_WARNINGS"] or warning_number >= 4 or details.get("duration_seconds", 0) >= 10:
        attempt.status = "suspended"
        attempt.suspension_count = max(attempt.suspension_count, warning_number, 1)
        attempt.suspension_reason = reason or ("Sortie prolongée de l'écran (10s)" if event_type == "AWAY_10S" else "4 avertissements anti-triche atteints : suspension disciplinaire de 5 minutes")
        attempt.suspended_until = now + timedelta(seconds=suspension_duration_sec)
        is_suspended = True
    else:
        if "WARNING" in event_type:
            attempt.suspension_count = warning_number

    db.add(AuditLog(
        session_id=attempt.session_id,
        student_id=current_user.id,
        event_type=event_type,
        details_json=json.dumps(details)
    ))
    db.commit()

    # Diffusion en direct aux surveillants
    try:
        await ws_manager.broadcast_to_teachers(attempt.session_id, {
            "type": "SECURITY_EVENT",
            "session_id": attempt.session_id,
            "student_id": current_user.id,
            "student_name": current_user.full_name,
            "event_type": event_type,
            "reason": attempt.suspension_reason or reason,
            "suspension_count": attempt.suspension_count,
            "is_suspended": is_suspended,
            "suspended_until": attempt.suspended_until.isoformat() if attempt.suspended_until else None,
            "suspension_remaining_seconds": suspension_duration_sec if is_suspended else 0,
            "timestamp": now.isoformat()
        })
    except Exception:
        pass

    return {
        "status": attempt.status,
        "is_suspended": is_suspended,
        "suspension_count": attempt.suspension_count,
        "suspended_until": attempt.suspended_until.isoformat() if attempt.suspended_until else None,
        "suspension_remaining_seconds": suspension_duration_sec if is_suspended else 0,
        "message": "Épreuve suspendue pour 5 minutes. Déblocage automatique à l'issue ou par le surveillant." if is_suspended else "Alerte de sécurité enregistrée."
    }

@router.get("/attempts/{attempt_id}/status")
def check_attempt_status(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permet au client étudiant de vérifier en temps réel si le surveillant a levé la suspension ou si les 5 min sont écoulées."""
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    now = datetime.now(timezone.utc)
    
    # Auto-resumption si suspension_until est écoulé (5 minutes)
    suspension_remaining_seconds = 0
    if attempt.status == "suspended":
        if attempt.suspended_until:
            s_until = attempt.suspended_until
            if s_until.tzinfo is None:
                s_until = s_until.replace(tzinfo=timezone.utc)
            if now >= s_until:
                attempt.status = "in_progress"
                attempt.suspension_reason = None
                attempt.suspension_count = 0
                attempt.suspended_until = None
                db.commit()
            else:
                suspension_remaining_seconds = max(0, int((s_until - now).total_seconds()))

    exam = attempt.session.exam if attempt.session else None
    start_time = attempt.started_at or now
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    total_seconds = exam.duration_minutes * 60 if exam else 3600
    elapsed_seconds = int((now - start_time).total_seconds())
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    if remaining_seconds <= 0:
        attempt.status = "timed_out"
        if not attempt.submitted_at:
            attempt.submitted_at = now
        db.commit()
        return {
            "status": "timed_out",
            "session_status": attempt.session.status if attempt.session else "unknown",
            "timed_out": True,
            "message": "Le temps imparti pour cette épreuve est écoulé. Clôture automatique effectuée.",
            "suspension_remaining_seconds": 0,
            "remaining_seconds": 0,
            "server_time_hms": now.strftime("%H:%M:%S"),
            "server_epoch_ms": int(now.timestamp() * 1000),
            "final_mark": attempt.final_mark,
            "raw_score": attempt.raw_score
        }

    return {
        "status": attempt.status,
        "session_status": attempt.session.status if attempt.session else "unknown",
        "suspension_reason": attempt.suspension_reason,
        "suspension_count": attempt.suspension_count,
        "suspension_remaining_seconds": suspension_remaining_seconds,
        "remaining_seconds": remaining_seconds,
        "server_time_hms": now.strftime("%H:%M:%S"),
        "server_epoch_ms": int(now.timestamp() * 1000),
        "final_mark": attempt.final_mark,
        "raw_score": attempt.raw_score
    }

@router.post("/attempts/{attempt_id}/questions/{question_id}/run-tests")
def run_attempt_question_tests(
    attempt_id: str,
    question_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exécute le code d'un défi de programmation pendant une épreuve officielle.
    Enforce la garde 403 Forbidden si l'épreuve est suspendue (anti-triche).
    Masque les sorties attendues des tests cachés.
    """
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    if attempt.status == "suspended":
        raise HTTPException(
            status_code=403, 
            detail="Votre épreuve est suspendue. Déblocage surveillant requis."
        )

    if attempt.status in ["submitted", "timed_out", "completed"]:
        raise HTTPException(status_code=400, detail="Cette épreuve a déjà été soumise.")

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question introuvable.")

    exam_id = attempt.session.exam_id if attempt.session else None
    if question.exam_id != exam_id:
        raise HTTPException(status_code=400, detail="Cette question n'appartient pas à l'épreuve en cours.")

    user_code = payload.get("code", "")
    run_all = bool(payload.get("run_all", False))
    timeout = float(payload.get("timeout", 3.0))

    # Récupérer les tests publics et cachés
    opts = {}
    try:
        opts = json.loads(question.options_json) if isinstance(question.options_json, str) else (question.options_json or {})
    except Exception:
        opts = {}

    corr = []
    try:
        corr = json.loads(question.correct_answers_json) if isinstance(question.correct_answers_json, str) else (question.correct_answers_json or [])
    except Exception:
        corr = []

    public_tests = []
    hidden_tests = []

    if isinstance(opts, dict) and "public_tests" in opts:
        for idx, t in enumerate(opts["public_tests"]):
            if isinstance(t, dict):
                public_tests.append({
                    "id": f"pub_{idx+1}",
                    "input": t.get("input", ""),
                    "output": t.get("output", t.get("expected_output", "")),
                    "is_public": True
                })

    if isinstance(corr, dict):
        if "hidden_tests" in corr:
            for idx, t in enumerate(corr["hidden_tests"]):
                if isinstance(t, dict):
                    hidden_tests.append({
                        "id": f"hid_{idx+1}",
                        "input": t.get("input", ""),
                        "output": t.get("output", t.get("expected_output", "")),
                        "is_public": False
                    })
        if not public_tests and "public_tests" in corr:
            for idx, t in enumerate(corr["public_tests"]):
                if isinstance(t, dict):
                    public_tests.append({
                        "id": f"pub_{idx+1}",
                        "input": t.get("input", ""),
                        "output": t.get("output", t.get("expected_output", "")),
                        "is_public": True
                    })
    elif isinstance(corr, list):
        num_pub = len(public_tests)
        for idx, t in enumerate(corr):
            if not isinstance(t, dict):
                continue
            is_pub = t.get("is_public")
            if is_pub is True:
                if not any(pt["input"] == t.get("input") for pt in public_tests):
                    public_tests.append({
                        "id": f"pub_{len(public_tests)+1}",
                        "input": t.get("input", ""),
                        "output": t.get("output", t.get("expected_output", "")),
                        "is_public": True
                    })
            elif is_pub is False:
                hidden_tests.append({
                    "id": f"hid_{len(hidden_tests)+1}",
                    "input": t.get("input", ""),
                    "output": t.get("output", t.get("expected_output", "")),
                    "is_public": False
                })
            else:
                if idx < num_pub:
                    pass
                else:
                    hidden_tests.append({
                        "id": f"hid_{len(hidden_tests)+1}",
                        "input": t.get("input", ""),
                        "output": t.get("output", t.get("expected_output", "")),
                        "is_public": False
                    })

    if run_all:
        test_cases = public_tests + hidden_tests
    else:
        test_cases = public_tests

    return execute_user_code_against_tests(
        user_code,
        test_cases,
        timeout_seconds=timeout,
        mask_hidden_output=True
    )

@router.post("/attempts/{attempt_id}/run-code")
def run_attempt_code(
    attempt_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exécute le code d'un étudiant avec une entrée personnalisée stdin pendant l'épreuve.
    Enforce la garde 403 Forbidden si l'épreuve est suspendue.
    """
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.student_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")

    if attempt.status == "suspended":
        raise HTTPException(
            status_code=403, 
            detail="Votre épreuve est suspendue. Déblocage surveillant requis."
        )

    if attempt.status in ["submitted", "timed_out", "completed"]:
        raise HTTPException(status_code=400, detail="Cette épreuve a déjà été soumise.")

    user_code = payload.get("code", "")
    custom_stdin = payload.get("stdin", "")
    timeout = float(payload.get("timeout", 3.0))

    return execute_user_code_with_input(user_code, custom_stdin, timeout_seconds=timeout)

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

    if attempt.status == "suspended":
        raise HTTPException(status_code=403, detail="Votre épreuve est suspendue. Déblocage surveillant requis.")

    if attempt.status in ["submitted", "timed_out"]:
        return {
            "status": attempt.status,
            "raw_score": attempt.raw_score,
            "final_mark": attempt.final_mark,
            "message": "Cet examen a déjà été soumis."
        }

    exam = attempt.session.exam
    questions = list(exam.questions)

    # Même échantillon déterministe attribué à cet étudiant
    rng_sub = random.Random(f"{attempt.id}-{current_user.id}")
    instr = exam.instructions or ""
    if "CONFIG_RANDOM_STUDENT_QUESTIONS=" in instr:
        try:
            target_k = int(instr.split("CONFIG_RANDOM_STUDENT_QUESTIONS=")[1].split("]")[0])
            if 0 < target_k < len(questions):
                questions = rng_sub.sample(questions, target_k)
        except Exception:
            pass
    elif getattr(exam, "exam_type", "") == "theoretical" and "PYTHON" in (exam.module_code or "") and len(questions) > 20:
        questions = rng_sub.sample(questions, 20)
    elif getattr(exam, "exam_type", "") == "practical" and "PYTHON" in (exam.module_code or "") and len(questions) > 5:
        questions = rng_sub.sample(questions, 5)
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

        # Découplage R2 : Les moyennes et statistiques officielles par module dérivent EXCLUSIVEMENT
        # des épreuves officielles (m_official). Les tests de niveau/practice ne polluent plus ces moyennes.
        best_mark = max(m_official) if m_official else 0.0
        avg_mark = round(sum(m_official) / len(m_official), 2) if m_official else 0.0

        if code in fundamental_codes:
            fundamental_best_marks[code] = max(m_practice) if m_practice else 0.0

        mastery = "Non commencé"
        if len(m_official) > 0:
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
            "attempts_count": len(m_official),
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



