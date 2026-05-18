// Tauri shell: запускает Python sidecar (optimyzer-backend) и проксирует JSON-RPC.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod sidecar;

use serde_json::Value;
use sidecar::SidecarHandle;
use std::sync::Mutex;
use tauri::{Manager, State};

struct AppState {
    sidecar: Mutex<Option<SidecarHandle>>,
}

#[tauri::command]
async fn rpc_call(
    state: State<'_, AppState>,
    method: String,
    params: Value,
) -> Result<Value, String> {
    let handle_opt = {
        let guard = state.sidecar.lock().map_err(|e| e.to_string())?;
        guard.clone()
    };
    let handle = handle_opt.ok_or_else(|| "sidecar not started".to_string())?;
    handle.request(method, params).await.map_err(|e| e.to_string())
}

#[tauri::command]
fn sidecar_status(state: State<'_, AppState>) -> Result<bool, String> {
    let guard = state.sidecar.lock().map_err(|e| e.to_string())?;
    Ok(guard.is_some())
}

#[tauri::command]
fn classify_path(path: String) -> Result<serde_json::Value, String> {
    let p = std::path::Path::new(&path);
    let kind = if !p.exists() {
        "missing"
    } else if p.is_dir() {
        "folder"
    } else {
        "file"
    };
    Ok(serde_json::json!({ "kind": kind }))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            sidecar: Mutex::new(None),
        })
        .setup(|app| {
            let handle = app.handle().clone();
            // Старт sidecar.
            let sidecar = sidecar::spawn(&handle).expect("failed to spawn sidecar");
            let state: State<'_, AppState> = handle.state();
            *state.sidecar.lock().unwrap() = Some(sidecar);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![rpc_call, sidecar_status, classify_path])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
