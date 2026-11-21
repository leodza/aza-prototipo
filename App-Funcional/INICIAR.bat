@echo off
chcp 65001 >nul
title AZA Analyzer - Prototipo funcional
cd /d "%~dp0"

set "PY=%~dp0..\APP-AZA\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  AZA Analyzer - Prototipo funcional
echo  Abriendo http://127.0.0.1:8000
echo  Usuarios: ldaza / jsarabia / dparedes   PIN: 1234
echo  Para detener el servidor: Ctrl + C
echo ============================================================
echo.

start "" http://127.0.0.1:8000
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
