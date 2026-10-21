# Handoff Report — Milestone M1: Backend Core

**Agent**: worker_m1_backend (implementer, qa, specialist)  
**Parent**: orchestrator (`5cc46d99-e8e9-4a94-a230-ffccaf76fc36`)  
**Date**: 2026-10-20T18:50:00Z  
**Type**: Hard Handoff (Task Complete)

---

## 1. Observation

### Codebase Changes
1. **`backend/app/schemas.py`**:
   - Reordered `UserBrief` prior to `ModuleResponse`.
   - Updated `ModuleResponse` to serialize assigned teachers: `teachers: Optional[List[UserBrief]] = []`.
   - Added `passing_score: float = Field(default=10.0, ge=0.0)` to `ExamBase`.
   - Added `exam_type: str = "theoretical"`, `total_question_points: float = 0.0`, and `passing_score: float = 10.0` to `ExamResponse` and `ExamDetailResponse`.
   - Added `QuestionOrderItem` and `QuestionReorderPayload` schemas for batch reordering.

2. **`backend/app/main.py`**:
   - Added auto-migration in `_auto_migrate_schema`:
     ```python
     if "passing_score" not in exam_cols:
         db.execute(text("ALTER TABLE exams ADD COLUMN passing_score FLOAT DEFAULT 10.0"))
     ```

3. **`backend/app/routers/modules.py`**:
   - In `list_modules`, `create_module`, and `get_module`: populated `teachers=[UserBrief(id=t.id, username=t.username, full_name=t.full_name, role=t.role) for t in m.teachers]`.

4. **`backend/app/routers/admin.py`**:
   - In `_build_student_bulletin`: decoupled diagnostic/fundamentals from GPA and semester averages.
   - `general_avg`, `general_gpa`, and pass status (`ADMIS` / `AJOURNÉ`) are computed exclusively from `exam_scores` (`StudentAttempt` from official exams).
   - Segregated fundamental scores into `"diagnostic_scores": {"scores": f_scores, "average": fundamentals_avg, "details": fundamentals}`.

5. **`backend/app/routers/student_exam.py`**:
   - `get_available_exams`: returns `exam_type`, `passing_score`, and `total_question_points` for each exam.
   - Added `POST /api/student/attempts/{attempt_id}/questions/{question_id}/run-tests`:
     - Checks if attempt is suspended (`attempt.status == "suspended"`). If suspended, immediately raises `HTTP 403 Forbidden` (`detail="Tentative actuellement suspendue par le système anti-triche."`).
     - Executes student code against public test cases via `sandbox_runner.execute_code` with a 3-second timeout.
     - Hides/masks hidden test cases, returning only passed/failed counts and public test details.
   - Added `POST /api/student/attempts/{attempt_id}/run-code`:
     - Checks if attempt is suspended (`attempt.status == "suspended"`). If suspended, immediately raises `HTTP 403 Forbidden`.
     - Executes student code with custom `stdin` using `sandbox_runner.execute_code`.
   - In `get_student_statistics`: module averages and best marks are computed strictly over `m_official` attempts, ignoring placement diagnostic tests.

6. **`backend/app/routers/exams.py`**:
   - Updated `list_exams`, `create_exam`, `load_exam_template`, `import_exam_template_payload`, `get_exam_detail`, and `update_exam` to include `exam_type`, `total_question_points`, and `passing_score`.
   - Updated `_create_exam_from_template_dict` to set `exam_type`.
   - Added `GET /api/exams/{exam_id}/validate`:
     - Returns `{valid: bool, exam_id, exam_type, question_count, total_points, global_points, passing_score, errors: [], warnings: []}`.
     - Enforces question type consistency: checks that theoretical exams contain 0 coding questions, and practical exams contain exclusively coding questions.
     - Flags warnings if practical questions have < 2 public tests or < 10 hidden tests.
   - Added `PUT /api/exams/{exam_id}/questions/reorder`:
     - Batch updates `question.ordering` accepting multiple payload formats (`question_orders`, `items`, or direct lists).
   - Question Type Validation Guard:
     - On `create_question`, `update_question`, `create_exam` (for embedded questions), and `import_questions_json`:
     - If `exam_type == "theoretical"` and question type is `coding` or `code`, raises `HTTP 400 Bad Request`.
     - If `exam_type == "practical"` and question type is not in `["coding", "code"]`, raises `HTTP 400 Bad Request`.

7. **`backend/app/routers/proctor.py`**:
   - Added `POST /api/proctor/sessions/{session_id}/unlock-all`:
     - Finds all attempts in the session where `status == "suspended"`.
     - Sets `status = "in_progress"`, resets `suspension_count = 0` and `suspension_reason = None`.
     - Logs audit entry `AUDIT_EVENT_PROCTOR_UNLOCK_ALL`.
     - Broadcasts WebSocket events (`STUDENT_UNLOCKED` to students, `STUDENTS_UNLOCKED_ALL` to proctors).

### Verification Execution Outputs
- **Original Baseline Test Suite (10 files)**:
  ```
  pytest tests/test_phase1.py tests/test_phase2.py tests/test_phase3.py tests/test_phase4.py tests/test_phase5.py tests/test_phase6.py tests/test_phase7.py tests/test_phase8_revisions.py tests/test_phase9_features.py tests/test_sandbox_and_challenges.py
  Result: 85 passed, 1 warning in 178.64s (0:02:58)
  Exit code: 0
  ```

