import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db, SessionLocal
from backend.app.models import (
    ExamSession, StudentAttempt, StudentAnswer, 
    Exam, User, AuditLog
)
from backend.app.services.websocket_manager import ws_manager
from backend.app.services.grading import evaluate_answer
from backend.app.services.item_analysis import calculate_exam_item_analysis, generate_item_analysis_csv
from backend.app.dependencies import get_current_user, require_teacher_or_admin

router = APIRouter(prefix="/api/proctor", tags=["Surveillance & Proctoring Enseignant"])

# --- Endpoints REST Proctoring ---

@router.get("/sessions")
def list_proctor_sessions(
    room_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste les sessions d'examen actives ou planifiées en salle."""
    query = db.query(ExamSession).order_by(ExamSession.started_at.desc())
    if room_id:
        query = query.filter(ExamSession.room_id == room_id)
        
    sessions = query.all()
    results = []
    for s in sessions:
        results.append({
            "session_id": s.id,
            "exam_id": s.exam_id,
            "exam_title": s.exam.title if s.exam else "Inconnu",
            "module_code": s.exam.module_code if s.exam else "Inconnu",
            "room_id": s.room_id,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "attempt_count": len(s.attempts)
        })
    return results

@router.post("/sessions")
def open_exam_session(
    payload: Dict[str, Any],  # {"exam_id": "...", "room_id": "SALLE-1"}
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Ouvre une nouvelle session d'examen pour une salle physique."""
    exam_id = payload.get("exam_id")
    room_id = payload.get("room_id", "SALLE-TP-1").strip()
    
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examen introuvable.")
        
    # Si une session est déjà en attente ou en cours pour cet examen, la réutiliser
    existing_session = db.query(ExamSession).filter(
        ExamSession.exam_id == exam.id,
        ExamSession.status.in_(["waiting", "in_progress"])
    ).first()
    if existing_session:
        return {
            "success": True,
            "session_id": existing_session.id,
            "room_id": existing_session.room_id,
            "status": existing_session.status,
            "message": f"Session active {existing_session.id} reprise pour la salle {existing_session.room_id}."
        }

    session = ExamSession(
        id=f"SESS-{uuid.uuid4().hex[:8].upper()}",
        exam_id=exam.id,
        room_id=room_id,
        status="waiting",  # Les étudiants patientent dans la salle d'attente
        launched_by=current_user.id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {
        "success": True,
        "session_id": session.id,
        "room_id": session.room_id,
        "status": session.status,
        "message": f"Session de salle {room_id} ouverte. Les étudiants peuvent désormais rejoindre la salle d'attente."
    }

@router.get("/sessions/{session_id}/overview")
def get_session_proctor_overview(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Retourne la grille de télémétrie complète de la salle (Style AlgoExamination).
    Affiche pour chaque poste étudiant : statut, question active, progression, temps et alertes.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")
        
    exam = session.exam
    total_questions = len(exam.questions) if exam else 0
    now = datetime.now(timezone.utc)
    
    attempt_by_student = {att.student_id: att for att in session.attempts}
    enrolled_students = []
    if exam and exam.groups:
        for g in exam.groups:
            enrolled_students.extend([u for u in g.users if u.role == "student"])
    
    seen_ids = set()
    student_cards = []
    
    # 1. Étudiants inscrits
    for student in enrolled_students:
        seen_ids.add(student.id)
        att = attempt_by_student.get(student.id)
        if att:
            answered_count = len(att.answers)
            progress_pct = round((answered_count / total_questions) * 100) if total_questions > 0 else 0
            elapsed_seconds = 0
            if att.started_at:
                s_time = att.started_at
                if s_time.tzinfo is None:
                    s_time = s_time.replace(tzinfo=timezone.utc)
                elapsed_seconds = int((now - s_time).total_seconds())
                
            total_duration_sec = (exam.duration_minutes if exam else 60) * 60
            remaining_sec = max(0, total_duration_sec - elapsed_seconds) if att.started_at and att.status == "in_progress" else 0
            if att.status == "waiting":
                remaining_sec = total_duration_sec
            elif att.status in ["submitted", "timed_out", "completed"]:
                remaining_sec = 0

            last_answer = max([a.updated_at for a in att.answers], default=None)
            last_activity_sec = None
            if last_answer:
                if last_answer.tzinfo is None:
                    last_answer = last_answer.replace(tzinfo=timezone.utc)
                last_activity_sec = int((now - last_answer).total_seconds())
            elif att.started_at:
                last_activity_sec = elapsed_seconds

            is_online = ws_manager.is_student_connected(session.id, student.id) or (att.status == "in_progress" and (last_activity_sec is None or last_activity_sec < 90))
                
            student_cards.append({
                "attempt_id": att.id,
                "student_id": student.id,
                "student_name": student.full_name,
                "username": student.username,
                "group_id": student.group_id,
                "status": att.status,  # 'waiting', 'in_progress', 'suspended', 'submitted'
                "is_online": is_online,
                "suspension_reason": att.suspension_reason,
                "suspension_count": att.suspension_count,
                "answered_count": answered_count,
                "total_questions": total_questions,
                "progress_pct": progress_pct,
                "elapsed_seconds": elapsed_seconds,
                "remaining_seconds": remaining_sec,
                "last_activity_seconds": last_activity_sec,
                "client_ip": att.client_ip or "127.0.0.1",
                "raw_score": att.raw_score,
                "final_mark": att.final_mark
            })
        else:
            student_cards.append({
                "attempt_id": None,
                "student_id": student.id,
                "student_name": student.full_name,
                "username": student.username,
                "group_id": student.group_id,
                "status": "not_entered",
                "is_online": False,
                "suspension_reason": None,
                "suspension_count": 0,
                "answered_count": 0,
                "total_questions": total_questions,
                "progress_pct": 0,
                "elapsed_seconds": 0,
                "remaining_seconds": (exam.duration_minutes if exam else 60) * 60,
                "last_activity_seconds": None,
                "client_ip": "—",
                "raw_score": None,
                "final_mark": None
            })
            
    # 2. Tentatives éventuelles d'étudiants non inscrits au groupe officiel
    for att in session.attempts:
        if att.student_id not in seen_ids:
            seen_ids.add(att.student_id)
            student = att.student
            answered_count = len(att.answers)
            progress_pct = round((answered_count / total_questions) * 100) if total_questions > 0 else 0
            elapsed_seconds = 0
            if att.started_at:
                s_time = att.started_at
                if s_time.tzinfo is None:
                    s_time = s_time.replace(tzinfo=timezone.utc)
                elapsed_seconds = int((now - s_time).total_seconds())
            total_duration_sec = (exam.duration_minutes if exam else 60) * 60
            remaining_sec = max(0, total_duration_sec - elapsed_seconds) if att.started_at and att.status == "in_progress" else 0
            if att.status == "waiting":
                remaining_sec = total_duration_sec
            elif att.status in ["submitted", "timed_out", "completed"]:
                remaining_sec = 0

            last_answer = max([a.updated_at for a in att.answers], default=None)
            last_activity_sec = None
            if last_answer:
                if last_answer.tzinfo is None:
                    last_answer = last_answer.replace(tzinfo=timezone.utc)
                last_activity_sec = int((now - last_answer).total_seconds())
            elif att.started_at:
                last_activity_sec = elapsed_seconds

            is_online = ws_manager.is_student_connected(session.id, student.id) or (att.status == "in_progress" and (last_activity_sec is None or last_activity_sec < 90))

            student_cards.append({
                "attempt_id": att.id,
                "student_id": student.id,
                "student_name": student.full_name,
                "username": student.username,
                "group_id": student.group_id,
                "status": att.status,
                "is_online": is_online,
                "suspension_reason": att.suspension_reason,
                "suspension_count": att.suspension_count,
                "answered_count": answered_count,
                "total_questions": total_questions,
                "progress_pct": progress_pct,
                "elapsed_seconds": elapsed_seconds,
                "remaining_seconds": remaining_sec,
                "last_activity_seconds": last_activity_sec,
                "client_ip": att.client_ip or "127.0.0.1",
                "raw_score": att.raw_score,
                "final_mark": att.final_mark
            })
        
    # Journal des alertes récentes
    recent_logs = db.query(AuditLog).filter(
        AuditLog.session_id == session_id
    ).order_by(AuditLog.timestamp.desc()).limit(20).all()
    
    logs_data = [{
        "id": l.id,
        "event_type": l.event_type,
        "student_id": l.student_id,
        "timestamp": l.timestamp.isoformat(),
        "details": json.loads(l.details_json) if l.details_json else {}
    } for l in recent_logs]
    
    # Calcul authoritaire du temps restant de session (REV-37)
    session_remaining_seconds = None
    if session.status == "in_progress" and session.started_at:
        s_time = session.started_at
        if s_time.tzinfo is None:
            s_time = s_time.replace(tzinfo=timezone.utc)
        elapsed = int((now - s_time).total_seconds())
        duration_sec = (exam.duration_minutes if exam else 60) * 60
        session_remaining_seconds = max(0, duration_sec - elapsed)
    elif session.status == "waiting":
        session_remaining_seconds = (exam.duration_minutes if exam else 60) * 60
    elif session.status == "completed":
        session_remaining_seconds = 0

    return {
        "session_id": session.id,
        "room_id": session.room_id,
        "status": session.status,
        "exam_title": exam.title if exam else "Inconnu",
        "duration_minutes": exam.duration_minutes if exam else 60,
        "session_started_at": session.started_at.isoformat() if session.started_at else None,
        "session_remaining_seconds": session_remaining_seconds,
        "total_enrolled": len(student_cards),
        "student_cards": student_cards,
        "recent_audit_logs": logs_data
    }

@router.post("/sessions/{session_id}/launch")
async def launch_synchronized_exam(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Lancement Groupé Synchronisé de l'Épreuve !
    Déclenche simultanément l'examen pour tous les étudiants connectés en attente.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")
        
    now = datetime.now(timezone.utc)
    session.status = "in_progress"
    session.started_at = now
    
    # Bascule de toutes les tentatives en attente vers 'in_progress'
    waiting_attempts = db.query(StudentAttempt).filter(
        StudentAttempt.session_id == session.id,
        StudentAttempt.status == "waiting"
    ).all()
    
    for att in waiting_attempts:
        att.status = "in_progress"
        att.started_at = now
        
    db.add(AuditLog(
        session_id=session.id,
        event_type="SYNCHRONIZED_LAUNCH",
        details_json=f'{{"launched_by": "{current_user.username}", "unlocked_students_count": {len(waiting_attempts)}}}'
    ))
    db.commit()
    
    # Diffusion WebSocket à tous les postes étudiants de la salle
    await ws_manager.broadcast_to_all_students(session_id, {
        "type": "EXAM_LAUNCHED",
        "session_id": session_id,
        "started_at": now.isoformat()
    })
    
    # Notification aux surveillants
    await ws_manager.broadcast_to_teachers(session_id, {
        "type": "SESSION_STATUS_CHANGED",
        "status": "in_progress",
        "started_at": now.isoformat()
    })
    
    return {
        "success": True,
        "status": "in_progress",
        "unlocked_students": len(waiting_attempts),
        "message": f"Épreuve lancée avec succès pour {len(waiting_attempts)} étudiant(s) dans la salle."
    }

@router.post("/sessions/{session_id}/extend-time")
async def extend_session_time(
    session_id: str,
    payload: Dict[str, Any],  # {"extra_minutes": 5, "student_id": Optional[str]}
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Accorde du temps supplémentaire individuel ou collectif pour toute la salle."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")
        
    extra_minutes = int(payload.get("extra_minutes", 5))
    target_student_id = payload.get("student_id")

    from datetime import timedelta
    if target_student_id:
        target_att = db.query(StudentAttempt).filter(
            StudentAttempt.session_id == session_id,
            StudentAttempt.student_id == target_student_id
        ).first()
        if target_att and target_att.started_at:
            target_att.started_at = target_att.started_at + timedelta(minutes=extra_minutes)
    else:
        if session.started_at:
            session.started_at = session.started_at + timedelta(minutes=extra_minutes)
        for att in session.attempts:
            if att.started_at:
                att.started_at = att.started_at + timedelta(minutes=extra_minutes)
    
    db.add(AuditLog(
        session_id=session_id,
        student_id=target_student_id,
        event_type="TIME_EXTENDED",
        details_json=f'{{"extra_minutes": {extra_minutes}, "granted_by": "{current_user.username}"}}'
    ))
    db.commit()
    
    # Diffusion de la prolongation de temps
    msg = {
        "type": "TIME_EXTENDED",
        "extra_minutes": extra_minutes,
        "student_id": target_student_id
    }
    
    if target_student_id:
        await ws_manager.send_to_student(session_id, target_student_id, msg)
    else:
        await ws_manager.broadcast_to_all_students(session_id, msg)
        
    await ws_manager.broadcast_to_teachers(session_id, msg)
    
    return {
        "success": True,
        "extra_minutes": extra_minutes,
        "target": target_student_id or "all_students",
        "message": f"{extra_minutes} minute(s) supplémentaire(s) accordée(s)."
    }

@router.post("/sessions/{session_id}/attempts/{attempt_id}/force-submit")
async def force_submit_student_attempt(
    session_id: str,
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Force la soumission immédiate de l'épreuve d'un étudiant par le surveillant."""
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.session_id == session_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")
        
    exam = attempt.session.exam
    questions = exam.questions
    answers = {a.question_id: a for a in attempt.answers}
    
    total_awarded = 0.0
    total_possible = 0.0
    for q in questions:
        total_possible += q.points
        ans_record = answers.get(q.id)
        u_ans = json.loads(ans_record.answer_payload_json) if ans_record else None
        c_ans = json.loads(q.correct_answers_json) if isinstance(q.correct_answers_json, str) else q.correct_answers_json
        
        awarded, is_corr, _ = evaluate_answer(
            q_type=q.type,
            user_answer=u_ans,
            correct_answers=c_ans,
            points=q.points,
            negative_penalty=q.negative_penalty
        )
        total_awarded += awarded
        if ans_record:
            ans_record.is_correct = is_corr
            ans_record.awarded_points = awarded
            
    final_mark = round((total_awarded / total_possible) * exam.global_points, 2) if total_possible > 0 else 0.0
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.raw_score = round(total_awarded, 2)
    attempt.final_mark = final_mark
    
    db.add(AuditLog(
        session_id=session_id,
        student_id=attempt.student_id,
        event_type="FORCE_SUBMITTED",
        details_json=f'{{"forced_by": "{current_user.username}", "final_mark": {final_mark}}}'
    ))
    db.commit()
    
    # Notification à l'étudiant
    await ws_manager.send_to_student(session_id, attempt.student_id, {
        "type": "EXAM_FORCE_SUBMITTED",
        "final_mark": final_mark
    })
    
    # Notification aux surveillants
    await ws_manager.broadcast_to_teachers(session_id, {
        "type": "STUDENT_SUBMITTED",
        "student_id": attempt.student_id,
        "final_mark": final_mark
    })
    
    return {
        "success": True,
        "student_id": attempt.student_id,
        "final_mark": final_mark,
        "message": f"Épreuve de {attempt.student.full_name} soumise de force. Note : {final_mark} / {exam.global_points}."
    }

@router.post("/sessions/{session_id}/attempts/{attempt_id}/unlock")
async def unlock_student_attempt(
    session_id: str,
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Débloque un poste étudiant suspendu suite à des alertes anti-triche."""
    attempt = db.query(StudentAttempt).filter(
        StudentAttempt.id == attempt_id,
        StudentAttempt.session_id == session_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Tentative introuvable.")
        
    attempt.status = "in_progress"
    attempt.suspension_reason = None
    attempt.suspension_count = 0  # REV-29 : Remise à zéro du compteur d'avertissements au déblocage
    
    db.add(AuditLog(
        session_id=session_id,
        student_id=attempt.student_id,
        event_type="UNLOCKED_BY_TEACHER",
        details_json=f'{{"unlocked_by": "{current_user.username}", "reset_warnings": true}}'
    ))
    db.commit()
    
    # Notification à l'étudiant via WebSocket
    await ws_manager.send_to_student(session_id, attempt.student_id, {
        "type": "ATTEMPT_UNLOCKED",
        "attempt_id": attempt.id,
        "status": "in_progress",
        "reset_warnings": True
    })
    
    # Notification aux surveillants
    await ws_manager.broadcast_to_teachers(session_id, {
        "type": "STUDENT_UNLOCKED",
        "student_id": attempt.student_id,
        "attempt_id": attempt.id
    })
    
    return {
        "success": True,
        "attempt_id": attempt.id,
        "student_id": attempt.student_id,
        "status": "in_progress",
        "message": f"Poste de {attempt.student.full_name} débloqué avec succès (compteur d'avertissements réinitialisé)."
    }

@router.post("/sessions/{session_id}/unlock-all")
async def unlock_all_student_attempts(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Débloque en masse tous les postes étudiants suspendus dans la session de salle.
    Remet à zéro leurs compteurs d'avertissements et diffuse les mises à jour WebSocket.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")

    suspended_attempts = db.query(StudentAttempt).filter(
        StudentAttempt.session_id == session.id,
        StudentAttempt.status == "suspended"
    ).all()

    for att in suspended_attempts:
        att.status = "in_progress"
        att.suspension_reason = None
        att.suspension_count = 0
        await ws_manager.send_to_student(session_id, att.student_id, {
            "type": "ATTEMPT_UNLOCKED",
            "attempt_id": att.id,
            "status": "in_progress",
            "reset_warnings": True
        })

    db.add(AuditLog(
        session_id=session_id,
        event_type="UNLOCKED_ALL_BY_TEACHER",
        details_json=f'{{"unlocked_by": "{current_user.username}", "unlocked_count": {len(suspended_attempts)}, "reset_warnings": true}}'
    ))
    db.commit()

    await ws_manager.broadcast_to_teachers(session_id, {
        "type": "ALL_ATTEMPTS_UNLOCKED",
        "session_id": session.id,
        "unlocked_count": len(suspended_attempts),
        "unlocked_by": current_user.username
    })

    return {
        "success": True,
        "unlocked_count": len(suspended_attempts),
        "message": f"{len(suspended_attempts)} étudiant(s) suspendu(s) débloqué(s) avec succès."
    }

@router.post("/sessions/{session_id}/close")
async def close_exam_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Clôture collective définitive de la session d'examen (REV-30).
    Force la soumission et le calcul des notes pour toutes les tentatives en cours ou suspendues.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")
        
    now = datetime.now(timezone.utc)
    session.status = "completed"
    session.ended_at = now
    
    exam = session.exam
    questions = exam.questions if exam else []
    total_possible = sum(q.points for q in questions)
    
    submitted_count = 0
    # Traiter toutes les tentatives non encore soumises
    for att in session.attempts:
        if att.status in ["in_progress", "suspended", "waiting"]:
            answers = {a.question_id: a for a in att.answers}
            total_awarded = 0.0
            for q in questions:
                ans_record = answers.get(q.id)
                u_ans = json.loads(ans_record.answer_payload_json) if ans_record else None
                c_ans = json.loads(q.correct_answers_json) if isinstance(q.correct_answers_json, str) else q.correct_answers_json
                awarded, is_corr, _ = evaluate_answer(
                    q_type=q.type,
                    user_answer=u_ans,
                    correct_answers=c_ans,
                    points=q.points,
                    negative_penalty=q.negative_penalty
                )
                total_awarded += awarded
                if ans_record:
                    ans_record.is_correct = is_corr
                    ans_record.awarded_points = awarded
            
            final_mark = round((total_awarded / total_possible) * exam.global_points, 2) if total_possible > 0 else 0.0
            att.status = "submitted"
            att.submitted_at = now
            att.raw_score = round(total_awarded, 2)
            att.final_mark = final_mark
            submitted_count += 1
            
            # Notification individuelle à chaque étudiant
            await ws_manager.send_to_student(session_id, att.student_id, {
                "type": "EXAM_FORCE_SUBMITTED",
                "final_mark": final_mark,
                "global_points": exam.global_points if exam else 20
            })
            
    db.add(AuditLog(
        session_id=session.id,
        event_type="SESSION_CLOSED_BY_TEACHER",
        details_json=f'{{"closed_by": "{current_user.username}", "total_sealed": {submitted_count}}}'
    ))
    db.commit()
    
    # Broadcast à tous les surveillants et étudiants
    await ws_manager.broadcast_to_teachers(session_id, {
        "type": "SESSION_CLOSED",
        "session_id": session.id,
        "submitted_count": submitted_count
    })
    
    return {
        "success": True,
        "session_id": session.id,
        "status": "completed",
        "submitted_count": submitted_count,
        "message": f"Épreuve clôturée avec succès pour toute la salle. {submitted_count} copie(s) scellée(s)."
    }

# --- Canaux WebSocket Temps Réel ---

@router.websocket("/ws/session/{session_id}/teacher")
async def websocket_teacher_feed(
    websocket: WebSocket,
    session_id: str
):
    """Canal WebSocket pour le dashboard enseignant (reçoit les flux de tous les étudiants)."""
    await ws_manager.connect_teacher(session_id, websocket)
    try:
        while True:
            # Écoute des ordres éventuels ou simple maintien du canal
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_teacher(session_id, websocket)

@router.websocket("/ws/session/{session_id}/student/{student_id}")
async def websocket_student_telemetry(
    websocket: WebSocket,
    session_id: str,
    student_id: str
):
    """Canal WebSocket pour le terminal étudiant (envoie battement de cœur et progression)."""
    await ws_manager.connect_student(session_id, student_id, websocket)
    try:
        while True:
            data_raw = await websocket.receive_text()
            try:
                msg = json.loads(data_raw)
                msg["student_id"] = student_id
                # Retransmission immédiate au dashboard enseignant
                await ws_manager.broadcast_to_teachers(session_id, msg)
            except Exception:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect_student(session_id, student_id)

# --- Analyse Psychométrique & Discrimination de la Session ---

@router.get("/sessions/{session_id}/item-analysis")
def get_session_item_analysis_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Retourne l'analyse psychométrique et l'indice de discrimination des questions
    spécifiquement pour cette session de surveillance en salle.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable.")
    
    return calculate_exam_item_analysis(exam_id=session.exam_id, db=db, session_id=session.id)

@router.get("/sessions/{session_id}/item-analysis/csv")
def export_session_item_analysis_csv_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Exporte l'analyse statistique et psychométrique des questions de la session en CSV.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable.")
    
    analysis = calculate_exam_item_analysis(exam_id=session.exam_id, db=db, session_id=session.id)
    csv_content = generate_item_analysis_csv(analysis)
    
    filename = f"analyse_questions_session_{session.room_id}_{session.id}.csv"
    return StreamingResponse(
        iter([csv_content.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

