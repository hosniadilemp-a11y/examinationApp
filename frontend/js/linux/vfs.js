/**
 * Virtual Linux Filesystem (VFS)
 * Simulation POSIX 100% côté client pour le Centre d'Entraînement Linux.
 * 
 * Modèle Inode complet, permissions POSIX (octal & symbolique), arborescence FHS standard,
 * résolution et normalisation des chemins, gestion des liens symboliques,
 * snapshots / restaurations instantanées pour les défis.
 */

export class VFSNode {
  /**
   * @param {Object} options
   * @param {string} options.name - Nom du nœud (ex: "bashrc", "home")
   * @param {'file' | 'dir' | 'symlink'} [options.type='file'] - Type de ressource
   * @param {number} [options.mode=0o644] - Permissions octales POSIX (ex: 0o755, 0o644)
   * @param {number} [options.uid=1000] - User ID
   * @param {number} [options.gid=1000] - Group ID
   * @param {string} [options.owner='student'] - Nom du propriétaire
   * @param {string} [options.group='student'] - Nom du groupe
   * @param {string} [options.content=''] - Contenu textuel pour un fichier
   * @param {string} [options.target=''] - Cible pour un lien symbolique
   * @param {Date|number} [options.mtime=null] - Date de dernière modification
   * @param {VFSNode|null} [options.parent=null] - Référence au dossier parent
   */
  constructor({
    name = '',
    type = 'file',
    mode = null,
    uid = 1000,
    gid = 1000,
    owner = 'student',
    group = 'student',
    content = '',
    target = '',
    mtime = null,
    parent = null
  } = {}) {
    this.name = name;
    this.type = type; // 'file' | 'dir' | 'symlink'
    
    // Mode par défaut: 0o755 pour les dossiers, 0o644 pour les fichiers, 0o777 pour les symlinks
    if (mode !== null && mode !== undefined) {
      this.mode = typeof mode === 'string' ? parseInt(mode, 8) : mode;
    } else {
      this.mode = type === 'dir' ? 0o755 : (type === 'symlink' ? 0o777 : 0o644);
    }

    this.uid = uid;
    this.gid = gid;
    this.owner = owner;
    this.group = group;
    this.content = content !== undefined ? String(content) : '';
    this.target = target ? String(target) : '';
    this.parent = parent;
    this.children = type === 'dir' ? {} : null;

    const now = new Date();
    this.mtime = mtime instanceof Date ? mtime : (mtime ? new Date(mtime) : now);
    this.atime = new Date(this.mtime.getTime());
    this.ctime = new Date(this.mtime.getTime());
    this.inode = VFSNode._nextInode++;
    this.nlink = type === 'dir' ? 2 : 1;
  }

  static _nextInode = 100;

  get size() {
    if (this.type === 'file') {
      return new TextEncoder().encode(this.content).length;
    }
    if (this.type === 'symlink') {
      return this.target.length;
    }
    return 4096; // Taille conventionnelle répertoire Linux
  }

  isDirectory() {
    return this.type === 'dir';
  }

  isFile() {
    return this.type === 'file';
  }

  isSymbolicLink() {
    return this.type === 'symlink';
  }

  /**
   * Retourne la chaîne de permissions symbolique à 10 caractères (ex: "drwxr-xr-x")
   */
  getPermissionsString() {
    let typeChar = '-';
    if (this.type === 'dir') typeChar = 'd';
    else if (this.type === 'symlink') typeChar = 'l';

    const u = (this.mode >> 6) & 0o7;
    const g = (this.mode >> 3) & 0o7;
    const o = this.mode & 0o7;

    const rwx = (bits, specialBit, specialCharLower, specialCharUpper) => {
      let r = (bits & 4) ? 'r' : '-';
      let w = (bits & 2) ? 'w' : '-';
      let x = (bits & 1) ? 'x' : '-';
      if (specialBit) {
        x = (bits & 1) ? specialCharLower : specialCharUpper;
      }
      return r + w + x;
    };

    const isSuid = Boolean(this.mode & 0o4000);
    const isSgid = Boolean(this.mode & 0o2000);
    const isSticky = Boolean(this.mode & 0o1000);

    const userStr = rwx(u, isSuid, 's', 'S');
    const groupStr = rwx(g, isSgid, 's', 'S');
    const otherStr = rwx(o, isSticky, 't', 'T');

    return typeChar + userStr + groupStr + otherStr;
  }

  /**
   * Retourne le mode octal standard sous forme de chaîne 3 ou 4 chiffres (ex: "755", "1777")
   */
  getOctalPermissions() {
    const raw = (this.mode & 0o7777).toString(8);
    return raw.padStart(3, '0');
  }

  /**
   * Clône récursivement le nœud
   * @param {VFSNode|null} parentRef
   * @returns {VFSNode}
   */
  clone(parentRef = null) {
    const copy = new VFSNode({
      name: this.name,
      type: this.type,
      mode: this.mode,
      uid: this.uid,
      gid: this.gid,
      owner: this.owner,
      group: this.group,
      content: this.content,
      target: this.target,
      mtime: new Date(this.mtime.getTime()),
      parent: parentRef
    });
    copy.inode = this.inode;
    copy.atime = new Date(this.atime.getTime());
    copy.ctime = new Date(this.ctime.getTime());
    copy.nlink = this.nlink;

    if (this.type === 'dir' && this.children) {
      copy.children = {};
      for (const [cName, cNode] of Object.entries(this.children)) {
        copy.children[cName] = cNode.clone(copy);
      }
    }
    return copy;
  }
}

