# Sales Sprint — Promt для Claude Code

> Запуск Optimyzer в продакшен: инфраструктура (auth, billing, web-кабинет, license activation, soft caps, telemetry) + маркетинг (лендинг, статья на Инфостарте, демо, outreach).
>
> **Не Sprint 6** — Sprint 6 (восстановление QueryAnalyzer через полноценный SDBL parser) заморожен до market validation после запуска.

---

## Контекст для исполнителя

**Кто работает:** Claude Code на компьютере Сергея (`D:\1C-Optimyzer\`).
**Что было до этого:** 5 закрытых спринтов разработки (теги `v0.5.0-internal`), UI Cleanup для Sales (commit `2532cc2`), готовый дизайн в `DESIGN_CONCEPT/` (Pulse logo, лендинг + web-кабинет + desktop Settings).
**Что не делается в этом спринте:** восстановление QueryAnalyzer / семантическая валидация / новые аналитические features. Только то, что нужно для **продаж**.

**Sales Sprint Phase 1 + Phase 2 = 6-9 недель работы.** Phase 1 — техническая инфраструктура без которой нельзя начать продавать. Phase 2 — собственно маркетинг + launch.

**Целевая метрика:** к концу Sales Sprint работающая система которая:
- Принимает оплату через YooKassa
- Активирует Pro лицензию в desktop приложении по ключу с email
- Показывает юзеру web-кабинет с балансом, расходом, устройствами, чеками
- Считает soft caps и не пропускает abuse
- Собирает анонимную телеметрию для будущих product decisions
- Имеет лендинг на optimyzer.pro
- Имеет первых платящих юзеров (метрика first revenue, не количество)

---

## Структура спринта

Sales Sprint разбит на **две фазы** с явным gating: Phase 2 НЕ начинается пока Phase 1 не закрыта.

### Phase 1 — Infrastructure (4-6 недель)

Backend для auth, billing, accounts. Web-кабинет на React. License activation в desktop. Soft caps. Telemetry.

### Phase 2 — Marketing & Launch (2-3 недели)

Лендинг deployment + DNS. Onboarding в desktop. Статья на Инфостарте. Demo videos. Outreach. Support page.

### После закрытия Sales Sprint — Market Validation (2-3 недели)

Не входит в спринт. Сергей оценивает реальные метрики: conversion Free→Pro, retention, какие features используются по телеметрии. На основе данных принимается решение про Sprint 6 (восстановление QueryAnalyzer) или другие приоритеты.

---

# PHASE 1 — INFRASTRUCTURE

## Глобальные технические решения для Phase 1

### Стек backend

| Компонент | Технология | Обоснование |
|---|---|---|
| Backend язык | Python 3.11+ | Уже используется в проекте |
| Web framework | FastAPI | Async, OpenAPI auto-docs, type hints |
| ORM | SQLAlchemy 2.x | Стандарт для Python |
| База данных | PostgreSQL 15+ | Производственная БД (НЕ SQLite в проде — нужна одновременная запись из API + workers) |
| Auth | Yandex OAuth 2.0 | Единственный способ входа |
| Billing | YooKassa | RUB-платежи + чеки самозанятого |
| Hosting backend | VDS (Selectel / Beget / RuVDS) | Российский провайдер для compliance |
| Hosting web-кабинет | тот же VDS, nginx | Subdomain account.optimyzer.pro |
| Hosting лендинг | static, отдельный subdomain | optimyzer.pro |
| SSL | Let's Encrypt | Бесплатно, автоматическое продление |
| Async tasks | None пока (cron + APScheduler) | Не вводим Celery до реальной необходимости |
| Логи | Stdout + journald | Минимум, потом можно добавить ELK |

### Где живёт backend

**Отдельный новый Python проект** в репозитории. Не смешиваем с существующим backend (который только для desktop).

Структура:

```
D:\1C-Optimyzer\
├── backend/              # СУЩЕСТВУЮЩИЙ — для desktop приложения (DuckDB, парсер ТЖ)
├── frontend/             # СУЩЕСТВУЮЩИЙ — React UI desktop приложения
├── server/               # НОВОЕ — backend для auth/billing/cabinet
│   ├── api/              # FastAPI app
│   ├── models/           # SQLAlchemy models
│   ├── services/         # business logic
│   ├── migrations/       # Alembic
│   ├── tests/
│   └── pyproject.toml
├── cabinet/              # НОВОЕ — React app для web-кабинета
│   ├── src/
│   ├── public/
│   └── package.json
├── landing/              # НОВОЕ — статика лендинга (копия DESIGN_CONCEPT/)
│   ├── index.html
│   ├── styles.css
│   └── assets/
└── docs/
    └── sales_sprint/     # документация Sales Sprint
```

**Принцип:** существующий backend и frontend не трогаем. server / cabinet / landing — отдельные сущности которые могут деплоиться независимо.

### Domain & DNS

- `optimyzer.pro` → лендинг (Cloudflare CDN или просто nginx)
- `account.optimyzer.pro` → web-кабинет (nginx → React build)
- `api.optimyzer.pro` → backend API
- `optimyzer.pro/download` → редирект на GitHub Releases (или внутренний CDN для бинарей)

DNS настраивается в registrar где куплен domain. SSL — Let's Encrypt на nginx.

### Безопасность

- Все запросы к API только HTTPS
- JWT-токены с коротким TTL (15 минут) + refresh tokens (30 дней)
- Rate limiting на API (slowapi или nginx-level)
- Anti-CSRF на web-кабинете
- Sensitive данные (Yandex tokens, YooKassa keys) — в env vars, не в коде
- Логи НЕ должны содержать токены или платёжные данные
- HTTPS-only cookies для web-кабинета

---

## Phase 1.1 — Yandex OAuth integration

### Что делаем

Реализуем вход в web-кабинет и активацию desktop приложения через Yandex OAuth 2.0.

**Flow для web-кабинета:**

1. Юзер заходит на `account.optimyzer.pro`
2. Кликает «Войти через Yandex»
3. Редирект на `https://oauth.yandex.ru/authorize?response_type=code&client_id=...`
4. Юзер авторизуется в Yandex (если не авторизован) и подтверждает доступ
5. Yandex редиректит обратно: `account.optimyzer.pro/oauth/callback?code=...`
6. Backend меняет code на access_token через `https://oauth.yandex.ru/token`
7. Backend получает профиль юзера через `https://login.yandex.ru/info`
8. Создаёт/обновляет запись в БД (users table)
9. Генерирует наш JWT и устанавливает в httpOnly cookie
10. Редирект на dashboard web-кабинета

**Flow для desktop активации:**

1. Юзер в desktop приложении: Settings → Аккаунт → «Перейти на Pro»
2. Открывается браузер на `optimyzer.pro/pricing`
3. Юзер покупает Pro через YooKassa (см. Phase 1.4)
4. На email приходит **activation key** (формат `OPTM-XXXX-XXXX-XXXX-XXXX`)
5. Юзер в desktop: Settings → Аккаунт → «Уже купили Pro? Введите ключ активации»
6. Вводит ключ, нажимает «Активировать»
7. Desktop POST'ит ключ на `api.optimyzer.pro/v1/license/activate` с device fingerprint
8. Backend валидирует ключ, привязывает к user_id и device fingerprint, возвращает JWT
9. Desktop сохраняет JWT в OS keychain (Tauri secure storage)
10. Pro активирован, юзер видит свой email и статус в Settings

### Конкретные шаги

**Шаг 1.** Зарегистрировать приложение в Yandex OAuth:
- Перейти на https://oauth.yandex.ru/client/new
- Создать приложение «Optimyzer»
- Тип: «Веб-сервисы»
- Redirect URI: `https://account.optimyzer.pro/oauth/callback`
- Разрешения: `login:email`, `login:info`
- Получить `client_id` и `client_secret`
- Сохранить в env vars сервера (НЕ в коде, НЕ в git)

**Шаг 2.** Реализовать в `server/api/` endpoints:
- `GET /v1/auth/yandex/login` → redirect на oauth.yandex.ru
- `GET /v1/auth/yandex/callback` → обмен code на token, создание user, set cookie
- `POST /v1/auth/logout` → invalidate refresh token, clear cookie
- `GET /v1/auth/me` → текущий юзер по cookie
- `POST /v1/auth/refresh` → обновление access token по refresh

**Шаг 3.** Реализовать SQLAlchemy модели:

```python
class User(Base):
    id: UUID (primary key)
    yandex_id: str (unique)
    email: str (indexed)
    display_name: str
    created_at: datetime
    last_login_at: datetime
    is_active: bool (default True)

class RefreshToken(Base):
    id: UUID
    user_id: UUID (FK)
    token_hash: str (хешируем, не plain)
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | null
```

**Шаг 4.** Тесты:
- Unit test для обмена code на token (mock httpx)
- Unit test для создания нового юзера
- Unit test для existing юзера (обновление last_login_at)
- Integration test с тестовым Yandex sandbox (если доступен) или e2e ручной

**Acceptance criteria Phase 1.1:**

- [ ] Юзер может залогиниться в `account.optimyzer.pro` через Yandex
- [ ] После логина видит свой email и имя из Yandex profile
- [ ] Logout очищает cookie и invalidates refresh token
- [ ] Refresh tokens корректно ротейтятся
- [ ] При попытке использовать revoked refresh token — 401
- [ ] Юзер не может попасть на dashboard без auth (редирект на login)
- [ ] Все email из Yandex сохраняются в lowercase

**Stop rule:** перед началом Phase 1.2 — продемонстрировать Сергею работающий OAuth flow на тестовом сервере. Без этого не двигаемся.

---

## Phase 1.2 — Backend API: subscriptions, credits, devices, usage

### Что делаем

Реализуем core business logic API для управления подпиской, кредитами, устройствами и трекингом использования.

### Модели данных

```python
class Subscription(Base):
    id: UUID
    user_id: UUID (FK, unique)  # один user = одна активная подписка
    plan: Enum["free", "pro"]   # сейчас 2, может расшириться
    status: Enum["active", "cancelled", "expired"]
    starts_at: datetime
    ends_at: datetime           # дата следующего billing'а
    auto_renew: bool
    early_adopter: bool         # True если зарегистрирован до даты-X (защищает цену)
    price_locked_at: int        # цена в копейках, зафиксирована при покупке
    yookassa_subscription_id: str | null
    created_at: datetime
    updated_at: datetime

class Credits(Base):
    id: UUID
    user_id: UUID (FK)
    package: Enum["mini", "standard", "bulk"]
    operations_total: int        # 30 / 100 / 300
    operations_used: int
    operations_remaining: int    # computed: total - used
    purchased_at: datetime
    expires_at: datetime         # purchased_at + 30 days
    is_active: bool              # False когда expired или fully consumed

class Device(Base):
    id: UUID
    user_id: UUID (FK)
    fingerprint: str             # hardware-based, SHA256 от machine_id+os+cpu
    name: str                    # автоматически из OS или введённое юзером
    platform: Enum["windows", "macos", "linux"]
    app_version: str             # "v0.5.0"
    last_seen_at: datetime
    last_ip: str (masked: "95.×××.×××.42")
    activated_at: datetime
    is_active: bool              # False когда юзер деактивировал

class Usage(Base):
    id: UUID
    user_id: UUID (FK)
    device_id: UUID (FK)
    operation_type: Enum["ai_explanation", "ai_deadlock_explanation", "ai_rewrite", ...]
    archive_hash: str | null     # для AI cache lookup
    timestamp: datetime
    cost_credits: int            # сколько списано (1 для simple explain, 2 для complex)
    billed_against: Enum["pro_quota", "credits_balance", "free_quota"]
    success: bool
    ai_tokens_input: int | null
    ai_tokens_output: int | null
    ai_cost_usd: float | null    # для нашего расчёта маржи
```

### API Endpoints

**Subscriptions:**
- `GET /v1/subscriptions/current` → текущая подписка юзера
- `POST /v1/subscriptions/cancel` → отмена авто-продления
- `POST /v1/subscriptions/reactivate` → возврат к авто-продлению

**Credits:**
- `GET /v1/credits/balance` → суммарный баланс по всем активным пакетам
- `GET /v1/credits/history` → история покупок
- `POST /v1/credits/purchase` → инициирует покупку (создаёт YooKassa payment)

**Devices:**
- `GET /v1/devices` → список активных устройств
- `POST /v1/devices/activate` → активация по license key (см. Phase 1.5)
- `POST /v1/devices/:id/deactivate` → деактивация
- `POST /v1/devices/:id/heartbeat` → desktop стучит каждые 24ч, обновляет last_seen_at

**Usage:**
- `POST /v1/usage/track` → desktop сообщает о выполненной AI операции
- `GET /v1/usage/summary` → summary за месяц для cabinet
- `GET /v1/usage/check` → проверка можно ли выполнить ещё одну операцию (см. Phase 1.6)

**Все endpoints требуют JWT auth.** Без токена — 401.

### Business logic — purchase flow

Когда юзер покупает Credits Mini (299 ₽) через web-кабинет:

1. Frontend cabinet → `POST /v1/credits/purchase {package: "mini"}`
2. Backend создаёт payment в YooKassa:
   - amount: 299.00 RUB
   - description: "Optimyzer Credits Mini · 30 AI операций"
   - metadata: {user_id, package: "mini"}
   - return_url: `account.optimyzer.pro/credits?status=pending`
3. Backend сохраняет запись в `Payment` table со status="pending"
4. Возвращает frontend'у `confirmation_url`
5. Frontend redirect на YooKassa checkout
6. Юзер оплачивает
7. YooKassa отправляет webhook на `api.optimyzer.pro/v1/webhooks/yookassa`
8. Backend верифицирует webhook signature
9. Обновляет Payment.status="succeeded"
10. Создаёт запись Credits с operations_remaining=30, expires_at=now+30days
11. Отправляет email юзеру: «Credits Mini активированы, баланс 30 операций»

Аналогично для Pro подписки — но через recurring YooKassa subscription.

### Acceptance criteria Phase 1.2

- [ ] Все модели созданы, Alembic migrations работают
- [ ] Все endpoints возвращают корректные данные
- [ ] Unit tests покрывают business logic (cancel, reactivate, balance calculation)
- [ ] Integration tests с YooKassa sandbox для purchase flow
- [ ] Endpoint `/v1/usage/check` корректно отвечает для Free / Pro / Credits сценариев
- [ ] Concurrent writes в Usage не дают race condition (transaction lock)
- [ ] OpenAPI docs автогенерированы и доступны на `api.optimyzer.pro/docs`

**Stop rule:** перед началом Phase 1.3 — Postman/Insomnia collection всех endpoints + демонстрация Сергею. Сценарий: создать тестового юзера, купить Credits Mini в sandbox YooKassa, потратить 1 кредит через manual API call, увидеть баланс 29.

---

## Phase 1.3 — Web-кабинет (React app)

### Что делаем

Реализуем web-кабинет на React по готовому дизайну в `DESIGN_CONCEPT/account.html`. Деплой на `account.optimyzer.pro`.

### Технический стек

- React 18 + TypeScript
- Vite для build
- React Router 6 для routing
- TanStack Query для server state
- Zustand для local state (если нужен)
- recharts для графиков (уже использованы в dashboard mockup)
- Стили — Tailwind или vanilla CSS (на выбор), но **обязательно** использовать дизайн-токены из `DESIGN_CONCEPT/styles.css` (CSS variables --accent, --fg, etc)
- Шрифты Manrope + JetBrains Mono из Google Fonts

### Структура

```
cabinet/
├── src/
│   ├── pages/
│   │   ├── Login.tsx           # Yandex OAuth button
│   │   ├── Overview.tsx        # главная — статус, метрики, последние сессии
│   │   ├── Subscription.tsx    # управление подпиской
│   │   ├── Credits.tsx         # баланс + покупка
│   │   ├── Devices.tsx         # список устройств
│   │   ├── Payments.tsx        # история платежей
│   │   ├── Usage.tsx           # графики использования
│   │   └── Settings.tsx        # профиль, уведомления
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── charts/
│   │   │   ├── UsageLineChart.tsx
│   │   │   ├── DonutDistribution.tsx
│   │   │   └── ArchivesBarChart.tsx
│   │   └── ui/                 # Button, Card, Pill, Toggle, ...
│   ├── api/
│   │   ├── client.ts           # axios с auth interceptor
│   │   └── endpoints/          # типизированные обёртки
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useSubscription.ts
│   │   └── ...
│   └── App.tsx
└── package.json
```

### Что должно быть реализовано

Все 7 страниц web-кабинета из `DESIGN_CONCEPT/account.html` (Overview, Subscription, Credits, Devices, Payments, Usage, Settings) + Login screen с Yandex OAuth.

Каждая страница тянет данные через TanStack Query из backend API. Mock-data из дизайна заменяется на реальные запросы.

### Особое внимание

**Overview страница** — главная. Должна загружаться **быстро** (< 500ms perceived). Использовать React Suspense + skeleton states. Не делать N+1 запросов — один endpoint `/v1/dashboard/summary` возвращает всё нужное для главной.

**Графики на Usage странице** — данные могут быть тяжёлыми. Считать на сервере, передавать готовые arrays. Не делать transformations на клиенте.

**Settings страница** — Email уведомления toggle'ы сохраняются через `PATCH /v1/users/me/preferences`. Telegram bot connection — через deep link `https://t.me/optimyzer_bot?start=<one_time_token>`.

### Acceptance criteria Phase 1.3

- [ ] Все 7 страниц + Login работают и подтягивают реальные данные
- [ ] Mobile responsive (test на 360px, 768px, 1280px)
- [ ] Lighthouse score: Performance > 80, Accessibility > 90
- [ ] Все формы (отмена подписки, изменение email уведомлений) работают
- [ ] Custom toggle для авто-продления работает с optimistic update
- [ ] Графики на Usage загружают данные за выбранный период (последние 30 дней default)
- [ ] Logout кнопка работает, после неё все запросы возвращают 401, происходит редирект на /login
- [ ] Production build < 500KB gzipped

**Stop rule:** перед началом Phase 1.4 — деплой web-кабинета на staging `account-staging.optimyzer.pro`, демонстрация Сергею.

---

## Phase 1.4 — YooKassa integration

### Что делаем

Интегрируем YooKassa для приёма платежей: recurring подписки (Pro 2 990 ₽/мес) и one-time платежи (Credits 299/990/2490 ₽).

### Подготовка

**Сергей делает (НЕ Claude Code):**
1. Регистрируется на yookassa.ru
2. Привязывает счёт самозанятого (Сбер / Альфа / Райффайзен)
3. Получает `shop_id` и `secret_key` для production + sandbox
4. Настраивает чеки: автоматическое формирование при платеже, отправка через email юзеру + в «Мой налог» (54-ФЗ)
5. Передаёт Claude Code: sandbox credentials для разработки

### Recurring subscription для Pro

YooKassa поддерживает рекуррентные платежи через механизм «autopayments»:

1. Первый платёж юзера — YooKassa сохраняет привязку карты (`payment_method_id`)
2. Каждый месяц мы сами через API создаём новый платёж с этим payment_method_id (он списывается без подтверждения от юзера)
3. Юзер может отменить в любой момент → удаляем payment_method_id, autopayments прекращаются

**Cron job в backend** (APScheduler):
- Каждый день в 03:00 МСК проверяем все active Pro subscriptions с ends_at == today
- Для каждой — создаём новый платёж через YooKassa API
- Если успех — обновляем ends_at = ends_at + 30 days
- Если неуспех (карта истекла, недостаточно средств) — переводим в "past_due", шлём email юзеру, через 7 дней переводим в "cancelled"

### One-time для Credits

Проще — обычный single-payment без сохранения карты:
1. Frontend → POST /v1/credits/purchase {package: "mini"}
2. Backend создаёт YooKassa payment, возвращает confirmation_url
3. Юзер платит через checkout YooKassa
4. Webhook от YooKassa → backend создаёт Credits запись

### Webhook handling

Endpoint `POST /v1/webhooks/yookassa`:
- Верифицирует signature (HMAC-SHA256 с secret_key)
- Парсит event (`payment.succeeded`, `payment.canceled`, `refund.succeeded`)
- Обновляет соответствующие записи в БД
- Возвращает 200 OK быстро (< 1 секунды), heavy work — в background

**Idempotency:** YooKassa может прислать webhook несколько раз. У каждого payment есть `idempotency_key` — наш backend хранит обработанные ключи (Redis или таблица в БД), при повторе возвращает 200 без действий.

### Receipts (чеки 54-ФЗ)

При создании платежа в YooKassa передаём `receipt`:
```json
{
  "customer": {"email": "user@yandex.ru"},
  "items": [{
    "description": "Optimyzer Pro · подписка на 1 месяц",
    "quantity": "1",
    "amount": {"value": "2990.00", "currency": "RUB"},
    "vat_code": 1,  // 1 — без НДС (для самозанятых)
    "payment_subject": "service",
    "payment_mode": "full_prepayment"
  }]
}
```

YooKassa сама формирует чек и отправляет на email юзера + регистрирует в «Мой налог».

### Refunds

В web-кабинете на странице Subscription есть кнопка «Отменить подписку». Отмена = выключение auto_renew. Доступ остаётся до ends_at.

Если юзер хочет частичный refund за неиспользованные дни — это **manual process**: пишет на support@optimyzer.pro, Сергей через YooKassa admin panel оформляет refund вручную. Не автоматизируем в Sales Sprint (low priority).

### Acceptance criteria Phase 1.4

- [ ] Sandbox: тестовый юзер покупает Pro, в YooKassa sandbox видна транзакция
- [ ] Webhook от YooKassa приходит, обрабатывается, юзер видит Pro в кабинете
- [ ] Cron job для recurring работает (тест: руками выставить ends_at = вчера, дождаться cron, проверить новый платёж)
- [ ] Webhook idempotent — повторная отправка не создаёт дубликат Credits
- [ ] Чек 54-ФЗ генерируется и отправляется на email юзера
- [ ] Отмена подписки в кабинете → auto_renew=false → recurring не выполняется
- [ ] Production credentials YooKassa загружены в env vars сервера

**Stop rule:** перед началом Phase 1.5 — Сергей делает первую тестовую покупку через **production** YooKassa за реальные ~10 ₽ (минимальная сумма), проверяет: пришёл чек на email, появилось в «Мой налог», деньги пришли на счёт самозанятого. Если всё ОК — двигаемся дальше.

---

## Phase 1.5 — License activation в desktop приложении

### Что делаем

Добавляем в desktop приложение flow активации Pro лицензии и graceful degradation при отсутствии connectivity.

### Что меняется в desktop

**Settings dialog (тот что уже есть после UI Cleanup):**

Появляется вкладка «Аккаунт» рядом с «О программе». Дизайн уже готов в `DESIGN_CONCEPT/desktop-settings.html` (Free и Pro состояния).

**Free состояние (если лицензия не активирована):**
- Бейдж «Free · v0.5.0»
- Текст «Бесплатная версия. У вас есть полный доступ к анализу. AI-объяснений: 5 в месяц.»
- Прогресс бар «3 / 5 использовано в этом месяце»
- Кнопка primary «Перейти на Pro» → открывает `optimyzer.pro/pricing` в браузере
- Скрытое поле «Уже купили Pro? Введите ключ активации» → разворачивается по клику

**Pro состояние (если активировано):**
- Аватар + имя + email из аккаунта
- Бейдж «PRO»
- Статус «Активирован»
- Поля: Тариф / Подписка до / Цена / AI в этом месяце / Кредитов / Устройств
- Кнопка primary «Открыть личный кабинет» → открывает `account.optimyzer.pro` с auto-login через SSO token
- Кнопка secondary «Купить кредиты» → открывает `account.optimyzer.pro/credits`

### Activation flow

Когда юзер вводит activation key:

1. Desktop собирает device fingerprint:
```python
import hashlib, platform, uuid
fingerprint_input = f"{platform.system()}_{platform.machine()}_{uuid.getnode()}"
fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()
```

2. POST на `api.optimyzer.pro/v1/license/activate`:
```json
{
  "key": "OPTM-XXXX-XXXX-XXXX-XXXX",
  "fingerprint": "abc123...",
  "device_name": "MacBook Pro",  // из OS
  "platform": "macos",
  "app_version": "v0.5.0"
}
```

3. Backend валидирует:
   - Key существует и не использован
   - Key относится к user'у с активной Pro подпиской
   - Лимит устройств не превышен (5 для Pro)
   - Если превышен — возвращает 409 + список текущих устройств, юзер выбирает которое деактивировать

4. Backend создаёт запись в `Device`, генерирует device-specific JWT (long-lived, 90 дней), возвращает:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {"email": "user@yandex.ru", "name": "Сергей"},
  "subscription": {"plan": "pro", "ends_at": "2026-06-25", ...},
  "device": {"id": "uuid", "name": "MacBook Pro"}
}
```

5. Desktop сохраняет токены в OS keychain через Tauri secure storage (НЕ в plain файл)

6. Желаемая UX: после ввода ключа моментально показывается Pro состояние Settings, никакого «перезапустите приложение»

### Heartbeat & graceful degradation

**Каждые 24 часа** desktop стучит на `api.optimyzer.pro/v1/devices/heartbeat`:
- Передаёт device_id и access_token
- Получает: текущий статус подписки, остаток AI квоты, баланс кредитов

Если backend недоступен:
- **До 7 дней** — desktop работает в Pro режиме на основе cached данных
- **После 7 дней** — desktop переходит в Free режим (важное предупреждение: «Не удалось проверить подписку 7+ дней. Перешли в Free режим. Подключитесь к интернету и перезапустите приложение.»)
- **Никогда не блокировать полностью** — анализ архивов работает всегда, даже если ничего не активировано

### Soft caps в desktop

Когда юзер нажимает «Объяснить через AI» на anatomy view:
1. Desktop проверяет local cache (`data/explainer_cache.db`) — если ответ есть, возвращает мгновенно
2. Если нет — desktop POST'ит на `api.optimyzer.pro/v1/usage/check`
3. Backend проверяет: есть ли квота / кредиты / soft cap
4. Возвращает: `{"allowed": true}` или `{"allowed": false, "reason": "free_limit_exceeded", "options": ["upgrade", "buy_credits"]}`
5. Если allowed — desktop выполняет AI запрос, кешит результат, отправляет `POST /v1/usage/track`
6. Если denied — показывает modal с CTA «Перейти на Pro» / «Купить кредиты» / «Вернуться»

Логика soft caps:
- **Free:** 5 AI explanation/мес. После 5 — denied до начала следующего месяца. Можно купить Credits для разовых.
- **Pro:** unlimited до 1000/мес. После 1000 — warning «Превышен soft cap, обратитесь в поддержку если это нормальная нагрузка».
- **Credits:** каждая операция списывает 1 credit, при остатке 0 — denied (если нет активной Pro).

### Acceptance criteria Phase 1.5

- [ ] Settings → Аккаунт вкладка работает в Free и Pro состояниях по дизайну
- [ ] Activation flow работает: ввод ключа → активация → Pro состояние
- [ ] Лимит устройств enforced (попытка активировать 6-е → 409 с выбором)
- [ ] Heartbeat работает, обновляет статус
- [ ] Graceful degradation: при отключённом backend Pro работает 7 дней, потом Free
- [ ] Soft cap для Free enforced: после 5 AI — modal с CTA
- [ ] Кеш AI ответов работает (повторный запрос не списывает квоту)
- [ ] Кнопка «Открыть личный кабинет» открывает браузер с auto-login

**Stop rule:** перед началом Phase 1.6 — Сергей делает end-to-end test: покупает Pro на staging, получает activation key на email, вводит в desktop, проверяет Pro работает, делает 1000+ AI запросов (или симулирует через manual API calls) чтобы убедиться что soft cap срабатывает.

---

## Phase 1.6 — Telemetry collector

### Что делаем

Собираем анонимную телеметрию использования продукта для product decisions через 2-3 недели после launch.

### Что собирается

**Категория 1: технические метрики (помогают понять scale данных)**
- Размер загружаемого архива (МБ)
- Количество событий после парсинга
- Время парсинга
- Распределение типов событий (DBMSSQL count, EXCP count, etc)
- Версия 1С платформы (если есть в архиве)
- Тип конфигурации (БП, УТ, ЕРП — если есть в метаданных)
- ОС и версия desktop приложения

**Категория 2: behavior метрики (что юзер реально использует)**
- Какой screen посещён (Operations / Anatomy / Slow Queries / Events / etc)
- Сколько раз кликнул AI Explainer
- Сколько раз использовал SQL Console
- Использовал ли Cross-filtering
- Сколько раз открывал Сравнение архивов (Pro)
- Длительность сессии в продукте
- Через сколько дней возвращается (retention)

**Категория 3: conversion метрики**
- Видел ли paywall modal (вошёл в денёный сценарий)
- Кликнул ли «Перейти на Pro» после paywall
- Сколько AI операций до первой покупки

### Что НЕ собирается (privacy)

- Содержимое запросов / SQL текст
- Имена баз 1С, имена пользователей 1С
- Контексты операций (Context поле в ТЖ)
- Содержимое EXCP сообщений
- AI ответы (содержательная часть)
- IP адреса (только страна / регион по геолоку)

### Технически

**Desktop приложение:**
- Локальный buffer событий в SQLite (`data/telemetry_buffer.db`)
- Каждые 5 минут или при выходе из приложения — flush на backend
- Endpoint `POST /v1/telemetry/batch` с anonymous device_id (тот же fingerprint, но в случае Free юзера не привязан к user_id)
- Если backend недоступен — события остаются в buffer, попытка retry через час
- **Privacy first toggle** в Settings → Аккаунт: «Отправлять анонимную статистику» (default: включено для Pro, opt-in для Free)

**Backend:**
- Endpoint `POST /v1/telemetry/batch` принимает array событий
- Сохраняет в `TelemetryEvent` table
- НЕ привязывает к user_id если юзер Free (только anonymous device_id)
- НЕ хранит дольше 90 дней (auto-cleanup через cron)
- Aggregated metrics доступны Сергею через admin endpoint `GET /v1/admin/telemetry/summary` (Basic auth, только Сергей)

**На лендинге:**
- В FAQ или в Settings desktop — ссылка «Какую статистику мы собираем» с детальным списком (чтобы было прозрачно)

### Acceptance criteria Phase 1.6

- [ ] Telemetry events накапливаются в desktop buffer
- [ ] Flush на backend каждые 5 минут работает
- [ ] Privacy toggle в Settings работает (если выключен — buffer не отправляется)
- [ ] Admin endpoint показывает summary: top screens, AI usage distribution, archive sizes histogram, retention cohorts
- [ ] Все события >90 дней удаляются автоматически
- [ ] При отключённом backend события не теряются (max 1000 в buffer)
- [ ] Документация для юзеров: список что собирается / не собирается на support page

**Stop rule:** перед началом Phase 2 — Сергей открывает admin endpoint и видит реальные telemetry данные со своего тестового использования.

---

## Phase 1 — итоговый Definition of Done

Перед переходом в Phase 2 должны быть выполнены ВСЕ:

- [ ] Yandex OAuth работает на production
- [ ] Web-кабинет deployed на `account.optimyzer.pro`, 7 страниц + Login работают
- [ ] Backend API deployed на `api.optimyzer.pro`, OpenAPI docs доступны
- [ ] YooKassa в production режиме принимает платежи, чеки 54-ФЗ генерируются
- [ ] Desktop приложение активируется через license key, работает Pro режим
- [ ] Soft caps срабатывают корректно для Free / Pro / Credits сценариев
- [ ] Telemetry собирается и доступна Сергею
- [ ] Все security checks: HTTPS, JWT, anti-CSRF, rate limiting
- [ ] Tests: backend 200+, frontend 50+, e2e smoke на основные flows
- [ ] DESIGN_CONCEPT/* применён к live версиям (cabinet выглядит как mockup)
- [ ] Документация в `docs/sales_sprint/PHASE_1_REPORT.md`

**Если хотя бы одно не выполнено — НЕ начинать Phase 2.**

---

# PHASE 2 — MARKETING & LAUNCH

## Что делаем в Phase 2

Доводим продукт до launch'а: лендинг на production, onboarding в desktop, контент для маркетинга (статья, видео), outreach plan, support page.

---

## Phase 2.1 — Лендинг deployment

### Что делаем

Развёртываем готовый лендинг из `DESIGN_CONCEPT/index.html` на `optimyzer.pro`.

### Конкретные шаги

**Шаг 1.** Скопировать `DESIGN_CONCEPT/` → `landing/` (отдельная папка для деплоя, оригинал остаётся как reference).

**Шаг 2.** Заменить mock-ссылки на реальные:
- «Скачать бесплатно» → ссылка на GitHub Releases (`/releases/latest` или прямые binary URLs)
- «Войти» → `account.optimyzer.pro`
- «Купить Pro» → `account.optimyzer.pro/pricing` (или прямо checkout через YooKassa)
- «Документация» → `optimyzer.pro/docs/` (см. Phase 2.6)
- «GitHub» → `https://github.com/anymasoft/1c-optimyzer`
- «Связаться» → mailto:hello@optimyzer.pro (или Telegram contact)

