"""
Générateur complet du Centre d'Entraînement Linux :
- 6 Chapitres fondamentaux
- Volet Théorique : 20 questions riches par chapitre (avec tous les types : single_choice, multi_choice, boolean, matching, fill_blank)
- Volet Pratique : 15 défis par chapitre (10 Faciles + 5 Intermédiaires) = 90 Défis pratiques au total !
- Sauvegarde dans :
    - backend/app/data/linux_training/challenges.json (90 défis complets avec VFS, public_tests et hidden_tests)
    - backend/app/data/linux_training/curriculum.json (6 chapitres, questions théoriques et coding_exercises reliés)
"""
import json
import os

CHAPTERS_CONFIG = [
    {
        "id": "fhs_navigation",
        "title": "Arborescence FHS & Navigation",
        "order": 1,
        "level": 1,
        "description": "Structure du système de fichiers Linux (FHS), chemins relatifs et absolus, commandes pwd, cd et ls avec options."
    },
    {
        "id": "file_management",
        "title": "Manipulation de Fichiers & Répertoires",
        "order": 2,
        "level": 1,
        "description": "Création, copie, déplacement, renommage et suppression sécurisée de fichiers et dossiers (touch, mkdir, cp, mv, rm)."
    },
    {
        "id": "permissions_security",
        "title": "Permissions & Droits d'Accès POSIX",
        "order": 3,
        "level": 2,
        "description": "Modèle de sécurité UNIX, attributs rwx (lecture, écriture, exécution), modes octaux et symboliques (chmod, chown, umask)."
    },
    {
        "id": "text_processing_pipes",
        "title": "Filtres, Tubes & Redirections",
        "order": 4,
        "level": 3,
        "description": "Flux standards (stdin, stdout, stderr), redirections (>, >>, 2>), pipelines (|), recherche grep, tri sort et filtres textuels."
    },
    {
        "id": "processes_signals",
        "title": "Gestion des Processus & Signaux",
        "order": 5,
        "level": 4,
        "description": "Cycle de vie des processus, identifiants PID/PPID, signaux POSIX (SIGTERM, SIGKILL, SIGHUP), commandes ps, kill et jobs."
    },
    {
        "id": "bash_scripting",
        "title": "Scripting Bash & Automatisation",
        "order": 6,
        "level": 3,
        "description": "Écriture de scripts shell Bash, shebang, variables, arguments positionnels, structures conditionnelles if/else et boucles."
    }
]

