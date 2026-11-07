@echo off
:: Configuration automatique de l'adresse du serveur d'examen
:: A executer en tant qu'Administrateur sur les postes etudiants
echo ========================================================
echo   Configuration de l'acces a la Plateforme d'Examen
echo ========================================================
echo.
set /p SERVER_IP="Entrez l'adresse IP du serveur d'examen : "
set TARGET_DOMAIN=exam.local
set HOSTS_FILE=%SystemRoot%\System32\drivers\etc\hosts

echo %SERVER_IP% %TARGET_DOMAIN% >> "%HOSTS_FILE%"
echo [OK] Redirection ajoutee avec succes !
echo Acces : http://%TARGET_DOMAIN%:8000
pause