**Шаг 3.** Настроить nginx на VDS:
```nginx
server {
    listen 443 ssl http2;
    server_name optimyzer.pro;
    root /var/www/optimyzer/landing;
    index index.html;

    # SSL via Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/optimyzer.pro/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/optimyzer.pro/privkey.pem;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Download redirect
    location /download {
        return 302 https://github.com/anymasoft/1c-optimyzer/releases/latest;
    }
}
```

**Шаг 4.** SEO базовый:
- `<meta>` теги (description, og:image, twitter:card)
- favicon из `assets/favicon.svg`
- og-image.png для соцсетей
- `robots.txt` allow all
- `sitemap.xml` с главными страницами

**Шаг 5.** Analytics:
- Yandex.Metrika (для российской аудитории)
- НЕ Google Analytics (заблокирован у части юзеров в РФ)
- Цели: «Скачать», «Перейти на Pro», «Связаться»

### Acceptance criteria Phase 2.1

- [ ] `https://optimyzer.pro` открывается, SSL валиден
- [ ] Все секции рендерятся, typewriter работает
- [ ] Скриншоты загружаются, не тормозят
- [ ] Mobile responsive проверен на iPhone и Android
- [ ] Lighthouse score: Performance > 85, SEO > 90
- [ ] Yandex.Metrika установлена, цели работают
- [ ] «Скачать бесплатно» редиректит на правильный GitHub Release
- [ ] og-image корректно показывается при шаринге в Telegram / VK

