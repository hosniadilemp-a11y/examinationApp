@echo off
chcp 65001 >nul
set TARGET_DIR=%~dp0extracted_app
echo Extraction de l'image Windows dans %TARGET_DIR% ...
powershell -Command "Expand-Archive -Force '%~dp0image\examquiz-windows-release.zip' '%TARGET_DIR%'"
cd /d "%TARGET_DIR%"
call deployment\windows\install_and_deploy.bat
