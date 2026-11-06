#!/usr/bin/env bash
# ==============================================================================
# Réinitialisation de la base de données avec les données de test officielles :
# - Admin (admin / Admin123!)
# - 3 Modules (PYTHON_INIT, CRYPTO, LINUX_ADMIN) + Enseignants dédiés
# - 4 Classes × 4 Étudiants = 16 Étudiants complets
# - Examens Modèles pour les 3 modules
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python scripts/reset_and_seed_exact_3_exams.py
else
    python3 scripts/reset_and_seed_exact_3_exams.py
fi
