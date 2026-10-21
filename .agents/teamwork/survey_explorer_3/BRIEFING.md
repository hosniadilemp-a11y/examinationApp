# BRIEFING — 2026-10-20T20:08:00Z

## Mission
Investigate backend architecture, database models, diagnostic placement, and testing framework for Linux Training Center integration.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, investigation, synthesis
- Working directory: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\survey_explorer_3
- Original parent: 6ba9e6b9-e9de-4958-abd5-dd2ad5895a59
- Milestone: Linux Training Center Backend Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strict decoupling of diagnostic tests / practice attempts from semester GPAs and official exams
- Produce report.md and handoff.md; communicate back via send_message

## Current Parent
- Conversation ID: 6ba9e6b9-e9de-4958-abd5-dd2ad5895a59
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `backend/app/main.py`: FastAPI configuration, auto-migration, lifespan, route mounts
  - `backend/app/database.py`: PostgreSQL/SQLite WAL fallback, SessionLocal, get_db
  - `backend/app/config.py`: Settings, environment flags, defaults
  - `backend/app/models.py`: User, Module, Exam, Question, StudentAttempt, PracticeAttempt, TrainingAttempt, ChapterProgress
  - `backend/app/schemas.py`: Pydantic models for practice, exams, questions, users
  - `backend/app/routers/practice.py`: 4 diagnostic placement tests (ALGO, PYTHON_INIT, CRYPTO, LINUX_ADMIN), scoring, history
  - `backend/app/routers/training_python.py`: Complete Python training center router architecture
  - `backend/app/services/training_service.py`: Progression state, gamification, curriculum loading
  - `backend/app/services/grading.py`: Evaluator for all question types + coding challenges
  - `backend/app/routers/admin.py`: `_build_student_bulletin` showing strict decoupling of diagnostic pillars from semester GPAs
  - `tests/`: 12 test suites, `conftest.py`, `pytest.ini`, executed `pytest` with 103/103 tests passing (100%)
- **Key findings**:
  1. Backend is FastAPI 0.115+ with SQLite WAL / PostgreSQL fallback.
  2. Diagnostic tests and practice attempts live in `practice_attempts` with `module_code="LINUX_ADMIN"`.
  3. `_build_student_bulletin` in `admin.py` displays `PracticeAttempt` under `fundamentals` / `diagnostic_scores`, while `official_scores`, `exams_average`, `general_average`, and `verdict` (ADMIS/AJOURNÉ) are computed strictly from `StudentAttempt` in `ExamSession`. Decoupling is 100% enforced and must remain so.
  4. Python training serves as the blueprint (`training_python.py` + `training_service.py` + `curriculum.json`). Linux training will mirror this with `training_linux.py`, `linux_training_service.py`, and `backend/app/data/linux_training/curriculum.json`.
  5. Test suite in `tests/` currently passes 103 tests. `tests/test_linux_training.py` will add comprehensive test coverage for curriculum loading, >=2 public tests & >=5 hidden tests, student secrecy, challenge submission, progress tracking, diagnostic linking, GPA decoupling, and RBAC.
- **Unexplored areas**: None. All 4 target areas thoroughly investigated.

## Key Decisions Made
- Confirmed architectural blueprint: mirror Python Training Center with dedicated `training_linux.py` and `linux_training_service.py`.
- Formulated decoupling guarantee: practice attempts link to `LINUX_ADMIN` diagnostic stats without entering official exam averaging.
- Outlined 10-point test specification for `tests/test_linux_training.py`.

## Artifact Index
- report.md — comprehensive survey report
- handoff.md — 5-component handoff report
