@echo off
rem Starts Jarvis in a minimised window, then opens the HUD. Used by autostart.ps1; you can double-click it too.
cd /d "%~dp0\.."
start "Jarvis" /min ".venv\Scripts\python.exe" server.py
timeout /t 6 /nobreak >nul
start "" http://127.0.0.1:8340/
