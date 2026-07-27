@echo off
setlocal enabledelayedexpansion
title ZK Bridge Portable Installer

REM Require administrator rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Please run this script as Administrator.
    echo Right-click the file and choose "Run as administrator".
    echo.
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"
set "PORTABLE_LAUNCHER=%SCRIPT_DIR%start_zk_bridge_portable.ps1"
set "SETUP_TASK=%SCRIPT_DIR%setup_zk_bridge_task.ps1"

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
    echo Install Python 3 and retry.
    echo.
    exit /b 1
)

REM Create or reuse a local virtual environment for the bridge
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating local bridge virtual environment...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo ERROR: Unable to create the bridge virtual environment.
        exit /b 1
    )
)

set "BRIDGE_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo Updating bridge dependencies...
"%BRIDGE_PYTHON%" -m pip install --upgrade pip >nul 2>&1
"%BRIDGE_PYTHON%" -m pip install -r "%REQUIREMENTS_FILE%"
if %errorlevel% neq 0 (
    echo ERROR: Could not install bridge dependencies from requirements.txt.
    exit /b 1
)

REM Sanity check: fail early if a required import is still missing
"%BRIDGE_PYTHON%" -c "import flask, requests, waitress, zk"
if %errorlevel% neq 0 (
    echo ERROR: One or more bridge dependencies are still missing.
    exit /b 1
)

if not exist "%PORTABLE_LAUNCHER%" (
    echo ERROR: Missing launcher script: %PORTABLE_LAUNCHER%
    exit /b 1
)

echo Installing portable ZK bridge auto-start task...
if exist "%SETUP_TASK%" (
    powershell -ExecutionPolicy Bypass -File "%SETUP_TASK%"
    if %errorlevel% neq 0 (
        echo ERROR: Scheduled task creation failed.
        exit /b 1
    )
) else (
    echo ERROR: Missing task setup script: %SETUP_TASK%
    exit /b 1
)

echo.
echo Starting ZK bridge watchdog...
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','%PORTABLE_LAUNCHER%') | Out-Null"

echo.
echo Waiting for http://localhost:5000/device/status ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok = $false; for ($i = 0; $i -lt 30; $i++) { try { $r = Invoke-RestMethod 'http://localhost:5000/device/status' -TimeoutSec 2; if ($r.success) { $ok = $true; break } } catch {} ; Start-Sleep -Seconds 1 }; if (-not $ok) { exit 1 }"
if %errorlevel% neq 0 (
    echo.
    echo WARNING: the bridge task was created, but the endpoint is not responding yet.
    echo Check %SCRIPT_DIR%zk_bridge.log and %SCRIPT_DIR%portable_bridge_launcher.log.
    echo.
) else (
    echo.
    echo SUCCESS: ZK bridge is ready on localhost:5000.
)

echo.
exit /b 0
