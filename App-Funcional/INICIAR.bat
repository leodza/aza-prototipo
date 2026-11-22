@echo off
chcp 65001 >nul
title AZA Analyzer - Prototipo funcional
cd /d "%~dp0"

rem 1) entorno local del proyecto   2) entorno del repo APP-AZA   3) Python del sistema
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%~dp0..\APP-AZA\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  AZA Analyzer - Prototipo funcional
echo  Abriendo http://127.0.0.1:8000
echo  Usuarios: ldaza / jsarabia / dparedes   PIN: 1234
echo  Para detener el servidor: Ctrl + C
echo ============================================================
echo.

if exist "%~dp0.venv\Scripts\python.exe" goto arrancar
if exist "%~dp0..\APP-AZA\.venv\Scripts\python.exe" goto arrancar

echo  Aviso: no encontre un entorno preparado.
echo  Si es la primera vez en este equipo, ejecuta INSTALAR.bat
echo  (o se usara el Python del sistema, que puede no tener las librerias).
echo.
timeout /t 4 >nul

:arrancar
start "" http://127.0.0.1:8000
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
