# scripts/type-check.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> Running TypeScript type-check..." -ForegroundColor Cyan
Push-Location web
try {
    npx.cmd tsc --noEmit
} finally {
    Pop-Location
}
