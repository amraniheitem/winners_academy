@echo off
setlocal enabledelayedexpansion
title ZK Bridge Service Uninstaller

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Please run this script as Administrator.
    echo.
    exit /b 1
)

set "SERVICE_NAME=ZKBridgeService"
set "SCRIPT_DIR=%~dp0"

REM Prefer the local nssm.exe shipped with the project
set "NSSM="
if exist "%SCRIPT_DIR%nssm.exe" (
    set "NSSM=%SCRIPT_DIR%nssm.exe"
) else (
    where nssm >nul 2>&1
    if !errorlevel! equ 0 set "NSSM=nssm"
)

echo.
echo Removing %SERVICE_NAME%...
echo.

if defined NSSM (
    "%NSSM%" status %SERVICE_NAME% >nul 2>&1
    if %errorlevel% neq 0 (
        echo Service %SERVICE_NAME% is not installed.
        exit /b 0
    )

    "%NSSM%" stop %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
    "%NSSM%" remove %SERVICE_NAME% confirm
    if %errorlevel% neq 0 (
        echo ERROR: service removal failed.
        exit /b 1
    )
) else (
    REM Fallback when nssm.exe is missing
    sc query %SERVICE_NAME% >nul 2>&1
    if %errorlevel% neq 0 (
        echo Service %SERVICE_NAME% is not installed.
        exit /b 0
    )

    sc stop %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
    sc delete %SERVICE_NAME%
)

echo.
echo SUCCESS: %SERVICE_NAME% removed.
echo.
exit /b 0
