/**
 * Electron Preload Script
 * =======================
 * Securely exposes a limited API to the renderer process via contextBridge.
 *
 * All communication between renderer and main process goes through this
 * script, enforcing context isolation and preventing direct Node.js access.
 *
 * Exposed APIs: backend status/restart, file dialogs, system info, theme,
 * auto-updater, and shell operations.
 */

import { contextBridge, ipcRenderer, IpcRendererEvent } from "electron";

// ---------------------------------------------------------------------------
// Type Definitions for the Exposed API
// ---------------------------------------------------------------------------

interface BackendStatus {
  running: boolean;
  port: number;
}

interface BackendLogEvent {
  level: "info" | "error" | "warn" | "debug";
  message: string;
  source: string;
}

interface SystemInfo {
  platform: string;
  arch: string;
  version: string;
  electronVersion: string;
  nodeVersion: string;
  chromeVersion: string;
  isDev: boolean;
}

interface UpdateInfo {
  version: string;
  releaseDate?: string;
  releaseNotes?: string;
}

interface FileFilter {
  name: string;
  extensions: string[];
}

type ThemeMode = "light" | "dark";

type EventCallback = (...args: unknown[]) => void;

// ---------------------------------------------------------------------------
// Exposed API
// ---------------------------------------------------------------------------

const electronAPI = {
  // =========================================================================
  // Backend Process Management
  // =========================================================================

  /**
   * Get the current status of the Python backend process.
   * @returns Object with `running` flag and `port` number.
   */
  getBackendStatus: (): Promise<BackendStatus> =>
    ipcRenderer.invoke("backend:getStatus"),

  /**
   * Get the base URL for the Python FastAPI backend.
   * @returns URL string like `http://127.0.0.1:18090`.
   */
  getBackendUrl: (): Promise<string> => ipcRenderer.invoke("backend:getUrl"),

  /**
   * Restart the Python backend process.
   */
  restartBackend: (): Promise<void> => ipcRenderer.invoke("backend:restart"),

  /**
   * Register a listener for backend log events (stdout/stderr).
   * @param callback Function receiving `{ level, message, source }`.
   * @returns Cleanup function to remove the listener.
   */
  onBackendLog: (callback: (event: BackendLogEvent) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, data: BackendLogEvent) =>
      callback(data);
    ipcRenderer.on("backend:log", handler);
    return () => ipcRenderer.removeListener("backend:log", handler);
  },

  /**
   * Register a listener for backend status change events.
   * @param callback Function receiving the new status object.
   * @returns Cleanup function to remove the listener.
   */
  onBackendStatus: (
    callback: (status: { running: boolean; exitCode?: number }) => void
  ): (() => void) => {
    const handler = (
      _event: IpcRendererEvent,
      data: { running: boolean; exitCode?: number }
    ) => callback(data);
    ipcRenderer.on("backend:status", handler);
    return () => ipcRenderer.removeListener("backend:status", handler);
  },

  // =========================================================================
  // System Information
  // =========================================================================

  /**
   * Get system-level information (OS, architecture, versions).
   * @returns System information object.
   */
  getSystemInfo: (): Promise<SystemInfo> => ipcRenderer.invoke("system:getInfo"),

  /**
   * Get the current system theme preference.
   * @returns `"light"` or `"dark"`.
   */
  getTheme: (): Promise<ThemeMode> => ipcRenderer.invoke("system:getTheme"),

  /**
   * Listen for native theme changes (light ↔ dark).
   * @param callback Receives the new theme mode.
   * @returns Cleanup function.
   */
  onThemeChange: (
    callback: (theme: ThemeMode) => void
  ): (() => void) => {
    // We piggyback on nativeTheme.updated via polling or a custom IPC
    const handler = (_event: IpcRendererEvent, theme: ThemeMode) =>
      callback(theme);
    ipcRenderer.on("system:themeChanged", handler);
    return () => ipcRenderer.removeListener("system:themeChanged", handler);
  },

  // =========================================================================
  // File Dialogs (Native)
  // =========================================================================

  /**
   * Open a native directory selection dialog.
   * @param defaultPath Optional starting directory path.
   * @returns Selected directory path or null if cancelled.
   */
  openDirectoryDialog: (defaultPath?: string): Promise<string | null> =>
    ipcRenderer.invoke("dialog:openDirectory", defaultPath),

  /**
   * Open a native file selection dialog.
   * @param options Optional filters and default path.
   * @returns Selected file path or null if cancelled.
   */
  openFileDialog: (options?: {
    filters?: FileFilter[];
    defaultPath?: string;
  }): Promise<string | null> =>
    ipcRenderer.invoke("dialog:openFile", options),

  // =========================================================================
  // Shell Operations
  // =========================================================================

  /**
   * Open an external URL in the system default browser.
   * @param url The URL to open.
   */
  openExternal: (url: string): Promise<void> =>
    ipcRenderer.invoke("shell:openExternal", url),

  /**
   * Reveal a file in the system file manager (Explorer / Finder).
   * @param filePath Absolute path to the file.
   */
  showItemInFolder: (filePath: string): Promise<void> =>
    ipcRenderer.invoke("shell:showItemInFolder", filePath),

  // =========================================================================
  // Auto-Updater
  // =========================================================================

  /**
   * Check for available application updates.
   * @returns Update availability info with optional version.
   */
  checkForUpdates: (): Promise<{
    updateAvailable: boolean;
    version?: string;
  }> => ipcRenderer.invoke("updater:check"),

  /**
   * Install downloaded update and restart the application.
   */
  installUpdate: (): Promise<void> => ipcRenderer.invoke("updater:install"),

  /**
   * Listen for update-available events.
   * @param callback Receives update info.
   * @returns Cleanup function.
   */
  onUpdateAvailable: (callback: (info: UpdateInfo) => void): (() => void) => {
    const handler = (_event: IpcRendererEvent, info: UpdateInfo) =>
      callback(info);
    ipcRenderer.on("updater:updateAvailable", handler);
    return () => ipcRenderer.removeListener("updater:updateAvailable", handler);
  },

  /**
   * Listen for update-downloaded events.
   * @param callback Receives update info.
   * @returns Cleanup function.
   */
  onUpdateDownloaded: (
    callback: (info: UpdateInfo) => void
  ): (() => void) => {
    const handler = (_event: IpcRendererEvent, info: UpdateInfo) =>
      callback(info);
    ipcRenderer.on("updater:updateDownloaded", handler);
    return () =>
      ipcRenderer.removeListener("updater:updateDownloaded", handler);
  },
};

// ---------------------------------------------------------------------------
// Expose to Renderer
// ---------------------------------------------------------------------------

contextBridge.exposeInMainWorld("electronAPI", electronAPI);

// Type augmentation for the renderer process
declare global {
  interface Window {
    electronAPI: typeof electronAPI;
  }
}
