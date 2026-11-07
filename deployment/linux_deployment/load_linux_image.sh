#!/usr/bin/env bash
# ==============================================================================
# Déploie l'image finale Linux sur une machine cible (hors-ligne ou en ligne)
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/image/examquiz-docker-linux.tar" ] && command -v docker &>/dev/null; then
    echo "📦 Chargement de l'image Docker Linux..."
    docker load -i "$SCRIPT_DIR/image/examquiz-docker-linux.tar"
    docker run -d --name examquiz-linux -p 8000:8000 --restart unless-stopped examquiz-app-linux:latest
    echo "✅ Image Docker Linux déployée sur http://localhost:8000"
elif [ -f "$SCRIPT_DIR/image/examquiz-linux-release.tar.gz" ]; then
    TARGET_DIR="${1:-/opt/examquiz}"
    echo "📦 Extraction de l'image Linux dans $TARGET_DIR ..."
    mkdir -p "$TARGET_DIR"
    tar -xzf "$SCRIPT_DIR/image/examquiz-linux-release.tar.gz" -C "$TARGET_DIR"
    cd "$TARGET_DIR"
    bash deployment/linux/install_and_deploy.sh
else
    echo "[ERREUR] Aucune image trouvée dans $SCRIPT_DIR/image/"
    exit 1
fi
