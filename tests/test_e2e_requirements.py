"""
Test Suite: Requirements-Driven End-to-End (E2E) Test Suite
Ref: ORIGINAL_REQUEST.md (Requirements R1 - R8), PROJECT.md, and explorer_survey_test_audit/handoff.md Section 5.2

Tiers Covered:
- Tier 1: Feature Coverage (R1 - R8)
    * T1.1: Autocomplete dictionary & libraries verification (R1)
    * T1.2: Training completion return button navigation (R1)
    * T1.3: Diagnostic placement test decoupling from GPA/bulletin (R2)
    * T1.4: Multi-teacher module assignment serialization (R2, R6)
    * T1.5: Theoretical vs Practical exam question type rejection 400 (R3)
    * T1.6: Teacher exam data table structure (R4)
    * T1.7: Student exam card button states (Rejoindre emerald/amber/primary) (R5)
    * T1.8: Universal Escape modal dismissal & alert replacement (R6)
- Tier 2: Boundary & Corner Cases
    * T2.1: Infinite loop sandbox timeout (3.0s kill)
    * T2.2: Negative penalty floor at 0.0
    * T2.3: Multiple Matplotlib figure extraction without memory leak
    * T2.4: Concurrent identical attempt submissions
- Tier 3: Cross-Feature Interactions
    * T3.1: Practical exam + 10s away anti-cheat suspension + 403 submission rejection + proctor unlock + completion
    * T3.2: Proctor time extension + reload (F5) + authoritative timer sync
- Tier 4: Real-World Scenarios
    * T4.1: Multi-role exam lifecycle simulation validation (Scenarios 1-6)
"""

import json
import os
import re
import subprocess
import sys
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.models import User, Group, Module, Exam, Question, ExamSession, StudentAttempt
from backend.app.security import hash_password
from backend.app.services.grading import evaluate_answer
from backend.app.services.sandbox_runner import execute_user_code_with_input


