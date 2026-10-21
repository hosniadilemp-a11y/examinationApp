# DISPATCH — m1_worker

## Task
Implement Milestone 1: Backend Models, APIs & Diagnostic Placement Decoupling for Linux Training Center.

## Input Documents
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST READ)
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\orchestrator_2\PROJECT.md`
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\orchestrator_2\TEST_INFRA.md`
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\survey_explorer_3\report.md` (Detailed blueprint)

## Ownership & Scope Boundaries
You own exclusively:
- `backend/app/data/linux_training/curriculum.json`
- `backend/app/data/linux_training/challenges.json`
- `backend/app/services/linux_training_service.py`
- `backend/app/routers/training_linux.py`
- `backend/app/main.py` (route registration only)
- `tests/test_linux_training.py` (initial backend test cases)

DO NOT modify frontend files or unrelated backend modules.

## Requirements
1. Create `backend/app/data/linux_training/` with `curriculum.json` (4 levels: Level 1 Navigation, Level 2 Permissions & Filters, Level 3 Scripts & Pipes, Level 4 Sysadmin) and `challenges.json`.
2. Mandatory Rule: Every challenge MUST have at least 2 public test cases and at least 5 hidden test cases!
3. Implement `backend/app/services/linux_training_service.py`:
   - Load and cache curriculum and challenges
   - Safe student view projection (filter out `hidden_tests` and `solution`)
   - Submission evaluation (comparing stdout and filesystem changes)
   - Synchronize with `practice_attempts` using `module_code="LINUX_ADMIN"`
   - Strict decoupling: never touch `StudentAttempt` or official exam GPAs
4. Implement `backend/app/routers/training_linux.py` exposing:
   - `GET /api/training/linux/curriculum`
   - `GET /api/training/linux/challenges`
   - `GET /api/training/linux/challenges/{challenge_id}`
   - `GET /api/training/linux/theory/quizzes`
   - `POST /api/training/linux/generate-session`
   - `POST /api/training/linux/submit-challenge`
   - `POST /api/training/linux/submit-session`
   - `GET /api/training/linux/progress`
   - `GET /api/training/linux/history`
5. Register router in `backend/app/main.py`.
6. Create `tests/test_linux_training.py` and run pytest:
   `pytest tests/test_linux_training.py` and `pytest tests/` (all 103+ tests must pass).
7. Produce `handoff.md` and report back.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-10-20T20:32:18Z
Received dispatch from 6ba9e6b9-e9de-4958-abd5-dd2ad5895a59:
Implement Milestone 1: Backend Models, APIs & Diagnostic Placement Decoupling:
- backend/app/data/linux_training/curriculum.json & challenges.json (4 levels, >=2 public tests & >=5 hidden tests per challenge)
- backend/app/services/linux_training_service.py
- backend/app/routers/training_linux.py
- Register router in backend/app/main.py
- Create tests/test_linux_training.py and run pytest tests/test_linux_training.py & pytest tests/
