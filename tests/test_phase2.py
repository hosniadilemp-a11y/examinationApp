import pytest
import json
from backend.app.services.grading import evaluate_answer, normalize_text

# ==============================================================================
# 1. TESTS UNITAIRES DU MOTEUR DE NOTATION MATHÉMATIQUE (evaluate_answer)
# ==============================================================================

def test_grading_boolean():
    # Vrai / Faux standard (sans pénalité négative)
    score, is_correct, _ = evaluate_answer("boolean", True, True, points=1.0)
    assert score == 1.0 and is_correct is True

    score, is_correct, _ = evaluate_answer("boolean", False, True, points=1.0)
    assert score == 0.0 and is_correct is False

    # Vrai / Faux strict avec pénalité
    score, is_correct, _ = evaluate_answer("boolean", False, True, points=1.0, negative_penalty=0.5, strict_single_penalty=True)
    assert score == 0.0 and is_correct is False  # Plancher par défaut à 0.0

def test_grading_single_choice():
    score, is_correct, _ = evaluate_answer("single_choice", "b", "b", points=2.0)
    assert score == 2.0 and is_correct is True

    score, is_correct, _ = evaluate_answer("single_choice", "a", "b", points=2.0)
    assert score == 0.0 and is_correct is False

def test_grading_multi_choice_partial_credit_and_penalty():
    # Exemple officiel du cahier des charges :
    # 4 points, 3 bonnes réponses ('a', 'b', 'c'), pénalité = 0.5
    # Étudiant choisit 2 bonnes ('a', 'b') et 1 mauvaise ('d') :
    # Calcul : 2 * (4/3) - 0.5 = 2.6667 - 0.5 = 2.17
    correct_options = ["a", "b", "c"]
    user_picks = ["a", "b", "d"]
    
    score, is_correct, fb = evaluate_answer(
        q_type="multi_choice",
        user_answer=user_picks,
        correct_answers=correct_options,
        points=4.0,
        negative_penalty=0.5,
        floor_score=0.0
    )
    assert score == 2.17
    assert is_correct is False
    assert "2/3 bonne(s)" in fb
    assert "1 mauvaise(s)" in fb

def test_grading_multi_choice_all_correct():
    correct_options = ["a", "b", "c"]
    user_picks = ["a", "b", "c"]
    score, is_correct, _ = evaluate_answer("multi_choice", user_picks, correct_options, points=3.0)
    assert score == 3.0
    assert is_correct is True

def test_grading_multi_choice_floor_zero():
    # Tout faux -> ne doit pas descendre sous 0.0
    correct_options = ["a", "b"]
    user_picks = ["c", "d"]
    score, is_correct, _ = evaluate_answer("multi_choice", user_picks, correct_options, points=2.0, negative_penalty=1.0)
    assert score == 0.0
    assert is_correct is False

def test_grading_multi_choice_empty_correct_set_trap():
    # Cas particulier : aucune bonne réponse requise (question piège)
    correct_options = []
    
    # L'étudiant ne coche rien -> plein points
    score, is_correct, _ = evaluate_answer("multi_choice", [], correct_options, points=2.0)
    assert score == 2.0 and is_correct is True
    
    # L'étudiant coche une option -> pénalisé
    score, is_correct, _ = evaluate_answer("multi_choice", ["a"], correct_options, points=2.0, negative_penalty=0.5)
    assert score == 0.0 and is_correct is False

def test_grading_fill_blank_normalization():
    acceptable = ["def", "function", "définition"]
    
    # Espaces multiples et casse
    score, is_correct, _ = evaluate_answer("fill_blank", "   DEF   ", acceptable, points=1.5)
    assert score == 1.5 and is_correct is True

    score, is_correct, _ = evaluate_answer("fill_blank", "Function", acceptable, points=1.5)
    assert score == 1.5 and is_correct is True

    score, is_correct, _ = evaluate_answer("fill_blank", "lambda", acceptable, points=1.5)
    assert score == 0.0 and is_correct is False

def test_grading_matching():
    correct_pairs = {
        "Pile": "LIFO",
        "File": "FIFO",
        "Tableau": "Index O(1)",
        "Hachage": "Clé O(1)"
    }
    
    # 4 bonnes paires sur 4 (4 points)
    user_pairs = {
        "Pile": "LIFO",
        "File": "FIFO",
        "Tableau": "Index O(1)",
        "Hachage": "Clé O(1)"
    }
    score, is_correct, _ = evaluate_answer("matching", user_pairs, correct_pairs, points=4.0)
    assert score == 4.0 and is_correct is True

    # 2 bonnes paires sur 4 -> 2.0 points
    user_pairs_partial = {
        "Pile": "LIFO",
        "File": "FIFO",
        "Tableau": "FAUX",
        "Hachage": "FAUX"
    }
    score, is_correct, _ = evaluate_answer("matching", user_pairs_partial, correct_pairs, points=4.0)
    assert score == 2.0 and is_correct is False