---

## Phase 2.2 — Onboarding flow в desktop

### Что делаем

При первом запуске desktop приложения показываем юзеру как начать. Цель — за 5 минут довести до «aha moment».

### Сценарий

При первом запуске (определяется по отсутствию `data/.first_run_completed` flag):

**Step 1: Welcome modal**
- «Привет! Optimyzer анализирует архивы технологического журнала 1С и объясняет проблемы через AI.»
- Кнопка «Начать с примера» (открывает demo архив) или «У меня есть свой архив»

**Step 2 (если demo):** загрузить sample архив
- Bundled в установщик: `samples/demo-archive.zip` (~200 МБ, реальный обезличенный архив с дедлоками и медленными запросами)
- Парсится автоматически, показывается прогресс
- После парсинга — toast «Готово. Это демо архив с примером проблем производительности 1С:ERP.»

**Step 3: Interactive tour (3-5 шагов)**

После загрузки архива — overlay tour:

1. **«Это топ проблем»** — указывает на первую строку в Operations с красными значениями. «Видите Σ ms 36 секунд и 63 EXCP? Это аномалии. Кликните на строку чтобы развернуть.»

2. **«Анатомия операции»** — после клика. «Здесь все детали проблемы: timeline, top SQL, exceptions. Чтобы получить объяснение от AI — кликните «Объяснить через AI» сверху.»

