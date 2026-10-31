# scripts/run.ps1
param (
    [string]$Target = "api"
)

if ($Target -eq "web") {
    Write-Host "==> Starting Next.js frontend (http://127.0.0.1:3000)..." -ForegroundColor Cyan
    Push-Location web
    try {
        npm.cmd run dev
    } finally {
        Pop-Location
    }
} else {
    Write-Host "==> Starting FastAPI backend (http://127.0.0.1:8000)..." -ForegroundColor Cyan
    if (Test-Path "venv\Scripts\python.exe") {
        & "venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
    } else {
        python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
    }
}
