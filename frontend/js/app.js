/**
 * Contrôleur Principal de l'Application Frontend (Vanilla JS)
 * Gère le routage des vues, l'authentification, le tableau de bord étudiant enrichi,
 * les statistiques complètes de performance, le centre d'évaluation et tests de niveau multi-modules,
 * et le déroulement unifié des examens (1 question / page avec touches fléchées).
 */

import { api } from './api.js';
import { AntiCheatManager } from './anticheat.js';
import { ExamRunner } from './exam-runner.js';

class AppController {
  constructor() {
    this.currentView = null;
    this.currentUser = null;
    this.activeExamRunner = null;
    this.activeAntiCheat = null;
    this.lastStudentStats = null;
  }

  async init() {
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

  _attachGlobalListeners() {
    // Déconnexion
    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) {
      logoutBtn.onclick = () => {
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
          if (errorBox) errorBox.style.display = 'none';
          const authData = await api.login(usernameInput.value, passwordInput.value);
          this.currentUser = authData.user;

          if (authData.must_change_password) {
            alert("Première connexion détectée : Pensez à mettre à jour votre mot de passe.");
          }

          this.renderDashboard(authData.user);
        } catch (err) {
          if (errorBox) {
            errorBox.textContent = err.message;
            errorBox.style.display = 'block';
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
      btnOpenCustomExam.onclick = () => {
        modalCustomExam.classList.add('active');
      };
    }

    if (formCustomExam) {
      formCustomExam.onsubmit = async (e) => {
        e.preventDefault();
        const title = document.getElementById('create-exam-title')?.value.trim();
        const module_code = document.getElementById('create-exam-module')?.value;
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
            duration_minutes,
            global_points,
            room_id,
            instructions,
            group_ids: targetGroups,
            shuffle_questions,
            shuffle_options
          });

          alert(`✅ Épreuve officielle "${res.title}" créée avec succès (${res.question_count} questions) ! Salle ${room_id} prête.`);
          this.closeModal('modal-create-custom-exam');
          formCustomExam.reset();
          await this.renderTeacherView();
        } catch (err) {
          alert(`Erreur de création d'examen : ${err.message}`);
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
          alert(`✅ Examen "${res.title}" importé avec succès (${res.question_count} questions). Il est prêt pour la surveillance.`);
          this.renderTeacherView();
        } catch (err) {
          alert(`Erreur d'importation de l'examen JSON : ${err.message}`);
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
          alert(`✅ ${res.message || "Package d'examen importé avec succès !"}`);
          await this.renderTeacherView();
        } catch (err) {
          alert(`Erreur d'importation du package : ${err.message}`);
        } finally {
          inputImportPackage.value = '';
        }
      };
    }

    // Proctoring : Exportation de l'archive de résultats .results.zip
    const btnProctorExportZip = document.getElementById('btn-proctor-export-results-zip');
    if (btnProctorExportZip) {
      btnProctorExportZip.onclick = async () => {
        if (!this.activeSessionId) return alert("Aucune session active sélectionnée.");
        try {
          await api.exportSessionResultsZip(this.activeSessionId);
        } catch (err) {
          alert(`Erreur d'exportation de l'archive de résultats : ${err.message}`);
        }
      };
    }

