/**
 * Gestionnaire du Déroulement d'Examen (Exam Runner) :
 * - Navigation libre via Palette interactive
 * - Rendu dynamique des 5 types de questions
 * - Auto-sauvegarde transparente
 * - Décompte avec alerte rouge de 60 secondes (Grace Warning)
 * - Soumission finale et affichage immédiat de la note
 */

import { api } from './api.js';

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
    alert("Le temps imparti pour cette épreuve est écoulé. Soumission automatique de vos réponses.");
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

    // Coding / Python Code (REV-19 : Prise en charge stdin sans EOFError)
    else if (question.type === 'coding' || question.type === 'code') {
      const editor = document.getElementById('input-coding-editor');
      const runBtn = document.getElementById('btn-run-code-local');
      const outputBox = document.getElementById('code-output-box');

      const initialCode = this.answers[qId] !== undefined ? this.answers[qId] : (question.starter_code || (editor ? editor.value : '') || '');
      this.answers[qId] = initialCode;

      let cmInstance = null;
      if (window.CodeMirror && editor) {
        if (editor._cmInstance) {
          try { editor._cmInstance.toTextArea(); } catch (e) {}
        }
        cmInstance = window.CodeMirror.fromTextArea(editor, {
          mode: 'python',
          theme: 'dracula',
          lineNumbers: true,
          indentUnit: 4,
          tabSize: 4,
          matchBrackets: true,
          autoCloseBrackets: true,
          lineWrapping: true
        });
        editor._cmInstance = cmInstance;
        cmInstance.setValue(initialCode);
        cmInstance.on('change', (cm) => {
          this.answers[qId] = cm.getValue();
          this._renderPalette();
        });
        setTimeout(() => cmInstance.refresh(), 50);
      } else if (editor) {
        editor.value = initialCode;
        editor.oninput = (e) => {
          this.answers[qId] = e.target.value;
          this._renderPalette();
        };
      }

      if (runBtn) {
        runBtn.onclick = async () => {
          const codeToRun = cmInstance ? cmInstance.getValue() : (editor ? editor.value : '');
          const stdinInput = document.getElementById('input-coding-stdin');
          const sampleInput = (question.tests && question.tests[0] && question.tests[0].input !== undefined) ? question.tests[0].input : (question.sample_input || '');
          const inputVal = stdinInput ? stdinInput.value : sampleInput;

          runBtn.disabled = true;
          runBtn.textContent = "⏳ Exécution...";
          if (outputBox) {
            outputBox.style.display = 'block';
            outputBox.textContent = "Exécution locale du script Python via Pyodide...";
            outputBox.style.color = "#93c5fd";
          }
          try {
            const { pythonRunner } = await import('./pyodide-runner.js');
            const res = await pythonRunner.runCode(codeToRun, inputVal);
            if (outputBox) {
              outputBox.style.display = 'block';
              if (res.error) {
                outputBox.style.color = "#f87171";
                outputBox.textContent = `Erreur d'exécution :\n${res.error}`;
              } else {
                outputBox.style.color = res.stdout ? "#a7f3d0" : "#fcd34d";
                outputBox.textContent = res.stdout || "(Exécution terminée avec succès sans affichage console)";
              }
            }
          } catch (err) {
            if (outputBox) {
              outputBox.style.display = 'block';
              outputBox.style.color = "#f87171";
              outputBox.textContent = `Erreur : ${err.error || err.message || err}`;
            }
          } finally {
            runBtn.disabled = false;
            runBtn.textContent = "▶️ Tester mon code localement";
          }
        };
      }

      // Gestion dynamique des indices (avec suivi des pénalités)
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
      alert(`Erreur lors de la soumission : ${err.message}`);
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
