@echo off
setlocal EnableDelayedExpansion
title Jalaram CNC - Installer
color 0A

echo.
echo  ============================================================
echo    JALARAM CNC  ^|  One-Click Installer
echo    Billing System for Windows Laptop
echo  ============================================================
echo.

:: Must run as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Run as Administrator: right-click ^> "Run as administrator"
    pause
    exit /b 1
)

:: Resolve absolute project root (parent of this install\ folder)
for /f "delims=" %%P in ('powershell -NoProfile -Command "[IO.Path]::GetFullPath(''%~dp0..'')"') do set "ROOT=%%P"
echo  Installing to: %ROOT%
echo.

set "UV=%~dp0tools\uv.exe"
set "NSSM=%~dp0tools\nssm.exe"
set "VENV=%ROOT%\.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "SERVICE=JalaramCNCService"
set "LOGS=%ROOT%\logs"

:: Check bundled tools
if not exist "%UV%" (
    echo  [ERROR] Missing: install\tools\uv.exe
    echo  Download: https://github.com/astral-sh/uv/releases/latest
    echo  File:     uv-x86_64-pc-windows-msvc.zip  (extract uv.exe)
    pause & exit /b 1
)
if not exist "%NSSM%" (
    echo  [ERROR] Missing: install\tools\nssm.exe
    echo  Download: https://nssm.cc/download
    echo  File:     nssm-2.24.zip  (extract win64\nssm.exe)
    pause & exit /b 1
)

:: [1/7] Create folders
echo  [1/7] Creating folders...
if not exist "%LOGS%"                   mkdir "%LOGS%" >nul 2>&1
if not exist "%ROOT%\backups\daily"     mkdir "%ROOT%\backups\daily" >nul 2>&1
if not exist "%ROOT%\backups\monthly"   mkdir "%ROOT%\backups\monthly" >nul 2>&1

:: [2/7] Install Python 3.14 into project folder (no internet = error)
echo  [2/7] Installing Python 3.14 (needs internet, ~35 MB)...
set "UV_PYTHON_INSTALL_DIR=%ROOT%\.python"
"%UV%" python install 3.14 >"%LOGS%\install_python.log" 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python download failed. Check internet. Log: %LOGS%\install_python.log
    pause & exit /b 1
)
for /f "delims=" %%P in ('"%UV%" python find 3.14 2^>nul') do set "PY_BASE=%%P"
if not defined PY_BASE ( echo  [ERROR] Cannot locate Python 3.14. & pause & exit /b 1 )
echo         Python: %PY_BASE%

:: [3/7] Create virtual environment + install packages
echo  [3/7] Creating virtual environment and installing packages...
"%UV%" venv "%VENV%" --python "%PY_BASE%" >nul 2>&1
if %errorlevel% neq 0 ( echo  [ERROR] Failed to create venv. & pause & exit /b 1 )
set "VIRTUAL_ENV=%VENV%"
"%UV%" pip install -r "%ROOT%\requirements.txt" >"%LOGS%\install_packages.log" 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Package install failed. Log: %LOGS%\install_packages.log
    pause & exit /b 1
)
echo         Packages installed.

:: [4/7] Generate .env and run Django setup
echo  [4/7] Configuring application...
if not exist "%ROOT%\.env" (
    for /f "delims=" %%K in ('"%PYTHON%" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"') do set "SK=%%K"
    set "OD_DIR="
    for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\OneDrive" /v "UserFolder" 2^>nul ^| findstr "UserFolder"') do set "OD_DIR=%%b"
    (
        echo DEBUG=False
        echo DJANGO_SECRET_KEY=!SK!
        echo ALLOWED_HOSTS=127.0.0.1,localhost
        echo SERVER_HOST=127.0.0.1
        echo SERVER_PORT=8000
    ) > "%ROOT%\.env"
    if defined OD_DIR (
        echo ONEDRIVE_BACKUP_DIR=!OD_DIR!\JalaramCNC_Backups>>"%ROOT%\.env"
        echo         OneDrive found. Cloud backup enabled: !OD_DIR!\JalaramCNC_Backups
    ) else (
        echo         OneDrive not found. Local backup only.
    )
    echo         .env created with secure secret key.
) else (
    echo         .env already exists - keeping current settings.
)
cd /d "%ROOT%"
"%PYTHON%" manage.py migrate --noinput >"%LOGS%\migrate.log" 2>&1
"%PYTHON%" manage.py collectstatic --noinput --clear >nul 2>&1
echo         Database and static files ready.

