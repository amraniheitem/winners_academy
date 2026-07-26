// ============================================================================
// Winners TV — Electron Main Process
// Application de bureau Kiosk / Plein Écran pour l'Affichage TV (Odoo 17 /tv)
// ============================================================================

const { app, BrowserWindow, Menu, Tray, shell, dialog, nativeImage, globalShortcut } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const fs = require('fs');

function resolveZkBridgeScript() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'zk_bridge', 'zk_bridge_service.py');
  }
  return path.join(__dirname, '..', 'zk_bridge', 'zk_bridge_service.py');
}

// ── Configuration ───────────────────────────────────────────────────────────
const CONFIG = {
  odoo: {
    python: 'C:\\odoo17\\venv\\Scripts\\python.exe',
    bin: 'C:\\odoo17\\odoo-bin',
    conf: 'C:\\odoo17\\odoo.conf',
    url: 'http://localhost:8069',
    tvPath: '/tv',
    host: 'localhost',
    port: 8069,
  },
  zkBridge: {
    script: resolveZkBridgeScript(),
  },
  app: {
    title: 'Winners TV — Écran d\'Affichage',
  },
};

// ── State ───────────────────────────────────────────────────────────────────
let mainWindow = null;
let splashWindow = null;
let tray = null;
let odooProcess = null;
let zkBridgeProcess = null;
let isQuitting = false;

// ── Single Instance Lock ────────────────────────────────────────────────────
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ── Utility: Check if Odoo port is ready ────────────────────────────────────
function waitForOdoo(maxAttempts = 60, interval = 1500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const tryConnect = () => {
      attempts++;
      const socket = new net.Socket();
      socket.setTimeout(1000);
      socket.on('connect', () => {
        socket.destroy();
        resolve();
      });
      socket.on('timeout', () => {
        socket.destroy();
        if (attempts >= maxAttempts) {
          reject(new Error('Le serveur Odoo n\'a pas répondu à temps'));
        } else {
          setTimeout(tryConnect, interval);
        }
      });
      socket.on('error', () => {
        socket.destroy();
        if (attempts >= maxAttempts) {
          reject(new Error('Le serveur Odoo n\'a pas répondu à temps'));
        } else {
          setTimeout(tryConnect, interval);
        }
      });
      socket.connect(CONFIG.odoo.port, CONFIG.odoo.host);
    };
    tryConnect();
  });
}

// ── Utility: Check if Odoo is running ───────────────────────────────────────
function isOdooRunning() {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(800);
    socket.on('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.on('error', () => {
      socket.destroy();
      resolve(false);
    });
    socket.connect(CONFIG.odoo.port, CONFIG.odoo.host);
  });
}

// ── Launch Odoo Server ──────────────────────────────────────────────────────
async function launchOdoo() {
  const alreadyRunning = await isOdooRunning();
  if (alreadyRunning) {
    console.log('[Odoo] Serveur déjà en cours d\'exécution sur le port', CONFIG.odoo.port);
    return;
  }

  if (!fs.existsSync(CONFIG.odoo.python)) {
    dialog.showErrorBox(
      'Erreur de Configuration',
      `Python introuvable à : ${CONFIG.odoo.python}\n\nVeuillez vérifier l'installation.`
    );
    app.quit();
    return;
  }

  console.log('[Odoo] Démarrage du serveur Odoo...');
  odooProcess = spawn(CONFIG.odoo.python, [CONFIG.odoo.bin, '-c', CONFIG.odoo.conf], {
    cwd: 'C:\\odoo17',
    env: { ...process.env, PYTHONPATH: 'C:\\odoo17' },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
    windowsHide: true,
  });

  if (odooProcess.stdout) {
    odooProcess.stdout.on('data', (data) => {
      console.log('[Odoo]', data.toString().trim());
    });
  }
  if (odooProcess.stderr) {
    odooProcess.stderr.on('data', (data) => {
      console.error('[Odoo:err]', data.toString().trim());
    });
  }

  odooProcess.on('error', (err) => {
    console.error('[Odoo] Échec de démarrage:', err.message);
  });

  odooProcess.on('exit', (code) => {
    console.log('[Odoo] Processus terminé avec le code', code);
    odooProcess = null;
  });
}

