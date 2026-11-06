"""
Service d'exportation de documents académiques haute fidélité (PDF, DOCX Word, ZIP).
Génère les bulletins officiels individuels et le palmarès consolidé par spécialité / module.
"""

import io
import csv
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional

# ReportLab pour PDF haute fidélité
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.units import cm

# Python-docx pour documents Microsoft Word natifs (.docx)
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

NAVY_BLUE = colors.HexColor("#1e3a8a")
SLATE_HEADER = colors.HexColor("#0f172a")
EMERALD_GREEN = colors.HexColor("#059669")
ROSE_RED = colors.HexColor("#dc2626")
BORDER_GRAY = colors.HexColor("#cbd5e1")
BG_LIGHT_GRAY = colors.HexColor("#f8fafc")

def _get_pdf_styles():
    styles = getSampleStyleSheet()
    
    # Évite les exceptions si réexécuté
    if "RepubliqueHeader" not in styles:
        styles.add(ParagraphStyle(
            "RepubliqueHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            alignment=1, # Center
            textColor=colors.HexColor("#334155")
        ))
    if "BulletinTitle" not in styles:
        styles.add(ParagraphStyle(
            "BulletinTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=NAVY_BLUE
        ))
    if "SectionHeader" not in styles:
        styles.add(ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=NAVY_BLUE,
            spaceAfter=4
        ))
    if "TableCell" not in styles:
        styles.add(ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1e293b")
        ))
    if "TableCellBold" not in styles:
        styles.add(ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0f172a")
        ))
    if "VerdictLarge" not in styles:
        styles.add(ParagraphStyle(
            "VerdictLarge",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=1,
            textColor=colors.HexColor("#ffffff")
        ))
    return styles

