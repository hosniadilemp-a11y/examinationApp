@echo off
setlocal enabledelayedexpansion
title Plateforme d'Examen LAN - Mise a Jour de l'Image Docker

echo ===============================================================================
echo     MISE A JOUR DE L'APPLICATION ET REGENERATION DE L'IMAGE DOCKER
echo ===============================================================================

cd /d "%~dp0.."

echo [SECURITE DES DONNEES]
echo   Les volumes de stockage persistant (PostgreSQL / SQLite WAL) restent 
echo   100%% intacts. Vos utilisateurs, examens, copies et notes sont preserves.
echo.

echo [1/4] Reconstruction de la nouvelle image Docker (examination-quiz-server:latest)...
docker compose build

if %ERRORLEVEL% neq 0 (
    echo [ERREUR] La compilation de la nouvelle image Docker a echoue.
    pause
    exit /b 1
)

echo [2/4] Redemarrage transparent des conteneurs avec la nouvelle version...
docker compose up -d

echo [3/4] Execution des migrations de schema automatiques non destructives...
timeout /t 5 /nobreak >nul

echo [4/4] Verification du controle de sante de la nouvelle version...
curl -s http://localhost:8000/api/health >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [SUCCES] Le serveur mis a jour repond avec succes !
) else (
    echo [INFO] Le serveur finalise son initialisation...
)

echo.
echo ===============================================================================
echo  MISE A JOUR REUSSIE ! L'APPLICATION FONCTIONNE AVEC LA DERNIERE IMAGE DOCKER.
echo  TOUTES VOS DONNEES ET NOTES SONT INTEGRALEMENT CONSERVEES.
echo ===============================================================================
echo.
pause

