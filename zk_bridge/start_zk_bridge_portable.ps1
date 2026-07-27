param(
    [int]$RetryDelaySeconds = 10
)

$ErrorActionPreference = 'SilentlyContinue'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bridgeScript = Join-Path $scriptDir 'zk_bridge_service.py'
$logFile = Join-Path $scriptDir 'portable_bridge_launcher.log'
$statusUrl = 'http://localhost:5000/device/status'

function Write-Log {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logFile -Value $line
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $scriptDir '.venv\Scripts\pythonw.exe'),
        (Join-Path $scriptDir '.venv\Scripts\python.exe')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    return $null
}

function Test-Bridge {
    try {
        $resp = Invoke-RestMethod -Uri $statusUrl -Method Get -TimeoutSec 2
        return ($resp.success -eq $true)
    } catch {
        return $false
    }
}

function Start-BridgeProcess {
    param([string]$PythonExe)

    return Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @('-u', $bridgeScript) `
        -WorkingDirectory $scriptDir `
        -WindowStyle Hidden `
        -PassThru
}

$pythonExe = Resolve-Python
if (-not $pythonExe) {
    Write-Log 'Python introuvable pour lancer le bridge.'
    exit 1
}

Write-Log "Launcher demarre avec $pythonExe"

$bridgeProcess = $null
while ($true) {
    if (Test-Bridge) {
        Start-Sleep -Seconds 15
        continue
    }

    if (-not $bridgeProcess -or $bridgeProcess.HasExited) {
        Write-Log 'Bridge indisponible, demarrage automatique...'
        try {
            $bridgeProcess = Start-BridgeProcess -PythonExe $pythonExe
            Start-Sleep -Seconds 5
        } catch {
            Write-Log "Echec de demarrage: $($_.Exception.Message)"
            Start-Sleep -Seconds $RetryDelaySeconds
            continue
        }
    }

    if (Test-Bridge) {
        Write-Log "Bridge en ligne (PID=$($bridgeProcess.Id))"
        Start-Sleep -Seconds 30
    } else {
        Write-Log 'Bridge non repondu. Nouvelle tentative dans quelques secondes...'
        Start-Sleep -Seconds $RetryDelaySeconds
    }
}
