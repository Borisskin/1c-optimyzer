# S13 · Фаза 0 — Разведка существующей инфраструктуры

> Цель Фазы 0: изучить что уже есть (из Sales Sprint), чтобы Remote Config +
> расширение телеметрии + админку **достраивать**, а не дублировать. Источники —
> прямое чтение кода `server/`, `frontend/`, `cabinet/` (без изменений). СТОП после
> отчёта: согласование архитектуры Remote Config — развилка, от неё зависит реализация.

## Сводка: что есть / переиспользуем / достраиваем

| Блок | Состояние | Вердикт S13 |
|------|-----------|-------------|
| Telemetry collector (сервер + клиент) | **Есть**, работает | Переиспользуем; **достраиваем** новые события + агрегаты под B1/B2/B4 |
| Billing / Credits / Subscriptions / soft caps | **Есть** | Переиспользуем; **добавляем** точку discovery-режима в `decide()` |
| License activation + heartbeat | **Есть** (login mandatory) | Переиспользуем как факт «у всех есть device JWT» |
| Admin endpoints | **Минимум** (1 шт, HTTP Basic) | **Достраиваем** config/users/leads + статистику |
| Yandex OAuth + JWT | **Есть** | Переиспользуем; ролей (`is_admin`) **нет** |
| AI endpoints + кэш | **Есть** | Переиспользуем; для feedback **нет** идентификатора объяснения |
| Cabinet (web) | **Есть** (3 видимые стр.) | Кандидат под админ-раздел |
| Remote Config / feature-flags / kill-switch | **НЕТ ВООБЩЕ** | **Строим с нуля** (ядро S13) |
| Onboarding-портрет ЦА (роль/тип/размер/СУБД) | **НЕТ** | **Строим с нуля** |

---

## 1. Telemetry collector (Phase 1.6) — есть, расширяемо

**Сервер:**
- `POST /v1/telemetry/batch` — приём (открытый, *опциональный* JWT привязывает `user_id`; rate-limit 20/мин аноним, 100/мин авторизованный). Файл `server/api/routers/telemetry.py`.
- `GET /v1/admin/telemetry/summary?period_days=N` — агрегаты (HTTP Basic). Файл `server/api/routers/admin.py`.
- Модель `TelemetryEvent` (`server/models/telemetry.py`): `user_id?`, `device_fingerprint`, `app_version`, `platform`, `category` (tech/behavior/conversion), `event_type` (свободная строка ≤64), `payload` (JSON), `timestamp`, `received_at`.
- Сервис `server/services/telemetry_service.py`: `record_batch()`, `summarize()`, `cleanup_old_events()` (90 дней; scheduler 05:00 МСК, только если `ENABLE_SCHEDULER` + prod).

**Клиент (desktop):**
- `frontend/src/utils/telemetry.ts` — `emit(category, event_type, payload)` + объект `telemetry.*`.
- `frontend/src/store/telemetryStore.ts` — буфер (Zustand + localStorage `optimyzer.telemetry.buffer.v1`, max 1000, старые вытесняются).
- `frontend/src/hooks/useTelemetryFlush.ts` — flush через 30 c после старта, затем каждые 5 мин + на unmount/beforeunload. Сеть упала → буфер сохраняется, ретрай в следующий цикл.

**Текущие события:** `app_started`, `screen_view`, `archive_loaded`, `ai_clicked`, `paywall_shown`, `upgrade_clicked` (последние 4 определены, вызываются не все).

**Ключевой вывод:** новые **события** добавляются БЕЗ изменений сервера (`event_type` свободный, summary группирует top-30 по типу). НО `summarize()` отдаёт только `by_category / by_event_type / by_app_version / by_platform` — **нет** разрезов по сегменту/портрету/retention/feedback. Значит B1 (портрет ЦА), B2 (флагман), B4 (retention), AI-feedback-сводка требуют **новых агрегатов** (новый admin-endpoint или расширение `summarize()` + новые поля в payload).

