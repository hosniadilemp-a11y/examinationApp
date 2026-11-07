"""
Script d'automatisation de la compilation de l'application Desktop en fichier exécutable Windows autonome (.EXE).
Utilisation : python desktop_admin/build_exe.py
Génère : dist/ExamControlMaster.exe
"""

import os
import sys
import subprocess
import shutil
import time
import customtkinter

def build():
    print("=" * 70)
    print("  COMPILATION DE L'APPLICATION DESKTOP : ExamControlMaster.exe")
    print("=" * 70)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    main_script = os.path.join(current_dir, "main.py")
    dist_dir = os.path.join(project_root, "dist")
    build_dir = os.path.join(project_root, "build")

    ctk_dir = os.path.dirname(customtkinter.__file__)
    print(f"Path CustomTkinter : {ctk_dir}")
    print(f"Script d'entrée    : {main_script}")
    print(f"Dossier de sortie  : {dist_dir}")

    # Commande PyInstaller avec exclusions des bibliothèques data-science lourdes d'Anaconda
    # (numpy, scipy, pandas, matplotlib, mkl) qui ne sont pas utilisées par l'application desktop
    excludes = [
        "numpy", "scipy", "pandas", "matplotlib", "torch", "torchvision",
        "sklearn", "scipy", "IPython", "jupyter", "notebook", "pytest",
        "sphinx", "mkl", "sqlalchemy", "bokeh", "seaborn"
    ]
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "ExamControlMaster",
        "--collect-all", "customtkinter",
        "--collect-all", "zeroconf",
        "--collect-all", "ifaddr",
        "--add-data", f"{ctk_dir};customtkinter",
        "--paths", project_root,
    ]
    
    for exc in excludes:
        cmd.extend(["--exclude-module", exc])
        
    cmd.append(main_script)

    print("\nLancement de PyInstaller...")
    print(" ".join(cmd))
    
    res = subprocess.run(cmd, cwd=project_root)
    if res.returncode == 0:
        exe_path = os.path.join(dist_dir, "ExamControlMaster.exe")
        print("\n" + "=" * 70)
        print("  🎉 COMPILATION RÉUSSIE AVEC SUCCÈS !")
        print(f"  Fichier exécutable disponible ici :")
        print(f"  👉 {exe_path}")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"  Taille de l'exécutable : {size_mb:.2f} Mo")
            
            # Copie dans le package autonome desktop_application avec arrêt préalable des processus résiduels
            target_pkg = os.path.join(project_root, "deployment", "desktop_application", "ExamControlMaster.exe")
            os.makedirs(os.path.dirname(target_pkg), exist_ok=True)
            try:
                shutil.copy2(exe_path, target_pkg)
                print(f"  Copié dans le package autonome : {target_pkg}")
            except PermissionError:
                print("  Tentative d'arrêt de l'instance précédente en cours d'exécution...")
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "ExamControlMaster.exe"], capture_output=True)
                    time.sleep(1.0)
                    shutil.copy2(exe_path, target_pkg)
                    print(f"  Copié avec succès après arrêt du processus : {target_pkg}")
                except Exception as ex:
                    print(f"  Attention lors de la copie : {ex}")
        print("=" * 70)
    else:
        print("\n❌ Erreur lors de la compilation PyInstaller.")
        sys.exit(res.returncode)

if __name__ == "__main__":
    build()

