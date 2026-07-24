$DesktopPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), "Winners Academy.lnk")
$TargetFile = "C:\Users\dell\Desktop\winners\start_winners_silent.vbs"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($DesktopPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$TargetFile`""
$Shortcut.WorkingDirectory = "C:\Users\dell\Desktop\winners"
$Shortcut.Description = "Lancer Winners Academy"
$Shortcut.IconLocation = "shell32.dll, 14" # Standard application icon
$Shortcut.Save()

Write-Host "Raccourci Bureau créé avec succès sur : $DesktopPath"
