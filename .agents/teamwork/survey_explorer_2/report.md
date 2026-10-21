# Spécification Technique Exhaustive : Moteur Shell Virtuel & Système de Fichiers en Mémoire (VFS)
**Projet :** Examination & Quiz Platform — Centre d'Entraînement Linux (Linux Training Center)  
**Auteur :** survey_explorer_2 (Specification Miner)  
**Date :** 2026-10-20  
**Statut :** Spécification d'Ingénierie & d'Architecture Référence  

---

## 1. Vue d'Ensemble & Architecture Générale

Le **Centre d'Entraînement Linux** requiert une émulation complète d'un environnement Unix/POSIX exécutée à 100% côté client (in-browser) sans nécessiter de backend Docker lourd ou de conteneurs distants pour la pratique quotidienne. Cette approche garantit :
- Une latence nulle pour l'étudiant (réponse instantanée du terminal).
- Un passage à l'échelle illimité (aucune charge CPU serveur pour les commandes d'entraînement).
- Une étanchéité de sécurité totale (sandbox isolée dans le contexte du navigateur).
- Une vérification déterministe et reproductible des états de fichiers et des sorties consoles.

L'architecture se décompose en 5 sous-systèmes modulaires découplés :
```
┌────────────────────────────────────────────────────────────────────────┐
│                   Terminal UI (DOM / CSS / Key Events)                 │
│    Prompt dynamique (student@examquiz:~$ ), Historique, Tab-Autocompl   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Command Line String
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Shell Engine (Lexer, Parser, Orchestrator)               │
│   Tokenisation (quotes, escapes), Pipes (|), Redirections (>, >>, <),  │
│          Enchaînements (&&, ||, ;), Variables ($VAR, $?)               │
└──────────────┬───────────────────────────────────────────┬─────────────┘
               │ Exec argv / streams                       │ Node lookup / FS ops
               ▼                                           ▼
┌──────────────────────────────┐          ┌──────────────────────────────┐
│       POSIX Commands         │          │   Virtual Filesystem (VFS)   │
│  ls, cd, cat, grep, find,    │◄────────►│ Inodes, Permissions (rwx),    │
│  chmod, ps, top, kill, wc... │          │ FHS standard, Normalisation  │
└──────────────────────────────┘          └──────────────┬───────────────┘
                                                         │ Clone / Diff / Inspect
                                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Challenge Evaluation Harness (Tests Publics & Cachés)      │
│      Validation des sorties (stdout), codes retour, état VFS (nodes)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Spécification du Système de Fichiers Virtuel (VFS)

### 2.1 Modèle de Données des Nœuds (`VFSNode`)
Chaque entrée dans le système de fichiers est un nœud en mémoire identifié par un numéro d'inode unique.

```typescript
type NodeType = 'file' | 'dir' | 'symlink';

interface VFSNode {
  inode: number;              // Identifiant unique auto-incrémenté
  name: string;               // Nom du fichier ou dossier (ex: "bashrc", "workspace")
  type: NodeType;             // Type de ressource
  parent: VFSNode | null;     // Référence au dossier parent (null pour '/')
  children?: Map<string, VFSNode>; // Table des enfants par nom (si type === 'dir')
  content?: string;           // Contenu textuel UTF-8 (si type === 'file')
  target?: string;            // Cible du lien symbolique (si type === 'symlink')
  
  // Permissions & Propriété POSIX
  mode: number;               // Masque de permissions octal (ex: 0o755, 0o644)
  uid: number;                // User ID (ex: 1000 pour 'student', 0 pour 'root')
  gid: number;                // Group ID (ex: 1000 pour 'student', 0 pour 'root')
  owner: string;              // Nom du propriétaire (ex: "student", "root")
  group: string;              // Nom du groupe (ex: "student", "root")
  
  // Métadonnées & Horodatage
  size: number;               // Octets du contenu pour un fichier, 4096 pour un répertoire
  atime: number;              // Dernier accès (ms timestamp)
  mtime: number;              // Dernière modification de contenu (ms timestamp)
  ctime: number;              // Dernier changement de métadonnées (ms timestamp)
  nlink: number;              // Nombre de liens (1 pour fichier, 2 + sous-dossiers pour dossier)
}
```

### 2.2 Arborescence Standard Linux FHS (Filesystem Hierarchy Standard)
À l'initialisation, le VFS construit une hiérarchie Linux réaliste :
- `/` : Racine système (mode `0o755`, `root:root`).
- `/bin` & `/usr/bin` : Répertoire des binaires système. Contient les stubs exécutables correspondant aux commandes supportées.
- `/etc` : Fichiers de configuration système :
  - `/etc/passwd` : Comptes utilisateurs (`root:x:0:0:root:/root:/bin/bash`, `student:x:1000:1000:Student User:/home/student:/bin/bash`).
  - `/etc/group` : Groupes système (`root:x:0:`, `student:x:1000:`, `sudo:x:27:student`).
  - `/etc/shadow` : Hachages confidentiels (mode `0o600`, inaccessible à l'étudiant non root).
  - `/etc/hostname` : Nom d'hôte (`examquiz`).
  - `/etc/os-release` : Description de l'OS (`NAME="Ubuntu ExamQuiz Linux" VERSION="24.04 LTS"`).
- `/home` : Répertoires des utilisateurs normaux (mode `0o755`).
  - `/home/student` : Répertoire de travail par défaut (`$HOME`, mode `0o755`, `student:student`).
    - `/home/student/.bashrc` : Configuration du shell interactif.
    - `/home/student/.profile` : Environnement utilisateur.
- `/root` : Dossier personnel du super-administrateur (mode `0o700`, `root:root`). Accès refusé pour l'utilisateur `student`.
- `/var` : Données variables :
  - `/var/log` : Logs système (`/var/log/syslog`, `/var/log/auth.log`).
- `/tmp` : Fichiers temporaires mondiaux (mode `0o1777` avec Sticky Bit).
- `/proc` : Système virtuel de pseudo-fichiers noyau :
  - `/proc/version` : Version du noyau Linux simulée.
  - `/proc/uptime` : Secondes d'activité système.
  - `/proc/cpuinfo` & `/proc/meminfo` : Caractéristiques processeur et mémoire simulées.
- `/dev` : Périphériques simulés :
  - `/dev/null` : Puits sans fond (écritures absorbées, lectures retournent EOF).
  - `/dev/zero` : Fournit des zéros infinis.
  - `/dev/urandom` : Pseudo-générateur aléatoire.

### 2.3 Algorithme de Résolution et Normalisation des Chemins
Tout chemin doit être normalisé de manière univoque :
1. **Expansion du tilde :** Si le chemin débute par `~` ou `~/`, remplacer par `/home/student`.
2. **Gestion relative / absolue :** Si le chemin ne commence pas par `/`, le préfixer par `cwd + '/'`.
3. **Nettoyage lexical :** Remplacer les séparateurs consécutifs multiples `/{2,}` par `/`.
4. **Parcours par pile (Stack-based resolution) :**
   - Découper la chaîne selon `/`.
   - Pour chaque composant :
     - `""` ou `"."` : Ignorer (répertoire courant).
     - `".."` : Dépiler le dernier élément (s'arrêter à la racine `/`).
     - Autre nom : Empiler le composant.
   - Joindre avec `/`. Si la pile est vide, le résultat est `"/"`.
5. **Vérification des droits de traversée (`x`) :**
   - Lors de la navigation le long de chaque répertoire intermédiaire, le VFS vérifie que l'utilisateur courant possède le droit d'exécution (`x`) sur le répertoire parent.
   - En cas d'échec : Renvoie immédiatement `EACCES (Permission denied)`.
6. **Résolution des liens symboliques (`symlink`) :**
   - Si un nœud traversé est de type `symlink`, résoudre récursivement sa cible en surveillant le nombre de sauts (maximum 20 sauts pour prévenir les boucles infinies `ELOOP: Too many levels of symbolic links`).

### 2.4 Modèle de Permissions & Évaluation POSIX
Le mode d'un nœud est stocké sous forme d'entier 16 bits standard POSIX :
- **Bits 0 à 8 :** Permissions d'accès `rwxrwxrwx` (Propriétaire, Groupe, Autres).
- **Bits 9 à 11 :** Bits spéciaux (Sticky bit `0o1000`, SGID `0o2000`, SUID `0o4000`).
- **Bits 12 à 15 :** Type de fichier (`0o040000` pour dossier, `0o100000` pour fichier régulier, `0o120000` pour lien symbolique).

#### Algorithme d'évaluation des droits (`checkAccess(node, requiredMode, user)`) :
1. Si `user.uid === 0` (`root`) :
   - Lecture (`r`) et écriture (`w`) sont **toujours accordées**, quel que soit le mode.
   - Exécution (`x`) sur un fichier ordinaire n'est accordée que si au moins **un** bit `x` (propriétaire, groupe ou autre) est actif sur le fichier. Sur un répertoire, l'exécution est toujours accordée à root.
2. Si `user.uid === node.uid` (l'utilisateur est le propriétaire) :
   - Tester le triplet Propriétaire : `((node.mode >> 6) & 0o7) & requiredMode === requiredMode`.
3. Sinon, si `user.gid === node.gid` (l'utilisateur appartient au groupe) :
   - Tester le triplet Groupe : `((node.mode >> 3) & 0o7) & requiredMode === requiredMode`.
4. Sinon (autre utilisateur) :
   - Tester le triplet Autres : `(node.mode & 0o7) & requiredMode === requiredMode`.
5. Si le test échoue : Erreur `Permission denied`.

#### Droits requis selon les opérations système :
| Opération | Nœud cible | Dossier parent | Droits requis |
|-----------|------------|----------------|---------------|
| `cat file` | `file` | Parent de `file` | Lecture (`r`) sur le fichier + Exécution (`x`) sur tous les dossiers parents |
| `echo "txt" > file` (modif) | `file` | Parent de `file` | Écriture (`w`) sur le fichier + Exécution (`x`) sur les dossiers parents |
| `touch newfile` (création) | - | Parent | Écriture (`w`) et Exécution (`x`) sur le dossier parent |
| `rm file` | `file` | Parent | Écriture (`w`) et Exécution (`x`) sur le dossier parent (le fichier lui-même n'a pas besoin d'être inscriptible !) |
| `cd dir` | `dir` | - | Exécution (`x`) sur `dir` et tous les ancêtres |
| `ls dir` | `dir` | - | Lecture (`r`) sur `dir` (pour lister les noms) + Exécution (`x`) si `-l` (pour lire les attributs des inodes) |

### 2.5 Snapshotting, Clônage & Réinitialisation
Pour garantir l'étanchéité des défis d'entraînement :
- `vfs.snapshot()` : Sérialise l'arborescence complète sous forme d'un objet JSON pur.
- `vfs.restore(snapshot)` : Réhydrate l'arborescence à son état exact de départ en une opération synchrone (< 5ms).
- `vfs.diff(initialSnapshot)` : Compare l'état courant avec l'état initial pour extraire la liste des fichiers créés, modifiés, supprimés ou dont les attributs de permissions ont changé.

---

## 3. Spécification de l'Interface Terminal & Moteur Shell Interactif

### 3.1 Structure DOM & Ergonomie du Terminal
Le composant Terminal virtuel s'intègre dans le volet droit de l'atelier Linux :
- **En-tête de fenêtre :**
  - Boutons de contrôle de style terminal macOS/Linux (points rouge, jaune, vert).
  - Titre dynamique : `student@examquiz:~ (bash)`.
  - Actions rapides : Bouton "🧹 Effacer (Ctrl+L)", Bouton "🔄 Réinitialiser le Terminal".
- **Corps de terminal :**
  - Police monospace système à chasse fixe : `'Fira Code', 'JetBrains Mono', 'Consolas', 'Courier New', monospace`.
  - Fond noir bleuté profond (`#050814` / `#0b1120`), bordure subtile `rgba(255, 255, 255, 0.1)`.
  - Zone de défilement d'historique (`terminal-history-log`) conservant l'intégralité des invites et des sorties passées.
  - Ligne de commande active en bas, restant continuellement visible avec scroll automatique vers le bas.

