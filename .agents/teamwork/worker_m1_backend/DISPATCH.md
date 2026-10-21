## 2026-10-20T17:23:37Z
You are the Backend Core Engineer for Milestone M1 of the Examination & Quiz platform project.
Your working directory is: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\worker_m1_backend
Project root is: c:\Users\adel\Documents\ExaminationQuiz APP
Authoritative user request path: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan path: c:\Users\adel\Documents\ExaminationQuiz APP\PROJECT.md
Backend survey report: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\explorer_survey_backend\handoff.md

You MUST read ORIGINAL_REQUEST.md and PROJECT.md before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File write ownership:
You have exclusive write ownership of:
- backend/app/schemas.py
- backend/app/routers/exams.py
- backend/app/routers/admin.py
- backend/app/routers/student_exam.py
- backend/app/routers/modules.py
- backend/app/routers/proctor.py
- backend/app/main.py
Do NOT touch frontend files.

Your task:
1. Fix Exam Type Serialization & Validation:
   - In `backend/app/schemas.py`: ensure `ExamResponse` and `ExamDetailResponse` include `exam_type: str = "theoretical"`, `total_question_points: float = 0.0`, `passing_score: float = 10.0`.
   - In `backend/app/routers/exams.py`: explicitly pass `exam_type=getattr(e, 'exam_type', 'theoretical')` in all `ExamResponse` and `ExamDetailResponse` instantiations (`list_exams`, `create_exam`, `get_exam_detail`, `update_exam`, `load_exam_template`, `import_exam_template_payload`).
   - In `backend/app/routers/student_exam.py` (`get_available_exams`): include `"exam_type": getattr(exam, 'exam_type', 'theoretical')`.
   - Enforce question type validation in `create_question`, `update_question`, `create_exam` (for embedded questions), and `import_questions_json`: Theoretical exams reject "coding" questions (HTTP 400); Practical exams reject all non-coding question types (HTTP 400).
2. Decouple Diagnostic Placement Tests:
   - In `backend/app/routers/admin.py` (`_build_student_bulletin`): remove `f_scores` (from PracticeAttempt) from `all_scores` calculation. Official module averages, GPAs, and admission verdicts MUST derive strictly from official semester exams (`StudentAttempt`). Provide diagnostic test summary separately under a dedicated `"diagnostic_scores"` key.
   - In `backend/app/routers/student_exam.py` (`get_student_statistics`): calculate official module averages exclusively from `m_official`. Do not pollute official statistics with `m_practice` or `m_training`.
3. Fix Module Multi-Teacher Serialization:
   - In `backend/app/schemas.py`: in `ModuleResponse`, include `teachers: Optional[List[UserBrief]] = []`.
   - In `backend/app/routers/modules.py`: in `list_modules` and `get_module`, populate `teachers` from module's assigned teacher relations.
4. Add Student Attempt Code Runner with Anti-Cheat 403 Guard:
   - In `backend/app/routers/student_exam.py`: add endpoint `POST /api/student/attempts/{attempt_id}/questions/{question_id}/run-tests`. Check attempt status: if `suspended`, raise `HTTPException(status_code=403, detail="Votre épreuve est suspendue. Déblocage surveillant requis.")`. Execute code against public tests using `sandbox_runner.py` and mask hidden test outputs.
5. Add Teacher Workflow APIs:
   - In `backend/app/routers/exams.py`: add batch reorder endpoint `PUT /api/exams/{exam_id}/questions/reorder` accepting list of question IDs and display orders.
   - Add exam validation endpoint `GET /api/exams/{exam_id}/validate` checking question counts, point totals, and exam type consistency.
6. Add Proctor Bulk Unlock:
   - In `backend/app/routers/proctor.py`: add `POST /api/proctor/sessions/{session_id}/unlock-all` to unlock all suspended student attempts in the room session at once, reset warnings, and broadcast WebSocket update.
7. Verification:
   - Run `pytest tests/` to confirm all 85 existing tests continue to pass with 0 regressions.
   - Document your changes and verification output in `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\worker_m1_backend\handoff.md`.
8. Send a message to the orchestrator upon completion.
