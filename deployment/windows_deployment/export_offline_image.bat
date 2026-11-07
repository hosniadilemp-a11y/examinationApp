@echo off
title Exportation de l'Image Docker Hors-Ligne (Cle USB)

echo ===============================================================================
echo     EXPORTATION DE L'IMAGE DOCKER POUR DEPLOIEMENT HORS-LIGNE / CLE USB
echo ===============================================================================

cd /d "%~dp0..\..\.."

echo [1/2] Construction de l'image Docker de l'application...
docker compose build

echo [2/2] Exportation de l'image vers "deployment\images_hors_ligne\examination-quiz-server.tar"...
if not exist "deployment\images_hors_ligne" mkdir "deployment\images_hors_ligne"
docker save -o "deployment\images_hors_ligne\examination-quiz-server.tar" examination-quiz-server:latest

echo.
echo ===============================================================================
echo  EXPORTATION TERMINEE !
echo  Fichier genere : deployment\images_hors_ligne\examination-quiz-server.tar
echo  Copiez ce fichier .tar sur votre cle USB pour installer l'application hors-ligne.
echo ===============================================================================
echo.
pause

