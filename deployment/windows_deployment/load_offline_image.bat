@echo off
title Chargement de l'Image Docker Hors-Ligne

echo ===============================================================================
echo     CHARGEMENT DE L'IMAGE DOCKER DEPUIS UNE CLE USB / HORS-LIGNE
echo ===============================================================================

cd /d "%~dp0..\..\.."

set TAR_FILE=deployment\images_hors_ligne\examination-quiz-server.tar

if not exist "%TAR_FILE%" (
    echo [ERREUR] Le fichier "%TAR_FILE%" est introuvable.
    echo Veuillez placer votre fichier .tar dans le dossier deployment\images_hors_ligne\
    pause
    exit /b 1
)

echo [1/2] Chargement de l'image Docker dans le moteur local...
docker load -i "%TAR_FILE%"

echo [2/2] Demarrage des conteneurs applicatifs...
docker compose up -d

echo.
echo ===============================================================================
echo  IMAGE CHARGEE ET APPLICATION LANCEE SUR LE PORT 8000 !
echo  Accedez a l'application sur : http://localhost:8000
echo ===============================================================================
echo.
pause

