Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
Set WshEnv = WshShell.Environment("Process")

' Get dynamic directory of the script
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Set PYTHONPATH so Odoo module can be found
WshEnv("PYTHONPATH") = "C:\odoo17"

' 1. Lancement silencieux du serveur Odoo 17 (Fenêtre masquée = 0)
WshShell.CurrentDirectory = "C:\odoo17"
WshShell.Run """C:\odoo17\venv\Scripts\python.exe"" ""C:\odoo17\odoo-bin"" -c ""C:\odoo17\odoo.conf""", 0, False

' 2. Lancement silencieux du pont biométrique ZKTeco (Fenêtre masquée = 0)
ZkScript = ScriptDir & "\zk_bridge\zk_bridge_service.py"
If FSO.FileExists(ZkScript) Then
    WshShell.Run """C:\odoo17\venv\Scripts\python.exe"" """ & ZkScript & """", 0, False
End If

' 3. Pause d'initialisation de 3 secondes
WScript.Sleep 3000

' 4. Lancement en MODE APPLICATION NATIVE DÉDIÉE
Dim appCmd
appCmd = """C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"" --app=http://localhost:8069/web --title=""Winners Academy"""

If Not FSO.FileExists("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") Then
    If FSO.FileExists("C:\Program Files\Google\Chrome\Application\chrome.exe") Then
        appCmd = """C:\Program Files\Google\Chrome\Application\chrome.exe"" --app=http://localhost:8069/web"
    Else
        appCmd = "http://localhost:8069/web"
    End If
End If

WshShell.Run appCmd, 1, False
