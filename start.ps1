# LogisticAI — Start Script
# Runs backend (FastAPI) + frontend (Vite) concurrently

Write-Host ""
Write-Host "  ██╗      ██████╗  ██████╗ ██╗███████╗████████╗██╗ ██████╗ █████╗ ██╗" -ForegroundColor Cyan
Write-Host "  ██║     ██╔═══██╗██╔════╝ ██║██╔════╝╚══██╔══╝██║██╔════╝██╔══██╗██║" -ForegroundColor Cyan
Write-Host "  ██║     ██║   ██║██║  ███╗██║███████╗   ██║   ██║██║     ███████║██║" -ForegroundColor Cyan
Write-Host "  ██║     ██║   ██║██║   ██║██║╚════██║   ██║   ██║██║     ██╔══██║██║" -ForegroundColor Cyan
Write-Host "  ███████╗╚██████╔╝╚██████╔╝██║███████║   ██║   ██║╚██████╗██║  ██║██║" -ForegroundColor Cyan
Write-Host "  ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  AI-Powered Intelligent Logistics Optimization System" -ForegroundColor White
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Check Python ────────────────────────────────────────────────────────
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "    ERROR: Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "    Python: $(python --version)" -ForegroundColor Green

# ── Install Python deps ──────────────────────────────────────────────────
Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow
Set-Location "$root\backend"
pip install -r requirements.txt -q
Write-Host "    Dependencies installed." -ForegroundColor Green

# ── Train ML Models if needed ────────────────────────────────────────────
$modelsPath = "$root\backend\ml\models\eta_model.pkl"
if (-not (Test-Path $modelsPath)) {
    Write-Host "[2.5] Training ML models (first run only — takes ~60s)..." -ForegroundColor Yellow
    python ml\train_models.py
    Write-Host "    Models trained and saved." -ForegroundColor Green
} else {
    Write-Host "    ML models already trained. Skipping." -ForegroundColor Green
}

# ── Start FastAPI backend ────────────────────────────────────────────────
Write-Host "[3/4] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($backendPath)
    Set-Location $backendPath
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload 2>&1
} -ArgumentList "$root\backend"

Start-Sleep -Seconds 4
Write-Host "    Backend started (Job ID: $($backendJob.Id))" -ForegroundColor Green

# ── Start React frontend ─────────────────────────────────────────────────
Write-Host "[4/4] Starting React frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Set-Location "$root\frontend"
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "  ════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🚀 LogisticAI is running!" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  ════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor Gray
Write-Host ""

npm run dev
