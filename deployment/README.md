# 📦 Répertoire de Déploiement Autonome — 3 Packages Clés en Main

Ce dossier contient **3 packages de déploiement 100% autonomes (self-contained)**.  
Chacun des 3 dossiers dispose de **tous ses fichiers nécessaires** (scripts, fichiers Docker, images hors-ligne, données utilisateurs, identifiants et modèles d'épreuves) sans dépendance externe :

---

## 🗂️ Structure des 3 Packages Autonomes

```
deployment/
│
├── LANCER_EXAM_CONTROL.bat         <-- Raccourci de lancement direct de l'App Desktop
│
├── 🐧 linux_deployment/             <-- PACKAGE 1 : SERVEUR LINUX (100% Autonome)
│   ├── start_server.sh             (Lancement rapide Docker)
│   ├── stop_server.sh              (Arrêt propre)
│   ├── install_and_deploy.sh       (Installation complète)
│   ├── init_test_db.sh             (Injection des données)
│   ├── update_app.sh               (Mise à jour d'image)
│   ├── docker-compose.yml          (Compose PostgreSQL 16 + FastAPI)
│   ├── Dockerfile                  (Recette de conteneur Linux)
│   ├── examquiz.service            (Service Systemd pour boot auto)
│   ├── README.md & README.txt      (Manuels administrateur Linux)
│   ├── logins.txt                  (Identifiants admin, profs, étudiants)
│   ├── images_docker/              (examination-quiz-server.tar - 126 Mo)
│   ├── csv_utilisateurs/           (enseignants_modules.csv, etudiants_4_specialites.csv)
│   ├── examens_json/               (Python, Linux, Cryptographie)
│   └── backups/                    (Sauvegardes complètes)
│
├── 🪟 windows_deployment/           <-- PACKAGE 2 : SERVEUR WINDOWS CLI (100% Autonome)
│   ├── start_server.bat            (Lancement rapide en 1 clic)
│   ├── stop_server.bat             (Arrêt propre)
│   ├── install_and_deploy.bat      (Installation automatisée)
│   ├── install_and_deploy.ps1      (Script PowerShell équivalent)
│   ├── init_test_db.bat            (Injection des données)
│   ├── load_offline_image.bat      (Chargement image Docker hors-ligne)
│   ├── installer_nom_local.bat     (Configuration exam.local pour clients)
│   ├── docker-compose.yml          (Compose PostgreSQL 16 + FastAPI)
│   ├── Dockerfile                  (Recette de conteneur Windows)
│   ├── README.md & README.txt      (Manuels administrateur Windows)
│   ├── logins.txt                  (Identifiants complets)
│   ├── images_docker/              (examination-quiz-server.tar - 126 Mo)
│   ├── csv_utilisateurs/           (enseignants_modules.csv, etudiants_4_specialites.csv)
│   ├── examens_json/               (Python, Linux, Cryptographie)
│   └── backups/                    (Sauvegardes complètes)
│
└── 🎓 desktop_application/         <-- PACKAGE 3 : APPLICATION DESKTOP (100% Autonome)
    ├── ExamControlMaster.exe       (20.6 Mo - Exécutable autonome compilé)
    ├── LANCER_EXAM_CONTROL.bat     (Lanceur en 1 clic)
    ├── docker-compose.yml          (Pilote des conteneurs en tâche de fond)
    ├── installer_nom_local.bat     (Script pour les PC étudiants)
    ├── plan_salle_template.csv     (Modèle pour nommer les postes)
    ├── README.md & README.txt      (Manuel utilisateur complet pour surveillants)
    ├── logins.txt                  (Identifiants complets)
    ├── images_docker/              (examination-quiz-server.tar pour màj USB)
    ├── data/network_topology.json  (Sauvegarde des alias de postes)
    ├── csv_utilisateurs/           (enseignants_modules.csv, etudiants_4_specialites.csv)
    └── examens_json/               (Python, Linux, Cryptographie)
```

---

## 🔑 Résumé des Comptes & Identifiants Inclus dans les 3 Packages

### 1. Administrateur Global
- **Identifiant :** `admin`
- **Mot de passe :** `admin123`

### 2. Enseignants par Module d'Examen
- **Python Avancé :** `prof_python` / `ProfPython1!` *(Dr. Martin Laurent — Module PYTHON_INIT)*
- **Cryptographie :** `prof_crypto` / `ProfCrypto1!` *(Dr. Sophie Bernard — Module CRYPTO)*
- **Administration Linux :** `prof_linux` / `ProfLinux1!` *(Dr. Karim Mansouri — Module LINUX_ADMIN)*
- **Responsable Pédagogique :** `prof_martin` / `prof123` *(Accès à tous les modules)*

### 3. Étudiants (16 Comptes répartis sur 4 Spécialités)
- **Spécialité DEV-IA :** `etu_dev1`, `etu_dev2`, `etu_dev3`, `etu_dev4` *(Mdp: `StudentDev1!` à `StudentDev4!`)*
- **Spécialité SYS-ADMIN :** `etu_sys1`, `etu_sys2`, `etu_sys3`, `etu_sys4` *(Mdp: `StudentSys1!` à `StudentSys4!`)*
- **Spécialité CYBER-SEC :** `etu_sec1`, `etu_sec2`, `etu_sec3`, `etu_sec4` *(Mdp: `StudentSec1!` à `StudentSec4!`)*
- **Spécialité GRP-1 :** `etudiant1` *(Mdp: `etu123`)*, `etu_log2`, `etu_log3`, `etu_log4` *(Mdp: `StudentLog2!` à `StudentLog4!`)*

---

## 📝 Fichiers d'Injection d'Examens Inclus dans les 3 Packages

Chaque package contient les 3 examens officiels prêts à être injectés :
1. **`examen_modele_python_avance.json`** : 15 questions théoriques + 5 problèmes pratiques avec tests unitaires cachés et évaluation sandbox.
2. **`examen_modele_linux.json`** : 20 questions théoriques + commandes d'administration système.
3. **`examen_modele_crypto.json`** : 15 questions théoriques + exercices pratiques de chiffrement/hachage.

