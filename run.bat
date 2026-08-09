@echo off
setlocal EnableExtensions
chcp 65001 >nul

pushd "%~dp0"
if errorlevel 1 goto workdir_error

if not exist ".venv\Scripts\python.exe" goto environment_missing

".venv\Scripts\python.exe" "launcher.py"
set "APP_EXIT_CODE=%ERRORLEVEL%"
if not "%APP_EXIT_CODE%"=="0" pause
popd
endlocal & exit /b %APP_EXIT_CODE%

:environment_missing
echo 尚未建立執行環境，請先雙擊 setup_and_run.bat。
popd
pause
endlocal
exit /b 1

:workdir_error
echo 無法進入程式所在資料夾，請先將 ZIP 完整解壓縮後再執行。
pause
endlocal
exit /b 1
