# Project: Centre d'Entraînement Linux (Linux Training Center)

## Architecture
The Linux Training Center is built on a clean client-server architecture:
- **Client-Side Engine (`frontend/js/linux/`)**:
  - Pure in-browser Virtual File System (VFS) simulating POSIX inodes, permissions, FHS directory tree, and instant snapshotting/restoration.
  - Full lexical and syntactic shell engine supporting quotes, variable substitution, multi-stage pipelines (`|`), file redirections (`>`, `>>`, `<`), exit codes (`$?`), and command chaining (`&&`, `||`, `;`).
  - Interactive Terminal UI featuring dynamic prompt (`student@examquiz:~$ `), history navigation, tab autocompletion, signal handling (`Ctrl+C`), and clear screen (`Ctrl+L`).
  - Built-in POSIX utilities (23 commands: `pwd`, `cd`, `ls`, `cat`, `touch`, `mkdir`, `rm`, `cp`, `mv`, `echo`, `head`, `tail`, `wc`, `chmod`, `chown`, `whoami`, `ps`, `top`, `kill`, `uptime`, `uname`, `env`, `export`, `date`, `grep`, `find`, `sort`, `uniq`).
  - Challenge Evaluator verifying both stdout and filesystem side-effects against public and confidential hidden tests.
  - Dual-Track Student UI (`#view-linux`): Volet Théorique (QCM & concepts) and Volet Pratique (2-pane problem & terminal layout) with completion return button (`Retourner au Centre d'Entraînement Linux ➔`).
- **Backend Infrastructure (`backend/app/`)**:
  - FastAPI routers (`/api/training/linux`) serving curriculum, challenge metadata, and practice submission endpoints.
  - Structured JSON datasets in `backend/app/data/linux_training/` (4 progressive levels, >= 2 public tests, >= 5 hidden tests per challenge).
  - Diagnostic pillar synchronization (`LINUX_ADMIN`) in `practice_attempts` with strict mathematical decoupling from semester exam GPAs.
- **Automated Test Suite (`tests/`)**:
  - Comprehensive pytest suite in `tests/test_linux_training.py` validating curriculum, security masking, API endpoints, evaluation logic, and non-regression of existing 103 tests.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | VFS Inode Data Model | Pure client-side virtual filesystem with directories, files, inodes, permissions, timestamps, and deep cloning | M2 | R2 |
