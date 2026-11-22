@echo off
rem Guarda la IP del servidor en deploy\ip.txt
setlocal
if "%~1"=="" (
    echo Uso:  guardar-ip.bat 13.223.49.56
    echo.
    echo La IP se ve en la consola de AWS: EC2 - Instancias - "Public IPv4"
    pause
    exit /b 1
)
cd /d "%~dp0"
echo %~1 > ip.txt
echo.
echo IP guardada: %~1
echo.
echo Ahora puedes usar NUBE.bat para abrir el sistema.
pause
