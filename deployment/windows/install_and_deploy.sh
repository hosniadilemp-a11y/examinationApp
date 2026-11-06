#!/usr/bin/env bash
# ==============================================================================
# ExamQuiz Platform — Installation & Déploiement sous Windows (Git Bash / WSL)
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

echo "=============================================================================="
echo "   🪟 DÉPLOIEMENT WINDOWS (BASH) — PLATEFORME EXAMQUIZ"
echo "=============================================================================="

PY_CMD="python"
if ! command -v python &>/dev/null && command -v python3 &>/dev/null; then
    PY_CMD="python3"
fi

if [ ! -d ".venv" ]; then
    echo "[1/4] Création de l'environnement virtuel (.venv)..."
    $PY_CMD -m venv .venv
fi

if [ -f ".venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

echo "[2/4] Installation des dépendances (requirements.txt)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "[3/4] Initialisation de la base de données et des comptes de test..."
python scripts/reset_and_seed_exact_3_exams.py

echo "[4/4] Démarrage du serveur sur http://0.0.0.0:8000 ..."
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
