@echo off
title Chargement de l'Image Docker Hors-Ligne

echo ===============================================================================
echo     CHARGEMENT DE L'IMAGE DOCKER DEPUIS UNE CLE USB / HORS-LIGNE
echo ===============================================================================

cd /d "%~dp0.."

if not exist "deployment\examination-quiz-server.tar" (
    echo [ERREUR] Le fichier "deployment\examination-quiz-server.tar" est introuvable.
    echo Veuillez vous assurer que le fichier tar est present dans le dossier deployment.
    pause
    exit /b 1
)

echo [1/2] Chargement de l'image Docker dans le registre local...
docker load -i deployment\examination-quiz-server.tar

echo [2/2] Demarrage de l'application a partir de l'image chargee...
docker compose up -d

echo.
echo ===============================================================================
echo  IMAGE CHARGEE ET APPLICATION LANCEE SUR LE PORT 8000 !
echo  Accedez a l'application sur : http://localhost:8000
echo ===============================================================================
echo.
pause

