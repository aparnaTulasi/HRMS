Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  HRMS Backend - Starting with VENV" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Error: Virtual environment 'venv' not found!" -ForegroundColor Red
    Write-Host "Please make sure you are in the project root." -ForegroundColor Yellow
    Exit
}

Write-Host "Activating virtual environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

Write-Host "Starting Flask App..." -ForegroundColor Green
python app.py
