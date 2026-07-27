# ZK Bridge Portable - Installation et demarrage

## 1. Principe
Le pont `ZK Bridge` tourne maintenant en mode **portable auto-restart** :
- un petit watchdog PowerShell demarre le bridge en arriere-plan
- une tache planifiee Windows le relance au logon et au deblocage de session
- si le bridge tombe, il est relance automatiquement

Ce mode evite la dependance forte a `nssm.exe` et au service Windows classique.

## 2. Installation
1. Clic droit sur `install_service.bat`
2. Choisir **Executer en tant qu'administrateur**
3. Attendre la fin du script

Le script :
- cree le venv local dans `zk_bridge\.venv`
- installe les dependances Python
- cree la tache planifiee `Winners_ZKBridge_AutoStart`
- demarre le watchdog portable

## 3. Verification
Le bridge doit repondre sur :
- `http://localhost:5000/device/status`

Commandes utiles :

```powershell
Get-ScheduledTask Winners_ZKBridge_AutoStart
Invoke-RestMethod http://localhost:5000/device/status
```

## 4. Logs
Les fichiers importants sont :

| Fichier | Contenu |
|---------|---------|
| `zk_bridge.log` | Log principal du bridge |
| `portable_bridge_launcher.log` | Log du watchdog qui relance le bridge |

## 5. En cas de probleme
Si `device/status` ne repond pas :
1. Verifier que la tache `Winners_ZKBridge_AutoStart` existe
2. Regarder `portable_bridge_launcher.log`
3. Regarder `zk_bridge.log`
4. Relancer `install_service.bat`
