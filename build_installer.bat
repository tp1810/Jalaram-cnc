@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_installer.ps1" %*
if errorlevel 1 (
    echo.
    echo BUILD FAILED. Review the error above.
    pause
    exit /b 1
)
echo.
echo BUILD COMPLETE.
pause