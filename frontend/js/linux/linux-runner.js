/**
 * Linux Training Center Coordinator (Linux Runner)
 * 
 * Coordonne l'ensemble de l'expérience d'apprentissage Linux (#view-linux) :
 * - Hub d'accueil avec bascule fluide entre les deux voies d'apprentissage :
 *   1. Volet Théorique (Concepts & Administration Système) : Quiz QCM interactifs et explications.
 *   2. Volet Pratique (Atelier Terminal & Défis Ligne de Commande) : Atelier 2 volets homogène.
 * - Atelier 2 volets :
 *   - Volet gauche : Consignes, badges de difficulté/points, sélecteur de défis, indices.
 *   - Volet droit : Éditeur de commandes, Terminal interactif VFS, onglet de validation des tests.
 * - Actions d'évaluation :
 *   - Exécuter la commande (live dans le terminal)
 *   - Tester sur les cas publics (retour instantané)
 *   - Soumettre le défi (évaluation complète public + cachés avec masquage, appel API backend)
 * - Bouton de retour universel : "Retourner au Centre d'Entraînement Linux ➔"
 */

import { VirtualFS } from './vfs.js';
import { ShellEngine } from './shell-engine.js';
import { TerminalUI } from './terminal-ui.js';
import { LinuxChallengeEvaluator } from './linux-evaluator.js';
import { api } from '../api.js';

export class LinuxRunner {
  /**
   * @param {Object} options
   * @param {Object} [options.app] - Référence au contrôleur global AppController
   * @param {Object} [options.api] - Client API
   * @param {HTMLElement|string} [options.container] - Sélecteur ou élément DOM conteneur
   */
  constructor(options = {}) {
    this.app = options.app || window.app;
    this.api = options.api || api;
    this.container = null;

    // État courant
    this.currentMode = 'practical'; // 'practical' | 'theoretical'
    this.currentView = 'hub'; // 'hub' | 'practical_workshop' | 'theory_quiz'

    // Données en mémoire
    this.curriculum = null;
    this.progression = null;
    this.challenges = [];
    this.selectedLevel = null;
    this.activeChallenge = null;
    this.activeChallengeIndex = 0;

    // Volet théorique
    this.theoryQuizzes = [];
    this.currentQuizIndex = 0;
    this.theoryScore = 0;
    this.theoryAnswers = [];

    // Moteurs Linux actifs pour l'atelier pratique
    this.activeVFS = null;
    this.activeShellEngine = null;
    this.activeTerminalUI = null;

    if (options.container) {
      this.bindContainer(options.container);
    }
  }

  /**
   * Lie le conteneur DOM
   * @param {HTMLElement|string} container
   */
  bindContainer(container) {
    if (typeof container === 'string') {
      this.container = document.querySelector(container);
    } else {
      this.container = container;
    }
  }

  /**
   * Point d'entrée principal : Rendu du Centre d'Entraînement Linux
   */
  async render() {
    if (!this.container) {
      this.container = document.getElementById('view-linux');
    }
    if (!this.container) return;

    if (this.currentView === 'practical_workshop' && this.activeChallenge) {
      this.renderPracticalWorkshop();
    } else if (this.currentView === 'theory_quiz' && this.theoryQuizzes.length > 0) {
      this.renderTheoryQuizStep();
    } else {
      await this.renderHub();
    }
  }

  // =========================================================================
  // 1. HUB CENTRAL DU CENTRE LINUX
  // =========================================================================

