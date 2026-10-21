# Original User Request

## Initial Request — 2026-10-20T16:59:37Z

Full-scale update, security audit, and feature enhancement of the Examination & Quiz platform (ExaminationQuiz APP), integrating an AlgoCompiler/HackerRank-style Python practical coding environment with verified test suites, full teacher exam creation workflow, robust surveillance/monitoring dashboard, resilient exam-session state management, anti-cheating enforcement, and database expansions.

Working directory: c:\Users\adel\Documents\ExaminationQuiz APP
Integrity mode: development

## Requirements

### R1. AlgoCompiler / HackerRank-Style Python Practical Environment & CodeMirror Autocomplete
- Implement a fully fused, homogeneous two-pane layout (matching `oldapps/AlgoCompilerv2` and seamlessly integrated into the application without cramped nested frames or double scrollbars):
  - Left pane: Problem description with KaTeX LaTeX math rendering, topic tags, difficulty badges, and challenge navigation.
  - Right pane: Code editor toolbar (undo, redo, format, comment toggle, font size controls, reset to template, template lock indicators, challenge timer), full-viewport CodeMirror editor with Python syntax highlighting and active line highlighting, status bar (Ln, Col, char count, line count, word wrap), and bottom tabs.
  - Bottom pane: Tabs for "Console E/S" (stdin input and stdout output) and "Cas de Test" (test cases).
  - Execution controls: "Exécuter avec Entrée" (run with custom stdin), "Exécuter sur les Tests" (run public tests), and "Soumettre la Solution" (evaluate against both public and hidden tests).
- Provide native Python Autocomplete & Recommendations (IntelliSense) in CodeMirror:
  - Autocomplete for Python keywords, built-in functions (`print`, `range`, `len`, `sum`, etc.), and standard libraries (`math`, `sys`, `pandas`, `matplotlib.pyplot`, `seaborn`, `collections`).
  - Auto-closing brackets and quotes, matching bracket highlighting.
  - Triggerable via `Ctrl-Space` and automatically upon typing alphanumeric characters or dot (`.`).
- Every coding challenge in the database must have at least 2 public test cases (input & expected output visible to students) and at least 10 hidden test cases (evaluates student code without leaking expected outputs in API payloads).
- Support headless data science and visualization execution (Matplotlib, Seaborn, Pandas) with base64 PNG figure capture and rendering in the student console.
- In Python training, after completing a practice session, the completion screen action button must state "Retourner au Centre d'Entraînement Python ➔" and navigate directly to the Python training center (`#view-python`).

### R2. Four Diagnostic "Niveau" Placement Tests & Modular Separation
- Provide 4 diagnostic placement tests (**Python**, **Algorithmique**, **Cryptographie**, and **Linux Administration**) that students can take on-demand 24/7 to assess their fundamental level.
- Strictly decouple these 4 diagnostic tests from regular semester curriculum modules: their results must not count toward official module averages, academic GPAs, or exam transcripts.
- Ensure full support in the database and API for adding, updating, and managing other regular curriculum modules and courses, with support for multiple teachers assigned per module without error.

### R3. Strict Distinction between Theoretical and Practical Exams
- Formally distinguish between two types of examinations across backend models, APIs, and teacher/student interfaces:
  1. **Épreuve Théorique (QCM & Synthèse de Connaissances)**: Exclusively contains non-coding questions (Single Choice, Multiple Choice, True/False, Fill-in-the-Blank, Matching). Coding challenge option is disabled/excluded.
  2. **Épreuve Pratique (Atelier de Programmation & Défis Machine)**: Exclusively contains practical Python coding challenges with starter code, public tests (>= 2), and hidden tests (>= 10).
- When creating an exam, the teacher chooses the exam type, and the question authoring interface adapts dynamically to the chosen type.

### R4. Complete Teacher Exam Creation & Management Experience
- Redesign the Teacher Exam Management view (`#view-teacher`):
  - Display "Examens Créés & Disponibles" as a structured, responsive data table with columns: Title, Module, Type (Théorique vs Pratique), Duration, Question Count, Total Points, Allowed Groups, and Direct Actions (Edit Questions, Open Room & Proctor, Export, Delete).
- Provide a dedicated, full-view Exam Creation & Question Authoring page:
  - Step 1: General configuration (Title, Module, Exam Type, Duration, Passing Score, Allowed Groups, Navigation and Shuffling rules).
  - Step 2: Integrated Question Builder (adapted to Theoretical vs Practical type), question reordering, live points total, and instant validation.

