# scripts/build.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> Building Next.js application..." -ForegroundColor Cyan
Push-Location web
try {
    npm.cmd run build
} finally {
    Pop-Location
}