:: [5/7] Database delete password
echo.
echo  [5/7] Set database delete password
echo  -----------------------------------------------------------
echo  This password is needed to permanently delete the database.
echo  WRITE IT DOWN. You cannot delete the database without it.
echo.
"%PYTHON%" "%ROOT%\scripts\set_db_password.py"

:: [6/7] NSSM Windows service (auto-start on boot)
echo.
echo  [6/7] Installing Windows auto-start service...
sc query "%SERVICE%" >nul 2>&1
if %errorlevel% == 0 (
    "%NSSM%" stop "%SERVICE%" >nul 2>&1
    timeout /t 3 /nobreak >nul
    "%NSSM%" remove "%SERVICE%" confirm >nul 2>&1
)
"%NSSM%" install "%SERVICE%" "%PYTHON%"                                        >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppParameters   "%ROOT%\scripts\start_server.py"  >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppDirectory    "%ROOT%"                           >nul 2>&1
"%NSSM%" set     "%SERVICE%" Description     "Jalaram CNC Billing System"       >nul 2>&1
"%NSSM%" set     "%SERVICE%" Start           SERVICE_AUTO_START                 >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppStdout       "%LOGS%\app.log"                   >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppStderr       "%LOGS%\error.log"                 >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppRotateFiles  1                                  >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppRotateBytes  10485760                           >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppExit Default Restart                            >nul 2>&1
"%NSSM%" set     "%SERVICE%" AppRestartDelay 5000                               >nul 2>&1
"%NSSM%" start   "%SERVICE%"                                                    >nul 2>&1
timeout /t 5 /nobreak >nul
sc query "%SERVICE%" | findstr "RUNNING" >nul 2>&1
if %errorlevel% == 0 ( echo         Service RUNNING. ) else ( echo  [WARN] Check %LOGS%\error.log if app does not open. )

:: [7/7] Task Scheduler - daily 10 PM + startup catch-up
echo  [7/7] Scheduling backup tasks...

schtasks /delete /tn "JalaramCNC_DailyBackup"   /f >nul 2>&1
schtasks /delete /tn "JalaramCNC_StartupBackup" /f >nul 2>&1

:: Daily at 10 PM — always runs regardless
schtasks /create /tn "JalaramCNC_DailyBackup" /tr "\"%PYTHON%\" \"%ROOT%\scripts\backup.py\"" /sc daily /st 22:00 /ru SYSTEM /rl HIGHEST /f >nul 2>&1

:: At every startup — only runs if no backup done in last 20 hours
:: 2-minute delay gives Windows time to fully start before the script runs
schtasks /create /tn "JalaramCNC_StartupBackup" /tr "\"%PYTHON%\" \"%ROOT%\scripts\backup.py\" --if-needed" /sc onstart /delay 0002:00 /ru SYSTEM /rl HIGHEST /f >nul 2>&1

echo         Daily backup: 10:00 PM
echo         Startup backup: runs on boot if previous backup ^>20h ago

:: Desktop shortcut
echo  Creating Desktop shortcut...
(
    echo [InternetShortcut]
    echo URL=http://localhost:8000
    echo IconFile=%SystemRoot%\system32\shell32.dll
    echo IconIndex=14
) > "%PUBLIC%\Desktop\Jalaram CNC.url"

:: Done
echo.
echo  ============================================================
echo    INSTALLATION COMPLETE!
echo  ============================================================
echo.
echo   Open app : http://localhost:8000
echo            ( or double-click "Jalaram CNC" on Desktop )
echo.
echo   Service  : %SERVICE%  [auto-starts on every boot]
echo   Backup   : Daily 10 PM + on startup if missed
echo   Logs     : %LOGS%
echo.
echo   NEXT STEP: Restart the laptop once to confirm the app
echo   comes back automatically without doing anything.
echo.
pause