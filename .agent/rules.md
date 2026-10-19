# Directives et Règles du Projet (Antigravity Agent Rules)
# AGENTS.md — Instructions for LLM coding agents

Project: Multi-Module Examination & Training Platform (LAN, distributed room servers).
Source of truth: `EXAM_APP_SPECIFICATION.md`. This file adds locked decisions and working rules.
If this file and the spec disagree, THIS FILE wins for the items listed under "Locked decisions". For everything else the spec wins.

---

## 0. Golden rules (read first)

1. **Never guess.** If a requirement is missing, ambiguous, or listed in "Open decisions" (section 12), STOP and ask the user. Do not invent behavior.
2. **Never contradict a locked decision** (section 1) without asking.
3. **No internet at runtime.** Nothing may fetch from a CDN, font host, analytics, or external API. All assets are vendored locally.
4. **The server is the authority.** The browser is untrusted. Timers, scores, suspension state, and answer correctness are decided and stored server-side.
5. **Never send correct answers to a student client during an official exam.** Correct keys and explanations leave the server only after submission (official exams) or after answering (free practice tests).
6. **Do not edit `oldapps/`.** It is read-only reference material. Port logic by reading it, never by importing it.
7. **Small, tested changes.** One feature per change. Every change ships with tests. Run the full test suite before declaring done.
8. **Do not add dependencies** (Python or JS) without asking. Prefer the standard library.

---

## 1. Locked decisions

| Topic | Decision |
| :--- | :--- |
| Frontend | Vanilla JavaScript (ES modules) + Web Components. No framework, no bundler, no build step, no npm runtime dependencies. |
| UI language | French only. UI text is written directly in French. No i18n library. Code, identifiers, comments, commit messages, and docs are in English. |
| Exam package format | `.exam` = gzip-compressed JSON, **plain (no encryption, no signature)**. See section 6. This knowingly deviates from spec section 2.2 ("encrypted/signed"). |
| Deployment | Docker Compose. Docker is a prerequisite on every room server and on the master. |
| Student authentication | User ID + password, hashed with argon2 (or bcrypt if argon2 is unavailable). Initial password = the student ID, and the first login forces a password change. Teachers (for their students) and admins can reset a password back to the student ID, which again forces a change. Accepted risk: until it is changed, anyone who knows the ID can log in as that student. |
| Scoring (`multi_choice`) | Per-option sum with absolute penalty and floor. See section 4. |
| Network disconnects | Timer keeps running, no suspension for offline time. See section 5. |
| Package import timing | Import just before the exam session. See section 6. |
| Python training runtime | Pyodide running in the student's browser inside a Web Worker. Pyodide files are vendored locally. No server-side execution of student code. |
| Scale target | Up to 30 simultaneous students per room server. |
| Legacy code | Available in `oldapps/` (read-only). See section 9. |
| Student grouping | By **Groups** only (never "specialty"). |

---

## 2. Architecture rules

- Two deployable roles from one codebase: **Master** and **Room Server**, selected by configuration (`APP_ROLE=master|room`).
- A Room Server must run with zero connectivity to the Master or the internet during an exam.
- A failure or restart in one room must never affect another room. Rooms share no runtime state.
- Data moves between Master and rooms only through files: exam packages (Master → Room) and result bundles (Room → Master), via LAN upload or USB.
- Room Server storage: SQLite in WAL mode, with a single writer path and batched writes for autosave and telemetry (30 students, frequent heartbeats).
- Master storage: SQLite by default, PostgreSQL optional. Write portable SQL through the ORM; do not use database-specific features.
- Live monitoring: WebSocket between student client, server, and teacher dashboard. Every message type has a documented schema (see section 8).

### Suggested layout (adapt only after asking)

```
backend/
  app/
    core/            # config, security, db, roles
    exam_engine/     # question types, scoring, session state machine
    monitoring/      # WebSocket hub, suspension logic
    training/        # Python chapters, evolution mode
    sync/            # package export/import, result bundles
    api/             # routers per resource
  tests/
frontend/
  student_exam/
  teacher_monitor/
  admin/
  training/
  shared/            # web components, api client, styles
  vendor/pyodide/    # vendored, offline
data/
  curriculum/python/
  practice_tests/    # 4 free tests x 30 questions
docker/
oldapps/             # READ-ONLY legacy reference
```

---

## 3. Roles and permissions

Enforce permissions **on the server for every endpoint**, never only by hiding UI. Implement the matrix in spec section 4.2 as a single, tested policy module (`core/permissions.py`) and reuse it everywhere.

- Super Administrator: full access.
- Teacher: only assigned modules, only own sessions. A teacher must never read another teacher's sessions or modules.
- Student: only exams assigned to their Group, only their own scores.
- Admin and Teacher cannot take official exams. They can use free practice tests and Python training.
- Write a test for every cell of the permission matrix.

---

## 4. Question engine and scoring

Supported types: `boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching`.

