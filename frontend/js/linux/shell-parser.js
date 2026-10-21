/**
 * Shell Parser (Analyseur Syntaxique POSIX Shell)
 * Construit un Arbre Syntaxique Abstrait (AST) à partir du flux de jetons
 * émis par ShellLexer.
 * 
 * Modèle AST :
 * - ShellCommandList: { chains: Array<ChainNode> }
 * - ChainNode: { operator: 'START' | 'AND' | 'OR' | 'SEQ', pipeline: PipelineNode }
 * - PipelineNode: { commands: Array<SimpleCommand> }
 * - SimpleCommand: { executable: string, args: string[], tokens: Array<WordToken>, redirections: Array<Redirection> }
 */

import { TokenType, ShellLexer } from './shell-lexer.js';

export class ShellParser {
  /**
   * @param {Array<Object>} tokens
   * @param {Object} [options]
   */
  constructor(tokens, options = {}) {
    this.tokens = tokens || [];
    this.pos = 0;
    this.options = options;
  }

  /**
   * Méthode statique utilitaire pour parser directement une chaîne
   * @param {string} input
   * @param {Object} [options]
   * @returns {Object} AST
   */
  static parse(input, options = {}) {
    const lexer = new ShellLexer(input, options);
    const tokens = lexer.tokenize();
    const parser = new ShellParser(tokens, options);
    return parser.parse();
  }

  peek() {
    return this.tokens[this.pos] || { type: TokenType.EOF, value: '' };
  }

  consume() {
    const t = this.tokens[this.pos];
    if (this.pos < this.tokens.length) {
      this.pos++;
    }
    return t;
  }

  /**
   * Parse la séquence complète de commandes
   * @returns {{ chains: Array<Object> }}
   */
  parse() {
    const chains = [];

    // Ignorer les points-virgules ou sauts de ligne initiaux
    while (this.peek().type === TokenType.SEMICOLON) {
      this.consume();
    }

    if (this.peek().type === TokenType.EOF) {
      return { chains: [] };
    }

    // Vérifier les erreurs de syntaxe sur opérateur au tout début
    const firstToken = this.peek();
    if (
      firstToken.type === TokenType.PIPE ||
      firstToken.type === TokenType.AND_IF ||
      firstToken.type === TokenType.OR_IF
    ) {
      const err = new SyntaxError(`syntax error near unexpected token '${firstToken.value}'`);
      err.code = 'SYNTAX_ERROR';
      throw err;
    }

    // Premier pipeline obligatoire avec opérateur START
    const firstPipeline = this.parsePipeline();
    chains.push({
      operator: 'START',
      pipeline: firstPipeline
    });

    while (this.peek().type !== TokenType.EOF) {
      const opToken = this.peek();
      let op = null;

      if (opToken.type === TokenType.AND_IF) {
        op = 'AND';
        this.consume();
      } else if (opToken.type === TokenType.OR_IF) {
        op = 'OR';
        this.consume();
      } else if (opToken.type === TokenType.SEMICOLON) {
        op = 'SEQ';
        this.consume();

        // Point-virgule final autorisé
        while (this.peek().type === TokenType.SEMICOLON) {
          this.consume();
        }
        if (this.peek().type === TokenType.EOF) {
          break;
        }
      } else {
        const err = new SyntaxError(`syntax error near unexpected token '${opToken.value}'`);
        err.code = 'SYNTAX_ERROR';
        throw err;
      }

      // Vérification qu'un opérateur n'est pas suivi d'un autre opérateur ou EOF
      const afterOp = this.peek();
      if (
        afterOp.type === TokenType.AND_IF ||
        afterOp.type === TokenType.OR_IF ||
        afterOp.type === TokenType.PIPE ||
        afterOp.type === TokenType.EOF
      ) {
        const unexpected = afterOp.type === TokenType.EOF ? 'newline' : afterOp.value;
        const err = new SyntaxError(`syntax error near unexpected token '${unexpected}'`);
        err.code = 'SYNTAX_ERROR';
        throw err;
      }

      const nextPipeline = this.parsePipeline();
      chains.push({
        operator: op,
        pipeline: nextPipeline
      });
    }

    return { chains };
  }

