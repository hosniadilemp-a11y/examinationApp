import io
import json
import zipfile
import csv
import random
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from html import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from backend.app.models import Exam, ExamSession, StudentAttempt, StudentAnswer, User, Question, AuditLog

def get_student_displayed_questions(
    exam: Exam,
    student: User,
    attempt: Optional[StudentAttempt],
    answers_map: Dict[str, StudentAnswer]
) -> List[Question]:
    """
    Retourne strictement la liste ordonnée des questions qui ont été
    effectivement présentées / assignées à cet étudiant (Dual Shuffling déterministe).
    """
    all_q = list(exam.questions)
    if not all_q:
        return []

    assigned_q_ids = set(answers_map.keys())
    if attempt and attempt.id:
        rng = random.Random(f"{attempt.id}-{student.id}")
        instr = exam.instructions or ""
        target_k = None
        if "CONFIG_RANDOM_STUDENT_QUESTIONS=" in instr:
            try:
                target_k = int(instr.split("CONFIG_RANDOM_STUDENT_QUESTIONS=")[1].split("]")[0])
            except Exception:
                pass

        if target_k and 0 < target_k < len(all_q):
            sampled_q = rng.sample(all_q, target_k)
        elif exam.exam_type == "theoretical" and len(all_q) > 20:
            sampled_q = rng.sample(all_q, 20)
        elif exam.exam_type == "practical" and len(all_q) > 5:
            sampled_q = rng.sample(all_q, 5)
        else:
            sampled_q = all_q

        assigned_q_ids.update(q.id for q in sampled_q)

    if assigned_q_ids:
        res = [q for q in all_q if q.id in assigned_q_ids]
    else:
        res = all_q

    res.sort(key=lambda q: q.ordering)
    return res

