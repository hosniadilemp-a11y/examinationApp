/**
 * Adversarial Forensic Stress-Test for LinuxChallengeEvaluator
 * Executed independently by m4_auditor.
 */

import { LinuxChallengeEvaluator } from '../../../frontend/js/linux/linux-evaluator.js';
import { VirtualFS } from '../../../frontend/js/linux/vfs.js';

let passed = 0;
let failed = 0;

function check(condition, message) {
  if (condition) {
    passed++;
    console.log(`[PASS] ${message}`);
  } else {
    failed++;
    console.error(`[FAIL] ${message}`);
  }
}

async function runForensicAudit() {
  console.log('--- STARTING FORENSIC INTEGRITY AUDIT ON LinuxChallengeEvaluator ---');

  // Test 1: Empty command with existence assertions must FAIL
  {
    const ch = {
      id: 'AUDIT-01',
      public_tests: [
        { name: 'T1', assertion_type: 'file_exists', path: '/home/student/required.txt' }
      ]
    };
    const res = await LinuxChallengeEvaluator.evaluate('', ch);
    check(res.success === false, 'Empty command fails when file must be created');
    check(res.public_results[0].passed === false, 'file_exists assertion fails when file does not exist');
  }

  // Test 2: Spoofed stdout when file_exists is expected must FAIL
  {
    const ch = {
      id: 'AUDIT-02',
      public_tests: [
        { name: 'T2', assertion_type: 'file_exists', path: '/home/student/created.txt' }
      ]
    };
    const res = await LinuxChallengeEvaluator.evaluate('echo "/home/student/created.txt"', ch);
    check(res.success === false, 'Spoofing stdout does not satisfy file_exists assertion');
    check(res.public_results[0].passed === false, 'created.txt is not in VFS, assertion correctly fails');
  }

  // Test 3: Mode mismatch must FAIL
  {
    const ch = {
      id: 'AUDIT-03',
      initial_fs: {
        files: [{ path: '/home/student/script.sh', content: '#!/bin/bash', mode: '0644' }]
      },
      public_tests: [
        { name: 'T3', assertion_type: 'fs_mode', path: '/home/student/script.sh', expected: '755' }
      ]
    };
    // Student sets 700 instead of 755
    const res = await LinuxChallengeEvaluator.evaluate('chmod 700 /home/student/script.sh', ch);
    check(res.success === false, 'Incorrect chmod (700 instead of 755) fails');
    check(res.public_results[0].passed === false, 'fs_mode detects mode mismatch');
  }

  // Test 4: Hidden test confidentiality under failure and success
  {
    const secretCmd = 'cat /home/student/secret_audit_passphrase.txt';
    const secretExpected = 'SUPER_SECRET_TOKEN_XYZ';
    const ch = {
      id: 'AUDIT-04',
      initial_fs: {
        files: [{ path: '/home/student/secret_audit_passphrase.txt', content: 'placeholder', mode: '0600' }]
      },
      public_tests: [],
      hidden_tests: [
        {
          name: 'Confidential Audit Test',
          cmd: secretCmd,
          assertion_type: 'stdout_contains',
          expected: secretExpected
        }
      ]
    };

    // When student writes the expected token and test passes
    const passRes = await LinuxChallengeEvaluator.evaluate(`echo "${secretExpected}" > /home/student/secret_audit_passphrase.txt`, ch, { runHidden: true });
    const serializedHiddenPass = JSON.stringify(passRes.hidden_results);
    check(!serializedHiddenPass.includes(secretCmd), 'Passing hidden test cmd is NOT leaked in hidden_results');
    check(!serializedHiddenPass.includes(secretExpected), 'Passing hidden test expected value is NOT leaked in hidden_results');
    check(passRes.hidden_results[0].cmd === '[Protégé]', 'Hidden cmd is masked as [Protégé]');
    check(passRes.hidden_results[0].expected === '[Protégé]', 'Hidden expected is masked as [Protégé]');
    check(passRes.hidden_results[0].actual === '[Protégé]', 'Hidden actual is masked as [Protégé]');

    // When test fails
    const failRes = await LinuxChallengeEvaluator.evaluate('echo "wrong" > /home/student/secret_audit_passphrase.txt', ch, { runHidden: true });
    const serializedHiddenFail = JSON.stringify(failRes.hidden_results);
    check(!serializedHiddenFail.includes(secretCmd), 'Failing hidden test cmd is NOT leaked');
    check(!serializedHiddenFail.includes(secretExpected), 'Failing hidden test expected is NOT leaked');
    check(failRes.hidden_results[0].cmd === '[Protégé]', 'Failing cmd masked as [Protégé]');
    check(failRes.hidden_results[0].expected === '[Protégé]', 'Failing expected masked as [Protégé]');
    check(failRes.hidden_results[0].actual === 'Échec', 'Failing actual displays neutral "Échec"');
  }

  // Test 5: Isolation & Snapshot rollback between test assertions
  {
    const ch = {
      id: 'AUDIT-05',
      initial_fs: {
        files: [{ path: '/home/student/data.txt', content: 'INITIAL_STUDENT_DATA', mode: '0644' }]
      },
      public_tests: [
        {
          name: 'Destructive Test 1',
          cmd: 'rm -f /home/student/data.txt && touch /home/student/polluted_by_test1.txt',
          assertion_type: 'exit_code',
          expected: 0
        },
        {
          name: 'Verification Test 2',
          assertion_type: 'fs_content_exact',
          path: '/home/student/data.txt',
          expected: 'STUDENT_MODIFIED_CONTENT\n'
        },
        {
          name: 'Absence of pollution from Test 1',
          assertion_type: 'file_not_exists',
          path: '/home/student/polluted_by_test1.txt'
        }
      ]
    };

    const res = await LinuxChallengeEvaluator.evaluate('echo "STUDENT_MODIFIED_CONTENT" > /home/student/data.txt', ch);
    check(res.success === true, 'All isolation tests pass');
    check(res.public_results[0].passed === true, 'Destructive test 1 executed');
    check(res.public_results[1].passed === true, 'Test 2 saw original student state, rollback worked');
    check(res.public_results[2].passed === true, 'Test 1 pollution was cleaned up by snapshot restore');
  }

  // Test 6: Exit code sensitivity
  {
    const ch = {
      id: 'AUDIT-06',
      public_tests: [
        { name: 'Exit 0 expected', cmd: 'ls /nonexistent_folder_abc', assertion_type: 'exit_code', expected: 0 }
      ]
    };
    const res = await LinuxChallengeEvaluator.evaluate('echo "hi"', ch);
    check(res.success === false, 'Command exiting with non-zero fails exit_code: 0 check');
    check(res.public_results[0].passed === false, 'Non-zero exit code detected correctly');
  }

  console.log(`\nFORENSIC ADVERSARIAL AUDIT COMPLETE: ${passed} PASSED, ${failed} FAILED`);
  if (failed > 0) process.exit(1);
}

runForensicAudit().catch(err => {
  console.error('Fatal error during forensic audit:', err);
  process.exit(1);
});
