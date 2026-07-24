const { app, BrowserWindow, Menu, Tray, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');



// ── CONFIGURATION DES SERVICES ──
const CONFIG = {
  // Chemin vers l'exécutable Python du venv Odoo
  PYTHON_VENV: 'C:\\odoo17\\venv\\Scripts\\python.exe',
  // Chemin vers odoo-bin
  ODOO_BIN: 'C:\\odoo17\\odoo-bin',
  // Fichier de configuration d'Odoo
  ODOO_CONF: 'C:\\odoo17\\odoo.conf',
  // Liste des modules Winners à mettre à jour/vérifier
  ADDONS: 'winners_auth,winners_branch,winners_student,winners_enrollment,winners_teacher,winners_room,winners_group,winners_schedule,winners_attendance,winners_payment,winners_salary,winners_dashboard,winners_tv,winners_theme,winners_print',

  // Script ZK Bridge
  ZK_BRIDGE_SCRIPT: 'C:\\Users\\dell\\Desktop\\winners\\zk_bridge\\zk_bridge_service.py',
  // Python système à utiliser pour le Bridge ZK
  PYTHON_SYSTEM: 'python',

  // Ports et URLs
  ODOO_PORT: 8069,
  ODOO_URL: 'http://localhost:8069',
  TV_URL: 'http://localhost:8069/tv',
};

let odooProcess = null;
let zkBridgeProcess = null;
let erpWindow = null;
let tvWindow = null;
let tray = null;
let isQuitting = false;

// ── CRÉATION DES FICHIERS LOGS ──
const logDir = path.join(app.getPath('userData'), 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}
const odooLogStream = fs.createWriteStream(path.join(logDir, 'odoo_stdout.log'), { flags: 'a' });
const zkLogStream = fs.createWriteStream(path.join(logDir, 'zk_bridge_stdout.log'), { flags: 'a' });

function log(msg) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${msg}`);
}

// ── LANCEMENT D'ODOO ──
function startOdoo() {
  log("Démarrage du processus Odoo...");
  const args = [
    CONFIG.ODOO_BIN,
    '-c', CONFIG.ODOO_CONF,
    '-u', CONFIG.ADDONS,
    '--dev=asset'
  ];

  odooProcess = spawn(CONFIG.PYTHON_VENV, args, {
    cwd: path.dirname(CONFIG.ODOO_BIN),
    env: process.env,
  });

  odooProcess.stdout.pipe(odooLogStream);
  odooProcess.stderr.pipe(odooLogStream);

  odooProcess.on('close', (code) => {
    log(`Processus Odoo arrêté avec le code : ${code}`);
    if (!isQuitting) {
      log("Redémarrage d'Odoo dans 5 secondes...");
      setTimeout(startOdoo, 5000);
    }
  });
}

// ── LANCEMENT DU ZK BRIDGE ──
function startZkBridge() {
  log("Démarrage du service ZK Bridge...");

  zkBridgeProcess = spawn(CONFIG.PYTHON_SYSTEM, [CONFIG.ZK_BRIDGE_SCRIPT], {
    cwd: path.dirname(CONFIG.ZK_BRIDGE_SCRIPT),
    env: process.env,
  });

  zkBridgeProcess.stdout.pipe(zkLogStream);
  zkBridgeProcess.stderr.pipe(zkLogStream);

  zkBridgeProcess.on('close', (code) => {
    log(`Processus ZK Bridge arrêté avec le code : ${code}`);
    if (!isQuitting) {
      log("Redémarrage du ZK Bridge dans 5 secondes...");
      setTimeout(startZkBridge, 5000);
    }
  });
}

// ── ATTENTE QUE LE PORT D'ODOO SOIT PRÊT ──
function checkOdooReady(callback) {
  const checkInterval = 1000;
  const timer = setInterval(() => {
    const req = http.request({
      host: 'localhost',
      port: CONFIG.ODOO_PORT,
      path: '/web/health' // URL légère de healthcheck d'Odoo
    }, (res) => {
      // Si on a n'importe quelle réponse (même 404), c'est que le serveur écoute!
      log("Le serveur Odoo écoute sur le port 8069.");
      clearInterval(timer);
      callback();
    });

    req.on('error', (err) => {
      log("Attente du démarrage d'Odoo...");
    });

    req.end();
  }, checkInterval);
}

// ── CRÉATION DES FENÊTRES ──
function createWindows() {
  // 1. Fenêtre ERP
  erpWindow = new BrowserWindow({
    title: "Winners Academy - ERP",
    width: 1200,
    height: 800,
    show: false,
    icon: path.join(__dirname, '..', 'winners_aca.jpg'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  erpWindow.loadURL(CONFIG.ODOO_URL);
  erpWindow.maximize();
  erpWindow.show();

  // Empêche la fermeture de l'application si l'utilisateur clique sur la croix
  erpWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      erpWindow.hide();
      log("Masquage de la fenêtre ERP (toujours active en arrière-plan).");
    }
  });

  // 2. Fenêtre TV Display
  tvWindow = new BrowserWindow({
    title: "Winners Academy - TV Display",
    width: 1024,
    height: 768,
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, '..', 'winners_aca.jpg'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  tvWindow.loadURL(CONFIG.TV_URL);
  tvWindow.show();

  tvWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      tvWindow.hide();
      log("Masquage de la fenêtre TV Display (toujours active en arrière-plan).");
    }
  });

  // Création du menu système standard (facultatif, permet de recharger)
  const menuTemplate = [
    {
      label: 'Fichier',
      submenu: [
        { label: 'Masquer', click: () => { erpWindow.hide(); tvWindow.hide(); } },
        { type: 'separator' },
        { label: 'Quitter Winners Academy', click: quitApp }
      ]
    },
    {
      label: 'Affichage',
      submenu: [
        { label: 'Actualiser l\'ERP', click: () => erpWindow.reload() },
        { label: 'Actualiser la TV', click: () => tvWindow.reload() },
        { type: 'separator' },
        { label: 'Plein écran ERP', click: () => erpWindow.setFullScreen(!erpWindow.isFullScreen()) },
        { label: 'Plein écran TV', click: () => tvWindow.setFullScreen(!tvWindow.isFullScreen()) },
        { type: 'separator' },
        { role: 'toggleDevTools' }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);
}

// ── CRÉATION DE L'ICÔNE SYSTEM TRAY ──
function createTray() {
  const iconPath = path.join(__dirname, '..', 'winners_aca.jpg'); // Utilisation de l'image existante

  try {
    tray = new Tray(iconPath);
  } catch (err) {
    log("Impossible de charger l'icône Tray, fallback standard.");
    // Si l'image n'est pas au bon format, Electron utilisera une icône vide
    tray = new Tray(path.join(__dirname, 'package.json')); // Fallback temporaire
  }

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Ouvrir l\'ERP (Gestion)', click: () => { erpWindow.show(); erpWindow.focus(); } },
    { label: 'Ouvrir l\'Écran TV (Affichage)', click: () => { tvWindow.show(); tvWindow.focus(); } },
    { type: 'separator' },
    { label: 'Tout Afficher', click: () => { erpWindow.show(); tvWindow.show(); } },
    { label: 'Tout Masquer', click: () => { erpWindow.hide(); tvWindow.hide(); } },
    { type: 'separator' },
    { label: 'Quitter Winners Academy', click: quitApp }
  ]);

  tray.setToolTip('Winners Academy ERP & TV Server');
  tray.setContextMenu(contextMenu);

  // Double clic sur l'icône de la barre des tâches affiche l'ERP
  tray.on('double-click', () => {
    erpWindow.show();
    erpWindow.focus();
  });
}

// ── QUITTER PROPREMENT ──
function quitApp() {
  log("Fermeture de l'application...");
  isQuitting = true;

  // Tuer les sous-processus python
  if (odooProcess) {
    log("Arrêt du serveur Odoo...");
    odooProcess.kill('SIGINT');
  }

  if (zkBridgeProcess) {
    log("Arrêt du service ZK Bridge...");
    zkBridgeProcess.kill('SIGINT');
  }

  // Quitter Electron
  app.quit();
}

// ── EVENEMENTS DE CYCLE DE VIE ELECTRON ──
app.whenReady().then(() => {
  // Lancement des serveurs
  startOdoo();
  startZkBridge();

  // Attente et ouverture des fenêtres
  checkOdooReady(() => {
    createWindows();
    createTray();
  });
});

app.on('window-all-closed', () => {
  // Ne pas quitter l'application quand toutes les fenêtres sont fermées
  // (Elle tourne toujours en arrière-plan avec le Tray icon)
  log("Toutes les fenêtres ont été fermées par l'utilisateur. Odoo et le Bridge tournent en tâche de fond.");
});

// Sécurité supplémentaire : tuer les processus enfants si l'application s'arrête brutalement
process.on('exit', () => {
  if (odooProcess) odooProcess.kill('SIGINT');
  if (zkBridgeProcess) zkBridgeProcess.kill('SIGINT');
});
