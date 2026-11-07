"""
Module de diagnostic de santé, de télémétrie serveur et de résolution d'incidents.
Surveille CPU, RAM, ports, endpoint API, base de données et Pare-Feu Windows.
Résolution automatisée en 1 clic pour les incidents courants.
"""

import os
import time
import socket
import psutil
import requests
from typing import Dict, Any, List, Optional
from desktop_admin.core.docker_manager import DockerManager
from desktop_admin.core.firewall_checker import FirewallChecker

class HealthChecker:
    def __init__(self, host: str = "127.0.0.1", port: int = 8000, db_port: int = 5432):
        self.host = host
        self.port = port
        self.db_port = db_port
        self.docker_mgr = DockerManager()
        self.firewall_checker = FirewallChecker(port=port, mdns_port=5353)
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.time()
        self._total_requests_tracked = 0

    def check_port_open(self, host: str, port: int, timeout: float = 0.8) -> bool:
        """Teste si un port TCP est ouvert et accepte des connexions."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                s.connect((host, port))
                return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                return False

    def find_process_on_port(self, port: int) -> Optional[Dict[str, Any]]:
        """Trouve le processus Windows écoutant sur un port spécifique."""
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    pid = conn.pid
                    if pid:
                        try:
                            p = psutil.Process(pid)
                            return {
                                "pid": pid,
                                "name": p.name(),
                                "exe": p.exe() if hasattr(p, "exe") else "N/A"
                            }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            return {"pid": pid, "name": "Inconnu (Protégé)", "exe": "N/A"}
        except Exception:
            pass
        return None

    def kill_process_on_port(self, port: int) -> Dict[str, Any]:
        """Libère un port bloqué en terminant le processus parasite."""
        proc_info = self.find_process_on_port(port)
        if not proc_info:
            return {"success": True, "message": f"Aucun processus ne bloque le port {port}."}
            
        pid = proc_info["pid"]
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=3)
            return {"success": True, "message": f"Processus {proc_info['name']} (PID {pid}) arrêté avec succès."}
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            try:
                p.kill()
                return {"success": True, "message": f"Processus PID {pid} forcé à l'arrêt."}
            except Exception as e:
                return {"success": False, "message": f"Impossible d'arrêter le PID {pid} : {str(e)}"}
        except psutil.AccessDenied:
            return {"success": False, "message": f"Accès refusé pour arrêter le PID {pid}. Lancez l'application en Administrateur."}

    def get_server_telemetry(self) -> Dict[str, Any]:
        """Mesure la télémétrie complète : CPU, RAM, Disque, I/O Réseau et conteneurs."""
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        
        now = time.time()
        curr_net = psutil.net_io_counters()
        dt = max(0.1, now - self._last_net_time)
        bytes_sent_per_sec = (curr_net.bytes_sent - self._last_net_io.bytes_sent) / dt
        bytes_recv_per_sec = (curr_net.bytes_recv - self._last_net_io.bytes_recv) / dt
        self._last_net_io = curr_net
        self._last_net_time = now

        try:
            disk = psutil.disk_usage(os.getcwd())
            disk_free_gb = round(disk.free / (1024**3), 1)
            disk_pct = disk.percent
        except Exception:
            disk_free_gb = 0.0
            disk_pct = 0.0

        container_stats = {}
        try:
            if self.docker_mgr.is_docker_running()["running"] and not self.docker_mgr.active_operation:
                container_stats = self.docker_mgr.get_container_stats()
        except Exception:
            pass

        api_latency_ms = None
        api_online = False
        api_data = {}
        try:
            start_t = time.perf_counter()
            r = requests.get(f"http://{self.host}:{self.port}/api/health", timeout=1.2)
            api_latency_ms = round((time.perf_counter() - start_t) * 1000, 1)
            if r.status_code == 200:
                api_online = True
                self._total_requests_tracked += 1
                try:
                    api_data = r.json()
                except Exception:
                    pass
        except Exception:
            pass

        db_online = self.check_port_open(self.host, self.db_port)

        return {
            "timestamp": now,
            "host_cpu_percent": cpu_pct,
            "host_mem_used_mb": round(mem.used / (1024**2), 1),
            "host_mem_total_mb": round(mem.total / (1024**2), 1),
            "host_mem_percent": mem.percent,
            "disk_free_gb": disk_free_gb,
            "disk_percent": disk_pct,
            "net_kb_recv_per_sec": round(bytes_recv_per_sec / 1024, 1),
            "net_kb_sent_per_sec": round(bytes_sent_per_sec / 1024, 1),
            "total_requests_received": self._total_requests_tracked,
            "api_online": api_online,
            "api_latency_ms": api_latency_ms,
            "api_data": api_data,
            "db_online": db_online,
            "container_stats": container_stats
        }

    def run_full_diagnosis(self) -> List[Dict[str, Any]]:
        """
        Analyse l'état du système et génère une liste de diagnostics explicatifs
        avec 'Ce qui ne va pas' et 'Comment le résoudre'.
        """
        items = []

        # 1. Vérification Docker
        docker_info = self.docker_mgr.is_docker_running()
        if not docker_info["installed"]:
            items.append({
                "component": "Docker",
                "status": "critical",
                "title": "Docker n'est pas installé sur ce système",
                "detail": "La commande 'docker' est introuvable dans le PATH Windows.",
                "solution": "Installez Docker Desktop pour Windows avec le backend WSL2.",
                "auto_fixable": False,
                "action_code": None
            })
        elif not docker_info["running"]:
            items.append({
                "component": "Docker Desktop",
                "status": "warning",
                "title": "Docker Desktop n'est pas démarré",
                "detail": "Docker Desktop est requis pour faire tourner le serveur et la base PostgreSQL.",
                "solution": "Veuillez lancer l'application Docker Desktop depuis le menu Démarrer de Windows.",
                "auto_fixable": False,
                "action_code": None
            })
        else:
            items.append({
                "component": "Docker",
                "status": "ok",
                "title": "Moteur Docker actif",
                "detail": f"{docker_info.get('message', 'Opérationnel')}",
                "solution": "Aucune action requise.",
                "auto_fixable": False,
                "action_code": None
            })

        # 2. Vérification des conteneurs
        if docker_info["running"]:
            c_status = self.docker_mgr.get_containers_status()
            if not c_status["is_fully_operational"]:
                if not c_status["app_server_running"]:
                    items.append({
                        "component": "Serveur Applicatif",
                        "status": "warning",
                        "title": "Conteneur Serveur Salle arrêté",
                        "detail": "Le conteneur exam_app_server (FastAPI) n'est pas en cours d'exécution.",
                        "solution": "Cliquez sur '▶ DÉMARRER LE SERVEUR' ci-dessus pour lancer les services.",
                        "auto_fixable": True,
                        "action_code": "start_app"
                    })
                if not c_status["postgres_running"]:
                    items.append({
                        "component": "Base de Données",
                        "status": "warning",
                        "title": "Conteneur PostgreSQL arrêté",
                        "detail": "Le conteneur exam_postgres_db n'est pas démarré.",
                        "solution": "Cliquez sur '▶ DÉMARRER LE SERVEUR' pour monter la base de données.",
                        "auto_fixable": True,
                        "action_code": "start_app"
                    })
            else:
                items.append({
                    "component": "Conteneurs",
                    "status": "ok",
                    "title": "Conteneurs FastAPI et PostgreSQL opérationnels",
                    "detail": "exam_app_server et exam_postgres_db sont en cours d'exécution.",
                    "solution": "Aucune action requise.",
                    "auto_fixable": False,
                    "action_code": None
                })

        # 3. Vérification des ports
        port_8000_open = self.check_port_open(self.host, self.port)
        if port_8000_open:
            items.append({
                "component": "Port 8000 (API)",
                "status": "ok",
                "title": f"Port {self.port} actif et accessible",
                "detail": f"Le serveur écoute sur http://{self.host}:{self.port}",
                "solution": "Aucune action requise.",
                "auto_fixable": False,
                "action_code": None
            })
        else:
            p_on_8000 = self.find_process_on_port(self.port)
            if p_on_8000:
                items.append({
                    "component": "Port 8000 (API)",
                    "status": "critical",
                    "title": f"Conflit de port sur le port {self.port}",
                    "detail": f"Le processus '{p_on_8000['name']}' (PID {p_on_8000['pid']}) occupe le port de l'examen.",
                    "solution": f"Cliquez sur 'Libérer le port {self.port}' pour terminer le processus en conflit.",
                    "auto_fixable": True,
                    "action_code": "kill_port_8000"
                })
            else:
                items.append({
                    "component": "Port 8000 (API)",
                    "status": "warning",
                    "title": f"Le port {self.port} est fermé",
                    "detail": "Le serveur FastAPI n'est pas encore démarré.",
                    "solution": "Cliquez sur '▶ DÉMARRER LE SERVEUR' pour ouvrir le port d'écoute.",
                    "auto_fixable": True,
                    "action_code": "start_app"
                })

        # 4. Vérification PostgreSQL Port 5432
        port_5432_open = self.check_port_open(self.host, self.db_port)
        if port_5432_open:
            items.append({
                "component": "Base PostgreSQL (5432)",
                "status": "ok",
                "title": "PostgreSQL 16 accessible",
                "detail": "Connexions prêtes.",
                "solution": "Aucune action requise.",
                "auto_fixable": False,
                "action_code": None
            })

        # 5. Vérification Pare-Feu Windows (Item 8)
        fw = self.firewall_checker.check_firewall_rules()
        if fw.get("needs_fix"):
            items.append({
                "component": "Pare-Feu Windows",
                "status": "warning",
                "title": "Autorisation Pare-Feu recommandée pour la salle",
                "detail": "Les règles d'ouverture du port 8000 et mDNS 5353 ne sont pas encore enregistrées.",
                "solution": "Cliquez sur 'Autoriser' pour inscrire les règles d'autorisation dans Windows Defender.",
                "auto_fixable": True,
                "action_code": "fix_firewall"
            })
        else:
            items.append({
                "component": "Pare-Feu Windows",
                "status": "ok",
                "title": "Ports d'examen autorisés dans le Pare-Feu",
                "detail": "Port 8000 (TCP) et mDNS 5353 (UDP) autorisés.",
                "solution": "Aucune action requise.",
                "auto_fixable": False,
                "action_code": None
            })

        # 6. Espace disque
        try:
            disk = psutil.disk_usage(os.getcwd())
            free_gb = disk.free / (1024**3)
            if free_gb < 1.0:
                items.append({
                    "component": "Disque",
                    "status": "critical",
                    "title": "Espace disque critique",
                    "detail": f"Il ne reste que {free_gb:.1f} Go d'espace libre sur le volume principal.",
                    "solution": "Libérez de l'espace disque.",
                    "auto_fixable": False,
                    "action_code": None
                })
            elif free_gb < 3.0:
                items.append({
                    "component": "Disque",
                    "status": "warning",
                    "title": "Espace disque faible",
                    "detail": f"{free_gb:.1f} Go disponibles.",
                    "solution": "Surveillez l'espace avant de lancer une épreuve volumineuse.",
                    "auto_fixable": False,
                    "action_code": None
                })
        except Exception:
            pass

        return items
