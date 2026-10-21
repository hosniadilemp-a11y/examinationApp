/**
 * Shell Engine (Moteur d'Exécution Shell POSIX)
 * Orchestre l'exécution des commandes, la gestion des variables d'environnement,
 * les pipelines multi-étages (|), les redirections de fichiers (>, >>, <, 2>),
 * l'enchaînement conditionnel (&&, ||, ;) et les codes de sortie ($?).
 */

import { ShellParser } from './shell-parser.js';
import { expandWord } from './shell-lexer.js';
import { POSIX_COMMANDS } from './posix-commands.js';

export class ShellEngine {
  /**
   * @param {Object} [options]
   * @param {VirtualFS} [options.vfs]
   * @param {Object} [options.commands]
   * @param {string} [options.cwd='/home/student']
   * @param {Object} [options.env]
   */
  constructor(options = {}) {
    this.vfs = options.vfs || null;
    this.commands = options.commands || POSIX_COMMANDS;
    this.cwd = options.cwd || '/home/student';

    this.env = {
      USER: 'student',
      HOME: '/home/student',
      PWD: this.cwd,
      OLDPWD: this.cwd,
      PATH: '/usr/local/bin:/usr/bin:/bin',
      SHELL: '/bin/bash',
      TERM: 'xterm-256color',
      LANG: 'fr_FR.UTF-8',
      '?': '0',
      ...(options.env || {})
    };

    // Commandes built-in d'appoint
    this.builtins = {
      true: () => ({ stdout: '', stderr: '', exitCode: 0 }),
      false: () => ({ stdout: '', stderr: '', exitCode: 1 }),
      ':': () => ({ stdout: '', stderr: '', exitCode: 0 })
    };
  }

  /**
   * Exécute une ligne de commande complète et retourne le résultat global
   * @param {string} commandLine
   * @returns {Promise<{ stdout: string, stderr: string, exitCode: number }>}
   */
  async execute(commandLine) {
    if (!commandLine || typeof commandLine !== 'string' || !commandLine.trim()) {
      return {
        stdout: '',
        stderr: '',
        exitCode: Number(this.env['?'] || 0)
      };
    }

    // Parse la ligne de commande en AST
    let ast;
    try {
      ast = ShellParser.parse(commandLine, { env: this.env });
    } catch (err) {
      this.env['?'] = '2';
      return {
        stdout: '',
        stderr: `bash: ${err.message}\n`,
        exitCode: 2
      };
    }

    if (!ast.chains || ast.chains.length === 0) {
      return {
        stdout: '',
        stderr: '',
        exitCode: Number(this.env['?'] || 0)
      };
    }

    let accumulatedStdout = '';
    let accumulatedStderr = '';
    let lastExitCode = Number(this.env['?'] || 0);

    for (let i = 0; i < ast.chains.length; i++) {
      const chain = ast.chains[i];
      const op = chain.operator; // 'START' | 'AND' | 'OR' | 'SEQ'

      // Court-circuit conditionnel selon le code de sortie précédent
      if (op === 'AND' && lastExitCode !== 0) {
        continue;
      }
      if (op === 'OR' && lastExitCode === 0) {
        continue;
      }

      // Exécute le pipeline
      const pipeResult = await this.executePipeline(chain.pipeline);
      accumulatedStdout += pipeResult.stdout;
      accumulatedStderr += pipeResult.stderr;
      lastExitCode = pipeResult.exitCode;
      this.env['?'] = String(lastExitCode);
    }

    return {
      stdout: accumulatedStdout,
      stderr: accumulatedStderr,
      exitCode: lastExitCode
    };
  }

  /**
   * Exécute un pipeline de commandes reliées par des tubes '|'
   * @param {Object} pipeline
   * @returns {Promise<{ stdout: string, stderr: string, exitCode: number }>}
   */
  async executePipeline(pipeline) {
    const commands = pipeline.commands || [];
    if (commands.length === 0) {
      return { stdout: '', stderr: '', exitCode: 0 };
    }

    let currentStdin = '';
    let accumulatedStderr = '';
    let lastExitCode = 0;
    let finalStdout = '';

    for (let i = 0; i < commands.length; i++) {
      const cmd = commands[i];
      const isLast = i === commands.length - 1;

      const cmdResult = await this.executeSimpleCommand(cmd, currentStdin);
      accumulatedStderr += cmdResult.stderr;
      lastExitCode = cmdResult.exitCode;

      if (!isLast) {
        // Redirige la sortie standard de cette commande vers l'entrée standard de la suivante
        currentStdin = cmdResult.stdout;
      } else {
        finalStdout = cmdResult.stdout;
      }
    }

    // Le code de retour du pipeline est celui de la dernière commande sous POSIX Bash
    return {
      stdout: finalStdout,
      stderr: accumulatedStderr,
      exitCode: lastExitCode
    };
  }