    // Proctoring : Analyse Psychométrique de la session en direct
    const btnProctorItemAnalysis = document.getElementById('btn-proctor-item-analysis');
    if (btnProctorItemAnalysis) {
      btnProctorItemAnalysis.onclick = () => {
        if (!this.activeSessionId) return alert("Aucune session active sélectionnée.");
        this.openSessionItemAnalysisModal(this.activeSessionId);
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
          alert(`✅ ${res.message || "Archive de résultats réconciliée avec succès !"}`);
          await this.loadAdminOverview();
          await this.loadAdminResults();
        } catch (err) {
          alert(`Erreur lors de la réconciliation de l'archive : ${err.message}`);
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
          alert(`Erreur de téléchargement : ${err.message}`);
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
          alert(`Erreur d'exportation CSV : ${err.message}`);
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
          alert(`✅ ${res.message || "Questions importées avec succès."}`);
          await this.openManageQuestionsModal(this._currentManageExamId, this._currentManageExamTitle);
          if (this.currentUser && this.currentUser.role === 'admin') {
            await this.loadAdminExams();
          } else {
            await this.renderTeacherView();
          }
        } catch (err) {
          alert(`Erreur d'importation JSON : ${err.message}`);
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
          alert(`Erreur d'exportation : ${err.message}`);
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
        const { options_json, correct_answers_json } = this._extractOptionsAndAnswersFromForm(type);

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
            alert("Question mise à jour avec succès.");
          } else {
            await api.createQuestion(examId, payload);
            alert("Nouvelle question ajoutée avec succès.");
          }
          this.closeModal('modal-edit-question');
          await this.openManageQuestionsModal(examId, this._currentManageExamTitle);
          if (this.currentUser && this.currentUser.role === 'admin') {
            await this.loadAdminExams();
          } else {
            await this.renderTeacherView();
          }
        } catch (err) {
          alert(`Erreur lors de l'enregistrement de la question : ${err.message}`);
        }
      };
    }

    // Fermeture générique des modales
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
      btn.onclick = () => {
        const target = btn.getAttribute('data-target');
        if (target) this.closeModal(target);
      };
    });

    // Navigation Centre Python Dédié
    const btnOpenTraining = document.getElementById('btn-open-training-center');
    if (btnOpenTraining) {
      btnOpenTraining.onclick = () => this.renderTrainingCenterView();
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

    // Alertes réseau déconnecté / reconnecté
    window.addEventListener('network:offline', () => {
      const banner = document.getElementById('banner-offline');
      if (banner) banner.classList.add('active');
    });

    window.addEventListener('online', () => {
      const banner = document.getElementById('banner-offline');
      if (banner) banner.classList.remove('active');
      api.flushOfflineQueue();
    });

    window.addEventListener('auth:expired', () => {
      alert("Votre session a expiré. Veuillez vous reconnecter.");
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
        { id: 'nav-dash', label: '📊 Mon Tableau de Bord', action: () => this.renderDashboard(user) },
        { id: 'nav-training', label: '🐍 Centre d\'Entraînement Python', action: () => this.renderTrainingCenterView() },
        { id: 'nav-practice', label: '🎯 Tests de Niveau par Module', action: () => {
          this.renderDashboard(user);
          setTimeout(() => {
            document.getElementById('practice-modules-grid')?.scrollIntoView({ behavior: 'smooth' });
          }, 100);
        }},
        { id: 'nav-exams', label: '📋 Examens Officiels', action: () => {
          this.renderDashboard(user);
          setTimeout(() => {
            document.getElementById('official-exams-grid')?.scrollIntoView({ behavior: 'smooth' });
          }, 100);
        }}
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
        <button class="role-nav-btn" onclick="window.open('/docs', '_blank')">📚 API Swagger (/docs)</button>
      `;
      const teacherBtn = document.getElementById('nav-teacher-surveillance');
      if (teacherBtn) {
        teacherBtn.onclick = () => {
          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));
          teacherBtn.classList.add('active');
          this.renderTeacherView();
        };
      }
    } else if (user.role === 'admin') {
      nav.innerHTML = `
        <button class="role-nav-btn active" id="nav-admin-console">⚙️ Console Administrateur</button>
        <button class="role-nav-btn" onclick="window.open('/docs', '_blank')">📚 API Swagger (/docs)</button>
      `;
      const adminBtn = document.getElementById('nav-admin-console');
      if (adminBtn) {
        adminBtn.onclick = () => {
          nav.querySelectorAll('.role-nav-btn').forEach(b => b.classList.remove('active'));
          adminBtn.classList.add('active');
          this.renderAdminView();
        };
      }
    }
  }

  // --- Vue : Connexion ---
  renderLogin() {
    document.getElementById('header-user-info').style.display = 'none';
    this._renderRoleNav(null);
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
        fundAvgText.textContent = `Moyenne 4 Piliers : ${stats.fundamental_average.toFixed(2)} / 20`;
      }
      if (levelBadge) {
        levelBadge.className = 'level-badge-large';
        if (stats.global_level >= 7) {
          levelBadge.classList.add('level-badge-expert');
        } else if (stats.global_level >= 4) {
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

  // --- Chargement des Examens Officiels ---
  async _loadOfficialExams() {
    const container = document.getElementById('official-exams-grid');
    if (!container) return;

    try {
      const exams = await api.getAvailableExams();
      if (!exams.length) {
        container.innerHTML = `
          <div style="grid-column: 1/-1; text-align:center; padding:32px; color:var(--text-secondary); background:var(--bg-surface); border-radius:var(--radius-md); border:1px solid var(--card-border);">
            Aucun examen officiel programmé pour votre groupe actuellement.
          </div>
        `;
        return;
      }

      container.innerHTML = '';
      exams.forEach(ex => {
        const card = document.createElement('div');
        card.className = 'exam-card';
        const isSubmitted = ex.attempt_status === 'submitted' || ex.attempt_status === 'completed' || ex.attempt_status === 'timed_out';
        const hasScore = ex.final_mark !== null && ex.final_mark !== undefined;

        let actionAreaHtml = '';
        if (isSubmitted) {
          actionAreaHtml = `
            <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid var(--success); border-radius: var(--radius-md); padding: 12px; text-align: center; color: var(--success); font-weight: 700; margin-top: 10px;">
              ✅ Épreuve Soumise & Scellée ${hasScore ? `(${Number(ex.final_mark).toFixed(2)} / ${ex.global_points})` : ''}
            </div>
          `;
        } else {
          actionAreaHtml = `
            <button class="btn btn-primary" style="width:100%; margin-top: 10px;" id="btn-start-exam-${ex.exam_id}">
              ${ex.attempt_status === 'in_progress' ? 'Reprendre mon épreuve ➔' : 'Commencer l\'épreuve ➔'}
            </button>
          `;
        }

        card.innerHTML = `
          <div>
            <span class="exam-card-badge">${this._escapeHtml(ex.module_code)}</span>
            <h4>${this._escapeHtml(ex.title)}</h4>
            <p>${this._escapeHtml(ex.instructions || 'Aucune consigne particulière.')}</p>
          </div>
          <div>
            <div class="exam-meta">
              <span>⏱️ ${ex.duration_minutes} min</span>
              <span>📝 ${ex.question_count} questions</span>
              <span>🎯 Barème / ${ex.global_points}</span>
            </div>
            ${actionAreaHtml}
          </div>
        `;

        const startBtn = card.querySelector(`#btn-start-exam-${ex.exam_id}`);
        if (startBtn) {
          startBtn.onclick = () => {
            this.launchOfficialExam(ex.exam_id);
          };
        }

        container.appendChild(card);
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
        fundAvgText.textContent = `Moyenne 4 Piliers : ${data.overall_last_4_average.toFixed(2)} / 20`;
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
        card.innerHTML = `
          <div class="pillar-mini-header">
            <span>${p.module_code}</span>
            <span>${p.attempts_count} tent.</span>
          </div>
          <div class="pillar-mini-level">${p.level_title}</div>
          <div class="pillar-mini-sub">
            <span>Score (4 der.) :</span>
            <strong style="color:#60a5fa; font-family:var(--font-mono);">${p.last_4_average.toFixed(2)} / 20</strong>
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
              <span class="user-tag" style="background:rgba(59, 130, 246, 0.15); color:#93c5fd; font-weight:700;">${m.code}</span>
              <span style="font-size:0.8rem; color:var(--text-muted); font-weight:600;">Tentatives : ${m.attempts_count}</span>
            </div>
            <h4 style="font-size:1.15rem; margin:0 0 10px 0; color:#fff;">${this._escapeHtml(m.title)}</h4>
            
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:var(--radius-md); padding:10px 12px; margin-bottom:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:0.8rem; color:var(--text-secondary);">Score (4 dernières tentatives) :</span>
                <strong style="font-size:1.05rem; color:#60a5fa; font-family:var(--font-mono);">${m.last_4_average.toFixed(2)} / 20</strong>
              </div>
              <div class="score-pills-row">
                ${pillsHtml}
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem;">
              <span style="color:var(--text-muted);">Niveau Actuel :</span>
              <span class="user-tag" style="background:rgba(16, 185, 129, 0.15); color:#6ee7b7; border-color:rgba(16, 185, 129, 0.3); font-weight:700;">
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

    const fundamentalGrid = document.getElementById('stats-fundamental-grid');
    const ladderGrid = document.getElementById('stats-level-ladder');
    const modulesTable = document.getElementById('stats-modules-table-body');
    const timelineTable = document.getElementById('stats-timeline-table-body');

    try {
      const stats = await api.getStudentStatistics();
      this.lastStudentStats = stats;

      // 1. Rendu des 4 Modules Fondamentaux (Pilier du Cursus)
      if (fundamentalGrid) {
        fundamentalGrid.innerHTML = '';
        const fundModules = stats.modules_breakdown.filter(m => m.is_fundamental);

        fundModules.forEach(m => {
          const card = document.createElement('div');
          card.className = `fundamental-card ${m.passed ? 'passed' : ''}`;

          let masteryClass = 'mastery-none';
          if (m.mastery_level.includes('Experte')) masteryClass = 'mastery-expert';
          else if (m.mastery_level.includes('Avancé')) masteryClass = 'mastery-advanced';
          else if (m.mastery_level.includes('acquise')) masteryClass = 'mastery-acquired';
          else if (m.mastery_level.includes('progression')) masteryClass = 'mastery-progression';

          card.innerHTML = `
            <div>
              <div class="fundamental-header">
                <span class="fundamental-code-tag">${this._escapeHtml(m.code)}</span>
                <span class="mastery-pill ${masteryClass}">${m.mastery_level}</span>
              </div>
              <h4 class="fundamental-title">${this._escapeHtml(m.title)}</h4>
              <div class="fundamental-mark-box">
                <div class="fundamental-big-mark">${m.best_mark.toFixed(1)}</div>
                <div class="fundamental-mark-total">/ 20</div>
              </div>
              <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:12px;">
                Moyenne : <strong>${m.average_mark.toFixed(1)} / 20</strong> • <strong>${m.attempts_count}</strong> évaluation(s)
              </div>
            </div>
            <div>
              <div style="margin-bottom:12px; font-size:0.8rem; font-weight:600; color:${m.passed ? 'var(--success)' : 'var(--warning)'};">
                ${m.passed ? '✅ Module Validé (≥ 10/20)' : '⏳ Module en Cours (< 10/20)'}
              </div>
              <button class="btn btn-secondary" style="width:100%; font-size:0.85rem;" id="btn-stats-train-${m.code}">
                S'entraîner sur ce pilier ➔
              </button>
            </div>
          `;

          card.querySelector(`#btn-stats-train-${m.code}`).onclick = () => {
            this.launchPracticeExam(m.code);
          };

          fundamentalGrid.appendChild(card);
        });
      }

      // 2. Rendu de l'Échelle Officielle des 6 Niveaux (REV-11)
      if (ladderGrid) {
        ladderGrid.innerHTML = '';
        const levelDescriptions = [
          { level: 1, title: "Insuffisant", range: "0.00 à < 7.00 / 20" },
          { level: 2, title: "Sous la moyenne", range: "7.00 à < 10.00 / 20" },
          { level: 3, title: "Limite", range: "10.00 à < 12.00 / 20" },
          { level: 4, title: "Moyen", range: "12.00 à < 14.00 / 20" },
          { level: 5, title: "Bon", range: "14.00 à < 16.00 / 20" },
          { level: 6, title: "Excellent", range: "16.00 à 20.00 / 20" },
        ];

        levelDescriptions.forEach(lvl => {
          const item = document.createElement('div');
          const isActive = (stats.global_level === lvl.level);
          item.className = `level-ladder-item ${isActive ? 'active-level' : ''}`;
          item.innerHTML = `
            <div class="level-number-badge">${lvl.level}</div>
            <div>
              <div style="font-weight:700; font-size:0.9rem; color:${isActive ? '#60a5fa' : 'var(--text-primary)'};">
                ${lvl.title} ${isActive ? '★ (Votre Niveau)' : ''}
              </div>
              <div style="font-size:0.75rem; color:var(--text-muted);">${lvl.range}</div>
            </div>
          `;
          ladderGrid.appendChild(item);
        });
      }

      // 3. Tableau Complet de Tous les Modules
      if (modulesTable) {
        modulesTable.innerHTML = '';
        stats.modules_breakdown.forEach(m => {
          const row = document.createElement('tr');
          let masteryClass = 'mastery-none';
          if (m.mastery_level.includes('Experte')) masteryClass = 'mastery-expert';
          else if (m.mastery_level.includes('Avancé')) masteryClass = 'mastery-advanced';
          else if (m.mastery_level.includes('acquise')) masteryClass = 'mastery-acquired';
          else if (m.mastery_level.includes('progression')) masteryClass = 'mastery-progression';

          row.innerHTML = `
            <td><code>${this._escapeHtml(m.code)}</code></td>
            <td style="font-weight:600;">${this._escapeHtml(m.title)}</td>
            <td>
              <span class="user-tag" style="font-size:0.75rem; ${m.is_fundamental ? 'background:rgba(59,130,246,0.15); color:#93c5fd;' : ''}">
                ${m.is_fundamental ? 'Pilier Fondamental' : 'Module Complémentaire'}
              </span>
            </td>
            <td><strong style="font-family:var(--font-mono); font-size:1.05rem; color:#60a5fa;">${m.best_mark.toFixed(1)}</strong> / 20</td>
            <td style="font-family:var(--font-mono);">${m.average_mark.toFixed(1)} / 20</td>
            <td>${m.attempts_count}</td>
            <td>
              <span style="font-weight:600; color:${m.passed ? 'var(--success)' : 'var(--text-muted)'};">
                ${m.passed ? '✅ Validé' : 'Non validé'}
              </span>
            </td>
            <td><span class="mastery-pill ${masteryClass}">${m.mastery_level}</span></td>
            <td>
              <button class="btn btn-secondary" style="padding:4px 10px; font-size:0.8rem;" id="btn-table-train-${m.code}">
                S'entraîner ➔
              </button>
            </td>
          `;

          row.querySelector(`#btn-table-train-${m.code}`).onclick = () => {
            this.launchPracticeExam(m.code);
          };

          modulesTable.appendChild(row);
        });
      }

      // 4. Historique Chronologique
      if (timelineTable) {
        timelineTable.innerHTML = '';
        if (!stats.recent_timeline || !stats.recent_timeline.length) {
          timelineTable.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Aucune évaluation enregistrée pour le moment.</td></tr>';
        } else {
          // Inverser pour avoir les plus récentes en haut
          [...stats.recent_timeline].reverse().forEach(ev => {
            const row = document.createElement('tr');
            const isPassed = ev.mark >= 10.0;
            row.innerHTML = `
              <td style="font-family:var(--font-mono); font-size:0.85rem;">${this._escapeHtml(ev.date)}</td>
              <td>
                <span class="user-tag" style="font-size:0.75rem; ${ev.type === 'officiel' ? 'background:rgba(16,185,129,0.15); color:#6ee7b7;' : 'background:rgba(59,130,246,0.15); color:#93c5fd;'}">
                  ${ev.type === 'officiel' ? '📋 Examen Officiel' : '🎯 Test de Niveau'}
                </span>
              </td>
              <td style="font-weight:600;">${this._escapeHtml(ev.title)}</td>
              <td><strong style="font-family:var(--font-mono); font-size:1.05rem; color:${isPassed ? 'var(--success)' : 'var(--danger)'};">${ev.mark.toFixed(1)} / 20</strong></td>
              <td>
                <span class="mastery-pill ${isPassed ? 'mastery-advanced' : 'mastery-progression'}">
                  ${isPassed ? 'Admis' : 'À renforcer'}
                </span>
              </td>
            `;
            timelineTable.appendChild(row);
          });
        }
      }

    } catch (err) {
      alert(`Erreur de chargement des statistiques : ${err.message}`);
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

      row.innerHTML = `
        <div class="topic-meta">
          <div class="topic-order">Chapitre ${String(topic.order).padStart(2, '0')}</div>
          <div class="topic-title">${this._escapeHtml(topic.title)}</div>
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

  // --- Lancement de l'entraînement selon le mode et type choisis ---
  async launchSelectedTraining() {
    if (!this.currentPythonProgression) {
      try {
        this.currentPythonProgression = await api.getPythonProgression();
      } catch (err) {
        alert("Erreur de récupération de la progression : " + err.message);
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
        alert("Aucune question ou exercice disponible pour ce chapitre et ce palier de difficulté.");
        return;
      }

      this.launchUnifiedPythonExam(session, sessionTitle);

    } catch (err) {
      alert(`Erreur lors de la préparation de la session : ${err.message}`);
    }
  }

  // --- Lancement d'une Session Python dans l'ExamRunner Unifié (Même interface que les examens) ---
  launchUnifiedPythonExam(session, title) {
    window.pythonHintsUsed = {};

    const questions = session.items.map((q, idx) => {
      if (q.type === 'coding' || q.type === 'code') {
        return {
          id: q.id,
          type: 'coding',
          points: q.points || 4.0,
          prompt_markdown: q.prompt_markdown || q.prompt || q.description || '',
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
            is_correct: null
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
            alert(`🎉 FÉLICITATIONS ! Vous passez au Niveau ${res.gamification.level} (${res.gamification.level_name}) !`);
          }
          if (res.new_badges && res.new_badges.length > 0) {
            const badgeNames = res.new_badges.map(b => `${b.emoji} ${b.name}`).join('\n• ');
            alert(`🏆 NOUVEAU(X) BADGE(S) DÉBLOQUÉ(S) :\n• ${badgeNames}`);
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
          alert(`Erreur de validation de la session Python : ${err.message}`);
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
        alert("⚠️ 4 avertissements atteints : Le test prend fin immédiatement. Vos résultats sont enregistrés.");
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
      quitBtn.onclick = () => {
        if (confirm("Voulez-vous quitter cette session et retourner au Centre Python ? Vos réponses en cours ne seront pas enregistrées.")) {
          if (this.activeExamRunner) this.activeExamRunner.stop();
          if (this.activeAntiCheat) this.activeAntiCheat.stop();
          this.renderTrainingCenterView();
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
            <span class="user-tag" style="background:rgba(59,130,246,0.15); color:#93c5fd; font-weight:700; margin-right:6px;">${a.module_code}</span>
            <span style="font-weight:600;">${this._escapeHtml(a.module_title)}</span>
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

  // --- Fermeture Générique de Modal ---
  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
  }

  // --- Lancement d'un Examen Officiel (avec Salle d'Attente Interactive REV-25) ---
  async launchOfficialExam(examId) {
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

        const leaveBtn = document.getElementById('btn-waiting-room-leave');
        if (leaveBtn) {
          leaveBtn.onclick = () => {
            const confirmLeave = confirm("⚠️ Attention : L'épreuve officielle va débuter sous peu.\n\nÊtes-vous certain de vouloir quitter la salle d'attente ?");
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
      alert(`Impossible de démarrer l'épreuve : ${err.message}`);
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
            alert(`Erreur de validation : ${err.message}`);
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
          alert("⚠️ 4 avertissements atteints : Le test prend fin immédiatement. Vos résultats sont enregistrés.");
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
        quitBtn.onclick = () => {
          if (confirm("Voulez-vous quitter ce test de niveau et retourner au tableau de bord ? Vos réponses en cours ne seront pas enregistrées.")) {
            if (this.activeExamRunner) this.activeExamRunner.stop();
            if (this.activeAntiCheat) this.activeAntiCheat.stop();
            this.renderDashboard(this.currentUser);
          }
        };
      }

      this.activeExamRunner.start();

    } catch (err) {
      alert(`Erreur de chargement du test de niveau : ${err.message}`);
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
    if (this.activeOriginView === 'view-python') {
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

  // --- Rendu du Score et Confirmation d'Épreuve Officielle Scellée (REV-32) ---
  renderScoreScreen(res) {
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

    if (this.activeOriginView === 'view-python') {
      if (backBtn) {
        backBtn.style.display = 'inline-flex';
        backBtn.innerHTML = '⬅️ Retourner au Centre d\'Entraînement Python';
        backBtn.onclick = () => this.renderTrainingCenterView();
      }
      if (statsBtn) statsBtn.style.display = 'none';
    } else {
      if (backBtn) {
        backBtn.style.display = 'inline-flex';
        backBtn.innerHTML = '⬅️ Retourner au Tableau de Bord';
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
        </div>
      `;
    }
  }

  // --- Vue Dédiée : Enseignant / Gestion des Examens (REV-13, REV-15) ---
  async renderTeacherView() {
    this.switchView('view-teacher');
    const container = document.getElementById('teacher-exams-list');
    if (!container) return;

    container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:32px; color:var(--text-secondary);">Chargement de vos examens...</div>';

    try {
      const exams = await api.listExams();
      if (!exams || exams.length === 0) {
        container.innerHTML = `
          <div style="grid-column: 1/-1; padding:32px; text-align:center; color:var(--text-secondary); background:var(--bg-surface); border-radius:var(--radius-md); border:1px solid var(--card-border);">
            <div style="font-size:2rem; margin-bottom:8px;">📝</div>
            <div style="font-weight:700; font-size:1.1rem; color:var(--text-primary); margin-bottom:6px;">Aucun examen disponible pour le moment</div>
            <p style="margin-bottom:16px;">Chargez un modèle officiel clé en main (Python, Linux, Cryptographie) ou importez un fichier JSON.</p>
            <button class="btn btn-primary" onclick="window.app.openExamTemplateModal()">
              📥 Charger un Modèle Officiel
            </button>
          </div>
        `;
        return;
      }

      container.innerHTML = '';
      exams.forEach(ex => {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.justifyContent = 'space-between';

        const assignedPills = (ex.assigned_groups || []).map(g => `<span class="badge" style="background:rgba(59,130,246,0.15); color:#93c5fd; border:1px solid #3b82f6; font-size:0.75rem; padding:2px 8px; border-radius:10px;">${g}</span>`).join(' ') || '<span style="color:var(--text-muted); font-size:0.75rem;">Tous</span>';

        card.innerHTML = `
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
              <span class="user-tag" style="background:rgba(59,130,246,0.12); color:#60a5fa; border-color:#3b82f6;">${ex.module_code}</span>
              <span class="badge" style="background:rgba(16,185,129,0.15); color:#6ee7b7; border:1px solid #10b981; font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:700;">🟢 Prêt</span>
            </div>
            <h4 style="color:var(--text-primary); font-size:1.05rem; margin-bottom:8px; line-height:1.3;">${this._escapeHtml(ex.title)}</h4>
            <div style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:12px; line-height:1.5;">
              <div>⏱️ Durée : <strong>${ex.duration_minutes} min</strong> | 🎯 Barème : <strong>${ex.global_points} pts</strong></div>
              <div>❓ Questions : <strong>${ex.question_count}</strong></div>
              <div style="margin-top:6px;">👥 Cible : ${assignedPills}</div>
            </div>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px; margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
            <div style="display:flex; gap:6px;">
              <button class="btn btn-primary btn-open-proctor" data-exam-id="${ex.id}" style="flex:1; font-size:0.83rem; padding:8px 10px; display:inline-flex; align-items:center; justify-content:center; gap:5px;">
                <span>👁️</span> Surveiller & Lancer
              </button>
              <button class="btn btn-secondary btn-exam-item-analysis" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}" data-exam-module="${ex.module_code}" style="font-size:0.83rem; padding:8px 10px; display:inline-flex; align-items:center; justify-content:center; gap:5px; background:rgba(16,185,129,0.15); border-color:#10b981; color:#6ee7b7;" title="Analyse psychométrique & discrimination">
                <span>📊</span> Psychométrie
              </button>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary btn-exam-manage-questions" data-exam-id="${ex.id}" data-exam-title="${this._escapeHtml(ex.title)}" style="flex:1; font-size:0.80rem; padding:6px 8px; display:inline-flex; align-items:center; justify-content:center; gap:4px;">
                <span>📝</span> Questions (${ex.question_count})
              </button>
              <button class="btn btn-secondary btn-exam-export-package" data-exam-id="${ex.id}" data-exam-module="${ex.module_code}" style="font-size:0.80rem; padding:6px 8px; display:inline-flex; align-items:center; justify-content:center; gap:4px; background:rgba(99,102,241,0.15); border-color:#6366f1; color:#a5b4fc;" title="Exporter Package .exam.zip pour transfert USB">
                <span>📦</span> Package (.exam.zip)
              </button>
            </div>
          </div>
        `;
        container.appendChild(card);
      });

      // Bind actions on exam cards
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

      container.querySelectorAll('.btn-exam-export-package').forEach(btn => {
        btn.onclick = async () => {
          const examId = btn.getAttribute('data-exam-id');
          const moduleCode = btn.getAttribute('data-exam-module');
          try {
            await api.exportExamPackage(examId, `examen_${moduleCode}_${examId}.exam.zip`);
          } catch (e) {
            alert(`Erreur d'exportation du package : ${e.message}`);
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
            alert(`✅ Examen officiel "${res.title}" chargé avec succès (${res.question_count} questions) ! Il est prêt.`);
            this.closeModal('modal-exam-template-picker');
            this.renderTeacherView();
          } catch (err) {
            alert(`Erreur de chargement du modèle : ${err.message}`);
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

      this.switchView('view-proctor-live');
      await this.initProctorMonitoringLive(sessionId);
    } catch (err) {
      alert(`Erreur d'ouverture de la session de surveillance : ${err.message}`);
    }
  }

  async initProctorMonitoringLive(sessionId) {
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
        this.renderTeacherView();
      };
    }

    const launchAllBtn = document.getElementById('btn-proctor-launch-all');
    if (launchAllBtn) {
      launchAllBtn.onclick = async () => {
        if (confirm("Lancer l'épreuve synchronisée pour tous les candidats connectés dans la salle ?")) {
          try {
            await api.launchProctorSession(sessionId);
            this._logProctorFeed("🚀 Lancement synchronisé de l'épreuve déclenché par le surveillant.");
            await this.refreshProctorOverview(sessionId);
          } catch (err) {
            alert(`Erreur lors du lancement synchronisé : ${err.message}`);
          }
        }
      };
    }

    const closeAllBtn = document.getElementById('btn-proctor-close-all');
    if (closeAllBtn) {
      closeAllBtn.onclick = async () => {
        if (confirm("🛑 Clôturer définitivement l'épreuve pour toute la salle ?\nToutes les copies actives seront immédiatement soumises et scellées.")) {
          try {
            await api.closeExamSession(sessionId);
            this._logProctorFeed("🛑 Clôture collective de l'épreuve par le surveillant : toutes les copies scellées.");
            await this.refreshProctorOverview(sessionId);
            alert("✅ L'épreuve a été clôturée avec succès. Toutes les copies actives ont été soumises et scellées.");
          } catch (err) {
            alert(`Erreur lors de la clôture : ${err.message}`);
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
          alert(`Erreur : ${err.message}`);
        }
      };
    }

    const refreshBtn = document.getElementById('btn-proctor-refresh');
    if (refreshBtn) {
      refreshBtn.onclick = () => this.refreshProctorOverview(sessionId);
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
    }, 1000);
  }

  async refreshProctorOverview(sessionId) {
    try {
      const data = await api.getProctorSessionOverview(sessionId);
      this._renderProctorOverviewData(data, sessionId);
    } catch (err) {
      console.error("Échec de rafraîchissement proctor :", err);
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

  _renderProctorOverviewData(data, sessionId) {
    const titleEl = document.getElementById('proctor-exam-title');
    if (titleEl) titleEl.textContent = data.exam_title;
    const roomEl = document.getElementById('proctor-room-id');
    if (roomEl) roomEl.textContent = data.room_id;
    const durEl = document.getElementById('proctor-duration');
    if (durEl) durEl.textContent = `${data.duration_minutes} min`;
    const enrEl = document.getElementById('proctor-enrolled-count');
    if (enrEl) enrEl.textContent = data.total_enrolled;

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

    const launchBtn = document.getElementById('btn-proctor-launch-all');
    if (launchBtn) {
      launchBtn.style.display = data.status === 'in_progress' ? 'none' : 'inline-block';
    }

    const tableBody = document.getElementById('proctor-students-table-body');
    const cardsContainer = document.getElementById('proctor-students-grid');
    if (!tableBody && !cardsContainer) return;

    const cards = data.student_cards || [];
    const connectedCount = cards.filter(c => c.status !== 'not_entered').length;
    const statsSummary = document.getElementById('proctor-stats-summary');
    if (statsSummary) statsSummary.textContent = `${connectedCount} / ${cards.length} postes actifs`;

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
          <td style="padding:12px 16px; font-family:var(--font-mono); font-size:0.88rem; color:#93c5fd;">
            ${timeText}
          </td>
          <td style="padding:12px 16px;">
            ${c.suspension_count > 0 ? `
              <span class="user-tag" style="background:rgba(239,68,68,0.15); color:#fca5a5; border-color:rgba(239,68,68,0.3); font-weight:600; font-size:0.78rem;">
                ⚠️ ${c.suspension_count} avert.
              </span>
              ${c.suspension_reason ? `<div style="font-size:0.75rem; color:#f87171; margin-top:2px; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${this._escapeHtml(c.suspension_reason)}">${this._escapeHtml(c.suspension_reason)}</div>` : ''}
            ` : '<span style="color:var(--text-muted); font-size:0.8rem;">0 alerte</span>'}
          </td>
          <td style="padding:12px 16px; font-size:0.8rem; color:var(--text-muted); font-family:var(--font-mono);">
            ${c.status === 'in_progress' ? '<span style="color:#10b981;">● En direct</span>' : (c.status === 'submitted' ? 'Terminé' : 'En attente')}
          </td>
          <td style="padding:12px 16px; text-align:right;">
            <div style="display:inline-flex; gap:6px; justify-content:flex-end;">
              ${c.status === 'suspended' && c.attempt_id ? `
                <button class="btn btn-primary btn-card-unlock" data-att="${c.attempt_id}" style="padding:4px 8px; font-size:0.78rem; background:#10b981;">
                  🔓 Débloquer
                </button>
              ` : ''}
              ${(c.status === 'in_progress' || c.status === 'suspended') && c.attempt_id ? `
                <button class="btn btn-secondary btn-card-force-submit" data-att="${c.attempt_id}" data-name="${this._escapeHtml(c.student_name)}" style="padding:4px 8px; font-size:0.78rem; color:#f87171; border-color:rgba(239,68,68,0.3);">
                  🛑 Forcer
                </button>
              ` : ''}
              ${c.status === 'in_progress' ? `
                <button class="btn btn-secondary btn-card-extend" data-sid="${c.student_id}" style="padding:4px 8px; font-size:0.78rem;">
                  +5m
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
            alert(`Erreur de déblocage : ${err.message}`);
          }
        };
      });

      tableBody.querySelectorAll('.btn-card-force-submit').forEach(btn => {
        btn.onclick = async () => {
          const attId = btn.getAttribute('data-att');
          const stName = btn.getAttribute('data-name');
          if (confirm(`Forcer immédiatement la soumission de l'épreuve pour ${stName} ?`)) {
            try {
              const res = await api.forceSubmitAttempt(sessionId, attId);
              this._logProctorFeed(`🛑 Épreuve de ${stName} soumise de force. Note : ${res.final_mark}/20.`);
              await this.refreshProctorOverview(sessionId);
            } catch (err) {
              alert(`Erreur : ${err.message}`);
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
            alert(`Erreur : ${err.message}`);
          }
        };
      });
    }

    if (data.recent_audit_logs && data.recent_audit_logs.length) {
      const feed = document.getElementById('proctor-live-feed');
      if (feed && !feed.hasChildNodes()) {
        data.recent_audit_logs.forEach(l => {
          this._logProctorFeed(`[${new Date(l.timestamp).toLocaleTimeString('fr-FR')}] [${l.event_type}] ${JSON.stringify(l.details)}`);
        });
      }
    }
  }

  _handleProctorWebSocketMessage(msg, sessionId) {
    const timeStr = new Date().toLocaleTimeString('fr-FR');
    if (msg.type === 'STUDENT_UNLOCKED') {
      this._logProctorFeed(`[${timeStr}] 🔓 Étudiant débloqué.`);
    } else if (msg.type === 'STUDENT_SUBMITTED') {
      this._logProctorFeed(`[${timeStr}] ✅ Épreuve soumise par ${msg.student_id}. Note : ${msg.final_mark}/20.`);
    } else if (msg.type === 'SECURITY_EVENT') {
      this._logProctorFeed(`[${timeStr}] ⚠️ Alerte sécurité : ${msg.event_type || 'Avertissement'} sur le poste ${msg.student_id}.`);
    } else {
      this._logProctorFeed(`[${timeStr}] 📡 Événement [${msg.type || 'TELEMETRY'}] reçu.`);
    }
    this.refreshProctorOverview(sessionId);
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

    // Générateur de mot de passe en clair pour l'admin
    const btnGenPwd = document.getElementById('btn-admin-student-gen-pwd');
    if (btnGenPwd) {
      btnGenPwd.onclick = () => {
        const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%";
        let pwd = "";
        for (let i = 0; i < 10; i++) pwd += chars.charAt(Math.floor(Math.random() * chars.length));
        const inputPwd = document.getElementById('admin-student-password');
        if (inputPwd) inputPwd.value = pwd;
      };
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
          alert(`Erreur d'exportation ZIP PDF : ${e.message}`);
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
          alert(`Erreur d'exportation ZIP Word : ${e.message}`);
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
          alert(`Erreur d'exportation Palmarès PDF : ${e.message}`);
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
          alert(`Erreur d'exportation Palmarès Word : ${e.message}`);
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
          alert(`Erreur téléchargement PDF : ${e.message}`);
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
          alert(`Erreur téléchargement Word : ${e.message}`);
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
        const password = document.getElementById('admin-student-password').value || undefined;

        try {
          if (mode === 'create') {
            await api.createUser({
              id,
              username,
              full_name,
              email,
              group_id,
              password,
              role: 'student'
            });
            alert(`✅ Étudiant "${full_name}" créé avec succès.`);
          } else {
            await api.updateUser(id, {
              full_name,
              email,
              group_id,
              password: password || undefined
            });
            alert(`✅ Étudiant "${full_name}" mis à jour.`);
          }
          this.closeModal('modal-admin-student');
          await this.loadAdminStudents();
          this.loadAdminOverview();
        } catch (err) {
          alert(`Erreur : ${err.message}`);
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
              id,
              username,
              full_name,
              email,
              password,
              role: 'teacher'
            });
            alert(`✅ Enseignant "${full_name}" créé avec succès.`);
          } else {
            await api.updateUser(id, {
              full_name,
              email
            });
            alert(`✅ Enseignant "${full_name}" mis à jour.`);
          }
          this.closeModal('modal-admin-teacher');
          await this.loadAdminTeachers();
          this.loadAdminOverview();
        } catch (err) {
          alert(`Erreur : ${err.message}`);
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
            alert(`✅ Module "${code} - ${title}" créé avec succès.`);
          } else {
            await api.updateModule(code, { title, description });
            alert(`✅ Module "${code}" mis à jour.`);
          }
          this.closeModal('modal-admin-module');
          await this.loadAdminModules();
          this.loadAdminOverview();
        } catch (err) {
          alert(`Erreur : ${err.message}`);
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
          alert(`Erreur d'affectation : ${err.message}`);
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
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des étudiants...</td></tr>';
    try {
      const [students, groups] = await Promise.all([
        api.listUsers('student'),
        api.listGroups()
      ]);
      this._adminStudentsList = students;
      this._adminGroupsList = groups;

      const filterGroup = document.getElementById('admin-students-filter-group');
      const modalGroup = document.getElementById('admin-student-group');
      if (filterGroup) {
        const cur = filterGroup.value;
        filterGroup.innerHTML = '<option value="">Toutes les Spécialités</option>' + groups.map(g => `<option value="${g.id}">${g.name || g.id}</option>`).join('');
        filterGroup.value = cur;
      }
      if (modalGroup) {
        modalGroup.innerHTML = groups.map(g => `<option value="${g.id}">${g.name || g.id}</option>`).join('');
      }

      this._renderAdminStudentsRows();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;
    }
  }

  _renderAdminStudentsRows() {
    const tbody = document.getElementById('admin-students-table-body');
    if (!tbody) return;
    const filterGroupVal = document.getElementById('admin-students-filter-group')?.value || '';
    const searchVal = (document.getElementById('admin-students-search')?.value || '').toLowerCase().trim();

    let list = this._adminStudentsList || [];
    if (filterGroupVal) {
      list = list.filter(s => s.group_id === filterGroupVal);
    }
    if (searchVal) {
      list = list.filter(s =>
        (s.id && s.id.toLowerCase().includes(searchVal)) ||
        (s.username && s.username.toLowerCase().includes(searchVal)) ||
        (s.full_name && s.full_name.toLowerCase().includes(searchVal)) ||
        (s.email && s.email.toLowerCase().includes(searchVal))
      );
    }

    const countEl = document.getElementById('admin-students-count');
    if (countEl) countEl.textContent = `${list.length} étudiant(s) affiché(s) (${(this._adminStudentsList || []).length} total)`;

    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun étudiant ne correspond aux critères.</td></tr>';
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
        if (confirm(`Confirmez-vous la suppression définitive de l'étudiant "${name}" (${id}) ?`)) {
          try {
            await api.deleteUser(id);
            alert("Étudiant supprimé avec succès.");
            await this.loadAdminStudents();
            this.loadAdminOverview();
          } catch (e) {
            alert(`Erreur de suppression : ${e.message}`);
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
    const passInput = document.getElementById('admin-student-password');

    modeInput.value = mode;
    if (mode === 'edit' && data) {
      title.textContent = `✏️ Modifier l'Étudiant ${data.username}`;
      idInput.value = data.id;
      idInput.disabled = true;
      userInput.value = data.username;
      userInput.disabled = true;
      nameInput.value = data.full_name || '';
      emailInput.value = data.email || '';
      groupSelect.value = data.group_id || '';
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
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des enseignants...</td></tr>';
    try {
      const teachers = await api.listUsers('teacher');
      this._adminTeachersList = teachers;

      const countEl = document.getElementById('admin-teachers-count');
      if (countEl) countEl.textContent = `${teachers.length} enseignant(s) au total`;

      if (teachers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun enseignant enregistré.</td></tr>';
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
          if (confirm(`Confirmez-vous la suppression de l'enseignant "${name}" (${id}) ?`)) {
            try {
              await api.deleteUser(id);
              alert("Enseignant supprimé avec succès.");
              await this.loadAdminTeachers();
              this.loadAdminOverview();
            } catch (e) {
              alert(`Erreur de suppression : ${e.message}`);
            }
          }
        };
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--danger);">Erreur : ${err.message}</td></tr>`;
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
      userInput.disabled = true;
      nameInput.value = data.full_name || '';
      emailInput.value = data.email || '';
      passInput.placeholder = "(Inchangé)";
      passInput.disabled = true;
    } else {
      title.textContent = '➕ Nouvel Enseignant';
      idInput.value = '';
      idInput.disabled = false;
      userInput.value = '';
      userInput.disabled = false;
      nameInput.value = '';
      emailInput.value = '';
      passInput.placeholder = "••••••••";
      passInput.disabled = false;
    }
    modal.classList.add('active');
  }

  // --- Tab 4 : Gestion des Modules Académiques (CRUD REV-39) ---
  async loadAdminModules() {
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
          ? m.teachers.map(t => `<span class="badge" style="background:rgba(167,139,250,0.15); color:#a78bfa; font-size:0.75rem; padding:2px 8px; border-radius:10px; margin-right:4px;">${this._escapeHtml(t.full_name)}</span>`).join('')
          : '<span style="color:var(--text-muted); font-size:0.8rem;">Aucun</span>';

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
          if (confirm(`Confirmez-vous la suppression définitive du module "${title}" (${code}) ?`)) {
            try {
              await api.deleteModule(code);
              alert("Module supprimé avec succès.");
              await this.loadAdminModules();
              this.loadAdminOverview();
            } catch (e) {
              alert(`Erreur de suppression : ${e.message}`);
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
      const assignedIds = new Set(assignedTeachers.map(t => t.id));
      const unassignedTeachers = allTeachers.filter(t => !assignedIds.has(t.id));

      const selectEl = document.getElementById('admin-assign-teacher-select');
      if (selectEl) {
        if (unassignedTeachers.length === 0) {
          selectEl.innerHTML = '<option value="">Tous les enseignants sont déjà affectés</option>';
        } else {
          selectEl.innerHTML = unassignedTeachers.map(t => `<option value="${t.id}">${t.full_name} (@${t.username})</option>`).join('');
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
            row.innerHTML = `
              <div>
                <strong>${this._escapeHtml(t.full_name)}</strong>
                <span style="font-size:0.8rem; color:var(--text-muted); margin-left:8px;">@${this._escapeHtml(t.username)} (${this._escapeHtml(t.id)})</span>
              </div>
              <button class="btn btn-danger btn-admin-remove-teacher-mod" data-tid="${t.id}" style="padding:3px 8px; font-size:0.75rem;">❌ Retirer</button>
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
                alert(`Erreur de retrait : ${err.message}`);
              }
            };
          });
        }
      }

      modal.classList.add('active');
    } catch (err) {
      alert(`Erreur lors du chargement des affectations : ${err.message}`);
    }
  }

  // --- Tab 5 : Gestion des Examens & Épreuves (CRUD REV-39) ---
  async loadAdminExams() {
    const tbody = document.getElementById('admin-exams-table-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">Chargement des examens...</td></tr>';
    try {
      const exams = await api.request('/exams');
      this._adminExamsList = exams;

      const countEl = document.getElementById('admin-exams-count');
      if (countEl) countEl.textContent = `${exams.length} examen(s) programmé(s)`;

      if (exams.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Aucun examen créé pour le moment.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      exams.forEach(ex => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--card-border)';
        tr.innerHTML = `
          <td style="padding:10px 14px; font-family:monospace; font-size:0.8rem; color:var(--text-muted);">${this._escapeHtml(ex.id)}</td>
          <td style="padding:10px 14px; font-weight:600; color:var(--text-primary);">${this._escapeHtml(ex.title)}</td>
          <td style="padding:10px 14px;"><span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8; font-size:0.78rem; padding:2px 8px; border-radius:10px;">${this._escapeHtml(ex.module_code)}</span></td>
          <td style="padding:10px 14px; font-size:0.85rem;">${ex.duration_minutes} min</td>
          <td style="padding:10px 14px; font-size:0.85rem; font-weight:600;">/ ${ex.global_points}</td>
          <td style="padding:10px 14px; font-size:0.85rem;">${ex.questions ? ex.questions.length : (ex.question_count || '—')} quest.</td>
          <td style="padding:10px 14px; text-align:center;">
            <div style="display:inline-flex; gap:6px; flex-wrap:wrap; justify-content:center;">
              <button class="btn btn-primary btn-admin-proctor-exam" data-id="${ex.id}" style="padding:4px 8px; font-size:0.78rem;">🖥️ Surveiller</button>
              <button class="btn btn-secondary btn-admin-analysis-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}" data-module="${ex.module_code}" style="padding:4px 8px; font-size:0.78rem; background:rgba(16,185,129,0.15); border-color:#10b981; color:#6ee7b7;" title="Analyse psychométrique & discrimination">📊</button>
              <button class="btn btn-secondary btn-admin-questions-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}" style="padding:4px 8px; font-size:0.78rem;" title="Gérer les questions">📝</button>
              <button class="btn btn-secondary btn-admin-export-pkg-exam" data-id="${ex.id}" data-module="${ex.module_code}" style="padding:4px 8px; font-size:0.78rem; background:rgba(99,102,241,0.15); border-color:#6366f1; color:#a5b4fc;" title="Exporter Package .exam.zip pour transfert USB">📦</button>
              <button class="btn btn-danger btn-admin-delete-exam" data-id="${ex.id}" data-title="${this._escapeHtml(ex.title)}" style="padding:4px 8px; font-size:0.78rem;">🗑️</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
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

      tbody.querySelectorAll('.btn-admin-export-pkg-exam').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const moduleCode = btn.getAttribute('data-module');
          try {
            await api.exportExamPackage(id, `examen_${moduleCode}_${id}.exam.zip`);
          } catch (e) {
            alert(`Erreur d'exportation du package : ${e.message}`);
          }
        };
      });

      tbody.querySelectorAll('.btn-admin-delete-exam').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const title = btn.getAttribute('data-title');
          if (confirm(`Confirmez-vous la suppression de l'examen "${title}" ?\nToutes les sessions et questions associées seront supprimées.`)) {
            try {
              await api.deleteExam(id);
              alert("Examen supprimé avec succès.");
              await this.loadAdminExams();
              this.loadAdminOverview();
            } catch (e) {
              alert(`Erreur de suppression : ${e.message}`);
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
    // Nettoie les en-têtes préfixés du type **[...]** ou [...] (REV-21)
    let clean = String(text).replace(/^(\*\*\[(.*?)\]\*\*|\[(.*?)\])\s*/, '');
    const codeBlocks = [];
    let processed = clean.replace(/```(?:[a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g, (match, code) => {
      const id = `___CODEBLOCK_${codeBlocks.length}___`;
      codeBlocks.push(`<pre class="code-block"><code>${this._escapeHtml(code)}</code></pre>`);
      return id;
    });

    const inlineCodes = [];
    processed = processed.replace(/`([^`]+)`/g, (match, code) => {
      const id = `___INLINECODE_${inlineCodes.length}___`;
      inlineCodes.push(`<code>${this._escapeHtml(code)}</code>`);
      return id;
    });

    processed = this._escapeHtml(processed);

    processed = processed.replace(/^### (.*$)/gim, '<h4 style="color:#93c5fd; margin:10px 0 6px 0; font-size:1.05rem;">$1</h4>');
    processed = processed.replace(/^## (.*$)/gim, '<h3 style="color:#60a5fa; margin:12px 0 8px 0; font-size:1.15rem;">$1</h3>');
    processed = processed.replace(/^# (.*$)/gim, '<h2 style="color:#3b82f6; margin:14px 0 10px 0; font-size:1.25rem;">$1</h2>');

    processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary);">$1</strong>');
    processed = processed.replace(/\*(.*?)\*/g, '<em style="color:#cbd5e1;">$1</em>');

    const paragraphs = processed.split(/\n\s*\n/);
    processed = paragraphs.map(p => {
      const trimmed = p.trim();
      if (!trimmed) return '';
      if (trimmed.startsWith('<h') || trimmed.startsWith('___CODEBLOCK_')) {
        return trimmed;
      }
      return `<p style="margin-bottom:8px; line-height:1.55;">${trimmed.replace(/\n/g, '<br>')}</p>`;
    }).filter(Boolean).join('');

    codeBlocks.forEach((block, idx) => {
      processed = processed.replace(`___CODEBLOCK_${idx}___`, block);
    });
    inlineCodes.forEach((code, idx) => {
      processed = processed.replace(`___INLINECODE_${idx}___`, code);
    });

    return processed;
  }

  toggleFullscreen() {
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
    btn.innerHTML = isFull ? '<span>✖️</span> Quitter Plein Écran' : '<span>⛶</span> Plein Écran';
  }

  renderStudentDashboard() {
    return this.renderDashboard(this.currentUser);
  }

  requestFullscreen() {
    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(() => {});
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
      }
    }
  }

  exitFullscreen() {
    if (document.fullscreenElement || document.webkitFullscreenElement) {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      }
    }
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
          alert(`Erreur téléchargement PDF : ${e.message}`);
        }
      };
    });
    tbody.querySelectorAll('.btn-download-bulletin-docx').forEach(btn => {
      btn.onclick = async () => {
        try {
          await api.downloadStudentBulletinDocx(btn.getAttribute('data-id'));
        } catch (e) {
          alert(`Erreur téléchargement Word : ${e.message}`);
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
      alert(`Erreur d'exportation : ${err.message}`);
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
          if (confirm("Confirmez-vous la suppression de cette question ?")) {
            try {
              await api.deleteQuestion(examId, qId);
              alert("Question supprimée avec succès.");
              await this.openManageQuestionsModal(examId, this._currentManageExamTitle);
              if (this.currentUser && this.currentUser.role === 'admin') {
                await this.loadAdminExams();
              } else {
                await this.renderTeacherView();
              }
            } catch (err) {
              alert(`Erreur de suppression : ${err.message}`);
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
      if (titleEl) titleEl.textContent = "➕ Ajouter une Question";
      if (inputQId) inputQId.value = "";
      if (selectType) selectType.value = "single_choice";
      const nextOrdering = (this._currentExamQuestions ? this._currentExamQuestions.length + 1 : 1);
      if (inputOrdering) inputOrdering.value = nextOrdering;
      if (textareaPrompt) textareaPrompt.value = "";
      if (inputPoints) inputPoints.value = 2.0;
      if (inputPenalty) inputPenalty.value = 0.5;

      this._renderDynamicQuestionOptionsForm("single_choice", null, null);
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
    }

    return { options_json: "[]", correct_answers_json: "[]" };
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

// Initialisation au chargement du DOM
window.addEventListener('DOMContentLoaded', () => {
  const app = new AppController();
  app.init();
});
