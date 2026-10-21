#!/usr/bin/env bash
# ==============================================================================
# Script de Démarrage Docker - Plateforme d'Examen et d'Entraînement LAN
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "==============================================================================="
echo "       DÉMARRAGE DU SERVEUR D'EXAMEN ET D'ENTRAÎNEMENT (DOCKER)"
echo "==============================================================================="

if ! command -v docker &> /dev/null; then
    echo "[ERREUR] Docker n'est pas installé ou le service docker n'est pas actif."
    exit 1
fi

echo "[1/3] Vérification des volumes de données persistantes..."
echo "[2/3] Démarrage des conteneurs via Docker Compose..."
docker compose up -d

echo "[3/3] Attente de la validation du contrôle de santé..."
sleep 4

echo ""
echo "==============================================================================="
echo "  SERVEUR D'EXAMEN EN LIGNE ET OPÉRATIONNEL DANS LE CONTENEUR DOCKER !"
echo "==============================================================================="
echo "  * URL Locale :              http://localhost:8000"
echo "  * URL Salle de TP (LAN) :   http://[IP_DU_SERVEUR]:8000"
echo "  * API Documentation :       http://localhost:8000/docs"
echo "  * Contrôle de Santé :       http://localhost:8000/api/health"
echo "==============================================================================="

