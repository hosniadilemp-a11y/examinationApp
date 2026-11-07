"""
Module de vérification et d'auto-configuration du Pare-Feu Windows (Port 8000 & 5353 mDNS).
Garantit que les postes étudiants peuvent contacter le serveur d'examen sans être bloqués
par le pare-feu local de la machine enseignante.
"""

import os
import subprocess
import logging
from typing import Dict, Any
from desktop_admin.core.docker_manager import _get_subprocess_flags

logger = logging.getLogger("FirewallChecker")

class FirewallChecker:
    def __init__(self, port: int = 8000, mdns_port: int = 5353):
        self.port = port
        self.mdns_port = mdns_port

    def check_firewall_rules(self) -> Dict[str, Any]:
        """
        Vérifie si les ports 8000 (TCP) et 5353 (UDP) sont autorisés dans le Pare-Feu Windows.
        Exécution 100% silencieuse sans aucune console visible.
        """
        if os.name != "nt":
            return {"port_8000_open": True, "mdns_open": True, "needs_fix": False, "message": "Système non-Windows"}

        flags = _get_subprocess_flags()
        rule_8000_ok = False
        rule_mdns_ok = False

        # Vérification règle 8000 via netsh
        try:
            res_8000 = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", f"name=ExamQuiz Server (Port {self.port})"],
                capture_output=True,
                text=True,
                timeout=4,
                **flags
            )
            if res_8000.returncode == 0 and "ExamQuiz" in res_8000.stdout:
                rule_8000_ok = True
        except Exception:
            pass

        # Vérification règle mDNS via netsh
        try:
            res_mdns = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", f"name=ExamQuiz mDNS (Port {self.mdns_port})"],
                capture_output=True,
                text=True,
                timeout=4,
                **flags
            )
            if res_mdns.returncode == 0 and "ExamQuiz" in res_mdns.stdout:
                rule_mdns_ok = True
        except Exception:
            pass

        needs_fix = not (rule_8000_ok and rule_mdns_ok)

        return {
            "port_8000_rule": rule_8000_ok,
            "mdns_rule": rule_mdns_ok,
            "needs_fix": needs_fix,
            "message": "Ports autorisés dans le pare-feu." if not needs_fix else "Règles d'autorisation manquantes dans le Pare-Feu Windows."
        }

    def configure_firewall_rules(self) -> Dict[str, Any]:
        """
        Ajoute les règles d'autorisation entrantes pour le port 8000 et 5353.
        Si l'application n'est pas lancée en Administrateur, tente une élévation via PowerShell.
        """
        if os.name != "nt":
            return {"success": True, "message": "Non requis hors Windows."}

        flags = _get_subprocess_flags()
        cmd_8000 = f'netsh advfirewall firewall add rule name="ExamQuiz Server (Port {self.port})" dir=in action=allow protocol=TCP localport={self.port} profile=any'
        cmd_mdns = f'netsh advfirewall firewall add rule name="ExamQuiz mDNS (Port {self.mdns_port})" dir=in action=allow protocol=UDP localport={self.mdns_port} profile=any'

        try:
            # 1. Tentative directe
            p1 = subprocess.run(cmd_8000, shell=True, capture_output=True, text=True, timeout=5, **flags)
            p2 = subprocess.run(cmd_mdns, shell=True, capture_output=True, text=True, timeout=5, **flags)

            if p1.returncode == 0 and p2.returncode == 0:
                return {
                    "success": True,
                    "message": f"Règles créées avec succès pour les ports {self.port} (TCP) et {self.mdns_port} (UDP) !"
                }
            
            # 2. Si échec (accès refusé), tentative avec élévation PowerShell RunAs
            ps_cmd = f"Start-Process cmd -ArgumentList '/c {cmd_8000} & {cmd_mdns}' -Verb RunAs -WindowStyle Hidden"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=8, **flags)
            return {
                "success": True,
                "message": f"Demande d'autorisation transmise à Windows pour les ports {self.port} et {self.mdns_port}."
            }
        except Exception as e:
            return {"success": False, "message": f"Erreur lors de la configuration du pare-feu : {str(e)}"}

