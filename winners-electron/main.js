// ============================================================================
// Winners Academy — Electron Main Process
// Application de bureau native pour Winners Academy (Odoo 17)
// ============================================================================

const { app, BrowserWindow, Menu, Tray, shell, dialog, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const fs = require('fs');

// ── Configuration ───────────────────────────────────────────────────────────
const CONFIG = {
  odoo: {
    python: 'C:\\odoo17\\venv\\Scripts\\python.exe',
    bin: 'C:\\odoo17\\odoo-bin',
    conf: 'C:\\odoo17\\odoo.conf',
    url: 'http://localhost:8069',
    webPath: '/web',
    host: 'localhost',
    port: 8069,
  },
  zkBridge: {
    // Use absolute path — the zk_bridge lives in the winners project folder
    script: 'C:\\Users\\dell\\Desktop\\winners\\zk_bridge\\zk_bridge_service.py',
  },
  app: {
    title: 'Winners Academy',
    width: 1380,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
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
          reject(new Error('Odoo server did not start in time'));
        } else {
          setTimeout(tryConnect, interval);
        }
      });
      socket.on('error', () => {
        socket.destroy();
        if (attempts >= maxAttempts) {
          reject(new Error('Odoo server did not start in time'));
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
    console.log('[Odoo] Server is already running on port', CONFIG.odoo.port);
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

  console.log('[Odoo] Starting server...');
  odooProcess = spawn(CONFIG.odoo.python, [CONFIG.odoo.bin, '-c', CONFIG.odoo.conf], {
    cwd: 'C:\\odoo17',
    env: { ...process.env, PYTHONPATH: 'C:\\odoo17' },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
    windowsHide: true,
  });

  // Log Odoo stdout/stderr for debugging
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
    console.error('[Odoo] Failed to start:', err.message);
  });

  odooProcess.on('exit', (code) => {
    console.log('[Odoo] Process exited with code', code);
    odooProcess = null;
  });
}