3. **«AI объяснение»** — после клика на AI кнопку. «Claude прочитал данные и написал на русском: что произошло, почему, что делать. Это и есть главная фишка Optimyzer.»

4. **«Лимит Free версии»** — после первого AI. «У вас Free версия — 5 AI объяснений в месяц. Для регулярной работы есть Pro подписка за 2 990 ₽/мес.»

5. **«Ваш архив»** — последний шаг. «Теперь загрузите свой архив через TopBar → "Загрузить архив". Demo архив можно удалить в любой момент.»

Tour можно пропустить в любой момент. Не показывается повторно если уже завершён.

### Empty state когда архива нет

Если юзер удалил demo архив и не загрузил свой — на главном экране показывается:

```
[иконка папки]
Архив с логами ТЖ не загружен

Перетащите папку с .log файлами сюда
или нажмите [Загрузить архив] в верхней панели

[Открыть демо архив]   [Что такое ТЖ?]
```

Кнопка «Что такое ТЖ?» открывает короткую doc страницу на лендинге с инструкцией по настройке logcfg.xml.

### Acceptance criteria Phase 2.2

- [ ] При первом запуске показывается Welcome modal
- [ ] Sample демо архив включён в bundle и парсится корректно
- [ ] Interactive tour работает, можно пропустить
- [ ] Tour не показывается повторно после завершения
- [ ] Empty state с CTA срабатывает когда архива нет
- [ ] «Что такое ТЖ?» открывает правильную doc страницу

