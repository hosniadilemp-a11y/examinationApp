# Project: Examination & Quiz Platform (Full-Scale Update & Security Audit)

## Architecture
- **Backend**: FastAPI with SQLAlchemy ORM, SQLite in WAL mode / PostgreSQL, Pydantic v2 schemas, Argon2 & JWT authentication.
- **Execution Sandbox**: Isolated subprocess runner with UTF-8 encoding, execution timeout enforcement, headless Matplotlib/Seaborn/Pandas base64 figure interception.
- **Frontend**: Vanilla ES6 SPA architecture (`frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`, `frontend/js/exam-runner.js`, `frontend/js/anticheat.js`), CodeMirror 5 with custom Python hint engine, KaTeX math typesetting.
- **Security & Integrity**: Strict separation of student payloads from correct answers and hidden tests; automatic student suspension on window blur / tab switch > 10s; HTTP 403 Forbidden enforcement on suspended attempts; authoritative server timer sync across page reloads.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | AlgoCompiler Fused Two-Pane Layout | Homogeneous two-pane layout (problem description + KaTeX math left; CodeMirror editor + toolbar + bottom console/test tabs right) without double scrollbars | M3 | R1 |
| 2 | CodeMirror Python Autocomplete & IntelliSense | Native Python autocomplete for keywords, builtins, standard libraries (`math`, `sys`, `pandas`, `matplotlib.pyplot`, `seaborn`, `collections`), auto-closing quotes/brackets, hint badges, Ctrl-Space and auto-trigger | M3 | R1 |
| 3 | Headless Data Science Execution & Figures | Execution of Matplotlib/Seaborn/Pandas with base64 PNG figure interception and rendering in student console | M3 | R1 |
| 4 | Coding Challenges Test Distribution | All coding problems in DB have >= 2 public test cases and >= 10 hidden test cases with protected output masking | M1 | R1 |
| 5 | Python Training Completion Navigation | Training session completion screen button displays "Retourner au Centre d'Entraînement Python ➔" returning to `#view-python` | M3 | R1 |
| 6 | Diagnostic Placement Tests Decoupling | 4 diagnostic tests (Python, Algo, Crypto, Linux) strictly decoupled from official module averages, academic GPAs, and semester bulletins | M1 | R2 |
| 7 | Module & Multi-Teacher Management | Support adding/updating modules and multiple teachers assigned per module; serialize `teachers` in `ModuleResponse` without `[object Object]` error | M1, M2 | R2, R6 |
| 8 | Strict Exam Type Separation Backend | Formally distinguish Épreuve Théorique (rejects coding) vs Épreuve Pratique (allows only coding) across models, schemas, and endpoints; serialize `exam_type` in `ExamResponse` and `get_available_exams` | M1 | R3 |
| 9 | Dynamic Question Authoring by Exam Type | Question builder adapts dynamically to chosen exam type, locking question types appropriately | M4 | R3 |
| 10 | Teacher Exam Management Structured Data Table | Redesign `#view-teacher` exam list as responsive data table with Title, Module, Type, Duration, Question Count, Total Points, Allowed Groups, Actions | M4 | R4 |
| 11 | Dedicated Step-by-Step Exam Creation Page | 2-step authoring: Step 1 (General config, exam type, rules), Step 2 (Integrated question builder, live points total, reordering, validation) | M4 | R4 |
| 12 | Anti-Cheating Hardening & Secrecy Invariants | Official answers and hidden tests never transmitted; fullscreen lock, 10s away countdown, suspension threshold, 403 Forbidden enforcement on submit/save/run | M1, M5 | R5 |
| 13 | Student Exam Card Action Button State Distinction | Ongoing attempt: "🔄 Rejoindre l'épreuve en cours ➔" (emerald); Waiting room: "⏳ Rejoindre la salle d'attente ➔" (amber); Not started: "Commencer l'épreuve ➔" (primary) | M5 | R5 |
| 14 | Session Resilience Across Reload | Student session survives F5 reload or reconnect with authoritative server timer resynchronization and zero progress loss | M1, M5 | R5 |
| 15 | Modern Glassmorphic Toast Notifications | Replace all raw browser `alert()` popups with sleek toast notifications (success, warning, danger, info) | M2 | R6 |
| 16 | Universal Escape Key Modal Dismissal | All modal dialogs dismiss immediately upon pressing Escape ("Échap") or clicking the backdrop | M2 | R6 |
| 17 | Clean In-Line Login Errors | `#login-error` displays invalid credentials cleanly without native browser alerts or spurious session expiry popups | M2 | R6 |
| 18 | Proctor Live Monitoring Dashboard Telemetry | Real-time monitoring of student connection status, heartbeat, progress %, remaining time, anti-cheat violations | M5 | R7 |
| 19 | Proctor Remote Controls & Bulk Unlock | Remote controls: individual and bulk attempt unlocking, time extension (+N minutes), force submit, session close | M1, M5 | R7 |
| 20 | Test Suite Maintenance (100% Pass) | Maintain 100% pass rate across automated test suite (`pytest tests/`) | E2E, M6 | R8 |
| 21 | Full Audit Logging & Resolutions Documentation | Comprehensive documentation of all fixes and security audits in `docs/AUDIT_AND_RESOLUTIONS.md` | M6 | R8 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Suite Track | Opaque-box 4-tier test suite development, test cases for R1-R8, publish TEST_READY.md | none | IN_PROGRESS |
| M1 | Backend Core & Security Foundations | Exam type serialization, transcript decoupling, ModuleResponse teachers, batch reordering & validation APIs, student code runner with 403 suspension guard, bulk unlock API | none | IN_PROGRESS |
| M2 | Frontend UX, Toasts, Modals & Clean Login | AppController.showToast implementation, replace all raw alert() calls, Escape & backdrop modal dismissal, inline login error, multi-teacher template fix | none | PLANNED |
| M3 | AlgoCompiler Two-Pane & CodeMirror Autocomplete | Fused two-pane workspace, CodeMirror Python autocomplete & hint badges, headless plot rendering, practice completion return button | M1 | PLANNED |
| M4 | Teacher Exam Management & Question Builder | Responsive data table in `#view-teacher`, dedicated 2-step exam creation wizard with dynamic question authoring and live points total | M1, M2 | PLANNED |
| M5 | Student Card States, Anti-Cheat & Proctor Dashboard | Exam card button state distinction, proctor live monitoring UI, bulk unlock action, simulation validation | M1, M2 | PLANNED |
| M6 | Final Verification, Adversarial Hardening & Audit Docs | 100% E2E test pass rate, adversarial test suite, forensic audit, update `docs/AUDIT_AND_RESOLUTIONS.md` | M1, M2, M3, M4, M5, E2E | PLANNED |

