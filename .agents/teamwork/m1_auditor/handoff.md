# Forensic Audit Report — Milestone 1: Backend Models, APIs & Diagnostic Placement Decoupling

**Auditor**: `m1_auditor`  
**Work Product**: Milestone 1 Implementation (`backend/app/data/linux_training/curriculum.json`, `backend/app/data/linux_training/challenges.json`, `backend/app/services/linux_training_service.py`, `backend/app/routers/training_linux.py`, `backend/app/main.py`, `tests/test_linux_training.py`)  
**Profile**: General Project (Development Mode per `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## 1. Observation

1. **Curriculum & Challenge Structure**:
   - `backend/app/data/linux_training/curriculum.json` defines 4 progressive levels (`levels` array: `[1, 2, 3, 4]`) and 6 chapters (`fhs_navigation`, `file_management`, `permissions_security`, `text_processing_pipes`, `processes_signals`, `bash_scripting`) containing 96 MCQ questions and 8 coding exercises.
   - `backend/app/data/linux_training/challenges.json` contains 9 practical challenges (`LINUX-101` through `LINUX-402`).
   - Every challenge in the pool (17 total across `challenges.json` and `curriculum.json`) defines `initial_fs`, `starter_cmd`, `solution`, `public_tests` with at least 2 test cases, and `hidden_tests` with at least 5 test cases. Programmatic verification (`_get_all_challenges_pool()`) confirmed:
     ```
     Total challenges in pool: 17
     Invalid challenges: []
     ```

2. **Evaluation Logic & VFS Verification**:
   - `backend/app/services/linux_training_service.py` (`evaluate_linux_challenge`, lines 308–447) implements multi-criteria evaluation without mock bypasses or static pass returns:
     - `_check_vfs_path_exists` (lines 243–276): Recursively inspects both flat and hierarchical VFS directories (`/home/student`, `/var/log`, `/proc`).
     - `_get_vfs_file_content` (lines 277–307): Genuinely retrieves file content strings from VFS file nodes.
     - `_eval_test_case` (lines 343–402): Evaluates `file_exists`, `file_not_exists`, `file_contains`, `permission`, and `stdout` assertions against student command, exit codes, and VFS state.
   - Empirical test execution with invalid input (`command="echo wrong"`, `execution_output={'stdout': 'wrong'}`) confirmed genuine failure:
     ```
     All passed?: False
     Awarded: 0.0
     Passed count: 0
     ```
   - Empirical test execution with valid input (`command="pwd && ls -la"`) confirmed genuine success:
     ```
     All passed?: True
     Awarded: 2.0
     Passed count: 7 (2 public + 5 hidden)
     ```

3. **Secrecy and Privacy Protections**:
   - Inspection of `get_safe_challenges_list`, `get_challenge_detail_student`, and `get_theory_quizzes` confirmed that `hidden_tests`, `solution`, `correct`, and `explanation` are rigorously stripped before returning responses to students.
   - In `evaluate_linux_challenge` (lines 414–423), hidden test results return:
     ```python
     "name": ht.get("name", f"Test Caché #{idx}"),
     "cmd": "[Protégé]",
     "passed": t_passed,
     "expected": "[Protégé]",
     "actual": "[Protégé]" if t_passed else "Échec"
     ```
   - Automated check confirmed zero leaks:
     ```
     Any hidden_tests in list? False
     Any hidden_tests in detail? False
     Any correct in quizzes? False
     ```

4. **Diagnostic Decoupling & GPA Zero-Tampering**:
   - `sync_student_linux_pillar` in `linux_training_service.py` (lines 449–480) strictly creates `PracticeAttempt` records with `module_code="LINUX_ADMIN"`.
   - Inspection of `backend/app/routers/admin.py` (`_build_student_bulletin`, lines 390–394):
     ```python
     # Découplage strict R2 : La moyenne générale et les verdicts académiques (ADMIS / AJOURNÉ)
     # sont calculés EXCLUSIVEMENT à partir des épreuves officielles du semestre (StudentAttempt).
     official_scores = exam_scores
     general_avg = round(sum(official_scores) / len(official_scores), 2) if official_scores else None
     ```
   - Empirical database check: `sync_student_linux_pillar` does not alter `StudentAttempt` count, enforces foreign key constraints on `users.id`, and preserves academic GPA calculations.
   - `test_linux_training_strict_decoupling_from_semester_gpa` verifies that before and after Linux practice attempts, `general_average`, `exams_average`, and `verdict` remain identical.

5. **Automated Test Suite Execution**:
   - `pytest tests/test_linux_training.py -v`: 16 passed, 0 failed in 29.37s.
   - `pytest tests/`: 119 passed, 0 failed in 194.42s (100% pass rate, 0 regressions across the entire test suite).

---

## 2. Logic Chain

1. **Absence of Prohibited Patterns**:
   - Source code analysis of `linux_training_service.py` and `training_linux.py` revealed no hardcoded test responses, fake mock returns, or bypass flags.
   - Evaluation with an invalid command resulted in 0 awarded points and 0 passing tests.
   - Therefore, the implementation contains no dummy facades or fake returns.

2. **Genuine VFS and Command Evaluation**:
   - Path resolution recursively navigates FHS directory trees and matches file properties.
   - Content and permission checks examine actual VFS nodes.
   - Therefore, the evaluation logic genuinely evaluates filesystem and command behavior.

3. **Confidentiality Assurance**:
   - All student-facing endpoints omit hidden tests, reference solutions, and quiz answers.
   - Test execution payloads mask hidden assertions with `"[Protégé]"`.
   - Therefore, hidden test confidentiality is genuinely enforced.

4. **Academic Decoupling**:
   - `PracticeAttempt` stores `LINUX_ADMIN` performance for diagnostic purposes.
   - Official GPA and verdict logic in `admin.py` and `student_exam.py` strictly relies on `StudentAttempt` for semester exams.
   - Verification of `/api/student/bulletin` before and after practice submissions showed zero drift in `general_average`, `exams_average`, or `verdict`.
   - Therefore, decoupling is authentic and complete.

5. **Test Suite Health**:
   - All 16 Linux-specific tests and all 119 total tests pass with 100% success rate.
   - Therefore, Milestone 1 is verified without regressions.

---

## 3. Caveats

- Milestone 1 encompasses backend models, APIs, datasets, and diagnostic decoupling. Client-side shell execution (virtual terminal DOM and in-browser POSIX command runner) is scheduled for implementation in Milestones 2 and 3.

---

## 4. Conclusion

**Verdict: CLEAN**

Milestone 1 satisfies all functional requirements and forensic integrity standards:
- Cursus datasets in `curriculum.json` and `challenges.json` are genuine and structured across 4 levels.
- Every practical challenge satisfies the requirement of >= 2 public tests and >= 5 hidden tests.
- Backend evaluation logic dynamically inspects VFS structures, stdout, and exit codes.
- Student-facing endpoints and submission responses strictly protect hidden tests and solutions.
- The `LINUX_ADMIN` diagnostic pillar is synchronized without affecting official semester GPAs or transcripts.
- 100% of automated tests pass (119/119).

---

## 5. Verification Method

To independently reproduce the forensic verification:

```powershell
# 1. Run Linux training test suite
pytest tests/test_linux_training.py -v

# 2. Run full test suite across all modules
pytest tests/

# 3. Verify challenge counts and rule (>=2 public, >=5 hidden)
python -c "from backend.app.services.linux_training_service import _get_all_challenges_pool; pool = _get_all_challenges_pool(); print('Pool count:', len(pool)); print('Invalid:', [c['id'] for c in pool if len(c.get('public_tests', [])) < 2 or len(c.get('hidden_tests', [])) < 5])"

# 4. Verify evaluation with bogus input (must return 0 points)
python -c "from backend.app.services.linux_training_service import evaluate_linux_challenge; res = evaluate_linux_challenge('LINUX-101', 'echo wrong', execution_output={'stdout': 'wrong'}); print('Passed:', res['all_passed'], 'Points:', res['awarded_points'])"
```
