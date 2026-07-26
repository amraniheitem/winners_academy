@echo off
REM ══════════════════════════════════════════════════════════
REM  ZK Bridge Service — Désinstallation via NSSM
REM  Lance ce script en tant qu'Administrateur
REM ══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM ── Vérification droits administrateur ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERREUR : Ce script doit être lancé en Administrateur.
    echo Clic droit → Exécuter en tant qu'administrateur
    echo.
    pause
    exit /b 1
)

REM ── Vérification NSSM ──
where nssm >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%~dp0nssm.exe" (
        set "NSSM=%~dp0nssm.exe"
        goto :nssm_found
    )
    echo ERREUR : nssm.exe introuvable dans le PATH.
    pause
    exit /b 1
)
set "NSSM=nssm"
:nssm_found

set "SERVICE_NAME=ZKBridgeService"

echo.
echo ══════════════════════════════════════════════════════════
echo   Désinstallation du service %SERVICE_NAME%
echo ══════════════════════════════════════════════════════════
echo.

REM ── Vérifier si le service existe ──
%NSSM% status %SERVICE_NAME% >nul 2>&1
if %errorlevel% neq 0 (
    echo Le service %SERVICE_NAME% n'est pas installé.
    echo Rien à faire.
    echo.
    pause
    exit /b 0
)

REM ── Arrêt du service ──
echo [1/2] Arrêt du service...
%NSSM% stop %SERVICE_NAME%
timeout /t 3 /nobreak >nul

REM ── Suppression du service ──
echo [2/2] Suppression du service...
%NSSM% remove %SERVICE_NAME% confirm
if %errorlevel% neq 0 (
    echo ERREUR lors de la suppression du service.
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  ✓ Service %SERVICE_NAME% désinstallé.          ║
echo ║                                                      ║
echo ║  Les fichiers de logs restent dans le dossier :      ║
echo ║  - service_stdout.log                                ║
echo ║  - service_stderr.log                                ║
echo ║  - zk_bridge.log                                     ║
echo ║  Vous pouvez les supprimer manuellement si besoin.   ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause
