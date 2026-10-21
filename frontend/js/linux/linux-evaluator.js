/**
 * Linux Challenge Evaluator (Harnais d'Évaluation Automatisée de Défis Linux)
 * 
 * Exécute la solution de l'étudiant dans un bac à sable VirtualFS dédié et isolé,
 * puis valide l'ensemble des assertions de test (publics et cachés) :
 * - file_exists / fs_exists (présence et type de fichier/répertoire)
 * - file_not_exists / fs_not_exists (suppression confirmée)
 * - file_contains / fs_content_contains / fs_content_exact / fs_content_regex / fs_content_lines
 * - permission / mode / fs_mode / fs_mode_mask (droits d'accès octaux et symboliques)
 * - owner / fs_owner (propriétaire et groupe)
 * - stdout_exact / stdout_contains / stdout_regex / stdout
 * - exit_code (code de retour POSIX)
 * 
 * Enforce la stricte confidentialité des tests cachés :
 * Les critères, commandes de vérification et sorties attendues des tests cachés
 * sont rigoureusement masqués en "[Protégé]" dans tous les payloads clients.
 */

import { VirtualFS } from './vfs.js';
import { ShellEngine } from './shell-engine.js';

export class LinuxChallengeEvaluator {
  /**
   * Évalue la solution de l'étudiant contre un défi Linux
   * @param {string} studentCommand - Commande(s) ou script soumis par l'étudiant
   * @param {Object} challengeData - Métadonnées du défi (initial_fs, public_tests, hidden_tests)
   * @param {Object} [options={}] - Options de configuration
   * @param {VirtualFS} [options.vfs] - Instance VFS optionnelle
   * @param {boolean} [options.runHidden=true] - Exécuter également les tests cachés
   * @param {string} [options.cwd='/home/student'] - Répertoire de travail
   * @returns {Promise<Object>} Rapport complet d'évaluation
   */
  static async evaluate(studentCommand, challengeData, options = {}) {
    const evaluator = new LinuxChallengeEvaluator(options);
    return await evaluator.evaluateChallenge(studentCommand, challengeData, options);
  }

  /**
   * @param {Object} [options={}]
   */
  constructor(options = {}) {
    this.options = options;
  }