# ==============================================================================
# 2. TESTS D'INTÉGRATION : CRUD EXAMENS ET QUESTIONS
# ==============================================================================

def test_exam_creation_and_question_management(client, admin_headers, teacher_headers):
    # L'administrateur affecte d'abord le professeur au module PYTHON_INIT
    client.post(
        "/api/modules/PYTHON_INIT/teachers",
        headers=admin_headers,
        json={"teacher_id": "prof-01", "module_code": "PYTHON_INIT"}
    )
    
    # Le professeur crée un examen pour PYTHON_INIT
    res_exam = client.post(
        "/api/exams",
        headers=teacher_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Final Python 2026",
            "instructions": "Calculatrice interdite. Plein écran requis.",
            "duration_minutes": 90,
            "global_points": 20.0,
            "group_ids": ["GRP-1"]
        }
    )
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]
    
    # Le professeur ajoute une question QCM
    res_q = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=teacher_headers,
        json={
            "ordering": 1,
            "type": "single_choice",
            "prompt_markdown": "Quel type est immuable ?\n```python\nx = (1, 2)\n```",
            "points": 2.0,
            "negative_penalty": 0.5,
            "options_json": json.dumps([{"id": "a", "text": "tuple"}, {"id": "b", "text": "list"}]),
            "correct_answers_json": json.dumps("a")
        }
    )
    assert res_q.status_code == 201
    q_id = res_q.json()["id"]
    
    # Vérification des détails de l'examen
    res_detail = client.get(f"/api/exams/{exam_id}", headers=teacher_headers)
    assert res_detail.status_code == 200
    data = res_detail.json()
    assert data["question_count"] == 1
    assert data["questions"][0]["id"] == q_id

def test_teacher_forbidden_on_unassigned_module(client, teacher_headers):
    # Le professeur Martin n'est PAS affecté au module CRYPTO
    res = client.post(
        "/api/exams",
        headers=teacher_headers,
        json={
            "module_code": "CRYPTO",
            "title": "Examen Crypto Interdit",
            "duration_minutes": 60
        }
    )
    assert res.status_code == 403
    assert "affecté au module" in res.json()["detail"].lower()

def test_batch_import_and_export_questions_json(client, admin_headers):
    # Création d'un examen par l'admin
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={
            "module_code": "PYTHON_INIT",
            "title": "Examen Test Import Batch",
            "duration_minutes": 45
        }
    )
    exam_id = res_exam.json()["id"]
    
    # Import par lot de 2 questions
    batch_payload = [
        {
            "ordering": 1,
            "type": "boolean",
            "prompt_markdown": "Python est un langage compilé ?",
            "points": 1.0,
            "negative_penalty": 0.5,
            "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
            "correct_answers_json": json.dumps(False)
        },
        {
            "ordering": 2,
            "type": "fill_blank",
            "prompt_markdown": "Mot clé pour les fonctions :",
            "points": 1.0,
            "negative_penalty": 0.0,
            "options_json": json.dumps([]),
            "correct_answers_json": json.dumps(["def"])
        }
    ]
    
    res_import = client.post(
        f"/api/exams/{exam_id}/questions/import-json",
        headers=admin_headers,
        json=batch_payload
    )
    assert res_import.status_code == 200
    assert res_import.json()["imported_count"] == 2
    
    # Export JSON des questions
    res_export = client.get(f"/api/exams/{exam_id}/questions/export-json", headers=admin_headers)
    assert res_export.status_code == 200
    exported_data = res_export.json()
    assert len(exported_data) == 2
    assert exported_data[0]["type"] == "boolean"
    assert exported_data[1]["type"] == "fill_blank"


# ==============================================================================
# 3. TESTS DES 4 MODULES D'ENTRAÎNEMENT LIBRE (24h/24)
# ==============================================================================

def test_practice_modules_list(client, student_headers):
    res = client.get("/api/practice/modules", headers=student_headers)
    assert res.status_code == 200
    modules = res.json()
    assert len(modules) == 4
    codes = [m["code"] for m in modules]
    assert "ALGO" in codes
    assert "PYTHON_INIT" in codes
    assert "CRYPTO" in codes
    assert "LINUX_ADMIN" in codes
    for m in modules:
        assert m["question_count"] == 30

