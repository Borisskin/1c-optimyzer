import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { installExternalLinkHijack } from "./utils/openExternal";
import "./styles/optimyzer-design.css";

// Ловит все `<a target="_blank">` и открывает через Tauri shell
// (иначе webview игнорирует new-window). См. openExternal.ts.
installExternalLinkHijack();

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