- Scoring is a **pure function**: `score(question, answer, policy) -> float`. No I/O, no clock, no randomness. Cover it with exhaustive unit tests (all-correct, all-wrong, partial, no selection, "no option applies", penalty floor).
- Policy hierarchy: per-question override > exam-level preset > system default.
- Score floor per question defaults to 0 and is configurable (can be negative).
- `multi_choice` supports the case where **no option is correct** (empty `correct_keys`). An empty answer is then correct.
- `fill_blank`: normalize whitespace; case-insensitivity is optional per question; accepted answers may be a list.
- Use `Decimal` or fixed rounding rules for scores. Never compare floats with `==`.
- **`multi_choice` formula (decided):** each correct selection earns `points / number_of_correct_options`; each incorrect selection subtracts `negative_penalty` (absolute points); unselected options score nothing; sum the result, then apply the floor. Example: 4 points, 3 correct options, penalty 0.5, two correct picks and one wrong pick = `2 x 4/3 - 0.5 = 2.17`. Use this as a unit test.
- **Still open (section 12, item 1):** partial credit for `matching`, wrong-answer scoring for `boolean` and `single_choice`, and the divide-by-zero case when `multi_choice` has no correct option. Do not implement these until the user confirms; implement the formula above only for `multi_choice` with at least one correct option.

---

## 5. Anti-cheating and exam session integrity

The client-side lockouts are **deterrents, not security**. Real enforcement is server-side.

- Student client requests fullscreen at start, blocks copy/cut/paste shortcuts, right-click, and text selection outside inputs, and logs clicks outside answer/navigation zones. Every blocked action produces a telemetry event.
- **10-second rule:** if the client reports it left fullscreen, switched tab, or lost focus for more than 10 consecutive seconds, the session becomes `SUSPENDED`.
  - The server decides, using timestamps it receives and its own clock. A missing heartbeat is treated separately from an away event.
  - **Disconnects (decided):** a lost connection is NOT an absence. The card shows Disconnected/Reconnecting, the server timer keeps running, and the 10-second rule does not count offline time. On reconnect the client resyncs and continues. Window/fullscreen/tab events recorded while connected, or reported after reconnecting, still count.
  - Suspension state is persisted in the database, so a browser refresh or reconnect does not clear it.
  - Answers entered before suspension are preserved.
  - Only a Teacher (own session) or Admin can unlock, via the proctor action. Students can never unlock.
- The exam timer is **server-authoritative**. The client countdown is cosmetic. Extra time, pause, and resume are server actions.
- Autosave answers on a short interval and on every answer change. A crash or reboot must lose at most the last few seconds of answers.
- Every proctor action and security event is written to an append-only audit log (who, what, when, session).
- Proctor actions: unlock, grant extra time (per student or room-wide), pause/resume one student, force-submit.

---

## 6. Data formats and sync

### CSV import (admin)
- `students.csv`: `student_id, full_name, email, group_id, group_name`
- `teachers.csv`: `teacher_id, full_name, email, assigned_modules`
- `groups.csv`: `group_id, group_name, description`
- `modules.csv`: `module_code, module_name, description`
- Import is validated row by row. Return a report of accepted and rejected rows with reasons. Never half-apply a file silently. Use UTF-8 and handle a BOM.

### JSON exam authoring
Per question: `type`, `prompt` (Markdown with code snippets), `options`, `correct_keys`, `scoring` (`points`, `negative_penalty`, `partial_credit_enabled`), optional `time_limit_seconds`. Validate with a strict schema; reject unknown fields with a clear error.
Render Markdown safely: sanitize HTML to prevent XSS from question content.

### Exam package (`.exam`)
- gzip JSON containing exam metadata, questions, assets, timer rules, scoring schemes.
- Include `schema_version`. Importers reject unknown major versions.
- Include a SHA-256 checksum field to detect **accidental corruption** only. It is not a security feature.
- Because packages are plain, teachers import the package on the room server just before the exam session. The server sends question content to students only after the session starts, and archives or deletes the package file after import.

### Result bundle (`.results.zip` / `.csv`)
- Single exam or all exams of a room. Master import must be **idempotent**: re-importing the same bundle never duplicates results.
- Master aggregation produces `master_grades.csv` and PDF/CSV statistics: mean, standard deviation, discrimination index, flagged anomalies, suspension logs.

---

## 7. Frontend rules

- ES modules and Web Components only. No framework, no bundler, no CDN, no remote fonts. Vendor everything under `frontend/vendor/`.
- Modern, clean dashboard aesthetic with dark and light themes using CSS custom properties (design tokens). Accessible: keyboard navigation, focus states, sufficient contrast.
- UI strings are in French. Keep them readable and consistent. Do not mix English into the UI.
- Responsive from lab-PC screens to tablets.
- Never trust data from the DOM or the client: validate again on the server.
- Student exam view must not expose answer keys in HTML, JS, network responses, or the console.

### Python training (Pyodide)
- Run in a Web Worker so the UI never freezes. Enforce an execution timeout and the ability to interrupt an infinite loop.
- Pyodide runtime files are vendored locally. Verify it loads with the network disabled.
- Chapter-by-chapter training and Evolution mode (difficulty adapts to previous chapter attempts). Port the evolution algorithm from `oldapps/QuizApp`.