- **E2E Requirements Suite**:
  ```
  pytest tests/test_e2e_requirements.py
  Result: 15 passed, 1 warning in 35.22s
  Exit code: 0
  ```

---

## 2. Logic Chain

1. **Serialization & Type Safety**:
   - Observation: When `ModuleResponse` attempted to reference `UserBrief`, order-of-declaration prevented proper serialization. Moving `UserBrief` above `ModuleResponse` enabled Pydantic validation of `teachers: Optional[List[UserBrief]]`.
   - Observation: `ExamResponse` and `ExamDetailResponse` lacked `exam_type`, `total_question_points`, and `passing_score`. Adding these to `ExamBase`, `ExamResponse`, and `ExamDetailResponse`, along with database auto-migration for `passing_score`, allowed endpoints to return accurate exam metadata.

2. **Validation Integrity (Theoretical vs Practical)**:
   - Observation: Theoretical exams must prohibit coding questions, while practical exams must require coding questions exclusively.
   - Implementation: Added checks to `create_question`, `update_question`, `import_questions_json`, and `create_exam`. If an incompatible question type is submitted, the API rejects it with `400 Bad Request`.
   - Observation: `test_t1_5_theoretical_vs_practical_exam_question_type_rejection_400` verifies that adding a coding question to a theoretical exam returns 400, and adding a non-coding question to a practical exam returns 400. This test passed.

3. **Academic Integrity & GPA Decoupling**:
   - Observation: Diagnostic placement exams (fundamentals) should not distort semester GPA or module grade averages.
   - Implementation: In `_build_student_bulletin`, `general_avg` and verdict (`ADMIS` / `AJOURNÉ`) are computed strictly from official `exam_scores`. Fundamental scores are reported separately under `diagnostic_scores`. In `get_student_statistics`, module averages only aggregate `m_official` attempts.
   - Observation: `test_t1_3_diagnostic_placement_decoupling_from_gpa` verifies that a 0/20 in placement does not lower semester GPA. This test passed.

4. **Anti-Cheat Enforcement & Code Execution**:
   - Observation: When a student attempt is suspended by anti-cheat telemetry, any subsequent attempt to execute code must be rejected immediately with `403 Forbidden`.
   - Implementation: `POST /api/student/attempts/{attempt_id}/questions/{question_id}/run-tests` and `POST /api/student/attempts/{attempt_id}/run-code` query the attempt status; if `status == "suspended"`, execution is blocked with HTTP 403. When active, tests run securely with hidden test masking.
   - Observation: `test_t3_1_practical_exam_anti_cheat_suspension_403_unlock_completion` and `test_api_run_code_and_run_tests_endpoints` passed.

5. **Teacher & Proctor Operations**:
   - Observation: Teachers need to reorder questions and validate exam readiness before session opening.
   - Implementation: Implemented `PUT /api/exams/{exam_id}/questions/reorder` (updating question order in database) and `GET /api/exams/{exam_id}/validate` (checking question count, type consistency, point sums, and test counts).
   - Observation: Proctors require a single action to unlock all suspended students in a room. Implemented `POST /api/proctor/sessions/{session_id}/unlock-all` which unlocks suspended attempts, clears warnings, audits the action, and notifies via WebSocket.
   - Observation: `test_phase8_revisions.py::test_proctor_close_all_session` and `test_t3_1_practical_exam_anti_cheat_suspension_403_unlock_completion` passed.

---

## 3. Caveats

- **No Caveats**: All 6 assigned backend tasks have been implemented strictly within backend file ownership boundaries. No frontend files were modified. All 85 baseline tests and 15 E2E tests pass cleanly.

---

## 4. Conclusion

Milestone M1 (Backend Core) is fully implemented, verified, and complete:
1. `ExamResponse` and `ExamDetailResponse` correctly serialize `exam_type`, `total_question_points`, and `passing_score`.
2. Strict question type validation prevents mixing theoretical and practical question types (returns 400).
3. Diagnostic placement test scores are segregated from GPA, semester averages, and student module statistics.
4. `ModuleResponse.teachers` serializes assigned teachers as `List[UserBrief]`.
5. Student code runner endpoints enforce the anti-cheat 403 guard when suspended, and mask hidden test cases.
6. Teacher question reordering and exam validation endpoints are fully functional.
7. Proctor bulk unlock endpoint (`/sessions/{session_id}/unlock-all`) unlocks all suspended attempts and broadcasts WebSocket updates.
8. Baseline test suite: 85/85 passed (0 regressions). E2E test suite: 15/15 passed.

---

## 5. Verification Method

To independently verify these changes:

1. **Run original baseline test suite**:
   ```powershell
   pytest tests/test_phase1.py tests/test_phase2.py tests/test_phase3.py tests/test_phase4.py tests/test_phase5.py tests/test_phase6.py tests/test_phase7.py tests/test_phase8_revisions.py tests/test_phase9_features.py tests/test_sandbox_and_challenges.py
   ```
   *Expected*: 85 passed in ~170s, 0 failures.

2. **Run E2E requirements test suite**:
   ```powershell
   pytest tests/test_e2e_requirements.py
   ```
   *Expected*: 15 passed in ~35s, 0 failures.

3. **Inspect modified backend files**:
   - `backend/app/schemas.py`
   - `backend/app/main.py`
   - `backend/app/routers/exams.py`
   - `backend/app/routers/admin.py`
   - `backend/app/routers/student_exam.py`
   - `backend/app/routers/modules.py`
   - `backend/app/routers/proctor.py`
