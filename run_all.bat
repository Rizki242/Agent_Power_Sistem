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

echo [2/2] Menjalankan Streamlit Dashboard di Port 8501...
start "PPLE Streamlit Dashboard (Port 8501)" cmd /k "chcp 65001 >nul && cd /d "%~dp0" && .\.venv\Scripts\python.exe -m streamlit run app.py"

echo.
echo ===================================================
echo [ONLINE] Layanan telah dijalankan!
echo ===================================================
echo - Streamlit UI : http://localhost:8501
echo - Backend API  : http://localhost:8000 (Swagger: http://localhost:8000/docs)
echo.
pause
