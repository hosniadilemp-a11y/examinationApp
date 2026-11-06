import pytest

def test_swagger_and_openapi_completely_disabled(client):
    """Vérifie que Swagger UI (/docs, /redoc) et le schéma OpenAPI sont désactivés (404)."""
    res_docs = client.get("/docs")
    assert res_docs.status_code == 404, "Swagger /docs must return 404"
    
    res_redoc = client.get("/redoc")
    assert res_redoc.status_code == 404, "ReDoc /redoc must return 404"
    
    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 404, "OpenAPI schema /openapi.json must return 404"

def test_python_bank_stats_and_exam_generator(client, teacher_headers):
    """Vérifie les statistiques de la banque de questions Python et la génération automatique."""
    # 1. Vérifier les stats
    stats_res = client.get("/api/exams/python/bank-stats", headers=teacher_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "theoretical" in stats
    assert "practical" in stats
    assert stats["theoretical"]["total_mcqs"] > 0
    assert stats["practical"]["total_challenges"] > 0
    assert stats["theoretical"]["total_exam_marked"] > 0
    assert stats["practical"]["exam_marked_count"] > 0
    assert "chapters" in stats["theoretical"]
    assert "by_topic" in stats["practical"]

    # 2. Générer une épreuve théorique Python (sélectionne 30 questions)
    gen_theo = client.post("/api/exams/python/generate", json={
        "exam_type": "theoretical",
        "title": "Examen Théorique Python Automatisé",
        "instructions": "Épreuve théorique tirée de la banque d'entraînement.",
        "duration_minutes": 45,
        "group_ids": ["GRP-1"],
        "target_count": 30
    }, headers=teacher_headers)
    assert gen_theo.status_code == 201
    theo_exam = gen_theo.json()
    assert theo_exam["exam_type"] == "theoretical"
    assert len(theo_exam["questions"]) == 30

    # 3. Générer une épreuve pratique Python (sélectionne 10 défis)
    gen_prac = client.post("/api/exams/python/generate", json={
        "exam_type": "practical",
        "title": "Examen Pratique Python Automatisé",
        "instructions": "Épreuve pratique machine.",
        "duration_minutes": 90,
        "group_ids": ["GRP-1"],
        "target_count": 10
    }, headers=teacher_headers)
    assert gen_prac.status_code == 201
    prac_exam = gen_prac.json()
    assert prac_exam["exam_type"] == "practical"
    assert len(prac_exam["questions"]) == 10
    for q in prac_exam["questions"]:
        assert q["type"] in ["coding", "code"]

def test_class_sheet_pv_and_exports(client, teacher_headers):
    """Vérifie le PV de classe par spécialité et module avec notes théorique, pratique et moyenne."""
    # 1. Obtenir les données de la feuille de classe
    res_sheet = client.get("/api/admin/bulletins/class-sheet?speciality=DEV-IA&module_code=PYTHON_INIT", headers=teacher_headers)
    assert res_sheet.status_code == 200
    data = res_sheet.json()
    assert "students" in data
    assert "class_stats" in data
    assert isinstance(data["students"], list)

    # 2. Exporter CSV
    res_csv = client.get("/api/admin/bulletins/class-sheet/export-csv?speciality=DEV-IA&module_code=PYTHON_INIT", headers=teacher_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")

    # 3. Exporter PDF
    res_pdf = client.get("/api/admin/bulletins/class-sheet/export-pdf?speciality=DEV-IA&module_code=PYTHON_INIT", headers=teacher_headers)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers.get("content-type", "")

def test_clear_all_exams_and_scores_admin(client, admin_headers):
    """Vérifie que le Super Administrateur peut réinitialiser tous les examens et scores."""
    # Appel de purge
    res_clear = client.post("/api/admin/clear-exams-and-scores", headers=admin_headers)
    assert res_clear.status_code == 200
    data = res_clear.json()
    assert data["success"] is True
    assert "exams_deleted" in data["cleared_summary"]

