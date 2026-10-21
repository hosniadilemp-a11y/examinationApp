/**
 * Terminal UI (Contrôleur DOM du Terminal Virtuel Linux)
 * Gère l'interaction utilisateur avec le terminal in-browser :
 * - Invite de commande dynamique (student@examquiz:~$ ou root@examquiz:~#)
 * - Historique des commandes avec sauvegarde du brouillon non validé
 * - Autocomplétion intelligente par Tab (commandes et chemins VFS avec détection de répertoire '/')
 * - Raccourcis clavier (Ctrl+C, Ctrl+L, Ctrl+U, Ctrl+K, Ctrl+A, Ctrl+E, Ctrl+W)
 * - Affichage et défilement fluide des logs
 */

import { ShellEngine } from './shell-engine.js';
import { POSIX_COMMANDS } from './posix-commands.js';

/**
 * Calcule le plus long préfixe commun parmi un tableau de chaînes
 * @param {Array<string>} strings
 * @returns {string}
 */
export function longestCommonPrefix(strings) {
  if (!strings || strings.length === 0) return '';
  if (strings.length === 1) return strings[0];
  let prefix = strings[0];
  for (let i = 1; i < strings.length; i++) {
    const s = strings[i];
    let j = 0;
    while (j < prefix.length && j < s.length && prefix[j] === s[j]) {
      j++;
    }
    prefix = prefix.slice(0, j);
    if (!prefix) break;
  }
  return prefix;
}

export class TerminalUI {
  /**
   * @param {Object} options
   * @param {HTMLElement|string} [options.container] - Élément ou sélecteur conteneur
   * @param {ShellEngine} [options.shellEngine] - Moteur shell connecté
   * @param {VirtualFS} [options.vfs] - Système de fichiers virtuel
   * @param {Function} [options.onCommandExecuted] - Callback post-exécution
   */
  constructor(options = {}) {
    this.options = options;
    this.shellEngine = options.shellEngine || new ShellEngine({ vfs: options.vfs });
    this.history = [];
    this.historyIndex = -1;
    this.draft = '';

    this.container = null;
    this.outputElement = null;
    this.inputElement = null;
    this.promptElement = null;
    this.clearBtnElement = null;

    if (typeof document !== 'undefined' && options.container) {
      this.bindOrMount(options.container);
    }
  }

  /**
   * Lie le contrôleur à des éléments DOM existants ou monte le template par défaut
   * @param {HTMLElement|string} container
   */
  bindOrMount(container) {
    if (typeof container === 'string') {
      this.container = document.querySelector(container);
    } else {
      this.container = container;
    }

    if (!this.container) return;

    // Vérifier si la structure existe déjà dans le conteneur
    const existingOutput = this.container.querySelector('#linux-term-output');
    const existingInput = this.container.querySelector('#linux-cli-input');
    const existingPrompt = this.container.querySelector('#linux-term-prompt-label');
    const existingClearBtn = this.container.querySelector('#btn-linux-clear-term');

    if (existingOutput && existingInput) {
      this.outputElement = existingOutput;
      this.inputElement = existingInput;
      this.promptElement = existingPrompt;
      this.clearBtnElement = existingClearBtn;
    } else {
      // Montage du template complet
      this.container.innerHTML = `
        <div class="terminal-ui-wrapper" style="display:flex; flex-direction:column; width:100%; height:100%; background:#050814; color:#f8fafc; font-family:'Fira Code', 'JetBrains Mono', Consolas, monospace; overflow:hidden; border-radius:8px; border:1px solid rgba(255,255,255,0.1);">
          <div class="terminal-ui-header" style="display:flex; justify-content:space-between; align-items:center; background:#0b1120; padding:8px 14px; border-bottom:1px solid rgba(255,255,255,0.08); user-select:none;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="width:11px; height:11px; border-radius:50%; background:#ef4444; display:inline-block;"></span>
              <span style="width:11px; height:11px; border-radius:50%; background:#f59e0b; display:inline-block;"></span>
              <span style="width:11px; height:11px; border-radius:50%; background:#10b981; display:inline-block;"></span>
              <span style="margin-left:8px; font-size:0.85rem; color:#94a3b8; font-weight:600;" id="linux-term-title">student@examquiz:~ (bash)</span>
            </div>
            <button id="btn-linux-clear-term" style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color:#94a3b8; border-radius:4px; padding:3px 10px; font-size:0.8rem; cursor:pointer;" title="Effacer l'écran (Ctrl+L)">🧹 Clear (Ctrl+L)</button>
          </div>
          <div id="linux-term-output" style="flex:1; overflow-y:auto; padding:12px 14px; font-size:0.92rem; line-height:1.55; color:#a7f3d0; background:#04070e; white-space:pre-wrap;"></div>
          <div class="terminal-ui-input-line" style="display:flex; align-items:center; background:#060a12; border-top:1px solid rgba(255,255,255,0.08); padding:8px 12px; gap:8px;">
            <span id="linux-term-prompt-label" style="font-size:0.92rem; font-weight:700; white-space:nowrap;"></span>
            <input type="text" id="linux-cli-input" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" placeholder="Tapez une commande (Tab pour autocomplétion)..." style="flex:1; background:transparent; border:none; color:#f8fafc; font-family:inherit; font-size:0.92rem; outline:none;" />
          </div>
        </div>
      `;
      this.outputElement = this.container.querySelector('#linux-term-output');
      this.inputElement = this.container.querySelector('#linux-cli-input');
      this.promptElement = this.container.querySelector('#linux-term-prompt-label');
      this.clearBtnElement = this.container.querySelector('#btn-linux-clear-term');
    }

    this.attachEventListeners();
    this.updatePrompt();
    if (this.inputElement) {
      this.inputElement.focus();
    }
  }

  /**
   * Retourne les composants du prompt dynamique
   * @returns {{ user: string, host: string, cwd: string, symbol: string, isRoot: boolean }}
   */
  getPromptInfo() {
    const env = (this.shellEngine && this.shellEngine.env) || {};
    const user = env.USER || 'student';
    const host = 'examquiz';
    const cwd = (this.shellEngine && this.shellEngine.cwd) || '/home/student';
    const isRoot = user === 'root' || (this.shellEngine && this.shellEngine.vfs && this.shellEngine.vfs.currentUser && this.shellEngine.vfs.currentUser.uid === 0);
    const home = isRoot ? (env.HOME && env.HOME !== '/home/student' ? env.HOME : '/root') : (env.HOME || '/home/student');

    let displayPath = cwd;
    if (cwd === home) {
      displayPath = '~';
    } else if (cwd.startsWith(home + '/')) {
      displayPath = '~' + cwd.slice(home.length);
    } else if (isRoot && (cwd === '/root' || cwd.startsWith('/root/'))) {
      displayPath = cwd === '/root' ? '~' : '~' + cwd.slice(5);
    }

    const symbol = isRoot ? '#' : '$';
    return { user, host, cwd: displayPath, symbol, isRoot };
  }

  /**
   * Chaîne textuelle brute du prompt (ex: student@examquiz:~$ )
   * @returns {string}
   */
  getPromptText() {
    const p = this.getPromptInfo();
    return `${p.user}@${p.host}:${p.cwd}${p.symbol} `;
  }

  /**
   * Version HTML avec mise en forme colorée
   * @returns {string}
   */
  getPromptHtml() {
    const p = this.getPromptInfo();
    const userColor = p.isRoot ? '#ef4444' : '#10b981';
    const pathColor = '#38bdf8';
    return `<span style="color:${userColor}; font-weight:700;">${p.user}@${p.host}</span>:<span style="color:${pathColor}; font-weight:600;">${p.cwd}</span><span style="color:#f8fafc; font-weight:700;">${p.symbol} </span>`;
  }

  /**
   * Met à jour l'affichage de l'invite dans le DOM
   */
  updatePrompt() {
    if (this.promptElement) {
      this.promptElement.innerHTML = this.getPromptHtml();
    }
    if (this.container) {
      const titleEl = this.container.querySelector('#linux-term-title');
      if (titleEl) {
        const p = this.getPromptInfo();
        titleEl.textContent = `${p.user}@${p.host}:${p.cwd} (bash)`;
      }
    }
  }

  /**
   * Écrit une ligne dans le journal d'affichage du terminal
   * @param {string} text
   * @param {'output'|'error'|'system'|'prompt'} [type='output']
   */
  write(text, type = 'output') {
    if (!this.outputElement) return;

    const div = document.createElement('div');
    if (type === 'error') {
      div.style.color = '#f87171'; // Rouge clair
    } else if (type === 'system') {
      div.style.color = '#94a3b8'; // Gris neutre
    } else if (type === 'prompt') {
      div.style.color = '#f8fafc';
    } else {
      div.style.color = '#a7f3d0'; // Vert d'eau émeraude
    }

    div.textContent = text;
    this.outputElement.appendChild(div);
    this.scrollToBottom();
  }

