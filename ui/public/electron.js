const { app, BrowserWindow, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess = null;
let backendPort = 8765; // Fixed for MVP
let isDev = process.env.ELECTRON_START_URL ? true : false;
let backendRestarts = 0;
const MAX_RESTARTS = 3;

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
  // Wait for health check before creating window
  waitForBackend();
}

// 2. Backend Spawning & Watchdog
function startBackend() {
  if (backendProcess) return;

  let exePath;
  if (isDev) {
    // In Dev, we assume backend is running separately or via python script
    console.log("Dev Mode: Launch backend manually or assume running.");
    // Optional: spawn python script
    return;
  } else {
    // Production: Bundled EXE
    exePath = path.join(process.resourcesPath, 'backend', 'assistant-backend.exe');
  }

  console.log(`Spawning backend: ${exePath}`);
  
  if (!require('fs').existsSync(exePath)) {
      console.error("Backend EXE not found at: " + exePath);
      // Fallback for debugging built app in non-standard location
      return;
  }

  backendProcess = spawn(exePath, [], {
    stdio: ['ignore', 'pipe', 'pipe'], // Redirect logs?
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
    
    // Watchdog
    if (code !== 0 && backendRestarts < MAX_RESTARTS) {
      backendRestarts++;
      console.log(`Restarting backend (Attempt ${backendRestarts})...`);
      setTimeout(startBackend, 1000);
    } else if (code !== 0) {
      dialog.showErrorBox("Backend Error", "The AI Assistant service crashed and could not restart.");
    }
  });
}

function waitForBackend() {
  const checkInterval = setInterval(() => {
    http.get(`http://127.0.0.1:${backendPort}/health`, (res) => {
        if (res.statusCode === 200) {
            clearInterval(checkInterval);
            console.log("Backend online!");
            createWindow();
        }
    }).on('error', (err) => {
        console.log("Waiting for backend...");
    });
  }, 1000);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false, // Custom Titlebar
    titleBarStyle: 'hidden',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false, // For MVP ease
    },
    icon: path.join(__dirname, 'icon.ico') // If exists
  });

  const startUrl = process.env.ELECTRON_START_URL || 
    `file://${path.join(__dirname, '../build/index.html')}`;
  
  mainWindow.loadURL(startUrl);
  
  // Handshake version check
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
                // In future: Compare ver.backend with package.json version
            } catch(e) {}
        });
    });
}

// 3. Graceful Shutdown
async function shutdownBackend() {
    if (!backendProcess && isDev) return; // Dev mode

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
         
         req.on('error', () => resolve()); // If already dead
         req.write('');
         req.end();
         
         // Force kill safety net
         setTimeout(() => resolve(), 2000);
    });
}

app.on('window-all-closed', async () => {
  await shutdownBackend();
  if (process.platform !== 'darwin') app.quit();
});
