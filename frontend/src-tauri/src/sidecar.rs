// Запуск Python sidecar + JSON-RPC over stdio (Sprint 1 — ADR-012).
//
// Sprint 0 — простой dev-mode: `python -m optimyzer_backend` из ../../backend.
// Sprint 3 — заменим на bundled PyInstaller exe в bundle/binaries.
//
// Sprint 1: помимо responses (с id) парсим notifications (без id) и эмитим их
// через Tauri events `rpc-notification:<method>` для frontend подписки.

use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Emitter};
use tokio::sync::oneshot;

type Pending = HashMap<i64, oneshot::Sender<Result<Value, String>>>;

#[derive(Clone)]
pub struct SidecarHandle {
    inner: Arc<Inner>,
}

struct Inner {
    next_id: AtomicI64,
    pending: Mutex<Pending>,
    stdin: Mutex<ChildStdin>,
    _child: Mutex<Child>,
}

impl SidecarHandle {
    pub async fn request(&self, method: String, params: Value) -> Result<Value, String> {
        let id = self.inner.next_id.fetch_add(1, Ordering::SeqCst);
        let payload = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        });
        let line = serde_json::to_string(&payload).map_err(|e| e.to_string())?;
        let (tx, rx) = oneshot::channel();
        {
            let mut pend = self.inner.pending.lock().map_err(|e| e.to_string())?;
            pend.insert(id, tx);
        }
        {
            let mut stdin = self.inner.stdin.lock().map_err(|e| e.to_string())?;
            writeln!(stdin, "{}", line).map_err(|e| e.to_string())?;
            stdin.flush().map_err(|e| e.to_string())?;
        }
        rx.await.map_err(|e| e.to_string())?
    }
}

pub fn spawn(app: &AppHandle) -> Result<SidecarHandle> {
    let backend_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("backend");
    let venv_python = if cfg!(windows) {
        backend_dir.join(".venv").join("Scripts").join("python.exe")
    } else {
        backend_dir.join(".venv").join("bin").join("python")
    };
    let python: std::ffi::OsString = if venv_python.is_file() {
        venv_python.into()
    } else if cfg!(windows) {
        "python".into()
    } else {
        "python3".into()
    };

    let mut child = Command::new(&python)
        .args(["-m", "optimyzer_backend"])
        .current_dir(&backend_dir)
        .env("PYTHONIOENCODING", "utf-8")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| anyhow!("Не удалось запустить sidecar ({}): {e}", python.to_string_lossy()))?;

    let stdin = child
        .stdin
        .take()
        .ok_or_else(|| anyhow!("sidecar stdin is None"))?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| anyhow!("sidecar stdout is None"))?;

    let inner = Arc::new(Inner {
        next_id: AtomicI64::new(1),
        pending: Mutex::new(HashMap::new()),
        stdin: Mutex::new(stdin),
        _child: Mutex::new(child),
    });

    let reader_inner = inner.clone();
    let app_clone = app.clone();
    std::thread::spawn(move || reader_loop(stdout, reader_inner, app_clone));

    Ok(SidecarHandle { inner })
}

fn reader_loop(stdout: ChildStdout, inner: Arc<Inner>, app: AppHandle) {
    let reader = BufReader::new(stdout);
    for line in reader.lines() {
        let Ok(line) = line else { break };
        let Ok(msg): Result<Value, _> = serde_json::from_str(&line) else {
            eprintln!("[sidecar] non-JSON line: {}", line);
            continue;
        };

        let id_opt = msg.get("id").and_then(|v| v.as_i64());
        if let Some(id) = id_opt {
            // Это response — диспатчим в pending oneshot.
            let sender = {
                let mut pend = match inner.pending.lock() {
                    Ok(g) => g,
                    Err(_) => continue,
                };
                pend.remove(&id)
            };
            if let Some(tx) = sender {
                if let Some(err) = msg.get("error") {
                    let _ = tx.send(Err(err.to_string()));
                } else if let Some(res) = msg.get("result") {
                    let _ = tx.send(Ok(res.clone()));
                } else {
                    let _ = tx.send(Err("malformed RPC response".into()));
                }
            }
            continue;
        }

        // Notification (без id) — пробуем эмитить как Tauri event.
        if let Some(method) = msg.get("method").and_then(|m| m.as_str()) {
            let params = msg.get("params").cloned().unwrap_or(Value::Null);
            let event_name = format!("rpc-notification:{}", method);
            if let Err(e) = app.emit(&event_name, params) {
                eprintln!("[sidecar] failed to emit {}: {}", event_name, e);
            }
        }
    }
}