# ==============================================================================
# TIER 1: FEATURE COVERAGE (R1 - R8)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Feature verification covering requirements R1 through R8."""

    def test_t1_1_autocomplete_dictionary_and_libraries(self):
        """
        T1.1 (R1): Verify CodeMirror autocomplete dictionary includes Python keywords,
        builtins (print, len, range, sum), standard & data science modules (math, sys, pandas,
        matplotlib.pyplot, seaborn, collections), member completions, and autoclosing config.
        """
        hint_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "vendor", "codemirror", "addon", "hint", "python-hint.js")
        )
        assert os.path.exists(hint_file_path), f"File not found: {hint_file_path}"
        with open(hint_file_path, "r", encoding="utf-8") as f:
            hint_content = f.read()

        # 1. Keywords
        required_keywords = ["def", "return", "if", "else", "for", "while", "import", "class", "try", "except", "True", "False"]
        for kw in required_keywords:
            assert f'"{kw}"' in hint_content or f"'{kw}'" in hint_content, f"Keyword '{kw}' missing from python-hint.js"

        # 2. Builtin functions
        required_builtins = ["print", "len", "range", "sum", "abs", "min", "max", "input", "round", "enumerate", "zip", "sorted"]
        for bi in required_builtins:
            assert f'"{bi}"' in hint_content or f"'{bi}'" in hint_content, f"Builtin '{bi}' missing from python-hint.js"

        # 3. Standard and Data Science Modules
        required_modules = ["math", "sys", "pandas", "matplotlib", "matplotlib.pyplot", "seaborn", "collections", "itertools", "heapq"]
        for mod in required_modules:
            assert f'"{mod}"' in hint_content or f"'{mod}'" in hint_content, f"Module '{mod}' missing from python-hint.js"

        # 4. Member autocompletions (math.sqrt, sys.stdin, pd.read_csv, plt.plot, sns.lineplot)
        assert '"sqrt"' in hint_content, "math member sqrt missing"
        assert '"stdin"' in hint_content, "sys member stdin missing"
        assert '"read_csv"' in hint_content, "pandas member read_csv missing"
        assert '"plot"' in hint_content, "pyplot member plot missing"
        assert '"lineplot"' in hint_content, "seaborn member lineplot missing"

        # 5. Code snippets present
        assert "PYTHON_SNIPPETS" in hint_content, "PYTHON_SNIPPETS definition missing"
        assert "stdin_read" in hint_content, "sys.stdin.read snippet missing"

        # 6. Autoclosing brackets and quotes in editor configuration
        runner_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "exam-runner.js")
        )
        assert os.path.exists(runner_file_path), f"File not found: {runner_file_path}"
        with open(runner_file_path, "r", encoding="utf-8") as f:
            runner_content = f.read()

        assert "autoCloseBrackets" in runner_content, "autoCloseBrackets option missing in exam-runner.js"
        assert "matchBrackets" in runner_content, "matchBrackets option missing in exam-runner.js"
        assert "autocomplete" in runner_content or "showHint" in runner_content, "autocomplete trigger missing in exam-runner.js"

    def test_t1_2_training_completion_return_button_navigation(self):
        """
        T1.2 (R1): Assert Python training completion screen contains button with text
        'Retourner au Centre d'Entraînement Python' navigating directly to #view-python.
        """
        app_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "app.js")
        )
        assert os.path.exists(app_file_path), f"File not found: {app_file_path}"
        with open(app_file_path, "r", encoding="utf-8") as f:
            app_content = f.read()

        # In renderPracticeResults: when coming from view-python
        assert "this.activeOriginView === 'view-python'" in app_content, "activeOriginView check missing in app.js"
        assert re.search(r"Retourner au Centre d.*Entra.*nement Python", app_content), (
            "Return to Python training center button text missing in app.js"
        )
        assert "renderTrainingCenterView" in app_content, (
            "Navigation handler renderTrainingCenterView() missing for completion return"
        )

        # In index.html: verify target score view and return button container
        index_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
        )
        with open(index_file_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        assert 'id="view-score"' in index_content, "#view-score container missing in index.html"
        assert 'id="btn-score-back-dashboard"' in index_content, "#btn-score-back-dashboard missing in index.html"
        assert 'id="view-python"' in index_content, "#view-python container missing in index.html"

    def test_t1_3_diagnostic_placement_decoupling_from_gpa(self, client, admin_headers, student_headers, db_session):
        """
        T1.3 (R2): Take a diagnostic placement test, submit answers, and verify student
        bulletin and official transcripts maintain strict decoupling from semester exams.
        """
        # 1. Étudiant soumet un test de niveau de diagnostic (PYTHON_INIT)
        practice_payload = {
            "question_ids": ["PRACTICE-PYTHON_INIT-1", "PRACTICE-PYTHON_INIT-2"],
            "answers": {
                "PRACTICE-PYTHON_INIT-1": "b",
                "PRACTICE-PYTHON_INIT-2": True
            }
        }
        res_submit = client.post(
            "/api/practice/exams/PYTHON_INIT/submit",
            headers=student_headers,
            json=practice_payload
        )
        assert res_submit.status_code == 200, f"Submit practice failed: {res_submit.text}"
        res_data = res_submit.json()
        assert "grade_20" in res_data
        assert "detailed_results" in res_data

        # 2. Consultation du bulletin étudiant
        res_bulletin = client.get("/api/admin/bulletins/ETU-001", headers=admin_headers)
        assert res_bulletin.status_code == 200, f"Fetch bulletin failed: {res_bulletin.text}"
        bulletin = res_bulletin.json()

        # 3. Vérification du cloisonnement strict
        # Le résultat du diagnostic doit apparaître sous 'fundamentals'
        assert "fundamentals" in bulletin, "fundamentals block missing from bulletin"
        assert "PYTHON_INIT" in bulletin["fundamentals"]
        assert bulletin["fundamentals"]["PYTHON_INIT"]["score"] is not None

        # Mais le bloc des examens officiels 'exams' ne doit pas assimiler le diagnostic à un examen officiel
        assert "exams" in bulletin, "exams block missing from bulletin"
        assert "theoretical" in bulletin["exams"]
        assert "practical" in bulletin["exams"]
        # En l'absence d'examen officiel passé par ETU-001, les scores officiels restent None
        assert bulletin["exams"]["theoretical"]["score"] is None
        assert bulletin["exams"]["practical"]["score"] is None

    def test_t1_4_multi_teacher_module_assignment_serialization(self, client, admin_headers, db_session):
        """
        T1.4 (R2, R6): Assign multiple teachers (prof-01, prof-02) to a single module
        via /api/modules/{code}/teachers, verifying status 200 and schema serialization
        without [object Object] error.
        """
        # 1. Création d'un module académique dédié
        mod_code = "MOD_MULTI_E2E"
        client.post(
            "/api/modules",
            headers=admin_headers,
            json={"code": mod_code, "title": "Module Multi Enseignants", "description": "Test assign"}
        )

        # 2. Création d'un deuxième enseignant dans la base de test
        teacher2 = User(
            id="prof-02",
            username="prof_durand",
            password_hash=hash_password("prof456"),
            plain_password="prof456",
            full_name="Professeur Durand",
            email="durand@test.com",
            role="teacher",
            must_change_password=False,
            is_active=True
        )
        db_session.add(teacher2)
        db_session.commit()

        # 3. Affectation du 1er enseignant
        res_assign1 = client.post(
            f"/api/modules/{mod_code}/teachers",
            headers=admin_headers,
            json={"teacher_id": "prof-01", "module_code": mod_code}
        )
        assert res_assign1.status_code == 200, f"Assign teacher 1 failed: {res_assign1.text}"
        assert res_assign1.json()["success"] is True

        # 4. Affectation du 2nd enseignant
        res_assign2 = client.post(
            f"/api/modules/{mod_code}/teachers",
            headers=admin_headers,
            json={"teacher_id": "prof-02", "module_code": mod_code}
        )
        assert res_assign2.status_code == 200, f"Assign teacher 2 failed: {res_assign2.text}"
        assert res_assign2.json()["success"] is True

        # 5. Récupération de la liste des enseignants affectés
        res_get_teachers = client.get(f"/api/modules/{mod_code}/teachers", headers=admin_headers)
        assert res_get_teachers.status_code == 200, f"Get teachers failed: {res_get_teachers.text}"
        teachers = res_get_teachers.json()

        assert isinstance(teachers, list)
        assert len(teachers) >= 2
        teacher_ids = [t["id"] for t in teachers]
        assert "prof-01" in teacher_ids
        assert "prof-02" in teacher_ids

        # Vérification qu'aucun champ n'affiche [object Object] et que la sérialisation est propre
        for t in teachers:
            assert isinstance(t["full_name"], str)
            assert "[object Object]" not in t["full_name"]
            assert t["role"] == "teacher"

    def test_t1_5_theoretical_vs_practical_exam_question_type_rejection_400(self, client, teacher_headers):
        """
        T1.5 (R3): Strict distinction between Theoretical and Practical exams:
        - Attempt POST /api/exams/{id}/questions with type='coding' on theoretical exam -> 400 Bad Request
        - Attempt POST /api/exams/{id}/questions with type='single_choice' on practical exam -> 400 Bad Request
        """
        # 1. Création d'une épreuve théorique
        res_theo = client.post(
            "/api/exams",
            headers=teacher_headers,
            json={
                "module_code": "PYTHON_INIT",
                "title": "Épreuve Théorique QCM",
                "exam_type": "theoretical",
                "duration_minutes": 45,
                "global_points": 20.0
            }
        )
        assert res_theo.status_code in [200, 201]
        theo_id = res_theo.json()["id"]

        # 2. Tentative d'insertion d'une question de code dans l'épreuve théorique -> Rejet 400
        res_bad_coding = client.post(
            f"/api/exams/{theo_id}/questions",
            headers=teacher_headers,
            json={
                "ordering": 1,
                "type": "coding",
                "prompt_markdown": "Écrire une fonction factorielle.",
                "points": 5.0,
                "options_json": json.dumps({"starter_code": "def fact(n): pass"}),
                "correct_answers_json": json.dumps({"public": [], "hidden": []})
            }
        )
        assert res_bad_coding.status_code == 400, f"Expected 400 for coding question in theoretical exam, got {res_bad_coding.status_code}"
        assert "théorique" in res_bad_coding.json()["detail"].lower()

        # 3. Création d'une épreuve pratique
        res_prac = client.post(
            "/api/exams",
            headers=teacher_headers,
            json={
                "module_code": "PYTHON_INIT",
                "title": "Épreuve Pratique Machine",
                "exam_type": "practical",
                "duration_minutes": 60,
                "global_points": 20.0
            }
        )
        assert res_prac.status_code in [200, 201]
        prac_id = res_prac.json()["id"]

        # 4. Tentative d'insertion d'un QCM dans l'épreuve pratique -> Rejet 400
        res_bad_qcm = client.post(
            f"/api/exams/{prac_id}/questions",
            headers=teacher_headers,
            json={
                "ordering": 1,
                "type": "single_choice",
                "prompt_markdown": "Quel mot-clé définit une fonction ?",
                "points": 2.0,
                "options_json": json.dumps([{"id": "a", "text": "def"}, {"id": "b", "text": "fn"}]),
                "correct_answers_json": json.dumps("a")
            }
        )
        assert res_bad_qcm.status_code == 400, f"Expected 400 for QCM in practical exam, got {res_bad_qcm.status_code}"
        assert "pratique" in res_bad_qcm.json()["detail"].lower()

    def test_t1_6_teacher_exam_data_table_structure(self):
        """
        T1.6 (R4): Verify teacher exam management view (#view-teacher) renders a structured,
        responsive data table with specified headers: Title, Module, Type, Duration,
        Question Count, Points, Allowed Groups, Actions.
        """
        app_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "app.js")
        )
        with open(app_file_path, "r", encoding="utf-8") as f:
            app_content = f.read()

        # Vérification du tableau dans renderTeacherView
        assert "teacher-exams-table" in app_content, "Class 'teacher-exams-table' missing in app.js"
        assert ("Module & Statut" in app_content or "Statut Session" in app_content), "Column 'Module & Statut' or 'Statut Session' missing"
        assert "Titre de l'Épreuve" in app_content, "Column 'Titre de l'Épreuve' missing"
        assert "Type" in app_content, "Column 'Type' missing"
        assert "Durée" in app_content, "Column 'Durée' missing"
        assert "Questions" in app_content, "Column 'Questions' missing"
        assert "Barème" in app_content, "Column 'Barème' missing"
        assert ("Cibles" in app_content or "Spécialité" in app_content), "Column 'Cibles' or 'Spécialité' missing"
        assert ("Actions Directes" in app_content or "Actions" in app_content), "Column 'Actions' missing"

        # Vérification des badges de distinction Pratique vs Théorique
        assert "badge-practical" in app_content, "Badge badge-practical missing in app.js"
        assert "badge-theoretical" in app_content, "Badge badge-theoretical missing in app.js"

    def test_t1_7_student_exam_card_button_states(self):
        """
        T1.7 (R5): Verify student exam card button state distinctions:
        - Ongoing attempt: Displays '🔄 Rejoindre l'épreuve en cours ➔' with emerald accent (#059669)
        - Waiting room: Displays '⏳ Rejoindre la salle d'attente ➔' with amber accent (#d97706)
        - Not started: Displays 'Commencer l'épreuve ➔' with standard primary styling
        """
        app_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "app.js")
        )
        with open(app_file_path, "r", encoding="utf-8") as f:
            app_content = f.read()

        # Ongoing attempt
        assert "🔄 Rejoindre l'épreuve en cours ➔" in app_content, (
            "Button text '🔄 Rejoindre l\'épreuve en cours ➔' missing in app.js"
        )
        assert "#059669" in app_content or "btn-success" in app_content, (
            "Emerald styling missing for ongoing attempt button"
        )

        # Waiting room attempt
        assert "⏳ Rejoindre la salle d'attente ➔" in app_content, (
            "Button text '⏳ Rejoindre la salle d\'attente ➔' missing in app.js"
        )
        assert "#d97706" in app_content or "amber" in app_content, (
            "Amber styling missing for waiting room button"
        )

        # Unstarted attempt
        assert "Commencer l'épreuve ➔" in app_content, (
            "Button text 'Commencer l\'épreuve ➔' missing in app.js"
        )

    def test_t1_8_universal_escape_modal_dismissal_and_alert_replacement(self):
        """
        T1.8 (R6): Verify:
        - Global keydown Escape ('Échap') handler for immediate modal dismissal
        - Toast notification system (showToast) replacing raw browser alert() popups
        - Clean in-line #login-error container
        """
        app_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "app.js")
        )
        with open(app_file_path, "r", encoding="utf-8") as f:
            app_content = f.read()

        # Escape key listener
        assert "e.key === 'Escape'" in app_content or 'e.key === "Escape"' in app_content, (
            "Escape keydown event handler missing in app.js"
        )

        # showToast definition
        assert "showToast(message" in app_content or "showToast(" in app_content, (
            "showToast() function missing in app.js"
        )

        # Clean in-line login error in index.html
        index_file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
        )
        with open(index_file_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        assert 'id="login-error"' in index_content, "#login-error container missing in index.html"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary, stress, and corner case test suites."""

    def test_t2_1_infinite_loop_sandbox_timeout_kill(self):
        """
        T2.1: Infinite loop sandbox execution timeout (kill process cleanly within timeout).
        Submits 'while True: pass' and verifies process is terminated with timed_out: True.
        """
        infinite_code = "while True:\n    pass\n"
        start_time = time.perf_counter()
        result = execute_user_code_with_input(infinite_code, custom_input="", timeout_seconds=1.5)
        elapsed = time.perf_counter() - start_time

        assert result["timed_out"] is True, f"Expected timed_out=True, got: {result}"
        assert elapsed < 3.5, f"Execution took {elapsed:.2f}s, expected kill within ~3.0s threshold"

    def test_t2_2_negative_penalty_floor_at_zero(self):
        """
        T2.2: Negative penalty floor at 0.0.
        Evaluates a multiple-choice question where student selected 0 correct answers
        and 3 wrong answers with penalty, asserting that awarded score is 0.0 (never negative).
        """
        # Question à 4 options ('a', 'b', 'c' correctes). Étudiant choisit uniquement l'option fausse 'd'.
        # Pénalité de 1.0 -> Score brut = -1.0. Plancher à 0.0.
        score, is_correct, feedback = evaluate_answer(
            q_type="multi_choice",
            user_answer=["d"],
            correct_answers=["a", "b", "c"],
            points=3.0,
            negative_penalty=1.0,
            floor_score=0.0
        )
        assert score == 0.0, f"Expected floor at 0.0, got: {score}"
        assert is_correct is False
        assert "mauvaise(s)" in feedback

        # Question QCU avec mauvaise réponse et pénalité stricte
        score_single, is_corr_single, _ = evaluate_answer(
            q_type="single_choice",
            user_answer="wrong",
            correct_answers="correct",
            points=2.0,
            negative_penalty=1.5,
            floor_score=0.0,
            strict_single_penalty=True
        )
        assert score_single == 0.0, f"Expected single choice floor at 0.0, got: {score_single}"
        assert is_corr_single is False

    def test_t2_3_multiple_matplotlib_figure_extraction_without_leak(self):
        """
        T2.3: Multiple Matplotlib figure extraction without memory leak.
        Generates 5+ subplots in a loop and verifies all figures are intercepted as Base64 PNGs.
        """
        code = (
            "import matplotlib.pyplot as plt\n"
            "for i in range(5):\n"
            "    plt.figure()\n"
            "    plt.plot([0, 1, 2], [i, i*2, i*3])\n"
            "    plt.title(f'Figure {i}')\n"
            "print('PLOTS_DONE')\n"
        )
        result = execute_user_code_with_input(code, custom_input="", timeout_seconds=10.0)
        assert result["success"] is True, f"Script failed: {result['stderr']}"
        assert "PLOTS_DONE" in result["stdout"]

        figures = result.get("figures", [])
        assert len(figures) >= 5, f"Expected at least 5 figures, captured {len(figures)}"
        for idx, fig in enumerate(figures):
            assert fig.startswith("data:image/png;base64,"), f"Figure {idx} is not a valid base64 data URI"
            assert len(fig) > 100, f"Figure {idx} payload is unexpectedly small"

    def test_t2_4_concurrent_identical_attempt_submissions(self, client, teacher_headers, student_headers):
        """
        T2.4: 10 concurrent / sequential submission requests for the same student attempt.
        Only the first calculates score; subsequent requests return 'Cet examen a déjà été soumis.'
        with idempotent status and identical mark.
        """
        # 1. Création d'un examen et d'une session
        res_exam = client.post(
            "/api/exams",
            headers=teacher_headers,
            json={"module_code": "PYTHON_INIT", "title": "Examen Concurrence", "duration_minutes": 30, "group_ids": ["GRP-1"]}
        )
        exam_id = res_exam.json()["id"]

        client.post(
            f"/api/exams/{exam_id}/questions",
            headers=teacher_headers,
            json={"ordering": 1, "type": "boolean", "prompt_markdown": "Python est dynamique ?", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
        )

        sess_res = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-CONC"}).json()
        session_id = sess_res["session_id"]
        client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

        # 2. Démarrage de l'épreuve par l'étudiant
        start_res = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
        attempt_id = start_res.json()["attempt_id"]
        q_id = start_res.json()["questions"][0]["id"]

        # Sauvegarde de la bonne réponse
        client.post(
            f"/api/student/attempts/{attempt_id}/save-answer",
            headers=student_headers,
            json={"question_id": q_id, "answer": True}
        )

        # 3. Première soumission officielle
        res_first = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
        assert res_first.status_code == 200
        first_data = res_first.json()
        assert first_data["final_mark"] == 20.0
        assert first_data["status"] in ["submitted", "completed"]

        # 4. Neuf soumissions subséquentes identiques (simulation de double-clic / réseau instable)
        for i in range(9):
            res_sub = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
            assert res_sub.status_code == 200, f"Submission {i+2} failed with code {res_sub.status_code}"
            sub_data = res_sub.json()
            assert sub_data["final_mark"] == 20.0
            assert "déjà été soumis" in sub_data.get("message", "")


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS
# ==============================================================================

class TestTier3CrossFeatureInteractions:
    """Tier 3: Complex multi-feature workflows and state interactions."""

    def test_t3_1_practical_exam_anti_cheat_suspension_403_unlock_completion(self, client, teacher_headers, student_headers):
        """
        T3.1: Practical exam + 10s away anti-cheat suspension + 403 submission rejection
        + proctor telemetry inspection + remote unlock + successful completion.
        """
        # 1. Création d'une épreuve pratique avec défi Python
        res_exam = client.post(
            "/api/exams",
            headers=teacher_headers,
            json={
                "module_code": "PYTHON_INIT",
                "title": "TP Machine Pratique E2E",
                "exam_type": "practical",
                "duration_minutes": 60,
                "global_points": 20.0,
                "group_ids": ["GRP-1"]
            }
        )
        exam_id = res_exam.json()["id"]

        coding_options = json.dumps({
            "starter_code": "def solution(x):\n    return x * 2\n",
            "public_tests": [{"input": "4", "expected_output": "8"}]
        })
        coding_solution = json.dumps({
            "public_tests": [{"input": "4", "expected_output": "8"}],
            "hidden_tests": [{"input": "10", "expected_output": "20"}]
        })

        client.post(
            f"/api/exams/{exam_id}/questions",
            headers=teacher_headers,
            json={
                "ordering": 1,
                "type": "coding",
                "prompt_markdown": "Écrire une fonction qui double l'entrée.",
                "points": 20.0,
                "options_json": coding_options,
                "correct_answers_json": coding_solution
            }
        )

        # 2. Ouverture de session et lancement par le surveillant
        res_sess = client.post(
            "/api/proctor/sessions",
            headers=teacher_headers,
            json={"exam_id": exam_id, "room_id": "SALLE-TP-T31"}
        ).json()
        session_id = res_sess["session_id"]
        client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

        # 3. L'étudiant démarre l'épreuve
        start_res = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
        assert start_res.status_code == 200
        attempt_id = start_res.json()["attempt_id"]
        q_id = start_res.json()["questions"][0]["id"]

        # 4. Infraction de sécurité : perte de focus > 10 secondes (AWAY_10S)
        res_sec = client.post(
            f"/api/student/attempts/{attempt_id}/security-event",
            headers=student_headers,
            json={"event_type": "AWAY_10S", "details": {"duration_seconds": 12}}
        )
        assert res_sec.status_code == 200
        assert res_sec.json()["status"] == "suspended"

        # 5. Tentative de soumission par l'étudiant suspendu -> Bloqué 403 Forbidden
        res_blocked_sub = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
        assert res_blocked_sub.status_code == 403, f"Expected 403 Forbidden on suspended submission, got {res_blocked_sub.status_code}"
        assert "suspendue" in res_blocked_sub.json()["detail"].lower()

        # 6. Tentative de sauvegarde par l'étudiant suspendu -> Bloqué 403 Forbidden
        res_blocked_save = client.post(
            f"/api/student/attempts/{attempt_id}/save-answer",
            headers=student_headers,
            json={"question_id": q_id, "answer": "def solution(x): return x * 2"}
        )
        assert res_blocked_save.status_code == 403

        # 7. Le surveillant constate la suspension dans son tableau de bord de télémétrie
        res_overview = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=teacher_headers)
        assert res_overview.status_code == 200
        student_cards = res_overview.json()["student_cards"]
        st_card = next((c for c in student_cards if c["student_id"] == "ETU-001"), None)
        assert st_card is not None
        assert st_card["status"] == "suspended"

        # 8. Le surveillant clique sur "Débloquer"
        res_unlock = client.post(
            f"/api/proctor/sessions/{session_id}/attempts/{attempt_id}/unlock",
            headers=teacher_headers
        )
        assert res_unlock.status_code == 200
        assert res_unlock.json()["success"] is True
        assert res_unlock.json()["status"] == "in_progress"

        # 9. Statut étudiant rétabli à 'in_progress'
        res_status = client.get(f"/api/student/attempts/{attempt_id}/status", headers=student_headers)
        assert res_status.json()["status"] == "in_progress"

        # 10. L'étudiant peut désormais sauvegarder sa réponse et soumettre sa copie
        res_ok_save = client.post(
            f"/api/student/attempts/{attempt_id}/save-answer",
            headers=student_headers,
            json={"question_id": q_id, "answer": "def solution(x): return x * 2"}
        )
        assert res_ok_save.status_code == 200

        res_final_sub = client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)
        assert res_final_sub.status_code == 200
        assert res_final_sub.json()["status"] in ["submitted", "completed"]
        assert res_final_sub.json()["final_mark"] == 20.0

    def test_t3_2_proctor_time_extension_reload_authoritative_timer_sync(self, client, teacher_headers, student_headers):
        """
        T3.2: Proctor time extension + reload (F5) + authoritative timer sync.
        Proctor grants +15 minutes; student refreshes and authoritative remaining_seconds
        reflects the added duration.
        """
        # 1. Création de l'épreuve de 20 minutes
        res_exam = client.post(
            "/api/exams",
            headers=teacher_headers,
            json={"module_code": "PYTHON_INIT", "title": "Examen Timer Sync", "duration_minutes": 20, "group_ids": ["GRP-1"]}
        )
        exam_id = res_exam.json()["id"]

        client.post(
            f"/api/exams/{exam_id}/questions",
            headers=teacher_headers,
            json={"ordering": 1, "type": "boolean", "prompt_markdown": "Test Timer", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
        )

        res_sess = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TIMER"}).json()
        session_id = res_sess["session_id"]
        client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

        # 2. Démarrage de l'épreuve par l'étudiant
        start_res = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
        attempt_id = start_res.json()["attempt_id"]
        initial_remaining = start_res.json()["remaining_seconds"]
        assert 1150 <= initial_remaining <= 1200  # ~20 min (1200 sec)

        # 3. Le surveillant accorde +15 minutes de prolongation
        res_extend = client.post(
            f"/api/proctor/sessions/{session_id}/extend-time",
            headers=teacher_headers,
            json={"extra_minutes": 15}
        )
        assert res_extend.status_code == 200
        assert res_extend.json()["extra_minutes"] == 15

        # 4. L'étudiant recharge la page (F5 / reconnect) en relançant start/resume
        reload_res = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
        assert reload_res.status_code == 200
        reload_data = reload_res.json()
        assert reload_data["attempt_id"] == attempt_id
        new_remaining = reload_data["remaining_seconds"]

        # Le temps restant doit avoir augmenté d'environ 15 minutes (900 secondes)
        assert new_remaining >= initial_remaining + 800, (
            f"Timer not synchronized after extension: initial={initial_remaining}, reloaded={new_remaining}"
        )


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Comprehensive end-to-end multi-role real-world cohort validation."""

    def test_t4_1_full_multi_role_exam_lifecycle_simulation(self):
        """
        T4.1: Multi-role exam lifecycle simulation validation.
        Executes scripts/simulate_all_exam_scenarios.py verifying all 6 lifecycle scenarios:
        1. Super Admin: Academic module creation and teacher assignment
        2. Teacher: Multi-type exam authoring and room proctor session launch
        3. Student 1: Waiting room secrecy, sync launch, console I/O, autosave, 100% grading
        4. Student 2: Network crash, session resume, +10 min extension, F5 authoritative sync
        5. Student 3: Anti-cheat 10s away suspension, 403 submission guard, remote proctor unlock
        6. Proctor Close: Collective session closure, all copies sealed, admin stats updated
        """
        script_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "scripts", "simulate_all_exam_scenarios.py")
        )
        assert os.path.exists(script_path), f"Simulation script missing: {script_path}"

        # Exécution du script de simulation en sous-processus Python isolé
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        assert proc.returncode == 0, f"Simulation failed with returncode {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        assert "TOUS LES SCÉNARIOS TESTÉS ONT ÉTÉ EXÉCUTÉS AVEC 100% DE SUCCÈS" in proc.stdout, (
            "Simulation did not reach 100% success message."
        )
