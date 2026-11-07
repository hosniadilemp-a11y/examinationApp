#!/usr/bin/env bash
echo "🛑 Arrêt des processus ExamQuiz (uvicorn)..."
pkill -f "uvicorn backend.app.main:app" || true
echo "✅ Serveur arrêté."
