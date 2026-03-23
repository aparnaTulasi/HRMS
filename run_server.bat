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
echo Setting UTF-8 encoding for Python console...
chcp 65001
set PYTHONIOENCODING=utf-8
echo Starting Flask App...
python app.py
pause
