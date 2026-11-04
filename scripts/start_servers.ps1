# Finance Tracker Pro — Start All Servers
# Run this script to start both Django and Flask ML service

$ProjectRoot = "c:\Users\kunal\OneDrive\Desktop\FINANCE TRACKER 1.0"
$Python = "C:\Users\kunal\.local\bin\python3.11.exe"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Finance Tracker Pro — Starting Servers   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Start Flask ML Service in a new window
Write-Host "[1/2] Starting Flask ML Service on port 5001..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot\ml_service'; & '$Python' app.py" -WindowStyle Normal

Start-Sleep -Seconds 2

# Start Django in a new window
Write-Host "[2/2] Starting Django Server on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot\backend'; & '$Python' manage.py runserver 0.0.0.0:8000" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Servers Started!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  App URL:     http://localhost:8000" -ForegroundColor White
Write-Host "  ML Service:  http://localhost:5001/health" -ForegroundColor White
Write-Host "  API Docs:    http://localhost:8000/api/docs/" -ForegroundColor White
Write-Host "  Admin:       http://localhost:8000/admin/" -ForegroundColor White
Write-Host ""
Write-Host "  Demo Login:" -ForegroundColor Cyan
Write-Host "    Username: demo_user" -ForegroundColor White
Write-Host "    Password: Demo@123456" -ForegroundColor White
Write-Host ""

# Open browser
Start-Process "http://localhost:8000"