  /**
   * Écrit directement du contenu HTML dans la sortie
   * @param {string} html
   */
  writeHtml(html) {
    if (!this.outputElement) return;
    const div = document.createElement('div');
    div.innerHTML = html;
    this.outputElement.appendChild(div);
    this.scrollToBottom();
  }

  /**
   * Fait défiler le terminal vers le bas
   */
  scrollToBottom() {
    if (this.outputElement) {
      this.outputElement.scrollTop = this.outputElement.scrollHeight;
    }
  }

  /**
   * Efface le journal de sortie du terminal (clear / Ctrl+L)
   */
  clear() {
    if (this.outputElement) {
      this.outputElement.innerHTML = '';
    }
  }

  /**
   * Calcule les propositions d'autocomplétion pour une ligne de saisie
   * @param {string} fullText
   * @param {number} cursorIndex
   * @returns {{ candidates: Array<string>, token: string, tokenStart: number, prefix: string, isCommand: boolean, lcp: string }}
   */
  getCompletions(fullText, cursorIndex) {
    const textBefore = fullText.slice(0, cursorIndex);

    // Trouver le début du token sous le curseur
    let tokenStart = cursorIndex;
    while (tokenStart > 0) {
      const ch = fullText[tokenStart - 1];
      if (ch === ' ' || ch === '\t' || ch === '|' || ch === ';' || ch === '&' || ch === '<' || ch === '>') {
        break;
      }
      tokenStart--;
    }

    const currentToken = fullText.slice(tokenStart, cursorIndex);

    // Déterminer si le token est en position de commande (premier mot après début ou séparateur)
    const beforeToken = fullText.slice(0, tokenStart).trim();
    let isCommand = false;
    if (!beforeToken) {
      isCommand = true;
    } else {
      const lastChar = beforeToken[beforeToken.length - 1];
      if (lastChar === '|' || lastChar === ';' || lastChar === '&') {
        isCommand = true;
      }
    }

    const candidates = [];

    if (isCommand) {
      // 1. Complétion des commandes POSIX et built-ins
      const cmdSet = new Set();
      if (this.shellEngine && this.shellEngine.commands) {
        Object.keys(this.shellEngine.commands).forEach(c => cmdSet.add(c));
      }
      if (this.shellEngine && this.shellEngine.builtins) {
        Object.keys(this.shellEngine.builtins).forEach(c => cmdSet.add(c));
      }

      // Complétion depuis les dossiers du PATH dans le VFS
      if (this.shellEngine && this.shellEngine.vfs) {
        const vfs = this.shellEngine.vfs;
        const pathDirs = ['/bin', '/usr/bin', '/usr/local/bin'];
        for (const pd of pathDirs) {
          const dirNode = vfs.resolve(pd);
          if (dirNode && dirNode.children) {
            Object.keys(dirNode.children).forEach(name => cmdSet.add(name));
          }
        }
      }

      for (const cmd of cmdSet) {
        if (cmd.startsWith(currentToken)) {
          candidates.push(cmd);
        }
      }
    } else {
      // 2. Complétion des chemins de fichiers et répertoires dans le VFS
      if (this.shellEngine && this.shellEngine.vfs) {
        const vfs = this.shellEngine.vfs;
        const cwd = this.shellEngine.cwd || '/home/student';

        let searchDir = cwd;
        let prefix = currentToken;

        const lastSlash = currentToken.lastIndexOf('/');
        if (lastSlash !== -1) {
          const dirPart = currentToken.slice(0, lastSlash);
          prefix = currentToken.slice(lastSlash + 1);
          searchDir = dirPart ? vfs.normalizePath(dirPart, cwd) : '/';
        }

        const dirNode = vfs.resolve(searchDir);
        if (dirNode && dirNode.type === 'dir' && dirNode.children) {
          for (const [name, child] of Object.entries(dirNode.children)) {
            // Ne proposer les fichiers cachés que si le préfixe commence par '.'
            if (name.startsWith('.') && !prefix.startsWith('.')) {
              continue;
            }
            if (name.startsWith(prefix)) {
              const fullMatch = lastSlash !== -1
                ? currentToken.slice(0, lastSlash + 1) + name
                : name;
              if (child.type === 'dir') {
                candidates.push(fullMatch + '/');
              } else {
                candidates.push(fullMatch + ' ');
              }
            }
          }
        }
      }
    }

    candidates.sort();
    const lcp = longestCommonPrefix(candidates);

    return {
      candidates,
      token: currentToken,
      tokenStart,
      prefix: currentToken,
      isCommand,
      lcp
    };
  }

