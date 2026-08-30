@echo off
setlocal
title Jalaram CNC - Create Deployment Package

echo.
echo  Creating deployment ZIP for friend's laptop...
echo.

set "HERE=%~dp0"
set "DIST=%HERE%dist\JalaramCNC"

:: Clean previous dist
if exist "%HERE%dist" (
    echo  Removing previous dist\...
    rmdir /s /q "%HERE%dist"
)
mkdir "%DIST%"

:: Copy project files, excluding developer/runtime folders
echo  Copying project files...
robocopy "%HERE%." "%DIST%" /E /NP /NFL /NDL ^
    /XD .venv .python __pycache__ logs backups staticfiles dist .git node_modules ^
    /XF .env db.sqlite3 *.pyc *.pyo *.log "*.sqlite3"

:: Ensure required folders exist in the package
if not exist "%DIST%\install\tools" mkdir "%DIST%\install\tools"
if not exist "%DIST%\logs"          mkdir "%DIST%\logs"
if not exist "%DIST%\backups\daily" mkdir "%DIST%\backups\daily"

echo.
echo  ───────────────────────────────────────────────
echo  BEFORE ZIPPING: Add these two files:
echo  ───────────────────────────────────────────────
echo.
echo    install\tools\uv.exe
echo    install\tools\nssm.exe
echo.
echo  See  install\tools\DOWNLOAD_THESE.txt  for links.
echo.
echo  ───────────────────────────────────────────────
echo  HOW TO ZIP:
echo  ───────────────────────────────────────────────
echo.
echo   1. Add uv.exe and nssm.exe to:
echo         dist\JalaramCNC\install\tools\
echo.
echo   2. Right-click the "JalaramCNC" folder inside dist\
echo      → Send to → Compressed (zipped) folder
echo      OR use 7-Zip: right-click → Add to archive...
echo.
echo   3. Rename the ZIP to  JalaramCNC.zip
echo.
echo   4. Send  JalaramCNC.zip  to your friend
echo.
echo  Package created at:
echo    %DIST%
echo.
pause
