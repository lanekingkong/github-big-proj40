/**
 * Electron Main Process
 * ====================
 * Entry point for the Electron desktop application.
 *
 * Responsibilities:
 * - Create and manage BrowserWindow instances
 * - Spawn Python FastAPI backend as a child process
 * - Bridge IPC communication between renderer and backend
 * - System tray integration
 * - Auto-update checks via electron-updater
 *
 * Architecture:
 *   Electron Main  <--IPC-->  Renderer (React)  <--HTTP/WS-->  Python Backend
 */

import {
  app,
  BrowserWindow,
  ipcMain,
  Tray,
  Menu,
  MenuItem,
  dialog,
  shell,
  nativeTheme,
} from "electron";
import * as path from "path";
import * as fs from "fs";
import { spawn, ChildProcess } from "child_process";
import { autoUpdater } from "electron-updater";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const IS_DEV: boolean = !app.isPackaged;
const PRELOAD_PATH: string = path.join(__dirname, "preload.js");
const BACKEND_PORT: number = 18090;
const BACKEND_HOST: string = "127.0.0.1";

// Paths
const PROJECT_ROOT: string = IS_DEV
  ? path.join(__dirname, "..", "..")
  : path.join(process.resourcesPath, "app.asar.unpacked");

const PYTHON_BACKEND_DIR: string = path.join(PROJECT_ROOT, "backend");
const PYTHON_ENTRY: string = path.join(PYTHON_BACKEND_DIR, "main.py");

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let tray: Tray | null = null;
let isQuitting: boolean = false;

// ---------------------------------------------------------------------------
// Python Backend Process Management
// ---------------------------------------------------------------------------

/**
 * Detect the Python executable path.
 * Priority: virtual env > system python3 > python
 */
function findPythonExecutable(): string {
  // Try virtual environment first
  const venvPython = path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe");
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  // Fallback to system Python
  return "python";
}

/**
 * Spawn the Python FastAPI backend process.
 * Sets up stdout/stderr piping for log capture and forwards logs to renderer.
 */
function spawnBackend(): void {
  if (backendProcess) {
    console.warn("[Main] Backend process already running");
    return;
  }

  const pythonExe = findPythonExecutable();
  console.log(`[Main] Starting backend: ${pythonExe} ${PYTHON_ENTRY}`);

  backendProcess = spawn(pythonExe, [PYTHON_ENTRY], {
    cwd: PYTHON_BACKEND_DIR,
    env: {
      ...process.env,
      AGENTFORGE_HOST: BACKEND_HOST,
      AGENTFORGE_PORT: String(BACKEND_PORT),
      PYTHONUNBUFFERED: "1",
    },
    stdio: ["pipe", "pipe", "pipe"],
  });

  // Forward stdout to renderer as log events
  if (backendProcess.stdout) {
    backendProcess.stdout.on("data", (data: Buffer) => {
      const message = data.toString().trim();
      if (message && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("backend:log", {
          level: "info",
          message,
          source: "backend",
        });
      }
    });
  }

  // Forward stderr to renderer as error log events
  if (backendProcess.stderr) {
    backendProcess.stderr.on("data", (data: Buffer) => {
      const message = data.toString().trim();
      if (message && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("backend:log", {
          level: "error",
          message,
          source: "backend",
        });
      }
    });
  }

  // Handle backend process exit
  backendProcess.on("exit", (code: number | null, signal: string | null) => {
    console.log(`[Main] Backend process exited: code=${code}, signal=${signal}`);
    backendProcess = null;

    if (!isQuitting && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("backend:status", {
        running: false,
        exitCode: code,
        signal,
      });
    }
  });

  backendProcess.on("error", (err: Error) => {
    console.error(`[Main] Backend process error:`, err);
    backendProcess = null;
  });

  // Notify renderer that backend started
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("backend:status", { running: true });
  }
}

/**
 * Gracefully terminate the Python backend process.
 */
function killBackend(): void {
  if (!backendProcess) return;

  console.log("[Main] Shutting down backend process...");

  // Try graceful shutdown on Windows
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"]);
  } else {
    backendProcess.kill("SIGTERM");
    // Force kill after 5 seconds
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        backendProcess.kill("SIGKILL");
      }
    }, 5000);
  }
  backendProcess = null;
}

// ---------------------------------------------------------------------------
// Window Management
// ---------------------------------------------------------------------------

/**
 * Create the main application window.
 * Configures frame, size, min constraints, and loads the renderer.
 */
function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    title: "AgentForge",
    icon: path.join(__dirname, "..", "assets", "icon.png"),
    frame: true,
    show: false, // Show after ready-to-show for smooth UX
    webPreferences: {
      preload: PRELOAD_PATH,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#1a1a2e" : "#f8fafc",
  });

  // Load renderer
  if (IS_DEV) {
    // In development, load from Vite dev server
    win.loadURL("http://localhost:5173");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    // In production, load built files
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  // Show window when ready (prevents white flash)
  win.once("ready-to-show", () => {
    win.show();
    win.focus();
  });

  // Intercept new window requests and open in external browser
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  // Handle close
  win.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      win.hide(); // Minimize to tray instead of closing
    }
  });

  win.on("closed", () => {
    mainWindow = null;
  });

  return win;
}

