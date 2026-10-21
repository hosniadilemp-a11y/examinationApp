/**
 * POSIX Commands Suite
 * Implémentation des 23 commandes fondamentales et des utilitaires de filtrage
 * pour le terminal virtuel et le bac à sable VFS du Centre d'Entraînement Linux.
 * 
 * Signature de chaque commande :
 * (args: string[], stdin: string, context: ShellContext) => Promise<CommandResult> | CommandResult
 * avec CommandResult = { stdout: string, stderr: string, exitCode: number }
 */

// =========================================================================
// Utilitaires Internes
// =========================================================================

function formatSizeHuman(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}M`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)}G`;
}

function formatDateLs(date) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const d = date instanceof Date ? date : new Date(date || Date.now());
  const month = months[d.getMonth()];
  const day = String(d.getDate()).padStart(2, ' ');
  const hours = String(d.getHours()).padStart(2, '0');
  const mins = String(d.getMinutes()).padStart(2, '0');
  return `${month} ${day} ${hours}:${mins}`;
}

function globToRegex(glob, caseInsensitive = false) {
  let reStr = '^';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') reStr += '.*';
    else if (c === '?') reStr += '.';
    else if ('\\.^$|()[]{}!+='.includes(c)) reStr += '\\' + c;
    else reStr += c;
  }
  reStr += '$';
  return new RegExp(reStr, caseInsensitive ? 'i' : '');
}

