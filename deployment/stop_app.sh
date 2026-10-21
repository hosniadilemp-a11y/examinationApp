#!/usr/bin/env bash
# ==============================================================================
# Script d'Arrêt Propre Docker - Plateforme d'Examen LAN
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "==============================================================================="
echo "        ARRÊT DU SERVEUR D'EXAMEN ET D'ENTRAÎNEMENT (DOCKER)"
echo "==============================================================================="

docker compose down

echo "Tous les conteneurs sont arrêtés. Les volumes de données persistent."

