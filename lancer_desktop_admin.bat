@echo off
title EXAM CONTROL MASTER - Supervision Reseau & Docker
echo ========================================================
echo    Lancement de l'Application Desktop EXAM CONTROL MASTER
echo ========================================================
echo.

if exist "deployment\desktop_application\ExamControlMaster.exe" (
    echo Demarrage de l'executable autonome optimise (20 Mo)...
    start "" "deployment\desktop_application\ExamControlMaster.exe"
) else if exist "dist\ExamControlMaster.exe" (
    echo Demarrage de l'executable dist...
    start "" "dist\ExamControlMaster.exe"
) else (
    echo Lancement via Python...
    start "" python desktop_admin\main.py
)

