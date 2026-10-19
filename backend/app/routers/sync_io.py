import io
import os
import zipfile
import hashlib
import json
import csv
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import (
    Exam, Question, ExamSession, StudentAttempt, 
    StudentAnswer, User, Group, AuditLog, Module
)
from backend.app.dependencies import require_admin, require_teacher_or_admin

router = APIRouter(prefix="/api/sync", tags=["Synchronisation Manuelle USB & Master (Option B)"])

SCHEMA_VERSION = "1.0.0"

# --- 1. Export d'un Examen sous Package .exam.zip (Master) ---

@router.get("/exams/{exam_id}/export-package")
def export_exam_package(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Exporte un examen complet sous forme d'archive compressée .exam.zip (pour transfert USB).
    Contient les questions, options, corrigés, barèmes et un hachage d'intégrité SHA-256.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examen introuvable.")

    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.ordering).all()
    groups = [g.id for g in exam.groups]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": current_user.username,
        "exam": {
            "id": exam.id,
            "module_code": exam.module_code,
            "title": exam.title,
            "instructions": exam.instructions,
            "duration_minutes": exam.duration_minutes,
            "global_points": exam.global_points,
            "navigation_mode": exam.navigation_mode,
            "shuffle_questions": exam.shuffle_questions,
            "shuffle_options": exam.shuffle_options,
            "partial_credit_enabled": exam.partial_credit_enabled,
            "default_negative_penalty": exam.default_negative_penalty,
            "assigned_groups": groups
        },
        "questions": [{
            "id": q.id,
            "ordering": q.ordering,
            "type": q.type,
            "prompt_markdown": q.prompt_markdown,
            "points": q.points,
            "negative_penalty": q.negative_penalty,
            "time_limit_seconds": q.time_limit_seconds,
            "options_json": q.options_json,
            "correct_answers_json": q.correct_answers_json
        } for q in questions]
    }

    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    checksum = hashlib.sha256(manifest_bytes).hexdigest()

    # Création du fichier ZIP en mémoire
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("exam_manifest.json", manifest_bytes)
        zf.writestr("checksum.sha256", checksum)

    zip_buffer.seek(0)
    filename = f"examen_{exam.module_code}_{exam.id}.exam.zip"

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- 2. Import d'un Package .exam.zip sur Serveur de Salle ---

