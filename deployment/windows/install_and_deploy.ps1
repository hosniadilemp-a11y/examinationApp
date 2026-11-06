# ==============================================================================
# ExamQuiz Platform — Script PowerShell d'Installation & Déploiement Windows
# ==============================================================================
$ErrorActionPreference = "Stop"
$AppRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $AppRoot

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "   DÉPLOIEMENT WINDOWS (POWERSHELL) — PLATEFORME EXAMQUIZ" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] Création de l'environnement virtuel (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}

$PyBin = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

Write-Host "[2/4] Installation des dépendances..." -ForegroundColor Yellow
& $PyBin -m pip install --upgrade pip -q
& $PyBin -m pip install -r requirements.txt -q

Write-Host "[3/4] Initialisation de la base de données de test..." -ForegroundColor Yellow
& $PyBin scripts\reset_and_seed_exact_3_exams.py

Write-Host "[4/4] Démarrage du serveur sur http://0.0.0.0:8000 ..." -ForegroundColor Green
& $PyBin -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