// ── ZK Bridge Configuration ─────────────────────────────────────────────────
const ZK_BRIDGE_PORT = 5000;
const ZK_BRIDGE_HOST = 'localhost';
const ZK_WATCHDOG_INTERVAL = 30000;
let zkWatchdogTimer = null;

function isZKBridgeRunning() {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(1500);
    socket.on('connect', () => { socket.destroy(); resolve(true); });
    socket.on('timeout', () => { socket.destroy(); resolve(false); });
    socket.on('error', () => { socket.destroy(); resolve(false); });
    socket.connect(ZK_BRIDGE_PORT, ZK_BRIDGE_HOST);
  });
}

// ── Launch ZK Bridge ────────────────────────────────────────────────────────
async function launchZKBridge() {
  if (!fs.existsSync(CONFIG.zkBridge.script)) {
    console.log('[ZKBridge] Script non trouvé:', CONFIG.zkBridge.script);
    return;
  }

  const alreadyRunning = await isZKBridgeRunning();
  if (alreadyRunning) {
    console.log('[ZKBridge] Service déjà en cours sur le port', ZK_BRIDGE_PORT);
    return;
  }

  console.log('[ZKBridge] Démarrage du service ZK Bridge...');
  zkBridgeProcess = spawn(CONFIG.odoo.python, [CONFIG.zkBridge.script], {
    stdio: 'ignore',
    detached: false,
    windowsHide: true,
  });

  zkBridgeProcess.on('error', (err) => {
    console.error('[ZKBridge] Échec de démarrage:', err.message);
    zkBridgeProcess = null;
  });

  zkBridgeProcess.on('exit', (code) => {
    console.log('[ZKBridge] Processus terminé avec le code', code);
    zkBridgeProcess = null;
  });
}

// ── ZK Bridge Watchdog ──────────────────────────────────────────────────────
function startZKBridgeWatchdog() {
  if (zkWatchdogTimer) return;
  console.log('[ZKBridge] Watchdog démarré — surveillance toutes les 30s');
  zkWatchdogTimer = setInterval(async () => {
    if (isQuitting) return;
    const running = await isZKBridgeRunning();
    if (!running) {
      console.warn('[ZKBridge] Watchdog: service DOWN — redémarrage auto...');
      await launchZKBridge();
    }
  }, ZK_WATCHDOG_INTERVAL);
}

function stopZKBridgeWatchdog() {
  if (zkWatchdogTimer) { clearInterval(zkWatchdogTimer); zkWatchdogTimer = null; }
}

// ── Create Splash Screen ───────────────────────────────────────────────────
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 360,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: false,
    center: true,
    title: 'Winners TV',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  splashWindow.loadFile(path.join(__dirname, 'splash_tv.html'));
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

// ── Resolve Icon Path ──────────────────────────────────────────────────────
function getIconPath() {
  const devIconPng = path.join(__dirname, 'assets', 'icon.png');
  const devIconIco = path.join(__dirname, 'assets', 'icon.ico');

  if (fs.existsSync(devIconPng)) return devIconPng;
  if (fs.existsSync(devIconIco)) return devIconIco;

  const extraPng = path.join(process.resourcesPath, 'assets', 'icon.png');
  const extraIco = path.join(process.resourcesPath, 'assets', 'icon.ico');
  if (fs.existsSync(extraPng)) return extraPng;
  if (fs.existsSync(extraIco)) return extraIco;

  return null;
}

