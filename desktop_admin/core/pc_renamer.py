"""
Module de gestion des alias et d'étiquetage des postes de la salle (Approche 1).
Associe une adresse MAC / IP à un nom convivial (ex: 'Poste 01', 'Rangée A - Table 2')
avec persistance JSON et import/export CSV.
"""

import os
import sys
import json
import csv
from typing import Dict, Any, Optional

class PCRenamer:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is not None:
            self.storage_path = os.path.abspath(storage_path)
        else:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.storage_path = os.path.join(data_dir, "network_topology.json")
            
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _normalize_mac(self, mac: str) -> str:
        """Harmonise le format de l'adresse MAC (majuscules, séparateur deux-points)."""
        if not mac:
            return ""
        clean = mac.strip().upper().replace("-", ":").replace(".", ":")
        return clean

    def _load(self) -> None:
        """Charge le dictionnaire de topologie depuis le disque."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        else:
            self._cache = {}

    def _save(self) -> None:
        """Sauvegarde les alias sur le disque."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def set_alias(self, mac: str, alias: str, room: str = "", ip: str = "", hostname: str = "", notes: str = "") -> None:
        """Définit ou met à jour l'alias d'un poste."""
        mac_clean = self._normalize_mac(mac)
        if not mac_clean:
            return
            
        self._cache[mac_clean] = {
            "alias": alias.strip(),
            "room": room.strip(),
            "last_known_ip": ip.strip(),
            "hostname": hostname.strip(),
            "notes": notes.strip()
        }
        self._save()

    def get_alias(self, mac: str, fallback_ip: str = "") -> str:
        """Récupère l'alias d'un poste par son adresse MAC (ou son IP en secours)."""
        mac_clean = self._normalize_mac(mac)
        if mac_clean in self._cache and self._cache[mac_clean].get("alias"):
            return self._cache[mac_clean]["alias"]
            
        # Recherche par IP si MAC inconnue
        if fallback_ip:
            for entry in self._cache.values():
                if entry.get("last_known_ip") == fallback_ip and entry.get("alias"):
                    return entry["alias"]
                    
        return ""

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Renvoie l'ensemble de la cartographie enregistrée."""
        return self._cache.copy()

    def delete_alias(self, mac: str) -> bool:
        """Supprime un alias enregistré."""
        mac_clean = self._normalize_mac(mac)
        if mac_clean in self._cache:
            del self._cache[mac_clean]
            self._save()
            return True
        return False

    def export_csv(self, file_path: str) -> bool:
        """Exporte la topologie en fichier CSV pour sauvegarde ou impression."""
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["MAC", "Alias", "Salle", "Derniere_IP", "Hostname", "Notes"])
                for mac, info in sorted(self._cache.items(), key=lambda x: x[1].get("alias", "")):
                    writer.writerow([
                        mac,
                        info.get("alias", ""),
                        info.get("room", ""),
                        info.get("last_known_ip", ""),
                        info.get("hostname", ""),
                        info.get("notes", "")
                    ])
            return True
        except Exception:
            return False

    def import_csv(self, file_path: str) -> int:
        """Importe des associations d'alias depuis un fichier CSV."""
        if not os.path.exists(file_path):
            return 0
            
        count = 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mac = row.get("MAC", "").strip()
                    alias = row.get("Alias", "").strip()
                    if mac and alias:
                        self.set_alias(
                            mac=mac,
                            alias=alias,
                            room=row.get("Salle", ""),
                            ip=row.get("Derniere_IP", ""),
                            hostname=row.get("Hostname", ""),
                            notes=row.get("Notes", "")
                        )
                        count += 1
        except Exception:
            pass
        return count