def build_challenges():
    challenges = []
    
    # -------------------------------------------------------------------------
    # CHAPITRE 1 : fhs_navigation (10 Easy + 5 Medium)
    # -------------------------------------------------------------------------
    # Easy 1-10
    challenges.append({
        "id": "lx_fhs_e01", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Afficher le Répertoire Courant (pwd)",
        "description": "Affichez le chemin absolu du répertoire de travail actuel avec la commande `pwd`.",
        "starter_cmd": "# Affichez votre répertoire courant\n",
        "solution": "pwd",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Vérification pwd", "cmd": "pwd", "assertion_type": "stdout_contains", "expected": "/home/student"}],
        "hidden_tests": [{"name": "Code de retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez la commande 'pwd' (Print Working Directory)."],
        "explanation": "La commande pwd renvoie le chemin absolu du répertoire dans lequel le shell se trouve actuellement."
    })
    challenges.append({
        "id": "lx_fhs_e02", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Lister les Fichiers Simples (ls)",
        "description": "Listez le contenu du répertoire courant en utilisant `ls`.",
        "starter_cmd": "# Listez le contenu\n",
        "solution": "ls",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"notes.txt": {"type": "file", "content": "Rappel Linux\n"}}}},
        "public_tests": [{"name": "Présence de notes.txt", "cmd": "ls", "assertion_type": "stdout_contains", "expected": "notes.txt"}],
        "hidden_tests": [{"name": "Code de retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["La commande de base pour lister les fichiers est 'ls'."],
        "explanation": "La commande ls affiche la liste des fichiers et répertoires visibles du dossier courant."
    })
    challenges.append({
        "id": "lx_fhs_e03", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Afficher les Fichiers Cachés (ls -a)",
        "description": "Affichez tous les fichiers du dossier courant, y compris les fichiers cachés (commençant par un point), avec `ls -a`.",
        "starter_cmd": "# Affichez les fichiers cachés\n",
        "solution": "ls -a",
        "initial_fs": {"/home/student": {"type": "dir", "files": {".bashrc": {"type": "file", "content": "# config\n"}, "main.py": {"type": "file", "content": "print('ok')\n"}}}},
        "public_tests": [{"name": "Détection .bashrc", "cmd": "ls -a", "assertion_type": "stdout_contains", "expected": ".bashrc"}],
        "hidden_tests": [{"name": "Détection main.py", "cmd": "ls -a", "assertion_type": "stdout_contains", "expected": "main.py"}],
        "hints": ["L'option '-a' (all) permet d'inclure les entrées commençant par '.'."],
        "explanation": "Sous Linux, un fichier commençant par un point est masqué par défaut. L'option -a force leur affichage."
    })
    challenges.append({
        "id": "lx_fhs_e04", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Format Long Détaillé (ls -l)",
        "description": "Affichez les fichiers du dossier courant avec leurs métadonnées détaillées (droits, taille, propriétaire) via `ls -l`.",
        "starter_cmd": "# Affichez le format long\n",
        "solution": "ls -l",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"rapport.pdf": {"type": "file", "content": "donnees\n"}}}},
        "public_tests": [{"name": "Affichage détaillé rapport.pdf", "cmd": "ls -l", "assertion_type": "stdout_contains", "expected": "rapport.pdf"}],
        "hidden_tests": [{"name": "Code de retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-l' (long listing) active le format détaillé."],
        "explanation": "L'option -l fournit les permissions, le nombre de liens, le propriétaire, le groupe, la taille et l'horodatage."
    })
    challenges.append({
        "id": "lx_fhs_e05", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Navigation vers la Racine (cd /)",
        "description": "Déplacez-vous à la racine du système de fichiers avec `cd /` puis affichez votre emplacement avec `pwd`.",
        "starter_cmd": "# Naviguez vers la racine et vérifiez\n",
        "solution": "cd / && pwd",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}, "/etc": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Vérification racine", "assertion_type": "stdout_contains", "expected": "/"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Enchaînez les commandes avec '&&' : 'cd / && pwd'."],
        "explanation": "Le slash '/' représente la racine absolue de l'arborescence UNIX FHS."
    })
    challenges.append({
        "id": "lx_fhs_e06", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Remonter au Répertoire Parent (cd ..)",
        "description": "Remontez d'un niveau dans l'arborescence en utilisant `cd ..` puis affichez le chemin avec `pwd`.",
        "starter_cmd": "# Remontez au parent\n",
        "solution": "cd .. && pwd",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Parent /home", "assertion_type": "stdout_contains", "expected": "/home"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["'..' désigne toujours le répertoire parent du dossier courant."],
        "explanation": "Le symbole '..' est le lien vers le répertoire parent direct."
    })
    challenges.append({
        "id": "lx_fhs_e07", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Exploration du Répertoire de Configuration (/etc)",
        "description": "Listez le contenu du répertoire système `/etc` sans changer de dossier, avec `ls /etc`.",
        "starter_cmd": "# Listez /etc\n",
        "solution": "ls /etc",
        "initial_fs": {"/etc": {"type": "dir", "files": {"hosts": {"type": "file", "content": "127.0.0.1 localhost\n"}, "passwd": {"type": "file", "content": "root:x:0:0::/root:/bin/bash\n"}}}},
        "public_tests": [{"name": "Fichiers hosts et passwd", "cmd": "ls /etc", "assertion_type": "stdout_contains", "expected": "hosts"}],
        "hidden_tests": [{"name": "Présence passwd", "cmd": "ls /etc", "assertion_type": "stdout_contains", "expected": "passwd"}],
        "hints": ["Passez le chemin absolu '/etc' en argument à 'ls'."],
        "explanation": "Le répertoire /etc contient les fichiers de configuration globaux du système d'exploitation."
    })
    challenges.append({
        "id": "lx_fhs_e08", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Retour au Dossier Personnel (cd ~)",
        "description": "Allez dans `/etc` puis retournez directement dans votre répertoire personnel avec `cd ~` ou `cd` seul, puis vérifiez avec `pwd`.",
        "starter_cmd": "# Allez dans /etc puis revenez au home\n",
        "solution": "cd /etc && cd ~ && pwd",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}, "/etc": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Emplacement final student", "assertion_type": "stdout_contains", "expected": "/home/student"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Le tilde '~' ou 'cd' sans argument ramène au HOME de l'utilisateur."],
        "explanation": "Le raccourci tilde '~' pointe sur la variable d'environnement $HOME."
    })
    challenges.append({
        "id": "lx_fhs_e09", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Inspection des Journaux (/var/log)",
        "description": "Listez les fichiers de journaux système présents dans `/var/log` avec `ls -l /var/log`.",
        "starter_cmd": "# Listez /var/log\n",
        "solution": "ls -l /var/log",
        "initial_fs": {"/var/log": {"type": "dir", "files": {"syslog": {"type": "file", "content": "kernel boot\n"}, "auth.log": {"type": "file", "content": "session open\n"}}}},
        "public_tests": [{"name": "Fichier syslog", "cmd": "ls -l /var/log", "assertion_type": "stdout_contains", "expected": "syslog"}],
        "hidden_tests": [{"name": "Fichier auth.log", "cmd": "ls -l /var/log", "assertion_type": "stdout_contains", "expected": "auth.log"}],
        "hints": ["Utilisez 'ls -l /var/log'."],
        "explanation": "/var/log regroupe les fichiers de journalisation et d'audit générés par les services."
    })
    challenges.append({
        "id": "lx_fhs_e10", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "easy", "points": 1.0,
        "title": "Dossier Temporaire (/tmp)",
        "description": "Vérifiez que le répertoire `/tmp` est accessible en listant son contenu complet avec `ls -la /tmp`.",
        "starter_cmd": "# Listez /tmp\n",
        "solution": "ls -la /tmp",
        "initial_fs": {"/tmp": {"type": "dir", "files": {".lock": {"type": "file", "content": "1\n"}}}},
        "public_tests": [{"name": "Présence .lock", "cmd": "ls -la /tmp", "assertion_type": "stdout_contains", "expected": ".lock"}],
        "hidden_tests": [{"name": "Code de retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Exécutez 'ls -la /tmp'."],
        "explanation": "/tmp est réservé aux fichiers éphémères accessibles à tous les utilisateurs."
    })
    # Medium 1-5
    challenges.append({
        "id": "lx_fhs_m01", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "medium", "points": 2.0,
        "title": "Navigation Relative Complexe",
        "description": "Depuis `/home/student/projects/web`, déplacez-vous dans `/home/student/data/raw` en utilisant uniquement un chemin relatif (avec `..`), puis affichez `pwd`.",
        "starter_cmd": "# Naviguez en relatif vers data/raw\n",
        "solution": "cd ../../data/raw && pwd",
        "initial_fs": {
            "/home/student": {
                "type": "dir",
                "files": {
                    "projects": {"type": "dir", "files": {"web": {"type": "dir", "files": {}}}},
                    "data": {"type": "dir", "files": {"raw": {"type": "dir", "files": {}}}}
                }
            }
        },
        "public_tests": [{"name": "Destination data/raw", "assertion_type": "stdout_contains", "expected": "/home/student/data/raw"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Chaque '..' remonte d'un dossier. Depuis projects/web, '..' mène à projects, puis à student."],
        "explanation": "Les chemins relatifs évitent les dépendances absolues et permettent une navigation portable."
    })
    challenges.append({
        "id": "lx_fhs_m02", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "medium", "points": 2.0,
        "title": "Tri Chronologique des Fichiers (ls -lt)",
        "description": "Listez les fichiers du dossier courant triés par date de modification décroissante (le plus récent en premier) avec `ls -lt`.",
        "starter_cmd": "# Listez avec tri par date\n",
        "solution": "ls -lt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"ancien.txt": {"type": "file", "content": "1\n"}, "recent.txt": {"type": "file", "content": "2\n"}}}},
        "public_tests": [{"name": "Affichage format long trié", "cmd": "ls -lt", "assertion_type": "stdout_contains", "expected": "recent.txt"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-t' trie par date de modification (mtime)."],
        "explanation": "ls -lt est essentiel en diagnostic pour identifier immédiatement les derniers fichiers modifiés."
    })
    challenges.append({
        "id": "lx_fhs_m03", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "medium", "points": 2.0,
        "title": "Exploration Récursive Complète (ls -R)",
        "description": "Affichez l'intégralité du contenu du dossier `workspace` et de tous ses sous-dossiers récursivement avec `ls -R workspace`.",
        "starter_cmd": "# Listez récursivement workspace\n",
        "solution": "ls -R workspace",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"workspace": {"type": "dir", "files": {"src": {"type": "dir", "files": {"app.js": {"type": "file", "content": "console.log('ok');\n"}}}}}}}},
        "public_tests": [{"name": "Détection app.js récursif", "cmd": "ls -R workspace", "assertion_type": "stdout_contains", "expected": "app.js"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-R' (majuscule) parcourt récursivement tous les sous-dossiers."],
        "explanation": "L'option -R permet de visualiser toute l'arborescence arborescente descendante."
    })
    challenges.append({
        "id": "lx_fhs_m04", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "medium", "points": 2.0,
        "title": "Identification des Binaires Système (/bin vs /sbin)",
        "description": "Vérifiez que `/bin` contient la commande `ls` et `/sbin` contient `fdisk` ou `ip` en exécutant `ls /bin/ls && ls /sbin`.",
        "starter_cmd": "# Vérifiez les dossiers de binaires\n",
        "solution": "ls /bin/ls && ls /sbin",
        "initial_fs": {"/bin": {"type": "dir", "files": {"ls": {"type": "file", "content": "ELF"}}}, "/sbin": {"type": "dir", "files": {"ip": {"type": "file", "content": "ELF"}}}},
        "public_tests": [{"name": "Binaire ls trouvé", "cmd": "ls /bin/ls", "assertion_type": "stdout_contains", "expected": "/bin/ls"}],
        "hidden_tests": [{"name": "Binaire ip trouvé", "cmd": "ls /sbin", "assertion_type": "stdout_contains", "expected": "ip"}],
        "hints": ["/bin contient les commandes pour tous les utilisateurs, /sbin celles d'administration système."],
        "explanation": "Selon FHS, /bin stocke les binaires essentiels, tandis que /sbin regroupe les utilitaires système réservés à root."
    })
    challenges.append({
        "id": "lx_fhs_m05", "chapter_id": "fhs_navigation", "level": 1, "topic": "Arborescence FHS & Navigation",
        "difficulty": "medium", "points": 2.0,
        "title": "Localisation et Inspection de /usr/share",
        "description": "Listez le contenu du dossier de données partagées `/usr/share` et affichez votre répertoire de retour.",
        "starter_cmd": "# Listez /usr/share\n",
        "solution": "ls /usr/share && pwd",
        "initial_fs": {"/usr/share": {"type": "dir", "files": {"doc": {"type": "dir", "files": {}}, "man": {"type": "dir", "files": {}}}}, "/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Dossier man trouvé", "cmd": "ls /usr/share", "assertion_type": "stdout_contains", "expected": "man"}],
        "hidden_tests": [{"name": "Retour home", "assertion_type": "stdout_contains", "expected": "/home/student"}],
        "hints": ["Exécutez 'ls /usr/share && pwd'."],
        "explanation": "/usr/share regroupe les données statiques et indépendantes de l'architecture (manuels, documentations)."
    })

    # -------------------------------------------------------------------------
    # CHAPITRE 2 : file_management (10 Easy + 5 Medium)
    # -------------------------------------------------------------------------
    # Easy 1-10
    challenges.append({
        "id": "lx_fm_e01", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Créer un Fichier Vide (touch)",
        "description": "Créez un nouveau fichier vide nommé `rapport.txt` dans votre répertoire courant.",
        "starter_cmd": "# Créez rapport.txt\n",
        "solution": "touch rapport.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Présence de rapport.txt", "assertion_type": "file_exists", "path": "/home/student/rapport.txt"}],
        "hidden_tests": [{"name": "Type fichier régulier", "assertion_type": "fs_exists", "path": "/home/student/rapport.txt"}],
        "hints": ["Utilisez la commande 'touch nom_du_fichier'."],
        "explanation": "La commande touch crée un fichier de 0 octet s'il n'existe pas, ou actualise son horodatage s'il existe."
    })
    challenges.append({
        "id": "lx_fm_e02", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Créer un Nouveau Dossier (mkdir)",
        "description": "Créez un nouveau répertoire nommé `sauvegardes` dans votre dossier courant.",
        "starter_cmd": "# Créez le dossier sauvegardes\n",
        "solution": "mkdir sauvegardes",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Dossier sauvegardes présent", "assertion_type": "file_exists", "path": "/home/student/sauvegardes"}],
        "hidden_tests": [{"name": "Code retour", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'mkdir sauvegardes'."],
        "explanation": "mkdir (Make Directory) alloue une nouvelle entrée de répertoire dans le système de fichiers."
    })
    challenges.append({
        "id": "lx_fm_e03", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Création d'Arborescence Imbriquée (mkdir -p)",
        "description": "Créez d'un seul coup l'arborescence complète `projets/cyber/audit` en utilisant l'option `-p`.",
        "starter_cmd": "# Créez l'arborescence imbriquée\n",
        "solution": "mkdir -p projets/cyber/audit",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Sous-dossier audit présent", "assertion_type": "file_exists", "path": "/home/student/projets/cyber/audit"}],
        "hidden_tests": [{"name": "Parent cyber présent", "assertion_type": "file_exists", "path": "/home/student/projets/cyber"}],
        "hints": ["L'option '-p' (parents) crée automatiquement tous les répertoires parents manquants."],
        "explanation": "mkdir -p ne génère pas d'erreur si le répertoire existe déjà et crée tous les maillons intermédiaires."
    })
    challenges.append({
        "id": "lx_fm_e04", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Copier un Fichier (cp)",
        "description": "Copiez le fichier `source.txt` vers un nouveau fichier nommé `copie.txt`.",
        "starter_cmd": "# Copiez source.txt\n",
        "solution": "cp source.txt copie.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"source.txt": {"type": "file", "content": "Contenu important\n"}}}},
        "public_tests": [{"name": "Fichier copie.txt existe", "assertion_type": "file_exists", "path": "/home/student/copie.txt"}],
        "hidden_tests": [{"name": "Contenu dupliqué", "assertion_type": "file_contains", "path": "/home/student/copie.txt", "expected": "Contenu important"}],
        "hints": ["Syntaxe : 'cp source destination'."],
        "explanation": "cp crée une réplique exacte du fichier source avec un nouvel inode indépendant."
    })
    challenges.append({
        "id": "lx_fm_e05", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Renommer un Fichier (mv)",
        "description": "Renommez le fichier `draft.txt` en `final.txt`.",
        "starter_cmd": "# Renommez draft.txt\n",
        "solution": "mv draft.txt final.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"draft.txt": {"type": "file", "content": "Version 1\n"}}}},
        "public_tests": [{"name": "Présence de final.txt", "assertion_type": "file_exists", "path": "/home/student/final.txt"}],
        "hidden_tests": [{"name": "Suppression de draft.txt", "assertion_type": "file_not_exists", "path": "/home/student/draft.txt"}],
        "hints": ["La commande 'mv' sert à la fois à renommer et à déplacer."],
        "explanation": "Sous Linux, le renommage est simplement un déplacement dans le même répertoire avec un nouveau nom."
    })
    challenges.append({
        "id": "lx_fm_e06", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Déplacer un Fichier dans un Dossier (mv)",
        "description": "Déplacez le fichier `photo.jpg` dans le répertoire `images/` existant.",
        "starter_cmd": "# Déplacez photo.jpg dans images/\n",
        "solution": "mv photo.jpg images/",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"photo.jpg": {"type": "file", "content": "JPEG_DATA\n"}, "images": {"type": "dir", "files": {}}}}},
        "public_tests": [{"name": "photo.jpg dans images/", "assertion_type": "file_exists", "path": "/home/student/images/photo.jpg"}],
        "hidden_tests": [{"name": "photo.jpg absent de la racine student", "assertion_type": "file_not_exists", "path": "/home/student/photo.jpg"}],
        "hints": ["Utilisez 'mv photo.jpg images/'."],
        "explanation": "Lorsque la destination de mv est un dossier existant, le fichier y est transféré sans changer de nom."
    })
    challenges.append({
        "id": "lx_fm_e07", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Supprimer un Fichier (rm)",
        "description": "Supprimez définitivement le fichier temporaire `temp.log` avec la commande `rm`.",
        "starter_cmd": "# Supprimez temp.log\n",
        "solution": "rm temp.log",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"temp.log": {"type": "file", "content": "debug logs\n"}}}},
        "public_tests": [{"name": "temp.log supprimé", "assertion_type": "file_not_exists", "path": "/home/student/temp.log"}],
        "hidden_tests": [{"name": "Code de retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'rm temp.log'."],
        "explanation": "rm (remove) dissocie le fichier du système de fichiers. Attention, il n'y a pas de corbeille par défaut !"
    })
    challenges.append({
        "id": "lx_fm_e08", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Supprimer un Répertoire Vide (rmdir)",
        "description": "Supprimez le répertoire vide nommé `ancien_dossier` avec `rmdir`.",
        "starter_cmd": "# Supprimez ancien_dossier\n",
        "solution": "rmdir ancien_dossier",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"ancien_dossier": {"type": "dir", "files": {}}}}},
        "public_tests": [{"name": "ancien_dossier supprimé", "assertion_type": "file_not_exists", "path": "/home/student/ancien_dossier"}],
        "hidden_tests": [{"name": "Code de retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'rmdir ancien_dossier'."],
        "explanation": "rmdir supprime un dossier uniquement s'il ne contient aucun fichier ni sous-dossier."
    })
    challenges.append({
        "id": "lx_fm_e09", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Copier Récursivement un Répertoire (cp -r)",
        "description": "Copiez l'intégralité du dossier `templates` et son contenu vers `templates_backup`.",
        "starter_cmd": "# Copiez récursivement templates\n",
        "solution": "cp -r templates templates_backup",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"templates": {"type": "dir", "files": {"index.html": {"type": "file", "content": "<h1>Hello</h1>\n"}}}}}},
        "public_tests": [{"name": "templates_backup créé", "assertion_type": "file_exists", "path": "/home/student/templates_backup"}],
        "hidden_tests": [{"name": "index.html dupliqué", "assertion_type": "file_exists", "path": "/home/student/templates_backup/index.html"}],
        "hints": ["L'option '-r' ou '-R' (recursive) est obligatoire pour copier un dossier avec cp."],
        "explanation": "Sans -r, cp ignore les répertoires et affiche un message d'erreur."
    })
    challenges.append({
        "id": "lx_fm_e10", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "easy", "points": 1.0,
        "title": "Supprimer un Répertoire et son Contenu (rm -r)",
        "description": "Supprimez le dossier `cache/` et tout son contenu récursivement en utilisant `rm -r cache`.",
        "starter_cmd": "# Supprimez le dossier cache et son contenu\n",
        "solution": "rm -r cache",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"cache": {"type": "dir", "files": {"data.bin": {"type": "file", "content": "0101\n"}}}}}},
        "public_tests": [{"name": "Dossier cache supprimé", "assertion_type": "file_not_exists", "path": "/home/student/cache"}],
        "hidden_tests": [{"name": "Fichier data.bin supprimé", "assertion_type": "file_not_exists", "path": "/home/student/cache/data.bin"}],
        "hints": ["Utilisez 'rm -r cache'."],
        "explanation": "L'option -r parcourt et supprime l'ensemble des éléments de l'arborescence descendante."
    })
    # Medium 1-5
    challenges.append({
        "id": "lx_fm_m01", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "medium", "points": 2.0,
        "title": "Déplacement Multiple avec Joker (*.log)",
        "description": "Déplacez tous les fichiers se terminant par `.log` dans le répertoire `archives/`.",
        "starter_cmd": "# Déplacez tous les .log dans archives/\n",
        "solution": "mv *.log archives/",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"a.log": {"type": "file", "content": "1\n"}, "b.log": {"type": "file", "content": "2\n"}, "notes.txt": {"type": "file", "content": "keep\n"}, "archives": {"type": "dir", "files": {}}}}},
        "public_tests": [{"name": "a.log archivé", "assertion_type": "file_exists", "path": "/home/student/archives/a.log"}],
        "hidden_tests": [{"name": "notes.txt préservé", "assertion_type": "file_exists", "path": "/home/student/notes.txt"}],
        "hints": ["Le métacaractère '*' remplace n'importe quelle chaîne de caractères : 'mv *.log archives/'."],
        "explanation": "Le shell développe le joker (globbing) avant de passer la liste des fichiers à la commande mv."
    })
    challenges.append({
        "id": "lx_fm_m02", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "medium", "points": 2.0,
        "title": "Sauvegarde et Nettoyage Sécurisé",
        "description": "Faites une copie de sauvegarde de `config.ini` sous le nom `config.ini.bak`, puis supprimez l'original `config.ini`.",
        "starter_cmd": "# Sauvegardez puis supprimez l'original\n",
        "solution": "cp config.ini config.ini.bak && rm config.ini",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"config.ini": {"type": "file", "content": "port=8080\n"}}}},
        "public_tests": [{"name": "config.ini.bak présent", "assertion_type": "file_exists", "path": "/home/student/config.ini.bak"}],
        "hidden_tests": [{"name": "config.ini original supprimé", "assertion_type": "file_not_exists", "path": "/home/student/config.ini"}],
        "hints": ["Enchaînez avec '&&' : 'cp config.ini config.ini.bak && rm config.ini'."],
        "explanation": "La duplication suivie de suppression garantit que l'opération ne réussit que si la sauvegarde est créée."
    })
    challenges.append({
        "id": "lx_fm_m03", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "medium", "points": 2.0,
        "title": "Création d'Architecture Projet Complète",
        "description": "Créez l'arborescence `app/src`, `app/tests` et `app/docs`, puis créez un fichier vide `app/src/index.js`.",
        "starter_cmd": "# Créez les dossiers et le fichier index.js\n",
        "solution": "mkdir -p app/src app/tests app/docs && touch app/src/index.js",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "app/src/index.js existe", "assertion_type": "file_exists", "path": "/home/student/app/src/index.js"}],
        "hidden_tests": [{"name": "app/tests existe", "assertion_type": "file_exists", "path": "/home/student/app/tests"}],
        "hints": ["'mkdir -p' peut prendre plusieurs dossiers cibles en argument."],
        "explanation": "mkdir -p permet d'initialiser rapidement un squelette de projet complet."
    })
    challenges.append({
        "id": "lx_fm_m04", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "medium", "points": 2.0,
        "title": "Copie avec Préservation des Attributs (cp -p)",
        "description": "Copiez le fichier sensible `cert.pem` vers `/tmp/cert_backup.pem`.",
        "starter_cmd": "# Copiez vers /tmp/\n",
        "solution": "cp cert.pem /tmp/cert_backup.pem",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"cert.pem": {"type": "file", "content": "CERTIFICATE_DATA\n"}}}, "/tmp": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "cert_backup.pem dans /tmp", "assertion_type": "file_exists", "path": "/tmp/cert_backup.pem"}],
        "hidden_tests": [{"name": "Contenu certificat intègre", "assertion_type": "file_contains", "path": "/tmp/cert_backup.pem", "expected": "CERTIFICATE_DATA"}],
        "hints": ["Spécifiez le chemin absolu de destination : '/tmp/cert_backup.pem'."],
        "explanation": "La copie inter-répertoires système permet de transférer des configurations vers des zones d'échange."
    })
    challenges.append({
        "id": "lx_fm_m05", "chapter_id": "file_management", "level": 1, "topic": "Manipulation de Fichiers",
        "difficulty": "medium", "points": 2.0,
        "title": "Nettoyage Sélectif de Fichiers Temporaires",
        "description": "Dans le dossier `workspace`, supprimez tous les fichiers `.tmp` sans toucher aux fichiers `.py` ni au sous-dossier `src`.",
        "starter_cmd": "# Supprimez les fichiers .tmp dans workspace\n",
        "solution": "rm workspace/*.tmp",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"workspace": {"type": "dir", "files": {"1.tmp": {"type": "file", "content": "a"}, "2.tmp": {"type": "file", "content": "b"}, "main.py": {"type": "file", "content": "pass\n"}, "src": {"type": "dir", "files": {}}}}}}},
        "public_tests": [{"name": "main.py conservé", "assertion_type": "file_exists", "path": "/home/student/workspace/main.py"}],
        "hidden_tests": [{"name": "1.tmp supprimé", "assertion_type": "file_not_exists", "path": "/home/student/workspace/1.tmp"}],
        "hints": ["Utilisez 'rm workspace/*.tmp'."],
        "explanation": "L'utilisation de jokers ciblés évite la suppression accidentelle de code source précieux."
    })

    # -------------------------------------------------------------------------
    # CHAPITRE 3 : permissions_security (10 Easy + 5 Medium)
    # -------------------------------------------------------------------------
    # Easy 1-10
    challenges.append({
        "id": "lx_perm_e01", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Ajouter le Droit d'Exécution (chmod +x)",
        "description": "Rendez le script `deploy.sh` exécutable en lui attribuant le bit d'exécution avec `chmod +x deploy.sh`.",
        "starter_cmd": "# Rendez deploy.sh exécutable\n",
        "solution": "chmod +x deploy.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"deploy.sh": {"type": "file", "content": "#!/bin/bash\necho ok\n", "mode": 420}}}}, # 644
        "public_tests": [{"name": "Droits exécutables attribués", "assertion_type": "mode", "path": "/home/student/deploy.sh", "expected": 493}], # 755
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'chmod +x deploy.sh'."],
        "explanation": "chmod +x ajoute la permission d'exécution (bit x) au propriétaire, groupe et autres."
    })
    challenges.append({
        "id": "lx_perm_e02", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Permissions Standard Fichier (chmod 644)",
        "description": "Appliquez les permissions octales `644` (rw-r--r--) sur le fichier `document.txt`.",
        "starter_cmd": "# Appliquez 644 sur document.txt\n",
        "solution": "chmod 644 document.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"document.txt": {"type": "file", "content": "texte\n", "mode": 511}}}}, # 777
        "public_tests": [{"name": "Mode 644 appliqué", "assertion_type": "mode", "path": "/home/student/document.txt", "expected": 420}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["6 = rw (4+2), 4 = r."],
        "explanation": "644 est la permission recommandée pour les fichiers publics ou partagés en lecture seule."
    })
    challenges.append({
        "id": "lx_perm_e03", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Sécurisation Clé Privée SSH (chmod 600)",
        "description": "Sécurisez la clé privée SSH `id_rsa` en lui appliquant la permission stricte `600` (lecture/écriture propriétaire seul).",
        "starter_cmd": "# Sécurisez la clé id_rsa en 600\n",
        "solution": "chmod 600 id_rsa",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"id_rsa": {"type": "file", "content": "-----BEGIN OPENSSH PRIVATE KEY-----\n", "mode": 436}}}}, # 664
        "public_tests": [{"name": "Mode 600 strict", "assertion_type": "mode", "path": "/home/student/id_rsa", "expected": 384}], # 600
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["600 signifie propriétaire rw, groupe aucun droit, autres aucun droit."],
        "explanation": "SSH refuse impérativement de charger une clé privée si ses permissions dépassent 600."
    })
    challenges.append({
        "id": "lx_perm_e04", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Script Exécutable Standard (chmod 755)",
        "description": "Appliquez le mode octal `755` (rwxr-xr-x) sur le script d'automatisation `backup.sh`.",
        "starter_cmd": "# Appliquez 755 sur backup.sh\n",
        "solution": "chmod 755 backup.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"backup.sh": {"type": "file", "content": "#!/bin/bash\n", "mode": 420}}}},
        "public_tests": [{"name": "Mode 755 vérifié", "assertion_type": "mode", "path": "/home/student/backup.sh", "expected": 493}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["7 = rwx (4+2+1), 5 = r-x (4+1)."],
        "explanation": "755 permet à tout le monde d'exécuter le script, mais seul le propriétaire peut le modifier."
    })
    challenges.append({
        "id": "lx_perm_e05", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Retirer les Droits d'Écriture (chmod -w)",
        "description": "Protégez le fichier `licence.txt` contre toute modification accidentelle en retirant le droit d'écriture avec `chmod -w licence.txt`.",
        "starter_cmd": "# Retirez le droit d'écriture\n",
        "solution": "chmod -w licence.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"licence.txt": {"type": "file", "content": "GPLv3\n", "mode": 420}}}}, # 644
        "public_tests": [{"name": "Écriture retirée (444)", "assertion_type": "mode", "path": "/home/student/licence.txt", "expected": 292}], # 444
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'chmod -w licence.txt' ou 'chmod a-w licence.txt'."],
        "explanation": "Le retrait de l'attribut w empêche l'écrasement ou l'édition involontaire du fichier."
    })
    challenges.append({
        "id": "lx_perm_e06", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Dossier Privé Strict (chmod 700)",
        "description": "Verrouillez le dossier `confidentiel` afin que seul son propriétaire puisse y accéder (`chmod 700 confidentiel`).",
        "starter_cmd": "# Verrouillez confidentiel en 700\n",
        "solution": "chmod 700 confidentiel",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"confidentiel": {"type": "dir", "files": {}, "mode": 493}}}}, # 755
        "public_tests": [{"name": "Dossier en 700", "assertion_type": "mode", "path": "/home/student/confidentiel", "expected": 448}], # 700
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["700 coupe tout accès (lecture, écriture, traversée) pour les autres utilisateurs."],
        "explanation": "Pour un dossier, le bit 'x' est nécessaire pour le traverser (cd) et 'r' pour lister son contenu."
    })
    challenges.append({
        "id": "lx_perm_e07", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Fichier de Configuration Restreint (chmod 640)",
        "description": "Appliquez le mode `640` (rw-r-----) sur le fichier d'environnement `.env`.",
        "starter_cmd": "# Appliquez 640 sur .env\n",
        "solution": "chmod 640 .env",
        "initial_fs": {"/home/student": {"type": "dir", "files": {".env": {"type": "file", "content": "SECRET_KEY=123\n", "mode": 420}}}},
        "public_tests": [{"name": "Mode 640 sur .env", "assertion_type": "mode", "path": "/home/student/.env", "expected": 416}], # 640
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["6 (propriétaire), 4 (groupe), 0 (autres)."],
        "explanation": "640 permet à l'équipe (groupe) de lire la configuration sans l'exposer au reste du système."
    })
    challenges.append({
        "id": "lx_perm_e08", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Fichier en Lecture Seule Stricte (chmod 400)",
        "description": "Passez la clé d'API `api.key` en lecture seule pour son propriétaire uniquement (`chmod 400 api.key`).",
        "starter_cmd": "# Appliquez 400 sur api.key\n",
        "solution": "chmod 400 api.key",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"api.key": {"type": "file", "content": "KEY_XYZ\n", "mode": 384}}}},
        "public_tests": [{"name": "Mode 400 appliqué", "assertion_type": "mode", "path": "/home/student/api.key", "expected": 256}], # 400
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["4 = lecture seule (r--)."],
        "explanation": "400 est le mode d'isolation maximale en lecture pour des fichiers sensibles non modifiables."
    })
    challenges.append({
        "id": "lx_perm_e09", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Attribution Symbolique Précise (chmod u=rw,go=r)",
        "description": "Définissez les droits de `rapport.txt` en utilisant la notation symbolique `chmod u=rw,go=r rapport.txt`.",
        "starter_cmd": "# Appliquez la notation symbolique\n",
        "solution": "chmod u=rw,go=r rapport.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"rapport.txt": {"type": "file", "content": "rapport\n", "mode": 511}}}},
        "public_tests": [{"name": "Mode 644 obtenu", "assertion_type": "mode", "path": "/home/student/rapport.txt", "expected": 420}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["u=user, g=group, o=others."],
        "explanation": "La notation symbolique permet d'exprimer les permissions de manière explicite et lisible."
    })
    challenges.append({
        "id": "lx_perm_e10", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "easy", "points": 1.0,
        "title": "Changer le Propriétaire Simulé (chown)",
        "description": "Changez le propriétaire du fichier `service.log` pour l'attribuer à l'utilisateur `student` avec `chown student service.log`.",
        "starter_cmd": "# Attribuez service.log à student\n",
        "solution": "chown student service.log",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"service.log": {"type": "file", "content": "logs\n", "owner": "root"}}}},
        "public_tests": [{"name": "Propriétaire student", "assertion_type": "owner", "path": "/home/student/service.log", "expected": "student"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'chown student service.log'."],
        "explanation": "chown (Change Owner) modifie l'UID propriétaire d'un fichier."
    })
    # Medium 1-5
    challenges.append({
        "id": "lx_perm_m01", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "medium", "points": 2.0,
        "title": "Application Récursive de Permissions (chmod -R)",
        "description": "Appliquez les permissions `750` à l'ensemble du dossier `projet_web` et de ses sous-éléments de manière récursive.",
        "starter_cmd": "# Appliquez récursivement 750\n",
        "solution": "chmod -R 750 projet_web",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"projet_web": {"type": "dir", "files": {"app.py": {"type": "file", "content": "pass\n", "mode": 511}}, "mode": 511}}}},
        "public_tests": [{"name": "Dossier projet_web en 750", "assertion_type": "mode", "path": "/home/student/projet_web", "expected": 488}], # 750
        "hidden_tests": [{"name": "Fichier app.py en 750", "assertion_type": "mode", "path": "/home/student/projet_web/app.py", "expected": 488}],
        "hints": ["L'option '-R' applique le changement à tout le contenu de l'arbre."],
        "explanation": "chmod -R modifie uniformément les permissions de tous les nœuds de l'arborescence."
    })
    challenges.append({
        "id": "lx_perm_m02", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "medium", "points": 2.0,
        "title": "Sécurisation Complète d'un Répertoire SSH (.ssh)",
        "description": "Appliquez les permissions requises par les standards de sécurité : le dossier `.ssh` doit être en `700` et le fichier `.ssh/authorized_keys` en `600`.",
        "starter_cmd": "# Sécurisez .ssh (700) et authorized_keys (600)\n",
        "solution": "chmod 700 .ssh && chmod 600 .ssh/authorized_keys",
        "initial_fs": {"/home/student": {"type": "dir", "files": {".ssh": {"type": "dir", "files": {"authorized_keys": {"type": "file", "content": "ssh-ed25519 AAA\n", "mode": 436}}, "mode": 493}}}},
        "public_tests": [{"name": ".ssh en 700", "assertion_type": "mode", "path": "/home/student/.ssh", "expected": 448}],
        "hidden_tests": [{"name": "authorized_keys en 600", "assertion_type": "mode", "path": "/home/student/.ssh/authorized_keys", "expected": 384}],
        "hints": ["Enchaînez avec '&&' : 'chmod 700 .ssh && chmod 600 .ssh/authorized_keys'."],
        "explanation": "OpenSSH rejette toute authentification si les clés publiques ou dossiers sont accessibles aux tiers."
    })
    challenges.append({
        "id": "lx_perm_m03", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "medium", "points": 2.0,
        "title": "Changement Simultané Propriétaire et Groupe (chown user:group)",
        "description": "Attribuez le fichier `serveur.conf` à l'utilisateur `student` et au groupe `developers` avec `chown student:developers serveur.conf`.",
        "starter_cmd": "# Changez propriétaire et groupe\n",
        "solution": "chown student:developers serveur.conf",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"serveur.conf": {"type": "file", "content": "port=80\n", "owner": "root", "group": "root"}}}},
        "public_tests": [{"name": "Propriétaire student", "assertion_type": "owner", "path": "/home/student/serveur.conf", "expected": "student"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Syntaxe : 'chown utilisateur:groupe fichier'."],
        "explanation": "Le séparateur deux-points permet d'ajuster l'utilisateur et le groupe en une seule opération atomique."
    })
    challenges.append({
        "id": "lx_perm_m04", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "medium", "points": 2.0,
        "title": "Audit et Correction de Droits Trop Permissifs",
        "description": "Le script `launch.sh` a été mal configuré en `777`. Corrigez-le en lui attribuant des permissions de sécurité professionnelles `750`.",
        "starter_cmd": "# Corrigez le 777 en 750\n",
        "solution": "chmod 750 launch.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"launch.sh": {"type": "file", "content": "#!/bin/bash\n", "mode": 511}}}}, # 777
        "public_tests": [{"name": "Mode 750 sécurisé", "assertion_type": "mode", "path": "/home/student/launch.sh", "expected": 488}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["777 donne tous les droits à n'importe quel attaquant. 750 supprime les droits aux tiers."],
        "explanation": "Le mode 777 est une faille critique courante en audit de cybersécurité."
    })
    challenges.append({
        "id": "lx_perm_m05", "chapter_id": "permissions_security", "level": 2, "topic": "Permissions & Droits d'Accès",
        "difficulty": "medium", "points": 2.0,
        "title": "Sécurisation d'un Dossier Web (/var/www)",
        "description": "Configurez le répertoire `/var/www/site` avec les permissions `755` pour permettre la lecture web sans permettre la modification aux tiers.",
        "starter_cmd": "# Appliquez 755 sur /var/www/site\n",
        "solution": "chmod 755 /var/www/site",
        "initial_fs": {"/var/www": {"type": "dir", "files": {"site": {"type": "dir", "files": {"index.html": {"type": "file", "content": "Bienvenue"}}, "mode": 511}}}},
        "public_tests": [{"name": "Mode 755 sur site", "assertion_type": "mode", "path": "/var/www/site", "expected": 493}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["755 sur les dossiers web permet aux démons HTTP (nginx/apache) de traverser et servir les fichiers."],
        "explanation": "Un serveur web a besoin de 'r-x' sur les répertoires pour parcourir et distribuer les pages."
    })

    # -------------------------------------------------------------------------
    # CHAPITRE 4 : text_processing_pipes (10 Easy + 5 Medium)
    # -------------------------------------------------------------------------
    # Easy 1-10
    challenges.append({
        "id": "lx_txt_e01", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Afficher le Contenu d'un Fichier (cat)",
        "description": "Affichez l'intégralité du contenu du fichier `message.txt` sur la sortie standard avec `cat`.",
        "starter_cmd": "# Affichez message.txt\n",
        "solution": "cat message.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"message.txt": {"type": "file", "content": "Formation Linux 2026\n"}}}},
        "public_tests": [{"name": "Contenu affiché", "assertion_type": "stdout_contains", "expected": "Formation Linux 2026"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'cat message.txt'."],
        "explanation": "cat concatène et affiche les fichiers séquentiellement sur stdout."
    })
    challenges.append({
        "id": "lx_txt_e02", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Redirection Simple vers un Fichier (>)",
        "description": "Écrivez le texte `Active` dans un nouveau fichier nommé `status.txt` en utilisant l'opérateur de redirection `>`.",
        "starter_cmd": "# Écrivez 'Active' dans status.txt\n",
        "solution": "echo 'Active' > status.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Fichier status.txt créé", "assertion_type": "file_exists", "path": "/home/student/status.txt"}],
        "hidden_tests": [{"name": "Contenu 'Active' présent", "assertion_type": "file_contains", "path": "/home/student/status.txt", "expected": "Active"}],
        "hints": ["Syntaxe : echo 'Active' > status.txt."],
        "explanation": "L'opérateur '>' redirige la sortie standard et écrase le fichier cible s'il existait."
    })
    challenges.append({
        "id": "lx_txt_e03", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Ajout à la Fin d'un Fichier (>>)",
        "description": "Ajoutez la ligne `Fin du log` à la fin du fichier existant `journal.log` sans effacer son contenu existant.",
        "starter_cmd": "# Ajoutez 'Fin du log' à la fin de journal.log\n",
        "solution": "echo 'Fin du log' >> journal.log",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"journal.log": {"type": "file", "content": "Debut du log\n"}}}},
        "public_tests": [{"name": "Ligne ajoutée", "assertion_type": "file_contains", "path": "/home/student/journal.log", "expected": "Fin du log"}],
        "hidden_tests": [{"name": "Ligne de début conservée", "assertion_type": "file_contains", "path": "/home/student/journal.log", "expected": "Debut du log"}],
        "hints": ["L'opérateur '>>' (append) ajoute les données sans écraser le fichier."],
        "explanation": ">> ouvre le fichier en mode ajout (O_APPEND), plaçant le curseur à la fin."
    })
    challenges.append({
        "id": "lx_txt_e04", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Afficher les Premières Lignes (head)",
        "description": "Affichez les 3 premières lignes du fichier `clients.csv` avec la commande `head -n 3 clients.csv`.",
        "starter_cmd": "# Affichez les 3 premières lignes\n",
        "solution": "head -n 3 clients.csv",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"clients.csv": {"type": "file", "content": "id,nom\n1,Alice\n2,Bob\n3,Charlie\n4,David\n"}}}},
        "public_tests": [{"name": "En-tête et Bob affichés", "assertion_type": "stdout_contains", "expected": "Bob"}],
        "hidden_tests": [{"name": "David non affiché", "assertion_type": "stdout_exact", "expected": "id,nom\n1,Alice\n2,Bob"}],
        "hints": ["head -n N sélectionne les N premières lignes."],
        "explanation": "head est particulièrement utile pour inspecter rapidement l'en-tête d'un fichier volumineux."
    })
    challenges.append({
        "id": "lx_txt_e05", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Afficher les Dernières Lignes (tail)",
        "description": "Affichez les 2 dernières lignes du fichier `erreurs.log` en utilisant `tail -n 2 erreurs.log`.",
        "starter_cmd": "# Affichez les 2 dernières lignes\n",
        "solution": "tail -n 2 erreurs.log",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"erreurs.log": {"type": "file", "content": "Ligne 1\nLigne 2\nLigne 3\nLigne 4\n"}}}},
        "public_tests": [{"name": "Ligne 4 présente", "assertion_type": "stdout_contains", "expected": "Ligne 4"}],
        "hidden_tests": [{"name": "Ligne 3 présente", "assertion_type": "stdout_contains", "expected": "Ligne 3"}],
        "hints": ["tail -n N sélectionne les N dernières lignes."],
        "explanation": "tail est la commande standard pour surveiller la fin des journaux d'activité."
    })
    challenges.append({
        "id": "lx_txt_e06", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Compter les Lignes d'un Fichier (wc -l)",
        "description": "Comptez le nombre de lignes présentes dans le fichier `donnees.txt` en utilisant `wc -l donnees.txt`.",
        "starter_cmd": "# Comptez les lignes de donnees.txt\n",
        "solution": "wc -l donnees.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"donnees.txt": {"type": "file", "content": "un\ndeux\ntrois\nquatre\ncinq\n"}}}},
        "public_tests": [{"name": "Résultat 5", "assertion_type": "stdout_contains", "expected": "5"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["wc -l (Word Count Lines) compte les sauts de ligne."],
        "explanation": "wc -l compte le nombre de retours chariot (\\n) dans le flux d'entrée."
    })
    challenges.append({
        "id": "lx_txt_e07", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Recherche Simple de Texte (grep)",
        "description": "Affichez toutes les lignes contenant le mot `CRITICAL` dans le fichier `syslog.txt`.",
        "starter_cmd": "# Recherchez CRITICAL dans syslog.txt\n",
        "solution": "grep CRITICAL syslog.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"syslog.txt": {"type": "file", "content": "INFO ok\nCRITICAL disk full\nINFO done\nCRITICAL db down\n"}}}},
        "public_tests": [{"name": "Ligne disk full", "assertion_type": "stdout_contains", "expected": "CRITICAL disk full"}],
        "hidden_tests": [{"name": "Ligne db down", "assertion_type": "stdout_contains", "expected": "CRITICAL db down"}],
        "hints": ["grep 'MOT_CLE' fichier.txt filtre les lignes correspondantes."],
        "explanation": "grep (Global Regular Expression Print) filtre et affiche les lignes satisfaisant un motif."
    })
    challenges.append({
        "id": "lx_txt_e08", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Recherche Insensible à la Casse (grep -i)",
        "description": "Recherchez le mot `admin` (en majuscules ou minuscules) dans `users.txt` avec `grep -i admin users.txt`.",
        "starter_cmd": "# Recherchez admin sans tenir compte de la casse\n",
        "solution": "grep -i admin users.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"users.txt": {"type": "file", "content": "Admin:1000\nuser1:1001\nADMIN_SYS:1002\n"}}}},
        "public_tests": [{"name": "Admin trouvé", "assertion_type": "stdout_contains", "expected": "Admin:1000"}],
        "hidden_tests": [{"name": "ADMIN_SYS trouvé", "assertion_type": "stdout_contains", "expected": "ADMIN_SYS"}],
        "hints": ["L'option '-i' ignore la casse (insensible majuscules/minuscules)."],
        "explanation": "grep -i traite indifféremment minuscules et majuscules pour le filtrage."
    })
    challenges.append({
        "id": "lx_txt_e09", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Trier un Fichier par Ordre Alphabétique (sort)",
        "description": "Affichez les lignes du fichier `noms.txt` triées par ordre alphabétique en utilisant `sort noms.txt`.",
        "starter_cmd": "# Triez noms.txt\n",
        "solution": "sort noms.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"noms.txt": {"type": "file", "content": "Zoé\nAlice\nMarc\n"}}}},
        "public_tests": [{"name": "Alice en tête", "assertion_type": "stdout_contains", "expected": "Alice"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["La commande 'sort fichier' trie les lignes dans l'ordre ASCII/alphabétique."],
        "explanation": "sort organise les lignes selon l'ordre lexicographique défini par la locale."
    })
    challenges.append({
        "id": "lx_txt_e10", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "easy", "points": 1.0,
        "title": "Supprimer les Doublons Consécutifs (uniq)",
        "description": "Affichez les lignes uniques du fichier trié `adresses.txt` avec la commande `uniq adresses.txt`.",
        "starter_cmd": "# Affichez les lignes uniques\n",
        "solution": "uniq adresses.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"adresses.txt": {"type": "file", "content": "Paris\nParis\nLyon\nLyon\nNice\n"}}}},
        "public_tests": [{"name": "Paris unique", "assertion_type": "stdout_contains", "expected": "Paris"}],
        "hidden_tests": [{"name": "Lyon et Nice présents", "assertion_type": "stdout_contains", "expected": "Nice"}],
        "hints": ["uniq élimine les lignes adjacentes identiques."],
        "explanation": "uniq requiert généralement que le flux ait été préalablement trié par sort."
    })
    # Medium 1-5
    challenges.append({
        "id": "lx_txt_m01", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "medium", "points": 2.0,
        "title": "Compter les Occurrences avec un Tube (| wc -l)",
        "description": "En combinant `grep` et `wc -l` via un tube `|`, comptez combien de lignes contiennent le mot `ERROR` dans `app.log`.",
        "starter_cmd": "# Comptez les lignes contenant ERROR via un pipeline\n",
        "solution": "grep ERROR app.log | wc -l",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"app.log": {"type": "file", "content": "INFO ok\nERROR timeout\nINFO ready\nERROR connect\nERROR crash\n"}}}},
        "public_tests": [{"name": "Exactement 3 erreurs", "assertion_type": "stdout_contains", "expected": "3"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Connectez la sortie de grep à l'entrée de wc avec le tube '|' : 'grep ERROR app.log | wc -l'."],
        "explanation": "Le tube '|' redirige le stdout de la commande de gauche vers le stdin de celle de droite."
    })
    challenges.append({
        "id": "lx_txt_m02", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "medium", "points": 2.0,
        "title": "Classement par Fréquence (sort | uniq -c | sort -nr)",
        "description": "Analysez `ips.txt` pour afficher chaque adresse IP avec son nombre d'occurrences trié du plus fréquent au moins fréquent.",
        "starter_cmd": "# Triez et comptez les fréquences d'IPs\n",
        "solution": "sort ips.txt | uniq -c | sort -nr",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"ips.txt": {"type": "file", "content": "10.0.0.1\n10.0.0.2\n10.0.0.1\n10.0.0.1\n10.0.0.2\n"}}}},
        "public_tests": [{"name": "3 pour 10.0.0.1", "assertion_type": "stdout_contains", "expected": "3 10.0.0.1"}],
        "hidden_tests": [{"name": "2 pour 10.0.0.2", "assertion_type": "stdout_contains", "expected": "2 10.0.0.2"}],
        "hints": ["Le pipeline classique est : sort | uniq -c | sort -nr."],
        "explanation": "C'est l'idiome UNIX le plus célèbre pour produire un histogramme de fréquence textuel."
    })
    challenges.append({
        "id": "lx_txt_m03", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "medium", "points": 2.0,
        "title": "Extraction de Champs Délimités (cut -d)",
        "description": "Extrayez uniquement le premier champ (les noms d'utilisateurs) du fichier délimité par des deux-points `passwd_sample` avec `cut -d: -f1 passwd_sample`.",
        "starter_cmd": "# Extrayez la première colonne avec cut\n",
        "solution": "cut -d: -f1 passwd_sample",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"passwd_sample": {"type": "file", "content": "root:x:0:0::/root:/bin/bash\nstudent:x:1000:1000::/home/student:/bin/bash\n"}}}},
        "public_tests": [{"name": "Noms d'utilisateurs extraits", "assertion_type": "stdout_contains", "expected": "student"}],
        "hidden_tests": [{"name": "root extrait", "assertion_type": "stdout_contains", "expected": "root"}],
        "hints": ["-d: spécifie le délimiteur deux-points, -f1 sélectionne la première colonne."],
        "explanation": "cut permet de découper efficacement des fichiers tabulaires délimités comme /etc/passwd ou CSV."
    })
    challenges.append({
        "id": "lx_txt_m04", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "medium", "points": 2.0,
        "title": "Inversion de Filtrage (grep -v)",
        "description": "Filtrez `serveurs.txt` pour afficher toutes les lignes SAUF celles contenant le mot `DOWN` en utilisant `grep -v DOWN serveurs.txt`.",
        "starter_cmd": "# Affichez les serveurs qui ne sont pas DOWN\n",
        "solution": "grep -v DOWN serveurs.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"serveurs.txt": {"type": "file", "content": "srv1 UP\nsrv2 DOWN\nsrv3 UP\n"}}}},
        "public_tests": [{"name": "srv1 UP conservé", "assertion_type": "stdout_contains", "expected": "srv1 UP"}],
        "hidden_tests": [{"name": "srv2 DOWN exclu", "assertion_type": "stdout_contains", "expected": "srv3 UP"}],
        "hints": ["L'option '-v' (invert-match) inverse la sélection de grep."],
        "explanation": "grep -v est la méthode standard pour éliminer le bruit, les commentaires ou les lignes indésirables."
    })
    challenges.append({
        "id": "lx_txt_m05", "chapter_id": "text_processing_pipes", "level": 3, "topic": "Filtres, Tubes & Redirections",
        "difficulty": "medium", "points": 2.0,
        "title": "Filtrage et Sauvegarde Automatique",
        "description": "Prenez les 10 dernières lignes de `access.log`, filtrez les lignes contenant le code `404`, et écrivez le résultat dans `erreurs_404.txt`.",
        "starter_cmd": "# Filtrez les 404 des 10 dernières lignes vers erreurs_404.txt\n",
        "solution": "tail -n 10 access.log | grep 404 > erreurs_404.txt",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"access.log": {"type": "file", "content": "GET / 200\nGET /page1 200\nGET /bad 404\nGET /test 200\nGET /missing 404\n"}}}},
        "public_tests": [{"name": "Fichier erreurs_404.txt créé", "assertion_type": "file_exists", "path": "/home/student/erreurs_404.txt"}],
        "hidden_tests": [{"name": "Contient bad 404", "assertion_type": "file_contains", "path": "/home/student/erreurs_404.txt", "expected": "/bad 404"}],
        "hints": ["Enchaînez : tail -n 10 access.log | grep 404 > erreurs_404.txt."],
        "explanation": "La combinaison de filtres en pipeline avec une redirection finale permet d'extraire des rapports ciblés."
    })

    # -------------------------------------------------------------------------
    # CHAPITRE 5 : processes_signals (10 Easy + 5 Medium)
    # -------------------------------------------------------------------------
    # Easy 1-10
    challenges.append({
        "id": "lx_proc_e01", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Lister les Processus Actifs (ps)",
        "description": "Affichez la liste des processus de votre terminal courant avec la commande `ps`.",
        "starter_cmd": "# Listez les processus\n",
        "solution": "ps",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Sortie ps avec PID et CMD", "assertion_type": "stdout_contains", "expected": "PID"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Tapez simplement 'ps'."],
        "explanation": "ps affiche les processus rattachés au terminal actuel."
    })
    challenges.append({
        "id": "lx_proc_e02", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Lister Tous les Processus Système (ps aux)",
        "description": "Affichez tous les processus s'exécutant sur le système avec `ps aux`.",
        "starter_cmd": "# Affichez tous les processus système\n",
        "solution": "ps aux",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "En-tête USER et PID", "assertion_type": "stdout_contains", "expected": "USER"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez la syntaxe BSD 'ps aux'."],
        "explanation": "a = tous les terminaux, u = format utilisateur avec CPU/MEM, x = processus sans terminal (démons)."
    })
    challenges.append({
        "id": "lx_proc_e03", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Rechercher le PID d'un Processus (pgrep)",
        "description": "Recherchez le PID du processus de serveur web `nginx` avec la commande `pgrep nginx`.",
        "starter_cmd": "# Trouvez le PID de nginx\n",
        "solution": "pgrep nginx",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "PID numérique affiché", "assertion_type": "stdout_regex", "expected": "\\d+"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["pgrep renvoie uniquement les numéros de processus (PID) correspondant au nom."],
        "explanation": "pgrep simplifie la recherche en évitant d'avoir à combiner 'ps aux | grep' manuellement."
    })
    challenges.append({
        "id": "lx_proc_e04", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Envoyer le Signal de Terminaison Propre (kill)",
        "description": "Terminez proprement le processus PID `1234` avec le signal par défaut SIGTERM via `kill 1234`.",
        "starter_cmd": "# Terminez le PID 1234\n",
        "solution": "kill 1234",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Commande kill exécutée", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["kill sans option envoie le signal 15 (SIGTERM)."],
        "explanation": "SIGTERM invite le processus à libérer ses ressources et s'éteindre proprement."
    })
    challenges.append({
        "id": "lx_proc_e05", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Forcer l'Arrêt Immédiat (kill -9)",
        "description": "Forcez l'arrêt immédiat et inconditionnel du processus bloqué PID `5678` avec `kill -9 5678` (SIGKILL).",
        "starter_cmd": "# Forcez l'arrêt du PID 5678 avec SIGKILL\n",
        "solution": "kill -9 5678",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Arrêt forcé -9", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-9' ou '-SIGKILL' ne peut pas être interceptée par le processus."],
        "explanation": "SIGKILL est traité directement par le noyau Linux et détruit immédiatement le processus."
    })
    challenges.append({
        "id": "lx_proc_e06", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Lancer une Tâche en Arrière-Plan (&)",
        "description": "Lancez la commande `sleep 10` en arrière-plan en ajoutant le caractère `&` à la fin.",
        "starter_cmd": "# Lancez sleep 10 en arrière-plan\n",
        "solution": "sleep 10 &",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Lancement tâche arrière-plan", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Le symbole '&' en fin de ligne détache l'exécution du premier plan."],
        "explanation": "La commande en arrière-plan libère immédiatement l'invite de commande du shell."
    })
    challenges.append({
        "id": "lx_proc_e07", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Consulter les Tâches de Session (jobs)",
        "description": "Affichez la liste des tâches actuellement en arrière-plan ou suspendues avec `jobs`.",
        "starter_cmd": "# Affichez les jobs de session\n",
        "solution": "jobs",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Commande jobs exécutée", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["La commande interne du shell est 'jobs'."],
        "explanation": "jobs affiche les numéros de job [1], [2] propres à la session interactive."
    })
    challenges.append({
        "id": "lx_proc_e08", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Temps d'Activité et Charge Système (uptime)",
        "description": "Affichez la durée de fonctionnement de la machine et les moyennes de charge système avec `uptime`.",
        "starter_cmd": "# Affichez l'uptime\n",
        "solution": "uptime",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "load average affiché", "assertion_type": "stdout_contains", "expected": "load average"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Exécutez 'uptime'."],
        "explanation": "uptime fournit l'heure actuelle, la durée d'activité, le nombre d'utilisateurs et le load average sur 1, 5 et 15 minutes."
    })
    challenges.append({
        "id": "lx_proc_e09", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "État de la Mémoire Vive (free -m)",
        "description": "Affichez l'état de la mémoire RAM en mégaoctets en utilisant la commande `free -m`.",
        "starter_cmd": "# Affichez la mémoire en Mo\n",
        "solution": "free -m",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "En-tête Mem et Swap", "assertion_type": "stdout_contains", "expected": "Mem:"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-m' convertit les valeurs en mégaoctets."],
        "explanation": "free extrait les informations de /proc/meminfo pour afficher la RAM totale, utilisée et disponible."
    })
    challenges.append({
        "id": "lx_proc_e10", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "easy", "points": 1.0,
        "title": "Arrêt par Nom de Processus (killall / pkill)",
        "description": "Arrêtez toutes les instances du processus `test_daemon` avec la commande `pkill test_daemon`.",
        "starter_cmd": "# Arrêtez test_daemon avec pkill\n",
        "solution": "pkill test_daemon",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Commande pkill exécutée", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["pkill prend directement le nom du processus au lieu de son PID."],
        "explanation": "pkill recherche la table des processus et transmet le signal à toutes les correspondances."
    })
    # Medium 1-5
    challenges.append({
        "id": "lx_proc_m01", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "medium", "points": 2.0,
        "title": "Rechargement à Chaud sans Coupure (SIGHUP)",
        "description": "Envoyez le signal SIGHUP (signal 1) au démon de configuration PID `1001` pour recharger ses paramètres sans l'éteindre.",
        "starter_cmd": "# Envoyez SIGHUP au PID 1001\n",
        "solution": "kill -HUP 1001",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Signal SIGHUP émis", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Utilisez 'kill -HUP 1001' ou 'kill -1 1001'."],
        "explanation": "Par convention sous UNIX, SIGHUP (Signal Hang Up) déclenche le rechargement de la configuration des démons."
    })
    challenges.append({
        "id": "lx_proc_m02", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "medium", "points": 2.0,
        "title": "Récupération du PID en Arrière-Plan ($!)",
        "description": "Lancez `sleep 60` en arrière-plan, puis affichez immédiatement son PID dans la variable `$!`.",
        "starter_cmd": "# Lancez en background et affichez son PID avec $!\n",
        "solution": "sleep 60 & echo $!",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "PID numérique retourné", "assertion_type": "stdout_regex", "expected": "\\d+"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["'$!' est la variable spéciale contenant le PID de la dernière commande lancée en arrière-plan."],
        "explanation": "Cette technique est indispensable dans les scripts pour enregistrer le PID d'un démon dans un fichier .pid."
    })
    challenges.append({
        "id": "lx_proc_m03", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "medium", "points": 2.0,
        "title": "Filtrage des Processus d'un Utilisateur Spécifique",
        "description": "Listez tous les processus appartenant à l'utilisateur `student` avec `ps -u student`.",
        "starter_cmd": "# Listez les processus de student\n",
        "solution": "ps -u student",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "En-tête PID affiché", "assertion_type": "stdout_contains", "expected": "PID"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-u nom_user' filtre par propriétaire réel/effectif."],
        "explanation": "ps -u isole les processus d'un compte précis lors d'un audit de consommation de ressources."
    })
    challenges.append({
        "id": "lx_proc_m04", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "medium", "points": 2.0,
        "title": "Supervision en Mode Batch (top -b -n 1)",
        "description": "Capturez un instantané non interactif des processus les plus consommateurs avec `top -b -n 1`.",
        "starter_cmd": "# Capturez un snapshot top en mode batch\n",
        "solution": "top -b -n 1",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Sortie top batch avec Tasks", "assertion_type": "stdout_contains", "expected": "Tasks"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["-b active le mode Batch (compatible scripts) et -n 1 spécifie une seule itération."],
        "explanation": "top -b permet de rediriger ou d'analyser la télémétrie système dans un fichier de log ou un pipeline."
    })
    challenges.append({
        "id": "lx_proc_m05", "chapter_id": "processes_signals", "level": 4, "topic": "Gestion des Processus & Signaux",
        "difficulty": "medium", "points": 2.0,
        "title": "Arrêt Sélectif par Motif Complet (pkill -f)",
        "description": "Arrêtez le script en cours d'exécution `worker.py` en recherchant dans sa ligne de commande complète avec `pkill -f worker.py`.",
        "starter_cmd": "# Arrêtez le worker avec pkill -f\n",
        "solution": "pkill -f worker.py",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Exécution pkill -f", "assertion_type": "exit_code", "expected": 0}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'option '-f' fait correspondre le motif sur toute la ligne de commande (arguments inclus)."],
        "explanation": "Sans -f, pkill ne teste que le nom de l'exécutable (ici 'python3'), ce qui risquerait de tuer d'autres scripts."
    })

    # -------------------------------------------------------------------------
    # CHAPITRE 6 : bash_scripting (10 Easy + 5 Medium)
    # -------------------------------------------------------------------------
    # Easy 1-10
    challenges.append({
        "id": "lx_sh_e01", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Créer un Script avec Shebang",
        "description": "Créez un script Bash nommé `hello.sh` qui commence par `#!/bin/bash` et affiche `Hello Linux`.",
        "starter_cmd": "# Créez hello.sh\n",
        "solution": "echo '#!/bin/bash\necho \"Hello Linux\"' > hello.sh && chmod +x hello.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Fichier hello.sh présent", "assertion_type": "file_exists", "path": "/home/student/hello.sh"}],
        "hidden_tests": [{"name": "Contient Hello Linux", "assertion_type": "file_contains", "path": "/home/student/hello.sh", "expected": "Hello Linux"}],
        "hints": ["N'oubliez pas le shebang '#!/bin/bash' à la première ligne."],
        "explanation": "Le shebang (#! /chemin/interpreteur) indique au noyau quel binaire utiliser pour exécuter le script."
    })
    challenges.append({
        "id": "lx_sh_e02", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Déclaration et Utilisation de Variable",
        "description": "Déclarez une variable `MODULE=\"CYBER\"` et affichez son contenu avec `echo $MODULE`.",
        "starter_cmd": "# Déclarez MODULE='CYBER' et affichez-la\n",
        "solution": "MODULE=\"CYBER\" && echo $MODULE",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "CYBER affiché", "assertion_type": "stdout_contains", "expected": "CYBER"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Pas d'espace autour du signe égal : NOM=\"valeur\"."],
        "explanation": "En Bash, les espaces sont des séparateurs d'arguments ; `VAR = val` provoquerait une erreur."
    })
    challenges.append({
        "id": "lx_sh_e03", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Récupérer le Premier Argument ($1)",
        "description": "Créez un script `greet.sh` qui affiche `Bienvenue $1` lorsqu'on lui passe un nom en paramètre.",
        "starter_cmd": "# Créez greet.sh\n",
        "solution": "echo '#!/bin/bash\necho \"Bienvenue $1\"' > greet.sh && chmod +x greet.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Fichier greet.sh existe", "assertion_type": "file_exists", "path": "/home/student/greet.sh"}],
        "hidden_tests": [{"name": "Contient $1", "assertion_type": "file_contains", "path": "/home/student/greet.sh", "expected": "$1"}],
        "hints": ["$1 représente le premier argument positionnel passé au script."],
        "explanation": "$1 à $9 contiennent les arguments reçus sur la ligne de commande."
    })
    challenges.append({
        "id": "lx_sh_e04", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Condition de Test de Fichier (if [ -f ... ])",
        "description": "Écrivez une condition Bash qui teste si le fichier `data.csv` existe et affiche `OK` si c'est le cas.",
        "starter_cmd": "# Testez si data.csv existe\n",
        "solution": "if [ -f data.csv ]; then echo 'OK'; fi",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"data.csv": {"type": "file", "content": "1,2\n"}}}},
        "public_tests": [{"name": "OK affiché si présent", "assertion_type": "stdout_contains", "expected": "OK"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'opérateur '-f' teste l'existence d'un fichier régulier."],
        "explanation": "Les crochets `[ ... ]` invoquent la commande de test standard POSIX."
    })
    challenges.append({
        "id": "lx_sh_e05", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Boucle Numérique For (for i in ...)",
        "description": "Écrivez une boucle `for` qui affiche successivement les nombres `1`, `2` et `3` (un par ligne).",
        "starter_cmd": "# Boucle for 1 2 3\n",
        "solution": "for i in 1 2 3; do echo $i; done",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Nombres affichés", "assertion_type": "stdout_contains", "expected": "2"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["Syntaxe : 'for i in 1 2 3; do echo $i; done'."],
        "explanation": "La boucle for itère sur la liste de mots fournie après le mot-clé in."
    })
    challenges.append({
        "id": "lx_sh_e06", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Calcul Arithmétique $(( ... ))",
        "description": "Effectuez l'addition de 15 et 27 avec la syntaxe arithmétique `$(( 15 + 27 ))` et affichez le résultat.",
        "starter_cmd": "# Calculez 15 + 27\n",
        "solution": "echo $(( 15 + 27 ))",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Résultat 42", "assertion_type": "stdout_contains", "expected": "42"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'expansion arithmétique utilise la syntaxe '$(( expression ))'."],
        "explanation": "$(( )) permet d'évaluer des opérations sur entiers sans faire appel à un utilitaire externe."
    })
    challenges.append({
        "id": "lx_sh_e07", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Vérifier le Code de Retour ($?)",
        "description": "Affichez le code de retour de la dernière commande avec `echo $?` après avoir exécuté `true`.",
        "starter_cmd": "# Exécutez true puis affichez $?\n",
        "solution": "true && echo $?",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Code de retour 0", "assertion_type": "stdout_contains", "expected": "0"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["'$?' stocke le code de retour de la dernière commande terminée."],
        "explanation": "Un code 0 indique un succès ; une valeur non nulle (1 à 255) signale une erreur."
    })
    challenges.append({
        "id": "lx_sh_e08", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Test d'Existence d'un Répertoire ([ -d ... ])",
        "description": "Écrivez un test vérifiant si le dossier `/tmp` existe et affichez `Dossier temporaire present` si vrai.",
        "starter_cmd": "# Testez si /tmp existe\n",
        "solution": "if [ -d /tmp ]; then echo 'Dossier temporaire present'; fi",
        "initial_fs": {"/tmp": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Confirmation présence", "assertion_type": "stdout_contains", "expected": "Dossier temporaire present"}],
        "hidden_tests": [{"name": "Code retour 0", "assertion_type": "exit_code", "expected": 0}],
        "hints": ["L'opérateur '-d' vérifie qu'un chemin existe et est un répertoire."],
        "explanation": "-d retourne vrai si la cible existe et possède le type dossier."
    })
    challenges.append({
        "id": "lx_sh_e09", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Nombre d'Arguments Passés ($#)",
        "description": "Créez un script `count_args.sh` qui affiche `Arguments: $#` pour indiquer le nombre de paramètres reçus.",
        "starter_cmd": "# Créez count_args.sh\n",
        "solution": "echo '#!/bin/bash\necho \"Arguments: $#\"' > count_args.sh && chmod +x count_args.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "count_args.sh créé", "assertion_type": "file_exists", "path": "/home/student/count_args.sh"}],
        "hidden_tests": [{"name": "Contient $#", "assertion_type": "file_contains", "path": "/home/student/count_args.sh", "expected": "$#"}],
        "hints": ["'$#' contient le compte total des arguments positionnels."],
        "explanation": "$# permet de valider que l'utilisateur a passé le bon nombre de paramètres."
    })
    challenges.append({
        "id": "lx_sh_e10", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "easy", "points": 1.0,
        "title": "Sortie d'un Script avec Code Erreur (exit 1)",
        "description": "Créez un script `fail.sh` qui affiche `Erreur critique` et se termine avec le code de statut d'échec `exit 1`.",
        "starter_cmd": "# Créez fail.sh avec exit 1\n",
        "solution": "echo '#!/bin/bash\necho \"Erreur critique\"\nexit 1' > fail.sh && chmod +x fail.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Fichier fail.sh présent", "assertion_type": "file_exists", "path": "/home/student/fail.sh"}],
        "hidden_tests": [{"name": "Contient exit 1", "assertion_type": "file_contains", "path": "/home/student/fail.sh", "expected": "exit 1"}],
        "hints": ["La commande 'exit N' interrompt le script et renvoie le code N."],
        "explanation": "exit 1 signale immédiatement aux outils d'orchestration que le script a échoué."
    })
    # Medium 1-5
    challenges.append({
        "id": "lx_sh_m01", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "medium", "points": 2.0,
        "title": "Script de Sauvegarde Horodatée",
        "description": "Créez un script `backup_logs.sh` qui copie `app.log` vers `backup_app.log` et affiche `Sauvegarde terminee avec succes`.",
        "starter_cmd": "# Créez backup_logs.sh\n",
        "solution": "echo '#!/bin/bash\ncp app.log backup_app.log\necho \"Sauvegarde terminee avec succes\"' > backup_logs.sh && chmod +x backup_logs.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"app.log": {"type": "file", "content": "donnees\n"}}}},
        "public_tests": [{"name": "backup_logs.sh présent", "assertion_type": "file_exists", "path": "/home/student/backup_logs.sh"}],
        "hidden_tests": [{"name": "Contient cp app.log", "assertion_type": "file_contains", "path": "/home/student/backup_logs.sh", "expected": "backup_app.log"}],
        "hints": ["Utilisez 'cp app.log backup_app.log' dans le script."],
        "explanation": "Les scripts de sauvegarde automatisent les tâches répétitives sans intervention humaine."
    })
    challenges.append({
        "id": "lx_sh_m02", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "medium", "points": 2.0,
        "title": "Validation des Arguments Obligatoires",
        "description": "Créez un script `check_param.sh` qui vérifie si au moins 1 argument est fourni : si `$# -lt 1`, il affiche `Usage: script.sh <nom>` et quitte avec `exit 1`.",
        "starter_cmd": "# Créez check_param.sh\n",
        "solution": "echo '#!/bin/bash\nif [ $# -lt 1 ]; then\n  echo \"Usage: script.sh <nom>\"\n  exit 1\nfi' > check_param.sh && chmod +x check_param.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Fichier check_param.sh existe", "assertion_type": "file_exists", "path": "/home/student/check_param.sh"}],
        "hidden_tests": [{"name": "Condition $# -lt 1 présente", "assertion_type": "file_contains", "path": "/home/student/check_param.sh", "expected": "$# -lt 1"}],
        "hints": ["Vérifiez avec 'if [ $# -lt 1 ]; then ... fi'."],
        "explanation": "La validation en amont des prérequis protège les scripts contre les exécutions erronées."
    })
    challenges.append({
        "id": "lx_sh_m03", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "medium", "points": 2.0,
        "title": "Lecture Ligne par Ligne (while read line)",
        "description": "Créez un script `read_users.sh` qui lit `users.txt` ligne par ligne avec `while read line; do echo \"User: $line\"; done < users.txt`.",
        "starter_cmd": "# Créez read_users.sh avec boucle while read\n",
        "solution": "echo '#!/bin/bash\nwhile read -r line; do\n  echo \"User: $line\"\ndone < users.txt' > read_users.sh && chmod +x read_users.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"users.txt": {"type": "file", "content": "alice\nbob\n"}}}},
        "public_tests": [{"name": "Fichier read_users.sh existe", "assertion_type": "file_exists", "path": "/home/student/read_users.sh"}],
        "hidden_tests": [{"name": "Boucle while read présente", "assertion_type": "file_contains", "path": "/home/student/read_users.sh", "expected": "while read"}],
        "hints": ["La boucle 'while read -r line; do ... done < fichier' traite chaque ligne individuellement."],
        "explanation": "C'est la méthode la plus robuste pour parser des flux de texte contenant des espaces."
    })
    challenges.append({
        "id": "lx_sh_m04", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "medium", "points": 2.0,
        "title": "Substitution de Commande $(...)",
        "description": "Créez un script `info.sh` qui stocke le répertoire courant dans une variable `DIR=$(pwd)` et affiche `Dossier: $DIR`.",
        "starter_cmd": "# Utilisez $(pwd) dans info.sh\n",
        "solution": "echo '#!/bin/bash\nDIR=$(pwd)\necho \"Dossier: $DIR\"' > info.sh && chmod +x info.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {}}},
        "public_tests": [{"name": "Fichier info.sh existe", "assertion_type": "file_exists", "path": "/home/student/info.sh"}],
        "hidden_tests": [{"name": "Contient $(pwd)", "assertion_type": "file_contains", "path": "/home/student/info.sh", "expected": "$(pwd)"}],
        "hints": ["La syntaxe $(commande) capture la sortie standard de la sous-commande."],
        "explanation": "La substitution de commande $( ) remplace l'ancienne syntaxe à backticks ` `."
    })
    challenges.append({
        "id": "lx_sh_m05", "chapter_id": "bash_scripting", "level": 3, "topic": "Scripting Bash & Automatisation",
        "difficulty": "medium", "points": 2.0,
        "title": "Script de Surveillance avec Condition Double",
        "description": "Créez un script `monitor.sh` qui vérifie si `flag.txt` existe ET n'est pas vide avec `[ -s flag.txt ]`. Si oui, affiche `ACTIF`.",
        "starter_cmd": "# Testez si flag.txt est non vide\n",
        "solution": "echo '#!/bin/bash\nif [ -s flag.txt ]; then\n  echo \"ACTIF\"\nfi' > monitor.sh && chmod +x monitor.sh",
        "initial_fs": {"/home/student": {"type": "dir", "files": {"flag.txt": {"type": "file", "content": "1\n"}}}},
        "public_tests": [{"name": "Fichier monitor.sh présent", "assertion_type": "file_exists", "path": "/home/student/monitor.sh"}],
        "hidden_tests": [{"name": "Test -s flag.txt présent", "assertion_type": "file_contains", "path": "/home/student/monitor.sh", "expected": "-s flag.txt"}],
        "hints": ["L'opérateur '-s' teste qu'un fichier existe et que sa taille est supérieure à 0."],
        "explanation": "-s (size) permet d'éviter de traiter des fichiers corrompus ou vides."
    })

    return challenges

