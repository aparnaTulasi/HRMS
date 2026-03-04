@echo off
echo ========================================
echo   HRMS Backend - Starting with VENV
echo ========================================
if not exist "venv\Scripts\activate" (
    echo Error: Virtual environment 'venv' not found!
    echo Please make sure you are in the project root.
    pause
    exit /b
)
echo Activating virtual environment...
call venv\Scripts\activate
echo Starting Flask App...
python app.py
pause