### 3.2 Invite de Commande Dynamique (CLI Prompt)
L'invite respecte rigoureusement la syntaxe standard Bash Debian/Ubuntu :
```
student@examquiz:~$ 
```
Composants de l'invite :
1. `student` : Nom de l'utilisateur courant (`root` si session élevée). Affiché en vert (`#10b981`).
2. `@` : Séparateur blanc.
3. `examquiz` : Nom d'hôte de la machine d'examen. Affiché en vert (`#10b981`).
4. `:` : Séparateur gris neutre.
5. `path` : Répertoire de travail courant (`cwd`) :
   - Si `cwd === '/home/student'` : Remplacé par `~`.
   - Si `cwd.startsWith('/home/student/')` : Remplacé par `~/${subpath}`.
   - Si `cwd === '/root'` et utilisateur root : Remplacé par `~`.
   - Sinon : Chemin absolu complet (ex: `/var/log`, `/etc`). Affiché en bleu roi clair (`#38bdf8`).
6. `char` : Caractère terminal :
   - `$` pour un utilisateur régulier (`uid !== 0`).
   - `#` pour le super-administrateur `root` (`uid === 0`).
   - Suivi d'une espace insécable.

### 3.3 Boucle Événementielle & Raccourcis Clavier
| Touche / Raccourci | Comportement Spécifié |
|--------------------|------------------------|
| `Entrée` (`Enter`) | Valide la commande courante. Ajoute la ligne non-vide à l'historique. Exécute la chaîne via le Shell Engine. Affiche la sortie (stdout/stderr). Réinitialise le champ et réaffiche une invite fraîche. Déroule l'affichage en bas. |
| `Flèche Haut` (`↑`) | Navigue vers la commande précédente dans l'historique. Si l'on quitte la ligne courante non validée, sauvegarde le brouillon en cours pour pouvoir le restaurer. Positionne le curseur à la fin de la commande rappelée. |
| `Flèche Bas` (`↓`) | Navigue vers la commande suivante dans l'historique. Si l'on dépasse la commande la plus récente, restaure le brouillon de texte initialement saisi. |
| `Tabulation` (`Tab`) | Déclenche l'autocomplétion contextuelle (prévenir le `defaultPrevented` pour ne pas perdre le focus navigateur). |
| `Ctrl + L` | Efface le contenu de l'écran (identique à la commande `clear`), repositionne l'invite courante en haut tout en préservant le texte saisi. |
| `Ctrl + C` | Envoie le signal d'interruption `SIGINT`. Affiche `^C` immédiatement à la suite du texte, saute à la ligne suivante, affecte le code retour `$? = 130`, et régénère une invite vierge. |
| `Ctrl + U` | Supprime tout le texte situé entre le début de la ligne et le curseur courant. |
| `Ctrl + K` | Supprime tout le texte situé entre le curseur courant et la fin de la ligne. |
| `Ctrl + A` / `Origine` (`Home`) | Déplace instantanément le curseur au tout début de la commande. |
| `Ctrl + E` / `Fin` (`End`) | Déplace instantanément le curseur à la fin de la commande. |
| `Ctrl + W` | Supprime le dernier mot avant le curseur (délimité par des espaces). |

### 3.4 Moteur d'Autocomplétion (Tab Completion)
Lorsqu'un étudiant appuie sur `Tab` :
1. **Analyse lexicale de la ligne en cours :** Extraire le dernier mot (token) sous le curseur.
2. **Si premier token (commande) :**
   - Lister tous les exécutables disponibles dans les répertoires du `$PATH` (`/bin`, `/usr/bin`, built-ins).
   - Filtrer les noms commençant par le préfixe saisi.
3. **Si argument (fichier ou dossier) :**
   - Extraire le répertoire parent du chemin saisi (ou `cwd` si pas de slash).
   - Lister les entrées de ce répertoire.
   - Filtrer celles qui correspondent au préfixe.
4. **Résultats de recherche :**
   - **0 correspondance :** Émettre un signal visuel discret (bref flash de la bordure du terminal).
   - **1 correspondance unique :**
     - Compléter immédiatement le texte dans le champ de saisie.
     - Si la cible est un répertoire, ajouter automatiquement un slash final `/`.
     - Si la cible est un fichier régulier, ajouter une espace finale `" "`.
   - **Plusieurs correspondances :**
     - Calculer le plus long préfixe commun et compléter jusqu'à cette limite.
     - Si une seconde tabulation est pressée (ou dès la première si déjà sur le préfixe commun), afficher la grille des choix possibles sous la ligne de commande, puis réafficher l'invite avec la ligne inchangée.

---

## 4. Spécification Détaillée des Commandes POSIX (23 Commandes)