export class VirtualFS {
  /**
   * @param {Object} options
   * @param {string} [options.cwd='/home/student']
   * @param {Object} [options.currentUser]
   */
  constructor(options = {}) {
    this.root = new VFSNode({
      name: '',
      type: 'dir',
      mode: 0o755,
      uid: 0,
      gid: 0,
      owner: 'root',
      group: 'root'
    });

    this.cwd = options.cwd || '/home/student';
    this.oldpwd = options.cwd || '/home/student';
    this.currentUser = options.currentUser || { name: 'student', uid: 1000, gid: 1000 };
    this.umask = 0o022;

    this.initFHS();
  }

  // =========================================================================
  // Initialisation FHS Standard (Filesystem Hierarchy Standard)
  // =========================================================================

  initFHS() {
    const defaultDirs = [
      { path: '/bin', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/boot', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/dev', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/etc', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/home', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/home/student', mode: 0o755, owner: 'student', group: 'student', uid: 1000, gid: 1000 },
      { path: '/lib', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/media', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/mnt', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/opt', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/proc', mode: 0o555, owner: 'root', group: 'root' },
      { path: '/root', mode: 0o700, owner: 'root', group: 'root', uid: 0, gid: 0 },
      { path: '/run', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/sbin', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/srv', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/sys', mode: 0o555, owner: 'root', group: 'root' },
      { path: '/tmp', mode: 0o1777, owner: 'root', group: 'root' },
      { path: '/usr', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/usr/bin', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/usr/lib', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/usr/local', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/usr/local/bin', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/var', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/var/log', mode: 0o755, owner: 'root', group: 'root' },
      { path: '/var/tmp', mode: 0o1777, owner: 'root', group: 'root' }
    ];

    for (const d of defaultDirs) {
      this._mkdirInternal(d.path, d.mode, d.owner, d.group, d.uid || 0, d.gid || 0);
    }

    // Fichiers de configuration et d'environnement standard
    this._writeFileInternal('/etc/hostname', 'examquiz\n', 0o644, 'root', 'root', 0, 0);
    this._writeFileInternal(
      '/etc/os-release',
      'NAME="Ubuntu ExamQuiz Linux"\nVERSION="24.04 LTS (Noble Numbat)"\nID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 24.04 LTS"\nVERSION_ID="24.04"\nHOME_URL="https://examquiz.local/"\n',
      0o644, 'root', 'root', 0, 0
    );
    this._writeFileInternal(
      '/etc/passwd',
      'root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000:Student User:/home/student:/bin/bash\nwww-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n',
      0o644, 'root', 'root', 0, 0
    );
    this._writeFileInternal(
      '/etc/group',
      'root:x:0:\nstudent:x:1000:\nsudo:x:27:student\nwww-data:x:33:\nnogroup:x:65534:\n',
      0o644, 'root', 'root', 0, 0
    );
    this._writeFileInternal(
      '/etc/shadow',
      'root:*:19700:0:99999:7:::\nstudent:*:19700:0:99999:7:::\n',
      0o600, 'root', 'root', 0, 0
    );
    this._writeFileInternal('/etc/shells', '/bin/sh\n/bin/bash\n/usr/bin/bash\n', 0o644, 'root', 'root', 0, 0);

    // Environnement utilisateur student
    this._writeFileInternal(
      '/home/student/.bashrc',
      '# ~/.bashrc: executed by bash(1) for non-login shells.\nexport PS1="\\u@\\h:\\w\\$ "\nalias ll="ls -la"\nalias l="ls -CF"\n',
      0o644, 'student', 'student', 1000, 1000
    );
    this._writeFileInternal(
      '/home/student/.profile',
      '# ~/.profile: executed by Bourne-compatible login shells.\nexport PATH="$HOME/bin:$PATH"\n',
      0o644, 'student', 'student', 1000, 1000
    );

    // Logs système réalistes
    this._writeFileInternal(
      '/var/log/syslog',
      'Oct 20 20:00:01 examquiz systemd[1]: Starting Daily apt download activities...\nOct 20 20:01:15 examquiz sshd[280]: Server listening on 0.0.0.0 port 22.\nOct 20 20:05:00 examquiz cron[190]: (CRON) STARTUP (fork ok)\n',
      0o644, 'root', 'root', 0, 0
    );
    this._writeFileInternal(
      '/var/log/auth.log',
      'Oct 20 20:10:00 examquiz sshd[440]: Accepted password for student from 127.0.0.1 port 54322 ssh2\nOct 20 20:10:00 examquiz systemd-logind[210]: New session 3 of user student.\n',
      0o640, 'root', 'root', 0, 0
    );

    // Pseudo-fichiers /proc
    this._writeFileInternal(
      '/proc/version',
      'Linux version 5.15.0-89-generic (buildd@lcy02-amd64-077) (gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0) #99-Ubuntu SMP Mon Oct 20 12:00:00 UTC 2026\n',
      0o444, 'root', 'root', 0, 0
    );
    this._writeFileInternal('/proc/uptime', '259200.42 258100.12\n', 0o444, 'root', 'root', 0, 0);
    this._writeFileInternal(
      '/proc/cpuinfo',
      'processor\t: 0\nvendor_id\t: GenuineIntel\ncpu family\t: 6\nmodel\t\t: 142\nmodel name\t: Intel(R) Core(TM) i7-10510U CPU @ 1.80GHz\ncpu MHz\t\t: 2304.000\ncache size\t: 8192 KB\n',
      0o444, 'root', 'root', 0, 0
    );
    this._writeFileInternal(
      '/proc/meminfo',
      'MemTotal:        4016128 kB\nMemFree:         2150204 kB\nMemAvailable:    2650316 kB\nBuffers:          124500 kB\nCached:           665600 kB\n',
      0o444, 'root', 'root', 0, 0
    );

    // Périphériques simulés /dev
    this._writeFileInternal('/dev/null', '', 0o666, 'root', 'root', 0, 0);
    this._writeFileInternal('/dev/zero', '', 0o666, 'root', 'root', 0, 0);
  }

  _mkdirInternal(pathStr, mode = 0o755, owner = 'root', group = 'root', uid = 0, gid = 0) {
    const parts = pathStr.split('/').filter(Boolean);
    let cur = this.root;
    for (const p of parts) {
      if (!cur.children[p]) {
        cur.children[p] = new VFSNode({
          name: p,
          type: 'dir',
          mode,
          owner,
          group,
          uid,
          gid,
          parent: cur
        });
      }
      cur = cur.children[p];
    }
    return cur;
  }

  _writeFileInternal(pathStr, content = '', mode = 0o644, owner = 'root', group = 'root', uid = 0, gid = 0) {
    const lastSlash = pathStr.lastIndexOf('/');
    const dirPath = pathStr.slice(0, lastSlash) || '/';
    const fileName = pathStr.slice(lastSlash + 1);

    const dirNode = this._mkdirInternal(dirPath, 0o755, owner, group, uid, gid);
    if (!dirNode || dirNode.type !== 'dir') return null;

    const fileNode = new VFSNode({
      name: fileName,
      type: 'file',
      mode,
      owner,
      group,
      uid,
      gid,
      content,
      parent: dirNode
    });
    dirNode.children[fileName] = fileNode;
    return fileNode;
  }

  // =========================================================================
  // Normalisation & Résolution des Chemins
  // =========================================================================

  /**
   * Normalise un chemin arbitraire (relatif, absolu, ~, .., etc.) en chemin absolu canonique
   * @param {string} rawPath
   * @param {string} [cwd=this.cwd]
   * @returns {string} Chemin canonique absolu
   */
  normalizePath(rawPath, cwd = this.cwd) {
    if (rawPath === undefined || rawPath === null) return cwd;
    let pathStr = String(rawPath).trim();
    if (!pathStr || pathStr === '.') return cwd;

    // Expansion du tilde
    if (pathStr === '~') {
      pathStr = '/home/student';
    } else if (pathStr.startsWith('~/')) {
      pathStr = '/home/student' + pathStr.slice(1);
    } else if (pathStr === '~root') {
      pathStr = '/root';
    } else if (pathStr.startsWith('~root/')) {
      pathStr = '/root' + pathStr.slice(5);
    } else if (pathStr.startsWith('~')) {
      // ~username
      const slashIdx = pathStr.indexOf('/');
      const userName = slashIdx === -1 ? pathStr.slice(1) : pathStr.slice(1, slashIdx);
      const rest = slashIdx === -1 ? '' : pathStr.slice(slashIdx);
      pathStr = (userName === 'root' ? '/root' : `/home/${userName}`) + rest;
    }

    // Gestion du tiret '-' (revient à $OLDPWD)
    if (pathStr === '-') {
      pathStr = this.oldpwd || '/home/student';
    }

    // Préfixer par cwd si chemin relatif
    if (!pathStr.startsWith('/')) {
      const base = cwd.endsWith('/') ? cwd : cwd + '/';
      pathStr = base + pathStr;
    }

    // Nettoyage lexical par pile
    const parts = pathStr.split('/');
    const stack = [];

    for (const part of parts) {
      if (!part || part === '.') continue;
      if (part === '..') {
        if (stack.length > 0) {
          stack.pop();
        }
      } else {
        stack.push(part);
      }
    }

    return '/' + stack.join('/');
  }

  /**
   * Résout un chemin vers un VFSNode dans l'arborescence
   * @param {string} rawPath
   * @param {Object} [options]
   * @param {string} [options.cwd=this.cwd]
   * @param {boolean} [options.followSymlinks=true]
   * @param {boolean} [options.checkPermissions=false]
   * @returns {VFSNode|null}
   */
  resolve(rawPath, options = {}) {
    const cwd = options.cwd || this.cwd;
    const followSymlinks = options.followSymlinks !== false;
    const checkPermissions = Boolean(options.checkPermissions);
    const absPath = this.normalizePath(rawPath, cwd);

    if (absPath === '/') return this.root;

    const parts = absPath.split('/').filter(Boolean);
    let cur = this.root;
    let symlinkHops = options.symlinkHops || 0;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];

      // Vérification des droits de traversée ('x') sur les répertoires intermédiaires
      if (checkPermissions && cur.type === 'dir') {
        if (!this.checkAccess(cur, 1)) {
          const err = new Error(`Permission denied: '${part}'`);
          err.code = 'EACCES';
          throw err;
        }
      }

      if (cur.type !== 'dir' || !cur.children || !cur.children[part]) {
        return null;
      }

      let child = cur.children[part];

      // Traitement des liens symboliques
      if (child.type === 'symlink' && (followSymlinks || i < parts.length - 1)) {
        symlinkHops++;
        if (symlinkHops > 20) {
          const err = new Error('Too many levels of symbolic links');
          err.code = 'ELOOP';
          throw err;
        }

        const remaining = parts.slice(i + 1);
        const targetResolved = this.normalizePath(child.target, this._getNodePath(cur));
        const combined = remaining.length > 0
          ? (targetResolved.endsWith('/') ? targetResolved : targetResolved + '/') + remaining.join('/')
          : targetResolved;

        return this.resolve(combined, { ...options, followSymlinks, symlinkHops });
      }

      cur = child;
    }

    return cur;
  }

