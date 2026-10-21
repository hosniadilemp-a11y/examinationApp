/**
 * Automated Unit Tests for Linux Challenge Evaluator
 * Verifies assertion types, VFS snapshot rollback, isolation, and confidential hidden test masking.
 * Run with: node frontend/js/linux/test-evaluator.mjs
 */

import { LinuxChallengeEvaluator } from './linux-evaluator.js';
import { VirtualFS } from './vfs.js';

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

function suite(name) {
  console.log(`\n========================================`);
  console.log(`[SUITE] ${name}`);
  console.log(`========================================`);
}

async function runAllTests() {
  // =========================================================================
  // SUITE 1: File Existence & Absence Assertions (file_exists, file_not_exists)
  // =========================================================================
  suite('File Existence & Non-Existence Assertions');
  {
    const challenge = {
      id: 'TEST-FS-01',
      title: 'Création et Suppression de Fichiers',
      points: 2.0,
      initial_fs: {
        dirs: [{ path: '/home/student/workspace', mode: '0755' }],
        files: [
          { path: '/home/student/workspace/temp.log', content: 'temporary', mode: '0644' }
        ]
      },
      public_tests: [
        {
          name: 'Vérification création src',
          assertion_type: 'file_exists',
          path: '/home/student/workspace/src',
          expected_type: 'dir'
        },
        {
          name: 'Vérification création README.md',
          assertion_type: 'file_exists',
          path: '/home/student/workspace/README.md',
          expected_type: 'file'
        },
        {
          name: 'Vérification suppression temp.log',
          assertion_type: 'file_not_exists',
          path: '/home/student/workspace/temp.log'
        }
      ],
      hidden_tests: []
    };

    // Correct student solution
    const studentCmd = 'cd /home/student/workspace && mkdir src && touch README.md && rm temp.log';
    const res = await LinuxChallengeEvaluator.evaluate(studentCmd, challenge);

    assert(res.success === true, 'All public existence/absence tests passed');
    assert(res.passed_count === 3, 'Passed 3/3 tests');
    assert(res.public_results[0].passed === true, 'src directory created and detected');
    assert(res.public_results[1].passed === true, 'README.md file created and detected');
    assert(res.public_results[2].passed === true, 'temp.log removal confirmed');

    // Incorrect student solution (failed to remove temp.log)
    const badCmd = 'cd /home/student/workspace && mkdir src && touch README.md';
    const badRes = await LinuxChallengeEvaluator.evaluate(badCmd, challenge);
    assert(badRes.success === false, 'Evaluation fails when required deletion is missing');
    assert(badRes.public_results[2].passed === false, 'file_not_exists fails when file remains');
  }

  // =========================================================================
  // SUITE 2: File Content Assertions (exact, regex, contains, lines)
  // =========================================================================
  suite('File Content Assertions (contains, exact, regex, lines)');
  {
    const challenge = {
      id: 'TEST-CONTENT-01',
      title: 'Génération de Logs et Rapports',
      points: 3.0,
      initial_fs: {
        dirs: [{ path: '/home/student/data', mode: '0755' }]
      },
      public_tests: [
        {
          name: 'Vérification sous-chaîne clé',
          assertion_type: 'file_contains',
          path: '/home/student/data/report.txt',
          expected: 'SUCCESS_CODE_42'
        },
        {
          name: 'Vérification exactitude en-tête',
          assertion_type: 'fs_content_exact',
          path: '/home/student/data/header.txt',
          expected: 'EXAM_PLATFORM_V2\n'
        },
        {
          name: 'Vérification format regex',
          assertion_type: 'fs_content_regex',
          path: '/home/student/data/report.txt',
          expected: 'DATE:\\d{4}-\\d{2}'
        },
        {
          name: 'Vérification décompte de lignes',
          assertion_type: 'fs_content_lines',
          path: '/home/student/data/lines.txt',
          expected: 3
        }
      ]
    };

    const studentCmd = `
      echo "DATE:2026-10 Status: OK, Token: SUCCESS_CODE_42" > /home/student/data/report.txt
      echo "EXAM_PLATFORM_V2" > /home/student/data/header.txt
      echo -e "line1\\nline2\\nline3" > /home/student/data/lines.txt
    `;

    const res = await LinuxChallengeEvaluator.evaluate(studentCmd, challenge);
    assert(res.success === true, 'All content assertions passed');
    assert(res.public_results[0].passed === true, 'file_contains verified substring');
    assert(res.public_results[1].passed === true, 'fs_content_exact matched string strictly');
    assert(res.public_results[2].passed === true, 'fs_content_regex matched date pattern');
    assert(res.public_results[3].passed === true, 'fs_content_lines verified line count 3');
  }

  // =========================================================================
  // SUITE 3: POSIX Permissions & Mode Bits (chmod, fs_mode, fs_mode_mask)
  // =========================================================================
  suite('POSIX Permissions & Mode Bits (chmod, fs_mode, fs_mode_mask)');
  {
    const challenge = {
      id: 'TEST-PERMS-01',
      title: 'Sécurisation de Scripts',
      initial_fs: {
        files: [
          { path: '/home/student/deploy.sh', content: '#!/bin/bash\necho ok', mode: '0644' },
          { path: '/home/student/secret.key', content: 'SECRET_DATA', mode: '0666' }
        ]
      },
      public_tests: [
        {
          name: 'Droits 750 sur script',
          assertion_type: 'fs_mode',
          path: '/home/student/deploy.sh',
          expected: '750'
        },
        {
          name: 'Mode 600 sur clé confidentielle',
          assertion_type: 'permission',
          path: '/home/student/secret.key',
          expected: '600'
        },
        {
          name: 'Masque absence droits others',
          assertion_type: 'fs_mode_mask',
          path: '/home/student/deploy.sh',
          mask: '007',
          expected: '000'
        }
      ]
    };

    const studentCmd = 'chmod 750 /home/student/deploy.sh && chmod 600 /home/student/secret.key';
    const res = await LinuxChallengeEvaluator.evaluate(studentCmd, challenge);

    assert(res.success === true, 'All permission tests passed');
    assert(res.public_results[0].passed === true, 'fs_mode octal 750 verified');
    assert(res.public_results[1].passed === true, 'permission octal 600 verified');
    assert(res.public_results[2].passed === true, 'fs_mode_mask verified others = 0');
  }

  // =========================================================================
  // SUITE 4: Standard Output & Exit Codes (stdout_exact, stdout_contains, exit_code)
  // =========================================================================
  suite('Standard Output & Exit Codes');
  {
    const challenge = {
      id: 'TEST-STDOUT-01',
      title: 'Pipeline et Commandes de Diagnostic',
      public_tests: [
        {
          name: 'Affichage kernel',
          cmd: 'uname -s',
          assertion_type: 'stdout_exact',
          expected: 'Linux'
        },
        {
          name: 'Recherche de motif',
          cmd: 'cat /etc/passwd | grep student',
          assertion_type: 'stdout_contains',
          expected: '1000:1000'
        },
        {
          name: 'Code de retour 0',
          assertion_type: 'exit_code',
          expected: 0
        }
      ]
    };

    const studentCmd = 'echo "Ready"';
    const res = await LinuxChallengeEvaluator.evaluate(studentCmd, challenge);

    assert(res.success === true, 'All stdout and exit code assertions passed');
    assert(res.public_results[0].passed === true, 'stdout_exact matched Linux');
    assert(res.public_results[1].passed === true, 'stdout_contains found student uid');
    assert(res.public_results[2].passed === true, 'exit_code 0 confirmed');
  }

  // =========================================================================
  // SUITE 5: Confidential Hidden Test Masking (Anti-Cheat & Anti-Leak)
  // =========================================================================
  suite('Confidential Hidden Test Masking');
  {
    const challenge = {
      id: 'CH-CONFIDENTIAL',
      title: 'Défi Haute Sécurité',
      points: 5.0,
      initial_fs: {
        files: [{ path: '/home/student/app.py', content: 'print("Production")', mode: '0644' }]
      },
      public_tests: [
        {
          name: 'Exécutabilité app.py',
          cmd: 'test -x /home/student/app.py && echo "EXEC_OK"',
          assertion_type: 'stdout',
          expected: 'EXEC_OK'
        }
      ],
      hidden_tests: [
        {
          name: 'Test Caché Inode',
          cmd: 'ls -i /home/student/app.py',
          assertion_type: 'stdout_contains',
          expected: 'app.py'
        },
        {
          name: 'Test Caché Droits Others',
          assertion_type: 'fs_mode_mask',
          path: '/home/student/app.py',
          mask: '007',
          expected: '000'
        },
        {
          name: 'Test Caché Contenu Strict',
          assertion_type: 'fs_content_exact',
          path: '/home/student/app.py',
          expected: 'print("Production")'
        }
      ]
    };

    const studentCmd = 'chmod 750 /home/student/app.py';
    const res = await LinuxChallengeEvaluator.evaluate(studentCmd, challenge);

    assert(res.success === true, 'All tests (public & hidden) passed');
    assert(res.total_tests === 4, 'Total 4 tests evaluated');
    assert(res.passed_count === 4, 'Passed count is 4');
    assert(res.public_results.length === 1, '1 public test');
    assert(res.hidden_results.length === 3, '3 hidden tests');

    // Strict confidentiality assertions:
    for (const ht of res.hidden_results) {
      assert(ht.is_public === false, 'Hidden test marked as is_public: false');
      assert(ht.cmd === '[Protégé]', 'Hidden test cmd is masked as [Protégé]');
      assert(ht.expected === '[Protégé]', 'Hidden test expected is masked as [Protégé]');
      assert(ht.actual === '[Protégé]', 'Hidden test actual is masked as [Protégé] when passed');
      assert(ht.assertion_type === '[Protégé]', 'Hidden test assertion_type is masked as [Protégé]');
      assert(!JSON.stringify(ht).includes('print("Production")'), 'Confidential payload does not leak expected content');
      assert(!JSON.stringify(ht).includes('ls -i'), 'Confidential payload does not leak test command');
    }

    // Now test a failing hidden test
    const failingCmd = 'chmod 777 /home/student/app.py';
    const failRes = await LinuxChallengeEvaluator.evaluate(failingCmd, challenge);
    assert(failRes.success === false, 'Fails when hidden mask test fails');
    const failedHidden = failRes.hidden_results.find(h => !h.passed);
    assert(failedHidden !== undefined, 'Failing hidden test found');
    assert(failedHidden.cmd === '[Protégé]', 'Failing hidden test still masks cmd');
    assert(failedHidden.expected === '[Protégé]', 'Failing hidden test still masks expected');
    assert(failedHidden.actual === 'Échec', 'Failing hidden test displays neutral "Échec"');
  }

  // =========================================================================
  // SUITE 6: VFS Snapshot Rollback & Test Isolation
  // =========================================================================
  suite('VFS Snapshot Rollback & Test Isolation');
  {
    const challenge = {
      id: 'TEST-ISOLATION-01',
      title: 'Isolation Multi-Tests',
      initial_fs: {
        files: [{ path: '/home/student/counter.txt', content: 'INITIAL', mode: '0644' }]
      },
      public_tests: [
        {
          name: 'Test #1 modifiant temporairement le VFS',
          cmd: 'echo "TEST_1_WAS_HERE" > /home/student/counter.txt && cat /home/student/counter.txt',
          assertion_type: 'stdout_contains',
          expected: 'TEST_1_WAS_HERE'
        },
        {
          name: 'Test #2 vérifiant que Test #1 n a pas pollué l état étudiant',
          cmd: 'cat /home/student/counter.txt',
          assertion_type: 'stdout_exact',
          expected: 'STUDENT_STATE'
        }
      ]
    };

    const studentCmd = 'echo "STUDENT_STATE" > /home/student/counter.txt';
    const res = await LinuxChallengeEvaluator.evaluate(studentCmd, challenge);

    assert(res.success === true, 'Test #2 saw unmodified student state despite Test #1 modification');
    assert(res.public_results[0].passed === true, 'Test 1 executed');
    assert(res.public_results[1].passed === true, 'Test 2 verified clean student rollback');
  }

  // =========================================================================
  // SUITE 7: Real Challenge Benchmark (LINUX-101 and LINUX-102)
  // =========================================================================
  suite('Real Curriculum Challenges Evaluation (LINUX-101, LINUX-102)');
  {
    // LINUX-101
    const ch101 = {
      id: 'LINUX-101',
      title: 'Exploration et Arborescence Système',
      initial_fs: {
        '/home/student': {
          type: 'dir',
          files: {
            '.bashrc': { type: 'file', content: '# bashrc config\n' },
            '.profile': { type: 'file', content: 'export PATH\n' },
            'documents': { type: 'dir', files: {} },
            'notes.txt': { type: 'file', content: 'Bienvenue sur Linux\n' }
          }
        }
      },
      public_tests: [
        {
          name: 'Affichage chemin absolu',
          cmd: 'pwd',
          expected_stdout: '/home/student',
          expected_exit_code: 0,
          assertion_type: 'stdout',
          expected: '/home/student'
        },
        {
          name: 'Affichage fichiers cachés',
          cmd: 'ls -la',
          expected_stdout: '.bashrc',
          expected_exit_code: 0,
          assertion_type: 'stdout',
          expected: '.bashrc'
        }
      ],
      hidden_tests: [
        {
          name: 'Vérification enchaînement pwd et ls',
          cmd: 'pwd && ls -a',
          expected_stdout: '/home/student',
          expected_exit_code: 0,
          assertion_type: 'stdout',
          expected: '/home/student'
        },
        {
          name: 'Vérification présence notes.txt',
          cmd: 'ls -l notes.txt',
          expected_stdout: 'notes.txt',
          expected_exit_code: 0,
          assertion_type: 'stdout',
          expected: 'notes.txt'
        }
      ]
    };

    const res101 = await LinuxChallengeEvaluator.evaluate('pwd && ls -la', ch101);
    assert(res101.success === true, 'LINUX-101 solution validated 100%');
    assert(res101.passed_count === 4, 'All 4 tests passed for LINUX-101');

    // LINUX-102
    const ch102 = {
      id: 'LINUX-102',
      title: 'Création d une Structure de Projet',
      initial_fs: {
        '/home/student': {
          type: 'dir',
          files: {}
        }
      },
      public_tests: [
        {
          name: 'Vérification répertoire project/src',
          cmd: 'test -d project/src && echo "SRC_OK"',
          expected_stdout: 'SRC_OK',
          expected_exit_code: 0,
          assertion_type: 'file_exists',
          expected: 'project/src'
        },
        {
          name: 'Vérification fichier README.md',
          cmd: 'test -f project/README.md && echo "README_OK"',
          expected_stdout: 'README_OK',
          expected_exit_code: 0,
          assertion_type: 'file_exists',
          expected: 'project/README.md'
        }
      ],
      hidden_tests: [
        {
          name: 'Vérification répertoire docs',
          cmd: 'test -d project/docs && echo "DOCS_OK"',
          expected_stdout: 'DOCS_OK',
          expected_exit_code: 0,
          assertion_type: 'file_exists',
          expected: 'project/docs'
        },
        {
          name: 'Vérification script main.sh',
          cmd: 'test -f project/src/main.sh && echo "MAIN_OK"',
          expected_stdout: 'MAIN_OK',
          expected_exit_code: 0,
          assertion_type: 'file_exists',
          expected: 'project/src/main.sh'
        }
      ]
    };

    const res102 = await LinuxChallengeEvaluator.evaluate('mkdir -p project/src project/docs && touch project/src/main.sh project/README.md', ch102);
    assert(res102.success === true, 'LINUX-102 solution validated 100%');
    assert(res102.passed_count === 4, 'All 4 tests passed for LINUX-102');
  }

  // =========================================================================
  // SUMMARY
  // =========================================================================
  console.log(`\n========================================`);
  console.log(`EVALUATOR TEST RESULTS: ${passedTests}/${totalTests} PASSED (${failedTests} FAILED)`);
  console.log(`========================================`);

  if (failedTests > 0) {
    process.exit(1);
  }
}

runAllTests().catch(err => {
  console.error("Unhandled error in test runner:", err);
  process.exit(1);
});
