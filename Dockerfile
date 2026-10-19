# ==============================================================================
# Dockerfile - Serveur Autonome d'Examen et d'Entraînement (Option B : Salle de TP)
# ==============================================================================
FROM python:3.11-slim

# Empêcher la création de fichiers .pyc et forcer le mode non-tamponné pour les logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV SQLITE_DB_PATH=/app/data/exam_app.db

WORKDIR /app

# Dépendances système de base
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'ensemble du projet
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY docs/ ./docs/

# Création du répertoire de données persistantes pour SQLite WAL
RUN mkdir -p /app/data

# Exposition du port HTTP
EXPOSE 8000

# Contrôle de santé intégré
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Lancement du serveur FastAPI Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
