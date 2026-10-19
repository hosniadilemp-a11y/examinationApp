@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Serveur de Salle d'Examen TP

echo =====================================================================
echo    PLATEFORME D'EXAMEN ET D'ENTRAINEMENT - SERVEUR DE SALLE TP
echo =====================================================================
echo.

REM 1. Verification de l'interpreteur Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Veuillez installer Python ou utiliser docker-compose up -d.
    pause
    exit /b 1
)

REM 2. Detection de l'adresse IP locale
set LOCAL_IP=127.0.0.1
for /f "tokens=4" %%a in ('route print 0.0.0.0 2^>nul ^| findstr /C:"0.0.0.0"') do (
    if not "%%a"=="" set LOCAL_IP=%%a
)

echo [INFO] Serveur actif sur le reseau local de la salle.
echo.
echo =====================================================================
echo    INTERFACE ENSEIGNANT / SURVEILLANCE : http://localhost:8000
echo    ACCES POSTES ETUDIANTS DE LA SALLE : http://!LOCAL_IP!:8000
echo =====================================================================
echo.
echo [INFO] Ouverture automatique du tableau de bord dans le navigateur...
start "" "http://localhost:8000"

echo [INFO] Demarrage de FastAPI (Uvicorn)...
echo Appuyez sur Ctrl+C pour arreter le serveur.
echo.
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
pause
