#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_ROOT"

if [ -f ".venv/Scripts/python.exe" ]; then
    .venv/Scripts/python.exe scripts/reset_and_seed_exact_3_exams.py
else
    python scripts/reset_and_seed_exact_3_exams.py
fi
