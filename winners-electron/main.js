// ============================================================================
// Winners Academy & Winners TV — Electron Main Process
// Application de bureau native pour Winners Academy (Odoo 17) & Affichage TV (/tv)
// ============================================================================

const { app, BrowserWindow, Menu, Tray, shell, dialog, nativeImage } = require('electron');
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

// ── App Mode Detection (Academy vs TV) ──────────────────────────────────────
const appNameLower = (app.name || app.getName() || '').toLowerCase();
const isTV = appNameLower.includes('tv') ||
             process.argv.includes('--tv') ||
             process.env.APP_MODE === 'tv';

console.log('[App] Mode initialisé:', isTV ? 'WINNERS TV (/tv)' : 'WINNERS ACADEMY (/web)');

// ── Configuration ───────────────────────────────────────────────────────────
const CONFIG = {
  odoo: {
    python: 'C:\\odoo17\\venv\\Scripts\\python.exe',
    bin: 'C:\\odoo17\\odoo-bin',
    conf: 'C:\\odoo17\\odoo.conf',
    url: 'http://localhost:8069',
    webPath: isTV ? '/tv' : '/web',
    host: 'localhost',
    port: 8069,
  },
  zkBridge: {
    script: resolveZkBridgeScript(),
  },
  app: {
    title: isTV ? 'Winners TV — Écran d\'Affichage' : 'Winners Academy',
    width: isTV ? 1920 : 1380,
    height: isTV ? 1080 : 860,
    minWidth: 1024,
    minHeight: 700,
    kiosk: isTV,
    fullscreen: isTV,
    frame: !isTV,
    splashHtml: isTV ? 'splash_tv.html' : 'splash.html',
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

// ── Utility: Check if Odoo is already running ───────────────────────────────
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
    socket.connect(ZK_BRIDGE_PORT, ZK_BRIDGE_HOST);
  });
}

async function launchZKBridge() {
  if (!fs.existsSync(CONFIG.zkBridge.script)) {
    console.log('[ZKBridge] Script introuvable:', CONFIG.zkBridge.script);
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
  if (zkWatchdogTimer) {
    clearInterval(zkWatchdogTimer);
    zkWatchdogTimer = null;
  }
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
    title: CONFIG.app.title,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  splashWindow.loadFile(path.join(__dirname, CONFIG.app.splashHtml));
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

// ── Resolve icon path ──────────────────────────────────────────────────────
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

// ── Create Main Application Window ─────────────────────────────────────────
function createMainWindow() {
  const iconPath = getIconPath();
  console.log('[App] Icon path:', iconPath);

  mainWindow = new BrowserWindow({
    width: CONFIG.app.width,
    height: CONFIG.app.height,
    minWidth: CONFIG.app.minWidth,
    minHeight: CONFIG.app.minHeight,
    title: CONFIG.app.title,
    icon: iconPath || undefined,
    show: false,
    frame: CONFIG.app.frame,
    fullscreen: CONFIG.app.fullscreen,
    kiosk: CONFIG.app.kiosk,
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
      label: CONFIG.app.title,
      submenu: [
        {
          label: 'Rafraîchir',
          accelerator: 'F5',
          click: () => mainWindow.webContents.reload(),
        },
        {
          label: isTV ? 'Basculer Plein Écran' : 'Plein Écran',
          accelerator: 'F11',
          click: () => {
            if (isTV) {
              const isK = mainWindow.isKiosk();
              mainWindow.setKiosk(!isK);
              mainWindow.setFullScreen(!isK);
            } else {
              mainWindow.setFullScreen(!mainWindow.isFullScreen());
            }
          },
        },
        ...(isTV ? [{
          label: 'Quitter le Mode Kiosque (Échap)',
          accelerator: 'Escape',
          click: () => {
            mainWindow.setKiosk(false);
            mainWindow.setFullScreen(false);
          },
        }] : []),
        { type: 'separator' },
        {
          label: 'Quitter',
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

  // ── Load Target URL ───────────────────────────────────────────────────
  const targetUrl = CONFIG.odoo.url + CONFIG.odoo.webPath;
  console.log('[App] Chargement de l\'URL:', targetUrl);
  mainWindow.loadURL(targetUrl);

  // ── Show window once content is ready ─────────────────────────────────
  let windowShown = false;

  const showMainWindow = () => {
    if (windowShown) return;
    windowShown = true;
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    mainWindow.show();
    if (!isTV) {
      mainWindow.maximize();
    }
    mainWindow.focus();
    console.log('[App] Fenêtre affichée avec succès');
  };

  mainWindow.once('ready-to-show', () => {
    showMainWindow();
  });

  setTimeout(() => {
    showMainWindow();
  }, 8000);

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('[App] Échec de chargement:', errorCode, errorDescription);
    setTimeout(() => {
      mainWindow.loadURL(targetUrl);
    }, 3000);
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(CONFIG.odoo.url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(CONFIG.odoo.url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
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
      if (trayIcon.isEmpty()) return;
      trayIcon = trayIcon.resize({ width: 16, height: 16 });
    } else {
      return;
    }

    tray = new Tray(trayIcon);
    tray.setToolTip(CONFIG.app.title);

    const contextMenu = Menu.buildFromTemplate([
      {
        label: `Ouvrir ${CONFIG.app.title}`,
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
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
  console.log(`[App] Démarrage de ${CONFIG.app.title}...`);

  createSplashWindow();

  await launchOdoo();
  await launchZKBridge();

  try {
    await waitForOdoo(60, 1500);
    console.log('[App] Serveur Odoo prêt !');
  } catch (err) {
    console.error('[App]', err.message);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    dialog.showErrorBox(
      `Erreur de Démarrage — ${CONFIG.app.title}`,
      'Le serveur Odoo n\'a pas répondu dans le délai imparti.\n\nVérifiez PostgreSQL et la configuration.'
    );
    app.quit();
    return;
  }

  createMainWindow();
  createTray();

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