def main():
    challenges = build_challenges()
    print(f"Total challenges generated: {len(challenges)}")
    
    # Validation : 15 défis par chapitre (10 easy + 5 medium)
    ch_counts = {}
    for c in challenges:
        ch_id = c["chapter_id"]
        diff = c["difficulty"]
        ch_counts.setdefault(ch_id, {}).setdefault(diff, 0)
        ch_counts[ch_id][diff] += 1
    
    print("\nChallenges breakdown:")
    for ch_id, diffs in ch_counts.items():
        print(f"  {ch_id}: {diffs} (Total: {sum(diffs.values())})")
        assert diffs.get("easy", 0) == 10, f"Chapter {ch_id} must have 10 easy challenges"
        assert diffs.get("medium", 0) == 5, f"Chapter {ch_id} must have 5 medium challenges"
        
    # Écriture de challenges.json
    challenges_path = "backend/app/data/linux_training/challenges.json"
    with open(challenges_path, "w", encoding="utf-8") as f:
        json.dump(challenges, f, ensure_ascii=False, indent=2)
    print(f"\nSuccessfully wrote {len(challenges)} challenges to {challenges_path}")

    # Mise à jour de curriculum.json
    curr_path = "backend/app/data/linux_training/curriculum.json"
    with open(curr_path, "r", encoding="utf-8") as f:
        curr = json.load(f)
        
    for ch in curr.get("chapters", []):
        ch_id = ch["id"]
        ch_challenges = [c for c in challenges if c["chapter_id"] == ch_id]
        ch["coding_exercises"] = ch_challenges
        ch["coding_exercises_count"] = len(ch_challenges)
        # Assurer que les questions théoriques ont toutes les types requis
        # Si bash_scripting manque un matching, l'ajouter
        qs = ch.get("mcq_questions", [])
        types = set(q.get("type") for q in qs)
        if "matching" not in types:
            qs.append({
                "id": f"q_{ch_id}_matching_spec",
                "type": "matching",
                "prompt": f"Associez chaque concept de {ch['title']} à son utilité principale.",
                "points": 1.0,
                "pairs": [
                    {"left": "Shebang (#!/bin/bash)", "right": "Interpréteur d'exécution"},
                    {"left": "$?", "right": "Code de retour"},
                    {"left": "$#", "right": "Nombre d'arguments"},
                    {"left": "$(( ))", "right": "Calcul arithmétique"}
                ],
                "explanation": "Les variables spéciales et constructions Bash sont fondamentales."
            })
            ch["mcq_questions_count"] = len(qs)
            
    with open(curr_path, "w", encoding="utf-8") as f:
        json.dump(curr, f, ensure_ascii=False, indent=2)
    print(f"Successfully updated curriculum.json with 15 coding exercises per chapter and enriched questions!")

if __name__ == "__main__":
    main()

