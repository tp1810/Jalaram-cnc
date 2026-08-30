@echo off
setlocal
title Jalaram CNC - Uninstall Service

echo.
echo  ================================================
echo    JALARAM CNC ^| Remove Windows Service
echo  ================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Run as Administrator.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "(Resolve-Path '%~dp0..').Path"') do set "PROJECT_DIR=%%i"

set "NSSM=%~dp0nssm\nssm.exe"
set "SERVICE_NAME=JalaramCNCService"

echo  Stopping service...
"%NSSM%" stop "%SERVICE_NAME%" >nul 2>&1
timeout /t 3 /nobreak >nul

echo  Removing service...
"%NSSM%" remove "%SERVICE_NAME%" confirm >nul 2>&1

echo  Removing backup task...
schtasks /delete /tn "JalaramCNC_DailyBackup" /f >nul 2>&1

echo  Removing desktop shortcut...
del "%PUBLIC%\Desktop\Jalaram CNC.url" >nul 2>&1

echo.
echo  Service removed.
echo  Data and backups at "%PROJECT_DIR%\backups" are untouched.
echo  To reinstall, run install.bat again.
echo.
pause
