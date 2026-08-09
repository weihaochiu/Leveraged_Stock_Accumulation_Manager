@echo off
setlocal EnableExtensions
chcp 65001 >nul

pushd "%~dp0"
if errorlevel 1 goto workdir_error

if exist ".venv\Scripts\python.exe" goto install_packages

echo 正在建立 Python 虛擬環境...
where py >nul 2>nul
if errorlevel 1 goto try_python_command

py -3.11 -m venv ".venv" 2>nul
if exist ".venv\Scripts\python.exe" goto install_packages

py -3 -m venv ".venv"
if exist ".venv\Scripts\python.exe" goto install_packages
goto venv_error

:try_python_command
where python >nul 2>nul
if errorlevel 1 goto python_not_found
python -m venv ".venv"
if not exist ".venv\Scripts\python.exe" goto venv_error

:install_packages
echo 正在準備安裝工具...
".venv\Scripts\python.exe" -m ensurepip --upgrade
if errorlevel 1 goto install_error

echo 正在安裝或更新必要套件，第一次執行可能需要數分鐘...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto install_error
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto install_error

echo 正在啟動貸款槓桿存股管理系統...
".venv\Scripts\python.exe" "launcher.py"
set "APP_EXIT_CODE=%ERRORLEVEL%"
if not "%APP_EXIT_CODE%"=="0" pause
popd
endlocal & exit /b %APP_EXIT_CODE%

:python_not_found
echo.
echo 找不到 Python。請先安裝 Python 3.11 或 3.12，安裝時勾選「Add Python to PATH」。
echo 安裝完成後，請重新雙擊 setup_and_run.bat。
goto failed

:venv_error
echo.
echo 無法建立 Python 虛擬環境，請確認 Python 安裝完整且磁碟有足夠空間。
goto failed

:install_error
echo.
echo 套件安裝失敗。請確認網路連線後，再執行一次 setup_and_run.bat。
goto failed

:workdir_error
echo.
echo 無法進入程式所在資料夾，請先將 ZIP 完整解壓縮後再執行。
goto failed_without_popd

:failed
popd

:failed_without_popd
pause
endlocal
exit /b 1