  /**
   * Affiche le tableau de bord du centre Linux avec la sélection de mode
   */
  async renderHub() {
    this.currentView = 'hub';
    if (!this.container) return;

    // Chargement parallèle des métadonnées
    let progData = { level: 1, pillar_title: 'Administration Linux', average_score: 0, total_attempts: 0 };
    let chaptersData = [];
    let challengesList = [];

    try {
      const [prog, chaptersRes, challengesRes] = await Promise.all([
        this.api.getLinuxProgression().catch(() => progData),
        this.api.getLinuxChapters().catch(() => []),
        this.api.getLinuxChallenges(this.selectedLevel).catch(() => [])
      ]);
      this.progression = prog || progData;
      this.curriculum = Array.isArray(chaptersRes) ? chaptersRes : ((chaptersRes && chaptersRes.chapters) || []);
      this.challenges = Array.isArray(challengesRes) ? challengesRes : [];
    } catch (err) {
      console.warn("Erreur chargement hub Linux:", err);
    }

    const prog = this.progression || progData;
    const chapters = Array.isArray(this.curriculum) ? this.curriculum : ((this.curriculum && this.curriculum.chapters) || []);

    this.container.innerHTML = `
      <div class="dashboard-container" style="max-width: 1200px; margin: 0 auto; padding: 24px 20px;">
        
        <!-- En-tête Supérieur -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
          <div>
            <h2 style="font-size: 1.6rem; display: flex; align-items: center; gap: 10px; margin: 0 0 6px 0;">
              <span>🐧</span> Centre d'Entraînement Linux <span style="font-size: 0.85rem; padding: 3px 10px; border-radius: 12px; background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3);">POSIX & VFS</span>
            </h2>
            <p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0;">
              Arborescence FHS, permissions, processus, scripting Bash et émulation complète de terminal POSIX dans le navigateur.
            </p>
          </div>
          <button id="btn-linux-hub-back-dash" class="btn btn-secondary" style="display: inline-flex; align-items: center; gap: 8px;">
            ← Revenir au Tableau de Bord
          </button>
        </div>

        <!-- 1. Cartes de Sélection Dual-Track : Pratique vs Théorique -->
        <div class="assessment-type-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px;">
          
          <!-- Carte 1 : Volet Pratique -->
          <div class="type-selection-card ${this.currentMode === 'practical' ? 'active-practical' : ''}" id="card-linux-hub-practical" style="cursor: pointer;">
            <div class="type-card-active-indicator">
              <span class="indicator-dot"></span>
              <span class="indicator-text">${this.currentMode === 'practical' ? '✓ ACTIF' : '○ CHOISIR'}</span>
            </div>
            
            <div class="type-card-icon-wrapper practical" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa;">
              <span class="type-card-big-icon">💻</span>
            </div>
            
            <div class="type-card-body">
              <div class="type-card-header">
                <div>
                  <span class="type-card-badge" style="background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.3);">⚡ Terminal Bash & VFS</span>
                  <h3 class="type-card-title">Volet Pratique (Atelier Terminal)</h3>
                </div>
              </div>
              <p class="type-card-desc">
                Manipulez un véritable système de fichiers Linux virtuel (VFS) dans votre navigateur. Exécution de commandes réelles (ls, grep, pipes, chmod), tests automatiques et validation instantanée.
              </p>
              <div class="type-card-meta">
                <span class="type-card-meta-pill">🐧 100% Client / Shell POSIX</span>
                <span class="type-card-meta-pill">🧪 Tests unitaires & side-effects</span>
                <span class="type-card-meta-pill">💡 Historique & Autocomplétion Tab</span>
              </div>
            </div>
          </div>

          <!-- Carte 2 : Volet Théorique -->
          <div class="type-selection-card ${this.currentMode === 'theoretical' ? 'active' : ''}" id="card-linux-hub-theoretical" style="cursor: pointer;">
            <div class="type-card-active-indicator">
              <span class="indicator-dot"></span>
              <span class="indicator-text">${this.currentMode === 'theoretical' ? '✓ ACTIF' : '○ CHOISIR'}</span>
            </div>
            
            <div class="type-card-icon-wrapper theoretical" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">
              <span class="type-card-big-icon">📖</span>
            </div>
            
            <div class="type-card-body">
              <div class="type-card-header">
                <div>
                  <span class="type-card-badge" style="background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3);">⏱️ Concepts & Administration</span>
                  <h3 class="type-card-title">Volet Théorique (Quiz & Connaissances)</h3>
                </div>
              </div>
              <p class="type-card-desc">
                Questions d'évaluation sur les concepts clés de Linux : arborescence FHS, droits d'accès, signaux de processus, variables d'environnement et syntaxe Bash.
              </p>
              <div class="type-card-meta">
                <span class="type-card-meta-pill">📚 Questions interactives QCM / Texte</span>
                <span class="type-card-meta-pill">⏱️ Évaluation immédiate</span>
                <span class="type-card-meta-pill">🎯 Barème instantané</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. Synthèse du Pilier Académique LINUX_ADMIN -->
        <div class="card" style="margin-bottom: 28px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.08); background: var(--bg-surface); border-radius: var(--radius-md);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <span style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:#60a5fa; letter-spacing:0.05em;">Pilier Académique LINUX_ADMIN (Découplé GPA)</span>
              <h3 style="margin:4px 0 0 0; font-size:1.25rem;">Niveau ${prog.level || 1} — ${prog.pillar_title || 'Administration Linux'}</h3>
            </div>
            <div style="display:flex; gap:20px; align-items:center;">
              <div style="text-align:right;">
                <div style="font-size:0.8rem; color:var(--text-muted);">Moyenne Pratique</div>
                <div style="font-size:1.4rem; font-weight:800; color:#10b981;">${typeof prog.average_score === 'number' ? prog.average_score.toFixed(1) : '0.0'} / 20</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:0.8rem; color:var(--text-muted);">Tentatives Enregistrées</div>
                <div style="font-size:1.4rem; font-weight:800; color:#60a5fa;">${prog.total_attempts || 0}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Zone de Contenu Dynamique selon le Volet Sélectionné -->
        <div id="linux-hub-dynamic-section">
          ${this.currentMode === 'practical' ? this._renderPracticalSectionHtml() : this._renderTheoreticalSectionHtml(chapters)}
        </div>

      </div>
    `;

    this._attachHubEvents();
  }

