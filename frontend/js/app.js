/**

 * Contrôleur Principal de l'Application Frontend (Vanilla JS)

 * Gère le routage des vues, l'authentification, le tableau de bord étudiant enrichi,

 * les statistiques complètes de performance, le centre d'évaluation et tests de niveau multi-modules,

 * et le déroulement unifié des examens (1 question / page avec touches fléchées).

 */



import { api } from './api.js';

import { AntiCheatManager } from './anticheat.js';

import { ExamRunner } from './exam-runner.js';

import { LinuxRunner } from './linux/linux-runner.js';



class AppController {

  constructor() {

    this.currentView = null;

    this.currentUser = null;

    this.activeExamRunner = null;

    this.activeAntiCheat = null;

    this.lastStudentStats = null;

    this.linuxRunner = null;

    window.activeAppController = this;

  }



  async init() {

    window.app = this;

    window.showToast = (msg, type = 'info', dur = 4000) => this.showToast(msg, type, dur);

    window.customConfirm = (opts) => this.showConfirmModal(opts);

    window.customAlert = (opts) => this.showAlertModal(opts);

    this.linuxRunner = new LinuxRunner({ app: this, api });



    // Remplacement des alerts natifs par des notifications toast modernes ou modales personnalisées

    window.alert = (msg) => {

      let type = 'info';

      const text = String(msg || '');

      if (text.includes('✅') || text.toLowerCase().includes('succès') || text.toLowerCase().includes('félicitations') || text.toLowerCase().includes('enregistré')) {

        type = 'success';

      } else if (text.includes('⚠️') || text.toLowerCase().includes('attention') || text.toLowerCase().includes('avertissement')) {

        type = 'warning';

      } else if (text.includes('❌') || text.toLowerCase().includes('erreur') || text.toLowerCase().includes('invalide') || text.toLowerCase().includes('impossible') || text.toLowerCase().includes('échoué')) {

        type = 'danger';

      }

      this.showToast(text, type);

    };



    this.initTheme();

    this._attachGlobalListeners();



    // Vérifier si une session est déjà active

    if (api.token && api.user) {

      try {

        const user = await api.getMe();

        this.currentUser = user;

        this.renderDashboard(user);

      } catch (_) {

        this.renderLogin();

      }

    } else {

      this.renderLogin();

    }

  }



  // --- Gestion du Thème (Clair / Sombre) ---

  initTheme() {

    const savedTheme = localStorage.getItem('exam_theme') || 'dark';

    this.setTheme(savedTheme);



    const toggleBtn = document.getElementById('btn-theme-toggle');

    if (toggleBtn) {

      toggleBtn.onclick = () => {

        const cur = document.documentElement.getAttribute('data-theme') || 'dark';

        const next = cur === 'dark' ? 'light' : 'dark';

        this.setTheme(next);

      };

    }

  }



  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('exam_theme', theme);
    const icon = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');
    if (icon) icon.textContent = theme === 'dark' ? '🌙' : '☀️';
    if (label) label.textContent = theme === 'dark' ? 'Mode Sombre' : 'Mode Clair';

    // Synchroniser CodeMirror si une session est active
    try {
      const cmTheme = theme === 'light' ? 'default' : 'dracula';
      if (window.examRunner && window.examRunner._cmInstance) {
        window.examRunner._cmInstance.setOption('theme', cmTheme);
      }
      document.querySelectorAll('.CodeMirror').forEach(el => {
        if (el.CodeMirror) {
          el.CodeMirror.setOption('theme', cmTheme);
        }
      });
    } catch (_) {}
  }



  _attachGlobalListeners() {

    this.initPythonGeneratorModal();

    this.initClearExamsHandler();

    this.initLevelTestRenameHandlers();

    // Déconnexion

    const logoutBtn = document.getElementById('btn-logout');

    if (logoutBtn) {

      logoutBtn.onclick = () => {

        if (this.waitingRoomInterval) {

          clearInterval(this.waitingRoomInterval);

          this.waitingRoomInterval = null;

        }

        this._cleanupProctorSession();

        if (this.activeExamRunner) {

          this.activeExamRunner.stop();

          this.activeExamRunner = null;

        }

        if (this.activeAntiCheat) {

          this.activeAntiCheat.stop();

          this.activeAntiCheat = null;

        }

        api.clearSession();

        this.currentUser = null;

        this.renderLogin();

      };

    }



    // Soumission Formulaire Login

    const loginForm = document.getElementById('form-login');

    if (loginForm) {

      loginForm.onsubmit = async (e) => {

        e.preventDefault();

        const usernameInput = document.getElementById('input-username');

        const passwordInput = document.getElementById('input-password');

        const errorBox = document.getElementById('login-error');



        try {

          if (errorBox) {

            errorBox.style.display = 'none';

            errorBox.textContent = '';

          }

          const authData = await api.login(usernameInput.value.trim(), passwordInput.value);

          this.currentUser = authData.user;



          if (authData.must_change_password) {

            this.showToast("Première connexion détectée : Pensez à mettre à jour votre mot de passe.", "info");

          }



          this.renderDashboard(authData.user);

        } catch (err) {

          if (errorBox) {

            let msg = err.message || "Identifiant ou mot de passe incorrect.";

            msg = msg.replace(/^Erreur HTTP \d+:\s*/i, '');

            errorBox.innerHTML = `⚠️ <strong>Identifiants invalides :</strong> ${this._escapeHtml(msg)}`;

            errorBox.style.display = 'block';

            passwordInput.focus();

            if (passwordInput.select) passwordInput.select();

          }

        }

      };

    }



    // Navigation Statistiques

    const btnOpenStats = document.getElementById('btn-open-full-stats');

    if (btnOpenStats) {

      btnOpenStats.onclick = () => this.renderStatisticsView();

    }



    const btnStatsBack = document.getElementById('btn-stats-back-dash');

    if (btnStatsBack) {

      btnStatsBack.onclick = () => this.renderDashboard(this.currentUser);

    }



    const btnScoreBack = document.getElementById('btn-score-back-dashboard');

    if (btnScoreBack) {

      btnScoreBack.onclick = () => {

        if (this.activeOriginView === 'view-python') {

          this.renderTrainingCenterView();

        } else {

          this.renderDashboard(this.currentUser);

        }

      };

    }



    const btnScoreStats = document.getElementById('btn-score-view-stats');

    if (btnScoreStats) {

      btnScoreStats.onclick = () => this.renderStatisticsView();

    }



    // Modal & Chargement des Modèles d'Examen (REV-13)

    const btnLoadTpl = document.getElementById('btn-load-template-modal');

    if (btnLoadTpl) {

      btnLoadTpl.onclick = () => this.openExamTemplateModal();

    }



    // Modal Création d'Examen Sur-Mesure (REV-31)

    const btnOpenCustomExam = document.getElementById('btn-open-create-exam-modal');

    const modalCustomExam = document.getElementById('modal-create-custom-exam');

    const formCustomExam = document.getElementById('form-create-custom-exam');



    if (btnOpenCustomExam && modalCustomExam) {

      btnOpenCustomExam.onclick = async () => {

        try {

          const modules = await api.listAdminModules();

          const selectModule = document.getElementById('create-exam-module');

          if (selectModule && Array.isArray(modules) && modules.length > 0) {

            selectModule.innerHTML = modules.map(m => `

              <option value="${m.code}">${m.code} (${m.title})</option>

            `).join('');

          }

        } catch (_) {}

                  const selectModule = document.getElementById('create-exam-module');

          const selectType = document.getElementById('create-exam-type');

          const updateTypeOpts = () => {

            const m = selectModule?.value || '';

            const isPy = m.includes('PYTHON');

            if (selectType) {

              const optPrac = selectType.querySelector('option[value="practical"]');

              if (optPrac) {

                optPrac.disabled = !isPy;

                if (!isPy && selectType.value === 'practical') {

                  selectType.value = 'theoretical';

                }

              }

            }

          };

          if (selectModule) {

            selectModule.onchange = updateTypeOpts;

            updateTypeOpts();

          }



        modalCustomExam.classList.add('active');

      };

    }



    if (formCustomExam) {

      formCustomExam.onsubmit = async (e) => {

        e.preventDefault();

        const title = document.getElementById('create-exam-title')?.value.trim();

        const module_code = document.getElementById('create-exam-module')?.value;

        const exam_type = document.getElementById('create-exam-type')?.value || 'theoretical';

        const duration_minutes = parseInt(document.getElementById('create-exam-duration')?.value, 10) || 45;

        const global_points = parseFloat(document.getElementById('create-exam-max-score')?.value) || 20.0;

        const room_id = document.getElementById('create-exam-room')?.value.trim() || 'SALLE-TP-1';

        const instructions = document.getElementById('create-exam-desc')?.value.trim();

        const shuffle_questions = !!document.getElementById('create-exam-shuffle-questions')?.checked;

        const shuffle_options = !!document.getElementById('create-exam-shuffle-options')?.checked;



        const targetGroups = [];

        document.querySelectorAll('.cb-target-group:checked').forEach(cb => {

          targetGroups.push(cb.value);

        });



        const submitBtn = document.getElementById('btn-submit-create-custom-exam');

        if (submitBtn) {

          submitBtn.disabled = true;

          submitBtn.textContent = "⏳ Création en cours...";

        }



        try {

          const res = await api.createCustomExam({

            title,

            module_code,

            exam_type,

            duration_minutes,

            global_points,

            room_id,

            instructions,

            group_ids: targetGroups,

            shuffle_questions,

            shuffle_options

          });



          this.showToast(`✅ Épreuve ${exam_type === 'practical' ? 'pratique' : 'théorique'} "${res.title}" créée avec succès (${res.question_count} questions) ! Salle ${room_id} prête.`, 'success');

          this.closeModal('modal-create-custom-exam');

          formCustomExam.reset();

          await this.renderTeacherView();

          // Ouvrir directement l'atelier de gestion et d'édition des questions

          await this.openManageQuestionsModal(res.id, res.title);

        } catch (err) {

          this.showToast(`Erreur de création d'examen : ${err.message}`, 'danger');

        } finally {

          if (submitBtn) {

            submitBtn.disabled = false;

            submitBtn.textContent = "🚀 Enregistrer et Publier l'Épreuve";

          }

        }

      };

    }



    // Import direct d'un fichier examen JSON (REV-13)

    const inputImportExam = document.getElementById('input-import-exam-file');

    if (inputImportExam) {

      inputImportExam.onchange = async (e) => {

        const file = e.target.files && e.target.files[0];

        if (!file) return;

        try {

          const text = await file.text();

          const payload = JSON.parse(text);

          const res = await api.importExamTemplate(payload);

          this.showToast(`Examen "${res.title}" importé avec succès (${res.question_count} questions). Il est prêt pour la surveillance.`, "success");

          this.renderTeacherView();

        } catch (err) {

          this.showToast(`Erreur d'importation de l'examen JSON : ${err.message}`, "danger");

        } finally {

          inputImportExam.value = '';

        }

      };

    }



    // Import Package d'Examen .exam.zip (Transfert USB Phase 5)

    const inputImportPackage = document.getElementById('input-import-exam-package-file');

    if (inputImportPackage) {

      inputImportPackage.onchange = async (e) => {

        const file = e.target.files && e.target.files[0];

        if (!file) return;

        try {

          const res = await api.importExamPackage(file);

          this.showToast(res.message || "Package d'examen importé avec succès !", "success");

          await this.renderTeacherView();

        } catch (err) {

          this.showToast(`Erreur d'importation du package : ${err.message}`, "danger");

        } finally {

          inputImportPackage.value = '';

        }

      };

    }



    // Proctoring : Exportation de l'archive de résultats .results.zip

    const btnProctorExportZip = document.getElementById('btn-proctor-export-results-zip');

    if (btnProctorExportZip) {

      btnProctorExportZip.onclick = async () => {

        const sid = this.currentProctorSessionId || this.activeSessionId;

        if (!sid) return this.showToast("Aucune session active sélectionnée.", "warning");

        try {

          await api.exportSessionResultsZip(sid);

        } catch (err) {

          this.showToast(`Erreur d'exportation de l'archive de résultats : ${err.message}`, "danger");

        }

      };

    }



    // Proctoring : Analyse Psychométrique de la session en direct

    const btnProctorItemAnalysis = document.getElementById('btn-proctor-item-analysis');

    if (btnProctorItemAnalysis) {

      btnProctorItemAnalysis.onclick = () => {

        const sid = this.currentProctorSessionId || this.activeSessionId;

        if (!sid) return this.showToast("Aucune session active sélectionnée.", "warning");

        this.openSessionItemAnalysisModal(sid);

      };

    }



    // Admin Multi-Salles : Importation Archive .results.zip

    const btnTriggerImportZip = document.getElementById('btn-admin-trigger-import-zip');

    const inputAdminZip = document.getElementById('input-admin-results-zip-file');

    if (btnTriggerImportZip && inputAdminZip) {

      btnTriggerImportZip.onclick = () => inputAdminZip.click();

      inputAdminZip.onchange = async (e) => {

        const file = e.target.files && e.target.files[0];

        if (!file) return;

        try {

          const res = await api.importResultsZip(file);

          this.showToast(res.message || "Archive de résultats réconciliée avec succès !", "success");

          await this.loadAdminOverview();

          await this.loadAdminResults();

        } catch (err) {

          this.showToast(`Erreur lors de la réconciliation de l'archive : ${err.message}`, "danger");

        } finally {

          inputAdminZip.value = '';

        }

      };

    }



    // Admin Multi-Salles : Téléchargement Notes Consolidées

    const btnAdminGradebook = document.getElementById('btn-admin-download-consolidated-gradebook');

    if (btnAdminGradebook) {

      btnAdminGradebook.onclick = async () => {

        try {

          await api.downloadConsolidatedGradebook();

        } catch (err) {

          this.showToast(`Erreur de téléchargement : ${err.message}`, "danger");

        }

      };

    }



    // Export CSV Analyse Psychométrique

    const btnExportAnalysisCsv = document.getElementById('btn-export-item-analysis-csv');

    if (btnExportAnalysisCsv) {

      btnExportAnalysisCsv.onclick = async () => {

        if (!this._currentAnalysisExamId) return;

        try {

          if (this._currentAnalysisSessionId) {

            await api.downloadSessionItemAnalysisCsv(this._currentAnalysisSessionId);

          } else {

            await api.downloadItemAnalysisCsv(this._currentAnalysisExamId);

          }

        } catch (err) {

          this.showToast(`Erreur d'exportation CSV : ${err.message}`, "danger");

        }

      };

    }



    // Gestionnaire de Questions : Ajout / Import / Export

    const btnAddNewQ = document.getElementById('btn-add-new-question');

    if (btnAddNewQ) {

      btnAddNewQ.onclick = () => {

        if (!this._currentManageExamId) return;

        this.openEditQuestionModal(this._currentManageExamId, null);

      };

    }



    const btnTriggerImportQ = document.getElementById('btn-trigger-import-questions-json');

    const inputImportQ = document.getElementById('input-import-questions-json');

    if (btnTriggerImportQ && inputImportQ) {

      btnTriggerImportQ.onclick = () => inputImportQ.click();

      inputImportQ.onchange = async (e) => {

        const file = e.target.files && e.target.files[0];

        if (!file) return;

        try {

          const text = await file.text();

          const payload = JSON.parse(text);

          if (!Array.isArray(payload)) throw new Error("Le fichier JSON doit contenir une liste de questions.");

          const res = await api.importQuestionsJson(this._currentManageExamId, payload);

          this.showToast(res.message || "Questions importées avec succès.", "success");

          await this.openManageQuestionsModal(this._currentManageExamId, this._currentManageExamTitle);

          if (this.currentUser && this.currentUser.role === 'admin') {

            await this.loadAdminExams();

          } else {

            await this.renderTeacherView();

          }

        } catch (err) {

          this.showToast(`Erreur d'importation JSON : ${err.message}`, "danger");

        } finally {

          inputImportQ.value = '';

        }

      };

    }



    const btnExportQ = document.getElementById('btn-export-questions-json');

    if (btnExportQ) {

      btnExportQ.onclick = async () => {

        if (!this._currentManageExamId) return;

        try {

          const data = await api.exportQuestionsJson(this._currentManageExamId);

          const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });

          const url = window.URL.createObjectURL(blob);

          const a = document.createElement('a');

          a.href = url;

          a.download = `questions_examen_${this._currentManageExamId}.json`;

          document.body.appendChild(a);

          a.click();

          window.URL.revokeObjectURL(url);

          a.remove();

        } catch (err) {

          this.showToast(`Erreur d'exportation : ${err.message}`, "danger");

        }

      };

    }



    // Sélecteur de type de question dans le modal d'édition

    const selectQType = document.getElementById('edit-question-type');

    if (selectQType) {

      selectQType.onchange = () => {

        this._renderDynamicQuestionOptionsForm(selectQType.value);

      };

    }



    // Soumission du Formulaire d'Édition de Question

    const formEditQ = document.getElementById('form-edit-question');

    if (formEditQ) {

      formEditQ.onsubmit = async (e) => {

        e.preventDefault();

        const examId = document.getElementById('edit-question-exam-id')?.value;

        const qId = document.getElementById('edit-question-id')?.value;

        const type = document.getElementById('edit-question-type')?.value;

        const ordering = parseInt(document.getElementById('edit-question-ordering')?.value, 10) || 1;

        const prompt_markdown = document.getElementById('edit-question-prompt')?.value.trim();

        const points = parseFloat(document.getElementById('edit-question-points')?.value) || 2.0;

        const negative_penalty = parseFloat(document.getElementById('edit-question-penalty')?.value) || 0.0;



        // Extraction des options et réponses correctes selon le type

        let options_json, correct_answers_json;

        try {

          const extracted = this._extractOptionsAndAnswersFromForm(type);

          options_json = extracted.options_json;

          correct_answers_json = extracted.correct_answers_json;

        } catch (err) {

          this.showToast(`Saisie incomplète : ${err.message}`, "warning");

          return;

        }



        const payload = {

          ordering,

          type,

          prompt_markdown,

          points,

          negative_penalty,

          options_json,

          correct_answers_json

        };



        try {

          if (qId) {

            await api.updateQuestion(examId, qId, payload);

            this.showToast("Question mise à jour avec succès.", "success");

          } else {

            await api.createQuestion(examId, payload);

            this.showToast("Nouvelle question ajoutée avec succès.", "success");

          }

          this.closeModal('modal-edit-question');

          await this.openManageQuestionsModal(examId, this._currentManageExamTitle);

          if (this.currentUser && this.currentUser.role === 'admin') {

            await this.loadAdminExams();

          } else {

            await this.renderTeacherView();

          }

        } catch (err) {

          this.showToast(`Erreur lors de l'enregistrement de la question : ${err.message}`, "danger");

        }

      };

    }



    // Fermeture générique des modales (Bouton, Échap, Clic Backdrop)

    document.querySelectorAll('.modal-close-btn').forEach(btn => {

      btn.onclick = () => {

        const target = btn.getAttribute('data-target');

        if (target) this.closeModal(target);

      };

    });



    // Fermeture par clic sur l'arrière-plan (backdrop)

    document.querySelectorAll('.modal-overlay, .modal-backdrop').forEach(overlay => {

      overlay.addEventListener('click', (e) => {

        if (e.target === overlay) {

          this.closeActiveModal();

        }

      });

    });



    // Écouteur délégué sur document pour toute modale active ou dynamique

    document.addEventListener('click', (e) => {

      if (e.target && (e.target.classList.contains('modal-overlay') || e.target.classList.contains('modal-backdrop'))) {

        this.closeActiveModal();

      }

    });



    // Fermeture globale par appui sur la touche Échap (Escape)

    document.addEventListener('keydown', (e) => {

      if (e.key === 'Escape' || e.key === 'Esc') {

        // 1. Si le panneau d'autocomplétion CodeMirror est affiché, le fermer en priorité

        const hints = document.querySelector('.CodeMirror-hints-container, .CodeMirror-hints');

        if (hints) {

          hints.remove();

          if (window.activeExamRunner && window.activeExamRunner._cmInstance && window.activeExamRunner._cmInstance.state && window.activeExamRunner._cmInstance.state.completionActive) {

            try { window.activeExamRunner._cmInstance.state.completionActive.close(); } catch (_) {}

          }

          e.preventDefault();

          e.stopPropagation();

          return;

        }



        // 2. Pendant une épreuve pratique ou un exercice de code, désactiver Échap pour la sortie plein écran

        const isExamActive = window.activeExamRunner && !window.activeExamRunner.isPracticeMode;

        const isCodingActive = document.querySelector('.challenge-layout') || document.querySelector('.exam-layout.coding-mode');

        if (isCodingActive) {

          // La touche Échap sert uniquement au code/autocomplétion, pas à quitter le plein écran

          e.preventDefault();

          e.stopPropagation();

          return;

        }



        this.closeActiveModal();

      }

    });



    // Navigation Centre Python Dédié

    const btnOpenTraining = document.getElementById('btn-open-training-center');

    if (btnOpenTraining) {

      btnOpenTraining.onclick = () => this.renderTrainingCenterView();

    }



    // Navigation Épreuves Officielles Dédiées

    const btnOpenDedExams = document.getElementById('btn-open-dedicated-exams');

    if (btnOpenDedExams) {

      btnOpenDedExams.onclick = () => this.renderOfficialExamsView();

    }

    const btnExamsBack = document.getElementById('btn-exams-back-dash');

    if (btnExamsBack) {

      btnExamsBack.onclick = () => this.renderDashboard(this.currentUser);

    }

    const btnOpenStudentStats = document.getElementById('btn-open-student-stats');

    if (btnOpenStudentStats) {

      btnOpenStudentStats.onclick = () => this.renderStatisticsView();

    }

    const btnCloseExamReview = document.getElementById('btn-close-exam-review');

    if (btnCloseExamReview) {

      btnCloseExamReview.onclick = () => this.closeModal('modal-exam-review');

    }

    const btnDoneExamReview = document.getElementById('btn-done-exam-review');

    if (btnDoneExamReview) {

      btnDoneExamReview.onclick = () => this.closeModal('modal-exam-review');

    }



    const btnOpenStudentBulletin = document.getElementById('btn-open-student-bulletin');

    if (btnOpenStudentBulletin) {

      btnOpenStudentBulletin.onclick = () => {

        if (this.currentUser && this.currentUser.id) {

          this.openStudentBulletinModal(this.currentUser.id);

        }

      };

    }



    const btnOpenDedicatedPython = document.getElementById('btn-open-dedicated-python-training');

    if (btnOpenDedicatedPython) {

      btnOpenDedicatedPython.onclick = () => this.renderTrainingCenterView();

    }



    // Navigation Centre Linux Dédié

    const btnOpenLinuxCenter = document.getElementById('btn-open-linux-center');

    if (btnOpenLinuxCenter) {

      btnOpenLinuxCenter.onclick = () => this.renderLinuxTrainingCenter();

    }



    const btnOpenDedicatedLinux = document.getElementById('btn-open-dedicated-linux-training');

    if (btnOpenDedicatedLinux) {

      btnOpenDedicatedLinux.onclick = () => this.renderLinuxTrainingCenter();

    }



    // Modal Historique des Tests de Niveau

    const btnOpenPracticeHist = document.getElementById('btn-open-practice-history');

    if (btnOpenPracticeHist) {

      btnOpenPracticeHist.onclick = () => this.openPracticeHistoryModal();

    }

    const btnClosePracticeHist = document.getElementById('btn-close-practice-history');

    if (btnClosePracticeHist) {

      btnClosePracticeHist.onclick = () => this.closeModal('modal-practice-history');

    }

    const btnPracticeHistDone = document.getElementById('btn-practice-history-done');

    if (btnPracticeHistDone) {

      btnPracticeHistDone.onclick = () => this.closeModal('modal-practice-history');

    }



    // Modal Galerie des 68 Badges

    const btnOpenBadges = document.getElementById('btn-open-badges-gallery');

    if (btnOpenBadges) {

      btnOpenBadges.onclick = () => this.openBadgesGalleryModal();

    }

    const btnCloseBadges = document.getElementById('btn-close-badges-gallery');

    if (btnCloseBadges) {

      btnCloseBadges.onclick = () => this.closeModal('modal-badges-gallery');

    }

    const btnBadgesDone = document.getElementById('btn-badges-gallery-done');

    if (btnBadgesDone) {

      btnBadgesDone.onclick = () => this.closeModal('modal-badges-gallery');

    }



    // Modal Historique des Entraînements Python

    const btnOpenPyHist = document.getElementById('btn-open-python-history');

    if (btnOpenPyHist) {

      btnOpenPyHist.onclick = () => this.openPythonHistoryModal();

    }

    const btnClosePyHist = document.getElementById('btn-close-python-history');

    if (btnClosePyHist) {

      btnClosePyHist.onclick = () => this.closeModal('modal-python-history');

    }

    const btnPyHistDone = document.getElementById('btn-python-history-done');

    if (btnPyHistDone) {

      btnPyHistDone.onclick = () => this.closeModal('modal-python-history');

    }



    // Lancement de l'épreuve active Cursus Python

    const btnStartCurriculum = document.getElementById('btn-start-curriculum-training');

    if (btnStartCurriculum) {

      btnStartCurriculum.onclick = () => this.launchSelectedTraining();

    }



    // Filtres galerie de badges

    document.querySelectorAll('.btn-badge-filter').forEach(btn => {

      btn.onclick = () => {

        document.querySelectorAll('.btn-badge-filter').forEach(b => b.classList.remove('active'));

        btn.classList.add('active');

        this.filterBadgesGallery(btn.dataset.filter);

      };

    });



    // Bascule Mode Plein Écran

    const btnFs = document.getElementById('btn-toggle-fullscreen');

    if (btnFs) {

      btnFs.onclick = () => this.toggleFullscreen();

    }

    document.addEventListener('fullscreenchange', () => {

      this._updateFullscreenButtonText();

      this._handleWaitingRoomFullscreenChange();

    });

    document.addEventListener('webkitfullscreenchange', () => {

      this._updateFullscreenButtonText();

      this._handleWaitingRoomFullscreenChange();

    });



    // Navigation Centre Python Retour

    const btnPythonBack = document.getElementById('btn-python-back-dash');

    if (btnPythonBack) {

      btnPythonBack.onclick = () => this.renderDashboard(this.currentUser);

    }



    // Initialisation globale du contrôleur de taille de police d'examen

    this._initGlobalExamFontScale();



    // Alertes réseau déconnecté / reconnecté (avec affichage spécifique plein écran en examen)

    const showOfflineBanners = () => {

      const banner = document.getElementById('banner-offline');

      if (banner) banner.classList.add('active');

      const examBanner = document.getElementById('exam-banner-offline');

      if (examBanner) examBanner.style.display = 'block';

    };



    const hideOfflineBanners = () => {

      const banner = document.getElementById('banner-offline');

      if (banner) banner.classList.remove('active');

      const examBanner = document.getElementById('exam-banner-offline');

      if (examBanner) examBanner.style.display = 'none';

      api.flushOfflineQueue();

    };



    window.addEventListener('network:offline', showOfflineBanners);

    window.addEventListener('offline', showOfflineBanners);

    window.addEventListener('online', hideOfflineBanners);



    window.addEventListener('auth:expired', () => {

      if (this.currentView && this.currentView !== 'view-login') {

        this.showToast("Votre session a expiré. Veuillez vous reconnecter.", "warning");

      }

      this.renderLogin();

    });

  }



  switchView(viewId) {

    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

    const target = document.getElementById(viewId);

    if (target) {

      target.classList.add('active');

      this.currentView = viewId;

      window.scrollTo(0, 0);

    }



    const nav = document.getElementById('app-role-nav');

    const btnLogout = document.getElementById('btn-logout');

    const headerUserInfo = document.getElementById('header-user-info');



    // Arrêt immédiat et nettoyage de l'anti-triche dès qu'on quitte l'écran d'épreuve (REV-12)

    if (viewId !== 'view-exam') {

      if (this.activeAntiCheat) {

        this.activeAntiCheat.stop();

        this.activeAntiCheat = null;

      }

      this.hideSuspensionScreen();

    }

    if (viewId !== 'view-proctor-live') {
      this._cleanupProctorSession();
    }



    // Réinitialisation des filtres de flou et modales de plein écran hors épreuve et salle d'attente

    if (viewId !== 'view-waiting-room' && viewId !== 'view-exam') {

      const waitingView = document.getElementById('view-waiting-room');

      if (waitingView) waitingView.classList.remove('exam-fullscreen-lost-blurred');

      const overlayFs = document.getElementById('overlay-fullscreen-required');

      if (overlayFs) overlayFs.classList.remove('active');

    }



    if (viewId === 'view-exam' || viewId === 'view-waiting-room') {

      // Pendant une épreuve (Officielle ou Test de Niveau) ou en salle d'attente : masquer la barre de navigation et le bouton de déconnexion

      if (nav) nav.style.display = 'none';

      if (btnLogout) btnLogout.style.display = 'none';

    } else if (viewId === 'view-login') {

      if (nav) nav.style.display = 'none';

      if (headerUserInfo) headerUserInfo.style.display = 'none';

    } else {

      // Écrans Tableau de Bord, Statistiques, Centre de Niveau, Score, etc.

      if (this.currentUser) {

        if (nav) nav.style.display = 'flex';

        if (headerUserInfo) headerUserInfo.style.display = 'flex';

        if (btnLogout) btnLogout.style.display = 'inline-block';

      }

    }

  }



  // --- Rendu de la Barre de Navigation selon le Rôle ---

  _renderRoleNav(user) {

    const nav = document.getElementById('app-role-nav');

    if (!nav) return;



    if (!user) {

      nav.style.display = 'none';

      nav.innerHTML = '';

      return;

    }



    nav.style.display = 'flex';

    nav.innerHTML = '';



    if (user.role === 'student') {
      const links = [
        { id: 'nav-dash', label: '🏠 Tableau de Bord', action: () => this.renderDashboard(user) },
        { id: 'nav-official-exams', label: '📝 Épreuves Officielles', action: () => this.renderOfficialExamsView() },
        { id: 'nav-training-hub', label: '🎓 Centres d\'Entraînement', action: () => this.renderTrainingHubView() }
      ];



      links.forEach(l => {

        const btn = document.createElement('button');

        btn.className = `role-nav-btn ${l.id === 'nav-dash' ? 'active' : ''}`;

        btn.id = l.id;

        btn.textContent = l.label;

        btn.onclick = () => {

          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

          btn.classList.add('active');

          l.action();

        };

        nav.appendChild(btn);

      });

    } else if (user.role === 'teacher') {

      nav.innerHTML = `

        <button class="role-nav-btn active" id="nav-teacher-surveillance">🖥️ Espace Enseignant & Examens</button>

        <button class="role-nav-btn" id="nav-teacher-bulletins">📑 PV par Spécialité & Module</button>

      `;

      const teacherBtn = document.getElementById('nav-teacher-surveillance');

      if (teacherBtn) {

        teacherBtn.onclick = () => {

          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

          teacherBtn.classList.add('active');

          this.renderTeacherView();

        };

      }

      const teacherBullBtn = document.getElementById('nav-teacher-bulletins');

      if (teacherBullBtn) {

        teacherBullBtn.onclick = () => {

          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

          teacherBullBtn.classList.add('active');

          this.renderClassSheetView();

        };

      }

    } else if (user.role === 'admin') {

      nav.innerHTML = `

        <button class="role-nav-btn active" id="nav-admin-console">⚙️ Console Administrateur</button>

        <button class="role-nav-btn" id="nav-admin-exams">🖥️ Surveillance & Gestion des Examens</button>

        <button class="role-nav-btn" id="nav-admin-bulletins">📑 PV par Spécialité & Module</button>

      `;

      const adminBtn = document.getElementById('nav-admin-console');

      if (adminBtn) {

        adminBtn.onclick = () => {

          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

          adminBtn.classList.add('active');

          this.renderAdminView();

        };

      }

      const adminExamsBtn = document.getElementById('nav-admin-exams');

      if (adminExamsBtn) {

        adminExamsBtn.onclick = () => {

          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

          adminExamsBtn.classList.add('active');

          this.renderTeacherView();

        };

      }

      const adminBullBtn = document.getElementById('nav-admin-bulletins');

      if (adminBullBtn) {

        adminBullBtn.onclick = () => {

          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

          adminBullBtn.classList.add('active');

          this.renderClassSheetView();

        };

      }

    }

  }



  // --- Vue : Connexion ---

  renderLogin() {

    const headerInfo = document.getElementById('header-user-info');

    if (headerInfo) headerInfo.style.display = 'none';

    this._renderRoleNav(null);

    const errorBox = document.getElementById('login-error');

    if (errorBox) {

      errorBox.style.display = 'none';

      errorBox.textContent = '';

    }

    this.switchView('view-login');

  }



  // --- Vue : Tableau de Bord ---

  async renderDashboard(user) {

    this.currentUser = user;

    document.getElementById('header-user-info').style.display = 'flex';

    document.getElementById('header-user-name').textContent = user.full_name;

    document.getElementById('header-user-group').textContent = user.group_id ? `Groupe : ${user.group_id}` : (user.role === 'admin' ? 'Super Admin' : 'Enseignant');



    this._renderRoleNav(user);



    // Routage selon le rôle

    if (user.role === 'student') {

      this.switchView('view-dashboard');

      document.getElementById('student-hero-banner').style.display = 'flex';

      document.getElementById('box-btn-view-stats').style.display = 'flex';



      // 1. Charger les statistiques et le niveau global

      await this._loadStudentStatistics();

      // 2. Charger la synthèse des 4 piliers fondamentaux avec niveaux individuels

      await this._loadPillarsSummary();

      // 3. Charger les examens officiels

      await this._loadOfficialExams();

      // 4. Charger les tests de niveau par module (cartes épurées)

      await this._loadPracticeModules();



    } else if (user.role === 'teacher') {

      this.renderTeacherView();

    } else if (user.role === 'admin') {

      this.renderAdminView();

    }

  }



  // --- Chargement des Statistiques Étudiant Synthétiques (Dashboard) ---

  async _loadStudentStatistics() {

    try {

      const stats = await api.getStudentStatistics();

      this.lastStudentStats = stats;



      // Bienvenue & Niveau Global

      const welcomeEl = document.getElementById('dash-student-welcome');

      if (welcomeEl) welcomeEl.textContent = `Bonjour, ${stats.student_name}`;



      const levelBadge = document.getElementById('dash-level-badge');

      const levelText = document.getElementById('dash-level-text');

      const fundAvgText = document.getElementById('dash-fund-avg-text');

      const levelBar = document.getElementById('dash-level-bar');



      if (levelText) {

        levelText.textContent = `Niveau ${stats.global_level} — ${stats.global_level_title}`;

      }

      if (fundAvgText) {

        fundAvgText.textContent = `Moyenne Tests de Niveau : ${stats.fundamental_average.toFixed(2)} / 20`;

      }

      if (levelBadge) {
        levelBadge.className = 'level-badge-large';
        const glTitle = (stats.global_level_title || '').toLowerCase();
        if (stats.global_level <= 1 || glTitle.includes('insuffisant')) {
          levelBadge.classList.add('level-badge-insufficient');
        } else if (stats.global_level <= 2 || glTitle.includes('sous la moyenne')) {
          levelBadge.classList.add('level-badge-warning');
        } else if (stats.global_level >= 5) {
          levelBadge.classList.add('level-badge-expert');
        } else if (stats.global_level >= 3) {
          levelBadge.classList.add('level-badge-advanced');
        }
      }

      if (levelBar) {

        const percent = Math.min(100, Math.max(10, (stats.global_level / 8) * 100));

        levelBar.style.width = `${percent}%`;

      }



      // Remplissage des 4 KPI Cards

      const kpiFund = document.getElementById('dash-kpi-fund-avg');

      const kpiOverall = document.getElementById('dash-kpi-overall-avg');

      const kpiSuccess = document.getElementById('dash-kpi-success-rate');

      const kpiValid = document.getElementById('dash-kpi-validated-count');



      if (kpiFund) kpiFund.textContent = `${stats.fundamental_average.toFixed(1)}/20`;

      if (kpiOverall) kpiOverall.textContent = `${stats.overall_average.toFixed(1)}/20`;

      if (kpiSuccess) kpiSuccess.textContent = `${stats.success_rate_percent}%`;

      if (kpiValid) kpiValid.textContent = `${stats.validated_modules_count}/${stats.total_modules_count}`;



    } catch (err) {

      console.warn("Impossible de charger les statistiques étudiant :", err);

    }

  }



  // --- Chargement des Examens Officiels (Vue en Liste Triée : non passés d'abord, terminés à la fin) ---

  async _loadOfficialExams(targetContainerId = 'official-exams-grid') {

    const container = document.getElementById(targetContainerId);

    if (!container) return;



    try {

      const exams = await api.getAvailableExams();

      if (!exams.length) {

        container.innerHTML = `

          <div style="text-align:center; padding:36px; color:var(--text-secondary); background:var(--bg-surface); border-radius:var(--radius-md); border:1px solid var(--card-border);">

            Aucun examen officiel programmé pour votre groupe actuellement.

          </div>

        `;

        return;

      }



      // Tri ordonné : Les épreuves non encore passées ou en cours en haut, les épreuves déjà terminées/soumises en bas

      exams.sort((a, b) => {

        const isSubA = a.attempt_status === 'submitted' || a.attempt_status === 'completed' || a.attempt_status === 'timed_out';

        const isSubB = b.attempt_status === 'submitted' || b.attempt_status === 'completed' || b.attempt_status === 'timed_out';

        if (isSubA !== isSubB) {

          return isSubA ? 1 : -1; // non-soumis en premier

        }

        const getPriority = (ex) => {

          if (ex.attempt_status === 'in_progress') return 1;

          if (ex.attempt_status === 'waiting') return 2;

          if (!ex.attempt_status) return 3;

          if (ex.attempt_status === 'suspended') return 4;

          return 5;

        };

        return getPriority(a) - getPriority(b);

      });



      container.innerHTML = '';

      exams.forEach(ex => {

        const row = document.createElement('div');

        row.className = 'exam-list-item card';

        row.style.cssText = 'padding: 16px 22px; border: 1px solid var(--card-border); border-radius: var(--radius-md); background: var(--bg-surface); display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; margin-bottom: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);';



        const isSubmitted = ex.attempt_status === 'submitted' || ex.attempt_status === 'completed' || ex.attempt_status === 'timed_out';

        const isProgress = ex.attempt_status === 'in_progress';

        const isWaiting = ex.attempt_status === 'waiting';

        const isSuspended = ex.attempt_status === 'suspended';

        const hasScore = ex.final_mark !== null && ex.final_mark !== undefined;



        let actionAreaHtml = '';

        let statusBadgeHtml = '';



        if (isSubmitted) {

          actionAreaHtml = `

            <div style="display:flex; flex-direction:column; gap:6px; min-width: 230px;">

              <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid var(--success); border-radius: var(--radius-md); padding: 8px 14px; text-align: center; color: var(--success); font-weight: 700; font-size: 0.9rem;">

                ✅ Épreuve Soumise ${hasScore ? `(${Number(ex.final_mark).toFixed(2)} / ${ex.global_points})` : ''}

              </div>

              ${ex.attempt_id ? `

                <button class="btn btn-sm" style="padding: 6px 12px; font-size: 0.82rem; font-weight: 700; border-radius: 6px; border: 1px solid rgba(59,130,246,0.4); color: #93c5fd; background: rgba(59,130,246,0.12); cursor: pointer; transition: all 0.2s ease;" id="btn-review-exam-${ex.exam_id}">

                  🔍 Consulter le Corrigé & Mes Erreurs

                </button>

              ` : ''}

            </div>

          `;

          statusBadgeHtml = `<span class="badge" style="background:rgba(16,185,129,0.2); color:#34d399; border:1px solid #10b981; font-size:11px; padding:3px 8px; border-radius:6px; font-weight:700;">✅ Soumis</span>`;

        } else if (isProgress) {

          actionAreaHtml = `

            <button class="btn btn-success" style="min-width:210px; padding:9px 18px; font-size:0.92rem; background:#059669; border-color:#047857; font-weight:700; box-shadow: 0 4px 14px rgba(5,150,105,0.35);" id="btn-start-exam-${ex.exam_id}">

              🔄 Rejoindre l'épreuve en cours ➔

            </button>

          `;

          statusBadgeHtml = `<span class="badge" style="background:#059669; color:#fff; font-size:11px; padding:3px 8px; border-radius:6px; font-weight:700;">● En cours</span>`;

        } else if (isWaiting) {

          actionAreaHtml = `

            <button class="btn" style="min-width:210px; padding:9px 18px; font-size:0.92rem; background:#d97706; color:#fff; border-color:#b45309; font-weight:700; box-shadow: 0 4px 14px rgba(217,119,6,0.35);" id="btn-start-exam-${ex.exam_id}">

              ⏳ Rejoindre la salle d'attente ➔

            </button>

          `;

          statusBadgeHtml = `<span class="badge" style="background:#d97706; color:#fff; font-size:11px; padding:3px 8px; border-radius:6px; font-weight:700;">⏳ Salle d'attente</span>`;

        } else if (isSuspended) {

          actionAreaHtml = `

            <button class="btn btn-danger" style="min-width:210px; padding:9px 18px; font-size:0.92rem; background:#dc2626; border-color:#b91c1c; font-weight:700; box-shadow: 0 4px 14px rgba(220,38,38,0.35);" id="btn-start-exam-${ex.exam_id}">

              🔒 Voir Statut Suspendu ➔

            </button>

          `;

          statusBadgeHtml = `<span class="badge" style="background:#dc2626; color:#fff; font-size:11px; padding:3px 8px; border-radius:6px; font-weight:700;">🔒 Suspendu</span>`;

        } else {

          actionAreaHtml = `

            <button class="btn btn-primary" style="min-width:210px; padding:9px 18px; font-size:0.92rem; font-weight:700;" id="btn-start-exam-${ex.exam_id}">

              Commencer l'épreuve ➔

            </button>

          `;

        }



        const typeBadge = ex.exam_type === 'practical'
          ? `<span class="badge badge-exam-type badge-practical" style="background:rgba(139,92,246,0.2); color:#c4b5fd; border:1px solid rgba(139,92,246,0.4); padding:3px 8px; border-radius:6px; font-size:11px; font-weight:600;">💻 Pratique</span>`
          : `<span class="badge badge-exam-type badge-theoretical" style="background:rgba(59,130,246,0.2); color:#93c5fd; border:1px solid rgba(59,130,246,0.4); padding:3px 8px; border-radius:6px; font-size:11px; font-weight:600;">📖 Théorique</span>`;

        const cleanTitle = (ex.title || '').replace(/^(?:Épreuve\s+Officielle|Examen\s+Officiel)\s*:\s*/i, '').trim();
        const cleanInstructions = (ex.instructions || '').replace(/\[CONFIG_RANDOM_STUDENT_QUESTIONS=\d+\]/gi, '').trim();

        row.innerHTML = `
          <div style="display:flex; align-items:flex-start; gap:16px; flex:1; min-width:280px;">
            <div style="font-size:1.7rem; line-height:1; padding:8px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid var(--card-border);">
              ${ex.exam_type === 'practical' ? '💻' : '📖'}
            </div>
            <div style="flex:1;">
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px; flex-wrap:wrap;">
                <span class="user-tag" style="font-size:11px; padding:2px 8px; font-weight:700;">${this._escapeHtml(ex.module_code)}</span>
                ${typeBadge}
                ${statusBadgeHtml}
              </div>
              <h4 style="margin:0 0 4px 0; font-size:1.1rem; color:var(--text-primary); font-weight:600;">${this._escapeHtml(cleanTitle)}</h4>
              <p style="margin:0; font-size:0.86rem; color:var(--text-secondary); line-height:1.4;">${this._escapeHtml(cleanInstructions || 'Épreuve officielle certifiante.')}</p>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap; justify-content:flex-end;">
            <div class="exam-meta" style="margin:0; display:flex; gap:14px; font-size:0.86rem; color:var(--text-secondary); white-space:nowrap;">
              <span>⏱️ <strong>${ex.duration_minutes}</strong> min</span>
              <span>📝 <strong>${ex.question_count}</strong> questions</span>
              <span>🎯 Barème <strong>/${ex.global_points}</strong></span>
            </div>
            <div style="text-align:right;">
              ${actionAreaHtml}
            </div>
          </div>
        `;



        const startBtn = row.querySelector(`#btn-start-exam-${ex.exam_id}`);

        if (startBtn) {

          startBtn.onclick = () => {

            this.launchOfficialExam(ex.exam_id);

          };

        }

        const reviewBtn = row.querySelector(`#btn-review-exam-${ex.exam_id}`);

        if (reviewBtn && ex.attempt_id) {

          reviewBtn.onclick = () => {

            this.openExamReviewModal(ex.attempt_id, ex.exam_id);

          };

        }



        container.appendChild(row);

      });

    } catch (err) {

      container.innerHTML = `<div style="color:var(--danger);">Erreur : ${err.message}</div>`;

    }

  }



  // --- Grille de Synthèse des 4 Piliers Fondamentaux (Niveaux par test & global) ---

  async _loadPillarsSummary() {

    const container = document.getElementById('dash-pillars-summary');

    if (!container) return;



    try {

      const data = await api.getPracticeHistory();

      if (!data || !data.pillars) return;



      container.innerHTML = '';



      const fundAvgText = document.getElementById('dash-fund-avg-text');

      if (fundAvgText) {

        fundAvgText.textContent = `Moyenne Tests de Niveau : ${data.overall_last_4_average.toFixed(2)} / 20`;

      }

      const kpiFund = document.getElementById('dash-kpi-fund-avg');

      if (kpiFund) {

        kpiFund.textContent = `${data.overall_last_4_average.toFixed(1)}/20`;

      }

      const kpiValid = document.getElementById('dash-kpi-validated-count');

      if (kpiValid) {

        const passedCount = Object.values(data.pillars).filter(p => p.attempts_count > 0 && p.last_4_average >= 10.0).length;

        kpiValid.textContent = `${passedCount}/4`;

      }



      Object.values(data.pillars).forEach(p => {
        const card = document.createElement('div');
        card.className = 'pillar-mini-card';
        const avg = p.last_4_average || 0;
        let lvlColor = '#f87171'; // Rouge pour insuffisant
        if (avg >= 14.0) lvlColor = '#34d399';
        else if (avg >= 12.0) lvlColor = '#60a5fa';
        else if (avg >= 10.0) lvlColor = '#facc15';
        else if (avg >= 7.0) lvlColor = '#fb923c';

        card.innerHTML = `
          <div class="pillar-mini-header">
            <span>${this._escapeHtml(p.module_title || p.module_code)}</span>
            <span>${p.attempts_count} tent.</span>
          </div>
          <div class="pillar-mini-level" style="color:${lvlColor}; font-weight:800;">${p.level_title}</div>
          <div class="pillar-mini-sub">
            <span>Score (4 der.) :</span>
            <strong style="color:${lvlColor}; font-family:var(--font-mono);">${p.last_4_average.toFixed(1)} / 20</strong>
          </div>
        `;
        container.appendChild(card);
      });

    } catch (err) {

      console.warn("Erreur chargement résumé 4 piliers :", err);

    }

  }



  // --- Chargement des Modules de Tests de Niveau (Cartes Épurées) ---

  async _loadPracticeModules() {

    const container = document.getElementById('practice-modules-grid');

    if (!container) return;



    try {

      const modules = await api.getPracticeModules();

      container.innerHTML = '';



      modules.forEach(m => {

        const card = document.createElement('div');

        card.className = 'practice-compact-card';



        let pillsHtml = '';

        if (m.last_4_scores && m.last_4_scores.length > 0) {

          pillsHtml = m.last_4_scores.map(s => {

            const cls = s >= 14 ? 'good' : (s >= 10 ? 'average' : 'low');

            return `<span class="score-pill ${cls}">${s.toFixed(1)}/20</span>`;

          }).join('');

        } else {

          pillsHtml = `<span style="font-size:0.8rem; color:var(--text-muted);">Aucune tentative</span>`;

        }



        card.innerHTML = `

          <div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">

              <span style="font-size:0.85rem; color:var(--text-secondary); font-weight:600; display:flex; align-items:center; gap:6px;">

                <span>🎯</span> Test Continu

              </span>

              <span style="font-size:0.8rem; color:var(--text-muted); font-weight:600;">Tentatives : ${m.attempts_count}</span>
            </div>
            <h4 style="font-size:1.15rem; margin:0 0 10px 0; color:var(--text-primary); font-weight:700;">${this._escapeHtml(m.title)}</h4>
            
            <div style="background:var(--bg-secondary); border:1px solid var(--card-border); border-radius:var(--radius-md); padding:10px 12px; margin-bottom:12px;">

              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">

                <span style="font-size:0.8rem; color:var(--text-secondary);">Moyenne glissante (4 dernières) :</span>

                <strong style="font-size:1.05rem; color:#60a5fa; font-family:var(--font-mono);">${m.last_4_average.toFixed(2)} / 20</strong>

              </div>

              <div class="score-pills-row">

                ${pillsHtml}

              </div>

            </div>



            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem;">

              <span style="color:var(--text-muted);">Niveau Actuel :</span>

              <span class="user-tag" style="${(() => {

                const avg = m.last_4_average || 0;

                const lt = (m.level_title || '').toLowerCase();

                if (avg < 10 || lt.includes('insuffisant') || lt.includes('évalué')) {

                  return 'background:rgba(239, 68, 68, 0.15); color:#fca5a5; border:1px solid rgba(239, 68, 68, 0.35); font-weight:700;';

                } else if (avg < 14) {

                  return 'background:rgba(59, 130, 246, 0.15); color:#93c5fd; border:1px solid rgba(59, 130, 246, 0.35); font-weight:700;';

                } else {

                  return 'background:rgba(16, 185, 129, 0.15); color:#34d399; border:1px solid rgba(16, 185, 129, 0.35); font-weight:700;';

                }

              })()}">

                ${m.level_title}

              </span>

            </div>

          </div>



          <div style="display:flex; gap:10px; margin-top:14px;">

            <button class="btn btn-primary" style="flex:1;" id="btn-practice-${m.code}">

              Lancer le Test de Niveau ➔

            </button>

            <button class="btn btn-secondary" style="padding:8px 14px;" id="btn-history-${m.code}" title="Voir l'historique">

              📜 Historique

            </button>

          </div>

        `;



        card.querySelector(`#btn-practice-${m.code}`).onclick = () => {

          this.launchPracticeExam(m.code);

        };

        card.querySelector(`#btn-history-${m.code}`).onclick = () => {

          this.openPracticeHistoryModal(m.code);

        };



        container.appendChild(card);

      });

    } catch (err) {

      container.innerHTML = `<div style="color:var(--danger);">Erreur : ${err.message}</div>`;

    }

  }



  // --- Vue Détaillée : Statistiques & Performance Académique ---

  async renderStatisticsView() {

    this.switchView('view-stats');



    // Boutons de navigation

    const btnGoExams = document.getElementById('btn-stats-go-official-exams');

    if (btnGoExams) btnGoExams.onclick = () => this.renderOfficialExamsView();

    const btnGoPy = document.getElementById('btn-stats-go-python');

    if (btnGoPy) btnGoPy.onclick = () => this.renderTrainingCenterView();

    const btnGoLx = document.getElementById('btn-stats-go-linux');

    if (btnGoLx) btnGoLx.onclick = () => this.renderLinuxTrainingCenter();

    const btnBack = document.getElementById('btn-stats-back-dash');

    if (btnBack) btnBack.onclick = () => this.renderDashboard(this.currentUser);



    try {

      const stats = await api.getStudentStatistics();

      this.lastStudentStats = stats;



      // 1. Synthèse Épreuves Officielles

      const offSummary = stats.official_summary || { total_attempts: 0, passed_count: 0, average_mark: 0.0, success_rate: 0.0, exams: [] };

      const elOffTotal = document.getElementById('stats-off-total');

      const elOffAvg = document.getElementById('stats-off-avg');

      const elOffPassed = document.getElementById('stats-off-passed');

      const elOffRate = document.getElementById('stats-off-rate');

      const tbodyOff = document.getElementById('stats-official-exams-table-body');



      if (elOffTotal) elOffTotal.textContent = offSummary.total_attempts;

      if (elOffAvg) elOffAvg.textContent = offSummary.total_attempts > 0 ? `${offSummary.average_mark.toFixed(2)} / 20` : '-- / 20';

      if (elOffPassed) elOffPassed.textContent = `${offSummary.passed_count} / 4`;

      if (elOffRate) elOffRate.textContent = `${offSummary.success_rate.toFixed(1)} %`;



      if (tbodyOff) {

        tbodyOff.innerHTML = '';

        if (!offSummary.exams || offSummary.exams.length === 0) {

          tbodyOff.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">Aucune épreuve officielle soumise pour le moment.</td></tr>';

        } else {

          offSummary.exams.forEach(ex => {

            const tr = document.createElement('tr');

            const isPass = ex.mark >= 10.0;
            const markColor = isPass ? 'var(--success)' : 'var(--danger)';
            const cleanExTitle = (ex.exam_title || '').replace(/^(?:Épreuve\s+Officielle|Examen\s+Officiel)\s*:\s*/i, '').trim();
            tr.innerHTML = `
              <td style="font-family:var(--font-mono); font-size:0.85rem;">${this._escapeHtml(ex.submitted_at || 'Terminé')}</td>
              <td style="font-weight:600; color:var(--text-primary);">${this._escapeHtml(cleanExTitle)}</td>
              <td><strong style="font-family:var(--font-mono); font-size:1.05rem; color:${markColor};">${ex.mark.toFixed(2)} / 20</strong></td>
              <td>
                <span class="badge" style="${isPass ? 'background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3);' : 'background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid rgba(239,68,68,0.3);'}">
                  ${isPass ? '✓ Validé' : '✗ Insuffisant'}
                </span>
              </td>
              <td style="text-align: right;">
                <button class="btn btn-secondary btn-sm" id="btn-review-stat-${ex.attempt_id}" style="padding: 4px 10px; font-size: 0.8rem;">
                  🔍 Voir Corrigé
                </button>
              </td>
            `;

            tbodyOff.appendChild(tr);

            const btnRev = tr.querySelector(`#btn-review-stat-${ex.attempt_id}`);

            if (btnRev) {

              btnRev.onclick = () => this.openExamReviewModal(ex.attempt_id, ex.exam_id);

            }

          });

        }

      }



      // 2. Tests de Niveau & Positionnement Continu (4 Piliers Fondamentaux)

      const fundamentalGrid = document.getElementById('stats-fundamental-grid');

      if (fundamentalGrid) {

        fundamentalGrid.innerHTML = '';

        const fundModules = stats.modules_breakdown.filter(m => m.is_fundamental);

        fundModules.forEach(m => {

          const card = document.createElement('div');

          card.className = `fundamental-card ${m.passed ? 'passed' : ''}`;



          let lvlColor = '#f87171'; // Rouge par défaut pour insuffisant

          let lvlBg = 'rgba(239, 68, 68, 0.15)';

          let lvlBorder = 'rgba(239, 68, 68, 0.35)';



          if (m.best_mark >= 16.0) {

            lvlColor = '#c084fc'; lvlBg = 'rgba(168, 85, 247, 0.18)'; lvlBorder = 'rgba(168, 85, 247, 0.4)';

          } else if (m.best_mark >= 14.0) {

            lvlColor = '#34d399'; lvlBg = 'rgba(16, 185, 129, 0.18)'; lvlBorder = 'rgba(16, 185, 129, 0.4)';

          } else if (m.best_mark >= 12.0) {

            lvlColor = '#60a5fa'; lvlBg = 'rgba(59, 130, 246, 0.18)'; lvlBorder = 'rgba(59, 130, 246, 0.4)';

          } else if (m.best_mark >= 10.0) {

            lvlColor = '#facc15'; lvlBg = 'rgba(234, 179, 8, 0.18)'; lvlBorder = 'rgba(234, 179, 8, 0.4)';

          } else if (m.best_mark >= 7.0) {

            lvlColor = '#fb923c'; lvlBg = 'rgba(249, 115, 22, 0.18)'; lvlBorder = 'rgba(249, 115, 22, 0.4)';

          }



          card.innerHTML = `

            <div>

              <div class="fundamental-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">

                <span style="font-size:0.75rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">Pilier Fondamental</span>

                <span class="mastery-pill" style="background:${lvlBg}; color:${lvlColor}; border:1px solid ${lvlBorder};">${m.mastery_level}</span>

              </div>

              <h4 class="fundamental-title" style="margin:0 0 10px 0; font-size:1.05rem; color:var(--text-primary); font-weight:700;">${this._escapeHtml(m.title)}</h4>

              <div class="fundamental-mark-box">

                <div class="fundamental-big-mark" style="color:${lvlColor};">${m.best_mark.toFixed(1)}</div>

                <div class="fundamental-mark-total">/ 20</div>

              </div>

              <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:12px;">

                Moyenne : <strong>${m.average_mark.toFixed(1)} / 20</strong> • <strong>${m.attempts_count}</strong> test${m.attempts_count > 1 ? 's' : ''}

              </div>

            </div>

            <div>

              <div style="margin-bottom:12px; font-size:0.8rem; font-weight:600; color:${m.passed ? 'var(--success)' : 'var(--danger)'};">

                ${m.passed ? '✓ Validé (≥ 10/20)' : '⚠ Insuffisant (< 10/20)'}

              </div>

              <button class="btn btn-secondary" style="width:100%; font-size:0.85rem;" id="btn-stats-train-${m.code}">

                Passer le Test de Niveau →

              </button>

            </div>

          `;



          const btnTr = card.querySelector(`#btn-stats-train-${m.code}`);

          if (btnTr) {

            btnTr.onclick = () => this.launchPracticeExam(m.code);

          }

          fundamentalGrid.appendChild(card);

        });

      }



      // Échelle des 6 Niveaux (REV-11)

      const ladderGrid = document.getElementById('stats-level-ladder');

      if (ladderGrid) {

        ladderGrid.innerHTML = '';

        const levelDescriptions = [

          { level: 1, title: "Insuffisant", range: "0.00 à < 7.00 / 20", color: "#f87171", bg: "rgba(239, 68, 68, 0.15)", border: "#ef4444" },

          { level: 2, title: "Sous la moyenne", range: "7.00 à < 10.00 / 20", color: "#fb923c", bg: "rgba(249, 115, 22, 0.15)", border: "#f97316" },

          { level: 3, title: "Limite", range: "10.00 à < 12.00 / 20", color: "#facc15", bg: "rgba(234, 179, 8, 0.15)", border: "#eab308" },

          { level: 4, title: "Moyen", range: "12.00 à < 14.00 / 20", color: "#60a5fa", bg: "rgba(59, 130, 246, 0.15)", border: "#3b82f6" },

          { level: 5, title: "Bon", range: "14.00 à < 16.00 / 20", color: "#34d399", bg: "rgba(16, 185, 129, 0.15)", border: "#10b981" },

          { level: 6, title: "Excellent", range: "16.00 à 20.00 / 20", color: "#c084fc", bg: "rgba(168, 85, 247, 0.15)", border: "#a855f7" },

        ];



        levelDescriptions.forEach(lvl => {

          const item = document.createElement('div');

          const isActive = (stats.global_level === lvl.level);

          item.className = `level-ladder-item ${isActive ? 'active-level' : ''}`;

          if (isActive) {

            item.style.borderColor = lvl.border;

            item.style.background = lvl.bg;

            item.style.boxShadow = `0 0 14px ${lvl.border}40`;

          }

          item.innerHTML = `

            <div class="level-number-badge" style="${isActive ? `background:${lvl.border}; color:#fff; font-weight:800;` : ''}">${lvl.level}</div>

            <div>

              <div style="font-weight:700; font-size:0.9rem; color:${isActive ? lvl.color : 'var(--text-primary)'};">

                ${lvl.title} ${isActive ? '★ (Votre Niveau)' : ''}

              </div>

              <div style="font-size:0.75rem; color:var(--text-muted);">${lvl.range}</div>

            </div>

          `;

          ladderGrid.appendChild(item);

        });

      }



      // 3. Synthèse Centre Python

      const pySum = stats.python_summary || { total_sessions: 0, average_mark: 0.0, level_name: 'Niveau 1 : Débutant', total_xp: 0, xp_next_threshold: 100, progress_percent: 0.0 };

      const elPyChip = document.getElementById('stats-py-level-chip');

      const elPyXp = document.getElementById('stats-py-xp');

      const elPyNextXp = document.getElementById('stats-py-next-xp');

      const elPyBar = document.getElementById('stats-py-xp-bar');

      const elPySess = document.getElementById('stats-py-sessions');

      const elPyAvg = document.getElementById('stats-py-avg');



      if (elPyChip) elPyChip.textContent = pySum.level_name;

      if (elPyXp) elPyXp.textContent = `${pySum.total_xp} XP`;

      if (elPyNextXp) elPyNextXp.textContent = `/ ${pySum.xp_next_threshold} XP`;

      if (elPyBar) elPyBar.style.width = `${pySum.progress_percent}%`;

      if (elPySess) elPySess.textContent = pySum.total_sessions;

      if (elPyAvg) elPyAvg.textContent = pySum.total_sessions > 0 ? `${pySum.average_mark.toFixed(2)} / 20` : '-- / 20';



      // 4. Synthèse Centre Linux

      const lxSum = stats.linux_summary || { total_sessions: 0, average_mark: 0.0, best_mark: 0.0 };

      const elLxSess = document.getElementById('stats-lx-sessions');

      const elLxBest = document.getElementById('stats-lx-best');

      if (elLxSess) elLxSess.textContent = lxSum.total_sessions;

      if (elLxBest) elLxBest.textContent = lxSum.total_sessions > 0 ? `${lxSum.best_mark.toFixed(1)} / 20` : '-- / 20';



      // 5. Historique Chronologique Global

      const timelineTable = document.getElementById('stats-timeline-table-body');

      if (timelineTable) {

        timelineTable.innerHTML = '';

        if (!stats.recent_timeline || !stats.recent_timeline.length) {

          timelineTable.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:20px;">Aucune évaluation enregistrée.</td></tr>';

        } else {

          [...stats.recent_timeline].reverse().forEach(ev => {

            const row = document.createElement('tr');

            const isPassed = ev.mark >= 10.0;

            const markColor = isPassed ? 'var(--success)' : 'var(--danger)';

            row.innerHTML = `

              <td style="font-family:var(--font-mono); font-size:0.85rem;">${this._escapeHtml(ev.date || '')}</td>

              <td>

                <span class="badge" style="font-size:0.75rem; ${ev.type === 'officiel' ? 'background:rgba(59,130,246,0.2); color:#93c5fd; border:1px solid rgba(59,130,246,0.4);' : 'background:rgba(16,185,129,0.15); color:#6ee7b7; border:1px solid rgba(16,185,129,0.3);'}">

                  ${ev.type === 'officiel' ? '🎓 Épreuve Officielle' : '📈 Test de Niveau'}

                </span>

              </td>

              <td style="font-weight:600; color:var(--text-primary);">${this._escapeHtml(ev.title)}</td>

              <td><strong style="font-family:var(--font-mono); font-size:1.05rem; color:${markColor};">${ev.mark.toFixed(2)} / 20</strong></td>

              <td>

                <span class="badge" style="${isPassed ? 'background:rgba(16,185,129,0.15); color:#34d399;' : 'background:rgba(239,68,68,0.15); color:#f87171;'}">

                  ${isPassed ? 'Admis' : 'Insuffisant'}

                </span>

              </td>

            `;

            timelineTable.appendChild(row);

          });

        }

      }



    } catch (err) {

      this.showToast(`Erreur de chargement des statistiques : ${err.message}`, "danger");

    }

  }



  // --- Vue Dédiée : Épreuves & Examens Officiels ---

  async renderOfficialExamsView() {

    this.switchView('view-official-exams');



    // Mettre à jour l'onglet actif dans la barre de navigation

    const nav = document.getElementById('role-nav');

    if (nav) {

      nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));

      const activeBtn = document.getElementById('nav-official-exams');

      if (activeBtn) activeBtn.classList.add('active');

    }



    // Bouton retour au tableau de bord

    const btnBack = document.getElementById('btn-exams-back-dash');

    if (btnBack) {

      btnBack.onclick = () => {

        if (this.currentUser) this.renderDashboard(this.currentUser);

        else this.switchView('view-dashboard');

      };

    }



    // Charger les indicateurs KPI des épreuves officielles

    try {

      const stats = await api.getStudentStatistics();

      if (stats && stats.official_summary) {

        const off = stats.official_summary;

        const totalCanonical = 4;



        const valCount = document.getElementById('official-stat-validated-count');

        if (valCount) valCount.textContent = `${off.passed_count || 0} / ${totalCanonical}`;



        const avgGrade = document.getElementById('official-stat-avg-grade');

        if (avgGrade) avgGrade.textContent = (off.average_mark !== undefined && off.total_attempts > 0) ? `${Number(off.average_mark).toFixed(2)} / 20` : '-- / 20';



        const subCount = document.getElementById('official-stat-submitted-count');

        if (subCount) subCount.textContent = `${off.total_attempts || 0}`;



        const passRate = document.getElementById('official-stat-pass-rate');

        if (passRate) passRate.textContent = off.total_attempts > 0 ? `${off.success_rate || 0} %` : '-- %';

      }

    } catch (e) {

      console.warn("Erreur chargement KPIs officiels :", e);

    }



    // Charger la liste des épreuves officielles dans la grille dédiée

    await this._loadOfficialExams('dedicated-official-exams-grid');

  }



  // --- Modal : Consultation du Corrigé Détaillé & des Erreurs d'Examen ---

  async openExamReviewModal(attemptId, examId) {

    const modal = document.getElementById('modal-exam-review');

    const container = document.getElementById('review-questions-container');

    const titleEl = document.getElementById('review-exam-title');

    const metaEl = document.getElementById('review-exam-meta');



    if (!modal || !container) return;



    container.innerHTML = `

      <div style="text-align: center; padding: 40px; color: var(--text-secondary);">

        <div class="loading-spinner" style="margin: 0 auto 16px auto;"></div>

        Chargement du corrigé officiel et de vos réponses...

      </div>

    `;

    this.openModal('modal-exam-review');



    try {

      const data = await api.getExamReview(attemptId);

      if (titleEl) titleEl.textContent = data.exam_title || "Corrigé Détaillé de l'Épreuve";



      const finalMark = data.final_mark !== null && data.final_mark !== undefined ? Number(data.final_mark).toFixed(2) : '--';

      const maxPts = data.global_points || 20;

      const totalQ = data.total_questions || (data.questions ? data.questions.length : 0);

      const corrQ = data.correct_count !== undefined ? data.correct_count : 0;

      const pct = totalQ > 0 ? Math.round((corrQ / totalQ) * 100) : 0;



      if (metaEl) {

        metaEl.innerHTML = `

          <span style="font-weight:700; color:${Number(finalMark) >= 10 ? '#34d399' : '#f87171'};">Note obtenue : ${finalMark} / ${maxPts}</span>

          • <span>Questions : ${corrQ} / ${totalQ} correctes (${pct}%)</span>

          ${data.submitted_at ? ` • <span>Soumis le : ${new Date(data.submitted_at).toLocaleString('fr-FR')}</span>` : ''}

        `;

      }



      container.innerHTML = '';

      if (!data.questions || !data.questions.length) {

        container.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">Aucune question trouvée pour ce corrigé.</div>`;

        return;

      }



      data.questions.forEach((q, idx) => {

        const qCard = document.createElement('div');

        qCard.className = 'card review-question-card';

        qCard.style.cssText = `
          padding: 18px 22px;
          border-radius: 10px;
          background: var(--bg-surface);
          border: 1px solid ${q.is_correct ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.45)'};
          margin-bottom: 14px;
        `;



        const isOk = q.is_correct;

        const statusBadge = isOk

          ? `<span class="badge" style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid #10b981; font-weight:700; padding:3px 10px; border-radius:6px; font-size:0.8rem;">✅ Réponse Correcte (+${q.awarded_points} pt)</span>`

          : `<span class="badge" style="background:rgba(239,68,68,0.18); color:#f87171; border:1px solid #ef4444; font-weight:700; padding:3px 10px; border-radius:6px; font-size:0.8rem;">❌ Erreur (${q.awarded_points} / ${q.points} pt)</span>`;



        let bodyHtml = '';
        const qType = (q.type || '').toLowerCase();

        // Correspondance robuste pour QCM, choix multiples, vrai/faux (supporte index 0, 'A', texte, valeur, booléen)
        const matchesOption = (candidate, optIdx, optVal, optText) => {
          if (candidate === null || candidate === undefined) return false;
          if (Array.isArray(candidate)) {
            return candidate.some(c => matchesOption(c, optIdx, optVal, optText));
          }
          if (typeof candidate === 'boolean') {
            if (typeof optVal === 'boolean') return candidate === optVal;
            const strVal = String(optVal).toLowerCase();
            if (candidate === true && (strVal === 'true' || strVal === 'vrai' || strVal === '1')) return true;
            if (candidate === false && (strVal === 'false' || strVal === 'faux' || strVal === '0')) return true;
          }
          const sCand = String(candidate).trim().toLowerCase();
          const sIdx = String(optIdx).trim().toLowerCase();
          const sLetter = String.fromCharCode(65 + optIdx).toLowerCase();
          const sOptVal = String(optVal ?? '').trim().toLowerCase();
          const sOptText = String(optText ?? '').trim().toLowerCase();
          return sCand === sIdx || sCand === sLetter || sCand === sOptVal || sCand === sOptText;
        };

        if (['single_choice', 'multi_choice', 'multiple_choice', 'qcm', 'boolean'].includes(qType)) {
          let opts = Array.isArray(q.options) ? q.options : [];
          if (qType === 'boolean' && (!opts || opts.length === 0)) {
            opts = [
              { id: 'true', text: 'Vrai', value: true },
              { id: 'false', text: 'Faux', value: false }
            ];
          }

          bodyHtml = `
            <div style="display:flex; flex-direction:column; gap:8px; margin: 12px 0;">
              ${opts.map((opt, optIdx) => {
                const optVal = typeof opt === 'object' && opt !== null ? (opt.id !== undefined ? opt.id : (opt.value !== undefined ? opt.value : opt.text)) : opt;
                const optText = typeof opt === 'object' && opt !== null ? (opt.text || opt.label || opt.value || opt.id) : opt;
                const letter = qType === 'boolean' ? '' : (String.fromCharCode(65 + optIdx) + ') ');

                const isUserPick = matchesOption(q.user_answer, optIdx, optVal, optText);
                const isCorrectOption = matchesOption(q.correct_answer, optIdx, optVal, optText);

                let optStyle = 'background:var(--bg-secondary); border:1px solid var(--card-border); color:var(--text-primary);';
                let tag = '';

                if (isCorrectOption && isUserPick) {
                  optStyle = 'background:rgba(16,185,129,0.15); border:1.5px solid #10b981; color:var(--text-primary); font-weight:600;';
                  tag = '<span style="color:#059669; font-size:0.82rem; font-weight:700; margin-left:auto;">✓ Votre choix (Correct)</span>';
                } else if (isCorrectOption && !isUserPick) {
                  optStyle = 'background:rgba(16,185,129,0.1); border:1.5px dashed #10b981; color:var(--text-primary); font-weight:600;';
                  tag = '<span style="color:#059669; font-size:0.82rem; font-weight:700; margin-left:auto;">★ Bonne réponse attendue</span>';
                } else if (!isCorrectOption && isUserPick) {
                  optStyle = 'background:rgba(239,68,68,0.12); border:1.5px solid #ef4444; color:var(--text-primary); font-weight:600;';
                  tag = '<span style="color:#dc2626; font-size:0.82rem; font-weight:700; margin-left:auto;">✗ Votre choix (Incorrect)</span>';
                }

                return `
                  <div style="display:flex; align-items:center; padding:9px 14px; border-radius:7px; font-size:0.92rem; ${optStyle}">
                    <span style="font-weight:700; margin-right:6px; color:var(--primary);">${this._escapeHtml(letter)}</span>
                    <span>${this._escapeHtml(String(optText))}</span>
                    ${tag}
                  </div>
                `;
              }).join('')}
            </div>
          `;
        } else if (qType === 'matching') {
          const formatPairList = (pairs) => {
            if (!pairs) return '(Aucune réponse)';
            if (typeof pairs === 'object' && !Array.isArray(pairs)) {
              return Object.entries(pairs).map(([k, v]) => `• ${k} ➔ ${v}`).join('\n');
            }
            if (Array.isArray(pairs)) {
              return pairs.map(p => {
                if (typeof p === 'object' && p !== null) {
                  const left = p.left || p.source || p.k || '';
                  const right = p.right || p.target || p.v || '';
                  return `• ${left} ➔ ${right}`;
                }
                return `• ${p}`;
              }).join('\n');
            }
            return String(pairs);
          };

          const userStr = formatPairList(q.user_answer);
          const corrStr = formatPairList(q.correct_answer);

          bodyHtml = `
            <div style="display:flex; flex-direction:column; gap:10px; margin: 12px 0;">
              <div style="background: ${isOk ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'}; border: 1px solid ${isOk ? '#10b981' : '#ef4444'}; padding: 10px 14px; border-radius: 7px;">
                <div style="font-size:0.8rem; font-weight:700; color: ${isOk ? '#059669' : '#dc2626'}; margin-bottom:4px;">
                  ${isOk ? '✓ Vos Associations (Validées)' : '✗ Vos Associations'}
                </div>
                <pre style="margin:0; font-family:var(--font-mono, monospace); font-size:0.88rem; white-space:pre-wrap; color:var(--text-primary); line-height:1.5;">${this._escapeHtml(userStr)}</pre>
              </div>
              ${!isOk && corrStr ? `
                <div style="background: rgba(16,185,129,0.1); border: 1px dashed #10b981; padding: 10px 14px; border-radius: 7px;">
                  <div style="font-size:0.8rem; font-weight:700; color:#059669; margin-bottom:4px;">★ Associations attendues :</div>
                  <pre style="margin:0; font-family:var(--font-mono, monospace); font-size:0.88rem; white-space:pre-wrap; color:var(--text-primary); font-weight:600; line-height:1.5;">${this._escapeHtml(corrStr)}</pre>
                </div>
              ` : ''}
            </div>
          `;
        } else {
          // Coding or other questions
          let userCode = q.user_answer;
          if (userCode && typeof userCode === 'object') {
            userCode = userCode.code !== undefined ? userCode.code : JSON.stringify(userCode, null, 2);
          }
          if (userCode === null || userCode === undefined || String(userCode).trim() === '') {
            userCode = '(Aucun code ou réponse soumise)';
          }

          let corrCode = q.correct_answer;
          if (corrCode && typeof corrCode === 'object') {
            if (corrCode.solution) corrCode = corrCode.solution;
            else if (corrCode.answer) corrCode = corrCode.answer;
            else corrCode = JSON.stringify(corrCode, null, 2);
          }
          corrCode = corrCode ? String(corrCode) : '';

          bodyHtml = `
            <div style="display:flex; flex-direction:column; gap:10px; margin: 12px 0;">
              <div style="background: ${isOk ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'}; border: 1px solid ${isOk ? '#10b981' : '#ef4444'}; padding: 10px 14px; border-radius: 7px;">
                <div style="font-size:0.8rem; font-weight:700; color: ${isOk ? '#059669' : '#dc2626'}; margin-bottom:4px;">
                  ${isOk ? '✓ Votre Solution / Code (Validé)' : '✗ Votre Solution / Code'}
                </div>
                <pre style="margin:0; font-family:var(--font-mono, monospace); font-size:0.88rem; white-space:pre-wrap; color:var(--text-primary); max-height:280px; overflow-y:auto; background:rgba(0,0,0,0.25); padding:8px 12px; border-radius:5px;">${this._escapeHtml(String(userCode))}</pre>
              </div>
              ${!isOk && corrCode ? `
                <div style="background: rgba(16,185,129,0.1); border: 1px dashed #10b981; padding: 10px 14px; border-radius: 7px;">
                  <div style="font-size:0.8rem; font-weight:700; color:#059669; margin-bottom:4px;">★ Solution de référence :</div>
                  <pre style="margin:0; font-family:var(--font-mono, monospace); font-size:0.88rem; white-space:pre-wrap; color:var(--text-primary); font-weight:500; max-height:280px; overflow-y:auto; background:rgba(0,0,0,0.25); padding:8px 12px; border-radius:5px;">${this._escapeHtml(corrCode)}</pre>
                </div>
              ` : ''}
            </div>
          `;
        }

        let explHtml = '';
        if (q.explanation && String(q.explanation).trim()) {
          explHtml = `
            <div style="margin-top:12px; padding:10px 14px; background:rgba(37,99,235,0.08); border-left:3px solid #2563eb; border-radius:4px; font-size:0.88rem; color:var(--text-primary);">
              <strong style="color:#2563eb;">💡 Explication :</strong> ${this._escapeHtml(q.explanation)}
            </div>
          `;
        }



        qCard.innerHTML = `

          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">

            <div style="font-weight:700; font-size:0.95rem; color:#94a3b8;">

              Question ${idx} / ${data.questions.length} <span style="font-weight:400; font-size:0.85rem; color:#64748b;">(${this._escapeHtml(q.type)})</span>

            </div>

            ${statusBadge}

          </div>

          <div style="font-size:1.02rem; font-weight:600; color:#f8fafc; line-height:1.5; margin-bottom:6px;">

            ${this._escapeHtml(q.prompt || '')}

          </div>

          ${bodyHtml}

          ${explHtml}

        `;



        container.appendChild(qCard);

      });



      if (window.renderMathInElement) {

        try {

          window.renderMathInElement(container, {

            delimiters: [

              { left: '$$', right: '$$', display: true },

              { left: '$', right: '$', display: false },

              { left: '\\(', right: '\\)', display: false },

              { left: '\\[', right: '\\]', display: true }

            ],

            throwOnError: false

          });

        } catch (_) {}

      }



    } catch (err) {

      container.innerHTML = `

        <div style="text-align: center; padding: 30px; color: var(--danger);">

          ❌ Impossible de charger le corrigé : ${this._escapeHtml(err.message)}

        </div>

      `;

      const consultRevBtn = document.getElementById('btn-score-consult-review');
      if (consultRevBtn && res.attempt_id) {
        consultRevBtn.onclick = () => this.openExamReviewModal(res.attempt_id, res.exam_id);
      }

    }

  }



    // --- Lancement d'une Session Linux (Théorique ou Pratique) ---

  async launchLinuxChapterSession(chapterId) {

    const sessionType = this.selectedLinuxMode || 'practical';

    try {

      const session = await api.generateLinuxSession({

        chapter_id: chapterId,

        session_type: sessionType,

        count: sessionType === 'theoretical' ? 6 : 2

      });



      if (!session.items || !session.items.length) {

        this.showToast("Aucun exercice disponible pour ce chapitre.", "warning");

        return;

      }



      this.activeOriginView = 'view-linux';

      window.linuxChallengeResults = {};



      const questions = session.items.map((q, idx) => {

        if (q.type === 'linux_cmd') {

          return {

            id: q.id,

            type: 'linux_cmd',

            points: q.points || 2.0,

            topic: q.topic || 'Linux Shell',

            title: q.title || `Défi Shell ${idx + 1}`,

            prompt_markdown: q.description || q.prompt || '',

            starter_code: q.starter_code || '# Tapez vos commandes Linux\n',

            initial_fs: q.initial_fs || {},

            public_tests: q.public_tests || [],

            hidden_tests: q.hidden_tests || [],

            hints: q.hints || [],

            hint1: q.hint1 || (q.hints && q.hints[0]) || '',

            hint2: q.hint2 || (q.hints && q.hints[1]) || '',

            solution: q.solution || ''

          };

        }



        let qType = q.type || 'single_choice';

        if (qType === 'yesno') qType = 'boolean';

        else if (qType === 'simple_blank') qType = 'fill_blank';



        let formattedOpts = q.options;

        if (Array.isArray(q.options)) {

          formattedOpts = q.options.map((opt, oIdx) => {

            if (typeof opt === 'object' && opt !== null) {

              return { id: opt.id !== undefined ? opt.id : oIdx, text: opt.text || opt.label || '' };

            }

            return { id: oIdx, text: String(opt) };

          });

        }



        return {

          id: q.id,

          type: qType,

          points: q.points || 1.0,

          topic: q.topic || 'Linux',

          prompt_markdown: q.prompt || q.question || '',

          options: formattedOpts,

          pairs: q.pairs || (typeof q.options === 'object' && !Array.isArray(q.options) ? q.options : undefined)

        };

      });



      const examData = {

        attempt_id: null,

        exam_title: session.title || 'Entraînement Linux',

        questions: questions,

        saved_answers: {},

        remaining_seconds: session.time_limit_seconds || (25 * 60)

      };



      if (this.activeExamRunner) {

        this.activeExamRunner.stop();

      }

      if (this.activeAntiCheat) {

        this.activeAntiCheat.stop();

        this.activeAntiCheat = null;

      }

      this.hideSuspensionScreen();



      this.activeExamRunner = new ExamRunner(examData, {

        isPracticeMode: true,

        onPracticeSubmit: async (answers) => {

          const submitAnswers = session.items.map(q => {

            const studentAns = answers[q.id] !== undefined ? answers[q.id] : null;

            let isCorrectFlag = null;

            if (q.type === 'linux_cmd') {

              isCorrectFlag = (window.linuxChallengeResults && window.linuxChallengeResults[q.id] && window.linuxChallengeResults[q.id].success) || false;

            }

            return {

              id: q.id,

              type: q.type,

              topic: q.topic || 'Linux',

              student_answer: studentAns,

              is_correct: isCorrectFlag

            };

          });



          try {

            const res = await api.submitLinuxSession(submitAnswers);

            this.showToast(`🎉 Séance Linux complétée ! Note : ${res.grade_20}/20`, "success", 5000);



            this.renderPracticeResults({

              module_title: session.title || 'Administration Système Linux',

              grade_20: res.grade_20,

              percentage: res.percentage,

              total_awarded: res.total_awarded,

              max_possible: res.max_possible,

              detailed_results: (res.item_results || []).map(r => {

                const matchedQ = session.items.find(item => String(item.id) === String(r.id));

                const fullPrompt = matchedQ ? (matchedQ.prompt || matchedQ.description || matchedQ.question) : null;

                return {

                  question_id: String(r.id),

                  prompt_markdown: fullPrompt || `**${r.topic}** (${r.type === 'linux_cmd' ? 'Défi Shell' : 'Question Théorique'})`,

                  type: r.type,

                  user_answer: answers[r.id] !== undefined ? answers[r.id] : 'Non répondu',

                  correct_answer: r.type === 'linux_cmd' ? 'Commandes conformes' : 'Réponse exacte enregistrée',

                  awarded_points: r.awarded,

                  max_points: r.points,

                  is_correct: r.is_correct,

                  explanation: r.explanation || (r.is_correct ? '✅ Validé avec succès !' : 'À perfectionner.')

                };

              })

            });

          } catch (err) {

            this.showToast(`Erreur soumission Linux : ${err.message}`, "danger");

          }

        }

      });



      window.activeExamRunner = this.activeExamRunner;

      this.switchView('view-exam');

      document.getElementById('exam-active-title').textContent = session.title || 'Entraînement Linux';



      const quitBtn = document.getElementById('btn-exam-quit');

      if (quitBtn) {

        quitBtn.style.display = 'inline-flex';

        quitBtn.onclick = async () => {

          const ok = await this.showConfirmModal({

            title: "Quitter la session Linux",

            message: "Voulez-vous quitter cette session et retourner au Centre Linux ? Vos réponses en cours ne seront pas enregistrées.",

            confirmText: "Quitter la session",

            cancelText: "Continuer",

            icon: "🐧",

            danger: true

          });

          if (ok) {

            if (this.activeExamRunner) this.activeExamRunner.stop();

            if (this.activeAntiCheat) this.activeAntiCheat.stop();

            this.renderLinuxTrainingCenter();

          }

        };

      }



      this.activeExamRunner.start();



    } catch (err) {

      this.showToast(`Erreur préparation session Linux : ${err.message}`, "danger");

    }

  }



  // --- Vue Dédiée : Centre d'Entraînement Python (Théorique & Pratique) ---

  async renderTrainingCenterView() {

    this.switchView('view-python');



    try {

      const data = await api.getPythonProgression();

      this.currentPythonProgression = data;



      const prog = data.progression;

      const gamif = data.gamification;



      // 1. Mise à jour de la Bannière Gamification & XP (10 Rangs & 68 Badges)

      const rankEl = document.getElementById('py-hero-rank');

      if (rankEl) {

        rankEl.textContent = `Niveau ${gamif.level} — ${gamif.level_name}`;

      }



      const xpEl = document.getElementById('py-hero-xp');

      if (xpEl) xpEl.textContent = gamif.total_xp;



      const nextXpEl = document.getElementById('py-hero-next-xp');

      if (nextXpEl) nextXpEl.textContent = gamif.xp_next_threshold;



      const badgesEl = document.getElementById('py-hero-badges');

      if (badgesEl) {

        badgesEl.textContent = `${gamif.unlocked_badges_count} / ${gamif.total_badges}`;

      }



      const barEl = document.getElementById('py-hero-xp-bar');

      if (barEl) {

        barEl.style.width = `${gamif.progress_percent}%`;

      }



      // 2. Rendu de la Matrice Pédagogique (10 Chapitres & 4 Difficultés)

      this._renderPythonCurriculumMatrix(prog);



      // 3. Synthèse Statistique & Diagnostic des Faiblesses

      await this._loadPythonStudentAnalytics();



    } catch (err) {

      console.error("Erreur de chargement du centre Python:", err);

      const container = document.getElementById('python-curriculum-container');

      if (container) {

        container.innerHTML = `<div style="color:var(--danger); padding:20px;">Erreur de chargement de la progression : ${err.message}</div>`;

      }

    }

  }



  // Alias pour compatibilité

  async renderPythonTrainingView() {

    return this.renderTrainingCenterView();

  }



  // --- Rendu de la Matrice des 10 Chapitres Python avec sélection libre / guidée ---

  _renderPythonCurriculumMatrix(prog) {

    const container = document.getElementById('python-curriculum-container');

    if (!container) return;



    if (!this.selectedAssessmentType) this.selectedAssessmentType = 'practical';

    if (!this.selectedProgressionMode) this.selectedProgressionMode = 'guided';



    container.innerHTML = '';



    if (!prog || !prog.topics) {

      container.innerHTML = '<div style="color:var(--text-muted); padding:20px;">Aucune donnée de progression disponible.</div>';

      return;

    }



    // 1. Branchement des 2 Grandes Cartes de Sélection (Pratique vs Théorique)

    const cardPractical = document.getElementById('card-select-practical');

    const cardTheoretical = document.getElementById('card-select-theoretical');

    const statusPractical = document.getElementById('status-practical');

    const statusTheoretical = document.getElementById('status-theoretical');



    const updateTypeCardsVisual = () => {

      if (this.selectedAssessmentType === 'practical') {

        if (cardPractical) cardPractical.classList.add('active-practical');

        if (cardTheoretical) cardTheoretical.classList.remove('active');

        if (statusPractical) statusPractical.textContent = '✓ ACTIF';

        if (statusTheoretical) statusTheoretical.textContent = '○ CHOISIR';

      } else {

        if (cardTheoretical) cardTheoretical.classList.add('active');

        if (cardPractical) cardPractical.classList.remove('active-practical');

        if (statusTheoretical) statusTheoretical.textContent = '✓ ACTIF';

        if (statusPractical) statusPractical.textContent = '○ CHOISIR';

      }

    };



    if (cardPractical && cardTheoretical) {

      cardPractical.onclick = () => {

        this.selectedAssessmentType = 'practical';

        updateTypeCardsVisual();

        this._updateLaunchButtonLabel(prog);

      };



      cardTheoretical.onclick = () => {

        this.selectedAssessmentType = 'theoretical';

        updateTypeCardsVisual();

        this._updateLaunchButtonLabel(prog);

      };



      updateTypeCardsVisual();

    }



    // 2. Branchement du Sélecteur de Mode (Guidé vs Personnalisé)

    const btnGuided = document.getElementById('btn-mode-guided');

    const btnCustom = document.getElementById('btn-mode-custom');

    const panelGuided = document.getElementById('panel-mode-guided');

    const panelCustom = document.getElementById('panel-mode-custom');

    const guidedTitle = document.getElementById('guided-step-title');

    const guidedMeta = document.getElementById('guided-step-meta');



    // Mise à jour de l'affichage du volet Guidé

    if (prog.active_step) {

      if (guidedTitle) {

        guidedTitle.textContent = `${prog.active_step.chapter_title || 'Bases de Python'}`;

      }

      if (guidedMeta) {

        guidedMeta.textContent = `Palier : ${prog.active_step.difficulty_label || 'Facile'} • Seuil de passage : 14/20 pour débloquer la suite`;

      }

    }



    const switchStudioMode = (mode) => {

      this.selectedProgressionMode = mode;

      if (mode === 'guided') {

        if (btnGuided) btnGuided.classList.add('active');

        if (btnCustom) btnCustom.classList.remove('active');

        if (panelGuided) panelGuided.classList.add('active');

        if (panelCustom) panelCustom.classList.remove('active');

      } else {

        if (btnCustom) btnCustom.classList.add('active');

        if (btnGuided) btnGuided.classList.remove('active');

        if (panelCustom) panelCustom.classList.add('active');

        if (panelGuided) panelGuided.classList.remove('active');

        this._syncCustomConfigurator(prog);

      }

      this._refreshDifficultyChipsStyle();

      this._updateLaunchButtonLabel(prog);

    };



    if (btnGuided && btnCustom) {

      btnGuided.onclick = () => switchStudioMode('guided');

      btnCustom.onclick = () => switchStudioMode('custom');



      if (this.selectedProgressionMode === 'custom') {

        switchStudioMode('custom');

      } else {

        switchStudioMode('guided');

      }

    }



    // 3. Initialisation du Sélecteur Personnalisé (Dropdown Chapitres & 4 Difficultés)

    this._initCustomConfigurator(prog);



    // 4. Rendu de la Feuille de Route (10 Chapitres Fondamentaux)

    prog.topics.forEach(topic => {

      const row = document.createElement('div');

      row.className = `curriculum-topic-row ${topic.unlocked ? '' : 'locked'}`;



      const chipsHtml = topic.difficulties.map(d => {

        let chipClass = 'locked';

        let icon = '🔒';

        let subText = d.label;



        if (d.completed) {

          chipClass = 'completed';

          icon = '✓';

          subText = `${d.label} (${d.best_mark}/20)`;

        } else if (d.current) {

          chipClass = 'current';

          icon = '▶';

          subText = `${d.label} (Cible)`;

        } else if (d.unlocked) {

          chipClass = 'unlocked';

          icon = '◆';

          subText = d.label;

        }



        const isCustomSelected = (this.customSelectedTopic === topic.id && this.customSelectedDifficulty === d.name);

        const activeBorder = isCustomSelected ? 'border: 2px solid var(--accent); transform: scale(1.05);' : '';



        return `

          <button type="button" 

                  class="diff-chip ${chipClass}" 

                  data-topic="${topic.id}" 

                  data-diff="${d.name}" 

                  data-unlocked="${d.unlocked || d.completed}"

                  style="${activeBorder}"

                  title="${d.label} - ${d.completed ? 'Validé' : (d.unlocked ? 'Débloqué' : 'Verrouillé')}">

            ${icon} ${subText}

          </button>

        `;

      }).join('');



      const chapterIcons = {

        'python_basics': '🐍',

        'data_types_structures': '📦',

        'control_flow': '🔀',

        'loops_iteration': '🔁',

        'functions_modules': '⚡',

        'file_io_exceptions': '📁',

        'oop_basics': '🏛️',

        'oop_advanced': '🧬',

        'algorithmic_thinking': '🧠',

        'standard_library': '🧰'

      };

      const chIcon = chapterIcons[topic.id] || '📘';



      row.innerHTML = `

        <div class="topic-meta">

          <div class="topic-order">Chapitre ${String(topic.order).padStart(2, '0')}</div>

          <div class="topic-title" style="display:flex; align-items:center; gap:8px;">

            <span style="font-size:1.25rem;">${chIcon}</span>

            <span>${this._escapeHtml(topic.title)}</span>

          </div>

          <div class="topic-desc">${this._escapeHtml(topic.description)}</div>

        </div>

        <div class="topic-difficulties">

          ${chipsHtml}

        </div>

      `;



      // Clic sur une difficulté pour sélection instantanée

      row.querySelectorAll('.diff-chip').forEach(btn => {

        btn.onclick = () => {

          const isUnlocked = btn.getAttribute('data-unlocked') === 'true';

          const topicId = btn.getAttribute('data-topic');

          const diff = btn.getAttribute('data-diff');



          // Basculer en mode personnalisé

          this.customSelectedTopic = topicId;

          this.customSelectedDifficulty = diff;

          switchStudioMode('custom');



          const selectEl = document.getElementById('select-custom-topic');

          if (selectEl) selectEl.value = topicId;



          this._syncCustomDiffButtons(prog);



          if (!isUnlocked) {

            const noticeEl = document.getElementById('custom-lock-notice');

            if (noticeEl) noticeEl.style.display = 'flex';

          } else {

            const noticeEl = document.getElementById('custom-lock-notice');

            if (noticeEl) noticeEl.style.display = 'none';

          }



          this._refreshDifficultyChipsStyle();

          this._updateLaunchButtonLabel(prog);

        };

      });



      container.appendChild(row);

    });



    // Mise à jour finale du libellé du bouton de lancement

    this._updateLaunchButtonLabel(prog);

  }



  // Initialise le dropdown des chapitres et les 4 boutons de difficulté

  _initCustomConfigurator(prog) {

    const selectTopic = document.getElementById('select-custom-topic');

    if (selectTopic && prog && prog.topics) {

      selectTopic.innerHTML = '';

      prog.topics.forEach(t => {

        const opt = document.createElement('option');

        opt.value = t.id;

        opt.textContent = `Chapitre ${String(t.order).padStart(2, '0')} : ${t.title} ${t.unlocked ? '' : '(🔒)'}`;

        selectTopic.appendChild(opt);

      });



      if (!this.customSelectedTopic) {

        this.customSelectedTopic = (prog.active_step && prog.active_step.chapter_id) || prog.topics[0]?.id;

      }

      selectTopic.value = this.customSelectedTopic;



      selectTopic.onchange = () => {

        this.customSelectedTopic = selectTopic.value;

        this._syncCustomDiffButtons(prog);

        this._refreshDifficultyChipsStyle();

        this._updateLaunchButtonLabel(prog);

      };

    }



    if (!this.customSelectedDifficulty) {

      this.customSelectedDifficulty = (prog.active_step && prog.active_step.difficulty) || 'easy';

    }



    // Branchement des 4 boutons de difficulté

    ['easy', 'medium', 'hard', 'expert'].forEach(diff => {

      const btn = document.getElementById(`diff-btn-${diff}`);

      if (btn) {

        btn.onclick = () => {

          this.customSelectedDifficulty = diff;

          this._syncCustomDiffButtons(prog);

          this._refreshDifficultyChipsStyle();

          this._updateLaunchButtonLabel(prog);

        };

      }

    });



    this._syncCustomDiffButtons(prog);

  }



  _syncCustomConfigurator(prog) {

    const selectTopic = document.getElementById('select-custom-topic');

    if (selectTopic && this.customSelectedTopic) {

      selectTopic.value = this.customSelectedTopic;

    }

    this._syncCustomDiffButtons(prog);

  }



  // Met à jour les 4 boutons de difficulté selon le chapitre actuellement sélectionné

  _syncCustomDiffButtons(prog) {

    if (!prog || !prog.topics) return;

    const currentTopic = prog.topics.find(t => t.id === this.customSelectedTopic) || prog.topics[0];

    const noticeEl = document.getElementById('custom-lock-notice');

    let isCurrentSelectedUnlocked = true;



    ['easy', 'medium', 'hard', 'expert'].forEach(diff => {

      const btn = document.getElementById(`diff-btn-${diff}`);

      if (!btn) return;



      const diffObj = currentTopic ? currentTopic.difficulties.find(d => d.name === diff) : null;

      const isUnlocked = diffObj ? (diffObj.unlocked || diffObj.completed) : false;



      if (this.customSelectedDifficulty === diff) {

        btn.classList.add('active');

        if (!isUnlocked) isCurrentSelectedUnlocked = false;

      } else {

        btn.classList.remove('active');

      }



      if (isUnlocked) {

        btn.classList.remove('locked');

      } else {

        btn.classList.add('locked');

      }

    });



    if (noticeEl) {

      if (!isCurrentSelectedUnlocked) {

        noticeEl.style.display = 'flex';

      } else {

        noticeEl.style.display = 'none';

      }

    }

  }



  _refreshDifficultyChipsStyle() {

    document.querySelectorAll('.diff-chip').forEach(btn => {

      const isCustom = (this.selectedProgressionMode === 'custom');

      const isSelected = isCustom && (this.customSelectedTopic === btn.getAttribute('data-topic') && this.customSelectedDifficulty === btn.getAttribute('data-diff'));

      if (isSelected) {

        btn.style.outline = '3px solid #60a5fa';

        btn.style.boxShadow = '0 0 16px rgba(96, 165, 250, 0.7)';

        btn.style.transform = 'scale(1.08)';

      } else {

        btn.style.outline = 'none';

        btn.style.boxShadow = 'none';

        btn.style.transform = 'none';

      }

    });

  }



  _updateLaunchButtonLabel(prog) {

    const launchBtn = document.getElementById('btn-start-curriculum-training');

    const mainText = document.getElementById('btn-hero-main-text');

    const summaryText = document.getElementById('launch-summary-text');



    const mode = this.selectedProgressionMode || 'guided';

    const type = this.selectedAssessmentType || 'practical';

    const typeLabel = type === 'practical' ? '💻 Laboratoire Pratique' : '📖 Quiz Théorique';

    const actionLabel = type === 'practical' ? "Commencer l'Entraînement Pratique ➔" : "Lancer le Quiz Théorique ➔";



    if (launchBtn) {

      if (type === 'practical') {

        launchBtn.classList.add('start-practical');

      } else {

        launchBtn.classList.remove('start-practical');

      }

    }



    if (mainText) {

      mainText.textContent = actionLabel;

    }



    if (mode === 'guided') {

      const active = prog.active_step || { chapter_title: 'Bases de Python', difficulty_label: 'Facile' };

      if (summaryText) {

        summaryText.textContent = `${typeLabel} • ${active.chapter_title} • Palier ${active.difficulty_label} [Mode Guidé Auto]`;

      }

    } else {

      let topicTitle = "Chapitre Sélectionné";

      if (this.customSelectedTopic && prog.topics) {

        const t = prog.topics.find(top => top.id === this.customSelectedTopic);

        if (t) topicTitle = t.title;

      }

      const diffNames = { easy: 'Facile', medium: 'Moyen', hard: 'Difficile', expert: 'Expert' };

      const diffLabel = diffNames[this.customSelectedDifficulty] || this.customSelectedDifficulty || 'Facile';

      if (summaryText) {

        summaryText.textContent = `${typeLabel} • ${topicTitle} • Palier ${diffLabel} [Mode Personnalisé]`;

      }

    }

  }



  // --- Synthèse Statistique Personnalisée & Diagnostic des Faiblesses ---

  async _loadPythonStudentAnalytics() {

    try {

      const data = await api.getPythonStudentAnalytics();

      if (!data) return;



      const badgeEl = document.getElementById('python-analytics-badge');

      const sessionsEl = document.getElementById('python-stat-sessions');

      const avgEl = document.getElementById('python-stat-avg');

      const rateEl = document.getElementById('python-stat-rate');

      const badgesEl = document.getElementById('python-stat-badges');

      const weakList = document.getElementById('python-weaknesses-list');

      const recList = document.getElementById('python-recommendations-list');



      if (badgeEl) {

        if (data.total_sessions === 0) {

          badgeEl.textContent = 'En attente de vos premiers tests';

          badgeEl.style.background = 'rgba(148, 163, 184, 0.15)';

          badgeEl.style.color = '#94a3b8';

        } else {

          badgeEl.textContent = `${data.total_sessions} session${data.total_sessions > 1 ? 's' : ''} enregistrée${data.total_sessions > 1 ? 's' : ''}`;

          badgeEl.style.background = 'rgba(59, 130, 246, 0.15)';

          badgeEl.style.color = '#93c5fd';

        }

      }



      if (sessionsEl) sessionsEl.textContent = data.total_sessions;

      if (avgEl) avgEl.textContent = `${data.average_mark} / 20`;

      if (rateEl) rateEl.textContent = `${data.success_rate_percent} %`;



      const gamif = data.gamification;

      const levelChip = document.getElementById('py-stat-level-chip');

      const xpVal = document.getElementById('python-stat-xp');

      const nextXpText = document.getElementById('python-stat-next-xp-text');

      const xpBar = document.getElementById('python-stat-xp-bar');



      if (gamif) {

        if (levelChip) levelChip.textContent = gamif.level_name;

        if (xpVal) xpVal.textContent = `${gamif.total_xp} XP`;

        if (nextXpText) nextXpText.textContent = `/ ${gamif.xp_next_threshold} XP`;

        if (xpBar) xpBar.style.width = `${gamif.progress_percent}%`;

      }



      // 1. Liste des faiblesses

      if (weakList) {

        if (!data.weaknesses || data.weaknesses.length === 0) {

          weakList.innerHTML = `<span style="color: #34d399; font-weight: 500;">✓ Excellent ! Aucun point faible sous le seuil de validation (14/20) n'a été identifié.</span>`;

        } else {

          weakList.innerHTML = data.weaknesses.map(w => `

            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px; gap: 8px;">

              <div style="min-width: 0; flex: 1;">

                <div style="font-weight: 600; color: #f87171; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">

                  ${this._escapeHtml(w.chapter_title)} • <span style="font-size: 0.8rem; font-weight: normal; color: #fca5a5;">${this._escapeHtml(w.difficulty_label)}</span>

                </div>

                <div style="font-size: 0.78rem; color: var(--text-muted);">

                  Moyenne : <strong style="color: #ef4444;">${w.avg_score}/20</strong> (${w.attempts_count} essai${w.attempts_count > 1 ? 's' : ''})

                </div>

              </div>

              <button class="btn btn-sm btn-outline-danger btn-weakness-retest" data-topic="${w.chapter_id}" data-diff="${w.difficulty}" style="font-size: 0.78rem; padding: 4px 8px; border-radius: 4px; white-space: nowrap; cursor: pointer;">

                🔄 Retravailler

              </button>

            </div>

          `).join('');



          weakList.querySelectorAll('.btn-weakness-retest').forEach(btn => {

            btn.onclick = () => {

              const ch = btn.getAttribute('data-topic');

              const diff = btn.getAttribute('data-diff');

              this._selectCustomChapterAndDiff(ch, diff);

            };

          });

        }

      }



      // 2. Liste des recommandations prioritaires

      if (recList) {

        if (!data.recommendations || data.recommendations.length === 0) {

          recList.innerHTML = `<span style="color: var(--text-muted);">Poursuivez le parcours guidé pour consolider les chapitres fondamentaux.</span>`;

        } else {

          recList.innerHTML = data.recommendations.map(r => `

            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 6px; gap: 8px;">

              <div style="min-width: 0; flex: 1;">

                <div style="font-weight: 600; color: #34d399; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">

                  ${this._escapeHtml(r.chapter_title)} • <span style="font-size: 0.8rem; font-weight: normal; color: #6ee7b7;">${this._escapeHtml(r.difficulty_label)}</span>

                </div>

                <div style="font-size: 0.78rem; color: var(--text-muted);">${this._escapeHtml(r.reason)}</div>

              </div>

              <button class="btn btn-sm btn-primary btn-rec-launch" data-topic="${r.chapter_id}" data-diff="${r.difficulty}" style="font-size: 0.78rem; padding: 4px 10px; border-radius: 4px; white-space: nowrap; cursor: pointer;">

                ▶ Lancer

              </button>

            </div>

          `).join('');



          recList.querySelectorAll('.btn-rec-launch').forEach(btn => {

            btn.onclick = () => {

              const ch = btn.getAttribute('data-topic');

              const diff = btn.getAttribute('data-diff');

              this._selectCustomChapterAndDiff(ch, diff);

            };

          });

        }

      }



    } catch (err) {

      console.warn("Impossible de charger les statistiques d'entraînement Python:", err);

    }

  }



  _selectCustomChapterAndDiff(topicId, diff) {

    this.customSelectedTopic = topicId;

    this.customSelectedDifficulty = diff;

    const btnCustom = document.getElementById('btn-mode-custom');

    if (btnCustom) btnCustom.click();



    const selectEl = document.getElementById('select-custom-topic');

    if (selectEl) selectEl.value = topicId;



    if (this.currentPythonProgression && this.currentPythonProgression.progression) {

      this._syncCustomDiffButtons(this.currentPythonProgression.progression);

      this._refreshDifficultyChipsStyle();

      this._updateLaunchButtonLabel(this.currentPythonProgression.progression);

    }



    const container = document.getElementById('python-curriculum-container');

    if (container) {

      container.scrollIntoView({ behavior: 'smooth', block: 'start' });

    }

  }



  // --- Lancement de l'entraînement selon le mode et type choisis ---

  async launchSelectedTraining() {

    if (!this.currentPythonProgression) {

      try {

        this.currentPythonProgression = await api.getPythonProgression();

      } catch (err) {

        this.showToast("Erreur de récupération de la progression : " + err.message, "danger");

        return;

      }

    }



    const prog = this.currentPythonProgression.progression;

    const mode = this.selectedProgressionMode || 'guided';

    const assessmentType = this.selectedAssessmentType || 'practical';



    let targetTopic = null;

    let targetDifficulty = null;

    let sessionTitle = "";



    if (mode === 'guided') {

      const active = prog.active_step || { chapter_id: 'python_basics', chapter_title: 'Bases de Python', difficulty: 'easy', difficulty_label: 'Facile' };

      targetTopic = active.chapter_id;

      targetDifficulty = active.difficulty;

      sessionTitle = `${assessmentType === 'practical' ? '💻 Lab Pratique' : '📖 Quiz Théorique'} : ${active.chapter_title} (${active.difficulty_label})`;

    } else {

      targetTopic = this.customSelectedTopic || (prog.topics.find(t => t.unlocked)?.id || 'python_basics');

      targetDifficulty = this.customSelectedDifficulty || 'easy';

      const topicObj = prog.topics.find(t => t.id === targetTopic);

      const topicTitle = topicObj ? topicObj.title : 'Python';

      sessionTitle = `${assessmentType === 'practical' ? '💻 Lab Pratique' : '📖 Quiz Théorique'} : ${topicTitle} (${targetDifficulty})`;

    }



    try {

      const payload = {

        topics: [targetTopic],

        difficulties: [targetDifficulty],

        target_topic: targetTopic,

        target_difficulty: targetDifficulty,

        assessment_type: assessmentType,

        count: assessmentType === 'theoretical' ? 10 : 3

      };



      const session = await api.generatePythonSession(payload);

      if (!session.items || session.items.length === 0) {

        this.showToast("Aucune question ou exercice disponible pour ce chapitre et ce palier de difficulté.", "warning");

        return;

      }



      this.launchUnifiedPythonExam(session, sessionTitle);



    } catch (err) {

      this.showToast(`Erreur lors de la préparation de la session : ${err.message}`, "danger");

    }

  }



  // --- Lancement d'une Session Python dans l'ExamRunner Unifié (Même interface que les examens) ---

  launchUnifiedPythonExam(session, title) {

    this.activeOriginView = 'view-python';

    window.pythonHintsUsed = {};



    const questions = session.items.map((q, idx) => {

      if (q.type === 'coding' || q.type === 'code') {

        let pMd = q.prompt_markdown || q.prompt || q.description || '';

        pMd = pMd.replace(/\*?Écrivez votre fonction\/script Python ci-dessous et testez son exécution locale\s*:?\*?/gi, '').trim();

        return {

          id: q.id,

          title: q.title || '',

          topic: q.topic || '',

          type: 'coding',

          points: q.points || 4.0,

          prompt_markdown: pMd,

          starter_code: q.starter_code || '# Écrivez votre code Python ici\n',

          public_tests: q.public_tests || [],

          hint1: q.hint1 || '',

          hint2: q.hint2 || ''

        };

      }



      // Traitement exhaustif de tous les types théoriques (REV-05, REV-07)

      let qType = q.type || 'single_choice';

      if (qType === 'yesno') qType = 'boolean';

      else if (qType === 'intruder') qType = 'single_choice';

      else if (qType === 'simple_blank') qType = 'fill_blank';

      else if (qType === 'mcq') {

        qType = (Array.isArray(q.correct) && q.correct.length > 1) ? 'multi_choice' : 'single_choice';

      }



      let formattedOpts = q.options;

      if (Array.isArray(q.options)) {

        formattedOpts = q.options.map((opt, oIdx) => {

          if (typeof opt === 'object' && opt !== null) {

            return { id: opt.id !== undefined ? opt.id : oIdx, text: opt.text || opt.label || '' };

          }

          return { id: oIdx, text: String(opt) };

        });

      }



      const promptTitle = q.topic ? `**[${q.topic} • Difficulté : ${q.difficulty || 'medium'}]**\n\n` : '';

      const promptText = q.prompt_markdown || q.prompt || q.question || '';



      return {

        id: q.id,

        type: qType,

        points: q.points || 1.0,

        prompt_markdown: promptText.startsWith('**[') ? promptText : `${promptTitle}${promptText}`,

        options: formattedOpts,

        pairs: q.pairs || (typeof q.options === 'object' && !Array.isArray(q.options) ? q.options : undefined)

      };

    });



    const examData = {

      attempt_id: null,

      exam_title: title,

      questions: questions,

      saved_answers: {},

      remaining_seconds: session.time_limit_seconds || (20 * 60)

    };



    if (this.activeExamRunner) {

      this.activeExamRunner.stop();

    }

    if (this.activeAntiCheat) {

      this.activeAntiCheat.stop();

      this.activeAntiCheat = null;

    }

    this.hideSuspensionScreen();



    // Mode plein écran facultatif (autres onglets autorisés)

    if (document.documentElement.requestFullscreen) {

      document.documentElement.requestFullscreen().catch(() => {});

    }

    this._updateFullscreenButtonText();



    this.activeExamRunner = new ExamRunner(examData, {

      isPracticeMode: true,

      onPracticeSubmit: async (answers) => {

        const submitAnswers = session.items.map(q => {

          return {

            id: q.id,

            type: q.type,

            topic: q.topic || session.target_topic || 'python_basics',

            difficulty: q.difficulty || session.target_difficulty || 'medium',

            student_answer: answers[q.id] !== undefined ? answers[q.id] : null,

            hints_used: (window.pythonHintsUsed && window.pythonHintsUsed[q.id]) || 0,

            is_correct: (window.codingValidationPassed && window.codingValidationPassed[q.id]) ? true : null

          };

        });



        try {

          const res = await api.submitPythonSession({

            assessment_type: session.assessment_type || 'training',

            selected_topics: session.selected_topics || [session.target_topic].filter(Boolean),

            selected_difficulties: session.selected_difficulties || [session.target_difficulty].filter(Boolean),

            target_topic: session.target_topic,

            target_difficulty: session.target_difficulty,

            answers: submitAnswers

          });



          // Notifier l'étudiant en cas de montée de niveau XP ou nouveau badge

          if (res.level_up) {

            this.showToast(`🎉 FÉLICITATIONS ! Vous passez au Niveau ${res.gamification.level} (${res.gamification.level_name}) !`, "success", 6000);

          }

          if (res.new_badges && res.new_badges.length > 0) {

            const badgeNames = res.new_badges.map(b => `${b.emoji} ${b.name}`).join('\n• ');

            this.showToast(`🏆 NOUVEAU(X) BADGE(S) DÉBLOQUÉ(S) :\n• ${badgeNames}`, "success", 6000);

          }



          // Afficher la page de corrigé et de résultat avec les vraies réponses (REV-06)

          this.renderPracticeResults({

            module_title: title,

            grade_20: res.final_mark,

            percentage: res.percentage,

            total_awarded: res.final_mark,

            max_possible: 20.0,

            detailed_results: (res.feedback || []).map(f => {

              const matchedQ = session.items.find(item => String(item.id) === String(f.id));

              const fullPrompt = matchedQ ? (matchedQ.prompt_markdown || matchedQ.prompt || matchedQ.question || matchedQ.description) : null;

              const userAns = f.user_answer !== undefined ? f.user_answer : (answers[f.id] !== undefined ? answers[f.id] : 'Non répondu');

              return {

                question_id: String(f.id),

                prompt_markdown: fullPrompt || `**${f.topic}** (${f.type === 'coding' ? 'Exercice de programmation' : 'Question Théorique'})`,

                type: f.type,

                user_answer: userAns,

                correct_answer: f.solution ? (typeof f.solution === 'string' ? f.solution : JSON.stringify(f.solution)) : 'Validé',

                awarded_points: f.awarded_points,

                max_points: f.max_points,

                is_correct: f.is_correct,

                explanation: f.explanation || (f.is_correct ? '✅ Validé avec succès !' : (f.solution ? `Corrigé attendu : ${typeof f.solution === 'string' ? f.solution : JSON.stringify(f.solution)}` : 'À perfectionner.'))

              };

            })

          });



        } catch (err) {

          this.showToast(`Erreur de validation de la session Python : ${err.message}`, "danger");

        }

      }

    });



    window.activeExamRunner = this.activeExamRunner;

    this.switchView('view-exam');

    document.getElementById('exam-active-title').textContent = title;



    // Dispositif Anti-Triche : Protocole des 4 avertissements et décompte de 10s hors plein écran

    this.activeAntiCheat = new AntiCheatManager(null, {

      isPracticeMode: true,

      maxWarnings: 4,

      onWarning: (count, max, reason) => {

        this._updateWarningBadge(count, max);

        this.showWarningToast(`⚠️ Avertissement ${count}/${max} : ${reason}. Si ${max} avertissements sont atteints, le test prend fin et vos résultats sont enregistrés.`);

      },

      onMaxWarningsReached: async (reason) => {

        this._updateWarningBadge(4, 4);

        this.showToast("⚠️ 4 avertissements atteints : Le test prend fin immédiatement. Vos résultats sont enregistrés.", "danger", 6000);

        if (this.activeExamRunner) {

          await this.activeExamRunner.submit();

        }

      }

    });



    this.activeAntiCheat.start();

    this._updateWarningBadge(0, 4);



    const quitBtn = document.getElementById('btn-exam-quit');

    if (quitBtn) {

      quitBtn.style.display = 'inline-flex';

      quitBtn.onclick = async () => {

        const destName = this.activeOriginView === 'view-linux' ? 'Centre Linux' : 'Centre Python';

        const ok = await this.showConfirmModal({

          title: `Quitter vers le ${destName}`,

          message: `Voulez-vous quitter cette session et retourner au ${destName} ? Vos réponses en cours ne seront pas enregistrées.`,

          confirmText: "Quitter la session",

          cancelText: "Continuer",

          icon: "⚠️",

          danger: true

        });

        if (ok) {

          if (this.activeExamRunner) this.activeExamRunner.stop();

          if (this.activeAntiCheat) this.activeAntiCheat.stop();

          if (this.activeOriginView === 'view-linux') {

            this.renderLinuxTrainingCenter();

          } else {

            this.renderTrainingCenterView();

          }

        }

      };

    }

    this.activeExamRunner.start();

  }



  // --- Modal : Historique Complet des Tests de Niveau ---

  async openPracticeHistoryModal(moduleFilter = null) {

    const modal = document.getElementById('modal-practice-history');

    if (modal) modal.classList.add('active');



    const tbody = document.getElementById('practice-history-table-body');

    if (!tbody) return;



    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement de l\'historique...</td></tr>';



    try {

      const data = await api.getPracticeHistory();

      tbody.innerHTML = '';



      let list = data.attempts || [];

      if (moduleFilter) {

        list = list.filter(a => a.module_code.toUpperCase() === moduleFilter.toUpperCase());

      }



      if (list.length === 0) {

        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-muted);">Aucune tentative enregistrée pour ${moduleFilter || 'les tests de niveau'}.</td></tr>`;

        return;

      }



      list.forEach(a => {

        const row = document.createElement('tr');

        const dt = new Date(a.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });

        const markColor = a.grade_20 >= 14 ? 'var(--success)' : (a.grade_20 >= 10 ? '#60a5fa' : 'var(--danger)');



        row.innerHTML = `

          <td style="font-family:var(--font-mono); font-size:0.85rem;">${dt}</td>

          <td>

            <span style="font-weight:600; color:var(--text-primary);">${this._escapeHtml(a.module_title)}</span>

          </td>

          <td><strong style="font-family:var(--font-mono); font-size:1.05rem; color:${markColor};">${a.grade_20.toFixed(2)}</strong> / 20</td>

          <td style="font-family:var(--font-mono);">${a.percentage.toFixed(1)}%</td>

          <td>

            <span class="user-tag" style="${a.warnings_count > 0 ? 'background:rgba(239,68,68,0.15); color:#fca5a5;' : ''}">

              ${a.warnings_count || 0} / 4

            </span>

          </td>

          <td>

            <span class="mastery-pill ${a.passed ? 'mastery-expert' : (a.grade_20 >= 10 ? 'mastery-acquired' : 'mastery-none')}">

              ${a.passed ? '✅ Validé (≥ 14)' : (a.grade_20 >= 10 ? 'Admis (≥ 10)' : 'À renforcer')}

            </span>

          </td>

        `;

        tbody.appendChild(row);

      });



    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger); padding:20px; text-align:center;">Erreur : ${err.message}</td></tr>`;

    }

  }



  // --- Modal : Galerie des 68 Badges & Milestones ---

  async openBadgesGalleryModal() {

    const modal = document.getElementById('modal-badges-gallery');

    if (modal) modal.classList.add('active');



    const container = document.getElementById('badges-gallery-grid');

    if (!container) return;



    container.innerHTML = '<div style="color:var(--text-muted); padding:20px;">Chargement des badges...</div>';



    try {

      const data = await api.getPythonProgression();

      this.lastBadgesList = data.gamification.all_milestones || [];

      this.filterBadgesGallery('all');

    } catch (err) {

      container.innerHTML = `<div style="color:var(--danger); padding:20px;">Erreur : ${err.message}</div>`;

    }

  }



  filterBadgesGallery(filter = 'all') {

    const container = document.getElementById('badges-gallery-grid');

    if (!container || !this.lastBadgesList) return;



    let items = this.lastBadgesList;

    if (filter === 'theo') {

      items = items.filter(m => m.id.includes('theo'));

    } else if (filter === 'prac') {

      items = items.filter(m => m.id.includes('prac'));

    } else if (filter === 'unlocked') {

      items = items.filter(m => m.unlocked === true);

    }



    container.innerHTML = '';

    if (items.length === 0) {

      container.innerHTML = '<div style="color:var(--text-muted); padding:20px;">Aucun badge dans cette catégorie pour le moment.</div>';

      return;

    }



    items.forEach(m => {

      const card = document.createElement('div');

      card.className = `badge-card ${m.unlocked ? 'badge-card-unlocked' : 'badge-card-locked'}`;

      card.innerHTML = `

        <div class="badge-icon">${m.emoji}</div>

        <div class="badge-title">${this._escapeHtml(m.name)}</div>

        <div class="badge-desc">${this._escapeHtml(m.desc)}</div>

        <div class="badge-footer">

          <span class="badge-points">+${m.points} XP</span>

          <span class="badge-status">${m.unlocked ? '✓ Obtenu' : '🔒 Verrouillé'}</span>

        </div>

      `;

      container.appendChild(card);

    });

  }



  // --- Modal : Historique des Entraînements Python ---

  async openPythonHistoryModal() {

    const modal = document.getElementById('modal-python-history');

    if (modal) modal.classList.add('active');



    const tbody = document.getElementById('python-history-table-body');

    if (!tbody) return;



    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement de l\'historique Python...</td></tr>';



    try {

      const data = await api.getPythonHistory();

      tbody.innerHTML = '';



      const attempts = data.attempts || [];

      if (attempts.length === 0) {

        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-muted);">Aucun entraînement Python enregistré pour le moment.</td></tr>';

        return;

      }



      attempts.slice().reverse().forEach(a => {

        const row = document.createElement('tr');

        const dt = new Date(a.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });

        const typeLabel = a.assessment_type === 'practical' ? '💻 Lab Pratique (Code)' : (a.assessment_type === 'theoretical' ? '📖 Quiz Théorique (QCM)' : '🔀 Mixte');

        const isPassed = a.final_mark >= 14.0;



        row.innerHTML = `

          <td style="font-family:var(--font-mono); font-size:0.85rem;">${dt}</td>

          <td><span class="user-tag" style="font-weight:600;">${typeLabel}</span></td>

          <td><strong style="font-family:var(--font-mono); font-size:1.05rem; color:${isPassed ? 'var(--success)' : '#60a5fa'};">${a.final_mark.toFixed(2)}</strong> / 20</td>

          <td style="font-family:var(--font-mono);">${a.percentage.toFixed(1)}%</td>

          <td>${a.correct_count} / ${a.total_questions}</td>

          <td>

            <span class="mastery-pill ${isPassed ? 'mastery-expert' : 'mastery-progression'}">

              ${isPassed ? 'Validé (≥ 14)' : 'À renforcer'}

            </span>

          </td>

        `;

        tbody.appendChild(row);

      });



    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--danger); padding:20px; text-align:center;">Erreur : ${err.message}</td></tr>`;

    }

  }



  // --- Gestion Générique des Modals ---
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
  }



  closeActiveModal() {

    const activeModals = document.querySelectorAll('.modal-overlay.active, .modal-backdrop.active, .modal.active, [id^="modal-"].active');

    activeModals.forEach(modal => {

      modal.classList.remove('active');

    });

  }



  // --- Lancement d'un Examen Officiel (avec Salle d'Attente Interactive REV-25) ---

  async launchOfficialExam(examId) {

    this.activeOriginView = 'view-student';

    // Activation synchrone immédiate du plein écran sur le geste utilisateur

    this.requestFullscreen();

    try {

      const examData = await api.startOrResumeExam(examId);



      // Si la session de salle est en attente du feu vert du surveillant

      if (examData.status === 'waiting') {

        if (this.waitingRoomInterval) {

          clearInterval(this.waitingRoomInterval);

        }

        this.switchView('view-waiting-room');

        this.requestFullscreen();



        const examTitleEl = document.getElementById('waiting-room-exam-title');

        if (examTitleEl) examTitleEl.textContent = examData.exam_title || 'Examen Officiel';

        const roomTagEl = document.getElementById('waiting-room-room-tag');

        if (roomTagEl) roomTagEl.textContent = `🏢 Salle : ${examData.room_id || 'SALLE-TP-1'}`;

        const durationEl = document.getElementById('waiting-room-duration');

        if (durationEl) durationEl.textContent = `⏱️ Durée : ${examData.duration_minutes || 45} min`;

        const statusEl = document.getElementById('waiting-room-status');

        if (statusEl) statusEl.textContent = '🟢 Statut : Poste Connecté & Enregistré';

        const clockEl = document.getElementById('waiting-room-server-clock');

        if (clockEl && examData.server_time_hms) {

          clockEl.textContent = `🕒 Heure Serveur : ${examData.server_time_hms} UTC`;

        }



        const leaveBtn = document.getElementById('btn-waiting-room-leave');

        if (leaveBtn) {

          leaveBtn.onclick = async () => {

            const confirmLeave = await this.showConfirmModal({

              title: "Quitter la Salle d'Attente",

              message: "⚠️ Attention : L'épreuve officielle va débuter sous peu.\n\nÊtes-vous certain de vouloir quitter la salle d'attente ?",

              confirmText: "Quitter la salle",

              cancelText: "Rester connecté",

              icon: "⏳",

              danger: true

            });

            if (!confirmLeave) {

              this.requestFullscreen();

              return;

            }

            if (this.waitingRoomInterval) {

              clearInterval(this.waitingRoomInterval);

              this.waitingRoomInterval = null;

            }

            const waitingView = document.getElementById('view-waiting-room');

            if (waitingView) waitingView.classList.remove('exam-fullscreen-lost-blurred');

            const overlayFs = document.getElementById('overlay-fullscreen-required');

            if (overlayFs) overlayFs.classList.remove('active');

            this.exitFullscreen();

            this.renderStudentDashboard();

          };

        }



        // Écoute automatique / polling (toutes les 2s) du feu vert officiel du surveillant

        this.waitingRoomInterval = setInterval(async () => {

          try {

            const pollData = await api.startOrResumeExam(examId);

            if (pollData && pollData.server_time_hms && clockEl) {

              clockEl.textContent = `🕒 Heure Serveur : ${pollData.server_time_hms} UTC`;

            }

            if (pollData && pollData.status !== 'waiting' && pollData.questions && pollData.questions.length > 0) {

              clearInterval(this.waitingRoomInterval);

              this.waitingRoomInterval = null;

              const waitingView = document.getElementById('view-waiting-room');

              if (waitingView) waitingView.classList.remove('exam-fullscreen-lost-blurred');

              const overlayFs = document.getElementById('overlay-fullscreen-required');

              if (overlayFs) overlayFs.classList.remove('active');

              this._proceedLaunchOfficialExam(pollData);

            }

          } catch (_) {}

        }, 2000);

        return;

      }



      this._proceedLaunchOfficialExam(examData);

    } catch (err) {

      this.showToast(`Impossible de démarrer l'épreuve : ${err.message}`, "danger");

    }

  }



  _proceedLaunchOfficialExam(examData) {

    if (examData.attempt_status === 'suspended') {

      this.showSuspensionScreen("Votre épreuve a été suspendue précédemment. Attendez que le surveillant la débloque.");

    }



    this.switchView('view-exam');

    document.getElementById('exam-active-title').textContent = examData.exam_title;

    const badge = document.getElementById('exam-mode-badge');

    if (badge) {

      badge.textContent = "● Session Sécurisée Officielle (Plein Écran Obligatoire • Surveillance Active)";

      badge.style.background = "rgba(16, 185, 129, 0.15)";

      badge.style.color = "#6ee7b7";

      badge.style.borderColor = "var(--success)";

    }

    const quitBtn = document.getElementById('btn-exam-quit');

    if (quitBtn) quitBtn.style.display = 'none';

    this._updateFullscreenButtonText();



    // 1. Initialisation Anti-Triche avec règle des 4 avertissements (REV-29)

    this.activeAntiCheat = new AntiCheatManager(examData.attempt_id, {

      maxWarnings: 4,

      onSuspended: (reason) => this.showSuspensionScreen(reason),

      onUnlocked: () => this.hideSuspensionScreen(),

      onWarning: (count, max, reason) => {

        this._updateWarningBadge(count, max);

        this.showWarningToast(`⚠️ Avertissement ${count}/${max} : ${reason}. Au 4e avertissement, l'épreuve est suspendue.`);

      },

      onMaxWarningsReached: async (reason) => {

        this._updateWarningBadge(4, 4);

        this.showSuspensionScreen("⚠️ 4 avertissements anti-triche atteints. Votre poste a été verrouillé. Veuillez contacter votre surveillant pour déblocage.");

      }

    });



    // 2. Initialisation Runner

    if (this.activeExamRunner) {

      this.activeExamRunner.stop();

    }



    this.activeExamRunner = new ExamRunner(examData, {

      antiCheat: this.activeAntiCheat,

      onFinish: (result) => this.renderScoreScreen(result)

    });



    window.activeExamRunner = this.activeExamRunner;



    this.activeAntiCheat.start();

    this.activeExamRunner.start();

  }



  showSuspensionScreen(reason) {

    const overlay = document.getElementById('overlay-suspension');

    const reasonText = document.getElementById('suspension-reason-text');

    if (reasonText) reasonText.textContent = reason;

    if (overlay) overlay.classList.add('active');

  }



  hideSuspensionScreen() {

    const overlay = document.getElementById('overlay-suspension');

    if (overlay) overlay.classList.remove('active');

  }



  // --- Lancement d'un Test de Niveau par Module (Mode Examen 1 Question/Page) ---

  async launchPracticeExam(moduleCode) {

    try {

      const data = await api.getPracticeQuestions(moduleCode);



      const examData = {

        attempt_id: null,

        exam_title: `Test de Niveau : ${data.module_title}`,

        questions: data.questions,

        saved_answers: {},

        remaining_seconds: 30 * 60

      };



      if (this.activeExamRunner) {

        this.activeExamRunner.stop();

      }

      // Désactiver tout dispositif anti-triche préalable pour la pratique libre

      if (this.activeAntiCheat) {

        this.activeAntiCheat.stop();

        this.activeAntiCheat = null;

      }

      this.hideSuspensionScreen();



      // Tentative d'activation du plein écran (l'étudiant reste libre de basculer d'onglet)

      if (document.documentElement.requestFullscreen) {

        document.documentElement.requestFullscreen().catch(() => {});

      }

      this._updateFullscreenButtonText();



      this.activeExamRunner = new ExamRunner(examData, {

        isPracticeMode: true,

        onPracticeSubmit: async (answers) => {

          try {

            const warningsCount = this.activeAntiCheat ? this.activeAntiCheat.warningCount : 0;

            const questionIds = (data.questions || []).map(q => q.id);

            const res = await api.submitPracticeExam(moduleCode, answers, warningsCount, questionIds);

            this.renderPracticeResults(res);

          } catch (err) {

            this.showToast(`Erreur de validation : ${err.message}`, "danger");

          }

        }

      });



      window.activeExamRunner = this.activeExamRunner;

      this.switchView('view-exam');

      document.getElementById('exam-active-title').textContent = `Test de Niveau : ${data.module_title}`;



      // Dispositif Anti-Triche : Protocole des 4 avertissements

      this.activeAntiCheat = new AntiCheatManager(null, {

        isPracticeMode: true,

        maxWarnings: 4,

        onWarning: (count, max, reason) => {

          this._updateWarningBadge(count, max);

          this.showWarningToast(`⚠️ Avertissement ${count}/${max} : ${reason}. Si ${max} avertissements sont atteints, le test prend fin et vos résultats sont enregistrés.`);

        },

        onMaxWarningsReached: async (reason) => {

          this._updateWarningBadge(4, 4);

          this.showToast("⚠️ 4 avertissements atteints : Le test prend fin immédiatement. Vos résultats sont enregistrés.", "danger", 6000);

          if (this.activeExamRunner) {

            await this.activeExamRunner.submit();

          }

        }

      });



      this.activeAntiCheat.start();

      this._updateWarningBadge(0, 4);



      const quitBtn = document.getElementById('btn-exam-quit');

      if (quitBtn) {

        quitBtn.style.display = 'inline-flex';

        quitBtn.onclick = async () => {

          const ok = await this.showConfirmModal({

            title: "Quitter le Test de Niveau",

            message: "Voulez-vous quitter ce test de niveau et retourner au tableau de bord ? Vos réponses en cours ne seront pas enregistrées.",

            confirmText: "Quitter",

            cancelText: "Continuer",

            icon: "🎯",

            danger: true

          });

          if (ok) {

            if (this.activeExamRunner) this.activeExamRunner.stop();

            if (this.activeAntiCheat) this.activeAntiCheat.stop();

            this.renderDashboard(this.currentUser);

          }

        };

      }



      this.activeExamRunner.start();



    } catch (err) {

      this.showToast(`Erreur de chargement du test de niveau : ${err.message}`, "danger");

    }

  }



  // --- Rendu des Résultats de Test de Niveau avec Corrigé Pédagogique (REV-17, REV-18, REV-20) ---

  renderPracticeResults(res) {

    this.switchView('view-score');

    document.getElementById('score-title').textContent = `Résultat : ${res.module_title}`;

    document.getElementById('score-grade').textContent = `${res.grade_20} / 20`;

    document.getElementById('score-percentage').textContent = `${res.percentage}% de réussite (${res.total_awarded} / ${res.max_possible} pts)`;



    const backBtn = document.getElementById('btn-score-back-dashboard');

    const statsBtn = document.getElementById('btn-score-view-stats');

    if (this.activeOriginView === 'view-linux' || (res && res.module_title && res.module_title.toLowerCase().includes('linux'))) {

      if (backBtn) {

        backBtn.style.display = 'inline-flex';

        backBtn.innerHTML = 'Retourner au Centre d\'Entraînement Linux ➔';

        backBtn.onclick = () => this.renderLinuxTrainingCenter();

      }

      if (statsBtn) {

        statsBtn.style.display = 'none';

      }

    } else if (this.activeOriginView === 'view-python' || (res && res.module_title && res.module_title.toLowerCase().includes('python'))) {

      if (backBtn) {

        backBtn.style.display = 'inline-flex';

        backBtn.innerHTML = '⬅️ Retourner au Centre d\'Entraînement Python';

        backBtn.onclick = () => this.renderTrainingCenterView();

      }

      if (statsBtn) {

        statsBtn.style.display = 'none';

      }

    } else {

      if (backBtn) {

        backBtn.style.display = 'inline-flex';

        backBtn.innerHTML = 'Retourner au Tableau de Bord ➔';

        backBtn.onclick = () => this.renderStudentDashboard();

      }

      if (statsBtn) {

        statsBtn.style.display = 'inline-flex';

      }

    }



    const breakdownBox = document.getElementById('score-detailed-breakdown');

    breakdownBox.innerHTML = '<h3 style="margin-bottom:16px;">Corrigé Pédagogique Détaillé</h3>';



    res.detailed_results.forEach((r, idx) => {

      const card = document.createElement('div');

      card.className = 'question-card';

      card.style.width = '100%';

      card.style.borderLeft = r.is_correct ? '4px solid var(--success)' : '4px solid var(--danger)';



      // Détection de code Python multi-lignes (REV-17)

      const isCoding = r.type === 'coding' || r.type === 'code' ||

        (typeof r.user_answer === 'string' && (r.user_answer.includes('\n') || r.user_answer.includes('def ') || r.user_answer.includes('print(') || r.user_answer.includes('input('))) ||

        (typeof r.correct_answer === 'string' && (r.correct_answer.includes('\n') || r.correct_answer.includes('def ')));



      // Détection d'association / matching (REV-18)

      let isMatching = r.type === 'matching';

      let userMatches = null;

      let corrMatches = null;



      if (!isCoding) {

        if (typeof r.user_answer === 'object' && r.user_answer !== null && !Array.isArray(r.user_answer)) {

          userMatches = r.user_answer;

          isMatching = true;

        } else if (typeof r.user_answer === 'string' && r.user_answer.trim().startsWith('{') && r.user_answer.trim().endsWith('}')) {

          try {

            userMatches = JSON.parse(r.user_answer);

            isMatching = true;

          } catch (_) {}

        }



        if (typeof r.correct_answer === 'object' && r.correct_answer !== null && !Array.isArray(r.correct_answer)) {

          corrMatches = r.correct_answer;

          isMatching = true;

        } else if (typeof r.correct_answer === 'string' && r.correct_answer.trim().startsWith('{') && r.correct_answer.trim().endsWith('}')) {

          try {

            corrMatches = JSON.parse(r.correct_answer);

            isMatching = true;

          } catch (_) {}

        }

      }



      let answerDisplayHtml = '';



      if (isCoding) {

        // Formatage élargi avec <pre><code class="python-code-block"> (REV-17)

        answerDisplayHtml = `

          <div style="margin-top:8px;">

            <div style="font-weight:600; color:#fcd34d; font-size:0.85rem; margin-bottom:4px;">💻 Votre code Python soumis :</div>

            <pre class="python-code-block"><code>${this._escapeHtml(r.user_answer || '# Aucun code soumis')}</code></pre>

          </div>

          <div style="margin-top:10px;">

            <div style="font-weight:600; color:#6ee7b7; font-size:0.85rem; margin-bottom:4px;">✨ Solution de référence attendue :</div>

            <pre class="python-code-block"><code>${this._escapeHtml(r.correct_answer || '# Solution validée')}</code></pre>

          </div>

        `;

      } else if (isMatching && corrMatches && typeof corrMatches === 'object') {

        // Formatage élégant en grille de badges pour l'association (REV-18)

        const entries = Object.entries(corrMatches);

        answerDisplayHtml = `

          <div style="margin-top:8px;">

            <div style="font-weight:600; color:#93c5fd; font-size:0.85rem; margin-bottom:6px;">🔗 Correspondances évaluées :</div>

            <div class="matching-badges-grid">

              ${entries.map(([leftK, rightExpected]) => {

                const rightUser = userMatches ? userMatches[leftK] : null;

                const isPairCorrect = rightUser !== undefined && rightUser !== null && String(rightUser).trim() === String(rightExpected).trim();

                return `

                  <div class="matching-badge-card ${isPairCorrect ? 'is-correct' : 'is-incorrect'}">

                    <div style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono); font-size:0.88rem;">${this._escapeHtml(leftK)}</div>

                    <div style="display:flex; align-items:center; gap:6px; color:${isPairCorrect ? '#6ee7b7' : '#f87171'}; font-size:0.82rem; margin-top:2px;">

                      <span>${isPairCorrect ? '✅' : '❌'}</span>

                      <strong>${this._escapeHtml(rightUser || '(Non associé)')}</strong>

                    </div>

                    ${!isPairCorrect ? `<div style="font-size:0.75rem; color:#6ee7b7; margin-top:4px;">Attendu : <strong>${this._escapeHtml(rightExpected)}</strong></div>` : ''}

                  </div>

                `;

              }).join('')}

            </div>

          </div>

        `;

      } else {

        // Format standard pour QCU, QCM, Vrai/Faux, Fill Blank

        answerDisplayHtml = `

          <div><strong>Votre réponse :</strong> <span style="color:#fcd34d;">${this._formatAnswerValue(r.user_answer)}</span></div>

          <div><strong>Réponse exacte attendue :</strong> <span style="color:#6ee7b7;">${this._formatAnswerValue(r.correct_answer)}</span></div>

        `;

      }



      card.innerHTML = `

        <div style="font-weight:700; margin-bottom:8px; color:${r.is_correct ? 'var(--success)' : 'var(--danger)'}; display:flex; justify-content:space-between; align-items:center;">

          <span>${r.is_correct ? '✅ Réponse Correcte' : '❌ Réponse Incorrecte'} — Question ${idx + 1}</span>

          <span class="question-points">${r.awarded_points} / ${r.max_points} pts</span>

        </div>

        <div style="font-size:0.95rem; margin-bottom:12px; line-height:1.5;">${this._renderSimpleMarkdown(r.prompt_markdown)}</div>

        <div style="font-size:0.85rem; color:var(--text-secondary); background:var(--bg-primary); padding:12px 16px; border-radius:var(--radius-sm); line-height:1.6; border:1px solid rgba(255,255,255,0.06);">

          ${answerDisplayHtml}

          <div style="margin-top:8px; color:#93c5fd; padding-top:6px; border-top:1px solid rgba(255,255,255,0.05);">

            <strong>Explication :</strong> ${this._renderSimpleMarkdown(r.explanation || (r.is_correct ? 'Bonne réponse !' : 'À revoir.'))}

          </div>

        </div>

      `;

      breakdownBox.appendChild(card);

    });



    // Rendu dynamique des formules mathématiques LaTeX (KaTeX) dans les explications et énoncés

    if (window.renderMathInElement) {

      try {

        window.renderMathInElement(breakdownBox, {

          delimiters: [

            { left: '$$', right: '$$', display: true },

            { left: '$', right: '$', display: false },

            { left: '\\(', right: '\\)', display: false },

            { left: '\\[', right: '\\]', display: true }

          ],

          throwOnError: false

        });

      } catch (_) {}

    }

  }



  _formatAnswerValue(val) {

    if (val === null || val === undefined || val === '') return '<em>Aucune réponse</em>';

    if (val === true || val === 'true') return '<strong>Vrai</strong>';

    if (val === false || val === 'false') return '<strong>Faux</strong>';

    if (typeof val === 'object') {

      if (Array.isArray(val)) {

        return val.length ? val.map(v => `<code>${this._escapeHtml(String(v))}</code>`).join(', ') : '<em>Aucune sélection</em>';

      }

      const entries = Object.entries(val);

      if (!entries.length) return '<em>Aucune association</em>';

      return entries.map(([k, v]) => `<code>${this._escapeHtml(k)}</code> ➔ <strong>${this._escapeHtml(v)}</strong>`).join(' | ');

    }

    return `<code>${this._escapeHtml(String(val))}</code>`;

  }



  handleExamForcedClosure(data = {}) {
    console.warn("[AppController] Clôture collective ou soumission forcée déclenchée :", data);
    this.hideSuspensionScreen();
    const overlayFs = document.getElementById('overlay-fullscreen-required');
    if (overlayFs) overlayFs.classList.remove('active');
    document.querySelectorAll('.exam-fullscreen-lost-blurred').forEach(el => {
      el.classList.remove('exam-fullscreen-lost-blurred');
    });

    if (this.activeAntiCheat) {
      this.activeAntiCheat.stop();
      this.activeAntiCheat = null;
    }

    if (this.activeExamRunner) {
      this.activeExamRunner.stop();
      this.activeExamRunner = null;
    }

    if (this._studentWs) {
      try { this._studentWs.close(); } catch (_) {}
      this._studentWs = null;
    }

    const finalResult = {
      title: data.exam_title || "Épreuve Officielle",
      final_mark: data.final_mark !== undefined ? data.final_mark : (data.score !== undefined ? data.score : 0),
      raw_score: data.raw_score !== undefined ? data.raw_score : (data.final_mark !== undefined ? data.final_mark : 0),
      global_points: data.global_points || 20,
      max_score: data.global_points || 20,
      message: "🛑 Épreuve clôturée par l'enseignant. Vos réponses enregistrées ont été scellées et transmises."
    };

    this.renderScoreScreen(finalResult);
    this.showToast("🛑 L'épreuve est terminée. Vos résultats officiels sont enregistrés.", "warning", 8000);
  }

  // --- Rendu du Score et Confirmation d'Épreuve Officielle Scellée (REV-32) ---

  renderScoreScreen(res) {

    this.hideSuspensionScreen();

    const overlayFs = document.getElementById('overlay-fullscreen-required');

    if (overlayFs) overlayFs.classList.remove('active');

    document.querySelectorAll('.exam-fullscreen-lost-blurred').forEach(el => {

      el.classList.remove('exam-fullscreen-lost-blurred');

    });

    this.switchView('view-score');

    const titleElem = document.getElementById('score-title');

    const gradeElem = document.getElementById('score-grade');

    const pctElem = document.getElementById('score-percentage');

    const breakdownBox = document.getElementById('score-detailed-breakdown');

    const backBtn = document.getElementById('btn-score-back-dashboard');

    const statsBtn = document.getElementById('btn-score-view-stats');



    if (titleElem) {

      titleElem.textContent = res.title ? `Épreuve Officielle : ${res.title}` : `Épreuve Officielle Soumise`;

    }



    const finalMark = res.final_mark !== undefined ? res.final_mark : (res.raw_score !== undefined ? res.raw_score : 0);

    const globalPts = res.global_points !== undefined ? res.global_points : 20;

    const maxScore = res.max_score || globalPts;

    const rawScore = res.raw_score !== undefined ? res.raw_score : finalMark;

    const pct = (maxScore > 0) ? Math.round((rawScore / maxScore) * 100) : 0;



    if (gradeElem) gradeElem.textContent = `${Number(finalMark).toFixed(2)} / ${globalPts}`;

    if (pctElem) pctElem.textContent = `${pct}% de réussite (${Number(rawScore).toFixed(2)} / ${maxScore} pts)`;



    if (this.activeOriginView === 'view-linux' || (res && res.title && res.title.toLowerCase().includes('linux') && !res.attempt_id)) {

      if (backBtn) {

        backBtn.style.display = 'inline-flex';

        backBtn.innerHTML = 'Retourner au Centre d\'Entraînement Linux ➔';

        backBtn.onclick = () => this.renderLinuxTrainingCenter();

      }

      if (statsBtn) statsBtn.style.display = 'none';

    } else if (this.activeOriginView === 'view-python' || (res && res.title && res.title.toLowerCase().includes('python') && !res.attempt_id)) {

      if (backBtn) {

        backBtn.style.display = 'inline-flex';

        backBtn.innerHTML = 'Retourner au Centre d\'Entraînement Python ➔';

        backBtn.onclick = () => this.renderTrainingCenterView();

      }

      if (statsBtn) statsBtn.style.display = 'none';

    } else {

      if (backBtn) {

        backBtn.style.display = 'inline-flex';

        backBtn.innerHTML = 'Retourner au Tableau de Bord ➔';

        backBtn.onclick = () => this.renderStudentDashboard();

      }

      if (statsBtn) statsBtn.style.display = 'inline-flex';

    }



    if (breakdownBox) {

      breakdownBox.innerHTML = `

        <div style="text-align:center; padding: 28px 20px; background: rgba(16, 185, 129, 0.08); border: 2px solid var(--success); border-radius: var(--radius-lg); margin-top: 20px;">

          <div style="font-size: 2.2rem; margin-bottom: 8px;">📋🔒</div>

          <h3 style="color: var(--success); margin: 0 0 10px 0; font-size: 1.35rem;">Épreuve Officielle Scellée avec Succès</h3>

          <p style="color: var(--text-secondary); max-width: 650px; margin: 0 auto 16px auto; font-size: 1rem; line-height: 1.5;">

            Votre copie a été enregistrée de manière immuable sur le serveur de salle.<br/>

            Note officielle attribuée : <strong style="color:#60a5fa; font-size:1.15rem;">${Number(finalMark).toFixed(2)} / ${globalPts}</strong>.

          </p>

          <div style="font-size: 0.85rem; color: var(--text-muted); font-family: var(--font-mono);">

            Statut : SOUMIS & VERROUILLÉ • Date de scellement : ${res.submitted_at ? new Date(res.submitted_at).toLocaleString('fr-FR') : new Date().toLocaleString('fr-FR')}

          </div>

          ${res.attempt_id ? `
            <div style="margin-top: 20px;">
              <button id="btn-score-consult-review" class="btn btn-primary" style="padding: 10px 22px; font-weight: 700; font-size: 0.95rem; display: inline-flex; align-items: center; gap: 8px; border-radius: 8px; box-shadow: 0 4px 12px rgba(37,99,235,0.25);">
                <span>🔍</span> Consulter le Corrigé &amp; Mes Réponses
              </button>
            </div>
          ` : ''}

        </div>

      `;

    }

  }



  // --- Vue Dédiée : Enseignant / Gestion des Examens (REV-13, REV-15) ---

  async renderTeacherView() {

    this.switchView('view-teacher');

    const container = document.getElementById('teacher-exams-list');

    if (!container) return;



    // Bouton PV par Spécialité & Module dans l'espace enseignant

    const btnClassSheet = document.getElementById('btn-teacher-open-class-sheet');

    if (btnClassSheet) {

      btnClassSheet.onclick = () => this.renderClassSheetView();

    }



    // Affichage des modules assignés à l'enseignant et filtrage du générateur Python

    const assignedMods = (this.currentUser && Array.isArray(this.currentUser.assigned_modules))

      ? this.currentUser.assigned_modules.map(m => (typeof m === 'object' && m !== null) ? m.code : String(m))

      : [];

    const modBadgesEl = document.getElementById('teacher-assigned-modules-badges');

    if (modBadgesEl) {

      if (this.currentUser && this.currentUser.role === 'admin') {

        modBadgesEl.innerHTML = `<span class="badge" style="background:rgba(59,130,246,0.18); color:#93c5fd; border:1px solid #3b82f6; padding:4px 10px; border-radius:12px; font-size:0.8rem; font-weight:700;">👑 Tous les Modules (Admin)</span>`;

      } else if (assignedMods.length > 0) {

        modBadgesEl.innerHTML = assignedMods.map(code =>

          `<span class="badge" style="background:rgba(59,130,246,0.18); color:#93c5fd; border:1px solid #3b82f6; padding:4px 10px; border-radius:12px; font-size:0.8rem; font-weight:700;">📚 Module : ${this._escapeHtml(code)}</span>`

        ).join('');

      } else {

        modBadgesEl.innerHTML = `<span class="badge" style="background:rgba(245,158,11,0.15); color:#fcd34d; border:1px solid #f59e0b; padding:4px 10px; border-radius:12px; font-size:0.8rem;">⚠️ Aucun module affecté</span>`;

      }

    }



    const btnPyGen = document.getElementById('btn-open-python-generator-modal');

    if (btnPyGen) {

      const canUsePythonGen = (this.currentUser && this.currentUser.role === 'admin') || assignedMods.some(c => c.toUpperCase().includes('PYTHON'));

      btnPyGen.style.display = canUsePythonGen ? 'inline-flex' : 'none';

    }



    container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:32px; color:var(--text-secondary);">Chargement de vos examens...</div>';



    try {

      const exams = await api.listExams();



      // Mise à jour des KPIs Enseignant

      const kpiMods = document.getElementById('teacher-kpi-modules');

      const kpiTotal = document.getElementById('teacher-kpi-total-exams');

      const kpiActive = document.getElementById('teacher-kpi-active-exams');

      const kpiCompleted = document.getElementById('teacher-kpi-completed-exams');

      if (kpiMods) kpiMods.textContent = (this.currentUser && this.currentUser.role === 'admin') ? 'Tous' : String(assignedMods.length || 0);

      if (kpiTotal) kpiTotal.textContent = String((exams || []).length);

      if (kpiActive) kpiActive.textContent = String((exams || []).filter(e => e.session_status === 'in_progress' || e.session_status === 'waiting').length);

      if (kpiCompleted) kpiCompleted.textContent = String((exams || []).filter(e => e.session_status === 'completed').length);



      if (!exams || exams.length === 0) {

        container.innerHTML = `

          <div style="grid-column: 1/-1; padding:32px; text-align:center; color:var(--text-secondary); background:var(--bg-surface); border-radius:var(--radius-md); border:1px solid var(--card-border);">

            <div style="font-size:2rem; margin-bottom:8px;">📝</div>

            <div style="font-weight:700; font-size:1.1rem; color:var(--text-primary); margin-bottom:6px;">Aucun examen disponible pour vos modules</div>

            <p style="margin-bottom:16px;">Créez un nouvel examen ou chargez un modèle officiel correspondant à votre module.</p>

            <button class="btn btn-primary" onclick="window.app.openExamTemplateModal()">

              📥 Charger un Modèle Officiel

            </button>

          </div>

        `;

        return;

      }



      container.innerHTML = `

        <div class="teacher-exams-table-wrap" style="width:100%; overflow-x:auto;">

          <table class="teacher-exams-table" style="width:100%; border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:2px solid var(--card-border); text-align:left; font-size:0.82rem; color:var(--text-muted); text-transform:uppercase;">
                <th style="padding:12px 10px; min-width:240px;">Titre de l'Épreuve</th>
                <th style="padding:12px 10px; white-space:nowrap;">Statut Session</th>
                <th style="padding:12px 6px; width:75px; max-width:85px; text-align:center; white-space:nowrap;">Type</th>
                <th style="padding:12px 10px; white-space:nowrap;">Durée</th>
                <th style="padding:12px 10px; white-space:nowrap;">Questions</th>
                <th style="padding:12px 10px; white-space:nowrap;">Barème</th>
                <th style="padding:12px 6px; width:95px; max-width:115px; white-space:nowrap;" title="Spécialité / Cibles" data-col="Cibles">Spécialité</th>
                <th style="padding:12px 10px; text-align:center; min-width:160px;">Actions</th>
              </tr>
            </thead>
            <tbody id="teacher-exams-tbody"></tbody>
          </table>
        </div>
      `;

      const tbody = container.querySelector('#teacher-exams-tbody');
      const isSuperAdmin = (this.currentUser && this.currentUser.role === 'admin');

      exams.forEach(ex => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.06)';

        const assignedPills = (ex.assigned_groups || []).map(g => `<span class="badge" style="background:rgba(59,130,246,0.12); color:#93c5fd; border:1px solid rgba(59,130,246,0.35); font-size:0.7rem; padding:1px 5px; border-radius:5px; white-space:nowrap;">${g}</span>`).join('') || '<span style="color:var(--text-muted); font-size:0.72rem;">Toutes</span>';

        const typeBadge = ex.exam_type === 'practical'
          ? `<span class="badge-exam-type badge-practical" style="display:inline-flex; align-items:center; justify-content:center; height:24px; padding:0 6px; border-radius:5px; font-size:0.72rem; font-weight:600; white-space:nowrap; background:rgba(139,92,246,0.2); color:#c4b5fd; border:1px solid rgba(139,92,246,0.4);">💻 Pratique</span>`
          : `<span class="badge-exam-type badge-theoretical" style="display:inline-flex; align-items:center; justify-content:center; height:24px; padding:0 6px; border-radius:5px; font-size:0.72rem; font-weight:600; white-space:nowrap; background:rgba(59,130,246,0.2); color:#93c5fd; border:1px solid rgba(59,130,246,0.4);">📖 Théorique</span>`;

        const sessStatus = ex.session_status || 'not_started';
        const isCompleted = sessStatus === 'completed';

        let statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(148,163,184,0.15); color:#cbd5e1; border:1px solid #64748b; font-weight:700; white-space:nowrap;">⚪ Non démarré</span>`;
        if (sessStatus === 'waiting') {
          statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(245,158,11,0.15); color:#fcd34d; border:1px solid #f59e0b; font-weight:700; white-space:nowrap;">⏳ Salle ouverte</span>`;
        } else if (sessStatus === 'in_progress') {
          statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(16,185,129,0.18); color:#6ee7b7; border:1px solid #10b981; font-weight:700; white-space:nowrap;">🟢 En cours</span>`;
        } else if (isCompleted) {
          statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(168,85,247,0.18); color:#d8b4fe; border:1px solid #a855f7; font-weight:700; white-space:nowrap;">🟣 Terminé (${ex.submitted_count || 0})</span>`;
        }

        const cleanInstr = (ex.instructions || '').replace(/\[CONFIG_RANDOM_STUDENT_QUESTIONS=\d+\]/g, '').trim();

        let primaryBtnHtml = '';
        let menuItemsHtml = '';

        if (isCompleted) {
          primaryBtnHtml = `
            <button class="btn btn-secondary btn-exam-item-analysis" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}" data-exam-module="${ex.module_code}" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(16,185,129,0.15); border:1px solid #10b981; color:#6ee7b7; font-weight:600; white-space:nowrap;" title="Psychométrie & discrimination">
              📊 Stats
            </button>
          `;
          menuItemsHtml = `
            <button class="menu-action-item btn-exam-download-csv" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}">
              <span>📥</span> <span>Notes CSV</span>
            </button>
            <button class="menu-action-item btn-exam-download-pdf" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}">
              <span>📄</span> <span>PV Notes PDF</span>
            </button>
            <button class="menu-action-item btn-exam-download-copies-zip" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}" style="color:#38bdf8;">
              <span>📦</span> <span>Copies Étudiants (ZIP)</span>
            </button>
            <button class="menu-action-item btn-exam-manage-questions" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}" data-exam-type="${ex.exam_type || 'theoretical'}">
              <span>📝</span> <span>Consulter Questions</span>
            </button>
            <button class="menu-action-item btn-exam-export-package" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}">
              <span>📦</span> <span>Exporter (.exam.zip)</span>
            </button>
            ${isSuperAdmin ? `
              <button class="menu-action-item danger btn-exam-delete" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}">
                <span>🗑️</span> <span>Supprimer l'épreuve</span>
              </button>
            ` : ''}
          `;
        } else if (sessStatus === 'in_progress') {
          primaryBtnHtml = `
            <button class="btn btn-primary btn-open-proctor" data-exam-id="${ex.id}" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:#10b981; border:1px solid #059669; font-weight:700; white-space:nowrap;" title="Surveiller en direct">
              👁️ Surveiller
            </button>
          `;
          menuItemsHtml = `
            <button class="menu-action-item btn-exam-manage-questions" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}" data-exam-type="${ex.exam_type || 'theoretical'}">
              <span>📝</span> <span>Questions</span>
            </button>
            <button class="menu-action-item btn-exam-export-package" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}">
              <span>📦</span> <span>Exporter (.exam.zip)</span>
            </button>
          `;
        } else {
          primaryBtnHtml = `
            <button class="btn btn-primary btn-open-proctor" data-exam-id="${ex.id}" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; font-weight:600; white-space:nowrap;" title="Ouvrir la salle de surveillance">
              👁️ Surveiller
            </button>
          `;
          menuItemsHtml = `
            <button class="menu-action-item btn-exam-manage-questions" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}" data-exam-type="${ex.exam_type || 'theoretical'}">
              <span>📝</span> <span>Gérer Questions</span>
            </button>
            <button class="menu-action-item btn-exam-export-package" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}">
              <span>📦</span> <span>Exporter (.exam.zip)</span>
            </button>
            <button class="menu-action-item danger btn-exam-delete" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}">
              <span>🗑️</span> <span>Supprimer l'épreuve</span>
            </button>
          `;
        }

        tr.innerHTML = `
          <td style="padding:12px 10px; vertical-align:middle;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:3px; flex-wrap:wrap;">
              <span class="user-tag" style="background:rgba(59,130,246,0.12); color:#60a5fa; border:1px solid rgba(59,130,246,0.35); font-weight:700; font-size:0.75rem; padding:2px 6px; border-radius:4px;">${this._escapeHtml(ex.module_code)}</span>
              <span style="font-weight:600; color:var(--text-primary); font-size:0.92rem;">${this._escapeHtml(ex.title)}</span>
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); line-height:1.3;">${this._escapeHtml(cleanInstr ? (cleanInstr.slice(0, 65) + (cleanInstr.length > 65 ? '...' : '')) : 'Sans consigne')}</div>
          </td>
          <td style="padding:12px 10px; vertical-align:middle; white-space:nowrap;">
            ${statusBadgeHtml}
          </td>
          <td style="padding:10px 6px; vertical-align:middle; text-align:center; width:75px; max-width:85px; white-space:nowrap;">
            ${typeBadge}
          </td>
          <td style="padding:12px 10px; vertical-align:middle; font-size:0.85rem; font-weight:600; white-space:nowrap;">
            ⏱️ ${ex.duration_minutes} min
          </td>
          <td style="padding:12px 10px; vertical-align:middle; font-size:0.85rem; white-space:nowrap;">
            <span style="font-weight:700; color:#60a5fa;">${ex.question_count}</span> Q
          </td>
          <td style="padding:12px 10px; vertical-align:middle; font-size:0.85rem; font-weight:600; white-space:nowrap;">
            🎯 / ${ex.global_points}
          </td>
          <td style="padding:10px 6px; vertical-align:middle; width:95px; max-width:115px;">
            <div style="display:flex; flex-wrap:wrap; gap:3px;">
              ${assignedPills}
            </div>
          </td>
          <td style="padding:12px 10px; vertical-align:middle; text-align:center;">
            <div style="display:inline-flex; align-items:center; gap:6px; position:relative;">
              ${primaryBtnHtml}
              <div class="row-menu-wrapper">
                <button class="btn btn-secondary btn-row-menu-toggle" type="button" title="Options supplémentaires" style="height:28px; line-height:26px; width:28px; padding:0; display:inline-flex; align-items:center; justify-content:center; border-radius:6px;">⋮</button>
                <div class="row-actions-dropdown">
                  ${menuItemsHtml}
                </div>
              </div>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });

      // Gestion de l'ouverture / fermeture des menus déroulants
      container.querySelectorAll('.btn-row-menu-toggle').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const menu = btn.nextElementSibling;
          const isVisible = menu && menu.style.display === 'block';
          document.querySelectorAll('.row-actions-dropdown').forEach(m => m.style.display = 'none');
          if (!isVisible && menu) {
            menu.style.display = 'block';
          }
        };
      });

      if (!window._globalRowMenuBound) {
        window._globalRowMenuBound = true;
        document.addEventListener('click', () => {
          document.querySelectorAll('.row-actions-dropdown').forEach(m => m.style.display = 'none');
        });
      }

      // Bind actions on exam table rows
      container.querySelectorAll('.btn-open-proctor').forEach(btn => {
        btn.onclick = () => {
          const examId = btn.getAttribute('data-exam-id');
          this.openExamProctoringRoom(examId);
        };
      });

      container.querySelectorAll('.btn-exam-item-analysis').forEach(btn => {
        btn.onclick = () => {
          const examId = btn.getAttribute('data-exam-id');
          const title = btn.getAttribute('data-exam-title');
          const moduleCode = btn.getAttribute('data-exam-module');
          this.openItemAnalysisModal(examId, title, moduleCode);
        };
      });

      container.querySelectorAll('.btn-exam-manage-questions').forEach(btn => {
        btn.onclick = () => {
          const examId = btn.getAttribute('data-exam-id');
          const title = btn.getAttribute('data-exam-title');
          this.openManageQuestionsModal(examId, title);
        };
      });

      container.querySelectorAll('.btn-exam-download-csv').forEach(btn => {
        btn.onclick = async () => {
          const examId = btn.getAttribute('data-exam-id');
          const moduleCode = btn.getAttribute('data-exam-module');
          try {
            await api.downloadExamResultsCsv(examId, moduleCode);
            this.showToast('Notes finales (CSV) téléchargées avec succès.', 'success');
          } catch (e) {
            this.showToast(`Erreur lors du téléchargement CSV : ${e.message}`, 'danger');
          }
        };
      });

      container.querySelectorAll('.btn-exam-download-copies-zip').forEach(btn => {
        btn.onclick = async () => {
          const examId = btn.getAttribute('data-exam-id');
          const moduleCode = btn.getAttribute('data-exam-module');
          try {
            this.showToast("Génération de l'archive des copies en cours...", "info");
            await api.downloadExamStudentCopiesZip(examId, moduleCode);
            this.showToast("Copies des étudiants (ZIP) téléchargées avec succès.", "success");
          } catch (e) {
            this.showToast(`Erreur lors du téléchargement des copies : ${e.message}`, "danger");
          }
        };
      });

      container.querySelectorAll('.btn-exam-download-pdf').forEach(btn => {
        btn.onclick = async () => {
          const examId = btn.getAttribute('data-exam-id');
          const moduleCode = btn.getAttribute('data-exam-module');
          try {
            await api.downloadExamResultsPdf(examId, moduleCode);
            this.showToast('PV des notes finales (PDF) téléchargé avec succès.', 'success');
          } catch (e) {
            this.showToast(`Erreur lors du téléchargement PDF : ${e.message}`, 'danger');
          }
        };
      });

      container.querySelectorAll('.btn-exam-export-package').forEach(btn => {
        btn.onclick = async () => {
          const examId = btn.getAttribute('data-exam-id');
          const moduleCode = btn.getAttribute('data-exam-module');
          try {
            await api.exportExamPackage(examId, `examen_${moduleCode}_${examId}.exam.zip`);
            this.showToast('Package exporté avec succès.', 'success');
          } catch (e) {
            this.showToast(`Erreur d'exportation du package : ${e.message}`, 'danger');
          }
        };
      });

      container.querySelectorAll('.btn-exam-delete').forEach(btn => {
        btn.onclick = async () => {
          const examId = btn.getAttribute('data-exam-id');
          const title = btn.getAttribute('data-exam-title');
          const ok = await this.showConfirmModal({
            title: "Supprimer l'épreuve",
            message: `Confirmez-vous la suppression définitive de l'épreuve "${title}" ? Cette action est irréversible.`,
            confirmText: "Supprimer définitivement",
            cancelText: "Annuler",
            icon: "🗑️",
            danger: true
          });
          if (ok) {
            try {
              await api.deleteExam(examId);
              this.showToast(`Épreuve "${title}" supprimée avec succès.`, 'success');
              await this.renderTeacherView();
            } catch (err) {
              this.showToast(`Erreur de suppression : ${err.message}`, 'danger');
            }
          }
        };
      });




    } catch (err) {

      container.innerHTML = `<div style="grid-column:1/-1; color:var(--danger); padding:20px;">Erreur de chargement des examens : ${err.message}</div>`;

    }

  }



  // --- Modal Modèles d'Examens JSON (REV-13) ---

  async openExamTemplateModal() {

    const modal = document.getElementById('modal-exam-template-picker');

    if (modal) modal.classList.add('active');

    const container = document.getElementById('templates-cards-container');

    if (!container) return;



    container.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-secondary);">Recherche des modèles disponibles...</div>';



    try {

      const templates = await api.listExamTemplates();

      if (!templates.length) {

        container.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-muted);">Aucun modèle JSON trouvé dans backend/app/seeds/templates/.</div>';

        return;

      }



      container.innerHTML = '';

      templates.forEach(t => {

        const item = document.createElement('div');

        item.style.background = 'var(--bg-primary)';

        item.style.border = '1px solid var(--card-border)';

        item.style.borderRadius = 'var(--radius-md)';

        item.style.padding = '14px 18px';

        item.style.display = 'flex';

        item.style.justifyContent = 'space-between';

        item.style.alignItems = 'center';

        item.style.gap = '16px';



        const groupsText = (t.group_ids || []).join(', ') || 'Tous';



        item.innerHTML = `

          <div>

            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">

              <span class="user-tag">${t.module_code}</span>

              <strong style="color:var(--text-primary); font-size:0.95rem;">${this._escapeHtml(t.title)}</strong>

            </div>

            <div style="font-size:0.8rem; color:var(--text-secondary);">

              ⏱️ ${t.duration_minutes} min | ❓ ${t.question_count} questions | 🎯 ${t.global_points} pts | 👥 Spécialité : <strong>${groupsText}</strong>

            </div>

          </div>

          <button class="btn btn-primary btn-instantiate-template" data-tid="${t.template_id}" style="padding:6px 14px; font-size:0.85rem; white-space:nowrap;">

            Charger ➔

          </button>

        `;

        container.appendChild(item);

      });



      container.querySelectorAll('.btn-instantiate-template').forEach(b => {

        b.onclick = async () => {

          const tid = b.getAttribute('data-tid');

          b.disabled = true;

          b.textContent = '⏳ Chargement...';

          try {

            const res = await api.loadExamTemplate(tid);

            this.showToast(`Examen officiel "${res.title}" chargé avec succès (${res.question_count} questions) ! Il est prêt.`, "success");

            this.closeModal('modal-exam-template-picker');

            this.renderTeacherView();

          } catch (err) {

            this.showToast(`Erreur de chargement du modèle : ${err.message}`, "danger");

            b.disabled = false;

            b.textContent = 'Charger ➔';

          }

        };

      });



    } catch (err) {

      container.innerHTML = `<div style="color:var(--danger); padding:16px;">Erreur : ${err.message}</div>`;

    }

  }



  // --- Salle de Surveillance Interactive (REV-16, Style AlgoExamination) ---

  async openExamProctoringRoom(examId) {

    try {

      const sessRes = await api.openProctorSession(examId, 'SALLE-TP-1');

      const sessionId = sessRes.session_id;

      this.currentProctorSessionId = sessionId;

      this.activeSessionId = sessionId;

      this.currentProctorExamId = examId;



      this.switchView('view-proctor-live');

      await this.initProctorMonitoringLive(sessionId);

    } catch (err) {

      this.showToast(`Erreur d'ouverture de la session de surveillance : ${err.message}`, "danger");

    }

  }



  async initProctorMonitoringLive(sessionId) {

    this.currentProctorSessionId = sessionId;

    this.activeSessionId = sessionId;

    if (this.proctorWebSocket) {

      try { this.proctorWebSocket.close(); } catch (_) {}

      this.proctorWebSocket = null;

    }

    if (this.proctorPollInterval) {

      clearInterval(this.proctorPollInterval);

      this.proctorPollInterval = null;

    }

    if (this.proctorTimerInterval) {

      clearInterval(this.proctorTimerInterval);

      this.proctorTimerInterval = null;

    }



    const backBtn = document.getElementById('btn-proctor-back');

    if (backBtn) {

      backBtn.onclick = () => {

        if (this.proctorWebSocket) {

          try { this.proctorWebSocket.close(); } catch (_) {}

          this.proctorWebSocket = null;

        }

        if (this.proctorPollInterval) {

          clearInterval(this.proctorPollInterval);

          this.proctorPollInterval = null;

        }

        if (this.proctorTimerInterval) {

          clearInterval(this.proctorTimerInterval);

          this.proctorTimerInterval = null;

        }

        if (this.currentUser && this.currentUser.role === 'admin') {

          this.renderAdminView();

        } else {

          this.renderTeacherView();

        }

      };

    }



    const launchAllBtn = document.getElementById('btn-proctor-launch-all');

    if (launchAllBtn) {

      launchAllBtn.onclick = async () => {

        const ok = await this.showConfirmModal({

          title: "Lancer l'Épreuve pour la Salle",

          message: "Voulez-vous démarrer l'épreuve synchronisée pour tous les candidats connectés dans la salle ? Le chronomètre serveur démarrera immédiatement.",

          confirmText: "🚀 Lancer l'Épreuve",

          cancelText: "Annuler",

          icon: "🚀",

          danger: false

        });

        if (ok) {

          try {

            await api.launchProctorSession(sessionId);

            this._logProctorFeed("🚀 Lancement synchronisé de l'épreuve déclenché par le surveillant.");

            await this.refreshProctorOverview(sessionId);

          } catch (err) {

            this.showToast(`Erreur lors du lancement synchronisé : ${err.message}`, "danger");

          }

        }

      };

    }



    const closeAllBtn = document.getElementById('btn-proctor-close-all');

    if (closeAllBtn) {

      closeAllBtn.onclick = async () => {

        const ok = await this.showConfirmModal({

          title: "Clôturer Définitivement l'Épreuve",

          message: "🛑 Clôturer définitivement l'épreuve pour toute la salle ?\nToutes les copies actives seront immédiatement soumises, corrigées et scellées.",

          confirmText: "🛑 Clôturer l'Épreuve",

          cancelText: "Annuler",

          icon: "🛑",

          danger: true

        });

        if (ok) {

          try {

            await api.closeExamSession(sessionId);

            this._logProctorFeed("🛑 Clôture collective de l'épreuve par le surveillant : toutes les copies scellées.");

            await this.refreshProctorOverview(sessionId);

            this.showToast("L'épreuve a été clôturée avec succès. Toutes les copies actives ont été soumises et scellées.", "success");

          } catch (err) {

            this.showToast(`Erreur lors de la clôture : ${err.message}`, "danger");

          }

        }

      };

    }



    const extendAllBtn = document.getElementById('btn-proctor-extend-all');

    if (extendAllBtn) {

      extendAllBtn.onclick = async () => {

        try {

          await api.extendProctorTime(sessionId, 5, null);

          this._logProctorFeed("⏱️ +5 minutes accordées à tous les étudiants de la salle.");

          await this.refreshProctorOverview(sessionId);

        } catch (err) {

          this.showToast(`Erreur : ${err.message}`, "danger");

        }

      };

    }



    const refreshBtn = document.getElementById('btn-proctor-refresh');

    if (refreshBtn) {

      refreshBtn.onclick = () => this.refreshProctorOverview(sessionId);

    }



    const dlGradesCsvBtn = document.getElementById('btn-proctor-download-grades-csv');

    if (dlGradesCsvBtn) {

      dlGradesCsvBtn.onclick = async () => {

        const exId = this.currentProctorExamId || (sessionId.startsWith('SESS-') ? sessionId.slice(5) : sessionId);

        try {

          await api.downloadExamResultsCsv(exId);

          this.showToast('Notes finales de tous les étudiants (CSV) téléchargées.', 'success');

        } catch (err) {

          this.showToast(`Erreur téléchargement CSV : ${err.message}`, 'danger');

        }

      };

    }



    const dlCopiesZipBtn = document.getElementById('btn-proctor-download-copies-zip');
    if (dlCopiesZipBtn) {
      dlCopiesZipBtn.onclick = async () => {
        try {
          this.showToast("Génération de l'archive des copies en cours...", "info");
          await api.downloadSessionStudentCopiesZip(sessionId);
          this.showToast("Copies des étudiants (ZIP) téléchargées avec succès.", "success");
        } catch (err) {
          this.showToast(`Erreur téléchargement copies : ${err.message}`, "danger");
        }
      };
    }

    const dlGradesPdfBtn = document.getElementById('btn-proctor-download-grades-pdf');

    if (dlGradesPdfBtn) {

      dlGradesPdfBtn.onclick = async () => {

        const exId = this.currentProctorExamId || (sessionId.startsWith('SESS-') ? sessionId.slice(5) : sessionId);

        try {

          await api.downloadExamResultsPdf(exId);

          this.showToast('PV officiel des notes finales (PDF) téléchargé.', 'success');

        } catch (err) {

          this.showToast(`Erreur téléchargement PDF : ${err.message}`, 'danger');

        }

      };

    }



    // Connexion WebSocket

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    const wsUrl = `${wsProtocol}//${window.location.host}/api/proctor/ws/session/${sessionId}/teacher`;

    try {

      this.proctorWebSocket = new WebSocket(wsUrl);

      this.proctorWebSocket.onopen = () => {

        const ind = document.getElementById('proctor-ws-indicator');

        if (ind) ind.style.color = '#10b981';

        this._logProctorFeed("🟢 Canal télémétrique WebSocket connecté en direct.");

      };

      this.proctorWebSocket.onmessage = (event) => {

        try {

          const msg = JSON.parse(event.data);

          this._handleProctorWebSocketMessage(msg, sessionId);

        } catch (_) {}

      };

      this.proctorWebSocket.onclose = () => {

        const ind = document.getElementById('proctor-ws-indicator');

        if (ind) ind.style.color = '#94a3b8';

      };

    } catch (e) {

      console.warn("WebSocket proctor fallback sur polling :", e);

    }



    await this.refreshProctorOverview(sessionId);



    this.proctorPollInterval = setInterval(() => {

      this.refreshProctorOverview(sessionId);

    }, 5000);



    this.proctorTimerInterval = setInterval(() => {

      if (this._proctorSessionStatus === 'in_progress' && this._proctorRemainingSeconds !== undefined && this._proctorRemainingSeconds !== null) {

        this._proctorRemainingSeconds = Math.max(0, this._proctorRemainingSeconds - 1);

        this._updateProctorTimerDisplay();

      }

      this._updateProctorServerClockDisplay();

    }, 1000);

  }



  _cleanupProctorSession() {
    if (this.proctorPollInterval) {
      clearInterval(this.proctorPollInterval);
      this.proctorPollInterval = null;
    }
    if (this.proctorTimerInterval) {
      clearInterval(this.proctorTimerInterval);
      this.proctorTimerInterval = null;
    }
    if (this.proctorWebSocket) {
      try { this.proctorWebSocket.close(); } catch (_) {}
      this.proctorWebSocket = null;
    }
    if (this._studentWs) {
      try { this._studentWs.close(); } catch (_) {}
      this._studentWs = null;
    }
    this.activeSessionId = null;
    this.currentProctorSessionId = null;
    this.currentProctorExamId = null;
  }

  async refreshProctorOverview(sessionId) {
    if (!this.currentUser || (this.currentUser.role !== 'teacher' && this.currentUser.role !== 'admin') || this.currentView !== 'view-proctor-live') {
      this._cleanupProctorSession();
      return;
    }
    try {
      const data = await api.getProctorSessionOverview(sessionId);

      this._renderProctorOverviewData(data, sessionId);

    } catch (err) {
      if (err.status === 401 || err.status === 403 || err.status === 404 ||
          (err.message && (err.message.includes('401') || err.message.includes('403') || err.message.includes('404') || err.message.includes('expirée') || err.message.includes('Accès refusé')))) {
        this._cleanupProctorSession();
        return;
      }
      console.error("Échec de rafraîchissement proctor :", err);

      if (err.status === 404 || (err.message && (err.message.includes('404') || err.message.toLowerCase().includes('introuvable')))) {

        if (this.proctorPollInterval) {

          clearInterval(this.proctorPollInterval);

          this.proctorPollInterval = null;

        }

        if (this.proctorTimerInterval) {

          clearInterval(this.proctorTimerInterval);

          this.proctorTimerInterval = null;

        }

        if (this.proctorWebSocket) {

          try { this.proctorWebSocket.close(); } catch (_) {}

          this.proctorWebSocket = null;

        }

        this.activeSessionId = null;

        this.showToast("La session de surveillance n'existe plus ou a été supprimée.", "warning");

        if (this.currentRole === 'teacher') {

          this.renderTeacherDashboard();

        } else if (this.currentRole === 'admin') {

          this.renderAdminDashboard();

        }

      }

    }

  }



  _updateProctorTimerDisplay() {

    const timerEl = document.getElementById('proctor-session-timer');

    if (!timerEl) return;



    if (this._proctorSessionStatus === 'waiting') {

      timerEl.textContent = 'En attente';

      timerEl.style.color = '#f59e0b';

      return;

    }

    if (this._proctorSessionStatus === 'finished' || this._proctorSessionStatus === 'completed' || this._proctorSessionStatus === 'closed') {

      timerEl.textContent = 'Clôturé (00:00)';

      timerEl.style.color = '#a855f7';

      return;

    }

    if (this._proctorRemainingSeconds === null || this._proctorRemainingSeconds === undefined) {

      timerEl.textContent = '--:--';

      timerEl.style.color = '#a5b4fc';

      return;

    }



    const sec = Math.max(0, Math.floor(this._proctorRemainingSeconds));

    const m = Math.floor(sec / 60);

    const s = sec % 60;

    timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

    if (sec <= 60) {

      timerEl.style.color = '#ef4444';

    } else if (sec <= 300) {

      timerEl.style.color = '#f59e0b';

    } else {

      timerEl.style.color = '#a5b4fc';

    }

  }



  _updateProctorServerClockDisplay() {

    const el = document.getElementById('proctor-server-clock');

    if (!el) return;

    const offset = this._proctorServerOffsetMs || 0;

    const nowUtc = new Date(Date.now() + offset);

    const hh = String(nowUtc.getUTCHours()).padStart(2, '0');

    const mm = String(nowUtc.getUTCMinutes()).padStart(2, '0');

    const ss = String(nowUtc.getUTCSeconds()).padStart(2, '0');

    el.textContent = `🕒 Heure Serveur : ${hh}:${mm}:${ss} UTC`;

  }



  _formatAuditLogEntry(l, studentMap = {}) {
    const timeStr = l.timestamp ? new Date(l.timestamp).toLocaleTimeString('fr-FR') : new Date().toLocaleTimeString('fr-FR');
    const details = typeof l.details === 'string' ? (() => { try { return JSON.parse(l.details); } catch (_) { return {}; } })() : (l.details || {});
    const stName = studentMap[l.student_id] || (l.student_id ? `Étudiant ${l.student_id}` : 'Système');

    switch (l.event_type) {
      case 'FORCE_SUBMITTED': {
        const by = details.forced_by ? ` par ${details.forced_by}` : '';
        const mark = details.final_mark !== undefined ? ` Note : ${details.final_mark}/20.` : '';
        return `[${timeStr}] 🛑 Épreuve de ${stName} soumise de force${by}.${mark}`;
      }
      case 'SUBMIT':
      case 'STUDENT_SUBMITTED':
      case 'EXAM_SUBMITTED': {
        const mark = details.final_mark !== undefined ? ` Note : ${details.final_mark}/20.` : (details.score !== undefined ? ` Note : ${details.score}/20.` : '');
        return `[${timeStr}] ✅ Épreuve soumise par ${stName}.${mark}`;
      }
      case 'EXAM_STARTED': {
        const att = details.attempt_id ? ` (Session #${details.attempt_id.slice(-6)})` : '';
        return `[${timeStr}] 🚀 Épreuve débutée pour ${stName}${att}.`;
      }
      case 'SECURITY_WARNING': {
        const num = details.warning_number ? ` (Avertissement #${details.warning_number})` : '';
        const reason = details.reason ? ` — ${details.reason}` : '';
        return `[${timeStr}] ⚠️ Alerte de sécurité pour ${stName}${num}${reason}.`;
      }
      case 'UNLOCKED_BY_TEACHER': {
        const by = details.unlocked_by ? ` par ${details.unlocked_by}` : ' par le surveillant';
        return `[${timeStr}] 🔓 Poste de ${stName} débloqué${by} (compteur d'avertissements réinitialisé).`;
      }
      case 'STUDENT_CONNECTED':
        return `[${timeStr}] 🟢 ${stName} connecté au poste d'épreuve.`;
      case 'STUDENT_DISCONNECTED':
        return `[${timeStr}] 🔴 Déconnexion détectée pour ${stName}.`;
      case 'TIME_EXTENDED': {
        const mins = details.minutes_added || 5;
        return `[${timeStr}] ⏱️ Prolongation de +${mins} min accordée à ${stName}.`;
      }
      case 'SESSION_LAUNCHED':
        return `[${timeStr}] 🚀 Lancement officiel synchronisé de la session d'épreuve.`;
      case 'SESSION_CLOSED':
        return `[${timeStr}] 🛑 Clôture officielle de la session par le surveillant.`;
      default: {
        const cleanDetails = details.reason || details.message || (typeof details === 'object' && Object.keys(details).length ? Object.entries(details).map(([k, v]) => `${k}: ${v}`).join(', ') : '');
        const detailPart = cleanDetails ? ` — ${cleanDetails}` : '';
        return `[${timeStr}] ℹ️ [${l.event_type}] ${stName}${detailPart}`;
      }
    }
  }

  _renderProctorOverviewData(data, sessionId) {

    const titleEl = document.getElementById('proctor-exam-title');

    if (titleEl) titleEl.textContent = data.exam_title;

    const roomEl = document.getElementById('proctor-room-id');

    if (roomEl) roomEl.textContent = data.room_id;

    const durEl = document.getElementById('proctor-duration');

    if (durEl) durEl.textContent = `${data.duration_minutes} min`;

    const enrEl = document.getElementById('proctor-enrolled-count');

    if (enrEl) enrEl.textContent = data.total_enrolled;



    this.lastProctorData = data;

    this._proctorSessionStatus = data.status;

    if (data.session_remaining_seconds !== undefined) {

      this._proctorRemainingSeconds = data.session_remaining_seconds;

    }

    this._updateProctorTimerDisplay();



    const statusBadge = document.getElementById('proctor-session-status-badge');

    if (statusBadge) {

      if (data.status === 'in_progress') {

        statusBadge.textContent = '💻 En cours (LIVE)';

        statusBadge.style.color = '#10b981';

        statusBadge.style.borderColor = '#10b981';

        statusBadge.style.background = 'rgba(16,185,129,0.15)';

      } else if (data.status === 'finished' || data.status === 'completed' || data.status === 'closed') {

        statusBadge.textContent = '✅ Clôturé / Terminé';

        statusBadge.style.color = '#a855f7';

        statusBadge.style.borderColor = '#a855f7';

        statusBadge.style.background = 'rgba(168,85,247,0.15)';

      } else {

        statusBadge.textContent = '⏳ En attente';

        statusBadge.style.color = '#f59e0b';

        statusBadge.style.borderColor = '#f59e0b';

        statusBadge.style.background = 'rgba(245,158,11,0.15)';

      }

    }



    if (data.server_epoch_ms) {

      this._proctorServerOffsetMs = Number(data.server_epoch_ms) - Date.now();

    }

    this._updateProctorServerClockDisplay();



    // Machine à états stricte des boutons de la barre d'outils de surveillance

    const isWaiting = data.status === 'waiting';

    const isInProgress = data.status === 'in_progress';

    const isFinished = data.status === 'completed' || data.status === 'finished' || data.status === 'closed';



    const setBtnVisible = (id, visible) => {

      const el = document.getElementById(id);

      if (el) el.style.display = visible ? 'inline-flex' : 'none';

    };



    // 1. Avant démarrage (waiting) : uniquement "Lancer l'Épreuve" + "Rafraîchir"

    setBtnVisible('btn-proctor-launch-all', isWaiting);

    // 2. Pendant l'épreuve (in_progress) : uniquement "Clôturer", "+5 Min (Tous)", "Rafraîchir"

    setBtnVisible('btn-proctor-close-all', isInProgress);

    setBtnVisible('btn-proctor-refresh', !isFinished);

    // 3. Après clôture (completed/finished/closed) : uniquement les exports finaux & Analyse Psychométrique

    setBtnVisible('btn-proctor-download-grades-csv', isFinished);

    setBtnVisible('btn-proctor-download-grades-pdf', isFinished);
    setBtnVisible('btn-proctor-download-copies-zip', isFinished);

    setBtnVisible('btn-proctor-export-results-zip', isFinished);

    setBtnVisible('btn-proctor-item-analysis', isFinished);



    const tableBody = document.getElementById('proctor-students-table-body');

    const cardsContainer = document.getElementById('proctor-students-grid');

    if (!tableBody && !cardsContainer) return;



    const rawCards = data.student_cards || [];

    const connectedCount = rawCards.filter(c => c.is_online || c.status === 'in_progress').length;

    const notConnectedCount = rawCards.filter(c => c.status === 'not_entered' || (!c.is_online && c.status !== 'submitted')).length;

    const finishedCount = rawCards.filter(c => c.status === 'submitted').length;



    let totalAnsweredAll = 0;

    let totalQuestionsAll = 0;

    rawCards.forEach(c => {

      totalAnsweredAll += (c.answered_count || 0);

      totalQuestionsAll += (c.total_questions || 0);

    });

    const avgProgressPct = totalQuestionsAll > 0 ? Math.round((totalAnsweredAll / totalQuestionsAll) * 100) : 0;



    // Mise à jour des cartes KPI supérieures en temps réel

    const kpiConn = document.getElementById('proctor-kpi-connected');

    if (kpiConn) kpiConn.textContent = connectedCount;

    const kpiNotConn = document.getElementById('proctor-kpi-not-connected');

    if (kpiNotConn) kpiNotConn.textContent = notConnectedCount;

    const kpiFin = document.getElementById('proctor-kpi-finished');

    if (kpiFin) kpiFin.textContent = finishedCount;

    const kpiAvg = document.getElementById('proctor-kpi-progress-avg');

    if (kpiAvg) kpiAvg.textContent = `${avgProgressPct}%`;

    const kpiDetail = document.getElementById('proctor-kpi-progress-detail');

    if (kpiDetail) kpiDetail.textContent = `(${totalAnsweredAll} / ${totalQuestionsAll} rép.)`;



    const statsSummary = document.getElementById('proctor-stats-summary');

    if (statsSummary) statsSummary.textContent = `${connectedCount} connectés / ${rawCards.length} inscrits`;



    // Tri interactif des colonnes de la salle de surveillance

    this._proctorSortColumn = this._proctorSortColumn || 'name';

    this._proctorSortDirection = this._proctorSortDirection || 'asc';



    const sortCol = this._proctorSortColumn;

    const isAsc = this._proctorSortDirection === 'asc';



    const cards = [...rawCards].sort((a, b) => {

      let valA, valB;

      if (sortCol === 'name') {

        valA = (a.student_name || '').toLowerCase();

        valB = (b.student_name || '').toLowerCase();

        return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);

      } else if (sortCol === 'status') {

        valA = (a.status || '').toLowerCase();

        valB = (b.status || '').toLowerCase();

        return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);

      } else if (sortCol === 'progress') {

        valA = a.progress_pct !== undefined ? a.progress_pct : 0;

        valB = b.progress_pct !== undefined ? b.progress_pct : 0;

        return isAsc ? valA - valB : valB - valA;

      } else if (sortCol === 'alerts') {

        valA = a.suspension_count !== undefined ? a.suspension_count : 0;

        valB = b.suspension_count !== undefined ? b.suspension_count : 0;

        return isAsc ? valA - valB : valB - valA;

      } else if (sortCol === 'activity') {

        valA = a.is_online ? 1 : 0;

        valB = b.is_online ? 1 : 0;

        if (valA !== valB) return isAsc ? valA - valB : valB - valA;

        const actA = a.last_activity_seconds !== null && a.last_activity_seconds !== undefined ? a.last_activity_seconds : 99999;

        const actB = b.last_activity_seconds !== null && b.last_activity_seconds !== undefined ? b.last_activity_seconds : 99999;

        return isAsc ? actB - actA : actA - actB;

      } else if (sortCol === 'mark') {

        valA = a.final_mark !== null && a.final_mark !== undefined ? Number(a.final_mark) : -1;

        valB = b.final_mark !== null && b.final_mark !== undefined ? Number(b.final_mark) : -1;

        return isAsc ? valA - valB : valB - valA;

      }

      return 0;

    });



    // Mise à jour des icônes de tri des en-têtes

    ['name', 'status', 'progress', 'alerts', 'activity', 'mark'].forEach(col => {

      const iconEl = document.getElementById(`proctor-sort-icon-${col}`);

      if (iconEl) {

        if (col === sortCol) {

          iconEl.textContent = isAsc ? '▲' : '▼';

          iconEl.style.color = '#38bdf8';

        } else {

          iconEl.textContent = '⇅';

          iconEl.style.color = 'var(--text-muted)';

        }

      }

    });



    // Attachement des listeners de tri sur les en-têtes

    if (!this._proctorSortHeadersBound) {

      this._proctorSortHeadersBound = true;

      document.querySelectorAll('.proctor-sort-th').forEach(th => {

        th.onclick = () => {

          const col = th.getAttribute('data-col');

          if (this._proctorSortColumn === col) {

            this._proctorSortDirection = this._proctorSortDirection === 'asc' ? 'desc' : 'asc';

          } else {

            this._proctorSortColumn = col;

            this._proctorSortDirection = 'asc';

          }

          if (this.lastProctorData && this.activeSessionId) {

            this._renderProctorOverviewData(this.lastProctorData, this.activeSessionId);

          }

        };

      });

    }



    const statusLabels = {

      not_entered: { label: 'Absent / Non entré', color: '#64748b', bg: 'rgba(100,116,139,0.15)' },

      waiting: { label: '⏳ Salle d\'attente', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },

      in_progress: { label: '💻 En épreuve', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },

      suspended: { label: '⚠️ Suspendu', color: '#ef4444', bg: 'rgba(239,68,68,0.2)' },

      submitted: { label: '✅ Rendu', color: '#a855f7', bg: 'rgba(168,85,247,0.15)' }

    };



    if (tableBody) {

      if (!cards.length) {

        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun étudiant inscrit au groupe de cet examen.</td></tr>';

        return;

      }

      tableBody.innerHTML = '';

      cards.forEach(c => {

        const row = document.createElement('tr');

        row.className = `status-${c.status}`;



        const st = statusLabels[c.status] || { label: c.status, color: '#94a3b8', bg: 'rgba(255,255,255,0.05)' };

        const timeText = c.elapsed_seconds > 0 ? `${Math.floor(c.elapsed_seconds / 60)}m ${c.elapsed_seconds % 60}s` : '—';

        const markLabel = c.final_mark !== null && c.final_mark !== undefined ? ` (${Number(c.final_mark).toFixed(2)}/20)` : '';



        row.innerHTML = `

          <td style="padding:12px 16px;">

            <div style="font-weight:700; color:var(--text-primary); font-size:0.95rem;">${this._escapeHtml(c.student_name)}</div>

            <div style="font-size:0.8rem; color:var(--text-secondary); display:flex; align-items:center; gap:6px; margin-top:2px;">

              <span class="user-tag" style="font-size:0.7rem; padding:1px 6px;">${c.group_id || 'GRP'}</span>

              <span>${this._escapeHtml(c.username)}</span>

              <span style="color:var(--text-muted);">• IP : ${c.client_ip || '—'}</span>

            </div>

          </td>

          <td style="padding:12px 16px;">

            <span class="proctor-stat-pill" style="color:${st.color}; background:${st.bg}; border:1px solid ${st.color}; font-weight:600; font-size:0.78rem; padding:3px 10px; border-radius:12px; display:inline-block;">

              ${st.label}${markLabel}

            </span>

          </td>

          <td style="padding:12px 16px; min-width:160px;">

            <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--text-secondary); margin-bottom:4px;">

              <span>Réponses :</span>

              <strong>${c.answered_count} / ${c.total_questions} (${c.progress_pct}%)</strong>

            </div>

            <div class="proctor-progress-track" style="height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">

              <div class="proctor-progress-fill" style="width:${c.progress_pct}%; height:100%; background:#3b82f6; transition:width 0.3s ease;"></div>

            </div>

          </td>

          <td style="padding:12px 16px;">

            ${c.suspension_count > 0 ? `

              <span class="user-tag" style="background:rgba(239,68,68,0.15); color:#fca5a5; border-color:rgba(239,68,68,0.3); font-weight:600; font-size:0.78rem;">

                ⚠️ ${c.suspension_count} avert.

              </span>

              ${c.status === 'suspended' && c.suspension_remaining_seconds ? `

                <span class="user-tag" style="background:rgba(239,68,68,0.25); color:#ef4444; font-family:var(--font-mono); font-weight:700; font-size:0.75rem;">

                  ⏱️ ${Math.floor(c.suspension_remaining_seconds / 60)}m ${c.suspension_remaining_seconds % 60}s

                </span>

              ` : ''}

              ${c.suspension_reason ? `<div style="font-size:0.75rem; color:#f87171; margin-top:2px; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${this._escapeHtml(c.suspension_reason)}">${this._escapeHtml(c.suspension_reason)}</div>` : ''}

            ` : '<span style="color:var(--text-muted); font-size:0.8rem;">0 alerte</span>'}

          </td>

          <td style="padding:12px 16px; font-size:0.8rem; font-family:var(--font-mono);">

            ${c.is_online ? '<span style="color:#10b981; font-weight:700; display:inline-flex; align-items:center; gap:5px;"><span style="width:7px; height:7px; border-radius:50%; background:#10b981; box-shadow:0 0 6px #10b981;"></span> En ligne</span>' : (c.status === 'in_progress' ? '<span style="color:#ef4444; font-weight:700; display:inline-flex; align-items:center; gap:5px;"><span style="width:7px; height:7px; border-radius:50%; background:#ef4444;"></span> Connexion perdue</span>' : (c.status === 'submitted' ? '<span style="color:#a855f7;">Terminé</span>' : (c.status === 'waiting' ? '<span style="color:#f59e0b;">En attente</span>' : '<span style="color:#64748b;">Absent</span>')))}

            ${c.last_activity_seconds !== null && c.last_activity_seconds !== undefined ? `<div style="font-size:0.72rem; color:var(--text-muted); margin-top:3px;">Activité : il y a ${c.last_activity_seconds < 60 ? c.last_activity_seconds + 's' : Math.floor(c.last_activity_seconds / 60) + 'm'}</div>` : ''}

          </td>

          <td style="padding:12px 16px; text-align:right;">

            <div style="display:inline-flex; gap:6px; justify-content:flex-end;">

              ${(c.status === 'suspended' || c.suspension_count > 0) && c.attempt_id ? `

                <button class="btn btn-primary btn-card-unlock" data-att="${c.attempt_id}" style="padding:4px 8px; font-size:0.78rem; background:#10b981;">

                  🔓 Débloquer

                </button>

              ` : ''}

              ${(c.status === 'in_progress' || c.status === 'suspended') && c.attempt_id ? `

                <button class="btn btn-secondary btn-card-force-submit" data-att="${c.attempt_id}" data-name="${this._escapeHtml(c.student_name)}" style="padding:4px 8px; font-size:0.78rem; color:#f87171; border-color:rgba(239,68,68,0.3);">

                  🛑 Forcer

                </button>

              ` : ''}



              ${c.status === 'not_entered' ? `

                <span style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">Poste non connecté</span>

              ` : ''}

            </div>

          </td>

        `;

        tableBody.appendChild(row);

      });



      // Bind actions for candidates table

      tableBody.querySelectorAll('.btn-card-unlock').forEach(btn => {

        btn.onclick = async () => {

          const attId = btn.getAttribute('data-att');

          try {

            await api.unlockStudentAttempt(sessionId, attId);

            this._logProctorFeed(`🔓 Poste ${attId} débloqué par le surveillant. Compteur réinitialisé à 0.`);

            await this.refreshProctorOverview(sessionId);

          } catch (err) {

            this.showToast(`Erreur de déblocage : ${err.message}`, "danger");

          }

        };

      });



      tableBody.querySelectorAll('.btn-card-force-submit').forEach(btn => {

        btn.onclick = async () => {

          const attId = btn.getAttribute('data-att');

          const stName = btn.getAttribute('data-name');

          const ok = await this.showConfirmModal({

            title: "Forcer la soumission",

            message: `Forcer immédiatement la soumission de l'épreuve pour ${stName} ?`,

            confirmText: "🛑 Forcer la soumission",

            cancelText: "Annuler",

            icon: "🛑",

            danger: true

          });

          if (ok) {

            try {

              const res = await api.forceSubmitAttempt(sessionId, attId);

              this._logProctorFeed(`🛑 Épreuve de ${stName} soumise de force. Note : ${res.final_mark}/20.`);

              await this.refreshProctorOverview(sessionId);

            } catch (err) {

              this.showToast(`Erreur : ${err.message}`, "danger");

            }

          }

        };

      });



      tableBody.querySelectorAll('.btn-card-extend').forEach(btn => {

        btn.onclick = async () => {

          const stId = btn.getAttribute('data-sid');

          try {

            await api.extendProctorTime(sessionId, 5, stId);

            this._logProctorFeed(`⏱️ +5 minutes accordées à l'étudiant ${stId}.`);

            await this.refreshProctorOverview(sessionId);

          } catch (err) {

            this.showToast(`Erreur : ${err.message}`, "danger");

          }

        };

      });

    }



    if (data.recent_audit_logs && data.recent_audit_logs.length) {

      const studentMap = {};

      if (Array.isArray(data.student_cards)) {

        data.student_cards.forEach(c => {

          if (c.student_id) studentMap[c.student_id] = c.student_name || c.username || c.student_id;

        });

      }

      this._loggedAuditLogIds = this._loggedAuditLogIds || new Set();

      const logs = [...data.recent_audit_logs].reverse();

      logs.forEach(l => {

        if (!this._loggedAuditLogIds.has(l.id)) {

          this._loggedAuditLogIds.add(l.id);

          const formattedText = this._formatAuditLogEntry(l, studentMap);

          this._logProctorFeed(formattedText);

        }

      });

    }

  }



  _handleProctorWebSocketMessage(msg, sessionId) {

    const timeStr = new Date().toLocaleTimeString('fr-FR');

    if (msg.type === 'STUDENT_CONNECTED') {

      this._logProctorFeed(`[${timeStr}] 🟢 Étudiant ${msg.student_id} connecté au poste d'épreuve.`);

    } else if (msg.type === 'STUDENT_DISCONNECTED') {

      this._logProctorFeed(`[${timeStr}] 🔴 Déconnexion détectée pour l'étudiant ${msg.student_id}.`);

    } else if (msg.type === 'STUDENT_UNLOCKED') {

      this._logProctorFeed(`[${timeStr}] 🔓 Étudiant ${msg.student_id} débloqué par le surveillant.`);

    } else if (msg.type === 'STUDENT_SUBMITTED') {

      this._logProctorFeed(`[${timeStr}] ✅ Épreuve soumise par ${msg.student_id}. Note : ${msg.final_mark}/20.`);

    } else if (msg.type === 'SECURITY_EVENT') {

      const suspBadge = msg.is_suspended ? ' ⛔ SUSPENDU (5 MIN)' : '';

      this._logProctorFeed(`[${timeStr}] ⚠️ Sécurité [${msg.event_type || 'Avertissement'}] : ${msg.student_name || msg.student_id} (${msg.suspension_count || 1} avert.) — ${msg.reason || 'Sortie plein écran/focus'}${suspBadge}`);

    } else {

      this._logProctorFeed(`[${timeStr}] 📡 Événement [${msg.type || 'TELEMETRY'}] poste ${msg.student_id || ''}.`);

    }

    this.refreshProctorOverview(sessionId);

  }



  _connectStudentTelemetryWebSocket(sessionId, studentId) {

    if (this._studentWs) {

      try { this._studentWs.close(); } catch (_) {}

      this._studentWs = null;

    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    const wsUrl = `${wsProtocol}//${window.location.host}/api/proctor/ws/session/${sessionId}/student/${studentId}`;

    try {

      this._studentWs = new WebSocket(wsUrl);

      this._studentWs.onopen = () => {

        console.log(`[StudentTelemetry] Connecté au canal de session ${sessionId}`);

      };

      this._studentWs.onmessage = (event) => {

        try {

          const msg = JSON.parse(event.data);

          if (msg.type === 'ATTEMPT_UNLOCKED') {

            if (this.activeAntiCheat) {

              this.activeAntiCheat._unlockSuspension();

            }

            this.hideSuspensionScreen();

          } else if (msg.type === 'EXAM_FORCE_SUBMITTED' || msg.type === 'SESSION_CLOSED') {

            this.handleExamForcedClosure(msg);

          } else if (msg.type === 'TIME_EXTENDED') {

            const extraMin = msg.extra_minutes || 5;

            if (this.activeExamRunner) {

              this.activeExamRunner.extendTime(extraMin);

            }

            this.showToast(`⏱️ +${extraMin} minutes accordées pour cette épreuve !`, "info");

          }

        } catch (_) {}

      };

      this._studentWs.onerror = () => {};

      this._studentWs.onclose = () => {

        this._studentWs = null;

      };

    } catch (_) {}

  }



  _logProctorFeed(text) {

    const feed = document.getElementById('proctor-live-feed');

    if (!feed) return;

    const entry = document.createElement('div');

    entry.style.borderBottom = '1px solid rgba(255,255,255,0.04)';

    entry.style.padding = '3px 0';

    entry.textContent = text;

    feed.insertBefore(entry, feed.firstChild);

  }



  // --- Vue Dédiée : Super Administrateur & Pilotage Académique (REV-39, REV-40) ---

  renderAdminView() {

    this.switchView('view-admin');

    this._bindAdminGlobalListeners();

    this.switchAdminTab(this.currentAdminTab || 'admin-tab-stats');

  }



  _bindAdminGlobalListeners() {

    if (this._adminListenersBound) return;

    this._adminListenersBound = true;



    // Navigation des onglets

    document.querySelectorAll('.admin-tab-btn').forEach(btn => {

      btn.onclick = () => {

        const tabId = btn.getAttribute('data-tab');

        this.switchAdminTab(tabId);

      };

    });



    // Actualiser tout

    const refreshBtn = document.getElementById('btn-admin-refresh-all');

    if (refreshBtn) {

      refreshBtn.onclick = () => this.switchAdminTab(this.currentAdminTab || 'admin-tab-stats');

    }



    // Ingestion CSV Multi-Salles

    const triggerCsvBtn = document.getElementById('btn-admin-trigger-import-csv');

    const inputCsv = document.getElementById('input-admin-csv-file');

    if (triggerCsvBtn && inputCsv) {

      triggerCsvBtn.onclick = () => inputCsv.click();

      inputCsv.onchange = async (e) => {

        const file = e.target.files && e.target.files[0];

        if (file) {

          await this.handleAdminResultsCsvImport(file);

          inputCsv.value = '';

        }

      };

    }



    // Filtres des résultats

    const btnResultsRefresh = document.getElementById('btn-admin-results-refresh');

    if (btnResultsRefresh) {

      btnResultsRefresh.onclick = () => this.loadAdminResults();

    }

    const filterRoom = document.getElementById('admin-results-filter-room');

    if (filterRoom) {

      filterRoom.onchange = () => this.loadAdminResults();

    }

    const filterGroup = document.getElementById('admin-results-filter-group');

    if (filterGroup) {

      filterGroup.onchange = () => this.loadAdminResults();

    }



    // Filtre & Recherche Étudiants

    const filterStuGroup = document.getElementById('admin-students-filter-group');

    if (filterStuGroup) {

      filterStuGroup.onchange = () => this._renderAdminStudentsRows();

    }

    const searchStu = document.getElementById('admin-students-search');

    if (searchStu) {

      searchStu.oninput = () => this._renderAdminStudentsRows();

    }



    // Import CSV Étudiants (REV-43)

    const inputStudentCsv = document.getElementById('input-admin-student-csv');

    const btnTriggerStudentCsv = document.getElementById('btn-admin-trigger-student-csv');

    const feedbackStudentCsv = document.getElementById('admin-student-csv-feedback');

    if (btnTriggerStudentCsv && inputStudentCsv) {

      btnTriggerStudentCsv.onclick = () => inputStudentCsv.click();

      inputStudentCsv.onchange = async () => {

        const file = inputStudentCsv.files[0];

        if (!file) return;

        if (feedbackStudentCsv) {

          feedbackStudentCsv.style.display = 'block';

          feedbackStudentCsv.style.background = 'rgba(59, 130, 246, 0.15)';

          feedbackStudentCsv.style.color = '#60a5fa';

          feedbackStudentCsv.textContent = `⏳ Importation des étudiants depuis "${file.name}"...`;

        }

        try {

          const res = await api.importStudentsCsv(file);

          if (feedbackStudentCsv) {

            feedbackStudentCsv.style.background = 'rgba(16, 185, 129, 0.15)';

            feedbackStudentCsv.style.color = '#34d399';

            feedbackStudentCsv.textContent = `✅ Succès : ${res.imported_count} étudiant(s) importé(s), ${res.updated_count} mis à jour.`;

          }

          await this.loadAdminStudents();

          this.loadAdminOverview();

        } catch (err) {

          if (feedbackStudentCsv) {

            feedbackStudentCsv.style.background = 'rgba(239, 68, 68, 0.15)';

            feedbackStudentCsv.style.color = '#f87171';

            feedbackStudentCsv.textContent = `❌ Erreur : ${err.message}`;

          }

        } finally {

          inputStudentCsv.value = '';

        }

      };

    }



    // Import CSV Enseignants

    const inputTeacherCsv = document.getElementById('input-admin-teacher-csv');

    const btnTriggerTeacherCsv = document.getElementById('btn-admin-trigger-teacher-csv');

    const feedbackTeacherCsv = document.getElementById('admin-teacher-csv-feedback');

    if (btnTriggerTeacherCsv && inputTeacherCsv) {

      btnTriggerTeacherCsv.onclick = () => inputTeacherCsv.click();

      inputTeacherCsv.onchange = async () => {

        const file = inputTeacherCsv.files[0];

        if (!file) return;

        if (feedbackTeacherCsv) {

          feedbackTeacherCsv.style.display = 'block';

          feedbackTeacherCsv.style.background = 'rgba(16, 185, 129, 0.15)';

          feedbackTeacherCsv.style.color = '#6ee7b7';

          feedbackTeacherCsv.textContent = `⏳ Importation des enseignants depuis "${file.name}"...`;

        }

        try {

          const res = await api.importTeachersCsv(file);

          if (feedbackTeacherCsv) {

            feedbackTeacherCsv.style.background = 'rgba(16, 185, 129, 0.15)';

            feedbackTeacherCsv.style.color = '#34d399';

            feedbackTeacherCsv.textContent = `✅ Succès : ${res.imported_count} enseignant(s) importé(s), ${res.updated_count} mis à jour (identifiants et mots de passe générés automatiquement).`;

          }

          await this.loadAdminTeachers();

          await this.loadAdminModules();

          this.loadAdminOverview();

        } catch (err) {

          if (feedbackTeacherCsv) {

            feedbackTeacherCsv.style.background = 'rgba(239, 68, 68, 0.15)';

            feedbackTeacherCsv.style.color = '#f87171';

            feedbackTeacherCsv.textContent = `❌ Erreur : ${err.message}`;

          }

        } finally {

          inputTeacherCsv.value = '';

        }

      };

    }



    // Générateurs de mot de passe aléatoire pour Étudiant, Enseignant et Admin

    const genRandomPass = (inputId) => {

      const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%";

      let pwd = "";

      for (let i = 0; i < 10; i++) pwd += chars.charAt(Math.floor(Math.random() * chars.length));

      const inputPwd = document.getElementById(inputId);

      if (inputPwd) inputPwd.value = pwd;

    };



    const btnGenPwd = document.getElementById('btn-admin-student-gen-pwd');

    if (btnGenPwd) btnGenPwd.onclick = () => genRandomPass('admin-student-password');



    const btnTeacherGenPwd = document.getElementById('btn-admin-teacher-gen-pwd');

    if (btnTeacherGenPwd) btnTeacherGenPwd.onclick = () => genRandomPass('admin-teacher-password');



    const btnAdminOwnGenPwd = document.getElementById('btn-admin-own-gen-pwd');

    if (btnAdminOwnGenPwd) btnAdminOwnGenPwd.onclick = () => genRandomPass('admin-own-password');



    // Bouton PV par Spécialité & Module dans l'espace Admin

    const btnAdminClassSheet = document.getElementById('btn-admin-open-class-sheet');

    if (btnAdminClassSheet) {

      btnAdminClassSheet.onclick = () => this.renderClassSheetView();

    }



    // Bouton Mon Compte Admin (Login & Mot de passe)

    const btnAdminOwnAccount = document.getElementById('btn-admin-edit-own-account');

    if (btnAdminOwnAccount) {

      btnAdminOwnAccount.onclick = () => {

        const modal = document.getElementById('modal-admin-own-credentials');

        if (!modal || !this.currentUser) return;

        const uInput = document.getElementById('admin-own-username');

        const nInput = document.getElementById('admin-own-fullname');

        const pInput = document.getElementById('admin-own-password');

        if (uInput) uInput.value = this.currentUser.username || 'admin';

        if (nInput) nInput.value = this.currentUser.full_name || 'Administrateur';

        if (pInput) pInput.value = '';

        modal.classList.add('active');

      };

    }



    const formAdminOwn = document.getElementById('form-admin-own-credentials');

    if (formAdminOwn) {

      formAdminOwn.onsubmit = async (e) => {

        e.preventDefault();

        if (!this.currentUser) return;

        const username = document.getElementById('admin-own-username')?.value.trim();

        const full_name = document.getElementById('admin-own-fullname')?.value.trim();

        const password = document.getElementById('admin-own-password')?.value || undefined;

        try {

          const updated = await api.updateUser(this.currentUser.id, {

            username: username || undefined,

            full_name: full_name || undefined,

            password

          });

          this.currentUser = updated;

          const navName = document.getElementById('user-display-name');

          if (navName) navName.textContent = updated.full_name || updated.username;

          this.closeModal('modal-admin-own-credentials');

          this.showToast("Vos identifiants Administrateur ont été mis à jour avec succès.", "success");

        } catch (err) {

          this.showToast(`Erreur de mise à jour : ${err.message}`, "danger");

        }

      };

    }



    // Boutons Impression Fiches Identifiants Découpables (Étudiants & Enseignants séparément)

    const btnPrintStudentSlips = document.getElementById('btn-admin-print-student-slips');

    if (btnPrintStudentSlips) {

      btnPrintStudentSlips.onclick = () => this.openPrintCredentialsSlipsModal('student');

    }

    const btnPrintTeacherSlips = document.getElementById('btn-admin-print-teacher-slips');

    if (btnPrintTeacherSlips) {

      btnPrintTeacherSlips.onclick = () => this.openPrintCredentialsSlipsModal('teacher');

    }

    const btnExecPrintSlips = document.getElementById('btn-execute-print-slips') || document.getElementById('btn-trigger-print-slips');

    if (btnExecPrintSlips) {

      btnExecPrintSlips.onclick = () => this.printCredentialsSlipsWindow();

    }



    // Filtres, Tri & Recherche Bulletins (REV-45, REV-47)

    const filterSpecBulletins = document.getElementById('admin-bulletins-filter-speciality');

    if (filterSpecBulletins) {

      filterSpecBulletins.onchange = () => this._renderAdminBulletinsRows();

    }

    const sortModuleBulletins = document.getElementById('admin-bulletins-sort-module');

    if (sortModuleBulletins) {

      sortModuleBulletins.onchange = () => this._renderAdminBulletinsRows();

    }

    const searchBulletins = document.getElementById('admin-bulletins-search');

    if (searchBulletins) {

      searchBulletins.oninput = () => this._renderAdminBulletinsRows();

    }

    const btnExportBulletinsCsv = document.getElementById('btn-admin-export-bulletins-csv');

    if (btnExportBulletinsCsv) {

      btnExportBulletinsCsv.onclick = () => this.downloadBulletinsCsv();

    }

    const btnPrintBulletin = document.getElementById('btn-print-bulletin');

    if (btnPrintBulletin) {

      btnPrintBulletin.onclick = () => window.print();

    }



    // Export ZIP des Bulletins (PDF et Word)

    const btnZipPdf = document.getElementById('btn-admin-export-bulletins-zip-pdf');

    if (btnZipPdf) {

      btnZipPdf.onclick = async () => {

        try {

          const spec = document.getElementById('admin-bulletins-filter-speciality')?.value || '';

          await api.downloadBulletinsZip('pdf', spec);

        } catch (e) {

          this.showToast(`Erreur d'exportation ZIP PDF : ${e.message}`, "danger");

        }

      };

    }

    const btnZipDocx = document.getElementById('btn-admin-export-bulletins-zip-docx');

    if (btnZipDocx) {

      btnZipDocx.onclick = async () => {

        try {

          const spec = document.getElementById('admin-bulletins-filter-speciality')?.value || '';

          await api.downloadBulletinsZip('docx', spec);

        } catch (e) {

          this.showToast(`Erreur d'exportation ZIP Word : ${e.message}`, "danger");

        }

      };

    }



    // Export Palmarès Spécialité / Trié par Module (PDF et Word)

    const btnPalmaresPdf = document.getElementById('btn-admin-export-palmares-pdf');

    if (btnPalmaresPdf) {

      btnPalmaresPdf.onclick = async () => {

        try {

          const spec = document.getElementById('admin-bulletins-filter-speciality')?.value || '';

          const sortMod = document.getElementById('admin-bulletins-sort-module')?.value || 'AVG';

          await api.downloadSpecialityResultsPdf(spec, sortMod);

        } catch (e) {

          this.showToast(`Erreur d'exportation Palmarès PDF : ${e.message}`, "danger");

        }

      };

    }

    const btnPalmaresDocx = document.getElementById('btn-admin-export-palmares-docx');

    if (btnPalmaresDocx) {

      btnPalmaresDocx.onclick = async () => {

        try {

          const spec = document.getElementById('admin-bulletins-filter-speciality')?.value || '';

          const sortMod = document.getElementById('admin-bulletins-sort-module')?.value || 'AVG';

          await api.downloadSpecialityResultsDocx(spec, sortMod);

        } catch (e) {

          this.showToast(`Erreur d'exportation Palmarès Word : ${e.message}`, "danger");

        }

      };

    }



    // Téléchargements directs depuis la modale de bulletin

    const btnModalPdf = document.getElementById('btn-modal-bulletin-pdf');

    if (btnModalPdf) {

      btnModalPdf.onclick = async () => {

        try {

          if (this.currentUser && this.currentUser.role === 'student') {

            await api.downloadMyBulletinPdf();

          } else if (this.activeBulletinStudentId) {

            await api.downloadStudentBulletinPdf(this.activeBulletinStudentId);

          }

        } catch (e) {

          this.showToast(`Erreur téléchargement PDF : ${e.message}`, "danger");

        }

      };

    }

    const btnModalDocx = document.getElementById('btn-modal-bulletin-docx');

    if (btnModalDocx) {

      btnModalDocx.onclick = async () => {

        try {

          if (this.currentUser && this.currentUser.role === 'student') {

            await api.downloadMyBulletinDocx();

          } else if (this.activeBulletinStudentId) {

            await api.downloadStudentBulletinDocx(this.activeBulletinStudentId);

          }

        } catch (e) {

          this.showToast(`Erreur téléchargement Word : ${e.message}`, "danger");

        }

      };

    }



    // Boutons Ajout

    const btnAddStudent = document.getElementById('btn-admin-add-student');

    if (btnAddStudent) {

      btnAddStudent.onclick = () => this.openAdminStudentModal('create');

    }

    const btnAddTeacher = document.getElementById('btn-admin-add-teacher');

    if (btnAddTeacher) {

      btnAddTeacher.onclick = () => this.openAdminTeacherModal('create');

    }

    const btnAddModule = document.getElementById('btn-admin-add-module');

    if (btnAddModule) {

      btnAddModule.onclick = () => this.openAdminModuleModal('create');

    }



    // Formulaire Étudiant

    const formStudent = document.getElementById('form-admin-student');

    if (formStudent) {

      formStudent.onsubmit = async (e) => {

        e.preventDefault();

        const mode = document.getElementById('admin-student-mode').value;

        const id = document.getElementById('admin-student-id').value.trim();

        const username = document.getElementById('admin-student-username').value.trim();

        const full_name = document.getElementById('admin-student-fullname').value.trim();

        const email = document.getElementById('admin-student-email').value.trim() || undefined;

        const group_id = document.getElementById('admin-student-group').value || undefined;

        const enrollment_year = document.getElementById('admin-student-year')?.value.trim() || undefined;

        const password = document.getElementById('admin-student-password').value || undefined;



        try {

          if (mode === 'create') {

            await api.createUser({

              id: id || undefined,

              username: username || undefined,

              full_name,

              email,

              group_id,

              enrollment_year,

              password,

              role: 'student'

            });

            this.showToast(`Étudiant "${full_name}" créé avec succès.`, "success");

          } else {

            await api.updateUser(id, {

              username: username || undefined,

              full_name,

              email,

              group_id,

              enrollment_year,

              password: password || undefined

            });

            this.showToast(`Étudiant "${full_name}" mis à jour.`, "success");

          }

          this.closeModal('modal-admin-student');

          await this.loadAdminStudents();

          this.loadAdminOverview();

        } catch (err) {

          this.showToast(`Erreur : ${err.message}`, "danger");

        }

      };

    }



    // Formulaire Enseignant

    const formTeacher = document.getElementById('form-admin-teacher');

    if (formTeacher) {

      formTeacher.onsubmit = async (e) => {

        e.preventDefault();

        const mode = document.getElementById('admin-teacher-mode').value;

        const id = document.getElementById('admin-teacher-id').value.trim();

        const username = document.getElementById('admin-teacher-username').value.trim();

        const full_name = document.getElementById('admin-teacher-fullname').value.trim();

        const email = document.getElementById('admin-teacher-email').value.trim() || undefined;

        const password = document.getElementById('admin-teacher-password').value || undefined;



        try {

          if (mode === 'create') {

            await api.createUser({

              id: id || undefined,

              username: username || undefined,

              full_name,

              email,

              password,

              role: 'teacher'

            });

            this.showToast(`Enseignant "${full_name}" créé avec succès.`, "success");

          } else {

            await api.updateUser(id, {

              username: username || undefined,

              full_name,

              email,

              password: password || undefined

            });

            this.showToast(`Enseignant "${full_name}" mis à jour.`, "success");

          }

          this.closeModal('modal-admin-teacher');

          await this.loadAdminTeachers();

          this.loadAdminOverview();

        } catch (err) {

          this.showToast(`Erreur : ${err.message}`, "danger");

        }

      };

    }



    // Formulaire Module

    const formModule = document.getElementById('form-admin-module');

    if (formModule) {

      formModule.onsubmit = async (e) => {

        e.preventDefault();

        const mode = document.getElementById('admin-module-mode').value;

        const code = document.getElementById('admin-module-code').value.trim().toUpperCase();

        const title = document.getElementById('admin-module-title').value.trim();

        const description = document.getElementById('admin-module-desc').value.trim();



        try {

          if (mode === 'create') {

            await api.createModule({ code, title, description });

            this.showToast(`Module "${code} - ${title}" créé avec succès.`, "success");

          } else {

            await api.updateModule(code, { title, description });

            this.showToast(`Module "${code}" mis à jour.`, "success");

          }

          this.closeModal('modal-admin-module');

          await this.loadAdminModules();

          this.loadAdminOverview();

        } catch (err) {

          this.showToast(`Erreur : ${err.message}`, "danger");

        }

      };

    }



    // Affectation Enseignant -> Module

    const btnDoAssign = document.getElementById('btn-admin-do-assign-teacher');

    if (btnDoAssign) {

      btnDoAssign.onclick = async () => {

        const moduleCode = document.getElementById('admin-assign-module-code').value;

        const teacherId = document.getElementById('admin-assign-teacher-select').value;

        if (!moduleCode || !teacherId) return;

        try {

          await api.assignTeacherModule(moduleCode, teacherId);

          await this.openAdminAssignModuleModal(moduleCode);

          this.loadAdminModules();

        } catch (err) {

          this.showToast(`Erreur d'affectation : ${err.message}`, "danger");

        }

      };

    }

  }



  switchAdminTab(tabId) {

    this.currentAdminTab = tabId;

    document.querySelectorAll('.admin-tab-btn').forEach(btn => {

      const isTarget = btn.getAttribute('data-tab') === tabId;

      btn.classList.toggle('active', isTarget);

      btn.classList.toggle('btn-primary', isTarget);

      btn.classList.toggle('btn-secondary', !isTarget);

    });



    document.querySelectorAll('.admin-tab-content').forEach(content => {

      content.style.display = content.id === tabId ? 'block' : 'none';

    });



    if (tabId === 'admin-tab-stats') {

      this.loadAdminOverview();

    } else if (tabId === 'admin-tab-students') {

      this.loadAdminStudents();

    } else if (tabId === 'admin-tab-teachers') {

      this.loadAdminTeachers();

    } else if (tabId === 'admin-tab-modules') {

      this.loadAdminModules();

    } else if (tabId === 'admin-tab-exams') {

      this.loadAdminExams();

    } else if (tabId === 'admin-tab-bulletins') {

      this.loadAdminBulletins();

    }

  }



  // --- Tab 1 : Statistiques Globales & Consolidation Multi-Salles (REV-40) ---

  async loadAdminOverview() {

    try {

      const data = await api.getAdminOverview();

      this.lastAdminOverview = data;

      const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

      setVal('admin-kpi-students', data.total_students);

      setVal('admin-kpi-teachers', data.total_teachers);

      setVal('admin-kpi-modules', data.total_modules);

      setVal('admin-kpi-exams', data.total_exams);

      setVal('admin-kpi-submitted', data.total_submitted);

      setVal('admin-kpi-avg', `${Number(data.average_mark || 0).toFixed(2)} / 20`);

      setVal('admin-kpi-pass-rate', `${Number(data.pass_rate || 0).toFixed(1)} %`);



      const roomSelect = document.getElementById('admin-results-filter-room');

      const groupSelect = document.getElementById('admin-results-filter-group');

      if (roomSelect) {

        const curRoom = roomSelect.value;

        const rooms = [...new Set((data.recent_submissions || []).map(s => s.room_id).filter(r => r && r !== '—'))];

        roomSelect.innerHTML = '<option value="">Toutes les Salles</option>' + rooms.map(r => `<option value="${r}">${r}</option>`).join('');

        roomSelect.value = curRoom;

      }

      if (groupSelect) {

        const curGroup = groupSelect.value;

        groupSelect.innerHTML = '<option value="">Tous les Groupes</option>' + (data.groups_summary || []).map(g => `<option value="${g.group_id}">${g.group_name || g.group_id}</option>`).join('');

        groupSelect.value = curGroup;

      }



      await this.loadAdminResults();

    } catch (err) {

      console.error("Erreur chargement aperçu admin :", err);

    }

  }



  async loadAdminResults() {

    const tbody = document.getElementById('admin-results-table-body');

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des copies...</td></tr>';

    try {

      const room_id = document.getElementById('admin-results-filter-room')?.value || undefined;

      const group_id = document.getElementById('admin-results-filter-group')?.value || undefined;

      const results = await api.getAdminResults({ room_id, group_id });

      if (!results || results.length === 0) {

        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-muted);">Aucune copie trouvée avec ces critères.</td></tr>';

        return;

      }

      tbody.innerHTML = '';

      results.forEach(item => {

        const tr = document.createElement('tr');

        tr.style.borderBottom = '1px solid var(--card-border)';

        const markText = (item.final_mark !== null && item.final_mark !== undefined)

          ? `<strong style="color:${item.final_mark >= 10 ? '#4ade80' : '#f87171'};">${Number(item.final_mark).toFixed(2)} / 20</strong>`

          : '—';

        const dateText = item.submitted_at ? new Date(item.submitted_at).toLocaleString('fr-FR') : (item.started_at ? new Date(item.started_at).toLocaleString('fr-FR') : '—');

        tr.innerHTML = `

          <td style="padding:10px 14px; font-family:monospace; font-weight:600;">${this._escapeHtml(item.student_id)}</td>

          <td style="padding:10px 14px;">

            <div style="font-weight:600; color:var(--text-primary);">${this._escapeHtml(item.student_name)}</div>

            <div style="font-size:0.78rem; color:var(--text-muted);">@${this._escapeHtml(item.username)}</div>

          </td>

          <td style="padding:10px 14px;"><span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8; font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(item.group_id || '—')}</span></td>

          <td style="padding:10px 14px;">

            <div style="font-size:0.85rem; color:var(--text-primary);">${this._escapeHtml(item.exam_title || '—')}</div>

            <div style="font-size:0.75rem; color:var(--text-secondary);">${this._escapeHtml(item.module_code || '')}</div>

          </td>

          <td style="padding:10px 14px;"><span class="badge" style="background:rgba(255,255,255,0.05); color:var(--text-secondary); font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(item.room_id || '—')}</span></td>

          <td style="padding:10px 14px; text-align:center;">${markText}</td>

          <td style="padding:10px 14px;"><span class="badge" style="background:rgba(16,185,129,0.15); color:#10b981; font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(item.status)}</span></td>

          <td style="padding:10px 14px; font-size:0.8rem; color:var(--text-secondary);">${dateText}</td>

        `;

        tbody.appendChild(tr);

      });

    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  async handleAdminResultsCsvImport(file) {

    const feedback = document.getElementById('admin-csv-import-feedback');

    if (feedback) {

      feedback.style.display = 'block';

      feedback.style.background = 'rgba(99,102,241,0.15)';

      feedback.style.color = '#818cf8';

      feedback.innerHTML = `⏳ Ingestion du fichier CSV (${this._escapeHtml(file.name)}) en cours...`;

    }

    try {

      const res = await api.importResultsCsv(file);

      if (feedback) {

        feedback.style.background = res.success ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)';

        feedback.style.color = res.success ? '#10b981' : '#f59e0b';

        let errorList = '';

        if (res.errors && res.errors.length > 0) {

          errorList = `<div style="margin-top:6px; font-size:0.8rem;">Erreurs relevées : ${res.errors.slice(0, 5).join('<br/>')}</div>`;

        }

        feedback.innerHTML = `✅ ${res.message}${errorList}`;

      }

      await this.loadAdminOverview();

    } catch (err) {

      if (feedback) {

        feedback.style.background = 'rgba(239,68,68,0.15)';

        feedback.style.color = '#ef4444';

        feedback.textContent = `❌ Échec de l'import CSV : ${err.message}`;

      }

    }

  }



  // --- Tab 2 : Gestion des Étudiants (CRUD REV-39) ---

  async loadAdminStudents() {

    const tbody = document.getElementById('admin-students-table-body');

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des étudiants...</td></tr>';

    try {

      const [students, groups, years] = await Promise.all([

        api.listUsers('student'),

        api.listGroups(),

        api.listEnrollmentYears()

      ]);

      this._adminStudentsList = students;

      this._adminGroupsList = groups;

      this._adminYearsList = years;



      const filterYear = document.getElementById('admin-students-filter-year');

      if (filterYear) {

        const curY = filterYear.value;

        filterYear.innerHTML = '<option value="">Toutes les Années</option>' + (years || []).map(y => `<option value="${y}">${y}</option>`).join('');

        filterYear.value = curY;

        filterYear.onchange = () => this._renderAdminStudentsRows();

      }



      const filterGroup = document.getElementById('admin-students-filter-group');

      const modalGroup = document.getElementById('admin-student-group');

      if (filterGroup) {

        const cur = filterGroup.value;

        filterGroup.innerHTML = '<option value="">Toutes les Spécialités</option>' + groups.map(g => `<option value="${g.id}">${g.name || g.id}</option>`).join('');

        filterGroup.value = cur;

        filterGroup.onchange = () => this._renderAdminStudentsRows();

      }

      if (modalGroup) {

        modalGroup.innerHTML = groups.map(g => `<option value="${g.id}">${g.name || g.id}</option>`).join('');

      }



      this._renderAdminStudentsRows();

    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  _renderAdminStudentsRows() {

    const tbody = document.getElementById('admin-students-table-body');

    if (!tbody) return;

    const filterYearVal = document.getElementById('admin-students-filter-year')?.value || '';

    const filterGroupVal = document.getElementById('admin-students-filter-group')?.value || '';

    const searchVal = (document.getElementById('admin-students-search')?.value || '').toLowerCase().trim();



    let list = this._adminStudentsList || [];

    if (filterYearVal) {

      list = list.filter(s => s.enrollment_year === filterYearVal);

    }

    if (filterGroupVal) {

      list = list.filter(s => s.group_id === filterGroupVal);

    }

    if (searchVal) {

      list = list.filter(s =>

        (s.id && s.id.toLowerCase().includes(searchVal)) ||

        (s.username && s.username.toLowerCase().includes(searchVal)) ||

        (s.full_name && s.full_name.toLowerCase().includes(searchVal)) ||

        (s.enrollment_year && s.enrollment_year.toLowerCase().includes(searchVal)) ||

        (s.email && s.email.toLowerCase().includes(searchVal))

      );

    }



    const countEl = document.getElementById('admin-students-count');

    if (countEl) countEl.textContent = `${list.length} étudiant(s) affiché(s) (${(this._adminStudentsList || []).length} total)`;



    if (list.length === 0) {

      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun étudiant ne correspond aux critères.</td></tr>';

      return;

    }



    tbody.innerHTML = '';

    list.forEach(s => {

      const tr = document.createElement('tr');

      tr.style.borderBottom = '1px solid var(--card-border)';

      tr.innerHTML = `

        <td style="padding:10px 14px; font-family:monospace; font-weight:600;">${this._escapeHtml(s.id)}</td>

        <td style="padding:10px 14px; font-weight:600; color:var(--text-primary);">${this._escapeHtml(s.username)}</td>

        <td style="padding:10px 14px;">${this._escapeHtml(s.full_name)}</td>

        <td style="padding:10px 14px;"><span class="badge" style="background:rgba(52,211,153,0.15); color:#34d399; font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(s.enrollment_year || '—')}</span></td>

        <td style="padding:10px 14px;"><span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8; font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(s.group_id || '—')}</span></td>

        <td style="padding:10px 14px;"><span style="font-family:monospace; font-size:0.85rem; background:rgba(255,255,255,0.06); padding:3px 8px; border-radius:4px; border:1px solid var(--card-border); color:#38bdf8;">${this._escapeHtml(s.plain_password || '••••••••')}</span></td>

        <td style="padding:10px 14px; font-size:0.82rem; color:var(--text-secondary);">${this._escapeHtml(s.email || '—')}</td>

        <td style="padding:10px 14px; text-align:center;">

          <div style="display:inline-flex; gap:6px;">

            <button class="btn btn-secondary btn-admin-edit-student" data-id="${s.id}" style="padding:4px 8px; font-size:0.78rem;">✏️ Modifier</button>

            <button class="btn btn-danger btn-admin-delete-student" data-id="${s.id}" data-name="${s.full_name}" style="padding:4px 8px; font-size:0.78rem;">🗑️ Supprimer</button>

          </div>

        </td>

      `;

      tbody.appendChild(tr);

    });



    tbody.querySelectorAll('.btn-admin-edit-student').forEach(btn => {

      btn.onclick = () => {

        const id = btn.getAttribute('data-id');

        const st = (this._adminStudentsList || []).find(x => x.id === id);

        if (st) this.openAdminStudentModal('edit', st);

      };

    });



    tbody.querySelectorAll('.btn-admin-delete-student').forEach(btn => {

      btn.onclick = async () => {

        const id = btn.getAttribute('data-id');

        const name = btn.getAttribute('data-name');

        const ok = await this.showConfirmModal({

          title: "Supprimer l'étudiant",

          message: `Confirmez-vous la suppression définitive de l'étudiant "${name}" (${id}) ?`,

          confirmText: "Supprimer",

          cancelText: "Annuler",

          icon: "🗑️",

          danger: true

        });

        if (ok) {

          try {

            await api.deleteUser(id);

            this.showToast("Étudiant supprimé avec succès.", "success");

            await this.loadAdminStudents();

            this.loadAdminOverview();

          } catch (e) {

            this.showToast(`Erreur de suppression : ${e.message}`, "danger");

          }

        }

      };

    });

  }



  openAdminStudentModal(mode = 'create', data = null) {

    const modal = document.getElementById('modal-admin-student');

    if (!modal) return;

    const title = document.getElementById('modal-admin-student-title');

    const modeInput = document.getElementById('admin-student-mode');

    const idInput = document.getElementById('admin-student-id');

    const userInput = document.getElementById('admin-student-username');

    const nameInput = document.getElementById('admin-student-fullname');

    const emailInput = document.getElementById('admin-student-email');

    const groupSelect = document.getElementById('admin-student-group');

    const yearInput = document.getElementById('admin-student-year');

    const passInput = document.getElementById('admin-student-password');



    modeInput.value = mode;

    if (mode === 'edit' && data) {

      title.textContent = `✏️ Modifier l'Étudiant ${data.username}`;

      idInput.value = data.id;

      idInput.disabled = true;

      userInput.value = data.username;

      userInput.disabled = false;

      nameInput.value = data.full_name || '';

      emailInput.value = data.email || '';

      groupSelect.value = data.group_id || '';

      if (yearInput) yearInput.value = data.enrollment_year || '';

      passInput.value = data.plain_password || '';

      passInput.placeholder = "Mot de passe étudiant";

      passInput.disabled = false;

    } else {

      title.textContent = '➕ Nouvel Étudiant';

      idInput.value = '';

      idInput.disabled = false;

      userInput.value = '';

      userInput.disabled = false;

      nameInput.value = '';

      emailInput.value = '';

      if (yearInput) yearInput.value = '2025-2026';

      passInput.value = '';

      passInput.placeholder = "Mot de passe (ou vide = matricule)";

      passInput.disabled = false;

    }

    modal.classList.add('active');

  }



  // --- Tab 3 : Gestion des Enseignants (CRUD REV-39) ---

  async loadAdminTeachers() {

    const tbody = document.getElementById('admin-teachers-table-body');

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des enseignants...</td></tr>';

    try {

      const teachers = await api.listUsers('teacher');

      this._adminTeachersList = teachers;



      const countEl = document.getElementById('admin-teachers-count');

      if (countEl) countEl.textContent = `${teachers.length} enseignant(s) au total`;



      if (teachers.length === 0) {

        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun enseignant enregistré.</td></tr>';

        return;

      }



      tbody.innerHTML = '';

      teachers.forEach(t => {

        const tr = document.createElement('tr');

        tr.style.borderBottom = '1px solid var(--card-border)';

        const modulesBadges = (t.assigned_modules && t.assigned_modules.length > 0)

          ? t.assigned_modules.map(m => `<span class="badge" style="background:rgba(52,211,153,0.15); color:#34d399; font-size:0.75rem; padding:2px 8px; border-radius:10px; margin-right:4px;">${m.code || m}</span>`).join('')

          : '<span style="color:var(--text-muted); font-size:0.8rem;">Aucun</span>';



        tr.innerHTML = `

          <td style="padding:10px 14px; font-family:monospace; font-weight:600;">${this._escapeHtml(t.id)}</td>

          <td style="padding:10px 14px; font-weight:600; color:var(--text-primary);">${this._escapeHtml(t.username)}</td>

          <td style="padding:10px 14px;">${this._escapeHtml(t.full_name)}</td>

          <td style="padding:10px 14px;"><span style="font-family:monospace; font-size:0.85rem; background:rgba(255,255,255,0.06); padding:3px 8px; border-radius:4px; border:1px solid var(--card-border); color:#34d399;">${this._escapeHtml(t.plain_password || '••••••••')}</span></td>

          <td style="padding:10px 14px; font-size:0.82rem; color:var(--text-secondary);">${this._escapeHtml(t.email || '—')}</td>

          <td style="padding:10px 14px;">${modulesBadges}</td>

          <td style="padding:10px 14px; text-align:center;">

            <div style="display:inline-flex; gap:6px;">

              <button class="btn btn-secondary btn-admin-edit-teacher" data-id="${t.id}" style="padding:4px 8px; font-size:0.78rem;">✏️ Modifier</button>

              <button class="btn btn-danger btn-admin-delete-teacher" data-id="${t.id}" data-name="${t.full_name}" style="padding:4px 8px; font-size:0.78rem;">🗑️ Supprimer</button>

            </div>

          </td>

        `;

        tbody.appendChild(tr);

      });



      tbody.querySelectorAll('.btn-admin-edit-teacher').forEach(btn => {

        btn.onclick = () => {

          const id = btn.getAttribute('data-id');

          const t = (this._adminTeachersList || []).find(x => x.id === id);

          if (t) this.openAdminTeacherModal('edit', t);

        };

      });



      tbody.querySelectorAll('.btn-admin-delete-teacher').forEach(btn => {

        btn.onclick = async () => {

          const id = btn.getAttribute('data-id');

          const name = btn.getAttribute('data-name');

          const ok = await this.showConfirmModal({

            title: "Supprimer l'enseignant",

            message: `Confirmez-vous la suppression de l'enseignant "${name}" (${id}) ?`,

            confirmText: "Supprimer",

            cancelText: "Annuler",

            icon: "🗑️",

            danger: true

          });

          if (ok) {

            try {

              await api.deleteUser(id);

              this.showToast("Enseignant supprimé avec succès.", "success");

              await this.loadAdminTeachers();

              this.loadAdminOverview();

            } catch (e) {

              this.showToast(`Erreur de suppression : ${e.message}`, "danger");

            }

          }

        };

      });

    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  openAdminTeacherModal(mode = 'create', data = null) {

    const modal = document.getElementById('modal-admin-teacher');

    if (!modal) return;

    const title = document.getElementById('modal-admin-teacher-title');

    const modeInput = document.getElementById('admin-teacher-mode');

    const idInput = document.getElementById('admin-teacher-id');

    const userInput = document.getElementById('admin-teacher-username');

    const nameInput = document.getElementById('admin-teacher-fullname');

    const emailInput = document.getElementById('admin-teacher-email');

    const passInput = document.getElementById('admin-teacher-password');



    modeInput.value = mode;

    if (mode === 'edit' && data) {

      title.textContent = `✏️ Modifier l'Enseignant ${data.username}`;

      idInput.value = data.id;

      idInput.disabled = true;

      userInput.value = data.username;

      userInput.disabled = false;

      nameInput.value = data.full_name || '';

      emailInput.value = data.email || '';

      passInput.value = data.plain_password || '';

      passInput.placeholder = "Nouveau mot de passe enseignant";

      passInput.disabled = false;

    } else {

      title.textContent = '➕ Nouvel Enseignant';

      idInput.value = '';

      idInput.disabled = false;

      userInput.value = '';

      userInput.disabled = false;

      nameInput.value = '';

      emailInput.value = '';

      passInput.value = '';

      passInput.placeholder = "Auto-généré si vide";

      passInput.disabled = false;

    }

    modal.classList.add('active');

  }



  // --- Tab 4 : Gestion des Modules Académiques (CRUD REV-39) ---

  async loadAdminModules() {

    this.loadAdminLevelTests();

    const tbody = document.getElementById('admin-modules-table-body');

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des modules...</td></tr>';

    try {

      const modules = await api.listAdminModules();

      this._adminModulesList = modules;



      const countEl = document.getElementById('admin-modules-count');

      if (countEl) countEl.textContent = `${modules.length} module(s) académique(s)`;



      if (modules.length === 0) {

        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun module configuré.</td></tr>';

        return;

      }



      tbody.innerHTML = '';

      modules.forEach(m => {

        const tr = document.createElement('tr');

        tr.style.borderBottom = '1px solid var(--card-border)';

        const teachersBadges = (m.teachers && m.teachers.length > 0)

          ? m.teachers.map(t => {

              const name = (typeof t === 'object' && t !== null)

                ? (t.full_name || t.username || t.id || 'Enseignant')

                : String(t || 'Enseignant');

              return `<span class="badge" style="background:rgba(167,139,250,0.15); color:#a78bfa; font-size:0.75rem; padding:2px 8px; border-radius:10px; margin-right:4px;">${this._escapeHtml(name)}</span>`;

            }).join('')

          : '<span style="color:var(--text-muted); font-size:0.8rem;">Aucun enseignant</span>';



        tr.innerHTML = `

          <td style="padding:10px 14px; font-family:monospace; font-weight:700; color:#60a5fa;">${this._escapeHtml(m.code)}</td>

          <td style="padding:10px 14px; font-weight:600; color:var(--text-primary);">${this._escapeHtml(m.title)}</td>

          <td style="padding:10px 14px; font-size:0.82rem; color:var(--text-secondary); max-width:280px;">${this._escapeHtml(m.description || '—')}</td>

          <td style="padding:10px 14px;">${teachersBadges}</td>

          <td style="padding:10px 14px; text-align:center;">

            <div style="display:inline-flex; gap:6px;">

              <button class="btn btn-secondary btn-admin-assign-mod-teachers" data-code="${m.code}" style="padding:4px 8px; font-size:0.78rem;">👨‍🏫 Enseignants</button>

              <button class="btn btn-secondary btn-admin-edit-module" data-code="${m.code}" style="padding:4px 8px; font-size:0.78rem;">✏️ Modifier</button>

              <button class="btn btn-danger btn-admin-delete-module" data-code="${m.code}" data-title="${m.title}" style="padding:4px 8px; font-size:0.78rem;">🗑️ Supprimer</button>

            </div>

          </td>

        `;

        tbody.appendChild(tr);

      });



      tbody.querySelectorAll('.btn-admin-assign-mod-teachers').forEach(btn => {

        btn.onclick = () => {

          const code = btn.getAttribute('data-code');

          this.openAdminAssignModuleModal(code);

        };

      });



      tbody.querySelectorAll('.btn-admin-edit-module').forEach(btn => {

        btn.onclick = () => {

          const code = btn.getAttribute('data-code');

          const mod = (this._adminModulesList || []).find(x => x.code === code);

          if (mod) this.openAdminModuleModal('edit', mod);

        };

      });



      tbody.querySelectorAll('.btn-admin-delete-module').forEach(btn => {

        btn.onclick = async () => {

          const code = btn.getAttribute('data-code');

          const title = btn.getAttribute('data-title');

          const ok = await this.showConfirmModal({

            title: "Supprimer le module",

            message: `Confirmez-vous la suppression définitive du module "${title}" (${code}) ?`,

            confirmText: "Supprimer",

            cancelText: "Annuler",

            icon: "🗑️",

            danger: true

          });

          if (ok) {

            try {

              await api.deleteModule(code);

              this.showToast("Module supprimé avec succès.", "success");

              await this.loadAdminModules();

              this.loadAdminOverview();

            } catch (e) {

              this.showToast(`Erreur de suppression : ${e.message}`, "danger");

            }

          }

        };

      });

    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  openAdminModuleModal(mode = 'create', data = null) {

    const modal = document.getElementById('modal-admin-module');

    if (!modal) return;

    const title = document.getElementById('modal-admin-module-title');

    const modeInput = document.getElementById('admin-module-mode');

    const codeInput = document.getElementById('admin-module-code');

    const titleInput = document.getElementById('admin-module-title');

    const descInput = document.getElementById('admin-module-desc');



    modeInput.value = mode;

    if (mode === 'edit' && data) {

      title.textContent = `✏️ Modifier le Module ${data.code}`;

      codeInput.value = data.code;

      codeInput.disabled = true;

      titleInput.value = data.title || '';

      descInput.value = data.description || '';

    } else {

      title.textContent = '➕ Nouveau Module Académique';

      codeInput.value = '';

      codeInput.disabled = false;

      titleInput.value = '';

      descInput.value = '';

    }

    modal.classList.add('active');

  }



  async openAdminAssignModuleModal(moduleCode) {

    const modal = document.getElementById('modal-admin-assign-module');

    if (!modal) return;

    document.getElementById('admin-assign-module-code').value = moduleCode;

    document.getElementById('modal-admin-assign-title').textContent = `📚 Affectations au Module : ${moduleCode}`;



    try {

      const [allTeachers, modData] = await Promise.all([

        api.listUsers('teacher'),

        api.request(`/modules/${encodeURIComponent(moduleCode)}`)

      ]);



      const assignedTeachers = modData.teachers || [];

      const assignedIds = new Set(assignedTeachers.map(t => (typeof t === 'object' && t !== null) ? t.id : String(t)));

      const unassignedTeachers = allTeachers.filter(t => !assignedIds.has(t.id));



      const selectEl = document.getElementById('admin-assign-teacher-select');

      if (selectEl) {

        if (unassignedTeachers.length === 0) {

          selectEl.innerHTML = '<option value="">Tous les enseignants sont déjà affectés</option>';

        } else {

          selectEl.innerHTML = unassignedTeachers.map(t => `<option value="${t.id}">${this._escapeHtml(t.full_name || t.username)} (@${this._escapeHtml(t.username)})</option>`).join('');

        }

      }



      const listEl = document.getElementById('admin-assign-teachers-list');

      if (listEl) {

        if (assignedTeachers.length === 0) {

          listEl.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:8px 0;">Aucun enseignant actuellement affecté à ce module.</div>';

        } else {

          listEl.innerHTML = '';

          assignedTeachers.forEach(t => {

            const row = document.createElement('div');

            row.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); padding:8px 12px; border-radius:6px; border:1px solid var(--card-border);';

            const tid = (typeof t === 'object' && t !== null) ? (t.id || t.username || '') : String(t);

            const tname = (typeof t === 'object' && t !== null) ? (t.full_name || t.username || t.id || 'Enseignant') : String(t);

            const tuname = (typeof t === 'object' && t !== null) ? (t.username || t.id || '') : String(t);

            row.innerHTML = `

              <div>

                <strong>${this._escapeHtml(tname)}</strong>

                <span style="font-size:0.8rem; color:var(--text-muted); margin-left:8px;">@${this._escapeHtml(tuname)} (${this._escapeHtml(tid)})</span>

              </div>

              <button class="btn btn-danger btn-admin-remove-teacher-mod" data-tid="${this._escapeHtml(tid)}" style="padding:3px 8px; font-size:0.75rem;">❌ Retirer</button>

            `;

            listEl.appendChild(row);

          });



          listEl.querySelectorAll('.btn-admin-remove-teacher-mod').forEach(btn => {

            btn.onclick = async () => {

              const tid = btn.getAttribute('data-tid');

              try {

                await api.removeTeacherModule(moduleCode, tid);

                await this.openAdminAssignModuleModal(moduleCode);

                this.loadAdminModules();

              } catch (err) {

                this.showToast(`Erreur de retrait : ${err.message}`, "danger");

              }

            };

          });

        }

      }



      modal.classList.add('active');

    } catch (err) {

      this.showToast(`Erreur lors du chargement des affectations : ${err.message}`, "danger");

    }

  }



  // --- Tab 5 : Gestion des Examens & Épreuves (CRUD REV-39) ---

  async loadAdminExams() {

    const tbody = document.getElementById('admin-exams-table-body');

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des examens...</td></tr>';

    try {

      const exams = await api.request('/exams');

      this._adminExamsList = exams;



      const countEl = document.getElementById('admin-exams-count');

      if (countEl) countEl.textContent = `${exams.length} examen(s) programmé(s)`;



      if (exams.length === 0) {

        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun examen créé pour le moment.</td></tr>';

        return;

      }



      tbody.innerHTML = '';

      exams.forEach(ex => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--card-border)';

        const sessStatus = ex.session_status || 'not_started';
        const isCompleted = sessStatus === 'completed';

        let statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(148,163,184,0.15); color:#cbd5e1; border:1px solid #64748b; font-weight:700; white-space:nowrap;">⚪ Non démarré</span>`;
        if (sessStatus === 'waiting') {
          statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(245,158,11,0.15); color:#fcd34d; border:1px solid #f59e0b; font-weight:700; white-space:nowrap;">⏳ Salle ouverte</span>`;
        } else if (sessStatus === 'in_progress') {
          statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(16,185,129,0.18); color:#6ee7b7; border:1px solid #10b981; font-weight:700; white-space:nowrap;">🟢 En cours</span>`;
        } else if (isCompleted) {
          statusBadgeHtml = `<span class="badge" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(168,85,247,0.18); color:#d8b4fe; border:1px solid #a855f7; font-weight:700; white-space:nowrap;">🟣 Terminé (${ex.submitted_count || 0})</span>`;
        }

        let primaryBtnHtml = '';
        let menuItemsHtml = '';

        if (isCompleted) {
          primaryBtnHtml = `
            <button class="btn btn-secondary btn-admin-analysis-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}" data-module="${ex.module_code}" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:rgba(16,185,129,0.15); border:1px solid #10b981; color:#6ee7b7; font-weight:600; white-space:nowrap;" title="Analyse psychométrique & discrimination">
              📊 Stats
            </button>
          `;
          menuItemsHtml = `
            <button class="menu-action-item btn-admin-grades-csv-exam" data-id="${ex.id}" data-module="${ex.module_code}">
              <span>📥</span> <span>Notes CSV</span>
            </button>
            <button class="menu-action-item btn-admin-grades-pdf-exam" data-id="${ex.id}" data-module="${ex.module_code}">
              <span>📄</span> <span>PV PDF</span>
            </button>
            <button class="menu-action-item btn-admin-download-copies-zip" data-id="${ex.id}" data-module="${ex.module_code}" style="color:#38bdf8;">
              <span>📦</span> <span>Copies Étudiants (ZIP)</span>
            </button>
            <button class="menu-action-item btn-admin-questions-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}">
              <span>📝</span> <span>Gérer Questions</span>
            </button>
            <button class="menu-action-item btn-admin-export-pkg-exam" data-id="${ex.id}" data-module="${ex.module_code}">
              <span>📦</span> <span>Exporter (.exam.zip)</span>
            </button>
            <button class="menu-action-item danger btn-admin-delete-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}">
              <span>🗑️</span> <span>Supprimer (Super Admin)</span>
            </button>
          `;
        } else if (sessStatus === 'in_progress') {
          primaryBtnHtml = `
            <button class="btn btn-primary btn-admin-proctor-exam" data-id="${ex.id}" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; background:#10b981; border:1px solid #059669; font-weight:700; white-space:nowrap;">
              🖥️ Surveiller
            </button>
          `;
          menuItemsHtml = `
            <button class="menu-action-item btn-admin-questions-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}">
              <span>📝</span> <span>Questions</span>
            </button>
            <button class="menu-action-item btn-admin-export-pkg-exam" data-id="${ex.id}" data-module="${ex.module_code}">
              <span>📦</span> <span>Exporter (.exam.zip)</span>
            </button>
          `;
        } else {
          primaryBtnHtml = `
            <button class="btn btn-primary btn-admin-proctor-exam" data-id="${ex.id}" style="display:inline-flex; align-items:center; justify-content:center; height:28px; line-height:26px; padding:0 10px; font-size:0.76rem; border-radius:6px; box-sizing:border-box; font-weight:600; white-space:nowrap;">
              🖥️ Surveiller
            </button>
          `;
          menuItemsHtml = `
            <button class="menu-action-item btn-admin-questions-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}">
              <span>📝</span> <span>Gérer Questions</span>
            </button>
            <button class="menu-action-item btn-admin-export-pkg-exam" data-id="${ex.id}" data-module="${ex.module_code}">
              <span>📦</span> <span>Exporter (.exam.zip)</span>
            </button>
            <button class="menu-action-item danger btn-admin-delete-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}">
              <span>🗑️</span> <span>Supprimer</span>
            </button>
          `;
        }

        tr.innerHTML = `
          <td style="padding:10px 14px; vertical-align:middle;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px; flex-wrap:wrap;">
              <span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8; font-size:0.75rem; padding:2px 6px; border-radius:4px; font-weight:700;">${this._escapeHtml(ex.module_code)}</span>
              <span style="font-weight:600; color:var(--text-primary); font-size:0.92rem;">${this._escapeHtml(ex.title)}</span>
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">${this._escapeHtml(ex.id)}</div>
          </td>
          <td style="padding:10px 14px; vertical-align:middle; white-space:nowrap;">${statusBadgeHtml}</td>
          <td style="padding:10px 14px; vertical-align:middle; font-size:0.85rem; font-weight:600; white-space:nowrap;">⏱️ ${ex.duration_minutes} min</td>
          <td style="padding:10px 14px; vertical-align:middle; font-size:0.85rem; white-space:nowrap;"><span style="font-weight:700; color:#60a5fa;">${ex.questions ? ex.questions.length : (ex.question_count || '—')}</span> Q</td>
          <td style="padding:10px 14px; vertical-align:middle; font-size:0.85rem; font-weight:600; white-space:nowrap;">🎯 / ${ex.global_points}</td>
          <td style="padding:10px 14px; vertical-align:middle; text-align:center;">
            <div style="display:inline-flex; align-items:center; gap:6px; position:relative;">
              ${primaryBtnHtml}
              <div class="row-menu-wrapper">
                <button class="btn btn-secondary btn-row-menu-toggle" type="button" title="Options supplémentaires" style="height:28px; line-height:26px; width:28px; padding:0; display:inline-flex; align-items:center; justify-content:center; border-radius:6px;">⋮</button>
                <div class="row-actions-dropdown">
                  ${menuItemsHtml}
                </div>
              </div>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-row-menu-toggle').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const menu = btn.nextElementSibling;
          const isVisible = menu && menu.style.display === 'block';
          document.querySelectorAll('.row-actions-dropdown').forEach(m => m.style.display = 'none');
          if (!isVisible && menu) {
            menu.style.display = 'block';
          }
        };
      });

      tbody.querySelectorAll('.btn-admin-proctor-exam').forEach(btn => {
        btn.onclick = () => {
          const id = btn.getAttribute('data-id');
          this.openExamProctoringRoom(id);
        };
      });

      tbody.querySelectorAll('.btn-admin-analysis-exam').forEach(btn => {
        btn.onclick = () => {
          const id = btn.getAttribute('data-id');
          const title = btn.getAttribute('data-title');
          const moduleCode = btn.getAttribute('data-module');
          this.openItemAnalysisModal(id, title, moduleCode);
        };
      });

      tbody.querySelectorAll('.btn-admin-questions-exam').forEach(btn => {
        btn.onclick = () => {
          const id = btn.getAttribute('data-id');
          const title = btn.getAttribute('data-title');
          this.openManageQuestionsModal(id, title);
        };
      });

      tbody.querySelectorAll('.btn-admin-grades-csv-exam').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const moduleCode = btn.getAttribute('data-module');
          try {
            await api.downloadExamResultsCsv(id, moduleCode);
            this.showToast('Notes finales (CSV) téléchargées avec succès.', 'success');
          } catch (e) {
            this.showToast(`Erreur lors du téléchargement CSV : ${e.message}`, 'danger');
          }
        };
      });

      tbody.querySelectorAll('.btn-admin-download-copies-zip').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const moduleCode = btn.getAttribute('data-module');
          try {
            this.showToast("Génération de l'archive des copies en cours...", "info");
            await api.downloadExamStudentCopiesZip(id, moduleCode);
            this.showToast("Copies des étudiants (ZIP) téléchargées avec succès.", "success");
          } catch (e) {
            this.showToast(`Erreur lors du téléchargement des copies : ${e.message}`, "danger");
          }
        };
      });

      tbody.querySelectorAll('.btn-admin-grades-pdf-exam').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const moduleCode = btn.getAttribute('data-module');
          try {
            await api.downloadExamResultsPdf(id, moduleCode);
            this.showToast('PV des notes finales (PDF) téléchargé avec succès.', 'success');
          } catch (e) {
            this.showToast(`Erreur lors du téléchargement PDF : ${e.message}`, 'danger');
          }
        };
      });

      tbody.querySelectorAll('.btn-admin-export-pkg-exam').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const moduleCode = btn.getAttribute('data-module');
          try {
            await api.exportExamPackage(id, `examen_${moduleCode}_${id}.exam.zip`);
            this.showToast('Package exporté avec succès.', 'success');
          } catch (e) {
            this.showToast(`Erreur d'exportation du package : ${e.message}`, 'danger');
          }
        };
      });

      tbody.querySelectorAll('.btn-admin-delete-exam').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const title = btn.getAttribute('data-title');
          const ok = await this.showConfirmModal({
            title: "Supprimer l'examen",
            message: `Confirmez-vous la suppression de l'examen "${title}" ?\nToutes les sessions et questions associées seront supprimées.`,
            confirmText: "Supprimer",
            cancelText: "Annuler",
            icon: "🗑️",
            danger: true
          });
          if (ok) {
            try {
              await api.deleteExam(id);
              this.showToast("Examen supprimé avec succès.", "success");
              await this.loadAdminExams();
              this.loadAdminOverview();
            } catch (e) {
              this.showToast(`Erreur de suppression : ${e.message}`, "danger");
            }
          }
        };
      });


    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  _renderSimpleMarkdown(text) {

    if (!text) return '';

    let processed = String(text);



    // 0. Nettoyage initial : en-têtes préfixés du type **[...]** ou [...] (REV-21) et phrases parasites

    processed = processed

      .replace(/^(\*\*\[(.*?)\]\*\*|\[(.*?)\])\s*/, '')

      .replace(/\*?Écrivez votre fonction\/script Python ci-dessous et testez son exécution locale\s*:?\*?/gi, '')

      .trim();



    // 1. Extraire et protéger les formules mathématiques KaTeX ($$...$$ et $...$)

    const mathBlocks = [];

    processed = processed.replace(/\$\$([\s\S]*?)\$\$/g, (match) => {

      const id = `___MATHBLOCK_${mathBlocks.length}___`;

      mathBlocks.push(this._escapeHtml(match));

      return id;

    });

    processed = processed.replace(/(^|[^\\])\$([^\$\n]+?)\$/g, (match, prefix, formula) => {

      if (/^\s*\d+([.,]\d+)?\s*$/.test(formula)) return match;

      const id = `___MATHINLINE_${mathBlocks.length}___`;

      mathBlocks.push(this._escapeHtml(`$${formula}$`));

      return prefix + id;

    });



    // 2. Extraire et protéger les blocs de code explicites (```lang ... ```)

    const codeBlocks = [];

    processed = processed.replace(/```([a-zA-Z0-9_\-+#.]*)[ \t]*[\n]+([\s\S]*?)[\n]*```/g, (match, lang, code) => {

      const id = `___CODEBLOCK_${codeBlocks.length}___`;

      const cleanLang = (lang || '').trim().toLowerCase();

      const displayLang = cleanLang ? (cleanLang === 'py' ? 'python' : cleanLang) : 'code';

      const cleanCode = code.replace(/\n/g, '\n').replace(/\r/g, '\n').trimEnd();

      const escapedCode = this._escapeHtml(cleanCode);

      const blockHtml = `\n\n<div class="formatted-code-container"><div class="formatted-code-header"><span class="code-lang-badge">${this._escapeHtml(displayLang)}</span></div><pre class="code-block"><code class="language-${displayLang}">${escapedCode}</code></pre></div>\n\n`;

      codeBlocks.push(blockHtml);

      return id;

    });



    // 3. Extraire et protéger les segments de code inline (`...`)

    const inlineCodes = [];

    processed = processed.replace(/`([^`\n]+)`/g, (match, code) => {

      const id = `___INLINECODE_${inlineCodes.length}___`;

      inlineCodes.push(`<code class="md-inline-code">${this._escapeHtml(code)}</code>`);

      return id;

    });



    // 4. Échappement HTML sécurisé du texte libre

    const segments = processed.split(/(___[A-Z0-9_]+___)/g);

    processed = segments.map(seg => {

      if (seg.startsWith('___')) return seg;

      return this._escapeHtml(seg);

    }).join('');



    // 5. Titres Markdown (####, ###, ##, #)

    processed = processed.replace(/^#### (.*$)/gim, '\n\n<h5 style="color:#bfdbfe; margin:10px 0 6px 0; font-size:1.0rem; font-weight:700;">$1</h5>\n\n');

    processed = processed.replace(/^### (.*$)/gim, '\n\n<h4 style="color:#93c5fd; margin:12px 0 6px 0; font-size:1.08rem; font-weight:700;">$1</h4>\n\n');

    processed = processed.replace(/^## (.*$)/gim, '\n\n<h3 style="color:#60a5fa; margin:14px 0 8px 0; font-size:1.18rem; font-weight:700;">$1</h3>\n\n');

    processed = processed.replace(/^# (.*$)/gim, '\n\n<h2 style="color:#3b82f6; margin:16px 0 10px 0; font-size:1.28rem; font-weight:700;">$1</h2>\n\n');



    // 6. Typographie (Gras et Italique)

    processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary); font-weight:700;">$1</strong>');

    processed = processed.replace(/\*(.*?)\*/g, '<em style="color:#cbd5e1; font-style:italic;">$1</em>');



    // 7. Listes ordonnées et non-ordonnées

    processed = processed.replace(/(?:^|\n)((?:[ \t]*[-*]\s+[^\n]+(?:\r?\n|$))+)/g, (match, listBlock) => {

      const items = listBlock.trim().split(/\r?\n/).map(l => l.replace(/^[ \t]*[-*]\s+/, '').trim()).filter(Boolean);

      return '\n\n<ul class="md-list">' + items.map(it => `<li>${it}</li>`).join('') + '</ul>\n\n';

    });



    // 8. Restitution des paragraphes

    const paragraphs = processed.split(/\r?\n\s*\r?\n/);

    processed = paragraphs.map(p => {

      const trimmed = p.trim();

      if (!trimmed) return '';

      if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<div') || trimmed.startsWith('___CODEBLOCK_')) {

        return trimmed;

      }

      return `<p style="margin-bottom:8px; line-height:1.6;">${trimmed.replace(/\r?\n/g, '<br>')}</p>`;

    }).filter(Boolean).join('');



    // 9. Restitution des éléments protégés

    codeBlocks.forEach((block, idx) => {

      processed = processed.split(`___CODEBLOCK_${idx}___`).join(block);

    });

    inlineCodes.forEach((code, idx) => {

      processed = processed.split(`___INLINECODE_${idx}___`).join(code);

    });

    mathBlocks.forEach((math, idx) => {

      processed = processed.split(`___MATHBLOCK_${idx}___`).join(math);

      processed = processed.split(`___MATHINLINE_${idx}___`).join(math);

    });



    return processed;

  }



  toggleFullscreen() {
    if (this.activeAntiCheat && this.activeAntiCheat.isActive) {
      // Durant un examen officiel ou un test de niveau, le plein écran est obligatoire et ne peut être quitté
      if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        const elem = document.documentElement;
        if (elem.requestFullscreen) {
          elem.requestFullscreen().catch(() => {});
        } else if (elem.webkitRequestFullscreen) {
          elem.webkitRequestFullscreen();
        }
      }
      return;
    }

    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(() => {});
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      }
    }
  }

  _updateFullscreenButtonText() {
    const btn = document.getElementById('btn-toggle-fullscreen');
    if (!btn) return;
    const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement);
    if (this.activeAntiCheat && this.activeAntiCheat.isActive) {
      btn.innerHTML = '<span>⛶</span> Plein Écran Obligatoire';
      btn.title = 'Le mode Plein Écran est obligatoire durant les épreuves et tests de niveau.';
      return;
    }
    btn.title = '';
    btn.innerHTML = isFull ? '<span>✖️</span> Quitter Plein Écran' : '<span>⛶</span> Plein Écran';

  }



  _initGlobalExamFontScale() {

    const viewExam = document.getElementById('view-exam');

    const btnDecrease = document.getElementById('btn-exam-font-decrease');

    const btnIncrease = document.getElementById('btn-exam-font-increase');

    const btnReset = document.getElementById('btn-exam-font-reset');

    const labelScale = document.getElementById('label-exam-font-scale');



    if (!viewExam) return;



    let savedScale = parseFloat(localStorage.getItem('exam_font_scale')) || 1.0;

    if (savedScale < 0.8 || savedScale > 1.6) savedScale = 1.0;



    const applyScale = (s) => {

      savedScale = Math.round(s * 100) / 100;

      viewExam.style.setProperty('--exam-font-scale', savedScale);

      try { localStorage.setItem('exam_font_scale', savedScale); } catch (_) {}

      if (labelScale) labelScale.textContent = `${Math.round(savedScale * 100)}%`;

      if (window._activeExamCodeMirror) {

        try { window._activeExamCodeMirror.refresh(); } catch (_) {}

      }

    };



    applyScale(savedScale);



    if (btnDecrease) {

      btnDecrease.onclick = (e) => {

        e.preventDefault();

        if (savedScale > 0.85) applyScale(savedScale - 0.1);

      };

    }

    if (btnIncrease) {

      btnIncrease.onclick = (e) => {

        e.preventDefault();

        if (savedScale < 1.5) applyScale(savedScale + 0.1);

      };

    }

    if (btnReset) {

      btnReset.onclick = (e) => {

        e.preventDefault();

        applyScale(1.0);

      };

    }

  }



  renderStudentDashboard() {

    return this.renderDashboard(this.currentUser);

  }



  requestFullscreen() {

    try {

      if (!document.fullscreenElement && !document.webkitFullscreenElement) {

        const elem = document.documentElement;

        if (elem.requestFullscreen) {

          elem.requestFullscreen().catch(() => {});

        } else if (elem.webkitRequestFullscreen) {

          try { elem.webkitRequestFullscreen(); } catch (_) {}

        }

      }

    } catch (_) {}

  }



  exitFullscreen() {

    try {

      if (document.fullscreenElement || document.webkitFullscreenElement) {

        if (document.exitFullscreen) {

          document.exitFullscreen().catch(() => {});

        } else if (document.webkitExitFullscreen) {

          try { document.webkitExitFullscreen(); } catch (_) {}

        }

      }

    } catch (_) {}

  }



  _handleWaitingRoomFullscreenChange() {

    if (this.currentView !== 'view-waiting-room') return;

    const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement);

    const waitingView = document.getElementById('view-waiting-room');

    const overlayFs = document.getElementById('overlay-fullscreen-required');



    if (!isFull) {

      if (waitingView) waitingView.classList.add('exam-fullscreen-lost-blurred');

      if (overlayFs) {

        overlayFs.classList.add('active');

        const btnRestore = document.getElementById('btn-restore-fullscreen');

        if (btnRestore) {

          btnRestore.onclick = () => this.requestFullscreen();

        }

      }

    } else {

      if (waitingView) waitingView.classList.remove('exam-fullscreen-lost-blurred');

      if (overlayFs) overlayFs.classList.remove('active');

    }

  }



  showWarningToast(message) {

    const toast = document.getElementById('warning-toast');

    if (!toast) return;

    toast.textContent = message;

    toast.style.display = 'flex';

    if (this._warningToastTimeout) clearTimeout(this._warningToastTimeout);

    this._warningToastTimeout = setTimeout(() => {

      toast.style.display = 'none';

    }, 4500);

  }



  _updateWarningBadge(count, max = 4) {

    const badge = document.getElementById('exam-mode-badge');

    if (!badge) return;

    badge.textContent = `⚠️ Avertissements : ${count}/${max} (Si 4 avertissements atteints, le test prend fin et les résultats sont enregistrés)`;

    if (count >= 3) {

      badge.style.background = "rgba(239, 68, 68, 0.25)";

      badge.style.color = "#f87171";

      badge.style.borderColor = "var(--danger)";

    } else if (count >= 1) {

      badge.style.background = "rgba(245, 158, 11, 0.25)";

      badge.style.color = "#fbbf24";

      badge.style.borderColor = "#f59e0b";

    } else {

      badge.style.background = "rgba(59, 130, 246, 0.15)";

      badge.style.color = "#93c5fd";

      badge.style.borderColor = "var(--accent-primary)";

    }

  }



  // --- Tab 6 : Gestion des Bulletins Académiques (REV-45) ---

  async loadAdminBulletins() {

    const tbody = document.getElementById('admin-bulletins-table-body');

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="12" style="text-align:center; padding:20px; color:var(--text-muted);">Génération et calcul des bulletins académiques...</td></tr>';



    try {

      const [bulletins, groups] = await Promise.all([

        api.getAdminBulletins(),

        api.listGroups()

      ]);

      this._adminBulletinsList = bulletins;



      const filterSpeciality = document.getElementById('admin-bulletins-filter-speciality');

      if (filterSpeciality) {

        const cur = filterSpeciality.value;

        filterSpeciality.innerHTML = '<option value="">Toutes les Spécialités</option>' + groups.map(g => `<option value="${g.id}">${g.name || g.id}</option>`).join('');

        filterSpeciality.value = cur;

      }



      this._renderAdminBulletinsRows();

    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  _renderAdminBulletinsRows() {

    const tbody = document.getElementById('admin-bulletins-table-body');

    if (!tbody) return;



    const filterSpec = document.getElementById('admin-bulletins-filter-speciality')?.value || '';

    const searchVal = (document.getElementById('admin-bulletins-search')?.value || '').toLowerCase().trim();



    let list = (this._adminBulletinsList || []).slice();

    if (filterSpec) {

      list = list.filter(b => b.speciality === filterSpec);

    }

    if (searchVal) {

      list = list.filter(b =>

        (b.student_id && b.student_id.toLowerCase().includes(searchVal)) ||

        (b.full_name && b.full_name.toLowerCase().includes(searchVal)) ||

        (b.username && b.username.toLowerCase().includes(searchVal)) ||

        (b.speciality && b.speciality.toLowerCase().includes(searchVal))

      );

    }



    // Tri dynamique par module ou moyenne générale

    const sortMod = document.getElementById('admin-bulletins-sort-module')?.value || 'AVG';

    if (sortMod === 'AVG') {

      list.sort((a, b) => (b.general_average !== null ? b.general_average : -1) - (a.general_average !== null ? a.general_average : -1));

    } else if (['ALGO', 'PYTHON_INIT', 'CRYPTO', 'LINUX_ADMIN'].includes(sortMod)) {

      list.sort((a, b) => {

        const sa = a.fundamentals?.[sortMod]?.score !== null && a.fundamentals?.[sortMod]?.score !== undefined ? a.fundamentals[sortMod].score : -1;

        const sb = b.fundamentals?.[sortMod]?.score !== null && b.fundamentals?.[sortMod]?.score !== undefined ? b.fundamentals[sortMod].score : -1;

        return sb - sa;

      });

    } else if (sortMod === 'THEO') {

      list.sort((a, b) => {

        const sa = a.exams?.theoretical?.score !== null && a.exams?.theoretical?.score !== undefined ? a.exams.theoretical.score : -1;

        const sb = b.exams?.theoretical?.score !== null && b.exams?.theoretical?.score !== undefined ? b.exams.theoretical.score : -1;

        return sb - sa;

      });

    } else if (sortMod === 'PRAC') {

      list.sort((a, b) => {

        const sa = a.exams?.practical?.score !== null && a.exams?.practical?.score !== undefined ? a.exams.practical.score : -1;

        const sb = b.exams?.practical?.score !== null && b.exams?.practical?.score !== undefined ? b.exams.practical.score : -1;

        return sb - sa;

      });

    }



    const countEl = document.getElementById('admin-bulletins-count');

    if (countEl) countEl.textContent = `${list.length} bulletin(s) affiché(s) (${(this._adminBulletinsList || []).length} total)`;



    if (list.length === 0) {

      tbody.innerHTML = '<tr><td colspan="12" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun bulletin académique trouvé.</td></tr>';

      return;

    }



    tbody.innerHTML = '';

    list.forEach(b => {

      const f = b.fundamentals;

      const ex = b.exams;

      const tr = document.createElement('tr');

      tr.style.borderBottom = '1px solid var(--card-border)';

      

      const formatMark = (mark) => mark !== null && mark !== undefined ? `<span style="font-weight:600; color:${mark >= 10.0 ? '#34d399' : '#f87171'};">${mark.toFixed(1)}</span>` : '<span style="color:var(--text-muted);">—</span>';

      

      tr.innerHTML = `

        <td style="padding:10px 14px; font-family:monospace; font-weight:600;">${this._escapeHtml(b.student_id)}</td>

        <td style="padding:10px 14px; font-weight:600; color:var(--text-primary);">${this._escapeHtml(b.full_name)}</td>

        <td style="padding:10px 14px;"><span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8; font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(b.speciality)}</span></td>

        <td style="padding:10px 14px; text-align:center;">${formatMark(f.ALGO?.score)}</td>

        <td style="padding:10px 14px; text-align:center;">${formatMark(f.PYTHON_INIT?.score)}</td>

        <td style="padding:10px 14px; text-align:center;">${formatMark(f.CRYPTO?.score)}</td>

        <td style="padding:10px 14px; text-align:center;">${formatMark(f.LINUX_ADMIN?.score)}</td>

        <td style="padding:10px 14px; text-align:center;">${formatMark(ex.theoretical?.score)}</td>

        <td style="padding:10px 14px; text-align:center;">${formatMark(ex.practical?.score)}</td>

        <td style="padding:10px 14px; text-align:center; font-weight:700; font-size:0.95rem; color:${b.is_pass ? '#10b981' : (b.general_average !== null ? '#ef4444' : 'var(--text-muted)')};">

          ${b.general_average !== null ? b.general_average.toFixed(2) + ' / 20' : '—'}

        </td>

        <td style="padding:10px 14px; text-align:center;">

          <span style="display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:700; background:${b.is_pass ? 'rgba(16,185,129,0.15)' : (b.general_average !== null ? 'rgba(239,68,68,0.15)' : 'rgba(100,116,139,0.15)')}; color:${b.verdict_color}; border:1px solid ${b.verdict_color};">

            ${b.verdict_label}

          </span>

        </td>

        <td style="padding:10px 14px; text-align:center;">

          <div style="display:inline-flex; gap:4px; flex-wrap:wrap; justify-content:center;">

            <button class="btn btn-primary btn-view-bulletin" data-id="${b.student_id}" title="Consulter le bulletin officiel" style="padding:3px 6px; font-size:0.75rem;">👁️ Voir</button>

            <button class="btn btn-secondary btn-download-bulletin-pdf" data-id="${b.student_id}" title="Télécharger en PDF" style="padding:3px 6px; font-size:0.75rem; background:#1e3a8a; color:#fff; border-color:#1e40af;">📄 PDF</button>

            <button class="btn btn-secondary btn-download-bulletin-docx" data-id="${b.student_id}" title="Télécharger en Word (.docx)" style="padding:3px 6px; font-size:0.75rem; background:#2563eb; color:#fff; border-color:#1d4ed8;">📝 Word</button>

            <button class="btn btn-secondary btn-print-quick-bulletin" data-id="${b.student_id}" title="Imprimer directement" style="padding:3px 6px; font-size:0.75rem;">🖨️</button>

          </div>

        </td>

      `;

      tbody.appendChild(tr);

    });



    tbody.querySelectorAll('.btn-view-bulletin').forEach(btn => {

      btn.onclick = () => this.openStudentBulletinModal(btn.getAttribute('data-id'));

    });

    tbody.querySelectorAll('.btn-download-bulletin-pdf').forEach(btn => {

      btn.onclick = async () => {

        try {

          await api.downloadStudentBulletinPdf(btn.getAttribute('data-id'));

        } catch (e) {

          this.showToast(`Erreur téléchargement PDF : ${e.message}`, "danger");

        }

      };

    });

    tbody.querySelectorAll('.btn-download-bulletin-docx').forEach(btn => {

      btn.onclick = async () => {

        try {

          await api.downloadStudentBulletinDocx(btn.getAttribute('data-id'));

        } catch (e) {

          this.showToast(`Erreur téléchargement Word : ${e.message}`, "danger");

        }

      };

    });

    tbody.querySelectorAll('.btn-print-quick-bulletin').forEach(btn => {

      btn.onclick = async () => {

        await this.openStudentBulletinModal(btn.getAttribute('data-id'));

        window.print();

      };

    });

  }



  async openStudentBulletinModal(studentId) {

    this.activeBulletinStudentId = studentId;

    const modal = document.getElementById('modal-admin-bulletin');

    const area = document.getElementById('printable-bulletin-area');

    if (!modal || !area) return;



    area.innerHTML = '<div style="text-align:center; padding:40px; color:#64748b;">Chargement des données du bulletin officiel...</div>';

    modal.classList.add('active');



    try {

      const b = (this.currentUser && this.currentUser.role === 'student') 

        ? await api.getMyBulletin() 

        : await api.getSingleStudentBulletin(studentId);

      const f = b.fundamentals;

      const ex = b.exams;



      const renderGaugeBar = (label, score) => {

        const val = score !== null && score !== undefined ? score : 0;

        const pct = Math.min(100, Math.max(0, (val / 20.0) * 100));

        return `

          <div style="margin-bottom: 12px;">

            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">

              <span style="font-weight:600; color:#1e293b;">${label}</span>

              <span style="font-weight:700; color:${val >= 10.0 ? '#059669' : '#dc2626'};">${score !== null && score !== undefined ? score.toFixed(1) + ' / 20 (' + pct.toFixed(0) + '%)' : 'Non évalué'}</span>

            </div>

            <div style="height:10px; background:#e2e8f0; border-radius:5px; overflow:hidden;">

              <div style="width:${pct}%; height:100%; background:${val >= 10.0 ? 'linear-gradient(90deg, #10b981, #059669)' : 'linear-gradient(90deg, #ef4444, #dc2626)'}; border-radius:5px;"></div>

            </div>

          </div>

        `;

      };



      area.innerHTML = `

        <div style="border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">

          <div>

            <div style="font-size: 0.8rem; font-weight: 700; letter-spacing: 1px; color: #64748b; text-transform: uppercase;">République / Établissement d'Enseignement Supérieur</div>

            <h1 style="margin: 4px 0 0 0; font-size: 1.6rem; color: #0f172a; font-weight: 800;">BULLETIN OFFICIEL DE NOTES & COMPÉTENCES</h1>

            <div style="font-size: 0.9rem; color: #475569; margin-top: 4px;">Session Académique 2026 — Plateforme d'Évaluation Autonome LAN</div>

          </div>

          <div style="text-align: right; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 16px;">

            <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600;">Date d'édition</div>

            <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a;">${new Date().toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })}</div>

          </div>

        </div>



        <!-- Identité Étudiant -->

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin-bottom: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">

          <div>

            <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 600;">Nom & Prénom</div>

            <div style="font-size: 1.15rem; font-weight: 800; color: #0f172a;">${this._escapeHtml(b.full_name)}</div>

          </div>

          <div>

            <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 600;">Matricule / Identifiant</div>

            <div style="font-size: 1.05rem; font-weight: 700; font-family: monospace; color: #0284c7;">${this._escapeHtml(b.student_id)} (${this._escapeHtml(b.username)})</div>

          </div>

          <div>

            <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 600;">Spécialité Académique</div>

            <div style="font-size: 1.05rem; font-weight: 700; color: #4f46e5;">${this._escapeHtml(b.speciality)}</div>

          </div>

          <div>

            <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 600;">Mot de Passe (Consultation)</div>

            <div style="font-size: 0.95rem; font-weight: 700; font-family: monospace; color: #0f172a; background: #e2e8f0; padding: 2px 8px; border-radius: 4px; display: inline-block;">${this._escapeHtml(b.plain_password)}</div>

          </div>

        </div>



        <!-- Section 1 : Piliers Fondamentaux (Tests de Diagnostic Initial & Progression) -->

        <div style="margin-bottom: 24px;">

          <h3 style="font-size: 1.05rem; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">

            <span>1. Piliers Fondamentaux (Évaluations Initiales & Entraînements)</span>

            <span style="font-size: 0.9rem; color: #0284c7; font-weight: 700;">Moyenne Piliers : ${b.fundamentals_average !== null ? b.fundamentals_average.toFixed(2) + ' / 20' : '—'}</span>

          </h3>

          <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">

            ${renderGaugeBar("Algorithmique Fondamentale (ALGO)", f.ALGO?.score)}

            ${renderGaugeBar("Initiation & Pratique Python (PYTHON_INIT)", f.PYTHON_INIT?.score)}

            ${renderGaugeBar("Cryptographie & Sécurité Réseau (CRYPTO)", f.CRYPTO?.score)}

            ${renderGaugeBar("Administration Systèmes Linux (LINUX_ADMIN)", f.LINUX_ADMIN?.score)}

          </div>

        </div>



        <!-- Section 2 : Examens Officiels (Théorie & Machine) -->

        <div style="margin-bottom: 28px;">

          <h3 style="font-size: 1.05rem; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">

            <span>2. Épreuves Officielles de Fin de Module</span>

            <span style="font-size: 0.9rem; color: #4f46e5; font-weight: 700;">Moyenne Épreuves : ${b.exams_average !== null ? b.exams_average.toFixed(2) + ' / 20' : '—'}</span>

          </h3>

          <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">

            ${renderGaugeBar("Épreuve Théorique : " + (ex.theoretical?.title || "Examen Théorique"), ex.theoretical?.score)}

            ${renderGaugeBar("Épreuve Pratique : " + (ex.practical?.title || "Épreuve sur Machine"), ex.practical?.score)}

          </div>

        </div>



        <!-- Synthèse Générale & Décision Jury -->

        <div style="background: linear-gradient(135deg, ${b.is_pass ? '#f0fdf4' : '#fef2f2'} 0%, #ffffff 100%); border: 2px solid ${b.verdict_color}; border-radius: 12px; padding: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; margin-bottom: 30px;">

          <div>

            <div style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; color: #64748b;">Moyenne Générale Consolidée</div>

            <div style="font-size: 2.2rem; font-weight: 900; color: ${b.verdict_color}; margin: 4px 0;">

              ${b.general_average !== null ? b.general_average.toFixed(2) + ' / 20' : 'Non Évalué'}

            </div>

            <div style="font-size: 0.85rem; color: #475569;">Calculée sur l'ensemble des ${b.evaluations_count} épreuves passées</div>

          </div>

          <div style="text-align: right;">

            <div style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; color: #64748b; margin-bottom: 6px;">Décision du Jury Académique</div>

            <div style="display: inline-block; padding: 8px 24px; border-radius: 30px; font-size: 1.15rem; font-weight: 900; background: ${b.is_pass ? '#10b981' : '#ef4444'}; color: #ffffff; box-shadow: 0 4px 12px ${b.is_pass ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'};">

              ${b.verdict_label}

            </div>

            <div style="font-size: 0.8rem; color: #64748b; margin-top: 6px;">Seuil d'admission officiel : 10.00 / 20</div>

          </div>

        </div>



        <!-- Signature & Cachet Officiel -->

        <div style="display: flex; justify-content: space-between; margin-top: 40px; padding-top: 20px; border-top: 1px dashed #cbd5e1; font-size: 0.85rem; color: #475569;">

          <div>

            <strong>Le Responsable Pédagogique</strong><br/>

            Commission d'Évaluation LAN<br/>

            <em>Cachet & Visa Électronique</em>

          </div>

          <div style="text-align: right;">

            <strong>Le Président du Jury</strong><br/>

            Établissement Universitaire<br/>

            <em>Signature Certifiée</em>

          </div>

        </div>

      `;

    } catch (err) {

      area.innerHTML = `<div style="text-align:center; padding:40px; color:#ef4444;">Erreur lors du chargement du bulletin : ${err.message}</div>`;

    }

  }



  async downloadBulletinsCsv() {

    try {

      const filterSpec = document.getElementById('admin-bulletins-filter-speciality')?.value || '';

      const qs = filterSpec ? `?speciality=${encodeURIComponent(filterSpec)}` : '';

      const url = `/api/admin/bulletins/export-csv${qs}`;

      const res = await fetch(url, {

        headers: api.getHeaders()

      });

      if (!res.ok) throw new Error("Erreur de téléchargement CSV.");

      const blob = await res.blob();

      const downloadUrl = window.URL.createObjectURL(blob);

      const a = document.createElement('a');

      a.href = downloadUrl;

      a.download = `bulletins_academiques_consolides_${new Date().toISOString().slice(0, 10)}.csv`;

      document.body.appendChild(a);

      a.click();

      a.remove();

      window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {

      this.showToast(`Erreur d'exportation : ${err.message}`, "danger");

    }

  }



  // --- Analyse Psychométrique & Discrimination des Questions (Item Analysis) ---

  async openItemAnalysisModal(examId, examTitle = '', moduleCode = '') {

    this._currentAnalysisExamId = examId;

    this._currentAnalysisSessionId = null;

    const modal = document.getElementById('modal-item-analysis');

    if (modal) modal.classList.add('active');



    const subtitleEl = document.getElementById('item-analysis-subtitle');

    if (subtitleEl) subtitleEl.textContent = `Épreuve : ${examTitle || examId} | Module : ${moduleCode || '—'}`;



    const tbody = document.getElementById('item-analysis-table-body');

    if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--text-secondary);">Calcul psychométrique et discrimination en cours...</td></tr>';



    try {

      const analysis = await api.getItemAnalysis(examId);

      this._renderItemAnalysisContent(analysis);

    } catch (err) {

      if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  async openSessionItemAnalysisModal(sessionId) {

    this._currentAnalysisExamId = null;

    this._currentAnalysisSessionId = sessionId;

    const modal = document.getElementById('modal-item-analysis');

    if (modal) modal.classList.add('active');



    const subtitleEl = document.getElementById('item-analysis-subtitle');

    if (subtitleEl) subtitleEl.textContent = `Session de Surveillance Salle : ${sessionId}`;



    const tbody = document.getElementById('item-analysis-table-body');

    if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--text-secondary);">Calcul psychométrique et discrimination de la session...</td></tr>';



    try {

      const analysis = await api.getSessionItemAnalysis(sessionId);

      this._currentAnalysisExamId = analysis.exam_id;

      this._renderItemAnalysisContent(analysis);

    } catch (err) {

      if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  _renderItemAnalysisContent(analysis) {

    const candidatesEl = document.getElementById('analysis-kpi-candidates');

    const meanEl = document.getElementById('analysis-kpi-mean');

    const medianEl = document.getElementById('analysis-kpi-median');

    const stddevEl = document.getElementById('analysis-kpi-stddev');

    const passRateEl = document.getElementById('analysis-kpi-pass-rate');



    const g = analysis.global_stats || {};

    if (candidatesEl) candidatesEl.textContent = analysis.total_candidates || 0;

    if (meanEl) meanEl.textContent = `${g.mean !== undefined ? g.mean.toFixed(2) : '--'} / 20`;

    if (medianEl) medianEl.textContent = `${g.median !== undefined ? g.median.toFixed(2) : '--'} / 20`;

    if (stddevEl) stddevEl.textContent = `${g.std_dev !== undefined ? g.std_dev.toFixed(2) : '--'}`;

    if (passRateEl) passRateEl.textContent = `${g.pass_rate_pct !== undefined ? g.pass_rate_pct.toFixed(1) : '--'} %`;



    const anomaliesBox = document.getElementById('item-analysis-anomalies-box');

    const anomaliesList = document.getElementById('item-analysis-anomalies-list');

    const anomaliesTitle = document.getElementById('item-analysis-anomalies-title');



    if (analysis.anomalies_count > 0) {

      if (anomaliesBox) anomaliesBox.style.display = 'block';

      if (anomaliesTitle) anomaliesTitle.textContent = `${analysis.anomalies_count} anomalie(s) psychométrique(s) détectée(s) :`;

      if (anomaliesList) {

        anomaliesList.innerHTML = (analysis.anomalies || []).map(a => `

          <div style="margin-top:4px;">

            <strong>Question ${a.ordering}</strong> (D = ${a.discrimination_index > 0 ? '+' : ''}${a.discrimination_index.toFixed(3)}) : ${this._escapeHtml(a.reason)}

          </div>

        `).join('');

      }

    } else {

      if (anomaliesBox) anomaliesBox.style.display = 'none';

    }



    const tbody = document.getElementById('item-analysis-table-body');

    if (!tbody) return;



    const questions = analysis.questions_analysis || [];

    if (questions.length === 0) {

      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:24px; color:var(--text-muted);">Aucune question analysée.</td></tr>';

      return;

    }



    tbody.innerHTML = '';

    questions.forEach(q => {

      const tr = document.createElement('tr');

      tr.style.borderBottom = '1px solid var(--card-border)';

      if (q.is_anomaly) {

        tr.style.background = 'rgba(239, 68, 68, 0.05)';

      }



      let barColor = '#10b981';

      if (q.facility_pct < 40.0) barColor = '#ef4444';

      else if (q.facility_pct < 70.0) barColor = '#f59e0b';



      let badgeBg = 'rgba(16,185,129,0.15)';

      let badgeColor = '#10b981';

      let badgeBorder = '#10b981';

      if (q.discrimination_index < 0) {

        badgeBg = 'rgba(239,68,68,0.2)';

        badgeColor = '#ef4444';

        badgeBorder = '#ef4444';

      } else if (q.discrimination_index < 0.20) {

        badgeBg = 'rgba(245,158,11,0.15)';

        badgeColor = '#f59e0b';

        badgeBorder = '#f59e0b';

      } else if (q.discrimination_index < 0.30) {

        badgeBg = 'rgba(59,130,246,0.15)';

        badgeColor = '#60a5fa';

        badgeBorder = '#3b82f6';

      }



      const dFormatted = (q.discrimination_index >= 0 ? '+' : '') + q.discrimination_index.toFixed(3);



      tr.innerHTML = `

        <td style="padding:8px 10px; font-weight:700; color:var(--text-primary);">${q.ordering}</td>

        <td style="padding:8px 10px; color:var(--text-primary); font-size:0.82rem; max-width:240px; line-height:1.4;">${this._escapeHtml(q.prompt_snippet)}</td>

        <td style="padding:8px 10px;"><span class="badge" style="background:rgba(255,255,255,0.06); font-size:0.75rem; padding:2px 6px;">${q.type}</span></td>

        <td style="padding:8px 10px; font-size:0.82rem;">${q.points} pt(s)</td>

        <td style="padding:8px 10px;">

          <div style="display:flex; align-items:center; gap:8px;">

            <div style="flex:1; background:rgba(255,255,255,0.1); height:7px; border-radius:4px; overflow:hidden;">

              <div style="background:${barColor}; width:${Math.min(100, Math.max(0, q.facility_pct))}%; height:100%;"></div>

            </div>

            <span style="font-size:0.8rem; font-weight:700; font-family:monospace; min-width:38px;">${q.facility_pct}%</span>

          </div>

        </td>

        <td style="padding:8px 10px; text-align:center; font-family:monospace; font-size:0.82rem; color:#60a5fa;">${(q.p_upper * 100).toFixed(0)}%</td>

        <td style="padding:8px 10px; text-align:center; font-family:monospace; font-size:0.82rem; color:#f87171;">${(q.p_lower * 100).toFixed(0)}%</td>

        <td style="padding:8px 10px; text-align:center;">

          <span class="badge" style="background:${badgeBg}; color:${badgeColor}; border:1px solid ${badgeBorder}; font-weight:700; font-family:monospace; font-size:0.78rem; padding:2px 8px; border-radius:10px;">

            ${dFormatted}

          </span>

        </td>

        <td style="padding:8px 10px; font-size:0.80rem; color:${q.is_anomaly ? '#f87171' : 'var(--text-secondary)'};">

          ${q.discrimination_quality}

          ${q.anomaly_reason ? `<div style="font-size:0.75rem; color:#ef4444; margin-top:2px;">⚠️ ${this._escapeHtml(q.anomaly_reason)}</div>` : ''}

        </td>

      `;

      tbody.appendChild(tr);

    });

  }



  // --- Gestionnaire de Questions & Banques d'Épreuves (Web Editor) ---

  async openManageQuestionsModal(examId, examTitle = '') {

    this._currentManageExamId = examId;

    this._currentManageExamTitle = examTitle;

    const modal = document.getElementById('modal-manage-questions');

    if (modal) modal.classList.add('active');



    const subtitleEl = document.getElementById('manage-questions-subtitle');

    if (subtitleEl) subtitleEl.textContent = `Examen : ${examTitle || examId}`;



    const tbody = document.getElementById('manage-questions-table-body');

    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-secondary);">Chargement des questions...</td></tr>';



    try {

      const examDetail = await api.getExamDetail(examId);

      this._currentExamQuestions = examDetail.questions || [];

      this._currentExamType = examDetail.exam_type || 'theoretical';



      if (!this._currentExamQuestions.length) {

        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:30px; color:var(--text-muted);">Aucune question dans cet examen. Cliquez sur "➕ Ajouter une Question" ou "📥 Importer JSON".</td></tr>';

        return;

      }



      tbody.innerHTML = '';

      this._currentExamQuestions.forEach(q => {

        const tr = document.createElement('tr');

        tr.style.borderBottom = '1px solid var(--card-border)';

        const promptSnippet = q.prompt_markdown ? (q.prompt_markdown.slice(0, 80) + (q.prompt_markdown.length > 80 ? '...' : '')) : '';



        tr.innerHTML = `

          <td style="padding:8px 10px; font-weight:700; color:var(--text-primary);">${q.ordering}</td>

          <td style="padding:8px 10px; color:var(--text-primary); font-size:0.82rem; line-height:1.4;">${this._escapeHtml(promptSnippet)}</td>

          <td style="padding:8px 10px;"><span class="badge" style="background:rgba(59,130,246,0.12); color:#93c5fd; font-size:0.75rem; padding:2px 8px; border-radius:10px;">${q.type}</span></td>

          <td style="padding:8px 10px; font-size:0.82rem; font-weight:600;">${q.points} pt(s)</td>

          <td style="padding:8px 10px; font-size:0.82rem; color:var(--text-muted);">${q.negative_penalty || 0} pt(s)</td>

          <td style="padding:8px 10px; text-align:center;">

            <div style="display:inline-flex; gap:6px;">

              <button class="btn btn-secondary btn-edit-question-item" data-qid="${q.id}" style="padding:4px 8px; font-size:0.75rem;">✏️ Modifier</button>

              <button class="btn btn-danger btn-delete-question-item" data-qid="${q.id}" style="padding:4px 8px; font-size:0.75rem;">🗑️</button>

            </div>

          </td>

        `;

        tbody.appendChild(tr);

      });



      tbody.querySelectorAll('.btn-edit-question-item').forEach(btn => {

        btn.onclick = () => {

          const qId = btn.getAttribute('data-qid');

          const qData = this._currentExamQuestions.find(item => item.id === qId);

          this.openEditQuestionModal(examId, qData);

        };

      });



      tbody.querySelectorAll('.btn-delete-question-item').forEach(btn => {

        btn.onclick = async () => {

          const qId = btn.getAttribute('data-qid');

          const ok = await this.showConfirmModal({

            title: "Supprimer la question",

            message: "Confirmez-vous la suppression de cette question ?",

            confirmText: "Supprimer",

            cancelText: "Annuler",

            icon: "🗑️",

            danger: true

          });

          if (ok) {

            try {

              await api.deleteQuestion(examId, qId);

              this.showToast("Question supprimée avec succès.", "success");

              await this.openManageQuestionsModal(examId, this._currentManageExamTitle);

              if (this.currentUser && this.currentUser.role === 'admin') {

                await this.loadAdminExams();

              } else {

                await this.renderTeacherView();

              }

            } catch (err) {

              this.showToast(`Erreur de suppression de la question : ${err.message}`, "danger");

            }

          }

        };

      });



    } catch (err) {

      if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;

    }

  }



  openEditQuestionModal(examId, questionData = null) {

    const modal = document.getElementById('modal-edit-question');

    if (!modal) return;

    modal.classList.add('active');



    const titleEl = document.getElementById('modal-edit-question-title');

    const inputExamId = document.getElementById('edit-question-exam-id');

    const inputQId = document.getElementById('edit-question-id');

    const selectType = document.getElementById('edit-question-type');

    const inputOrdering = document.getElementById('edit-question-ordering');

    const textareaPrompt = document.getElementById('edit-question-prompt');

    const inputPoints = document.getElementById('edit-question-points');

    const inputPenalty = document.getElementById('edit-question-penalty');



    if (inputExamId) inputExamId.value = examId;



    // Adaptation des types de question selon le type d'épreuve (Théorique vs Pratique)

    if (selectType) {

      if (this._currentExamType === 'practical') {

        selectType.innerHTML = `

          <option value="coding" selected>💻 Défi de Programmation Python & Machine</option>

        `;

      } else {

        selectType.innerHTML = `

          <option value="single_choice" selected>🔘 QCM Choix Unique</option>

          <option value="multi_choice">☑️ QCM Choix Multiple</option>

          <option value="boolean">⚖️ Vrai / Faux</option>

          <option value="fill_blank">✏️ Texte / Mot-Clé à trou</option>

          <option value="matching">🔄 Correspondance / Appariement</option>

        `;

      }

    }



    if (questionData) {

      if (titleEl) titleEl.textContent = `✏️ Modifier la Question N°${questionData.ordering}`;

      if (inputQId) inputQId.value = questionData.id;

      if (selectType) selectType.value = questionData.type;

      if (inputOrdering) inputOrdering.value = questionData.ordering;

      if (textareaPrompt) textareaPrompt.value = questionData.prompt_markdown || '';

      if (inputPoints) inputPoints.value = questionData.points || 2.0;

      if (inputPenalty) inputPenalty.value = questionData.negative_penalty || 0.5;



      let parsedOptions = null;

      let parsedCorrect = null;

      try {

        parsedOptions = typeof questionData.options_json === 'string' ? JSON.parse(questionData.options_json) : questionData.options_json;

      } catch (_) {}

      try {

        parsedCorrect = typeof questionData.correct_answers_json === 'string' ? JSON.parse(questionData.correct_answers_json) : questionData.correct_answers_json;

      } catch (_) {}



      this._renderDynamicQuestionOptionsForm(questionData.type, parsedOptions, parsedCorrect);

    } else {

      const defaultType = (this._currentExamType === 'practical') ? 'coding' : 'single_choice';

      if (titleEl) titleEl.textContent = "➕ Ajouter une Question";

      if (inputQId) inputQId.value = "";

      if (selectType) selectType.value = defaultType;

      const nextOrdering = (this._currentExamQuestions ? this._currentExamQuestions.length + 1 : 1);

      if (inputOrdering) inputOrdering.value = nextOrdering;

      if (textareaPrompt) textareaPrompt.value = "";

      if (inputPoints) inputPoints.value = 2.0;

      if (inputPenalty) inputPenalty.value = 0.5;



      this._renderDynamicQuestionOptionsForm(defaultType, null, null);

    }

  }



  _renderDynamicQuestionOptionsForm(type, existingOptions = null, existingCorrect = null) {

    const container = document.getElementById('edit-question-dynamic-options-container');

    if (!container) return;



    if (type === 'boolean') {

      const isTrue = existingCorrect === true || existingCorrect === 'true';

      container.innerHTML = `

        <label style="font-weight:600; display:block; margin-bottom:6px; font-size:0.85rem;">Réponse Vraie :</label>

        <div style="display:flex; gap:20px; font-size:0.9rem;">

          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">

            <input type="radio" name="boolean_correct" value="true" ${isTrue ? 'checked' : ''} required /> ✅ Vrai

          </label>

          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">

            <input type="radio" name="boolean_correct" value="false" ${!isTrue ? 'checked' : ''} /> ❌ Faux

          </label>

        </div>

      `;

    } else if (type === 'single_choice' || type === 'multi_choice') {

      const isMulti = type === 'multi_choice';

      const defaultOpts = [

        { id: 'A', text: '' },

        { id: 'B', text: '' },

        { id: 'C', text: '' },

        { id: 'D', text: '' }

      ];

      let opts = defaultOpts;

      if (Array.isArray(existingOptions) && existingOptions.length) {

        opts = existingOptions.map((o, idx) => ({

          id: o.id || String.fromCharCode(65 + idx),

          text: o.text || ''

        }));

      }



      let correctList = [];

      if (Array.isArray(existingCorrect)) {

        correctList = existingCorrect.map(x => String(x));

      } else if (existingCorrect !== null && existingCorrect !== undefined) {

        correctList = [String(existingCorrect)];

      }



      let html = `

        <label style="font-weight:600; display:block; margin-bottom:8px; font-size:0.85rem;">

          Choix de réponses (${isMulti ? 'Cochez toutes les bonnes réponses' : 'Cochez la seule bonne réponse'}) :

        </label>

        <div style="display:flex; flex-direction:column; gap:8px;">

      `;



      opts.forEach((opt, idx) => {

        const letter = opt.id || String.fromCharCode(65 + idx);

        const isChecked = correctList.includes(letter);

        const inputType = isMulti ? 'checkbox' : 'radio';

        html += `

          <div style="display:flex; align-items:center; gap:8px;">

            <input type="${inputType}" name="choice_correct" value="${letter}" ${isChecked ? 'checked' : ''} style="width:16px; height:16px; cursor:pointer;" />

            <span style="font-weight:700; font-family:monospace; min-width:20px;">${letter})</span>

            <input type="text" class="form-control edit-choice-text" data-letter="${letter}" value="${this._escapeHtml(opt.text)}" placeholder="Texte de l'option ${letter}..." required style="flex:1; font-size:0.85rem; padding:6px 10px;" />

          </div>

        `;

      });



      html += `</div>`;

      container.innerHTML = html;

    } else if (type === 'fill_blank') {

      let val = '';

      if (Array.isArray(existingCorrect)) val = existingCorrect.join(', ');

      else if (existingCorrect) val = String(existingCorrect);



      container.innerHTML = `

        <label style="font-weight:600; display:block; margin-bottom:4px; font-size:0.85rem;">Texte ou mot-clé attendu (insensible à la casse) * :</label>

        <input type="text" id="edit-fill-blank-answer" class="form-control" value="${this._escapeHtml(val)}" placeholder="Ex: polymorphisme, return, chmod" required style="width:100%; font-size:0.85rem;" />

        <span style="font-size:0.75rem; color:var(--text-muted); margin-top:4px; display:block;">Pour plusieurs synonymes acceptés, séparez-les par des virgules.</span>

      `;

    } else if (type === 'matching') {

      let pairs = [

        { left: '', right: '' },

        { left: '', right: '' },

        { left: '', right: '' },

        { left: '', right: '' }

      ];



      if (existingCorrect && typeof existingCorrect === 'object' && !Array.isArray(existingCorrect)) {

        pairs = Object.entries(existingCorrect).map(([k, v]) => ({ left: k, right: v }));

      }



      let html = `

        <label style="font-weight:600; display:block; margin-bottom:8px; font-size:0.85rem;">

          Paires de Correspondance (Élément Gauche ➔ Cible Droite) :

        </label>

        <div style="display:flex; flex-direction:column; gap:8px;">

      `;



      pairs.forEach((p, idx) => {

        html += `

          <div style="display:flex; gap:8px; align-items:center;">

            <span style="font-weight:700; font-size:0.8rem; color:var(--text-muted); min-width:18px;">${idx + 1}.</span>

            <input type="text" class="form-control edit-matching-left" value="${this._escapeHtml(p.left)}" placeholder="Élément gauche..." required style="flex:1; font-size:0.83rem; padding:6px 8px;" />

            <span>➔</span>

            <input type="text" class="form-control edit-matching-right" value="${this._escapeHtml(p.right)}" placeholder="Cible correspondante..." required style="flex:1; font-size:0.83rem; padding:6px 8px;" />

          </div>

        `;

      });



      html += `</div>`;

      container.innerHTML = html;

    } else if (type === 'coding') {

      let starterCode = '';

      let pubTests = [

        { input: '', expected_output: '' },

        { input: '', expected_output: '' }

      ];

      let hidTests = [

        { input: '', expected_output: '' }

      ];



      if (existingOptions && typeof existingOptions === 'object') {

        if (existingOptions.starter_code) starterCode = existingOptions.starter_code;

        if (Array.isArray(existingOptions.public_tests) && existingOptions.public_tests.length > 0) {

          pubTests = existingOptions.public_tests;

        }

      }



      if (Array.isArray(existingCorrect) && existingCorrect.length > 0) {

        const h = existingCorrect.filter(t => t.is_public === false);

        if (h.length > 0) hidTests = h;

        const p = existingCorrect.filter(t => t.is_public !== false);

        if (p.length > 0) pubTests = p;

      }



      while (pubTests.length < 2) {

        pubTests.push({ input: '', expected_output: '' });

      }

      if (hidTests.length === 0) {

        hidTests.push({ input: '', expected_output: '' });

      }



      let html = `

        <div style="display:flex; flex-direction:column; gap:12px;">

          <div>

            <label style="font-weight:600; display:block; margin-bottom:4px; font-size:0.85rem;">Code de Départ (Starter Code) :</label>

            <textarea id="edit-coding-starter" class="form-control" rows="4" placeholder="# Squelette fourni à l'étudiant...\ndef solution():\n    pass" style="width:100%; font-family:var(--font-mono); font-size:0.83rem;">${this._escapeHtml(starterCode)}</textarea>

          </div>

          <div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">

              <label style="font-weight:600; font-size:0.85rem; color:#60a5fa;">

                Cas de Test Publics (Visibles par l'étudiant) - Au moins 2 requis :

              </label>

            </div>

            <div id="coding-public-tests-container" style="display:flex; flex-direction:column; gap:8px;">

      `;



      pubTests.forEach((pt, idx) => {

        html += `

          <div class="coding-pub-test-row" style="display:grid; grid-template-columns:1fr 1fr; gap:8px; background:rgba(0,0,0,0.2); padding:8px; border-radius:4px; border:1px solid rgba(255,255,255,0.06);">

            <div>

              <span style="font-size:0.75rem; color:var(--text-muted);">Entrée (stdin) #${idx + 1} :</span>

              <input type="text" class="form-control edit-pub-test-in" value="${this._escapeHtml(pt.input || '')}" placeholder="ex: 10 20" style="font-family:var(--font-mono); font-size:0.82rem; padding:4px 8px; width:100%;" />

            </div>

            <div>

              <span style="font-size:0.75rem; color:var(--text-muted);">Sortie Attendue (stdout) #${idx + 1} :</span>

              <input type="text" class="form-control edit-pub-test-out" value="${this._escapeHtml(pt.expected_output || pt.output || '')}" placeholder="ex: 30" style="font-family:var(--font-mono); font-size:0.82rem; padding:4px 8px; width:100%;" />

            </div>

          </div>

        `;

      });



      html += `

            </div>

          </div>

          <div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">

              <label style="font-weight:600; font-size:0.85rem; color:#f87171;">

                Cas de Test Cachés (Strictement confidentiels - Évaluation finale anti-triche) :

              </label>

            </div>

            <div id="coding-hidden-tests-container" style="display:flex; flex-direction:column; gap:8px;">

      `;



      hidTests.forEach((ht, idx) => {

        html += `

          <div class="coding-hid-test-row" style="display:grid; grid-template-columns:1fr 1fr; gap:8px; background:rgba(0,0,0,0.2); padding:8px; border-radius:4px; border:1px solid rgba(255,255,255,0.06);">

            <div>

              <span style="font-size:0.75rem; color:var(--text-muted);">Entrée Cachée #${idx + 1} :</span>

              <input type="text" class="form-control edit-hid-test-in" value="${this._escapeHtml(ht.input || '')}" placeholder="ex: 999 1" style="font-family:var(--font-mono); font-size:0.82rem; padding:4px 8px; width:100%;" />

            </div>

            <div>

              <span style="font-size:0.75rem; color:var(--text-muted);">Sortie Attendue #${idx + 1} :</span>

              <input type="text" class="form-control edit-hid-test-out" value="${this._escapeHtml(ht.expected_output || ht.output || '')}" placeholder="ex: 1000" style="font-family:var(--font-mono); font-size:0.82rem; padding:4px 8px; width:100%;" />

            </div>

          </div>

        `;

      });



      html += `

            </div>

          </div>

        </div>

      `;

      container.innerHTML = html;

    }

  }



  _extractOptionsAndAnswersFromForm(type) {

    if (type === 'boolean') {

      const checkedVal = document.querySelector('input[name="boolean_correct"]:checked')?.value;

      const boolVal = checkedVal === 'true';

      return {

        options_json: JSON.stringify([

          { id: "true", text: "Vrai" },

          { id: "false", text: "Faux" }

        ]),

        correct_answers_json: JSON.stringify(boolVal)

      };

    } else if (type === 'single_choice' || type === 'multi_choice') {

      const isMulti = type === 'multi_choice';

      const options = [];

      document.querySelectorAll('.edit-choice-text').forEach(input => {

        const letter = input.getAttribute('data-letter');

        options.push({

          id: letter,

          text: input.value.trim()

        });

      });



      const checkedBoxes = Array.from(document.querySelectorAll('input[name="choice_correct"]:checked')).map(cb => cb.value);

      if (checkedBoxes.length === 0) {

        throw new Error("Veuillez cocher au moins une bonne réponse.");

      }



      return {

        options_json: JSON.stringify(options),

        correct_answers_json: JSON.stringify(isMulti ? checkedBoxes : checkedBoxes[0])

      };

    } else if (type === 'fill_blank') {

      const raw = document.getElementById('edit-fill-blank-answer')?.value.trim();

      const synonyms = raw.split(',').map(s => s.trim()).filter(Boolean);

      return {

        options_json: JSON.stringify([]),

        correct_answers_json: JSON.stringify(synonyms.length === 1 ? synonyms[0] : synonyms)

      };

    } else if (type === 'matching') {

      const leftInputs = document.querySelectorAll('.edit-matching-left');

      const rightInputs = document.querySelectorAll('.edit-matching-right');

      const leftList = [];

      const rightList = [];

      const correctMap = {};



      for (let i = 0; i < leftInputs.length; i++) {

        const lVal = leftInputs[i].value.trim();

        const rVal = rightInputs[i].value.trim();

        if (lVal && rVal) {

          leftList.push(lVal);

          rightList.push(rVal);

          correctMap[lVal] = rVal;

        }

      }



      if (Object.keys(correctMap).length < 2) {

        throw new Error("Veuillez renseigner au moins 2 paires de correspondance.");

      }



      return {

        options_json: JSON.stringify({ left: leftList, right: rightList }),

        correct_answers_json: JSON.stringify(correctMap)

      };

    } else if (type === 'coding') {

      const starterCode = document.getElementById('edit-coding-starter')?.value || '';

      const pubInInputs = document.querySelectorAll('.edit-pub-test-in');

      const pubOutInputs = document.querySelectorAll('.edit-pub-test-out');

      const hidInInputs = document.querySelectorAll('.edit-hid-test-in');

      const hidOutInputs = document.querySelectorAll('.edit-hid-test-out');



      const publicTests = [];

      const allTests = [];



      for (let i = 0; i < pubInInputs.length; i++) {

        const inp = pubInInputs[i].value;

        const out = pubOutInputs[i].value;

        if (inp.trim() || out.trim()) {

          const tc = { id: `pub_${i + 1}`, input: inp, expected_output: out, is_public: true };

          publicTests.push(tc);

          allTests.push(tc);

        }

      }



      for (let j = 0; j < hidInInputs.length; j++) {

        const inp = hidInInputs[j].value;

        const out = hidOutInputs[j].value;

        if (inp.trim() || out.trim()) {

          const tc = { id: `hid_${j + 1}`, input: inp, expected_output: out, is_public: false };

          allTests.push(tc);

        }

      }



      if (publicTests.length < 2) {

        throw new Error("Veuillez définir au moins 2 cas de test publics.");

      }

      if (allTests.filter(t => !t.is_public).length < 1) {

        throw new Error("Veuillez définir au moins 1 cas de test caché pour l'évaluation confidentielle.");

      }



      return {

        options_json: JSON.stringify({ starter_code: starterCode, public_tests: publicTests }),

        correct_answers_json: JSON.stringify(allTests)

      };

    }



    return { options_json: "[]", correct_answers_json: "[]" };

  }



  showToast(message, type = 'info', duration = 4000) {

    let container = document.getElementById('app-toast-container');

    if (!container) {

      container = document.createElement('div');

      container.id = 'app-toast-container';

      container.className = 'app-toast-container';

      document.body.appendChild(container);

    }



    let normalizedType = (type || 'info').toLowerCase();

    if (normalizedType === 'error') normalizedType = 'danger';

    if (!['success', 'danger', 'warning', 'info'].includes(normalizedType)) {

      normalizedType = 'info';

    }



    let icon = 'ℹ️';

    if (normalizedType === 'success') icon = '✅';

    else if (normalizedType === 'danger') icon = '❌';

    else if (normalizedType === 'warning') icon = '⚠️';



    const toast = document.createElement('div');

    toast.className = `app-toast toast-${normalizedType}`;

    toast.setAttribute('role', 'alert');

    toast.setAttribute('aria-live', 'assertive');



    toast.innerHTML = `

      <span class="app-toast-icon toast-icon">${icon}</span>

      <div class="app-toast-content toast-message">${this._escapeHtml(message)}</div>

      <button class="app-toast-close toast-close" aria-label="Fermer">&times;</button>

    `;



    const closeBtn = toast.querySelector('.app-toast-close');

    const dismiss = () => {

      if (toast._isDismissed) return;

      toast._isDismissed = true;

      toast.style.opacity = '0';

      toast.style.transform = 'translateX(40px)';

      setTimeout(() => {

        if (toast.parentElement) toast.parentElement.removeChild(toast);

      }, 260);

    };



    if (closeBtn) {

      closeBtn.onclick = (e) => {

        e.stopPropagation();

        dismiss();

      };

    }



    container.appendChild(toast);



    if (duration > 0) {

      setTimeout(dismiss, duration);

    }

    return toast;

  }



  _escapeHtml(str) {

    if (!str) return '';

    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  }



  // =========================================================================

  // HUB UNIFIÉ DES CENTRES D'ENTRAÎNEMENT (PYTHON & LINUX)

  // =========================================================================



  renderTrainingHubView() {

    this.switchView('view-training-hub');

    this.activeOriginView = 'view-training-hub';



    const btnBack = document.getElementById('btn-training-hub-back-dash');

    if (btnBack) {

      btnBack.onclick = () => this.renderDashboard(this.currentUser);

    }



    // Boutons d'accès Python

    const btnPy1 = document.getElementById('btn-hub-open-python');

    const btnPyPrac = document.getElementById('btn-hub-card-python-prac');

    const btnPyTheo = document.getElementById('btn-hub-card-python-theo');



    if (btnPy1) btnPy1.onclick = () => this.renderTrainingCenterView();

    if (btnPyPrac) btnPyPrac.onclick = () => this.renderTrainingCenterView();

    if (btnPyTheo) btnPyTheo.onclick = () => this.renderTrainingCenterView();



    // Boutons d'accès Linux

    const btnLx1 = document.getElementById('btn-hub-open-linux');

    const btnLxPrac = document.getElementById('btn-hub-card-linux-prac');

    const btnLxTheo = document.getElementById('btn-hub-card-linux-theo');



    if (btnLx1) btnLx1.onclick = () => this.renderLinuxTrainingCenter();

    if (btnLxPrac) btnLxPrac.onclick = () => this.renderLinuxTrainingCenter();

    if (btnLxTheo) {

      btnLxTheo.onclick = async () => {

        await this.renderLinuxTrainingCenter();

        if (this.linuxRunner) {

          this.linuxRunner.currentMode = 'theoretical';

          await this.linuxRunner.renderHub();

        }

      };

    }

  }



  showStudentExamsTab() {

    this.switchView('view-dashboard');

    setTimeout(() => {

      document.getElementById('official-exams-grid')?.scrollIntoView({ behavior: 'smooth' });

    }, 100);

  }



  // =========================================================================

  // PV & BULLETINS DE CLASSE PAR SPÉCIALITÉ ET MODULE

  // =========================================================================



  async renderClassSheetView() {

    this.switchView('view-class-bulletins');

    const backBtn = document.getElementById('btn-class-sheet-back');

    if (backBtn) {

      backBtn.onclick = () => {

        if (this.currentUser && this.currentUser.role === 'admin') {

          this.renderAdminView();

        } else {

          this.renderTeacherView();

        }

      };

    }



    // Charger les listes de spécialités et de modules disponibles

    try {

      const [groups, modules] = await Promise.all([

        api.listGroups().catch(() => []),

        api.listAdminModules().catch(() => [])

      ]);



      const selectSpec = document.getElementById('class-sheet-filter-speciality');

      if (selectSpec && Array.isArray(groups) && groups.length > 0) {

        selectSpec.innerHTML = groups.map(g => `

          <option value="${g.id}">${g.name || g.id}</option>

        `).join('');

      }



      const selectMod = document.getElementById('class-sheet-filter-module');

      if (selectMod && Array.isArray(modules) && modules.length > 0) {

        selectMod.innerHTML = modules.map(m => `

          <option value="${m.code}">${m.code} (${m.title})</option>

        `).join('');

      }

    } catch (_) {}



    // Attacher les écouteurs de rafraîchissement et téléchargement

    const btnRefresh = document.getElementById('btn-class-sheet-refresh');

    if (btnRefresh) {

      btnRefresh.onclick = () => this.loadClassSheet();

    }



    const selectSpec = document.getElementById('class-sheet-filter-speciality');

    if (selectSpec) selectSpec.onchange = () => this.loadClassSheet();



    const selectMod = document.getElementById('class-sheet-filter-module');

    if (selectMod) selectMod.onchange = () => this.loadClassSheet();



    const btnPdf = document.getElementById('btn-class-sheet-export-pdf');

    if (btnPdf) {

      btnPdf.onclick = async () => {

        const spec = document.getElementById('class-sheet-filter-speciality')?.value || 'DEV-IA';

        const mod = document.getElementById('class-sheet-filter-module')?.value || 'PYTHON_INIT';

        try {

          await api.downloadClassSheetPdf(spec, mod);

        } catch (e) {

          this.showToast(`Erreur export PDF : ${e.message}`, 'danger');

        }

      };

    }



    const btnCsv = document.getElementById('btn-class-sheet-export-csv');

    if (btnCsv) {

      btnCsv.onclick = async () => {

        const spec = document.getElementById('class-sheet-filter-speciality')?.value || 'DEV-IA';

        const mod = document.getElementById('class-sheet-filter-module')?.value || 'PYTHON_INIT';

        try {

          await api.downloadClassSheetCsv(spec, mod);

        } catch (e) {

          this.showToast(`Erreur export CSV : ${e.message}`, 'danger');

        }

      };

    }



    await this.loadClassSheet();

  }



  async loadClassSheet() {

    const spec = document.getElementById('class-sheet-filter-speciality')?.value || 'DEV-IA';

    const mod = document.getElementById('class-sheet-filter-module')?.value || 'PYTHON_INIT';

    const tbody = document.getElementById('class-sheet-table-body');

    if (!tbody) return;



    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">Génération du procès-verbal de classe...</td></tr>';



    try {

      const data = await api.getClassSheet(spec, mod);

      const students = data.students || [];

      const stats = data.class_stats || {};



      // Mettre à jour les KPI Cards

      const elEnrolled = document.getElementById('class-sheet-kpi-enrolled');

      const elEvaluated = document.getElementById('class-sheet-kpi-evaluated');

      const elAvg = document.getElementById('class-sheet-kpi-average');

      const elSuccess = document.getElementById('class-sheet-kpi-success-rate');



      if (elEnrolled) elEnrolled.textContent = stats.enrolled_count || students.length;

      if (elEvaluated) elEvaluated.textContent = stats.evaluated_count || 0;

      if (elAvg) elAvg.textContent = stats.class_average !== null ? `${stats.class_average.toFixed(2)} / 20` : '—';

      if (elSuccess) elSuccess.textContent = `${stats.success_rate_percent || 0}%`;



      if (students.length === 0) {

        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun étudiant inscrit dans cette filière.</td></tr>';

        return;

      }



      tbody.innerHTML = students.map((s, idx) => {

        const theoStr = s.theoretical_score !== null ? `<span style="font-weight:700; color:#3b82f6;">${Number(s.theoretical_score).toFixed(2)}</span>` : '<span style="color:var(--text-muted);">—</span>';

        const pracStr = s.practical_score !== null ? `<span style="font-weight:700; color:#10b981;">${Number(s.practical_score).toFixed(2)}</span>` : '<span style="color:var(--text-muted);">—</span>';

        const avgStr = s.module_average !== null ? `<strong style="font-size:1.05rem; color:${s.module_average >= 10 ? '#10b981' : '#ef4444'};">${Number(s.module_average).toFixed(2)} / 20</strong>` : '<span style="color:var(--text-muted);">—</span>';



        let statusBadge = '<span class="badge" style="background:rgba(255,255,255,0.08); color:var(--text-muted);">En cours</span>';

        if (s.status === 'ADMIS') {

          statusBadge = '<span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3);">✓ ADMIS</span>';

        } else if (s.status === 'AJOURNÉ') {

          statusBadge = '<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3);">✗ AJOURNÉ</span>';

        }



        return `

          <tr style="border-bottom: 1px solid var(--card-border);">

            <td style="padding:12px 14px; font-family:var(--font-mono); font-size:0.85rem; color:var(--text-muted);">${s.student_id}</td>

            <td style="padding:12px 14px; font-weight:600; color:var(--text-primary);">${s.full_name} <small style="color:var(--text-muted);">(@${s.username})</small></td>

            <td style="padding:12px 14px; text-align:center;">${theoStr}</td>

            <td style="padding:12px 14px; text-align:center;">${pracStr}</td>

            <td style="padding:12px 14px; text-align:center;">${avgStr}</td>

            <td style="padding:12px 14px; text-align:center;">${statusBadge}</td>

            <td style="padding:12px 14px; text-align:right;">

              <button class="btn btn-secondary btn-sm btn-open-student-individual-bulletin" data-id="${s.student_id}" style="padding:4px 10px; font-size:0.8rem;">

                📄 Bulletin

              </button>

            </td>

          </tr>

        `;

      }).join('');



      tbody.querySelectorAll('.btn-open-student-individual-bulletin').forEach(btn => {

        btn.onclick = () => {

          const stId = btn.getAttribute('data-id');

          this.openStudentBulletinModal(stId);

        };

      });



    } catch (err) {

      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:#ef4444;">Erreur lors du chargement : ${err.message}</td></tr>`;

    }

  }



  // =========================================================================

  // MODAL : GÉNÉRATEUR D'ÉPREUVES PYTHON (BANQUE D'EXERCICES)

  // =========================================================================



  initPythonGeneratorModal() {

    const btnOpen = document.getElementById('btn-open-python-generator-modal');

    const modal = document.getElementById('modal-python-generator');

    const form = document.getElementById('form-python-generator');



    if (btnOpen && modal) {

      btnOpen.onclick = async () => {

        try {

          const stats = await api.getPythonBankStats();

          const statsBox = document.getElementById('py-gen-bank-stats-box');

          if (statsBox && stats) {

            const theo = stats.theoretical || {};

            const prac = stats.practical || {};

            statsBox.innerHTML = `

              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">

                <span>📚 <strong>Banque QCM :</strong> ${theo.total_mcqs || 414} questions (${theo.total_exam_marked || 83} marquées examen)</span>

                <span>💻 <strong>Banque Code :</strong> ${prac.total_challenges || 47} défis (${prac.exam_marked_count || 16} marqués examen)</span>

              </div>

            `;

          }

        } catch (_) {}

        modal.classList.add('active');

      };

    }



    if (form) {

      form.onsubmit = async (e) => {

        e.preventDefault();

        const title = document.getElementById('py-gen-title')?.value.trim();

        const exam_type = document.getElementById('py-gen-type')?.value || 'theoretical';

        const duration_minutes = parseInt(document.getElementById('py-gen-duration')?.value, 10) || 45;

        const room_id = document.getElementById('py-gen-room')?.value.trim() || 'SALLE-CENTRAL-01';



        const diff_easy = parseInt(document.getElementById('py-gen-diff-easy')?.value, 10) || 10;

        const diff_medium = parseInt(document.getElementById('py-gen-diff-medium')?.value, 10) || 10;

        const diff_hard = parseInt(document.getElementById('py-gen-diff-hard')?.value, 10) || 5;

        const diff_vhard = parseInt(document.getElementById('py-gen-diff-vhard')?.value, 10) || 5;



        const submitBtn = document.getElementById('btn-submit-python-generator');

        if (submitBtn) {

          submitBtn.disabled = true;

          submitBtn.textContent = "⏳ Génération en cours...";

        }



        try {

          const res = await api.generatePythonExam({

            title,

            exam_type,

            duration_minutes,

            room_id,

            difficulty_counts: {

              easy: diff_easy,

              medium: diff_medium,

              hard: diff_hard,

              "very hard": diff_vhard

            }

          });



          this.showToast(res.message || "Épreuve Python générée avec succès !", "success");

          this.closeModal('modal-python-generator');

          form.reset();

          await this.renderTeacherView();

        } catch (err) {

          this.showToast(`Erreur génération Python : ${err.message}`, "danger");

        } finally {

          if (submitBtn) {

            submitBtn.disabled = false;

            submitBtn.textContent = "⚡ Générer & Ouvrir la Session";

          }

        }

      };

    }

  }



  // =========================================================================

  // PURGE SÉCURISÉE DES EXAMENS & NOTES (ADMIN)

  // =========================================================================



  initClearExamsHandler() {
    // Export PV Tests de Niveau (PDF)
    const btnExportLevel = document.getElementById('btn-admin-export-level-tests-pdf');
    if (btnExportLevel) {
      btnExportLevel.onclick = async () => {
        const specSelect = document.getElementById('select-admin-level-tests-spec');
        const spec = specSelect ? specSelect.value : 'ALL';
        this.showToast(`Génération du PV officiel des Tests de Niveau (${spec})...`, "info");
        try {
          await api.downloadLevelTestsPDF(spec);
          this.showToast("Procès-Verbal des Tests de Niveau téléchargé avec succès.", "success");
        } catch (err) {
          this.showToast(`Erreur d'export du PV : ${err.message}`, "danger");
        }
      };
    }

    // Purge exclusive des scores des Tests de Niveau
    const btnPurgePractice = document.getElementById('btn-admin-purge-practice-scores');
    if (btnPurgePractice) {
      btnPurgePractice.onclick = async () => {
        const confirmed = await this.showConfirmModal({
          title: "Purger les Scores des Tests de Niveau",
          message: "⚠️ Voulez-vous réinitialiser l'ensemble des scores et tentatives de Tests de Niveau (Programmation Python, Systèmes d'Exploitation, Cybersécurité) pour tous les étudiants ?\n\nLes comptes étudiants et les 100 questions par module restent intacts.",
          confirmText: "🗑️ Purger Scores Tests",
          cancelText: "Annuler",
          icon: "⚠️",
          danger: true
        });
        if (!confirmed) return;

        try {
          const res = await api.purgePracticeScores();
          this.showToast(res.message || "Scores des tests de niveau purgés avec succès.", "success");
          await this.loadAdminOverview();
        } catch (err) {
          this.showToast(`Erreur lors de la purge : ${err.message}`, "danger");
        }
      };
    }

    // Purge exclusive des notes d'examen officiel (sessions réinitialisées sans effacer les sujets)
    const btnPurgeExams = document.getElementById('btn-admin-purge-exam-scores');
    if (btnPurgeExams) {
      btnPurgeExams.onclick = async () => {
        const confirmed = await this.showConfirmModal({
          title: "Purger les Notes des Examens Officiels",
          message: "⚠️ Voulez-vous purger l'ensemble des copies, notes et tentatives d'examen officiel pour démarrer une nouvelle session d'examen ?\n\nLes sujets d'examens, barèmes et questions créés sont préservés intacts.",
          confirmText: "🗑️ Purger Notes Examens",
          cancelText: "Annuler",
          icon: "⚠️",
          danger: true
        });
        if (!confirmed) return;

        try {
          const res = await api.purgeExamScores();
          this.showToast(res.message || "Notes des examens officiels purgées avec succès.", "success");
          await this.loadAdminOverview();
          await this.loadAdminResults();
        } catch (err) {
          this.showToast(`Erreur lors de la purge : ${err.message}`, "danger");
        }
      };
    }

    const btnClear = document.getElementById('btn-admin-clear-exams');
    if (btnClear) {
      btnClear.onclick = async () => {
        const confirmed = await this.showConfirmModal({
          title: "Purge Totale des Examens & Notes",
          message: "⚠️ ATTENTION : Êtes-vous certain de vouloir purger TOUS les examens, sessions et notes ?\n\nLes comptes utilisateurs et modules seront conservés.\nCette action est irréversible.",
          confirmText: "🗑️ Purger Tout",
          cancelText: "Annuler",
          icon: "⚠️",
          danger: true
        });
        if (!confirmed) return;

        try {
          const res = await api.clearAllExamsAndScores(false);
          this.showToast(res.message || "Examens et notes purgés avec succès.", "success");
          await this.loadAdminOverview();
          await this.loadAdminResults();
        } catch (err) {
          this.showToast(`Erreur lors de la purge : ${err.message}`, "danger");
        }
      };
    }
  }

  initLevelTestRenameHandlers() {
    const btnRefresh = document.getElementById('btn-admin-refresh-level-tests');
    if (btnRefresh) {
      btnRefresh.onclick = () => {
        this.loadAdminLevelTests();
      };
    }

    const form = document.getElementById('form-edit-level-test');
    if (form) {
      form.onsubmit = async (e) => {
        e.preventDefault();
        const code = document.getElementById('edit-level-test-code')?.value;
        const title = document.getElementById('edit-level-test-title')?.value?.trim();
        const description = document.getElementById('edit-level-test-desc')?.value?.trim();

        if (!code || !title) {
          this.showToast("Le titre officiel est obligatoire.", "warning");
          return;
        }

        try {
          const res = await api.updateLevelTestName(code, { title, description });
          this.showToast(res.message || "Intitulé du test de niveau mis à jour avec succès !", "success");
          this.closeModal('modal-edit-level-test');
          await this.loadAdminLevelTests();
          await this.loadAdminModules();
          if (typeof this._loadPracticeModules === 'function') {
            await this._loadPracticeModules();
          }
        } catch (err) {
          this.showToast(`Erreur de mise à jour : ${err.message}`, "danger");
        }
      };
    }
  }

  async loadAdminLevelTests() {
    const tbody = document.getElementById('admin-level-tests-table-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:18px; color:var(--text-muted);">Chargement des tests de niveau...</td></tr>';

    try {
      const tests = await api.getLevelTestsConfigs();
      this._adminLevelTestsList = tests;

      if (!tests || tests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:18px; color:var(--text-muted);">Aucun test de niveau trouvé.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      tests.forEach(t => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--card-border)';
        tr.innerHTML = `
          <td style="padding:10px 14px; font-family:monospace; font-weight:700; color:#38bdf8;">
            ${this._escapeHtml(t.code)}
          </td>
          <td style="padding:10px 14px; font-weight:600; color:var(--text-primary);">
            ${this._escapeHtml(t.title)}
          </td>
          <td style="padding:10px 14px; font-size:0.82rem; color:var(--text-secondary); max-width:320px;">
            ${this._escapeHtml(t.description || '—')}
          </td>
          <td style="padding:10px 14px; text-align:center;">
            <span class="badge" style="background:rgba(56, 189, 248, 0.15); color:#38bdf8; font-weight:700; font-size:0.8rem; padding:3px 8px; border-radius:12px;">
              ${t.total_questions || 100} Q
            </span>
          </td>
          <td style="padding:10px 14px; text-align:center;">
            <button class="btn btn-secondary btn-admin-edit-level-test" data-code="${t.code}" style="padding:5px 10px; font-size:0.8rem; border-color:#38bdf8; color:#38bdf8;">
              ✏️ Renommer
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-admin-edit-level-test').forEach(btn => {
        btn.onclick = () => {
          const code = btn.getAttribute('data-code');
          const t = (this._adminLevelTestsList || []).find(x => x.code === code);
          if (t) {
            this.openEditLevelTestModal(t);
          }
        };
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:18px; color:var(--danger);">Erreur : ${this._escapeHtml(err.message)}</td></tr>`;
    }
  }

  openEditLevelTestModal(test) {
    const modal = document.getElementById('modal-edit-level-test');
    if (!modal) return;

    const codeInp = document.getElementById('edit-level-test-code');
    const codeDisp = document.getElementById('edit-level-test-code-display');
    const titleInp = document.getElementById('edit-level-test-title');
    const descInp = document.getElementById('edit-level-test-desc');

    if (codeInp) codeInp.value = test.code || '';
    if (codeDisp) codeDisp.value = test.code || '';
    if (titleInp) titleInp.value = test.title || '';
    if (descInp) descInp.value = test.description || '';

    this.openModal('modal-edit-level-test');
  }



  // =========================================================================

  // MODALE PERSONNALISÉE DE CONFIRMATION & ALERTE (ZÉRO ALERT/CONFIRM NATIF)

  // =========================================================================



  showConfirmModal({

    title = "Confirmation",

    message = "Êtes-vous certain de vouloir effectuer cette action ?",

    confirmText = "Confirmer",

    cancelText = "Annuler",

    icon = "⚠️",

    danger = false

  } = {}) {

    return new Promise((resolve) => {

      const modal = document.getElementById('modal-custom-dialog');

      if (!modal) {

        resolve(true);

        return;

      }

      const iconEl = document.getElementById('custom-dialog-icon');

      const titleEl = document.getElementById('custom-dialog-title');

      const msgEl = document.getElementById('custom-dialog-message');

      const btnConfirm = document.getElementById('btn-custom-dialog-confirm');

      const btnCancel = document.getElementById('btn-custom-dialog-cancel');



      if (iconEl) iconEl.textContent = icon;

      if (titleEl) titleEl.textContent = title;

      if (msgEl) msgEl.textContent = message;



      if (btnConfirm) {

        btnConfirm.textContent = confirmText;

        btnConfirm.className = danger ? 'btn btn-danger' : 'btn btn-primary';

        btnConfirm.style.background = danger ? '#ef4444' : '';

      }

      if (btnCancel) {

        btnCancel.style.display = 'inline-flex';

        btnCancel.textContent = cancelText;

      }



      const cleanup = (result) => {

        modal.classList.remove('active');

        if (btnConfirm) btnConfirm.onclick = null;

        if (btnCancel) btnCancel.onclick = null;

        resolve(result);

      };



      if (btnConfirm) btnConfirm.onclick = () => cleanup(true);

      if (btnCancel) btnCancel.onclick = () => cleanup(false);



      modal.classList.add('active');

    });

  }



  showAlertModal({

    title = "Information",

    message = "",

    buttonText = "Fermer",

    icon = "ℹ️"

  } = {}) {

    return new Promise((resolve) => {

      const modal = document.getElementById('modal-custom-dialog');

      if (!modal) {

        this.showToast(message, "info");

        resolve(true);

        return;

      }

      const iconEl = document.getElementById('custom-dialog-icon');

      const titleEl = document.getElementById('custom-dialog-title');

      const msgEl = document.getElementById('custom-dialog-message');

      const btnConfirm = document.getElementById('btn-custom-dialog-confirm');

      const btnCancel = document.getElementById('btn-custom-dialog-cancel');



      if (iconEl) iconEl.textContent = icon;

      if (titleEl) titleEl.textContent = title;

      if (msgEl) msgEl.textContent = message;

      if (btnCancel) btnCancel.style.display = 'none';

      if (btnConfirm) {

        btnConfirm.textContent = buttonText;

        btnConfirm.className = 'btn btn-primary';

        btnConfirm.style.background = '';

        btnConfirm.onclick = () => {

          modal.classList.remove('active');

          resolve(true);

        };

      }

      modal.classList.add('active');

    });

  }



  // =========================================================================

  // FICHES IDENTIFIANTS DÉCOUPABLES (✂️) SÉPARÉES ÉTUDIANTS / ENSEIGNANTS

  // =========================================================================



  async openPrintCredentialsSlipsModal(role = 'student') {

    const modal = document.getElementById('modal-print-credentials-slips');

    const titleEl = document.getElementById('print-slips-modal-title');

    const container = document.getElementById('printable-credentials-slips-container') || document.getElementById('printable-slips-container');

    if (!modal || !container) return;



    this._currentPrintSlipsRole = role;

    if (titleEl) {

      titleEl.textContent = role === 'teacher'

        ? '✂️ Fiches Identifiants Découpables — Enseignants'

        : '✂️ Fiches Identifiants Découpables — Étudiants';

    }

    container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:24px; color:var(--text-secondary);">Préparation des fiches identifiants à découper...</div>';

    modal.classList.add('active');



    try {

      let users = await api.listUsers(role);

      if (role === 'student') {

        const filterYearVal = document.getElementById('admin-students-filter-year')?.value || '';

        const filterGroupVal = document.getElementById('admin-students-filter-group')?.value || '';

        if (filterYearVal) users = users.filter(u => u.enrollment_year === filterYearVal);

        if (filterGroupVal) users = users.filter(u => u.group_id === filterGroupVal);

      }



      this._currentPrintSlipsUsers = users;

      if (!users || users.length === 0) {

        container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:24px; color:var(--text-muted);">Aucun compte à imprimer pour cette sélection.</div>';

        return;

      }



      container.innerHTML = users.map(u => {

        const roleLabel = role === 'teacher' ? 'ENSEIGNANT / SURVEILLANT' : `ÉTUDIANT • ${this._escapeHtml(u.group_id || 'SPÉCIALITÉ')}`;

        const subMeta = role === 'teacher'

          ? `Modules : ${(u.assigned_modules || []).map(m => m.code || m).join(', ') || 'Aucun'}`

          : `Matricule : ${this._escapeHtml(u.id)} • Année : ${this._escapeHtml(u.enrollment_year || '2025-2026')}`;



        return `

          <div class="credential-cut-slip" style="border: 2px dashed #64748b; border-radius: 10px; padding: 14px 16px; background: rgba(15, 23, 42, 0.65); position: relative;">

            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(148,163,184,0.25); padding-bottom:6px; margin-bottom:8px;">

              <span style="font-size:0.72rem; font-weight:800; letter-spacing:0.06em; color:#60a5fa;">✂️ FICHE D'ACCÈS INDIVIDUELLE</span>

              <span style="font-size:0.72rem; font-weight:700; color:#a78bfa;">${roleLabel}</span>

            </div>

            <div style="font-size:1rem; font-weight:800; color:var(--text-primary); margin-bottom:3px;">${this._escapeHtml(u.full_name || u.username)}</div>

            <div style="font-size:0.78rem; color:var(--text-secondary); margin-bottom:10px;">${subMeta}</div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; background:rgba(0,0,0,0.28); padding:8px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.08);">

              <div>

                <div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase;">Identifiant (Login)</div>

                <div style="font-family:var(--font-mono); font-size:0.95rem; font-weight:800; color:#38bdf8;">${this._escapeHtml(u.username)}</div>

              </div>

              <div>

                <div style="font-size:0.7rem; color:var(--text-muted); text-transform:uppercase;">Mot de Passe</div>

                <div style="font-family:var(--font-mono); font-size:0.95rem; font-weight:800; color:#34d399;">${this._escapeHtml(u.plain_password || '••••••••')}</div>

              </div>

            </div>

          </div>

        `;

      }).join('');

    } catch (err) {

      container.innerHTML = `<div style="grid-column:1/-1; color:var(--danger); padding:16px;">Erreur : ${this._escapeHtml(err.message)}</div>`;

    }

  }



  printCredentialsSlipsWindow() {

    const users = this._currentPrintSlipsUsers || [];

    const role = this._currentPrintSlipsRole || 'student';

    if (!users.length) {

      this.showToast("Aucune fiche à imprimer.", "warning");

      return;

    }



    const title = role === 'teacher'

      ? "Fiches d'Identifiants à Découper — Enseignants"

      : "Fiches d'Identifiants à Découper — Étudiants";



    const slipsHtml = users.map(u => {

      const roleLabel = role === 'teacher' ? 'ENSEIGNANT / SURVEILLANT' : `ÉTUDIANT • ${this._escapeHtml(u.group_id || 'SPÉCIALITÉ')}`;

      const subMeta = role === 'teacher'

        ? `ID : ${this._escapeHtml(u.id)} • Modules : ${(u.assigned_modules || []).map(m => m.code || m).join(', ') || 'Aucun'}`

        : `Matricule : ${this._escapeHtml(u.id)} • Année : ${this._escapeHtml(u.enrollment_year || '2025-2026')}`;

      return `

        <div class="slip">

          <div class="slip-header">

            <span>✂️ PLATEFORME D'EXAMEN — FICHE D'IDENTIFIANTS</span>

            <strong>${roleLabel}</strong>

          </div>

          <div class="slip-name">${this._escapeHtml(u.full_name || u.username)}</div>

          <div class="slip-meta">${subMeta}</div>

          <div class="slip-creds">

            <div>

              <span class="lbl">Identifiant (Login) :</span>

              <span class="val">${this._escapeHtml(u.username)}</span>

            </div>

            <div>

              <span class="lbl">Mot de passe :</span>

              <span class="val">${this._escapeHtml(u.plain_password || '••••••••')}</span>

            </div>

          </div>

        </div>

      `;

    }).join('');



    const w = window.open('', '_blank', 'width=950,height=750');

    if (!w) {

      window.print();

      return;

    }

    w.document.write(`<!DOCTYPE html>

<html lang="fr">

<head>

  <meta charset="UTF-8">

  <title>${title}</title>

  <style>

    * { box-sizing: border-box; }

    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 16px; color: #0f172a; background: #fff; }

    h1 { font-size: 16px; margin: 0 0 12px 0; text-align: center; text-transform: uppercase; letter-spacing: 0.04em; }

    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

    .slip { border: 2px dashed #334155; border-radius: 8px; padding: 12px 14px; page-break-inside: avoid; }

    .slip-header { display: flex; justify-content: space-between; font-size: 10px; color: #475569; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; margin-bottom: 6px; }

    .slip-name { font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 2px; }

    .slip-meta { font-size: 11px; color: #475569; margin-bottom: 8px; }

    .slip-creds { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: #f8fafc; border: 1px solid #cbd5e1; padding: 8px; border-radius: 6px; }

    .lbl { display: block; font-size: 10px; text-transform: uppercase; color: #64748b; }

    .val { font-family: Consolas, monospace; font-size: 14px; font-weight: 800; color: #0f172a; }

    @media print {

      body { margin: 8mm; }

    }

  </style>

</head>

<body>

  <h1>${title}</h1>

  <div class="grid">${slipsHtml}</div>

  <script>window.onload = function() { window.print(); };</script>

</body>

</html>`);

    w.document.close();

  }



}



// Exposer globalement window.showToast

window.showToast = (msg, type = 'info', dur = 4000) => {

  if (window.app && typeof window.app.showToast === 'function') {

    return window.app.showToast(msg, type, dur);

  }

};



// Initialisation au chargement du DOM

window.addEventListener('DOMContentLoaded', () => {

  const app = new AppController();

  app.init();

});