  /**
   * Exécute une commande simple individuelle avec gestion des redirections
   * @param {Object} cmd
   * @param {string} pipelineStdin
   * @returns {Promise<{ stdout: string, stderr: string, exitCode: number }>}
   */
  async executeSimpleCommand(cmd, pipelineStdin = '') {
    // 1. Ré-expansion dynamique des arguments avec l'environnement courant
    let executable = cmd.executable;
    let args = [...cmd.args];

    if (cmd.tokens && cmd.tokens.length > 0) {
      executable = expandWord(cmd.tokens[0], this.env);
      args = cmd.tokens.slice(1).map(tok => expandWord(tok, this.env));
    }

    // 2. Gestion de la redirection d'entrée standard '<'
    let effectiveStdin = pipelineStdin;
    const inputRedirs = (cmd.redirections || []).filter(r => r.type === 'read');

    if (inputRedirs.length > 0) {
      // Sous bash, la dernière redirection d'entrée prévaut, mais toutes sont vérifiées
      for (const redir of inputRedirs) {
        const targetPath = redir.targetToken ? expandWord(redir.targetToken, this.env) : redir.target;
        if (!this.vfs) {
          return {
            stdout: '',
            stderr: `bash: ${targetPath}: No such file or directory\n`,
            exitCode: 1
          };
        }
        try {
          const content = this.vfs.readFile(targetPath, this.cwd);
          effectiveStdin = content;
        } catch (err) {
          return {
            stdout: '',
            stderr: `bash: ${targetPath}: No such file or directory\n`,
            exitCode: 1
          };
        }
      }
    }

    // 3. Cas particulier : Pas d'exécutable mais présence de redirections (ex: "> file.txt")
    if (!executable) {
      if (cmd.redirections && cmd.redirections.length > 0) {
        for (const redir of cmd.redirections) {
          if (redir.type === 'write' || redir.type === 'append') {
            const targetPath = redir.targetToken ? expandWord(redir.targetToken, this.env) : redir.target;
            if (this.vfs) {
              try {
                this.vfs.writeFile(targetPath, '', this.cwd, { append: redir.type === 'append' });
              } catch (err) {
                return {
                  stdout: '',
                  stderr: `bash: ${targetPath}: ${err.message}\n`,
                  exitCode: 1
                };
              }
            }
          }
        }
      }
      return { stdout: '', stderr: '', exitCode: 0 };
    }

    // 4. Assignation de variable locale directe (ex: FOO=bar) sans commande
    if (executable.includes('=') && !this.commands[executable] && !this.builtins[executable]) {
      const match = executable.match(/^([a-zA-Z_][a-zA-Z0-9_]*)=(.*)$/);
      if (match) {
        const key = match[1];
        const val = match[2];
        this.env[key] = val;
        return { stdout: '', stderr: '', exitCode: 0 };
      }
    }

    // 5. Exécution de la commande
    let cmdStdout = '';
    let cmdStderr = '';
    let cmdExitCode = 0;

    const commandFn = this.commands[executable] || this.builtins[executable];

    if (!commandFn) {
      return {
        stdout: '',
        stderr: `bash: ${executable}: command not found\n`,
        exitCode: 127
      };
    }

    try {
      if (this.vfs) {
        if (this.env.USER === 'root') {
          this.vfs.currentUser = { name: 'root', uid: 0, gid: 0 };
        } else if (this.env.USER && this.vfs.currentUser && this.vfs.currentUser.name !== this.env.USER) {
          this.vfs.currentUser = { name: this.env.USER, uid: 1000, gid: 1000 };
        }
      }

      const context = {
        vfs: this.vfs,
        cwd: this.cwd,
        env: this.env,
        commands: this.commands,
        currentUser: this.vfs && this.vfs.currentUser
          ? this.vfs.currentUser
          : (this.env.USER === 'root' ? { name: 'root', uid: 0, gid: 0 } : { name: this.env.USER || 'student', uid: 1000, gid: 1000 })
      };

      const result = await commandFn(args, effectiveStdin, context);

      cmdStdout = result && result.stdout !== undefined ? String(result.stdout) : '';
      cmdStderr = result && result.stderr !== undefined ? String(result.stderr) : '';
      cmdExitCode = result && result.exitCode !== undefined ? Number(result.exitCode) : 0;

      // Synchronisation du répertoire courant et de l'environnement mis à jour
      if (context.cwd) {
        this.cwd = context.cwd;
        this.env.PWD = this.cwd;
      }
      if (context.env) {
        this.env = context.env;
      }
    } catch (err) {
      cmdStderr = `bash: ${executable}: ${err.message}\n`;
      cmdExitCode = 1;
    }

    // 6. Application des redirections de sortie (>, >>, 2>, 2>>, &>)
    const outRedirs = (cmd.redirections || []).filter(r => r.type !== 'read');

    for (const redir of outRedirs) {
      const targetPath = redir.targetToken ? expandWord(redir.targetToken, this.env) : redir.target;
      if (!this.vfs) continue;

      try {
        if (redir.type === 'write') {
          this.vfs.writeFile(targetPath, cmdStdout, this.cwd, { append: false });
          cmdStdout = '';
        } else if (redir.type === 'append') {
          this.vfs.writeFile(targetPath, cmdStdout, this.cwd, { append: true });
          cmdStdout = '';
        } else if (redir.type === 'stderr_write') {
          this.vfs.writeFile(targetPath, cmdStderr, this.cwd, { append: false });
          cmdStderr = '';
        } else if (redir.type === 'stderr_append') {
          this.vfs.writeFile(targetPath, cmdStderr, this.cwd, { append: true });
          cmdStderr = '';
        } else if (redir.type === 'all_write') {
          const combined = cmdStdout + cmdStderr;
          this.vfs.writeFile(targetPath, combined, this.cwd, { append: false });
          cmdStdout = '';
          cmdStderr = '';
        }
      } catch (err) {
        return {
          stdout: '',
          stderr: `bash: ${targetPath}: ${err.message}\n`,
          exitCode: 1
        };
      }
    }

    return {
      stdout: cmdStdout,
      stderr: cmdStderr,
      exitCode: cmdExitCode
    };
  }
}

// Compatibilité Window / Browser
if (typeof window !== 'undefined') {
  window.ShellEngine = ShellEngine;
}
