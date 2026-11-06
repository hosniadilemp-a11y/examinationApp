#!/bin/sh
set -e

echo "=========================================================="
echo " Plateforme d'Examen et d'Entraînement - Démarrage Docker "
echo "=========================================================="

# 1. Attente active de la base de données (PostgreSQL ou SQLite WAL)
echo "==> [1/3] Vérification de la connexion à la base de données..."
python - << 'EOF'
import time
import sys
from sqlalchemy import text
from backend.app.database import engine

max_retries = 30
for i in range(1, max_retries + 1):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[OK] Base de données accessible ({engine.url.drivername}).")
        sys.exit(0)
    except Exception as exc:
        print(f"[{i}/{max_retries}] En attente de la base de données ({exc})...")
        time.sleep(1)

print("[ERREUR] Délai dépassé : impossible de se connecter à la base de données.")
sys.exit(1)
EOF

# 2. Peuplement des données initiales si demandé
if [ "${SEED_DATA:-true}" = "true" ] || [ "${SEED_DATA:-true}" = "1" ]; then
    echo "==> [2/3] Peuplement initial de la base de données (SEED_DATA=true)..."
    python scripts/reset_and_seed_exact_3_exams.py
else
    echo "==> [2/3] Initialisation du schéma sans écrasement..."
    python -c "from backend.app.main import init_db; init_db()"
fi

# 3. Lancement du processus principal
echo "==> [3/3] Démarrage du serveur Uvicorn..."
exec "$@"
