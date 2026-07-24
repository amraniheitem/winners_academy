$DesktopPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), "Winners Academy.lnk")
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Priority 1: Electron Native Executable
$ElectronPath1 = "$env:LOCALAPPDATA\Programs\winners-academy\Winners Academy.exe"
$ElectronPath2 = "C:\Program Files\Winners Academy\Winners Academy.exe"
$ElectronPath3 = "$ScriptDir\winners-electron\dist\win-unpacked\Winners Academy.exe"

$TargetPath = ""
$Arguments = ""
$IconPath = ""

if (Test-Path $ElectronPath1) {
    $TargetPath = $ElectronPath1
    $IconPath = "$ElectronPath1,0"
} elseif (Test-Path $ElectronPath2) {
    $TargetPath = $ElectronPath2
    $IconPath = "$ElectronPath2,0"
} elseif (Test-Path $ElectronPath3) {
    $TargetPath = $ElectronPath3
    $IconPath = "$ElectronPath3,0"
} else {
    # Fallback to Silent VBS launch
    $TargetPath = "C:\Windows\System32\wscript.exe"
    $Arguments = "`"$ScriptDir\start_winners_silent.vbs`""
    $IconPath = "shell32.dll,14"
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($DesktopPath)
$Shortcut.TargetPath = $TargetPath
if ($Arguments) { $Shortcut.Arguments = $Arguments }
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Winners Academy - Application Desktop Native"
$Shortcut.IconLocation = $IconPath
$Shortcut.Save()

Write-Host "Raccourci Bureau créé avec succès sur : $DesktopPath"
