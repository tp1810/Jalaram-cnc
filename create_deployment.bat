@echo off
setlocal
title Jalaram CNC - Build Installer
cd /d "%~dp0"
call build_installer.bat %*
exit /b %errorlevel%
