// Запуск Python sidecar + JSON-RPC over stdio (Sprint 1 — ADR-012).
//
// Prod: bundled PyInstaller onedir exe (binaries/backend/optimyzer_backend.exe
// в resource_dir) — конечному пользователю не нужен Python. Dev fallback:
// `python -m optimyzer_backend` из ../../backend (venv, затем системный python).
//
// Sprint 1: помимо responses (с id) парсим notifications (без id) и эмитим их
// через Tauri events `rpc-notification:<method>` для frontend подписки.
//
// Устойчивость (fix «Ошибка RPC: os error 232»): раньше stderr sidecar'а
// пробрасывался в /dev/null оконного приложения, а падение процесса ничем не
// обрабатывалось — любой следующий RPC утыкался в закрытый pipe (Windows
// ERROR_NO_DATA = 232). Теперь:
//   * stderr пишется в файл-лог (%APPDATA%/1c-optimyzer/logs/backend.log);
//   * при завершении процесса ожидающие запросы получают понятную ошибку
//     (не зависают), а sidecar автоматически перезапускается;
//   * request() при обрыве «до записи» прозрачно повторяет запрос на свежем
//     процессе — пользователь не видит ошибку вовсе.

use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use std::collections::{HashMap, VecDeque};
use std::fs::OpenOptions;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicI64, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::oneshot;

type Pending = HashMap<i64, oneshot::Sender<Result<Value, String>>>;

/// Сколько последних строк stderr держим в памяти — чтобы приложить «хвост»
/// журнала к сообщению об аварийном перезапуске (для диагностики).
const STDERR_TAIL_LINES: usize = 40;

/// Защита от «шторма перезапусков» (например, sidecar падает сразу на старте):
/// не более RESPAWN_MAX_IN_WINDOW перезапусков за RESPAWN_WINDOW.
const RESPAWN_WINDOW: Duration = Duration::from_secs(30);
const RESPAWN_MAX_IN_WINDOW: usize = 5;

#[derive(Clone)]
pub struct SidecarHandle {
    inner: Arc<Inner>,
}

/// Живой процесс sidecar'а: его stdin + сам Child. Меняется целиком при
/// перезапуске (под `proc` mutex).
struct Proc {
    stdin: ChildStdin,
    child: Child,
}

struct Inner {
    next_id: AtomicI64,
    /// Поколение процесса. Инкрементится при каждом (пере)запуске. reader_loop
    /// знает своё поколение и не инициирует повторный respawn, если процесс уже
    /// сменился.
    generation: AtomicU64,
    pending: Mutex<Pending>,
    proc: Mutex<Proc>,
    /// Последние строки stderr — для человекочитаемого сообщения о падении.
    stderr_tail: Mutex<VecDeque<String>>,
    /// Моменты последних перезапусков — для ограничения частоты (anti-storm).
    respawn_history: Mutex<VecDeque<Instant>>,
    app: AppHandle,
    log_path: PathBuf,
}

impl SidecarHandle {
    pub async fn request(&self, method: String, params: Value) -> Result<Value, String> {
        // До двух попыток: если процесс уже был мёртв на момент записи —
        // перезапускаем и повторяем на свежем процессе (запрос ещё не был
        // доставлен, дублирования нет). Если запись прошла, но процесс умер во
        // время обработки — reader_loop разбудит ожидание понятной ошибкой.
        let mut last_err = String::new();
        for attempt in 0..2u8 {
            let id = self.inner.next_id.fetch_add(1, Ordering::SeqCst);
            let payload = json!({
                "jsonrpc": "2.0",
                "id": id,
                "method": method.clone(),
                "params": params.clone(),
            });
            let line = serde_json::to_string(&payload).map_err(|e| e.to_string())?;

            let (tx, rx) = oneshot::channel();
            {
                let mut pend = self.inner.pending.lock().map_err(|e| e.to_string())?;
                pend.insert(id, tx);
            }

            let gen_before = self.inner.generation.load(Ordering::SeqCst);
            match self.inner.write_line(&line) {
                Ok(()) => {
                    // Запрос доставлен. Ждём ответ (или разбудку от reader_loop
                    // при падении процесса во время обработки).
                    return rx.await.map_err(|e| e.to_string())?;
                }
                Err(_write_err) => {
                    // Запись не удалась — процесс, скорее всего, уже завершился.
                    // Наш pending-запрос никуда не ушёл, снимаем его.
                    if let Ok(mut pend) = self.inner.pending.lock() {
                        pend.remove(&id);
                    }
                    last_err = self.inner.crash_message();
                    if attempt == 0 {
                        // Поднимаем свежий процесс и повторяем запись.
                        let _ = self.inner.respawn(gen_before);
                        continue;
                    }
                }
            }
        }
        Err(last_err)
    }
}

