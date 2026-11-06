# 🐧 Déploiement Linux (`deployment/linux/`)

Ce dossier regroupe tous les scripts Bash/Shell, fichiers de configuration et l'image finale pour déployer la plateforme **ExamQuiz** sous Linux (Ubuntu, Debian, RHEL, Rocky, Fedora).

## Contenu du dossier
- `image/examquiz-linux-release.tar.gz` : **Image finale autonome Linux** pré-peuplée avec la base de données de test (Admin, 3 modules + leurs enseignants, 4 classes de 4 étudiants, et examens modèles).
- `install_and_deploy.sh` / `install_and_deploy.bash` : Script complet d'installation et de démarrage (`--native`, `--docker`, ou `--systemd`).
- `init_test_db.sh` : Réinitialise la base de données avec les données de test officielles.
- `start_server.sh` / `stop_server.sh` : Démarre / arrête le serveur Uvicorn sur `0.0.0.0:8000`.
- `build_linux_image.sh` / `load_linux_image.sh` : Construit ou charge l'image finale Linux.
- `Dockerfile.linux` & `docker-compose.linux.yml` : Conteneurisation Docker Linux.
- `examquiz.service` : Unité `systemd` pour exécution en tant que démon Linux au démarrage.

## Démarrage Rapide (1 commande)
```bash
chmod +x deployment/linux/*.sh
./deployment/linux/install_and_deploy.sh
```
