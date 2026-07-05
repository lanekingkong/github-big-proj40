/**
 * React Application Entry Point
 * =============================
 * Mounts the root App component into the DOM.
 *
 * This is the JavaScript entry point loaded by Vite/Electron.
 * StrictMode is enabled for development-time checks.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./index.css";

/**
 * DOM mount point.
 * The #root element is defined in index.html (Vite entry).
 */
const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error(
    'AgentForge: Could not find #root element. Ensure index.html contains <div id="root"></div>.'
  );
}

const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
