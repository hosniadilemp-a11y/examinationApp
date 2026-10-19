#!/usr/bin/env bash
# ==============================================================================
# Lancement Clé en Main du Serveur de Salle d'Examen TP (Linux / macOS)
# ==============================================================================

set -e

echo "====================================================================="
echo "   PLATEFORME D'EXAMEN & D'ENTRAÎNEMENT - SERVEUR DE SALLE DE TP"
echo "====================================================================="
echo ""

# Détection de l'IP LAN
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "[INFO] Démarrage du serveur FastAPI..."
echo "[INFO] Adresse pour les postes étudiants de la salle : http://${LOCAL_IP}:8000"
echo "[INFO] Interface enseignant : http://localhost:8000"
echo ""

# Démarrage avec Uvicorn
exec python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