---

## Phase 2.3 — Статья на Инфостарте

### Что делаем

Пишем и публикуем статью на Инфостарте — главный канал привлечения первых пользователей. Angle: «Если парсил ТЖ через gawk-скрипты — посмотри как у нас».

### Структура статьи

**Заголовок:** «Анализ ТЖ 1С без bash-скриптов: SQL поверх архива + AI объясняет проблемы»

**Подзаголовок:** «Как мы заменили pipeline `cat | grep | sed | gawk` универсальным SQL-движком и Claude в качестве AI-эксперта»

### Структура (8 разделов)

1. **Знакомая боль (200 слов)**
   - Открыть архив 12 ГБ, написать pipeline, три часа подбирать regex, переписать под новый вопрос
   - Параллель с курсом 1С:Эксперт (где этим и учат)
   - Скриншот примера bash pipeline из курса

2. **Что мы сделали (300 слов)**
   - Концептуально то же самое: парсер ТЖ, нормализация контекстов, агрегаты
   - Но вместо fixed pipeline — DuckDB-индекс + произвольный SQL
   - Скриншот SQL Console продукта

3. **Конкретный пример (400 слов)**
   - Тот же запрос «топ-1000 контекстов по avg duration» в виде:
     - bash скрипт (9 строк) — оригинал из курса
     - SQL в Optimyzer (4 строки) — наша версия
   - Видно что концепция одна, реализация компактнее

