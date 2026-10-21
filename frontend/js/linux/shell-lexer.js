/**
 * Shell Lexer (Tokenisation POSIX Shell)
 * Découpe une ligne de commande en jetons typés en respectant les règles
 * de citation POSIX (single quotes, double quotes, backslash escapes,
 * expansions de variables, redirections et opérateurs).
 */

export const TokenType = {
  WORD: 'WORD',
  PIPE: 'PIPE',                    // |
  REDIRECT_OUT: 'REDIRECT_OUT',    // >
  REDIRECT_APPEND: 'REDIRECT_APPEND', // >>
  REDIRECT_IN: 'REDIRECT_IN',      // <
  REDIRECT_ERR: 'REDIRECT_ERR',    // 2>
  REDIRECT_ERR_APPEND: 'REDIRECT_ERR_APPEND', // 2>>
  REDIRECT_ALL: 'REDIRECT_ALL',    // &> ou >&
  AND_IF: 'AND_IF',                // &&
  OR_IF: 'OR_IF',                  // ||
  SEMICOLON: 'SEMICOLON',          // ; ou \n
  EOF: 'EOF'
};

/**
 * Expande les variables dans un texte : $VAR, ${VAR}, ${VAR:-default}, $?
 * @param {string} text
 * @param {Object} env
 * @returns {string}
 */
export function expandVariables(text, env = {}) {
  if (!text || typeof text !== 'string') return '';

  return text.replace(/\$(?:\{([^}]+)\}|([a-zA-Z_0-9]+|\?))/g, (match, braced, simple) => {
    if (braced) {
      // Support ${VAR:-default}
      const defaultIdx = braced.indexOf(':-');
      if (defaultIdx !== -1) {
        const varName = braced.slice(0, defaultIdx);
        const defaultVal = braced.slice(defaultIdx + 2);
        if (env[varName] !== undefined && env[varName] !== '') {
          return String(env[varName]);
        }
        return defaultVal;
      }

      const varName = braced;
      if (varName === '?') {
        return env['?'] !== undefined ? String(env['?']) : '0';
      }
      if (varName in env) {
        return String(env[varName]);
      }
      return '';
    }

    const varName = simple;
    if (varName === '?') {
      return env['?'] !== undefined ? String(env['?']) : '0';
    }
    if (varName in env) {
      return String(env[varName]);
    }
    return '';
  });
}

/**
 * Re-évalue un WordToken avec un environnement spécifique
 * @param {Object} wordToken
 * @param {Object} env
 * @returns {string}
 */
export function expandWord(wordToken, env = {}) {
  if (!wordToken || !wordToken.parts) {
    return wordToken ? String(wordToken.value || '') : '';
  }

  let result = '';
  for (const part of wordToken.parts) {
    if (part.type === 'raw') {
      result += part.text;
    } else if (part.type === 'expandable') {
      result += expandVariables(part.text, env);
    }
  }
  return result;
}

export class ShellLexer {
  /**
   * @param {string} input
   * @param {Object} [options]
   * @param {Object} [options.env]
   */
  constructor(input, options = {}) {
    this.input = input || '';
    this.env = options.env || {};
  }

