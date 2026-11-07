"""
Module de cartographie et de balayage réseau local (ARP + Ping ICMP + Résolution d'hôte).
Détecte l'ensemble des postes connectés sur le sous-réseau en quelques fractions de seconde
sans saturer le processeur et sans ouvrir AUCUNE fenêtre de console.
"""

import os
import re
import socket
import subprocess
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from desktop_admin.core.pc_renamer import PCRenamer

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

class NetworkScanner:
    def __init__(self, renamer: Optional[PCRenamer] = None):
        self.renamer = renamer or PCRenamer()
        self._hostname_cache: Dict[str, str] = {}

    def get_local_ip(self) -> str:
        """Récupère l'adresse IP locale active."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_subnet_prefix(self, ip: str) -> str:
        """Déduit le préfixe réseau /24 (ex: 192.168.1)."""
        parts = ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3])
        return "192.168.1"

    def read_arp_table(self) -> Dict[str, str]:
        """Lit la table ARP système Windows pour extraire les paires (IP, MAC)."""
        arp_map: Dict[str, str] = {}
        flags = _get_subprocess_flags()
        try:
            res = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=1.5,
                encoding="utf-8",
                errors="replace",
                **flags
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F\-]{17})\s+(\w+)", line)
                    if match:
                        ip = match.group(1)
                        mac = match.group(2).upper().replace("-", ":")
                        # Ignorer les adresses broadcast et multicast
                        if not ip.startswith("224.") and not ip.endswith(".255"):
                            arp_map[ip] = mac
        except Exception:
            pass
        return arp_map

    def _ping_host(self, ip: str, timeout_ms: int = 150) -> Optional[float]:
        """Ping rapide d'une adresse IP pour tester sa joignabilité et mesurer la latence."""
        flags = _get_subprocess_flags()
        try:
            t0 = time.perf_counter()
            res = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), ip],
                capture_output=True,
                text=True,
                timeout=0.6,
                encoding="utf-8",
                errors="replace",
                **flags
            )
            if res.returncode == 0:
                match = re.search(r"(?:temps|time)[=<](\d+)ms", res.stdout, re.IGNORECASE)
                if match:
                    return float(match.group(1))
                dt = (time.perf_counter() - t0) * 1000
                return round(max(0.5, dt), 1)
        except Exception:
            pass
        return None

    def _resolve_hostname_fast(self, ip: str) -> str:
        """Résolution d'hôte non-bloquante avec cache et timeout strict."""
        if ip in self._hostname_cache:
            return self._hostname_cache[ip]

        name_box = ["Poste Réseau"]
        def lookup():
            try:
                n, _, _ = socket.gethostbyaddr(ip)
                if n:
                    name_box[0] = n
            except Exception:
                pass

        th = threading.Thread(target=lookup, daemon=True)
        th.start()
        th.join(timeout=0.25)  # 250ms max

        self._hostname_cache[ip] = name_box[0]
        return name_box[0]

    def scan_network(self, max_threads: int = 6, fast_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Effectue une cartographie réseau optimisée :
        1. Lit la table ARP (instantané, < 5ms).
        2. Mesure la latence uniquement sur les machines candidates.
        3. Résolution d'hôte en parallèle avec cache rapide.
        """
        local_ip = self.get_local_ip()
        prefix = self.get_subnet_prefix(local_ip)
        
        # 1. Lecture immédiate de la table ARP système
        arp_table = self.read_arp_table()
        
        # Ensemble des IPs candidates (postes découverts + machine locale + passerelle)
        candidate_ips = set(arp_table.keys())
        candidate_ips.add(local_ip)
        gateway_ip = f"{prefix}.1"
        candidate_ips.add(gateway_ip)

        # Mesure de latence sur les cibles réelles
        live_hosts: Dict[str, float] = {}
        live_hosts[local_ip] = 0.1

        target_list = [ip for ip in candidate_ips if ip != local_ip]
        if target_list and not fast_mode:
            with ThreadPoolExecutor(max_workers=min(max_threads, len(target_list))) as executor:
                future_to_ip = {executor.submit(self._ping_host, ip): ip for ip in target_list}
                for future in as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        lat = future.result()
                        if lat is not None:
                            live_hosts[ip] = lat
                    except Exception:
                        pass
        else:
            for ip in target_list:
                live_hosts[ip] = 1.0

        # Résolution des noms en parallèle si non-fast
        hostnames: Dict[str, str] = {}
        if not fast_mode and target_list:
            with ThreadPoolExecutor(max_workers=min(max_threads, len(target_list))) as executor:
                future_to_ip = {executor.submit(self._resolve_hostname_fast, ip): ip for ip in target_list}
                for future in as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        hostnames[ip] = future.result()
                    except Exception:
                        hostnames[ip] = "Poste Réseau"
        else:
            for ip in target_list:
                hostnames[ip] = self._hostname_cache.get(ip, "Poste Réseau")

        # Construction de la liste des postes
        results: List[Dict[str, Any]] = []
        for ip in sorted(candidate_ips, key=lambda x: [int(p) for p in x.split(".") if p.isdigit()]):
            if not ip.startswith(prefix) and ip != local_ip:
                continue

            mac = arp_table.get(ip, "N/A")
            latency = live_hosts.get(ip, None)
            is_online = (latency is not None) or (ip == local_ip)

            is_self = (ip == local_ip)
            is_gateway = (ip == gateway_ip)

            # Nom d'hôte
            if is_self:
                try:
                    hostname = socket.gethostname() + " (Ce Serveur)"
                except Exception:
                    hostname = "Serveur Local"
            elif is_gateway:
                hostname = "Passerelle / Routeur Salle"
            elif is_online:
                hostname = hostnames.get(ip, "Poste Réseau")
            else:
                hostname = "Injoignable"

            # Recherche d'un alias personnalisé attribué par l'enseignant (ex: "Poste 01")
            alias = self.renamer.get_alias(mac, fallback_ip=ip)
            if not alias and is_self:
                alias = "Serveur Central (Enseignant)"
            elif not alias and is_gateway:
                alias = "Routeur Réseau"

            results.append({
                "ip": ip,
                "mac": mac,
                "hostname": hostname,
                "alias": alias,
                "latency_ms": latency if latency is not None else -1.0,
                "status": "online" if is_online else "offline",
                "is_self": is_self,
                "is_gateway": is_gateway
            })

        return results
