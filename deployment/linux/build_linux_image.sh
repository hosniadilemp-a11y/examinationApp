#!/usr/bin/env bash
# ==============================================================================
# Construit l'image finale Linux :
# 1) Archive autonome prête à déployer : deployment/linux/image/examquiz-linux-release.tar.gz
# 2) Image Docker exportée (.tar) si Docker est actif : deployment/linux/image/examquiz-docker-linux.tar
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

mkdir -p deployment/linux/image

echo "[1/2] Création de l'image autonome Linux : deployment/linux/image/examquiz-linux-release.tar.gz ..."
tar --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.git' \
    --exclude='deployment/linux/image/*' --exclude='deploy/windows/image/*' \
    -czf deployment/linux/image/examquiz-linux-release.tar.gz \
    backend frontend scripts archive_data deployment/linux requirements.txt logins.txt deploy.sh deploy.bash setup_and_seed.sh exam_app.db

if command -v docker &>/dev/null && docker info &>/dev/null; then
    echo "[2/2] Construction et exportation de l'image Docker Linux..."
    docker build -f deployment/linux/Dockerfile.linux -t examquiz-app-linux:latest .
    docker save -o deployment/linux/image/examquiz-docker-linux.tar examquiz-app-linux:latest
    echo "✅ Image Docker exportée dans deployment/linux/image/examquiz-docker-linux.tar"
else
    echo "[INFO] Docker démon non actif : l'archive autonome tar.gz et le Dockerfile.linux sont prêts dans deployment/linux/image/."
fi
echo "✅ Image finale Linux prête dans deployment/linux/image/"
