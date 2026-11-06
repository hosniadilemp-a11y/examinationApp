# 🚀 Guide Complet de Déploiement — ExaminationQuiz APP

Ce dossier unique `deployment/` rassemble **tous les scripts, images de déploiement, fichiers CSV d'exemple, modèles d'examens JSON et fiches d'identifiants** nécessaires pour installer et exploiter la plateforme sur **Linux** et **Windows**.

---

## 📁 Structure du Dossier `deployment/`

```text
deployment/
├── README_DEPLOIEMENT.md                     # Ce guide pas-à-pas
├── credentials/
│   └── logins.txt                            # Récapitulatif de tous les identifiants par défaut
├── examples_csv/
│   ├── etudiants_4_specialites.csv           # Modèle CSV Étudiants (ID;nom;prenom;annee;specialite)
│   └── enseignants_modules.csv               # Modèle CSV Enseignants (nom;prenom;email;modules)
├── examples_exams/
│   ├── examen_modele_python_40q.json         # Examen Python Théorique (40 QCM -> 20 aléatoires/étudiant)
│   ├── examen_modele_python_pratique.json    # Examen Python Pratique (10 défis -> 5 aléatoires/étudiant)
│   ├── examen_modele_crypto.json             # Examen Cryptographie (20 questions multi-types)
│   ├── examen_modele_linux.json              # Examen Administration Linux (20 questions)
│   └── backups/                              # Sauvegardes additionnelles
├── linux/
│   ├── install_and_run_linux.sh              # Installation & démarrage automatique Linux
│   ├── start_linux.sh                        # Démarrage rapide Linux
│   ├── reset_test_env_linux.sh               # Réinitialisation de la base de test
│   ├── Dockerfile.linux                      # Image Docker Linux
│   ├── docker-compose.linux.yml              # Orchestration Docker Linux
│   ├── examquiz.service                      # Service systemd Linux
│   └── image/
│       └── examquiz-linux-release.tar.gz     # Archive de déploiement Linux prête à l'emploi
└── windows/
    ├── install_and_run_windows.bat           # Installation & démarrage Windows (CMD)
    ├── install_and_run_windows.ps1           # Installation & démarrage Windows (PowerShell)
    ├── install_and_run_windows.sh            # Script Git Bash Windows
    ├── reset_test_env_windows.bat            # Réinitialisation de la base de test Windows
    ├── Dockerfile.windows                    # Image Docker Windows
    ├── docker-compose.windows.yml            # Orchestration Docker Windows
    └── image/
        └── examquiz-windows-release.zip      # Archive de déploiement Windows prête à l'emploi
```

---

## 🐧 Déploiement sous Linux (Ubuntu / Debian / RHEL)

1. **Extraire l'archive Linux** (ou cloner le dépôt) :
   ```bash
   tar -xzf deployment/linux/image/examquiz-linux-release.tar.gz -C /opt/examquiz
   cd /opt/examquiz
   ```
2. **Lancer l'installation et le serveur** :
   ```bash
   chmod +x deployment/linux/*.sh
   ./deployment/linux/install_and_run_linux.sh
   ```
3. **Accéder à l'application** :
   - Ouvrez `http://<IP_DU_SERVEUR>:8000` dans votre navigateur.

---

## 🪟 Déploiement sous Windows (Windows 10 / 11 / Server)

1. **Extraire l'archive Windows** `deployment/windows/image/examquiz-windows-release.zip` (ou ouvrir le dossier du projet).
2. **Double-cliquer sur** `deployment\windows\install_and_run_windows.bat` (ou exécuter `install_and_run_windows.ps1` dans PowerShell).
3. **Accéder à l'application** :
   - Ouvrez `http://localhost:8000` dans votre navigateur.

---

## 📥 Importation CSV & Génération Automatique des Identifiants

- **Étudiants (`deployment/examples_csv/etudiants_4_specialites.csv`)** :
  - Colonnes requises : `ID;nom;prenom;annee;specialite`
  - Le système génère automatiquement l'identifiant (`username`) et le mot de passe en clair (`plain_password`).
  - Cliquez sur **✂️ Imprimer Fiches Identifiants (Étudiants)** dans l'onglet *Étudiants* pour imprimer les coupons découpables.
- **Enseignants (`deployment/examples_csv/enseignants_modules.csv`)** :
  - Colonnes requises : `nom;prenom;email;modules`
  - Le système génère automatiquement le matricule (`ENS-xxx`), l'identifiant (`prof.xxx`) et le mot de passe, et affecte les modules listés.
  - Cliquez sur **✂️ Imprimer Fiches Identifiants (Enseignants)** dans l'onglet *Enseignants* pour imprimer les coupons découpables.
