# E2E Test Infra: Centre d'Entraînement Linux

## Test Philosophy
- Opaque-box, requirement-driven testing. Verification of API contracts, student confidentiality, POSIX command correctness, stream piping, and filesystem side-effects.
- Zero tolerance for regressions: 100% pass on all existing 103 pytest tests + 100% pass on new Linux test suite.
- Methodology: Category-Partition + Boundary Value Analysis + Combinatorial Shell Pipelines + Academic Decoupling Verification.

## Feature Inventory
| # | Feature | Source | Tier 1 (Coverage) | Tier 2 (Boundaries) | Tier 3 (Interactions) |
|---|---------|--------|:-----------------:|:-------------------:|:---------------------:|
| 1 | Cursus Serialization & Schema | R3 | 5 | 5 | ✓ |
| 2 | Challenge Public & Hidden Tests Rule | R3 | 5 | 5 | ✓ |
| 3 | Student View Confidentiality (Masking) | R3 | 5 | 5 | ✓ |
| 4 | Challenge Retrieval & Initial VFS | R3 | 5 | 5 | ✓ |
| 5 | Challenge Submission & Evaluation | R3 | 5 | 5 | ✓ |
| 6 | Hidden Tests Masking in Submissions | R3 | 5 | 5 | ✓ |
| 7 | Student Progress & History Tracking | R4 | 5 | 5 | ✓ |
| 8 | Diagnostic Pillar Linkage (`LINUX_ADMIN`) | R4 | 5 | 5 | ✓ |
| 9 | Strict GPA Decoupling Verification | R4 | 5 | 5 | ✓ |
| 10 | RBAC & Security Enforcements | R1, R4 | 5 | 5 | ✓ |
| 11 | Non-Regression Across Platform | R5 | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest tests/test_linux_training.py -v`
- Full suite runner: `pytest tests/` (103 existing + new linux tests = 114+ tests passing)
- Fixture environment: Isolated in-memory SQLite database (`conftest.py`), mocked RBAC tokens (`student_headers`, `teacher_headers`, `admin_headers`).
- Test output format: standard JUnit/pytest console output with zero failures or unexpected errors.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Complete Level 1 Student Practice Flow | Curriculum retrieval, initial VFS load, file creation commands, public & hidden tests pass | Medium |
| 2 | Sysadmin Permissions Hardening Flow | `chmod 755`, `chown`, `ls -l` permissions validation, side-effect verification | Medium |
| 3 | Log Analysis Pipeline Flow | `cat log.txt \| grep "ERROR" \| wc -l`, output assertion | High |
| 4 | Diagnostic Placement Decoupling Verification | Submission of multiple Linux challenges followed by official bulletin generation, proving zero GPA drift | Critical |
| 5 | Unauthorized Student Access & Data Leak Prevention | Attempt to query `hidden_tests` directly via API, ensuring 100% redaction | Critical |

## Coverage Thresholds
- Tier 1: >= 5 test cases per core feature area.
- Tier 2: Boundary conditions (empty inputs, missing files, permission denied, invalid modes).
- Tier 3: Cross-feature combinations (piping into filtering into counting, file creation followed by chmod).
- Tier 4: >= 5 realistic student workflow scenarios.