  /**
   * Exécute l'évaluation complète d'un défi
   * @param {string} studentCommand
   * @param {Object} challengeData
   * @param {Object} [options={}]
   * @returns {Promise<Object>}
   */
  async evaluateChallenge(studentCommand, challengeData, options = {}) {
    if (!challengeData) {
      throw new Error("Données de défi manquantes pour l'évaluation.");
    }

    const cwd = options.cwd || '/home/student';
    const runHidden = options.runHidden !== false;
    const challengePoints = Number(challengeData.points !== undefined ? challengeData.points : 2.0);

    // 1. Initialiser une instance VFS propre et isolée
    const vfs = options.vfs ? options.vfs : new VirtualFS();
    const initialFs = challengeData.initial_fs || challengeData.initial_vfs;
    if (initialFs) {
      vfs.loadInitialFS(initialFs);
    }
    vfs.cwd = cwd;

    // Snapshot avant exécution de l'étudiant
    const initialSnapshot = vfs.snapshot();

    // 2. Moteur Shell et exécution de la commande de l'étudiant
    const shellEngine = new ShellEngine({ vfs, cwd });
    const cleanCmd = (studentCommand || '').trim();

    let studentExec = { stdout: '', stderr: '', exitCode: 0 };
    if (cleanCmd) {
      studentExec = await shellEngine.execute(cleanCmd);
    }

    // Capture de l'état VFS résultant de l'étudiant
    const studentVfsSnapshot = vfs.snapshot();

    // 3. Évaluation des assertions
    const publicTests = Array.isArray(challengeData.public_tests) ? challengeData.public_tests : [];
    const hiddenTests = Array.isArray(challengeData.hidden_tests) ? challengeData.hidden_tests : [];

    const publicResults = [];
    const hiddenResults = [];

    // --- Tests Publics ---
    for (let idx = 0; idx < publicTests.length; idx++) {
      const test = publicTests[idx];
      const result = await this._runSingleTest(test, {
        vfs,
        shellEngine,
        studentExec,
        studentCommand: cleanCmd,
        studentVfsSnapshot,
        isPublic: true,
        testIndex: idx + 1
      });
      publicResults.push(result);
    }

    // --- Tests Cachés (si activés) ---
    if (runHidden) {
      for (let idx = 0; idx < hiddenTests.length; idx++) {
        const test = hiddenTests[idx];
        const result = await this._runSingleTest(test, {
          vfs,
          shellEngine,
          studentExec,
          studentCommand: cleanCmd,
          studentVfsSnapshot,
          isPublic: false,
          testIndex: publicTests.length + idx + 1
        });
        hiddenResults.push(result);
      }
    }

    // 4. Calcul des scores et métriques
    const totalTests = publicResults.length + hiddenResults.length;
    const passedCount = publicResults.filter(r => r.passed).length + hiddenResults.filter(r => r.passed).length;
    const allPassed = totalTests > 0 && passedCount === totalTests;
    const scorePercentage = totalTests > 0 ? Math.round((passedCount / totalTests) * 100) : 100;
    const awardedPoints = totalTests > 0 ? Number(((passedCount / totalTests) * challengePoints).toFixed(2)) : 0.0;

    const message = allPassed
      ? '✅ Défi validé avec succès !'
      : `Validation : ${passedCount}/${totalTests} cas de test réussis (${scorePercentage}%).`;

    return {
      challenge_id: challengeData.id || '',
      title: challengeData.title || '',
      success: allPassed,
      all_passed: allPassed,
      awarded_points: awardedPoints,
      max_points: challengePoints,
      passed_count: passedCount,
      total_tests: totalTests,
      score_percentage: scorePercentage,
      exec_stdout: studentExec.stdout,
      exec_stderr: studentExec.stderr,
      exec_exit_code: studentExec.exitCode,
      public_results: publicResults,
      hidden_results: hiddenResults,
      test_results: [...publicResults, ...hiddenResults],
      vfs_snapshot: studentVfsSnapshot,
      initial_snapshot: initialSnapshot,
      message
    };
  }

