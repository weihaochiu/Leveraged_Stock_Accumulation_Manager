@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 尚未安裝環境，請先執行 setup_and_run.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 pause

