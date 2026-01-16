/**
 * Flash Assistant - Electron Main Process
 * P2: Production-grade with port discovery, watchdog, and recovery.
 */
const { app, BrowserWindow, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');
const os = require('os');

let mainWindow;
let backendProcess = null;
let backendPort = null;
let isDev = process.env.ELECTRON_START_URL ? true : false;
let backendRestarts = 0;
const MAX_RESTARTS = 3;
const HEALTH_CHECK_TIMEOUT = 30000; // 30 seconds

// P2.2: Port file path (matches Python's paths.py)
function getPortFilePath() {
  const appData = process.env.APPDATA || path.join(os.homedir(), '.coworkai');
  return path.join(appData, 'CoworkAI', 'backend.port');
}

// Read port from file written by backend
function readPortFile() {
  const portFile = getPortFilePath();
  if (!fs.existsSync(portFile)) {
    return null;
  }
  try {
    const data = JSON.parse(fs.readFileSync(portFile, 'utf8'));
    return data;
  } catch (e) {
    console.error('Failed to read port file:', e);
    return null;
  }
}

// 1. Single Instance Lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(startApp);
}

function startApp() {
  startBackend();
  waitForBackend();
}

// 2. Backend Spawning & Watchdog
function startBackend() {
  if (backendProcess) return;

  let exePath;
  if (isDev) {
    console.log("Dev Mode: Assuming backend is running separately.");
    // In dev, try to read port file or use default
    const portData = readPortFile();
    backendPort = portData ? portData.port : 8765;
    return;
  } else {
    // Production: Bundled EXE
    exePath = path.join(process.resourcesPath, 'backend', 'assistant-backend.exe');
  }

  console.log(`Spawning backend: ${exePath}`);
  
  if (!fs.existsSync(exePath)) {
    console.error("Backend EXE not found at: " + exePath);
    showRecoveryScreen("Backend executable not found. Please reinstall Flash Assistant.");
    return;
  }

  backendProcess = spawn(exePath, [], {
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend Err: ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
    
    // Watchdog: Restart on crash
    if (code !== 0 && backendRestarts < MAX_RESTARTS) {
      backendRestarts++;
      console.log(`Restarting backend (Attempt ${backendRestarts}/${MAX_RESTARTS})...`);
      setTimeout(startBackend, 2000);
    } else if (code !== 0) {
      showRecoveryScreen(`Backend crashed ${MAX_RESTARTS} times. Please check logs or reinstall.`);
    }
  });
}

function waitForBackend() {
  const startTime = Date.now();
  
  const checkInterval = setInterval(() => {
    // First, try to read port from file
    const portData = readPortFile();
    if (portData && portData.port) {
      backendPort = portData.port;
    } else if (!backendPort) {
      backendPort = 8765; // Fallback
    }
    
    http.get(`http://127.0.0.1:${backendPort}/health`, (res) => {
      if (res.statusCode === 200) {
        clearInterval(checkInterval);
        console.log(`Backend online at port ${backendPort}!`);
        backendRestarts = 0; // Reset counter on success
        createWindow();
      }
    }).on('error', (err) => {
      console.log("Waiting for backend...");
      
      // Timeout check
      if (Date.now() - startTime > HEALTH_CHECK_TIMEOUT) {
        clearInterval(checkInterval);
        showRecoveryScreen("Backend failed to start within 30 seconds. Please check logs.");
      }
    });
  }, 1000);
}

function showRecoveryScreen(message) {
  const result = dialog.showMessageBoxSync({
    type: 'error',
    title: 'Flash Assistant - Startup Error',
    message: message,
    buttons: ['View Logs', 'Retry', 'Quit'],
    defaultId: 1,
    cancelId: 2
  });
  
  if (result === 0) {
    // Open logs folder
    const logsPath = path.join(process.env.APPDATA || '', 'CoworkAI', 'logs');
    shell.openPath(logsPath);
  } else if (result === 1) {
    // Retry
    backendRestarts = 0;
    startApp();
  } else {
    app.quit();
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      // P2: Inject backend URL into renderer
      additionalArguments: [`--backend-port=${backendPort}`]
    },
    icon: path.join(__dirname, 'icon.ico')
  });

  // Inject backend URL as global variable
  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.webContents.executeJavaScript(`
      window.BACKEND_URL = 'http://127.0.0.1:${backendPort}';
      window.BACKEND_PORT = ${backendPort};
    `);
  });

  const startUrl = process.env.ELECTRON_START_URL || 
    `file://${path.join(__dirname, '../build/index.html')}`;
  
  mainWindow.loadURL(startUrl);
  
  checkVersionMatch();

  mainWindow.on('closed', () => mainWindow = null);
}

function checkVersionMatch() {
  http.get(`http://127.0.0.1:${backendPort}/version`, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      try {
        const ver = JSON.parse(data);
        console.log("Connected to Backend:", ver);
      } catch(e) {}
    });
  }).on('error', () => {});
}

// 3. Graceful Shutdown
async function shutdownBackend() {
  if (!backendProcess && isDev) return;

  console.log("Sending shutdown signal...");
  return new Promise((resolve) => {
    const req = http.request({
      hostname: '127.0.0.1',
      port: backendPort,
      path: '/shutdown',
      method: 'POST',
      headers: {'Content-Type': 'application/json'}
    }, (res) => {
      resolve();
    });
    
    req.on('error', () => resolve());
    req.write('');
    req.end();
    
    setTimeout(() => resolve(), 2000);
  });
}

app.on('window-all-closed', async () => {
  await shutdownBackend();
  if (process.platform !== 'darwin') app.quit();
});
