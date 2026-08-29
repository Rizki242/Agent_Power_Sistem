@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ===================================================
echo [1/5] Memeriksa dan Menyiapkan Virtual Environment...
echo ===================================================
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment belum ditemukan. Membuat .venv baru...
    py -3.11 -m venv .venv 2>nul
    if errorlevel 1 py -3 -m venv .venv 2>nul
    if errorlevel 1 python -m venv .venv
)

".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo Virtual environment rusak atau menunjuk Python yang sudah tidak ada. Membuat ulang .venv...
    rmdir /s /q ".venv"
    py -3.11 -m venv .venv 2>nul
    if errorlevel 1 py -3 -m venv .venv 2>nul
    if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Gagal membuat Python virtual environment. Pastikan Python sudah terinstal.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [2/5] Menginstal Dependensi Python (requirements.txt)...
echo ===================================================
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal menginstal dependensi Python.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [3/5] Memeriksa dan Membangun Frontend (Vite/React)...
echo ===================================================
where npm >nul 2>nul
if errorlevel 1 (
    echo [WARNING] npm tidak ditemukan di PATH. Melewati build frontend web.
) else (
    if exist "frontend\package.json" (
        echo Menginstal dependensi frontend...
        npm --prefix frontend install
        echo Menjalankan build frontend...
        npm --prefix frontend run build
        if errorlevel 1 (
            echo [ERROR] Build frontend gagal.
            pause
            exit /b 1
        )
    )
)

echo.
echo ===================================================
echo [4/5] Menjalankan Unit Tests...
echo ===================================================
".venv\Scripts\python.exe" -m unittest discover -s . -p "test_*.py"
if errorlevel 1 (
    echo [ERROR] Satu atau lebih unit test gagal.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [5/5] Menjalankan Verifikasi Sistem (verify_app.py)...
echo ===================================================
".venv\Scripts\python.exe" verify_app.py
if errorlevel 1 (
    echo [ERROR] Verifikasi sistem gagal.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo [SUCCESS] Build, instalasi, dan verifikasi selesai!
echo ===================================================
echo.
echo Jalankan aplikasi menggunakan salah satu skrip berikut:
echo - Streamlit Dashboard : run.bat
echo - FastAPI Backend     : run_api.bat
echo - Frontend Dev Server : run_frontend.bat
echo.
pause