def generate_student_bulletin_pdf(b: Dict[str, Any]) -> bytes:
    """Génère le bulletin officiel individuel d'un étudiant au format PDF haute résolution."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = _get_pdf_styles()
    story = []

    # 1. En-tête officiel
    story.append(Paragraph("RÉPUBLIQUE ALGÉRIENNE DÉMOCRATIQUE ET POPULAIRE", styles["RepubliqueHeader"]))
    story.append(Paragraph("MINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR ET DE LA RECHERCHE SCIENTIFIQUE", styles["RepubliqueHeader"]))
    story.append(Paragraph("DIRECTION DES EXAMENS • CENTRE D'ÉVALUATION ET DE CERTIFICATION", styles["RepubliqueHeader"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY_BLUE, spaceAfter=12))

    story.append(Paragraph("BULLETIN OFFICIEL DES NOTES & RELEVÉ DE COMPÉTENCES", styles["BulletinTitle"]))
    story.append(Paragraph("Session Principale 2025 - 2026 • Épreuves Officielles sur Machine", styles["RepubliqueHeader"]))
    story.append(Spacer(1, 14))

    # 2. Carte d'identité du candidat
    date_str = datetime.now().strftime("%d/%m/%Y")
    info_data = [
        [
            Paragraph(f"<b>Matricule :</b> {b.get('student_id', '—')}", styles["TableCell"]),
            Paragraph(f"<b>Nom & Prénom :</b> {b.get('full_name', '—')}", styles["TableCellBold"])
        ],
        [
            Paragraph(f"<b>Identifiant :</b> {b.get('username', '—')}", styles["TableCell"]),
            Paragraph(f"<b>Spécialité :</b> {b.get('speciality', '—')}", styles["TableCellBold"])
        ],
        [
            Paragraph(f"<b>Code d'accès LAN :</b> {b.get('plain_password', '—')}", styles["TableCell"]),
            Paragraph(f"<b>Date de délivrance :</b> {date_str}", styles["TableCell"])
        ]
    ]
    t_info = Table(info_data, colWidths=[240, 280])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT_GRAY),
        ('BOX', (0,0), (-1,-1), 1, BORDER_GRAY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 16))

    # 3. Tableau des 4 Piliers Fondamentaux
    story.append(Paragraph("1. ÉVALUATION DES 4 PILIERS FONDAMENTAUX (TESTS DIAGNOSTIQUES)", styles["SectionHeader"]))
    
    pillars_order = [
        ("ALGO", "Algorithmique Fondamentale"),
        ("PYTHON_INIT", "Programmation Python"),
        ("CRYPTO", "Cryptographie & Sécurité"),
        ("LINUX_ADMIN", "Administration Système Linux")
    ]
    
    fund_table_data = [
        ["Pilier / Module", "Code", "Note /20", "Statut / Appréciation"]
    ]
    
    fundamentals = b.get("fundamentals", {})
    for code, label in pillars_order:
        p_data = fundamentals.get(code, {})
        score = p_data.get("score")
        if score is not None:
            score_str = f"{score:.2f} / 20"
            if score >= 16:
                appr = "Excellent (Maîtrise complète)"
            elif score >= 14:
                appr = "Bien (Acquis solides)"
            elif score >= 12:
                appr = "Assez Bien (Acquis acceptables)"
            elif score >= 10:
                appr = "Passable (Limite)"
            else:
                appr = "Insuffisant"
        else:
            score_str = "—"
            appr = "Non évalué"
        fund_table_data.append([label, code, score_str, appr])
        
    f_avg = b.get("fundamentals_average")
    f_avg_str = f"{f_avg:.2f} / 20" if f_avg is not None else "—"
    fund_table_data.append(["MOYENNE DES 4 PILIERS FONDAMENTAUX", "", f_avg_str, "Validé" if (f_avg and f_avg >= 10) else "En cours"])

    t_fund = Table(fund_table_data, colWidths=[200, 80, 100, 140])
    t_fund.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY_BLUE),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ALIGN', (1,1), (2,-1), 'CENTER'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_fund)
    story.append(Spacer(1, 16))

    # 4. Tableau des Épreuves Officielles
    story.append(Paragraph("2. ÉPREUVES D'EXAMENS OFFICIELS (SESSION SUR MACHINE)", styles["SectionHeader"]))
    
    exams = b.get("exams", {})
    theo = exams.get("theoretical", {})
    prac = exams.get("practical", {})
    
    th_score = theo.get("score")
    pr_score = prac.get("score")
    
    exam_table_data = [
        ["Type d'Épreuve", "Intitulé du Sujet", "Note /20", "Statut"],
        [
            "Examen Théorique",
            theo.get("title", "Examen Théorique"),
            f"{th_score:.2f} / 20" if th_score is not None else "—",
            "Épreuve Validée" if (th_score and th_score >= 10) else ("Non Validée" if th_score else "En attente")
        ],
        [
            "Épreuve Pratique",
            prac.get("title", "Épreuve Pratique Machine"),
            f"{pr_score:.2f} / 20" if pr_score is not None else "—",
            "Épreuve Validée" if (pr_score and pr_score >= 10) else ("Non Validée" if pr_score else "En attente")
        ]
    ]
    ex_avg = b.get("exams_average")
    ex_avg_str = f"{ex_avg:.2f} / 20" if ex_avg is not None else "—"
    exam_table_data.append(["MOYENNE DES ÉPREUVES OFFICIELLES", "", ex_avg_str, "Validé" if (ex_avg and ex_avg >= 10) else "En attente"])

    t_exam = Table(exam_table_data, colWidths=[140, 200, 90, 90])
    t_exam.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY_BLUE),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ALIGN', (2,1), (3,-1), 'CENTER'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_exam)
    story.append(Spacer(1, 16))

    # 5. Bilan Général & Décision du Jury
    story.append(Paragraph("3. DÉLIBÉRATION GÉNÉRALE DU JURY D'EXAMEN", styles["SectionHeader"]))
    
    gen_avg = b.get("general_average")
    is_pass = b.get("is_pass", False)
    verdict_label = b.get("verdict_label", "EN ATTENTE")
    
    gen_avg_str = f"{gen_avg:.2f} / 20" if gen_avg is not None else "—"
    box_color = EMERALD_GREEN if is_pass else (ROSE_RED if gen_avg is not None else colors.HexColor("#64748b"))

    decision_data = [
        [
            Paragraph(f"<b>MOYENNE GÉNÉRALE ACADÉMIQUE :</b> {gen_avg_str}", styles["VerdictLarge"]),
            Paragraph(f"<b>DÉCISION DU JURY :</b> {verdict_label}", styles["VerdictLarge"])
        ]
    ]
    t_decision = Table(decision_data, colWidths=[260, 260])
    t_decision.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), box_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_decision)
    story.append(Spacer(1, 24))

    # 6. Signatures officielles
    sig_data = [
        [
            Paragraph("<b>Le Responsable Pédagogique</b><br/><br/><br/><i>Signature & Cachet</i>", styles["TableCellBold"]),
            Paragraph("<b>Le Président du Jury des Examens</b><br/><br/><br/><i>Signature & Visa Officiel</i>", styles["TableCellBold"])
        ]
    ]
    t_sig = Table(sig_data, colWidths=[260, 260])
    t_sig.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 0.5, BORDER_GRAY),
        ('BOX', (1,0), (1,0), 0.5, BORDER_GRAY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(KeepTogether([t_sig]))

    doc.build(story)
    return buf.getvalue()

def generate_student_bulletin_docx(b: Dict[str, Any]) -> bytes:
    """Génère le bulletin officiel individuel d'un étudiant au format Microsoft Word (.docx)."""
    doc = docx.Document()
    
    # Configuration des marges (2 cm)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # 1. En-tête
    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_rep = p_rep.add_run("RÉPUBLIQUE ALGÉRIENNE DÉMOCRATIQUE ET POPULAIRE\nMINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR ET DE LA RECHERCHE SCIENTIFIQUE\nDIRECTION DES EXAMENS • CENTRE DE CERTIFICATION")
    r_rep.font.size = Pt(9)
    r_rep.font.bold = True
    r_rep.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    doc.add_paragraph() # Spacer

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("BULLETIN OFFICIEL DES NOTES & RELEVÉ DE COMPÉTENCES")
    r_title.font.size = Pt(15)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Session Principale 2025 - 2026 • Épreuves Officielles sur Machine")
    r_sub.font.size = Pt(10)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # 2. Carte d'identité du candidat
    date_str = datetime.now().strftime("%d/%m/%Y")
    t_info = doc.add_table(rows=3, cols=2)
    t_info.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    rows_info = [
        (f"Matricule : {b.get('student_id', '—')}", f"Nom & Prénom : {b.get('full_name', '—')}"),
        (f"Identifiant : {b.get('username', '—')}", f"Spécialité : {b.get('speciality', '—')}"),
        (f"Mot de passe LAN : {b.get('plain_password', '—')}", f"Date de délivrance : {date_str}")
    ]
    for idx, (c1, c2) in enumerate(rows_info):
        t_info.rows[idx].cells[0].text = c1
        t_info.rows[idx].cells[1].text = c2
        t_info.rows[idx].cells[0].paragraphs[0].runs[0].font.size = Pt(9.5)
        t_info.rows[idx].cells[1].paragraphs[0].runs[0].font.size = Pt(9.5)
        t_info.rows[idx].cells[1].paragraphs[0].runs[0].font.bold = True

    # Shading sur t_info
    shd_xml = f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>'
    for row in t_info.rows:
        for cell in row.cells:
            cell._tc.get_or_add_tcPr().append(parse_xml(shd_xml))

    doc.add_paragraph() # Spacer

    # 3. 4 Piliers Fondamentaux
    p_h1 = doc.add_paragraph()
    r_h1 = p_h1.add_run("1. ÉVALUATION DES 4 PILIERS FONDAMENTAUX (TESTS DIAGNOSTIQUES)")
    r_h1.font.bold = True
    r_h1.font.size = Pt(11)
    r_h1.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    t_fund = doc.add_table(rows=1, cols=4)
    t_fund.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Pilier / Module", "Code", "Note /20", "Statut / Appréciation"]
    hdr_cells = t_fund.rows[0].cells
    for i, h_text in enumerate(headers):
        hdr_cells[i].text = h_text
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        hdr_cells[i]._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="1E3A8A"/>'))

    pillars_order = [
        ("ALGO", "Algorithmique Fondamentale"),
        ("PYTHON_INIT", "Programmation Python"),
        ("CRYPTO", "Cryptographie & Sécurité"),
        ("LINUX_ADMIN", "Administration Système Linux")
    ]
    fundamentals = b.get("fundamentals", {})
    for code, label in pillars_order:
        p_data = fundamentals.get(code, {})
        score = p_data.get("score")
        if score is not None:
            score_str = f"{score:.2f} / 20"
            appr = "Excellent" if score >= 16 else ("Bien" if score >= 14 else ("Assez Bien" if score >= 12 else ("Passable" if score >= 10 else "Insuffisant")))
        else:
            score_str = "—"
            appr = "Non évalué"
        row_c = t_fund.add_row().cells
        row_c[0].text = label
        row_c[1].text = code
        row_c[2].text = score_str
        row_c[3].text = appr
        for c in row_c:
            c.paragraphs[0].runs[0].font.size = Pt(9)

    f_avg = b.get("fundamentals_average")
    f_avg_str = f"{f_avg:.2f} / 20" if f_avg is not None else "—"
    row_sub = t_fund.add_row().cells
    row_sub[0].text = "MOYENNE DES 4 PILIERS FONDAMENTAUX"
    row_sub[1].text = ""
    row_sub[2].text = f_avg_str
    row_sub[3].text = "Validé" if (f_avg and f_avg >= 10) else "En cours"
    for c in row_sub:
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
        c._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="E2E8F0"/>'))

    doc.add_paragraph() # Spacer

    # 4. Examens Officiels
    p_h2 = doc.add_paragraph()
    r_h2 = p_h2.add_run("2. ÉPREUVES D'EXAMENS OFFICIELS (SESSION SUR MACHINE)")
    r_h2.font.bold = True
    r_h2.font.size = Pt(11)
    r_h2.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    t_exam = doc.add_table(rows=1, cols=4)
    t_exam.alignment = WD_TABLE_ALIGNMENT.CENTER
    ex_hdrs = ["Type d'Épreuve", "Intitulé du Sujet", "Note /20", "Statut"]
    for i, h_text in enumerate(ex_hdrs):
        t_exam.rows[0].cells[i].text = h_text
        t_exam.rows[0].cells[i].paragraphs[0].runs[0].font.bold = True
        t_exam.rows[0].cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        t_exam.rows[0].cells[i]._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="1E3A8A"/>'))

    exams = b.get("exams", {})
    theo = exams.get("theoretical", {})
    prac = exams.get("practical", {})
    th_score = theo.get("score")
    pr_score = prac.get("score")

    r1 = t_exam.add_row().cells
    r1[0].text = "Examen Théorique"
    r1[1].text = theo.get("title", "Examen Théorique")
    r1[2].text = f"{th_score:.2f} / 20" if th_score is not None else "—"
    r1[3].text = "Épreuve Validée" if (th_score and th_score >= 10) else ("Non Validée" if th_score else "En attente")

    r2 = t_exam.add_row().cells
    r2[0].text = "Épreuve Pratique"
    r2[1].text = prac.get("title", "Épreuve Pratique Machine")
    r2[2].text = f"{pr_score:.2f} / 20" if pr_score is not None else "—"
    r2[3].text = "Épreuve Validée" if (pr_score and pr_score >= 10) else ("Non Validée" if pr_score else "En attente")

    ex_avg = b.get("exams_average")
    ex_avg_str = f"{ex_avg:.2f} / 20" if ex_avg is not None else "—"
    r_sub_ex = t_exam.add_row().cells
    r_sub_ex[0].text = "MOYENNE DES ÉPREUVES OFFICIELLES"
    r_sub_ex[1].text = ""
    r_sub_ex[2].text = ex_avg_str
    r_sub_ex[3].text = "Validé" if (ex_avg and ex_avg >= 10) else "En attente"
    for c in r_sub_ex:
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.size = Pt(9)
        c._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="E2E8F0"/>'))

    doc.add_paragraph() # Spacer

    # 5. Délibération Finale & Décision
    gen_avg = b.get("general_average")
    is_pass = b.get("is_pass", False)
    verdict_label = b.get("verdict_label", "EN ATTENTE")
    gen_avg_str = f"{gen_avg:.2f} / 20" if gen_avg is not None else "—"

    t_dec = doc.add_table(rows=1, cols=2)
    t_dec.alignment = WD_TABLE_ALIGNMENT.CENTER
    fill_hex = "059669" if is_pass else ("DC2626" if gen_avg is not None else "64748B")
    
    t_dec.rows[0].cells[0].text = f"MOYENNE GÉNÉRALE : {gen_avg_str}"
    t_dec.rows[0].cells[1].text = f"DÉCISION DU JURY : {verdict_label}"
    for cell in t_dec.rows[0].cells:
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(11)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

    doc.add_paragraph() # Spacer
    doc.add_paragraph()

    # 6. Signatures
    t_sig = doc.add_table(rows=2, cols=2)
    t_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_sig.rows[0].cells[0].text = "Le Responsable Pédagogique"
    t_sig.rows[0].cells[1].text = "Le Président du Jury des Examens"
    t_sig.rows[1].cells[0].text = "\n\nSignature & Cachet\n"
    t_sig.rows[1].cells[1].text = "\n\nVisa Officiel & Décision\n"
    for r in t_sig.rows:
        for c in r.cells:
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].runs[0].font.size = Pt(9.5)
            c.paragraphs[0].runs[0].font.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def _sort_bulletins(bulletins: List[Dict[str, Any]], sort_by_module: Optional[str] = None) -> List[Dict[str, Any]]:
    """Trie la liste des bulletins selon le module spécifié ou la moyenne générale."""
    if not sort_by_module or sort_by_module == "AVG":
        return sorted(
            bulletins,
            key=lambda x: (x.get("general_average") is not None, x.get("general_average") or -1),
            reverse=True
        )
    elif sort_by_module in ["ALGO", "PYTHON_INIT", "CRYPTO", "LINUX_ADMIN"]:
        return sorted(
            bulletins,
            key=lambda x: (
                x.get("fundamentals", {}).get(sort_by_module, {}).get("score") is not None,
                x.get("fundamentals", {}).get(sort_by_module, {}).get("score") or -1
            ),
            reverse=True
        )
    elif sort_by_module == "THEO":
        return sorted(
            bulletins,
            key=lambda x: (
                x.get("exams", {}).get("theoretical", {}).get("score") is not None,
                x.get("exams", {}).get("theoretical", {}).get("score") or -1
            ),
            reverse=True
        )
    elif sort_by_module == "PRAC":
        return sorted(
            bulletins,
            key=lambda x: (
                x.get("exams", {}).get("practical", {}).get("score") is not None,
                x.get("exams", {}).get("practical", {}).get("score") or -1
            ),
            reverse=True
        )
    return bulletins

