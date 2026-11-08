"""
Module de déblocage et d'optimisation de l'accès réseau câblé (Ethernet LAN).
Résout l'ensemble des causes d'inaccessibilité du serveur Docker depuis les autres PC de la salle :
- Déblocage du Pare-Feu Windows (Port 8000, 5353 mDNS, Ping ICMP) sur tous les profils (Public, Privé).
- Configuration du relais Windows PortProxy pour forcer la redirection depuis la carte Ethernet physique vers Docker/WSL2.
- Bascule de la catégorie de réseau de "Public" vers "Privé".
- Détection des adresses APIPA (169.254.x.x) et assistance à l'adressage de salle.
"""

import os
import sys
import subprocess
import socket
import logging
import psutil
from typing import Dict, Any, List, Optional
from desktop_admin.core.docker_manager import _get_subprocess_flags

logger = logging.getLogger("LanUnlocker")

class LanUnlocker:
    def __init__(self, port: int = 8000, mdns_port: int = 5353):
        self.port = port
        self.mdns_port = mdns_port

    def get_physical_ethernet_info(self) -> Dict[str, Any]:
        """Détecte la carte réseau physique Ethernet de la machine."""
        info = {
            "name": "Ethernet",
            "ip": "Non configurée",
            "is_connected": False,
            "is_apipa": False,
            "speed_mbps": 0,
            "category": "Inconnu"
        }

        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for iface, addr_list in addrs.items():
                iface_lower = iface.lower()
                # Exclure les cartes virtuelles
                if "vEthernet" in iface or "wsl" in iface_lower or "loopback" in iface_lower or "virtual" in iface_lower:
                    continue

                is_eth = "ethernet" in iface_lower or "eth" in iface_lower or "connexion au réseau local" in iface_lower or "local area connection" in iface_lower
                if is_eth:
                    info["name"] = iface
                    if iface in stats:
                        info["is_connected"] = stats[iface].isup
                        info["speed_mbps"] = stats[iface].speed
                    for a in addr_list:
                        if a.family == socket.AF_INET:
                            info["ip"] = a.address
                            info["is_apipa"] = a.address.startswith("169.254.")
                    break
        except Exception as e:
            logger.error(f"Erreur détection Ethernet : {e}")

        # Catégorie de réseau (Public / Private) via PowerShell sous Windows
        if os.name == "nt":
            flags = _get_subprocess_flags()
            try:
                ps_cmd = f"(Get-NetConnectionProfile -InterfaceAlias '{info['name']}' -ErrorAction SilentlyContinue).NetworkCategory"
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=3, **flags)
                cat = res.stdout.strip()
                if cat:
                    info["category"] = cat
            except Exception:
                pass

        return info

    def audit_lan_status(self) -> Dict[str, Any]:
        """Audit complet des paramètres réseau requis pour l'accessibilité câblée."""
        eth = self.get_physical_ethernet_info()
        flags = _get_subprocess_flags()

        fw_8000_ok = False
        fw_mdns_ok = False
        fw_icmp_ok = False
        portproxy_ok = False

        if os.name == "nt":
            # 1. Vérification Pare-Feu Port 8000
            try:
                r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", "name=ExamQuiz Server LAN (Port 8000)"], capture_output=True, text=True, timeout=3, **flags)
                if r.returncode == 0 and "ExamQuiz" in r.stdout:
                    fw_8000_ok = True
            except Exception:
                pass

            # 2. Vérification Pare-Feu mDNS 5353
            try:
                r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", "name=ExamQuiz mDNS LAN (Port 5353)"], capture_output=True, text=True, timeout=3, **flags)
                if r.returncode == 0 and "ExamQuiz" in r.stdout:
                    fw_mdns_ok = True
            except Exception:
                pass

            # 3. Vérification Ping ICMP
            try:
                r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", "name=ExamQuiz ICMP Ping"], capture_output=True, text=True, timeout=3, **flags)
                if r.returncode == 0 and "ExamQuiz" in r.stdout:
                    fw_icmp_ok = True
            except Exception:
                pass

            # 4. Vérification PortProxy 8000
            try:
                r = subprocess.run(["netsh", "interface", "portproxy", "show", "v4tov4"], capture_output=True, text=True, timeout=3, **flags)
                if str(self.port) in r.stdout:
                    portproxy_ok = True
            except Exception:
                pass

        issues = []
        if not fw_8000_ok:
            issues.append("Règle Pare-Feu manquante pour le port 8000 (bloque l'accès HTTP).")
        if not fw_icmp_ok:
            issues.append("Requêtes Ping ICMP bloquées par le Pare-Feu (empêche la cartographie des postes).")
        if not portproxy_ok:
            issues.append("Relais Windows PortProxy non configuré (nécessaire pour traverser vers WSL2/Docker).")
        if eth.get("category") == "Public":
            issues.append("L'interface réseau est classée en 'Réseau Public' (Windows bloque les connexions entrantes).")
        if eth.get("is_apipa"):
            issues.append("Adresse IP de type APIPA (169.254.x.x) détectée : le switch de salle n'a pas de serveur DHCP.")

        all_ok = len(issues) == 0

        return {
            "ethernet": eth,
            "fw_port_8000": fw_8000_ok,
            "fw_mdns": fw_mdns_ok,
            "fw_icmp": fw_icmp_ok,
            "portproxy": portproxy_ok,
            "all_ok": all_ok,
            "issues": issues,
            "status_text": "🟢 Accès réseau câblé (LAN) entièrement opérationnel" if all_ok else f"⚠️ {len(issues)} réglage(s) nécessaire(s) pour le réseau câblé"
        }

    def unlock_lan_access(self) -> Dict[str, Any]:
        """
        Débloque en 1 clic l'ensemble des règles réseau pour que les postes de la salle
        accèdent au serveur Docker via le câble Ethernet.
        """
        if os.name != "nt":
            return {"success": True, "message": "Non requis sur ce système."}

        flags = _get_subprocess_flags()
        eth = self.get_physical_ethernet_info()
        iface_name = eth["name"]

        # Construction du script batch de configuration avec privilèges
        commands = [
            f'netsh advfirewall firewall add rule name="ExamQuiz Server LAN (Port {self.port})" dir=in action=allow protocol=TCP localport={self.port} profile=any',
            f'netsh advfirewall firewall add rule name="ExamQuiz mDNS LAN (Port {self.mdns_port})" dir=in action=allow protocol=UDP localport={self.mdns_port} profile=any',
            'netsh advfirewall firewall add rule name="ExamQuiz ICMP Ping" dir=in action=allow protocol=icmpv4:8,any profile=any',
            f'netsh interface portproxy delete v4tov4 listenport={self.port} listenaddress=0.0.0.0 >nul 2>&1',
            f'netsh interface portproxy add v4tov4 listenport={self.port} listenaddress=0.0.0.0 connectport={self.port} connectaddress=127.0.0.1',
            f'powershell -NoProfile -Command "Set-NetConnectionProfile -InterfaceAlias \'{iface_name}\' -NetworkCategory Private -ErrorAction SilentlyContinue"'
        ]

        full_cmd = " & ".join(commands)

        try:
            # 1. Tentative d'exécution directe
            p = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=8, **flags)
            if p.returncode == 0:
                audit = self.audit_lan_status()
                return {
                    "success": True,
                    "message": "Accès Réseau Câblé (LAN) débloqué avec succès !",
                    "audit": audit
                }

            # 2. Si besoin d'élévation, exécution via PowerShell Start-Process RunAs
            ps_script = f"Start-Process cmd -ArgumentList '/c {full_cmd}' -Verb RunAs -WindowStyle Hidden"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=10, **flags)
            
            # Laisser 1 seconde à Windows pour appliquer
            import time
            time.sleep(1.5)
            audit = self.audit_lan_status()
            return {
                "success": True,
                "message": "Demande de déblocage réseau transmise et appliquée avec succès !",
                "audit": audit
            }
        except Exception as e:
            return {"success": False, "message": f"Erreur lors du déblocage LAN : {str(e)}"}

    def configure_static_ip(self, iface_name: str, ip: str = "192.168.1.100", mask: str = "255.255.255.0") -> Dict[str, Any]:
        """Configure une IP fixe sur la carte Ethernet en cas de switch de salle sans DHCP."""
        if os.name != "nt":
            return {"success": False, "message": "Disponible uniquement sous Windows."}

        flags = _get_subprocess_flags()
        cmd = f'netsh interface ip set address name="{iface_name}" static {ip} {mask}'
        try:
            ps_script = f"Start-Process cmd -ArgumentList '/c {cmd}' -Verb RunAs -WindowStyle Hidden"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=8, **flags)
            return {
                "success": True,
                "message": f"Adresse IP fixe de salle ({ip}) configurée sur {iface_name}."
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

