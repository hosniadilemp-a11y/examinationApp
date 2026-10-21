# Handoff Report — Milestone 1: Backend Models, APIs & Diagnostic Placement Decoupling

## 1. Observation
- **Initial Baseline Execution**: Prior to modifications, `pytest tests/` executed 107 test cases in 188.46s with 100% pass rate (`107 passed, 1 warning`).
- **Files Created / Modified**:
  - `backend/app/data/linux_training/challenges.json` (Created): 9 practical challenges organized across 4 levels. Every challenge defines `initial_fs`, `starter_cmd`, `solution`, `public_tests` (>= 2 test cases), and `hidden_tests` (>= 5 test cases).
  - `backend/app/data/linux_training/curriculum.json` (Modified): Added `curriculum_title`, `total_levels`, and 4 level definitions (`levels`) matching R3 while preserving all 6 existing chapters (`fhs_navigation`, `file_management`, `permissions_security`, `text_processing_pipes`, `processes_signals`, `bash_scripting`).
  - `backend/app/services/linux_training_service.py` (Created): Core business service implementing caching (`load_linux_curriculum`, `load_linux_challenges`), safe student projections (filtering `hidden_tests` and `solution`), multi-assertion challenge evaluation (stdout matching, exit codes, VFS file existence, contents, and permissions), and automatic persistence in `PracticeAttempt` with `module_code="LINUX_ADMIN"`.
  - `backend/app/services/training_linux_service.py` (Updated): Backwards compatibility re-export wrapper.
  - `backend/app/routers/training_linux.py` (Updated): Exposes 11 endpoints under `/api/training/linux`:
    - `GET /api/training/linux/curriculum`
    - `GET /api/training/linux/challenges`
    - `GET /api/training/linux/challenges/{challenge_id}`
    - `GET /api/training/linux/theory/quizzes`
    - `POST /api/training/linux/generate-session`
    - `POST /api/training/linux/submit-challenge`
    - `POST /api/training/linux/submit-session`
    - `GET /api/training/linux/progress` & `/progression`
    - `GET /api/training/linux/history`
    - `GET /api/training/linux/chapters` & `/chapters/{id}`
  - `backend/app/main.py`: Verified router inclusion (`app.include_router(training_linux.router)`).
  - `tests/test_linux_training.py` (Updated): 16 comprehensive automated pytest test cases covering curriculum structure, public/hidden test count rules, secrecy masking, session generation, challenge evaluation, persistence, diagnostic pillar sync, mathematical GPA decoupling, and RBAC 401 enforcement.
- **Test Results**:
  - `pytest tests/test_linux_training.py -v`: 16 passed, 0 failed in 23.57s.
  - `pytest tests/`: 119 passed, 0 failed in 202.35s (100% success rate, 0 regressions).

## 2. Logic Chain
1. *Requirement R3 / Dispatch item 1 & 2*: Required a progressive Linux curriculum spanning 4 levels with challenges requiring at least 2 public tests and at least 5 hidden tests.
   - Observation: `challenges.json` contains 9 progressive challenges across Levels 1-4 with 2 public tests and 5 hidden tests each. `curriculum.json` defines the 4 levels and maintains the 6 chapters with 8 additional practical exercises also providing 2 public and 5 hidden tests.
   - Verification: `test_linux_challenges_public_and_hidden_tests_counts` programmatically validates `len(pub) >= 2` and `len(hid) >= 5` for every challenge.
2. *Requirement R3 / Dispatch item 3 (Confidentiality & Evaluation)*: Required client-side protection so that hidden test assertions and reference solutions are never leaked in API payloads or DOM inspector.
   - Observation: `get_safe_challenges_list`, `get_challenge_detail_student`, and `get_theory_quizzes` omit `hidden_tests` and `solution`. In `evaluate_linux_challenge`, hidden test results are masked with `cmd: "[Protégé]"` and `expected: "[Protégé]"`.
   - Verification: `test_linux_curriculum_endpoint_student_view_secrecy` and `test_linux_submit_challenge_hidden_tests_masking` verify that no secret strings are leaked in GET or POST responses.
3. *Requirement R2 / Dispatch item 3 (Diagnostic Pillar & Strict Decoupling)*: Required synchronization with `practice_attempts` using `module_code="LINUX_ADMIN"` without altering official semester GPAs.
   - Observation: `sync_student_linux_pillar` inserts/updates only `PracticeAttempt` records. In `backend/app/routers/admin.py` and `student_exam.py`, semester averages and jury verdicts (`ADMIS` / `AJOURNÉ`) are computed strictly from `StudentAttempt` linked to `ExamSession`.
   - Verification: `test_linux_training_strict_decoupling_from_semester_gpa` calls `GET /api/student/bulletin` before and after Linux practice submissions, confirming that `general_average`, `exams_average`, and `verdict` remain strictly identical.
4. *Non-Regression*: Baseline had 107 passing tests; the expanded test suite has 119 tests, all passing without regression.

## 3. Caveats
- The backend challenge evaluation supports evaluating stdout, exit codes, and VFS file assertions. Client-side shell execution (in-browser VFS and interactive terminal UI) will be implemented in subsequent Milestones (M2/M3/M4).
- The `StaticPool` SQLite in-memory database used in tests guarantees complete isolation per test run; real SQLite WAL operates when running through uvicorn.

## 4. Conclusion
Milestone 1 is fully completed and verified.
- Data structures for curriculum (4 levels) and challenges (>= 2 public and >= 5 hidden tests per challenge) are deployed.
- Backend service `linux_training_service.py` and REST router `training_linux.py` are implemented and operational.
- Diagnostic pillar `LINUX_ADMIN` is synchronized while preserving strict mathematical decoupling from official semester GPAs.
- The automated test suite has expanded from 107 to 119 tests with 100% pass rate.

## 5. Verification Method
Execute the following commands from the root directory:
```powershell
# Run the Linux training test suite (16 tests)
pytest tests/test_linux_training.py -v

# Run the complete test suite (119 tests)
pytest tests/
```
Inspect files:
- `backend/app/data/linux_training/curriculum.json`
- `backend/app/data/linux_training/challenges.json`
- `backend/app/services/linux_training_service.py`
- `backend/app/routers/training_linux.py`
- `tests/test_linux_training.py`