  /**
   * Attache les écouteurs d'événements au champ de commande
   */
  attachEventListeners() {
    if (!this.inputElement) return;

    this.inputElement.addEventListener('keydown', (e) => {
      this.handleKeyDown(e);
    });

    if (this.clearBtnElement) {
      this.clearBtnElement.addEventListener('click', () => {
        this.clear();
        if (this.inputElement) this.inputElement.focus();
      });
    }

    // Clic n'importe où dans le terminal donne le focus au champ de saisie
    if (this.container) {
      this.container.addEventListener('click', (e) => {
        if (e.target !== this.clearBtnElement && this.inputElement) {
          this.inputElement.focus();
        }
      });
    }
  }

  /**
   * Traitement centralisé des touches du clavier
   * @param {KeyboardEvent} e
   */
  async handleKeyDown(e) {
    if (!this.inputElement) return;

    const key = e.key;
    const ctrl = e.ctrlKey;

    // 1. Touche Entrée : Exécution de la commande
    if (key === 'Enter') {
      e.preventDefault();
      const rawCmd = this.inputElement.value;
      const cmd = rawCmd.trim();
      const promptText = this.getPromptText();

      // Écriture de la ligne de saisie dans le journal
      this.write(`${promptText}${rawCmd}`, 'prompt');
      this.inputElement.value = '';
      this.historyIndex = -1;
      this.draft = '';

      if (!cmd) {
        this.scrollToBottom();
        return;
      }

      // Ajout à l'historique si distinct de la dernière commande
      if (this.history.length === 0 || this.history[this.history.length - 1] !== cmd) {
        this.history.push(cmd);
      }

      // Commande clear immédiate
      if (cmd === 'clear') {
        this.clear();
        this.updatePrompt();
        return;
      }

      // Exécution par le Shell Engine
      try {
        const result = await this.shellEngine.execute(cmd);
        if (result.stdout) {
          this.write(result.stdout, 'output');
        }
        if (result.stderr) {
          this.write(result.stderr, 'error');
        }
        if (typeof this.options.onCommandExecuted === 'function') {
          this.options.onCommandExecuted(cmd, result);
        }
      } catch (err) {
        this.write(`bash: ${err.message}\n`, 'error');
      }

      this.updatePrompt();
      this.scrollToBottom();
      return;
    }

    // 2. Touche Flèche Haut (↑) : Recul dans l'historique
    if (key === 'ArrowUp') {
      e.preventDefault();
      if (this.history.length === 0) return;

      if (this.historyIndex === -1) {
        this.draft = this.inputElement.value;
        this.historyIndex = this.history.length - 1;
      } else if (this.historyIndex > 0) {
        this.historyIndex--;
      }

      this.inputElement.value = this.history[this.historyIndex] || '';
      const len = this.inputElement.value.length;
      this.inputElement.setSelectionRange(len, len);
      return;
    }

    // 3. Touche Flèche Bas (↓) : Avance dans l'historique
    if (key === 'ArrowDown') {
      e.preventDefault();
      if (this.historyIndex === -1) return;

      if (this.historyIndex < this.history.length - 1) {
        this.historyIndex++;
        this.inputElement.value = this.history[this.historyIndex] || '';
      } else {
        this.historyIndex = -1;
        this.inputElement.value = this.draft;
      }

      const len = this.inputElement.value.length;
      this.inputElement.setSelectionRange(len, len);
      return;
    }

    // 4. Touche Tabulation : Autocomplétion contextuelle
    if (key === 'Tab') {
      e.preventDefault();
      const val = this.inputElement.value;
      const cursorPos = this.inputElement.selectionStart || val.length;

      const completion = this.getCompletions(val, cursorPos);

      if (completion.candidates.length === 0) {
        // Signal visuel discret si 0 correspondance
        this.flashInput();
        return;
      }

      if (completion.candidates.length === 1) {
        // Correspondance unique : remplacement direct
        const match = completion.candidates[0];
        const before = val.slice(0, completion.tokenStart);
        const after = val.slice(cursorPos);
        const newVal = before + match + after;
        this.inputElement.value = newVal;
        const newCursor = before.length + match.length;
        this.inputElement.setSelectionRange(newCursor, newCursor);
        return;
      }

      // Plusieurs correspondances
      if (completion.lcp && completion.lcp.length > completion.token.length) {
        // Compléter jusqu'au plus long préfixe commun
        const before = val.slice(0, completion.tokenStart);
        const after = val.slice(cursorPos);
        const newVal = before + completion.lcp + after;
        this.inputElement.value = newVal;
        const newCursor = before.length + completion.lcp.length;
        this.inputElement.setSelectionRange(newCursor, newCursor);
      } else {
        // Déjà au LCP : afficher la liste des choix
        const promptText = this.getPromptText();
        this.write(`${promptText}${val}`, 'prompt');
        this.write(completion.candidates.join('   '), 'system');
        this.scrollToBottom();
      }
      return;
    }

    // 5. Raccourcis avec Ctrl
    if (ctrl) {
      const lowerKey = key.toLowerCase();

      // Ctrl + C : Signal SIGINT, abandon de la commande
      if (lowerKey === 'c') {
        e.preventDefault();
        const promptText = this.getPromptText();
        this.write(`${promptText}${this.inputElement.value}^C`, 'prompt');
        this.inputElement.value = '';
        this.historyIndex = -1;
        this.draft = '';
        if (this.shellEngine && this.shellEngine.env) {
          this.shellEngine.env['?'] = '130';
        }
        this.updatePrompt();
        this.scrollToBottom();
        return;
      }

      // Ctrl + L : Effacer l'écran
      if (lowerKey === 'l') {
        e.preventDefault();
        this.clear();
        return;
      }

      // Ctrl + U : Supprime du début de la ligne jusqu'au curseur
      if (lowerKey === 'u') {
        e.preventDefault();
        const cursorPos = this.inputElement.selectionStart || 0;
        const after = this.inputElement.value.slice(cursorPos);
        this.inputElement.value = after;
        this.inputElement.setSelectionRange(0, 0);
        return;
      }

      // Ctrl + K : Supprime du curseur jusqu'à la fin de la ligne
      if (lowerKey === 'k') {
        e.preventDefault();
        const cursorPos = this.inputElement.selectionStart || 0;
        const before = this.inputElement.value.slice(0, cursorPos);
        this.inputElement.value = before;
        this.inputElement.setSelectionRange(cursorPos, cursorPos);
        return;
      }

      // Ctrl + A : Curseur au début de la ligne
      if (lowerKey === 'a') {
        e.preventDefault();
        this.inputElement.setSelectionRange(0, 0);
        return;
      }

      // Ctrl + E : Curseur à la fin de la ligne
      if (lowerKey === 'e') {
        e.preventDefault();
        const len = this.inputElement.value.length;
        this.inputElement.setSelectionRange(len, len);
        return;
      }

      // Ctrl + W : Supprime le mot précédent avant le curseur
      if (lowerKey === 'w') {
        e.preventDefault();
        const cursorPos = this.inputElement.selectionStart || 0;
        const before = this.inputElement.value.slice(0, cursorPos);
        const after = this.inputElement.value.slice(cursorPos);

        const trimmed = before.trimEnd();
        const lastSpace = trimmed.lastIndexOf(' ');
        const newBefore = lastSpace === -1 ? '' : trimmed.slice(0, lastSpace + 1);

        this.inputElement.value = newBefore + after;
        const newPos = newBefore.length;
        this.inputElement.setSelectionRange(newPos, newPos);
        return;
      }
    }
  }

  /**
   * Effet visuel lors d'une autocomplétion infructueuse
   */
  flashInput() {
    if (!this.inputElement) return;
    const origBorder = this.inputElement.style.outline;
    this.inputElement.style.outline = '1px solid rgba(239, 68, 68, 0.6)';
    setTimeout(() => {
      if (this.inputElement) {
        this.inputElement.style.outline = origBorder;
      }
    }, 150);
  }
}

// Compatibilité Window / Browser
if (typeof window !== 'undefined') {
  window.TerminalUI = TerminalUI;
  window.longestCommonPrefix = longestCommonPrefix;
}
