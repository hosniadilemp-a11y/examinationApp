"""
Point d'entrée principal de l'application Desktop de supervision et cartographie réseau.
Lancement : python desktop_admin/main.py ou ExamControlMaster.exe
"""

import sys
import os
import traceback
import logging

# Détermination du répertoire de travail (compatible PyInstaller et standard)
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.abspath(os.path.join(app_dir, "..")) if not getattr(sys, 'frozen', False) else app_dir
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configuration du logging sur fichier local
log_file = os.path.join(app_dir, "desktop_admin.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("ExamMasterMain")
logger.info("Démarrage de Exam Control Master...")

try:
    from desktop_admin.ui.app_window import ExamMasterApp
except Exception as e:
    logger.error(f"Erreur d'importation de l'interface : {e}\n{traceback.format_exc()}")
    try:
        import tkinter.messagebox as mb
        mb.showerror("Erreur d'initialisation", f"Impossible d'importer l'interface :\n{e}")
    except Exception:
        pass
    sys.exit(1)

def main():
    try:
        logger.info("Initialisation de la fenêtre principale ExamMasterApp...")
        app = ExamMasterApp()
        
        # Arrêt propre des services lors de la fermeture de la fenêtre
        def on_closing():
            try:
                logger.info("Fermeture demandée par l'utilisateur.")
                app.auto_refresh_active = False
                if hasattr(app, 'mdns') and app.mdns:
                    app.mdns.stop()
            except Exception:
                pass
            app.destroy()

        app.protocol("WM_DELETE_WINDOW", on_closing)
        logger.info("Lancement de la boucle événementielle GUI (mainloop)...")
        app.mainloop()
        logger.info("Application terminée normalement.")
    except Exception as e:
        err_msg = f"Erreur critique lors de l'exécution de l'application :\n{e}\n\n{traceback.format_exc()}"
        logger.error(err_msg)
        try:
            import tkinter.messagebox as mb
            mb.showerror("Erreur Critique - Exam Control Master", f"L'application a rencontré une erreur :\n{e}\n\nConsultez le fichier desktop_admin.log.")
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()

