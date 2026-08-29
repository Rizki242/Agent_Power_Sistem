@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ===================================================
echo Menjalankan Power Plant O&M Reliability API Server...
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment (.venv) belum ada. Jalankan build.bat terlebih dahulu.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" run_server.py
pause