  _getNodePath(node) {
    if (!node || node === this.root) return '/';
    const parts = [];
    let cur = node;
    while (cur && cur.parent) {
      parts.unshift(cur.name);
      cur = cur.parent;
    }
    return '/' + parts.join('/');
  }

  // =========================================================================
  // Contrôle des Permissions POSIX
  // =========================================================================

  /**
   * Vérifie si l'utilisateur courant (ou spécifié) dispose des droits demandés
   * @param {VFSNode} node
   * @param {number} requiredMode - 4 (read), 2 (write), 1 (execute) ou bitwise OR (ex: 6 = rw)
   * @param {Object} [user=this.currentUser]
   * @returns {boolean}
   */
  checkAccess(node, requiredMode, user = this.currentUser) {
    if (!node) return false;

    // Utilisateur root (uid 0)
    if (user.uid === 0) {
      // Lecture et écriture sont toujours accordées à root
      if ((requiredMode & 1) === 0) return true;
      // Pour l'exécution : sur un dossier, root a toujours l'accès
      if (node.type === 'dir') return true;
      // Sur un fichier, il faut au moins un bit 'x' actif quelque part
      return Boolean(node.mode & 0o111);
    }

    // Propriétaire
    if (user.uid === node.uid) {
      const userBits = (node.mode >> 6) & 0o7;
      return (userBits & requiredMode) === requiredMode;
    }

    // Groupe
    if (user.gid === node.gid) {
      const groupBits = (node.mode >> 3) & 0o7;
      return (groupBits & requiredMode) === requiredMode;
    }

    // Autres (others)
    const otherBits = node.mode & 0o7;
    return (otherBits & requiredMode) === requiredMode;
  }