def format_answer_for_display(question: Question, raw_answer: Any, is_expected: bool = False) -> str:
    """
    Formate une réponse (étudiant ou corrigé attendu) de manière 100% lisible et humaine.
    Résout les indices numériques en textes clairs d'options (ex: A) [0, 4] au lieu de 0).
    Extrait les solutions propres pour le code (sans JSON brut ni tests).
    """
    if raw_answer is None or raw_answer == "" or raw_answer == [] or raw_answer == {}:
        return "<font color='#64748b'><i>(Non répondu)</i></font>" if not is_expected else "<font color='#64748b'><i>(Non défini)</i></font>"

    q_type = question.type or ""
    options = []
    if question.options_json:
        try:
            options = json.loads(question.options_json) if isinstance(question.options_json, str) else question.options_json
        except Exception:
            options = []

    # 1. Questions à choix unique (single_choice, qcm)
    if q_type in ["single_choice", "qcm"]:
        val = raw_answer
        if isinstance(val, list) and len(val) > 0:
            val = val[0]
        
        idx = None
        if isinstance(val, int):
            idx = val
        elif isinstance(val, str) and val.strip().isdigit():
            idx = int(val.strip())

        if idx is not None and isinstance(options, list) and 0 <= idx < len(options):
            opt_item = options[idx]
            opt_text = opt_item.get("text", str(opt_item)) if isinstance(opt_item, dict) else str(opt_item)
            letter = chr(65 + idx)
            return f"<b>{letter})</b> {escape(opt_text)}"
        elif isinstance(val, str):
            for i, opt_item in enumerate(options):
                opt_text = opt_item.get("text", str(opt_item)) if isinstance(opt_item, dict) else str(opt_item)
                if val.strip() == opt_text.strip():
                    return f"<b>{chr(65 + i)})</b> {escape(opt_text)}"
            return escape(val)
        return escape(str(val))

    # 2. Questions à choix multiples (multi_choice, multiple_choice)
    elif q_type in ["multi_choice", "multiple_choice"]:
        indices = []
        if isinstance(raw_answer, list):
            for item in raw_answer:
                if isinstance(item, int):
                    indices.append(item)
                elif isinstance(item, str) and item.strip().isdigit():
                    indices.append(int(item.strip()))
                elif isinstance(item, str) and isinstance(options, list):
                    for i, opt_item in enumerate(options):
                        opt_text = opt_item.get("text", str(opt_item)) if isinstance(opt_item, dict) else str(opt_item)
                        if item.strip() == opt_text.strip() and i not in indices:
                            indices.append(i)
                            break
        elif isinstance(raw_answer, int):
            indices = [raw_answer]
        elif isinstance(raw_answer, str) and raw_answer.strip().isdigit():
            indices = [int(raw_answer.strip())]

        if indices and isinstance(options, list):
            parts = []
            for idx in sorted(indices):
                if 0 <= idx < len(options):
                    opt_item = options[idx]
                    opt_text = opt_item.get("text", str(opt_item)) if isinstance(opt_item, dict) else str(opt_item)
                    letter = chr(65 + idx)
                    parts.append(f"<b>{letter})</b> {escape(opt_text)}")
            if parts:
                return "<br/>".join(parts)

        if isinstance(raw_answer, list):
            return escape(", ".join(str(x) for x in raw_answer))
        return escape(str(raw_answer))

    # 3. Booléen (Vrai / Faux)
    elif q_type == "boolean":
        b_val = None
        if isinstance(raw_answer, bool):
            b_val = raw_answer
        elif str(raw_answer).lower() in ["true", "vrai", "1"]:
            b_val = True
        elif str(raw_answer).lower() in ["false", "faux", "0"]:
            b_val = False

        if b_val is True:
            return "<b>Vrai</b>"
        elif b_val is False:
            return "<b>Faux</b>"
        return escape(str(raw_answer))

    # 4. Fill in the blank (Texte à trou)
    elif q_type == "fill_blank":
        if isinstance(raw_answer, list):
            return escape(", ".join(str(x) for x in raw_answer))
        return escape(str(raw_answer))

    # 5. Matching (Associations)
    elif q_type == "matching":
        if isinstance(raw_answer, dict):
            lines = [f"• {escape(str(k))} ➔ {escape(str(v))}" for k, v in raw_answer.items()]
            return "<br/>".join(lines)
        return escape(str(raw_answer))

    # 6. Programmation Python / Code (code_python, coding, code)
    elif q_type in ["code_python", "coding", "code"]:
        if isinstance(raw_answer, dict):
            sol = raw_answer.get("solution") or raw_answer.get("code") or ""
            if sol:
                lines = [l for l in sol.strip().split("\n") if l.strip()]
                preview = "\n".join(lines[:5])
                if len(lines) > 5:
                    preview += f"\n# ... ({len(lines) - 5} lignes suppl.)"
                return f"<font face='Courier' size='7'>{escape(preview).replace(chr(10), '<br/>&nbsp;&nbsp;')}</font>"
            return "<i>(Solution validée)</i>"
        elif isinstance(raw_answer, str):
            code_text = raw_answer.strip()
            if not code_text:
                return "<font color='#64748b'><i>(Non répondu)</i></font>"
            lines = [l for l in code_text.split("\n") if l.strip()]
            preview = "\n".join(lines[:5])
            if len(lines) > 5:
                preview += f"\n# ... ({len(lines) - 5} lignes suppl.)"
            return f"<font face='Courier' size='7'>{escape(preview).replace(chr(10), '<br/>&nbsp;&nbsp;')}</font>"
        return escape(str(raw_answer))

    # Autres types
    return escape(str(raw_answer))

def _clean_pdf_text(s: Any, max_len: int = 240) -> str:
    if s is None:
        return "—"
    txt = str(s).strip()
    txt = re.sub(r'[*_#]', '', txt)
    if len(txt) > max_len:
        txt = txt[:max_len - 3] + "..."
    return escape(txt).replace("\n", "<br/>")

