/**
 * Test Suite Automatisée pour VFS et Commandes POSIX
 * Exécution Node.js: node frontend/js/linux/test-posix-vfs.mjs
 */

import { VirtualFS, VFSNode } from './vfs.js';
import { POSIX_COMMANDS } from './posix-commands.js';

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function assert(condition, message) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✓ ${message}`);
  } else {
    failedTests++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

function assertEqual(actual, expected, message) {
  totalTests++;
  const actStr = JSON.stringify(actual);
  const expStr = JSON.stringify(expected);
  if (actStr === expStr) {
    passedTests++;
    console.log(`  ✓ ${message}`);
  } else {
    failedTests++;
    console.error(`  ✗ FAIL: ${message}`);
    console.error(`     Expected: ${expStr}`);
    console.error(`     Actual:   ${actStr}`);
  }
}

function suite(name, fn) {
  console.log(`\n========================================\n[SUITE] ${name}\n========================================`);
  fn();
}

// -------------------------------------------------------------------------
// SUITE 1: VFSNode - Propriétés et Méthodes
// -------------------------------------------------------------------------
suite('VFSNode - Data Model & Permissions Format', () => {
  const fileNode = new VFSNode({
    name: 'script.sh',
    type: 'file',
    mode: 0o755,
    content: '#!/bin/bash\necho "Hello"',
    owner: 'student',
    group: 'student'
  });

  assert(fileNode.isFile(), 'VFSNode isFile() should return true for file');
  assert(!fileNode.isDirectory(), 'VFSNode isDirectory() should return false for file');
  assertEqual(fileNode.getPermissionsString(), '-rwxr-xr-x', 'Permissions string for 0755 file');
  assertEqual(fileNode.getOctalPermissions(), '755', 'Octal string for 0755');
  assert(fileNode.size > 0, 'File size should reflect content byte length');

  const dirNode = new VFSNode({
    name: 'docs',
    type: 'dir',
    mode: 0o700,
    owner: 'root',
    group: 'root'
  });
  assert(dirNode.isDirectory(), 'VFSNode isDirectory() should return true for dir');
  assertEqual(dirNode.getPermissionsString(), 'drwx------', 'Permissions string for 0700 dir');
  assertEqual(dirNode.getOctalPermissions(), '700', 'Octal string for 0700 dir');
  assertEqual(dirNode.size, 4096, 'Directory size is standard 4096');

  // Sticky bit
  const tmpNode = new VFSNode({
    name: 'tmp',
    type: 'dir',
    mode: 0o1777,
    owner: 'root',
    group: 'root'
  });
  assertEqual(tmpNode.getPermissionsString(), 'drwxrwxrwt', 'Permissions string for sticky 1777 dir');

  // Clone
  const cloneNode = fileNode.clone();
  assertEqual(cloneNode.name, fileNode.name, 'Clone preserves name');
  assertEqual(cloneNode.content, fileNode.content, 'Clone preserves content');
  assertEqual(cloneNode.mode, fileNode.mode, 'Clone preserves mode');
  cloneNode.content = 'Modified';
  assert(fileNode.content !== cloneNode.content, 'Modifying clone does not affect original');
});

// -------------------------------------------------------------------------
// SUITE 2: VirtualFS - Initialisation FHS & Normalisation de Chemins
// -------------------------------------------------------------------------
suite('VirtualFS - FHS Initialization & Path Normalization', () => {
  const vfs = new VirtualFS();

  // FHS verification
  assert(vfs.resolve('/bin') !== null, '/bin exists in FHS');
  assert(vfs.resolve('/etc') !== null, '/etc exists in FHS');
  assert(vfs.resolve('/home/student') !== null, '/home/student exists in FHS');
  assert(vfs.resolve('/tmp') !== null, '/tmp exists in FHS');
  assert(vfs.resolve('/proc/version') !== null, '/proc/version exists in FHS');
  assert(vfs.resolve('/var/log/syslog') !== null, '/var/log/syslog exists in FHS');

  const passwdNode = vfs.resolve('/etc/passwd');
  assert(passwdNode.isFile(), '/etc/passwd is a file');
  assert(passwdNode.content.includes('student:x:1000:1000'), '/etc/passwd has student account');

  const shadowNode = vfs.resolve('/etc/shadow');
  assertEqual(shadowNode.getOctalPermissions(), '600', '/etc/shadow has 0600 mode');

  // Normalization
  assertEqual(vfs.normalizePath('.'), '/home/student', "normalizePath('.') returns cwd");
  assertEqual(vfs.normalizePath('..'), '/home', "normalizePath('..') returns /home");
  assertEqual(vfs.normalizePath('~'), '/home/student', "normalizePath('~') returns home");
  assertEqual(vfs.normalizePath('~/notes.txt'), '/home/student/notes.txt', "normalizePath('~/notes.txt') expands home");
  assertEqual(vfs.normalizePath('~root'), '/root', "normalizePath('~root') returns /root");
  assertEqual(vfs.normalizePath('/a//b///c/./d/../e'), '/a/b/c/e', 'normalizePath collapses slashes and resolves . and ..');
  assertEqual(vfs.normalizePath('/../../..'), '/', 'normalizePath stops at root');
});

// -------------------------------------------------------------------------
// SUITE 3: VirtualFS - CRUD & Permissions
// -------------------------------------------------------------------------
suite('VirtualFS - CRUD Operations & Permissions', () => {
  const vfs = new VirtualFS();

  // Write and Read
  vfs.writeFile('/home/student/test.txt', 'Hello VFS');
  const readBack = vfs.readFile('/home/student/test.txt');
  assertEqual(readBack, 'Hello VFS', 'writeFile and readFile work');

  // Append
  vfs.writeFile('/home/student/test.txt', '\nLine 2', '/home/student', { append: true });
  assertEqual(vfs.readFile('/home/student/test.txt'), 'Hello VFS\nLine 2', 'writeFile with append: true');

  // Mkdir
  vfs.mkdir('/home/student/workspace');
  assert(vfs.resolve('/home/student/workspace').isDirectory(), 'mkdir creates directory');

  // Mkdir -p
  vfs.mkdir('/home/student/a/b/c', { recursive: true });
  assert(vfs.resolve('/home/student/a/b/c').isDirectory(), 'mkdir -p creates nested directories');

  // Copy
  vfs.copy('/home/student/test.txt', '/home/student/workspace/copy.txt');
  assertEqual(vfs.readFile('/home/student/workspace/copy.txt'), 'Hello VFS\nLine 2', 'copy replicates file content');

  // Move
  vfs.move('/home/student/workspace/copy.txt', '/home/student/workspace/renamed.txt');
  assert(vfs.resolve('/home/student/workspace/copy.txt') === null, 'move removes source');
  assert(vfs.resolve('/home/student/workspace/renamed.txt') !== null, 'move creates target');

  // Remove
  vfs.remove('/home/student/workspace/renamed.txt');
  assert(vfs.resolve('/home/student/workspace/renamed.txt') === null, 'remove deletes file');

  // Remove dir with recursive
  vfs.remove('/home/student/a', { recursive: true });
  assert(vfs.resolve('/home/student/a') === null, 'remove -r deletes nested directory');

  // Chmod octal
  vfs.chmod('/home/student/test.txt', '700');
  assertEqual(vfs.resolve('/home/student/test.txt').getOctalPermissions(), '700', 'chmod 700 applies correctly');

  // Chmod symbolic
  vfs.chmod('/home/student/test.txt', '+x');
  assertEqual(vfs.resolve('/home/student/test.txt').getOctalPermissions(), '711', 'chmod +x adds execute bits');

  // Snapshot & Restore
  const snap = vfs.snapshot();
  vfs.writeFile('/home/student/should_disappear.txt', 'temp');
  assert(vfs.resolve('/home/student/should_disappear.txt') !== null, 'File created before restore');
  vfs.restore(snap);
  assert(vfs.resolve('/home/student/should_disappear.txt') === null, 'restore rolls back state accurately');

  // Load initial challenge FS
  vfs.loadInitialFS({
    dirs: [{ path: '/home/student/ch1', mode: '755' }],
    files: [{ path: '/home/student/ch1/hello.c', content: 'int main(){}', mode: '644' }]
  });
  assert(vfs.resolve('/home/student/ch1').isDirectory(), 'loadInitialFS creates dirs');
  assertEqual(vfs.readFile('/home/student/ch1/hello.c'), 'int main(){}', 'loadInitialFS creates files');
});

// -------------------------------------------------------------------------
// SUITE 4: POSIX Commands - Navigation & Listing
// -------------------------------------------------------------------------
suite('POSIX Commands - pwd, cd, ls', () => {
  const vfs = new VirtualFS();
  const context = {
    vfs,
    cwd: '/home/student',
    env: { USER: 'student', HOME: '/home/student', PWD: '/home/student', OLDPWD: '/home/student' },
    currentUser: { name: 'student', uid: 1000, gid: 1000 },
    setCwd(c) { this.cwd = c; }
  };

  // pwd
  let res = POSIX_COMMANDS.pwd([], '', context);
  assertEqual(res.stdout, '/home/student\n', 'pwd returns normalized cwd');
  assertEqual(res.exitCode, 0, 'pwd returns exit code 0');

  // cd to /etc
  res = POSIX_COMMANDS.cd(['/etc'], '', context);
  assertEqual(res.exitCode, 0, 'cd /etc succeeds');
  assertEqual(context.cwd, '/etc', 'context.cwd is updated to /etc');
  assertEqual(context.env.OLDPWD, '/home/student', 'OLDPWD tracks previous dir');

  // cd -
  res = POSIX_COMMANDS.cd(['-'], '', context);
  assertEqual(res.exitCode, 0, 'cd - succeeds');
  assertEqual(context.cwd, '/home/student', 'cd - returns to /home/student');
  assertEqual(res.stdout, '/home/student\n', 'cd - prints target directory');

  // cd nonexistent
  res = POSIX_COMMANDS.cd(['nonexistent_folder'], '', context);
  assertEqual(res.exitCode, 1, 'cd nonexistent returns code 1');
  assert(res.stderr.includes('No such file or directory'), 'cd nonexistent error message');

  // ls
  vfs.writeFile('/home/student/fileA.txt', 'A');
  vfs.writeFile('/home/student/fileB.txt', 'B');
  vfs.writeFile('/home/student/.hidden', 'secret');

  res = POSIX_COMMANDS.ls([], '', context);
  assertEqual(res.exitCode, 0, 'ls returns code 0');
  assert(res.stdout.includes('fileA.txt') && res.stdout.includes('fileB.txt'), 'ls lists visible files');
  assert(!res.stdout.includes('.hidden'), 'ls without -a omits hidden file');

  // ls -a
  res = POSIX_COMMANDS.ls(['-a'], '', context);
  assert(res.stdout.includes('.hidden'), 'ls -a includes hidden file');
  assert(res.stdout.includes('.'), 'ls -a includes .');
  assert(res.stdout.includes('..'), 'ls -a includes ..');

  // ls -l
  res = POSIX_COMMANDS.ls(['-l'], '', context);
  assert(res.stdout.includes('-rw-r--r--'), 'ls -l displays permissions');
  assert(res.stdout.includes('student'), 'ls -l displays owner/group');

  // ls -1
  res = POSIX_COMMANDS.ls(['-1'], '', context);
  assert(res.stdout.includes('fileA.txt\nfileB.txt'), 'ls -1 displays one per line');

  // ls nonexistent
  res = POSIX_COMMANDS.ls(['nonexistent_dir'], '', context);
  assertEqual(res.exitCode, 2, 'ls nonexistent returns code 2');
  assert(res.stderr.includes('No such file or directory'), 'ls error message on stderr');
});

// -------------------------------------------------------------------------
// SUITE 5: POSIX Commands - Fichiers (cat, touch, mkdir, rm, cp, mv)
// -------------------------------------------------------------------------
suite('POSIX Commands - cat, touch, mkdir, rm, cp, mv, echo, head, tail, wc', () => {
  const vfs = new VirtualFS();
  const context = {
    vfs,
    cwd: '/home/student',
    env: { USER: 'student', HOME: '/home/student', PWD: '/home/student' },
    currentUser: { name: 'student', uid: 1000, gid: 1000 }
  };

  // echo
  let res = POSIX_COMMANDS.echo(['Bonjour', 'Linux'], '', context);
  assertEqual(res.stdout, 'Bonjour Linux\n', 'echo standard');
  assertEqual(res.exitCode, 0, 'echo exitCode 0');

  res = POSIX_COMMANDS.echo(['-n', 'No newline'], '', context);
  assertEqual(res.stdout, 'No newline', 'echo -n omits newline');

  res = POSIX_COMMANDS.echo(['-e', 'Line1\\nLine2'], '', context);
  assertEqual(res.stdout, 'Line1\nLine2\n', 'echo -e interprets escapes');

  // touch
  res = POSIX_COMMANDS.touch(['notes.txt'], '', context);
  assertEqual(res.exitCode, 0, 'touch creates file');
  assert(vfs.resolve('/home/student/notes.txt') !== null, 'touch file exists in VFS');

  // cat
  vfs.writeFile('/home/student/notes.txt', 'line 1\n\nline 3\n');
  res = POSIX_COMMANDS.cat(['notes.txt'], '', context);
  assertEqual(res.stdout, 'line 1\n\nline 3\n', 'cat reads file');

  res = POSIX_COMMANDS.cat(['-n', 'notes.txt'], '', context);
  assert(res.stdout.includes('     1\tline 1'), 'cat -n numbers lines');

  res = POSIX_COMMANDS.cat(['-s', 'notes.txt'], '', context);
  assertEqual(res.stdout, 'line 1\n\nline 3\n', 'cat -s squeezes blank lines');

  res = POSIX_COMMANDS.cat([], 'Piped Stdin', context);
  assertEqual(res.stdout, 'Piped Stdin', 'cat with stdin');

  // head
  const longText = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join('\n') + '\n';
  vfs.writeFile('/home/student/long.txt', longText);

  res = POSIX_COMMANDS.head(['-n', '3', 'long.txt'], '', context);
  assertEqual(res.stdout, 'Line 1\nLine 2\nLine 3\n', 'head -n 3 extracts first 3 lines');

  // tail
  res = POSIX_COMMANDS.tail(['-n', '2', 'long.txt'], '', context);
  assertEqual(res.stdout, 'Line 19\nLine 20\n', 'tail -n 2 extracts last 2 lines');

  // wc
  res = POSIX_COMMANDS.wc(['-l', 'long.txt'], '', context);
  assert(res.stdout.includes('20 long.txt'), 'wc -l counts lines accurately');

  res = POSIX_COMMANDS.wc([], 'one two three\nfour five\n', context);
  assert(res.stdout.includes('2') && res.stdout.includes('5'), 'wc counts lines and words from stdin');

  // mkdir
  res = POSIX_COMMANDS.mkdir(['sub1'], '', context);
  assertEqual(res.exitCode, 0, 'mkdir sub1');
  assert(vfs.resolve('/home/student/sub1').isDirectory(), 'sub1 is a dir');

  res = POSIX_COMMANDS.mkdir(['-p', 'p1/p2/p3'], '', context);
  assertEqual(res.exitCode, 0, 'mkdir -p p1/p2/p3');
  assert(vfs.resolve('/home/student/p1/p2/p3').isDirectory(), 'nested dirs created');

  // cp
  res = POSIX_COMMANDS.cp(['notes.txt', 'notes_backup.txt'], '', context);
  assertEqual(res.exitCode, 0, 'cp file succeeds');
  assertEqual(vfs.readFile('/home/student/notes_backup.txt'), vfs.readFile('/home/student/notes.txt'), 'cp preserved content');

  // mv
  res = POSIX_COMMANDS.mv(['notes_backup.txt', 'notes_renamed.txt'], '', context);
  assertEqual(res.exitCode, 0, 'mv succeeds');
  assert(vfs.resolve('/home/student/notes_backup.txt') === null, 'mv deleted source');
  assert(vfs.resolve('/home/student/notes_renamed.txt') !== null, 'mv created destination');

  // rm
  res = POSIX_COMMANDS.rm(['notes_renamed.txt'], '', context);
  assertEqual(res.exitCode, 0, 'rm file succeeds');
  assert(vfs.resolve('/home/student/notes_renamed.txt') === null, 'file deleted');

  res = POSIX_COMMANDS.rm(['sub1'], '', context);
  assertEqual(res.exitCode, 1, 'rm on dir without -r fails with code 1');
  assert(res.stderr.includes('Is a directory'), 'rm error message specifies Is a directory');

  res = POSIX_COMMANDS.rm(['-r', 'sub1'], '', context);
  assertEqual(res.exitCode, 0, 'rm -r on dir succeeds');
  assert(vfs.resolve('/home/student/sub1') === null, 'sub1 removed');

  // Safety on rm /
  res = POSIX_COMMANDS.rm(['-r', '/'], '', context);
  assertEqual(res.exitCode, 1, 'rm -r / is blocked');
  assert(res.stderr.includes('dangerous'), 'rm / dangerous warning');
});

// -------------------------------------------------------------------------
// SUITE 6: POSIX Commands - Droits & Système (chmod, whoami, uname, date, env, export, ps, kill)
// -------------------------------------------------------------------------
suite('POSIX Commands - Permissions & System Utilities', () => {
  const vfs = new VirtualFS();
  const procs = [
    { pid: 1, cmd: '/sbin/init', user: 'root', cpu: '0.0', mem: '0.1' },
    { pid: 101, cmd: 'bash', user: 'student', cpu: '0.0', mem: '0.1' },
    { pid: 200, cmd: 'sleep 100', user: 'student', cpu: '0.0', mem: '0.1' }
  ];
  const context = {
    vfs,
    cwd: '/home/student',
    env: { USER: 'student', HOME: '/home/student', PWD: '/home/student' },
    currentUser: { name: 'student', uid: 1000, gid: 1000 },
    processes: procs
  };

  vfs.writeFile('/home/student/run.sh', '#!/bin/bash');

  // chmod
  let res = POSIX_COMMANDS.chmod(['750', 'run.sh'], '', context);
  assertEqual(res.exitCode, 0, 'chmod 750 succeeds');
  assertEqual(vfs.resolve('/home/student/run.sh').getOctalPermissions(), '750', 'chmod 750 applied');

  res = POSIX_COMMANDS.chmod(['+x', 'run.sh'], '', context);
  assertEqual(res.exitCode, 0, 'chmod +x succeeds');
  assertEqual(vfs.resolve('/home/student/run.sh').getOctalPermissions(), '751', 'chmod +x added execution');

  res = POSIX_COMMANDS.chmod(['invalid_mode', 'run.sh'], '', context);
  assertEqual(res.exitCode, 1, 'chmod invalid mode returns code 1');

  // whoami
  res = POSIX_COMMANDS.whoami([], '', context);
  assertEqual(res.stdout, 'student\n', 'whoami returns student');

  // uname
  res = POSIX_COMMANDS.uname([], '', context);
  assertEqual(res.stdout, 'Linux\n', 'uname default is Linux');

  res = POSIX_COMMANDS.uname(['-a'], '', context);
  assert(res.stdout.includes('Linux examquiz 5.15'), 'uname -a provides complete system string');

  // date
  res = POSIX_COMMANDS.date(['+%Y'], '', context);
  assert(res.stdout.trim().length === 4, 'date +%Y returns 4-digit year');

  // uptime
  res = POSIX_COMMANDS.uptime(['-p'], '', context);
  assert(res.stdout.startsWith('up '), 'uptime -p returns pretty string');

  // env
  res = POSIX_COMMANDS.env([], '', context);
  assert(res.stdout.includes('USER=student'), 'env lists USER');

  // export
  res = POSIX_COMMANDS.export(['MY_VAR=secret_value'], '', context);
  assertEqual(res.exitCode, 0, 'export MY_VAR succeeds');
  assertEqual(context.env.MY_VAR, 'secret_value', 'export modified context.env');

  res = POSIX_COMMANDS.export(['123_bad=error'], '', context);
  assertEqual(res.exitCode, 1, 'export invalid identifier fails with code 1');

  // ps
  res = POSIX_COMMANDS.ps([], '', context);
  assertEqual(res.exitCode, 0, 'ps succeeds');
  assert(res.stdout.includes('bash'), 'ps lists student processes');

  res = POSIX_COMMANDS.ps(['aux'], '', context);
  assert(res.stdout.includes('/sbin/init'), 'ps aux includes root processes');

  // top
  res = POSIX_COMMANDS.top([], '', context);
  assertEqual(res.exitCode, 0, 'top snapshot succeeds');
  assert(res.stdout.includes('Tasks:'), 'top snapshot has tasks header');

  // kill
  res = POSIX_COMMANDS.kill(['1'], '', context);
  assertEqual(res.exitCode, 1, 'kill 1 is forbidden (exit 1)');

  res = POSIX_COMMANDS.kill(['99999'], '', context);
  assertEqual(res.exitCode, 1, 'kill non-existent pid fails');

  res = POSIX_COMMANDS.kill(['200'], '', context);
  assertEqual(res.exitCode, 0, 'kill valid process succeeds');
  assert(!procs.some(p => p.pid === 200), 'process 200 removed from list');

  // test / [
  res = POSIX_COMMANDS.test(['-f', '/home/student/run.sh'], '', context);
  assertEqual(res.exitCode, 0, 'test -f file returns 0');

  res = POSIX_COMMANDS.test(['-d', '/home/student/run.sh'], '', context);
  assertEqual(res.exitCode, 1, 'test -d file returns 1');
});

// -------------------------------------------------------------------------
// SUITE 7: Utilitaires de Filtrage (grep, find, sort, uniq)
// -------------------------------------------------------------------------
suite('Text Utilities - grep, find, sort, uniq', () => {
  const vfs = new VirtualFS();
  const context = {
    vfs,
    cwd: '/home/student',
    env: { USER: 'student' }
  };

  vfs.writeFile('/home/student/log.txt', 'INFO: System starting\nERROR: Failed to connect\nINFO: Connection retry\nERROR: Timeout\n');

  // grep
  let res = POSIX_COMMANDS.grep(['ERROR', 'log.txt'], '', context);
  assertEqual(res.exitCode, 0, 'grep match returns 0');
  assertEqual(res.stdout, 'ERROR: Failed to connect\nERROR: Timeout\n', 'grep extracts matching lines');

  res = POSIX_COMMANDS.grep(['-c', 'ERROR', 'log.txt'], '', context);
  assertEqual(res.stdout, '2\n', 'grep -c returns count 2');

  res = POSIX_COMMANDS.grep(['-v', 'ERROR', 'log.txt'], '', context);
  assertEqual(res.stdout, 'INFO: System starting\nINFO: Connection retry\n', 'grep -v inverts selection');

  res = POSIX_COMMANDS.grep(['-n', 'Failed', 'log.txt'], '', context);
  assertEqual(res.stdout, '2:ERROR: Failed to connect\n', 'grep -n includes line number 2:');

  res = POSIX_COMMANDS.grep(['NONEXISTENT_PATTERN', 'log.txt'], '', context);
  assertEqual(res.exitCode, 1, 'grep without match returns exit code 1');

  // grep with stdin
  res = POSIX_COMMANDS.grep(['-i', 'python'], 'I love Python\nRuby is fine\npython is great\n', context);
  assertEqual(res.exitCode, 0, 'grep -i stdin match');
  assertEqual(res.stdout, 'I love Python\npython is great\n', 'grep -i case insensitive');

  // find
  vfs.mkdir('/home/student/project/src', { recursive: true });
  vfs.writeFile('/home/student/project/src/main.py', 'print("hello")');
  vfs.writeFile('/home/student/project/README.md', '# Readme');

  res = POSIX_COMMANDS.find(['/home/student/project', '-name', '*.py'], '', context);
  assertEqual(res.exitCode, 0, 'find by glob pattern succeeds');
  assertEqual(res.stdout.trim(), '/home/student/project/src/main.py', 'find located main.py');

  res = POSIX_COMMANDS.find(['/home/student/project', '-type', 'd'], '', context);
  assert(res.stdout.includes('/home/student/project/src'), 'find -type d lists directories');

  // sort
  const unsorted = 'cherry\napple\nbanana\napple\n';
  vfs.writeFile('/home/student/fruits.txt', unsorted);

  res = POSIX_COMMANDS.sort(['fruits.txt'], '', context);
  assertEqual(res.stdout, 'apple\napple\nbanana\ncherry\n', 'sort alphabetically');

  res = POSIX_COMMANDS.sort(['-r', 'fruits.txt'], '', context);
  assertEqual(res.stdout, 'cherry\nbanana\napple\napple\n', 'sort -r reverse');

  res = POSIX_COMMANDS.sort(['-u', 'fruits.txt'], '', context);
  assertEqual(res.stdout, 'apple\nbanana\ncherry\n', 'sort -u deduplicates');

  // sort numeric
  res = POSIX_COMMANDS.sort(['-n'], '10\n2\n1\n20\n3\n', context);
  assertEqual(res.stdout, '1\n2\n3\n10\n20\n', 'sort -n sorts numerically');

  // uniq
  const repeats = 'A\nA\nB\nB\nB\nA\n'; // Note adjacent vs non-adjacent
  res = POSIX_COMMANDS.uniq([], repeats, context);
  assertEqual(res.stdout, 'A\nB\nA\n', 'uniq removes adjacent repeats');

  res = POSIX_COMMANDS.uniq(['-c'], repeats, context);
  assert(res.stdout.includes('2 A') && res.stdout.includes('3 B'), 'uniq -c prefixes counts');

  res = POSIX_COMMANDS.uniq(['-d'], repeats, context);
  assertEqual(res.stdout, 'A\nB\n', 'uniq -d only duplicates');

  res = POSIX_COMMANDS.uniq(['-u'], repeats, context);
  assertEqual(res.stdout, 'A\n', 'uniq -u only strictly unique adjacent lines (the trailing A)');

  // uniq -i
  res = POSIX_COMMANDS.uniq(['-i'], 'a\nA\nB\nb\n', context);
  assertEqual(res.stdout, 'a\nB\n', 'uniq -i ignores case for adjacent matches');
});

// -------------------------------------------------------------------------
// SUITE 8: Edge Cases Avancés (Symlinks, Multi-fichiers, Permissions)
// -------------------------------------------------------------------------
suite('Advanced Edge Cases - Symlinks, Multi-File Ops, Permissions', () => {
  const vfs = new VirtualFS();
  const context = {
    vfs,
    cwd: '/home/student',
    env: { USER: 'student' },
    currentUser: { name: 'student', uid: 1000, gid: 1000 }
  };

  // Symlinks in VFS
  const linkNode = new VFSNode({
    name: 'link_to_passwd',
    type: 'symlink',
    target: '/etc/passwd'
  });
  vfs.resolve('/home/student').children['link_to_passwd'] = linkNode;

  const resolvedLink = vfs.resolve('/home/student/link_to_passwd');
  assert(resolvedLink !== null, 'Symlink resolved');
  assertEqual(resolvedLink.name, 'passwd', 'Symlink target resolved to /etc/passwd');

  // Multi-file cp
  vfs.writeFile('/home/student/f1.txt', '1');
  vfs.writeFile('/home/student/f2.txt', '2');
  vfs.mkdir('/home/student/dest_dir');

  let res = POSIX_COMMANDS.cp(['f1.txt', 'f2.txt', 'dest_dir'], '', context);
  assertEqual(res.exitCode, 0, 'cp multi-file to dir succeeds');
  assertEqual(vfs.readFile('/home/student/dest_dir/f1.txt'), '1', 'f1 copied');
  assertEqual(vfs.readFile('/home/student/dest_dir/f2.txt'), '2', 'f2 copied');

  // Multi-file mv
  res = POSIX_COMMANDS.mv(['f1.txt', 'f2.txt', 'dest_dir'], '', context);
  assertEqual(res.exitCode, 0, 'mv multi-file to dir succeeds');
  assert(vfs.resolve('/home/student/f1.txt') === null, 'f1 moved from source');
  assert(vfs.resolve('/home/student/f2.txt') === null, 'f2 moved from source');

  // Multi-file wc with total line
  res = POSIX_COMMANDS.wc(['dest_dir/f1.txt', 'dest_dir/f2.txt'], '', context);
  assert(res.stdout.includes('total'), 'wc multi-file contains total row');

  // Multi-file grep with filename prefix
  res = POSIX_COMMANDS.grep(['1', 'dest_dir/f1.txt', 'dest_dir/f2.txt'], '', context);
  assert(res.stdout.includes('dest_dir/f1.txt:1'), 'grep multi-file prefixes filename');

  // tail -n +N
  vfs.writeFile('/home/student/numbers.txt', '1\n2\n3\n4\n5\n');
  res = POSIX_COMMANDS.tail(['-n', '+3', 'numbers.txt'], '', context);
  assertEqual(res.stdout, '3\n4\n5\n', 'tail -n +3 starts from 3rd line');

  // Complex symbolic chmod: u=rwx,go=rx
  res = POSIX_COMMANDS.chmod(['u=rwx,go=rx', 'numbers.txt'], '', context);
  assertEqual(res.exitCode, 0, 'chmod u=rwx,go=rx succeeds');
  assertEqual(vfs.resolve('/home/student/numbers.txt').getOctalPermissions(), '755', 'chmod u=rwx,go=rx results in 755');

  // chown as student (operation not permitted)
  res = POSIX_COMMANDS.chown(['root', 'numbers.txt'], '', context);
  assertEqual(res.exitCode, 1, 'chown as student fails with code 1');
  assert(res.stderr.includes('Operation not permitted'), 'chown error message');

  // chown as root
  const rootContext = { ...context, currentUser: { name: 'root', uid: 0, gid: 0 } };
  res = POSIX_COMMANDS.chown(['root:root', 'numbers.txt'], '', rootContext);
  assertEqual(res.exitCode, 0, 'chown as root succeeds');
  assertEqual(vfs.resolve('/home/student/numbers.txt').owner, 'root', 'owner is now root');
  assertEqual(vfs.resolve('/home/student/numbers.txt').group, 'root', 'group is now root');

  // find with -maxdepth 1
  res = POSIX_COMMANDS.find(['/home/student', '-maxdepth', '1'], '', context);
  assert(!res.stdout.includes('/home/student/dest_dir/f1.txt'), 'find -maxdepth 1 restricts recursion');
  assert(res.stdout.includes('/home/student/dest_dir'), 'find -maxdepth 1 includes direct child dir');
});


console.log(`\n========================================`);
console.log(`TEST RESULTS: ${passedTests}/${totalTests} PASSED (${failedTests} FAILED)`);
console.log(`========================================`);

if (failedTests > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
