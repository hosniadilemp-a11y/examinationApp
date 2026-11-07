# 🪟 Déploiement Windows (`deployment/windows/`)

Ce dossier regroupe les scripts Batch (`.bat`), PowerShell (`.ps1`), Bash (`.sh` / `.bash` pour Git Bash / WSL), la configuration Docker Desktop et l'image finale autonome pour déployer **ExamQuiz** sous Windows 10/11 ou Windows Server.

## Contenu du dossier
- `image/examquiz-windows-release.zip` : **Image finale autonome Windows** contenant le code complet, les banques d'exercices et la base SQLite pré-initialisée (Admin, 3 modules + leurs enseignants, 4 classes de 4 étudiants, et examens modèles).
- `install_and_deploy.bat` / `install_and_deploy.ps1` / `install_and_deploy.sh` : Installation complète et démarrage automatique.
- `init_test_db.bat` / `init_test_db.sh` : Réinitialise la base de données avec les comptes et examens de test.
- `start_server.bat` / `stop_server.bat` : Démarre / arrête le serveur sur le port `8000`.
- `build_windows_image.bat` / `load_windows_image.bat` : Construit ou déploie l'image finale Windows.
- `Dockerfile.windows` & `docker-compose.windows.yml` : Déploiement via Docker Desktop.

## Démarrage Rapide
- **Invite de commandes / Double-clic** : `deployment\windows\install_and_deploy.bat`
- **PowerShell** : `.\deployment\windows\install_and_deploy.ps1`
- **Git Bash / WSL** : `bash deployment/windows/install_and_deploy.sh`
