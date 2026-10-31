# scripts/install.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> Installing Python dependencies..." -ForegroundColor Cyan
if (Test-Path "venv\Scripts\python.exe") {
    & "venv\Scripts\python.exe" -m pip install -r requirements.txt
} else {
    python -m pip install -r requirements.txt
}

Write-Host "==> Generating sample fixture PDF..." -ForegroundColor Cyan
if (Test-Path "venv\Scripts\python.exe") {
    & "venv\Scripts\python.exe" create_sample_report.py
} else {
    python create_sample_report.py
}

Write-Host "==> Installing web dependencies..." -ForegroundColor Cyan
Push-Location web
try {
    npm.cmd install
} finally {
    Pop-Location
}

Write-Host "==> Install complete!" -ForegroundColor Green