Toutes les commandes s'exécutent avec la signature :
```typescript
type CommandFn = (
  args: string[], 
  stdin: string, 
  context: ShellContext
) => Promise<CommandResult> | CommandResult;

interface CommandResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}
```

---

### 4.1 Navigation et Manipulation de Fichiers

#### 1. `pwd` — Print Working Directory
- **Syntaxe :** `pwd [-L|-P]`
- **Comportement :** Écrit sur stdout le chemin absolu normalisé du répertoire de travail courant, suivi d'un saut de ligne.
- **Entrées :** Aucune.
- **Sortie :** Ex: `/home/student\n`.
- **Code retour :** `0`.

#### 2. `cd` — Change Working Directory
- **Syntaxe :** `cd [répertoire]`
- **Comportement :**
  - Sans argument ou avec `~` : bascule vers `$HOME` (`/home/student`).
  - Avec `-` : bascule vers `$OLDPWD` et affiche le nouveau chemin sur stdout.
  - Avec chemin relatif ou absolu : résout le nœud cible dans le VFS.
- **Erreurs & Codes retour :**
  - Si le chemin n'existe pas : `stderr: "cd: <dir>: No such file or directory\n"`, code `1`.
  - Si la cible n'est pas un répertoire : `stderr: "cd: <dir>: Not a directory\n"`, code `1`.
  - Si les droits de traversée (`x`) manquent : `stderr: "cd: <dir>: Permission denied\n"`, code `1`.
- **Effets de bord :** Met à jour `$OLDPWD = $PWD` et `$PWD = nouveau_chemin`.

#### 3. `ls` — List Directory Contents
- **Syntaxe :** `ls [-l] [-a] [-la|-al] [-lh] [-1] [-d] [chemin...]`
- **Options supportées :**
  - `-a` : Affiche toutes les entrées, y compris celles débutant par `.` (notamment `.` et `..`).
  - `-l` : Format long détaillé (permissions, nlinks, propriétaire, groupe, taille, date, nom).
  - `-h` : Tailles lisibles pour l'humain (K, M, G) en conjonction avec `-l`.
  - `-1` : Force une entrée par ligne.
  - `-d` : Affiche le répertoire lui-même au lieu de son contenu.
- **Format du mode long (`-l`) :**
  ```
  drwxr-xr-x 2 student student 4096 Oct 20 18:30 documents
  -rw-r--r-- 1 student student  142 Oct 20 18:32 notes.txt
  lrwxrwxrwx 1 student student    9 Oct 20 18:35 link -> notes.txt
  ```
- **Sortie :** Noms séparés par des espaces/tabulations (mode court) ou lignes complètes (mode `-l`).
- **Erreur :** `ls: cannot access '<path>': No such file or directory\n`, code `2`.

#### 4. `cat` — Concatenate and Print Files
- **Syntaxe :** `cat [-n] [-b] [-s] [fichier...]`
- **Options :**
  - `-n` : Numérote toutes les lignes de sortie à partir de 1.
  - `-b` : Numérote uniquement les lignes non-vides.
  - `-s` : Compresse les lignes vides consécutives en une seule ligne vide.
- **Comportement :**
  - Si aucun fichier ou `-` : Lit depuis `stdin`.
  - Concatène les fichiers spécifiés dans l'ordre vers `stdout`.
- **Erreurs :**
  - Fichier inexistant : `cat: <file>: No such file or directory\n`, code `1`.
  - Répertoire passé en paramètre : `cat: <file>: Is a directory\n`, code `1`.
  - Droits insuffisants : `cat: <file>: Permission denied\n`, code `1`.

#### 5. `touch` — Update File Timestamps / Create File
- **Syntaxe :** `touch [-c] [fichier...]`
- **Comportement :**
  - Si le fichier n'existe pas : Crée un nouveau fichier régulier vide (taille 0, mode `0o644` modifié par umask `0o022`, propriétaire `student:student`, horodatages `atime` et `mtime` à l'heure courante).
  - Si le fichier existe déjà : Met à jour `atime` et `mtime` à l'instant présent sans altérer le contenu.
- **Erreurs :**
  - Répertoire parent inexistant : `touch: cannot touch '<file>': No such file or directory\n`, code `1`.
  - Dossier parent non inscriptible : `touch: cannot touch '<file>': Permission denied\n`, code `1`.

#### 6. `mkdir` — Make Directories
- **Syntaxe :** `mkdir [-p] [-m mode] répertoire...`
- **Options :**
  - `-p`, `--parents` : Crée les répertoires parents manquants si nécessaire. Ne génère aucune erreur si le répertoire cible existe déjà.
  - `-m` : Définit les permissions octales explicites (ex: `-m 700`).
- **Comportement standard :** Crée un répertoire avec mode par défaut `0o755`.
- **Erreurs :**
  - Sans `-p`, dossier parent inexistant : `mkdir: cannot create directory '<dir>': No such file or directory\n`, code `1`.
  - Sans `-p`, dossier déjà existant : `mkdir: cannot create directory '<dir>': File exists\n`, code `1`.
  - Droits d'écriture absents sur le parent : `mkdir: cannot create directory '<dir>': Permission denied\n`, code `1`.

#### 7. `rm` — Remove Files or Directories
- **Syntaxe :** `rm [-r|-R] [-f] [-rf] chemin...`
- **Options :**
  - `-r`, `-R` : Suppression récursive des dossiers et de leur contenu.
  - `-f` : Ignore les fichiers inexistants, n'affiche aucun avertissement, ne bloque pas.
- **Sécurités :**
  - Si `rm /` ou `rm -rf /` : Bloqué avec `rm: it is dangerous to operate recursively on '/'\n`, code `1`.
  - Dossier ciblé sans `-r` : `rm: cannot remove '<dir>': Is a directory\n`, code `1`.
  - Fichier inexistant sans `-f` : `rm: cannot remove '<path>': No such file or directory\n`, code `1`.

#### 8. `cp` — Copy Files and Directories
- **Syntaxe :** `cp [-r|-R] [-f] [-p] source destination` ou `cp source... répertoire`
- **Options :**
  - `-r` : Copie récursive des sous-dossiers.
  - `-f` : Force l'écrasement des destinations existantes.
  - `-p` : Préserve le mode et les horodatages.
- **Comportement :**
  - Si `destination` est un dossier existant, la source y est dupliquée avec son nom original.
  - Dossier source sans `-r` : `cp: -r not specified; omitting directory '<dir>'\n`, code `1`.
  - Source inexistante : `cp: cannot stat '<src>': No such file or directory\n`, code `1`.

#### 9. `mv` — Move / Rename Files and Directories
- **Syntaxe :** `mv [-f] [-n] source destination` ou `mv source... répertoire`
- **Comportement :**
  - Déplace ou renomme un fichier/dossier atomiquement dans l'arbre VFS.
  - Si `destination` est un dossier, déplace la source à l'intérieur de ce dossier.
  - Si `destination` est un fichier existant, écrase ce dernier.
- **Erreurs :**
  - Source inexistante : `mv: cannot stat '<src>': No such file or directory\n`, code `1`.
  - Tentative de déplacer un dossier à l'intérieur de lui-même : `mv: cannot move '<dir>' to a subdirectory of itself\n`, code `1`.

#### 10. `echo` — Display a Line of Text
- **Syntaxe :** `echo [-n] [-e] [arg...]`
- **Options :**
  - `-n` : Supprime le saut de ligne final conventionnel.
  - `-e` : Active l'interprétation des séquences d'échappement (`\n` saut de ligne, `\t` tabulation, `\\` antislash).
- **Sortie :** Concaténation des arguments séparés par une espace unique.
- **Code retour :** `0`.

#### 11. `head` — Output the First Part of Files
- **Syntaxe :** `head [-n count] [fichier...]` ou `head -count [fichier...]`
- **Comportement :**
  - Par défaut, extrait les 10 premières lignes.
  - Si aucun fichier n'est fourni, lit depuis `stdin`.
- **Erreur :** `head: cannot open '<file>' for reading: No such file or directory\n`, code `1`.

#### 12. `tail` — Output the Last Part of Files
- **Syntaxe :** `tail [-n count] [fichier...]` ou `tail -count [fichier...]`
- **Comportement :**
  - Par défaut, extrait les 10 dernières lignes.
  - Supporte `tail -n +N` pour démarrer à la N-ième ligne.
  - Lit depuis `stdin` si aucun fichier n'est spécifié.
- **Erreur :** `tail: cannot open '<file>' for reading: No such file or directory\n`, code `1`.