impl Inner {
    /// Пишет строку в stdin текущего процесса. Ошибка = pipe закрыт (процесс мёртв).
    fn write_line(&self, line: &str) -> Result<(), String> {
        let mut proc = self.proc.lock().map_err(|e| e.to_string())?;
        writeln!(proc.stdin, "{}", line).map_err(|e| e.to_string())?;
        proc.stdin.flush().map_err(|e| e.to_string())?;
        Ok(())
    }

    /// Человекочитаемое сообщение об аварийном завершении с указанием лога и
    /// (если есть) последней строкой stderr.
    fn crash_message(&self) -> String {
        let last = self
            .stderr_tail
            .lock()
            .ok()
            .and_then(|t| t.iter().rev().find(|l| !l.trim().is_empty()).cloned());
        let log = self.log_path.display();
        match last {
            Some(detail) => format!(
                "Локальный модуль анализа завершился аварийно и был перезапущен. \
                 Повторите операцию. Последнее сообщение: {detail}. Журнал: {log}"
            ),
            None => format!(
                "Локальный модуль анализа завершился аварийно и был перезапущен. \
                 Повторите операцию. Журнал: {log}"
            ),
        }
    }

    /// Разбудить все ожидающие запросы понятной ошибкой (чтобы UI не завис).
    fn drain_pending(&self, message: &str) {
        if let Ok(mut pend) = self.pending.lock() {
            for (_id, tx) in pend.drain() {
                let _ = tx.send(Err(message.to_string()));
            }
        }
    }

    /// Перезапуск процесса. Идемпотентен по поколению: если процесс уже сменился
    /// (кто-то другой уже перезапустил) — ничего не делаем.
    fn respawn(self: &Arc<Self>, expected_gen: u64) -> Result<(), String> {
        let mut proc = self.proc.lock().map_err(|e| e.to_string())?;
        if self.generation.load(Ordering::SeqCst) != expected_gen {
            return Ok(()); // уже перезапущен
        }

        // Anti-storm: если sidecar падает слишком часто (например, крешит на
        // старте) — прекращаем автоперезапуск, чтобы не крутить CPU. Через
        // RESPAWN_WINDOW окно очистится и попытки возобновятся.
        if let Ok(mut hist) = self.respawn_history.lock() {
            let now = Instant::now();
            while hist.front().is_some_and(|t| now.duration_since(*t) > RESPAWN_WINDOW) {
                hist.pop_front();
            }
            if hist.len() >= RESPAWN_MAX_IN_WINDOW {
                append_log(
                    &self.log_path,
                    "[supervisor] слишком частые перезапуски — автоперезапуск приостановлен",
                );
                return Ok(());
            }
            hist.push_back(now);
        }

        let _ = proc.child.kill();
        let _ = proc.child.wait();

        let mut child = build_command(&self.app)
            .map_err(|e| e.to_string())?
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("respawn sidecar: {e}"))?;

        let stdin = child.stdin.take().ok_or("sidecar stdin is None")?;
        let stdout = child.stdout.take().ok_or("sidecar stdout is None")?;
        let stderr = child.stderr.take().ok_or("sidecar stderr is None")?;

        proc.stdin = stdin;
        proc.child = child;
        let new_gen = expected_gen.wrapping_add(1);
        self.generation.store(new_gen, Ordering::SeqCst);
        drop(proc); // отпускаем lock перед запуском потоков

        append_log(&self.log_path, "[supervisor] sidecar перезапущен после аварийного завершения");
        start_reader(stdout, Arc::clone(self), new_gen);
        start_stderr_logger(stderr, Arc::clone(self));
        // Сообщаем фронтенду — чтобы он переоткрыл загруженный архив (in-memory
        // state нового процесса пуст; .duckdb и SQLite-история на диске живы).
        let _ = self.app.emit("sidecar-restarted", ());
        Ok(())
    }
}

/// Bundled onedir exe (относительно resource_dir): `binaries/backend/optimyzer_backend.exe`.
/// Собирается `scripts/build-backend-binary.ps1` (PyInstaller) и копируется в
/// `frontend/src-tauri/binaries/backend/`, откуда tauri.conf.json bundle.resources
/// упаковывает его в установщик. В dev-режиме (`npm run tauri dev`) resource_dir
/// не заполнен — используется fallback на venv/системный python.
fn bundled_backend_exe(app: &AppHandle) -> Option<PathBuf> {
    let rel = "binaries/backend/optimyzer_backend.exe";
    let path = app.path().resolve(rel, BaseDirectory::Resource).ok()?;
    path.is_file().then_some(path)
}

