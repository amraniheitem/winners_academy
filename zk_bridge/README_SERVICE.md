# ZK Bridge Service — Guide d'installation & Arrière-plan

## 1. Démarrage en arrière-plan sans fenêtre CMD
Le pont `ZK Bridge` s'exécute en tant que **Service Windows en arrière-plan** (`ZKBridgeService`).
- **Aucune fenêtre CMD** n'est affichée à l'écran.
- Impossible à fermer accidentellement par un employé (Ctrl+C ou fermeture de console).
- Démarrage automatique au lancement du PC.

## 2. Notification automatique (Au démarrage & Sortie de veille)
Un guetteur PowerShell silencieux (`zk_notifier.ps1`) vérifie le statut du service et de la pointeuse :
- Au **démarrage du PC / Ouverture de session**.
- À chaque **déverrouillage du PC / Sortie de veille**.
- Une **petite notification native Windows** apparaît en bas à droite pour confirmer l'état de la connexion.

## 3. Installer / Réinstaller le service Windows

1. **Clic droit** sur `install_service.bat` → **Exécuter en tant qu'administrateur**.
2. Le service `ZKBridgeService` est configuré en démarrage automatique avec redémarrage automatique en cas d'erreur.

## 4. Vérifier que le service tourne

Ouvrir `services.msc` (Win+R → `services.msc`) → chercher **"ZK Bridge Service (Winners Academy)"**. L'état doit être **"En cours d'exécution"**.

## 5. Logs système

| Fichier | Contenu |
|---------|---------|
| `zk_bridge.log` | Log applicatif principal (pointages, connexions, erreurs) |
| `service_stdout.log` | Sortie standard du processus (capturé par NSSM) |
| `service_stderr.log` | Erreurs système (import manquant, crash Python, etc.) |