  /**
   * Découpe la chaîne en liste de jetons
   * @returns {Array<{ type: string, value: string, parts?: Array, pos: number }>}
   */
  tokenize() {
    const input = this.input;
    const len = input.length;
    let pos = 0;
    const tokens = [];

    const isWhitespace = (ch) => ch === ' ' || ch === '\t' || ch === '\r';

    while (pos < len) {
      // 1. Sauter les espaces blancs
      while (pos < len && isWhitespace(input[pos])) {
        pos++;
      }
      if (pos >= len) break;

      const startPos = pos;
      const c = input[pos];
      const next = pos + 1 < len ? input[pos + 1] : '';

      // 2. Opérateurs sur 2 ou 3 caractères
      if (c === '&' && next === '&') {
        tokens.push({ type: TokenType.AND_IF, value: '&&', pos: startPos });
        pos += 2;
        continue;
      }
      if (c === '|' && next === '|') {
        tokens.push({ type: TokenType.OR_IF, value: '||', pos: startPos });
        pos += 2;
        continue;
      }
      if (c === '>' && next === '>') {
        tokens.push({ type: TokenType.REDIRECT_APPEND, value: '>>', pos: startPos });
        pos += 2;
        continue;
      }
      if (c === '2' && next === '>') {
        // Vérifier 2>>
        if (pos + 2 < len && input[pos + 2] === '>') {
          tokens.push({ type: TokenType.REDIRECT_ERR_APPEND, value: '2>>', pos: startPos });
          pos += 3;
          continue;
        }
        tokens.push({ type: TokenType.REDIRECT_ERR, value: '2>', pos: startPos });
        pos += 2;
        continue;
      }
      if ((c === '&' && next === '>') || (c === '>' && next === '&')) {
        tokens.push({ type: TokenType.REDIRECT_ALL, value: '&>', pos: startPos });
        pos += 2;
        continue;
      }

      // 3. Opérateurs sur 1 caractère
      if (c === '|') {
        tokens.push({ type: TokenType.PIPE, value: '|', pos: startPos });
        pos++;
        continue;
      }
      if (c === '>') {
        tokens.push({ type: TokenType.REDIRECT_OUT, value: '>', pos: startPos });
        pos++;
        continue;
      }
      if (c === '<') {
        tokens.push({ type: TokenType.REDIRECT_IN, value: '<', pos: startPos });
        pos++;
        continue;
      }
      if (c === ';' || c === '\n') {
        tokens.push({ type: TokenType.SEMICOLON, value: c, pos: startPos });
        pos++;
        continue;
      }

      // 4. Lecture d'un mot (WORD) pouvant contenir quotes, escapes et texte
      const parts = [];
      let inWord = false;

      while (pos < len) {
        const curChar = input[pos];

        // Arrêt si espace blanc hors quotes
        if (isWhitespace(curChar)) {
          break;
        }

        // Arrêt si opérateur rencontré hors quotes
        if (
          curChar === '|' || curChar === '&' || curChar === ';' ||
          curChar === '<' || curChar === '>' || curChar === '\n'
        ) {
          break;
        }

        // Cas 2> en début de token d'opérateur
        if (curChar === '2' && pos + 1 < len && input[pos + 1] === '>') {
          break;
        }

        inWord = true;

        // 4a. Guillemet simple '...' : contenu strictement littéral
        if (curChar === '\'') {
          pos++; // consommer '
          let rawText = '';
          let closed = false;
          while (pos < len) {
            if (input[pos] === '\'') {
              closed = true;
              pos++; // consommer fermant
              break;
            }
            rawText += input[pos++];
          }
          if (!closed) {
            const err = new SyntaxError('syntax error: unexpected EOF while looking for matching single quote');
            err.code = 'SYNTAX_ERROR';
            throw err;
          }
          parts.push({ type: 'raw', text: rawText });
          continue;
        }

        // 4b. Guillemet double "..." : variables expansibles, échappements \" et \\
        if (curChar === '"') {
          pos++; // consommer "
          let expandableChunk = '';
          let closed = false;

          while (pos < len) {
            const dChar = input[pos];
            if (dChar === '"') {
              closed = true;
              pos++;
              break;
            }
            if (dChar === '\\') {
              // Antislash dans les doubles quotes
              if (pos + 1 < len) {
                const nextD = input[pos + 1];
                if (nextD === '"' || nextD === '\\' || nextD === '$') {
                  if (expandableChunk) {
                    parts.push({ type: 'expandable', text: expandableChunk });
                    expandableChunk = '';
                  }
                  parts.push({ type: 'raw', text: nextD });
                  pos += 2;
                  continue;
                }
                if (nextD === '\n') {
                  // Saut de ligne échappé
                  pos += 2;
                  continue;
                }
              }
              expandableChunk += input[pos++];
            } else {
              expandableChunk += input[pos++];
            }
          }

          if (!closed) {
            const err = new SyntaxError('syntax error: unexpected EOF while looking for matching double quote');
            err.code = 'SYNTAX_ERROR';
            throw err;
          }

          if (expandableChunk) {
            parts.push({ type: 'expandable', text: expandableChunk });
          }
          continue;
        }

        // 4c. Antislash hors guillemets : échappe le caractère suivant
        if (curChar === '\\') {
          pos++; // consommer \
          if (pos >= len) {
            parts.push({ type: 'raw', text: '\\' });
          } else {
            const escaped = input[pos++];
            if (escaped !== '\n') {
              parts.push({ type: 'raw', text: escaped });
            }
          }
          continue;
        }

        // 4d. Caractères ordinaires hors quotes
        let chunk = '';
        while (pos < len) {
          const ch = input[pos];
          if (
            isWhitespace(ch) ||
            ch === '|' || ch === '&' || ch === ';' ||
            ch === '<' || ch === '>' || ch === '\n' ||
            ch === '\'' || ch === '"' || ch === '\\'
          ) {
            break;
          }
          // Cas 2>
          if (ch === '2' && pos + 1 < len && input[pos + 1] === '>') {
            break;
          }
          chunk += ch;
          pos++;
        }

        if (chunk) {
          parts.push({ type: 'expandable', text: chunk });
        }
      }

      if (inWord) {
        const dummyToken = { parts };
        const evaluatedValue = expandWord(dummyToken, this.env);
        tokens.push({
          type: TokenType.WORD,
          value: evaluatedValue,
          parts: parts,
          pos: startPos
        });
      }
    }

    tokens.push({ type: TokenType.EOF, value: '', pos: len });
    return tokens;
  }
}

// Compatibilité Window / Browser
if (typeof window !== 'undefined') {
  window.TokenType = TokenType;
  window.ShellLexer = ShellLexer;
  window.expandVariables = expandVariables;
  window.expandWord = expandWord;
}