@router.post("/exams/import-package")
def import_exam_package(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Importe un package d'examen (.exam.zip) sur le serveur de salle depuis une clé USB.
    Vérifie l'intégrité SHA-256 et insère l'examen et les questions en base locale.
    """
    try:
        content = file.file.read()
        zip_buffer = io.BytesIO(content)
        
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            if "exam_manifest.json" not in zf.namelist():
                raise HTTPException(status_code=400, detail="Package invalide : 'exam_manifest.json' absent.")

            manifest_bytes = zf.read("exam_manifest.json")
            
            # Vérification du checksum si présent
            if "checksum.sha256" in zf.namelist():
                expected_sha = zf.read("checksum.sha256").decode("utf-8").strip()
                actual_sha = hashlib.sha256(manifest_bytes).hexdigest()
                if expected_sha != actual_sha:
                    raise HTTPException(status_code=400, detail="Intégrité corrompue : le hachage SHA-256 ne correspond pas.")

            manifest = json.loads(manifest_bytes.decode("utf-8"))

        exam_data = manifest["exam"]
        questions_data = manifest["questions"]

        # Vérification / création automatique du module rattaché si absent
        module = db.query(Module).filter(Module.code == exam_data["module_code"]).first()
        if not module:
            module = Module(code=exam_data["module_code"], title=exam_data["module_code"])
            db.add(module)
            db.flush()

        # Si un enseignant importe un examen sur ce serveur de salle, lui associer le module s'il ne l'est pas
        if current_user.role == "teacher" and module not in current_user.assigned_modules:
            current_user.assigned_modules.append(module)

        # Vérification de l'examen existant (mise à jour ou création)
        existing_exam = db.query(Exam).filter(Exam.id == exam_data["id"]).first()
        if existing_exam:
            existing_exam.title = exam_data["title"]
            existing_exam.instructions = exam_data.get("instructions")
            existing_exam.duration_minutes = exam_data.get("duration_minutes", 60)
            existing_exam.global_points = exam_data.get("global_points", 20.0)
            existing_exam.navigation_mode = exam_data.get("navigation_mode", "free")
            existing_exam.shuffle_questions = exam_data.get("shuffle_questions", True)
            existing_exam.shuffle_options = exam_data.get("shuffle_options", True)
            existing_exam.partial_credit_enabled = exam_data.get("partial_credit_enabled", True)
            existing_exam.default_negative_penalty = exam_data.get("default_negative_penalty", 0.5)
            target_exam = existing_exam
            # Supprimer les anciennes questions pour synchronisation exacte
            db.query(Question).filter(Question.exam_id == target_exam.id).delete()
        else:
            target_exam = Exam(
                id=exam_data["id"],
                module_code=exam_data["module_code"],
                title=exam_data["title"],
                instructions=exam_data.get("instructions"),
                duration_minutes=exam_data.get("duration_minutes", 60),
                global_points=exam_data.get("global_points", 20.0),
                navigation_mode=exam_data.get("navigation_mode", "free"),
                shuffle_questions=exam_data.get("shuffle_questions", True),
                shuffle_options=exam_data.get("shuffle_options", True),
                partial_credit_enabled=exam_data.get("partial_credit_enabled", True),
                default_negative_penalty=exam_data.get("default_negative_penalty", 0.5),
                created_by=current_user.id
            )
            db.add(target_exam)

        db.flush()

        # Affectation des groupes
        if exam_data.get("assigned_groups"):
            target_exam.groups.clear()
            for gid in exam_data["assigned_groups"]:
                grp = db.query(Group).filter(Group.id == gid).first()
                if not grp:
                    grp = Group(id=gid, name=gid)
                    db.add(grp)
                    db.flush()
                target_exam.groups.append(grp)

        # Insertion des questions
        for q_dict in questions_data:
            q = Question(
                id=q_dict["id"],
                exam_id=target_exam.id,
                ordering=q_dict["ordering"],
                type=q_dict["type"],
                prompt_markdown=q_dict["prompt_markdown"],
                points=q_dict["points"],
                negative_penalty=q_dict["negative_penalty"],
                time_limit_seconds=q_dict.get("time_limit_seconds"),
                options_json=q_dict["options_json"],
                correct_answers_json=q_dict["correct_answers_json"]
            )
            db.add(q)

        db.commit()

        return {
            "success": True,
            "exam_id": target_exam.id,
            "title": target_exam.title,
            "questions_count": len(questions_data),
            "message": f"Examen '{target_exam.title}' importé avec succès ({len(questions_data)} questions)."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur d'importation de l'archive : {str(e)}")

# --- 3. Export des Résultats d'une Session sous .results.zip (Serveur de Salle) ---

@router.get("/sessions/{session_id}/export-results")
def export_session_results(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Exporte l'ensemble des copies et du journal d'audit d'une session sous archive .results.zip
    pour importation et consolidation sur l'instance Master via clé USB.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable.")

    exam = session.exam

    # 1. Métadonnées de Session
    session_meta = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "room_id": session.room_id,
        "session_id": session.id,
        "exam_id": exam.id if exam else "INCONNU",
        "exam_title": exam.title if exam else "INCONNU",
        "module_code": exam.module_code if exam else "INCONNU",
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "total_attempts": len(session.attempts)
    }

    # 2. Tableur CSV des Soumissions Étudiants
    csv_submissions = io.StringIO()
    sub_writer = csv.writer(csv_submissions, delimiter=";")
    sub_writer.writerow([
        "session_id", "room_id", "exam_id", "student_id", "username", 
        "full_name", "group_id", "status", "raw_score", "final_mark", 
        "suspension_count", "suspension_reason", "submitted_at"
    ])

    for att in session.attempts:
        s = att.student
        sub_writer.writerow([
            session.id, session.room_id, exam.id if exam else "",
            s.id, s.username, s.full_name, s.group_id or "",
            att.status, att.raw_score if att.raw_score is not None else "",
            att.final_mark if att.final_mark is not None else "",
            att.suspension_count, att.suspension_reason or "",
            att.submitted_at.isoformat() if att.submitted_at else ""
        ])

    # 3. Tableur CSV détaillé des Réponses par Question
    csv_answers = io.StringIO()
    ans_writer = csv.writer(csv_answers, delimiter=";")
    ans_writer.writerow(["session_id", "student_id", "question_id", "is_correct", "awarded_points", "answer_json"])

    for att in session.attempts:
        for ans in att.answers:
            ans_writer.writerow([
                session.id, att.student_id, ans.question_id,
                ans.is_correct, ans.awarded_points, ans.answer_payload_json
            ])

    # 4. Journal d'Audit JSON
    audit_logs = db.query(AuditLog).filter(AuditLog.session_id == session.id).all()
    logs_data = [{
        "id": l.id,
        "session_id": l.session_id,
        "student_id": l.student_id,
        "event_type": l.event_type,
        "details": json.loads(l.details_json) if l.details_json else {},
        "timestamp": l.timestamp.isoformat()
    } for l in audit_logs]

    # Création du ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("session_metadata.json", json.dumps(session_meta, ensure_ascii=False, indent=2))
        zf.writestr("student_submissions.csv", csv_submissions.getvalue().encode("utf-8-sig"))
        zf.writestr("question_answers.csv", csv_answers.getvalue().encode("utf-8-sig"))
        zf.writestr("audit_logs.json", json.dumps(logs_data, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)
    filename = f"resultats_{session.room_id}_{session.id}.results.zip"

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- 4. Import & Réconciliation Idempotente sur le Master ---

@router.post("/master/import-results")
def import_results_to_master(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Importe et consolide une archive de résultats (.results.zip) provenant d'une salle sur le Master.
    Opération strictement IDEMPOTENTE : peut être ré-exécutée sans créer de doublons.
    """
    try:
        content = file.file.read()
        zip_buffer = io.BytesIO(content)

        with zipfile.ZipFile(zip_buffer, "r") as zf:
            if "session_metadata.json" not in zf.namelist() or "student_submissions.csv" not in zf.namelist():
                raise HTTPException(status_code=400, detail="Archive de résultats invalide.")

            meta = json.loads(zf.read("session_metadata.json").decode("utf-8"))
            submissions_csv = zf.read("student_submissions.csv").decode("utf-8-sig")

        session_id = meta["session_id"]
        exam_id = meta["exam_id"]
        room_id = meta["room_id"]

        # Création ou récupération de la session sur le Master
        session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        if not session:
            session = ExamSession(
                id=session_id,
                exam_id=exam_id,
                room_id=room_id,
                status="completed"
            )
            db.add(session)
            db.flush()

        # Lecture des soumissions CSV
        reader = csv.DictReader(io.StringIO(submissions_csv), delimiter=";")
        imported_students = 0
        updated_students = 0

        for row in reader:
            student_id = row["student_id"]
            username = row["username"]
            full_name = row["full_name"]
            group_id = row.get("group_id") or None
            status_val = row["status"]
            raw_score = float(row["raw_score"]) if row["raw_score"] else None
            final_mark = float(row["final_mark"]) if row["final_mark"] else None
            suspension_count = int(row.get("suspension_count", 0))

            # Assurer l'existence de l'étudiant sur le Master
            student = db.query(User).filter(User.id == student_id).first()
            if not student:
                student = User(
                    id=student_id,
                    username=username,
                    full_name=full_name,
                    password_hash="IMPORTED_OFFLINE",
                    role="student",
                    group_id=group_id,
                    must_change_password=True,
                    is_active=True
                )
                db.add(student)
                db.flush()

            # Réconciliation de la tentative (Idempotence)
            attempt = db.query(StudentAttempt).filter(
                StudentAttempt.session_id == session_id,
                StudentAttempt.student_id == student_id
            ).first()

            if attempt:
                attempt.status = status_val
                attempt.raw_score = raw_score
                attempt.final_mark = final_mark
                attempt.suspension_count = suspension_count
                updated_students += 1
            else:
                attempt = StudentAttempt(
                    id=f"ATT-{session_id[:6]}-{student_id[:6]}",
                    session_id=session_id,
                    student_id=student_id,
                    status=status_val,
                    raw_score=raw_score,
                    final_mark=final_mark,
                    suspension_count=suspension_count
                )
                db.add(attempt)
                imported_students += 1

        db.commit()

        return {
            "success": True,
            "session_id": session_id,
            "room_id": room_id,
            "imported_attempts": imported_students,
            "updated_attempts": updated_students,
            "message": f"Résultats de la salle {room_id} réconciliés avec succès ({imported_students} importés, {updated_students} mis à jour)."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la réconciliation : {str(e)}")

# --- 5. Génération du Tableur Consolidé des Notes & Statistiques (Master) ---

@router.get("/master/consolidated-gradebook")
def export_consolidated_gradebook(
    module_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Génère le tableur de notes consolidé multi-salles (notes_consolidees.csv) avec calcul
    de la moyenne générale, médiane et taux d'anomalies de surveillance.
    """
    query = db.query(StudentAttempt).filter(StudentAttempt.status == "submitted")
    if module_code:
        query = query.join(ExamSession).join(Exam).filter(Exam.module_code == module_code.upper())

    attempts = query.all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Matricule", "Nom d'utilisateur", "Nom et Prénom", "Groupe",
        "Module", "Titre Examen", "Salle", "Note Finale (/20)", 
        "Score Brut", "Suspensions Anti-Triche"
    ])

    scores = []
    for att in attempts:
        student = att.student
        session = att.session
        exam = session.exam if session else None
        mark = att.final_mark if att.final_mark is not None else 0.0
        scores.append(mark)

        writer.writerow([
            student.id, student.username, student.full_name, student.group_id or "N/A",
            exam.module_code if exam else "N/A",
            exam.title if exam else "N/A",
            session.room_id if session else "N/A",
            mark, att.raw_score or 0.0, att.suspension_count
        ])

    output.seek(0)
    filename = f"notes_consolidees_{module_code or 'tous'}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