  // =========================================================================
  // Méthodes Système de Fichiers (CRUD)
  // =========================================================================

  /**
   * Lit le contenu textuel d'un fichier régulier
   * @param {string} pathStr
   * @param {string} [cwd=this.cwd]
   * @returns {string}
   */
  readFile(pathStr, cwd = this.cwd) {
    const node = this.resolve(pathStr, { cwd, checkPermissions: true });
    if (!node) {
      const err = new Error(`No such file or directory: '${pathStr}'`);
      err.code = 'ENOENT';
      throw err;
    }
    if (node.type === 'dir') {
      const err = new Error(`Is a directory: '${pathStr}'`);
      err.code = 'EISDIR';
      throw err;
    }
    if (!this.checkAccess(node, 4)) {
      const err = new Error(`Permission denied: '${pathStr}'`);
      err.code = 'EACCES';
      throw err;
    }

    node.atime = new Date();
    return node.content;
  }

  /**
   * Crée ou remplace le contenu d'un fichier
   * @param {string} pathStr
   * @param {string} [content='']
   * @param {string} [cwd=this.cwd]
   * @param {Object} [options]
   * @param {boolean} [options.append=false]
   * @param {number} [options.mode=0o644]
   * @returns {VFSNode}
   */
  writeFile(pathStr, content = '', cwd = this.cwd, options = {}) {
    const absPath = this.normalizePath(pathStr, cwd);
    const lastSlash = absPath.lastIndexOf('/');
    const dirPath = absPath.slice(0, lastSlash) || '/';
    const fileName = absPath.slice(lastSlash + 1);

    if (!fileName) {
      const err = new Error(`Invalid file path: '${pathStr}'`);
      err.code = 'EINVAL';
      throw err;
    }

    const dirNode = this.resolve(dirPath, { cwd: '/', checkPermissions: true });
    if (!dirNode) {
      const err = new Error(`No such file or directory: '${dirPath}'`);
      err.code = 'ENOENT';
      throw err;
    }
    if (dirNode.type !== 'dir') {
      const err = new Error(`Not a directory: '${dirPath}'`);
      err.code = 'ENOTDIR';
      throw err;
    }

    // Le dossier parent doit être inscriptible et exécutable
    if (!this.checkAccess(dirNode, 3)) { // 2 (w) + 1 (x) = 3
      const err = new Error(`Permission denied: '${dirPath}'`);
      err.code = 'EACCES';
      throw err;
    }

    let fileNode = dirNode.children[fileName];

    if (fileNode) {
      if (fileNode.type === 'dir') {
        const err = new Error(`Is a directory: '${pathStr}'`);
        err.code = 'EISDIR';
        throw err;
      }
      if (!this.checkAccess(fileNode, 2)) {
        const err = new Error(`Permission denied: '${pathStr}'`);
        err.code = 'EACCES';
        throw err;
      }

      if (options.append) {
        fileNode.content += String(content);
      } else {
        fileNode.content = String(content);
      }
      fileNode.mtime = new Date();
      fileNode.ctime = new Date();
      return fileNode;
    }

    // Nouveau fichier : appliquer umask par défaut
    const defaultMode = options.mode !== undefined ? options.mode : (0o666 & ~this.umask);
    fileNode = new VFSNode({
      name: fileName,
      type: 'file',
      mode: defaultMode,
      uid: this.currentUser.uid,
      gid: this.currentUser.gid,
      owner: this.currentUser.name,
      group: this.currentUser.name,
      content: String(content),
      parent: dirNode
    });

    dirNode.children[fileName] = fileNode;
    dirNode.mtime = new Date();
    dirNode.ctime = new Date();
    return fileNode;
  }

