# DESIGN_CONCEPT — финальный дизайн для веб Optimyzer

Папка содержит **только утверждённый дизайн** лендинга и веб рабочей области
Optimyzer, отобранный из общего бакета `DESIGN_TEMP/` по решению Сергея
(23 мая 2026).

## Состав

| Файл                    | Назначение                                        |
| ----------------------- | ------------------------------------------------- |
| `index.html`            | Лендинг (hero, фичи, тарифы, CTA «Скачать»)       |
| `account.html`          | Личный кабинет (веб рабочая область)              |
| `desktop-settings.html` | Экран Settings · Аккаунт                          |
| `styles.css`            | Общие стили (≈9 KB)                               |
| `assets/`               | PNG-скриншоты экранов desktop-приложения          |

Все три HTML-страницы — статические, открываются двойным кликом, без сборки.
Зависимостей нет (Tailwind подключается через CDN внутри HTML).

## Как смотреть архитектору (Opus)

1. **Локально** (после `git pull`):
   ```
   D:\1C-Optimyzer\DESIGN_CONCEPT\index.html
   D:\1C-Optimyzer\DESIGN_CONCEPT\account.html
   D:\1C-Optimyzer\DESIGN_CONCEPT\desktop-settings.html
   ```
2. **С GitHub raw** (через `WebFetch`):
   - https://raw.githubusercontent.com/anymasoft/1c-optimyzer/main/DESIGN_CONCEPT/index.html
   - https://raw.githubusercontent.com/anymasoft/1c-optimyzer/main/DESIGN_CONCEPT/account.html
   - https://raw.githubusercontent.com/anymasoft/1c-optimyzer/main/DESIGN_CONCEPT/desktop-settings.html

## Бакет с черновиками

Полный бакет с альтернативными концептами и неиспользуемыми макетами лежит
в `DESIGN_TEMP/` (≈6 MB, тоже закоммичен). Там есть другой концепт workspace
на React (`1C-Optimyzer.html` + `opt/*.jsx`), а также не-Optimyzer-дизайны
(Agenter, GosLog, Konvey). Использовать как референс по желанию — в финальный
дизайн идёт только содержимое `DESIGN_CONCEPT/`.