---

## 2. Billing / soft caps — есть; точки discovery нет

- Модели (`server/models/`): `Subscription` (FREE/PRO), `Credits` (MINI/STANDARD/BULK), `Device`, `LicenseKey`, `Usage`, `Payment`, `RefreshToken`.
- `server/services/soft_caps.py` → `decide(db, user, *, cost=1) -> UsageDecision`. Логика: **Pro** (безлимит до soft cap 1000/мес, warning не блокирует) → **Credits** (списываем) → **Free** (`settings.free_ai_monthly_limit`=5/мес) → `denied(reason="free_limit_exceeded")`.
- Вызовы: `/v1/usage/check` (десктоп спрашивает ПЕРЕД AI-операцией) и `services/usage_service.track()`.
- **Точки «отключить лимиты для discovery» НЕТ.** Точка интеграции Remote Config — **начало `decide()`**: если `monetization_mode == discovery` → вернуть `allowed=True` (либо щедрый лимит из конфига) до проверки квот.

---

## 3. License + heartbeat — есть; важный факт для доставки конфига

- `server/api/routers/license.py`: `/activate` (key+fingerprint → **device JWT**), `/my-key`, `/regenerate-key`, `/heartbeat` (device JWT, десктоп стучит раз в 24 ч; ответ: `subscription_plan`, `subscription_ends_at`, `ai_quota_remaining`, `credits_remaining`).
- **Login mandatory** (решение 23.05.2026 — приложение заблокировано без активации; Free тоже активируется и получает device JWT). → **у ВСЕХ десктопов есть device JWT**. Это снимает необходимость в отдельном анонимном канале для конфига, но heartbeat (24 ч) слишком медленный как единственный канал доставки (kill-switch должен применяться быстрее).

---

## 4. Admin endpoints + авторизация — минимум

- Единственный: `GET /v1/admin/telemetry/summary`.
- Auth = **HTTP Basic** (`server/api/deps.py:require_admin`), креды `settings.admin_username`/`admin_password` (дефолт `admin`/`change-me` — переопределить в `.env`). Защита `secrets.compare_digest`.

---

## 5. Auth (Yandex OAuth + JWT) — есть; ролей нет

- `get_current_user` — access JWT (Bearer header ИЛИ cookie `access_token`) → для cabinet.
- `get_current_device_user` — device JWT (Bearer only) → для desktop.
- JWT: access 900 c / refresh 30 д (хеш в БД) / device 90 д. Секрет `settings.jwt_secret`.
- **Роли отсутствуют** — в `User` нет `is_admin`. Админ-доступ сейчас только через HTTP Basic.

---

## 6. AI endpoints + кэш — есть; идентификатора объяснения нет

- `server/api/routers/ai.py`: `/v1/ai/explain`, `/explain_plan`, `/explain_regression`, `/generate_logcfg` + `/force_refresh_status/{cache_key}`.
- Ответы: `summary` + специфика (issues/hotspots/recommendations/…) + `cache_key`, `was_cached`, `cache_age_seconds`. **`explanation_id` НЕТ** — `cache_key` (sha256) не привязан к юзеру.
- Кэш (`server/services/ai_cache/`): ключ = `sha256(canonical_input | type | prompt_version | model)`; `PROMPT_VERSION_*` = `"v1"`; TTL: query 90 д, plan ∞, logcfg 30 д, regression ∞.
- Desktop: вызовы в `frontend/src/api/cloud.ts`; AI-объяснения рендерятся в `frontend/src/components/explainer/ExplainerCard.tsx` (kinds: deadlock/operation/session/lock/exception/slow_op) и в планах PlanAnalyzer → **сюда вешать 👍/👎**.

---

## 7. Cabinet (web) — кандидат под админку