def generate_student_copy_pdf(
    exam: Exam,
    student: User,
    attempt: Optional[StudentAttempt],
    answers_map: Dict[str, StudentAnswer]
) -> bytes:
    """
    Génère la copie officielle de l'étudiant au format PDF concis sous forme de tableau
    conforme aux exigences : uniquement les questions posées à l'étudiant, sa réponse,
    la réponse attendue, le barème et la note obtenue.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#0f172a')
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )
    cell_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.white
    )

    story = []
    story.append(Paragraph("<b>RÉPUBLIQUE ALGÉRIENNE DÉMOCRATIQUE ET POPULAIRE</b>", ParagraphStyle('SubHeader', alignment=1, fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#475569'))))
    story.append(Paragraph("<b>COPIE OFFICIELLE D'ÉPREUVE & FEUILLE DE RÉPONSES</b>", title_style))
    story.append(Spacer(1, 6))

    final_mark_val = attempt.final_mark if attempt and attempt.final_mark is not None else 0.0
    is_passed = final_mark_val >= 10.0
    verdict_text = "ADMIS / VALIDÉ" if is_passed else "AJOURNÉ"
    verdict_color = "#059669" if is_passed else "#dc2626"
    status_label = "Soumis / Rendu" if (attempt and attempt.status in ["submitted", "timed_out"]) else (attempt.status if attempt else "Absent")
    mins_spent = 0
    if attempt and attempt.started_at and attempt.submitted_at:
        mins_spent = max(1, int((attempt.submitted_at - attempt.started_at).total_seconds() / 60))

    meta_data = [
        [
            Paragraph(f"<b>Épreuve :</b> {escape(exam.title or 'Examen')} ({escape(exam.module_code or 'MOD')})", meta_style),
            Paragraph(f"<b>Candidat :</b> {escape(student.full_name or student.username)} (ID: {escape(student.id or '')})", meta_style),
        ],
        [
            Paragraph(f"<b>Groupe / Classe :</b> {escape(student.group_id or 'Tous')} | <b>Promo :</b> {escape(student.enrollment_year or '2025-2026')}", meta_style),
            Paragraph(f"<b>Statut Copie :</b> {status_label} | <b>Temps :</b> {mins_spent} min / {exam.duration_minutes} min", meta_style),
        ],
        [
            Paragraph(f"<b>Barème Global :</b> / {exam.global_points} pts | <b>Type :</b> {'Pratique' if exam.exam_type == 'practical' else 'Théorique'}", meta_style),
            Paragraph(f"<b>NOTE FINALE :</b> <font color='{verdict_color}'><b>{final_mark_val:.2f} / 20.00</b></font> ({verdict_text})", meta_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[285, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    student_questions = get_student_displayed_questions(exam, student, attempt, answers_map)

    headers = [
        Paragraph("N°", cell_header),
        Paragraph("Question / Énoncé", cell_header),
        Paragraph("Réponse Soumise Étudiant", cell_header),
        Paragraph("Corrigé / Attendu", cell_header),
        Paragraph("Barème", cell_header),
        Paragraph("Résultat", cell_header)
    ]
    table_data = [headers]

    for idx, q in enumerate(student_questions, 1):
        ans_record = answers_map.get(q.id)
        awarded_pts = ans_record.awarded_points if ans_record and ans_record.awarded_points is not None else 0.0
        is_corr = ans_record.is_correct if ans_record else False

        st_ans = None
        if ans_record and ans_record.answer_payload_json:
            try:
                st_ans = json.loads(ans_record.answer_payload_json)
            except Exception:
                st_ans = ans_record.answer_payload_json

        corr_ans = None
        if q.correct_answers_json:
            try:
                corr_ans = json.loads(q.correct_answers_json)
            except Exception:
                corr_ans = q.correct_answers_json

        st_ans_str = format_answer_for_display(q, st_ans, is_expected=False)
        corr_ans_str = format_answer_for_display(q, corr_ans, is_expected=True)

        if st_ans is None or st_ans == "" or st_ans == []:
            res_str = "<font color='#64748b'><b>ABS</b></font>"
        elif is_corr:
            res_str = "<font color='#059669'><b>CORRECT</b></font>"
        elif awarded_pts > 0:
            res_str = "<font color='#b45309'><b>PARTIEL</b></font>"
        else:
            res_str = "<font color='#dc2626'><b>FAUX</b></font>"

        pts_str = f"<b>{awarded_pts:.2f}</b> / {q.points:.2f}"
        prompt_clean = _clean_pdf_text(q.prompt_markdown, max_len=180)

        table_data.append([
            Paragraph(f"<b>{idx}</b>", cell_style),
            Paragraph(prompt_clean, cell_style),
            Paragraph(st_ans_str, cell_style),
            Paragraph(corr_ans_str, cell_style),
            Paragraph(pts_str, cell_style),
            Paragraph(res_str, cell_style),
        ])

    col_widths = [20, 195, 135, 135, 40, 30]
    q_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(q_table)

    doc.build(story)
    return buf.getvalue()

def generate_student_copy_html(
    exam: Exam,
    student: User,
    attempt: Optional[StudentAttempt],
    answers_map: Dict[str, StudentAnswer],
    audit_logs: List[AuditLog]
) -> str:
    """
    Génère un document HTML complet et imprimable représentant
    la copie officielle d'épreuve d'un étudiant avec filtrage des questions posées.
    """
    exam_title = escape(exam.title or "Examen")
    module_code = escape(exam.module_code or "MODULE")
    student_name = escape(student.full_name or student.username)
    student_id = escape(student.id or "")
    username = escape(student.username or "")
    group_id = escape(student.group_id or "Sans classe")
    promo = escape(student.enrollment_year or "2025-2026")
    
    status_label = "Non présenté"
    final_mark_str = "ABS"
    raw_score_str = "0.00"
    verdict = "Absent"
    verdict_color = "#64748b"
    started_str = "N/A"
    submitted_str = "N/A"
    duration_str = "0 min"
    
    if attempt:
        status_translations = {
            "submitted": "Soumis / Rendu",
            "timed_out": "Clôturé par temps écoulé",
            "in_progress": "En cours",
            "waiting": "En salle d'attente",
            "suspended": "Suspendu pour incident"
        }
        status_label = status_translations.get(attempt.status, attempt.status)
        if attempt.final_mark is not None:
            final_mark_str = f"{attempt.final_mark:.2f} / 20"
            if attempt.final_mark >= 10.0:
                verdict = "ADMIS / VALIDÉ"
                verdict_color = "#10b981"
            else:
                verdict = "AJOURNÉ"
                verdict_color = "#ef4444"
        raw_score_str = f"{attempt.raw_score:.2f}" if attempt.raw_score is not None else "0.00"
        started_str = attempt.started_at.strftime("%d/%m/%Y %H:%M:%S") if attempt.started_at else "N/A"
        submitted_str = attempt.submitted_at.strftime("%d/%m/%Y %H:%M:%S") if attempt.submitted_at else "Non soumis"
        if attempt.started_at and attempt.submitted_at:
            mins = max(1, int((attempt.submitted_at - attempt.started_at).total_seconds() / 60))
            duration_str = f"{mins} min"

    questions = get_student_displayed_questions(exam, student, attempt, answers_map)
    total_pts = sum(q.points for q in questions) or exam.global_points or 20.0
    
    rows_html = []
    for idx, q in enumerate(questions, 1):
        ans_record = answers_map.get(q.id)
        awarded_pts = ans_record.awarded_points if ans_record and ans_record.awarded_points is not None else 0.0
        is_corr = ans_record.is_correct if ans_record else False
        
        st_ans = None
        if ans_record and ans_record.answer_payload_json:
            try:
                st_ans = json.loads(ans_record.answer_payload_json)
            except Exception:
                st_ans = ans_record.answer_payload_json
                
        corr_ans = None
        if q.correct_answers_json:
            try:
                corr_ans = json.loads(q.correct_answers_json)
            except Exception:
                corr_ans = q.correct_answers_json
                
        if ans_record is None or st_ans is None or st_ans == "" or st_ans == []:
            badge_html = '<span style="color:#64748b; font-weight:700;">⚪ NON RÉPONDU</span>'
            ans_clean = '<i>(Aucune réponse saisie)</i>'
        elif is_corr:
            badge_html = '<span style="color:#10b981; font-weight:700;">✅ CORRECT</span>'
            ans_clean = escape(str(st_ans))
        elif awarded_pts > 0:
            badge_html = f'<span style="color:#f59e0b; font-weight:700;">⚠️ PARTIEL ({awarded_pts:.2f})</span>'
            ans_clean = escape(str(st_ans))
        else:
            badge_html = '<span style="color:#ef4444; font-weight:700;">❌ FAUX</span>'
            ans_clean = escape(str(st_ans))

        prompt_clean = escape(q.prompt_markdown or "").replace("\n", "<br>")
        corr_clean = escape(str(corr_ans or "N/A"))

        rows_html.append(f"""
        <tr style="border-bottom:1px solid #e2e8f0;">
            <td style="padding:8px 10px; font-weight:700; text-align:center;">{idx}</td>
            <td style="padding:8px 10px; font-size:0.9rem;">{prompt_clean}</td>
            <td style="padding:8px 10px; font-family:monospace; font-size:0.85rem;">{ans_clean}</td>
            <td style="padding:8px 10px; font-family:monospace; font-size:0.85rem; color:#047857;">{corr_clean}</td>
            <td style="padding:8px 10px; text-align:center; font-weight:700;">{awarded_pts:.2f} / {q.points:.2f}</td>
            <td style="padding:8px 10px; text-align:center;">{badge_html}</td>
        </tr>
        """)

    table_body = "".join(rows_html)

    html_doc = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>COPIE OFFICIELLE D'ÉPREUVE - {student_name} ({student_id})</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; color: #0f172a; line-height: 1.4; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.85rem; }}
        th {{ background: #1e3a8a; color: #ffffff; padding: 10px 8px; text-align: left; }}
        td {{ vertical-align: top; }}
        @media print {{ body {{ margin: 0; }} }}
    </style>
</head>
<body>
    <div style="border: 2px solid #1e3a8a; border-radius: 8px; padding: 16px; margin-bottom: 20px; background: #f8fafc;">
        <h2 style="margin: 0 0 10px 0; color: #1e3a8a; font-size: 1.3rem;">COPIE OFFICIELLE D'ÉPREUVE & FEUILLE DE RÉPONSES</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem;">
            <div><strong>Épreuve :</strong> {exam_title} ({module_code})</div>
            <div><strong>Candidat :</strong> {student_name} ({student_id})</div>
            <div><strong>Groupe :</strong> {group_id} | <strong>Promo :</strong> {promo}</div>
            <div><strong>Statut :</strong> {status_label} | <strong>Durée :</strong> {duration_str}</div>
            <div><strong>Barème :</strong> / {exam.global_points} pts</div>
            <div><strong>NOTE FINALE :</strong> <span style="font-size:1.1rem; font-weight:800; color:{verdict_color};">{final_mark_str}</span> ({verdict})</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width:30px; text-align:center;">N°</th>
                <th>Question / Énoncé</th>
                <th style="width:25%;">Réponse Étudiant</th>
                <th style="width:25%;">Réponse Attendue</th>
                <th style="width:80px; text-align:center;">Points</th>
                <th style="width:90px; text-align:center;">Résultat</th>
            </tr>
        </thead>
        <tbody>
            {table_body}
        </tbody>
    </table>
</body>
</html>
"""
    return html_doc

