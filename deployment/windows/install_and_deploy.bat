@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

cd /d "%~dp0..\.."

echo ==============================================================================
echo    DÉPLOIEMENT WINDOWS — PLATEFORME D'EXAMEN EXAMQUIZ
echo ==============================================================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Python 3.10+ n'est pas installe ou absent du PATH Windows.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/4] Creation de l'environnement virtuel Python (.venv)...
    python -m venv .venv
)

echo [2/4] Installation des dependances Python...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

echo [3/4] Initialisation de la base de donnees de deploiement (Admin, 3 Modules, 4x4 Etudiants)...
python scripts\reset_and_seed_exact_3_exams.py

echo [4/4] Lancement du serveur sur le port 8000...
call "%~dp0start_server.bat"
