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

echo [2/3] Menjalankan Streamlit Dashboard di Port 8501...
start "PPLE Streamlit Dashboard (Port 8501)" cmd /k "chcp 65001 >nul && cd /d "%~dp0" && .\.venv\Scripts\python.exe -m streamlit run app.py"

where npm >nul 2>nul
if errorlevel 1 (
    echo [3/3] npm tidak ditemukan - frontend React dilewati. Instal Node.js untuk mengaktifkannya.
) else (
    if not exist "frontend\node_modules" (
        echo [3/3] Menyiapkan dependency frontend ^(npm install^)...
        call npm --prefix frontend install
    )
    echo [3/3] Menjalankan React/Vite Frontend di Port 5173...
    start "PPLE React Frontend (Port 5173)" cmd /k "chcp 65001 >nul && cd /d "%~dp0" && npm --prefix frontend run dev"
)

echo.
echo ===================================================
echo [ONLINE] Layanan telah dijalankan!
echo ===================================================
echo - Streamlit UI : http://localhost:8501
echo - Backend API  : http://localhost:8000 (Swagger: http://localhost:8000/docs)
echo - React UI     : http://localhost:5173 (jika Node.js tersedia)
echo.
pause