  /**
   * Crée un répertoire
   * @param {string} pathStr
   * @param {Object} [options]
   * @param {boolean} [options.recursive=false]
   * @param {number} [options.mode=0o755]
   * @param {string} [cwd=this.cwd]
   * @returns {VFSNode}
   */
  mkdir(pathStr, options = {}, cwd = this.cwd) {
    const recursive = Boolean(options.recursive);
    const mode = options.mode !== undefined ? options.mode : (0o777 & ~this.umask);
    const absPath = this.normalizePath(pathStr, cwd);

    if (absPath === '/') {
      if (recursive) return this.root;
      const err = new Error("File exists: '/'");
      err.code = 'EEXIST';
      throw err;
    }

    const parts = absPath.split('/').filter(Boolean);
    let cur = this.root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;

      if (!cur.children[part]) {
        if (!recursive && !isLast) {
          const err = new Error(`No such file or directory: '${parts.slice(0, i + 1).join('/')}'`);
          err.code = 'ENOENT';
          throw err;
        }

        // Vérifier droit d'écriture sur le parent
        if (!this.checkAccess(cur, 3)) {
          const err = new Error(`Permission denied: '${cur.name || '/'}'`);
          err.code = 'EACCES';
          throw err;
        }

        const newDir = new VFSNode({
          name: part,
          type: 'dir',
          mode: isLast ? mode : (0o777 & ~this.umask),
          uid: this.currentUser.uid,
          gid: this.currentUser.gid,
          owner: this.currentUser.name,
          group: this.currentUser.name,
          parent: cur
        });
        cur.children[part] = newDir;
        cur.mtime = new Date();
        cur.ctime = new Date();
        cur = newDir;
      } else {
        cur = cur.children[part];
        if (cur.type !== 'dir') {
          const err = new Error(`Not a directory: '${parts.slice(0, i + 1).join('/')}'`);
          err.code = 'ENOTDIR';
          throw err;
        }
        if (isLast && !recursive) {
          const err = new Error(`File exists: '${pathStr}'`);
          err.code = 'EEXIST';
          throw err;
        }
      }
    }