4. **AI объясняет проблемы (300 слов)**
   - Скриншот Анатомии операции с AI Explainer
   - Цитата из реального AI ответа: «использование исключений как управляющей логики... 96% всех затрат...»
   - Главная фишка: на курсе учат **интерпретировать**, у нас AI интерпретирует автоматически

5. **Реальный кейс (500 слов)**
   - Конкретная история с цифрами: «Архив 1.66 ГБ, нашли проблему за 3 минуты»
   - Скриншоты: Operations → Anatomy → AI Explainer
   - До оптимизации: 36 сек среднее время операции
   - После: 4 сек (ускорение 9×)

6. **Anatomy дедлока (200 слов)**
   - AI объясняет дедлоки на русском
   - Скриншот DeadlockAnatomy с lock graph
   - Не нужно курса 1С:Эксперт чтобы понять дедлок

7. **Кому это подходит / не подходит (200 слов)**
   - **Подходит:** middle 1С-разработчик без сертификата 1С:Эксперт, senior без КИП-лицензии, разовые расследования
   - **Не подходит:** continuous monitoring продакшена (пока offline-only), анализ памяти, крупные корпорации с КИП

8. **Цена и где скачать (100 слов)**
   - Free для разовых проверок
   - Pro 2 990 ₽/мес для регулярной работы
   - Ссылка на `optimyzer.pro`
   - Ссылка на GitHub (продукт open source / source available?)

### Тон

- Технический, конкретный — код, числа, реальные команды
- Без маркетинг-speak («революционный AI инструмент» запрещено)
- С самоиронией про разработку («мы сами парсили ТЖ через gawk, надоело — сделали это»)
- БЕЗ агрессии против ЦУПа («младший брат», не «убийца»)
- БЕЗ упоминания того что QueryAnalyzer временно отсутствует — фокус на том что есть

### Где публиковать

1. **Инфостарт** — основная площадка. Категория «Технологический журнал 1С».
2. **Хабр** — версия адаптированная под более широкую аудиторию (меньше специфики 1С)
3. **Mista** — кросс-пост в форум 1С
4. **Telegram-каналы 1С** (см. Phase 2.5) — анонс со ссылкой на статью

### Acceptance criteria Phase 2.3

- [ ] Статья 2000-2500 слов написана и вычитана
- [ ] 8 скриншотов вставлены и подписаны
- [ ] Опубликована на Инфостарте, набрала комментарии
- [ ] Кросс-пост на Хабр (адаптированная)
- [ ] В первый день после публикации — ссылка в Telegram-каналах

---

## Phase 2.4 — Демо-видео

### Что делаем

Записываем 3 коротких демо-видео по 30 секунд каждое. Для лендинга и для outreach.

### Видео 1: «Find the bottleneck» (30 сек)

- 0-5s: открываем Optimyzer с уже загруженным архивом
- 5-15s: показываем топ операций, наводим на красную строку с 36 000 сек
- 15-25s: кликаем, открывается Anatomy, видим breakdown по EXCP
- 25-30s: кликаем «Объяснить через AI», появляется текст «исключения как управляющая логика...»

### Видео 2: «AI explains deadlock» (30 сек)

- 0-5s: события ТЖ, фильтруем TDEADLOCK
- 5-15s: кликаем на дедлок, открывается DeadlockAnatomy с lock graph
- 15-25s: показываем участников цепочки
- 25-30s: AI объяснение «Процесс A держит ресурс X и ждёт Y, процесс B держит Y...»

### Видео 3: «SQL Console» (30 сек)

- 0-5s: открываем SQL Console
- 5-15s: пишем `SELECT context_normalized, SUM(duration_us)/1000 FROM events WHERE event_type='CALL' GROUP BY context_normalized ORDER BY 2 DESC LIMIT 100`
- 15-25s: выполняем, видим результаты
- 25-30s: «Любые срезы данных через SQL»

### Технически

- Запись: OBS Studio или встроенный screen recorder
- Разрешение: 1920×1080
- Формат: MP4 (H.264)
- Звук: НЕ обязательный закадровый голос. Если есть — Сергея на русском. Если нет — субтитры на русском.
- Фоновая музыка: можно либо тихую инструменталку без копирайта, либо без музыки
- Длительность: строго 30 сек каждое (для embed в Telegram и Twitter)

### Где использовать

