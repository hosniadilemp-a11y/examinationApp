#!/usr/bin/env bash
# ==============================================================================
# Script de Déblocage Réseau Câblé (LAN) — Serveur Linux (Ubuntu/Debian/RHEL/CentOS)
# Configure les règles UFW/Firewalld/iptables pour autoriser le port 8000 et mDNS.
# ==============================================================================

set -e

# Vérification des privilèges root / sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Ce script doit être exécuté avec les privilèges root (sudo)."
    echo "Usage : sudo ./debloquer_acces_lan.sh"
    exit 1
fi

echo "=============================================================================="
echo "   DÉBLOCAGE DU SERVEUR D'EXAMEN POUR LE RÉSEAU CÂBLÉ (ETHERNET LAN)"
echo "=============================================================================="
echo ""

# 1. Activation de l'acheminement des paquets IP (IP Forwarding pour Docker)
echo "[1/3] Vérification du routage IP (ip_forward)..."
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1
echo "   -> net.ipv4.ip_forward = 1 (Actif)"

# 2. Configuration du Pare-Feu Linux
echo ""
echo "[2/3] Configuration des règles de pare-feu..."

if command -v ufw >/dev/null 2>&1 && ufw status | grep -qw "active"; then
    echo "   -> Pare-feu UFW détecté (Ubuntu / Debian) :"
    ufw allow 8000/tcp comment "ExamQuiz Web Server" >/dev/null 2>&1 || true
    ufw allow 5353/udp comment "ExamQuiz mDNS ZeroConf" >/dev/null 2>&1 || true
    ufw reload >/dev/null 2>&1 || true
    echo "      ✔ Port 8000 (TCP) et Port 5353 (UDP) autorisés dans UFW."
elif command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    echo "   -> Pare-feu Firewalld détecté (RHEL / CentOS / Rocky) :"
    firewall-cmd --add-port=8000/tcp --permanent >/dev/null 2>&1 || true
    firewall-cmd --add-port=5353/udp --permanent >/dev/null 2>&1 || true
    firewall-cmd --reload >/dev/null 2>&1 || true
    echo "      ✔ Port 8000 (TCP) et Port 5353 (UDP) autorisés dans Firewalld."
else
    echo "   -> Configuration via iptables :"
    iptables -C INPUT -p tcp --dport 8000 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
    iptables -C INPUT -p udp --dport 5353 -j ACCEPT 2>/dev/null || iptables -I INPUT -p udp --dport 5353 -j ACCEPT
    echo "      ✔ Règles iptables appliquées pour les ports 8000 et 5353."
fi

# 3. Affichage des adresses IP disponibles
echo ""
echo "[3/3] Adresses IP détectées sur ce serveur Linux :"
echo "------------------------------------------------------------------------------"
for ip in $(hostname -I 2>/dev/null || ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1'); do
    echo "   👉 http://${ip}:8000"
done
echo "------------------------------------------------------------------------------"
echo ""
echo "✔ SUCCÈS : Le serveur est prêt et accessible par les postes de la salle !"
echo ""