def generate_speciality_results_pdf(
    speciality_name: str,
    bulletins: List[Dict[str, Any]],
    sort_by_module: Optional[str] = None
) -> bytes:
    """Génère le palmarès consolidé des résultats par spécialité / module au format PDF Paysage."""
    sorted_b = _sort_bulletins(bulletins, sort_by_module)
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    styles = _get_pdf_styles()
    story = []

    # Titre officiel
    story.append(Paragraph("MINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR • DIRECTION DES EXAMENS", styles["RepubliqueHeader"]))
    story.append(Paragraph(f"PALMARÈS OFFICIEL DES RÉSULTATS ACADÉMIQUES — SPÉCIALITÉ : {speciality_name.upper()}", styles["BulletinTitle"]))
    
    sort_desc = f"(Classement ordonné selon les performances du module : {sort_by_module})" if sort_by_module and sort_by_module != "AVG" else "(Classement ordonné par Moyenne Générale décroissante)"
    story.append(Paragraph(f"{sort_desc} • Session Principale 2026", styles["RepubliqueHeader"]))
    story.append(Spacer(1, 10))

    # Calcul des métriques KPI
    total = len(sorted_b)
    passes = sum(1 for b in sorted_b if b.get("is_pass"))
    fails = total - passes
    pass_rate = round((passes / total * 100), 1) if total > 0 else 0.0
    valid_avgs = [b.get("general_average") for b in sorted_b if b.get("general_average") is not None]
    promo_avg = round(sum(valid_avgs) / len(valid_avgs), 2) if valid_avgs else 0.0

    kpi_data = [
        [
            Paragraph(f"<b>Effectif Total :</b> {total} candidats", styles["TableCellBold"]),
            Paragraph(f"<b>Admis :</b> {passes}", styles["TableCellBold"]),
            Paragraph(f"<b>Ajournés :</b> {fails}", styles["TableCellBold"]),
            Paragraph(f"<b>Taux de Réussite :</b> {pass_rate}%", styles["TableCellBold"]),
            Paragraph(f"<b>Moyenne Promo :</b> {promo_avg:.2f} / 20", styles["TableCellBold"]),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[150, 130, 130, 160, 170])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, BORDER_GRAY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 12))

    # Table des étudiants
    headers = [
        "N°", "Matricule", "Nom & Prénom", "Spécialité",
        "ALGO", "PYTHON", "CRYPTO", "LINUX",
        "Théorie", "Pratique", "Moyenne", "Décision"
    ]
    table_data = [headers]

    for rank, b in enumerate(sorted_b, start=1):
        f = b.get("fundamentals", {})
        ex = b.get("exams", {})
        
        algo = f.get("ALGO", {}).get("score")
        py = f.get("PYTHON_INIT", {}).get("score")
        cry = f.get("CRYPTO", {}).get("score")
        lin = f.get("LINUX_ADMIN", {}).get("score")
        
        th = ex.get("theoretical", {}).get("score")
        pr = ex.get("practical", {}).get("score")
        
        avg = b.get("general_average")
        verdict = "ADMIS" if b.get("is_pass") else "AJOURNÉ"
        
        table_data.append([
            str(rank),
            b.get("student_id", "—"),
            b.get("full_name", "—")[:22],
            b.get("speciality", "—"),
            f"{algo:.1f}" if algo is not None else "—",
            f"{py:.1f}" if py is not None else "—",
            f"{cry:.1f}" if cry is not None else "—",
            f"{lin:.1f}" if lin is not None else "—",
            f"{th:.1f}" if th is not None else "—",
            f"{pr:.1f}" if pr is not None else "—",
            f"{avg:.2f}" if avg is not None else "—",
            verdict
        ])

    t_main = Table(table_data, colWidths=[25, 80, 150, 75, 48, 48, 48, 48, 55, 55, 62, 70])
    
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), NAVY_BLUE),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ALIGN', (0,1), (0,-1), 'CENTER'),
        ('ALIGN', (4,1), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]
    
    # Alternance des couleurs et coloration de la décision
    for row_idx, row in enumerate(table_data[1:], start=1):
        if row_idx % 2 == 0:
            t_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#f8fafc")))
        if row[11] == "ADMIS":
            t_style.append(('TEXTCOLOR', (11, row_idx), (11, row_idx), EMERALD_GREEN))
            t_style.append(('FONTNAME', (11, row_idx), (11, row_idx), 'Helvetica-Bold'))
        else:
            t_style.append(('TEXTCOLOR', (11, row_idx), (11, row_idx), ROSE_RED))
            t_style.append(('FONTNAME', (11, row_idx), (11, row_idx), 'Helvetica-Bold'))

    t_main.setStyle(TableStyle(t_style))
    story.append(t_main)
    story.append(Spacer(1, 16))

    # Bloc signatures
    sig_data = [
        [
            Paragraph("<b>Le Chef du Département / Responsable de Spécialité</b><br/><br/><i>Visa & Signature</i>", styles["TableCellBold"]),
            Paragraph("<b>Le Président du Jury d'Établissement</b><br/><br/><i>Pour la Délibération Officielle</i>", styles["TableCellBold"])
        ]
    ]
    t_sig = Table(sig_data, colWidths=[370, 370])
    t_sig.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(KeepTogether([t_sig]))

    doc.build(story)
    return buf.getvalue()

