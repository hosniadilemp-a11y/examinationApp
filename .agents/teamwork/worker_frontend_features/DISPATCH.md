## 2026-10-20T17:50:11Z
You are the Frontend Features Specialist Engineer for Milestones M3, M4, and M5 of the Examination & Quiz platform project.
Your working directory is: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\worker_frontend_features
Project root is: c:\Users\adel\Documents\ExaminationQuiz APP
Authoritative user request path: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan path: c:\Users\adel\Documents\ExaminationQuiz APP\PROJECT.md
Frontend survey report: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\explorer_survey_frontend\handoff.md
Backend handoff report: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\worker_m1_backend\handoff.md
M2 frontend handoff report: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\worker_m2_frontend\handoff.md

Tasks:
1. Milestone M3: AlgoCompiler Two-Pane Layout & CodeMirror Autocomplete (R1):
   - In `frontend/css/style.css` and `frontend/js/exam-runner.js`: Ensure the two-pane workspace (`.challenge-layout.fused-workspace`) is fully fused and responsive, occupying full viewport height without cramped nested containers or double scrollbars (`height: 100%; flex: 1; min-height: 0; overflow: hidden;`).
   - Left pane: problem description with KaTeX LaTeX math rendering (`renderMathInElement`), topic tags, difficulty badges, challenge navigation.
   - Right pane: toolbar (undo, redo, format, comment toggle, font size controls, reset template, template lock indicators, challenge timer), full-height CodeMirror editor with Python syntax highlighting and active line highlighting, status bar (Ln, Col, char count, line count, word wrap), and bottom tabs ("Console E/S", "Cas de Test").
   - Execution controls: "Exécuter avec Entrée" (run with custom stdin), "Exécuter sur les Tests" (run public tests), and "Soumettre la Solution" (submit solution). Wire to the new backend endpoints (`/api/student/attempts/{attempt_id}/questions/{question_id}/run-tests` and `/api/student/attempts/{attempt_id}/run-code`).
   - CodeMirror Python Autocomplete & IntelliSense: Ensure Python keywords, built-in functions (`print`, `range`, `len`, `sum`, etc.), and standard libraries (`math`, `sys`, `pandas`, `matplotlib.pyplot`, `seaborn`, `collections`) trigger via `Ctrl-Space` and typing alphanumeric characters or dot (`.`). Add CSS badge styling in `style.css` matching `oldapps/AlgoCompilerv2` (`.hint-badge-snippet`, `.hint-badge-keyword`, `.hint-badge-builtin`, `.hint-badge-variable`, `.hint-badge-module`).
   - Headless Data Science plot rendering: Ensure base64 PNG figures in `res.figures` render cleanly into `#console-figures`.
   - In Python training completion screen: Ensure the action button states verbatim "Retourner au Centre d'Entraînement Python ➔" and navigates directly to `#view-python`.

2. Milestone M4: Teacher Exam Management & Dedicated Question Authoring Wizard (R3, R4):
   - In `frontend/js/app.js` and `frontend/index.html`:
   - Redesign Teacher Exam Management view (`#view-teacher`): Replace card grid with a responsive, structured data table with columns: Title, Module, Type (Théorique vs Pratique badges: `💻 Pratique` / `📖 Théorique`), Duration, Question Count, Total Points, Allowed Groups, and Direct Actions (Edit Questions, Open Room & Proctor, Export, Delete).
   - Dedicated 2-Step Exam Creation & Question Builder:
     * Step 1: General configuration (Title, Module, Exam Type selector: "Épreuve Théorique" vs "Épreuve Pratique", Duration, Passing Score, Allowed Groups, Navigation, Shuffling rules).
     * Step 2: Integrated Question Builder dynamically adapted to chosen Exam Type:
       - If Épreuve Théorique: exclude/disable "coding" question type. Allow Single Choice, Multiple Choice, True/False, Fill-in-the-Blank, Matching.
       - If Épreuve Pratique: exclusively allow Python coding challenges with starter code, public tests (>= 2), and hidden tests (>= 10).
       - Live points total counter showing sum of questions vs global exam points.
       - Question reordering wired to `PUT /api/exams/{exam_id}/questions/reorder`.
       - Instant exam validation button wired to `GET /api/exams/{exam_id}/validate`.

3. Milestone M5: Student Card State Buttons & Proctor Dashboard (R5, R7):
   - In `frontend/js/app.js`: Student exam card action buttons must visually distinguish states:
     * Ongoing attempt (`attempt_status === 'in_progress'`): Displays "🔄 Rejoindre l'épreuve en cours ➔" with emerald/green accent styling (`#10b981` / `#059669`).
     * Waiting room (`session_status === 'waiting'` or `attempt_status === 'waiting'`): Displays "⏳ Rejoindre la salle d'attente ➔" with amber/yellow accent styling (`#f59e0b` / `#d97706`).
     * Not started: Displays "Commencer l'épreuve ➔" with standard primary styling (`#2563eb`).
   - Proctor live monitoring dashboard:
     * Add "Débloquer Tous les Postes Suspendus" button wired to `POST /api/proctor/sessions/{session_id}/unlock-all` with confirmation toast.
     * Ensure student connection status, heartbeat, progress, remaining authoritative timer, and violation logs render cleanly.

4. Verification:
   - Validate JS syntax with `node -c` on all modified files.
   - Run full automated test suite: `pytest tests/` (all 100 tests must pass).
   - Run simulation script: `python scripts/simulate_all_exam_scenarios.py` (all 6 scenarios must pass).
   - Document changes and verification results in `handoff.md`.
