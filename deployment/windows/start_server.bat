@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
echo ==============================================================================
echo    SERVEUR EXAMQUIZ (WINDOWS) ACTIF SUR LE PORT 8000
echo    Acces Local : http://127.0.0.1:8000
echo ==============================================================================
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
) else (
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
)
