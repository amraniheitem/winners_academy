@echo off
setlocal enabledelayedexpansion
title ZK Bridge Service Installer

REM Require administrator rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Please run this script as Administrator.
    echo Right-click the file and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

set "SERVICE_NAME=ZKBridgeService"
set "SCRIPT_DIR=%~dp0"
set "SERVICE_SCRIPT=%SCRIPT_DIR%zk_bridge_service.py"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"

REM Prefer the local nssm.exe shipped with the project
set "NSSM="
if exist "%SCRIPT_DIR%nssm.exe" (
    set "NSSM=%SCRIPT_DIR%nssm.exe"
) else (
    where nssm >nul 2>&1
    if !errorlevel! equ 0 set "NSSM=nssm"
)

if not defined NSSM (
    echo.
    echo ERROR: nssm.exe was not found.
    echo Keep nssm.exe inside the zk_bridge folder or add it to PATH.
    echo.
    pause
    exit /b 1
)

REM Detect Python available on the machine
set "PYTHON_EXE="
py -3 -c "import sys; print(sys.executable)" > "%TEMP%\python_path.tmp" 2>nul
if %errorlevel% equ 0 (
    set /p PYTHON_EXE=<"%TEMP%\python_path.tmp"
    del "%TEMP%\python_path.tmp" 2>nul
)

if not defined PYTHON_EXE (
    python -c "import sys; print(sys.executable)" > "%TEMP%\python_path.tmp" 2>nul
    if %errorlevel% equ 0 (
        set /p PYTHON_EXE=<"%TEMP%\python_path.tmp"
        del "%TEMP%\python_path.tmp" 2>nul
    )
)

if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if not defined PYTHON_EXE if exist "C:\Python312\python.exe" (
    set "PYTHON_EXE=C:\Python312\python.exe"
) else if not defined PYTHON_EXE if exist "C:\Python311\python.exe" (
    set "PYTHON_EXE=C:\Python311\python.exe"
)

if not defined PYTHON_EXE (
    echo.
    echo ERROR: Python was not found.
    pause
    exit /b 1
)

REM Create or reuse a local virtual environment for the bridge
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating local bridge virtual environment...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo ERROR: Unable to create the bridge virtual environment.
        pause
        exit /b 1
    )
)

set "BRIDGE_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo Updating bridge dependencies...
"%BRIDGE_PYTHON%" -m pip install --upgrade pip >nul 2>&1
"%BRIDGE_PYTHON%" -m pip install -r "%REQUIREMENTS_FILE%"
if %errorlevel% neq 0 (
    echo ERROR: Could not install bridge dependencies from requirements.txt.
    pause
    exit /b 1
)

echo Installing %SERVICE_NAME%...
echo System Python: %PYTHON_EXE%
echo Bridge Python: %BRIDGE_PYTHON%
echo Script: %SERVICE_SCRIPT%

REM Remove an existing service first
"%NSSM%" status %SERVICE_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    "%NSSM%" stop %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
    "%NSSM%" remove %SERVICE_NAME% confirm >nul 2>&1
    timeout /t 2 /nobreak >nul
)

"%NSSM%" install %SERVICE_NAME% "%BRIDGE_PYTHON%" "%SERVICE_SCRIPT%"
if %errorlevel% neq 0 (
    echo ERROR: service installation failed.
    pause
    exit /b 1
)

"%NSSM%" set %SERVICE_NAME% AppDirectory "%SCRIPT_DIR%"
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICE_NAME% AppExit Default Restart
"%NSSM%" set %SERVICE_NAME% AppRestartDelay 5000
"%NSSM%" set %SERVICE_NAME% AppStdout "%SCRIPT_DIR%service_stdout.log"
"%NSSM%" set %SERVICE_NAME% AppStderr "%SCRIPT_DIR%service_stderr.log"
"%NSSM%" set %SERVICE_NAME% AppStdoutCreationDisposition 4
"%NSSM%" set %SERVICE_NAME% AppStderrCreationDisposition 4
"%NSSM%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM%" set %SERVICE_NAME% AppRotateBytes 5242880
"%NSSM%" set %SERVICE_NAME% Description "ZK Bridge Service - bridge between Odoo and the ZKTeco device"
"%NSSM%" set %SERVICE_NAME% DisplayName "ZK Bridge Service (Winners Academy)"

"%NSSM%" start %SERVICE_NAME%
if %errorlevel% neq 0 (
    echo.
    echo WARNING: the service was installed but did not start immediately.
    echo Check %SCRIPT_DIR%service_stderr.log for details.
) else (
    echo.
    echo SUCCESS: %SERVICE_NAME% installed and started.
)

echo.
pause
