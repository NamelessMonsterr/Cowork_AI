const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow;
let backendProcess;

const BACKEND_URL = "http://127.0.0.1:8765";

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    icon: path.join(__dirname, "assets/icon.ico"),
    title: "Cowork Assistant",
  });

  // Load UI
  mainWindow.loadFile("ui/index.html");

  // Open DevTools in development
  if (process.env.NODE_ENV === "development") {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function startBackend() {
  // Try to find bundled backend first
  const bundledPath = path.join(
    process.resourcesPath,
    "backend",
    "CoworkAssistant.exe"
  );

  if (require("fs").existsSync(bundledPath)) {
    // Production: use bundled exe
    backendProcess = spawn(bundledPath, [], { detached: false });
  } else {
    // Development: use Python directly
    backendProcess = spawn(
      "python",
      ["-m", "uvicorn", "assistant.main:app", "--port", "8765"],
      {
        cwd: __dirname,
      }
    );
  }

  backendProcess.stdout.on("data", (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`Backend: ${data}`);
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

// Wait for backend to be ready
async function waitForBackend(maxRetries = 30) {
  const http = require("http");

  for (let i = 0; i < maxRetries; i++) {
    try {
      await new Promise((resolve, reject) => {
        http
          .get(`${BACKEND_URL}/health`, (res) => {
            if (res.statusCode === 200) resolve();
            else reject();
          })
          .on("error", reject);
      });
      console.log("Backend ready");
      return true;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  console.error("Backend failed to start");
  return false;
}

app.whenReady().then(async () => {
  startBackend();
  await waitForBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on("before-quit", () => {
  stopBackend();
});

// IPC handlers for renderer
ipcMain.handle("get-backend-url", () => BACKEND_URL);