def test_practice_get_questions_student_view_secrecy(client, student_headers):
    # Vérifie que les 30 questions de la banque sont renvoyées par défaut et que les réponses exactes sont masquées
    res = client.get("/api/practice/exams/PYTHON_INIT/questions", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["module_code"] == "PYTHON_INIT"
    assert data["total_questions"] == 30
    
    first_q = data["questions"][0]
    assert "id" in first_q
    assert "prompt_markdown" in first_q
    assert "options" in first_q
    assert "correct_answers_json" not in first_q
    assert "correct_answer" not in first_q

    # Test du tirage aléatoire de 20 questions parmi les 30 (REV-10)
    res_20 = client.get("/api/practice/exams/PYTHON_INIT/questions?count=20", headers=student_headers)
    assert res_20.status_code == 200
    data_20 = res_20.json()
    assert data_20["total_questions"] == 20
    assert len(data_20["questions"]) == 20
    # Vérification que toutes les 20 questions tirées sont uniques
    q_ids_20 = [q["id"] for q in data_20["questions"]]
    assert len(set(q_ids_20)) == 20

    # Vérification du double brassage (options avec id et text préservés)
    single_q = next((q for q in data_20["questions"] if q["type"] == "single_choice"), None)
    if single_q and isinstance(single_q["options"], list):
        assert len(single_q["options"]) > 0
        assert "id" in single_q["options"][0]
        assert "text" in single_q["options"][0]

def test_practice_submit_and_instant_scoring(client, student_headers):
    # Soumission de réponses pour l'entraînement Python
    # Q1 est un boolean : "Les tuples sont mutables" -> Réponse attendue : False
    payload = {
        "answers": {
            "PRACTICE-PYTHON_INIT-1": False,  # Bonne réponse (+1.0)
            "PRACTICE-PYTHON_INIT-4": "lambda"  # Q4 est fill_blank: fonction anonyme -> "lambda" (+1.0)
        }
    }
    
    res = client.post("/api/practice/exams/PYTHON_INIT/submit", headers=student_headers, json=payload)
    assert res.status_code == 200
    result = res.json()
    
    assert result["module_code"] == "PYTHON_INIT"
    assert result["total_awarded"] >= 2.0
    assert result["max_possible"] > 0
    assert "grade_20" in result
    assert "percentage" in result
    assert len(result["detailed_results"]) == 30
    
    # Vérification des explications de Q1 et Q4
    q1_res = next(r for r in result["detailed_results"] if r["question_id"] == "PRACTICE-PYTHON_INIT-1")
    assert q1_res["is_correct"] is True
    assert q1_res["awarded_points"] == 1.0
    
    q4_res = next(r for r in result["detailed_results"] if r["question_id"] == "PRACTICE-PYTHON_INIT-4")
    assert q4_res["is_correct"] is True
    assert q4_res["awarded_points"] == 1.0

def test_practice_all_modules_loaded(client, student_headers):
    # Vérifie que les 4 banques de 30 questions se chargent sans aucune erreur
    for mod_code in ["ALGO", "PYTHON_INIT", "CRYPTO", "LINUX_ADMIN"]:
        res = client.get(f"/api/practice/exams/{mod_code}/questions", headers=student_headers)
        assert res.status_code == 200
        assert res.json()["total_questions"] == 30

def test_exam_templates_listing(client, teacher_headers):
    res = client.get("/api/exams/templates", headers=teacher_headers)
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 3
    t_ids = [t["template_id"] for t in templates]
    assert "template_exam_python" in t_ids
    assert "template_exam_linux" in t_ids
    assert "template_exam_crypto" in t_ids
    
    # Check details of python template
    py_t = next(t for t in templates if t["template_id"] == "template_exam_python")
    assert py_t["module_code"] == "PYTHON_INIT"
    assert py_t["question_count"] == 8
    assert py_t["global_points"] == 20.0

def test_exam_template_loading_and_decoupling(client, teacher_headers):
    # Charge le modèle officiel Python (REV-13)
    res = client.post("/api/exams/templates/template_exam_python/load", headers=teacher_headers)
    assert res.status_code == 201
    exam = res.json()
    exam_id = exam["id"]
    assert exam["module_code"] == "PYTHON_INIT"
    assert exam["question_count"] == 8
    assert exam["global_points"] == 20.0
    assert "DEV-IA" in exam["assigned_groups"]
    
    # Vérification du découplage (REV-15) : l'examen est créé en base sans session active
    detail_res = client.get(f"/api/exams/{exam_id}", headers=teacher_headers)
    assert detail_res.status_code == 200
    assert len(detail_res.json()["questions"]) == 8
    
    # Vérifie que la liste des sessions proctor n'a pas été polluée prématurément
    sess_res = client.get("/api/proctor/sessions", headers=teacher_headers)
    assert sess_res.status_code == 200
    active_for_exam = [s for s in sess_res.json() if s["exam_id"] == exam_id]
    assert len(active_for_exam) == 0  # Aucune session prématurément ouverte !

def test_exam_template_import_json_payload(client, teacher_headers):
    payload = {
        "module_code": "PYTHON_INIT",
        "title": "Examen Custom Importé",
        "instructions": "Directives personnalisées",
        "duration_minutes": 30,
        "global_points": 20.0,
        "group_ids": ["DEV-IA"],
        "questions": [
            {
                "ordering": 1,
                "type": "boolean",
                "prompt_markdown": "Python est typé dynamiquement.",
                "points": 20.0,
                "options_json": "[{\"id\": \"true\", \"text\": \"Vrai\"}]",
                "correct_answers_json": "true"
            }
        ]
    }
    res = client.post("/api/exams/import-template", headers=teacher_headers, json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["title"] == "Examen Custom Importé"
    assert created["question_count"] == 1

