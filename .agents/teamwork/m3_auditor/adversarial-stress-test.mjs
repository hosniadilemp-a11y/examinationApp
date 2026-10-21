/**
 * Adversarial Forensic Stress-Test Suite for Milestone 3
 * Run independently by m3_auditor
 */

import { VirtualFS, VFSNode } from '../../../frontend/js/linux/vfs.js';
import { POSIX_COMMANDS } from '../../../frontend/js/linux/posix-commands.js';
import { ShellLexer, TokenType, expandVariables, expandWord } from '../../../frontend/js/linux/shell-lexer.js';
import { ShellParser } from '../../../frontend/js/linux/shell-parser.js';
import { ShellEngine } from '../../../frontend/js/linux/shell-engine.js';
import { TerminalUI, longestCommonPrefix } from '../../../frontend/js/linux/terminal-ui.js';

let passed = 0;
let failed = 0;

function check(desc, cond) {
  if (cond) {
    passed++;
    console.log(`  [PASS] ${desc}`);
  } else {
    failed++;
    console.error(`  [FAIL] ${desc}`);
  }
}

async function runAdversarialAudit() {
  console.log("=== 1. DYNAMIC DATA PIPELINE STREAM PIPING ===");
  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });
    
    // Generate dynamic random lines that could not be pre-programmed
    const randomItems = Array.from({ length: 50 }, (_, i) => `item_${(i * 37) % 100}_val`);
    const fileContent = randomItems.join('\n') + '\n';
    vfs.writeFile('/home/student/dynamic.txt', fileContent);

    // Filter items ending with 0_val or 7_val, sort, take head, count lines
    const cmd = 'cat /home/student/dynamic.txt | grep "_val" | grep "7_val" | sort | wc -l';
    const res = await engine.execute(cmd);
    
    // Calculate expected purely in JS
    const expectedCount = randomItems.filter(x => x.includes('_val') && x.includes('7_val')).length;
    const actualCount = parseInt(res.stdout.trim(), 10);
    check(`Dynamic multi-stage pipeline computes exact count (${actualCount} === ${expectedCount})`, actualCount === expectedCount);
    check(`Dynamic pipeline exit code is 0`, res.exitCode === 0);
  }

  console.log("\n=== 2. ADVANCED REDIRECTIONS & STREAM ISOLATION ===");
  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // Output redirection should NOT pollute stdout
    const r1 = await engine.execute('echo "secret data 123" > /tmp/secret.log');
    check('Output redirection produces empty stdout', r1.stdout === '');
    check('Target file contains secret data', vfs.readFile('/tmp/secret.log') === 'secret data 123\n');

    // Chained redirection with < and >>
    await engine.execute('cat < /tmp/secret.log | grep "secret" >> /tmp/append.log');
    check('Append file has first line', vfs.readFile('/tmp/append.log') === 'secret data 123\n');

    await engine.execute('echo "more data 456" >> /tmp/append.log');
    check('Append file has both lines', vfs.readFile('/tmp/append.log') === 'secret data 123\nmore data 456\n');

    // Missing file for input redirection
    const rMissing = await engine.execute('cat < /tmp/nonexistent_file_xyz.txt');
    check('Input redirection with missing file sets exit code 1', rMissing.exitCode === 1);
    check('Input redirection error message sent to stderr', rMissing.stderr.includes('No such file or directory'));
  }

  console.log("\n=== 3. SHORT-CIRCUITING & EXIT CODE PROPAGATION ===");
  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // true && false || echo "recovered"
    const r1 = await engine.execute('true && false || echo "recovered"');
    check('Complex chaining with recovery prints "recovered"', r1.stdout.trim() === 'recovered');
    check('Final exit code after recovery is 0', r1.exitCode === 0);

    // false && echo "skip" || echo "alt" ; echo "always"
    const r2 = await engine.execute('false && echo "skip" || echo "alt" ; echo "always"');
    check('Sequence with short-circuit executes alternate and sequence', r2.stdout === 'alt\nalways\n');
    check('Exit code is 0', r2.exitCode === 0);

    // Command not found sets 127 and ? reflects 127
    const rNotFound = await engine.execute('nonexistent_bin_test_abc');
    check('Command not found gives exit code 127', rNotFound.exitCode === 127);
    check('Command not found prints bash error', rNotFound.stderr.includes('command not found'));

    const rCodeCheck = await engine.execute('echo $?');
    check('$? reflects 127', rCodeCheck.stdout.trim() === '127');
  }

  console.log("\n=== 4. QUOTES, ESCAPING & VARIABLE EXPANSION EDGE CASES ===");
  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs, env: { FOO: 'bar', EMPTY: '' } });

    // Single quotes inside double quotes
    const r1 = await engine.execute('echo "foo \'inside single\' $FOO"');
    check('Single quotes inside double quotes are literal and $FOO expands', r1.stdout.trim() === "foo 'inside single' bar");

    // Double quotes inside single quotes
    const r2 = await engine.execute('echo \'foo "inside double" $FOO\'');
    check('Double quotes and $FOO inside single quotes remain literal', r2.stdout.trim() === 'foo "inside double" $FOO');

    // Fallback variable expansion: unset variable
    const r3 = await engine.execute('echo "${UNSET_VAR:-fallback_value}"');
    check('Unset variable uses fallback', r3.stdout.trim() === 'fallback_value');

    // Fallback variable expansion: empty variable
    const r4 = await engine.execute('echo "${EMPTY:-empty_fallback}"');
    check('Empty variable uses fallback under :- syntax', r4.stdout.trim() === 'empty_fallback');

    // Escaped spaces
    const r5 = await engine.execute('echo hello\\ world');
    check('Escaped space outside quotes preserves single token', r5.stdout.trim() === 'hello world');
  }

  console.log("\n=== 5. PARSER SYNTAX ERROR BOUNDARIES ===");
  {
    const syntaxTests = [
      { input: '| echo hi', name: 'Leading pipe' },
      { input: 'echo hi |', name: 'Trailing pipe' },
      { input: 'echo hi || | cat', name: 'Pipe after OR' },
      { input: 'echo hi && && echo bye', name: 'Duplicate AND' },
      { input: 'cat >', name: 'Trailing output redirect' },
      { input: 'cat <', name: 'Trailing input redirect' },
      { input: 'echo "unclosed quote', name: 'Unclosed double quote' },
      { input: "echo 'unclosed quote", name: 'Unclosed single quote' },
    ];

    for (const st of syntaxTests) {
      let threw = false;
      try {
        ShellParser.parse(st.input);
      } catch (err) {
        threw = true;
      }
      check(`Syntax error caught for: ${st.name}`, threw);
    }
  }

  console.log("\n=== 6. AUDIT FIX VERIFICATION: SYMLINK ELOOP & RM -RF / ===");
  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs });

    // rm -rf / must return exit code 1 even with -f
    const rm1 = await engine.execute('rm -rf /');
    check('rm -rf / returns exitCode 1', rm1.exitCode === 1);
    check('rm -rf / prints dangerous warning', rm1.stderr.includes('dangerous'));

    const rm2 = await engine.execute('rm -fr /');
    check('rm -fr / returns exitCode 1', rm2.exitCode === 1);
    check('rm -fr / prints dangerous warning', rm2.stderr.includes('dangerous'));

    // Create a 5-hop linear symlink chain (should resolve cleanly)
    const home = vfs.resolve('/home/student');
    home.children['f_final'] = new VFSNode({ name: 'f_final', type: 'file', content: 'target reached' });
    home.children['s1'] = new VFSNode({ name: 's1', type: 'symlink', target: '/home/student/f_final' });
    home.children['s2'] = new VFSNode({ name: 's2', type: 'symlink', target: '/home/student/s1' });
    home.children['s3'] = new VFSNode({ name: 's3', type: 'symlink', target: '/home/student/s2' });
    home.children['s4'] = new VFSNode({ name: 's4', type: 'symlink', target: '/home/student/s3' });
    home.children['s5'] = new VFSNode({ name: 's5', type: 'symlink', target: '/home/student/s4' });

    const resolved5 = vfs.resolve('/home/student/s5');
    check('5-hop symlink resolves target correctly', resolved5 !== null && resolved5.content === 'target reached');

    // Create circular symlink loop: loop1 -> loop2 -> loop1
    home.children['loop1'] = new VFSNode({ name: 'loop1', type: 'symlink', target: '/home/student/loop2' });
    home.children['loop2'] = new VFSNode({ name: 'loop2', type: 'symlink', target: '/home/student/loop1' });

    let loopThrew = false;
    let loopErrorCode = null;
    try {
      vfs.resolve('/home/student/loop1');
    } catch (err) {
      loopThrew = true;
      loopErrorCode = err.code;
    }
    check('Circular symlink throws error', loopThrew);
    check('Circular symlink error code is ELOOP', loopErrorCode === 'ELOOP');
  }

  console.log("\n=== 7. TERMINAL UI READLINE SHORTCUTS & PROMPT FORMAT ===");
  {
    const vfs = new VirtualFS();
    const engine = new ShellEngine({ vfs, cwd: '/home/student' });
    const term = new TerminalUI({ shellEngine: engine, vfs });

    // Prompt info
    const pInfo = term.getPromptInfo();
    check('Student prompt user is student', pInfo.user === 'student');
    check('Student prompt host is examquiz', pInfo.host === 'examquiz');
    check('Student prompt path is ~', pInfo.cwd === '~');
    check('Student prompt symbol is $', pInfo.symbol === '$');
    check('Student prompt isRoot is false', pInfo.isRoot === false);

    // Root prompt info
    engine.env.USER = 'root';
    engine.cwd = '/root';
    const rInfo = term.getPromptInfo();
    check('Root prompt user is root', rInfo.user === 'root');
    check('Root prompt path is ~', rInfo.cwd === '~');
    check('Root prompt symbol is #', rInfo.symbol === '#');
    check('Root prompt isRoot is true', rInfo.isRoot === true);

    // Autocompletion LCP
    check('LCP of ["abc", "abd"] is "ab"', longestCommonPrefix(["abc", "abd"]) === "ab");
    check('LCP of ["test"] is "test"', longestCommonPrefix(["test"]) === "test");
    check('LCP of ["foo", "bar"] is ""', longestCommonPrefix(["foo", "bar"]) === "");
    check('LCP of [] is ""', longestCommonPrefix([]) === "");
  }

  console.log("\n========================================");
  console.log(`ADVERSARIAL STRESS-TEST RESULTS: ${passed} passed, ${failed} failed`);
  console.log("========================================");

  if (failed > 0) {
    process.exit(1);
  }
}

runAdversarialAudit().catch(err => {
  console.error("Adversarial test error:", err);
  process.exit(1);
});