  /**
   * Génère le HTML pour la section Pratique (Filtres de niveau + Grille des défis)
   * @private
   */
  _renderPracticalSectionHtml() {
    const levels = [
      { id: null, label: 'Tous les niveaux' },
      { id: 1, label: 'Niveau 1 : Navigation & Fichiers' },
      { id: 2, label: 'Niveau 2 : Permissions & Filtrage' },
      { id: 3, label: 'Niveau 3 : Scripts & Tubes' },
      { id: 4, label: 'Niveau 4 : SysAdmin & Processus' }
    ];

    const filterButtons = levels.map(l => `
      <button class="btn btn-sm ${this.selectedLevel === l.id ? 'btn-primary' : 'btn-secondary'} btn-filter-level" data-level="${l.id === null ? '' : l.id}" style="font-size:0.82rem; padding:5px 12px; border-radius:14px;">
        ${l.label}
      </button>
    `).join('');

    let challengesCards = '';
    if (this.challenges.length === 0) {
      challengesCards = `
        <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: var(--text-muted); background: rgba(255, 255, 255, 0.02); border-radius: 8px;">
          <p>Aucun défi pratique trouvé pour ce niveau.</p>
        </div>
      `;
    } else {
      challengesCards = this.challenges.map((ch, idx) => {
        let statusBadge = '<span class="badge" style="background:rgba(255,255,255,0.08); color:var(--text-muted);">○ Non résolu</span>';
        if (ch.status === 'solved') {
          statusBadge = '<span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3);">✓ Résolu</span>';
        } else if (ch.status === 'in_progress') {
          statusBadge = '<span class="badge" style="background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);">⏳ En cours</span>';
        }

        const diffColors = {
          easy: '#34d399',
          medium: '#fbbf24',
          hard: '#f87171'
        };
        const diffColor = diffColors[ch.difficulty] || '#60a5fa';

        return `
          <div class="card challenge-item-card" data-ch-id="${ch.id}" style="padding: 18px; display: flex; flex-direction: column; justify-content: space-between; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: var(--bg-surface); transition: transform 0.15s, border-color 0.15s;">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="user-tag" style="background:rgba(59,130,246,0.15); color:#93c5fd; font-weight:700; font-size:0.75rem;">
                  Niveau ${ch.level || 1} • ${ch.topic || 'Linux'}
                </span>
                ${statusBadge}
              </div>
              <h4 style="margin: 0 0 6px 0; font-size: 1.05rem; color: var(--text-primary);">${this._escapeHtml(ch.title)}</h4>
              <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.45; margin: 0 0 14px 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                ${this._escapeHtml((ch.description || '').replace(/###/g, '').replace(/####/g, ''))}
              </p>
            </div>
            
            <div style="padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center;">
              <div style="display: flex; gap: 8px; align-items: center; font-size: 0.8rem;">
                <span style="color: ${diffColor}; font-weight: 600;">● ${ch.difficulty || 'Moyen'}</span>
                <span style="color: var(--text-muted);">•</span>
                <span style="color: #60a5fa; font-weight: 700;">${ch.points || 2.0} pts</span>
              </div>
              <button class="btn btn-primary btn-launch-challenge" data-ch-id="${ch.id}" style="padding: 5px 14px; font-size: 0.82rem; font-weight: 600;">
                Lancer l'Atelier ➔
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
        <h3 style="font-size:1.2rem; display:flex; align-items:center; gap:8px; margin:0;">
          <span>💻</span> Défis Pratiques Ligne de Commande (${this.challenges.length})
        </h3>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          ${filterButtons}
        </div>
      </div>

      <div class="grid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
        ${challengesCards}
      </div>
    `;
  }

  /**
   * Génère le HTML pour la section Théorique (Liste des chapitres)
   * @private
   */
  _renderTheoreticalSectionHtml(chapters) {
    if (!chapters || chapters.length === 0) {
      return `
        <div style="padding: 40px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border: 1px solid var(--card-border); border-radius: 8px;">
          <p>Chargement des chapitres d'administration Linux...</p>
        </div>
      `;
    }

    const chaptersCards = chapters.map(ch => `
      <div class="card chapter-item-card" data-ch-id="${ch.id}" style="padding: 18px; display: flex; flex-direction: column; justify-content: space-between; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: var(--bg-surface);">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span class="user-tag" style="background:rgba(16,185,129,0.15); color:#6ee7b7; font-weight:700; font-size:0.75rem;">
              Chapitre 0${ch.order || 1}
            </span>
            <span style="font-size:0.78rem; color:var(--text-muted);">
              ${ch.mcq_count || ch.mcq_questions_count || 20} Questions (10 tirées au sort)
            </span>
          </div>
          <h4 style="margin: 0 0 6px 0; font-size: 1.05rem; color: var(--text-primary);">${this._escapeHtml(ch.title)}</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.45; margin: 0 0 14px 0;">
            ${this._escapeHtml(ch.description || '')}
          </p>
        </div>

        <div style="padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.8rem; color: #34d399; font-weight: 600;">📖 Évaluation Théorique</span>
          <button class="btn btn-primary btn-start-theory-chapter" data-ch-id="${ch.id}" style="padding: 5px 14px; font-size: 0.82rem; font-weight: 600; background: #059669; border-color: #059669;">
            Démarrer le Quiz ➔
          </button>
        </div>
      </div>
    `).join('');

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
        <h3 style="font-size:1.2rem; display:flex; align-items:center; gap:8px; margin:0;">
          <span>📖</span> Chapitres Théoriques & Administration (${chapters.length})
        </h3>
        <span style="font-size:0.85rem; color:var(--text-muted);">Testez vos fondamentaux FHS, permissions, signaux et bash</span>
      </div>

      <div class="grid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
        ${chaptersCards}
      </div>
    `;
  }

  /**
   * Attache les écouteurs d'événements du hub
   * @private
   */
  _attachHubEvents() {
    // Bouton retour Dashboard
    const btnBack = document.getElementById('btn-linux-hub-back-dash');
    if (btnBack) {
      btnBack.onclick = () => {
        if (this.app && this.app.renderDashboard) {
          this.app.renderDashboard(this.app.currentUser);
        }
      };
    }

    // Bascule cartes Pratique vs Théorique
    const cardPrac = document.getElementById('card-linux-hub-practical');
    const cardTheo = document.getElementById('card-linux-hub-theoretical');

    if (cardPrac) {
      cardPrac.onclick = () => {
        this.currentMode = 'practical';
        this.renderHub();
      };
    }
    if (cardTheo) {
      cardTheo.onclick = () => {
        this.currentMode = 'theoretical';
        this.renderHub();
      };
    }

    // Filtres de niveau
    const levelBtns = this.container.querySelectorAll('.btn-filter-level');
    levelBtns.forEach(btn => {
      btn.onclick = async () => {
        const lvlStr = btn.getAttribute('data-level');
        this.selectedLevel = lvlStr ? parseInt(lvlStr, 10) : null;
        await this.renderHub();
      };
    });

    // Lancement d'un défi pratique
    const launchBtns = this.container.querySelectorAll('.btn-launch-challenge');
    launchBtns.forEach(btn => {
      btn.onclick = async () => {
        const chId = btn.getAttribute('data-ch-id');
        await this.startPracticalWorkshop(chId);
      };
    });

    // Lancement d'un quiz théorique (Examen unifié avec 10 questions tirées au sort et types riches)
    const startTheoryBtns = this.container.querySelectorAll('.btn-start-theory-chapter');
    startTheoryBtns.forEach(btn => {
      btn.onclick = async () => {
        const chId = btn.getAttribute('data-ch-id');
        if (window.app && window.app.launchLinuxChapterSession) {
          window.app.selectedLinuxMode = 'theoretical';
          await window.app.launchLinuxChapterSession(chId);
        } else {
          await this.startTheoryQuiz(chId);
        }
      };
    });
  }

  // =========================================================================
  // 2. ATELIER PRATIQUE (DISPOSITION HOMOGÈNE 2 VOLETS)
  // =========================================================================

  /**
   * Charge les données du défi et lance l'atelier 2-volets
   * @param {string} challengeId
   */
  async startPracticalWorkshop(challengeId) {
    try {
      let challenge = null;
      if (this.api && this.api.getLinuxChallenge) {
        challenge = await this.api.getLinuxChallenge(challengeId);
      }
      if (!challenge) {
        challenge = this.challenges.find(c => c.id === challengeId);
      }
      if (!challenge) {
        throw new Error(`Défi Linux ${challengeId} introuvable.`);
      }

      this.activeChallenge = challenge;
      this.activeChallengeIndex = this.challenges.findIndex(c => c.id === challengeId);
      if (this.activeChallengeIndex === -1) this.activeChallengeIndex = 0;
      this.currentView = 'practical_workshop';

      // Initialiser le système de fichiers pour ce défi
      this.activeVFS = new VirtualFS();
      const initFs = challenge.initial_fs || challenge.initial_vfs;
      if (initFs) {
        this.activeVFS.loadInitialFS(initFs);
      }

      // Initialiser le moteur shell
      this.activeShellEngine = new ShellEngine({
        vfs: this.activeVFS,
        cwd: '/home/student'
      });

      this.renderPracticalWorkshop();
    } catch (err) {
      console.error("Erreur lancement atelier pratique:", err);
      if (window.showToast) {
        window.showToast(`Erreur : ${err.message}`, 'danger');
      }
    }
  }

  /**
   * Rendu complet de l'atelier 2-volets (homogène avec l'AlgoCompiler)
   */
  renderPracticalWorkshop() {
    if (!this.container || !this.activeChallenge) return;
    const ch = this.activeChallenge;

    const diffColors = {
      easy: '#34d399',
      medium: '#fbbf24',
      hard: '#f87171'
    };
    const diffColor = diffColors[ch.difficulty] || '#60a5fa';

    // Options du sélecteur de défis
    const challengeOptions = this.challenges.map((item, idx) => {
      const selected = item.id === ch.id ? 'selected' : '';
      let prefix = '○ ';
      if (item.status === 'solved') prefix = '✓ ';
      else if (item.status === 'in_progress') prefix = '⏳ ';
      return `<option value="${item.id}" ${selected}>${prefix}${idx + 1}. ${item.title}</option>`;
    }).join('');

    // Instructions formatées
    let instructionsHtml = (ch.description || '')
      .replace(/^### (.*$)/gim, '<h3 style="font-size:1.15rem; color:var(--text-primary); margin:12px 0 8px;">$1</h3>')
      .replace(/^#### (.*$)/gim, '<h4 style="font-size:0.98rem; color:#93c5fd; margin:10px 0 6px;">$1</h4>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08); color:#38bdf8; padding:2px 6px; border-radius:4px; font-size:0.88em; font-family:var(--font-mono);">$1</code>')
      .replace(/\n\n/g, '<p style="margin:0 0 10px; line-height:1.55; color:var(--text-secondary);"></p>');

    // Indices
    const hints = Array.isArray(ch.hints) ? ch.hints : [];
    const hintsHtml = hints.map((h, i) => `
      <details style="margin-top:8px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:8px 12px;">
        <summary style="cursor:pointer; font-weight:600; color:#fbbf24; font-size:0.85rem;">💡 Indice ${i + 1}</summary>
        <p style="margin:8px 0 0 0; font-size:0.85rem; color:var(--text-secondary);">${this._escapeHtml(h)}</p>
      </details>
    `).join('');

    this.container.innerHTML = `
      <div class="challenge-layout fused-workspace" style="display:flex; width:100%; height:calc(100vh - 120px); min-height:620px; overflow:hidden; background:#080c14; border:1px solid rgba(255,255,255,0.08); border-radius:8px;">
        
        <!-- ================= VOLET GAUCHE : CONSIGNES & SÉLECTEUR ================= -->
        <div class="problem-pane" style="flex: 0 0 42%; width: 42%; display: flex; flex-direction: column; height: 100%; background: #0d1322; border-right: 1px solid rgba(255,255,255,0.08); overflow-y: auto;">
          
          <!-- Barre Supérieure d'Action -->
          <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; background:#0b1120; border-bottom:1px solid rgba(255,255,255,0.08);">
            <button id="btn-practical-return-hub" class="btn btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:6px; font-size:0.82rem;">
              ← Retour au Centre Linux
            </button>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:0.8rem; color:var(--text-muted);">Défi :</span>
              <select id="select-active-challenge" style="background:#131c31; color:#f8fafc; border:1px solid rgba(255,255,255,0.15); border-radius:4px; padding:4px 8px; font-size:0.82rem; outline:none; max-width:220px;">
                ${challengeOptions}
              </select>
            </div>
          </div>

          <!-- Corps des Consignes -->
          <div style="padding: 20px 22px; flex: 1; overflow-y: auto;">
            
            <!-- Badges Métadonnées -->
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:14px;">
              <span class="user-tag" style="background:rgba(59,130,246,0.15); color:#93c5fd; font-weight:700;">
                Niveau ${ch.level || 1} • ${ch.topic || 'Linux'}
              </span>
              <span class="badge" style="background:rgba(255,255,255,0.05); color:${diffColor}; font-weight:600; border:1px solid ${diffColor}40;">
                ● ${ch.difficulty || 'Moyen'}
              </span>
              <span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; font-weight:700;">
                ⭐ ${ch.points || 2.0} pts
              </span>
            </div>

            <!-- Titre -->
            <h2 style="font-size:1.35rem; color:var(--text-primary); margin:0 0 16px 0; line-height:1.3;">
              ${this._escapeHtml(ch.title)}
            </h2>

            <!-- Enoncé & Instructions -->
            <div class="challenge-markdown-body" style="font-size:0.92rem; line-height:1.6; color:var(--text-secondary);">
              ${instructionsHtml}
            </div>

            <!-- Indices Déroulants -->
            ${hints.length > 0 ? `
              <div style="margin-top:24px;">
                <h4 style="font-size:0.9rem; color:#f8fafc; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">Indices & Conseils</h4>
                ${hintsHtml}
              </div>
            ` : ''}

          </div>
        </div>

        <!-- ================= VOLET DROIT : ÉDITEUR & TERMINAL CLI ================= -->
        <div class="editor-pane" style="flex: 1; display: flex; flex-direction: column; height: 100%; background: #080c14; overflow: hidden;">
          
          <!-- 1. En-tête de l'éditeur de commande / script -->
          <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 16px; background:#0b1120; border-bottom:1px solid rgba(255,255,255,0.08);">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:0.85rem; font-weight:700; color:#f8fafc;">💻 Commande(s) / Script à Évaluer :</span>
              <span id="label-editor-status" style="font-size:0.75rem; color:#10b981; font-weight:600;">● Prêt</span>
            </div>
            <button id="btn-editor-reset-tpl" class="btn btn-secondary btn-sm" style="font-size:0.78rem; padding:3px 10px;" title="Réinitialiser à la commande modèle">
              ↺ Modèle
            </button>
          </div>

          <!-- 2. Zone Textarea d'édition -->
          <div style="flex: 0 0 110px; min-height: 90px; background: #050811; border-bottom: 1px solid rgba(255,255,255,0.08); position: relative;">
            <textarea id="linux-cmd-editor" style="width:100%; height:100%; background:transparent; border:none; color:#f8fafc; font-family:'Fira Code', 'JetBrains Mono', Consolas, monospace; font-size:0.92rem; padding:10px 14px; outline:none; resize:none; line-height:1.55;" placeholder="# Tapez vos commandes Linux ici (ex: pwd && ls -la)">${this._escapeHtml(ch.starter_cmd || ch.starter_code || '')}</textarea>
          </div>

          <!-- 3. Barre d'onglets et boutons d'action d'exécution -->
          <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 14px; background:#090e1a; border-bottom:1px solid rgba(255,255,255,0.08); flex-wrap:wrap; gap:8px;">
            
            <!-- Onglets de la zone basse -->
            <div style="display:flex; gap:6px;">
              <button id="tab-btn-workshop-term" class="btn btn-sm btn-primary active-tab" style="font-size:0.82rem; padding:5px 12px; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                <span>🖥️</span> Terminal Interactif (CLI)
              </button>
              <button id="tab-btn-workshop-tests" class="btn btn-sm btn-secondary" style="font-size:0.82rem; padding:5px 12px; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                <span>🧪</span> Cas de Test (<span id="test-tab-count">${(ch.public_tests || []).length}</span>)
              </button>
            </div>

            <!-- Actions d'Exécution & Soumission -->
            <div style="display:flex; gap:8px; align-items:center;">
              <button id="btn-workshop-exec-cmd" class="btn btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:6px; font-weight:600; padding:6px 14px;">
                <span>⚡</span> Exécuter
              </button>
              <button id="btn-workshop-test-public" class="btn btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:6px; font-weight:600; padding:6px 14px; background:rgba(59,130,246,0.15); color:#93c5fd; border:1px solid rgba(59,130,246,0.3);">
                <span>🧪</span> Tester Publics
              </button>
              <button id="btn-workshop-submit" class="btn btn-primary btn-sm" style="display:inline-flex; align-items:center; gap:6px; font-weight:700; padding:6px 18px; background:linear-gradient(135deg, #10b981 0%, #059669 100%); border:none; box-shadow:0 2px 10px rgba(16,185,129,0.35);">
                <span>🚀</span> Soumettre le Défi
              </button>
            </div>

          </div>

          <!-- 4. Zone Basse à Onglets : Terminal CLI vs Cas de Test -->
          <div style="flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative;">
            
            <!-- Contenu Onglet 1 : Terminal Interactif -->
            <div id="workshop-pane-terminal" style="flex:1; display:flex; flex-direction:column; width:100%; height:100%; overflow:hidden;">
              <div id="linux-workshop-terminal-container" style="flex:1; width:100%; height:100%; overflow:hidden;"></div>
            </div>

            <!-- Contenu Onglet 2 : Résultats des Cas de Test -->
            <div id="workshop-pane-tests" style="flex:1; display:none; flex-direction:column; padding:16px; overflow-y:auto; background:#04070e;">
              <div id="workshop-tests-summary" style="margin-bottom:14px; font-size:0.95rem; font-weight:700; color:#93c5fd;">
                Cas de test du défi (Cliquez sur "Tester Publics" ou "Soumettre" pour lancer la validation) :
              </div>
              <div id="workshop-tests-list" style="display:flex; flex-direction:column; gap:10px;">
                ${this._renderInitialTestCards(ch)}
              </div>
            </div>

          </div>

        </div>

      </div>

      <!-- Modal de Résultat & Félicitations Défi Validé -->
      <div id="modal-linux-challenge-result" class="modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.75); z-index:9999; justify-content:center; align-items:center;">
        <div style="background:#0f172a; border:1px solid rgba(255,255,255,0.12); border-radius:12px; width:92%; max-width:540px; padding:28px 24px; text-align:center; box-shadow:0 20px 50px rgba(0,0,0,0.8);">
          <div id="modal-result-icon" style="font-size:3rem; margin-bottom:12px;">🎉</div>
          <h3 id="modal-result-title" style="font-size:1.4rem; color:#f8fafc; margin:0 0 8px 0;">Défi Validé avec Succès !</h3>
          <p id="modal-result-msg" style="color:var(--text-secondary); font-size:0.95rem; margin:0 0 20px 0;">Tous les tests publics et cachés ont été validés.</p>
          
          <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:14px; margin-bottom:24px; display:flex; justify-content:space-around;">
            <div>
              <div style="font-size:0.8rem; color:var(--text-muted);">Points Obtenus</div>
              <div id="modal-result-points" style="font-size:1.3rem; font-weight:800; color:#10b981;">+2.0 pts</div>
            </div>
            <div>
              <div style="font-size:0.8rem; color:var(--text-muted);">Réussite</div>
              <div id="modal-result-percentage" style="font-size:1.3rem; font-weight:800; color:#60a5fa;">100%</div>
            </div>
          </div>

          <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <button id="btn-modal-return-linux-center" class="btn btn-primary" style="padding:10px 22px; font-weight:700; font-size:0.95rem;">
              Retourner au Centre d'Entraînement Linux ➔
            </button>
          </div>
        </div>
      </div>
    `;

    // Monter le terminal interactif
    const termContainer = document.getElementById('linux-workshop-terminal-container');
    if (termContainer) {
      this.activeTerminalUI = new TerminalUI({
        container: termContainer,
        shellEngine: this.activeShellEngine,
        vfs: this.activeVFS
      });
      this.activeTerminalUI.write(`\n🐧 [Environnement Défi "${ch.title}" initialisé]\nTapez vos commandes ou utilisez le volet supérieur.\n\n`, 'system');
      this.activeTerminalUI.updatePrompt();
    }

    this._attachWorkshopEvents();
  }

  /**
   * Cartes de tests affichées par défaut avant exécution
   * @private
   */
  _renderInitialTestCards(challenge) {
    const publicTests = challenge.public_tests || [];
    return publicTests.map((t, idx) => `
      <div class="test-case-card" style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-size:0.9rem; font-weight:600; color:#f8fafc; margin-bottom:4px;">
            ${this._escapeHtml(t.name || `Test Public #${idx + 1}`)}
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted); font-family:var(--font-mono);">
            ${t.cmd ? `Commande : ${this._escapeHtml(t.cmd)}` : `Vérification : ${this._escapeHtml(t.assertion_type || t.type || 'état')}`}
          </div>
        </div>
        <span class="badge" style="background:rgba(255,255,255,0.06); color:var(--text-muted); font-size:0.8rem; padding:4px 10px; border-radius:12px;">
          En attente
        </span>
      </div>
    `).join('');
  }

  /**
   * Attache les écouteurs d'événements de l'atelier
   * @private
   */
  _attachWorkshopEvents() {
    // Bouton retour hub
    const btnReturn = document.getElementById('btn-practical-return-hub');
    if (btnReturn) {
      btnReturn.onclick = () => this.renderHub();
    }

    // Sélecteur de défi
    const selectCh = document.getElementById('select-active-challenge');
    if (selectCh) {
      selectCh.onchange = (e) => {
        this.startPracticalWorkshop(e.target.value);
      };
    }

    // Réinitialiser au modèle
    const btnResetTpl = document.getElementById('btn-editor-reset-tpl');
    const editor = document.getElementById('linux-cmd-editor');
    if (btnResetTpl && editor) {
      btnResetTpl.onclick = () => {
        editor.value = this.activeChallenge.starter_cmd || this.activeChallenge.starter_code || '';
        editor.focus();
      };
    }

    // Bascule onglets : Terminal vs Cas de Test
    const tabBtnTerm = document.getElementById('tab-btn-workshop-term');
    const tabBtnTests = document.getElementById('tab-btn-workshop-tests');
    const paneTerm = document.getElementById('workshop-pane-terminal');
    const paneTests = document.getElementById('workshop-pane-tests');

    const switchWorkshopTab = (tab) => {
      if (tab === 'term') {
        if (paneTerm) paneTerm.style.display = 'flex';
        if (paneTests) paneTests.style.display = 'none';
        if (tabBtnTerm) {
          tabBtnTerm.className = 'btn btn-sm btn-primary active-tab';
        }
        if (tabBtnTests) {
          tabBtnTests.className = 'btn btn-sm btn-secondary';
        }
      } else {
        if (paneTerm) paneTerm.style.display = 'none';
        if (paneTests) paneTests.style.display = 'flex';
        if (tabBtnTerm) {
          tabBtnTerm.className = 'btn btn-sm btn-secondary';
        }
        if (tabBtnTests) {
          tabBtnTests.className = 'btn btn-sm btn-primary active-tab';
        }
      }
    };

    if (tabBtnTerm) tabBtnTerm.onclick = () => switchWorkshopTab('term');
    if (tabBtnTests) tabBtnTests.onclick = () => switchWorkshopTab('tests');

    // 1. Bouton "Exécuter" (applique la commande en direct dans le terminal)
    const btnExec = document.getElementById('btn-workshop-exec-cmd');
    if (btnExec && editor) {
      btnExec.onclick = async () => {
        const cmd = editor.value.trim();
        if (!cmd) return;
        switchWorkshopTab('term');
        if (this.activeTerminalUI) {
          await this.activeTerminalUI.executeCommand(cmd);
        }
      };
    }

    // 2. Bouton "Tester Publics" (évalue localement sur les tests publics)
    const btnTestPublic = document.getElementById('btn-workshop-test-public');
    if (btnTestPublic && editor) {
      btnTestPublic.onclick = async () => {
        const cmd = editor.value.trim();
        switchWorkshopTab('tests');
        await this._runEvaluation(cmd, { runHidden: false });
      };
    }

    // 3. Bouton "Soumettre le Défi" (évalue public + cachés et appelle l'API)
    const btnSubmit = document.getElementById('btn-workshop-submit');
    if (btnSubmit && editor) {
      btnSubmit.onclick = async () => {
        const cmd = editor.value.trim();
        switchWorkshopTab('tests');
        await this._submitChallenge(cmd);
      };
    }

    // Modal bouton retour
    const btnModalReturn = document.getElementById('btn-modal-return-linux-center');
    if (btnModalReturn) {
      btnModalReturn.onclick = () => {
        const modal = document.getElementById('modal-linux-challenge-result');
        if (modal) modal.style.display = 'none';
        this.renderHub();
      };
    }
  }

  /**
   * Évalue les tests publics et met à jour l'affichage de l'onglet
   * @private
   */
  async _runEvaluation(command, options = {}) {
    const summaryEl = document.getElementById('workshop-tests-summary');
    const listEl = document.getElementById('workshop-tests-list');

    if (summaryEl) summaryEl.innerHTML = '<em>Validation en cours...</em>';

    try {
      const evalRes = await LinuxChallengeEvaluator.evaluate(command, this.activeChallenge, {
        runHidden: options.runHidden || false
      });

      this._displayTestResults(evalRes, summaryEl, listEl);
      return evalRes;
    } catch (err) {
      console.error("Erreur évaluation tests:", err);
      if (summaryEl) summaryEl.innerHTML = `<span style="color:#ef4444;">Erreur d'évaluation : ${err.message}</span>`;
      return null;
    }
  }

  /**
   * Affiche les résultats des tests dans l'onglet
   * @private
   */
  _displayTestResults(evalRes, summaryEl, listEl) {
    if (!evalRes || !listEl) return;

    if (summaryEl) {
      const color = evalRes.all_passed ? '#10b981' : '#f59e0b';
      summaryEl.innerHTML = `
        <span style="color:${color}; font-weight:700;">
          ${evalRes.message || `${evalRes.passed_count}/${evalRes.total_tests} tests réussis`}
        </span>
      `;
    }

    listEl.innerHTML = evalRes.test_results.map(r => {
      const passColor = r.passed ? '#10b981' : '#ef4444';
      const statusBadge = r.passed
        ? '<span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; font-weight:700;">✓ Passé</span>'
        : '<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; font-weight:700;">✗ Échec</span>';

      return `
        <div class="test-case-card" style="background:rgba(255,255,255,0.02); border:1px solid ${r.passed ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}; border-radius:6px; padding:12px 14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:0.9rem; font-weight:600; color:#f8fafc;">
              ${this._escapeHtml(r.name)}
            </div>
            ${statusBadge}
          </div>
          ${r.is_public ? `
            <div style="font-size:0.8rem; color:var(--text-muted); display:flex; flex-direction:column; gap:2px; font-family:var(--font-mono);">
              ${r.cmd ? `<div>Commande : <code>${this._escapeHtml(r.cmd)}</code></div>` : ''}
              <div>Attendu : <span style="color:#93c5fd;">${this._escapeHtml(String(r.expected))}</span></div>
              <div>Obtenu : <span style="color:${passColor};">${this._escapeHtml(String(r.actual))}</span></div>
            </div>
          ` : `
            <div style="font-size:0.8rem; color:var(--text-muted); font-family:var(--font-mono);">
              <em>Critères confidentiels [Protégé]</em>
            </div>
          `}
        </div>
      `;
    }).join('');
  }

  /**
   * Soumission officielle du défi avec synchronisation au backend
   * @private
   */
  async _submitChallenge(command) {
    const summaryEl = document.getElementById('workshop-tests-summary');
    const listEl = document.getElementById('workshop-tests-list');

    if (summaryEl) summaryEl.innerHTML = '<em>Évaluation exhaustive et soumission en cours...</em>';

    // 1. Évaluation client complète (publics + cachés)
    const clientEval = await LinuxChallengeEvaluator.evaluate(command, this.activeChallenge, {
      runHidden: true
    });
    this._displayTestResults(clientEval, summaryEl, listEl);

    // 2. Appel backend /api/training/linux/submit-challenge
    try {
      const vfsSnapshot = clientEval.vfs_snapshot || (this.activeVFS ? this.activeVFS.snapshot() : {});
      let apiRes = null;

      if (this.api && this.api.submitLinuxChallenge) {
        apiRes = await this.api.submitLinuxChallenge({
          challenge_id: this.activeChallenge.id,
          command,
          vfs_state: vfsSnapshot,
          execution_output: {
            stdout: clientEval.exec_stdout,
            stderr: clientEval.exec_stderr,
            exitCode: clientEval.exec_exit_code
          },
          client_tests_passed: clientEval.all_passed
        });
      }

      // Marquer localement le défi comme résolu si réussi
      if (clientEval.all_passed) {
        this.activeChallenge.status = 'solved';
        const inPool = this.challenges.find(c => c.id === this.activeChallenge.id);
        if (inPool) inPool.status = 'solved';

        // Afficher modal de félicitations
        this._showCompletionModal({
          title: `Défi Validé : ${this.activeChallenge.title}`,
          message: apiRes && apiRes.message ? apiRes.message : 'Tous les tests publics et cachés ont été validés avec succès.',
          points: `+${this.activeChallenge.points || 2.0} pts`,
          percentage: '100%'
        });
      } else {
        if (window.showToast) {
          window.showToast(clientEval.message, 'warning');
        }
      }
    } catch (err) {
      console.warn("Erreur soumission backend:", err);
      if (clientEval.all_passed) {
        this._showCompletionModal({
          title: `Défi Validé : ${this.activeChallenge.title}`,
          message: 'Tous les tests ont été validés.',
          points: `+${this.activeChallenge.points || 2.0} pts`,
          percentage: '100%'
        });
      }
    }
  }

  /**
   * Ouvre la modale de complétion
   * @private
   */
  _showCompletionModal(data) {
    const modal = document.getElementById('modal-linux-challenge-result');
    if (!modal) return;

    const titleEl = document.getElementById('modal-result-title');
    const msgEl = document.getElementById('modal-result-msg');
    const ptsEl = document.getElementById('modal-result-points');
    const pctEl = document.getElementById('modal-result-percentage');

    if (titleEl) titleEl.textContent = data.title;
    if (msgEl) msgEl.textContent = data.message;
    if (ptsEl) ptsEl.textContent = data.points;
    if (pctEl) pctEl.textContent = data.percentage;

    modal.style.display = 'flex';
  }

  // =========================================================================
  // 3. VOLET THÉORIQUE (QUIZ & ADMINISTRATION SYSTÈME)
  // =========================================================================

  /**
   * Démarre une session de quiz théorique
   * @param {string} [chapterId=null]
   */
  async startTheoryQuiz(chapterId = null) {
    try {
      let quizzes = [];
      if (chapterId && this.api && this.api.getLinuxChapter) {
        try {
          const chap = await this.api.getLinuxChapter(chapterId, 'theoretical');
          if (chap && chap.items) {
            quizzes = chap.items.filter(item => item.type !== 'linux_cmd' && item.options);
          }
        } catch (_) {}
      }
      if (!quizzes || quizzes.length === 0) {
        if (this.api && this.api.getLinuxTheoryQuizzes) {
          quizzes = await this.api.getLinuxTheoryQuizzes();
        }
      }
      if (!quizzes || quizzes.length === 0) {
        // Fallback session
        const session = await this.api.generateLinuxSession({
          chapter_id: chapterId,
          assessment_type: 'theoretical',
          count: 8
        });
        quizzes = (session.items || []).filter(item => item.type !== 'linux_cmd' && item.options);
      }

      if (!quizzes || quizzes.length === 0) {
        if (window.showToast) window.showToast("Aucun quiz théorique disponible.", "warning");
        return;
      }

      this.theoryQuizzes = quizzes;
      this.currentQuizIndex = 0;
      this.theoryScore = 0;
      this.theoryAnswers = [];
      this.currentView = 'theory_quiz';

      this.renderTheoryQuizStep();
    } catch (err) {
      console.error("Erreur lancement quiz théorique:", err);
      if (window.showToast) window.showToast(`Erreur : ${err.message}`, 'danger');
    }
  }

  /**
   * Rendu de la question active du quiz théorique
   */
  renderTheoryQuizStep() {
    if (!this.container) return;

    if (this.currentQuizIndex >= this.theoryQuizzes.length) {
      this.renderTheoryCompletion();
      return;
    }

    const q = this.theoryQuizzes[this.currentQuizIndex];
    const total = this.theoryQuizzes.length;
    const currentNum = this.currentQuizIndex + 1;
    const options = q.options || [];

    const optionsHtml = options.map((opt, i) => {
      const optId = `opt-${i}`;
      const optText = (typeof opt === 'object' && opt !== null) ? (opt.text || opt.title || opt.label || '') : String(opt);
      return `
        <label for="${optId}" class="quiz-option-label" style="display:flex; align-items:center; gap:12px; padding:12px 16px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; cursor:pointer; margin-bottom:10px; transition:background 0.15s, border-color 0.15s;">
          <input type="radio" name="theory-quiz-option" id="${optId}" value="${i}" style="accent-color:#10b981; transform:scale(1.2);" />
          <span style="font-size:0.95rem; color:var(--text-primary);">${this._escapeHtml(optText)}</span>
        </label>
      `;
    }).join('');

    this.container.innerHTML = `
      <div class="dashboard-container" style="max-width: 800px; margin: 0 auto; padding: 32px 20px;">
        
        <!-- En-tête -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
          <div>
            <span class="user-tag" style="background:rgba(16,185,129,0.15); color:#6ee7b7; font-weight:700;">
              Volet Théorique • ${this._escapeHtml(q.topic || 'Administration Linux')}
            </span>
            <h2 style="font-size:1.4rem; color:var(--text-primary); margin:8px 0 0 0;">
              Question ${currentNum} sur ${total}
            </h2>
          </div>
          <button id="btn-theory-cancel" class="btn btn-secondary btn-sm">
            ← Quitter le Quiz
          </button>
        </div>

        <!-- Carte Question -->
        <div class="card" style="padding:26px 24px; background:var(--bg-surface); border:1px solid rgba(255,255,255,0.08); border-radius:10px; margin-bottom:24px;">
          <p style="font-size:1.1rem; font-weight:600; color:var(--text-primary); line-height:1.5; margin:0 0 20px 0;">
            ${this._escapeHtml(q.prompt || q.question || q.title || '')}
          </p>

          <form id="form-theory-quiz">
            <div id="theory-options-container">
              ${optionsHtml}
            </div>
            
            <div id="theory-feedback-box" style="display:none; margin:16px 0; padding:12px 16px; border-radius:6px; font-size:0.9rem;"></div>

            <div style="margin-top:20px; display:flex; justify-content:flex-end;">
              <button type="submit" id="btn-theory-validate" class="btn btn-primary" style="padding:8px 22px; font-weight:600; font-size:0.95rem; background:#059669; border-color:#059669;">
                Valider la Réponse
              </button>
              <button type="button" id="btn-theory-next" class="btn btn-primary" style="display:none; padding:8px 22px; font-weight:600; font-size:0.95rem; background:#2563eb; border-color:#2563eb;">
                Question Suivante ➔
              </button>
            </div>
          </form>
        </div>

      </div>
    `;

    // Événements du quiz
    const btnCancel = document.getElementById('btn-theory-cancel');
    if (btnCancel) {
      btnCancel.onclick = () => {
        if (confirm("Voulez-vous quitter ce quiz ? Vos réponses seront perdues.")) {
          this.renderHub();
        }
      };
    }

    const form = document.getElementById('form-theory-quiz');
    const feedbackBox = document.getElementById('theory-feedback-box');
    const btnValidate = document.getElementById('btn-theory-validate');
    const btnNext = document.getElementById('btn-theory-next');

    if (form) {
      form.onsubmit = (e) => {
        e.preventDefault();
        const selected = form.querySelector('input[name="theory-quiz-option"]:checked');
        if (!selected) {
          if (window.showToast) window.showToast("Veuillez sélectionner une réponse.", "warning");
          return;
        }

        const chosenIdx = parseInt(selected.value, 10);
        // Validation (si correct index fourni ou simulation)
        const isCorrect = q.correct_index !== undefined ? (chosenIdx === q.correct_index) : true;
        if (isCorrect) this.theoryScore++;

        this.theoryAnswers.push({
          question_id: q.id,
          selected_index: chosenIdx,
          is_correct: isCorrect
        });

        // Afficher feedback
        if (feedbackBox) {
          feedbackBox.style.display = 'block';
          if (isCorrect) {
            feedbackBox.style.background = 'rgba(16,185,129,0.15)';
            feedbackBox.style.color = '#34d399';
            feedbackBox.style.border = '1px solid rgba(16,185,129,0.3)';
            feedbackBox.innerHTML = `<strong>✓ Bonne réponse !</strong> ${this._escapeHtml(q.explanation || '')}`;
          } else {
            feedbackBox.style.background = 'rgba(239,68,68,0.15)';
            feedbackBox.style.color = '#f87171';
            feedbackBox.style.border = '1px solid rgba(239,68,68,0.3)';
            feedbackBox.innerHTML = `<strong>✗ Incorrect.</strong> ${this._escapeHtml(q.explanation || '')}`;
          }
        }

        // Désactiver options
        form.querySelectorAll('input[name="theory-quiz-option"]').forEach(inp => inp.disabled = true);
        if (btnValidate) btnValidate.style.display = 'none';
        if (btnNext) btnNext.style.display = 'inline-block';
      };
    }

    if (btnNext) {
      btnNext.onclick = () => {
        this.currentQuizIndex++;
        this.renderTheoryQuizStep();
      };
    }
  }

  /**
   * Écran de fin de session théorique avec le bouton officiel de retour
   */
  renderTheoryCompletion() {
    if (!this.container) return;
    const total = this.theoryQuizzes.length;
    const score = this.theoryScore;
    const grade20 = total > 0 ? ((score / total) * 20).toFixed(1) : '20.0';
    const pct = total > 0 ? Math.round((score / total) * 100) : 100;

    // Envoi de la session théorique au backend pour synchronisation et historique
    if (this.api && this.api.submitLinuxSession && this.theoryAnswers.length > 0) {
      const answersForBackend = this.theoryAnswers.map(ans => ({
        id: ans.question_id,
        type: "single_choice",
        topic: "Linux",
        student_answer: ans.selected_index,
        is_correct: ans.is_correct
      }));
      this.api.submitLinuxSession(answersForBackend).catch(() => {});
    }

    this.container.innerHTML = `
      <div class="dashboard-container" style="max-width: 680px; margin: 40px auto; text-align: center; padding: 32px 20px;">
        <div style="font-size: 3.5rem; margin-bottom: 12px;">🎉</div>
        <h2 style="font-size: 1.8rem; color: #f8fafc; margin: 0 0 8px 0;">Quiz Théorique Terminé !</h2>
        <p style="color: var(--text-secondary); margin: 0 0 28px 0; font-size: 1.05rem;">
          Vous avez complété l'ensemble des questions d'administration Linux.
        </p>

        <div class="card" style="padding: 24px; background: var(--bg-surface); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; margin-bottom: 28px;">
          <div style="font-size: 3.2rem; font-weight: 800; font-family: var(--font-mono); color: #10b981; margin-bottom: 6px;">
            ${grade20} / 20
          </div>
          <div style="font-size: 1.05rem; color: #93c5fd; font-weight: 600;">
            ${pct}% de réussite (${score} / ${total} questions correctes)
          </div>
        </div>

        <button id="btn-theory-finish-return-hub" class="btn btn-primary" style="padding: 12px 28px; font-weight: 700; font-size: 1rem; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);">
          Retourner au Centre d'Entraînement Linux ➔
        </button>
      </div>
    `;

    const btnReturn = document.getElementById('btn-theory-finish-return-hub');
    if (btnReturn) {
      btnReturn.onclick = () => this.renderHub();
    }
  }

  // =========================================================================
  // Utilitaires
  // =========================================================================

  _escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}
