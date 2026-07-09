# Запуск с нуля

Требования: Windows, Node.js 18+, Python 3.11, Rust (для Tauri), Visual Studio Build Tools (C++), Git.

## 1. Клонировать и настроить `.env`

```powershell
git clone https://github.com/anymasoft/1c-optimyzer.git
cd 1c-optimyzer
copy .env.example .env
```

Открой `.env` и заполни как минимум `ANTHROPIC_API_KEY` (иначе AI-функции будут показывать «AI not configured» — остальное приложение при этом работает офлайн).

## 2. Backend (Python sidecar)

```powershell
pwsh scripts/setup-backend.ps1
```

Создаёт `backend/.venv` и ставит зависимости. Отдельно запускать не нужно — sidecar стартует автоматически вместе с desktop-приложением (шаг 5).

## 3. Cloud server (нужен для AI-функций)

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
alembic upgrade head
cd ..
```

`alembic upgrade head` создаёт локальную SQLite-базу сервера (аккаунты, лицензии, AI-кэш).

## 4. Frontend (Tauri + React)

```powershell
cd frontend
npm install
cd src-tauri
cargo build
cd ..\..
```

## 5. Запустить всё вместе

```powershell
.\start.bat
```

Этот скрипт: поднимает cloud-сервер на `:8001` (если ещё не запущен), подчищает зависшие backend-процессы с прошлых сессий, запускает desktop-приложение (`npm run tauri dev`). Когда закрываешь окно приложения — сервер останавливается сам, ничего не остаётся висеть в фоне.

## Только фронт, без Tauri-обвязки

```powershell
cd frontend
npm run dev
```

## Проверить, что всё собирается

```powershell
cd frontend && npm run build && npm test
cd ../backend && .\.venv\Scripts\Activate.ps1 && pytest
cd ../server && .\.venv\Scripts\Activate.ps1 && pytest
```
