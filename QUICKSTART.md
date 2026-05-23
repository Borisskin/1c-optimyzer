# Quickstart — установка и запуск

5 компонентов Optimyzer:

| Папка       | Что это                                                    | Когда запускать                   |
| ----------- | ---------------------------------------------------------- | --------------------------------- |
| `backend/`  | Python sidecar для desktop (DuckDB, парсер ТЖ, AI calls)   | Автоматически из `start.bat`      |
| `frontend/` | Tauri desktop app (анализ архивов, UI)                     | `start.bat` (dev)                 |
| `server/`   | Облачный FastAPI (auth, billing, license, telemetry)       | `uvicorn` для cabinet / activation |
| `cabinet/`  | React webapp для `account.optimyzer.pro`                   | `npm run dev` (или build для prod)|
| `landing/`  | Статический лендинг для `optimyzer.pro` + docs             | Любой static server (или nginx)   |

---

## 0. Prerequisites

```bash
python --version      # 3.11+
node --version        # 22+
rustc --version       # 1.77+ (только для frontend Tauri build)
git --version
```

Windows — Rust ставится через [rustup-init.exe](https://rustup.rs).

---

## 1. Clone + конфиг

```bash
git clone https://github.com/anymasoft/1c-optimyzer.git D:\1C-Optimyzer
cd D:\1C-Optimyzer

# Один .env на все компоненты (см. .env.example).
copy .env.example .env
```

Открыть `.env` и заполнить нужное. Минимум для локальной работы desktop:

```
ANTHROPIC_API_KEY=sk-ant-...   # для AI Explainer (опц. — без него AI кнопка показывает "not configured")
```

Для полного flow (Yandex OAuth + cabinet + activation) — заполнить `YANDEX_*` и `YOOKASSA_*`. Без них cloud-фичи работают в stub-режиме.

---

## 2. Desktop приложение (`backend/` + `frontend/`)

### Первичная установка

```powershell
# backend Python deps
pwsh scripts/setup-backend.ps1

# frontend Node deps + Rust
cd frontend
npm install
cd src-tauri
cargo build
cd ..\..
```

### Запуск (dev mode)

```powershell
.\start.bat
```

Этот скрипт:
1. Стартует Python sidecar (backend/)
2. Стартует Vite dev server для React UI (frontend/)
3. Открывает Tauri окно

Открывается окно Optimyzer. **При первом запуске будет full-screen LoginGate** — без активации внутрь не пускает (см. §4 ниже).

---

## 3. Cloud server (`server/`) — для cabinet и активации

Нужен только если хочешь полный flow с регистрацией / активацией / Pro подпиской. Для чистого desktop dev'а — можно не запускать.

### Первичная установка

```bash
cd server
python -m venv .venv
.venv/Scripts/activate           # Windows  (на macOS/Linux: source .venv/bin/activate)
pip install -e .[dev]
```

### Миграции БД

```bash
alembic upgrade head             # создаст optimyzer.db (SQLite) — для PostgreSQL см. DEPLOY_CHECKLIST.md
```

### Запуск

```bash
uvicorn api.main:app --reload --port 8001
```

OpenAPI docs: <http://127.0.0.1:8001/docs>

### Тесты

```bash
pytest                           # 99 tests, 89% coverage
```

---

## 4. Web cabinet (`cabinet/`) — для регистрации / активации desktop

```bash
cd cabinet
npm install
npm run dev                      # порт 5173
```

Открыть <http://127.0.0.1:5173>. Логин через Yandex OAuth → после login `/desktop-activate` показывает activation key для вставки в desktop.

### Production build

```bash
npm run build                    # → cabinet/dist/ (на nginx)
```

---

## 5. Landing (`landing/`) — статика

```bash
cd landing
python -m http.server 8000       # или любой другой static server
```

Открыть <http://localhost:8000>. Docs живут в `landing/docs/*.html`.

Production deploy — nginx config в `landing/nginx.conf.example`.

---

## 6. OAuth callback для dev (опционально)

Yandex OAuth callback зарегистрирован как `http://localhost/success`. Чтобы это работало локально на 80-м порту:

- **Через Apache** (есть у Сергея для 1С web-публикаций):
  ```apache
  ProxyPass /success http://127.0.0.1:8001/success
  ProxyPassReverse /success http://127.0.0.1:8001/success
  ```
- **Через nginx**:
  ```nginx
  location = /success {
    proxy_pass http://127.0.0.1:8001/success;
  }
  ```
- **Без proxy** — поднять `uvicorn` напрямую на `--port 80` (требует admin на Linux/Mac).

---

## 7. Полный dev flow с активацией

Запустить в трёх терминалах одновременно:

```bash
# Terminal 1 — cloud API
cd server && .venv/Scripts/activate && uvicorn api.main:app --reload --port 8001

# Terminal 2 — web cabinet
cd cabinet && npm run dev

# Terminal 3 — desktop
.\start.bat
```

Desktop откроется → LoginGate → «Войти через Yandex» → откроется browser на cabinet/login → OAuth → cabinet выдаст ключ → скопировать → вернуться в desktop → вставить → активирован ✅

---

## 8. Тесты

```bash
# Server (FastAPI)
cd server && pytest                            # 99 tests

# Desktop backend (Python)
cd backend && pytest                           # 499 tests

# Desktop frontend (TypeScript typecheck)
cd frontend && npm run typecheck

# Cabinet (TypeScript typecheck)
cd cabinet && npm run typecheck
```

---

## 9. Что лежит в корне

| Файл / папка                     | Что это                                          |
| -------------------------------- | ------------------------------------------------ |
| `.env.example`                   | Шаблон конфига для всех компонентов              |
| `.env`                           | Твой локальный конфиг (gitignored)              |
| `start.bat`                      | Запуск desktop в dev mode                       |
| `DESIGN_CONCEPT/`                | Утверждённые дизайны (read-only reference)      |
| `SCREENS/`                       | Скриншоты desktop UI                            |
| `docs/sales_sprint/`             | Отчёты sprint + `DEPLOY_CHECKLIST.md`           |

---

## 10. Production deploy

См. **`docs/sales_sprint/DEPLOY_CHECKLIST.md`** — там полный план:
- VDS + nginx + SSL (certbot)
- PostgreSQL вместо SQLite
- Yandex OAuth redirect URI на `https://api.optimyzer.pro/success`
- Production env vars (JWT_SECRET, YOOKASSA, ANTHROPIC ротация)
- systemd unit для uvicorn
- Cabinet build + landing static + nginx subdomain config

---

## 11. Troubleshooting

| Проблема                                                  | Решение                                                                  |
| --------------------------------------------------------- | ------------------------------------------------------------------------ |
| LoginGate в desktop — нет accessToken                     | Запусти cabinet + server, пройди регистрацию, скопируй ключ              |
| `npm install` падает на cabinet                           | Удалить `cabinet/node_modules` и `package-lock.json`, перезапустить      |
| `alembic upgrade head` ругается на DATABASE_URL           | Проверь что `.env` в корне (не в server/), DATABASE_URL заполнен          |
| Yandex OAuth: `invalid redirect_uri`                      | Зарегистрирован `http://localhost/success` — нужен proxy на :80 → :8001  |
| Tauri build падает на Windows                             | Установить Microsoft C++ Build Tools (часть Visual Studio)               |
| YooKassa: `Payment service unavailable`                   | `YOOKASSA_SHOP_ID`/`SECRET_KEY` пусты — это нормально в dev (stub-mode)  |
| AI Explainer: «AI not configured»                         | Заполни `ANTHROPIC_API_KEY` в корневом `.env`                            |