function parseEscapeSequences(str) {
  return str.replace(/\\([abefnrtv\\'"0-7]|x[0-9a-fA-F]{1,2}|c)/g, (match, code) => {
    switch (code) {
      case 'a': return '\x07';
      case 'b': return '\b';
      case 'e': return '\x1b';
      case 'f': return '\f';
      case 'n': return '\n';
      case 'r': return '\r';
      case 't': return '\t';
      case 'v': return '\v';
      case '\\': return '\\';
      case "'": return "'";
      case '"': return '"';
      default:
        if (code.startsWith('x')) {
          return String.fromCharCode(parseInt(code.slice(1), 16));
        }
        if (/^[0-7]+$/.test(code)) {
          return String.fromCharCode(parseInt(code, 8));
        }
        return match;
    }
  });
}

// =========================================================================
// Registre des Commandes POSIX
// =========================================================================

export const POSIX_COMMANDS = {

  // -----------------------------------------------------------------------
  // 1. pwd — Print Working Directory
  // -----------------------------------------------------------------------
  pwd(args, stdin, context) {
    const cwd = context.cwd || (context.vfs ? context.vfs.cwd : '/home/student');
    return {
      stdout: `${cwd}\n`,
      stderr: '',
      exitCode: 0
    };
  },

  // -----------------------------------------------------------------------
  // 2. cd — Change Working Directory
  // -----------------------------------------------------------------------
  cd(args, stdin, context) {
    const vfs = context.vfs;
    let target = args[0] || '~';
    let isOldPwd = false;

    if (target === '-') {
      target = context.env?.OLDPWD || (vfs ? vfs.oldpwd : '/home/student');
      isOldPwd = true;
    }

    const currentCwd = context.cwd || (vfs ? vfs.cwd : '/home/student');
    const normalized = vfs ? vfs.normalizePath(target, currentCwd) : target;
    const node = vfs ? vfs.resolve(normalized, { cwd: currentCwd }) : null;

    if (!node) {
      return {
        stdout: '',
        stderr: `cd: ${target}: No such file or directory\n`,
        exitCode: 1
      };
    }

    if (node.type !== 'dir') {
      return {
        stdout: '',
        stderr: `cd: ${target}: Not a directory\n`,
        exitCode: 1
      };
    }

    if (vfs && !vfs.checkAccess(node, 1, context.currentUser)) {
      return {
        stdout: '',
        stderr: `cd: ${target}: Permission denied\n`,
        exitCode: 1
      };
    }

    const oldCwd = currentCwd;
    context.cwd = normalized;
    if (context.setCwd) context.setCwd(normalized);
    if (vfs) {
      vfs.cwd = normalized;
      vfs.oldpwd = oldCwd;
    }
    if (context.env) {
      context.env.OLDPWD = oldCwd;
      context.env.PWD = normalized;
    }

    return {
      stdout: isOldPwd ? `${normalized}\n` : '',
      stderr: '',
      exitCode: 0
    };
  },

  // -----------------------------------------------------------------------
  // 3. ls — List Directory Contents
  // -----------------------------------------------------------------------
  ls(args, stdin, context) {
    const vfs = context.vfs;
    let showAll = false;
    let showLong = false;
    let humanReadable = false;
    let onePerLine = false;
    let dirOnly = false;
    let reverse = false;
    let sortByTime = false;
    const targets = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '--') {
        targets.push(...args.slice(i + 1));
        break;
      }
      if (a.startsWith('-') && a.length > 1) {
        for (let j = 1; j < a.length; j++) {
          const opt = a[j];
          if (opt === 'a') showAll = true;
          else if (opt === 'l') showLong = true;
          else if (opt === 'h') humanReadable = true;
          else if (opt === '1') onePerLine = true;
          else if (opt === 'd') dirOnly = true;
          else if (opt === 'r') reverse = true;
          else if (opt === 't') sortByTime = true;
        }
      } else {
        targets.push(a);
      }
    }

    const currentCwd = context.cwd || (vfs ? vfs.cwd : '/home/student');
    const queryPaths = targets.length > 0 ? targets : ['.'];
    const outputBlocks = [];
    let exitCode = 0;
    let stderr = '';

    for (const p of queryPaths) {
      const absPath = vfs ? vfs.normalizePath(p, currentCwd) : p;
      const node = vfs ? vfs.resolve(absPath, { cwd: currentCwd }) : null;

      if (!node) {
        stderr += `ls: cannot access '${p}': No such file or directory\n`;
        exitCode = 2;
        continue;
      }

      if (node.type !== 'dir' || dirOnly) {
        if (showLong) {
          const perms = node.getPermissionsString();
          const nlink = node.nlink || 1;
          const owner = node.owner || 'student';
          const group = node.group || 'student';
          const sizeStr = humanReadable ? formatSizeHuman(node.size) : String(node.size);
          const dateStr = formatDateLs(node.mtime);
          let line = `${perms} ${nlink} ${owner} ${group} ${sizeStr.padStart(6)} ${dateStr} ${p}`;
          if (node.type === 'symlink') line += ` -> ${node.target}`;
          outputBlocks.push(line);
        } else {
          outputBlocks.push(p);
        }
        continue;
      }

      // Dossier ciblé
      if (vfs && !vfs.checkAccess(node, 4, context.currentUser)) {
        stderr += `ls: cannot open directory '${p}': Permission denied\n`;
        exitCode = 2;
        continue;
      }

      let entries = Object.keys(node.children || {});
      if (showAll) {
        entries = ['.', '..', ...entries];
      } else {
        entries = entries.filter(e => !e.startsWith('.'));
      }

      // Tri
      entries.sort((a, b) => {
        if (sortByTime) {
          const nodeA = a === '.' ? node : (a === '..' ? (node.parent || node) : node.children[a]);
          const nodeB = b === '.' ? node : (b === '..' ? (node.parent || node) : node.children[b]);
          const tA = nodeA?.mtime?.getTime() || 0;
          const tB = nodeB?.mtime?.getTime() || 0;
          if (tA !== tB) return tB - tA;
        }
        return a.localeCompare(b);
      });
      if (reverse) entries.reverse();

      const blockLines = [];
      if (queryPaths.length > 1) {
        blockLines.push(`${p}:`);
      }

      if (showLong) {
        for (const name of entries) {
          let itemNode = name === '.' ? node : (name === '..' ? (node.parent || node) : node.children[name]);
          if (!itemNode) continue;
          const perms = itemNode.getPermissionsString();
          const nlink = itemNode.nlink || (itemNode.type === 'dir' ? 2 : 1);
          const owner = itemNode.owner || 'student';
          const group = itemNode.group || 'student';
          const sizeStr = humanReadable ? formatSizeHuman(itemNode.size) : String(itemNode.size);
          const dateStr = formatDateLs(itemNode.mtime);
          let row = `${perms} ${nlink} ${owner} ${group} ${sizeStr.padStart(6)} ${dateStr} ${name}`;
          if (itemNode.type === 'symlink') row += ` -> ${itemNode.target}`;
          blockLines.push(row);
        }
      } else if (onePerLine) {
        blockLines.push(...entries);
      } else {
        blockLines.push(entries.join('  '));
      }

      outputBlocks.push(blockLines.join('\n'));
    }

    const stdout = outputBlocks.filter(Boolean).join('\n\n') + (outputBlocks.length > 0 ? '\n' : '');
    return { stdout, stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 4. cat — Concatenate and Print Files
  // -----------------------------------------------------------------------
  cat(args, stdin, context) {
    const vfs = context.vfs;
    let numberAll = false;
    let numberNonBlank = false;
    let squeezeBlank = false;
    const files = [];

    for (const a of args) {
      if (a === '-n') numberAll = true;
      else if (a === '-b') numberNonBlank = true;
      else if (a === '-s') squeezeBlank = true;
      else files.push(a);
    }

    let rawContent = '';
    let stderr = '';
    let exitCode = 0;

    if (files.length === 0 || (files.length === 1 && files[0] === '-')) {
      rawContent = stdin || '';
    } else {
      for (const f of files) {
        if (f === '-') {
          rawContent += stdin || '';
          continue;
        }
        try {
          const text = vfs.readFile(f, context.cwd);
          rawContent += text;
        } catch (err) {
          exitCode = 1;
          if (err.code === 'ENOENT') stderr += `cat: ${f}: No such file or directory\n`;
          else if (err.code === 'EISDIR') stderr += `cat: ${f}: Is a directory\n`;
          else if (err.code === 'EACCES') stderr += `cat: ${f}: Permission denied\n`;
          else stderr += `cat: ${f}: ${err.message}\n`;
        }
      }
    }

    if (exitCode !== 0 && !rawContent) {
      return { stdout: '', stderr, exitCode };
    }

    // Traitement des lignes (-n, -b, -s)
    let lines = rawContent.split('\n');
    // Si la fin de rawContent se termine par un newline, split produit un élément vide final
    const endsWithNewline = rawContent.endsWith('\n');
    if (endsWithNewline) lines.pop();

    if (squeezeBlank) {
      const squeezed = [];
      let lastWasBlank = false;
      for (const line of lines) {
        const isBlank = line.trim() === '';
        if (isBlank && lastWasBlank) continue;
        squeezed.push(line);
        lastWasBlank = isBlank;
      }
      lines = squeezed;
    }

    let lineCounter = 1;
    const formattedLines = lines.map(line => {
      const isBlank = line.trim() === '';
      if (numberNonBlank) {
        if (!isBlank) {
          const numStr = String(lineCounter++).padStart(6, ' ');
          return `${numStr}\t${line}`;
        }
        return line;
      }
      if (numberAll) {
        const numStr = String(lineCounter++).padStart(6, ' ');
        return `${numStr}\t${line}`;
      }
      return line;
    });

    let stdout = formattedLines.join('\n');
    if (endsWithNewline || (stdout.length > 0 && !rawContent)) {
      stdout += '\n';
    }

    return { stdout, stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 5. touch — Update File Timestamps / Create File
  // -----------------------------------------------------------------------
  touch(args, stdin, context) {
    const vfs = context.vfs;
    let noCreate = false;
    const files = [];

    for (const a of args) {
      if (a === '-c' || a === '--no-create') noCreate = true;
      else files.push(a);
    }

    if (files.length === 0) {
      return { stdout: '', stderr: 'touch: missing file operand\n', exitCode: 1 };
    }

    let stderr = '';
    let exitCode = 0;

    for (const f of files) {
      const node = vfs.resolve(f, { cwd: context.cwd });
      if (node) {
        node.mtime = new Date();
        node.atime = new Date();
      } else {
        if (!noCreate) {
          try {
            vfs.writeFile(f, '', context.cwd);
          } catch (err) {
            exitCode = 1;
            if (err.code === 'ENOENT') stderr += `touch: cannot touch '${f}': No such file or directory\n`;
            else if (err.code === 'EACCES') stderr += `touch: cannot touch '${f}': Permission denied\n`;
            else stderr += `touch: cannot touch '${f}': ${err.message}\n`;
          }
        }
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 6. mkdir — Make Directories
  // -----------------------------------------------------------------------
  mkdir(args, stdin, context) {
    const vfs = context.vfs;
    let recursive = false;
    let mode = undefined;
    const dirs = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-p' || a === '--parents') {
        recursive = true;
      } else if (a === '-m' && args[i + 1]) {
        mode = parseInt(args[++i], 8);
      } else if (a.startsWith('-m=')) {
        mode = parseInt(a.slice(3), 8);
      } else {
        dirs.push(a);
      }
    }

    if (dirs.length === 0) {
      return { stdout: '', stderr: 'mkdir: missing operand\n', exitCode: 1 };
    }

    let stderr = '';
    let exitCode = 0;

    for (const d of dirs) {
      try {
        vfs.mkdir(d, { recursive, mode }, context.cwd);
      } catch (err) {
        exitCode = 1;
        if (err.code === 'EEXIST') stderr += `mkdir: cannot create directory '${d}': File exists\n`;
        else if (err.code === 'ENOENT') stderr += `mkdir: cannot create directory '${d}': No such file or directory\n`;
        else if (err.code === 'EACCES') stderr += `mkdir: cannot create directory '${d}': Permission denied\n`;
        else stderr += `mkdir: cannot create directory '${d}': ${err.message}\n`;
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 7. rm — Remove Files or Directories
  // -----------------------------------------------------------------------
  rm(args, stdin, context) {
    const vfs = context.vfs;
    let recursive = false;
    let force = false;
    const targets = [];

    for (const a of args) {
      if (a.startsWith('-') && a.length > 1) {
        if (a.includes('r') || a.includes('R')) recursive = true;
        if (a.includes('f')) force = true;
      } else {
        targets.push(a);
      }
    }

    if (targets.length === 0) {
      if (force) return { stdout: '', stderr: '', exitCode: 0 };
      return { stdout: '', stderr: 'rm: missing operand\n', exitCode: 1 };
    }

    let stderr = '';
    let exitCode = 0;

    for (const t of targets) {
      try {
        vfs.remove(t, { recursive, force }, context.cwd);
      } catch (err) {
        if (err.message.includes('dangerous')) {
          stderr += `rm: it is dangerous to operate recursively on '/'\n`;
          exitCode = 1;
          continue;
        }
        if (force) continue;
        exitCode = 1;
        if (err.code === 'ENOENT') {
          stderr += `rm: cannot remove '${t}': No such file or directory\n`;
        } else if (err.code === 'EISDIR') {
          stderr += `rm: cannot remove '${t}': Is a directory\n`;
        } else if (err.code === 'EACCES') {
          stderr += `rm: cannot remove '${t}': Permission denied\n`;
        } else {
          stderr += `rm: cannot remove '${t}': ${err.message}\n`;
        }
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 8. cp — Copy Files and Directories
  // -----------------------------------------------------------------------
  cp(args, stdin, context) {
    const vfs = context.vfs;
    let recursive = false;
    let force = false;
    let preserve = false;
    const paths = [];

    for (const a of args) {
      if (a.startsWith('-') && a.length > 1) {
        if (a.includes('r') || a.includes('R')) recursive = true;
        if (a.includes('f')) force = true;
        if (a.includes('p')) preserve = true;
      } else {
        paths.push(a);
      }
    }

    if (paths.length < 2) {
      return { stdout: '', stderr: 'cp: missing file operand\n', exitCode: 1 };
    }

    const dst = paths.pop();
    let stderr = '';
    let exitCode = 0;

    for (const src of paths) {
      try {
        vfs.copy(src, dst, { recursive, force, preserve }, context.cwd);
      } catch (err) {
        exitCode = 1;
        if (err.code === 'EISDIR') {
          stderr += `cp: -r not specified; omitting directory '${src}'\n`;
        } else if (err.code === 'ENOENT') {
          stderr += `cp: cannot stat '${src}': No such file or directory\n`;
        } else if (err.code === 'EACCES') {
          stderr += `cp: cannot copy '${src}': Permission denied\n`;
        } else {
          stderr += `cp: ${err.message}\n`;
        }
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 9. mv — Move / Rename Files and Directories
  // -----------------------------------------------------------------------
  mv(args, stdin, context) {
    const vfs = context.vfs;
    const paths = args.filter(a => !a.startsWith('-'));

    if (paths.length < 2) {
      return { stdout: '', stderr: 'mv: missing file operand\n', exitCode: 1 };
    }

    const dst = paths.pop();
    let stderr = '';
    let exitCode = 0;

    for (const src of paths) {
      try {
        vfs.move(src, dst, context.cwd);
      } catch (err) {
        exitCode = 1;
        if (err.code === 'ENOENT') {
          stderr += `mv: cannot stat '${src}': No such file or directory\n`;
        } else if (err.message.includes('subdirectory of itself')) {
          stderr += `mv: cannot move '${src}' to a subdirectory of itself\n`;
        } else {
          stderr += `mv: ${err.message}\n`;
        }
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 10. echo — Display a Line of Text
  // -----------------------------------------------------------------------
  echo(args, stdin, context) {
    let noNewline = false;
    let enableEscapes = false;
    const tokens = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-n') {
        noNewline = true;
      } else if (a === '-e') {
        enableEscapes = true;
      } else if (a === '-E') {
        enableEscapes = false;
      } else if (a === '-ne' || a === '-en') {
        noNewline = true;
        enableEscapes = true;
      } else {
        tokens.push(a);
      }
    }

    let text = tokens.join(' ');
    if (enableEscapes) {
      text = parseEscapeSequences(text);
    }
    if (!noNewline) {
      text += '\n';
    }

    return { stdout: text, stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 11. head — Output the First Part of Files
  // -----------------------------------------------------------------------
  head(args, stdin, context) {
    const vfs = context.vfs;
    let n = 10;
    const files = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-n' && args[i + 1]) {
        n = parseInt(args[++i], 10) || 10;
      } else if (a.startsWith('-n') && /^-n\d+$/.test(a)) {
        n = parseInt(a.slice(2), 10);
      } else if (/^-\d+$/.test(a)) {
        n = parseInt(a.slice(1), 10);
      } else {
        files.push(a);
      }
    }

    let stderr = '';
    let exitCode = 0;
    const outParts = [];

    if (files.length === 0) {
      const lines = (stdin || '').split('\n').slice(0, n);
      return { stdout: lines.join('\n') + (lines.length > 0 ? '\n' : ''), stderr: '', exitCode: 0 };
    }

    for (const f of files) {
      try {
        const text = vfs.readFile(f, context.cwd);
        const lines = text.split('\n');
        if (text.endsWith('\n')) lines.pop();
        const selected = lines.slice(0, n);

        if (files.length > 1) {
          outParts.push(`==> ${f} <==\n` + selected.join('\n') + '\n');
        } else {
          outParts.push(selected.join('\n') + (selected.length > 0 ? '\n' : ''));
        }
      } catch (err) {
        exitCode = 1;
        stderr += `head: cannot open '${f}' for reading: No such file or directory\n`;
      }
    }

    return { stdout: outParts.join('\n'), stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 12. tail — Output the Last Part of Files
  // -----------------------------------------------------------------------
  tail(args, stdin, context) {
    const vfs = context.vfs;
    let n = 10;
    let plusMode = false;
    const files = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-n' && args[i + 1]) {
        const val = args[++i];
        if (val.startsWith('+')) {
          plusMode = true;
          n = parseInt(val.slice(1), 10) || 1;
        } else {
          n = parseInt(val, 10) || 10;
        }
      } else if (/^-\d+$/.test(a)) {
        n = parseInt(a.slice(1), 10);
      } else {
        files.push(a);
      }
    }

    const processLines = (text) => {
      const lines = text.split('\n');
      if (text.endsWith('\n')) lines.pop();
      if (plusMode) {
        // tail -n +N commence à la ligne N (1-indexé)
        return lines.slice(Math.max(0, n - 1));
      }
      return lines.slice(-n);
    };

    if (files.length === 0) {
      const selected = processLines(stdin || '');
      return { stdout: selected.join('\n') + (selected.length > 0 ? '\n' : ''), stderr: '', exitCode: 0 };
    }

    let stderr = '';
    let exitCode = 0;
    const outParts = [];

    for (const f of files) {
      try {
        const text = vfs.readFile(f, context.cwd);
        const selected = processLines(text);
        if (files.length > 1) {
          outParts.push(`==> ${f} <==\n` + selected.join('\n') + '\n');
        } else {
          outParts.push(selected.join('\n') + (selected.length > 0 ? '\n' : ''));
        }
      } catch (err) {
        exitCode = 1;
        stderr += `tail: cannot open '${f}' for reading: No such file or directory\n`;
      }
    }

    return { stdout: outParts.join('\n'), stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 13. wc — Word, Line, Character, and Byte Count
  // -----------------------------------------------------------------------
  wc(args, stdin, context) {
    const vfs = context.vfs;
    let countLines = false;
    let countWords = false;
    let countBytes = false;
    let countChars = false;
    const files = [];

    for (const a of args) {
      if (a.startsWith('-') && a.length > 1) {
        if (a.includes('l')) countLines = true;
        if (a.includes('w')) countWords = true;
        if (a.includes('c')) countBytes = true;
        if (a.includes('m')) countChars = true;
      } else {
        files.push(a);
      }
    }

    if (!countLines && !countWords && !countBytes && !countChars) {
      countLines = true;
      countWords = true;
      countBytes = true;
    }

    const calcCounts = (text) => {
      const rawLines = text.split('\n');
      const lines = text ? (rawLines.length - (text.endsWith('\n') ? 1 : 0)) : 0;
      const words = text ? text.trim().split(/\s+/).filter(Boolean).length : 0;
      const bytes = new TextEncoder().encode(text).length;
      const chars = text.length;
      return { lines, words, bytes, chars };
    };

    const formatRow = (counts, label = '') => {
      const parts = [];
      if (countLines) parts.push(String(counts.lines).padStart(7, ' '));
      if (countWords) parts.push(String(counts.words).padStart(7, ' '));
      if (countChars) parts.push(String(counts.chars).padStart(7, ' '));
      if (countBytes && !countChars) parts.push(String(counts.bytes).padStart(7, ' '));
      let row = parts.join(' ');
      if (label) row += ` ${label}`;
      return row;
    };

    if (files.length === 0) {
      const counts = calcCounts(stdin || '');
      return { stdout: formatRow(counts) + '\n', stderr: '', exitCode: 0 };
    }

    let stderr = '';
    let exitCode = 0;
    const rows = [];
    const totals = { lines: 0, words: 0, bytes: 0, chars: 0 };

    for (const f of files) {
      try {
        const text = vfs.readFile(f, context.cwd);
        const counts = calcCounts(text);
        totals.lines += counts.lines;
        totals.words += counts.words;
        totals.bytes += counts.bytes;
        totals.chars += counts.chars;
        rows.push(formatRow(counts, f));
      } catch (err) {
        exitCode = 1;
        stderr += `wc: ${f}: No such file or directory\n`;
      }
    }

    if (files.length > 1) {
      rows.push(formatRow(totals, 'total'));
    }

    return { stdout: rows.join('\n') + (rows.length > 0 ? '\n' : ''), stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 14. chmod — Change File Mode Bits
  // -----------------------------------------------------------------------
  chmod(args, stdin, context) {
    const vfs = context.vfs;
    let recursive = false;
    let modeSpec = null;
    const files = [];

    for (const a of args) {
      if (a === '-R' || a === '--recursive') {
        recursive = true;
      } else if (!modeSpec) {
        modeSpec = a;
      } else {
        files.push(a);
      }
    }

    if (!modeSpec || files.length === 0) {
      return { stdout: '', stderr: 'chmod: missing operand\n', exitCode: 1 };
    }

    let stderr = '';
    let exitCode = 0;

    for (const f of files) {
      try {
        vfs.chmod(f, modeSpec, { recursive, user: context.currentUser }, context.cwd);
      } catch (err) {
        exitCode = 1;
        if (err.code === 'EINVAL') {
          stderr += `chmod: invalid mode: '${modeSpec}'\n`;
          break;
        } else if (err.code === 'EPERM') {
          stderr += `chmod: changing permissions of '${f}': Operation not permitted\n`;
        } else if (err.code === 'ENOENT') {
          stderr += `chmod: cannot access '${f}': No such file or directory\n`;
        } else {
          stderr += `chmod: ${err.message}\n`;
        }
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 15. chown — Change File Owner and Group
  // -----------------------------------------------------------------------
  chown(args, stdin, context) {
    const vfs = context.vfs;
    let recursive = false;
    let ownerSpec = null;
    const files = [];

    for (const a of args) {
      if (a === '-R' || a === '--recursive') {
        recursive = true;
      } else if (!ownerSpec) {
        ownerSpec = a;
      } else {
        files.push(a);
      }
    }

    if (!ownerSpec || files.length === 0) {
      return { stdout: '', stderr: 'chown: missing operand\n', exitCode: 1 };
    }

    // Seul root peut chown sous POSIX GNU/Linux
    if (context.currentUser?.uid !== 0) {
      return {
        stdout: '',
        stderr: `chown: changing ownership of '${files[0]}': Operation not permitted\n`,
        exitCode: 1
      };
    }

    let [owner, group] = ownerSpec.split(':');
    let stderr = '';
    let exitCode = 0;

    for (const f of files) {
      try {
        vfs.chown(f, owner, group || null, { recursive, user: context.currentUser }, context.cwd);
      } catch (err) {
        exitCode = 1;
        stderr += `chown: ${err.message}\n`;
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 16. whoami — Print Effective User ID
  // -----------------------------------------------------------------------
  whoami(args, stdin, context) {
    const user = context.currentUser?.name || context.env?.USER || 'student';
    return { stdout: `${user}\n`, stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 17. uname — Print System Information
  // -----------------------------------------------------------------------
  uname(args, stdin, context) {
    let all = false;
    let kernelName = false;
    let nodename = false;
    let release = false;
    let version = false;
    let machine = false;
    let os = false;

    for (const a of args) {
      if (a === '-a' || a === '--all') all = true;
      else if (a === '-s') kernelName = true;
      else if (a === '-n') nodename = true;
      else if (a === '-r') release = true;
      else if (a === '-v') version = true;
      else if (a === '-m') machine = true;
      else if (a === '-o') os = true;
    }

    if (!all && !kernelName && !nodename && !release && !version && !machine && !os) {
      kernelName = true;
    }

    if (all) {
      return {
        stdout: 'Linux examquiz 5.15.0-89-generic #99-Ubuntu SMP Mon Oct 20 12:00:00 UTC 2026 x86_64 GNU/Linux\n',
        stderr: '',
        exitCode: 0
      };
    }

    const parts = [];
    if (kernelName) parts.push('Linux');
    if (nodename) parts.push('examquiz');
    if (release) parts.push('5.15.0-89-generic');
    if (version) parts.push('#99-Ubuntu SMP Mon Oct 20 12:00:00 UTC 2026');
    if (machine) parts.push('x86_64');
    if (os) parts.push('GNU/Linux');

    return { stdout: parts.join(' ') + '\n', stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 18. date — Display System Date and Time
  // -----------------------------------------------------------------------
  date(args, stdin, context) {
    const now = new Date();
    let format = null;

    for (const a of args) {
      if (a.startsWith('+')) {
        format = a.slice(1);
      }
    }

    if (!format) {
      // Ex: "Tue Oct 20 14:38:00 UTC 2026"
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const dName = days[now.getUTCDay()];
      const mName = months[now.getUTCMonth()];
      const day = String(now.getUTCDate()).padStart(2, '0');
      const time = now.toTimeString().split(' ')[0];
      const year = now.getUTCFullYear();
      return { stdout: `${dName} ${mName} ${day} ${time} UTC ${year}\n`, stderr: '', exitCode: 0 };
    }

    const pad = (n) => String(n).padStart(2, '0');
    const replacements = {
      '%Y': now.getFullYear(),
      '%m': pad(now.getMonth() + 1),
      '%d': pad(now.getDate()),
      '%H': pad(now.getHours()),
      '%M': pad(now.getMinutes()),
      '%S': pad(now.getSeconds()),
      '%s': Math.floor(now.getTime() / 1000),
      '%F': `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
      '%T': `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
      '%Z': 'UTC'
    };

    let result = format;
    for (const [k, v] of Object.entries(replacements)) {
      result = result.replaceAll(k, v);
    }
    return { stdout: result + '\n', stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 19. uptime — Tell How Long System Has Been Running
  // -----------------------------------------------------------------------
  uptime(args, stdin, context) {
    let pretty = args.includes('-p');
    if (pretty) {
      return { stdout: 'up 3 days, 5 hours, 15 minutes\n', stderr: '', exitCode: 0 };
    }
    return {
      stdout: ' 14:35:10 up 3 days,  5:15,  1 user,  load average: 0.05, 0.03, 0.01\n',
      stderr: '',
      exitCode: 0
    };
  },

  // -----------------------------------------------------------------------
  // 20. env — Display Environment Variables
  // -----------------------------------------------------------------------
  env(args, stdin, context) {
    const env = context.env || {};
    const lines = Object.entries(env)
      .filter(([k]) => k !== '?' && !k.startsWith('_'))
      .map(([k, v]) => `${k}=${v}`);
    return { stdout: lines.join('\n') + (lines.length > 0 ? '\n' : ''), stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 21. export — Set Environment Variables
  // -----------------------------------------------------------------------
  export(args, stdin, context) {
    if (!context.env) context.env = {};

    if (args.length === 0) {
      const sorted = Object.entries(context.env)
        .filter(([k]) => k !== '?' && !k.startsWith('_'))
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, v]) => `declare -x ${k}="${v}"`);
      return { stdout: sorted.join('\n') + (sorted.length > 0 ? '\n' : ''), stderr: '', exitCode: 0 };
    }

    let stderr = '';
    let exitCode = 0;

    for (const a of args) {
      const eqIdx = a.indexOf('=');
      const name = eqIdx === -1 ? a : a.slice(0, eqIdx);
      const val = eqIdx === -1 ? '' : a.slice(eqIdx + 1).replace(/^["']|["']$/g, '');

      if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
        stderr += `export: '${a}': not a valid identifier\n`;
        exitCode = 1;
        continue;
      }

      if (eqIdx !== -1) {
        context.env[name] = val;
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 22. ps — Report Current Processes
  // -----------------------------------------------------------------------
  ps(args, stdin, context) {
    const defaultProcs = [
      { pid: 1, user: 'root', cpu: '0.0', mem: '0.1', vsz: '21424', rss: '5420', tty: '?', stat: 'Ss', start: '09:00', time: '0:01', cmd: '/sbin/init' },
      { pid: 2, user: 'root', cpu: '0.0', mem: '0.0', vsz: '0', rss: '0', tty: '?', stat: 'S', start: '09:00', time: '0:00', cmd: '[kthreadd]' },
      { pid: 101, user: 'student', cpu: '0.0', mem: '0.1', vsz: '13560', rss: '3840', tty: 'pts/0', stat: 'Ss', start: '09:15', time: '0:00', cmd: '-bash' },
      { pid: 115, user: 'student', cpu: '0.0', mem: '0.0', vsz: '15280', rss: '2100', tty: 'pts/0', stat: 'R+', start: '10:30', time: '0:00', cmd: 'ps' }
    ];

    const procs = context.processes || defaultProcs;
    const isAux = args.some(a => a.includes('aux') || a === '-ef' || a === '-A');

    if (isAux) {
      const header = 'USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND';
      const lines = procs.map(p => {
        const u = (p.user || 'student').padEnd(8, ' ');
        const pid = String(p.pid).padStart(5, ' ');
        const cpu = (p.cpu || '0.0').padStart(4, ' ');
        const mem = (p.mem || '0.1').padStart(4, ' ');
        const vsz = (p.vsz || '13560').padStart(6, ' ');
        const rss = (p.rss || '3840').padStart(5, ' ');
        const tty = (p.tty || 'pts/0').padEnd(8, ' ');
        const stat = (p.stat || 'S').padEnd(4, ' ');
        const start = (p.start || '09:00').padEnd(7, ' ');
        const time = (p.time || '0:00').padEnd(6, ' ');
        return `${u} ${pid} ${cpu} ${mem} ${vsz} ${rss} ${tty} ${stat} ${start} ${time} ${p.cmd}`;
      });
      return { stdout: `${header}\n${lines.join('\n')}\n`, stderr: '', exitCode: 0 };
    }

    const header = '  PID TTY          TIME CMD';
    const lines = procs
      .filter(p => p.tty === 'pts/0' || p.user === 'student')
      .map(p => {
        const pid = String(p.pid).padStart(5, ' ');
        const tty = (p.tty || 'pts/0').padEnd(8, ' ');
        const time = (p.time || '00:00:00').padEnd(8, ' ');
        return `${pid} ${tty} ${time} ${p.cmd}`;
      });

    return { stdout: `${header}\n${lines.join('\n')}\n`, stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 23. top — Display Linux Processes Snapshot
  // -----------------------------------------------------------------------
  top(args, stdin, context) {
    const header = `top - 14:32:01 up 3 days,  5:12,  1 user,  load average: 0.08, 0.03, 0.01
Tasks: 4 total,   1 running,   3 sleeping,   0 stopped,   0 zombie
%Cpu(s):  1.2 us,  0.6 sy,  0.0 ni, 98.1 id,  0.1 wa,  0.0 hi,  0.0 si
MiB Mem :   3920.4 total,   2150.2 free,    980.1 used,    790.1 buff/cache
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   2650.3 avail Mem

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
  101 student   20   0   13560   3840   3120 S   0.0   0.1   0:00.12 bash
    1 root      20   0   21424   5420   4100 S   0.0   0.1   0:01.05 systemd
  115 student   20   0   15280   2100   1800 R   0.0   0.0   0:00.01 top
`;
    return { stdout: header, stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 24. kill — Send Signal to a Process
  // -----------------------------------------------------------------------
  kill(args, stdin, context) {
    const pids = [];
    let signal = 'TERM';

    for (const a of args) {
      if (a.startsWith('-')) {
        signal = a.replace(/^-/, '');
      } else {
        pids.push(parseInt(a, 10));
      }
    }

    if (pids.length === 0) {
      return { stdout: '', stderr: 'kill: usage: kill [-s sigspec | -n signum | -sigspec] pid | jobspec ...\n', exitCode: 1 };
    }

    let stderr = '';
    let exitCode = 0;
    const procs = context.processes;

    for (const pid of pids) {
      if (isNaN(pid)) {
        stderr += `kill: illegal pid\n`;
        exitCode = 1;
        continue;
      }
      if (pid === 1) {
        stderr += `kill: (1) - Operation not permitted\n`;
        exitCode = 1;
        continue;
      }

      if (procs) {
        const idx = procs.findIndex(p => p.pid === pid);
        if (idx === -1) {
          stderr += `kill: (${pid}) - No such process\n`;
          exitCode = 1;
        } else {
          procs.splice(idx, 1);
        }
      }
    }

    return { stdout: '', stderr, exitCode };
  },

  // -----------------------------------------------------------------------
  // 25. clear — Clear Screen
  // -----------------------------------------------------------------------
  clear(args, stdin, context) {
    return { stdout: '\x1b[2J\x1b[H', stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 26. history — Display Command History
  // -----------------------------------------------------------------------
  history(args, stdin, context) {
    const historyList = context.history || [];
    const lines = historyList.map((cmd, i) => `${String(i + 1).padStart(5, ' ')}  ${cmd}`);
    return { stdout: lines.join('\n') + (lines.length > 0 ? '\n' : ''), stderr: '', exitCode: 0 };
  },

  // -----------------------------------------------------------------------
  // 27. test / [ — Condition Testing
  // -----------------------------------------------------------------------
  test(args, stdin, context) {
    const vfs = context.vfs;
    let cleanArgs = args.filter(a => a !== ']');
    if (cleanArgs.length === 0) return { stdout: '', stderr: '', exitCode: 1 };

    let invert = false;
    if (cleanArgs[0] === '!') {
      invert = true;
      cleanArgs = cleanArgs.slice(1);
    }

    let result = false;
    const op = cleanArgs[0];
    const val = cleanArgs[1];

    if (op === '-d') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node && node.type === 'dir');
    } else if (op === '-f') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node && node.type === 'file');
    } else if (op === '-e') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node);
    } else if (op === '-s') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node && node.size > 0);
    } else if (op === '-x') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node && (vfs.checkAccess ? vfs.checkAccess(node, 1, context.currentUser) : (node.mode & 0o111) !== 0));
    } else if (op === '-r') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node && (vfs.checkAccess ? vfs.checkAccess(node, 4, context.currentUser) : (node.mode & 0o444) !== 0));
    } else if (op === '-w') {
      const node = vfs ? vfs.resolve(val, { cwd: context.cwd }) : null;
      result = Boolean(node && (vfs.checkAccess ? vfs.checkAccess(node, 2, context.currentUser) : (node.mode & 0o222) !== 0));
    } else if (op === '-z') {
      result = !val || val.length === 0;
    } else if (op === '-n') {
      result = Boolean(val && val.length > 0);
    } else if (cleanArgs.length === 3) {
      const left = cleanArgs[0];
      const comp = cleanArgs[1];
      const right = cleanArgs[2];

      if (comp === '=' || comp === '==') result = left === right;
      else if (comp === '!=') result = left !== right;
      else if (comp === '-eq') result = parseInt(left, 10) === parseInt(right, 10);
      else if (comp === '-ne') result = parseInt(left, 10) !== parseInt(right, 10);
      else if (comp === '-lt') result = parseInt(left, 10) < parseInt(right, 10);
      else if (comp === '-le') result = parseInt(left, 10) <= parseInt(right, 10);
      else if (comp === '-gt') result = parseInt(left, 10) > parseInt(right, 10);
      else if (comp === '-ge') result = parseInt(left, 10) >= parseInt(right, 10);
    }

    if (invert) result = !result;
    return { stdout: '', stderr: '', exitCode: result ? 0 : 1 };
  },

  '['(args, stdin, context) {
    return POSIX_COMMANDS.test(args, stdin, context);
  },

  // =======================================================================
  // Text Processing Utilities
  // =======================================================================

  // -----------------------------------------------------------------------
  // 28. grep — Print Lines Matching a Pattern
  // -----------------------------------------------------------------------
  grep(args, stdin, context) {
    const vfs = context.vfs;
    let ignoreCase = false;
    let invertMatch = false;
    let lineNumbers = false;
    let countOnly = false;
    let filesWithMatches = false;
    let extendedRegex = false;
    let wordMatch = false;
    let pattern = null;
    const files = [];

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '--') {
        if (!pattern && args[i + 1]) pattern = args[++i];
        files.push(...args.slice(i + 1));
        break;
      }
      if (a.startsWith('-') && a.length > 1 && !pattern) {
        if (a.includes('i')) ignoreCase = true;
        if (a.includes('v')) invertMatch = true;
        if (a.includes('n')) lineNumbers = true;
        if (a.includes('c')) countOnly = true;
        if (a.includes('l')) filesWithMatches = true;
        if (a.includes('E')) extendedRegex = true;
        if (a.includes('w')) wordMatch = true;
      } else if (!pattern) {
        pattern = a;
      } else {
        files.push(a);
      }
    }

    if (!pattern) {
      return { stdout: '', stderr: 'grep: missing pattern\n', exitCode: 2 };
    }

    let regex;
    try {
      let pat = pattern;
      if (wordMatch) pat = `\\b${pat}\\b`;
      regex = new RegExp(pat, ignoreCase ? 'i' : '');
    } catch (e) {
      return { stdout: '', stderr: `grep: invalid regular expression: ${pattern}\n`, exitCode: 2 };
    }

    const processText = (text, fileLabel = '') => {
      const lines = text.split('\n');
      if (text.endsWith('\n')) lines.pop();

      const matchedLines = [];
      let matchCount = 0;

      lines.forEach((line, idx) => {
        const matches = regex.test(line);
        if ((matches && !invertMatch) || (!matches && invertMatch)) {
          matchCount++;
          let outLine = line;
          if (lineNumbers) outLine = `${idx + 1}:${outLine}`;
          if (fileLabel && files.length > 1) outLine = `${fileLabel}:${outLine}`;
          matchedLines.push(outLine);
        }
      });

      return { matchCount, matchedLines };
    };

    if (files.length === 0 || (files.length === 1 && files[0] === '-')) {
      const { matchCount, matchedLines } = processText(stdin || '');
      if (countOnly) {
        return { stdout: `${matchCount}\n`, stderr: '', exitCode: matchCount > 0 ? 0 : 1 };
      }
      if (filesWithMatches) {
        return { stdout: matchCount > 0 ? '(standard input)\n' : '', stderr: '', exitCode: matchCount > 0 ? 0 : 1 };
      }
      return {
        stdout: matchedLines.join('\n') + (matchedLines.length > 0 ? '\n' : ''),
        stderr: '',
        exitCode: matchCount > 0 ? 0 : 1
      };
    }

    let totalMatches = 0;
    const outputLines = [];
    let stderr = '';
    let exitCode = 1;

    for (const f of files) {
      try {
        const text = vfs.readFile(f, context.cwd);
        const { matchCount, matchedLines } = processText(text, f);
        totalMatches += matchCount;

        if (filesWithMatches && matchCount > 0) {
          outputLines.push(f);
        } else if (countOnly) {
          outputLines.push(files.length > 1 ? `${f}:${matchCount}` : String(matchCount));
        } else {
          outputLines.push(...matchedLines);
        }
      } catch (err) {
        stderr += `grep: ${f}: No such file or directory\n`;
        exitCode = 2;
      }
    }

    if (totalMatches > 0 && exitCode !== 2) {
      exitCode = 0;
    }

    return {
      stdout: outputLines.join('\n') + (outputLines.length > 0 ? '\n' : ''),
      stderr,
      exitCode
    };
  },

  // -----------------------------------------------------------------------
  // 29. find — Search for Files in a Directory Hierarchy
  // -----------------------------------------------------------------------
  find(args, stdin, context) {
    const vfs = context.vfs;
    const paths = [];
    let namePattern = null;
    let inamePattern = null;
    let typeFilter = null; // 'f', 'd', 'l'
    let maxdepth = Infinity;
    let emptyFilter = false;

    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-name' && args[i + 1] !== undefined) {
        namePattern = args[++i];
      } else if (a === '-iname' && args[i + 1] !== undefined) {
        inamePattern = args[++i];
      } else if (a === '-type' && args[i + 1] !== undefined) {
        typeFilter = args[++i];
      } else if (a === '-maxdepth' && args[i + 1] !== undefined) {
        maxdepth = parseInt(args[++i], 10);
      } else if (a === '-empty') {
        emptyFilter = true;
      } else if (!a.startsWith('-')) {
        paths.push(a);
      }
    }

    const startPaths = paths.length > 0 ? paths : ['.'];
    const results = [];
    let stderr = '';
    let exitCode = 0;

    const nameRegex = namePattern ? globToRegex(namePattern, false) : null;
    const inameRegex = inamePattern ? globToRegex(inamePattern, true) : null;

    const walk = (displayPath, node, currentDepth) => {
      let keep = true;

      if (typeFilter) {
        if (typeFilter === 'f' && node.type !== 'file') keep = false;
        if (typeFilter === 'd' && node.type !== 'dir') keep = false;
        if (typeFilter === 'l' && node.type !== 'symlink') keep = false;
      }

      if (nameRegex && !nameRegex.test(node.name)) keep = false;
      if (inameRegex && !inameRegex.test(node.name)) keep = false;

      if (emptyFilter) {
        if (node.type === 'file' && node.content.length > 0) keep = false;
        if (node.type === 'dir' && Object.keys(node.children || {}).length > 0) keep = false;
      }

      if (keep) {
        results.push(displayPath);
      }

      if (node.type === 'dir' && node.children && currentDepth < maxdepth) {
        const sortedEntries = Object.keys(node.children).sort();
        for (const childName of sortedEntries) {
          const childNode = node.children[childName];
          const childDisplay = displayPath === '.' ? `./${childName}` : (displayPath.endsWith('/') ? `${displayPath}${childName}` : `${displayPath}/${childName}`);
          walk(childDisplay, childNode, currentDepth + 1);
        }
      }
    };

    for (const p of startPaths) {
      const node = vfs.resolve(p, { cwd: context.cwd });
      if (!node) {
        stderr += `find: '${p}': No such file or directory\n`;
        exitCode = 1;
        continue;
      }
      walk(p, node, 0);
    }

    return {
      stdout: results.join('\n') + (results.length > 0 ? '\n' : ''),
      stderr,
      exitCode
    };
  },

  // -----------------------------------------------------------------------
  // 30. sort — Sort Lines of Text
  // -----------------------------------------------------------------------
  sort(args, stdin, context) {
    const vfs = context.vfs;
    let reverse = false;
    let numeric = false;
    let unique = false;
    const files = [];

    for (const a of args) {
      if (a.startsWith('-') && a.length > 1) {
        if (a.includes('r')) reverse = true;
        if (a.includes('n')) numeric = true;
        if (a.includes('u')) unique = true;
      } else {
        files.push(a);
      }
    }

    let text = '';
    let stderr = '';
    let exitCode = 0;

    if (files.length === 0 || (files.length === 1 && files[0] === '-')) {
      text = stdin || '';
    } else {
      for (const f of files) {
        try {
          text += vfs.readFile(f, context.cwd);
        } catch (err) {
          exitCode = 1;
          stderr += `sort: ${f}: No such file or directory\n`;
        }
      }
    }

    if (exitCode !== 0 && !text) {
      return { stdout: '', stderr, exitCode };
    }

    let lines = text.split('\n');
    if (text.endsWith('\n')) lines.pop();

    lines.sort((a, b) => {
      if (numeric) {
        const numA = parseFloat(a) || 0;
        const numB = parseFloat(b) || 0;
        if (numA !== numB) return numA - numB;
      }
      return a.localeCompare(b);
    });

    if (reverse) lines.reverse();

    if (unique) {
      const uLines = [];
      let last = null;
      for (const l of lines) {
        if (l !== last) {
          uLines.push(l);
          last = l;
        }
      }
      lines = uLines;
    }

    return {
      stdout: lines.join('\n') + (lines.length > 0 ? '\n' : ''),
      stderr,
      exitCode
    };
  },

  // -----------------------------------------------------------------------
  // 31. uniq — Report or Omit Repeated Lines
  // -----------------------------------------------------------------------
  uniq(args, stdin, context) {
    const vfs = context.vfs;
    let countOnly = false;
    let duplicatesOnly = false;
    let uniqueOnly = false;
    let ignoreCase = false;
    const files = [];

    for (const a of args) {
      if (a.startsWith('-') && a.length > 1) {
        if (a.includes('c')) countOnly = true;
        if (a.includes('d')) duplicatesOnly = true;
        if (a.includes('u')) uniqueOnly = true;
        if (a.includes('i')) ignoreCase = true;
      } else {
        files.push(a);
      }
    }

    let text = '';
    let stderr = '';
    let exitCode = 0;

    if (files.length === 0 || (files.length === 1 && files[0] === '-')) {
      text = stdin || '';
    } else {
      try {
        text = vfs.readFile(files[0], context.cwd);
      } catch (err) {
        return { stdout: '', stderr: `uniq: ${files[0]}: No such file or directory\n`, exitCode: 1 };
      }
    }

    let lines = text.split('\n');
    if (text.endsWith('\n')) lines.pop();

    const result = [];
    let prev = null;
    let runCount = 0;

    const areEqual = (a, b) => {
      if (a === null || b === null) return false;
      return ignoreCase ? a.toLowerCase() === b.toLowerCase() : a === b;
    };

    const flush = () => {
      if (prev === null) return;
      if (duplicatesOnly && runCount <= 1) return;
      if (uniqueOnly && runCount > 1) return;

      if (countOnly) {
        result.push(`${String(runCount).padStart(7, ' ')} ${prev}`);
      } else {
        result.push(prev);
      }
    };

    for (const line of lines) {
      if (areEqual(line, prev)) {
        runCount++;
      } else {
        flush();
        prev = line;
        runCount = 1;
      }
    }
    flush();

    return {
      stdout: result.join('\n') + (result.length > 0 ? '\n' : ''),
      stderr,
      exitCode: 0
    };
  }
};
