// Tauri shell: запускает Python sidecar (optimyzer-backend) и проксирует JSON-RPC.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod sidecar;

use serde_json::Value;
use sidecar::SidecarHandle;
use std::sync::Mutex;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager, State};

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

#[derive(serde::Serialize)]
struct BslLsPaths {
    java_executable: String,
    bsl_ls_jar: String,
    available: bool,
}

/// Возвращает пути к bundled JRE 21 и bsl-language-server JAR.
///
/// Используется Python sidecar для запуска bsl-LS subprocess (WebSocket sidecar).
/// Sprint 6 Phase A. Подробнее: docs/sales_sprint/SPRINT_6_PROMT.md.
///
/// `available=false` означает что файлы не нашлись в resource_dir — это нормально
/// для dev-mode (npm run tauri dev) когда bundle.resources не копируются. В таком
/// случае Python fallback на системный java + research/jar (для разработки).
#[tauri::command]
fn get_bsl_ls_paths(app: AppHandle) -> Result<BslLsPaths, String> {
    let java_rel = "binaries/jre-21/bin/java.exe";
    let jar_rel = "binaries/bsl-ls/bsl-language-server-0.29.0-exec.jar";

    let java_path = app
        .path()
        .resolve(java_rel, BaseDirectory::Resource)
        .map_err(|e| format!("resolve java: {e}"))?;
    let jar_path = app
        .path()
        .resolve(jar_rel, BaseDirectory::Resource)
        .map_err(|e| format!("resolve jar: {e}"))?;

    let available = java_path.is_file() && jar_path.is_file();

    Ok(BslLsPaths {
        java_executable: java_path.to_string_lossy().into_owned(),
        bsl_ls_jar: jar_path.to_string_lossy().into_owned(),
        available,
    })
}

#[derive(serde::Serialize)]
struct PlanviewPath {
    executable: String,
    available: bool,
}

/// Возвращает путь к bundled PerformanceStudio CLI (PlanViewer.Cli.exe).
///
/// Используется Python sidecar для subprocess wrapper'а в `planview/cli.py`.
/// Sprint 7 Phase A. Подробнее: docs/sales_sprint/SPRINT_7_PROMT.md.
///
/// `available=false` — бинарь не в resource_dir. Это нормально для dev-mode
/// (`npm run tauri dev` не копирует bundle.resources). Sidecar fallback:
/// repo-relative `frontend/src-tauri/binaries/planview/PlanViewer.Cli.exe`.
#[tauri::command]
fn get_planview_path(app: AppHandle) -> Result<PlanviewPath, String> {
    let exe_rel = "binaries/planview/PlanViewer.Cli.exe";
    let exe_path = app
        .path()
        .resolve(exe_rel, BaseDirectory::Resource)
        .map_err(|e| format!("resolve planview exe: {e}"))?;

    let available = exe_path.is_file();

    Ok(PlanviewPath {
        executable: exe_path.to_string_lossy().into_owned(),
        available,
    })
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
        .invoke_handler(tauri::generate_handler![
            rpc_call,
            sidecar_status,
            classify_path,
            get_bsl_ls_paths,
            get_planview_path
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