// ---------------------------------------------------------------------------
// System Tray
// ---------------------------------------------------------------------------

/**
 * Create and configure the system tray icon and menu.
 */
function createTray(): void {
  const trayIconPath = path.join(__dirname, "..", "assets", "tray-icon.png");

  tray = new Tray(trayIconPath);
  tray.setToolTip("AgentForge");

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Show AgentForge",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          mainWindow = createMainWindow();
        }
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  // Double-click tray icon to show window
  tray.on("double-click", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ---------------------------------------------------------------------------
// IPC Handlers — Bridge renderer ↔ backend
// ---------------------------------------------------------------------------

/**
 * Register all IPC handlers for renderer-backend communication.
 */
function registerIpcHandlers(): void {
  // --- Backend Status ---

  /** Get current backend running status */
  ipcMain.handle("backend:getStatus", (): { running: boolean; port: number } => {
    return {
      running: backendProcess !== null && !backendProcess.killed,
      port: BACKEND_PORT,
    };
  });

  /** Get the base URL for the Python backend */
  ipcMain.handle("backend:getUrl", (): string => {
    return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
  });

  /** Restart the backend process */
  ipcMain.handle("backend:restart", async (): Promise<void> => {
    killBackend();
    // Wait a moment for cleanup before restart
    await new Promise((resolve) => setTimeout(resolve, 1000));
    spawnBackend();
  });

  // --- System ---

  /** Get system information */
  ipcMain.handle("system:getInfo", (): Record<string, unknown> => {
    return {
      platform: process.platform,
      arch: process.arch,
      version: app.getVersion(),
      electronVersion: process.versions.electron,
      nodeVersion: process.versions.node,
      chromeVersion: process.versions.chrome,
      isDev: IS_DEV,
    };
  });

  /** Get the current theme (light/dark) */
  ipcMain.handle("system:getTheme", (): "light" | "dark" => {
    return nativeTheme.shouldUseDarkColors ? "dark" : "light";
  });

  // --- File Dialogs ---

  /** Open a directory selection dialog */
  ipcMain.handle(
    "dialog:openDirectory",
    async (_event, defaultPath?: string): Promise<string | null> => {
      const result = await dialog.showOpenDialog(mainWindow!, {
        properties: ["openDirectory"],
        defaultPath: defaultPath || app.getPath("home"),
      });
      return result.canceled ? null : result.filePaths[0];
    }
  );

  /** Open a file selection dialog */
  ipcMain.handle(
    "dialog:openFile",
    async (
      _event,
      options?: { filters?: Electron.FileFilter[]; defaultPath?: string }
    ): Promise<string | null> => {
      const result = await dialog.showOpenDialog(mainWindow!, {
        properties: ["openFile"],
        filters: options?.filters,
        defaultPath: options?.defaultPath || app.getPath("home"),
      });
      return result.canceled ? null : result.filePaths[0];
    }
  );

  // --- Auto Updater ---

  /** Check for available updates */
  ipcMain.handle("updater:check", async (): Promise<{
    updateAvailable: boolean;
    version?: string;
  }> => {
    try {
      const result = await autoUpdater.checkForUpdates();
      return {
        updateAvailable: !!result?.updateInfo,
        version: result?.updateInfo?.version,
      };
    } catch {
      return { updateAvailable: false };
    }
  });

  /** Install downloaded update and restart */
  ipcMain.handle("updater:install", (): void => {
    autoUpdater.quitAndInstall();
  });
}

// ---------------------------------------------------------------------------
// Auto Updater
// ---------------------------------------------------------------------------

/**
 * Configure the auto-updater for release channel.
 */
function configureAutoUpdater(): void {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on("update-available", (info) => {
    if (mainWindow) {
      mainWindow.webContents.send("updater:updateAvailable", info);
    }
  });

  autoUpdater.on("update-downloaded", (info) => {
    if (mainWindow) {
      mainWindow.webContents.send("updater:updateDownloaded", info);
    }
  });

  autoUpdater.on("error", (error) => {
    console.error("[Main] Auto-updater error:", error);
  });
}

// ---------------------------------------------------------------------------
// App Lifecycle
// ---------------------------------------------------------------------------

/**
 * Application ready handler.
 * Creates window, spawns backend, sets up tray and IPC.
 */
app.whenReady().then(() => {
  // Configure auto-updater in production
  if (!IS_DEV) {
    configureAutoUpdater();
  }

  // Register IPC handlers before creating window
  registerIpcHandlers();

  // Create main window
  mainWindow = createMainWindow();

  // Create system tray
  createTray();

  // Spawn Python backend
  spawnBackend();

  // macOS: re-create window when dock icon is clicked
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

/**
 * Prevent multiple instances.
 */
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

/**
 * Cleanup on quit: kill backend, destroy tray.
 */
app.on("before-quit", () => {
  isQuitting = true;
  killBackend();
  if (tray) {
    tray.destroy();
    tray = null;
  }
});

app.on("window-all-closed", () => {
  // On macOS apps typically stay active until Cmd+Q
  if (process.platform !== "darwin") {
    app.quit();
  }
});
