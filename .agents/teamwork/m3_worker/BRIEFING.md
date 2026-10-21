# BRIEFING — 2026-10-20T21:40:00Z

## Mission
Implement Milestone 3: Shell Lexer, Shell Parser, Shell Engine, and Virtual Terminal UI for the Linux Training Center, plus M2 edge-case fixes and comprehensive unit tests.

## 🔒 My Identity
- Archetype: implementer, qa, specialist
- Roles: implementer, qa, specialist
- Working directory: c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\m3_worker
- Original parent: 6ba9e6b9-e9de-4958-abd5-dd2ad5895a59
- Milestone: M3 (Shell Parser, Shell Engine & Virtual Terminal UI)

## 🔒 Key Constraints
- Pure client-side JavaScript (ES modules or standard browser/node compatible modules).
- No external heavy dependencies; genuine parser, lexer, AST, pipeline executor, and terminal controller.
- NO CHEATING: Genuine logic, no hardcoded test outputs, no facades.
- All 119 existing pytest tests must remain 100% passing.
- Fix the 2 edge cases in vfs.js (symlinkHops recursion) and posix-commands.js (rm -r / with -f exit code).
- Write thorough unit tests in frontend/js/linux/test-shell-engine.mjs.

## Current Parent
- Conversation ID: 6ba9e6b9-e9de-4958-abd5-dd2ad5895a59
- Updated: not yet

## Task Summary
- **What to build**:
  1. `frontend/js/linux/shell-lexer.js`: Tokenizer supporting single/double quotes, backslash escapes, variable expansion, operators (`|`, `>`, `>>`, `<`, `&&`, `||`, `;`).
  2. `frontend/js/linux/shell-parser.js`: AST parser building CommandNode, PipelineNode, ChainNode (`&&`, `||`, `;`), handling input/output redirections (`<`, `>`, `>>`, `2>`).
  3. `frontend/js/linux/shell-engine.js`: Execution engine orchestrating pipes, redirections, environment variables, exit codes (`$?`), conditional execution (`&&`, `||`, `;`), built-in integration.
  4. `frontend/js/linux/terminal-ui.js`: Interactive DOM terminal controller with dynamic prompt (`student@examquiz:~$ `), command history with draft retention, tab completion, clear screen, Ctrl+C interrupt.
  5. Fix edge cases in `vfs.js` and `posix-commands.js`.
  6. Comprehensive test suite `frontend/js/linux/test-shell-engine.mjs`.
- **Success criteria**:
  - All unit tests pass genuine assertions (104/104 passed).
  - Pytest non-regression passes 100% (119/119).
  - Clean modular code matching architectural guidelines.
- **Interface contracts**: PROJECT.md and survey report §3, §6, §8, §9.
- **Code layout**: `frontend/js/linux/`

## Key Decisions Made
- Implemented dual-part token model (`raw` vs `expandable`) in `shell-lexer.js` allowing strict literal preservation inside single quotes and backslash escapes, while cleanly expanding variables in double quotes and unquoted words.
- Handled all 9 POSIX operators including multi-char operators `&&`, `||`, `>>`, `2>`, `&>`.
- Implemented true sequential stream piping in `shell-engine.js` connecting stdout of command N to stdin of command N+1, with pipeline exit code taken from the final command.
- Integrated file redirections (`<`, `>`, `>>`, `2>`, `&>`) directly with VFS inodes.
- Built interactive `TerminalUI` with dynamic prompt (`student@examquiz:~$ `), history navigation with draft retention, contextual Tab completion (commands on first token, VFS paths on arguments with directory `/` trailing and longest common prefix calculation), and keyboard shortcuts.
- Applied 2 edge-case fixes: `vfs.js` recursive symlink hop propagation (ELOOP limit 20), and `posix-commands.js` rm safety lock returning exitCode 1 on `/` even with `-f`.

## Artifact Index
- `frontend/js/linux/vfs.js` — VirtualFS (with symlinkHops fix)
- `frontend/js/linux/posix-commands.js` — POSIX commands (with rm -rf / fix)
- `frontend/js/linux/shell-lexer.js` — Lexical tokenizer
- `frontend/js/linux/shell-parser.js` — AST syntax parser
- `frontend/js/linux/shell-engine.js` — Execution engine
- `frontend/js/linux/terminal-ui.js` — Terminal DOM UI controller
- `frontend/js/linux/test-shell-engine.mjs` — Comprehensive unit test suite (104 tests)
- `handoff.md` — Final hard handoff report

## Change Tracker
- **Files modified**:
  - `frontend/js/linux/vfs.js`: pass `symlinkHops` in recursive `resolve`
  - `frontend/js/linux/posix-commands.js`: prevent `-f` from suppressing dangerous `/` deletion error
  - `frontend/js/linux/shell-lexer.js`: new lexer implementation
  - `frontend/js/linux/shell-parser.js`: new AST parser implementation
  - `frontend/js/linux/shell-engine.js`: new execution engine implementation
  - `frontend/js/linux/terminal-ui.js`: new terminal DOM controller implementation
  - `frontend/js/linux/test-shell-engine.mjs`: new automated test suite
- **Build status**: Node suites pass (162/162 VFS, 104/104 Shell Engine). Pytest running.
- **Pending issues**: None

## Quality Status
- **Build/test result**: 104/104 M3 tests passed, 162/162 M2 tests passed.
- **Lint status**: Clean
- **Tests added/modified**: 104 new automated tests in `test-shell-engine.mjs`

## Loaded Skills
None
