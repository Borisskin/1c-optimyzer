# Architect Handoff — Optimyzer v0.5

**Дата:** 2026-05-24
**Для:** Claude Opus 4.7 (новая сессия, контекст потерян)
**От:** Sergey (owner) + Claude Sonnet (executor, эта сессия)

> Один документ, который восстанавливает весь контекст проекта. Читать сверху вниз. Ссылки на git/docs — кликабельные пути от корня репо.

---

## 1. Команда и роли

| Кто | Роль | Что делает |
|-----|------|-----------|
| **Сергей** | Owner, organizer, domain expert (1С эксперт) | Принимает все продуктовые/UX решения. Гоняет E2E-сценарии на реальных архивах ТЖ. Запускает спринты. Финальный QA. |
| **Claude Opus 4.7** | Architect | Декомпозирует фичи в Phase/Sprint, пишет промпты для executor'а, проверяет архитектурные решения, держит DECISIONS.md. **← это ты.** |
| **Claude Sonnet (Code)** | Executor | Реализует промпты. Пишет код, тесты, fix'ы. Коммитит. Не принимает архитектурных решений без согласования. |

**Поток работы:**
```
Сергей (что нужно) → Opus (как делать, в каком порядке, какой промпт)
                  ↓
              Sonnet (делает по промпту, коммитит)
                  ↓
              Сергей (тестирует, даёт feedback)
                  ↓ если что-то не так
              Opus (как фиксить) → Sonnet (фиксит)
```

Промпты от Opus к Sonnet лежат в [`docs/sprint_prompts/`](../docs/sprint_prompts/) и [`docs/SPRINT_*_PROMPT.md`](../docs/).

---

## 2. Продукт — что это

**Optimyzer** — APM (Application Performance Monitoring) для 1С:Предприятие.

**Конкретно:** инструмент анализа архивов **технологического журнала 1С** (ТЖ). Юзер собирает с продуктива папку логов 1С (часто 1-15 ГБ), кидает в Optimyzer drag-and-drop → получает: медленные SQL, deadlocks, exceptions, паттерны нагрузки, AI-объяснения проблем.

**Целевая аудитория:** 1С-разработчики, DBA, тех. поддержка крупных внедрений 1С.

**Уникальность vs существующих решений (ЦУП от 1С, MD-Audit):**
- Десктоп, не SaaS — данные клиента не уходят в облако (для них это важно)
- Анализирует архивы любого размера через streaming (ЦУП падает на >2 ГБ)
- AI-объяснения на русском (Claude API) — что значит этот EXCPCNTX, как пофиксить блокировку
- Удобный SQL Console поверх DuckDB (raw queries, autocomplete по schema)
- ru-RU first, не calque с английского

**Бизнес-модель:** Free (5 AI-консультаций/мес) + Pro (2 990 ₽/мес безлимит) + Credits (разовые пакеты).

---

## 3. Архитектура — 5 компонентов

| Компонент | Папка | Что | Технологии |
|-----------|-------|-----|------------|
| **Desktop backend** | [`backend/`](../backend/) | Python sidecar для Tauri — парсинг ТЖ, DuckDB analytics, AI calls | Python 3.11+, DuckDB, sqlparse, anthropic SDK, pyarrow |
| **Desktop frontend** | [`frontend/`](../frontend/) | Tauri 2 app — основной UI юзера | Tauri 2 + React 18 + TypeScript + Vite + CodeMirror 6 + Recharts + zustand |
| **Cloud server** | [`server/`](../server/) | FastAPI — auth, billing, license, telemetry для cabinet и desktop activation | Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, SQLite (dev) → PostgreSQL (prod), JWT, yookassa SDK |
| **Web cabinet** | [`cabinet/`](../cabinet/) | React webapp для `account.optimyzer.pro` — регистрация, выдача ключа активации, управление подпиской | React 18 + TypeScript + Vite + React Router 6 + TanStack Query 5 |
| **Landing** | [`landing/`](../landing/) | Статика для `optimyzer.pro` — маркетинг + docs | HTML + CSS, nginx config готов |

