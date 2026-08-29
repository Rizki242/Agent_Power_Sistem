@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ===================================================
echo Menjalankan Frontend Dev Server (Vite + React)...
echo ===================================================

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js / npm tidak ditemukan di PATH. Pastikan Node.js sudah terinstal.
    pause
    exit /b 1
)

npm --prefix frontend run dev
pause
