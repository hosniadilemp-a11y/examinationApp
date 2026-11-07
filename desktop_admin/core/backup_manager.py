"""
Module de gestion des sauvegardes et points de restauration instantanés (Snapshots 1-Clic).
Permet de créer un instantané complet de la base de données PostgreSQL 16 ou SQLite
avant le début d'une épreuve pour garantir zéro perte de données.
"""

import os
import sys
import time
import subprocess
import json
import shutil
import logging
from typing import Dict, Any, List, Optional
from desktop_admin.core.docker_manager import DockerManager, _get_subprocess_flags

logger = logging.getLogger("BackupManager")

class BackupManager:
    def __init__(self, project_root: Optional[str] = None):
        self.docker_mgr = DockerManager(project_root=project_root)
        self.project_root = self.docker_mgr.project_root
        self.snapshot_dir = os.path.join(self.project_root, "backups", "snapshots")
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def create_snapshot(self, label: str = "Avant_Epreuve") -> Dict[str, Any]:
        """Crée un point de restauration complet horodaté de la base de données."""
        now_str = time.strftime("%Y%m%d_%H%M%S")
        sanitized_label = "".join(c for c in label if c.isalnum() or c in ("_", "-"))
        filename = f"snapshot_{now_str}_{sanitized_label}.sql"
        filepath = os.path.join(self.snapshot_dir, filename)

        flags = _get_subprocess_flags()
        docker_status = self.docker_mgr.is_docker_running()

        # 1. Tentative d'export via pg_dump dans le conteneur Docker PostgreSQL
        if docker_status.get("running"):
            c_status = self.docker_mgr.get_containers_status()
            if c_status.get("postgres_running"):
                try:
                    cmd = ["docker", "exec", "exam_postgres_db", "pg_dump", "-U", "examuser", "-d", "examquiz"]
                    with open(filepath, "w", encoding="utf-8", errors="replace") as out_f:
                        res = subprocess.run(
                            cmd,
                            stdout=out_f,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=60,
                            **flags
                        )
                    if res.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        size_kb = round(os.path.getsize(filepath) / 1024, 1)
                        meta = {
                            "filename": filename,
                            "filepath": filepath,
                            "label": label,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "size_kb": size_kb,
                            "type": "PostgreSQL 16 (pg_dump)"
                        }
                        self._save_meta(meta)
                        return {
                            "success": True,
                            "message": f"Point de restauration créé avec succès ({size_kb} Ko).",
                            "meta": meta
                        }
                except Exception as e:
                    logger.warning(f"pg_dump a échoué, tentative de fallback : {e}")

        # 2. Fallback : Sauvegarde des fichiers locaux SQLite s'ils existent
        sqlite_candidates = [
            os.path.join(self.project_root, "examination.db"),
            os.path.join(self.project_root, "data", "examination.db"),
            os.path.join(self.project_root, "backend", "examination.db"),
            os.path.join(self.project_root, "app.db")
        ]
        found_sqlite = [f for f in sqlite_candidates if os.path.exists(f)]
        if found_sqlite:
            src = found_sqlite[0]
            dst_name = f"snapshot_{now_str}_{sanitized_label}.db"
            dst_path = os.path.join(self.snapshot_dir, dst_name)
            try:
                shutil.copy2(src, dst_path)
                size_kb = round(os.path.getsize(dst_path) / 1024, 1)
                meta = {
                    "filename": dst_name,
                    "filepath": dst_path,
                    "label": label,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size_kb": size_kb,
                    "type": "SQLite Local Backup"
                }
                self._save_meta(meta)
                return {
                    "success": True,
                    "message": f"Snapshot SQLite sauvegardé avec succès ({size_kb} Ko).",
                    "meta": meta
                }
            except Exception as e:
                return {"success": False, "message": f"Échec de sauvegarde SQLite : {str(e)}"}

        # 3. Si aucun serveur actif n'a pu être dumpé
        # On crée un snapshot de secours des fichiers json du dossier backups/
        json_backups = os.path.join(self.project_root, "backups", "all_exams_backup.json")
        if os.path.exists(json_backups):
            dst_json = os.path.join(self.snapshot_dir, f"snapshot_{now_str}_{sanitized_label}_exams.json")
            shutil.copy2(json_backups, dst_json)
            size_kb = round(os.path.getsize(dst_json) / 1024, 1)
            meta = {
                "filename": os.path.basename(dst_json),
                "filepath": dst_json,
                "label": label,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "size_kb": size_kb,
                "type": "Banque d'Examens JSON"
            }
            self._save_meta(meta)
            return {
                "success": True,
                "message": f"Snapshot de la banque d'examens créé ({size_kb} Ko). Note : démarrez PostgreSQL pour un dump SQL complet.",
                "meta": meta
            }

        return {
            "success": False,
            "message": "Impossible de créer le snapshot : le conteneur PostgreSQL n'est pas démarré."
        }

    def _save_meta(self, meta: Dict[str, Any]):
        meta_file = os.path.join(self.snapshot_dir, "snapshots_index.json")
        try:
            items = []
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
            items.insert(0, meta)
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur d'enregistrement de l'index des snapshots : {e}")

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Renvoie la liste des snapshots ordonnés du plus récent au plus ancien."""
        meta_file = os.path.join(self.snapshot_dir, "snapshots_index.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    # Filtrer les fichiers encore existants sur disque
                    return [it for it in items if os.path.exists(it.get("filepath", ""))]
            except Exception:
                pass

        # Balayage du dossier si l'index n'existe pas
        res = []
        for f in os.listdir(self.snapshot_dir):
            if f.startswith("snapshot_") and (f.endswith(".sql") or f.endswith(".db") or f.endswith(".json")):
                fp = os.path.join(self.snapshot_dir, f)
                size_kb = round(os.path.getsize(fp) / 1024, 1)
                mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(fp)))
                res.append({
                    "filename": f,
                    "filepath": fp,
                    "label": "Sauvegarde Manuelle",
                    "timestamp": mtime,
                    "size_kb": size_kb,
                    "type": "SQL" if f.endswith(".sql") else ("DB" if f.endswith(".db") else "JSON")
                })
        res.sort(key=lambda x: x["timestamp"], reverse=True)
        return res