**Связи:**
```
                    ┌───────────────────────┐
                    │    optimyzer.pro      │  ← landing (статика)
                    │   (маркетинг + docs)  │
                    └───────────────────────┘
                                │
                ↓ «Скачать» / «Получить ключ»
                                │
   ┌────────────────────┐                ┌──────────────────────────┐
   │  Desktop (Tauri)   │ ←─activate─→   │  account.optimyzer.pro   │
   │  • парсит ТЖ       │   (OPTM-ключ)  │  (cabinet React app)     │
   │  • DuckDB + SQL    │                │  • Yandex OAuth login    │
   │  • AI explainer    │                │  • выдаёт ключ           │
   │  • локальный анализ│                │  • Pro/Credits/Billing   │
   └────────┬───────────┘                └──────────┬───────────────┘
            │                                        │
            └────────► api.optimyzer.pro (server/) ◄┘
                       • /v1/auth/* (Yandex OAuth)
                       • /v1/license/* (activate, my-key, heartbeat)
                       • /v1/subscriptions/* /credits/* /usage/*
                       • /v1/webhooks/yookassa (платежи)
                       • /v1/telemetry/* (сбор метрик)
```

**Запуск всего локально:** см. [`QUICKSTART.md`](../QUICKSTART.md) (5 терминалов: backend sidecar внутри tauri, frontend dev, server uvicorn, cabinet vite, landing python http.server, опц. oauth_proxy на :80).

---

## 4. История разработки — что сделано

### Module 1 / Desktop core (Sprint 0..5, март-май 2026)

Полный workbench для анализа ТЖ. **Production-ready на 2026-05-19** (тег `v0.5.0-internal`).

| Sprint | Что | Тесты | Отчёт |
|--------|-----|-------|-------|
| **0** | Discovery, скелет Tauri, DRY-run на маленьком архиве | — | [`docs/SPRINT_0_REPORT.md`](SPRINT_0_REPORT.md) |
| **1** | Streaming parser (12 GiB verified), DuckDB store, базовые экраны | 130 | [`docs/SPRINT_1_REPORT.md`](SPRINT_1_REPORT.md) |
| **2** | SQL Console + 6 pre-built Views + cross-filtering + Comparison + Templates | 183 + 15 acceptance | [`docs/SPRINT_2_REPORT.md`](SPRINT_2_REPORT.md) |
| **3** | AI Explainer (rule-based + Claude API), 8 rules для типовых проблем | +60 | [`docs/SPRINT_3_REPORT.md`](SPRINT_3_REPORT.md) |
| **3.5** | UX-polish 10 фиксов (formatting SQL, sticky headers, EXCPCNTX double-count) | — | [`docs/SPRINT_3_5_REPORT.md`](SPRINT_3_5_REPORT.md) |
| **4** | Anatomy views (drill-down по бизнес-операциям, deadlocks, slow queries) | +80 | [`docs/SPRINT_4_REPORT.md`](SPRINT_4_REPORT.md) |
| **5** | Configuration parser (XML конфигурации 1С), Predefined.xml, semantic rules с context конфигурации | +90 | [`docs/SPRINT_5_REPORT.md`](SPRINT_5_REPORT.md) |

**Итого в desktop backend:** 499 tests, ~89% coverage.

### Sales Sprint / Module 2 (Phase 1-2, 23-24 мая 2026)

Превращение desktop-only тула в продаваемый сервис.

| Phase | Что | Отчёт |
|-------|-----|-------|
| **1.1** | `server/` scaffold + Yandex OAuth + JWT (access/refresh/device) + cookies | [`docs/sales_sprint/PHASE_1_REPORT.md`](sales_sprint/PHASE_1_REPORT.md) |
| **1.2** | Backend API: subscriptions / credits / devices / usage / dashboard | ← там же |
| **1.3** | `cabinet/` React webapp — 7 pages (Overview, Subscription, Credits, Devices, Payments, Usage, Settings) | ← там же |
| **1.4** | YooKassa integration: sandbox/prod, чеки, recurring billing, idempotent webhooks | ← там же |
| **1.5** | License activation flow в desktop | ← там же |
| **1.6** | Telemetry collector | ← там же |
| **2.1** | Landing deployment prep (`landing/` копия `DESIGN_CONCEPT/`, mock-ссылки → реальные, nginx config) | [`docs/sales_sprint/PHASE_2_REPORT.md`](sales_sprint/PHASE_2_REPORT.md) |
| **2.2** | Onboarding flow в desktop (WelcomeModal, EmptyArchiveState) | ← там же |
| **2.6** | Support page + docs structure (`landing/docs/` — 7 HTML страниц) | ← там же |

