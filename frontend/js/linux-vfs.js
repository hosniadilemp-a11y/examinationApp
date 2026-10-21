/**
 * Virtual Linux Filesystem (VFS) & Shell Engine
 * Simulation POSIX 100% côté client pour le Centre d'Entraînement Linux.
 * 
 * Supporte :
 * - Arborescence FHS standard (/bin, /etc, /home/student, /var/log, /tmp, /dev, etc.)
 * - Commandes fondamentales : pwd, cd, ls, cat, touch, mkdir, rm, cp, mv, echo,
 *   head, tail, wc, grep, find, sort, uniq, chmod, chown, whoami, uname, uptime,
 *   date, ps, top, kill, env, export, test / [, clear, history.
 * - Tubes (pipes |), redirections (>, >>, <), variables ($VAR, $?, $USER, $HOME, etc.)
 * - Chaînage (&&, ;, ||)
 * - Évaluateur automatisé de défis (tests publics et cachés)
 * - Composant de Terminal interactif avec historique (Flèche Haut/Bas) et autocomplétion (Tab).
 */

class VFSNode {
  constructor(name, type = 'file', content = '', permissions = 'rw-r--r--', owner = 'student', group = 'student') {
    this.name = name;
    this.type = type; // 'file' ou 'dir'
    this.content = content;
    this.permissions = permissions;
    this.owner = owner;
    this.group = group;
    this.children = type === 'dir' ? {} : null;
    this.mtime = new Date();
  }
}

export class LinuxVFS {
  constructor() {
    this.root = new VFSNode('', 'dir', '', 'rwxr-xr-x', 'root', 'root');
    this.cwd = '/home/student';
    this.oldpwd = '/home/student';
    this.env = {
      USER: 'student',
      HOME: '/home/student',
      PWD: '/home/student',
      SHELL: '/bin/bash',
      PATH: '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
      TERM: 'xterm-256color',
      LANG: 'fr_FR.UTF-8',
      '?': '0'
    };
    this.history = [];
    this.processes = [
      { pid: 1, cmd: '/sbin/init', user: 'root', cpu: '0.0', mem: '0.1' },
      { pid: 2, cmd: '[kthreadd]', user: 'root', cpu: '0.0', mem: '0.0' },
      { pid: 142, cmd: '/lib/systemd/systemd-journald', user: 'root', cpu: '0.0', mem: '0.3' },
      { pid: 280, cmd: 'sshd: /usr/sbin/sshd -D', user: 'root', cpu: '0.0', mem: '0.2' },
      { pid: 310, cmd: 'nginx: master process', user: 'root', cpu: '0.0', mem: '0.4' },
      { pid: 311, cmd: 'nginx: worker process', user: 'www-data', cpu: '0.0', mem: '0.5' },
      { pid: 450, cmd: '-bash', user: 'student', cpu: '0.1', mem: '0.3' }
    ];

    this.initDefaultTree();
  }

  // --- Initialisation de l'arborescence standard FHS ---
  initDefaultTree() {
    const dirs = [
      '/bin', '/boot', '/dev', '/etc', '/home', '/home/student',
      '/lib', '/media', '/mnt', '/opt', '/proc', '/root', '/run',
      '/sbin', '/srv', '/sys', '/tmp', '/usr', '/usr/bin', '/usr/lib',
      '/usr/local', '/var', '/var/log', '/var/tmp'
    ];
    for (const d of dirs) {
      this.mkdirp(d);
    }

    // Fichiers système de base
    this.writeFile('/etc/os-release', 'NAME="Debian GNU/Linux"\nVERSION="12 (bookworm)"\nID=debian\nPRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n');
    this.writeFile('/etc/hostname', 'examquiz-vm\n');
    this.writeFile('/etc/passwd', 'root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000:Student,,,:/home/student:/bin/bash\nwww-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n');
    this.writeFile('/etc/shells', '/bin/sh\n/bin/bash\n/usr/bin/bash\n');
    this.writeFile('/home/student/.bashrc', '# ~/.bashrc: executed by bash(1) for non-login shells.\nexport PS1="\\u@\\h:\\w\\$ "\nalias ll="ls -la"\n');
    this.writeFile('/home/student/.profile', '# ~/.profile: executed by Bourne-compatible login shells.\nexport PATH="$HOME/bin:$PATH"\n');
    this.writeFile('/var/log/syslog', 'Oct 20 20:00:01 examquiz-vm systemd[1]: Starting Daily apt download activities...\nOct 20 20:01:15 examquiz-vm sshd[280]: Server listening on 0.0.0.0 port 22.\n');
    this.writeFile('/var/log/auth.log', 'Oct 20 20:10:00 examquiz-vm sshd[440]: Accepted password for student from 127.0.0.1 port 54322 ssh2\nOct 20 20:10:00 examquiz-vm systemd-logind[210]: New session 3 of user student.\n');

    this.chmod('/tmp', 'rwxrwxrwt');
    this.chmod('/var/tmp', 'rwxrwxrwt');
    this.chmod('/root', 'rwx------');
  }