def build_exam_student_copies_zip(
    exam: Optional[Exam] = None,
    db: Session = None,
    exam_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> io.BytesIO:
    """
    Génère l'archive ZIP officielle contenant les copies de tous les étudiants
    sous forme de PDF concis (conforme à la demande), de versions HTML, de JSON
    et le récapitulatif CSV.
    """
    if db is None:
        raise ValueError("Session de base de données requise.")
    if exam is None:
        if not exam_id:
            raise ValueError("exam ou exam_id doit être fourni.")
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise ValueError("Examen introuvable.")

    enrolled_students = []
    seen_ids = set()
    for g in exam.groups:
        for u in g.users:
            if u.role == "student" and u.id not in seen_ids:
                seen_ids.add(u.id)
                enrolled_students.append(u)

    sorted_students = sorted(enrolled_students, key=lambda s: (s.group_id or "", s.full_name or s.username))

    attempts_query = db.query(StudentAttempt).join(ExamSession).filter(
        ExamSession.exam_id == exam.id
    )
    if session_id:
        attempts_query = attempts_query.filter(StudentAttempt.session_id == session_id)
    attempts = attempts_query.all()
    attempts_by_student: Dict[str, StudentAttempt] = {att.student_id: att for att in attempts}

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # L'archive contient EXCLUSIVEMENT les copies PDF officielles des étudiants
        for stu in sorted_students:
            att = attempts_by_student.get(stu.id)
            answers_map: Dict[str, StudentAnswer] = {}
            if att:
                answers_map = {ans.question_id: ans for ans in att.answers}

            clean_username = "".join(c for c in stu.username if c.isalnum() or c in "_-")
            clean_id = "".join(c for c in stu.id if c.isalnum() or c in "_-")
            clean_grp = "".join(c for c in (stu.group_id or "CLASSE") if c.isalnum() or c in "_-")
            file_name = f"copie_{clean_grp}_{clean_id}_{clean_username}.pdf"

            pdf_bytes = generate_student_copy_pdf(
                exam=exam,
                student=stu,
                attempt=att,
                answers_map=answers_map
            )
            zf.writestr(file_name, pdf_bytes)

    zip_buffer.seek(0)
    return zip_buffer