**Phase 2.3-2.5** (статья на Инфостарте, demo-видео, outreach) — это **работа Сергея**, не Claude Code.

**Итого в server:** 101 tests, 89% coverage.

### Post-Phase fixes (24 мая 2026, эта сессия)

Sergey начал реальное E2E тестирование Sales Sprint flow. Куча мелких/средних багов всплыло — починили:

| Commit | Что | Файлы |
|--------|-----|-------|
| `225b693` | `@tauri-apps/plugin-shell` + global hijack `<a target=_blank>` (раньше кнопка «Открыть личный кабинет» в десктопе ничего не делала) | `frontend/src/utils/openExternal.ts`, `main.tsx`, `tauri.conf.json` |
| `7857ec5` | Cabinet vite — `host: true` (раньше слушал только `::1` → `127.0.0.1:5173` ECONNREFUSED) | `cabinet/vite.config.ts` |
| `0244e12` | Красная плашка «Подписку не удалось проверить» больше не показывается обычному Free-юзеру | `frontend/src/components/chrome/AccountTab.tsx` |
| `235ba07` | (отменён в a9d9779) | — |
| `a9d9779` | **Архитектурный рефакторинг:** server = source of truth для квот/кредитов. Heartbeat 24ч → 5 мин. После trackUsage — мгновенный triggerHeartbeat. Локально только token+deviceId. | `accountStore.ts`, `useHeartbeat.ts`, `AccountTab.tsx`, `ExplainerCard.tsx` |
| `3bd2433` | Дальнейшее упрощение: deviceId тоже выкинут (он зашит в JWT claims, сервер сам извлекает). В localStorage десктопа теперь **только accessToken**. | те же 3 файла |

### Решения по дороге (важные для контекста)

- **`yandex_id nullable`, email unique** — был многократный flip-flop между OAuth-only / email-only / key-only. Финал: **persistent personal key** (один OPTM-ключ на user, можно регенерить в cabinet).
- **Никаких упоминаний 54-ФЗ / 152-ФЗ / GDPR / compliance в UI и docs** — Sergey ОЧЕНЬ четко: «это технический продукт, не бюрократия». Commits `a293846`, `fc3871f`.
- **Никаких ▶▼ disclosure triangles** — Sergey ненавидит. Cursor:pointer + hover, никаких glyph'ов.
- **Telemetry без opt-out** — собираем silent, никаких privacy-toggle'ов в UI. Commit `c17faa6`.
- **Показывать ВСЕГДА `sql_text` (raw), НЕ `sql_text_normalized`** (с «?»). Norma только для GROUP BY hash. Commit `0878e2e`.
- **Никаких VPS/VDS пока** — Sergey разрабатывает локально, `localhost:8001` для server, no prod deploy. План deploy в [`docs/sales_sprint/DEPLOY_CHECKLIST.md`](sales_sprint/DEPLOY_CHECKLIST.md).
- **Single root `.env`** для всех 5 компонентов (vite через `envDir: ".."`, server через `PROJECT_ROOT/.env`).

---

## 5. UI/UX обзор

### Desktop (frontend/)

**Главное окно** ([`frontend/src/App.tsx`](../frontend/src/App.tsx)):
- При первом запуске — **WelcomeModal** (выбор «Загрузить архив» / «Пропустить»)
- Если нет архива — **EmptyArchiveState** с большой иконкой папки
- Sidebar слева (compact icons), top header с пикером архивов, status bar снизу

**Экраны** ([`frontend/src/components/screens/`](../frontend/src/components/screens/) и `views/`):
1. **События ТЖ** — raw таблица событий с фильтрами (тип, role, context)
2. **SQL Console** — CodeMirror SQL editor + autocomplete по DuckDB schema + результаты
3. **Медленные запросы** (Top SQL) — агрегация по sql_text_hash + expand row с timeline по каждой операции
4. **Блокировки** (Locks Timeline) — таблица с расшифровкой deadlock'ов
5. **Роли процессов** (Process Roles) — pie + by-role breakdown
6. **Гистограмма длительности** (Duration Histogram)
7. **Ошибки** (Errors Feed) — EXCPCNTX с stack trace
8. **Активность** (Activity Heatmap)
9. **Бизнес-операции** (Anatomy) — drill-down по бизнес-операции → timeline → breakdown → top SQL → exceptions внутри
10. **Сравнение архивов** — side-by-side baseline vs compared с regression detection

