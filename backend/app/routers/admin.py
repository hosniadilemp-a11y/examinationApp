import io
import csv
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, Group, Module, Exam, ExamSession, StudentAttempt, PracticeAttempt
from backend.app.schemas import CSVImportResponse
from backend.app.security import hash_password
from backend.app.dependencies import require_admin
from backend.app.services.document_export import (
    generate_student_bulletin_pdf,
    generate_student_bulletin_docx,
    generate_bulk_bulletins_zip,
    generate_speciality_results_pdf,
    generate_speciality_results_docx
)
from backend.app.services.item_analysis import (
    calculate_exam_item_analysis,
    generate_item_analysis_csv
)

router = APIRouter(prefix="/api/admin", tags=["Super Administrateur & Statistiques Globales"])

def _decode_csv_content(file: UploadFile) -> csv.DictReader:
    try:
        content = file.file.read()
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        csv_file = io.StringIO(text)
        sample = text[:1024]
        delimiter = ";" if ";" in sample else ","
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier CSV vide ou format d'en-tête invalide."
            )
        reader.fieldnames = [fn.strip().lower() for fn in reader.fieldnames if fn]
        return reader
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de lecture du fichier CSV : {str(e)}"
        )

@router.get("/statistics/overview")
def get_global_statistics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Fournit les métriques consolidées et les indicateurs clés de performance académiques."""
    total_students = db.query(User).filter(User.role == "student").count()
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    total_modules = db.query(Module).count()
    total_exams = db.query(Exam).count()

    attempts = db.query(StudentAttempt).all()
    submitted_attempts = [a for a in attempts if a.status in ["submitted", "completed", "timed_out"] and a.final_mark is not None]

    total_submitted = len(submitted_attempts)
    avg_mark = round(sum(a.final_mark for a in submitted_attempts) / total_submitted, 2) if total_submitted > 0 else 0.0
    passed_count = sum(1 for a in submitted_attempts if a.final_mark >= 10.0)
    pass_rate = round((passed_count / total_submitted) * 100, 1) if total_submitted > 0 else 0.0

    recent_submissions = []
    for a in sorted(attempts, key=lambda x: x.started_at or datetime.min, reverse=True)[:50]:
        st = a.student
        sess = a.session
        ex = sess.exam if sess else None
        recent_submissions.append({
            "attempt_id": a.id,
            "student_id": st.id if st else "—",
            "student_name": st.full_name if st else "—",
            "group_id": st.group_id if st else "—",
            "exam_title": ex.title if ex else "—",
            "module_code": ex.module_code if ex else "—",
            "room_id": sess.room_id if sess else "—",
            "status": a.status,
            "final_mark": a.final_mark,
            "raw_score": a.raw_score,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else (a.started_at.isoformat() if a.started_at else None)
        })

    groups = db.query(Group).all()
    groups_summary = []
    for g in groups:
        g_students = db.query(User).filter(User.group_id == g.id).all()
        g_s_ids = [s.id for s in g_students]
        g_attempts = [a for a in submitted_attempts if a.student_id in g_s_ids]
        g_avg = round(sum(a.final_mark for a in g_attempts) / len(g_attempts), 2) if g_attempts else 0.0
        groups_summary.append({
            "group_id": g.id,
            "group_name": g.name,
            "student_count": len(g_students),
            "submitted_count": len(g_attempts),
            "average_mark": g_avg
        })

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_modules": total_modules,
        "total_exams": total_exams,
        "total_attempts": len(attempts),
        "total_submitted": total_submitted,
        "average_mark": avg_mark,
        "pass_rate": pass_rate,
        "recent_submissions": recent_submissions,
        "groups_summary": groups_summary
    }

@router.get("/results")
def list_all_exam_results(
    exam_id: Optional[str] = None,
    group_id: Optional[str] = None,
    room_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Liste l'ensemble des tentatives et notes d'examens avec filtres dynamiques."""
    query = db.query(StudentAttempt)
    if exam_id:
        query = query.join(ExamSession).filter(ExamSession.exam_id == exam_id)
    if room_id:
        query = query.join(ExamSession).filter(ExamSession.room_id == room_id)
    if group_id:
        query = query.join(User).filter(User.group_id == group_id)

    attempts = query.order_by(StudentAttempt.started_at.desc()).all()
    results = []
    for a in attempts:
        st = a.student
        sess = a.session
        ex = sess.exam if sess else None
        results.append({
            "attempt_id": a.id,
            "session_id": sess.id if sess else None,
            "room_id": sess.room_id if sess else "—",
            "exam_id": ex.id if ex else None,
            "exam_title": ex.title if ex else "—",
            "module_code": ex.module_code if ex else "—",
            "student_id": st.id if st else "—",
            "student_name": st.full_name if st else "—",
            "username": st.username if st else "—",
            "group_id": st.group_id if st else "—",
            "status": a.status,
            "raw_score": a.raw_score,
            "final_mark": a.final_mark,
            "suspension_count": a.suspension_count,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None
        })
    return results

