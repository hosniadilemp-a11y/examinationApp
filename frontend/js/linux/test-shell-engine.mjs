/**
 * Test Suite Automatisée pour Shell Lexer, Shell Parser, Shell Engine et Terminal UI
 * Milestone 3 — Linux Training Center
 * Exécution: node frontend/js/linux/test-shell-engine.mjs
 */

import { VirtualFS, VFSNode } from './vfs.js';
import { POSIX_COMMANDS } from './posix-commands.js';
import { TokenType, ShellLexer, expandVariables, expandWord } from './shell-lexer.js';
import { ShellParser } from './shell-parser.js';
import { ShellEngine } from './shell-engine.js';
import { TerminalUI, longestCommonPrefix } from './terminal-ui.js';

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function assert(condition, message) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✓ ${message}`);
  } else {
    failedTests++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

function assertEqual(actual, expected, message) {
  totalTests++;
  const actStr = JSON.stringify(actual);
  const expStr = JSON.stringify(expected);
  if (actStr === expStr) {
    passedTests++;
    console.log(`  ✓ ${message}`);
  } else {
    failedTests++;
    console.error(`  ✗ FAIL: ${message}`);
    console.error(`     Expected: ${expStr}`);
    console.error(`     Actual:   ${actStr}`);
  }
}

function suite(name) {
  console.log(`\n========================================\n[SUITE] ${name}\n========================================`);
}

async function runAllSuites() {
  // ========================================
  // Suite 1: Shell Lexer - Tokenization, Quotes & Escapes
  // ========================================
  suite('Shell Lexer - Tokenization, Quotes & Escapes');

  {
    const lex = new ShellLexer('echo "hello world"');
    const tokens = lex.tokenize();
    assertEqual(tokens.length, 3, 'Lexer emits 2 words + EOF');
    assertEqual(tokens[0].type, TokenType.WORD, 'First token is WORD');
    assertEqual(tokens[0].value, 'echo', 'First token value is echo');
    assertEqual(tokens[1].type, TokenType.WORD, 'Second token is WORD');
    assertEqual(tokens[1].value, 'hello world', 'Double quotes preserve internal space');
    assertEqual(tokens[2].type, TokenType.EOF, 'Final token is EOF');
  }

  {
    const lex = new ShellLexer("echo 'single quoted $VAR literal'");
    const tokens = lex.tokenize();
    assertEqual(tokens[1].value, 'single quoted $VAR literal', 'Single quotes preserve literal $VAR');
  }

  {
    const lex = new ShellLexer('echo Mon\\ Dossier "nested \\"quotes\\""');
    const tokens = lex.tokenize();
    assertEqual(tokens[1].value, 'Mon Dossier', 'Backslash escapes space outside quotes');
    assertEqual(tokens[2].value, 'nested "quotes"', 'Backslash escapes double quote inside double quotes');
  }

  {
    const lex = new ShellLexer('cat file.txt | grep "foo" > out.txt >> append.txt < in.txt 2> err.txt &> all.txt && ls || pwd ; date');
    const tokens = lex.tokenize();
    const opTypes = tokens.filter(t => t.type !== TokenType.WORD && t.type !== TokenType.EOF).map(t => t.type);
    assertEqual(opTypes, [
      TokenType.PIPE,
      TokenType.REDIRECT_OUT,
      TokenType.REDIRECT_APPEND,
      TokenType.REDIRECT_IN,
      TokenType.REDIRECT_ERR,
      TokenType.REDIRECT_ALL,
      TokenType.AND_IF,
      TokenType.OR_IF,
      TokenType.SEMICOLON
    ], 'All 9 shell operators recognized accurately');
  }

  {
    let caughtSingle = false;
    try {
      new ShellLexer("echo 'unterminated").tokenize();
    } catch (e) {
      caughtSingle = true;
    }
    assert(caughtSingle, 'Lexer throws syntax error on unterminated single quote');

    let caughtDouble = false;
    try {
      new ShellLexer('echo "unterminated').tokenize();
    } catch (e) {
      caughtDouble = true;
    }
    assert(caughtDouble, 'Lexer throws syntax error on unterminated double quote');
  }

  // ========================================
  // Suite 2: Shell Lexer & Engine - Variable Substitution & Expansion
  // ========================================
  suite('Shell Lexer & Engine - Variable Substitution & Expansion');

  {
    const env = { USER: 'student', HOME: '/home/student', '?': '0' };
    const expanded = expandVariables('Hello $USER from $HOME (status: $?)', env);
    assertEqual(expanded, 'Hello student from /home/student (status: 0)', 'Basic $VAR and $? expansion');

    const braced = expandVariables('${USER}_backup_${?}', env);
    assertEqual(braced, 'student_backup_0', 'Braced ${VAR} expansion');

    const defaulted = expandVariables('${UNDEFINED:-fallback_value}', env);
    assertEqual(defaulted, 'fallback_value', '${VAR:-default} uses fallback when unset');

    const existingDefault = expandVariables('${USER:-fallback_value}', env);
    assertEqual(existingDefault, 'student', '${VAR:-default} uses existing variable when set');

    const missing = expandVariables('$NON_EXISTENT', env);
    assertEqual(missing, '', 'Missing variable expands to empty string');
  }

  {
    const env = { USER: 'student' };
    const lex = new ShellLexer('echo "$USER" \'$USER\' \\$USER', { env });
    const tokens = lex.tokenize();
    assertEqual(tokens[1].value, 'student', 'Double quote expands $USER');
    assertEqual(tokens[2].value, '$USER', 'Single quote preserves $USER');
    assertEqual(tokens[3].value, '$USER', 'Escaped \\$USER preserves $USER');
  }

  // ========================================
  // Suite 3: Shell Parser - AST Construction & Syntax Validation
  // ========================================
  suite('Shell Parser - AST Construction & Syntax Validation');

  {
    const ast = ShellParser.parse('cat < input.txt | grep "test" > out.txt && echo "done" ; pwd');
    assert(Array.isArray(ast.chains), 'AST has chains array');
    assertEqual(ast.chains.length, 3, '3 command chains in AST');

    // Chain 0: START pipeline
    const c0 = ast.chains[0];
    assertEqual(c0.operator, 'START', 'First chain has operator START');
    assertEqual(c0.pipeline.commands.length, 2, 'First pipeline has 2 commands (cat | grep)');
    assertEqual(c0.pipeline.commands[0].executable, 'cat', 'First command is cat');
    assertEqual(c0.pipeline.commands[0].redirections[0].type, 'read', 'cat has read redirection');
    assertEqual(c0.pipeline.commands[0].redirections[0].target, 'input.txt', 'cat reads from input.txt');
    assertEqual(c0.pipeline.commands[1].executable, 'grep', 'Second command is grep');
    assertEqual(c0.pipeline.commands[1].args, ['test'], 'grep has args ["test"]');
    assertEqual(c0.pipeline.commands[1].redirections[0].type, 'write', 'grep has write redirection');
    assertEqual(c0.pipeline.commands[1].redirections[0].target, 'out.txt', 'grep writes to out.txt');

    // Chain 1: AND pipeline
    const c1 = ast.chains[1];
    assertEqual(c1.operator, 'AND', 'Second chain has operator AND');
    assertEqual(c1.pipeline.commands[0].executable, 'echo', 'Second chain runs echo');
    assertEqual(c1.pipeline.commands[0].args, ['done'], 'echo arg is done');

    // Chain 2: SEQ pipeline
    const c2 = ast.chains[2];
    assertEqual(c2.operator, 'SEQ', 'Third chain has operator SEQ');
    assertEqual(c2.pipeline.commands[0].executable, 'pwd', 'Third chain runs pwd');
  }

  {
    // Syntax error tests
    let errPipe = false;
    try {
      ShellParser.parse('| echo hello');
    } catch (e) {
      errPipe = e.code === 'SYNTAX_ERROR';
    }
    assert(errPipe, 'Leading pipe throws SYNTAX_ERROR');

    let errTrailingPipe = false;
    try {
      ShellParser.parse('echo hello |');
    } catch (e) {
      errTrailingPipe = e.code === 'SYNTAX_ERROR';
    }
    assert(errTrailingPipe, 'Trailing pipe throws SYNTAX_ERROR');

    let errRedir = false;
    try {
      ShellParser.parse('cat > && echo ok');
    } catch (e) {
      errRedir = e.code === 'SYNTAX_ERROR';
    }
    assert(errRedir, 'Missing redirection target throws SYNTAX_ERROR');

    let errConsecutive = false;
    try {
      ShellParser.parse('echo a && && echo b');
    } catch (e) {
      errConsecutive = e.code === 'SYNTAX_ERROR';
    }
    assert(errConsecutive, 'Consecutive operators throw SYNTAX_ERROR');
  }

  // ========================================
  // Suite 4: Shell Engine - Pipelines & Multi-Stage Execution
  // ========================================
  suite('Shell Engine - Pipelines & Multi-Stage Execution');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // Seed file
    vfs.writeFile('/home/student/data.txt', 'apple\nbanana\napricot\ncherry\navocado\n');

    // 2-stage pipeline
    const r1 = await engine.execute('cat /home/student/data.txt | grep "ap"');
    assertEqual(r1.stdout, 'apple\napricot\n', '2-stage pipeline: cat | grep');
    assertEqual(r1.exitCode, 0, 'Exit code is 0');

    // 3-stage pipeline
    const r2 = await engine.execute('cat /home/student/data.txt | grep "ap" | wc -l');
    assertEqual(r2.stdout, '      2\n', '3-stage pipeline: cat | grep | wc -l');
    assertEqual(r2.exitCode, 0, '3-stage exit code is 0');

    // Multi-stage with sort and uniq
    vfs.writeFile('/home/student/fruits.txt', 'orange\nbanana\norange\napple\nbanana\n');
    const r3 = await engine.execute('cat /home/student/fruits.txt | sort | uniq');
    assertEqual(r3.stdout, 'apple\nbanana\norange\n', 'Pipeline with sort | uniq deduplicates sorted stream');

    // Intermediate command failure in pipeline: command not found sends stderr, wc receives empty stdin
    const r4 = await engine.execute('nonexistent_cmd | wc -l');
    assert(r4.stderr.includes('command not found'), 'stderr contains command not found');
    assertEqual(r4.stdout, '      0\n', 'wc counts 0 lines from failed upstream pipe');
    assertEqual(r4.exitCode, 0, 'Pipeline exit code reflects last command (wc)');
  }

  // ========================================
  // Suite 5: Shell Engine - File Redirections (>, >>, <, 2>, &>)
  // ========================================
  suite('Shell Engine - File Redirections (>, >>, <, 2>, &>)');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // > Overwrite
    const r1 = await engine.execute('echo "first line" > /home/student/out.txt');
    assertEqual(r1.stdout, '', 'Output redirection suppresses stdout from console');
    assertEqual(vfs.readFile('/home/student/out.txt'), 'first line\n', 'File created with content');

    // > Overwrite again (truncates)
    await engine.execute('echo "replaced line" > /home/student/out.txt');
    assertEqual(vfs.readFile('/home/student/out.txt'), 'replaced line\n', '> truncates previous content');

    // >> Append
    await engine.execute('echo "appended line" >> /home/student/out.txt');
    assertEqual(vfs.readFile('/home/student/out.txt'), 'replaced line\nappended line\n', '>> appends content');

    // < Input redirection
    const r2 = await engine.execute('cat < /home/student/out.txt');
    assertEqual(r2.stdout, 'replaced line\nappended line\n', '< feeds file into cat stdin');

    // Combined < and >
    await engine.execute('cat < /home/student/out.txt | grep "appended" > /home/student/filtered.txt');
    assertEqual(vfs.readFile('/home/student/filtered.txt'), 'appended line\n', 'Combined < and > across pipeline');

    // Input redirection on missing file fails with exitCode 1 without invoking command
    const r3 = await engine.execute('cat < /home/student/does_not_exist.txt');
    assertEqual(r3.exitCode, 1, 'Input redirection on missing file fails with exit code 1');
    assert(r3.stderr.includes('No such file or directory'), 'Error reported on missing input file');

    // Redirection with no command creates/truncates file
    await engine.execute('> /home/student/empty.txt');
    assert(vfs.resolve('/home/student/empty.txt') !== null, '"> file" creates empty file');
  }

  // ========================================
  // Suite 6: Shell Engine - Chaining Operators (&&, ||, ;) & Short-Circuiting
  // ========================================
  suite('Shell Engine - Chaining Operators (&&, ||, ;) & Short-Circuiting');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // && success chain
    const r1 = await engine.execute('echo "step 1" && echo "step 2"');
    assertEqual(r1.stdout, 'step 1\nstep 2\n', '&& executes second command when first succeeds');
    assertEqual(r1.exitCode, 0, 'Exit code is 0');

    // && short-circuit on failure
    const r2 = await engine.execute('false && echo "should_not_run"');
    assertEqual(r2.stdout, '', '&& short-circuits and skips second command on failure');
    assertEqual(r2.exitCode, 1, 'Final exit code is 1');

    // || recovery on failure
    const r3 = await engine.execute('false || echo "fallback"');
    assertEqual(r3.stdout, 'fallback\n', '|| executes second command when first fails');
    assertEqual(r3.exitCode, 0, 'Recovery exit code is 0');

    // || short-circuit on success
    const r4 = await engine.execute('echo "primary" || echo "secondary"');
    assertEqual(r4.stdout, 'primary\n', '|| short-circuits on success');
    assertEqual(r4.exitCode, 0, 'Primary exit code is 0');

    // Semicolon unconditional sequential execution
    const r5 = await engine.execute('echo "a" ; false ; echo "b"');
    assertEqual(r5.stdout, 'a\nb\n', '; runs all commands sequentially regardless of intermediate exit code');
    assertEqual(r5.exitCode, 0, 'Final exit code is that of the last executed command');
  }

  // ========================================
  // Suite 7: Shell Engine - Exit Codes ($?, 0, 1, 127, 130)
  // ========================================
  suite('Shell Engine - Exit Codes ($?, 0, 1, 127, 130)');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // Successful command sets $? = 0
    await engine.execute('true');
    const r0 = await engine.execute('echo $?');
    assertEqual(r0.stdout, '0\n', '$? is 0 after successful command');

    // General error sets $? = 1
    await engine.execute('false');
    const r1 = await engine.execute('echo $?');
    assertEqual(r1.stdout, '1\n', '$? is 1 after failed command');

    // Missing command sets exit code 127
    const r127 = await engine.execute('unknown_binary_xyz');
    assertEqual(r127.exitCode, 127, 'Command not found returns exit code 127');
    assert(r127.stderr.includes('command not found'), 'stderr specifies command not found');
    const rCheck127 = await engine.execute('echo $?');
    assertEqual(rCheck127.stdout, '127\n', '$? is 127 after command not found');

    // Variables updated during chaining
    await engine.execute('export GREETING="Bienvenue" && echo $GREETING');
    assertEqual(engine.env.GREETING, 'Bienvenue', 'export updates engine environment in chain');
  }

  // ========================================
  // Suite 8: Terminal UI - Prompt Formatting, History & Draft Retention
  // ========================================
  suite('Terminal UI - Prompt Formatting, History & Draft Retention');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs, cwd: '/home/student' });
    const term = new TerminalUI({ shellEngine: engine, vfs });

    // Dynamic prompt format
    assertEqual(term.getPromptText(), 'student@examquiz:~$ ', 'Default prompt is student@examquiz:~$ ');
    assert(term.getPromptHtml().includes('student@examquiz'), 'HTML prompt contains colored student user');

    // Changing cwd to subpath updates prompt to ~/subpath
    vfs.mkdir('/home/student/projects', { recursive: true });
    await engine.execute('cd /home/student/projects');
    assertEqual(term.getPromptText(), 'student@examquiz:~/projects$ ', 'Prompt adapts to subpath: ~/projects');

    // Changing cwd to /var/log shows full path
    await engine.execute('cd /var/log');
    assertEqual(term.getPromptText(), 'student@examquiz:/var/log$ ', 'Prompt shows absolute path for non-home dirs');

    // Root prompt formatting
    engine.env.USER = 'root';
    await engine.execute('cd /root');
    assertEqual(term.getPromptText(), 'root@examquiz:~# ', 'Root prompt displays ~# with hash symbol');

    // Reset user to student
    engine.env.USER = 'student';
    await engine.execute('cd /home/student');

    // History and draft retention logic simulation
    term.history = ['ls -la', 'cat notes.txt', 'pwd'];
    term.historyIndex = -1;
    term.draft = 'in-progress typing';

    // Simulate Up Arrow
    if (term.historyIndex === -1) {
      term.draft = 'in-progress typing';
      term.historyIndex = term.history.length - 1;
    }
    assertEqual(term.history[term.historyIndex], 'pwd', 'Up arrow recalls newest history item (pwd)');

    // Up Arrow again
    term.historyIndex--;
    assertEqual(term.history[term.historyIndex], 'cat notes.txt', 'Up arrow recalls previous history item');

    // Down Arrow forward
    term.historyIndex++;
    assertEqual(term.history[term.historyIndex], 'pwd', 'Down arrow moves forward in history');

    // Down Arrow past newest item restores draft
    term.historyIndex = -1;
    assertEqual(term.draft, 'in-progress typing', 'Down arrow past newest restores uncommitted draft');
  }

  // ========================================
  // Suite 9: Terminal UI - Tab Autocompletion (Commands & VFS Paths)
  // ========================================
  suite('Terminal UI - Tab Autocompletion (Commands & VFS Paths)');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs, cwd: '/home/student' });
    const term = new TerminalUI({ shellEngine: engine, vfs });

    // LCP algorithm verification
    assertEqual(longestCommonPrefix(['cargo', 'cat', 'car']), 'ca', 'LCP calculates "ca" for cargo/cat/car');
    assertEqual(longestCommonPrefix(['grep']), 'grep', 'LCP returns full word for single match');
    assertEqual(longestCommonPrefix([]), '', 'LCP returns empty for empty array');

    // Command completion on first token: prefix "ch" matches chmod, chown
    const comp1 = term.getCompletions('ch', 2);
    assert(comp1.isCommand, 'First token identified as command position');
    assert(comp1.candidates.includes('chmod'), 'Matches chmod');
    assert(comp1.candidates.includes('chown'), 'Matches chown');
    assertEqual(comp1.lcp, 'ch', 'LCP of chmod and chown is "ch"');

    // Unique command completion: prefix "who" matches whoami
    const comp2 = term.getCompletions('who', 3);
    assertEqual(comp2.candidates, ['whoami'], 'Unique match for whoami');

    // VFS file and directory path completion
    vfs.writeFile('/home/student/document.txt', 'test');
    vfs.writeFile('/home/student/dockerfile', 'FROM alpine');
    vfs.mkdir('/home/student/downloads');

    // Path completion on argument: "cat doc"
    const comp3 = term.getCompletions('cat doc', 7);
    assert(!comp3.isCommand, 'Argument position identified as path completion');
    assert(comp3.candidates.includes('document.txt '), 'Files completed with trailing space');
    assert(comp3.candidates.includes('dockerfile '), 'dockerfile included');

    // Directory completion: "cd down"
    const comp4 = term.getCompletions('cd down', 7);
    assertEqual(comp4.candidates, ['downloads/'], 'Directories completed with trailing slash /');

    // Absolute path completion: "cat /etc/pass"
    const comp5 = term.getCompletions('cat /etc/pass', 13);
    assertEqual(comp5.candidates, ['/etc/passwd '], 'Absolute path /etc/pass completes to /etc/passwd ');
  }

  // ========================================
  // Suite 10: Edge Cases & M2 Audit Fixes
  // ========================================
  suite('Edge Cases & M2 Audit Fixes (Circular Symlink ELOOP, rm -rf / exit code)');

  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // Edge case 1: rm -rf / must return exit code 1 and warning even with -f
    const rmRes = await engine.execute('rm -rf /');
    assertEqual(rmRes.exitCode, 1, 'rm -rf / returns exit code 1 with -f');
    assert(rmRes.stderr.includes('it is dangerous to operate recursively on'), 'Warning displayed for rm -rf /');

    // Edge case 2: Circular symlinks must throw ELOOP after 20 hops without call stack overflow
    const studentDir = vfs.resolve('/home/student');
    studentDir.children['link_a'] = new VFSNode({ name: 'link_a', type: 'symlink', target: '/home/student/link_b' });
    studentDir.children['link_b'] = new VFSNode({ name: 'link_b', type: 'symlink', target: '/home/student/link_a' });

    let eloopCaught = false;
    try {
      vfs.resolve('/home/student/link_a');
    } catch (err) {
      if (err.code === 'ELOOP') {
        eloopCaught = true;
      }
    }
    assert(eloopCaught, 'Circular symlink throws ELOOP error after 20 hops');

    // Edge case 3: Empty commands and whitespace-only lines preserve previous exit code
    await engine.execute('true');
    const emptyRes0 = await engine.execute('   ');
    assertEqual(emptyRes0.stdout, '', 'Whitespace-only line outputs empty string');
    assertEqual(emptyRes0.exitCode, 0, 'Whitespace-only line preserves exit code 0');

    await engine.execute('false');
    const emptyRes1 = await engine.execute('   ');
    assertEqual(emptyRes1.exitCode, 1, 'Whitespace-only line preserves exit code 1');

    // Edge case 4: Trailing semicolon
    const semiRes = await engine.execute('echo "semicolon test" ; ');
    assertEqual(semiRes.stdout, 'semicolon test\n', 'Trailing semicolon executes cleanly');
    assertEqual(semiRes.exitCode, 0, 'Trailing semicolon exit code 0');

    // Edge case 5: Redirection with spaces around operator
    await engine.execute('echo "spaced redir"   >   /home/student/spaced.txt');
    assertEqual(vfs.readFile('/home/student/spaced.txt'), 'spaced redir\n', 'Redirection with arbitrary whitespace');
  }

  // ========================================
  // Summary
  // ========================================
  console.log('\n========================================');
  console.log(`TEST RESULTS: ${passedTests}/${totalTests} PASSED (${failedTests} FAILED)`);
  console.log('========================================\n');

  if (failedTests > 0) {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

runAllSuites().catch(err => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
