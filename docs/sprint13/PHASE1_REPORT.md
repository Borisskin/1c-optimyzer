# S13 · Фаза 1 — Remote Config (ядро управления)

> Серверный конфиг, которым управляем продуктом без релиза desktop. Архитектура
> согласована в Фазе 0: отдельный `GET /v1/config`, админка через HTTP Basic,
> AI-feedback — телеметрией (Фаза 3). Дефолт — `discovery` (всё бесплатно).

## Что сделано

### Сервер

**Модель + миграция**
- `models/remote_config.py` — `RemoteConfig` (singleton-строка): `monetization_mode`
  (enum discovery/paid/mixed), `ai_kill_switch`, JSON-поля `limits` / `feature_flags` /
  `ai_model_per_type` / `prompt_versions`, `config_version` (int, +1 при изменении) + timestamps.
- `models/__init__.py` — регистрация (`RemoteConfig`, `MonetizationMode`).
- Миграция `d631f087e10c` (revises `a0ceab780d3b`) — `create_table('remote_config')`.
  Применена на dev SQLite (`alembic upgrade head`).

**Сервис** `services/config_service.py`
- `get_config(db)` — ORM singleton (создаётся с дефолтами при первом обращении).
- `get_effective_config(db)` — снимок-dict с TTL-кешем (30 c) для горячих путей
  (`decide`, AI guard); `invalidate_cache()` при `update_config` (и в тестовой фикстуре).
- `update_config(db, changes)` — частичное обновление; JSON-поля **мёржатся** (PUT не
  стирает непереданное); `config_version += 1`.
- `to_public_dict` отдаёт desktop только `monetization_mode / ai_kill_switch / limits /
  feature_flags / config_version` — серверные `ai_model_per_type` / `prompt_versions` **не утекают**.
- Дефолт: discovery, kill-switch off, лимиты безлимит (None), фичи включены
  (`query_analyzer` = false — он скрыт в продукте).

**Endpoints** `api/routers/config.py` (зарегистрированы в `main.py`)
- `GET /v1/config` — публичный (desktop тянет при старте + раз в ~6 ч; конфиг глобальный,
  device JWT не требуется → работает даже без активации).
- `GET /v1/admin/config` — HTTP Basic (`require_admin`), полный конфиг.
- `PUT /v1/admin/config` — HTTP Basic, частичное обновление; пустой PUT → 400.

**Применение на сервере**
- `services/soft_caps.py::decide()` — в начале: если режим `discovery` → `allowed=True`
  без проверки квот (учёт Usage ведём: `billed_against` = PRO_QUOTA для Pro иначе FREE_QUOTA).
  В `paid`/`mixed` — прежняя логика Free(5)/Credits/Pro без изменений.
- `api/routers/ai.py` — dependency `ai_enabled_guard` на всех 4 AI-эндпоинтах: при
  `ai_kill_switch` → 503 `{"error":"ai_temporarily_unavailable"}` (авторитетно на сервере).

### Desktop

- `api/cloud.ts` — `getRemoteConfig()` + типы `RemoteConfigPublic` / `RemoteConfigLimits` / `MonetizationMode`.
- `store/configStore.ts` — Zustand + localStorage (`optimyzer.remoteconfig.v1`). Дефолт
  пермиссивный (discovery, всё включено). При недоступности сервера — последний известный
  конфиг (**graceful**). Селекторы: `useFeatureEnabled` / `useAiKillSwitch` / `useMonetizationMode`
  + не-реактивные `isFeatureEnabled` / `isAiKillSwitchOn`.
- `hooks/useRemoteConfig.ts` — опрос при старте (+2 c) и раз в 6 ч; ошибка → молча на кеше.
- `App.tsx` — подключён `useRemoteConfig()`.
- `components/explainer/ExplainerCard.tsx` — **применение kill-switch** (демонстрация контура
  end-to-end): при `ai_kill_switch` AI-кнопки скрыты, вместо них нейтральная плашка
  «AI-консультация временно недоступна» (без тех-деталей про сервер/конфиг).

## Проверка

- **Сервер pytest — 322 passed, 0 failed** (`pytest -o addopts=""`). Новый `test_remote_config.py`
  (17 кейсов: config_service, discovery в decide, public/admin endpoints, Basic-auth, kill-switch 503).
- **Реальный smoke** (uvicorn :8001, curl): `GET /v1/config` → discovery; admin GET без auth → 401,
  c auth → 200; `PUT ai_kill_switch=true` → version 2 + публичный конфиг сразу отражает (кеш-инвалидация);
  `POST /v1/ai/explain` при kill-switch → **503 ai_temporarily_unavailable**; откат → dev-БД в дефолте.
  Сервер остановлен, `:8001` свободен, orphan нет.
- **Frontend typecheck — чисто**; **vitest — 128 passed** (+6 `configStore.test.ts`: дефолты,
  persist, merge при hydrate, graceful при сбое localStorage).
- ruff на изменённых core-файлах — чисто (кириллица RUF002/3 — шум для ru-проекта, не считаем).

## Попутно (предсущие проблемы, не регрессия S13)

В этом проекте `.env` имеет приоритет над `os.environ` (нестандартный порядок источников
в `settings`), из-за чего 2 теста были привязаны к захардкоженным значениям, которые локальный
`.env` перебивает → красные **до** S13. Сделал детерминичными от `settings`:
`test_telemetry.py::_admin_auth_header` (креды) и `test_yandex_oauth.py` (client_id/redirect).
Также 3 теста `soft_caps` + 1 `usage` обновлены под новое поведение (движок лимитов активен в
paid/mixed; discovery — безлимит) — это **by-design** следствие дефолта discovery.
`respx`/`ruff` уже были в `pyproject [dev]` — venv просто доустановлен (не правил зависимости).

## Отложено в Фазу 5 (интеграция/применение) — осознанно

- **feature_flags по всему UI** (прятать модули в Sidebar/routes по флагам) — широкий UI-проход;
  инфраструктура готова (`useFeatureEnabled`), применять в Фазе 5 «десктоп подхватывает».
- **limits/режим в UI** (показ остатка лимитов) — в discovery лимитов нет; актуально к paid (S16).
- **ai_model_per_type / prompt_versions** — поля и хранение есть; чтение моделью из конфига
  (вместо встроенных дефолтов `ai_explainer`) — наращиваемое, отдельным шагом.

## Критерии готовности (срез по Фазе 1)

- [x] Remote Config: режим/лимиты/фичи/AI kill-switch управляются с сервера без релиза desktop
- [x] Дефолт `discovery` (бесплатно, лимиты щедрые, реальный Claude+кэш не тронут)
- [x] Десктоп опрашивает конфиг, применяет (kill-switch), graceful при недоступности
- [x] Существующее (OAuth/billing/license/collector) не сломано, переиспользовано
- [x] Тесты, TS clean, точка отката (миграция down/ревизия), свои файлы в коммит

---
**Дата:** 2026-05-30 · **Статус:** Фаза 1 завершена. СТОП — отчёт.
**Дальше:** Фаза 2 (телеметрия под B1/B2/B4 + onboarding-портрет).
