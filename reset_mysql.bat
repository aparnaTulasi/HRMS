@echo off
:: Check for administrative rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -FilePath '%~dpnx0' -Verb RunAs"
    exit /b
)

echo Stopping MySQL service...
net stop MySQL80

echo Creating reset file...
echo ALTER USER 'root'@'localhost' IDENTIFIED BY 'Aparna@.7'; > C:\mysql-init.txt

echo Resetting password in the background (Command Prompt window will pop up)...
start "" "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.0\my.ini" --init-file="C:\mysql-init.txt" --console

timeout /t 15

echo Shutting down temporary MySQL process...
taskkill /F /IM mysqld.exe

echo Cleaning up...
del C:\mysql-init.txt

echo Starting MySQL service normally...
net start MySQL80

echo.
echo ==============================================
echo Password has been successfully reset!
echo You can now log into MySQL Workbench with:
echo User: root
echo Password: Aparna@.7
echo ==============================================
pause