### R5. Anti-Cheating Hardening, Resilient State & Rejoindre/Commencer State Distinction
- Ensure that official exam answer keys, solution codes, and hidden test expected outputs are NEVER transmitted to or accessible on the client during official exams.
- Enforce strict anti-cheating controls: full-screen lock enforcement, tab-switching and window-blur detection, suspension threshold upon prolonged focus loss (>10s away requiring proctor unlock), with 403 Forbidden preventing suspended students from submitting.
- When an exam attempt is already active or in waiting state, the student exam card must visually distinguish this state:
  - Ongoing attempt: Displays "🔄 Rejoindre l'épreuve en cours ➔" with emerald/green accent styling.
  - Waiting room: Displays "⏳ Rejoindre la salle d'attente ➔" with amber/yellow accent styling.
  - Not started: Displays "Commencer l'épreuve ➔" with standard primary styling.
- Student exam sessions survive page reload (`F5`) or network reconnection without loss of progress or timer desynchronization.

### R6. Modern UI Notifications, Escape Key Modal Dismissal & Clean Login Errors
- Replace raw browser `alert()` popups with modern, sleek toast notifications (floating glassmorphic alerts with type-specific icons and colors: success, warning, danger, info).
- Ensure all modal dialogs and popup windows can be immediately closed by pressing the `Escape` key ("Échap") or clicking the modal backdrop.
- Login form displays clean in-line error alerts within `#login-error` on incorrect credentials, eliminating unwanted browser alerts or incorrect "Session expirée" popups.
- Fix teacher assignment so that multiple teachers can be assigned to a module without `[object Object]` error messages.

### R7. Comprehensive Proctor Live Monitoring Dashboard
- Provide proctors/surveillants with a real-time, comprehensive monitoring dashboard displaying all crucial exam telemetry:
  - Live student connection status (connected, disconnected, heartbeat ping, last activity).
  - Real-time exam progress (current question index, percentage completed, remaining time authoritative counter).
  - Real-time anti-cheat violation logs and suspension alerts.
  - Proctor control actions: individual and bulk attempt unlocking, time extension (+N minutes), and forced submission.

### R8. Full Audit, Logging & Documentation
- Document all modifications and resolutions in `docs/AUDIT_AND_RESOLUTIONS.md` and related documentation.
- Maintain 100% test pass rate across the automated test suite (`pytest tests/`).

## Verification Resources
- Existing automated test suite: `tests/` (85+ pytest test suites covering RBAC, grading, sessions, anti-cheat, CSV import/export, concurrency, sandbox, and telemetry).
- Multi-scenario end-to-end simulation: `scripts/simulate_all_exam_scenarios.py`.
- Reference layout and styling: `oldapps/AlgoCompilerv2` (`challenge.html`, `challenge.css`, `algo-hints.js`).

## Acceptance Criteria

### Python Practical Coding Environment & Autocomplete
- [ ] Coding challenge UI is fully fused, responsive, and takes full viewport height without cramped nested containers.
- [ ] CodeMirror auto-completion (keywords, builtins, standard library methods, snippets) triggers via `Ctrl-Space` and typing.
- [ ] Every coding problem in the DB has at least 2 public test cases and at least 10 hidden test cases.
- [ ] Finishing a Python practice session displays "Retourner au Centre d'Entraînement Python ➔" returning to `#view-python`.

### Exam Type Distinction & Teacher Experience
- [ ] Exams are formally categorized as either "Épreuve Théorique" or "Épreuve Pratique".
- [ ] Theoretical exams allow only non-coding questions; Practical exams allow only coding challenges.
- [ ] Teacher exam list displays a comprehensive responsive table of created exams.
- [ ] Dedicated exam creation page allows full step-by-step authoring of exam settings and questions.

### Student State & Login Experience
- [ ] Active and waiting exams show "Rejoindre l'épreuve en cours ➔" / "Rejoindre la salle d'attente ➔" in green/amber buttons.
- [ ] Invalid login shows an in-form message without native browser alert or premature session expiry notification.
- [ ] All modals dismiss upon pressing Escape ("Échap").
- [ ] Modern toast notification system replaces native `alert()` calls.
- [ ] Multiple teachers can be assigned to modules without `[object Object]` errors.



## Follow-up — 2026-10-20T19:57:44Z

# Teamwork Project Prompt — Linux Training Center (Centre d'Entraînement Linux)