def generate_speciality_results_docx(
    speciality_name: str,
    bulletins: List[Dict[str, Any]],
    sort_by_module: Optional[str] = None
) -> bytes:
    """Génère le palmarès consolidé des résultats par spécialité au format Word (.docx) Paysage."""
    sorted_b = _sort_bulletins(bulletins, sort_by_module)
    doc = docx.Document()
    
    # Orientation Paysage
    section = doc.sections[-1]
    section.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11.69)
    section.page_height = Inches(8.27)
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    # Titre
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_h = p_h.add_run(f"PALMARÈS OFFICIEL DES RÉSULTATS ACADÉMIQUES — SPÉCIALITÉ : {speciality_name.upper()}")
    r_h.font.size = Pt(14)
    r_h.font.bold = True
    r_h.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    sort_desc = f"(Classement ordonné selon les performances du module : {sort_by_module})" if sort_by_module and sort_by_module != "AVG" else "(Classement ordonné par Moyenne Générale décroissante)"
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run(f"{sort_desc} • Session Principale 2026")
    r_sub.font.size = Pt(9.5)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # KPIs
    total = len(sorted_b)
    passes = sum(1 for b in sorted_b if b.get("is_pass"))
    fails = total - passes
    pass_rate = round((passes / total * 100), 1) if total > 0 else 0.0
    valid_avgs = [b.get("general_average") for b in sorted_b if b.get("general_average") is not None]
    promo_avg = round(sum(valid_avgs) / len(valid_avgs), 2) if valid_avgs else 0.0

    p_kpi = doc.add_paragraph()
    p_kpi.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_kpi = p_kpi.add_run(f"Effectif Total : {total} | Admis : {passes} | Ajournés : {fails} | Taux de Réussite : {pass_rate}% | Moyenne de Promo : {promo_avg:.2f} / 20")
    r_kpi.font.bold = True
    r_kpi.font.size = Pt(9.5)

    # Tableau des résultats
    headers = [
        "N°", "Matricule", "Nom & Prénom", "Spécialité",
        "ALGO", "PYTHON", "CRYPTO", "LINUX",
        "Théorie", "Pratique", "Moyenne", "Décision"
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    for i, h_text in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = h_text
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8.5)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="1E3A8A"/>'))

    for rank, b in enumerate(sorted_b, start=1):
        f = b.get("fundamentals", {})
        ex = b.get("exams", {})
        
        algo = f.get("ALGO", {}).get("score")
        py = f.get("PYTHON_INIT", {}).get("score")
        cry = f.get("CRYPTO", {}).get("score")
        lin = f.get("LINUX_ADMIN", {}).get("score")
        
        th = ex.get("theoretical", {}).get("score")
        pr = ex.get("practical", {}).get("score")
        
        avg = b.get("general_average")
        verdict = "ADMIS" if b.get("is_pass") else "AJOURNÉ"

        row_cells = t.add_row().cells
        row_vals = [
            str(rank),
            b.get("student_id", "—"),
            b.get("full_name", "—"),
            b.get("speciality", "—"),
            f"{algo:.1f}" if algo is not None else "—",
            f"{py:.1f}" if py is not None else "—",
            f"{cry:.1f}" if cry is not None else "—",
            f"{lin:.1f}" if lin is not None else "—",
            f"{th:.1f}" if th is not None else "—",
            f"{pr:.1f}" if pr is not None else "—",
            f"{avg:.2f}" if avg is not None else "—",
            verdict
        ]
        for col_idx, val in enumerate(row_vals):
            row_cells[col_idx].text = val
            p = row_cells[col_idx].paragraphs[0]
            p.runs[0].font.size = Pt(8)
            if col_idx == 11:
                p.runs[0].font.bold = True
                p.runs[0].font.color.rgb = RGBColor(0x05, 0x96, 0x69) if verdict == "ADMIS" else RGBColor(0xDC, 0x26, 0x26)

    doc.add_paragraph() # Spacer
    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_sig = p_sig.add_run("Le Président du Jury des Examens\n\n[Cachet & Signature]")
    r_sig.font.size = Pt(9.5)
    r_sig.font.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def generate_bulk_bulletins_zip(
    bulletins: List[Dict[str, Any]],
    format_type: str = "pdf"
) -> bytes:
    """
    Exporte l'ensemble des bulletins étudiants dans une archive ZIP.
    format_type: 'pdf', 'docx', ou 'all' (les deux).
    Inclut également un fichier CSV récapitulatif sans redondance.
    """
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Génération de chaque bulletin individuel
        for b in bulletins:
            stu_id = b.get("student_id", "ETU")
            uname = b.get("username", "user")
            clean_name = f"bulletin_{stu_id}_{uname}"
            
            if format_type in ["pdf", "all"]:
                pdf_bytes = generate_student_bulletin_pdf(b)
                zf.writestr(f"{clean_name}.pdf", pdf_bytes)
                
            if format_type in ["docx", "all"]:
                docx_bytes = generate_student_bulletin_docx(b)
                zf.writestr(f"{clean_name}.docx", docx_bytes)

        # 2. Ajout du récapitulatif CSV consolidé dans le ZIP
        csv_buf = io.StringIO()
        csv_buf.write("\ufeff") # BOM Excel
        writer = csv.writer(csv_buf, delimiter=";")
        writer.writerow([
            "Matricule", "Identifiant", "Nom Complet", "Specialite", "Mot de passe LAN",
            "Algo Fondamentale /20", "Python Init /20", "Crypto /20", "Linux Admin /20",
            "Moyenne Piliers /20", "Examen Theorique /20", "Epreuve Pratique /20",
            "Moyenne Examens /20", "Moyenne Generale /20", "Decision Jury"
        ])
        for b in bulletins:
            f = b.get("fundamentals", {})
            ex = b.get("exams", {})
            writer.writerow([
                b.get("student_id"),
                b.get("username"),
                b.get("full_name"),
                b.get("speciality"),
                b.get("plain_password"),
                f.get("ALGO", {}).get("score", ""),
                f.get("PYTHON_INIT", {}).get("score", ""),
                f.get("CRYPTO", {}).get("score", ""),
                f.get("LINUX_ADMIN", {}).get("score", ""),
                b.get("fundamentals_average", ""),
                ex.get("theoretical", {}).get("score", ""),
                ex.get("practical", {}).get("score", ""),
                b.get("exams_average", ""),
                b.get("general_average", ""),
                b.get("verdict", "")
            ])
        zf.writestr("RECAPITULATIF_PALMARES.csv", csv_buf.getvalue().encode("utf-8-sig"))

        # 3. Fichier d'information README
        readme_content = (
            "ARCHIVE DES BULLETINS ACADÉMIQUES OFFICIELS\n"
            f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n"
            f"Nombre de bulletins inclus : {len(bulletins)}\n"
            f"Format(s) : {format_type.upper()}\n"
            "Direction des Examens et de la Scolarité.\n"
        )
        zf.writestr("README_ARCHIVE.txt", readme_content.encode("utf-8"))

    return zip_buf.getvalue()