- На лендинге как embed (можно вставить в секцию «Демо» вместо/в дополнение к скриншотам)
- На YouTube канале Optimyzer (создаём отдельный канал)
- В статье на Инфостарте (embed)
- В Telegram-постах outreach (как media)

### Acceptance criteria Phase 2.4

- [ ] 3 видео по 30 секунд записаны и смонтированы
- [ ] Загружены на YouTube под аккаунтом Optimyzer
- [ ] Embed на лендинге работает
- [ ] Видео доступны для скачивания (для отправки в Telegram где autoplay)

---

## Phase 2.5 — Outreach в Telegram-каналы 1С

### Что делаем

Анонсируем продукт в профильных Telegram-каналах. Цель — первые 100-500 юзеров.

### Список каналов (предварительный)

**Сергей дополняет своими известными каналами.** Базовый список:

| Канал | Тип | Аудитория |
|---|---|---|
| 1С Программисты | публичный | ~10k |
| 1С Эксперт | публичный | ~5k |
| Котёл 1С | публичный | ~15k |
| 1C-Чат | публичный | ~20k |
| Канал Кушнира (если есть) | публичный | ~? |
| ... | ... | ... |

### Стратегия — НЕ спам

**Не делаем:**
- Массовый постинг одного и того же текста
- Прямую рекламу «КУПИТЕ НАШ ПРОДУКТ»
- Не упоминать ЦУП агрессивно

**Делаем:**
1. **Сначала вступаем** в каналы как обычный участник (1-2 недели до публикации)
2. **Создаём ценность сначала** — отвечаем на вопросы по производительности 1С, даём советы без упоминания продукта
3. **Тогда публикуем анонс** — со ссылкой на статью на Инфостарте, не на лендинг напрямую

### Шаблон поста

```
Привет, коллеги. Сделал бесплатную программу для анализа архивов ТЖ 1С — Optimyzer.

Открываете архив (десятки гигабайт — норма), видите топ медленных операций, 
кликаете на проблемную — Claude объясняет на русском что не так и что делать.

Бесплатно навсегда [стоп — не пишем!], в Free версии 5 AI-объяснений в месяц.

Подробнее в статье на Инфостарте: [ссылка]
Сайт: optimyzer.pro

Буду рад вашим вопросам и фидбеку.
```

Корректировка: убрать «бесплатно навсегда», написать «Базовая версия бесплатно». Это часть глобального правила «не обещать навсегда».

### План публикаций

- **День 0:** публикация статьи на Инфостарте
- **День 0-1:** анонс в 5 главных каналах (с разрывом 1-2 часа между каналами, чтобы не выглядело как спам)
- **День 2-3:** анонс в остальных каналах
- **День 7:** follow-up — рассказать о первых отзывах, поблагодарить попробовавших
- **День 14:** второй follow-up — «обновили продукт по фидбеку», новые фичи (если есть)

### Acceptance criteria Phase 2.5

- [ ] Список 10+ Telegram каналов составлен
- [ ] Сергей вступил в каналы, читал контент 1-2 недели
- [ ] Шаблон поста готов, согласован
- [ ] Публикация анонсов выполнена по плану
- [ ] Прямой трафик с Telegram отслеживается через Yandex.Metrika

---

## Phase 2.6 — Support page + документация

### Что делаем

Минимальная документация на лендинге для самообслуживания юзеров.

### Структура `optimyzer.pro/docs/`

```
docs/
├── getting-started/
│   ├── installation.md
│   ├── first-archive.md
│   └── understanding-results.md
├── features/
│   ├── operations-anatomy.md
│   ├── deadlock-analysis.md
│   ├── ai-explainer.md
│   ├── sql-console.md
│   └── archive-comparison.md
├── billing/
│   ├── plans-and-pricing.md
│   ├── credits.md
│   ├── payment-methods.md
│   └── refunds.md
├── technical/
│   ├── configuring-tj.md       # настройка logcfg.xml
│   ├── archive-formats.md
│   ├── privacy-and-data.md
│   └── system-requirements.md
└── faq.md
```

### Контент

**Минимальный набор для запуска:**

1. `installation.md` — как скачать, установить, запустить (Windows / macOS / Linux отдельно)
2. `first-archive.md` — как настроить logcfg.xml для сбора ТЖ, как создать архив, как загрузить в Optimyzer
3. `configuring-tj.md` — детальная инструкция по logcfg.xml для разных сценариев (production, расследование, дедлоки)
4. `ai-explainer.md` — как работает AI Explainer, что отправляется в Claude API, что не отправляется
5. `plans-and-pricing.md` — цена, что в Free / Pro / Credits, FAQ по биллингу
6. `privacy-and-data.md` — privacy policy: где хранятся данные, что в Claude API уходит, что в телеметрию
7. `faq.md` — те же 8 вопросов что на лендинге + расширенные

### Формат

Markdown файлы рендерятся через простой статический генератор (или просто HTML с импортом MD через JS на client-side). Не используем тяжёлые solutions типа Docusaurus / GitBook — для запуска достаточно простой реализации.

Sidebar с навигацией по разделам, breadcrumbs, search (опционально).

### Support email & Telegram

- `hello@optimyzer.pro` — общая почта
- `support@optimyzer.pro` — техподдержка (для Pro юзеров — приоритет)
- `@optimyzer_support` Telegram (опционально, для быстрых вопросов)

Все три обрабатываются Сергеем лично пока поток < 20 обращений в день.

### Acceptance criteria Phase 2.6

- [ ] Все 7 minimum документов написаны
- [ ] Документация задеплоена на `optimyzer.pro/docs/`
- [ ] Email hello@ и support@ настроены, форвардятся Сергею
- [ ] FAQ страница на лендинге линкует на расширенный faq.md
- [ ] Privacy policy юридически приемлемый (можно через ChatGPT шаблон, потом проверить)

---

## Phase 2 — итоговый Definition of Done

Перед launch и закрытием Sales Sprint:

- [ ] Лендинг на `optimyzer.pro` live, SSL, SEO, analytics
- [ ] Web-кабинет на `account.optimyzer.pro` live
- [ ] Backend API на `api.optimyzer.pro` live
- [ ] Onboarding в desktop работает
- [ ] Статья опубликована на Инфостарте + Хабр + Mista
- [ ] 3 demo-видео загружены и embedded
- [ ] Анонсы в 10+ Telegram-каналах выполнены
- [ ] Documentation на `optimyzer.pro/docs/` доступна
- [ ] Email/Telegram support настроены
- [ ] Yandex.Metrika собирает данные
- [ ] **Первая реальная продажа состоялась** (даже одна — это сигнал что система работает end-to-end)

---

# ПОСЛЕ SALES SPRINT — Market Validation (2-3 недели)

**НЕ входит в спринт, делается Сергеем самостоятельно.**

### Что отслеживаем

- Конверсия Free → Pro
- Какие screens используются по телеметрии
- Какие AI explanation наиболее популярны
- Retention: возвращаются ли юзеры через 7 / 14 / 30 дней
- Откуда трафик (Yandex.Metrika source attribution)
- Какие отказы платежей (YooKassa dashboard)

### Решения после Market Validation

На основе данных решается:
1. **Менять ли тарификацию** (например, если 80% юзеров не используют экспорт — убрать его из Pro)
2. **Какой следующий спринт** — Sprint 6 (восстановление QueryAnalyzer с SDBL parser) или другие приоритеты по фидбеку
3. **Нужны ли изменения в Free лимитах** (5 AI/мес — может быть мало или много)
4. **Стоит ли поднять цену Pro** (2 990 → 3 990 для новых юзеров, существующие на old price)