    return cur;
  }

  /**
   * Supprime un fichier ou un répertoire
   * @param {string} pathStr
   * @param {Object} [options]
   * @param {boolean} [options.recursive=false]
   * @param {boolean} [options.force=false]
   * @param {string} [cwd=this.cwd]
   */
  remove(pathStr, options = {}, cwd = this.cwd) {
    const recursive = Boolean(options.recursive);
    const force = Boolean(options.force);
    const absPath = this.normalizePath(pathStr, cwd);

    if (absPath === '/') {
      const err = new Error("it is dangerous to operate recursively on '/'");
      err.code = 'EINVAL';
      throw err;
    }

    const node = this.resolve(absPath, { cwd: '/', followSymlinks: false });
    if (!node) {
      if (force) return;
      const err = new Error(`No such file or directory: '${pathStr}'`);
      err.code = 'ENOENT';
      throw err;
    }

    if (node.type === 'dir' && !recursive) {
      const err = new Error(`Is a directory: '${pathStr}'`);
      err.code = 'EISDIR';
      throw err;
    }

    const parent = node.parent;
    if (!parent) {
      const err = new Error(`Cannot remove root node`);
      err.code = 'EPERM';
      throw err;
    }

    if (!this.checkAccess(parent, 3)) {
      const err = new Error(`Permission denied: '${pathStr}'`);
      err.code = 'EACCES';
      throw err;
    }

    delete parent.children[node.name];
    parent.mtime = new Date();
    parent.ctime = new Date();
  }

  /**
   * Copie un fichier ou un répertoire vers une destination
   * @param {string} srcPath
   * @param {string} dstPath
   * @param {Object} [options]
   * @param {boolean} [options.recursive=false]
   * @param {boolean} [options.force=false]
   * @param {boolean} [options.preserve=false]
   * @param {string} [cwd=this.cwd]
   */
  copy(srcPath, dstPath, options = {}, cwd = this.cwd) {
    const recursive = Boolean(options.recursive);
    const preserve = Boolean(options.preserve);
    const srcNode = this.resolve(srcPath, { cwd, followSymlinks: false });

    if (!srcNode) {
      const err = new Error(`cannot stat '${srcPath}': No such file or directory`);
      err.code = 'ENOENT';
      throw err;
    }

    if (srcNode.type === 'dir' && !recursive) {
      const err = new Error(`-r not specified; omitting directory '${srcPath}'`);
      err.code = 'EISDIR';
      throw err;
    }

    const dstAbs = this.normalizePath(dstPath, cwd);
    const dstNode = this.resolve(dstAbs, { cwd: '/' });

    let finalDstPath = dstAbs;
    if (dstNode && dstNode.type === 'dir') {
      const srcBase = srcNode.name || srcPath.split('/').filter(Boolean).pop();
      finalDstPath = (dstAbs === '/' ? '' : dstAbs) + '/' + srcBase;
    }

    if (srcNode.type === 'file') {
      const mode = preserve ? srcNode.mode : undefined;
      const targetNode = this.writeFile(finalDstPath, srcNode.content, '/', { mode });
      if (preserve) {
        targetNode.owner = srcNode.owner;
        targetNode.group = srcNode.group;
        targetNode.uid = srcNode.uid;
        targetNode.gid = srcNode.gid;
        targetNode.mtime = new Date(srcNode.mtime.getTime());
      }
    } else if (srcNode.type === 'dir') {
      this._deepCopyDir(srcNode, finalDstPath, preserve);
    }
  }

  _deepCopyDir(srcDirNode, dstPath, preserve) {
    const dstDir = this.mkdir(dstPath, { recursive: true, mode: preserve ? srcDirNode.mode : 0o755 }, '/');
    if (preserve) {
      dstDir.owner = srcDirNode.owner;
      dstDir.group = srcDirNode.group;
      dstDir.uid = srcDirNode.uid;
      dstDir.gid = srcDirNode.gid;
      dstDir.mtime = new Date(srcDirNode.mtime.getTime());
    }

    for (const [name, child] of Object.entries(srcDirNode.children)) {
      const childDst = (dstPath === '/' ? '' : dstPath) + '/' + name;
      if (child.type === 'file') {
        const fNode = this.writeFile(childDst, child.content, '/', { mode: preserve ? child.mode : 0o644 });
        if (preserve) {
          fNode.owner = child.owner;
          fNode.group = child.group;
          fNode.uid = child.uid;
          fNode.gid = child.gid;
          fNode.mtime = new Date(child.mtime.getTime());
        }
      } else if (child.type === 'dir') {
        this._deepCopyDir(child, childDst, preserve);
      }
    }
  }

  /**
   * Déplace ou renomme un fichier/dossier
   * @param {string} srcPath
   * @param {string} dstPath
   * @param {string} [cwd=this.cwd]
   */
  move(srcPath, dstPath, cwd = this.cwd) {
    const srcAbs = this.normalizePath(srcPath, cwd);
    const dstAbs = this.normalizePath(dstPath, cwd);

    const srcNode = this.resolve(srcAbs, { cwd: '/', followSymlinks: false });
    if (!srcNode) {
      const err = new Error(`cannot stat '${srcPath}': No such file or directory`);
      err.code = 'ENOENT';
      throw err;
    }

    // Sécurité : Impossible de déplacer un dossier dans un de ses propres sous-dossiers
    if (srcNode.type === 'dir' && (dstAbs === srcAbs || dstAbs.startsWith(srcAbs + '/'))) {
      const err = new Error(`cannot move '${srcPath}' to a subdirectory of itself`);
      err.code = 'EINVAL';
      throw err;
    }

    this.copy(srcPath, dstPath, { recursive: true, preserve: true }, cwd);
    this.remove(srcPath, { recursive: true, force: true }, cwd);
  }

  /**
   * Modifie les permissions d'un nœud (notation octale ou symbolique)
   * @param {string} pathStr
   * @param {string|number} modeSpec - Ex: 755, "755", "+x", "u+x,go-w", "a=rwx"
   * @param {Object} [options]
   * @param {boolean} [options.recursive=false]
   * @param {string} [cwd=this.cwd]
   */
  chmod(pathStr, modeSpec, options = {}, cwd = this.cwd) {
    const user = options.user || this.currentUser;
    const recursive = Boolean(options.recursive);
    const node = this.resolve(pathStr, { cwd, followSymlinks: false });

    if (!node) {
      const err = new Error(`cannot access '${pathStr}': No such file or directory`);
      err.code = 'ENOENT';
      throw err;
    }

    // Seul le propriétaire ou root a le droit de chmod
    if (user.uid !== 0 && user.uid !== node.uid) {
      const err = new Error(`changing permissions of '${pathStr}': Operation not permitted`);
      err.code = 'EPERM';
      throw err;
    }

    const applyChmod = (targetNode) => {
      targetNode.mode = this._parseChmodMode(modeSpec, targetNode.mode, targetNode.type === 'dir');
      targetNode.ctime = new Date();
      if (recursive && targetNode.type === 'dir' && targetNode.children) {
        for (const child of Object.values(targetNode.children)) {
          applyChmod(child);
        }
      }
    };

    applyChmod(node);
  }

  _parseChmodMode(spec, currentMode, isDirectory) {
    const raw = String(spec).trim();

    // Mode octal (3 ou 4 chiffres octaux : 755, 0755, 1777, 644)
    if (/^[0-7]{3,4}$/.test(raw)) {
      return parseInt(raw, 8);
    }

    // Mode symbolique (ex: "+x", "u+x", "go-w", "u=rwx,go=rx")
    let newMode = currentMode;
    const clauses = raw.split(',');

    for (const clause of clauses) {
      const match = /^([ugoa]*)([\+\-\=])([rwxXst]*|[0-7]+)$/.exec(clause.trim());
      if (!match) {
        const err = new Error(`invalid mode: '${spec}'`);
        err.code = 'EINVAL';
        throw err;
      }

      let [, who, op, permStr] = match;
      if (!who || who === 'a') who = 'ugo';

      // Calcul du masque de bits
      let permBits = 0;
      if (/^[0-7]+$/.test(permStr)) {
        permBits = parseInt(permStr, 8) & 0o7;
      } else {
        if (permStr.includes('r')) permBits |= 4;
        if (permStr.includes('w')) permBits |= 2;
        if (permStr.includes('x')) permBits |= 1;
        if (permStr.includes('X') && (isDirectory || (newMode & 0o111))) permBits |= 1;
      }

      const applyToPart = (shift) => {
        if (op === '+') {
          newMode |= (permBits << shift);
        } else if (op === '-') {
          newMode &= ~(permBits << shift);
        } else if (op === '=') {
          newMode = (newMode & ~(0o7 << shift)) | (permBits << shift);
        }
      };

      if (who.includes('u')) applyToPart(6);
      if (who.includes('g')) applyToPart(3);
      if (who.includes('o')) applyToPart(0);
    }

    return newMode;
  }

  /**
   * Modifie le propriétaire et le groupe d'un nœud
   * @param {string} pathStr
   * @param {string} owner
   * @param {string} [group]
   * @param {Object} [options]
   * @param {boolean} [options.recursive=false]
   * @param {string} [cwd=this.cwd]
   */
  chown(pathStr, owner, group = null, options = {}, cwd = this.cwd) {
    const user = options.user || this.currentUser;
    // Sous POSIX GNU/Linux, seul root peut changer le propriétaire d'un fichier
    if (user.uid !== 0) {
      const err = new Error(`changing ownership of '${pathStr}': Operation not permitted`);
      err.code = 'EPERM';
      throw err;
    }

    const recursive = Boolean(options.recursive);
    const node = this.resolve(pathStr, { cwd, followSymlinks: false });
    if (!node) {
      const err = new Error(`cannot access '${pathStr}': No such file or directory`);
      err.code = 'ENOENT';
      throw err;
    }

    const applyChown = (targetNode) => {
      if (owner) {
        targetNode.owner = owner;
        targetNode.uid = owner === 'root' ? 0 : 1000;
      }
      if (group) {
        targetNode.group = group;
        targetNode.gid = group === 'root' ? 0 : 1000;
      }
      targetNode.ctime = new Date();
      if (recursive && targetNode.type === 'dir' && targetNode.children) {
        for (const child of Object.values(targetNode.children)) {
          applyChown(child);
        }
      }
    };

    applyChown(node);
  }

  /**
   * Liste les noms des entrées contenues dans un répertoire
   * @param {string} pathStr
   * @param {string} [cwd=this.cwd]
   * @returns {string[]}
   */
  readdir(pathStr, cwd = this.cwd) {
    const node = this.resolve(pathStr, { cwd, checkPermissions: true });
    if (!node) {
      const err = new Error(`cannot access '${pathStr}': No such file or directory`);
      err.code = 'ENOENT';
      throw err;
    }
    if (node.type !== 'dir') {
      const err = new Error(`Not a directory: '${pathStr}'`);
      err.code = 'ENOTDIR';
      throw err;
    }
    if (!this.checkAccess(node, 4)) {
      const err = new Error(`Permission denied: '${pathStr}'`);
      err.code = 'EACCES';
      throw err;
    }

    node.atime = new Date();
    return Object.keys(node.children || {}).sort();
  }

  /**
   * Retourne les métadonnées (stat) d'un fichier ou dossier
   * @param {string} pathStr
   * @param {string} [cwd=this.cwd]
   * @returns {Object}
   */
  stat(pathStr, cwd = this.cwd) {
    const node = this.resolve(pathStr, { cwd, followSymlinks: true });
    if (!node) {
      const err = new Error(`cannot stat '${pathStr}': No such file or directory`);
      err.code = 'ENOENT';
      throw err;
    }
    return {
      inode: node.inode,
      name: node.name,
      type: node.type,
      mode: node.mode,
      size: node.size,
      uid: node.uid,
      gid: node.gid,
      owner: node.owner,
      group: node.group,
      mtime: node.mtime,
      atime: node.atime,
      ctime: node.ctime,
      nlink: node.nlink,
      permissionsString: node.getPermissionsString(),
      octalMode: node.getOctalPermissions(),
      isDirectory: () => node.isDirectory(),
      isFile: () => node.isFile(),
      isSymbolicLink: () => node.isSymbolicLink()
    };
  }

  // =========================================================================
  // Snapshotting, Restauration & Initialisation de Défi
  // =========================================================================

  /**
   * Crée une capture sérialisable complète de l'état du système de fichiers
   * @returns {Object} Snapshot JSON pur
   */
  snapshot() {
    const serializeNode = (node) => {
      const res = {
        name: node.name,
        type: node.type,
        mode: node.mode,
        uid: node.uid,
        gid: node.gid,
        owner: node.owner,
        group: node.group,
        content: node.content,
        target: node.target,
        mtime: node.mtime.toISOString(),
        inode: node.inode,
        nlink: node.nlink
      };
      if (node.type === 'dir' && node.children) {
        res.children = {};
        for (const [k, v] of Object.entries(node.children)) {
          res.children[k] = serializeNode(v);
        }
      }
      return res;
    };

    return {
      cwd: this.cwd,
      oldpwd: this.oldpwd,
      currentUser: { ...this.currentUser },
      umask: this.umask,
      root: serializeNode(this.root)
    };
  }

  /**
   * Restaure le système de fichiers à partir d'un snapshot
   * @param {Object} snap
   */
  restore(snap) {
    if (!snap || !snap.root) return;

    this.cwd = snap.cwd || '/home/student';
    this.oldpwd = snap.oldpwd || '/home/student';
    this.currentUser = snap.currentUser ? { ...snap.currentUser } : { name: 'student', uid: 1000, gid: 1000 };
    this.umask = snap.umask !== undefined ? snap.umask : 0o022;

    const deserializeNode = (data, parentNode = null) => {
      const node = new VFSNode({
        name: data.name,
        type: data.type,
        mode: data.mode,
        uid: data.uid,
        gid: data.gid,
        owner: data.owner,
        group: data.group,
        content: data.content,
        target: data.target,
        mtime: new Date(data.mtime),
        parent: parentNode
      });
      node.inode = data.inode;
      node.nlink = data.nlink;

      if (data.type === 'dir' && data.children) {
        node.children = {};
        for (const [k, v] of Object.entries(data.children)) {
          node.children[k] = deserializeNode(v, node);
        }
      }
      return node;
    };

    this.root = deserializeNode(snap.root, null);
  }

  /**
   * Charge un état initial de défi (supporte les formats `{ "/path": { files: {...} } }`
   * et `{ dirs: [...], files: [...] }`)
   * @param {Object} fsDict
   */
  loadInitialFS(fsDict) {
    if (!fsDict || typeof fsDict !== 'object') return;

    // Format avec listes "dirs" et "files"
    if (Array.isArray(fsDict.dirs) || Array.isArray(fsDict.files)) {
      if (Array.isArray(fsDict.dirs)) {
        for (const d of fsDict.dirs) {
          const path = typeof d === 'string' ? d : d.path;
          const mode = (typeof d === 'object' && d.mode) ? parseInt(d.mode, 8) : 0o755;
          this.mkdir(path, { recursive: true, mode });
        }
      }
      if (Array.isArray(fsDict.files)) {
        for (const f of fsDict.files) {
          const path = f.path;
          const content = f.content !== undefined ? f.content : '';
          const mode = f.mode ? (typeof f.mode === 'string' ? parseInt(f.mode, 8) : f.mode) : 0o644;
          const node = this.writeFile(path, content, '/', { mode });
          if (f.owner) node.owner = f.owner;
          if (f.group) node.group = f.group;
        }
      }
      return;
    }

    // Format clé/valeur arborescente `{ "/home/student": { files: { "file.txt": { content: "..." } } } }`
    for (const [dirPath, dirDef] of Object.entries(fsDict)) {
      this.mkdir(dirPath, { recursive: true });
      if (dirDef && dirDef.files) {
        for (const [fName, fDef] of Object.entries(dirDef.files)) {
          const fullPath = dirPath.endsWith('/') ? `${dirPath}${fName}` : `${dirPath}/${fName}`;
          if (fDef.type === 'dir') {
            this.mkdir(fullPath, { recursive: true });
          } else {
            const content = fDef.content !== undefined ? fDef.content : '';
            const mode = fDef.permissions ? (typeof fDef.permissions === 'string' && /^[0-7]+$/.test(fDef.permissions) ? parseInt(fDef.permissions, 8) : 0o644) : 0o644;
            const node = this.writeFile(fullPath, content, '/', { mode });
            if (fDef.owner) node.owner = fDef.owner;
            if (fDef.group) node.group = fDef.group;
            if (fDef.permissions && typeof fDef.permissions === 'string' && !/^[0-7]+$/.test(fDef.permissions)) {
              this.chmod(fullPath, fDef.permissions);
            }
          }
        }
      }
    }
  }
}
