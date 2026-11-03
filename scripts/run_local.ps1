# PowerShell script to start Finance Tracker Pro locally
# Usage: .\scripts\run_local.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Finance Tracker Pro - Local Development Launcher      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ROOT_DIR = Split-Path -Parent $PSScriptRoot
$PYTHON = "C:\Users\kunal\.local\bin\python3.11.exe"
if (-not (Test-Path $PYTHON)) {
    $PYTHON = "python"
}

Write-Host "`n[1/3] Applying database migrations..." -ForegroundColor Yellow
Set-Location "$ROOT_DIR\backend"
& $PYTHON manage.py migrate

Write-Host "`n[2/3] Starting Flask ML Microservice on port 5001..." -ForegroundColor Yellow
$mlProcess = Start-Process -FilePath $PYTHON -ArgumentList "$ROOT_DIR\ml_service\app.py" -PassThru

Write-Host "`n[3/3] Starting Django Web Server on http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host "Demo Credentials: username = demo_user | password = Demo@123456" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate both servers.`n" -ForegroundColor DarkGray

try {
    & $PYTHON manage.py runserver 0.0.0.0:8000
} finally {
    Write-Host "`nStopping ML microservice process..." -ForegroundColor Red
    Stop-Process -Id $mlProcess.Id -ErrorAction SilentlyContinue
}

