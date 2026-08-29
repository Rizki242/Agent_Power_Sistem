@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ===================================================
echo Membuka PPLE Agent (FastAPI Backend + React Frontend)...
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment belum ditemukan. Menjalankan build awal...
    call build.bat
    if errorlevel 1 exit /b 1
)

echo [1/2] Menjalankan FastAPI Backend Server di Port 8000...
start "PPLE Backend API (Port 8000)" cmd /k "chcp 65001 >nul && cd /d "%~dp0" && .\.venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Menjalankan Vite React Frontend di Port 5173...
start "PPLE React Frontend (Port 5173)" cmd /k "chcp 65001 >nul && cd /d "%~dp0\frontend" && npm run dev"

echo.
echo ===================================================
echo [ONLINE] Kedua layanan telah dijalankan!
echo ===================================================
echo - Backend API : http://localhost:8000 (Swagger: http://localhost:8000/docs)
echo - Frontend UI : http://localhost:5173
echo.
pause
