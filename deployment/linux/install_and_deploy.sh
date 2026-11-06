#!/usr/bin/env bash
# ==============================================================================
# ExamQuiz Platform — Installation & Déploiement Complet sous Linux (.sh)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

MODE="${1:---native}" # --native | --docker | --systemd

echo "=============================================================================="
echo "   🐧 DÉPLOIEMENT LINUX — PLATEFORME EXAMQUIZ (LAN / STANDALONE)"
echo "=============================================================================="

if [ "$MODE" = "--docker" ]; then
    echo "[DOCKER] Construction et démarrage de l'image Linux..."
    docker compose -f deployment/linux/docker-compose.linux.yml up -d --build
    echo "✅ Conteneur Linux actif sur http://0.0.0.0:8000"
    exit 0
fi

if ! command -v python3 &>/dev/null; then
    echo "[INFO] Installation de Python3 et python3-venv..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip
    fi
fi

if [ ! -d ".venv" ]; then
    echo "[1/4] Création de l'environnement virtuel Python (.venv)..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/4] Installation des dépendances Python..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "[3/4] Initialisation de la base SQLite WAL et des données de test..."
python3 scripts/reset_and_seed_exact_3_exams.py

if [ "$MODE" = "--systemd" ]; then
    echo "[4/4] Installation du service systemd examquiz.service..."
    sed "s|__APP_ROOT__|$APP_ROOT|g" deployment/linux/examquiz.service | sudo tee /etc/systemd/system/examquiz.service >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable examquiz.service
    sudo systemctl restart examquiz.service
    echo "✅ Service systemd examquiz actif sur le port 8000 !"
    exit 0
fi

echo "[4/4] Lancement du serveur de production Linux..."
exec bash "$SCRIPT_DIR/start_server.sh"
