#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

PORT="${PORT:-8000}"
WORKERS="${WORKERS:-2}"
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "=============================================================================="
echo "   🟢 SERVEUR EXAMQUIZ (LINUX) ACTIF"
echo "   👉 Accès Local : http://127.0.0.1:${PORT}"
echo "   👉 Accès Salle LAN : http://${LAN_IP}:${PORT}"
echo "=============================================================================="

if [ -f ".venv/bin/uvicorn" ]; then
    exec .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS"
else
    exec python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS"
fi
