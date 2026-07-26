@echo off
REM ══════════════════════════════════════════════════════════
REM  ZK Bridge Service — Installation via NSSM
REM  Lance ce script en tant qu'Administrateur (clic droit → Exécuter en tant qu'administrateur)
REM ══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM ── Vérification droits administrateur ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ╔══════════════════════════════════════════════════════╗
    echo ║  ERREUR : Ce script doit être lancé en Administrateur  ║
    echo ║  Clic droit → Exécuter en tant qu'administrateur       ║
    echo ╚══════════════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)

REM ── Vérification NSSM ──
where nssm >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ╔══════════════════════════════════════════════════════╗
    echo ║  ERREUR : nssm.exe introuvable dans le PATH          ║
    echo ║                                                        ║
    echo ║  Téléchargez NSSM depuis : https://nssm.cc/download   ║
    echo ║  Placez nssm.exe dans un dossier du PATH système       ║
    echo ║  (ex: C:\Windows\System32) ou dans ce dossier.          ║
    echo ╚══════════════════════════════════════════════════════╝
    echo.
    REM Vérifier aussi dans le dossier courant
    if exist "%~dp0nssm.exe" (
        echo nssm.exe trouvé dans le dossier courant, utilisation locale.
        set "NSSM=%~dp0nssm.exe"
        goto :nssm_found
    )
    pause
    exit /b 1
)
set "NSSM=nssm"
:nssm_found

REM ── Définition des chemins (relatifs au dossier du script) ──
set "SERVICE_NAME=ZKBridgeService"
set "SCRIPT_DIR=%~dp0"
REM Supprimer le backslash final pour éviter les doubles backslashes
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "SERVICE_SCRIPT=%SCRIPT_DIR%\zk_bridge_service.py"

REM ── Détection automatique de python.exe ──
REM Essayer d'abord py (Python Launcher)
py -3 -c "import sys; print(sys.executable)" >"%TEMP%\python_path.tmp" 2>nul
if %errorlevel% equ 0 (
    set /p PYTHON_EXE=<"%TEMP%\python_path.tmp"
    del "%TEMP%\python_path.tmp" 2>nul
    goto :python_found
)

REM Essayer python directement
python -c "import sys; print(sys.executable)" >"%TEMP%\python_path.tmp" 2>nul
if %errorlevel% equ 0 (
    set /p PYTHON_EXE=<"%TEMP%\python_path.tmp"
    del "%TEMP%\python_path.tmp" 2>nul
    goto :python_found
)

REM Essayer le chemin connu
if exist "C:\Users\dell\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=C:\Users\dell\AppData\Local\Programs\Python\Python312\python.exe"
    goto :python_found
)

echo.
echo ERREUR : Impossible de trouver python.exe
echo Vérifiez que Python est installé et dans le PATH.
pause
exit /b 1

:python_found
echo.
echo ══════════════════════════════════════════════════════════
echo   Installation du service %SERVICE_NAME%
echo ══════════════════════════════════════════════════════════
echo.
echo   Python    : %PYTHON_EXE%
echo   Script    : %SERVICE_SCRIPT%
echo   Dossier   : %SCRIPT_DIR%
echo.

REM ── Arrêter et supprimer l'ancien service si présent ──
%NSSM% status %SERVICE_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo Service existant détecté, arrêt et suppression...
    %NSSM% stop %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
    %NSSM% remove %SERVICE_NAME% confirm >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo   Ancien service supprimé.
)

REM ── Installation du service ──
echo [1/7] Installation du service...
%NSSM% install %SERVICE_NAME% "%PYTHON_EXE%" "%SERVICE_SCRIPT%"
if %errorlevel% neq 0 (
    echo ERREUR lors de l'installation du service.
    pause
    exit /b 1
)

REM ── Configuration du répertoire de travail ──
echo [2/7] Répertoire de travail : %SCRIPT_DIR%
%NSSM% set %SERVICE_NAME% AppDirectory "%SCRIPT_DIR%"

REM ── Démarrage automatique avec Windows ──
echo [3/7] Démarrage automatique activé
%NSSM% set %SERVICE_NAME% Start SERVICE_AUTO_START

REM ── Redémarrage automatique en cas de crash ──
echo [4/7] Redémarrage auto en cas de crash (délai 5s)
%NSSM% set %SERVICE_NAME% AppExit Default Restart
%NSSM% set %SERVICE_NAME% AppRestartDelay 5000

REM ── Logs stdout/stderr ──
echo [5/7] Configuration des logs
%NSSM% set %SERVICE_NAME% AppStdout "%SCRIPT_DIR%\service_stdout.log"
%NSSM% set %SERVICE_NAME% AppStderr "%SCRIPT_DIR%\service_stderr.log"
%NSSM% set %SERVICE_NAME% AppStdoutCreationDisposition 4
%NSSM% set %SERVICE_NAME% AppStderrCreationDisposition 4
%NSSM% set %SERVICE_NAME% AppRotateFiles 1
%NSSM% set %SERVICE_NAME% AppRotateBytes 5242880

REM ── Description du service ──
echo [6/7] Description du service
%NSSM% set %SERVICE_NAME% Description "ZK Bridge Service - Pont entre Odoo et la pointeuse ZKTeco K60 Pro"
%NSSM% set %SERVICE_NAME% DisplayName "ZK Bridge Service (Winners Academy)"

REM ── Démarrage du service ──
echo [7/7] Démarrage du service...
%NSSM% start %SERVICE_NAME%
if %errorlevel% neq 0 (
    echo.
    echo AVERTISSEMENT : Le service n'a pas pu démarrer immédiatement.
    echo Vérifiez les logs : %SCRIPT_DIR%\service_stderr.log
    echo Ou dans services.msc, cherchez "%SERVICE_NAME%"
) else (
    echo.
    echo ╔══════════════════════════════════════════════════════╗
    echo ║  ✓ Service installé et démarré avec succès !          ║
    echo ║                                                        ║
    echo ║  Nom du service : %SERVICE_NAME%                  ║
    echo ║  Démarrage      : Automatique (avec Windows)           ║
    echo ║  Crash recovery : Redémarrage auto (5s)                ║
    echo ║                                                        ║
    echo ║  Vérifier : services.msc → ZKBridgeService             ║
    echo ║  Logs     : %SCRIPT_DIR%\zk_bridge.log          ║
    echo ╚══════════════════════════════════════════════════════╝
)
echo.
pause
