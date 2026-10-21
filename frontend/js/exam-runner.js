/**
 * Gestionnaire du Déroulement d'Examen (Exam Runner) :
 * - Navigation libre via Palette interactive
 * - Rendu dynamique des 5 types de questions
 * - Auto-sauvegarde transparente
 * - Décompte avec alerte rouge de 60 secondes (Grace Warning)
 * - Soumission finale et affichage immédiat de la note
 */

import { api } from './api.js';
import { LinuxVFS, LinuxChallengeEvaluator } from './linux-vfs.js';

export class ExamRunner {
  constructor(examData, options = {}) {
    this.attemptId = examData.attempt_id;
    this.examTitle = examData.exam_title;
    this.questions = examData.questions || [];
    this.answers = examData.saved_answers || {};
    this.flaggedQuestions = new Set();
    this.currentIndex = 0;
    this.remainingSeconds = examData.remaining_seconds || (30 * 60);
    this.timerInterval = null;
    this.isPracticeMode = options.isPracticeMode || false;
    this.onPracticeSubmit = options.onPracticeSubmit || null;
    this._keyListener = null;

    this.onFinish = options.onFinish || (() => {});
    this.antiCheat = options.antiCheat || null;
  }

  start() {
    this.currentIndex = 0;
    this._startTimer();
    this._attachKeyboardNavigation();
    this.render();
  }

