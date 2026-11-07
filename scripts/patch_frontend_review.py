import re

with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Target block in openExamReviewModal
target_review = """        let bodyHtml = '';

        if (q.type === 'single_choice' || q.type === 'multi_choice' || q.type === 'boolean') {

          const opts = Array.isArray(q.options) ? q.options : [];

          bodyHtml = `

            <div style="display:flex; flex-direction:column; gap:8px; margin: 12px 0;">

              ${opts.map(opt => {

                const optVal = typeof opt === 'object' ? (opt.id || opt.text || opt.value) : opt;

                const optText = typeof opt === 'object' ? (opt.text || opt.label || opt.value) : opt;



                let isUserPick = false;

                if (Array.isArray(q.user_answer)) {

                  isUserPick = q.user_answer.includes(optVal) || q.user_answer.includes(optText);

                } else {

                  isUserPick = (q.user_answer === optVal || q.user_answer === optText);

                }



                let isCorrectOption = false;

                if (Array.isArray(q.correct_answer)) {

                  isCorrectOption = q.correct_answer.includes(optVal) || q.correct_answer.includes(optText);

                } else {

                  isCorrectOption = (q.correct_answer === optVal || q.correct_answer === optText);

                }



                let optStyle = 'background:var(--bg-secondary); border:1px solid var(--card-border); color:var(--text-primary);';
                let tag = '';

                if (isCorrectOption && isUserPick) {
                  optStyle = 'background:rgba(16,185,129,0.15); border:1px solid #10b981; color:var(--text-primary); font-weight:600;';
                  tag = '<span style="color:#059669; font-size:0.82rem; font-weight:700; margin-left:auto;">✓ Votre choix (Correct)</span>';
                } else if (isCorrectOption && !isUserPick) {
                  optStyle = 'background:rgba(16,185,129,0.1); border:1px dashed #10b981; color:var(--text-primary); font-weight:600;';
                  tag = '<span style="color:#059669; font-size:0.82rem; font-weight:700; margin-left:auto;">★ Bonne réponse attendue</span>';
                } else if (!isCorrectOption && isUserPick) {
                  optStyle = 'background:rgba(239,68,68,0.12); border:1px solid #ef4444; color:var(--text-primary); font-weight:600;';
                  tag = '<span style="color:#dc2626; font-size:0.82rem; font-weight:700; margin-left:auto;">✗ Votre choix (Incorrect)</span>';
                }

                return `
                  <div style="display:flex; align-items:center; padding:9px 14px; border-radius:7px; font-size:0.92rem; ${optStyle}">
                    <span>${this._escapeHtml(optText)}</span>
                    ${tag}
                  </div>
                `;
              }).join('')}
            </div>
          `;
        } else {
          const userStr = typeof q.user_answer === 'object' ? JSON.stringify(q.user_answer, null, 2) : String(q.user_answer ?? '(Aucune réponse fournie)');
          const corrStr = typeof q.correct_answer === 'object' ? JSON.stringify(q.correct_answer, null, 2) : String(q.correct_answer ?? '');
          bodyHtml = `
            <div style="display:flex; flex-direction:column; gap:10px; margin: 12px 0;">
              <div style="background: ${isOk ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'}; border: 1px solid ${isOk ? '#10b981' : '#ef4444'}; padding: 10px 14px; border-radius: 7px;">
                <div style="font-size:0.8rem; font-weight:700; color: ${isOk ? '#059669' : '#dc2626'}; margin-bottom:4px;">
                  ${isOk ? '✓ Votre Réponse (Validée)' : '✗ Votre Réponse'}
                </div>
                <pre style="margin:0; font-family:var(--font-mono, monospace); font-size:0.88rem; white-space:pre-wrap; color:var(--text-primary);">${this._escapeHtml(userStr)}</pre>
              </div>
              ${!isOk && corrStr ? `
                <div style="background: rgba(16,185,129,0.1); border: 1px dashed #10b981; padding: 10px 14px; border-radius: 7px;">
                  <div style="font-size:0.8rem; font-weight:700; color:#059669; margin-bottom:4px;">★ Réponse attendue :</div>
                  <pre style="margin:0; font-family:var(--font-mono, monospace); font-size:0.88rem; white-space:pre-wrap; color:var(--text-primary); font-weight:600;">${this._escapeHtml(corrStr)}</pre>
                </div>
              ` : ''}
            </div>
          `;
        }"""

replacement_review = """        let bodyHtml = '';
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
              return Object.entries(pairs).map(([k, v]) => `• ${k} ➔ ${v}`).join('\\n');
            }
            if (Array.isArray(pairs)) {
              return pairs.map(p => {
                if (typeof p === 'object' && p !== null) {
                  const left = p.left || p.source || p.k || '';
                  const right = p.right || p.target || p.v || '';
                  return `• ${left} ➔ ${right}`;
                }
                return `• ${p}`;
              }).join('\\n');
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
        }"""

# 2. Add Review button in renderScoreScreen
target_score_breakdown = """          <div style="font-size: 0.85rem; color: var(--text-muted); font-family: var(--font-mono);">

            Statut : SOUMIS & VERROUILLÉ • Date de scellement : ${res.submitted_at ? new Date(res.submitted_at).toLocaleString('fr-FR') : new Date().toLocaleString('fr-FR')}

          </div>

        </div>"""

replacement_score_breakdown = """          <div style="font-size: 0.85rem; color: var(--text-muted); font-family: var(--font-mono);">

            Statut : SOUMIS & VERROUILLÉ • Date de scellement : ${res.submitted_at ? new Date(res.submitted_at).toLocaleString('fr-FR') : new Date().toLocaleString('fr-FR')}

          </div>

          ${res.attempt_id ? `
            <div style="margin-top: 20px;">
              <button id="btn-score-consult-review" class="btn btn-primary" style="padding: 10px 22px; font-weight: 700; font-size: 0.95rem; display: inline-flex; align-items: center; gap: 8px; border-radius: 8px; box-shadow: 0 4px 12px rgba(37,99,235,0.25);">
                <span>🔍</span> Consulter le Corrigé &amp; Mes Réponses
              </button>
            </div>
          ` : ''}

        </div>"""

# And attach click listener in renderScoreScreen
target_score_end = """        </div>

      `;

    }

  }"""

replacement_score_end = """        </div>

      `;

      const consultRevBtn = document.getElementById('btn-score-consult-review');
      if (consultRevBtn && res.attempt_id) {
        consultRevBtn.onclick = () => this.openExamReviewModal(res.attempt_id, res.exam_id);
      }

    }

  }"""

# Normalize \r\n
def normalize(s):
    return s.replace('\\r\\n', '\\n')

norm_content = normalize(content)
norm_target_rev = normalize(target_review)
norm_target_bd = normalize(target_score_breakdown)
norm_target_end = normalize(target_score_end)

if norm_target_rev in norm_content:
    norm_content = norm_content.replace(norm_target_rev, replacement_review, 1)
    print("Replaced review block successfully")
else:
    print("FAILED to find target_review block")

if norm_target_bd in norm_content:
    norm_content = norm_content.replace(norm_target_bd, replacement_score_breakdown, 1)
    print("Replaced score breakdown successfully")
else:
    print("FAILED to find target_score_breakdown block")

if norm_target_end in norm_content:
    norm_content = norm_content.replace(norm_target_end, replacement_score_end, 1)
    print("Replaced score end successfully")
else:
    print("FAILED to find target_score_end block")

with open('frontend/js/app.js', 'w', encoding='utf-8') as f:
    f.write(norm_content)

print("Finished updating app.js")

