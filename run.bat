@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ===================================================
echo Menjalankan MCSA Assistant Dashboard (Streamlit)...
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment belum ditemukan. Menjalankan build awal...
    call build.bat
    if errorlevel 1 exit /b 1
)

echo Membuka aplikasi Streamlit...
".venv\Scripts\python.exe" -m streamlit run app.py
pause
