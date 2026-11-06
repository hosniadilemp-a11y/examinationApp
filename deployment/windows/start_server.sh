#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

if [ -f ".venv/Scripts/python.exe" ]; then
    exec .venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
else
    exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
fi