  /**
   * Exécute une assertion de test unique avec isolation et rollback VFS
   * @private
   */
  async _runSingleTest(test, ctx) {
    const { vfs, shellEngine, studentExec, studentCommand, studentVfsSnapshot, isPublic, testIndex } = ctx;

    // Toujours restaurer l'état exact post-étudiant avant chaque test
    vfs.restore(studentVfsSnapshot);

    const testName = test.name || (isPublic ? `Cas de test #${testIndex} (Public)` : `Cas de test #${testIndex} (Caché)`);
    const assertionType = (test.assertion_type || test.type || 'stdout').toLowerCase();

    let cmdResult = null;
    if (test.cmd) {
      cmdResult = await shellEngine.execute(test.cmd);
    }

    let passed = false;
    let expectedDisplay = '';
    let actualDisplay = '';

    const effectiveStdout = cmdResult ? cmdResult.stdout : studentExec.stdout;
    const effectiveExitCode = cmdResult ? cmdResult.exitCode : studentExec.exitCode;

    // Détermination de la cible (chemin de fichier)
    const targetPath = test.path || test.expected_path || (typeof test.expected === 'string' && test.expected.startsWith('/') ? test.expected : (test.cmd && test.cmd.split(' ').slice(-1)[0]) || '');

    switch (assertionType) {
      // 1. Existence de fichier / dossier
      case 'file_exists':
      case 'fs_exists': {
        const pathToCheck = test.expected || test.path || (test.cmd && test.cmd.split(' ').slice(-1)[0]);
        const node = vfs.resolve(pathToCheck, { cwd: '/home/student' });
        expectedDisplay = `Existe (${pathToCheck})`;

        if (node) {
          const reqType = test.expected_type || (test.expected === 'dir' ? 'dir' : (test.expected === 'file' ? 'file' : null));
          if (reqType) {
            passed = node.type === reqType;
            actualDisplay = passed ? `Existe (${node.type})` : `Existe mais type '${node.type}' au lieu de '${reqType}'`;
          } else {
            passed = true;
            actualDisplay = `Existe (${node.type})`;
          }
        } else {
          // Si une commande test était attachée (ex: test -f ... && echo 'OK')
          if (test.expected_stdout && effectiveStdout.includes(String(test.expected_stdout))) {
            passed = true;
            actualDisplay = 'Validé via commande de test';
          } else {
            passed = false;
            actualDisplay = 'Introuvable';
          }
        }
        break;
      }

      // 2. Absence de fichier / suppression confirmée
      case 'file_not_exists':
      case 'fs_not_exists': {
        const pathToCheck = test.expected || test.path || '';
        const node = vfs.resolve(pathToCheck, { cwd: '/home/student' });
        passed = node === null;
        expectedDisplay = `Supprimé / Absent (${pathToCheck})`;
        actualDisplay = passed ? 'Absent (Suppression confirmée)' : 'Toujours présent';
        break;
      }

      // 3. Contenu de fichier (contient / exact / regex / lignes)
      case 'file_contains':
      case 'fs_content_contains': {
        const needle = String(test.expected || test.expected_content || test.expected_stdout || '');
        expectedDisplay = `Contient: "${needle}"`;

        let found = false;
        let contentSample = '';
        if (targetPath) {
          try {
            const content = vfs.readFile(targetPath, '/home/student');
            contentSample = content;
            if (content && content.includes(needle)) {
              found = true;
            }
          } catch (_) {}
        }
        if (!found && effectiveStdout && effectiveStdout.includes(needle)) {
          found = true;
          contentSample = effectiveStdout;
        }

        passed = found;
        actualDisplay = passed ? 'Contenu présent' : (contentSample ? `Non trouvé (extrait: "${contentSample.slice(0, 30)}...")` : 'Fichier introuvable ou vide');
        break;
      }

      case 'fs_content_exact': {
        const expectedExact = String(test.expected !== undefined ? test.expected : (test.expected_stdout || ''));
        expectedDisplay = expectedExact;
        try {
          const content = vfs.readFile(targetPath, '/home/student');
          passed = content === expectedExact;
          actualDisplay = passed ? 'Identique' : `Divergent (obtenu: "${content.slice(0, 40)}...")`;
        } catch (e) {
          passed = false;
          actualDisplay = `Erreur: ${e.message}`;
        }
        break;
      }

      case 'fs_content_regex': {
        const pattern = new RegExp(test.expected || test.pattern || '');
        expectedDisplay = `Regex /${pattern.source}/`;
        try {
          const content = vfs.readFile(targetPath, '/home/student');
          passed = pattern.test(content);
          actualDisplay = passed ? 'Match regex validé' : 'Aucune correspondance dans le fichier';
        } catch (e) {
          passed = false;
          actualDisplay = `Erreur: ${e.message}`;
        }
        break;
      }

      case 'fs_content_lines': {
        const expectedLines = Number(test.expected);
        expectedDisplay = `${expectedLines} ligne(s)`;
        try {
          const content = vfs.readFile(targetPath, '/home/student');
          const linesCount = content ? content.trim().split('\n').length : 0;
          passed = linesCount === expectedLines;
          actualDisplay = `${linesCount} ligne(s)`;
        } catch (e) {
          passed = false;
          actualDisplay = `Erreur: ${e.message}`;
        }
        break;
      }

      // 4. Permissions et Mode POSIX (chmod)
      case 'permission':
      case 'mode':
      case 'fs_mode': {
        const expectedPerm = String(test.expected || '755').replace(/^0o?/, '');
        const expectedVal = parseInt(expectedPerm, 8);
        expectedDisplay = `Mode ${expectedPerm}`;

        const node = vfs.resolve(targetPath, { cwd: '/home/student' });
        if (node) {
          const actualMode = node.mode & 0o777;
          passed = actualMode === expectedVal;
          actualDisplay = `Mode ${(actualMode).toString(8)}`;
        } else if (studentCommand.includes(expectedPerm) || studentCommand.includes(`chmod ${expectedPerm}`)) {
          passed = true;
          actualDisplay = `Validé via syntaxe commande (Mode ${expectedPerm})`;
        } else {
          passed = false;
          actualDisplay = 'Fichier introuvable pour vérification des droits';
        }
        break;
      }

      case 'fs_mode_mask': {
        const mask = parseInt(test.mask || '0777', 8);
        const expectedPerm = String(test.expected || '000').replace(/^0o?/, '');
        const expectedVal = parseInt(expectedPerm, 8);
        expectedDisplay = `Masque ${(mask).toString(8)} -> ${expectedPerm}`;

        const node = vfs.resolve(targetPath, { cwd: '/home/student' });
        if (node) {
          const actualMasked = node.mode & mask;
          passed = actualMasked === expectedVal;
          actualDisplay = `Mode masqué ${(actualMasked).toString(8).padStart(expectedPerm.length, '0')}`;
        } else {
          passed = false;
          actualDisplay = 'Fichier introuvable';
        }
        break;
      }

      // 5. Propriétaire et Groupe (chown)
      case 'owner':
      case 'fs_owner': {
        const expOwner = test.expected_owner || test.owner || test.expected;
        const expGroup = test.expected_group || test.group;
        expectedDisplay = expGroup ? `${expOwner}:${expGroup}` : `${expOwner}`;

        const node = vfs.resolve(targetPath, { cwd: '/home/student' });
        if (node) {
          const ownerMatch = node.owner === expOwner;
          const groupMatch = !expGroup || node.group === expGroup;
          passed = ownerMatch && groupMatch;
          actualDisplay = `${node.owner}:${node.group}`;
        } else {
          passed = false;
          actualDisplay = 'Fichier introuvable';
        }
        break;
      }

      // 6. Code de retour exit_code
      case 'exit_code': {
        const expectedExit = Number(test.expected !== undefined ? test.expected : (test.expected_exit_code !== undefined ? test.expected_exit_code : 0));
        expectedDisplay = `Code ${expectedExit}`;
        passed = effectiveExitCode === expectedExit;
        actualDisplay = `Code ${effectiveExitCode}`;
        break;
      }

      // 7. Sortie stdout exacte
      case 'stdout_exact': {
        const expectedOut = String(test.expected !== undefined ? test.expected : (test.expected_stdout || '')).trim();
        expectedDisplay = expectedOut;
        const actualOut = effectiveStdout.trim();
        passed = actualOut === expectedOut;
        actualDisplay = actualOut;
        break;
      }

      case 'stdout_regex': {
        const pattern = new RegExp(test.expected || test.pattern || '');
        expectedDisplay = `Regex /${pattern.source}/`;
        passed = pattern.test(effectiveStdout);
        actualDisplay = passed ? 'Match regex stdout' : `Divergent: "${effectiveStdout.slice(0, 40)}"`;
        break;
      }

      // 8. Sortie stdout contient (défaut)
      case 'stdout':
      case 'stdout_contains':
      default: {
        const expStdout = String(test.expected_stdout !== undefined ? test.expected_stdout : (test.expected !== undefined ? test.expected : '')).trim();
        const expExit = test.expected_exit_code !== undefined ? test.expected_exit_code : 0;

        expectedDisplay = expStdout || `Exit ${expExit}`;

        const exitMatches = effectiveExitCode === expExit;
        let outMatches = false;

        if (!expStdout) {
          outMatches = true;
        } else if (effectiveStdout.includes(expStdout)) {
          outMatches = true;
        } else if (effectiveStdout.trim() === expStdout) {
          outMatches = true;
        }

        passed = exitMatches && outMatches;
        actualDisplay = effectiveStdout.trim() || `Exit ${effectiveExitCode}`;
        break;
      }
    }

    // Rollback du VFS pour que les commandes de test ne polluent pas
    vfs.restore(studentVfsSnapshot);

    // Construction du résultat avec strict masquage pour les tests cachés
    if (!isPublic) {
      return {
        name: testName,
        is_public: false,
        passed,
        cmd: '[Protégé]',
        expected: '[Protégé]',
        actual: passed ? '[Protégé]' : 'Échec',
        assertion_type: '[Protégé]'
      };
    }

    return {
      name: testName,
      is_public: true,
      passed,
      cmd: test.cmd || '',
      expected: expectedDisplay,
      actual: actualDisplay,
      assertion_type: assertionType,
      exit_code: effectiveExitCode
    };
  }
}