  // --- Chargement d'un état initial spécifique d'un défi ---
  loadInitialFs(initialFs) {
    if (!initialFs || typeof initialFs !== 'object') return;
    for (const [dirPath, dirDef] of Object.entries(initialFs)) {
      this.mkdirp(dirPath);
      if (dirDef.files) {
        for (const [fName, fDef] of Object.entries(dirDef.files)) {
          const fullPath = dirPath.endsWith('/') ? `${dirPath}${fName}` : `${dirPath}/${fName}`;
          if (fDef.type === 'dir') {
            this.mkdirp(fullPath);
          } else {
            const content = fDef.content !== undefined ? fDef.content : '';
            const perms = fDef.permissions || 'rw-r--r--';
            this.writeFile(fullPath, content);
            this.chmod(fullPath, perms);
          }
        }
      }
    }
  }

  // --- Normalisation et Résolution de Chemins ---
  resolvePath(pathStr) {
    if (!pathStr || pathStr === '.') return this.cwd;
    let clean = String(pathStr).trim();
    if (clean.startsWith('~')) {
      clean = this.env.HOME + clean.slice(1);
    }
    if (!clean.startsWith('/')) {
      clean = (this.cwd.endsWith('/') ? this.cwd : this.cwd + '/') + clean;
    }

    const parts = clean.split('/').filter(Boolean);
    const resolvedParts = [];
    for (const p of parts) {
      if (p === '.') continue;
      if (p === '..') {
        if (resolvedParts.length > 0) resolvedParts.pop();
      } else {
        resolvedParts.push(p);
      }
    }
    return '/' + resolvedParts.join('/');
  }

  getNode(pathStr) {
    const abs = this.resolvePath(pathStr);
    if (abs === '/') return this.root;
    const parts = abs.split('/').filter(Boolean);
    let cur = this.root;
    for (const p of parts) {
      if (!cur || cur.type !== 'dir' || !cur.children[p]) {
        return null;
      }
      cur = cur.children[p];
    }
    return cur;
  }

  mkdirp(pathStr) {
    const abs = this.resolvePath(pathStr);
    if (abs === '/') return this.root;
    const parts = abs.split('/').filter(Boolean);
    let cur = this.root;
    for (const p of parts) {
      if (!cur.children[p]) {
        cur.children[p] = new VFSNode(p, 'dir', '', 'rwxr-xr-x', this.env.USER, this.env.USER);
      }
      cur = cur.children[p];
      if (cur.type !== 'dir') return null;
    }
    return cur;
  }

  writeFile(pathStr, content = '') {
    const abs = this.resolvePath(pathStr);
    const lastSlash = abs.lastIndexOf('/');
    const dirPath = abs.slice(0, lastSlash) || '/';
    const fileName = abs.slice(lastSlash + 1);

    const dirNode = this.mkdirp(dirPath);
    if (!dirNode || dirNode.type !== 'dir') return false;

    if (dirNode.children[fileName]) {
      dirNode.children[fileName].content = String(content);
      dirNode.children[fileName].mtime = new Date();
    } else {
      dirNode.children[fileName] = new VFSNode(fileName, 'file', String(content), 'rw-r--r--', this.env.USER, this.env.USER);
    }
    return true;
  }

  appendFile(pathStr, appendContent = '') {
    const abs = this.resolvePath(pathStr);
    const node = this.getNode(abs);
    if (node && node.type === 'file') {
      node.content += String(appendContent);
      node.mtime = new Date();
      return true;
    }
    return this.writeFile(abs, appendContent);
  }

  chmod(pathStr, modeStr) {
    const node = this.getNode(pathStr);
    if (!node) return false;
    let mode = String(modeStr).trim();

    // Mode octal (ex: 755, 644, 777)
    if (/^[0-7]{3,4}$/.test(mode)) {
      if (mode.length === 4) mode = mode.slice(1);
      const digitMap = {
        '0': '---', '1': '--x', '2': '-w-', '3': '-wx',
        '4': 'r--', '5': 'r-x', '6': 'rw-', '7': 'rwx'
      };
      node.permissions = (node.type === 'dir' ? 'd' : '-') +
        (digitMap[mode[0]] || 'rwx') +
        (digitMap[mode[1]] || 'r-x') +
        (digitMap[mode[2]] || 'r-x');
      return true;
    }

    // Mode symbolique (ex: +x, -w, u+x)
    if (mode.includes('+x')) {
      node.permissions = node.permissions.replace(/-(?=-|$)/g, 'x');
      return true;
    }
    node.permissions = mode;
    return true;
  }

