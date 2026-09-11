@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ===================================================
echo Menjalankan React/Vite Frontend...
echo ===================================================

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm tidak ditemukan. Instal Node.js terlebih dahulu.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [INFO] frontend\node_modules belum ada. Menjalankan npm install...
    call npm --prefix frontend install
    if errorlevel 1 exit /b 1
)

npm --prefix frontend run dev
pause
