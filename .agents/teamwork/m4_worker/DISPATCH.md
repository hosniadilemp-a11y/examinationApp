# DISPATCH — m4_worker

## Task
Implement Milestone 4: Challenge Evaluation Harness, Dual-Track UI & Navigation for Linux Training Center.

## Input Documents
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST READ)
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\orchestrator_2\PROJECT.md`
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\survey_explorer_2\report.md` (Challenge evaluator §7, frontend architecture §10)
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\m3_worker\handoff.md`

## Ownership & Scope Boundaries
You own:
- `frontend/js/linux/linux-evaluator.js`
- `frontend/js/linux/linux-runner.js`
- `frontend/index.html` (adding student nav button, `#view-linux` markup, completion button)
- `frontend/js/app.js` (routing to `#view-linux` and wiring nav button)
- Verification test script (e.g. `frontend/js/linux/test-evaluator.mjs`)

DO NOT modify backend files.

## Requirements
1. Implement `frontend/js/linux/linux-evaluator.js`:
   - Automated evaluation harness: runs student command against challenge environment on a clean VFS snapshot.
   - Verifies assertions: `file_exists`, `file_not_exists`, `file_contains`, `permission`/`mode`, `stdout_exact`, `stdout_contains`, `exit_code`.
   - Enforces confidential hidden test masking: hidden tests display status (pass/fail) but mask command and expected details as `"[Protégé]"`. Never leak secrets to console or DOM.

2. Implement `frontend/js/linux/linux-runner.js`:
   - Main controller for `#view-linux`.
   - Manages dual tracks:
     - **Volet Théorique (Concepts & Administration Système)**: Concept exercises and QCM quizzes (FHS, permissions, signals, bash scripts).
     - **Volet Pratique (Atelier Terminal & Défis Ligne de Commande)**: Ergonomic 2-pane layout (Instructions on left, Terminal + test tabs on right).
   - Challenge navigation with status badges (unsolved, in_progress, solved).
   - "Exécuter la Commande", "Valider les Tests Publics", "Soumettre le Défi" (calls API `/api/training/linux/submit-challenge`).
   - Completion action button: "Retourner au Centre d'Entraînement Linux ➔" navigating cleanly back to `#view-linux`.

3. Integrate in `frontend/index.html`:
   - Student navigation bar: add "Centre Linux" navigation button alongside Python Training and Exams.
   - Markup for `#view-linux` supporting the dual-track hub (Théorique and Pratique) and two-pane challenge layout.
   - Completion modal / banner with "Retourner au Centre d'Entraînement Linux ➔".

4. Integrate in `frontend/js/app.js`:
   - Import `LinuxRunner` from `./linux/linux-runner.js`.
   - Add view routing for `view-linux` and bind student nav button.

5. Verification:
   - Run evaluator unit tests: `node frontend/js/linux/test-evaluator.mjs`.
   - Run M2 & M3 test suites: `node frontend/js/linux/test-posix-vfs.mjs` and `node frontend/js/linux/test-shell-engine.mjs`.
   - Run `pytest tests/` (all 119 tests must remain 100% passing).

6. Produce `handoff.md` and report back.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-10-20T21:54:47Z
[Message from orchestrator]
Implement Milestone 4:
- frontend/js/linux/linux-evaluator.js (automated challenge evaluation harness, assertions, hidden test masking)
- frontend/js/linux/linux-runner.js (dual-track coordinator: Volet Théorique & Volet Pratique with 2-pane layout, challenge switcher, return button "Retourner au Centre d'Entraînement Linux ➔")
- frontend/index.html (student nav bar "Centre Linux" button, #view-linux markup, completion action)
- frontend/js/app.js (route to view-linux, event bindings)
- frontend/js/linux/test-evaluator.mjs (evaluator unit tests)
