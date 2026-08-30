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

:: Resolve project root — pushd/popd, no PowerShell needed
pushd "%~dp0.."
set "ROOT=%CD%"
popd

echo  Installing to: %ROOT%
echo.

set "NSSM=%~dp0tools\nssm.exe"
set "VENV=%ROOT%\.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "SERVICE=JalaramCNCService"
set "LOGS=%ROOT%\logs"

:: Check nssm.exe exists
if not exist "%NSSM%" (
    echo  [ERROR] Missing:  install\tools\nssm.exe
    echo.
    echo  How to fix:
    echo    1. Open browser on this laptop
    echo    2. Go to:  https://nssm.cc/download
    echo    3. Download nssm-2.24.zip
    echo    4. Open the ZIP, go into win64 folder
    echo    5. Copy nssm.exe to:  C:\JalaramCNC\install\tools\nssm.exe
    echo    6. Run install.bat again
    echo.
    pause
    exit /b 1
)

:: Check Python 3 is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found in PATH.
    echo  Make sure Python 3.14 was installed with "Add to PATH" checked.
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('python --version') do echo  Python: %%V

:: [1/7] Create folders
echo.
echo  [1/7] Creating folders...
if not exist "%LOGS%"                   mkdir "%LOGS%" >nul 2>&1
if not exist "%ROOT%\backups\daily"     mkdir "%ROOT%\backups\daily" >nul 2>&1
if not exist "%ROOT%\backups\monthly"   mkdir "%ROOT%\backups\monthly" >nul 2>&1
echo         Done.

:: [2/7] Create virtual environment using system Python
echo  [2/7] Creating virtual environment...
if exist "%VENV%" (
    echo         Already exists, skipping.
) else (
    python -m venv "%VENV%"
    if %errorlevel% neq 0 (
        echo  [ERROR] Could not create virtual environment.
        pause & exit /b 1
    )
    echo         Done.
)

:: [3/7] Install Python packages via pip
echo  [3/7] Installing packages (requires internet, ~2 minutes)...
"%PYTHON%" -m pip install --upgrade pip --quiet --no-warn-script-location
"%PYTHON%" -m pip install -r "%ROOT%\requirements.txt" --quiet --no-warn-script-location
if %errorlevel% neq 0 (
    echo  [ERROR] Package install failed. Check internet connection and retry.
    pause & exit /b 1
)
echo         All packages installed.

:: [4/7] Create .env and run Django setup
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
        echo         OneDrive found. Cloud backup enabled.
    ) else (
        echo         OneDrive not configured. Local backup only.
    )
    echo         .env file created with secure secret key.
) else (
    echo         .env already exists, keeping current settings.
)

cd /d "%ROOT%"
echo         Setting up database...
"%PYTHON%" manage.py migrate --noinput >"%LOGS%\migrate.log" 2>&1
echo         Collecting static files...
"%PYTHON%" manage.py collectstatic --noinput --clear >nul 2>&1
echo         Done.

:: [5/7] Set database delete password
echo.
echo  [5/7] Set database delete password
echo  -----------------------------------------------------------
echo  This password protects the database from deletion.
echo  WRITE IT DOWN somewhere safe.
echo.
"%PYTHON%" "%ROOT%\scripts\set_db_password.py"

:: [6/7] Install Windows Service via NSSM (auto-start on boot)
echo.
echo  [6/7] Installing Windows auto-start service...
sc query "%SERVICE%" >nul 2>&1
if %errorlevel% == 0 (
    echo         Removing previous installation...
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
if %errorlevel% == 0 (
    echo         Service is RUNNING.
) else (
    echo  [WARN] Service did not start. Check: %LOGS%\error.log
)

:: [7/7] Schedule backup tasks
echo  [7/7] Scheduling backup tasks...
schtasks /delete /tn "JalaramCNC_DailyBackup"   /f >nul 2>&1
schtasks /delete /tn "JalaramCNC_StartupBackup" /f >nul 2>&1
schtasks /create /tn "JalaramCNC_DailyBackup"   /tr "\"%PYTHON%\" \"%ROOT%\scripts\backup.py\""               /sc daily   /st 22:00    /ru SYSTEM /rl HIGHEST /f >nul 2>&1
schtasks /create /tn "JalaramCNC_StartupBackup" /tr "\"%PYTHON%\" \"%ROOT%\scripts\backup.py\" --if-needed"   /sc onstart /delay 0002:00 /ru SYSTEM /rl HIGHEST /f >nul 2>&1
echo         Daily backup: every night 10:00 PM
echo         Startup backup: runs on boot if ^>20h since last backup

:: Desktop shortcut on All Users desktop
echo  Creating desktop shortcut...
(
    echo [InternetShortcut]
    echo URL=http://localhost:8000
    echo IconFile=%SystemRoot%\system32\shell32.dll
    echo IconIndex=14
) > "%PUBLIC%\Desktop\Jalaram CNC.url"

echo.
echo  ============================================================
echo    INSTALLATION COMPLETE!
echo  ============================================================
echo.
echo   Open app : http://localhost:8000
echo            ( or double-click "Jalaram CNC" on Desktop )
echo.
echo   Service  : %SERVICE%  [starts automatically on every boot]
echo   Backup   : Daily 10 PM + on startup if missed
echo   Logs     : %LOGS%
echo.
echo   NEXT STEP: Restart the laptop to confirm the app
echo   comes back automatically without doing anything.
echo.
pause