---

# Технические инструкции для Claude Code

## Структура коммитов

Каждая Phase — отдельная feature branch. Внутри Phase — атомарные коммиты с осмысленными сообщениями.

```
git checkout -b sales-sprint/phase-1.1-yandex-oauth
# работа...
git commit -m "feat(server): add Yandex OAuth provider"
git commit -m "feat(server): add User and RefreshToken models"
# ...
git checkout main && git merge --no-ff sales-sprint/phase-1.1-yandex-oauth
git tag v0.6.0-phase1.1-oauth
git push origin main --tags
```

## Documentation

После каждой Phase создавать `docs/sales_sprint/PHASE_X_REPORT.md` с:
- Что сделано
- Decisions taken
- Tech debt / known issues
- Tests metrics
- Stop rule confirmation

## Stop rules — обязательны

Каждая Phase имеет stop rule. Без подтверждения Сергея — не двигаемся в следующую Phase.

Это **не задержка**, это **проверка** что мы не строим неправильное направление.

## Что НЕ делать в Sales Sprint

- НЕ восстанавливать QueryAnalyzer (Sprint 6)
- НЕ добавлять новые аналитические views
- НЕ менять существующую desktop логику (DuckDB парсер, anatomy views) кроме Settings → Account
- НЕ оптимизировать перформанс если работает приемлемо
- НЕ переписывать существующий код «потому что некрасиво»
- НЕ добавлять новые языки (только русский UI)
- НЕ делать mobile app
- НЕ делать enterprise features (SSO, audit logs, custom branding) — это Phase 3+
- НЕ автоматизировать корпоративные продажи (Team по запросу = manual через email)

## Stop rule общий — критичный

**Если Sales Sprint занимает больше 10 недель** — это сигнал что что-то идёт не так. Обсудить с Сергеем что выкинуть, какие фичи отложить, как ускорить.

## Если что-то блокирует

Если технически невозможно сделать что-то по этому плану — **остановиться и спросить**, не пытаться обойти. Например:
- YooKassa requires юрлица в каких-то операциях → обсудить
- Yandex OAuth не одобряет приложение → обсудить альтернативу
- Cost AI операций оказывается выше расчёта → пересмотр тарификации

---

# Roadmap после Sales Sprint

Это для контекста, **не входит в Sales Sprint**:

## Sprint 6 — QueryAnalyzer Restoration (после Market Validation)

- SDBL parser со scope tracking (ANTLR4 или PyParsing)
- Type chaser для цепочек `.Поле.Поле.Поле`
- Восстановление UI «Анализ запроса» в Sidebar
- Pro+ тариф с QueryAnalyzer (например 4 990 ₽/мес)

Все материалы готовы в `docs/QUERY_ANALYZER_HIDDEN_2026_05.md` (438 строк документации от предыдущего архитектурного решения).

## Sprint 7 — Continuous Monitoring (отдалённая перспектива)

Если телеметрия покажет спрос — добавить режим continuous monitoring (вместо offline-only анализа архивов).

## Sprint 8+ — AI Generator обработок 1С

Идея из ChatGPT analysis ранее: AI генерирует обработки 1С (внешние) для типичных задач. Очень узкая тема, но огромная boil-down value. Отложено до того как Optimyzer станет стабильным источником выручки.

---

# Приложение A — env vars для backend

```env
# General
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/optimyzer

# Auth
JWT_SECRET=...  # random 64 chars
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_DAYS=30

# Yandex OAuth
YANDEX_CLIENT_ID=...
YANDEX_CLIENT_SECRET=...
YANDEX_REDIRECT_URI=https://account.optimyzer.pro/oauth/callback

# YooKassa
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
YOOKASSA_WEBHOOK_SECRET=...

# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Email (SMTP for transactional)
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=hello@optimyzer.pro
SMTP_PASSWORD=...
SMTP_FROM="Optimyzer <hello@optimyzer.pro>"

# CORS
CORS_ALLOWED_ORIGINS=https://account.optimyzer.pro,https://optimyzer.pro

# Rate limiting
RATE_LIMIT_AUTHENTICATED=100/minute
RATE_LIMIT_ANONYMOUS=20/minute

# Telegram bot (optional, for notifications)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_USERNAME=optimyzer_bot
```

---

# Приложение B — Финансовая модель (контекст для решений)

**Себестоимость:**
- Claude AI операция: ~4 ₽ (avg)
- VDS hosting: ~3 000 ₽/мес
- Domain + SSL: ~200 ₽/мес
- YooKassa commission: 2.8% с транзакции
- Email service (SMTP): ~500 ₽/мес

**Расчёт маржи Pro (2 990 ₽):**
- Средний расход AI: 100 операций × 4 ₽ = 400 ₽
- YooKassa: 84 ₽
- Прочие costs (allocated): 50 ₽
- Маржа: 2 990 - 534 = **2 456 ₽** = **82% gross margin**

**Расчёт маржи Credits Mini (299 ₽):**
- AI расход: 30 × 4 ₽ = 120 ₽
- YooKassa: 8 ₽
- Маржа: 299 - 128 = **171 ₽** = **57% margin**

**Worst case Free (acquisition cost):**
- 5 AI операций × 4 ₽ = 20 ₽/мес
- Это **расход на привлечение**, не убыток. Окупается одной Pro подпиской с 150 Free юзеров.

**Точка безубыточности (break-even):**
- Расход операционный: ~5 000 ₽/мес (без учёта AI)
- Pro juzers нужно: 5 000 / 2 456 ≈ **3 платящих** для покрытия операционных расходов
- Это **очень низкий порог**

---

# Финальное напутствие

Sales Sprint — это **переход от разработки к бизнесу**. Это другой mindset:

**В разработке** оптимизируем код, фичи, архитектуру.

**В Sales** оптимизируем acquisition, conversion, retention. Это новый домен с другими метриками.

Главные мысли которые должен помнить исполнитель:

1. **Speed over polish.** Перфекционизм в Sales Sprint — враг. Лучше запустить с грубым лендингом, чем не запустить с идеальным.

2. **Talk to users.** Каждый платный юзер в первый месяц — это **золото**. Личное общение, благодарность, расспросы что нравится / не нравится.

3. **Don't over-engineer.** Backend на простом стеке. Простая БД. Простой деплой. Усложнения — после проверки spros'а.

4. **Telemetry > opinions.** Через 2-3 недели после launch — данные. До этого все мнения (включая моё, ChatGPT, друзей) — гипотезы.

5. **Don't quit.** Первые 30 дней могут быть тяжёлыми: мало юзеров, мало денег, негативные комментарии. Это **норма для нового продукта**. Bridge через первые 90 дней — критично.

Удачи в запуске. 🚀

(один эмодзи на 1500 строк допустим — это финальная мотивация, не deco)

---

**Подготовил:** Claude Opus 4.7 (Architect)
**Для:** Claude Code (executor)
**Дата:** 2026-05-23
**Версия:** Sales Sprint v1
**Длительность спринта:** 6-9 недель
**Следующий sprint:** Market Validation (2-3 недели после launch) → Sprint 6 или другие приоритеты по данным