  /**
   * Parse un pipeline (commandes reliées par |)
   * @returns {{ commands: Array<Object> }}
   */
  parsePipeline() {
    const commands = [];

    const firstCmd = this.parseSimpleCommand();
    commands.push(firstCmd);

    while (this.peek().type === TokenType.PIPE) {
      this.consume(); // Consomme '|'

      const afterPipe = this.peek();
      if (
        afterPipe.type === TokenType.PIPE ||
        afterPipe.type === TokenType.AND_IF ||
        afterPipe.type === TokenType.OR_IF ||
        afterPipe.type === TokenType.SEMICOLON ||
        afterPipe.type === TokenType.EOF
      ) {
        const unexpected = afterPipe.type === TokenType.EOF ? 'newline' : afterPipe.value;
        const err = new SyntaxError(`syntax error near unexpected token '${unexpected}'`);
        err.code = 'SYNTAX_ERROR';
        throw err;
      }

      const nextCmd = this.parseSimpleCommand();
      commands.push(nextCmd);
    }

    return { commands };
  }

  /**
   * Parse une commande simple avec ses arguments et ses redirections
   * @returns {{ executable: string, args: Array<string>, tokens: Array<Object>, redirections: Array<Object> }}
   */
  parseSimpleCommand() {
    let executable = null;
    const args = [];
    const tokens = [];
    const redirections = [];

    while (this.peek().type !== TokenType.EOF) {
      const token = this.peek();

      // Opérateurs qui mettent fin à la commande simple
      if (
        token.type === TokenType.PIPE ||
        token.type === TokenType.AND_IF ||
        token.type === TokenType.OR_IF ||
        token.type === TokenType.SEMICOLON
      ) {
        break;
      }

      // Redirections de flux
      if (
        token.type === TokenType.REDIRECT_OUT ||
        token.type === TokenType.REDIRECT_APPEND ||
        token.type === TokenType.REDIRECT_IN ||
        token.type === TokenType.REDIRECT_ERR ||
        token.type === TokenType.REDIRECT_ERR_APPEND ||
        token.type === TokenType.REDIRECT_ALL
      ) {
        const redirToken = this.consume();
        const targetToken = this.peek();

        if (targetToken.type !== TokenType.WORD) {
          const unexpected = targetToken.type === TokenType.EOF ? 'newline' : targetToken.value;
          const err = new SyntaxError(`syntax error near unexpected token '${unexpected}'`);
          err.code = 'SYNTAX_ERROR';
          throw err;
        }

        this.consume(); // Consomme le mot cible de la redirection

        let redirType = 'write';
        if (redirToken.type === TokenType.REDIRECT_APPEND) redirType = 'append';
        else if (redirToken.type === TokenType.REDIRECT_IN) redirType = 'read';
        else if (redirToken.type === TokenType.REDIRECT_ERR) redirType = 'stderr_write';
        else if (redirToken.type === TokenType.REDIRECT_ERR_APPEND) redirType = 'stderr_append';
        else if (redirToken.type === TokenType.REDIRECT_ALL) redirType = 'all_write';

        redirections.push({
          type: redirType,
          target: targetToken.value,
          targetToken: targetToken
        });
        continue;
      }

      // Argument ou exécutable
      if (token.type === TokenType.WORD) {
        const wordToken = this.consume();
        tokens.push(wordToken);
        if (executable === null) {
          executable = wordToken.value;
        } else {
          args.push(wordToken.value);
        }
        continue;
      }

      break;
    }

    if (executable === null && redirections.length === 0) {
      const unexpected = this.peek().type === TokenType.EOF ? 'newline' : this.peek().value;
      const err = new SyntaxError(`syntax error near unexpected token '${unexpected}'`);
      err.code = 'SYNTAX_ERROR';
      throw err;
    }

    return {
      executable: executable || '',
      args,
      tokens,
      redirections
    };
  }
}

// Compatibilité Window / Browser
if (typeof window !== 'undefined') {
  window.ShellParser = ShellParser;
}
