# IAARE one-shot launcher (Windows PowerShell)
# Starts the FastAPI backend and the Vite frontend in separate windows.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "==> Setting up IAARE backend..." -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org | Out-Null
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org | Out-Null

Write-Host "==> Launching backend on http://localhost:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

Write-Host "==> Setting up IAARE frontend..." -ForegroundColor Cyan
Set-Location "$root\frontend"
if (-not (Test-Path "node_modules")) {
    npm install --strict-ssl=false --no-audit --no-fund
}

Write-Host "==> Launching frontend on http://localhost:5173" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "IAARE is starting up:" -ForegroundColor Yellow
Write-Host "  Frontend : http://localhost:5173"
Write-Host "  Backend  : http://localhost:8000  (docs at /docs)"