**Overlays:**
- **PaywallModal** — показывается при попытке AI без login / при достижении лимита Free
- **Settings dialog** — 2 вкладки:
  - **Аккаунт** — Free/Pro badge, прогресс квоты, поле для OPTM-ключа, ссылка в cabinet
  - **О программе** — версия, ссылки

**AI Explainer** ([`frontend/src/components/explainer/ExplainerCard.tsx`](../frontend/src/components/explainer/ExplainerCard.tsx)) — карточка под каждой бизнес-операцией / deadlock / slow query / exception:
- Сначала проверяем cache БД (instant)
- Если rule-based объяснение есть — показываем сразу
- Кнопка «Объяснить через AI» → checkUsage (можно ли?) → backend call к Claude → cache в DuckDB → trackUsage → triggerHeartbeat (обновить счётчик в Settings)

### Cabinet (cabinet/)

**Pages** ([`cabinet/src/pages/`](../cabinet/src/pages/)):
- **Login** — единственная кнопка «Войти через Yandex»
- **OAuthCallback** — обрабатывает `?code=…&state=…` (но реально callback идёт через server `/success`)
- **Overview** — главная: приветствие, 3 metric cards (Тариф, AI-операции, Кредиты), `ActivationKeyCard` (OPTM-ключ + копировать + перегенерить), `DownloadCard` (placeholder — desktop сборки появятся в первом релизе)
- **Subscription / Credits / Payments / Usage / Devices / Settings** — заготовки, **сейчас скрыты из sidebar** по решению Sergey: «clean UX, начнём с Overview, остальное добавим когда понадобится»

### Landing (landing/)

- `index.html` — главная (Hero, Features, Pricing, FAQ, Footer)
- `docs/` — 7 HTML страниц (installation, first archive, AI explainer, plans, и т.д.)
- Pulse-логотип, teal accent, шрифты Inter (self-hosted)

### Скриншоты

Папка [`SCREENS/`](../SCREENS/) — 10+ PNG скриншотов desktop UI (от Sergey, периодически обновляются).

---

## 6. Git / Repo

