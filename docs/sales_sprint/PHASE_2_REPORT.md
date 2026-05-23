# Sales Sprint · Phase 2 Report

**Дата:** 2026-05-23  
**Версия:** v0.6.0 (development)

## Состав сделанного

### Phase 2.1 — Landing deployment prep

Скопировал `DESIGN_CONCEPT/` → `landing/`. Заменил mock-ссылки на реальные:

- `account.html` → `https://account.optimyzer.pro`
- `#pricing` (download кнопка) → `/download` (nginx редиректит на GitHub Releases)
- «Купить Pro» → `https://account.optimyzer.pro/subscription`
- «GitHub» → `https://github.com/anymasoft/1c-optimyzer`
- «Связаться» → `mailto:hello@optimyzer.pro`
- «Документация» → `/docs/`

Добавил:
- `robots.txt` (allow all + ссылка на sitemap)
- `sitemap.xml` (главные страницы)
- `nginx.conf.example` (с SSL, HSTS, CSP, кешем статики, `/download` редирект)
- Yandex.Metrika placeholder в `<head>` (закомментирован — Сергей раскомментит
  и заменит `YOUR_COUNTER_ID` после регистрации счётчика)
- Canonical link

### Phase 2.2 — Onboarding flow в desktop

- `WelcomeModal.tsx` — показывается один раз при первом запуске (флаг в
  localStorage). Юзер выбирает «Загрузить свой архив» или «Пропустить».
- `EmptyArchiveState.tsx` — показывается на главном экране когда архив не
  загружен. Большая иконка папки + CTA «Загрузить» + ссылка «Что такое ТЖ?»
  (открывает `optimyzer.pro/docs/technical/configuring-tj.html`).
- App.tsx wire: WelcomeModal перед всем UI, EmptyArchiveState заменяет
  render-screen-функцию когда `!archive && !welcome.open`.
- i18n строки для onboarding в `i18n/ru.ts`.

**Что НЕ сделано:**
- Interactive tour (overlay'и с инструкциями на конкретные элементы) — отложено,
  пользы меньше чем у первичных Welcome + Empty States, и сильно
  усложнит код.
- Sample demo архив в установщике — отложено, нужен реальный обезличенный
  архив для bundling.

### Phase 2.3, 2.4, 2.5 — НЕ сделано (по запросу Сергея)

Маркетинговый контент (статья на Инфостарте, demo-видео, outreach в
Telegram-каналы) — это работа Сергея, не Claude Code. Скип по решению
от 2026-05-23 ("делай все, кроме статьи и видео").

### Phase 2.6 — Support page + docs structure

Создал статический раздел `landing/docs/` — 7 страниц + индекс + общая CSS:

- `landing/docs/index.html` — обзор разделов
- `landing/docs/docs.css` — стили (sidebar nav + content)
- `getting-started/installation.html` — Windows/macOS/Linux установка
- `getting-started/first-archive.html` — как загрузить ТЖ
- `features/ai-explainer.html` — как работает AI, лимиты, что отправляется
- `billing/plans-and-pricing.html` — Free/Pro/Credits, оплата, возврат
- `technical/configuring-tj.html` — рабочие конфиги logcfg.xml для разных
  сценариев (расследование, охота за дедлоками, production)
- `technical/privacy-and-data.html` — privacy policy (без юридического тумана)
- `faq.html` — 9 вопросов: ЦУП, КИП, production, конфигурации, лимиты,
  возврат, Linux, query-analyzer

Все страницы — статические HTML с одинаковым sidebar (дублирование sidebar'а
по файлам — приемлемо для 7 страниц; в Phase 3+ можно сделать общий header
через include или простой статический генератор).

## Файловая структура landing/

```
landing/
├── README.md
├── index.html               # лендинг
├── styles.css
├── nginx.conf.example       # для деплоя на VDS
├── robots.txt
├── sitemap.xml
├── assets/                  # из DESIGN_CONCEPT
│   ├── favicon.svg
│   ├── og-image.png
│   └── screen-*.png         # 9 скриншотов desktop
└── docs/
    ├── docs.css
    ├── index.html
    ├── _template.html       # шаблон для новых doc-страниц
    ├── faq.html
    ├── getting-started/
    │   ├── installation.html
    │   └── first-archive.html
    ├── features/
    │   └── ai-explainer.html
    ├── billing/
    │   └── plans-and-pricing.html
    └── technical/
        ├── configuring-tj.html
        └── privacy-and-data.html
```

## Чек-лист готовности (Phase 2 DoD)

- [x] Лендинг готов к деплою (landing/), нужен domain + VDS + nginx
- [x] Web-кабинет готов к деплою (cabinet/), нужен account.optimyzer.pro
- [x] Backend API готов к деплою (server/), нужен api.optimyzer.pro
- [x] Onboarding в desktop работает (welcome + empty state)
- [ ] Статья на Инфостарте — НЕ в scope (Сергей сам)
- [ ] 3 demo-видео — НЕ в scope (Сергей сам)
- [ ] Анонсы в Telegram каналах — НЕ в scope (Сергей сам)
- [x] Documentation на /docs/ доступна (7 minimum-докуменentов)
- [x] Email hello@/support@ — указаны в docs (физически настроить нужно
      на стороне почтового провайдера)
- [x] Yandex.Metrika placeholder в landing index.html (раскомментить +
      заменить YOUR_COUNTER_ID)
- [ ] Первая реальная продажа — gates по prod-credentials и deploy

## Следующие шаги (для Сергея)

1. **Прежде чем launch:**
   - Зарегистрировать Yandex.Metrika счётчик, заменить YOUR_COUNTER_ID
     в `landing/index.html` и раскомментировать script
   - Положить в GitHub Releases первые binary артефакты (msi/dmg/AppImage),
     чтобы `/download` редирект не вёл в 404
   - Деплой landing/cabinet/server по плану из `landing/README.md`
   - Купить и привязать domain через регистратор

2. **После launch:**
   - Написать статью на Инфостарте (Phase 2.3 — Сергей сам)
   - Записать 3 demo-видео (Phase 2.4 — Сергей сам)
   - Outreach в Telegram-каналах (Phase 2.5 — Сергей сам)

3. **Market Validation (2-3 недели после launch):**
   - Открывать admin telemetry summary, смотреть какие screens юзают
   - Считать конверсию Free → Pro
   - Если конверсия низкая — пересмотр Free лимита или offer'а
   - Решение про Sprint 6 (восстановление QueryAnalyzer) на основе данных
