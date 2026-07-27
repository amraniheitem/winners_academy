# ZK Bridge Notifier & Watcher - Notification native au demarrage et sortie de veille
param(
    [switch]$Watch = $false
)

$ErrorActionPreference = "SilentlyContinue"

function Show-Notification {
    param([string]$Title, [string]$Message)
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $toastXml = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>$Title</text>
            <text>$Message</text>
        </binding>
    </visual>
</toast>
"@
        $xml.LoadXml($toastXml)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        $appId = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId)
        $notifier.Show($toast)
    } catch {
        Add-Type -AssemblyName System.Windows.Forms
        $global:balloon = New-Object System.Windows.Forms.NotifyIcon
        $global:balloon.Icon = [System.Drawing.SystemIcons]::Information
        $global:balloon.BalloonTipTitle = $Title
        $global:balloon.BalloonTipText = $Message
        $global:balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
        $global:balloon.Visible = $true
        $global:balloon.ShowBalloonTip(5000)
    }
}

function Test-ZKBridgeStatus {
    $url = "http://localhost:5000/device/status"
    $title = "Winners Academy - ZK Bridge"
    $taskName = "Winners_ZKBridge_AutoStart"

    try {
        $resp = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 4
        if ($resp.success -eq $true -and $resp.data.connected -eq $true) {
            $ip = $resp.data.ip
            $users = $resp.data.user_count
            $msg = "ZK Bridge actif - Pointeuse connectee ($ip) [$users utilisateurs]"
        } elseif ($resp.error) {
            $msg = "ZK Bridge actif mais pointeuse injoignable: " + $resp.error
        } else {
            $msg = "Service ZK Bridge en cours d'initialisation..."
        }
    } catch {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        } else {
            $launcher = Join-Path $PSScriptRoot "start_zk_bridge_portable.ps1"
            if (Test-Path $launcher) {
                Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
                    "-ExecutionPolicy", "Bypass",
                    "-File", $launcher
                ) | Out-Null
            }
        }

        $msg = "Attention: ZK Bridge ne repond pas. Redemarrage automatique lance."
    }

    Show-Notification -Title $title -Message $msg
}

# 1. Verification immediate et notification au lancement
Test-ZKBridgeStatus

# 2. Si le mode -Watch est active, ecouter la sortie de veille en arriere-plan
if ($Watch) {
    Add-Type -AssemblyName Microsoft.Win32.SystemEvents
    
    $action = {
        param($sender, $e)
        if ($e.Reason -eq [Microsoft.Win32.SessionSwitchReason]::SessionUnlock -or $e.Reason -eq [Microsoft.Win32.SessionSwitchReason]::SessionLogon) {
            Start-Sleep -Seconds 2
            Test-ZKBridgeStatus
        }
    }

    [System.Diagnostics.EventLog]::WriteEntry("WinnersZK", "Démarrage du guetteur de sortie de veille ZK Bridge", "Information")
    [Microsoft.Win32.SystemEvents]::add_SessionSwitch($action)

    # Boucle d'attente silencieuse
    while ($true) {
        Start-Sleep -Seconds 10
    }
}
