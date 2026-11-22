@echo off
setlocal
title AZA Analyzer - acceso a la nube
cd /d "%~dp0"

echo ==============================================
echo    AZA Analyzer  -  acceso al sistema en AWS
echo ==============================================
echo.

if not exist "deploy\ip.txt" goto sin_ip
for /f "usebackq delims=" %%a in ("deploy\ip.txt") do set "IP=%%a"
if "%IP%"=="" goto sin_ip

echo  Servidor: %IP%
echo.
echo  Comprobando que este encendido...
echo. | powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $r = Invoke-WebRequest -Uri ('http://%IP%:8000/api/health') -TimeoutSec 12 -UseBasicParsing; Write-Host ('   OK  ' + $r.Content); exit 0 } catch { Write-Host '   sin respuesta'; exit 1 }"
if errorlevel 1 goto caido

echo.
echo  Abriendo la aplicacion y el visor de la base de datos...
start "" "http://%IP%:8000"
timeout /t 2 >nul
start "" "http://%IP%:8081"
echo.
echo  --------------------------------------------------------
echo   Aplicacion web : http://%IP%:8000
echo                    usuarios: ldaza / jsarabia / dparedes
echo                    PIN: 1234
echo.
echo   Base de datos  : http://%IP%:8081
echo                    usuario: aza
echo                    clave:   AzaLab2026Db
echo  --------------------------------------------------------
echo.
goto fin

:caido
echo.
echo  [X] La instancia no responde.
echo.
echo   Causas posibles:
echo     1. La sesion del laboratorio de AWS Academy termino y la instancia se apago.
echo     2. La instancia se reinicio y le asignaron otra IP publica.
echo.
echo   Que hacer:
echo     a) Entra a la consola de AWS: EC2 - Instancias - columna "Public IPv4"
echo     b) Escribe la IP en el archivo:  deploy\ip.txt
echo     c) O vuelve a desplegar con:     python deploy\desplegar_aws.py crear --si
echo.
goto fin

:sin_ip
echo  [X] No encontre el archivo deploy\ip.txt
echo.
echo   Ese archivo se crea al desplegar. Si ya tienes la IP, escribela asi:
echo      deploy\guardar-ip.bat 1.2.3.4
echo.
goto fin

:fin
echo.
pause
