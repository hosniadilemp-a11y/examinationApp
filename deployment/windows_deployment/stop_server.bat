@echo off
echo Arret du serveur ExamQuiz sur le port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>nul
echo Serveur arrete.