Build and integrate a comprehensive Linux Training Center (Centre d'Entraînement Linux) into the ExaminationQuiz APP, mirroring the dual architecture of the Python Training Center with theoretical knowledge checks and an interactive client-side Linux shell terminal powered by an in-browser virtual filesystem for command testing and automated challenge evaluation.

Working directory: c:\Users\adel\Documents\ExaminationQuiz APP
Integrity mode: development

## Requirements

### R1. Linux Training Center UI & Dual-Track Navigation
- Provide a dedicated, responsive Linux Training Center view seamlessly integrated into the student workspace and navigation bar alongside Python Training and Official Exams.
- Offer two distinct learning tracks matching the proven Python training model:
  1. **Volet Théorique (Concepts & Administration Système) :** Progressive exercises and quizzes covering Linux fundamentals (FHS directory hierarchy, permissions, user management, process lifecycle, bash scripting, network utilities).
  2. **Volet Pratique (Atelier Terminal & Défis Ligne de Commande) :** Ergonomic two-pane layout featuring problem description/task instructions on the left, and an interactive Linux terminal window with command editor and test execution tab on the right.
- Ensure the completion screen features a direct return action ("Retourner au Centre d'Entraînement Linux ➔") navigating back to the Linux training hub.

### R2. Client-Side Linux Shell & Virtual Filesystem (VFS) Engine
- Implement a pure client-side virtual Linux terminal and hierarchical virtual file system (VFS) running entirely within the browser.
- The virtual terminal must support:
  - An interactive CLI prompt (e.g. `student@examquiz:~$ `) with command history (Up/Down arrows), tab autocompletion for filenames and basic commands, and clear screen (`clear` / `Ctrl+L`).
  - Core navigation & file manipulation commands: `pwd`, `cd`, `ls` (with `-l`, `-a`, `-la`), `cat`, `touch`, `mkdir` (with `-p`), `rm` (with `-r`), `cp`, `mv`, `echo`, `head`, `tail`, `wc` (lines/words/bytes).
  - Permissions & user simulation: `chmod` (octal & symbolic: `755`, `+x`), `chown`, file permission attributes displayed in `ls -l`.
  - Process & system utilities: `ps`, `top` snapshot, `kill`, `uptime`, `whoami`, `uname`, `env`, `export`, `date`.
  - Text filtering & searching: `grep` (with `-i`, `-v`, `-n`), `find` (by name/type), `sort`, `uniq`.
  - Shell mechanics: stdout piping (`cmd1 | cmd2`), file redirection (`>`, `>>`, `<`), exit codes (`$?`), and command chaining (`&&`, `;`).

### R3. Linux Challenge Curriculum & Automated Test Verification
- Create a rich curriculum of progressive Linux challenges stored in structured JSON/DB formats (Level 1: Navigation & Basic Files, Level 2: Permissions & Text Processing, Level 3: Scripting, Pipes & Redirection, Level 4: Advanced Sysadmin & Troubleshooting).
- Each practical challenge includes:
  - Initial VFS state setup (pre-populated directories and files matching the scenario).
  - Clear objective, task context, and constraints.
  - Automated evaluation harness: runs the student's command or script against the challenge environment and verifies both stdout output and resulting filesystem state (e.g., file created, contents modified, correct permissions set).
  - At least 2 public test cases and at least 5 hidden test cases per challenge, with granular test results and pass/fail indicators.

### R4. Academic Integration, Student Progress & Diagnostic Decoupling
- Record practice attempts, scores, and completion timestamps in the database (`practice_attempts` or dedicated Linux practice progress schema).
- Link progress to the existing `LINUX_ADMIN` diagnostic placement pillar while preserving strict decoupling from official semester exams and GPAs.

### R5. Complete Verification Suite & Scenario Testing
- Provide automated unit/integration tests (`pytest tests/test_linux_training.py`) verifying API endpoints, curriculum serialization, challenge data schemas, and non-regression of existing modules.
- Maintain 100% test pass rate across the entire test suite (`pytest tests/`).
- Document all new features and architecture in `docs/AUDIT_AND_RESOLUTIONS.md` and related documentation.

## Verification Resources
- Existing automated test suite: `tests/` (103 automated pytest tests across 12 test suites covering all platform capabilities).
- Reference UI & execution models: `frontend/js/exam-runner.js`.

## Acceptance Criteria

### Linux UI & Navigation
- [ ] The student interface displays a dedicated "Centre d'Entraînement Linux" with separate buttons/tabs for Théorique and Pratique.
- [ ] Completing or exiting a Linux exercise navigates back to the Linux Training Center hub without broken redirects.

### Virtual Terminal & Shell Commands
- [ ] Typing commands into the terminal executes them against the in-browser VFS and displays expected output with appropriate exit codes.
- [ ] Commands `ls -la`, `cd`, `pwd`, `mkdir -p`, `touch`, `cat`, `rm -r`, `cp`, `mv`, `chmod`, `grep`, `head`, `tail`, and `wc` behave consistently with POSIX conventions.
- [ ] Command piping (`cat file | grep pattern | wc -l`) and redirection (`echo text > file`, `echo more >> file`) correctly transform streams and files.
- [ ] Arrow keys navigate command history, and Tab autocompletes matching file and directory paths.

### Automated Challenge Evaluation
- [ ] Every practical Linux challenge validates both the command output and filesystem side-effects against public and hidden tests.
- [ ] Test execution displays clear pass/fail status cards without leaking hidden test criteria to DevTools console.
- [ ] Challenge navigator allows switching between exercises with real-time status indicators (unsolved, in-progress, solved).

### Integration & System Health
- [ ] All existing 103 pytest tests continue to pass with 100% success rate (`pytest tests/`).
- [ ] New automated tests in `tests/test_linux_training.py` pass with 100% success rate.
- [ ] Changes and architecture are documented in `docs/AUDIT_AND_RESOLUTIONS.md` and documentation files.
