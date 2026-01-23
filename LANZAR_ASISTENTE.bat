@echo off
title Lanzador Asistente de Cuentas
echo Iniciando el servidor del asistente...
start /B .venv\Scripts\python app.py
timeout /t 2 /nobreak > nul
echo Abriendo la interfaz en el navegador...
start index.html
echo.
echo ==========================================
echo   ASISTENTE ACTIVO Y LISTO PARA USAR
echo   Cierra esta ventana para detenerlo.
echo ==========================================
pause