- **URL:** https://github.com/anymasoft/1c-optimyzer
- **Default branch:** `main`
- **Текущий tag:** `v0.5.0-internal` (Sprint 5 closure, до Sales Sprint)
- **HEAD:** `3bd2433` (после Phase 1-2 + сегодняшние fix'ы)

**Свежие 10 commits:**
```
3bd2433 refactor(account): убираю deviceId из локалки — только accessToken
a9d9779 refactor(account): server = source of truth для квот/кредитов
235ba07 fix(quota): счётчик AI-консультаций обновляется сразу
0244e12 fix(account): красный warning только при реальной offline-degradation
7857ec5 fix(cabinet): vite слушать на всех loopback интерфейсах (host: true)
225b693 fix(desktop): открытие cabinet/landing/docs ссылок через Tauri shell
ba8d3d8 feat(license): персональный постоянный ключ вместо одноразовых
18c7cae revert(auth): возврат к key-flow вместо email-only
7e9a7fe chore(cleanup): доделать email-flow + убрать dead code device-flow
73d1ea1 feat(auth): email-only flow для desktop вместо OAuth/device-flow
```

**Tests** (на 2026-05-24):
- `backend/`: 499 tests passed (89% coverage)
- `server/`: 101 tests passed (89% coverage)
- `frontend/`: TypeScript typecheck clean
- `cabinet/`: TypeScript typecheck clean

---

## 7. Что работает / что нет (текущее состояние)

### ✅ Работает end-to-end (Sergey проверил руками 24 мая)

- Open cabinet → Yandex OAuth → выдача ключа OPTM-XXXX
- Перегенерация ключа в cabinet (старый отозван)
- Активация ключа в desktop → device JWT выдан
- AI-консультация в desktop → tokens отосланы, trackUsage → счётчик в Settings обновляется
- Открытие cabinet из десктопа через `<a target=_blank>` (через Tauri shell.open)
- E2E smoke-тест: [`server/scripts/_e2e_check.py`](../server/scripts/_e2e_check.py) — 9 шагов, все ✓

### ⚠️ Работает но в stub/dev режиме

- **YooKassa** — без реальных credentials в `.env` (`YOOKASSA_SHOP_ID` / `SECRET_KEY` пусты) — confirmation URL фейковый, реальную оплату не пройти. Сервер автоматически в stub-mode. Для prod — нужно Sergey зарегистрироваться как самозанятый и привязать ЮKassa.
- **Email transactional** — `SMTP_*` пусты, никакие письма не уходят (но нигде в текущем flow они и не нужны, OAuth-only регистрация).
- **OAuth callback** — работает только через локальный `scripts/oauth_proxy_80.py` (port 80 → 8001). В prod нужен nginx с реверс-проксированием `https://api.optimyzer.pro/success`.

### ❌ НЕ сделано (отложено)

- **Production deploy** — нет VDS, нет SSL, нет nginx, нет PostgreSQL. План полный — [`docs/sales_sprint/DEPLOY_CHECKLIST.md`](sales_sprint/DEPLOY_CHECKLIST.md).
- **Desktop installers** — `.msi` / `.dmg` / `.AppImage` не собираются ни в один CI/release. Юзер не может скачать продукт — только `git clone` + `cargo build` + `npm install`.
- **OS Keychain для JWT** — accessToken в localStorage (plaintext на диске). Не критично для MVP, но указано в `accountStore.ts` как Phase 2.
- **Recurring billing scheduler** — есть код в `services/recurring_billing.py` но не запущен в фоне. Нужно systemd unit или внутренний APScheduler.
- **Interactive onboarding tour** — отложено. Решили что Welcome + Empty States достаточно.
- **Маркетинг** — статья на Инфостарте, demo-видео, outreach в TG-каналы — это работа Sergey.

### 🐛 Известные баги / разовые неудобства

- Sergey при следующем рестарте десктопа должен будет **активировать OPTM-ключ заново** (поднял STORAGE_KEY v1→v3 при рефакторинге `accountStore`). Дальше всё стабильно.
- Yandex OAuth `redirect_uri=http://localhost/success` — для prod надо менять и в Yandex admin, и в `.env`.

---

## 8. Архитектурные принципы, которые Sergey требует уважать

1. **Server = source of truth** для всего, что касается биллинга (квоты, кредиты, plan). Локальный кеш в desktop — только UX cosmetic. Подмена в localStorage никак не активирует Pro-фичи, потому что сервер сам решает `checkUsage → allowed`.
2. **Локально храним МИНИМУМ** — сейчас в `localStorage` десктопа лежит **только `accessToken`**. user_id и device_id — внутри JWT claims, сервер сам декодирует.
3. **Single .env в корне** — для всех 5 компонентов. Vite/Tauri/FastAPI читают один источник.
4. **Никаких ▶▼ disclosure-triangles.** Никогда. Курсор-pointer + hover на всю строку.
5. **Никакой бюрократии в UI** — 54-ФЗ, 152-ФЗ, GDPR, compliance, persdata processing — этих слов нигде нет. Технический продукт.
6. **Real SQL > normalized.** В UI всегда показывать `sql_text` (с реальными параметрами), не `sql_text_normalized` (со `?`). Юзер должен видеть что реально гонялось.
7. **Telemetry silent.** Собираем всегда, никаких opt-out toggle'ов в UI.
8. **Local-dev first.** Никаких production URL hardcoded. Всё через `localhost`/`127.0.0.1`. Production — отдельной фазой.
9. **Локализация ru-RU first.** Англ. интерфейс не нужен (target = российский рынок 1С).
10. **Self-hosted шрифты, никаких Google Fonts** на runtime (privacy).

---

## 9. Где смотреть код для понимания каждой фичи

| Фича | Точки входа |
|------|------------|
| **Парсинг ТЖ** | `backend/src/optimyzer_backend/parsers/` |
| **DuckDB schema** | `backend/src/optimyzer_backend/storage/` |
| **AI Explainer** | `backend/src/optimyzer_backend/ai/` (Python), `frontend/src/components/explainer/ExplainerCard.tsx` (UI) |
| **Configuration parser (Sprint 5)** | `backend/src/optimyzer_backend/config_parser/` |
| **JSON-RPC sidecar protocol** | `backend/src/optimyzer_backend/rpc/` (Python), `frontend/src-tauri/src/sidecar.rs` (Rust) |
| **Auth (Yandex OAuth)** | `server/api/routers/auth.py`, `server/services/yandex_oauth.py`, `server/services/auth_service.py` |
| **License (activate / my-key / heartbeat)** | `server/api/routers/license.py`, `server/services/license_keys_service.py`, `server/services/device_service.py` |
| **Subscriptions + YooKassa** | `server/api/routers/subscriptions.py`, `server/services/payment_processor.py`, `server/services/yookassa_client.py` |
| **Credits** | `server/api/routers/credits.py`, `server/services/credits_service.py` |
| **Usage / Soft caps** | `server/api/routers/usage.py`, `server/services/soft_caps.py` |
| **Cabinet pages** | `cabinet/src/pages/*.tsx` |
| **Desktop account state** | `frontend/src/store/accountStore.ts`, `frontend/src/hooks/useHeartbeat.ts` |

---

## 10. Открытые вопросы для архитектора

Sergey хочет, чтобы Opus подумал/прорешал:

1. **Когда деплоить на VDS?** Сейчас всё на localhost. У нас работающий MVP — но никто извне не может попробовать. Phase 3 = production deploy. Когда стартовать?
2. **Device limits (Free=1, Pro=5)** — сохраняем или убираем? Аргумент Sergey: «зачем усложнять защитой от шаринга, у нас target-юзеры не будут шарить массово». Аргумент в пользу limits: классический anti-abuse.
3. **Desktop installers + auto-update.** Сейчас нет ни одного. Какой подход? Tauri updater + GitHub Releases? Подписывать ли .msi (Microsoft signing — $$$)?
4. **Email transactional flow.** Сейчас на ноль. Нужно ли: payment receipts, key delivery, password reset (нет паролей — OAuth-only), churn warnings («Pro заканчивается через 3 дня»)?
5. **Onboarding для landing.** Сейчас юзер заходит на landing → жмёт «Скачать» → 404 (нет installer'ов). Что показывать вместо? «Скачивание скоро»? Waitlist email-сбор?
6. **PostgreSQL миграция.** SQLite OK для dev, для prod уже многие clients. Когда переезжать? До или после первого платного клиента?
7. **Куда положить configuration parser в продуктовом флоу?** В Sprint 5 он есть в backend, но в UI он сейчас выключен (commit `feat: hide query-analyzer from Sidebar/shortcuts/routes`). Реактивировать? Куда?

---

## 11. Файлы которые архитектор должен прочитать первыми

После этого handoff:

1. [`QUICKSTART.md`](../QUICKSTART.md) — как поднять локально
2. [`docs/DECISIONS.md`](DECISIONS.md) — все ADR (Architecture Decision Records) — 32 решения
3. [`docs/sales_sprint/PHASE_1_REPORT.md`](sales_sprint/PHASE_1_REPORT.md) + [`PHASE_2_REPORT.md`](sales_sprint/PHASE_2_REPORT.md) — что сделано в Sales Sprint
4. [`docs/sales_sprint/DEPLOY_CHECKLIST.md`](sales_sprint/DEPLOY_CHECKLIST.md) — план prod deploy
5. [`docs/SPRINT_5_REPORT.md`](SPRINT_5_REPORT.md) — последний по Module 1 (для контекста как анализ ТЖ устроен)
6. [`server/api/routers/`](../server/api/routers/) — все endpoints
7. [`frontend/src/store/accountStore.ts`](../frontend/src/store/accountStore.ts) + [`useHeartbeat.ts`](../frontend/src/hooks/useHeartbeat.ts) — текущая модель состояния десктопа после рефакторинга 24 мая
8. [`SALES_SPRINT_PROMT.md`](../SALES_SPRINT_PROMT.md) — изначальный промпт Sales Sprint (от Opus → Sonnet) — для понимания исходного плана

---

## 12. Как Sergey даёт фидбек (для понимания стиля)

- **Прямой, без воды.** «Не работает кнопка в десктопе» — без длинных пояснений.
- Часто присылает **скриншот** + одно предложение.
- Реагирует на over-engineering: «зачем ты все усложняешь???»
- Не любит когда отвлекают вопросами по мелочам — admin-actions (commits, fixes) делать без явного approval. Destructive (delete, reset --hard) — спрашивать.
- **НИКОГДА** не удалять без явного warning'а — был инцидент когда executor удалил ANTHROPIC_API_KEY из `.env.example` при push protection failure. Sergey очень сильно отреагировал.

---

**Конец handoff.** Если что-то непонятно — спрашивай у Sergey, он эксперт по продукту и принимает все архитектурные решения совместно с тобой.
