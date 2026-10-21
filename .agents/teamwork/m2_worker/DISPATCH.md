# DISPATCH — m2_worker

## Task
Implement Milestone 2: Client-Side Linux Shell & Virtual Filesystem (VFS) Engine.

## Input Documents
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST READ)
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\orchestrator_2\PROJECT.md`
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\survey_explorer_2\report.md` (MUST READ — complete POSIX specifications, edge cases §4, §5, §8, §9)

## Ownership & Scope Boundaries
You own exclusively:
- `frontend/js/linux/vfs.js`
- `frontend/js/linux/posix-commands.js`
- Unit verification script (e.g. Node/browser-compatible test or test runner)

DO NOT modify backend files or other frontend modules.

## Requirements
1. Create `frontend/js/linux/vfs.js` (ES Module):
   - `VFSNode` class: name, type ('file' | 'dir'), mode/permissions (numeric octal e.g. 0o755 and symbolic display helpers), owner ('student'), group ('student'), content (string), mtime (Date), size (number), children (Map or Object for dirs).
   - `VirtualFS` class:
     - Root initialization with complete standard FHS tree (`/bin`, `/etc`, `/home/student`, `/root`, `/tmp`, `/proc`, `/dev`, `/var/log`).
     - Default cwd `/home/student`, `$OLDPWD`.
     - Normalization & path resolution: `.`, `..`, `~` (maps to `/home/student`), `-` (maps to `$OLDPWD`), absolute & relative paths.
     - Methods: `resolve()`, `readFile()`, `writeFile()`, `mkdir()` (with `-p`), `remove()` (with `-r`, `-f`), `copy()` (`-r`), `move()`, `chmod()` (octal `755` & symbolic `+x`, `u+x`, etc.), `chown()`, `readdir()`, `stat()`.
     - State snapshotting: `snapshot()` (deep JSON clone) and `restore(snapshot)` for instant challenge isolation and resets.
     - `loadInitialFS(fsDict)`: populates VFS from challenge definitions.

2. Create `frontend/js/linux/posix-commands.js` (ES Module):
   - Exports command registry dictionary `POSIX_COMMANDS` where each command has signature:
     `(args: string[], stdin: string, context: ShellContext) => Promise<CommandResult> | CommandResult`
     with `CommandResult = { stdout: string, stderr: string, exitCode: number }`.
   - Core 23 commands:
     - `pwd`, `cd`, `ls` (-l, -a, -la, -lh, -1, -d), `cat` (-n, -b, -s), `touch`, `mkdir` (-p), `rm` (-r, -f), `cp` (-r), `mv`, `echo` (-n, -e), `head` (-n), `tail` (-n), `wc` (-l, -w, -c), `chmod` (octal & symbolic), `chown`, `whoami`, `uname` (-a, -r), `date`, `uptime`, `env`, `export`, `ps`, `top`, `kill`.
   - Text processing utilities:
     - `grep`: `-i`, `-v`, `-n`, `-c`, `-l`, regex patterns, reading files or stdin.
     - `find`: `-name <pattern>`, `-iname`, `-type f|d`, `-maxdepth <N>`.
     - `sort`: `-r`, `-n`, `-u`.
     - `uniq`: `-c`, `-d`, `-u`, `-i` (adjacent lines).

3. Verify and test all commands and VFS methods thoroughly.
4. Produce `handoff.md` and report back via `send_message`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-10-20T21:03:02Z
You are m2_worker.
Working directory: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\m2_worker
Read:
1. c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\m2_worker\DISPATCH.md
3. c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\survey_explorer_2\report.md (Authoritative POSIX and VFS specification)
4. c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\orchestrator_2\PROJECT.md

Implement Milestone 2:
- frontend/js/linux/vfs.js (VirtualFS, VFSNode, FHS hierarchy, permissions, snapshot/restore)
- frontend/js/linux/posix-commands.js (23 POSIX commands + grep, find, sort, uniq with exact POSIX flags and outputs)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Test and verify your implementation, write handoff.md, and send_message when done.