#### 13. `wc` — Word, Line, Character, and Byte Count
- **Syntaxe :** `wc [-l] [-w] [-c] [-m] [fichier...]`
- **Options :**
  - `-l` : Compte le nombre de sauts de ligne (`\n`).
  - `-w` : Compte le nombre de mots (délimités par des espaces blancs).
  - `-c` : Compte le nombre d'octets.
  - `-m` : Compte le nombre de caractères.
- **Comportement :**
  - Sans option : Affiche `lines words bytes [fichier]`.
  - Lit depuis `stdin` si aucun fichier spécifié.
  - Si plusieurs fichiers, affiche une ligne par fichier puis une ligne `total`.
- **Erreur :** `wc: <file>: No such file or directory\n`, code `1`.

---

### 4.2 Permissions et Gestion d'Identité Utilisateur

#### 14. `chmod` — Change File Mode Bits
- **Syntaxe :** `chmod [-R] mode fichier...`
- **Modes supportés :**
  1. **Octal :** 3 ou 4 chiffres octaux (ex: `755`, `644`, `700`, `777`, `0755`).
     - Calcule la valeur numérique : `parseInt(mode, 8)`.
  2. **Symbolique :** Syntaxe POSIX standard :
     - Cibles : `u` (user), `g` (group), `o` (other), `a` (all, par défaut si omis).
     - Opérateurs : `+` (ajouter), `-` (retirer), `=` (définir exactement).
     - Droits : `r` (lecture=4), `w` (écriture=2), `x` (exécution=1).
     - Exemples valides : `chmod +x script.sh`, `chmod u=rwx,go=rx file`, `chmod 755 app.py`, `chmod a-w document.txt`.
- **Vérification de sécurité :**
  - Seul le propriétaire du fichier ou `root` peut modifier ses permissions.
  - Si un étudiant non-root tente de modifier un fichier appartenant à root : `chmod: changing permissions of '<file>': Operation not permitted\n`, code `1`.
- **Erreur de syntaxe :** `chmod: invalid mode: '<mode>'\n`, code `1`.

