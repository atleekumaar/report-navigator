# scripts/test.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> Running pytest suite..." -ForegroundColor Cyan
if (Test-Path "venv\Scripts\pytest.exe") {
    & "venv\Scripts\pytest.exe" -v
} else {
    python -m pytest -v
}