  // --- Exécution d'une ligne de commande ou d'un script ---
  executeScript(scriptStr) {
    if (!scriptStr) return { stdout: '', stderr: '', exitCode: 0 };
    const lines = scriptStr.split('\n');
    let totalStdout = '';
    let totalStderr = '';
    let lastExit = 0;

    for (let rawLine of lines) {
      let line = rawLine.trim();
      if (!line || line.startsWith('#')) continue;

      // Découpage par opérateurs logiques &&, ;, ||
      const tokens = this._splitChain(line);
      for (const tok of tokens) {
        if (tok.op === '&&' && lastExit !== 0) break;
        if (tok.op === '||' && lastExit === 0) break;

        const res = this.executePipeline(tok.cmd);
        if (res.stdout) totalStdout += (totalStdout ? '\n' : '') + res.stdout;
        if (res.stderr) totalStderr += (totalStderr ? '\n' : '') + res.stderr;
        lastExit = res.exitCode;
        this.env['?'] = String(lastExit);
      }
    }

    return { stdout: totalStdout, stderr: totalStderr, exitCode: lastExit };
  }

  _splitChain(line) {
    // Sépare la ligne en conservant les séparateurs &&, ||, ;
    const result = [];
    const re = /(&&|\|\||;)/g;
    let lastIdx = 0;
    let lastOp = ';';

    let match;
    while ((match = re.exec(line)) !== null) {
      const cmd = line.slice(lastIdx, match.index).trim();
      if (cmd) {
        result.push({ op: lastOp, cmd });
      }
      lastOp = match[1];
      lastIdx = re.lastIndex;
    }
    const tail = line.slice(lastIdx).trim();
    if (tail) {
      result.push({ op: lastOp, cmd: tail });
    }
    return result;
  }

  // --- Exécution d'un pipeline avec tubes ( | ) ---
  executePipeline(pipelineStr) {
    const rawSegments = pipelineStr.split('|').map(s => s.trim()).filter(Boolean);
    if (!rawSegments.length) return { stdout: '', stderr: '', exitCode: 0 };

    let currentStdin = '';
    let lastRes = { stdout: '', stderr: '', exitCode: 0 };

    for (let i = 0; i < rawSegments.length; i++) {
      const seg = rawSegments[i];
      lastRes = this.executeSingleCommand(seg, currentStdin);
      currentStdin = lastRes.stdout;
      if (lastRes.exitCode !== 0 && i < rawSegments.length - 1) {
        // En cas d'erreur dans la chaîne
        return lastRes;
      }
    }
    return lastRes;
  }

