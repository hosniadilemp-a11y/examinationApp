@echo off
setlocal enabledelayedexpansion
title Plateforme d'Examen LAN - Demarrage Docker

echo ===============================================================================
echo        DEMARRAGE DU SERVEUR D'EXAMEN ET D'ENTRAINEMENT (DOCKER)
echo ===============================================================================

cd /d "%~dp0.."

where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou le daemon Docker Desktop n'est pas demarre.
    echo Veuillez installer et lancer Docker Desktop, puis reessayez.
    pause
    exit /b 1
)

echo [1/3] Verification des volumes persistants de donnees...
echo      Les bases de donnees et les copies d'examen sont conservees de maniere immuable.

echo [2/3] Demarrage des conteneurs (FastAPI + Base relationnelle)...
docker compose up -d

if %ERRORLEVEL% neq 0 (
    echo [ALERTE] Echec de docker compose standard. Tentative avec le profil SQLite autonome...
    docker compose -f deployment/docker-compose.standalone.yml up -d
)

echo [3/3] Attente du controle de sante du serveur...
timeout /t 5 /nobreak >nul

echo.
echo ===============================================================================
echo  SERVEUR D'EXAMEN EN LIGNE ET OPERATIONNEL DANS LE CONTENEUR DOCKER !
echo ===============================================================================
echo.
echo   * URL Locale :              http://localhost:8000
echo   * URL Salle de TP (LAN) :   http://[IP_DU_SERVEUR]:8000
echo   * API Documentation :       http://localhost:8000/docs
echo   * Controle de Sante :       http://localhost:8000/api/health
echo.
echo   Pour arreter le serveur proprement : executez "deployment\stop_app.bat"
echo   Pour mettre a jour l'application :   executez "deployment\update_app.bat"
echo ===============================================================================
echo.
pause

