@echo off
title Exportation de l'Image Docker Hors-Ligne (Cle USB)

echo ===============================================================================
echo     EXPORTATION DE L'IMAGE DOCKER POUR DEPLOIEMENT HORS-LIGNE / CLE USB
echo ===============================================================================

cd /d "%~dp0.."

echo [1/2] Construction de l'image la plus recente...
docker compose build

echo [2/2] Exportation de l'image vers le fichier "examination-quiz-server.tar"...
docker save -o deployment\examination-quiz-server.tar examination-quiz-server:latest

echo.
echo ===============================================================================
echo  EXPORTATION TERMINEE !
echo  Fichier genere : deployment\examination-quiz-server.tar
echo  Copiez ce fichier sur votre cle USB pour l'installer sur un serveur hors-ligne.
echo ===============================================================================
echo.
pause

