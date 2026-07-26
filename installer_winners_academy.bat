@echo off
setlocal enabledelayedexpansion
title Installation Automatique — Winners Academy Desktop
color 0A

:: =======================================================================
:: WINNERS ACADEMY DESKTOP — INSTALLATEUR AUTOMATIQUE (Juillet 2026)
:: =======================================================================

echo =======================================================================
echo          INSTALLATEUR AUTOMATIQUE — WINNERS ACADEMY DESKTOP
echo =======================================================================
echo.

:: Relaunch as administrator if needed
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Redemarrage en administrateur requis...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: 1. Detection de Python
echo [1/4] Detection de l'environnement Python...
set "PYTHON_EXE="

if exist "C:\odoo17\venv\Scripts\python.exe" (
    set "PYTHON_EXE=C:\odoo17\venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=*" %%i in ('where python') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
        )
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) else if exist "C:\Python312\python.exe" (
        set "PYTHON_EXE=C:\Python312\python.exe"
    )
)

if not defined PYTHON_EXE (
    echo.
    echo [ATTENTION] Python n'a pas ete detecte sur ce PC.
    echo Veuillez installer Python depuis https://www.python.org/
    echo Cochez la case "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python detecte : "%PYTHON_EXE%"

:: 2. Creation automatique du venv C:\odoo17\venv si necessaire
if not exist "C:\odoo17\venv\Scripts\python.exe" (
    echo [INFO] Creation automatique de l'environnement virtuel C:\odoo17\venv...
    if not exist "C:\odoo17" mkdir "C:\odoo17"
    "%PYTHON_EXE%" -m venv "C:\odoo17\venv"
)

set "PYTHON_EXE=C:\odoo17\venv\Scripts\python.exe"

:: 3. Verification Odoo
if not exist "C:\odoo17\odoo-bin" (
    echo [INFO] Odoo 17 initialise dans C:\odoo17.
)

:: 4. Installation / mise a jour des modules Winners
echo.
echo [2/4] Installation et mise a jour des modules custom Winners...
set "PYTHONPATH=C:\odoo17"
if exist "C:\odoo17\odoo-bin" (
    pushd "C:\odoo17"
    "%PYTHON_EXE%" "C:\odoo17\odoo-bin" -c "C:\odoo17\odoo.conf" -d winners_db -i winners_auth,winners_branch,winners_student,winners_enrollment,winners_teacher,winners_room,winners_group,winners_schedule,winners_attendance,winners_payment,winners_salary,winners_print,winners_dashboard,winners_tv,winners_theme -u winners_auth,winners_branch,winners_student,winners_enrollment,winners_teacher,winners_room,winners_group,winners_schedule,winners_attendance,winners_payment,winners_salary,winners_print,winners_dashboard,winners_tv,winners_theme
    popd
)

:: 5. Traduction & Formatage Chiffres (123)
echo.
echo [3/4] Application des traductions bilingues et formatage des chiffres 123...
if exist "%~dp0scratch_master_i18n_fix.py" (
    "%PYTHON_EXE%" "%~dp0scratch_master_i18n_fix.py"
)

:: 6. Creation du Raccourci Bureau Application Native
echo.
echo [4/4] Creation du raccourci Bureau Application Native...
if exist "%~dp0create_desktop_shortcut.ps1" (
    powershell -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
)

:: 7. Installation du service ZK Bridge en arriere-plan
echo.
echo [5/5] Installation et demarrage du service ZK Bridge...
if exist "%~dp0zk_bridge\install_service.bat" (
    call "%~dp0zk_bridge\install_service.bat"
) else (
    echo [ATTENTION] Script ZK Bridge introuvable: "%~dp0zk_bridge\install_service.bat"
)

if exist "%~dp0zk_bridge\setup_zk_task.ps1" (
    powershell -ExecutionPolicy Bypass -File "%~dp0zk_bridge\setup_zk_task.ps1"
)

echo.
echo =======================================================================
echo [SUCCES] L'installation de Winners Academy Desktop est terminee !
echo L'icone "Winners Academy" a ete creee sur votre Bureau Windows.
echo =======================================================================
