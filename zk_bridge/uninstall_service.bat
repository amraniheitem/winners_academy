@echo off
setlocal enabledelayedexpansion
title ZK Bridge Portable Uninstaller

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Please run this script as Administrator.
    echo.
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "TASK_NAME=Winners_ZKBridge_AutoStart"
set "SERVICE_NAME=ZKBridgeService"

echo.
echo Removing portable auto-start task: %TASK_NAME%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $task = Get-ScheduledTask -TaskName '%TASK_NAME%' -ErrorAction SilentlyContinue; if ($task) { Stop-ScheduledTask -TaskName '%TASK_NAME%' -ErrorAction SilentlyContinue | Out-Null; Unregister-ScheduledTask -TaskName '%TASK_NAME%' -Confirm:$false -ErrorAction SilentlyContinue | Out-Null; Write-Host 'Task removed.' } else { Write-Host 'Task not installed.' } } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo ERROR: Failed to remove the scheduled task.
    exit /b 1
)

REM Backward compatibility: remove the legacy Windows service if it still exists.
set "NSSM="
if exist "%SCRIPT_DIR%nssm.exe" (
    set "NSSM=%SCRIPT_DIR%nssm.exe"
) else (
    where nssm >nul 2>&1
    if !errorlevel! equ 0 set "NSSM=nssm"
)

if defined NSSM (
    "%NSSM%" status %SERVICE_NAME% >nul 2>&1
    if %errorlevel% equ 0 (
        "%NSSM%" stop %SERVICE_NAME% >nul 2>&1
        timeout /t 2 /nobreak >nul
        "%NSSM%" remove %SERVICE_NAME% confirm >nul 2>&1
    )
) else (
    sc query %SERVICE_NAME% >nul 2>&1
    if %errorlevel% equ 0 (
        sc stop %SERVICE_NAME% >nul 2>&1
        timeout /t 2 /nobreak >nul
        sc delete %SERVICE_NAME% >nul 2>&1
    )
)

echo.
echo SUCCESS: ZK Bridge portable auto-start removed.
echo.
exit /b 0