---

## 8. Real-time telemetry

- Define each WebSocket message in one schema file shared by backend tests and frontend docs: `type`, `session_id`, `student_id`, `ts`, payload.
- Required teacher grid data per student: connection state (online / disconnected / reconnecting), security state (normal / focus warning / suspended), current question index and progress, answer states (answered / unanswered / marked for review), elapsed vs remaining time.
- Client reconnects automatically with backoff and resumes the same session.
- Throttle and batch events. Target: 30 students without noticeable lag.

---

## 9. Working with legacy code (`oldapps/`)

Mapping (from spec section 9):

| Legacy source | Port to | Reuse |
| :--- | :--- | :--- |
| `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoExamination` | `monitoring/`, `frontend/teacher_monitor/` | proctoring UI, telemetry schema, suspension controls, student state tracking |
| `oldapps/QuizApp/QuizApp/` | `training/`, `data/curriculum/python/` | Python curriculum, chapters, `.quiz` format, evolution scoring |
| `oldapps/TP_DM/` | `frontend/student_exam/`, `exam_engine/` | exam workflow, question rendering, timers, autosave |

Rules:
- **Read the legacy source before implementing the matching feature.** Spec says "100% preservation of all functional workflows". Write down what the legacy app does, then port it.
- If legacy behavior is unclear or contradicts the spec, ask the user.
- Provide a converter for the legacy `.quiz` format if the curriculum data cannot be reused directly.
- Do not copy legacy code that depends on the internet, on desktop-only APIs, or has known security problems. Reimplement it.

---

## 10. Free practice tests

Four tests, 30 questions each, available to all students 24/7 with no scheduling: Algorithmique, Python, Cryptographie, Administration Linux.

- Instant score, per-question explanations, and breakdown after completion.
- Practice results are stored separately from official exam results and never enter Master grade aggregation.
- Question content must be provided or approved by the user. Do not fabricate curriculum questions as final content (see section 12).

---

## 11. Engineering standards and definition of done

Defaults (change only after asking):
- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic migrations, pytest, ruff, mypy where practical.
- Passwords: argon2. Rate-limit login. Session tokens are short-lived and server-validated.
- Type hints everywhere in backend code. No bare `except`. Structured logging, never log passwords or tokens.
- Database changes always go through a migration.

A task is done only when:
1. It matches the spec and this file.
2. Unit tests pass, and API tests exist for every new endpoint including permission-denied cases.
3. For exam-critical paths (scoring, suspension, timer, autosave, package import), tests cover failure cases.
4. `docker compose up` starts the stack from a clean checkout with no network access.
5. No new network calls, CDN links, or undeclared dependencies.
6. The change is summarized with files touched and anything left open.

---

## 12. Open decisions — ASK the user, do not decide

Numbering matches section 12 of `EXAM_APP_SPECIFICATION.md`.

1. Scoring edge cases: partial credit for `matching`, wrong-answer scoring for `boolean` and `single_choice` (penalty or 0), and `multi_choice` with no correct option (the formula divides by zero).
2. Who writes the 120 practice questions and the Python curriculum questions, and in what format.
3. Per-module permissions: "Own sessions" for teachers, exact meaning when several teachers share a module.
4. Backup and recovery policy for room databases, and what happens if a room server dies mid-exam.
5. Master hosting model: where it runs, who administers it, how result bundles are transported.
6. Browser support matrix for student terminals (needed for fullscreen and Pyodide behavior).
7. Test strategy for the browser UI (end-to-end tool) and CI environment.
8. Whether question and exam content needs images or other media assets, and size limits.
9. Retention of audit logs and student data (privacy and institutional policy).
10. Confirm Docker can be installed on every room server and on the master.
## Règle Fondamentale : Documentation Systématique des Mises à Jour
Chaque mise à jour, évolution fonctionnelle, modification d'architecture ou refonte d'interface doit être immédiatement et scrupuleusement documentée dans le dossier de spécifications (`docs/spec.md` et `docs/ARCHITECTURE_AND_SYSTEM_DESIGN.md`).

## Règles Architecturales & Techniques :
1. **Frontend Vanilla Strict :** HTML5, CSS3 moderne et Vanilla JavaScript (ES Modules). Aucun framework (React, Vue), aucun bundler (Webpack, Vite), aucune dépendance CDN externe.
2. **Fonctionnement 100% Hors-Ligne :** Tout composant, police, runtime (Pyodide WebAssembly) doit être stocké et servi localement sur le réseau LAN autonome.
3. **Localisation Intégrale :** 100% des interfaces, messages d'erreurs, badges et en-têtes doivent être en Français.
4. **Intégrité des Évaluations :** Maintien absolu du secret des réponses correctes côté serveur, double brassage déterministe (questions et options) et barème avec pénalité paramétrable.
5. **Validation par les Tests :** Chaque fonctionnalité ajoutée doit être couverte par des tests automatisés dans `tests/` sans aucune régression autorisée.
