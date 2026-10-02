@echo off
title Lufthansa Bot Portal
echo ===================================================
echo     Iniciando Lufthansa Case Tracker Portal
echo ===================================================
echo.
echo Abrindo o navegador em http://localhost:8000 ...
start http://localhost:8000
echo.
"C:\Users\dan-s\OpenCode-Lab\.planning\.venv\Scripts\python.exe" "C:\Users\dan-s\OpenCode-Lab\lufthansa_bot\main.py" portal
pause
