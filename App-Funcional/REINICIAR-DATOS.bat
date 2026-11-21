@echo off
chcp 65001 >nul
title AZA - Reiniciar datos de demostracion
cd /d "%~dp0"

echo ============================================================
echo  Esto elimina la base de datos y las capturas actuales.
echo  Al volver a iniciar la aplicacion se crean datos nuevos.
echo ============================================================
echo.
choice /C SN /M "Continuar (S=si, N=no)"
if errorlevel 2 goto :fin
if errorlevel 1 goto :borrar

:borrar
if exist "data\aza.db" del /q "data\aza.db"
if exist "data\capturas" rmdir /s /q "data\capturas"
echo.
echo Listo. Los datos de demostracion se regeneran al iniciar la aplicacion.
echo.

:fin
pause
