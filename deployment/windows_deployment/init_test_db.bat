@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\reset_and_seed_exact_3_exams.py
) else (
    python scripts\reset_and_seed_exact_3_exams.py
)
echo Base de donnees reinitialisee avec succes !