  stop() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    if (this._keyListener) {
      window.removeEventListener('keydown', this._keyListener);
      this._keyListener = null;
    }
  }

  _attachKeyboardNavigation() {
    if (this._keyListener) {
      window.removeEventListener('keydown', this._keyListener);
    }
    this._keyListener = (e) => {
      // Ne pas intercepter les flèches si l'étudiant est en train d'écrire dans un champ
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (this.currentIndex > 0) {
          this.currentIndex--;
          this.render();
        }
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (this.currentIndex < this.questions.length - 1) {
          this.currentIndex++;
          this.render();
        }
      }
    };
    window.addEventListener('keydown', this._keyListener);
  }

  _startTimer() {
    this._updateTimerDisplay();
    this.timerInterval = setInterval(() => {
      this.remainingSeconds--;

      this._updateTimerDisplay();

      // Alerte rouge de grâce des 60 dernières secondes
      const timerBox = document.getElementById('exam-timer-box');
      if (this.remainingSeconds <= 60 && this.remainingSeconds > 0) {
        if (timerBox) timerBox.classList.add('timer-grace-warning');
      }

      // Expiration du temps : Soumission automatique
      if (this.remainingSeconds <= 0) {
        this.stop();
        this._autoSubmitOnTimeout();
      }
    }, 1000);
  }

  _updateTimerDisplay() {
    const el = document.getElementById('exam-timer-digits');
    if (!el) return;

    const total = Math.max(0, this.remainingSeconds);
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;

    const pad = (n) => String(n).padStart(2, '0');
    if (hours > 0) {
      el.textContent = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    } else {
      el.textContent = `${pad(minutes)}:${pad(seconds)}`;
    }
  }

  // Synchronisation authoritaire du chronomètre avec le serveur (REV-28)
  syncServerRemainingSeconds(serverSeconds) {
    if (typeof serverSeconds === 'number' && serverSeconds >= 0) {
      if (Math.abs(this.remainingSeconds - serverSeconds) > 2) {
        this.remainingSeconds = serverSeconds;
        this._updateTimerDisplay();
      }
    }
  }

  async _autoSubmitOnTimeout() {
    if (typeof window.showToast === 'function') {
      window.showToast("Le temps imparti pour cette épreuve est écoulé. Soumission automatique de vos réponses.", "warning", 5000);
    }
    await this.submit();
  }

  render() {
    this._renderPalette();
    this._renderCurrentQuestion();
    this._updateNavigationButtons();
  }

  _renderPalette() {
    const palette = document.getElementById('exam-palette-grid');
    if (!palette) return;

    palette.innerHTML = '';
    this.questions.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.className = 'palette-btn';
      btn.textContent = idx + 1;

      if (idx === this.currentIndex) btn.classList.add('active');
      if (this._hasAnswer(q.id)) btn.classList.add('answered');
      if (this.flaggedQuestions.has(q.id)) btn.classList.add('flagged');

      btn.onclick = () => {
        this.currentIndex = idx;
        this.render();
      };
      palette.appendChild(btn);
    });
  }

  _hasAnswer(questionId) {
    const ans = this.answers[questionId];
    if (ans === undefined || ans === null) return false;
    if (typeof ans === 'string' && ans.trim() === '') return false;
    if (Array.isArray(ans) && ans.length === 0) return false;
    if (typeof ans === 'object' && Object.keys(ans).length === 0) return false;
    return true;
  }

  _renderCurrentQuestion() {
    const container = document.getElementById('exam-question-container');
    if (!container || !this.questions.length) return;

    const q = this.questions[this.currentIndex];
    const currentAnswer = this.answers[q.id];

    // Formatage du type
    const typeLabels = {
      boolean: "Vrai / Faux",
      single_choice: "QCM à Réponse Unique",
      multi_choice: "QCM à Réponses Multiples",
      fill_blank: "Texte à Trou",
      matching: "Appariement",
      coding: "💻 Exercice de Code Python",
      code: "💻 Exercice de Code Python"
    };

    // Extraction et nettoyage des métadonnées de difficulté et de thème (REV-21)
    let cleanPrompt = q.prompt_markdown || '';
    let extractedTopic = q.topic || '';
    let extractedDifficulty = q.difficulty || '';

    // Détecte les préfixes textuels du type **[Thème • Difficulté : easy]** ou [💻 ...]
    const tagMatch = cleanPrompt.match(/^(\*\*\[(.*?)\]\*\*|\[(.*?)\])\s*/);
    if (tagMatch) {
      const rawTag = tagMatch[2] || tagMatch[3] || '';
      cleanPrompt = cleanPrompt.slice(tagMatch[0].length).trim();
      if (rawTag.includes('•')) {
        const parts = rawTag.split('•').map(p => p.trim());
        if (!extractedTopic) extractedTopic = parts[0];
        const diffPart = parts.find(p => p.toLowerCase().includes('diff'));
        if (diffPart && !extractedDifficulty) {
          const m = diffPart.match(/:\s*([a-zA-Z]+)/);
          if (m) extractedDifficulty = m[1].toLowerCase();
        }
      } else {
        if (!extractedTopic) extractedTopic = rawTag;
      }
    }

    let diffBadgeHtml = '';
    const diffNorm = (extractedDifficulty || '').toLowerCase();
    if (diffNorm.includes('easy') || diffNorm.includes('facile') || diffNorm.includes('débutant')) {
      diffBadgeHtml = '<span class="badge" style="background:rgba(16,185,129,0.15); color:#6ee7b7; border:1px solid #10b981; font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:600;">🟢 Facile</span>';
    } else if (diffNorm.includes('medium') || diffNorm.includes('intermédiaire') || diffNorm.includes('moyen')) {
      diffBadgeHtml = '<span class="badge" style="background:rgba(245,158,11,0.15); color:#fcd34d; border:1px solid #f59e0b; font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:600;">🟡 Intermédiaire</span>';
    } else if (diffNorm.includes('hard') || diffNorm.includes('avancé') || diffNorm.includes('avance')) {
      diffBadgeHtml = '<span class="badge" style="background:rgba(249,115,22,0.15); color:#fdba74; border:1px solid #f97316; font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:600;">🟠 Avancé</span>';
    } else if (diffNorm.includes('expert') || diffNorm.includes('difficile')) {
      diffBadgeHtml = '<span class="badge" style="background:rgba(239,68,68,0.15); color:#fca5a5; border:1px solid #ef4444; font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:600;">🔴 Expert</span>';
    }

    const topicClean = (extractedTopic || '').replace(/^💻\s*/, '').replace(/^\*\*|\*\*$/g, '').trim();
    const topicBadgeHtml = topicClean ? `<span class="badge" style="background:rgba(59,130,246,0.15); color:#93c5fd; border:1px solid rgba(59,130,246,0.3); font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:600;">📁 ${this._escapeHtml(topicClean)}</span>` : '';

    let promptHtml = this._formatMarkdown(cleanPrompt);

    // Ajustement de la disposition selon le type d'exercice (Plein écran étendu en mode Coding ou Linux Shell)
    const layoutEl = document.querySelector('.exam-layout');
    if (layoutEl) {
      layoutEl.classList.toggle('coding-mode', q.type === 'coding' || q.type === 'code' || q.type === 'linux_cmd');
    }

    // --- Rendu Spécifique Défi Pratique Python (AlgoCompiler / HackerRank Split Layout) ---
    if (q.type === 'coding' || q.type === 'code') {
      this._renderCodingChallenge(container, q, topicClean, topicBadgeHtml, diffBadgeHtml, typeLabels, promptHtml);
      return;
    }

    // --- Rendu Spécifique Défi Pratique Linux Shell (Terminal & VFS) ---
    if (q.type === 'linux_cmd') {
      this._renderLinuxChallenge(container, q, topicClean, topicBadgeHtml, diffBadgeHtml, typeLabels, promptHtml);
      return;
    }

    let optionsHtml = '';

    // --- 1. Vrai / Faux ---
    if (q.type === 'boolean') {
      const isTrueSelected = currentAnswer === true || currentAnswer === 'true';
      const isFalseSelected = currentAnswer === false || currentAnswer === 'false';

      optionsHtml = `
        <div class="options-list">
          <div class="option-item ${isTrueSelected ? 'selected' : ''}" data-val="true">
            <div class="option-indicator"></div>
            <div><strong>Vrai</strong></div>
          </div>
          <div class="option-item ${isFalseSelected ? 'selected' : ''}" data-val="false">
            <div class="option-indicator"></div>
            <div><strong>Faux</strong></div>
          </div>
        </div>
      `;
    }

    // --- 2. QCM Unique ---
    else if (q.type === 'single_choice') {
      const options = q.options || [];
      optionsHtml = '<div class="options-list">';
      options.forEach((opt, idx) => {
        const optId = (typeof opt === 'object' && opt !== null && opt.id !== undefined) ? opt.id : idx;
        const optText = (typeof opt === 'object' && opt !== null && opt.text !== undefined) ? opt.text : String(opt);
        const isSelected = String(currentAnswer) === String(optId);
        optionsHtml += `
          <div class="option-item ${isSelected ? 'selected' : ''}" data-val="${optId}">
            <div class="option-indicator"></div>
            <div>${this._escapeHtml(optText)}</div>
          </div>
        `;
      });
      optionsHtml += '</div>';
    }

    // --- 3. QCM Multiple ---
    else if (q.type === 'multi_choice') {
      const options = q.options || [];
      const selectedList = Array.isArray(currentAnswer) ? currentAnswer.map(String) : [];
      optionsHtml = '<p style="color:var(--text-secondary); margin-bottom:12px; font-size:0.85rem;">ℹ️ Plusieurs réponses possibles. Cliquez pour cocher/décocher.</p><div class="options-list">';
      options.forEach((opt, idx) => {
        const optId = (typeof opt === 'object' && opt !== null && opt.id !== undefined) ? opt.id : idx;
        const optText = (typeof opt === 'object' && opt !== null && opt.text !== undefined) ? opt.text : String(opt);
        const isSelected = selectedList.includes(String(optId));
        optionsHtml += `
          <div class="option-item ${isSelected ? 'selected' : ''}" data-val="${optId}" data-multi="true">
            <div class="option-indicator"></div>
            <div>${this._escapeHtml(optText)}</div>
          </div>
        `;
      });
      optionsHtml += '</div>';
    }

    // --- 4. Texte à Trou ---
    else if (q.type === 'fill_blank') {
      const textVal = currentAnswer || '';
      optionsHtml = `
        <div style="margin-top: 16px;">
          <input type="text" id="input-fill-blank" class="form-control" placeholder="Saisissez votre réponse ici..." value="${this._escapeHtml(textVal)}" style="font-size:1.05rem; padding:12px 16px;" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
        </div>
      `;
    }

    // --- 5. Appariement (REV-22) ---
    else if (q.type === 'matching') {
      let matchingData = q.options;
      if (typeof matchingData === 'string') {
        try { matchingData = JSON.parse(matchingData); } catch (_) { matchingData = {}; }
      }
      const leftItems = (matchingData && matchingData.left) ? matchingData.left : [];
      const rightItems = (matchingData && matchingData.right) ? matchingData.right : [];
      const userMatches = (typeof currentAnswer === 'object' && currentAnswer !== null) ? currentAnswer : {};

      optionsHtml = '<p style="color:var(--text-secondary); margin-bottom:12px; font-size:0.85rem;">ℹ️ Associez chaque élément de gauche à sa correspondance unique de droite. Tout choix est désactivé pour les autres items.</p><div style="margin-top: 16px;">';
      leftItems.forEach(left => {
        const selectedVal = userMatches[left] || '';
        optionsHtml += `
          <div class="matching-pair" style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; margin-bottom:10px; background:var(--bg-surface); border:1px solid var(--card-border); border-radius:var(--radius-md); gap:16px;">
            <div style="font-weight:600; flex:1; color:var(--text-primary); font-family:var(--font-mono); font-size:0.92rem;">${this._escapeHtml(left)}</div>
            <div style="flex:1;">
              <select class="form-control matching-select" data-left="${this._escapeHtml(left)}" style="width:100%; font-size:0.88rem; padding:8px 12px;">
                <option value="">— Choisir une correspondance —</option>
                ${rightItems.map(right => `<option value="${this._escapeHtml(right)}" ${selectedVal === right ? 'selected' : ''}>${this._escapeHtml(right)}</option>`).join('')}
              </select>
            </div>
          </div>
        `;
      });
      optionsHtml += '</div>';
    }

    // --- 6. Exercice de Code Python (REV-19) ---
    else if (q.type === 'coding' || q.type === 'code') {
      const codeVal = currentAnswer !== undefined ? currentAnswer : (q.starter_code || '');
      const hasHints = Boolean(q.hint1 || q.hint2);
      const sampleInput = (q.tests && q.tests[0] && q.tests[0].input !== undefined) ? q.tests[0].input : (q.sample_input || '');

      optionsHtml = `
        <div class="coding-editor-container" style="width:100%;">
          <textarea id="input-coding-editor" class="code-textarea" placeholder="# Écrivez votre code Python ici...">${this._escapeHtml(codeVal)}</textarea>
          
          <div style="margin:10px 0; display:flex; gap:10px; align-items:center; flex-wrap:wrap; background:rgba(15,23,42,0.6); padding:8px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.08);">
            <label style="font-size:0.82rem; color:var(--text-secondary); white-space:nowrap; font-weight:600;">📥 Entrée standard (stdin) :</label>
            <input type="text" id="input-coding-stdin" class="form-control" style="font-family:var(--font-mono); font-size:0.85rem; padding:4px 8px; flex:1; min-width:180px; background:rgba(0,0,0,0.3);" value="${this._escapeHtml(sampleInput)}" placeholder="ex: 10 3" />
          </div>

          <div class="code-action-bar">
            <span style="font-size:0.8rem; color:var(--text-muted);">🐍 Python 3 Pyodide (Flux standard stdin / stdout gérés)</span>
            <button id="btn-run-code-local" class="btn btn-secondary" style="font-size:0.85rem; padding:6px 14px;">
              ▶️ Tester mon code localement
            </button>
          </div>
          <div id="code-output-box" class="code-terminal-output" style="display:none; white-space:pre-wrap; font-family:var(--font-mono); font-size:0.85rem; padding:12px; border-radius:6px; background:#0b1120; border:1px solid rgba(255,255,255,0.1); margin-top:10px;"></div>
          ${hasHints ? `
            <div style="margin-top:12px; padding:10px 14px; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:var(--radius-md);">
              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span style="font-size:0.85rem; font-weight:600; color:#fbbf24;">💡 Indices disponibles (Pénalité : 1 indice = 50% de la note, 2 indices = 0 pt)</span>
                <button id="btn-request-hint" class="btn btn-secondary" style="font-size:0.8rem; padding:4px 10px;">
                  Afficher un indice
                </button>
              </div>
              <div id="hint-display-area" style="margin-top:8px; font-size:0.85rem; color:#fef3c7; display:none;"></div>
            </div>
          ` : ''}
        </div>
      `;
    }

    const isFlagged = this.flaggedQuestions.has(q.id);

    container.innerHTML = `
      <div class="question-header" style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; margin-bottom:16px;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          ${topicBadgeHtml}
          ${diffBadgeHtml}
          <span class="question-badge">${typeLabels[q.type] || q.type}</span>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          <span class="question-points">${q.points} pt(s)</span>
          <button id="btn-flag-question" class="btn btn-secondary" style="padding:4px 10px; font-size:0.8rem;">
            ${isFlagged ? '🚩 Marqué' : '🏳️ Marquer pour relecture'}
          </button>
        </div>
      </div>
      <div class="question-prompt" style="font-size:1.02rem; line-height:1.6; margin-bottom:18px;">
        <div style="font-weight:700; margin-bottom:8px; color:#93c5fd; font-size:0.9rem;">Question ${this.currentIndex + 1} sur ${this.questions.length}</div>
        ${promptHtml}
      </div>
      ${optionsHtml}
    `;

    // Attachement des écouteurs d'interaction
    this._attachOptionListeners(q);
  }

  _attachOptionListeners(question) {
    const qId = question.id;

    // Flag bouton
    const flagBtn = document.getElementById('btn-flag-question');
    if (flagBtn) {
      flagBtn.onclick = () => {
        if (this.flaggedQuestions.has(qId)) {
          this.flaggedQuestions.delete(qId);
        } else {
          this.flaggedQuestions.add(qId);
        }
        this.render();
      };
    }

    // Boolean & Single Choice
    if (question.type === 'boolean' || question.type === 'single_choice') {
      const items = document.querySelectorAll('.option-item');
      items.forEach(item => {
        item.onclick = async () => {
          let val = item.getAttribute('data-val');
          if (question.type === 'boolean') {
            val = (val === 'true');
          }
          this.answers[qId] = val;
          this.render();
          if (!this.isPracticeMode && this.attemptId) {
            const res = await api.saveAnswer(this.attemptId, qId, val);
            if (res && res.remaining_seconds !== undefined) this.syncServerRemainingSeconds(res.remaining_seconds);
          }
        };
      });
    }

    // Multi Choice
    else if (question.type === 'multi_choice') {
      const items = document.querySelectorAll('.option-item[data-multi="true"]');
      items.forEach(item => {
        item.onclick = async () => {
          const val = String(item.getAttribute('data-val'));
          let currentList = Array.isArray(this.answers[qId]) ? this.answers[qId].map(String) : [];
          const idx = currentList.indexOf(val);
          if (idx >= 0) {
            currentList.splice(idx, 1);
          } else {
            currentList.push(val);
          }
          this.answers[qId] = currentList;
          this.render();
          if (!this.isPracticeMode && this.attemptId) {
            const res = await api.saveAnswer(this.attemptId, qId, currentList);
            if (res && res.remaining_seconds !== undefined) this.syncServerRemainingSeconds(res.remaining_seconds);
          }
        };
      });
    }

    // Fill in the Blank
    else if (question.type === 'fill_blank') {
      const input = document.getElementById('input-fill-blank');
      if (input) {
        input.oninput = (e) => {
          this.answers[qId] = e.target.value;
          this._renderPalette();
        };
        input.onblur = async (e) => {
          if (!this.isPracticeMode && this.attemptId) {
            const res = await api.saveAnswer(this.attemptId, qId, e.target.value);
            if (res && res.remaining_seconds !== undefined) this.syncServerRemainingSeconds(res.remaining_seconds);
          }
        };
      }
    }

    // Matching (REV-22 : Sélection exclusive 1-to-1 et désélection)
    else if (question.type === 'matching') {
      const selects = document.querySelectorAll('.matching-select');
      
      const updateMutualExclusion = () => {
        const selectedValues = new Set();
        selects.forEach(s => {
          if (s.value) selectedValues.add(s.value);
        });

        selects.forEach(s => {
          Array.from(s.options).forEach(opt => {
            if (!opt.value) return; // L'option vide "— Choisir..." reste toujours disponible
            if (opt.value === s.value) {
              opt.disabled = false;
              opt.text = opt.value;
            } else if (selectedValues.has(opt.value)) {
              opt.disabled = true;
              opt.text = opt.value + ' (Déjà sélectionné)';
            } else {
              opt.disabled = false;
              opt.text = opt.value;
            }
          });
        });
      };

      // Application immédiate de l'exclusion mutuelle à l'affichage
      updateMutualExclusion();

      selects.forEach(select => {
        select.onchange = async () => {
          const leftKey = select.getAttribute('data-left');
          const currentMap = (typeof this.answers[qId] === 'object' && this.answers[qId] !== null) ? { ...this.answers[qId] } : {};
          if (select.value) {
            currentMap[leftKey] = select.value;
          } else {
            delete currentMap[leftKey];
          }
          this.answers[qId] = currentMap;
          updateMutualExclusion();
          this._renderPalette();
          if (!this.isPracticeMode && this.attemptId) {
            const res = await api.saveAnswer(this.attemptId, qId, currentMap);
            if (res && res.remaining_seconds !== undefined) this.syncServerRemainingSeconds(res.remaining_seconds);
          }
        };
      });
    }

    // Coding / Python Code (AlgoCompiler Split Layout)
    else if (question.type === 'coding' || question.type === 'code') {
      const publicTests = question.public_tests || (question.options && question.options.public_tests) || (Array.isArray(question.options) ? question.options : []) || question.tests || [];
      const validPublicTests = (Array.isArray(publicTests) ? publicTests : []).filter(t => t && t.is_public !== false);
      this._attachCodingChallengeListeners(question, validPublicTests);
    }

    // Linux Command / Shell Challenge (Terminal & VFS)
    else if (question.type === 'linux_cmd') {
      const publicTests = question.public_tests || [];
      this._attachLinuxChallengeListeners(question, publicTests);
    }
  }

  // --- Rendu du Layout AlgoCompiler (2 Colonnes : Problème à gauche, Éditeur & E/S à droite) ---
  _renderCodingChallenge(container, q, topicClean, topicBadgeHtml, diffBadgeHtml, typeLabels, promptHtml) {
    const codeVal = this.answers[q.id] !== undefined ? this.answers[q.id] : (q.starter_code || (q.options && q.options.starter_code) || '# Écrivez votre code Python ici\n');
    const hasHints = Boolean(q.hint1 || q.hint2);
    const publicTests = q.public_tests || (q.options && q.options.public_tests) || (Array.isArray(q.options) ? q.options : []) || q.tests || [];
    const validPublicTests = (Array.isArray(publicTests) ? publicTests : []).filter(t => t && t.is_public !== false);
    const sampleInput = (validPublicTests[0] && validPublicTests[0].input !== undefined) ? validPublicTests[0].input : (q.sample_input || '');
    const isFlagged = this.flaggedQuestions.has(q.id);

    // Calcul de la progression globale des exercices de code
    const answeredCodingCount = this.questions.filter(ques => this._hasAnswer(ques.id)).length;

    container.innerHTML = `
      <div class="practical-workspace-container" style="display:flex; flex-direction:column; height:100%; width:100%; overflow:hidden;">
        <!-- BANDEAU DE NAVIGATION INTERACTIF DES DÉFIS -->
        <div class="coding-navigator-bar" style="display:flex; align-items:center; justify-content:space-between; padding:8px 16px; background:#070b16; border-bottom:1px solid rgba(255,255,255,0.08); gap:14px; min-height:46px; box-sizing:border-box;">
          <div style="display:flex; align-items:center; gap:8px; overflow-x:auto; flex:1; scrollbar-width:thin;">
            <span style="font-size:0.92rem; font-weight:700; color:#60a5fa; text-transform:uppercase; letter-spacing:0.04em; white-space:nowrap; margin-right:6px;">
              🎯 Défis (${this.questions.length}) :
            </span>
            ${this.questions.map((ques, idx) => {
              const hasAns = this._hasAnswer(ques.id);
              const isCur = idx === this.currentIndex;
              const isFlag = this.flaggedQuestions.has(ques.id);
              const qTitle = ques.topic || ques.title || `Défi ${idx + 1}`;
              const shortTitle = qTitle.length > 22 ? qTitle.slice(0, 20) + '…' : qTitle;
              let icon = isCur ? '⚡' : (hasAns ? '✅' : '○');
              if (isFlag) icon = '🚩';

              const borderCol = isCur ? '#3b82f6' : (hasAns ? '#10b981' : (isFlag ? '#f59e0b' : 'rgba(255,255,255,0.15)'));
              const bgCol = isCur ? 'rgba(59,130,246,0.22)' : (hasAns ? 'rgba(16,185,129,0.14)' : (isFlag ? 'rgba(245,158,11,0.15)' : 'rgba(255,255,255,0.03)'));
              const textCol = isCur ? '#bfdbfe' : (hasAns ? '#a7f3d0' : (isFlag ? '#fcd34d' : '#94a3b8'));
              return `
                <button class="coding-nav-pill" data-idx="${idx}" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; font-size:0.92rem; font-weight:600; border-radius:16px; border:1px solid ${borderCol}; background:${bgCol}; color:${textCol}; cursor:pointer; white-space:nowrap; transition:all 0.15s ease;">
                  <span style="font-size:1rem;">${icon}</span>
                  <span>#${idx + 1} ${this._escapeHtml(shortTitle)}</span>
                </button>
              `;
            }).join('')}
          </div>
          <div style="display:flex; align-items:center; gap:10px; white-space:nowrap;">
            <span style="font-size:0.92rem; color:var(--text-muted); font-family:var(--font-mono);">
              Avancement : <strong style="color:#10b981; font-size:1rem;">${answeredCodingCount}</strong> / ${this.questions.length} résolu(s)
            </span>
          </div>
        </div>

        <div class="challenge-layout fused-workspace" style="flex:1; height:calc(100% - 46px); min-height:0;">
          <!-- LEFT PANE: Description -->
          <div class="problem-pane" style="width:44%; min-width:280px; max-width:65%;">
            <div class="problem-header" style="margin-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:10px;">
                <span style="font-weight:700; color:#93c5fd; font-size:1.05rem;">Question ${this.currentIndex + 1} sur ${this.questions.length}</span>
                <div style="display:flex; align-items:center; gap:8px;">
                  <button id="btn-challenge-prev" class="btn btn-secondary" style="padding:6px 14px; font-size:0.92rem; font-weight:600;" ${this.currentIndex === 0 ? 'disabled' : ''}>← Préc.</button>
                  <button id="btn-challenge-next" class="btn btn-secondary" style="padding:6px 14px; font-size:0.92rem; font-weight:600;" ${this.currentIndex === this.questions.length - 1 ? 'disabled' : ''}>Suiv. ➔</button>
                  <span class="question-points" style="font-size:0.95rem; font-weight:700; padding:4px 10px;">${q.points} pt(s)</span>
                  <button id="btn-flag-question" class="btn btn-secondary" style="padding:6px 14px; font-size:0.92rem; font-weight:600;">
                    ${isFlagged ? '🚩 Marqué' : '🏳️ Marquer'}
                  </button>
                </div>
              </div>
              <h2 style="font-size:1.4rem; font-weight:700; margin:0 0 10px 0; color:var(--text-primary); line-height:1.3;">
                ${this._escapeHtml(topicClean || 'Défi Python')}
              </h2>
              <div class="problem-meta" style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                ${topicBadgeHtml}
                ${diffBadgeHtml}
                <span class="question-badge" style="font-size:0.88rem; padding:4px 12px; font-weight:600;">${typeLabels[q.type] || '💻 Python'}</span>
              </div>
            </div>

            <div id="problem-description" class="markdown-body" style="flex:1; overflow-y:auto; line-height:1.75; font-size:1.05rem; color:#e2e8f0;">
              ${promptHtml}
            </div>

            ${hasHints ? `
              <div style="margin-top:16px; padding:12px 14px; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                  <span style="font-size:0.95rem; font-weight:600; color:#fbbf24;">💡 Indice (Pénalité 50%/100%)</span>
                  <button id="btn-request-hint" class="btn btn-secondary" style="font-size:0.88rem; padding:5px 12px; font-weight:600;">
                    Afficher indice
                  </button>
                </div>
                <div id="hint-display-area" style="margin-top:8px; font-size:0.95rem; line-height:1.5; color:#fef3c7; display:none;"></div>
              </div>
            ` : ''}
          </div>

          <!-- DRAGGABLE SPLITTER -->
          <div class="split-pane-divider" id="vertical-splitter"></div>

          <!-- RIGHT PANE: Code Editor & Bottom Console/Tests -->
          <div class="editor-pane" style="width:calc(56% - 5px); flex:1; display:flex; flex-direction:column; background:#0a0f1d; overflow:hidden;">
            <!-- Top Toolbar -->
            <div class="editor-toolbar" style="padding:10px 16px; background:#070b14; border-bottom:1px solid rgba(255,255,255,0.08); display:flex; align-items:center; gap:8px;">
              <button id="undo-btn" class="toolbar-btn" style="padding:6px 12px; font-size:1.05rem; border-radius:6px;" title="Annuler (Ctrl+Z)">↩️</button>
              <button id="redo-btn" class="toolbar-btn" style="padding:6px 12px; font-size:1.05rem; border-radius:6px;" title="Refaire (Ctrl+Y)">↪️</button>
              <div class="toolbar-separator" style="width:1px; height:20px; background:rgba(255,255,255,0.15); margin:0 4px;"></div>
              <button id="comment-btn" class="toolbar-btn" style="padding:6px 12px; font-size:1.05rem; border-radius:6px;" title="Commenter (Ctrl+/)">💬</button>
              <button id="reset-template-btn" class="toolbar-btn" style="padding:6px 12px; font-size:1.05rem; border-radius:6px;" title="Réinitialiser le code">🔄</button>
              <div class="toolbar-separator" style="width:1px; height:20px; background:rgba(255,255,255,0.15); margin:0 4px;"></div>
              <span style="font-size:0.95rem; font-weight:600; color:var(--text-secondary);">🐍 Python 3</span>
              <div id="coding-status-indicator" style="margin-left:auto; font-size:0.92rem; color:#10b981; font-weight:600; display:flex; align-items:center; gap:6px;">
                <span class="status-pulse-dot" style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981;"></span> Prêt
              </div>
            </div>

          <!-- CodeMirror Wrapper -->
          <div class="editor-wrapper" id="editor-wrapper" style="height:calc(55% - 5px); min-height:180px; position:relative; overflow:hidden;">
            <textarea id="input-coding-editor" style="display:none;">${this._escapeHtml(codeVal)}</textarea>
          </div>

          <!-- Status Bar -->
          <div id="editor-status-bar" class="editor-status-bar" style="display:flex; justify-content:space-between; align-items:center; padding:6px 16px; font-size:0.88rem; height:34px; background:#070b14; border-top:1px solid rgba(255,255,255,0.06); color:var(--text-muted); font-family:var(--font-mono);">
            <div class="status-left" style="display:flex; gap:10px; align-items:center;">
              <span id="status-cursor">Ln 1, Col 1</span>
              <span class="status-sep">|</span>
              <span id="status-lines">0 lignes</span>
              <span class="status-sep">|</span>
              <span id="status-chars">0 car.</span>
            </div>
            <div class="status-right" style="display:flex; gap:8px; align-items:center;">
              <button id="wordwrap-btn" class="status-btn" style="background:none; border:none; color:inherit; cursor:pointer; font-size:0.88rem; font-weight:600; padding:2px 6px;">Wrap</button>
              <span class="status-sep">|</span>
              <button id="font-decrease-btn" class="status-btn" style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:inherit; cursor:pointer; font-size:0.88rem; font-weight:700; padding:2px 8px; border-radius:4px;">A-</button>
              <span id="status-fontsize" style="font-weight:700; font-size:0.88rem; color:#f8fafc; min-width:36px; text-align:center;">16px</span>
              <button id="font-increase-btn" class="status-btn" style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:inherit; cursor:pointer; font-size:0.88rem; font-weight:700; padding:2px 8px; border-radius:4px;">A+</button>
            </div>
          </div>

          <!-- Horizontal Splitter -->
          <div class="h-splitter" id="horizontal-splitter"></div>

          <!-- Bottom Pane -->
          <div class="bottom-pane" id="bottom-pane" style="height:45%; min-height:180px; display:flex; flex-direction:column; background:#060a12; border-top:1px solid rgba(255,255,255,0.08);">
            <div class="tabs-header" style="display:flex; align-items:center; padding:8px 16px; background:#0a0f1d; border-bottom:1px solid rgba(255,255,255,0.08); gap:10px;">
              <button class="tab-btn active" id="tab-btn-console" data-target="tab-console" style="padding:8px 16px; font-size:0.95rem; border-radius:6px; cursor:pointer; font-weight:600;">
                🖥️ Console E/S
              </button>
              <button class="tab-btn" id="tab-btn-tests" data-target="tab-tests" style="padding:8px 16px; font-size:0.95rem; border-radius:6px; cursor:pointer; font-weight:600;">
                🧪 Cas de Test (${validPublicTests.length} publics)
              </button>

              <div style="flex-grow:1;"></div>
              <button class="btn btn-secondary" id="run-stdin-btn" style="padding:8px 16px; font-size:0.95rem; font-weight:600; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                ▶️ Exécuter (stdin)
              </button>
              <button class="btn btn-primary" id="run-tests-btn" style="padding:9px 20px; font-size:1rem; font-weight:700; background:#2563eb; border-radius:6px; box-shadow:0 3px 12px rgba(37,99,235,0.45); display:inline-flex; align-items:center; gap:6px;">
                ⚡ Tester ma Solution
              </button>
              <button class="btn btn-success" id="btn-save-coding" style="padding:9px 18px; font-size:0.95rem; font-weight:600; background:#10b981; border:none; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                💾 Enregistrer
              </button>
            </div>

            <!-- Tab Console -->
            <div class="tab-content" id="tab-console" style="display:flex; flex:1; padding:12px 16px; gap:14px; overflow:hidden;">
              <div class="console-input-section" style="flex:1; display:flex; flex-direction:column;">
                <span style="font-size:0.88rem; color:var(--text-muted); font-weight:600; margin-bottom:6px;">Entrée standard (stdin) :</span>
                <textarea id="custom-input" placeholder="Saisissez vos données d'entrée..." style="flex:1; width:100%; font-family:var(--font-mono); font-size:0.95rem; padding:10px 14px; border-radius:6px; border:1px solid rgba(255,255,255,0.12); background:#0b1120; color:#e2e8f0; resize:none; line-height:1.5;">${this._escapeHtml(sampleInput)}</textarea>
              </div>
              <div class="console-output-section" style="flex:1.2; display:flex; flex-direction:column;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                  <span style="font-size:0.88rem; color:var(--text-muted); font-weight:600;">Sortie console (stdout) :</span>
                  <button id="clear-console-btn" class="btn btn-secondary" style="padding:3px 10px; font-size:0.82rem; font-weight:600; border-radius:4px;">Effacer</button>
                </div>
                <pre id="console-logs" class="output-logs" style="flex:1; margin:0; padding:12px 14px; background:#04070e; color:#a7f3d0; border-radius:6px; border:1px solid rgba(255,255,255,0.08); overflow-y:auto; font-size:0.95rem; font-family:var(--font-mono); white-space:pre-wrap; line-height:1.6;">(En attente d'exécution)</pre>
                <div id="console-figures" style="display:none; margin-top:10px; overflow-y:auto; max-height:240px; flex-direction:column; gap:10px;"></div>
              </div>
            </div>

            <!-- Tab Tests -->
            <div class="tab-content" id="tab-tests" style="display:none; flex:1; padding:14px 18px; overflow-y:auto;">
              <div id="test-cases-summary" style="margin-bottom:12px; font-size:1.02rem; font-weight:700; color:#93c5fd;"></div>
              <div id="test-cases-list" style="display:flex; flex-direction:column; gap:12px;">
                ${validPublicTests.map((tc, idx) => `
                  <div class="test-case-card" id="test-case-card-${idx}" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                      <span style="font-weight:700; font-size:0.95rem; color:#60a5fa;">Cas de test #${idx + 1} (Public)</span>
                      <span class="test-status-pill" id="test-status-${idx}" style="font-size:0.85rem; padding:4px 12px; border-radius:12px; background:rgba(255,255,255,0.08); color:var(--text-muted); font-weight:600;">Non exécuté</span>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:0.92rem; font-family:var(--font-mono);">
                      <div>
                        <div style="color:var(--text-muted); font-size:0.82rem; font-weight:600; margin-bottom:4px;">Entrée :</div>
                        <div class="io-block" style="background:#070b14; padding:10px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.08); white-space:pre-wrap; line-height:1.5;">${this._escapeHtml(tc.input || '(Vide)')}</div>
                      </div>
                      <div>
                        <div style="color:var(--text-muted); font-size:0.82rem; font-weight:600; margin-bottom:4px;">Sortie attendue :</div>
                        <div class="io-block" style="background:#070b14; padding:10px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.08); white-space:pre-wrap; line-height:1.5;">${this._escapeHtml(tc.expected_output || tc.output || '(Vide)')}</div>
                      </div>
                    </div>
                    <div id="test-actual-row-${idx}" style="display:none; margin-top:10px; font-size:0.92rem; font-family:var(--font-mono);">
                      <div style="color:var(--text-muted); font-size:0.82rem; font-weight:600; margin-bottom:4px;">Votre sortie :</div>
                      <div id="test-actual-out-${idx}" class="io-block" style="background:#070b14; padding:10px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.08); white-space:pre-wrap; line-height:1.5;"></div>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // KaTeX Math Rendering on Description Pane
    if (window.renderMathInElement) {
      try {
        window.renderMathInElement(container.querySelector('.problem-pane'), {
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

    this._attachCodingChallengeListeners(q, validPublicTests);
  }

  // --- Écouteurs & Logique Interactive Défi AlgoCompiler ---
  _attachCodingChallengeListeners(question, validPublicTests) {
    const qId = question.id;

    // Navigation Défi Précédent / Suivant (Intégrée au Panneau d'Énoncé)
    const btnChPrev = document.getElementById('btn-challenge-prev');
    const btnChNext = document.getElementById('btn-challenge-next');
    if (btnChPrev) {
      btnChPrev.onclick = () => {
        if (this.currentIndex > 0) this.goToQuestion(this.currentIndex - 1);
      };
    }
    if (btnChNext) {
      btnChNext.onclick = () => {
        if (this.currentIndex < this.questions.length - 1) this.goToQuestion(this.currentIndex + 1);
      };
    }

    // Navigation directe via les pilules de tous les défis de la série
    document.querySelectorAll('.coding-nav-pill').forEach(pill => {
      pill.onclick = () => {
        const targetIdx = parseInt(pill.getAttribute('data-idx'), 10);
        if (!isNaN(targetIdx) && targetIdx !== this.currentIndex) {
          this.goToQuestion(targetIdx);
        }
      };
    });

    // 1. Flag bouton
    const flagBtn = document.getElementById('btn-flag-question');
    if (flagBtn) {
      flagBtn.onclick = () => {
        if (this.flaggedQuestions.has(qId)) this.flaggedQuestions.delete(qId);
        else this.flaggedQuestions.add(qId);
        this.render();
      };
    }

    // 2. Vertical Splitter Dragging
    const vSplitter = document.getElementById('vertical-splitter');
    const problemPane = document.querySelector('.problem-pane');
    const editorPane = document.querySelector('.editor-pane');
    const challengeLayout = document.querySelector('.challenge-layout');

    if (vSplitter && problemPane && editorPane && challengeLayout) {
      let isDragging = false;
      vSplitter.onmousedown = (e) => {
        isDragging = true;
        vSplitter.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        e.preventDefault();
      };
      const onMouseMove = (e) => {
        if (!isDragging) return;
        const rect = challengeLayout.getBoundingClientRect();
        let pct = ((e.clientX - rect.left) / rect.width) * 100;
        if (pct < 22) pct = 22;
        if (pct > 65) pct = 65;
        problemPane.style.width = `${pct}%`;
        editorPane.style.width = `calc(${100 - pct}% - 5px)`;
        if (cmInstance) cmInstance.refresh();
      };
      const onMouseUp = () => {
        if (isDragging) {
          isDragging = false;
          vSplitter.classList.remove('dragging');
          document.body.style.cursor = '';
        }
      };
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    }

    // 3. Horizontal Splitter Dragging
    const hSplitter = document.getElementById('horizontal-splitter');
    const editorWrapper = document.getElementById('editor-wrapper');
    const bottomPane = document.getElementById('bottom-pane');

    if (hSplitter && editorWrapper && bottomPane && editorPane) {
      let isHDragging = false;
      hSplitter.onmousedown = (e) => {
        isHDragging = true;
        hSplitter.classList.add('dragging');
        document.body.style.cursor = 'row-resize';
        e.preventDefault();
      };
      const onHMouseMove = (e) => {
        if (!isHDragging) return;
        const rect = editorPane.getBoundingClientRect();
        let pct = ((e.clientY - rect.top) / rect.height) * 100;
        if (pct < 25) pct = 25;
        if (pct > 78) pct = 78;
        editorWrapper.style.height = `calc(${pct}% - 5px)`;
        bottomPane.style.height = `${100 - pct}%`;
        if (cmInstance) cmInstance.refresh();
      };
      const onHMouseUp = () => {
        if (isHDragging) {
          isHDragging = false;
          hSplitter.classList.remove('dragging');
          document.body.style.cursor = '';
        }
      };
      document.addEventListener('mousemove', onHMouseMove);
      document.addEventListener('mouseup', onHMouseUp);
    }

    // 4. Tabs switching
    const tabConsoleBtn = document.getElementById('tab-btn-console');
    const tabTestsBtn = document.getElementById('tab-btn-tests');
    const tabConsole = document.getElementById('tab-console');
    const tabTests = document.getElementById('tab-tests');

    if (tabConsoleBtn && tabTestsBtn && tabConsole && tabTests) {
      tabConsoleBtn.onclick = () => {
        tabConsoleBtn.classList.add('active');
        tabTestsBtn.classList.remove('active');
        tabConsole.style.display = 'flex';
        tabTests.style.display = 'none';
      };
      tabTestsBtn.onclick = () => {
        tabTestsBtn.classList.add('active');
        tabConsoleBtn.classList.remove('active');
        tabConsole.style.display = 'none';
        tabTests.style.display = 'block';
      };
    }

    // Clear console
    const clearBtn = document.getElementById('clear-console-btn');
    const consoleLogs = document.getElementById('console-logs');
    const consoleFigures = document.getElementById('console-figures');
    if (clearBtn && consoleLogs) {
      clearBtn.onclick = () => {
        consoleLogs.textContent = "(Console effacée)";
        consoleLogs.style.color = "var(--text-muted)";
        if (consoleFigures) {
          consoleFigures.innerHTML = '';
          consoleFigures.style.display = 'none';
        }
      };
    }

    // 5. CodeMirror Editor Setup
    const editorEl = document.getElementById('input-coding-editor');
    const initialCode = this.answers[qId] !== undefined ? this.answers[qId] : (question.starter_code || (question.options && question.options.starter_code) || (editorEl ? editorEl.value : '') || '');
    this.answers[qId] = initialCode;

    let cmInstance = null;
    let currentFontSize = 16;

    const updateStatusBar = () => {
      if (!cmInstance) return;
      const cur = cmInstance.getCursor();
      const lineCount = cmInstance.lineCount();
      const charCount = cmInstance.getValue().length;
      const curEl = document.getElementById('status-cursor');
      const linesEl = document.getElementById('status-lines');
      const charsEl = document.getElementById('status-chars');
      if (curEl) curEl.textContent = `Ln ${cur.line + 1}, Col ${cur.ch + 1}`;
      if (linesEl) linesEl.textContent = `${lineCount} lignes`;
      if (charsEl) charsEl.textContent = `${charCount} car.`;
    };

    if (window.CodeMirror && editorEl) {
      if (editorEl._cmInstance) {
        try { editorEl._cmInstance.toTextArea(); } catch (_) {}
      }
      cmInstance = window.CodeMirror.fromTextArea(editorEl, {
        mode: 'python',
        theme: 'dracula',
        lineNumbers: true,
        indentUnit: 4,
        tabSize: 4,
        matchBrackets: true,
        autoCloseBrackets: true,
        lineWrapping: true,
        extraKeys: {
          "Ctrl-Space": (cm) => {
            const hintFn = (window.CodeMirror && window.CodeMirror.hint && window.CodeMirror.hint.python) || null;
            if (typeof cm.showHint === 'function') {
              cm.showHint({ hint: hintFn, completeSingle: false });
            }
          },
          "Esc": (cm) => {
            if (cm.state.completionActive) {
              cm.state.completionActive.close();
            }
            const hints = document.querySelector('.CodeMirror-hints');
            if (hints) hints.remove();
          },
          "Tab": (cm) => {
            if (cm.somethingSelected()) {
              cm.indentSelection("add");
            } else {
              cm.replaceSelection("    ", "end");
            }
          }
        }
      });
      editorEl._cmInstance = cmInstance;
      this._cmInstance = cmInstance;
      cmInstance.setValue(initialCode);
      cmInstance.setSize('100%', '100%');
      const cmWrapper = cmInstance.getWrapperElement();
      if (cmWrapper) cmWrapper.style.fontSize = `${currentFontSize}px`;

      // IntelliSense Python Autocomplete automatique à la frappe (sur '.' ou mot >= 2 car.)
      cmInstance.on('inputRead', (cm, change) => {
        if (change.origin !== '+input') return;
        const text = change.text[0];
        if (!text || text === ' ' || text === '\n' || text === '\t') return;
        
        let shouldTrigger = false;
        if (text === '.') {
          shouldTrigger = true;
        } else if (/[a-zA-Z_]/.test(text)) {
          const cur = cm.getCursor();
          const line = cm.getLine(cur.line);
          const before = line.slice(0, cur.ch);
          const match = before.match(/[a-zA-Z_0-9]+$/);
          if (match && match[0].length >= 2) {
            shouldTrigger = true;
          }
        }

        if (shouldTrigger && !cm.state.completionActive && typeof cm.showHint === 'function') {
          const hintFn = (window.CodeMirror && window.CodeMirror.hint && window.CodeMirror.hint.python) || null;
          cm.showHint({ hint: hintFn, completeSingle: false });
        }
      });

      cmInstance.on('change', () => {
        this.answers[qId] = cmInstance.getValue();
        this._renderPalette();
        updateStatusBar();
      });
      cmInstance.on('cursorActivity', updateStatusBar);
      setTimeout(() => {
        cmInstance.refresh();
        updateStatusBar();
      }, 50);
    } else if (editorEl) {
      editorEl.style.display = 'block';
      editorEl.value = initialCode;
      editorEl.oninput = (e) => {
        this.answers[qId] = e.target.value;
        this._renderPalette();
      };
    }

    // 6. Toolbar Buttons
    const undoBtn = document.getElementById('undo-btn');
    const redoBtn = document.getElementById('redo-btn');
    const commentBtn = document.getElementById('comment-btn');
    const resetBtn = document.getElementById('reset-template-btn');
    const wordwrapBtn = document.getElementById('wordwrap-btn');
    const fontDecBtn = document.getElementById('font-decrease-btn');
    const fontIncBtn = document.getElementById('font-increase-btn');
    const fontDisplay = document.getElementById('status-fontsize');

    if (undoBtn && cmInstance) undoBtn.onclick = () => cmInstance.undo();
    if (redoBtn && cmInstance) redoBtn.onclick = () => cmInstance.redo();
    if (commentBtn && cmInstance) {
      commentBtn.onclick = () => {
        const cur = cmInstance.getCursor();
        const line = cmInstance.getLine(cur.line);
        if (line.trim().startsWith('#')) {
          const idx = line.indexOf('#');
          cmInstance.replaceRange('', { line: cur.line, ch: idx }, { line: cur.line, ch: idx + 1 + (line[idx + 1] === ' ' ? 1 : 0) });
        } else {
          cmInstance.replaceRange('# ', { line: cur.line, ch: 0 });
        }
      };
    }
    if (resetBtn && cmInstance) {
      resetBtn.onclick = () => {
        if (confirm("Réinitialiser le code au modèle de départ ? Votre code actuel sera écrasé.")) {
          const starter = question.starter_code || (question.options && question.options.starter_code) || '# Écrivez votre code Python ici\n';
          cmInstance.setValue(starter);
          this.answers[qId] = starter;
          this._renderPalette();
        }
      };
    }
    if (wordwrapBtn && cmInstance) {
      wordwrapBtn.onclick = () => {
        const current = cmInstance.getOption('lineWrapping');
        cmInstance.setOption('lineWrapping', !current);
        wordwrapBtn.style.color = !current ? '#60a5fa' : 'inherit';
      };
    }
    if (fontDecBtn && fontIncBtn && cmInstance) {
      const applyFontSize = () => {
        const wrapper = cmInstance.getWrapperElement();
        if (wrapper) wrapper.style.fontSize = `${currentFontSize}px`;
        if (fontDisplay) fontDisplay.textContent = `${currentFontSize}px`;
        cmInstance.refresh();
      };
      fontDecBtn.onclick = () => {
        if (currentFontSize > 11) {
          currentFontSize--;
          applyFontSize();
        }
      };
      fontIncBtn.onclick = () => {
        if (currentFontSize < 30) {
          currentFontSize++;
          applyFontSize();
        }
      };
    }

    // 7. Exécuter avec Entrée (stdin)
    const runStdinBtn = document.getElementById('run-stdin-btn');
    if (runStdinBtn) {
      runStdinBtn.onclick = async () => {
        const codeToRun = cmInstance ? cmInstance.getValue() : (editorEl ? editorEl.value : '');
        const stdinInput = document.getElementById('custom-input');
        const inputVal = stdinInput ? stdinInput.value : '';

        if (tabConsoleBtn) tabConsoleBtn.click();

        runStdinBtn.disabled = true;
        runStdinBtn.innerHTML = '⏳ Exécution...';
        if (consoleLogs) {
          consoleLogs.textContent = 'Exécution du code Python sur le serveur...\n';
          consoleLogs.style.color = '#93c5fd';
        }

        try {
          const res = await api.runPythonCode(codeToRun, inputVal);
          if (consoleLogs) {
            if (res.error) {
              consoleLogs.style.color = '#f87171';
              consoleLogs.textContent = `❌ Erreur d'exécution (${res.execution_time_ms} ms) :\n${res.error}`;
            } else {
              consoleLogs.style.color = '#a7f3d0';
              consoleLogs.textContent = res.stdout || `(Exécution terminée avec succès en ${res.execution_time_ms} ms sans affichage standard)`;
            }
          }

          // Visualisation des graphiques (Matplotlib, Seaborn)
          const figContainer = document.getElementById('console-figures');
          if (figContainer) {
            figContainer.innerHTML = '';
            if (res.figures && res.figures.length > 0) {
              figContainer.style.display = 'flex';
              res.figures.forEach((fUrl, fIdx) => {
                const imgWrap = document.createElement('div');
                imgWrap.style = "background:#fff; padding:6px; border-radius:6px; box-shadow:0 4px 14px rgba(0,0,0,0.4); text-align:center;";
                imgWrap.innerHTML = `
                  <div style="font-size:0.72rem; color:#64748b; margin-bottom:4px; font-weight:600;">📊 Graphique généré #${fIdx + 1}</div>
                  <img src="${fUrl}" alt="Graphique #${fIdx + 1}" style="max-width:100%; height:auto; border-radius:4px;" />
                `;
                figContainer.appendChild(imgWrap);
              });
            } else {
              figContainer.style.display = 'none';
            }
          }
        } catch (err) {
          if (consoleLogs) {
            consoleLogs.style.color = '#f87171';
            consoleLogs.textContent = `❌ Erreur réseau ou système : ${err.message}`;
          }
        } finally {
          runStdinBtn.disabled = false;
          runStdinBtn.innerHTML = '▶️ Exécuter (stdin)';
        }
      };
    }

    // 8. Tester ma Solution (sur les cas de test publics)
    const runTestsBtn = document.getElementById('run-tests-btn');
    if (runTestsBtn) {
      runTestsBtn.onclick = async () => {
        const codeToRun = cmInstance ? cmInstance.getValue() : (editorEl ? editorEl.value : '');
        if (tabTestsBtn) tabTestsBtn.click();

        runTestsBtn.disabled = true;
        runTestsBtn.innerHTML = '⏳ Exécution...';

        const summaryEl = document.getElementById('test-cases-summary');
        if (summaryEl) summaryEl.textContent = "Exécution des cas de test en cours...";

        try {
          const res = await api.runPythonTests(codeToRun, validPublicTests, false);
          if (res.success && Array.isArray(res.results)) {
            let passedCount = 0;
            res.results.forEach((r, idx) => {
              if (r.passed) passedCount++;
              const pill = document.getElementById(`test-status-${idx}`);
              const actualRow = document.getElementById(`test-actual-row-${idx}`);
              const actualOut = document.getElementById(`test-actual-out-${idx}`);

              if (pill) {
                if (r.passed) {
                  pill.textContent = `✅ Réussi (${r.execution_time_ms} ms)`;
                  pill.style.background = 'rgba(16,185,129,0.2)';
                  pill.style.color = '#6ee7b7';
                  pill.style.border = '1px solid #10b981';
                } else {
                  pill.textContent = `❌ Échoué (${r.execution_time_ms} ms)`;
                  pill.style.background = 'rgba(239,68,68,0.2)';
                  pill.style.color = '#fca5a5';
                  pill.style.border = '1px solid #ef4444';
                }
              }

              if (actualRow && actualOut) {
                actualRow.style.display = 'block';
                actualOut.textContent = r.error ? `Erreur: ${r.error}` : (r.actual_output || '(Vide)');
                actualOut.style.color = r.passed ? '#6ee7b7' : '#fca5a5';
              }
            });

            if (summaryEl) {
              if (res.all_passed) {
                summaryEl.innerHTML = `<span style="color:#10b981;">🎉 Tous les tests publics validés (${res.passed_count}/${res.total_count}) ! Temps moy: ${res.avg_execution_time_ms} ms</span>`;
              } else {
                summaryEl.innerHTML = `<span style="color:#f59e0b;">⚠️ ${res.passed_count}/${res.total_count} cas de test publics validés. Consultez les divergences ci-dessous.</span>`;
              }
            }
          }
        } catch (err) {
          if (summaryEl) summaryEl.innerHTML = `<span style="color:#ef4444;">Erreur: ${err.message}</span>`;
        } finally {
          runTestsBtn.disabled = false;
          runTestsBtn.innerHTML = '⚡ Tester ma Solution';
        }
      };
    }

    // 9. Enregistrer la solution
    const saveBtn = document.getElementById('btn-save-coding');
    const statusInd = document.getElementById('coding-status-indicator');
    if (saveBtn) {
      saveBtn.onclick = async () => {
        const codeToSave = cmInstance ? cmInstance.getValue() : (editorEl ? editorEl.value : '');
        this.answers[qId] = codeToSave;
        this._renderPalette();

        if (statusInd) {
          statusInd.innerHTML = '<span style="color:#60a5fa;">⏳ Enregistrement...</span>';
        }

        if (!this.isPracticeMode && this.attemptId) {
          const res = await api.saveAnswer(this.attemptId, qId, codeToSave);
          if (res && res.remaining_seconds !== undefined) this.syncServerRemainingSeconds(res.remaining_seconds);
        }

        if (statusInd) {
          statusInd.innerHTML = '<span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10b981; box-shadow:0 0 6px #10b981;"></span> <span style="color:#10b981;">Enregistré ✅</span>';
          setTimeout(() => {
            if (statusInd) {
              statusInd.innerHTML = '<span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10b981;"></span> Prêt';
            }
          }, 2500);
        }
      };
    }

    // 10. Hints Handler
    const hintBtn = document.getElementById('btn-request-hint');
    const hintBox = document.getElementById('hint-display-area');
    if (!window.pythonHintsUsed) window.pythonHintsUsed = {};
    if (window.pythonHintsUsed[qId] === undefined) window.pythonHintsUsed[qId] = 0;

    if (hintBtn && hintBox) {
      const currentHints = window.pythonHintsUsed[qId];
      if (currentHints === 1 && question.hint1) {
        hintBox.style.display = 'block';
        hintBox.innerHTML = `<strong>Indice 1 :</strong> ${this._escapeHtml(question.hint1)}`;
        if (question.hint2) hintBtn.textContent = "Afficher l'indice 2 (Pénalité 100%)";
        else hintBtn.disabled = true;
      } else if (currentHints >= 2 && question.hint2) {
        hintBox.style.display = 'block';
        hintBox.innerHTML = `<strong>Indice 1 :</strong> ${this._escapeHtml(question.hint1 || '')}<br/><strong>Indice 2 :</strong> ${this._escapeHtml(question.hint2)}`;
        hintBtn.disabled = true;
        hintBtn.textContent = "Tous les indices affichés";
      }

      hintBtn.onclick = () => {
        if (window.pythonHintsUsed[qId] === 0 && question.hint1) {
          window.pythonHintsUsed[qId] = 1;
          hintBox.style.display = 'block';
          hintBox.innerHTML = `<strong>Indice 1 :</strong> ${this._escapeHtml(question.hint1)}`;
          if (question.hint2) {
            hintBtn.textContent = "Afficher l'indice 2 (Pénalité 100%)";
          } else {
            hintBtn.disabled = true;
          }
        } else if (window.pythonHintsUsed[qId] === 1 && question.hint2) {
          window.pythonHintsUsed[qId] = 2;
          hintBox.innerHTML += `<br/><strong>Indice 2 :</strong> ${this._escapeHtml(question.hint2)}`;
          hintBtn.disabled = true;
          hintBtn.textContent = "Tous les indices affichés";
        }
      };
    }
  }

  // --- Rendu du Layout Défi Linux Shell (Terminal & VFS interactif) ---
  _renderLinuxChallenge(container, q, topicClean, topicBadgeHtml, diffBadgeHtml, typeLabels, promptHtml) {
    const codeVal = this.answers[q.id] !== undefined ? this.answers[q.id] : (q.starter_code || '# Tapez vos commandes Linux\n');
    const publicTests = q.public_tests || [];
    const hiddenTests = q.hidden_tests || [];
    const isFlagged = this.flaggedQuestions.has(q.id);
    const answeredCodingCount = this.questions.filter(ques => this._hasAnswer(ques.id)).length;

    // Arborescence initiale pour l'étudiant
    let initialFsHtml = '';
    if (q.initial_fs && typeof q.initial_fs === 'object') {
      const fsEntries = [];
      for (const [dir, dDef] of Object.entries(q.initial_fs)) {
        fsEntries.push(`<div style="color:#60a5fa; font-weight:700;">📁 ${this._escapeHtml(dir)}/</div>`);
        if (dDef.files) {
          for (const [fname, fDef] of Object.entries(dDef.files)) {
            const isD = fDef.type === 'dir';
            fsEntries.push(`<div style="margin-left:16px; color:${isD ? '#93c5fd' : '#cbd5e1'};">
              ${isD ? '📁' : '📄'} <strong>${this._escapeHtml(fname)}</strong>
              ${fDef.content ? `<span style="color:#64748b; font-size:0.75rem;">(${fDef.content.trim().slice(0, 30)}…)</span>` : ''}
            </div>`);
          }
        }
      }
      initialFsHtml = `
        <div style="margin-top:16px; padding:12px 14px; background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.08); border-radius:8px;">
          <div style="font-size:0.82rem; font-weight:700; color:#93c5fd; text-transform:uppercase; margin-bottom:8px;">
            🗂️ État initial du Système de Fichiers (VFS) :
          </div>
          <div style="font-family:var(--font-mono); font-size:0.85rem; line-height:1.6;">
            ${fsEntries.join('')}
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="practical-workspace-container" style="display:flex; flex-direction:column; height:100%; width:100%; overflow:hidden;">
        <!-- BANDEAU DE NAVIGATION INTERACTIF DES DÉFIS -->
        <div class="coding-navigator-bar" style="display:flex; align-items:center; justify-content:space-between; padding:8px 16px; background:#070b16; border-bottom:1px solid rgba(255,255,255,0.08); gap:14px; min-height:46px; box-sizing:border-box;">
          <div style="display:flex; align-items:center; gap:8px; overflow-x:auto; flex:1; scrollbar-width:thin;">
            <span style="font-size:0.92rem; font-weight:700; color:#60a5fa; text-transform:uppercase; letter-spacing:0.04em; white-space:nowrap; margin-right:6px;">
              🐧 Défis Linux (${this.questions.length}) :
            </span>
            ${this.questions.map((ques, idx) => {
              const hasAns = this._hasAnswer(ques.id);
              const isCur = idx === this.currentIndex;
              const isFlag = this.flaggedQuestions.has(ques.id);
              const qTitle = ques.topic || ques.title || `Défi ${idx + 1}`;
              const shortTitle = qTitle.length > 22 ? qTitle.slice(0, 20) + '…' : qTitle;
              let icon = isCur ? '⚡' : (hasAns ? '✅' : '○');
              if (isFlag) icon = '🚩';

              const borderCol = isCur ? '#3b82f6' : (hasAns ? '#10b981' : (isFlag ? '#f59e0b' : 'rgba(255,255,255,0.15)'));
              const bgCol = isCur ? 'rgba(59,130,246,0.22)' : (hasAns ? 'rgba(16,185,129,0.14)' : (isFlag ? 'rgba(245,158,11,0.15)' : 'rgba(255,255,255,0.03)'));
              const textCol = isCur ? '#bfdbfe' : (hasAns ? '#a7f3d0' : (isFlag ? '#fcd34d' : '#94a3b8'));
              return `
                <button class="coding-nav-pill" data-idx="${idx}" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; font-size:0.92rem; font-weight:600; border-radius:16px; border:1px solid ${borderCol}; background:${bgCol}; color:${textCol}; cursor:pointer; white-space:nowrap; transition:all 0.15s ease;">
                  <span style="font-size:1rem;">${icon}</span>
                  <span>#${idx + 1} ${this._escapeHtml(shortTitle)}</span>
                </button>
              `;
            }).join('')}
          </div>
          <div style="display:flex; align-items:center; gap:10px; white-space:nowrap;">
            <span style="font-size:0.92rem; color:var(--text-muted); font-family:var(--font-mono);">
              Avancement : <strong style="color:#10b981; font-size:1rem;">${answeredCodingCount}</strong> / ${this.questions.length} résolu(s)
            </span>
          </div>
        </div>

        <div class="challenge-layout fused-workspace" style="flex:1; height:calc(100% - 46px); min-height:0; display:flex;">
          <!-- LEFT PANE: Description -->
          <div class="problem-pane" style="width:42%; min-width:300px; max-width:65%; padding:20px; overflow-y:auto; border-right:1px solid rgba(255,255,255,0.08); background:var(--bg-surface);">
            <div class="problem-header" style="margin-bottom:16px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                  ${topicBadgeHtml}
                  ${diffBadgeHtml}
                  <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); font-size:0.75rem; padding:3px 9px; border-radius:12px; font-weight:600;">🐧 Linux Shell POSIX</span>
                </div>
                <div style="display:flex; align-items:center; gap:10px;">
                  <span class="question-points" style="font-weight:700; color:#f8fafc; font-size:1rem;">${q.points} pt(s)</span>
                  <button id="btn-flag-question" class="btn btn-secondary" style="padding:4px 10px; font-size:0.8rem;">
                    ${isFlagged ? '🚩 Marqué' : '🏳️ Marquer'}
                  </button>
                </div>
              </div>
              <h2 style="font-size:1.3rem; margin:0 0 6px 0; color:var(--text-primary); font-weight:700;">
                #${this.currentIndex + 1} ${this._escapeHtml(q.title || 'Défi Ligne de Commande')}
              </h2>
            </div>

            <div class="problem-body" style="font-size:1.02rem; line-height:1.7; color:#e2e8f0;">
              ${promptHtml}
            </div>

            ${initialFsHtml}

            <!-- Résumé des tests publics attendus -->
            <div style="margin-top:20px; padding:12px 14px; background:rgba(59,130,246,0.06); border:1px solid rgba(59,130,246,0.2); border-radius:8px;">
              <div style="font-size:0.85rem; font-weight:700; color:#93c5fd; margin-bottom:6px;">
                🎯 Spécifications d'évaluation :
              </div>
              <div style="font-size:0.88rem; color:var(--text-secondary); line-height:1.5;">
                • ${publicTests.length} tests publics visibles<br/>
                • ${hiddenTests.length} tests cachés d'intégrité système (arborescence, permissions, codes de retour)
              </div>
            </div>
          </div>

          <!-- Splitter -->
          <div class="v-splitter" id="vertical-splitter" style="width:6px; cursor:col-resize; background:rgba(255,255,255,0.03);"></div>

          <!-- RIGHT PANE: Workspace Shell & Terminal -->
          <div class="editor-pane" style="flex:1; display:flex; flex-direction:column; min-width:350px; background:#070b14; overflow:hidden;">
            <!-- Haut : Éditeur de commandes -->
            <div style="height:35%; min-height:130px; display:flex; flex-direction:column; border-bottom:1px solid rgba(255,255,255,0.08);">
              <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 14px; background:#0a0f1d; border-bottom:1px solid rgba(255,255,255,0.06);">
                <span style="font-size:0.85rem; color:#94a3b8; font-weight:600;">
                  📝 Commandes / Script à soumettre :
                </span>
                <span id="linux-editor-status" style="font-size:0.8rem; color:#10b981; font-weight:600;">
                  Prêt
                </span>
              </div>
              <textarea id="linux-script-editor" style="flex:1; width:100%; background:#050811; color:#f8fafc; font-family:var(--font-mono); font-size:1rem; padding:12px; border:none; resize:none; outline:none; line-height:1.6;" placeholder="# Tapez vos commandes Linux ici (ex: pwd && ls -la)">${this._escapeHtml(codeVal)}</textarea>
            </div>

            <!-- Bas : Terminal interactif & Onglet Tests -->
            <div style="flex:1; display:flex; flex-direction:column; min-height:220px; background:#04070e;">
              <!-- Barre d'outils et sélecteur d'onglets -->
              <div class="tabs-header" style="display:flex; align-items:center; padding:8px 14px; background:#0a0f1d; border-bottom:1px solid rgba(255,255,255,0.08); gap:10px; flex-wrap:wrap;">
                <button class="tab-btn active" id="tab-btn-linux-term" data-target="tab-linux-term" style="padding:7px 14px; font-size:0.92rem; border-radius:6px; cursor:pointer; font-weight:600;">
                  🖥️ Terminal Shell POSIX
                </button>
                <button class="tab-btn" id="tab-btn-linux-tests" data-target="tab-linux-tests" style="padding:7px 14px; font-size:0.92rem; border-radius:6px; cursor:pointer; font-weight:600;">
                  🧪 Cas de Test (${publicTests.length} publics)
                </button>

                <div style="flex-grow:1;"></div>

                <button class="btn btn-secondary" id="btn-linux-reset-vfs" title="Réinitialiser l'arborescence à son état d'origine" style="padding:7px 12px; font-size:0.88rem; font-weight:600; border-radius:6px;">
                  🔄 Réinit VFS
                </button>
                <button class="btn btn-secondary" id="btn-linux-run-script" style="padding:7px 14px; font-size:0.92rem; font-weight:600; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                  ▶️ Exécuter
                </button>
                <button class="btn btn-primary" id="btn-linux-test-solution" style="padding:8px 18px; font-size:0.95rem; font-weight:700; background:#2563eb; border-radius:6px; box-shadow:0 3px 12px rgba(37,99,235,0.45); display:inline-flex; align-items:center; gap:6px;">
                  ⚡ Tester ma Solution
                </button>
                <button class="btn btn-success" id="btn-linux-save-cmd" style="padding:8px 16px; font-size:0.92rem; font-weight:600; background:#10b981; border:none; border-radius:6px; display:inline-flex; align-items:center; gap:6px;">
                  💾 Enregistrer
                </button>
              </div>

              <!-- Onglet 1 : Terminal Interactif -->
              <div class="tab-content" id="tab-linux-term" style="display:flex; flex-direction:column; flex:1; padding:0; overflow:hidden;">
                <!-- Logs d'affichage du Terminal -->
                <div id="linux-term-output" style="flex:1; overflow-y:auto; padding:12px 14px; font-family:var(--font-mono); font-size:0.95rem; line-height:1.5; color:#a7f3d0; background:#04070e; white-space:pre-wrap;">
<span style="color:#60a5fa;">examquiz-vm GNU/Linux 6.1 (x86_64)</span>
Tapez vos commandes directement dans l'invite ci-dessous ou cliquez sur ▶️ Exécuter.
                </div>

                <!-- Ligne d'invite CLI interactive -->
                <div style="display:flex; align-items:center; background:#060a12; border-top:1px solid rgba(255,255,255,0.08); padding:8px 12px; gap:8px;">
                  <span id="linux-term-prompt-label" style="font-family:var(--font-mono); font-size:0.95rem; font-weight:700; color:#34d399; white-space:nowrap;">
                    student@examquiz:~$ 
                  </span>
                  <input type="text" id="linux-cli-input" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" placeholder="Tapez une commande (Tab pour autocomplétion)..." style="flex:1; background:transparent; border:none; color:#f8fafc; font-family:var(--font-mono); font-size:0.95rem; outline:none;" />
                  <button id="btn-linux-clear-term" style="background:none; border:none; color:#64748b; cursor:pointer; font-size:0.8rem;" title="Effacer l'écran (Ctrl+L)">Clear</button>
                </div>
              </div>

              <!-- Onglet 2 : Cas de Test -->
              <div class="tab-content" id="tab-linux-tests" style="display:none; flex:1; padding:14px 18px; overflow-y:auto;">
                <div id="linux-test-summary" style="margin-bottom:12px; font-size:1.02rem; font-weight:700; color:#93c5fd;">
                  Cliquez sur "⚡ Tester ma Solution" pour valider votre commande.
                </div>
                <div id="linux-tests-list" style="display:flex; flex-direction:column; gap:12px;">
                  ${publicTests.map((tc, idx) => `
                    <div class="test-case-card" id="linux-tc-card-${idx}" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:14px;">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-weight:700; font-size:0.95rem; color:#60a5fa;">Cas de test #${idx + 1} (Public)</span>
                        <span class="test-status-pill" id="linux-tc-status-${idx}" style="font-size:0.85rem; padding:4px 12px; border-radius:12px; background:rgba(255,255,255,0.08); color:var(--text-muted); font-weight:600;">Non exécuté</span>
                      </div>
                      <div style="font-family:var(--font-mono); font-size:0.9rem; background:#070b14; padding:8px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.06); color:#cbd5e1;">
                        <span style="color:#64748b;">$</span> ${this._escapeHtml(tc.cmd)}
                      </div>
                      <div style="margin-top:8px; font-size:0.85rem; color:var(--text-muted);">
                        Sortie attendue : <strong style="color:#a7f3d0; font-family:var(--font-mono);">${this._escapeHtml(tc.expected_stdout || 'Code retour 0')}</strong>
                      </div>
                    </div>
                  `).join('')}

                  <div style="background:rgba(255,255,255,0.02); border:1px dashed rgba(255,255,255,0.1); border-radius:8px; padding:12px 14px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.2rem;">🔒</span>
                    <span style="font-size:0.9rem; color:var(--text-muted);">
                      <strong>${hiddenTests.length} tests cachés d'intégrité</strong> seront vérifiés lors du test de votre solution (non dévoilés par mesure de sécurité).
                    </span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    `;

    this._attachOptionListeners(q);
  }

  _attachLinuxChallengeListeners(question, publicTests) {
    const qId = question.id;
    if (!this.vfsInstances) this.vfsInstances = {};
    if (!this.vfsInstances[qId]) {
      this.vfsInstances[qId] = new LinuxVFS();
      if (question.initial_fs) {
        this.vfsInstances[qId].loadInitialFs(question.initial_fs);
      }
    }
    const vfs = this.vfsInstances[qId];

    // Navigation des défis par pilules
    document.querySelectorAll('.coding-nav-pill').forEach(btn => {
      btn.onclick = () => {
        const targetIdx = parseInt(btn.dataset.idx, 10);
        if (!isNaN(targetIdx) && targetIdx >= 0 && targetIdx < this.questions.length) {
          const editorEl = document.getElementById('linux-script-editor');
          if (editorEl) this.answers[qId] = editorEl.value;
          this.currentIndex = targetIdx;
          this.render();
        }
      };
    });

    // Bascule des onglets
    const tabTermBtn = document.getElementById('tab-btn-linux-term');
    const tabTestsBtn = document.getElementById('tab-btn-linux-tests');
    const tabTerm = document.getElementById('tab-linux-term');
    const tabTests = document.getElementById('tab-linux-tests');

    if (tabTermBtn && tabTestsBtn) {
      tabTermBtn.onclick = () => {
        tabTermBtn.classList.add('active');
        tabTestsBtn.classList.remove('active');
        if (tabTerm) tabTerm.style.display = 'flex';
        if (tabTests) tabTests.style.display = 'none';
      };
      tabTestsBtn.onclick = () => {
        tabTestsBtn.classList.add('active');
        tabTermBtn.classList.remove('active');
        if (tabTests) tabTests.style.display = 'flex';
        if (tabTerm) tabTerm.style.display = 'none';
      };
    }

    const termOutput = document.getElementById('linux-term-output');
    const cliInput = document.getElementById('linux-cli-input');
    const promptLabel = document.getElementById('linux-term-prompt-label');
    const scriptEditor = document.getElementById('linux-script-editor');
    const statusLabel = document.getElementById('linux-editor-status');

    const updatePromptLabel = () => {
      if (promptLabel) {
        const cwdDisplay = vfs.cwd.startsWith(vfs.env.HOME) ? ('~' + vfs.cwd.slice(vfs.env.HOME.length)) : vfs.cwd;
        promptLabel.textContent = `${vfs.env.USER}@examquiz:${cwdDisplay}$ `;
      }
    };
    updatePromptLabel();

    const appendToTerminal = (text, isError = false) => {
      if (!termOutput) return;
      const span = document.createElement('div');
      span.style.color = isError ? '#f87171' : '#a7f3d0';
      span.textContent = text;
      termOutput.appendChild(span);
      termOutput.scrollTop = termOutput.scrollHeight;
    };

    // Historique des commandes CLI
    let historyIdx = -1;
    if (cliInput) {
      cliInput.focus();
      cliInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
          const cmd = cliInput.value.trim();
          cliInput.value = '';
          historyIdx = -1;
          if (!cmd) return;

          const promptText = promptLabel ? promptLabel.textContent : '$ ';
          appendToTerminal(`${promptText}${cmd}`);

          if (cmd === 'clear') {
            termOutput.innerHTML = '';
            return;
          }

          const res = vfs.executeScript(cmd);
          if (res.stdout) appendToTerminal(res.stdout);
          if (res.stderr) appendToTerminal(res.stderr, true);
          updatePromptLabel();

          // Si l'éditeur ne contient qu'une commande initiale ou vide, on synchronise avec la dernière commande tapée
          if (scriptEditor && (!scriptEditor.value.trim() || scriptEditor.value.startsWith('#'))) {
            scriptEditor.value = cmd;
            this.answers[qId] = cmd;
          }
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          if (vfs.history.length > 0) {
            if (historyIdx === -1) historyIdx = vfs.history.length - 1;
            else if (historyIdx > 0) historyIdx--;
            cliInput.value = vfs.history[historyIdx] || '';
          }
        } else if (e.key === 'ArrowDown') {
          e.preventDefault();
          if (historyIdx !== -1) {
            if (historyIdx < vfs.history.length - 1) {
              historyIdx++;
              cliInput.value = vfs.history[historyIdx] || '';
            } else {
              historyIdx = -1;
              cliInput.value = '';
            }
          }
        } else if (e.key === 'Tab') {
          e.preventDefault();
          const currentVal = cliInput.value;
          const tokens = currentVal.split(' ');
          const lastToken = tokens[tokens.length - 1] || '';

          const currentNode = vfs.getNode(vfs.cwd);
          if (currentNode && currentNode.children) {
            const matches = Object.keys(currentNode.children).filter(name => name.startsWith(lastToken));
            if (matches.length === 1) {
              tokens[tokens.length - 1] = matches[0];
              cliInput.value = tokens.join(' ');
            } else if (matches.length > 1) {
              appendToTerminal(matches.join('  '));
            }
          }
        }
      };
    }

    // Bouton Clear Terminal
    const clearBtn = document.getElementById('btn-linux-clear-term');
    if (clearBtn) {
      clearBtn.onclick = () => {
        if (termOutput) termOutput.innerHTML = '';
      };
    }

    // Réinitialiser le VFS
    const resetBtn = document.getElementById('btn-linux-reset-vfs');
    if (resetBtn) {
      resetBtn.onclick = () => {
        this.vfsInstances[qId] = new LinuxVFS();
        if (question.initial_fs) {
          this.vfsInstances[qId].loadInitialFs(question.initial_fs);
        }
        appendToTerminal('[VFS] Le système de fichiers et les permissions ont été réinitialisés.');
        updatePromptLabel();
      };
    }

    // Exécuter le script
    const runBtn = document.getElementById('btn-linux-run-script');
    if (runBtn) {
      runBtn.onclick = () => {
        const code = scriptEditor ? scriptEditor.value : '';
        if (tabTermBtn) tabTermBtn.click();
        appendToTerminal(`\n=== Exécution du script dans le Shell ===`);
        const res = vfs.executeScript(code);
        if (res.stdout) appendToTerminal(res.stdout);
        if (res.stderr) appendToTerminal(res.stderr, true);
        if (!res.stdout && !res.stderr) appendToTerminal('(Exécution sans sortie standard, code retour : 0)');
        updatePromptLabel();
      };
    }

    // Tester la Solution (Automated Challenge Evaluation)
    const testBtn = document.getElementById('btn-linux-test-solution');
    if (testBtn) {
      testBtn.onclick = () => {
        const code = scriptEditor ? scriptEditor.value : '';
        this.answers[qId] = code;

        testBtn.disabled = true;
        testBtn.textContent = '⏳ Évaluation...';

        const evalRes = LinuxChallengeEvaluator.evaluate(code, question);
        if (!window.linuxChallengeResults) window.linuxChallengeResults = {};
        window.linuxChallengeResults[qId] = evalRes;

        // Basculer sur l'onglet des tests pour afficher le résultat
        if (tabTestsBtn) tabTestsBtn.click();

        // Mettre à jour le résumé
        const summaryEl = document.getElementById('linux-test-summary');
        if (summaryEl) {
          if (evalRes.success) {
            summaryEl.innerHTML = `<span style="color:#10b981;">✅ Félicitations ! ${evalRes.passed_count}/${evalRes.total_tests} tests validés avec succès (100%) !</span>`;
          } else {
            summaryEl.innerHTML = `<span style="color:#f87171;">❌ ${evalRes.passed_count}/${evalRes.total_tests} test(s) validé(s). Des erreurs subsistent.</span>`;
          }
        }

        // Mettre à jour les cartes de test
        evalRes.test_results.forEach((tr, idx) => {
          if (tr.is_public) {
            const cardEl = document.getElementById(`linux-tc-card-${idx}`);
            const statusEl = document.getElementById(`linux-tc-status-${idx}`);
            if (cardEl && statusEl) {
              if (tr.passed) {
                cardEl.style.borderColor = 'rgba(16,185,129,0.4)';
                cardEl.style.background = 'rgba(16,185,129,0.05)';
                statusEl.style.background = '#10b981';
                statusEl.style.color = '#fff';
                statusEl.textContent = 'Passé ✅';
              } else {
                cardEl.style.borderColor = 'rgba(239,68,68,0.4)';
                cardEl.style.background = 'rgba(239,68,68,0.05)';
                statusEl.style.background = '#ef4444';
                statusEl.style.color = '#fff';
                statusEl.textContent = 'Échoué ❌';
              }
            }
          }
        });

        if (statusLabel) {
          statusLabel.textContent = evalRes.success ? 'Validé ✅' : 'En cours ⚙️';
          statusLabel.style.color = evalRes.success ? '#10b981' : '#f59e0b';
        }

        testBtn.disabled = false;
        testBtn.textContent = '⚡ Tester ma Solution';
      };
    }

    // Enregistrer
    const saveBtn = document.getElementById('btn-linux-save-cmd');
    if (saveBtn) {
      saveBtn.onclick = () => {
        const code = scriptEditor ? scriptEditor.value : '';
        this.answers[qId] = code;
        if (statusLabel) {
          statusLabel.textContent = 'Enregistré ✅';
          statusLabel.style.color = '#10b981';
          setTimeout(() => {
            if (statusLabel) {
              statusLabel.textContent = 'Prêt';
              statusLabel.style.color = '#10b981';
            }
          }, 2000);
        }
      };
    }
  }

  _updateNavigationButtons() {
    const prevBtn = document.getElementById('btn-exam-prev');
    const nextBtn = document.getElementById('btn-exam-next');

    if (prevBtn) {
      prevBtn.disabled = (this.currentIndex === 0);
      prevBtn.onclick = () => {
        if (this.currentIndex > 0) {
          this.currentIndex--;
          this.render();
        }
      };
    }

    if (nextBtn) {
      if (this.currentIndex === this.questions.length - 1) {
        nextBtn.textContent = "Vérifier & Soumettre";
        nextBtn.className = "btn btn-danger";
        nextBtn.onclick = () => this.showSubmitConfirmationModal();
      } else {
        nextBtn.textContent = "Suivant ➔";
        nextBtn.className = "btn btn-primary";
        nextBtn.onclick = () => {
          if (this.currentIndex < this.questions.length - 1) {
            this.currentIndex++;
            this.render();
          }
        };
      }
    }
  }

  showSubmitConfirmationModal() {
    const modal = document.getElementById('modal-submit-confirmation');
    if (!modal) {
      if (confirm("Êtes-vous sûr de vouloir soumettre définitivement votre épreuve ?")) {
        this.submit();
      }
      return;
    }

    const answeredCount = this.questions.filter(q => this._hasAnswer(q.id)).length;
    const unansweredCount = this.questions.length - answeredCount;

    document.getElementById('modal-answered-count').textContent = answeredCount;
    document.getElementById('modal-unanswered-count').textContent = unansweredCount;

    modal.classList.add('active');

    document.getElementById('btn-modal-cancel').onclick = () => {
      modal.classList.remove('active');
    };

    document.getElementById('btn-modal-confirm').onclick = async () => {
      modal.classList.remove('active');
      await this.submit();
    };
  }

  async submit() {
    this.stop();
    if (this.antiCheat) {
      this.antiCheat.stop();
    }

    if (this.isPracticeMode) {
      if (this.onPracticeSubmit) {
        await this.onPracticeSubmit(this.answers);
      } else {
        this.onFinish(this.answers);
      }
      return;
    }

    try {
      const result = await api.submitOfficialExam(this.attemptId);
      this.onFinish(result);
    } catch (err) {
      if (typeof window.showToast === 'function') {
        window.showToast(`Erreur lors de la soumission : ${err.message}`, "danger");
      }
    }
  }

  _formatMarkdown(text) {
    if (!text) return '';
    // 1. Extraire temporairement les blocs de code préformatés
    const codeBlocks = [];
    let processed = String(text).replace(/```(?:[a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g, (match, code) => {
      const id = `___CODEBLOCK_${codeBlocks.length}___`;
      const escapedCode = this._escapeHtml(code);
      codeBlocks.push(`<pre class="code-block"><code>${escapedCode}</code></pre>`);
      return id;
    });

    // 2. Extraire les segments de code inline
    const inlineCodes = [];
    processed = processed.replace(/`([^`]+)`/g, (match, code) => {
      const id = `___INLINECODE_${inlineCodes.length}___`;
      inlineCodes.push(`<code>${this._escapeHtml(code)}</code>`);
      return id;
    });

    // 3. Échappement HTML sécurisé du texte courant
    processed = this._escapeHtml(processed);

    // 4. Titres et en-têtes Markdown (###, ##, #)
    processed = processed.replace(/^### (.*$)/gim, '<h4 class="md-heading-3" style="color:#93c5fd; margin:10px 0 6px 0; font-size:1.05rem;">$1</h4>');
    processed = processed.replace(/^## (.*$)/gim, '<h3 class="md-heading-2" style="color:#60a5fa; margin:12px 0 8px 0; font-size:1.15rem;">$1</h3>');
    processed = processed.replace(/^# (.*$)/gim, '<h2 class="md-heading-1" style="color:#3b82f6; margin:14px 0 10px 0; font-size:1.25rem;">$1</h2>');

    // 5. Mise en valeur typographique (Gras et Italique)
    processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary);">$1</strong>');
    processed = processed.replace(/\*(.*?)\*/g, '<em style="color:#cbd5e1;">$1</em>');

    // 6. Gestion fluide des paragraphes et retours à la ligne
    const paragraphs = processed.split(/\n\s*\n/);
    processed = paragraphs.map(p => {
      const trimmed = p.trim();
      if (!trimmed) return '';
      if (trimmed.startsWith('<h') || trimmed.startsWith('___CODEBLOCK_')) {
        return trimmed;
      }
      return `<p class="md-paragraph" style="margin-bottom:8px; line-height:1.55;">${trimmed.replace(/\n/g, '<br>')}</p>`;
    }).filter(Boolean).join('');

    // 7. Restitution des blocs de code
    codeBlocks.forEach((block, idx) => {
      processed = processed.replace(`___CODEBLOCK_${idx}___`, block);
    });
    inlineCodes.forEach((code, idx) => {
      processed = processed.replace(`___INLINECODE_${idx}___`, code);
    });

    return processed;
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
