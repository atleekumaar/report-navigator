# scripts/lint.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> Running frontend linter (next lint)..." -ForegroundColor Cyan
Push-Location web
try {
    npm.cmd run lint
} finally {
    Pop-Location
}