| 2 | FHS Directory Tree | Standard hierarchy (`/bin`, `/etc`, `/home/student`, `/root`, `/tmp`, `/proc`, `/dev`) pre-populated | M2 | R2 |
| 3 | Path Normalization | Resolves relative/absolute paths, `.`, `..`, `~` (home), trailing slashes | M2 | R2 |
| 4 | POSIX File Permissions | Octal (755, 644) and symbolic permissions (+x) tracked and displayed in `ls -l` | M2 | R2 |
| 5 | VFS Snapshots & Restore | Deterministic environment setup and rollback for challenges | M2 | R2 |
| 6 | Core Navigation (`pwd`, `cd`) | Working directory tracking, `$HOME`, `$OLDPWD`, navigation error handling | M2 | R2 |
| 7 | Listing (`ls`) | Support for `-l`, `-a`, `-la`, `-lh`, `-1`, `-d` with realistic Linux formatting | M2 | R2 |
| 8 | File Content (`cat`, `head`, `tail`) | Viewing file contents, `-n` line numbering, `-n N` lines limit | M2 | R2 |
| 9 | File Modification (`touch`, `mkdir`, `rm`) | Creating files, `mkdir -p` recursive directory creation, `rm -r` recursive removal | M2 | R2 |
| 10 | File Operations (`cp`, `mv`) | Copying and moving files/directories with overwrite and rename | M2 | R2 |
| 11 | Output & Counting (`echo`, `wc`) | Text printing, `wc` lines/words/bytes count (-l, -w, -c) | M2 | R2 |
| 12 | Ownership & Mode (`chmod`, `chown`) | Octal & symbolic permissions modification, ownership simulation | M2 | R2 |
| 13 | Identity & Host (`whoami`, `uname`) | Returns `student`, simulated Linux kernel info (`uname -a`, `-r`) | M2 | R2 |
| 14 | Process & System (`ps`, `top`, `kill`, `uptime`, `date`) | Process snapshot, PID termination, system uptime counter, current date | M2 | R2 |
| 15 | Environment (`env`, `export`) | Viewing and exporting shell environment variables | M2 | R2 |
| 16 | Text Search (`grep`) | Pattern matching with `-i` (case-insensitive), `-v` (invert), `-n` (line numbers), regex | M2 | R2 |
| 17 | File Search (`find`) | Searching VFS by `-name`, `-type` (f/d), `-maxdepth` | M2 | R2 |
| 18 | Text Sorting & Deduplication (`sort`, `uniq`) | Sorting lines (-r, -n) and adjacent line deduplication (-c, -d, -u) | M2 | R2 |
| 19 | Shell Lexer | Tokenizes command lines preserving single quotes `'..'`, double quotes `".."`, backslash escapes, variable expansion | M3 | R2 |
| 20 | Shell Parser & AST | Parses pipelines, redirections, chaining into execution tree | M3 | R2 |
| 21 | Stdout Piping (`\|`) | Connecting stdout of one command to stdin of next (`cmd1 \| cmd2`) | M3 | R2 |
| 22 | File Redirection (`>`, `>>`, `<`) | Overwrite (`>`), append (`>>`), input from file (`<`) | M3 | R2 |
| 23 | Exit Codes & `$?` | Command exit code tracking (0 success, 1 general, 127 not found, 130 SIGINT) | M3 | R2 |
| 24 | Command Chaining (`&&`, `\|\|`, `;`) | Conditional sequential execution based on exit codes | M3 | R2 |
| 25 | Interactive CLI Prompt | Prompt formatting (`student@examquiz:~$ `) adapting to current path | M3 | R2 |
| 26 | Command History Buffer | Up/Down arrow navigation with uncommitted input draft preservation | M3 | R2 |
| 27 | Tab Autocompletion | Context-aware completion of command names and file/dir paths | M3 | R2 |
| 28 | Terminal Clear & Signals | `clear` command and `Ctrl+L`, `Ctrl+C` cancellation | M3 | R2 |
| 29 | Challenge Evaluator Harness | Executes student command on isolated snapshot, verifies stdout AND filesystem side-effects | M4 | R3 |
| 30 | Public & Hidden Test Masking | Strict confidentiality: hidden test assertions never leaked to client DOM/console | M4 | R3 |
| 31 | Dual-Track Navigation UI | Dedicated `#view-linux` with tabs for Volet Théorique and Volet Pratique | M4 | R1 |
| 32 | Ergonomic 2-Pane Practice Layout | Instructions on left, terminal + test execution tabs on right | M4 | R1 |
| 33 | Completion Return Button | "Retourner au Centre d'Entraînement Linux ➔" navigating to `#view-linux` hub | M4 | R1 |
| 34 | Student Nav Bar Integration | Dedicated "Centre Linux" button in student header alongside Python and Exams | M4 | R1 |
| 35 | Progressive Curriculum Dataset | 4 levels stored in `backend/app/data/linux_training/curriculum.json` and `challenges.json` | M1 | R3 |
| 36 | Public & Hidden Tests Rule | Every challenge has >= 2 public tests and >= 5 hidden tests | M1 | R3 |
| 37 | Linux Training Service | Curriculum loading, student-safe projection, submission grading | M1 | R1, R3 |
| 38 | Training Linux API Router | Endpoints `/api/training/linux/*` for curriculum, challenges, and submissions | M1 | R1, R3 |
| 39 | Diagnostic Pillar Linkage | Practice attempts recorded for `LINUX_ADMIN` pillar in `practice_attempts` | M1 | R4 |
| 40 | Strict GPA Decoupling | Guaranteed isolation of practice scores from semester exams and graduation status | M1 | R4 |
| 41 | Linux Automated Test Suite | `tests/test_linux_training.py` with 11+ automated test suites | M5 | R5 |
| 42 | Full Test Pass Rate (100%) | All 103 existing pytest tests + new linux tests pass with 0 regressions | M5 | R5 |
| 43 | Documentation & Audit Record | Comprehensive documentation in `docs/AUDIT_AND_RESOLUTIONS.md` | M5 | R5 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Models, APIs & Diagnostic Decoupling | Data files (`curriculum.json`, `challenges.json`), service `linux_training_service.py`, router `training_linux.py`, main.py registration, diagnostic pillar linkage | none | DONE |
| M2 | Client-Side VFS & POSIX Engine | In-browser VFS hierarchy, path resolution, permissions, snapshot/restore, 23 POSIX commands, text filters (`grep`, `find`, `sort`, `uniq`) | none | DONE |
| M3 | Shell Parser & Virtual Terminal UI | Lexer, AST parser, pipelines (`\|`), redirection (`>`, `>>`, `<`), exit codes (`$?`), chaining (`&&`, `;`), terminal DOM prompt, history, Tab completion, signals | M2 | DONE |
| M4 | Challenge Evaluator, Dual-Track UI & Navigation | Challenge evaluation harness (stdout + VFS assertions, hidden test masking), 2-pane practical UI, Volet Théorique, navigation bar integration, return button | M1, M2, M3 | DONE |
| M5 | E2E Integration, Full Test Pass & Documentation | Comprehensive pytest tests in `tests/test_linux_training.py`, verify 100% pass on all 103+ tests, document in `docs/AUDIT_AND_RESOLUTIONS.md` | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### Backend ↔ Frontend API (`/api/training/linux`)
- `GET /api/training/linux/curriculum` -> `{ levels: [{ id: 1, title: "...", description: "...", challenges_count: 5, quizzes_count: 5 }] }`
- `GET /api/training/linux/challenges?level=1` -> `[{ id: "LINUX-101", level: 1, title: "...", points: 2.0, status: "unsolved"|"in_progress"|"solved" }]` (Strictly excludes `hidden_tests` and `solution`)
- `GET /api/training/linux/challenges/{id}` -> `{ id: "LINUX-101", title: "...", description: "...", initial_fs: {...}, starter_cmd: "...", public_tests: [{ name: "...", assertion_type: "...", expected: "..." }], points: 2.0 }` (Never leaks `hidden_tests`)
- `POST /api/training/linux/submit-challenge` -> Request: `{ challenge_id: "...", command: "...", vfs_state: {...} }` -> Response: `{ success: true, all_passed: true, awarded_points: 2.0, public_results: [...], hidden_results: [{ name: "Test Caché #1", passed: true, expected: "[Protégé]" }], message: "..." }`
- `GET /api/training/linux/progress` -> `{ solved_challenges: [...], current_level: 2, total_points: 15.0, diagnostic_level: 5 }`

