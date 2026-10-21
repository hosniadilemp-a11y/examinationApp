# DISPATCH — m3_worker

## Task
Implement Milestone 3: Shell Parser, Shell Engine & Virtual Terminal UI.

## Input Documents
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST READ)
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\orchestrator_2\PROJECT.md`
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\survey_explorer_2\report.md` (MUST READ — Shell syntax, Lexer, Parser, AST, Terminal UI specifications §3, §6, §8, §9)
- `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\m2_worker\handoff.md` and `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\m2_auditor\handoff.md` (M2 VFS and POSIX commands reference, plus 3 edge-case fixes)

## Ownership & Scope Boundaries
You own exclusively:
- `frontend/js/linux/shell-lexer.js`
- `frontend/js/linux/shell-parser.js`
- `frontend/js/linux/shell-engine.js`
- `frontend/js/linux/terminal-ui.js`
- Minor edge-case refinements in `frontend/js/linux/vfs.js` and `frontend/js/linux/posix-commands.js` (symlink hop counter recursion in `resolve`, `rm -rf /` exit code)
- Unit test verification scripts (e.g. `frontend/js/linux/test-shell-engine.mjs`)

DO NOT modify backend files or other frontend modules.

## Requirements
1. `frontend/js/linux/shell-lexer.js`:
   - Tokenizer supporting single quotes `'...'` (raw literal), double quotes `"..."` (variable expansion, escaped quotes/backslashes), backslash escapes (`\ `).
   - Operators: `|`, `>`, `>>`, `<`, `&&`, `||`, `;`.
   - Emits structured token stream.

2. `frontend/js/linux/shell-parser.js`:
   - AST parser building CommandNode, PipelineNode, ChainNode (`&&`, `||`, `;`).
   - Extracts input redirection (`<`) and output redirections (`>`, `>>`).
   - Robust syntax error handling (e.g. unmatched quotes, empty pipe).

3. `frontend/js/linux/shell-engine.js`:
   - Integrates with `VirtualFS` and `POSIX_COMMANDS`.
   - Manages environment variables ($USER, $HOME, $PWD, $OLDPWD, $?, $PATH, $SHELL, exported variables).
   - Executes multi-stage pipelines: `cmd1 | cmd2 | cmd3` (pipes stdout of cmd1 to stdin of cmd2, etc.).
   - Executes file redirections: `>`, `>>`, `<` (writing to / reading from VFS files).
   - Executes conditional chaining: `&&`, `||`, `;` with accurate exit codes ($?).
   - Variable substitution: `$VAR`, `${VAR}`, `$?`.
   - Returns `{ stdout, stderr, exitCode }`.

4. `frontend/js/linux/terminal-ui.js`:
   - Terminal DOM controller for in-browser CLI.
   - Dynamic prompt: `student@examquiz:~$ ` (adapts to cwd: `~` for `/home/student`, full path otherwise).
   - History navigation (Up/Down) with uncommitted draft line preservation.
   - Tab autocompletion:
     - Commands on first token (from POSIX_COMMANDS and PATH).
     - Files and directories on arguments (with trailing `/` for dirs, trailing space for files).
   - Clear screen: `clear` command and `Ctrl+L`.
   - Signals: `Ctrl+C` cancels current input, prints `^C`, sets `$? = 130`, prints new prompt.
   - Line editing shortcuts: `Ctrl+U`, `Ctrl+K`, `Ctrl+A`, `Ctrl+E`, `Ctrl+W`.

5. Edge-case fixes from M2 audit:
   - `vfs.js`: Pass `symlinkHops` in recursive `resolve` calls to prevent call stack overflow on circular symlinks.
   - `posix-commands.js`: Ensure `rm -r /` safety lock returns exit code 1 even with `-f`.

6. Write comprehensive unit test suite (e.g. `frontend/js/linux/test-shell-engine.mjs`) verifying:
   - Lexer quote preservation and escape handling
   - Pipeline piping (`cat | grep | wc`)
   - Redirection (`echo > file`, `echo >> file`, `cat < file`)
   - Chaining (`&&`, `||`, `;`)
   - Exit codes (`$?`)
   - Tab autocompletion logic and history navigation
   Run both node tests and `pytest tests/` (all 119 tests must remain 100% passing).

7. Produce `handoff.md` and report back.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
