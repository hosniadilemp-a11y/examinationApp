#!/usr/bin/env bash
# ==============================================================================
# Script de Mise à Jour de l'Image Docker - Plateforme d'Examen LAN
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "==============================================================================="
echo "    MISE À JOUR DE L'APPLICATION ET RÉGÉNÉRATION DE L'IMAGE DOCKER"
echo "==============================================================================="
echo "Informations données : Les volumes Docker persistants (PostgreSQL / SQLite WAL)"
echo "restent intacts. Aucune note ni compte utilisateur n'est effacé."
echo ""

echo "[1/4] Régénération de l'image Docker..."
docker compose build

echo "[2/4] Relance des services avec la nouvelle image..."
docker compose up -d

echo "[3/4] Attente de la validation du contrôle de santé..."
sleep 4

echo "[4/4] Vérification de l'API..."
if curl -s http://localhost:8000/api/health | grep -q "online"; then
    echo "✅ [SUCCÈS] Le serveur d'examen est à jour et opérationnel !"
else
    echo "ℹ️ [INFO] Initialisation en cours..."
fi

echo "==============================================================================="