### Client VFS ↔ POSIX Commands (`frontend/js/linux/`)
- `VirtualFS.resolve(path, cwd) -> VFSNode | null`
- `VirtualFS.readFile(path, cwd) -> string`
- `VirtualFS.writeFile(path, content, cwd, options) -> void`
- `VirtualFS.mkdir(path, recursive, cwd) -> void`
- `VirtualFS.remove(path, recursive, cwd) -> void`
- `VirtualFS.chmod(path, mode, cwd) -> void`
- `VirtualFS.snapshot() -> object`
- `VirtualFS.restore(snapshot) -> void`

### Shell Engine ↔ Terminal UI
- `ShellEngine.execute(commandLine, context) -> Promise<{ stdout, stderr, exitCode }>`
- `TerminalUI.write(text, type)` (type: `'output' | 'error' | 'system'`)
- `TerminalUI.clear()`
- `TerminalUI.prompt()`

---

## Code Layout
```
backend/
├── app/
│   ├── data/
│   │   └── linux_training/
│   │       ├── curriculum.json           # 4 progressive training levels
│   │       └── challenges.json           # Practical challenges (>=2 public, >=5 hidden)
│   ├── routers/
│   │   └── training_linux.py             # REST endpoints for Linux Training
│   ├── services/
│   │   └── linux_training_service.py     # Cursus logic, safe projection, evaluation
│   └── main.py                           # Router registration & auto-migration
frontend/
├── index.html                            # Nav button, #view-linux markup, completion button
├── js/
│   ├── app.js                            # Navigation routing to #view-linux
│   └── linux/
│       ├── vfs.js                        # VirtualFS, VFSNode, path resolution, permissions
│       ├── posix-commands.js             # 23 built-in commands & text filtering
│       ├── shell-lexer.js                # Shell tokenizer (quotes, variables, escapes)
│       ├── shell-parser.js               # AST parser (pipelines, redirection, chaining)
│       ├── shell-engine.js               # Command execution and stream piping
│       ├── terminal-ui.js                # Interactive CLI terminal DOM controller
│       ├── linux-evaluator.js            # Automated challenge evaluation harness
│       └── linux-runner.js               # Dual-track coordinator (Théorique & Pratique)
tests/
└── test_linux_training.py                # Pytest verification suite (11+ tests)
docs/
└── AUDIT_AND_RESOLUTIONS.md              # Architectural documentation and audit log
```
