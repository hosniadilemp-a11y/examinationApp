@echo off
title Plateforme d'Examen LAN - Arret Docker

echo ===============================================================================
echo          ARRET PROPRE DU SERVEUR D'EXAMEN ET D'ENTRAINEMENT (DOCKER)
echo ===============================================================================

cd /d "%~dp0.."

echo [1/2] Arret des conteneurs en cours d'execution...
docker compose down

if %ERRORLEVEL% neq 0 (
    docker compose -f deployment/docker-compose.standalone.yml down
)

echo [2/2] Donnees sauvegardees. Tous les volumes de bases de donnees restent intacts.
echo.
echo ===============================================================================
echo  Le serveur d'examen a ete arrete sans aucune perte de donnees.
echo ===============================================================================
echo.
pause