// ── Create TV Application Window ──────────────────────────────────────────
function createMainWindow() {
  const iconPath = getIconPath();

  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    title: CONFIG.app.title,
    icon: iconPath || undefined,
    show: false,
    frame: false, // Frameless for TV kiosk look
    fullscreen: true, // Auto Fullscreen
    kiosk: true, // Kiosk mode for public TV display
    autoHideMenuBar: true,
    backgroundColor: '#0F172A',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      spellcheck: false,
    },
  });

  // ── Custom Application Menu ───────────────────────────────────────────
  const menuTemplate = [
    {
      label: 'Winners TV',
      submenu: [
        {
          label: 'Rafraîchir (F5)',
          accelerator: 'F5',
          click: () => mainWindow.webContents.reload(),
        },
        {
          label: 'Basculer Plein Écran (F11)',
          accelerator: 'F11',
          click: () => {
            const isKiosk = mainWindow.isKiosk();
            mainWindow.setKiosk(!isKiosk);
            mainWindow.setFullScreen(!isKiosk);
          },
        },
        {
          label: 'Quitter le Mode Kiosque (Échap)',
          accelerator: 'Escape',
          click: () => {
            mainWindow.setKiosk(false);
            mainWindow.setFullScreen(false);
          },
        },
        { type: 'separator' },
        {
          label: 'Quitter Application',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            isQuitting = true;
            app.quit();
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  // ── Load Odoo TV Page ─────────────────────────────────────────────────
  const tvUrl = CONFIG.odoo.url + CONFIG.odoo.tvPath;
  console.log('[TV] Chargement de l\'URL TV:', tvUrl);
  mainWindow.loadURL(tvUrl);

  // ── Show Window once Content is Ready ────────────────────────────────
  let windowShown = false;

  const showMainWindow = () => {
    if (windowShown) return;
    windowShown = true;
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    mainWindow.show();
    mainWindow.focus();
    console.log('[TV] Fenêtre TV affichée en Plein Écran');
  };

  mainWindow.once('ready-to-show', () => {
    showMainWindow();
  });

  setTimeout(() => {
    showMainWindow();
  }, 8000);

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('[TV] Échec de chargement de la page TV:', errorCode, errorDescription);
    setTimeout(() => {
      mainWindow.loadURL(tvUrl);
    }, 3000);
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(CONFIG.odoo.url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.webContents.on('page-title-updated', (event) => {
    event.preventDefault();
    mainWindow.setTitle(CONFIG.app.title);
  });
}

// ── System Tray ─────────────────────────────────────────────────────────────
function createTray() {
  try {
    const iconPath = getIconPath();
    let trayIcon;

    if (iconPath) {
      trayIcon = nativeImage.createFromPath(iconPath);
      if (!trayIcon.isEmpty()) {
        trayIcon = trayIcon.resize({ width: 16, height: 16 });
      } else {
        return;
      }
    } else {
      return;
    }

    tray = new Tray(trayIcon);
    tray.setToolTip('Winners TV — Écran d\'Affichage');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Afficher Winners TV',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      {
        label: 'Basculer Plein Écran (F11)',
        click: () => {
          if (mainWindow) {
            const isKiosk = mainWindow.isKiosk();
            mainWindow.setKiosk(!isKiosk);
            mainWindow.setFullScreen(!isKiosk);
          }
        },
      },
      { type: 'separator' },
      {
        label: 'Quitter',
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  } catch (err) {
    console.warn('[Tray] Erreur création tray:', err.message);
  }
}

// ── Cleanup ─────────────────────────────────────────────────────────────────
function cleanupProcesses() {
  stopZKBridgeWatchdog();
  if (odooProcess && !odooProcess.killed) {
    try { process.kill(odooProcess.pid); } catch (e) {}
  }
  if (zkBridgeProcess && !zkBridgeProcess.killed) {
    try { process.kill(zkBridgeProcess.pid); } catch (e) {}
  }
}

// ── App Lifecycle ───────────────────────────────────────────────────────────
app.on('ready', async () => {
  console.log('[TV] Démarrage de Winners TV Desktop...');

  createSplashWindow();

  await launchOdoo();
  await launchZKBridge();

  try {
    await waitForOdoo(60, 1500);
    console.log('[TV] Le serveur Odoo est prêt !');
  } catch (err) {
    console.error('[TV]', err.message);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    dialog.showErrorBox(
      'Erreur de Démarrage Winners TV',
      'Le serveur Odoo n\'a pas répondu dans le délai imparti.\n\nVérifiez PostgreSQL et le serveur Odoo.'
    );
    app.quit();
    return;
  }

  createMainWindow();
  createTray();

  // Start ZK Bridge watchdog (auto-restart si crash)
  startZKBridgeWatchdog();
});

app.on('before-quit', () => {
  isQuitting = true;
  cleanupProcesses();
});

app.on('window-all-closed', () => {
  cleanupProcesses();
  app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) {
    createMainWindow();
  } else {
    mainWindow.show();
  }
});