@router.post("/csv/import/results", response_model=CSVImportResponse)
def import_results_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Importe et réconcilie un fichier CSV de résultats provenant d'un serveur de salle.
    Accepte les colonnes student_id, final_mark, exam_id, session_id, room_id, status, etc.
    """
    reader = _decode_csv_content(file)
    imported = 0
    updated = 0
    errors = []
    row_num = 1

    for row in reader:
        row_num += 1
        try:
            student_id = (row.get("student_id") or row.get("id") or "").strip()
            if not student_id:
                errors.append(f"Ligne {row_num}: 'student_id' manquant.")
                continue

            username = (row.get("username") or student_id).strip()
            full_name = (row.get("full_name") or f"Étudiant {student_id}").strip()
            group_id = (row.get("group_id") or row.get("groupe") or "").strip() or None
            exam_id = (row.get("exam_id") or "").strip()
            session_id = (row.get("session_id") or "").strip()
            room_id = (row.get("room_id") or "SALLE-EXTERNE").strip()
            status_val = (row.get("status") or "submitted").strip()

            raw_score_str = row.get("raw_score")
            raw_score = float(raw_score_str) if raw_score_str and raw_score_str.strip() else None

            final_mark_str = row.get("final_mark") or row.get("note")
            final_mark = float(final_mark_str) if final_mark_str and final_mark_str.strip() else None

            if group_id:
                grp = db.query(Group).filter(Group.id == group_id).first()
                if not grp:
                    grp = Group(id=group_id, name=group_id)
                    db.add(grp)
                    db.flush()

            student = db.query(User).filter(User.id == student_id).first()
            if not student:
                student = User(
                    id=student_id,
                    username=username,
                    password_hash=hash_password(student_id),
                    full_name=full_name,
                    role="student",
                    group_id=group_id,
                    is_active=True
                )
                db.add(student)
                db.flush()

            if not session_id:
                session_id = f"SESS-IMP-{room_id}"

            sess = db.query(ExamSession).filter(ExamSession.id == session_id).first()
            if not sess:
                exam = db.query(Exam).filter(Exam.id == exam_id).first() if exam_id else None
                if not exam:
                    exam = db.query(Exam).first()
                if not exam:
                    exam = Exam(
                        id="EXAM-AUTO-IMP",
                        module_code="CRYPTO",
                        title="Examen Consolidé Multi-Salles",
                        duration_minutes=45,
                        global_points=20.0
                    )
                    db.add(exam)
                    db.flush()
                sess = ExamSession(
                    id=session_id,
                    exam_id=exam.id,
                    room_id=room_id,
                    status="completed",
                    started_at=datetime.now(timezone.utc)
                )
                db.add(sess)
                db.flush()

            attempt = db.query(StudentAttempt).filter(
                StudentAttempt.session_id == sess.id,
                StudentAttempt.student_id == student.id
            ).first()

            if attempt:
                if final_mark is not None:
                    attempt.final_mark = final_mark
                if raw_score is not None:
                    attempt.raw_score = raw_score
                attempt.status = status_val
                updated += 1
            else:
                attempt = StudentAttempt(
                    id=f"ATT-{sess.id[:8]}-{student.id}",
                    session_id=sess.id,
                    student_id=student.id,
                    status=status_val,
                    raw_score=raw_score,
                    final_mark=final_mark,
                    started_at=datetime.now(timezone.utc),
                    submitted_at=datetime.now(timezone.utc)
                )
                db.add(attempt)
                imported += 1

        except Exception as e:
            errors.append(f"Ligne {row_num}: Erreur ({str(e)})")

    db.commit()
    return CSVImportResponse(
        success=len(errors) == 0,
        imported_count=imported,
        updated_count=updated,
        errors=errors,
        message=f"{imported} résultat(s) importé(s), {updated} mis à jour depuis la salle externe."
    )

@router.get("/csv/export/exam-results")
def export_all_exam_results_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte la totalité des copies officielles d'examen au format CSV."""
    attempts = db.query(StudentAttempt).order_by(StudentAttempt.started_at.desc()).all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "attempt_id", "session_id", "room_id", "exam_id", "exam_title", "module_code",
        "student_id", "username", "full_name", "group_id", "status",
        "raw_score", "final_mark", "suspension_count", "started_at", "submitted_at"
    ])

    for a in attempts:
        st = a.student
        sess = a.session
        ex = sess.exam if sess else None
        writer.writerow([
            a.id,
            sess.id if sess else "",
            sess.room_id if sess else "",
            ex.id if ex else "",
            ex.title if ex else "",
            ex.module_code if ex else "",
            st.id if st else "",
            st.username if st else "",
            st.full_name if st else "",
            st.group_id if st else "",
            a.status,
            a.raw_score if a.raw_score is not None else "",
            a.final_mark if a.final_mark is not None else "",
            a.suspension_count,
            a.started_at.isoformat() if a.started_at else "",
            a.submitted_at.isoformat() if a.submitted_at else ""
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultats_examens_officiels.csv"}
    )

def _build_student_bulletin(st: User, db: Session) -> dict:
    """Construit la structure de bulletin académique d'un étudiant avec les 4 piliers fondamentaux et les examens."""
    p_attempts = db.query(PracticeAttempt).filter(PracticeAttempt.user_id == st.id).all()
    
    pillar_configs = [
        ("ALGO", "Algorithmique Fondamentale"),
        ("PYTHON_INIT", "Programmation Python"),
        ("CRYPTO", "Cryptographie & Réseau"),
        ("LINUX_ADMIN", "Administration Linux")
    ]
    
    fundamentals = {}
    f_scores = []
    for code, title in pillar_configs:
        matching = [p.grade_20 for p in p_attempts if p.module_code == code]
        best_score = round(max(matching), 2) if matching else None
        fundamentals[code] = {
            "module_code": code,
            "title": title,
            "score": best_score,
            "percentage": round((best_score / 20.0) * 100, 1) if best_score is not None else 0.0,
            "completed": best_score is not None
        }
        if best_score is not None:
            f_scores.append(best_score)
            
    fundamentals_avg = round(sum(f_scores) / len(f_scores), 2) if f_scores else None
    
    s_attempts = db.query(StudentAttempt).filter(
        StudentAttempt.student_id == st.id,
        StudentAttempt.status.in_(["submitted", "completed", "timed_out"]),
        StudentAttempt.final_mark.isnot(None)
    ).all()
    
    theo_att = None
    prac_att = None
    for a in s_attempts:
        sess = a.session
        ex_title = sess.exam.title.lower() if sess and sess.exam else ""
        if ("theor" in ex_title or "théor" in ex_title or "qcm" in ex_title) and not theo_att:
            theo_att = a
        elif ("prat" in ex_title or "machine" in ex_title or "tp" in ex_title) and not prac_att:
            prac_att = a
            
    if not theo_att and s_attempts:
        theo_att = s_attempts[0]
    if not prac_att and len(s_attempts) > 1:
        candidates = [a for a in s_attempts if a != theo_att]
        prac_att = candidates[0] if candidates else None
        
    theo_score = round(theo_att.final_mark, 2) if theo_att and theo_att.final_mark is not None else None
    prac_score = round(prac_att.final_mark, 2) if prac_att and prac_att.final_mark is not None else None
    
    exam_scores = [s for s in [theo_score, prac_score] if s is not None]
    exams_avg = round(sum(exam_scores) / len(exam_scores), 2) if exam_scores else None
    
    all_scores = f_scores + exam_scores
    general_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    
    if general_avg is not None:
        is_pass = general_avg >= 10.0
        verdict = "ADMIS" if is_pass else "AJOURNÉ"
        verdict_label = "ADMIS / VALIDÉ" if is_pass else "AJOURNÉ (NON VALIDÉ)"
        verdict_color = "#10b981" if is_pass else "#ef4444"
    else:
        is_pass = False
        verdict = "EN_COURS"
        verdict_label = "EN COURS D'ÉVALUATION"
        verdict_color = "#64748b"
        
    return {
        "student_id": st.id,
        "username": st.username,
        "full_name": st.full_name,
        "email": st.email or "—",
        "speciality": st.group_id or "—",
        "plain_password": st.plain_password or "—",
        "fundamentals": fundamentals,
        "fundamentals_average": fundamentals_avg,
        "exams": {
            "theoretical": {
                "title": theo_att.session.exam.title if theo_att and theo_att.session and theo_att.session.exam else "Examen Théorique",
                "score": theo_score,
                "percentage": round((theo_score / 20.0) * 100, 1) if theo_score is not None else 0.0,
                "completed": theo_score is not None
            },
            "practical": {
                "title": prac_att.session.exam.title if prac_att and prac_att.session and prac_att.session.exam else "Épreuve Pratique sur Machine",
                "score": prac_score,
                "percentage": round((prac_score / 20.0) * 100, 1) if prac_score is not None else 0.0,
                "completed": prac_score is not None
            }
        },
        "exams_average": exams_avg,
        "general_average": general_avg,
        "is_pass": is_pass,
        "verdict": verdict,
        "verdict_label": verdict_label,
        "verdict_color": verdict_color,
        "evaluations_count": len(all_scores)
    }

@router.get("/bulletins")
def list_student_bulletins(
    speciality: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Génère la liste consolidée des bulletins de tous les étudiants."""
    query = db.query(User).filter(User.role == "student")
    if speciality and speciality.strip():
        query = query.filter(User.group_id == speciality.strip())
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (User.full_name.ilike(term)) |
            (User.username.ilike(term)) |
            (User.id.ilike(term))
        )
    students = query.order_by(User.group_id, User.id).all()
    return [_build_student_bulletin(s, db) for s in students]

@router.get("/bulletins/export-csv")
def export_bulletins_csv(
    speciality: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte tous les bulletins au format CSV consolidé sans redondance."""
    query = db.query(User).filter(User.role == "student")
    if speciality and speciality.strip():
        query = query.filter(User.group_id == speciality.strip())
    students = query.order_by(User.group_id, User.id).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Matricule", "Nom Complet", "Identifiant", "Mot de Passe", "Specialite",
        "Note Algo (/20)", "Note Python (/20)", "Note Crypto (/20)", "Note Linux (/20)",
        "Moyenne Fondamentaux (/20)", "Examen Theorique (/20)", "Examen Pratique (/20)",
        "Moyenne Examens (/20)", "Moyenne Generale (/20)", "Decision Jury"
    ])

    for s in students:
        b = _build_student_bulletin(s, db)
        f = b["fundamentals"]
        ex = b["exams"]
        writer.writerow([
            b["student_id"],
            b["full_name"],
            b["username"],
            b["plain_password"],
            b["speciality"],
            f["ALGO"]["score"] if f["ALGO"]["score"] is not None else "",
            f["PYTHON_INIT"]["score"] if f["PYTHON_INIT"]["score"] is not None else "",
            f["CRYPTO"]["score"] if f["CRYPTO"]["score"] is not None else "",
            f["LINUX_ADMIN"]["score"] if f["LINUX_ADMIN"]["score"] is not None else "",
            b["fundamentals_average"] if b["fundamentals_average"] is not None else "",
            ex["theoretical"]["score"] if ex["theoretical"]["score"] is not None else "",
            ex["practical"]["score"] if ex["practical"]["score"] is not None else "",
            b["exams_average"] if b["exams_average"] is not None else "",
            b["general_average"] if b["general_average"] is not None else "",
            b["verdict_label"]
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=bulletins_academiques_consolides.csv"}
    )

@router.get("/bulletins/export-zip")
def export_bulletins_bulk_zip(
    format: str = Query("pdf", pattern="^(pdf|docx|all)$"),
    speciality: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte tous les bulletins dans une archive ZIP (PDF, Word DOCX ou les deux)."""
    query = db.query(User).filter(User.role == "student")
    if speciality and speciality.strip():
        query = query.filter(User.group_id == speciality.strip())
    students = query.order_by(User.group_id, User.id).all()
    bulletins = [_build_student_bulletin(s, db) for s in students]
    zip_bytes = generate_bulk_bulletins_zip(bulletins, format_type=format)
    spec_tag = speciality.strip().lower() if speciality and speciality.strip() else "toutes_specialites"
    filename = f"bulletins_{format}_{spec_tag}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/bulletins/{student_id}")
def get_single_student_bulletin(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Récupère le bulletin complet d'un étudiant par son identifiant."""
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Étudiant introuvable.")
    return _build_student_bulletin(student, db)

@router.get("/bulletins/{student_id}/export-pdf")
def export_single_bulletin_pdf(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte le bulletin individuel d'un étudiant au format PDF officiel."""
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Étudiant introuvable.")
    b = _build_student_bulletin(student, db)
    pdf_bytes = generate_student_bulletin_pdf(b)
    filename = f"bulletin_{student.id}_{student.username}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/bulletins/{student_id}/export-docx")
def export_single_bulletin_docx(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte le bulletin individuel d'un étudiant au format Word (.docx)."""
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Étudiant introuvable.")
    b = _build_student_bulletin(student, db)
    docx_bytes = generate_student_bulletin_docx(b)
    filename = f"bulletin_{student.id}_{student.username}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/results/export-pdf")
def export_speciality_results_pdf(
    speciality: Optional[str] = Query(None),
    sort_by_module: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte le palmarès officiel de tous les étudiants (par spécialité et ordonné par module) en PDF Paysage."""
    query = db.query(User).filter(User.role == "student")
    if speciality and speciality.strip():
        query = query.filter(User.group_id == speciality.strip())
    students = query.order_by(User.group_id, User.id).all()
    bulletins = [_build_student_bulletin(s, db) for s in students]
    spec_name = speciality.strip() if speciality and speciality.strip() else "Toutes Spécialités"
    pdf_bytes = generate_speciality_results_pdf(spec_name, bulletins, sort_by_module=sort_by_module)
    sort_tag = sort_by_module.lower() if sort_by_module else "general"
    filename = f"palmares_{spec_name.lower().replace(' ', '_')}_{sort_tag}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/results/export-docx")
def export_speciality_results_docx(
    speciality: Optional[str] = Query(None),
    sort_by_module: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte le palmarès officiel de tous les étudiants (par spécialité et ordonné par module) en Word (.docx) Paysage."""
    query = db.query(User).filter(User.role == "student")
    if speciality and speciality.strip():
        query = query.filter(User.group_id == speciality.strip())
    students = query.order_by(User.group_id, User.id).all()
    bulletins = [_build_student_bulletin(s, db) for s in students]
    spec_name = speciality.strip() if speciality and speciality.strip() else "Toutes Spécialités"
    docx_bytes = generate_speciality_results_docx(spec_name, bulletins, sort_by_module=sort_by_module)
    sort_tag = sort_by_module.lower() if sort_by_module else "general"
    filename = f"palmares_{spec_name.lower().replace(' ', '_')}_{sort_tag}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/exams/{exam_id}/item-analysis")
def get_admin_exam_item_analysis_endpoint(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Retourne l'analyse psychométrique et l'indice de discrimination des questions pour l'administrateur."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    return calculate_exam_item_analysis(exam_id=exam.id, db=db)

@router.get("/exams/{exam_id}/item-analysis/csv")
def export_admin_exam_item_analysis_csv_endpoint(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte l'analyse psychométrique d'un examen en CSV pour l'administrateur."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    analysis = calculate_exam_item_analysis(exam_id=exam.id, db=db)
    csv_content = generate_item_analysis_csv(analysis)
    filename = f"analyse_questions_admin_{exam.module_code}_{exam.id}.csv"
    return StreamingResponse(
        iter([csv_content.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )




