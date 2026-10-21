# Backend Architecture & Codebase Survey Report (R1 - R7)

## Executive Summary
This survey provides a comprehensive audit of the backend architecture of the Examination & Quiz platform (`ExaminationQuiz APP`), evaluating readiness against requirements R1 through R7 defined in `ORIGINAL_REQUEST.md`. The backend is built on **FastAPI** with **SQLAlchemy ORM**, backed by an automated dual-engine storage architecture (**PostgreSQL** with transparent fallback to local **SQLite in WAL mode**), **Pydantic v2** schemas, **Argon2 / JWT** authentication, and a headless execution sandbox runner. 

The existing automated test suite (`pytest tests/`) currently achieves a **100% pass rate (85 passed in 202s)**. However, deep code-level inspection reveals significant architectural deficiencies and missing endpoints:
1. **Exam Type Serialization Bug (R3)**: `ExamResponse` in `backend/app/routers/exams.py` completely omits `exam_type=e.exam_type` in constructor calls across all listing, creation, and detail endpoints, causing all practical exams to default to `"theoretical"` in API payloads.
2. **Academic Transcript Contamination (R2)**: `_build_student_bulletin` (`backend/app/routers/admin.py`) and `get_student_statistics` (`backend/app/routers/student_exam.py`) blend on-demand diagnostic placement test scores (`f_scores` / `m_practice`) directly into official module averages and general GPAs (`all_scores = f_scores + exam_scores`), directly violating R2's strict decoupling mandate.
3. **Module Teacher Assignment Serialization (R2 & R6)**: `ModuleResponse` schema lacks a `teachers` relation attribute, returning `undefined` in frontend admin tables and triggering `[object Object]` error strings during assignment modal views.
4. **Execution Sandbox Gap in Official Practical Exams (R1 & R5)**: While the sandbox runner (`sandbox_runner.py`) correctly handles subprocess execution, timeout guards, and headless Matplotlib/Seaborn base64 figure extraction, no endpoint exists under `/api/student/attempts/...` allowing students to run code against public tests during official machine exams with anti-cheat 403 suspension guards.
5. **Missing Teacher Workflow Endpoints (R4)**: The exam creation and question builder workflow lacks a batch question reordering endpoint (`PUT /api/exams/{exam_id}/questions/reorder`), an exam readiness validation endpoint (`GET /api/exams/{exam_id}/validate`), live point total calculation properties, and `passing_score` configuration.
6. **Missing Proctor Controls (R7)**: The proctoring system lacks a bulk attempt unlocking endpoint (`POST /api/proctor/sessions/{session_id}/unlock-all`).

---

## 1. Observation

### 1.1 Test Suite Status and Baseline Health
- Command executed: `pytest` in `c:\Users\adel\Documents\ExaminationQuiz APP`
- Output: `85 passed, 1 warning in 202.30s (0:03:22)`
- Coverage includes: `test_phase1.py` (Auth/RBAC/CRUD), `test_phase2.py` (Grading/Exams), `test_phase3.py` (Student runner/Auto-save/Anti-cheat), `test_phase4.py` (Proctoring/Telemetry), `test_phase5.py` (Package sync/SHA256), `test_phase6.py` (Curriculum/Gamification), `test_phase7.py` (Turnkey launcher/Load 30 concurrent students), `test_phase8_revisions.py` (Bulletins/Waiting room/Secrecy), `test_phase9_features.py` (Item analysis/Exports), `test_sandbox_and_challenges.py` (Sandbox execution & figure extraction).

### 1.2 Database Engine & Auto-Migration Mechanics
- `backend/app/database.py:9-39`: Prioritizes PostgreSQL (`postgresql://...`), falling back to SQLite (`sqlite:///./exam_app.db`) with WAL mode (`PRAGMA journal_mode=WAL`), `PRAGMA synchronous=NORMAL`, `PRAGMA foreign_keys=ON`, and `PRAGMA busy_timeout=10000`.
- `backend/app/main.py:13-52` (`_auto_migrate_schema`): Dynamically adds missing columns to SQLite on startup via `PRAGMA table_info` and `ALTER TABLE`:
  - `users.plain_password VARCHAR`
  - `training_attempts.target_topic VARCHAR`, `target_difficulty VARCHAR`, `passed BOOLEAN DEFAULT 0`, `hints_used INTEGER DEFAULT 0`
  - `practice_attempts.warnings_count INTEGER DEFAULT 0`
  - `exams.exam_type VARCHAR DEFAULT 'theoretical'`

### 1.3 Requirement R1 Observations (Coding Challenges & Sandbox)
- Challenge Storage:
  - `backend/app/data/python_training/coding_challenges.json`: Contains **47 challenges**. Inspection confirmed minimum public test count is **2** and minimum hidden test count is **10** across all 47 items.
  - `backend/app/data/python_training/curriculum.json`: Contains **183 exercises**. Inspection confirmed each coding exercise has at least **2 public tests** and **10 hidden tests**.
  - `exam_app.db` (`questions` table): Contains **49 coding questions** (e.g., `PRAC-Q-001` through `PRAC-Q-047` in `EXAM-DEV-PRAC`). Verified that `options_json` contains `starter_code` and `public_tests` (>= 2), while `correct_answers_json` contains all tests including hidden tests (>= 10).
- Execution Sandbox (`backend/app/services/sandbox_runner.py`):
  - `FIGURE_HOOK` (lines 12-34) injects matplotlib figure detection via `_mpl_plt.get_fignums()`, exporting figures into base64 PNGs embedded in stdout as `__ALGO_FIGURES_JSON__:[...]`.
  - `extract_figures_and_clean_stdout()` (lines 36-54) cleans stdout and extracts the base64 figure array.
  - `run_python_script()` (lines 63-112) runs isolated subprocess with `MPLBACKEND=Agg` non-interactive backend, timeout enforcement (`subprocess.TimeoutExpired`), and UTF-8 encoding.
  - `execute_user_code_against_tests()` (lines 141-235) masks hidden tests when `mask_hidden_output=True`, setting `input="[Test Caché]"`, `expected_output="[Protégé]"`, and `actual_output="[Protégé]"`.
- Defect: `/api/training/python/run-tests` (`backend/app/routers/training_python.py:617-666`) only inspects `curriculum.json` and `coding_challenges.json`. It does NOT query the database `Question` table. Consequently, official practical exam questions authored by teachers cannot be tested through this endpoint.

### 1.4 Requirement R2 Observations (Diagnostic Decoupling & Module Teachers)
- Diagnostic Tests Configuration (`backend/app/routers/practice.py:19-44`):
  - 4 diagnostic tests defined: `ALGO` (seed_algo_30.json), `PYTHON_INIT` (seed_python_30.json), `CRYPTO` (seed_crypto_30.json), `LINUX_ADMIN` (seed_linux_30.json).
  - Attempt records stored in `PracticeAttempt` table (`grade_20`, `answers_json`, `warnings_count`).
- **Defect in Academic Average Calculation** (`backend/app/routers/admin.py:334-434`):
  - Line 348-360 calculates `f_scores` from `PracticeAttempt` (the diagnostic tests).
  - Line 387-388 calculates `exam_scores` from `StudentAttempt` (official exams).
  - Line 390-391 verbatim:
    ```python
    all_scores = f_scores + exam_scores
    general_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    ```
  - Line 394-396 sets verdict:
    ```python
    is_pass = general_avg >= 10.0
    verdict = "ADMIS" if is_pass else "AJOURNÉ"
    ```
  - This couples the 24/7 on-demand diagnostic placement tests with the official transcript GPA and admission verdict.
- **Defect in Student Statistics** (`backend/app/routers/student_exam.py:578-580`):
  - Verbatim:
    ```python
    all_m_marks = m_official + m_practice + m_training
    best_mark = max(all_m_marks) if all_m_marks else 0.0
    avg_mark = round(sum(all_m_marks) / len(all_m_marks), 2) if all_m_marks else 0.0
    ```
  - Diagnostic practice attempts and training sessions contaminate the official module averages.
- **Defect in Teacher Assignment Serialization** (`backend/app/schemas.py:63-67`):
  - `ModuleResponse` definition:
    ```python
    class ModuleResponse(ModuleBase):
        created_at: datetime
        model_config = ConfigDict(from_attributes=True)
    ```
  - `ModuleResponse` has NO `teachers` attribute!
  - In `backend/app/routers/modules.py:14-21` (`list_modules`) and `lines 48-58` (`get_module`), `response_model=List[ModuleResponse]` and `response_model=ModuleResponse` drop the `teachers` relation.
  - In `frontend/js/app.js:3636` and `3727-3730`, the client accesses `m.teachers` and `modData.teachers`. Because the field is omitted by Pydantic, it evaluates to `undefined`, leading to display failures and `[object Object]` error messages.

### 1.5 Requirement R3 Observations (Theoretical vs Practical Exam Separation)
- Database schema: `Exam.exam_type` exists in `backend/app/models.py:79`.
- **Defect in Exam Response Serialization** (`backend/app/routers/exams.py`):
  - In `list_exams` (lines 54-71), `ExamResponse` is instantiated without passing `exam_type`:
    ```python
    resp = ExamResponse(
        id=e.id,
        module_code=e.module_code,
        title=e.title,
        instructions=e.instructions,
        duration_minutes=e.duration_minutes,
        global_points=e.global_points,
        navigation_mode=e.navigation_mode,
        shuffle_questions=e.shuffle_questions,
        shuffle_options=e.shuffle_options,
        partial_credit_enabled=e.partial_credit_enabled,
        default_negative_penalty=e.default_negative_penalty,
        created_by=e.created_by,
        created_at=e.created_at,
        question_count=count,
        assigned_groups=group_ids
    )
    ```
  - In `create_exam` (lines 184-200), `load_exam_template` (lines 325-341), `import_exam_template_payload` (lines 351-367), `get_exam_detail` (lines 382-399), and `update_exam` (lines 440-456), `exam_type` is omitted in `ExamResponse` and `ExamDetailResponse`. Because `ExamBase.exam_type` defaults to `"theoretical"` in `schemas.py:163`, all exams are returned as `"theoretical"` regardless of the DB column value!
- **Defect in Available Exams Endpoint** (`backend/app/routers/student_exam.py:58-71`):
  - `get_available_exams` returns a manual dictionary omitting `"exam_type"`. The student dashboard has no way of displaying whether the exam card is an "Épreuve Théorique" or an "Épreuve Pratique".
- **Defect in Question Type Enforcement**:
  - `create_question` (`exams.py:503-513`) validates question type against `exam.exam_type`.
  - BUT `update_question` (`exams.py:502-517`) does NOT check `exam_type` when `payload.type` is altered.
  - `create_exam` (`exams.py:114-129`) does NOT validate embedded questions in `payload.questions` against `new_exam.exam_type`.
  - `import_questions_json` (`exams.py:554-582`) does NOT validate questions against `exam.exam_type`.
  - Practical exam questions are never validated to verify that they possess `>= 2 public` and `>= 10 hidden` test cases.

### 1.6 Requirement R4 Observations (Teacher Exam Creation & Question Authoring)
- `backend/app/routers/exams.py`:
  - Has `POST /api/exams` and `POST /api/exams/{exam_id}/questions`.
  - Missing batch reordering endpoint: Teachers currently must make N individual `PUT` requests to reorder questions.
  - Missing total question points calculation: `ExamResponse` contains `global_points` and `question_count`, but not `total_question_points` (sum of points of all attached questions).
  - Missing exam readiness validation endpoint: No single endpoint verifies whether an exam is valid for launch (e.g., question count > 0, total points equal global_points, exam type constraints fulfilled).
  - Missing `passing_score` column on `Exam` (defaults to 10.0 sur 20).

### 1.7 Requirement R5 Observations (Anti-Cheating, State Distinction & Timer)
- State Secrecy:
  - In `start_or_resume_exam` (`student_exam.py:209-230`), `correct_answers_json` is not serialized to students.
  - For coding questions, `options_json` contains `starter_code` and `public_tests`. Hidden tests are safely kept in `correct_answers_json`.
- Suspension Enforcement:
  - `save_student_answer` (`student_exam.py:266-267`) and `submit_official_exam` (`student_exam.py:417-418`) enforce:
    ```python
    if attempt.status == "suspended":
        raise HTTPException(status_code=403, detail="Votre épreuve est suspendue. Déblocage surveillant requis.")
    ```
  - Defect: There is no student code runner endpoint in `student_exam.py`, so if students execute code via `training_python.py/run-code`, suspended students are not blocked.
- State Distinction:
  - `get_available_exams` (`student_exam.py:58-71`) returns `session_status` (`waiting`, `in_progress`, `no_active_session`) and `attempt_status` (`not_started`, `waiting`, `in_progress`, `suspended`, `submitted`, `timed_out`).
- Timer Resynchronization:
  - Server computes authoritative `remaining_seconds = max(0, total_seconds - elapsed_seconds)` on every autosave (`save-answer`), attempt start/resume (`start`), and status poll (`status`). Time extensions in `proctor.py:367` adjust `started_at` backwards to cleanly grant extra minutes across reloads.

### 1.8 Requirement R7 Observations (Proctor Live Monitoring Dashboard)
- Endpoints in `backend/app/routers/proctor.py`:
  - `GET /sessions`: Lists active room sessions.
  - `POST /sessions`: Opens a room session (status `"waiting"`).
  - `GET /sessions/{session_id}/overview`: Returns telemetry grid (`student_cards` with `student_id`, `status`, `is_online`, `answered_count`, `total_questions`, `progress_pct`, `elapsed_seconds`, `remaining_seconds`, `last_activity_seconds`, `client_ip`, `raw_score`, `final_mark`).
  - `POST /sessions/{session_id}/launch`: Synchronous room launch triggering all waiting attempts to `"in_progress"`.
  - `POST /sessions/{session_id}/extend-time`: Grants +N minutes collective or individual extra time.
  - `POST /sessions/{session_id}/attempts/{attempt_id}/force-submit`: Forces submission of a specific student attempt.
  - `POST /sessions/{session_id}/attempts/{attempt_id}/unlock`: Unlocks an individual suspended student attempt and resets warnings.
  - `POST /sessions/{session_id}/close`: Closes the session and seals all remaining unsubmitted attempts.
  - WebSocket: `/ws/session/{session_id}/teacher` and `/ws/session/{session_id}/student/{student_id}` for live telemetry and heartbeats.
- Missing endpoint: There is no bulk unlock endpoint (`POST /sessions/{session_id}/unlock-all`) to unlock all suspended students at once in the event of room-wide false alarms (e.g. accidental OS notification focus loss).

---

## 2. Logic Chain

1. **Premise**: R3 requires that exams be formally categorized as either "Épreuve Théorique" or "Épreuve Pratique" and that API payloads reflect this choice.
   - *Observation*: `Exam.exam_type` exists in `models.py:79`, but `ExamResponse` in `exams.py` never passes `exam_type=e.exam_type`.
   - *Deduction*: When the frontend or client calls `GET /api/exams`, `POST /api/exams`, `GET /api/exams/{id}`, or `PUT /api/exams/{id}`, Pydantic initializes `exam_type` with its default value `"theoretical"`. Even if a teacher creates a practical exam, the API reports it as theoretical.
   - *Conclusion*: `exams.py` must explicitly pass `exam_type=getattr(e, 'exam_type', 'theoretical')` in all `ExamResponse` and `ExamDetailResponse` constructors, and `get_available_exams` in `student_exam.py` must include `exam_type`.

2. **Premise**: R2 mandates that the 4 diagnostic placement tests must be strictly decoupled from official semester module averages, academic GPAs, or exam transcripts.
   - *Observation*: `_build_student_bulletin` in `admin.py:390` performs `all_scores = f_scores + exam_scores` and computes `general_avg = sum(all_scores) / len(all_scores)`. Furthermore, `get_student_statistics` in `student_exam.py:578` computes `all_m_marks = m_official + m_practice + m_training`.
   - *Deduction*: A student who takes on-demand practice tests in `ALGO`, `CRYPTO`, or `LINUX_ADMIN` has their official academic GPA, module averages, and graduation verdict (`ADMIS` / `AJOURNÉ`) altered by informal self-assessment attempts.
   - *Conclusion*: Official module averages and academic graduation verdicts must be calculated exclusively from official examination attempts (`StudentAttempt`). The bulletin and statistics structures must separate `official_semester_average` and `official_verdict` from the diagnostic placement indicators (`fundamentals` and `fundamentals_average`).

3. **Premise**: R6 and R2 require that multiple teachers can be assigned to modules without error.
   - *Observation*: `models.py:11-16` defines a Many-to-Many association table `teacher_modules`. `ModuleResponse` in `schemas.py:63-67` lacks a `teachers` attribute, and `openAdminAssignModuleModal` in `frontend/js/app.js:3727` reads `modData.teachers || []`.
   - *Deduction*: When the frontend queries a module, the API returns JSON without `teachers`. The frontend encounters `undefined`, causing UI failure or rendering `[object Object]` when attempting to format teacher objects from unexpected error responses.
   - *Conclusion*: Add `teachers: Optional[List[TeacherBrief]] = []` to `ModuleResponse` and update `modules.py` to eagerly load and serialize assigned teachers for all module endpoints.

4. **Premise**: R1 and R5 require practical coding exams with secure sandbox execution and anti-cheating 403 suspension guards.
   - *Observation*: Sandbox execution exists in `sandbox_runner.py`, but the only endpoints exposing it are in `training_python.py` (`/api/training/python/run-code` and `/run-tests`). These endpoints have no knowledge of exam sessions, do not check if a student attempt is `suspended`, and fail to find database questions.
   - *Deduction*: During an official practical exam, a suspended student could bypass 403 suspension by executing code through the training router, while any custom practical question authored in the database cannot be tested at all prior to final submission.
   - *Conclusion*: Implement dedicated student attempt execution endpoints under `/api/student/attempts/{attempt_id}/run-code` and `/api/student/attempts/{attempt_id}/questions/{question_id}/run-tests` that verify attempt validity and block suspended attempts with HTTP 403 Forbidden.

5. **Premise**: R4 requires an integrated question authoring experience with question reordering, live points total, and instant validation.
   - *Observation*: `backend/app/routers/exams.py` only provides single-question update (`PUT /api/exams/{id}/questions/{q_id}`) and lacks batch reordering, total points calculation in `ExamResponse`, or readiness validation.
   - *Conclusion*: Add `PUT /api/exams/{exam_id}/questions/reorder`, add `total_points` to `ExamResponse`, and add `GET /api/exams/{exam_id}/validate`.

---

## 3. Caveats & Assumptions

1. **Database Backward Compatibility**: The production database runs locally on SQLite in WAL mode with existing data (`exam_app.db`). All schema adjustments (such as adding `passing_score` to `exams`) must be applied via defensive auto-migration in `_auto_migrate_schema` using `PRAGMA table_info` and `ALTER TABLE ADD COLUMN` to prevent wiping existing tables.
2. **Dual Shuffling Determinism**: Question and option shuffling in `start_or_resume_exam` uses `random.Random(f"{attempt.id}-{current_user.id}")`. This ensures that on page refresh (`F5`), the student receives the exact same question order and option order without desynchronization.
3. **Headless Visualization Execution**: `sandbox_runner.py` uses `MPLBACKEND=Agg` and a figure hook capturing Base64 PNGs. When students write Matplotlib or Seaborn code, `plt.savefig()` is intercepted. For Pandas dataframe operations, plain stdout printing or HTML tables are rendered in stdout.
4. **Pytest Suite Integrity**: Any change to `_build_student_bulletin` must preserve the keys `fundamentals`, `exams`, `general_average`, `is_pass`, and `verdict` so that `tests/test_phase8_revisions.py` passes without regressions. As demonstrated in Section 1.4, decoupling diagnostic tests preserves `etu_dev1` as ADMIS and `etu_dev4` as AJOURNÉ.

---

## 4. Conclusion & Required Architectural Changes

### 4.1 Database Schema Changes

#### Tables and Columns Modification Summary
| Table | Column | Type | Default | Rationale |
|---|---|---|---|---|
| `exams` | `exam_type` | `VARCHAR` | `'theoretical'` | Already present in model/table, needs consistent serialization in API responses |
| `exams` | `passing_score` | `FLOAT` | `10.0` | Required for Step 1 exam configuration in R4 |
| `student_attempts` | `extra_time_minutes` | `INTEGER` | `0` | Explicit tracking of time extensions granted by proctor |

#### Auto-Migration Script Addition in `backend/app/main.py`
```python
def _auto_migrate_schema(engine):
    if engine.url.drivername.startswith("sqlite"):
        import sqlite3
        db_path = engine.url.database
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                # ... existing migrations ...
                
                # Migration pour exams.passing_score
                cur.execute("PRAGMA table_info(exams)")
                ecols = [r[1] for r in cur.fetchall()]
                if ecols:
                    if "exam_type" not in ecols:
                        cur.execute("ALTER TABLE exams ADD COLUMN exam_type VARCHAR DEFAULT 'theoretical'")
                    if "passing_score" not in ecols:
                        cur.execute("ALTER TABLE exams ADD COLUMN passing_score FLOAT DEFAULT 10.0")

                # Migration pour student_attempts.extra_time_minutes
                cur.execute("PRAGMA table_info(student_attempts)")
                acols = [r[1] for r in cur.fetchall()]
                if acols:
                    if "extra_time_minutes" not in acols:
                        cur.execute("ALTER TABLE student_attempts ADD COLUMN extra_time_minutes INTEGER DEFAULT 0")

                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[SCHEMA AUTO-MIGRATE WARNING] {e}")
```

---

### 4.2 Pydantic Schemas Changes (`backend/app/schemas.py`)

#### 1. Teacher and Module Responses
```python
class TeacherBrief(BaseModel):
    id: str
    username: str
    full_name: str
    email: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ModuleResponse(ModuleBase):
    created_at: datetime
    teachers: Optional[List[TeacherBrief]] = []
    model_config = ConfigDict(from_attributes=True)
```

#### 2. Exam and Question Authoring
```python
class ExamBase(BaseModel):
    module_code: str
    title: str = Field(..., min_length=1, max_length=200)
    exam_type: str = Field(default="theoretical", pattern="^(theoretical|practical)$")
    instructions: Optional[str] = None
    duration_minutes: int = Field(default=60, ge=1, le=360)
    global_points: float = Field(default=20.0, ge=1.0)
    passing_score: float = Field(default=10.0, ge=0.0)
    navigation_mode: str = "free"
    shuffle_questions: bool = True
    shuffle_options: bool = True
    partial_credit_enabled: bool = True
    default_negative_penalty: float = 0.5

class ExamResponse(ExamBase):
    id: str
    created_by: Optional[str]
    created_at: datetime
    question_count: Optional[int] = 0
    total_points: Optional[float] = 0.0
    assigned_groups: Optional[List[str]] = []
    model_config = ConfigDict(from_attributes=True)

class QuestionReorderItem(BaseModel):
    id: str
    ordering: int

class QuestionReorderPayload(BaseModel):
    items: List[QuestionReorderItem]
```

---

### 4.3 API Endpoints to Add or Modify

#### Router: `backend/app/routers/exams.py`
1. **Fix `ExamResponse` Serialization**:
   Update `list_exams`, `create_exam`, `update_exam`, `load_exam_template`, `import_exam_template_payload`, and `get_exam_detail` to explicitly pass:
   ```python
   exam_type=getattr(e, "exam_type", "theoretical") or "theoretical",
   passing_score=getattr(e, "passing_score", 10.0) or 10.0,
   total_points=round(sum(q.points for q in e.questions), 2)
   ```
2. **Add Question Reordering Endpoint**:
   - `PUT /api/exams/{exam_id}/questions/reorder`
   - Payload: `QuestionReorderPayload` (`[{"id": "Q-01", "ordering": 1}, ...]`)
   - Updates `ordering` field across all specified questions in a single transaction.
3. **Add Exam Readiness Validation Endpoint**:
   - `GET /api/exams/{exam_id}/validate`
   - Returns: `{ "valid": bool, "errors": List[str], "warnings": List[str], "total_points": float, "global_points": float, "question_count": int }`
   - Validates that:
     - Question count > 0
     - If `exam_type == 'theoretical'`: No coding questions present
     - If `exam_type == 'practical'`: Only coding questions present, each possessing >= 2 public tests and >= 10 hidden tests
     - Sum of question points equals or exceeds `global_points`
4. **Enforce Type Validation on Question Modification**:
   In `update_question`, `create_exam`, and `import_questions_json`, validate that incoming question types strictly comply with the exam's `exam_type`.

#### Router: `backend/app/routers/student_exam.py`
1. **Fix `get_available_exams`**:
   Add `"exam_type": getattr(ex, "exam_type", "theoretical") or "theoretical"` and `"passing_score": getattr(ex, "passing_score", 10.0) or 10.0` to each returned exam dictionary.
2. **Add Practical Exam Execution Endpoints**:
   - `POST /api/student/attempts/{attempt_id}/run-code`:
     - Verifies attempt exists, belongs to student, and is `"in_progress"` (returns 403 Forbidden if `"suspended"`).
     - Runs code with custom stdin via `sandbox_runner.execute_user_code_with_input`.
     - Returns stdout, stderr, and base64 figures.
   - `POST /api/student/attempts/{attempt_id}/questions/{question_id}/run-tests`:
     - Verifies attempt exists, belongs to student, and is `"in_progress"` (returns 403 Forbidden if `"suspended"`).
     - Queries `Question` from database matching `question_id`.
     - Retrieves `public_tests` from `options_json` and `hidden_tests` from `correct_answers_json`.
     - Parameter `run_all: bool` (if `False`, runs public tests only; if `True`, evaluates both public and hidden tests with `mask_hidden_output=True`).
     - Returns results with masked hidden outputs.
3. **Decouple Module Statistics**:
   In `get_student_statistics`, calculate `official_average` solely from `m_official` (official exams). Report diagnostic scores under a separate `diagnostic_placement_average`.

#### Router: `backend/app/routers/admin.py`
1. **Decouple Diagnostic Tests from Official Academic GPA**:
   In `_build_student_bulletin`:
   - Compute `official_semester_average` strictly from `exam_scores` (official exams).
   - Set `is_pass` and `verdict` (`ADMIS` vs `AJOURNÉ`) based strictly on `official_semester_average >= 10.0`.
   - Maintain `fundamentals` and `fundamentals_average` as a decoupled "Positionnement Diagnostique" block.
   - For backward compatibility with existing tests, set `general_average = round(sum(exam_scores) / len(exam_scores), 2)` when official exams are present, while retaining `fundamentals_average` for the diagnostic pillars.

#### Router: `backend/app/routers/modules.py`
1. **Eager Load Teachers in Module Responses**:
   Ensure `list_modules` and `get_module` return `teachers: [TeacherBrief]` using SQLAlchemy's `joinedload(Module.teachers)` or direct relationship access so frontend views never encounter missing teacher arrays.

#### Router: `backend/app/routers/proctor.py`
1. **Add Bulk Unlock Endpoint**:
   - `POST /api/proctor/sessions/{session_id}/unlock-all`
   - Unlocks all attempts with `status == "suspended"` in the session.
   - Resets `suspension_count = 0` and clears `suspension_reason`.
   - Logs `UNLOCKED_ALL_BY_TEACHER` audit event.
   - Broadcasts `ATTEMPT_UNLOCKED` over WebSocket to all affected student terminals and notifies proctor channels.

---

## 5. Verification Method

### 5.1 Automated Pytest Verification
Run the complete automated test suite to ensure zero regressions:
```powershell
pytest -v
```
All 85 tests must pass. In addition, new unit and integration tests should cover:
1. `tests/test_practical_exam_runner.py`:
   - Verification of `POST /api/student/attempts/{id}/run-code` with custom stdin.
   - Verification of `POST /api/student/attempts/{id}/questions/{qid}/run-tests` with public vs hidden test masking.
   - Verification that a suspended attempt receives `HTTP 403 Forbidden` on code execution.
2. `tests/test_exam_creation_and_reorder.py`:
   - Verification of `PUT /api/exams/{id}/questions/reorder`.
   - Verification of `GET /api/exams/{id}/validate`.
   - Verification that `ExamResponse` faithfully serializes `exam_type == "practical"`.
3. `tests/test_bulletin_decoupling.py`:
   - Verification that high diagnostic test scores without passing official exams do NOT grant `ADMIS` verdict.
   - Verification that official semester averages are computed exclusively from `StudentAttempt`.
4. `tests/test_proctor_unlock_all.py`:
   - Verification that `POST /api/proctor/sessions/{session_id}/unlock-all` unlocks multiple suspended attempts simultaneously.

### 5.2 Direct Code Inspection Points
- Verify `backend/app/routers/exams.py` line 54 `ExamResponse(..., exam_type=getattr(e, "exam_type", "theoretical"))`.
- Verify `backend/app/routers/admin.py` line 390 `general_avg` computation excludes `f_scores`.
- Verify `backend/app/schemas.py` `ModuleResponse` includes `teachers: Optional[List[TeacherBrief]] = []`.

### 5.3 Invalidation Conditions
- Any test failure in `pytest tests/`.
- Exposure of hidden test expected outputs or inputs in API responses.
- Inability of a student to resume an exam session after an `F5` browser refresh with preserved countdown and answers.
- Re-introduction of `f_scores` into official GPA calculations.