## Interface Contracts
### Backend ↔ Frontend API Contracts
1. **Exam Serialization (`ExamResponse`, `ExamDetailResponse`)**:
   - `exam_type: str` ("theoretical" | "practical") must always be serialized explicitly.
   - `total_question_points: float` (sum of attached question points) included in responses.
   - `passing_score: float` (default 10.0) included in responses.
2. **Module Serialization (`ModuleResponse`)**:
   - `teachers: List[UserBrief]` where `UserBrief = {id: str, username: str, full_name: str, role: str}`.
3. **Student Exam Card Actions (`/api/student/exams/available`)**:
   - Each item includes `exam_type: str`, `session_status: str` ("waiting" | "in_progress" | "no_active_session"), `attempt_status: str` ("not_started" | "waiting" | "in_progress" | "suspended" | "submitted" | "timed_out").
4. **Proctor Bulk Unlock (`POST /api/proctor/sessions/{session_id}/unlock-all`)**:
   - Unlocks all suspended student attempts in the room session, resets suspension reasons, broadcasts WebSocket update, returns `{unlocked_count: int, message: str}`.
5. **Question Reordering (`PUT /api/exams/{exam_id}/questions/reorder`)**:
   - Payload: `{"question_orders": [{"id": str, "display_order": int}]}` -> Returns 200 OK.
6. **Toast Notification Interface**:
   - `window.showToast(message: string, type: 'info' | 'success' | 'warning' | 'danger', duration?: number)`

## Code Layout
- `backend/app/models.py`: Database SQLAlchemy models (`Exam`, `Question`, `StudentAttempt`, `Module`, etc.)
- `backend/app/schemas.py`: Pydantic request/response schemas (`ExamResponse`, `ModuleResponse`, etc.)
- `backend/app/routers/exams.py`: Teacher exam and question management endpoints
- `backend/app/routers/student_exam.py`: Student exam delivery, autosave, submission, and statistics
- `backend/app/routers/modules.py`: Academic module management and teacher assignments
- `backend/app/routers/admin.py`: Admin statistics and student bulletin generation
- `backend/app/routers/proctor.py`: Proctor room sessions, telemetry, time extensions, unlock actions
- `backend/app/services/sandbox_runner.py`: Python code execution sandbox and figure extraction
- `frontend/index.html`: Main SPA HTML layout, views, and modal overlays
- `frontend/css/style.css`: Application styling, two-pane layout, toast animations, exam card themes
- `frontend/js/app.js`: Core frontend controller, view rendering, toasts, modal handlers, teacher view
- `frontend/js/exam-runner.js`: Exam & challenge player, CodeMirror editor, execution tabs, plot display
- `frontend/js/anticheat.js`: Focus loss detection, 10s countdown, suspension trigger
- `tests/`: Automated pytest test suite
- `scripts/simulate_all_exam_scenarios.py`: Full multi-scenario E2E exam simulation script
- `docs/AUDIT_AND_RESOLUTIONS.md`: Full audit logs and resolution documentation