  // --- Exécution d'une commande unique avec redirections >, >>, < ---
  executeSingleCommand(commandStr, stdinText = '') {
    this.history.push(commandStr);
    let str = commandStr.trim();

    // Gestion des redirections
    let redirectOut = null;
    let isAppend = false;
    let redirectIn = null;

    if (str.includes('>>')) {
      const parts = str.split('>>');
      str = parts[0].trim();
      redirectOut = parts[1].trim();
      isAppend = true;
    } else if (str.includes('>')) {
      const parts = str.split('>');
      str = parts[0].trim();
      redirectOut = parts[1].trim();
      isAppend = false;
    }

    if (str.includes('<')) {
      const parts = str.split('<');
      str = parts[0].trim();
      redirectIn = parts[1].trim();
    }

    if (redirectIn) {
      const inNode = this.getNode(redirectIn);
      if (inNode && inNode.type === 'file') {
        stdinText = inNode.content;
      } else {
        return { stdout: '', stderr: `bash: ${redirectIn}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      }
    }

    // Découpage arguments en préservant guillemets
    const args = this._parseArgs(str);
    if (!args.length) return { stdout: '', stderr: '', exitCode: 0 };

    const cmdName = args[0];
    const cmdArgs = args.slice(1);

    const res = this._dispatchCommand(cmdName, cmdArgs, stdinText);

    // Écriture de la redirection si présente
    if (redirectOut) {
      const outPath = this.resolvePath(redirectOut);
      if (isAppend) {
        this.appendFile(outPath, res.stdout + '\n');
      } else {
        this.writeFile(outPath, res.stdout + '\n');
      }
      return { stdout: '', stderr: res.stderr, exitCode: res.exitCode };
    }

    return res;
  }

  _parseArgs(cmdStr) {
    const args = [];
    let current = '';
    let inSingle = false;
    let inDouble = false;

    for (let i = 0; i < cmdStr.length; i++) {
      const ch = cmdStr[i];
      if (ch === "'" && !inDouble) {
        inSingle = !inSingle;
      } else if (ch === '"' && !inSingle) {
        inDouble = !inDouble;
      } else if (ch === ' ' && !inSingle && !inDouble) {
        if (current) {
          args.push(this._expandEnv(current));
          current = '';
        }
      } else {
        current += ch;
      }
    }
    if (current) {
      args.push(this._expandEnv(current));
    }
    return args;
  }

  _expandEnv(token) {
    return token.replace(/\$([a-zA-Z0-9_?]+)/g, (match, varName) => {
      return this.env[varName] !== undefined ? this.env[varName] : '';
    });
  }

  // --- Dispatcher des commandes POSIX émulées ---
  _dispatchCommand(cmd, args, stdin) {
    switch (cmd) {
      case 'pwd':
        return { stdout: this.cwd, stderr: '', exitCode: 0 };

      case 'whoami':
        return { stdout: this.env.USER, stderr: '', exitCode: 0 };

      case 'uname':
        if (args.includes('-a')) {
          return { stdout: 'Linux examquiz-vm 6.1.0-28-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.1.119-1 (2024-11-22) x86_64 GNU/Linux', stderr: '', exitCode: 0 };
        }
        return { stdout: 'Linux', stderr: '', exitCode: 0 };

      case 'date':
        return { stdout: new Date().toUTCString(), stderr: '', exitCode: 0 };

      case 'uptime':
        return { stdout: ' 21:30:00 up 42 days, 1 user, load average: 0.08, 0.05, 0.01', stderr: '', exitCode: 0 };

      case 'cd':
        return this._cmdCd(args);

      case 'ls':
        return this._cmdLs(args);

      case 'cat':
        return this._cmdCat(args, stdin);

      case 'touch':
        return this._cmdTouch(args);

      case 'mkdir':
        return this._cmdMkdir(args);

      case 'rm':
        return this._cmdRm(args);

      case 'cp':
        return this._cmdCp(args);

      case 'mv':
        return this._cmdMv(args);

      case 'echo':
        return { stdout: args.join(' '), stderr: '', exitCode: 0 };

      case 'head':
        return this._cmdHead(args, stdin);

      case 'tail':
        return this._cmdTail(args, stdin);

      case 'wc':
        return this._cmdWc(args, stdin);

      case 'grep':
        return this._cmdGrep(args, stdin);

      case 'find':
        return this._cmdFind(args);

      case 'sort':
        return this._cmdSort(args, stdin);

      case 'uniq':
        return this._cmdUniq(args, stdin);

      case 'chmod':
        return this._cmdChmod(args);

      case 'chown':
        return { stdout: '', stderr: '', exitCode: 0 };

      case 'ps':
        return this._cmdPs(args);

      case 'top':
        return { stdout: 'top - 21:30:00 up 42 days, 1 user, load average: 0.08, 0.05, 0.01\nTasks: 7 total, 1 running, 6 sleeping, 0 stopped\n%Cpu(s): 1.2 us, 0.4 sy, 0.0 ni, 98.4 id', stderr: '', exitCode: 0 };

      case 'kill':
        return this._cmdKill(args);

      case 'env':
        return { stdout: Object.entries(this.env).map(([k, v]) => `${k}=${v}`).join('\n'), stderr: '', exitCode: 0 };

      case 'export':
        return this._cmdExport(args);

      case 'history':
        return { stdout: this.history.map((h, i) => `  ${i + 1}  ${h}`).join('\n'), stderr: '', exitCode: 0 };

      case 'clear':
        return { stdout: '\x1b[2J\x1b[H', stderr: '', exitCode: 0 };

      case 'test':
      case '[':
        return this._cmdTest(args);

      default:
        return { stdout: '', stderr: `bash: ${cmd}: commande introuvable`, exitCode: 127 };
    }
  }

  _cmdCd(args) {
    const target = args[0] || '~';
    let dest = target;
    if (dest === '-') {
      dest = this.oldpwd;
    }
    const resolved = this.resolvePath(dest);
    const node = this.getNode(resolved);
    if (!node) {
      return { stdout: '', stderr: `bash: cd: ${target}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
    }
    if (node.type !== 'dir') {
      return { stdout: '', stderr: `bash: cd: ${target}: N'est pas un dossier`, exitCode: 1 };
    }
    this.oldpwd = this.cwd;
    this.cwd = resolved;
    this.env.PWD = this.cwd;
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdLs(args) {
    let showAll = false;
    let showLong = false;
    let dirOnly = false;
    const paths = [];

    for (const a of args) {
      if (a.startsWith('-')) {
        if (a.includes('a')) showAll = true;
        if (a.includes('l')) showLong = true;
        if (a.includes('d')) dirOnly = true;
      } else {
        paths.push(a);
      }
    }

    const targetPaths = paths.length ? paths : ['.'];
    const outLines = [];

    for (const p of targetPaths) {
      const node = this.getNode(p);
      if (!node) {
        return { stdout: '', stderr: `ls: impossible d'accéder à '${p}': Aucun fichier ou dossier de ce type`, exitCode: 2 };
      }

      if (node.type === 'file' || dirOnly) {
        outLines.push(showLong ? this._formatLsLong(node, p) : p);
        continue;
      }

      const entries = Object.keys(node.children);
      if (showAll) {
        entries.unshift('..');
        entries.unshift('.');
      } else {
        // Exclure fichiers cachés commençant par '.'
        for (let i = entries.length - 1; i >= 0; i--) {
          if (entries[i].startsWith('.')) entries.splice(i, 1);
        }
      }
      entries.sort();

      if (showLong) {
        for (const name of entries) {
          let childNode = node.children[name];
          if (name === '.') childNode = node;
          if (name === '..') childNode = this.getNode(this.resolvePath(`${p}/..`)) || node;
          outLines.push(this._formatLsLong(childNode, name));
        }
      } else {
        outLines.push(entries.join('  '));
      }
    }

    return { stdout: outLines.join('\n'), stderr: '', exitCode: 0 };
  }

  _formatLsLong(node, displayName) {
    const prefix = node.type === 'dir' ? 'd' : '-';
    const perms = node.permissions.startsWith('d') || node.permissions.startsWith('-') ? node.permissions : `${prefix}${node.permissions}`;
    const size = node.type === 'dir' ? 4096 : (node.content ? node.content.length : 0);
    const dateStr = 'Oct 20 20:00';
    return `${perms.padEnd(10)} 1 ${node.owner || 'student'} ${node.group || 'student'} ${String(size).padStart(6)} ${dateStr} ${displayName}`;
  }

  _cmdCat(args, stdin) {
    if (!args.length) {
      return { stdout: stdin || '', stderr: '', exitCode: 0 };
    }
    const out = [];
    for (const f of args) {
      if (f === '-') {
        out.push(stdin || '');
        continue;
      }
      const node = this.getNode(f);
      if (!node) {
        return { stdout: '', stderr: `cat: ${f}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      }
      if (node.type === 'dir') {
        return { stdout: '', stderr: `cat: ${f}: Est un dossier`, exitCode: 1 };
      }
      out.push(node.content);
    }
    return { stdout: out.join(''), stderr: '', exitCode: 0 };
  }

  _cmdTouch(args) {
    if (!args.length) return { stdout: '', stderr: 'touch: opérande de fichier manquant', exitCode: 1 };
    for (const f of args) {
      if (!this.writeFile(f, '')) {
        return { stdout: '', stderr: `touch: impossible de faire un touch sur '${f}'`, exitCode: 1 };
      }
    }
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdMkdir(args) {
    let makeParents = false;
    const dirs = [];
    for (const a of args) {
      if (a === '-p' || a === '--parents') makeParents = true;
      else dirs.push(a);
    }
    if (!dirs.length) return { stdout: '', stderr: 'mkdir: opérande manquant', exitCode: 1 };

    for (const d of dirs) {
      const abs = this.resolvePath(d);
      const parentPath = abs.slice(0, abs.lastIndexOf('/')) || '/';
      const parentNode = this.getNode(parentPath);
      if (!parentNode && !makeParents) {
        return { stdout: '', stderr: `mkdir: impossible de créer le dossier '${d}': Aucun fichier ou dossier de ce type`, exitCode: 1 };
      }
      this.mkdirp(abs);
    }
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdRm(args) {
    let recursive = false;
    let force = false;
    const targets = [];
    for (const a of args) {
      if (a.startsWith('-')) {
        if (a.includes('r') || a.includes('R')) recursive = true;
        if (a.includes('f')) force = true;
      } else {
        targets.push(a);
      }
    }
    if (!targets.length) {
      return force ? { stdout: '', stderr: '', exitCode: 0 } : { stdout: '', stderr: 'rm: opérande manquant', exitCode: 1 };
    }

    for (const t of targets) {
      const abs = this.resolvePath(t);
      if (abs === '/') {
        return { stdout: '', stderr: "rm: il est dangereux de supprimer '/' récursivement", exitCode: 1 };
      }
      const node = this.getNode(abs);
      if (!node) {
        if (!force) return { stdout: '', stderr: `rm: impossible de supprimer '${t}': Aucun fichier ou dossier de ce type`, exitCode: 1 };
        continue;
      }
      if (node.type === 'dir' && !recursive) {
        return { stdout: '', stderr: `rm: impossible de supprimer '${t}': Est un dossier`, exitCode: 1 };
      }
      const parentAbs = abs.slice(0, abs.lastIndexOf('/')) || '/';
      const baseName = abs.slice(abs.lastIndexOf('/') + 1);
      const parent = this.getNode(parentAbs);
      if (parent && parent.children) {
        delete parent.children[baseName];
      }
    }
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdCp(args) {
    let recursive = false;
    const paths = [];
    for (const a of args) {
      if (a === '-r' || a === '-R') recursive = true;
      else paths.push(a);
    }
    if (paths.length < 2) return { stdout: '', stderr: 'cp: opérande de fichier manquant', exitCode: 1 };

    const src = paths[0];
    const dst = paths[1];
    const srcNode = this.getNode(src);
    if (!srcNode) return { stdout: '', stderr: `cp: impossible d'évaluer '${src}': Aucun fichier ou dossier de ce type`, exitCode: 1 };

    if (srcNode.type === 'dir' && !recursive) {
      return { stdout: '', stderr: `cp: -r non spécifié ; omission du dossier '${src}'`, exitCode: 1 };
    }

    const dstNode = this.getNode(dst);
    let targetPath = this.resolvePath(dst);
    if (dstNode && dstNode.type === 'dir') {
      const srcName = src.split('/').filter(Boolean).pop();
      targetPath = `${targetPath}/${srcName}`;
    }

    if (srcNode.type === 'file') {
      this.writeFile(targetPath, srcNode.content);
      this.chmod(targetPath, srcNode.permissions);
    } else {
      this._deepCopyDir(srcNode, targetPath);
    }
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _deepCopyDir(srcDirNode, dstPath) {
    this.mkdirp(dstPath);
    for (const [name, child] of Object.entries(srcDirNode.children)) {
      const childDst = `${dstPath}/${name}`;
      if (child.type === 'file') {
        this.writeFile(childDst, child.content);
        this.chmod(childDst, child.permissions);
      } else {
        this._deepCopyDir(child, childDst);
      }
    }
  }

  _cmdMv(args) {
    if (args.length < 2) return { stdout: '', stderr: 'mv: opérande de fichier manquant', exitCode: 1 };
    const src = args[0];
    const dst = args[1];
    const srcNode = this.getNode(src);
    if (!srcNode) return { stdout: '', stderr: `mv: impossible d'évaluer '${src}': Aucun fichier ou dossier de ce type`, exitCode: 1 };

    const cpRes = this._cmdCp(['-r', src, dst]);
    if (cpRes.exitCode !== 0) return cpRes;
    this._cmdRm(['-rf', src]);
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdHead(args, stdin) {
    let n = 10;
    const files = [];
    for (let i = 0; i < args.length; i++) {
      if (args[i] === '-n' && args[i + 1]) {
        n = parseInt(args[++i], 10) || 10;
      } else if (args[i].startsWith('-') && /^\d+$/.test(args[i].slice(1))) {
        n = parseInt(args[i].slice(1), 10);
      } else {
        files.push(args[i]);
      }
    }

    let text = stdin;
    if (files.length) {
      const node = this.getNode(files[0]);
      if (!node) return { stdout: '', stderr: `head: ${files[0]}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      text = node.content;
    }
    const lines = (text || '').split('\n').slice(0, n);
    return { stdout: lines.join('\n'), stderr: '', exitCode: 0 };
  }

  _cmdTail(args, stdin) {
    let n = 10;
    const files = [];
    for (let i = 0; i < args.length; i++) {
      if (args[i] === '-n' && args[i + 1]) {
        n = parseInt(args[++i], 10) || 10;
      } else if (args[i].startsWith('-') && /^\d+$/.test(args[i].slice(1))) {
        n = parseInt(args[i].slice(1), 10);
      } else {
        files.push(args[i]);
      }
    }

    let text = stdin;
    if (files.length) {
      const node = this.getNode(files[0]);
      if (!node) return { stdout: '', stderr: `tail: ${files[0]}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      text = node.content;
    }
    const allLines = (text || '').split('\n');
    if (allLines.length && allLines[allLines.length - 1] === '') allLines.pop();
    const lines = allLines.slice(-n);
    return { stdout: lines.join('\n'), stderr: '', exitCode: 0 };
  }

  _cmdWc(args, stdin) {
    let countLines = false;
    let countWords = false;
    let countChars = false;
    const files = [];

    for (const a of args) {
      if (a.startsWith('-')) {
        if (a.includes('l')) countLines = true;
        if (a.includes('w')) countWords = true;
        if (a.includes('c') || a.includes('m')) countChars = true;
      } else {
        files.push(a);
      }
    }
    if (!countLines && !countWords && !countChars) {
      countLines = true; countWords = true; countChars = true;
    }

    let text = stdin;
    let filename = '';
    if (files.length) {
      filename = files[0];
      const node = this.getNode(filename);
      if (!node) return { stdout: '', stderr: `wc: ${filename}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      text = node.content;
    }

    const rawLines = (text || '').split('\n');
    const lines = text ? (rawLines.length - (text.endsWith('\n') ? 1 : 0)) : 0;
    const words = (text || '').trim().split(/\s+/).filter(Boolean).length;
    const chars = (text || '').length;

    const parts = [];
    if (countLines) parts.push(String(lines));
    if (countWords) parts.push(String(words));
    if (countChars) parts.push(String(chars));
    if (filename) parts.push(filename);

    return { stdout: parts.join(' '), stderr: '', exitCode: 0 };
  }

  _cmdGrep(args, stdin) {
    let ignoreCase = false;
    let invertMatch = false;
    let lineNumbers = false;
    let pattern = null;
    const files = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a.startsWith('-')) {
        if (a.includes('i')) ignoreCase = true;
        if (a.includes('v')) invertMatch = true;
        if (a.includes('n')) lineNumbers = true;
      } else if (!pattern) {
        pattern = a;
      } else {
        files.push(a);
      }
    }

    if (!pattern) return { stdout: '', stderr: 'grep: motif de recherche manquant', exitCode: 2 };

    let text = stdin;
    if (files.length && files[0] !== '-') {
      const node = this.getNode(files[0]);
      if (!node) return { stdout: '', stderr: `grep: ${files[0]}: Aucun fichier ou dossier de ce type`, exitCode: 2 };
      text = node.content;
    }

    const regex = new RegExp(pattern, ignoreCase ? 'i' : '');
    const lines = (text || '').split('\n');
    const matches = [];

    lines.forEach((l, idx) => {
      const isMatch = regex.test(l);
      if ((isMatch && !invertMatch) || (!isMatch && invertMatch)) {
        if (lineNumbers) {
          matches.push(`${idx + 1}:${l}`);
        } else {
          matches.push(l);
        }
      }
    });

    return { stdout: matches.join('\n'), stderr: '', exitCode: matches.length > 0 ? 0 : 1 };
  }

  _cmdFind(args) {
    const rootPath = args[0] && !args[0].startsWith('-') ? args[0] : '.';
    let namePattern = null;
    let typeFilter = null;

    for (let i = 0; i < args.length; i++) {
      if (args[i] === '-name' && args[i + 1]) {
        namePattern = args[++i].replace(/\*/g, '.*');
      } else if (args[i] === '-type' && args[i + 1]) {
        typeFilter = args[++i]; // 'f' ou 'd'
      }
    }

    const regex = namePattern ? new RegExp(`^${namePattern}$`) : null;
    const results = [];

    const traverse = (path, node) => {
      let keep = true;
      if (typeFilter === 'f' && node.type !== 'file') keep = false;
      if (typeFilter === 'd' && node.type !== 'dir') keep = false;
      if (regex && !regex.test(node.name || '')) keep = false;

      if (keep) results.push(path);

      if (node.type === 'dir' && node.children) {
        for (const [cName, cNode] of Object.entries(node.children)) {
          traverse(path === '.' ? `./${cName}` : `${path}/${cName}`, cNode);
        }
      }
    };

    const startNode = this.getNode(rootPath);
    if (!startNode) return { stdout: '', stderr: `find: '${rootPath}': Aucun fichier ou dossier de ce type`, exitCode: 1 };
    traverse(rootPath, startNode);

    return { stdout: results.join('\n'), stderr: '', exitCode: 0 };
  }

  _cmdSort(args, stdin) {
    let reverse = args.includes('-r');
    let numeric = args.includes('-n');
    const files = args.filter(a => !a.startsWith('-'));

    let text = stdin;
    if (files.length) {
      const node = this.getNode(files[0]);
      if (!node) return { stdout: '', stderr: `sort: ${files[0]}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      text = node.content;
    }

    const lines = (text || '').split('\n').filter(Boolean);
    lines.sort((a, b) => {
      if (numeric) {
        return (parseFloat(a) || 0) - (parseFloat(b) || 0);
      }
      return a.localeCompare(b);
    });
    if (reverse) lines.reverse();
    return { stdout: lines.join('\n'), stderr: '', exitCode: 0 };
  }

  _cmdUniq(args, stdin) {
    let count = args.includes('-c');
    let duplicatesOnly = args.includes('-d');
    const files = args.filter(a => !a.startsWith('-'));

    let text = stdin;
    if (files.length) {
      const node = this.getNode(files[0]);
      if (!node) return { stdout: '', stderr: `uniq: ${files[0]}: Aucun fichier ou dossier de ce type`, exitCode: 1 };
      text = node.content;
    }

    const lines = (text || '').split('\n').filter(Boolean);
    const result = [];
    let prev = null;
    let runCount = 0;

    const flush = () => {
      if (prev === null) return;
      if (duplicatesOnly && runCount <= 1) return;
      if (count) {
        result.push(`   ${runCount} ${prev}`);
      } else {
        result.push(prev);
      }
    };

    for (const l of lines) {
      if (l === prev) {
        runCount++;
      } else {
        flush();
        prev = l;
        runCount = 1;
      }
    }
    flush();

    return { stdout: result.join('\n'), stderr: '', exitCode: 0 };
  }

  _cmdChmod(args) {
    if (args.length < 2) return { stdout: '', stderr: 'chmod: opérande manquant', exitCode: 1 };
    const mode = args[0];
    const target = args[1];
    if (!this.chmod(target, mode)) {
      return { stdout: '', stderr: `chmod: impossible d'accéder à '${target}': Aucun fichier ou dossier de ce type`, exitCode: 1 };
    }
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdPs(args) {
    const lines = ['  PID TTY          TIME CMD'];
    for (const p of this.processes) {
      lines.push(`${String(p.pid).padStart(5)} pts/0    00:00:00 ${p.cmd}`);
    }
    return { stdout: lines.join('\n'), stderr: '', exitCode: 0 };
  }

  _cmdKill(args) {
    const pidStr = args.find(a => !a.startsWith('-'));
    const pid = parseInt(pidStr, 10);
    if (!pid) return { stdout: '', stderr: 'kill: usage: kill [-s sigspec | -n signum | -sigspec] pid | jobspec ...', exitCode: 1 };

    const idx = this.processes.findIndex(p => p.pid === pid);
    if (idx === -1) {
      return { stdout: '', stderr: `bash: kill: (${pid}) - Aucun processus de ce type`, exitCode: 1 };
    }
    this.processes.splice(idx, 1);
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdExport(args) {
    if (!args.length) return { stdout: Object.entries(this.env).map(([k, v]) => `declare -x ${k}="${v}"`).join('\n'), stderr: '', exitCode: 0 };
    for (const a of args) {
      const eqIdx = a.indexOf('=');
      if (eqIdx !== -1) {
        const k = a.slice(0, eqIdx).trim();
        const v = a.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, '');
        this.env[k] = v;
      }
    }
    return { stdout: '', stderr: '', exitCode: 0 };
  }

  _cmdTest(args) {
    // Émulation de test / [ ... ]
    let cleanArgs = args.filter(a => a !== ']');
    if (!cleanArgs.length) return { stdout: '', stderr: '', exitCode: 1 };

    let invert = false;
    if (cleanArgs[0] === '!') {
      invert = true;
      cleanArgs = cleanArgs.slice(1);
    }

    const op = cleanArgs[0];
    const val = cleanArgs[1];
    let result = false;

    if (op === '-d') {
      const node = this.getNode(val);
      result = Boolean(node && node.type === 'dir');
    } else if (op === '-f') {
      const node = this.getNode(val);
      result = Boolean(node && node.type === 'file');
    } else if (op === '-s') {
      const node = this.getNode(val);
      result = Boolean(node && node.content && node.content.length > 0);
    } else if (op === '-z') {
      result = !val || val.length === 0;
    } else if (op === '-n') {
      result = Boolean(val && val.length > 0);
    } else if (cleanArgs.length === 3 && cleanArgs[1] === '=') {
      result = cleanArgs[0] === cleanArgs[2];
    } else if (cleanArgs.length === 3 && cleanArgs[1] === '!=') {
      result = cleanArgs[0] !== cleanArgs[2];
    }

    if (invert) result = !result;
    return { stdout: '', stderr: '', exitCode: result ? 0 : 1 };
  }
}

/**
 * Évaluateur de défis d'entraînement Linux côté client.
 * Exécute la solution de l'étudiant dans un bac à sable VFS dédié, puis valide
 * l'ensemble des tests publics et cachés.
 */
export class LinuxChallengeEvaluator {
  static evaluate(studentCode, challengeData) {
    const vfs = new LinuxVFS();

    // 1. Charger l'état initial
    if (challengeData.initial_fs) {
      vfs.loadInitialFs(challengeData.initial_fs);
    }

    // 2. Exécuter le code / la commande de l'étudiant
    const execRes = vfs.executeScript(studentCode || '');

    const publicTests = challengeData.public_tests || [];
    const hiddenTests = challengeData.hidden_tests || [];
    const totalTests = publicTests.length + hiddenTests.length;

    let passedCount = 0;
    const testResults = [];

    // Validation des tests publics
    publicTests.forEach((t, idx) => {
      const testRes = vfs.executeScript(t.cmd);
      let passed = false;
      const expectedOut = t.expected_stdout !== undefined ? String(t.expected_stdout).trim() : null;
      const expectedExit = t.expected_exit_code !== undefined ? t.expected_exit_code : 0;

      const actualOut = testRes.stdout.trim();
      const exitMatch = testRes.exitCode === expectedExit;
      const outMatch = expectedOut === null || actualOut.includes(expectedOut);

      if (exitMatch && outMatch) {
        passed = true;
        passedCount++;
      }

      testResults.push({
        name: `Cas de test #${idx + 1} (Public)`,
        is_public: true,
        passed,
        cmd: t.cmd,
        expected_stdout: expectedOut,
        actual_stdout: actualOut,
        exit_code: testRes.exitCode,
        expected_exit_code: expectedExit
      });
    });

    // Validation des tests cachés
    hiddenTests.forEach((t, idx) => {
      const testRes = vfs.executeScript(t.cmd);
      let passed = false;
      const expectedOut = t.expected_stdout !== undefined ? String(t.expected_stdout).trim() : null;
      const expectedExit = t.expected_exit_code !== undefined ? t.expected_exit_code : 0;

      const actualOut = testRes.stdout.trim();
      const exitMatch = testRes.exitCode === expectedExit;
      const outMatch = expectedOut === null || actualOut.includes(expectedOut);

      if (exitMatch && outMatch) {
        passed = true;
        passedCount++;
      }

      testResults.push({
        name: `Cas de test #${publicTests.length + idx + 1} (Caché)`,
        is_public: false,
        passed,
        // On ne divulgue pas le détail interne du test caché à l'étudiant
        actual_stdout: passed ? 'Validation réussie' : 'Échec de la validation'
      });
    });

    const success = totalTests > 0 ? (passedCount === totalTests) : true;
    const percentage = totalTests > 0 ? Math.round((passedCount / totalTests) * 100) : 100;

    return {
      success,
      percentage,
      passed_count: passedCount,
      total_tests: totalTests,
      exec_stdout: execRes.stdout,
      exec_stderr: execRes.stderr,
      exec_exit_code: execRes.exitCode,
      test_results: testResults
    };
  }
}

