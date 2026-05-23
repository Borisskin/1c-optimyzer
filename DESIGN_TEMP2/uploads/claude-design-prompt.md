# Промпт для Claude Design

> Использовать на https://claude.ai/design
> Вставить целиком. Цель: получить визуальный макет Workspace 2.0.

---

## Промпт

```
Design a professional B2B SaaS web application screen for "ГосЛог Проверка" (GosLog Check) —
a Russian logistics compliance platform that verifies contractors against government registries.

The design should match the existing landing page aesthetic precisely:
- Primary color: indigo (#4f46e5, gradient to #4338ca)
- Background: near-white #fdfcfe (hsl 0 0% 99%)
- Cards: pure white, 18px border-radius, border: 1px solid rgba(15,18,30,0.08), subtle shadow
- Font: Inter (body, UI), JetBrains Mono (INN numbers, codes)
- Accent colors: green #22c55e (success/registered), red #ef4444 (danger/not registered)
- Style: clean, modern, light theme only, no dark mode

LAYOUT:
Left sidebar (240px wide, fixed):
- Top: logo (shield icon, 28px) + "ГосЛог Проверка" in bold
- Navigation items (rounded-xl, 40px height):
  * Shield icon + "Проверка" (ACTIVE - indigo background tint, indigo text)
  * Bell icon + "Мониторинг"
  * Clock icon + "История"
- Balance card (bottom of sidebar, above user):
  White card with subtle border, title "Баланс проверок",
  progress bar (482/500 checks, green color), 
  small indigo gradient button "Пополнить" full width
- User section at bottom: avatar circle (indigo, letter "И"), name "Иван И.", email below, logout icon

Main content area (flex-1, padding 32px):
- Page title "Проверка подрядчиков" (28px bold)

COMMAND BAR (primary input, top of content):
Large textarea-style input box, 18px radius, 2px border (subtle gray, indigo on focus):
  - Placeholder: "Введите ИНН подрядчиков — по одному на строке или через запятую"
  - Inside: monospace numbers visible "7707329152\n5032001234\n7812345678"
  - Below the box: two ghost buttons "⬆ Загрузить CSV" and "⬆ Загрузить XLSX"
  - Below those: large indigo gradient button (full width of command bar) "Проверить →"

SUMMARY BAR (between input and results):
White card, horizontal layout:
  "Проверено: 12" | "Рисков: 3" (in red) | "В реестре: 9" (in green) | "Добавлено в мониторинг: 5"
  Right side: icon-only buttons (Download PDF, Copy, Refresh)

RESULTS (3 cards stacked vertically):

Card 1 — REGISTERED (success state):
- Left: large green checkmark circle icon (20px)
- Center: "ООО «Транспортная компания»" (bold, 15px), 
  below: "ИНН 7707329152 · ОГРН 1027739040542" (mono, muted gray),
  below: "В реестре с 14.02.2022 · Запись № 12345" (small, muted)
- Right: green badge "В реестре" + bell icon button (green tint, 32x32px, rounded-xl border)

Card 2 — NOT REGISTERED (danger state):
- Left: large red X circle icon (20px)
- Center: "ИП Смирнов Алексей Игоревич" (bold), "ИНН 503200123456" (mono, muted)
- Right: red badge "Не в реестре" + bell+ button (green tint, to add to monitoring)
- Bottom of card: amber/red warning strip with rounded bottom corners:
  "⚠ Риск: работа с незарегистрированным экспедитором — штраф от 300 000 ₽"

Card 3 — REGISTERED (similar to card 1 but for "ООО «Логистик Групп»")

META ROW (below results, centered):
Small muted text: "✓ Данные Минтранс · Обновлено сегодня · Реестр: 12 847 экспедиторов"
Similar to landing page trust indicators.

VISUAL STYLE DETAILS:
- Cards: white bg, border 1px solid rgba(15,18,30,0.08), box-shadow: 0 1px 4px rgba(15,18,30,0.07)
- Hover state on result cards: subtle -2px translateY, stronger shadow
- Sidebar nav active item: background rgba(79,70,229,0.08), text #4f46e5
- Progress bar: smooth green gradient, height 6px, rounded
- All badge/status pills: small padding (4px 10px), 20px border-radius, no border or very subtle
- Indigo gradient button: linear-gradient(135deg, #5b54ea, #4338ca), white text, 12px radius
- Typography: heading 28px/600, subheading 15px/600, body 14px/400, mono 13px
- Spacing: generous whitespace, 24px gaps between sections

The overall impression should be: premium, trustworthy, data-dense but not cluttered,
like a high-quality enterprise SaaS tool (Notion, Linear, Stripe Dashboard aesthetic).
Light, airy, professional.

Show the full application window at 1440px width desktop layout.
```

---

## Уточняющие промпты (если нужно доработать)

### Если получилось слишком тёмно или ярко:
```
Make it lighter and more subtle. The background should be almost pure white (#fdfcfe).
Cards should be pure white with very subtle shadow. Borders should be barely visible.
Primary indigo only for active states and CTA buttons, not for backgrounds.
```

### Если сайдбар выглядит плохо:
```
The sidebar should be clean white, same background as main content but separated by
a subtle 1px right border (rgba(15,18,30,0.08)). Nav items: transparent background normally,
soft indigo tint (rgba(79,70,229,0.08)) when active. Balance card inside sidebar
should have white background with a light border, NOT a colored background.
```

### Если карточки результатов плохие:
```
Each result card should be a clean white rectangle with 18px radius.
The checkmark icon should be a circle outline with a checkmark inside — green for registered,
red X for not registered. The status badge on the right should be small pill-shaped:
green pill with "В реестре" for registered, red pill with "Не в реестре" for not registered.
The bell button should be a small square (32x32px) with rounded corners, very subtle green tint.
```

### Для мобильной версии (отдельный запрос):
```
Now show the same screen at 375px mobile width. 
Instead of a sidebar, show a bottom navigation bar with 4 icon-only tabs:
Shield (Проверка, active), Bell (Мониторинг), Clock (История), User (Аккаунт).
The command bar and results should take full width. Balance should be a small chip in the top bar.
```

### Для мониторинг-раздела:
```
Show the Мониторинг (Monitoring) section of the same app.
Same sidebar layout, but main content shows:
- Page title "Мониторинг контрагентов" with count "12 компаний"
- Row of filter pills: "Все" (active, indigo), "Изменились", "Под риском", "Без риска"
- List of company cards similar to results, but each shows:
  * Company name + INN
  * Bell icon (monitoring active indicator, green)
  * Status badge
  * "Последнее изменение: 07.05.2026" in muted text
  * Trash icon button on the right to remove
- One card should show "изменился сегодня" with a subtle indigo highlight/dot indicator
```

---

## Ключевые ориентиры для ревью

Хороший результат должен:
- [ ] Совпадать по цветам с лендингом goslog.art (indigo primary, green success, red danger)
- [ ] Иметь чистый белый sidebar без градиентов
- [ ] Показывать прогресс-бар баланса в sidebar (зелёный, 96% заполнен)
- [ ] Карточки результатов — белые, не серые, с чёткими иконками статуса
- [ ] Command bar — крупный, с тенью на focus, placeholder серый
- [ ] Summary bar горизонтальный над результатами
- [ ] В целом: выглядит как Notion / Linear / Stripe, не как Bootstrap admin

---

*Последнее обновление: 2026-05-07*
