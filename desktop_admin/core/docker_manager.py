"""
Module de gestion et de contrôle du moteur Docker.
Permet de vérifier le démon, démarrer/arrêter les conteneurs, charger des images .tar et superviser leur état.
Garantit une exécution 100% silencieuse sans aucune fenêtre de terminal visible sous Windows.
Résilience avancée : élimination des clignotements "off/on" et retours d'état en direct.
"""

import os
import sys
import shutil
import subprocess
import json
import logging
import time
import psutil
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("DockerManager")

def _get_subprocess_flags() -> Dict[str, Any]:
    """Retourne les drapeaux requis pour empêcher l'ouverture d'une fenêtre console sous Windows."""
    kwargs: Dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = si
    return kwargs

class DockerManager:
    def __init__(self, project_root: Optional[str] = None):
        if project_root is not None:
            self.project_root = os.path.abspath(project_root)
        else:
            candidates = []
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                candidates.extend([exe_dir, os.path.abspath(os.path.join(exe_dir, ".."))])
            cwd = os.getcwd()
            candidates.append(cwd)
            code_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates.append(code_dir)

            found_root = None
            for c in candidates:
                if os.path.exists(os.path.join(c, "docker-compose.yml")) or os.path.exists(os.path.join(c, "docker-compose.standalone.yml")):
                    found_root = c
                    break
            self.project_root = found_root or (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else code_dir)

        if os.path.exists(os.path.join(self.project_root, "docker-compose.yml")):
            self.compose_file = os.path.join(self.project_root, "docker-compose.yml")
        elif os.path.exists(os.path.join(self.project_root, "docker-compose.standalone.yml")):
            self.compose_file = os.path.join(self.project_root, "docker-compose.standalone.yml")
        else:
            self.compose_file = os.path.join(self.project_root, "docker-compose.yml")

        self._cached_docker_state: Optional[Dict[str, Any]] = None
        self._cached_docker_time: float = 0.0
        self._consecutive_failures: int = 0
        self.active_operation: Optional[str] = None

    def set_active_operation(self, op: Optional[str]):
        """Définit l'opération en cours (permet de verrouiller l'état et éviter les timeouts parasites)."""
        self.active_operation = op

    def _run_cmd(self, cmd: List[str], timeout: int = 25) -> Dict[str, Any]:
        """Exécute une commande système de manière totalement silencieuse sans fenêtre cmd."""
        flags = _get_subprocess_flags()
        try:
            res = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                **flags
            )
            return {
                "success": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "returncode": -1, "stdout": "", "stderr": f"Délai d'exécution dépassé (> {timeout}s)"}
        except FileNotFoundError:
            return {"success": False, "returncode": -1, "stdout": "", "stderr": f"Exécutable introuvable : {cmd[0]}"}
        except Exception as e:
            return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}

    def is_docker_installed(self) -> bool:
        """Vérifie si la commande docker est présente dans le PATH Windows."""
        return shutil.which("docker") is not None

    def _is_docker_process_running(self) -> bool:
        """Vérifie rapidement si le processus Docker Desktop ou démon est actif sous Windows."""
        target_procs = {
            "docker desktop.exe",
            "dockerd.exe",
            "com.docker.backend.exe",
            "com.docker.proxy.exe",
            "com.docker.service",
            "docker.exe",
            "wsl.exe",
            "wslhost.exe"
        }
        try:
            for p in psutil.process_iter(['name']):
                p_name = p.info.get('name')
                if p_name and p_name.lower() in target_procs:
                    return True
        except Exception:
            pass
        return False

    def is_docker_running(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Vérifie si le démon Docker est actif.
        Résistance accrue aux faux positifs :
        - Si une opération lourde est active (chargement image, compose), Docker est réputé actif.
        - Si les processus Docker Desktop tournent en mémoire, un délai de réponse ne déclare pas Docker 'Éteint'.
        """
        now = time.time()
        if use_cache and self._cached_docker_state and (now - self._cached_docker_time < 3.5):
            return self._cached_docker_state

        if not self.is_docker_installed():
            state = {
                "running": False,
                "installed": False,
                "version": "",
                "message": "Docker CLI n'est pas installé ou absent du PATH Windows."
            }
            self._cached_docker_state = state
            self._cached_docker_time = now
            return state

        # 1. Vérification par processus Windows
        process_up = self._is_docker_process_running()
        if not process_up:
            self._consecutive_failures += 1
            state = {
                "running": False,
                "installed": True,
                "version": "",
                "message": "Docker Desktop n'est pas lancé. Veuillez ouvrir Docker Desktop."
            }
            self._cached_docker_state = state
            self._cached_docker_time = now
            return state

        # 2. Si une opération lourde est déjà en cours d'exécution, Docker est évidemment actif et occupé
        if self.active_operation:
            state = {
                "running": True,
                "installed": True,
                "version": self._cached_docker_state.get("version", "") if self._cached_docker_state else "",
                "message": f"Docker actif — {self.active_operation}"
            }
            self._cached_docker_state = state
            self._cached_docker_time = now
            return state

        # 3. Test de ping du démon Docker avec un timeout généreux (6s)
        res = self._run_cmd(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=6)
        if res["success"] and res["stdout"]:
            self._consecutive_failures = 0
            state = {
                "running": True,
                "installed": True,
                "version": res["stdout"],
                "message": f"Docker Démon opérationnel (v{res['stdout']})"
            }
        else:
            # Si le processus est là mais que docker info tarde, ne pas faire clignoter le statut
            self._consecutive_failures += 1
            if self._consecutive_failures < 3 and self._cached_docker_state and self._cached_docker_state.get("running"):
                # Maintien de l'état précédent en statut occupé
                state = {
                    "running": True,
                    "installed": True,
                    "version": self._cached_docker_state.get("version", ""),
                    "message": "Docker Démon occupé (traitement en cours...)"
                }
            else:
                state = {
                    "running": False,
                    "installed": True,
                    "version": "",
                    "message": "Docker Desktop est en cours de démarrage ou ne répond pas."
                }

        self._cached_docker_state = state
        self._cached_docker_time = now
        return state

    def get_containers_status(self) -> Dict[str, Any]:
        """Récupère l'état d'exécution des conteneurs de la plateforme."""
        if not self.is_docker_running()["running"]:
            return {
                "all_containers": [],
                "app_server_running": False,
                "postgres_running": False,
                "is_fully_operational": False,
                "count": 0
            }

        res = self._run_cmd(["docker", "compose", "ps", "--format", "json"], timeout=8)
        containers = []
        if res["success"] and res["stdout"]:
            for line in res["stdout"].splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        app_running = any("exam_app_server" in c.get("Name", "") and "running" in c.get("State", "").lower() for c in containers)
        db_running = any("exam_postgres_db" in c.get("Name", "") and "running" in c.get("State", "").lower() for c in containers)

        return {
            "all_containers": containers,
            "app_server_running": app_running,
            "postgres_running": db_running,
            "is_fully_operational": app_running and db_running,
            "count": len(containers)
        }

    def start_app(self, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Démarre l'ensemble des conteneurs applicatifs avec retour d'état en direct."""
        if not self.is_docker_running(use_cache=False)["running"]:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Impossible de démarrer : Docker Desktop n'est pas lancé."
            }

        self.set_active_operation("Démarrage des conteneurs (docker compose up)...")
        if progress_callback:
            progress_callback("Lancement des conteneurs PostgreSQL 16 et Serveur FastAPI...")

        res = self._run_cmd(["docker", "compose", "up", "-d"], timeout=90)
        self.set_active_operation(None)

        if res["success"]:
            if progress_callback:
                progress_callback("Conteneurs lancés avec succès. Initialisation des services...")
        else:
            if progress_callback:
                progress_callback(f"Erreur lors du démarrage : {res['stderr']}")

        return res

    def stop_app(self, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Arrête proprement les conteneurs sans détruire les données."""
        if not self.is_docker_running(use_cache=False)["running"]:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Docker n'est pas actif."
            }

        self.set_active_operation("Arrêt des conteneurs (docker compose stop)...")
        if progress_callback:
            progress_callback("Arrêt ordonné des conteneurs applicatifs...")

        res = self._run_cmd(["docker", "compose", "stop"], timeout=45)
        self.set_active_operation(None)

        if res["success"]:
            if progress_callback:
                progress_callback("Conteneurs arrêtés proprement.")
        else:
            if progress_callback:
                progress_callback(f"Erreur lors de l'arrêt : {res['stderr']}")

        return res

    def restart_app(self, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Redémarre tous les conteneurs."""
        if not self.is_docker_running(use_cache=False)["running"]:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Docker n'est pas actif."
            }

        self.set_active_operation("Redémarrage des conteneurs...")
        if progress_callback:
            progress_callback("Redémarrage de l'ensemble des conteneurs...")

        res = self._run_cmd(["docker", "compose", "restart"], timeout=60)
        self.set_active_operation(None)
        return res

    def load_image_from_tar(self, tar_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Charge une image Docker depuis un fichier archive .tar avec streaming des étapes."""
        if not os.path.exists(tar_path):
            return {"success": False, "returncode": -1, "stdout": "", "stderr": f"Fichier introuvable : {tar_path}"}
            
        if not self.is_docker_running(use_cache=False)["running"]:
            return {"success": False, "returncode": -1, "stdout": "", "stderr": "Docker Desktop n'est pas lancé. Démarrez Docker avant d'importer une image."}

        file_size_mb = os.path.getsize(tar_path) / (1024 * 1024)
        file_name = os.path.basename(tar_path)
        
        self.set_active_operation(f"Chargement de l'image ({file_name} - {file_size_mb:.1f} Mo)...")
        if progress_callback:
            progress_callback(f"Ouverture de l'archive '{file_name}' ({file_size_mb:.1f} Mo)...")
            progress_callback("Décompression et transmission des couches au moteur Docker (WSL2)...")

        flags = _get_subprocess_flags()
        start_t = time.time()
        try:
            res = subprocess.run(
                ["docker", "load", "-i", tar_path],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace",
                **flags
            )
            elapsed = time.time() - start_t
            self.set_active_operation(None)

            if res.returncode == 0:
                output = res.stdout.strip()
                if progress_callback:
                    progress_callback(f"Succès ({elapsed:.1f}s) : {output or 'Image chargée'}")
                return {
                    "success": True,
                    "returncode": 0,
                    "stdout": output,
                    "stderr": res.stderr.strip(),
                    "elapsed_sec": round(elapsed, 1)
                }
            else:
                err = res.stderr.strip() or res.stdout.strip()
                if progress_callback:
                    progress_callback(f"Échec ({elapsed:.1f}s) : {err}")
                return {
                    "success": False,
                    "returncode": res.returncode,
                    "stdout": res.stdout.strip(),
                    "stderr": err,
                    "elapsed_sec": round(elapsed, 1)
                }
        except subprocess.TimeoutExpired:
            self.set_active_operation(None)
            if progress_callback:
                progress_callback("Délai d'attente dépassé lors du chargement de l'image (> 300s).")
            return {"success": False, "returncode": -1, "stdout": "", "stderr": "Délai de chargement dépassé (> 300s)."}
        except Exception as e:
            self.set_active_operation(None)
            if progress_callback:
                progress_callback(f"Exception : {str(e)}")
            return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}

    def update_and_recreate(self, tar_path: Optional[str] = None, progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Met à jour l'application avec la nouvelle image et recrée le conteneur."""
        if not self.is_docker_running(use_cache=False)["running"]:
            return {"success": False, "returncode": -1, "stdout": "", "stderr": "Docker Desktop n'est pas lancé. Impossible de mettre à jour."}

        if tar_path:
            load_res = self.load_image_from_tar(tar_path, progress_callback=progress_callback)
            if not load_res["success"]:
                return load_res

        self.set_active_operation("Recréation du conteneur serveur-salle...")
        if progress_callback:
            progress_callback("Recréation du conteneur avec la nouvelle image...")

        res = self._run_cmd(["docker", "compose", "up", "-d", "--force-recreate", "--no-deps", "serveur-salle"], timeout=90)
        self.set_active_operation(None)
        
        if progress_callback:
            if res["success"]:
                progress_callback("Serveur mis à jour et conteneur recréé avec succès !")
            else:
                progress_callback(f"Échec de recréation : {res['stderr']}")

        return res

    def get_container_stats(self) -> Dict[str, Any]:
        """Récupère la consommation CPU et Mémoire en temps réel des conteneurs."""
        if not self.is_docker_running()["running"] or self.active_operation:
            return {}

        res = self._run_cmd([
            "docker", "stats", "--no-stream", "--format", 
            "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}"
        ], timeout=5)
        
        stats = {}
        if res["success"] and res["stdout"]:
            for line in res["stdout"].splitlines():
                parts = line.split("|")
                if len(parts) >= 5:
                    name = parts[0].strip()
                    stats[name] = {
                        "cpu_percent": parts[1].strip(),
                        "mem_usage": parts[2].strip(),
                        "mem_percent": parts[3].strip(),
                        "net_io": parts[4].strip()
                    }
        return stats
