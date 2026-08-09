@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 正在建立 Python 虛擬環境...
  py -3.11 -m venv .venv 2>nul || py -3 -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python launcher.py
if errorlevel 1 pause
endlocal