- React 18 + Vite + react-router 6 + react-query. Auth = **HttpOnly cookies** (`cabinet/src/api/client.ts`, `credentials: "include"`).
- Видимые страницы: Overview / Credits / Payments (+ Login); 5 скрыты редиректом на `/`.
- Layout `cabinet/src/components/layout/CabinetLayout.tsx` (sidebar + NavLink) — легко добавить раздел.
- **Конфликт auth:** cabinet на JWT-cookies, а `/v1/admin/*` на HTTP Basic — несовместимо без доработки (см. развилку 2).

---

## 8. Alembic / БД

- Dev: SQLite `server/optimyzer.db`. Head-ревизия: `a0ceab780d3b`.
- Новая миграция: `alembic revision --autogenerate -m "slug"` → `alembic upgrade head` (из `server/`). `render_as_batch` включён для SQLite.

---

## Предложение архитектуры Remote Config

**Хранилище (сервер):** таблица `remote_config` — одна строка-«документ»: типизированные колонки для критичного (`monetization_mode` enum discovery/paid/mixed, `ai_kill_switch` bool) + JSON-колонки для гибкого (`limits`, `feature_flags`, `ai_model_per_type`, `prompt_versions`) + `version` (int, инкремент при PUT) + `updated_at`. Опционально — `config_audit` (кто/когда/что менял).

**Доставка на десктоп:** новый `GET /v1/config` — отдаёт глобальный конфиг + `version`; опциональный device JWT (как у `/telemetry/batch`). Десктоп: опрос при старте + раз в ~6 ч, кеш в localStorage, **graceful** при недоступности сервера (работа на последнем известном конфиге, не падать). Применение: режим/лимиты/доступность фич/модель/kill-switch.

**Применение лимитов:** `soft_caps.decide()` читает активный конфиг в начале; `discovery` → `allowed=True` (или щедрый лимит из `limits`).

**AI kill-switch:** проверяется авторитетно на сервере в `/v1/ai/*` (мягкий 503/«временно недоступно») И на десктопе (прячет кнопки AI по конфигу).

**Управление (запись):** `/v1/admin/config` GET/PUT под `require_admin`; PUT инкрементит `version`.

**Дефолт:** `monetization_mode=discovery`, лимиты щедрые/без лимита, все рабочие фичи включены, AI на реальном Claude + кэш, `ai_kill_switch=false`. Биллинг выключен, но включается сменой `monetization_mode` (готовность к S16).

---

## Развилки на согласование (СТОП — жду решения)

**Развилка 1 — Канал доставки конфига на десктоп**
- **A (рекомендую):** отдельный `GET /v1/config`, свой период (старт + ~6 ч). Чистое разделение; kill-switch применяется за ≤6 ч.
- B: прицепить к `/v1/license/heartbeat` (24 ч). Минус — медленное применение kill-switch.

**Развилка 2 — Админка: вход и размещение**
- **A (рекомендую):** раздел в cabinet, вход по admin-паролю (переиспользуем HTTP Basic `require_admin` как есть). Просто, не трогает `User`/OAuth. Владелец — единственный админ.
- B: роли — `is_admin` в `User`, перевод `/v1/admin/*` на JWT+роль, NavLink только админу. Красивее/масштабируемо, но миграция `User` + правка auth (риск задеть рабочий OAuth).
- C: отдельное мини-приложение admin.

**Развилка 3 — Привязка AI-feedback (👍/👎)**
- **A (рекомендую):** слать как telemetry-событие `ai_feedback{kind, rating, was_cached}` — без `explanation_id`, без содержимого. Приватно, просто; для сводки «% полезных по типам» хватает.
- B: добавить `explanation_id` (UUID) во все 4 AI-ответа + таблица `ai_feedback` с привязкой к юзеру/объяснению. Точнее (дедуп, привязка), но трогает все AI-ответы + новая модель/endpoint.

---

**Дата:** 2026-05-29 · **Статус:** Фаза 0 завершена, СТОП — согласование 3 развилок.
**Дальше:** Фаза 1 (Remote Config: модель + `/v1/config` + `/v1/admin/config` + применение в `decide()` и `/v1/ai/*` + опрос на десктопе).
