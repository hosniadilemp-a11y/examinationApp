"""
Module de publication mDNS (Multicast DNS / ZeroConf) et de gestion réseau.
Permet aux étudiants d'accéder à l'application via 'http://<nom>.local:8000'
Permet le renommage dynamique à chaud et la détection multi-cartes réseau (Ethernet / Wi-Fi).
"""

import os
import sys
import socket
import json
import logging
import time
import psutil
from typing import Optional, Dict, Any, List
from zeroconf import Zeroconf, ServiceInfo

logger = logging.getLogger("MDNSBroadcaster")

class MDNSBroadcaster:
    def __init__(self, hostname: str = "exam", port: int = 8000, project_root: Optional[str] = None):
        self.port = port
        self.project_root = project_root or self._detect_project_root()
        self.config_file = os.path.join(self.project_root, "data", "app_config.json")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        # Charger la configuration sauvegardée si elle existe
        saved_name = self._load_saved_hostname()
        self.hostname = (saved_name or hostname).rstrip(".local").rstrip(".")
        
        self.selected_ip: Optional[str] = None
        self.zeroconf: Optional[Zeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        self._is_active = False

    def _detect_project_root(self) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _load_saved_hostname(self) -> Optional[str]:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("custom_hostname")
        except Exception:
            pass
        return None

    def _save_hostname(self, name: str):
        try:
            cfg = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["custom_hostname"] = name
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la config mDNS : {e}")

    def list_network_interfaces(self) -> List[Dict[str, Any]]:
        """Liste toutes les interfaces réseau physiques actives avec leurs adresses IPv4."""
        interfaces = []
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for iface_name, addr_list in addrs.items():
                is_up = stats.get(iface_name).isup if iface_name in stats else True
                speed = stats.get(iface_name).speed if iface_name in stats else 0
                for a in addr_list:
                    if a.family == socket.AF_INET and not a.address.startswith("127.") and not a.address.startswith("169.254."):
                        is_ethernet = "ethernet" in iface_name.lower() or "eth" in iface_name.lower() or "local area" in iface_name.lower()
                        is_wifi = "wi-fi" in iface_name.lower() or "wireless" in iface_name.lower() or "wlan" in iface_name.lower()
                        label_type = "Ethernet (Câble)" if is_ethernet else ("Wi-Fi (Sans fil)" if is_wifi else "Réseau")
                        interfaces.append({
                            "name": iface_name,
                            "ip": a.address,
                            "netmask": a.netmask,
                            "is_up": is_up,
                            "speed_mbps": speed,
                            "type_label": label_type,
                            "display": f"{iface_name} ({a.address}) - {label_type}"
                        })
        except Exception as e:
            logger.error(f"Erreur lors de l'énumération des interfaces : {e}")

        # Si aucune interface détectée via psutil, fallback sur socket
        if not interfaces:
            ip = self.get_local_ip()
            interfaces.append({
                "name": "Interface Principale",
                "ip": ip,
                "netmask": "255.255.255.0",
                "is_up": True,
                "speed_mbps": 0,
                "type_label": "Réseau Local",
                "display": f"Interface Principale ({ip})"
            })
        return interfaces

    def get_local_ip(self) -> str:
        """Détecte l'adresse IPv4 locale principale connectée au réseau de la salle."""
        if self.selected_ip:
            return self.selected_ip

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def set_selected_ip(self, ip: str):
        """Permet à l'enseignant de sélectionner manuellement l'adresse IP de diffusion."""
        if self.selected_ip != ip:
            self.selected_ip = ip
            if self._is_active:
                self.restart()

    def start(self) -> Dict[str, Any]:
        """Démarre la publication mDNS sur le réseau local."""
        if self._is_active:
            return {"success": True, "message": "Le diffuseur mDNS est déjà actif."}
            
        local_ip = self.get_local_ip()
        if local_ip.startswith("127."):
            return {
                "success": False,
                "message": "Impossible de déterminer l'adresse IP locale. Vérifiez la connexion réseau."
            }

        try:
            desc = {"path": "/", "app": "ExamQuiz"}
            service_type = "_http._tcp.local."
            service_name = f"{self.hostname}._http._tcp.local."
            server_name = f"{self.hostname}.local."

            ip_bytes = socket.inet_aton(local_ip)

            self.service_info = ServiceInfo(
                type_=service_type,
                name=service_name,
                addresses=[ip_bytes],
                port=self.port,
                properties=desc,
                server=server_name
            )

            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            self._is_active = True
            
            return {
                "success": True,
                "ip": local_ip,
                "domain": f"{self.hostname}.local",
                "full_url": f"http://{self.hostname}.local:{self.port}",
                "message": f"Diffusion active : http://{self.hostname}.local:{self.port}"
            }
        except Exception as e:
            self._is_active = False
            return {
                "success": False,
                "message": f"Erreur lors du démarrage mDNS : {str(e)}"
            }

    def stop(self) -> None:
        """Arrête la publication du service mDNS."""
        if self.zeroconf and self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            except Exception:
                pass
        self._is_active = False
        self.zeroconf = None
        self.service_info = None

    def restart(self) -> Dict[str, Any]:
        """Redémarre la publication mDNS (utile après changement d'IP ou de nom)."""
        self.stop()
        time.sleep(0.1)
        return self.start()

    def set_hostname(self, new_name: str) -> Dict[str, Any]:
        """
        Modifie le nom d'hôte mDNS à chaud.
        Validation : lettres, chiffres, tirets uniquement.
        """
        cleaned = new_name.strip().lower().replace(".local", "").replace("http://", "").replace("https://", "").rstrip("/")
        if not cleaned:
            return {"success": False, "message": "Le nom de domaine ne peut pas être vide."}

        # Vérification des caractères autorisés
        import re
        if not re.match(r"^[a-z0-9][a-z0-9\-]{0,30}[a-z0-9]$", cleaned) and len(cleaned) > 1:
            return {
                "success": False,
                "message": "Nom invalide. Utilisez uniquement des lettres minuscules, chiffres et tirets (ex: 'quiz', 'exam-info')."
            }

        self.hostname = cleaned
        self._save_hostname(cleaned)
        
        if self._is_active:
            res = self.restart()
            if res["success"]:
                return {
                    "success": True,
                    "hostname": cleaned,
                    "domain": f"{cleaned}.local",
                    "full_url": f"http://{cleaned}.local:{self.port}",
                    "message": f"Nouveau nom actif : http://{cleaned}.local:{self.port}"
                }
            return res

        return {
            "success": True,
            "hostname": cleaned,
            "domain": f"{cleaned}.local",
            "full_url": f"http://{cleaned}.local:{self.port}",
            "message": f"Nom enregistré : http://{cleaned}.local:{self.port}"
        }

    def is_running(self) -> bool:
        """Vérifie si le répondeur mDNS est actif."""
        return self._is_active

    def generate_hosts_script(self, output_path: str, domain: Optional[str] = None) -> bool:
        """
        Génère un script batch Windows à copier sur clé USB.
        Permet aux postes étudiants d'associer le domaine '<nom>.local' à l'IP du serveur en 1 clic.
        """
        target_domain = domain or f"{self.hostname}.local"
        server_ip = self.get_local_ip()

        bat_content = f"""@echo off
:: ============================================================================
:: Script de Configuration Réseau Étudiant — Plateforme d'Examen
:: Associe le nom convivial '{target_domain}' à l'adresse IP du serveur : {server_ip}
:: ============================================================================
title Configuration Acces Examen - {target_domain}
echo.
echo ========================================================================
echo   CONFIGURATION DU LIEN CONVIVIAL DE LA SALLE : http://{target_domain}:{self.port}
echo ========================================================================
echo.

:: Vérification des privilèges Administrateur
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Ce script necessite les droits Administrateur pour modifier le fichier hosts.
    echo Clic droit sur ce fichier, puis 'Executer en tant qu'administrateur'.
    echo.
    pause
    exit /b 1
)

set HOSTS_FILE=%SystemRoot%\\System32\\drivers\\etc\\hosts
set DOMAIN={target_domain}
set IP={server_ip}

echo Verification du fichier hosts (%HOSTS_FILE%)...

:: Nettoyage des anciennes entrees pour ce domaine
powershell -NoProfile -Command "(Get-Content '%HOSTS_FILE%') | Where-Object {{$_ -notmatch '%DOMAIN%'}} | Set-Content '%HOSTS_FILE%'"

:: Ajout de l'entree pour l'examen
echo %IP%  %DOMAIN% >> "%HOSTS_FILE%"

echo [SUCCES] L'adresse http://%DOMAIN%:{self.port} pointe desormais vers %IP% !
echo.
echo Test de connectivite...
ping -n 1 %DOMAIN% >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Resolution operationnelle.
) else (
    echo [ATTENTION] Ping non repondu, mais l'entree hosts est appliquee.
)

echo.
echo Ouverture de la plateforme dans le navigateur...
start http://%DOMAIN%:{self.port}
timeout /t 3 >nul
exit /b 0
"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la génération du script hosts : {e}")
            return False