#### 15. `chown` — Change File Owner and Group
- **Syntaxe :** `chown [-R] propriétaire[:groupe] fichier...`
- **Comportement POSIX :**
  - Sous GNU/Linux, seul le super-administrateur `root` dispose du droit de changer le propriétaire d'un fichier.
  - Si exécuté par `student` : `chown: changing ownership of '<file>': Operation not permitted\n`, code `1`.
  - Si exécuté en tant que `root` (ou simulation root autorisée par l'exercice) : Met à jour les champs `owner` et `group` du nœud VFS.
- **Erreur utilisateur inconnu :** `chown: invalid user: '<user>'\n`, code `1`.

#### 16. `whoami` — Print Effective User ID
- **Syntaxe :** `whoami`
- **Comportement :** Écrit le nom de l'utilisateur actif courant (`student` ou `root`), suivi d'un saut de ligne.
- **Code retour :** `0`.

---

### 4.3 Processus et Utilitaires Système

#### 17. `ps` — Report a Snapshot of Current Processes
- **Syntaxe :** `ps [aux|-ef]`
- **Comportement :** Affiche la table simulée des processus du système.
- **Format standard (`ps`) :**
  ```
    PID TTY          TIME CMD
    101 pts/0    00:00:00 bash
    115 pts/0    00:00:00 ps
  ```
- **Format complet (`ps aux`) :**
  ```
  USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
  root         1  0.0  0.1  21424  5420 ?        Ss   09:00   0:01 /sbin/init
  root         2  0.0  0.0      0     0 ?        S    09:00   0:00 [kthreadd]
  student    101  0.0  0.1  13560  3840 pts/0    Ss   09:15   0:00 -bash
  student    115  0.0  0.0  15280  2100 pts/0    R+   10:30   0:00 ps aux
  ```
- **Code retour :** `0`.

#### 18. `top` — Display Linux Processes (Snapshot Mode)
- **Syntaxe :** `top [-n 1]`
- **Comportement en mode snapshot :** Génère l'en-tête de charge système et le tableau des processus consommateurs :
  ```
  top - 14:32:01 up 3 days,  5:12,  1 user,  load average: 0.08, 0.03, 0.01
  Tasks: 4 total,   1 running,   3 sleeping,   0 stopped,   0 zombie
  %Cpu(s):  1.2 us,  0.6 sy,  0.0 ni, 98.1 id,  0.1 wa,  0.0 hi,  0.0 si
  MiB Mem :   3920.4 total,   2150.2 free,    980.1 used,    790.1 buff/cache
  MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   2650.3 avail Mem

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
    101 student   20   0   13560   3840   3120 S   0.0   0.1   0:00.12 bash
      1 root      20   0   21424   5420   4100 S   0.0   0.1   0:01.05 systemd
  ```
- **Code retour :** `0`.

#### 19. `kill` — Send Signal to a Process
- **Syntaxe :** `kill [-9|-15|-SIGKILL|-SIGTERM] pid...`
- **Comportement :**
  - Vérifie l'existence du PID ciblé.
  - Si PID inexistant : `kill: (<pid>) - No such process\n`, code `1`.
  - Protection noyau : Impossible de tuer le PID 1 (`kill: (1) - Operation not permitted\n`), code `1`.
  - En cas de succès : Retire le PID simulé de la table des processus actifs. Code `0`.

#### 20. `uptime` — Tell How Long System Has Been Running
- **Syntaxe :** `uptime [-p]`
- **Comportement :** Affiche l'heure courante, le temps écoulé depuis le boot simulé, le nombre d'utilisateurs connectés et les moyennes de charge système (1 min, 5 min, 15 min).
  - Ex standard : ` 14:35:10 up 3 days,  5:15,  1 user,  load average: 0.05, 0.03, 0.01\n`
  - Ex pretty (`-p`) : `up 3 days, 5 hours, 15 minutes\n`
- **Code retour :** `0`.

#### 21. `uname` — Print System Information
- **Syntaxe :** `uname [-a] [-s] [-n] [-r] [-m]`
- **Comportement :**
  - Sans argument : `Linux\n`.
  - `-a` : `Linux examquiz 5.15.0-89-generic #99-Ubuntu SMP Mon Oct 20 12:00:00 UTC 2026 x86_64 GNU/Linux\n`.
  - `-s` : `Linux\n`.
  - `-n` : `examquiz\n`.
  - `-r` : `5.15.0-89-generic\n`.
  - `-m` : `x86_64\n`.
- **Code retour :** `0`.

#### 22. `env` — Display Environment Variables
- **Syntaxe :** `env`
- **Comportement :** Écrit l'ensemble des variables d'environnement actives sous la forme `NOM=valeur`, une par ligne.
  ```
  SHELL=/bin/bash
  USER=student
  HOME=/home/student
  PATH=/usr/local/bin:/usr/bin:/bin
  PWD=/home/student
  TERM=xterm-256color
  LANG=fr_FR.UTF-8
  ```
- **Code retour :** `0`.

#### 23. `export` — Set Environment Variables
- **Syntaxe :** `export [NOM=valeur...]` ou `export NOM`
- **Comportement :**
  - Sans argument : Affiche les variables avec le préfixe `declare -x NOM="valeur"`.
  - Avec assignation : Stocke la variable dans la table d'environnement du shell et l'exporte aux sous-commandes.
  - Validation du nom d'identifiant (doit commencer par lettre ou `_`) : Si invalide (`export 1var=abc`), renvoie `export: '1var=abc': not a valid identifier\n`, code `1`.

#### 24. `date` — Display System Date and Time
- **Syntaxe :** `date [+format]`
- **Comportement :** Formate la date selon le standard POSIX (par défaut : `Tue Oct 20 14:38:00 UTC 2026\n`). Supporte les jetons usuels `+%Y`, `+%m`, `+%d`, `+%H:%M:%S`.
- **Code retour :** `0`.

---

## 5. Spécification des Utilitaires de Filtrage et de Recherche de Texte

### 5.1 `grep` — Print Lines Matching a Pattern
- **Syntaxe :** `grep [-i] [-v] [-n] [-c] [-l] [-E] motif [fichier...]`
- **Options :**
  - `-i` : Ignore la distinction majuscules/minuscules (case-insensitive).
  - `-v` : Inverse la sélection (conserve les lignes qui ne correspondent PAS au motif).
  - `-n` : Préfixe chaque ligne correspondante par son numéro de ligne (1-indexé) suivi de deux-points `:`.
  - `-c` : Affiche uniquement le décompte total des lignes correspondantes.
  - `-l` : Affiche uniquement les noms des fichiers contenant au moins une correspondance.
  - `-E` : Interprète le motif comme une expression régulière étendue (regex JS native).
- **Gestion des flux :**
  - Si aucun fichier n'est spécifié : Lit depuis `stdin` (permet les pipes `cat file | grep pattern`).
  - Si plusieurs fichiers sont fournis : Préfixe chaque ligne par le nom du fichier (`fichier:ligne`).
- **Codes retour POSIX rigoureux :**
  - `0` : Au moins une ligne correspondante a été trouvée.
  - `1` : Aucune ligne correspondante trouvée.
  - `2` : Erreur (fichier introuvable ou expression régulière invalide).

### 5.2 `find` — Search for Files in a Directory Hierarchy
- **Syntaxe :** `find [chemin...] [-name motif] [-iname motif] [-type f|d|l] [-maxdepth N] [-empty]`
- **Prédicats de filtrage :**
  - `-name motif` : Filtrage par motif glob (`*.txt`, `test_*`, `a.?`). Sensible à la casse.
  - `-iname motif` : Filtrage par glob insensible à la casse.
  - `-type [f|d|l]` : Filtre selon la nature du nœud (`f` = fichier ordinaire, `d` = répertoire, `l` = lien).
  - `-maxdepth N` : Limite la profondeur de récursion dans l'arbre (0 = répertoire de départ seul, 1 = enfants directs).
  - `-empty` : Cible les fichiers de taille 0 ou les répertoires sans enfants.
- **Comportement :**
  - Par défaut (sans chemin) : Démarre la recherche à partir du répertoire courant `.`.
  - Parcourt l'arborescence VFS de façon récursive pré-ordre (depth-first).
  - Écrit les chemins trouvés sur `stdout`, un par ligne.
- **Erreur :** Chemin racine inexistant : `find: '<path>': No such file or directory\n`, code `1`.

### 5.3 `sort` — Sort Lines of Text
- **Syntaxe :** `sort [-r] [-n] [-u] [fichier...]`
- **Options :**
  - `-r` : Inverse l'ordre du tri (décroissant).
  - `-n` : Compare selon la valeur numérique de la chaîne (ex: 2 avant 10, contrairement au tri alphabétique).
  - `-u` : Filtre les doublons stricts (produit des lignes uniques).
- **Comportement :** Concatène les fichiers (ou lit `stdin`), trie les lignes selon les options et écrit le résultat sur `stdout`. Code retour `0`.

### 5.4 `uniq` — Report or Omit Repeated Lines
- **Syntaxe :** `uniq [-c] [-d] [-u] [-i] [fichier]`
- **Options :**
  - `-c` : Préfixe chaque ligne par son nombre d'occurrences adjacentes consécutives.
  - `-d` : Affiche uniquement les lignes dupliquées consécutives.
  - `-u` : Affiche uniquement les lignes uniques (strictement non répétées consécutivement).
  - `-i` : Ignore la casse des caractères.
- **Règle fondamentale POSIX :** `uniq` ne détecte que les doublons consécutifs (adjacents). Pour dédoublonner un fichier non trié, la séquence idiome `sort file | uniq` est requise et doit fonctionner de manière fluide. Code retour `0`.

---

## 6. Spécification de la Mécanique Shell (Pipes, Redirections, Enchaînements)

### 6.1 Analyseur Lexical (Lexer) & Tokenisation
L'analyseur découpe la ligne de commande brute en jetons typés en respectant scrupuleusement les règles de citation POSIX :
1. **Guillemets simples (`'...'`) :**
   - Préservation littérale intégrale. Aucune substitution de variable (`$VAR`), aucun échappement par antislash n'est interprété.
2. **Guillemets doubles (`"..."`) :**
   - Préservation des espaces internes comme faisant partie d'un seul argument.
   - Expansion des variables d'environnement (`$VAR` ou `${VAR}`) et du code retour (`$?`).
   - Interprétation des antislashes d'échappement (`\"`, `\\`, `\$`).
3. **Antislash hors guillemets (`\`) :**
   - Échappe le caractère suivant immédiat (permet par exemple d'écrire `Mon\ Dossier`).
4. **Opérateurs reconnus :**
   - Redirections : `>`, `>>`, `<`, `2>`, `&>`
   - Pipe : `|`
   - Enchaînements : `&&`, `||`, `;`

### 6.2 Grammaire et Arbre Syntaxique Abstrait (AST)
```typescript
interface ShellCommandList {
  chains: Array<{
    operator: 'START' | 'AND' | 'OR' | 'SEQ'; // 'START' | '&&' | '||' | ';'
    pipeline: Pipeline;
  }>;
}

interface Pipeline {
  commands: Array<SimpleCommand>;
}

interface SimpleCommand {
  executable: string;
  args: string[];
  redirections: Array<{
    type: 'write' | 'append' | 'read' | 'stderr_write'; // '>', '>>', '<', '2>'
    target: string;
  }>;
}
```

### 6.3 Moteur de Redirection de Flux
1. **Redirection de sortie standard (`>`) :**
   - Capture le flux `stdout` de la commande.
   - Écrit dans le fichier cible du VFS.
   - Si le fichier n'existe pas : Le crée avec mode `0o644`.
   - Si le fichier existe déjà : **Tronque son contenu à 0** avant écriture.
2. **Ajout à la sortie standard (`>>`) :**
   - Capture `stdout`.
   - Si le fichier n'existe pas : Le crée.
   - Si le fichier existe : **Ajoute** le nouveau contenu à la suite du contenu existant.
3. **Redirection d'entrée standard (`<`) :**
   - Ouvre le fichier spécifié dans le VFS.
   - Si le fichier n'existe pas : Interrompt l'exécution avec `bash: <file>: No such file or directory\n`, code retour `1`.
   - Injecte le contenu du fichier comme flux `stdin` de la commande.
4. **Redirection combinée :**
   - Exemple : `cat < input.txt | grep "cle" > output.txt`
   - Lit `input.txt`, le transmet via pipe à `grep`, et écrit le résultat filtré dans `output.txt`.

### 6.4 Moteur de Pipelines (`cmd1 | cmd2 | cmd3`)
1. Le flux `stdout` produit par `cmd1` est bufferisé en mémoire et connecté comme `stdin` de `cmd2`.
2. Le flux `stdout` produit par `cmd2` devient le `stdin` de `cmd3`.
3. Les commandes du pipeline s'exécutent de façon séquentielle ou asynchrone concurrente.
4. **Code de retour du pipeline :**
   - Par défaut sous Bash, le code retour de l'ensemble du pipeline est celui de la **dernière commande** du pipeline (`cmd3`).
   - L'ensemble des modifications d'état du VFS effectuées par chaque maillon du pipeline persiste immédiatement.

### 6.5 Variable Spéciale `$?` et Codes de Retour
- Chaque exécution de commande met à jour la variable globale interne `$?` avec l'exit code résultant :
  - `0` : Succès total.
  - `1` : Erreur applicative générale (fichier absent, permission refusée, syntaxe incorrecte).
  - `2` : Mauvaise utilisation des commandes internes (ou `grep` sans correspondance avec erreur).
  - `127` : Commande introuvable (`bash: <cmd>: command not found\n`).
  - `130` : Interruption par `Ctrl+C` (`SIGINT`).
- L'exécution de `echo $?` renvoie la valeur exacte du code retour de la commande immédiatement antérieure.

### 6.6 Opérateurs d'Enchaînement Conditionnel
1. **Opérateur ET logique (`&&`) :**
   - `cmd1 && cmd2` : Exécute `cmd1`. Si et seulement si `cmd1` retourne un code `0`, alors `cmd2` est exécutée. Si `cmd1` échoue (`code !== 0`), `cmd2` est court-circuitée.
2. **Opérateur OU logique (`||`) :**
   - `cmd1 || cmd2` : Exécute `cmd1`. Si `cmd1` réussit (`code === 0`), `cmd2` est court-circuitée. Si `cmd1` échoue (`code !== 0`), alors `cmd2` est exécutée.
3. **Séparateur séquentiel (`;`) :**
   - `cmd1 ; cmd2` : Exécute `cmd1` jusqu'à son terme, puis exécute inconditionnellement `cmd2`, quel que soit le code retour de `cmd1`.

---

## 7. Spécification du Moteur d'Évaluation des Défis Linux

### 7.1 Schéma de Définition d'un Défi Pratique
```json
{
  "id": "linux_ch_03_permissions",
  "title": "Sécurisation d'un Script de Déploiement",
  "difficulty": "Intermédiaire",
  "category": "Permissions & Droits",
  "instructions_markdown": "Le script `/home/student/deploy.sh` contient des instructions sensibles. Modifiez ses permissions pour que le propriétaire ait tous les droits (lecture, écriture, exécution) et les membres du groupe uniquement la lecture et l'exécution, tandis que les autres utilisateurs n'ont aucun droit.",
  "initial_vfs": {
    "dirs": [
      { "path": "/home/student/backup", "mode": "0755" }
    ],
    "files": [
      { 
        "path": "/home/student/deploy.sh", 
        "content": "#!/bin/bash\necho \"Déploiement en cours...\"\n", 
        "mode": "0644",
        "owner": "student",
        "group": "student"
      }
    ]
  },
  "public_tests": [
    {
      "name": "Exécutabilité par le propriétaire",
      "type": "fs_mode",
      "path": "/home/student/deploy.sh",
      "expected": "750"
    },
    {
      "name": "Intégrité du script",
      "type": "fs_exists",
      "path": "/home/student/deploy.sh",
      "expected": "file"
    }
  ],
  "hidden_tests": [
    {
      "name": "Absence totale de droits pour others",
      "type": "fs_mode_mask",
      "path": "/home/student/deploy.sh",
      "mask": "007",
      "expected": "000"
    },
    {
      "name": "Préservation du contenu original",
      "type": "fs_content_exact",
      "path": "/home/student/deploy.sh",
      "expected": "#!/bin/bash\necho \"Déploiement en cours...\"\n"
    },
    {
      "name": "Code de retour réussi",
      "type": "exit_code",
      "expected": 0
    }
  ]
}
```

### 7.2 Typologie des Assertions d'Évaluation
| Type d'Assertion | Description | Critères Vérifiés |
|------------------|-------------|-------------------|
| `fs_exists` | Vérifie l'existence d'une ressource et son type | Le chemin existe et est de type `file`, `dir` ou `symlink`. |
| `fs_not_exists` | Vérifie la suppression d'une ressource | Le chemin n'existe plus dans le VFS (ex: test de `rm`). |
| `fs_content_exact` | Vérifie le contenu d'un fichier textuel | Comparaison stricte de la chaîne UTF-8 du fichier. |
| `fs_content_regex` | Vérifie le contenu partiel ou formaté | Expression régulière validée sur le texte du fichier. |
| `fs_content_lines` | Vérifie le nombre de lignes | Décompte exact des lignes du fichier après commande. |
| `fs_mode` | Vérifie les permissions octales | Le mode POSIX du fichier correspond (ex: `"755"`, `"644"`). |
| `fs_owner` | Vérifie l'appartenance utilisateur et groupe | `owner === expected_owner && group === expected_group`. |
| `stdout_exact` | Vérifie la sortie standard | La sortie affichée correspond exactement au résultat attendu. |
| `stdout_regex` | Vérifie la sortie par motif | La sortie valide une expression régulière. |
| `stdout_contains` | Vérifie la présence d'une sous-chaîne | `stdout.includes(expectedSubstr)`. |
| `exit_code` | Vérifie le code d'état du shell | `$? === expectedCode` (typiquement `0`). |

### 7.3 Isolation Anti-Triche et Confidentialité
- **Étanchéité des tests cachés :** Les critères des tests cachés (`hidden_tests`) ne sont **jamais** exposés dans le DOM HTML, ni enregistrés dans les variables globales accessibles depuis la console DevTools de l'étudiant.
- **Exécution d'évaluation :** Lors du clic sur "Tester sur les Cas Publics", seules les assertions publiques sont exécutées avec feedback détaillé (attendu vs obtenu). Lors du clic sur "Soumettre le Défi", l'évaluation complète (tests publics + au moins 5 tests cachés) est déroulée de façon sécurisée, renvoyant uniquement le score agrégé (ex: `7/7 validés`) et le statut de validation.
- **Réinitialisation en un clic :** L'étudiant peut à tout moment cliquer sur "🔄 Réinitialiser l'environnement" pour recharger l'état `initial_vfs` propre défini par l'exercice.

---

## 8. Inventaire Exhaustif des Fonctionnalités Découvertes (Features Discovered)

| # | Catégorie | Fonctionnalité | Description | Entrées | Sorties | Comportement d'Erreur | Découvert Via |
|---|-----------|----------------|-------------|---------|---------|-----------------------|---------------|
| 1 | VFS | Modèle Inode & Nœud | Représentation en mémoire d'un fichier ou dossier avec métadonnées complètes | Propriétés nœud (mode, uid, gid, size, etc.) | Instance `VFSNode` | N/A | DISPATCH §1, FHS standard |
| 2 | VFS | Normalisation de Chemins | Résolution des chemins relatifs, `..`, `.`, doubles slashes et `~` | `(cwd, rawPath)` | Chemin absolu normalisé (ex: `/home/student/doc`) | Conserve `/` si pile vide | POSIX IEEE 1003.1 |
| 3 | VFS | Évaluation des Permissions | Contrôle des bits octaux `rwx` pour user, group et others | `(node, mode, user)` | Booléen `true`/`false` | `EACCES` si refus | POSIX chmod/stat specs |
| 4 | VFS | Traversée de Répertoires | Validation du droit d'exécution (`x`) sur chaque parent | Segment de chemin | Pointeur vers nœud enfant | `EACCES` (Permission denied) | Linux Kernel VFS rules |
| 5 | VFS | Liens Symboliques | Suivi récursif de la cible d'un symlink avec garde-fou | `node.target` | Nœud cible | `ELOOP` si > 20 sauts | POSIX readlink specs |
| 6 | VFS | Snapshot & Restore | Clônage sérialisé complet de l'arbre pour isolation des tests | Arborescence VFS | Objet JSON / Restauration VFS | N/A | DISPATCH §1, R3 |
| 7 | Terminal | CLI Prompt Dynamique | Invite `student@examquiz:~$ ` avec tilde et couleurs | Utilisateur, Host, CWD | Chaîne prompt HTML stylisée | Affiche `#` si root | DISPATCH §2, Bash manual |
| 8 | Terminal | Historique Up/Down | Navigation dans les commandes antérieures avec conservation du brouillon | Touches Flèche Haut / Bas | Remplacement du texte de saisie | Butée haute/basse gérée sans plantage | DISPATCH §2, Readline spec |
| 9 | Terminal | Autocomplétion Tab | Complétion des binaires et des chemins de fichiers | Touche Tabulation | Complétion ou liste des choix | Flash visuel si 0 match | DISPATCH §2, Readline spec |
| 10 | Terminal | Effacement Écran | Remise à blanc de la zone d'affichage du terminal | Commande `clear` ou `Ctrl+L` | Nettoyage du DOM log | Conserve la ligne active | DISPATCH §2, xterm spec |
| 11 | Terminal | Interruption SIGINT | Annulation de la frappe en cours avec code retour 130 | Touche `Ctrl+C` | Affiche `^C`, nouvelle invite, `$?=130` | Ligne en cours abandonnée | POSIX signal spec |
| 12 | POSIX Nav | `pwd` | Affiche le chemin absolu du répertoire courant | Aucun | `<cwd>\n` | Code retour 0 | POSIX IEEE 1003.1 `pwd` |
| 13 | POSIX Nav | `cd` | Change de répertoire avec support de `~` et `-` | `[dir]` | Met à jour CWD et OLDPWD | `cd: <dir>: No such file or directory` (code 1) | POSIX IEEE 1003.1 `cd` |
| 14 | POSIX Nav | `ls` | Liste les fichiers avec options `-l`, `-a`, `-la`, `-lh`, `-1` | Options, `[paths...]` | Tableau des entrées formaté | `ls: cannot access '<p>': No such file...` (code 2) | POSIX IEEE 1003.1 `ls` |
| 15 | POSIX Files | `cat` | Concatène et affiche des fichiers ou l'entrée standard | `[-n] [files...]`, stdin | Contenu concaténé sur stdout | `cat: <file>: Is a directory` (code 1) | POSIX IEEE 1003.1 `cat` |
| 16 | POSIX Files | `touch` | Crée un fichier vide ou rafraîchit ses horodatages | `[files...]` | Fichier créé ou mtime mis à jour | `touch: cannot touch '<f>': No such file...` (code 1) | POSIX IEEE 1003.1 `touch` |
| 17 | POSIX Files | `mkdir` | Crée des répertoires avec option récursive `-p` | `[-p] [dirs...]` | Nouveaux nœuds répertoire dans VFS | `mkdir: cannot create...: File exists` (code 1) | POSIX IEEE 1003.1 `mkdir` |
| 18 | POSIX Files | `rm` | Supprime fichiers ou dossiers (avec `-r`, force `-f`) | `[-rf] [paths...]` | Suppression des nœuds dans VFS | Refus de supprimer `/` ; `Is a directory` sans `-r` | POSIX IEEE 1003.1 `rm` |
| 19 | POSIX Files | `cp` | Copie fichiers ou répertoires (avec `-r`) | `[-r] src dst` | Nœud dupliqué dans VFS | `omitting directory` sans `-r` (code 1) | POSIX IEEE 1003.1 `cp` |
| 20 | POSIX Files | `mv` | Déplace ou renomme fichiers et répertoires | `src dst` | Déplacement du nœud dans l'arborescence | `cannot move to a subdirectory of itself` (code 1) | POSIX IEEE 1003.1 `mv` |
| 21 | POSIX Files | `echo` | Affiche du texte avec support de `-n` et `-e` | `[-n] [-e] [args...]` | Texte affiché sur stdout | Code retour 0 | POSIX IEEE 1003.1 `echo` |
| 22 | POSIX Files | `head` | Extrait les N premières lignes d'un flux | `[-n count] [file]`, stdin | N premières lignes sur stdout | `head: cannot open '<f>': No such file...` (code 1) | POSIX IEEE 1003.1 `head` |
| 23 | POSIX Files | `tail` | Extrait les N dernières lignes d'un flux | `[-n count] [file]`, stdin | N dernières lignes sur stdout | `tail: cannot open '<f>': No such file...` (code 1) | POSIX IEEE 1003.1 `tail` |
| 24 | POSIX Files | `wc` | Décompte les lignes (`-l`), mots (`-w`) et octets (`-c`) | `[-lwc] [file]`, stdin | Totaux formatés sur stdout | `wc: <file>: No such file or directory` (code 1) | POSIX IEEE 1003.1 `wc` |
| 25 | Permissions | `chmod` | Modifie les droits en notation octale (`755`) ou symbolique (`+x`) | Mode, `file...` | Nœud VFS mis à jour avec nouveau mode | `invalid mode` ou `Operation not permitted` (code 1) | DISPATCH §4, IEEE 1003.1 `chmod` |
| 26 | Permissions | `chown` | Modifie le propriétaire et le groupe d'un fichier | `owner[:group] file...` | `node.owner` et `node.group` mis à jour | `Operation not permitted` si non-root (code 1) | DISPATCH §4, IEEE 1003.1 `chown` |
| 27 | Permissions | `whoami` | Affiche le nom de l'utilisateur effectif courant | Aucun | `student\n` ou `root\n` | Code retour 0 | DISPATCH §4, IEEE 1003.1 `whoami` |
| 28 | Processus | `ps` | Affiche la table instantanée des processus (`aux`, `-ef`) | `[options]` | Tableau formaté PID/USER/%CPU/CMD | Code retour 0 | DISPATCH §5, Linux man `ps` |
| 29 | Processus | `top` | Affiche un instantané d'utilisation CPU/Mémoire/Tâches | Aucun | En-tête système + liste des processus | Code retour 0 | DISPATCH §5, Linux man `top` |
| 30 | Processus | `kill` | Envoie un signal de terminaison à un processus | `[-9|-15] pid...` | Processus retiré de la table active | `No such process` ou `Operation not permitted` sur PID 1 | DISPATCH §5, IEEE 1003.1 `kill` |
| 31 | Système | `uptime` | Affiche la durée d'activité système et load average | `[-p]` | Chaîne uptime formatée | Code retour 0 | DISPATCH §5, Linux man `uptime` |
| 32 | Système | `uname` | Affiche les informations d'architecture noyau | `[-a|-s|-r|-m]` | `Linux examquiz 5.15...` | Code retour 0 | DISPATCH §5, IEEE 1003.1 `uname` |
| 33 | Système | `env` | Liste les variables d'environnement actives | Aucun | Lignes `KEY=value` | Code retour 0 | DISPATCH §5, POSIX `env` |
| 34 | Système | `export` | Définit ou affiche des variables d'environnement | `[NAME=val]` | Variable insérée dans l'environnement | `not a valid identifier` si nom invalide (code 1) | DISPATCH §5, Bash manual `export` |
| 35 | Système | `date` | Affiche la date et l'heure système formatée | `[+format]` | Date formatée standard POSIX | Code retour 0 | DISPATCH §5, IEEE 1003.1 `date` |
| 36 | Filtrage | `grep` | Recherche de motifs regex avec `-i`, `-v`, `-n`, `-c`, `-l` | Motif, `[files...]`, stdin | Lignes correspondantes | Code 0 si trouvé, 1 si non trouvé, 2 si erreur | DISPATCH §6, IEEE 1003.1 `grep` |
| 37 | Filtrage | `find` | Recherche arborescente par `-name`, `-type`, `-maxdepth` | `[path]`, prédicats | Chemins correspondants | `No such file or directory` si chemin invalide (code 1) | DISPATCH §6, IEEE 1003.1 `find` |
| 38 | Filtrage | `sort` | Tri lexicographique ou numérique (`-n`), inversé (`-r`) | `[-rnu] [file]`, stdin | Lignes triées sur stdout | Code retour 0 | DISPATCH §6, IEEE 1003.1 `sort` |
| 39 | Filtrage | `uniq` | Déduplication des lignes adjacentes (`-c`, `-d`, `-u`) | `[-cdui] [file]`, stdin | Lignes filtrées sur stdout | Code retour 0 | DISPATCH §6, IEEE 1003.1 `uniq` |
| 40 | Shell Mechanics | Tubes (Pipes `\|`) | Chaînage du stdout de commande N vers le stdin de N+1 | `cmd1 \| cmd2` | Flux de sortie final de la dernière commande | Code retour de la dernière commande | DISPATCH §7, POSIX Shell grammar |
| 41 | Shell Mechanics | Redirection Sortie `>` | Écrasement d'un fichier avec le stdout produit | `cmd > file` | Fichier créé ou tronqué, contenu écrit | `Permission denied` si dossier parent non inscriptible | DISPATCH §7, POSIX Shell grammar |
| 42 | Shell Mechanics | Redirection Ajout `>>` | Concaténation du stdout à la fin d'un fichier | `cmd >> file` | Fichier créé ou complété | `Permission denied` si fichier non inscriptible | DISPATCH §7, POSIX Shell grammar |
| 43 | Shell Mechanics | Redirection Entrée `<` | Injection du contenu d'un fichier comme stdin | `cmd < file` | Contenu transmis comme flux d'entrée | `No such file or directory` si fichier absent (code 1) | DISPATCH §7, POSIX Shell grammar |
| 44 | Shell Mechanics | Variable `$?` | Conservation et consultation du code de sortie | `echo $?` | Nombre entier (0, 1, 127, 130...) | Code retour 0 | DISPATCH §7, POSIX Shell grammar |
| 45 | Shell Mechanics | Chaînage `&&` | Exécution conditionnelle si commande précédente réussie | `cmd1 && cmd2` | Sorties combinées, cmd2 exécutée si cmd1 code=0 | Court-circuit si cmd1 échoue | DISPATCH §7, POSIX Shell grammar |
| 46 | Shell Mechanics | Chaînage `\|\|` | Exécution alternative si commande précédente échouée | `cmd1 \|\| cmd2` | Sorties combinées, cmd2 exécutée si cmd1 code!=0 | Court-circuit si cmd1 réussit | POSIX Shell grammar |
| 47 | Shell Mechanics | Séparateur `;` | Exécution séquentielle inconditionnelle de commandes | `cmd1 ; cmd2` | Sorties combinées dans l'ordre | Exécute cmd2 quel que soit le code de cmd1 | DISPATCH §7, POSIX Shell grammar |
| 48 | Évaluation | Moteur de Tests Défi | Validation des assertions stdout et état VFS pour défis | `challenge.json` | Tableau des résultats de tests (Pass/Fail) | Feedback précis sur divergences | DISPATCH §3, R3 |

---

## 9. Analyse Exhaustive des Cas Limites (Edge Cases)

| # | Fonctionnalité | Entrée / Contexte | Comportement Observé & Spécifié |
|---|----------------|-------------------|---------------------------------|
| 1 | VFS Navigation | `cd /` puis `cd ..` | Reste bloqué à la racine `/`. Aucun plantage de pile. |
| 2 | VFS Traversal | `cd ///home///student///` | Les slashes consécutifs multiples sont nettoyés en `/home/student`. |
| 3 | VFS Traversal | `cd non_existent_folder` | Affiche `cd: non_existent_folder: No such file or directory` sur stderr, exit code 1. |
| 4 | VFS Traversal | `cd file.txt` (sur un fichier régulier) | Affiche `cd: file.txt: Not a directory` sur stderr, exit code 1. |
| 5 | VFS Traversal | `cat /root/secret.txt` (en tant que `student`) | Refusé avec `cat: /root/secret.txt: Permission denied` (dossier parent `/root` mode `0700` sans execute pour student). |
| 6 | VFS Traversal | Dossier sans droit lecture mais avec exécution (`--x`) | `cd dir` réussit (droit `x` présent), mais `ls dir` échoue avec `Permission denied` (droit `r` manquant). |
| 7 | Shell Parsing | Guillemets simples imbriqués : `echo '$USER'` | Affiche littéralement `$USER` sans substituer la variable. |
| 8 | Shell Parsing | Guillemets doubles : `echo "$USER is here"` | Substitue correctement la variable : `student is here`. |
| 9 | Shell Parsing | Ligne vide ou composée uniquement d'espaces | Aucun affichage, aucun code d'erreur, réaffiche immédiatement l'invite sans polluer l'historique. |
| 10 | Shell Pipes | `cat file.txt \| grep "cle" \| wc -l` | Multi-étage : le stdout de cat est filtré par grep, et wc compte exactement les lignes résultantes. |
| 11 | Shell Pipes | `invalid_cmd \| wc -l` | `invalid_cmd: command not found` envoyé sur stderr, wc reçoit un stdin vide et renvoie `0`. Code retour du pipeline est 0 (exit code de wc). |
| 12 | Shell Redirection | `echo "abc" > file.txt && echo "def" > file.txt` | Le fichier `file.txt` contient uniquement `"def\n"` (troncature par `>`). |
| 13 | Shell Redirection | `echo "abc" > file.txt && echo "def" >> file.txt` | Le fichier `file.txt` contient `"abc\ndef\n"` (concaténation par `>>`). |
| 14 | Shell Redirection | `cat < non_existent.txt` | Affiche `bash: non_existent.txt: No such file or directory`, `cat` n'est pas invoqué, exit code 1. |
| 15 | Shell Chaining | `false && echo "reussi"` | `echo "reussi"` n'est jamais exécuté. Exit code final est 1. |
| 16 | Shell Chaining | `false \|\| echo "recupere"` | Affiche `"recupere\n"`. Exit code final est 0. |
| 17 | Shell Chaining | `echo "a" ; false ; echo "b"` | Affiche `"a\n"` puis `"b\n"`. Les trois commandes s'exécutent. Exit code final est 0. |
| 18 | `chmod` | `chmod 777 /home/student/notes.txt` | Met à jour le mode à `0o777`. `ls -l` affiche `-rwxrwxrwx`. |
| 19 | `chmod` | `chmod +x script.sh` (mode symbolique) | Ajoute le bit d'exécution sur user, group et others. |
| 20 | `chmod` | `chmod 999 file.txt` (chiffres octaux invalides) | Rejeté immédiatement avec `chmod: invalid mode: '999'`, exit code 1. |
| 21 | `chmod` | `chmod 755 /etc/shadow` (par l'étudiant) | Refusé avec `chmod: changing permissions of '/etc/shadow': Operation not permitted`. |
| 22 | `chown` | `chown root file.txt` (par l'étudiant) | Refusé avec `chown: changing ownership of 'file.txt': Operation not permitted`. |
| 23 | `mkdir` | `mkdir a/b/c` (sans `-p`, parents inexistants) | Affiche `mkdir: cannot create directory 'a/b/c': No such file or directory`, code 1. |
| 24 | `mkdir` | `mkdir -p a/b/c` (avec parents inexistants) | Crée récursivement les dossiers `a`, `a/b` et `a/b/c`. Exit code 0. |
| 25 | `mkdir` | `mkdir existing_dir` (répertoire existant) | Affiche `mkdir: cannot create directory 'existing_dir': File exists`, code 1. |
| 26 | `mkdir` | `mkdir -p existing_dir` (avec `-p`) | Réussite silencieuse sans erreur. Exit code 0. |
| 27 | `rm` | `rm -r /` | Bloqué par la sécurité noyau : `rm: it is dangerous to operate recursively on '/'`. |
| 28 | `rm` | `rm -rf non_existent_file` | Réussite silencieuse (pas d'erreur grâce au flag force `-f`). Exit code 0. |
| 29 | `rm` | `rm dir` (sans `-r` sur un dossier) | Affiche `rm: cannot remove 'dir': Is a directory`, exit code 1. |
| 30 | `grep` | `grep "python" document.txt` (aucun match) | N'affiche rien sur stdout, exit code est 1. |
| 31 | `grep` | `grep -v "error" log.txt` | N'affiche que les lignes ne contenant pas la sous-chaîne `"error"`. |
| 32 | `grep` | `grep -n "motif" file.txt` | Affiche `1:premiere ligne`, `4:quatrieme ligne` avec numéro 1-indexé. |
| 33 | `find` | `find . -name "*.sh"` | Trouve tous les scripts récursivement, sans être bloqué par la casse. |
| 34 | `find` | `find / -type f -maxdepth 1` | Ne recherche que les fichiers réguliers à la racine immédiate `/`. |
| 35 | `sort` & `uniq` | `echo -e "b\na\nb" \| uniq` | Affiche `b\na\nb` car les `b` ne sont pas adjacents ! |
| 36 | `sort` & `uniq` | `echo -e "b\na\nb" \| sort \| uniq` | Affiche proprement `a\nb` (déduplication effective). |
| 37 | `kill` | `kill 1` (tentative d'arrêt de systemd/init) | Affiche `kill: (1) - Operation not permitted`, exit code 1. |
| 38 | `kill` | `kill 99999` (PID inexistant) | Affiche `kill: (99999) - No such process`, exit code 1. |
| 39 | `whoami` | Exécution standard | Affiche `student\n`, exit code 0. |
| 40 | Terminal UI | Pression de `Ctrl+C` en cours de frappe | Affiche `^C`, annule la saisie, affecte `$?=130` et crée une nouvelle ligne avec l'invite. |
| 41 | Terminal UI | Double tabulation sur préfixe ambigu (ex: `co`) | Affiche la liste des commandes candidates (`cp`, etc.) sans effacer la ligne courante. |
| 42 | Terminal UI | Commande introuvable : `foobar` | Affiche `bash: foobar: command not found` sur stderr, exit code 127. |

---

## 10. Recommandations d'Architecture Logicielle Frontend & Fichiers Cibles

Pour implémenter cette spécification avec une séparation des responsabilités exemplaire, les modules suivants doivent être introduits dans `frontend/js/` :

```
frontend/js/
├── linux/
│   ├── vfs.js              # Classe VirtualFS, VFSNode, résolution & normalisation
│   ├── shell-lexer.js      # Analyseur lexical (tokens, quotes, escapes, variables)
│   ├── shell-parser.js     # Analyseur syntaxique (AST, pipelines, redirections)
│   ├── shell-engine.js     # Exécuteur shell, orchestration des flux et des enchaînements
│   ├── posix-commands.js   # Implémentation des 23 commandes intégrées (ls, cd, grep, ...)
│   ├── terminal-ui.js      # Gestionnaire du DOM terminal, prompt, historique, Tab
│   ├── linux-evaluator.js  # Moteur d'évaluation des défis (tests publics et cachés)
│   └── linux-runner.js     # Contrôleur général de la vue Linux Training (#view-linux)
```

### Intégration dans `index.html` et `app.js` :
- L'import principal s'effectue dans `app.js` :
  ```javascript
  import { LinuxRunner } from './linux/linux-runner.js';
  ```
- La vue `#view-linux` s'active de manière homogène avec `#view-python` lors de la navigation, avec bascule fluide entre le **Volet Théorique** (QCM & synthèses) et le **Volet Pratique** (Atelier Terminal deux-volets).
