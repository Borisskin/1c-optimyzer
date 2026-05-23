# cabinet/ — Optimyzer web кабинет

React приложение для управления подпиской, кредитами, устройствами.
Деплоится на `account.optimyzer.pro`.

## Стек

- React 18 + TypeScript + Vite
- React Router 6
- TanStack Query 5 (server state)
- recharts (графики)
- Дизайн-токены из `DESIGN_CONCEPT/styles.css` (cabinet/src/styles/tokens.css)

## Запуск

```bash
cd cabinet/
npm install
cp .env.example .env
npm run dev
```

Открыть http://127.0.0.1:5173/. Backend ожидается на :8001 (см. server/README.md).

## Структура

| Файл                              | Назначение                                       |
| --------------------------------- | ------------------------------------------------ |
| `src/pages/Login.tsx`             | Yandex OAuth button                              |
| `src/pages/Overview.tsx`          | Главная — статус, метрики, последние сессии      |
| `src/pages/Subscription.tsx`      | Управление подпиской                             |
| `src/pages/Credits.tsx`           | Баланс + покупка кредитов                        |
| `src/pages/Devices.tsx`           | Список устройств                                 |
| `src/pages/Payments.tsx`          | История платежей                                 |
| `src/pages/Usage.tsx`             | Графики использования                            |
| `src/pages/Settings.tsx`          | Профиль, уведомления, telegram bot               |
| `src/components/layout/`          | Sidebar, Header, ProtectedRoute                  |
| `src/api/`                        | TanStack Query клиенты                           |
| `src/styles/tokens.css`           | Дизайн-токены (cv: --accent, --bg, …)            |

## Деплой (Phase 2.1)

`npm run build` → `dist/`. Залить на nginx как static. См.
`docs/sales_sprint/PHASE_2_REPORT.md`.