// ── Launch ZK Bridge ────────────────────────────────────────────────────────
function launchZKBridge() {
  if (!fs.existsSync(CONFIG.zkBridge.script)) {
    console.log('[ZKBridge] Script not found, skipping:', CONFIG.zkBridge.script);
    return;
  }

  console.log('[ZKBridge] Starting bridge service...');
  zkBridgeProcess = spawn(CONFIG.odoo.python, [CONFIG.zkBridge.script], {
    stdio: 'ignore',
    detached: false,
    windowsHide: true,
  });

  zkBridgeProcess.on('error', (err) => {
    console.error('[ZKBridge] Failed to start:', err.message);
  });

  zkBridgeProcess.on('exit', (code) => {
    console.log('[ZKBridge] Process exited with code', code);
    zkBridgeProcess = null;
  });
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
    title: 'Winners Academy',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

// ── Resolve icon path (works in dev and packaged mode) ──────────────────────
function getIconPath() {
  // In packaged app, __dirname is inside app.asar
  // Assets are also packed, so use path within asar
  const devIconPng = path.join(__dirname, 'assets', 'icon.png');
  const devIconIco = path.join(__dirname, 'assets', 'icon.ico');

  if (fs.existsSync(devIconPng)) return devIconPng;
  if (fs.existsSync(devIconIco)) return devIconIco;

  // Fallback: try extraResources location
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
    frame: true,
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
      label: 'Winners Academy',
      submenu: [
        {
          label: 'Rafraîchir',
          accelerator: 'F5',
          click: () => mainWindow.webContents.reload(),
        },
        {
          label: 'Plein écran',
          accelerator: 'F11',
          click: () => mainWindow.setFullScreen(!mainWindow.isFullScreen()),
        },
        { type: 'separator' },
        {
          label: 'Zoom +',
          accelerator: 'CmdOrCtrl+=',
          click: () => {
            const zoom = mainWindow.webContents.getZoomFactor();
            mainWindow.webContents.setZoomFactor(Math.min(zoom + 0.1, 2.0));
          },
        },
        {
          label: 'Zoom -',
          accelerator: 'CmdOrCtrl+-',
          click: () => {
            const zoom = mainWindow.webContents.getZoomFactor();
            mainWindow.webContents.setZoomFactor(Math.max(zoom - 0.1, 0.5));
          },
        },
        {
          label: 'Zoom par défaut',
          accelerator: 'CmdOrCtrl+0',
          click: () => mainWindow.webContents.setZoomFactor(1.0),
        },
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

  // ── Load Odoo Web ─────────────────────────────────────────────────────
  console.log('[App] Loading URL:', CONFIG.odoo.url + CONFIG.odoo.webPath);
  mainWindow.loadURL(CONFIG.odoo.url + CONFIG.odoo.webPath);

  // ── Show window once content is ready ─────────────────────────────────
  let windowShown = false;

  const showMainWindow = () => {
    if (windowShown) return;
    windowShown = true;
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    mainWindow.show();
    mainWindow.maximize();
    mainWindow.focus();
    console.log('[App] Main window shown');
  };

  mainWindow.once('ready-to-show', () => {
    console.log('[App] ready-to-show fired');
    showMainWindow();
  });

  // Fallback: force show after 8 seconds even if ready-to-show hasn't fired
  setTimeout(() => {
    console.log('[App] Timeout fallback — forcing window display');
    showMainWindow();
  }, 8000);

  // Handle page load errors
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('[App] Page load failed:', errorCode, errorDescription);
    // Retry after 3 seconds
    setTimeout(() => {
      console.log('[App] Retrying page load...');
      mainWindow.loadURL(CONFIG.odoo.url + CONFIG.odoo.webPath);
    }, 3000);
  });

  // Prevent navigating away from Odoo domain
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(CONFIG.odoo.url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(CONFIG.odoo.url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  // Minimize to tray instead of closing (only if tray exists)
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Always show "Winners Academy" as window title
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
      if (trayIcon.isEmpty()) {
        console.warn('[Tray] Icon loaded but is empty, skipping tray');
        return;
      }
      trayIcon = trayIcon.resize({ width: 16, height: 16 });
    } else {
      console.warn('[Tray] No icon found, skipping tray creation');
      return;
    }

    tray = new Tray(trayIcon);
    tray.setToolTip('Winners Academy');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Ouvrir Winners Academy',
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
    console.log('[Tray] System tray created successfully');
  } catch (err) {
    console.warn('[Tray] Failed to create system tray:', err.message);
    // App works fine without tray
  }
}

// ── Cleanup background processes ────────────────────────────────────────────
function cleanupProcesses() {
  if (odooProcess && !odooProcess.killed) {
    console.log('[Cleanup] Killing Odoo process...');
    try { process.kill(odooProcess.pid); } catch (e) { /* ignore */ }
  }
  if (zkBridgeProcess && !zkBridgeProcess.killed) {
    console.log('[Cleanup] Killing ZKBridge process...');
    try { process.kill(zkBridgeProcess.pid); } catch (e) { /* ignore */ }
  }
}

// ── App Lifecycle ───────────────────────────────────────────────────────────
app.on('ready', async () => {
  console.log('[App] Winners Academy Desktop starting...');
  console.log('[App] __dirname:', __dirname);
  console.log('[App] resourcesPath:', process.resourcesPath);

  // 1. Show splash screen
  createSplashWindow();

  // 2. Launch backend services
  await launchOdoo();
  launchZKBridge();

  // 3. Wait for Odoo to be ready
  try {
    console.log('[App] Waiting for Odoo server...');
    await waitForOdoo(60, 1500);
    console.log('[App] Odoo server is ready!');
  } catch (err) {
    console.error('[App]', err.message);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    dialog.showErrorBox(
      'Erreur de Démarrage',
      'Le serveur Odoo n\'a pas répondu dans le délai imparti (90 secondes).\n\nVérifiez que :\n1. PostgreSQL est démarré\n2. La base de données est initialisée\n3. Le fichier odoo.conf est correct'
    );
    app.quit();
    return;
  }

  // 4. Create main window and system tray
  createMainWindow();
  createTray();
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
