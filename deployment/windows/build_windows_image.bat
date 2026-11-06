@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
echo Generation de l'image finale Windows dans deployment\windows\image\examquiz-windows-release.zip ...
python -c "import zipfile, os; zf=zipfile.ZipFile('deployment/windows/image/examquiz-windows-release.zip','w',zipfile.ZIP_DEFLATED); [zf.write(os.path.join(r,f), os.path.relpath(os.path.join(r,f), '.')) for d in ['backend','frontend','scripts','archive_data','deployment/windows'] for r,_,fs in os.walk(d) if '__pycache__' not in r and 'image' not in r for f in fs]; [zf.write(f,f) for f in ['requirements.txt','logins.txt','deploy.sh','deploy.bash','setup_and_seed.sh','exam_app.db'] if os.path.exists(f)]; zf.close()"
echo Image finale Windows prete : deployment\windows\image\examquiz-windows-release.zip