def generate_class_sheet_pdf(data: Dict[str, Any]) -> bytes:
    """Génère le PV officiel de classe pour une spécialité et un module donné au format PDF."""
    spec_name = data.get("speciality_name", data.get("speciality", ""))
    mod_title = data.get("module_title", data.get("module_code", ""))
    students = data.get("students", [])
    class_stats = data.get("class_stats", {})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    styles = _get_pdf_styles()
    story = []

    # En-tête
    story.append(Paragraph("MINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR • DIRECTION DES EXAMENS", styles["RepubliqueHeader"]))
    story.append(Paragraph(f"PROCÈS-VERBAL ACADÉMIQUE DE CLASSE — {mod_title.upper()}", styles["BulletinTitle"]))
    story.append(Paragraph(f"Filière / Spécialité : <b>{spec_name}</b> • Année Universitaire 2025-2026", styles["RepubliqueHeader"]))
    story.append(Spacer(1, 10))

    # Tableau KPI
    enrolled = class_stats.get("enrolled_count", len(students))
    evaluated = class_stats.get("evaluated_count", 0)
    cls_avg = class_stats.get("class_average", 0.0) or 0.0
    succ_rate = class_stats.get("success_rate_percent", 0.0) or 0.0

    kpi_data = [
        [
            Paragraph(f"<b>Effectif Total :</b> {enrolled} étudiants", styles["TableCellBold"]),
            Paragraph(f"<b>Évalués :</b> {evaluated}", styles["TableCellBold"]),
            Paragraph(f"<b>Taux de Réussite :</b> {succ_rate}%", styles["TableCellBold"]),
            Paragraph(f"<b>Moyenne du Module :</b> {cls_avg:.2f} / 20", styles["TableCellBold"]),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[180, 150, 180, 230])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, BORDER_GRAY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 14))

    # Tableau des étudiants
    headers = ["N°", "Matricule", "Nom & Prénom(s)", "Note Théorique", "Note Pratique", "Moyenne Module", "Verdict"]
    t_rows = [[Paragraph(f"<b>{h}</b>", styles["TableCellBold"]) for h in headers]]

    for idx, s in enumerate(students, start=1):
        theo_str = f"{s['theoretical_score']:.2f} / 20" if s.get("theoretical_score") is not None else "—"
        prac_str = f"{s['practical_score']:.2f} / 20" if s.get("practical_score") is not None else "—"
        avg_str = f"{s['module_average']:.2f} / 20" if s.get("module_average") is not None else "—"
        
        status_val = s.get("status", "NON_ÉVALUÉ")
        if status_val == "ADMIS":
            v_color = "#059669"
            v_text = "ADMIS"
        elif status_val == "AJOURNÉ":
            v_color = "#dc2626"
            v_text = "AJOURNÉ"
        else:
            v_color = "#64748b"
            v_text = "EN COURS"

        t_rows.append([
            Paragraph(str(idx), styles["TableCell"]),
            Paragraph(f"<code>{s.get('student_id', '')}</code>", styles["TableCell"]),
            Paragraph(f"<b>{s.get('full_name', '')}</b>", styles["TableCellBold"]),
            Paragraph(theo_str, styles["TableCell"]),
            Paragraph(prac_str, styles["TableCell"]),
            Paragraph(f"<b>{avg_str}</b>", styles["TableCellBold"]),
            Paragraph(f"<font color='{v_color}'><b>{v_text}</b></font>", styles["TableCellBold"])
        ])

    table_students = Table(t_rows, colWidths=[30, 85, 230, 100, 100, 100, 95])
    table_students.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SLATE_HEADER),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GRAY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (3,1), (5,-1), 'CENTER'),
        ('ALIGN', (6,1), (6,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT_GRAY]),
    ]))
    story.append(table_students)

    doc.build(story)
    return buf.getvalue()
