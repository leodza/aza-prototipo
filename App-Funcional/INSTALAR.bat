@echo off
chcp 65001 >nul
title AZA Analyzer - instalacion
cd /d "%~dp0"

echo ============================================================
echo   AZA Analyzer - instalacion del entorno
echo ============================================================
echo.
echo  Esto crea un entorno de Python solo para este proyecto
echo  e instala las librerias que necesita (OpenCV, FastAPI...).
echo  Tarda entre 3 y 6 minutos y necesita internet.
echo.
pause

where py >nul 2>&1
if not errorlevel 1 goto con_py
where python >nul 2>&1
if not errorlevel 1 goto con_python
goto sin_python

:con_py
echo.
echo  Creando entorno con "py -3"...
py -3 -m venv .venv
goto verificar

:con_python
echo.
echo  Creando entorno con "python"...
python -m venv .venv
goto verificar

:verificar
if not exist ".venv\Scripts\python.exe" goto fallo_venv

echo.
echo  Instalando librerias (esto es lo que demora)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo ============================================================
echo   Listo. Ya puedes ejecutar INICIAR.bat
echo ============================================================
echo.
pause
exit /b 0

:sin_python
echo.
echo  [X] No encontre Python en este equipo.
echo.
echo      1. Descarga Python 3.12 o superior desde:
echo         https://www.python.org/downloads/windows/
echo      2. Al instalar, MARCA la casilla "Add python.exe to PATH".
echo      3. Vuelve a ejecutar este archivo.
echo.
pause
exit /b 1

:fallo_venv
echo.
echo  [X] No se pudo crear el entorno .venv
echo      Revisa que Python este bien instalado y que tengas permisos
echo      para escribir en esta carpeta.
echo.
pause
exit /b 1