/// Строит команду запуска sidecar'а (prod bundled exe либо dev python).
/// Единый источник для первичного spawn и respawn.
fn build_command(app: &AppHandle) -> Result<Command> {
    let mut cmd = if let Some(exe) = bundled_backend_exe(app) {
        // Prod: bundled exe, никакого Python на машине пользователя не нужно.
        let work_dir = exe.parent().map(|p| p.to_path_buf());
        let mut c = Command::new(&exe);
        if let Some(dir) = work_dir {
            c.current_dir(dir);
        }
        c
    } else {
        // Dev fallback: venv python (../../backend/.venv) либо системный python.
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
        let mut c = Command::new(&python);
        c.args(["-m", "optimyzer_backend"]).current_dir(&backend_dir);
        c
    };
    cmd.env("PYTHONIOENCODING", "utf-8");
    Ok(cmd)
}

/// Путь к файлу-логу sidecar'а: `%APPDATA%/1c-optimyzer/logs/backend.log`
/// (рядом с duckdb-хранилищем бэкенда). Каталог создаётся при необходимости.
pub fn log_path() -> PathBuf {
    let base = std::env::var("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| std::env::temp_dir());
    let dir = base.join("1c-optimyzer").join("logs");
    let _ = std::fs::create_dir_all(&dir);
    dir.join("backend.log")
}

fn append_log(path: &PathBuf, line: &str) {
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(f, "{line}");
    }
}

pub fn spawn(app: &AppHandle) -> Result<SidecarHandle> {
    let log = log_path();
    append_log(&log, "[supervisor] запуск sidecar");

    let mut child = build_command(app)?
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| anyhow!("Не удалось запустить sidecar: {e}"))?;

    let stdin = child
        .stdin
        .take()
        .ok_or_else(|| anyhow!("sidecar stdin is None"))?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| anyhow!("sidecar stdout is None"))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| anyhow!("sidecar stderr is None"))?;

    let inner = Arc::new(Inner {
        next_id: AtomicI64::new(1),
        generation: AtomicU64::new(1),
        pending: Mutex::new(HashMap::new()),
        proc: Mutex::new(Proc { stdin, child }),
        stderr_tail: Mutex::new(VecDeque::with_capacity(STDERR_TAIL_LINES)),
        respawn_history: Mutex::new(VecDeque::new()),
        app: app.clone(),
        log_path: log,
    });

    start_reader(stdout, inner.clone(), 1);
    start_stderr_logger(stderr, inner.clone());

    Ok(SidecarHandle { inner })
}

/// Поток чтения stdout: диспетчеризует ответы/уведомления. При закрытии stdout
/// (процесс завершился) — будит ожидающие запросы и перезапускает sidecar.
fn start_reader(stdout: ChildStdout, inner: Arc<Inner>, my_gen: u64) {
    std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            let Ok(line) = line else { break };
            let Ok(msg): Result<Value, _> = serde_json::from_str(&line) else {
                append_log(&inner.log_path, &format!("[sidecar] non-JSON stdout: {line}"));
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
                if let Err(e) = inner.app.emit(&event_name, params) {
                    append_log(&inner.log_path, &format!("[sidecar] emit {event_name} failed: {e}"));
                }
            }
        }

        // stdout закрыт — процесс этого поколения завершился.
        if inner.generation.load(Ordering::SeqCst) != my_gen {
            return; // уже сменилось поколение, ничего не делаем
        }
        append_log(&inner.log_path, "[supervisor] stdout sidecar закрыт (процесс завершился)");
        let message = inner.crash_message();
        inner.drain_pending(&message);
        // Поднимаем свежий процесс, чтобы следующие действия пользователя работали.
        let _ = inner.respawn(my_gen);
    });
}

/// Поток чтения stderr: пишет строки в файл-лог и хранит «хвост» в памяти.
fn start_stderr_logger(stderr: ChildStderr, inner: Arc<Inner>) {
    std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            let Ok(line) = line else { break };
            append_log(&inner.log_path, &format!("[stderr] {line}"));
            if let Ok(mut tail) = inner.stderr_tail.lock() {
                if tail.len() >= STDERR_TAIL_LINES {
                    tail.pop_front();
                }
                tail.push_back(line);
            }
        }
    });
}
