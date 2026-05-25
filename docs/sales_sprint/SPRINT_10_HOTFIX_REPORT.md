# Sprint 10 — Post-release Hotfix Session

**Дата:** 2026-05-25  
**Аудитория:** архитектор (Claude Opus)  
**Тип:** Post-release bugfix — три критических ошибки, обнаруженные при проверке по официальной документации и ручном тестировании  
**Коммиты:** `38d423a`, `6c0bb98`, `825f770`

---

## Контекст

После закрытия Sprint 10 (`v0.10.0-internal`) проводилась верификация реализации TJ Config Builder
по официальной документации 1С (раздел 3.14 «Настройка технологического журнала» Руководства
администратора). В ходе верификации и ручного тестирования обнаружено три независимых бага
разного уровня критичности.

---

## Bug 1 — Duration filter units: 100× занижение (критический)

**Коммит:** `38d423a`  
**Файлы:** `frontend/src/features/tj-config-builder/xmlSerializer.ts`,
`frontend/src/features/tj-config-builder/__tests__/xmlSerializer.test.ts`

### Суть

`xmlSerializer.ts` записывал в `<gt property="duration" value="..."/>` значение `threshold_cs`
напрямую. Но единица Duration в logcfg.xml — **десятитысячная доля секунды** (= 100 мкс/unit),
а `threshold_cs` — centiseconds (= 10 мс = 100 units). Итог: каждый сгенерированный фильтр
был занижен в 100 раз.

**Официальная документация (раздел 3.14):**
> «Duration — длительность события в десятитысячных долях секунды»

Пример из документации:
- `value="100000"` = 10 секунд → 100000 × 100 мкс = 10 сек ✓

**Практическое следствие до фикса:**

| Пользователь выставляет | Намерение | Реальный фильтр (до) | Реальный фильтр (после) |
|---|---|---|---|
| `threshold_cs = 10` | ≥ 100 мс | `value="10"` → ≥ 1 мс | `value="1000"` → ≥ 100 мс ✓ |
| `threshold_cs = 100` | ≥ 1 сек | `value="100"` → ≥ 10 мс | `value="10000"` → ≥ 1 сек ✓ |
| `threshold_cs = 1000` | ≥ 10 сек | `value="1000"` → ≥ 100 мс | `value="100000"` → ≥ 10 сек ✓ |

С занижённым порогом 1С писала бы почти ВСЕ SQL-запросы — диагностический инструмент
превращался в генератор гигантских логов.

### Фикс

```typescript
// ДО (неверно):
lines.push(`      <gt property="duration" value="${settings.threshold_cs}"/>`);

// ПОСЛЕ:
// ВАЖНО: 1C ТЖ измеряет Duration в сотнях микросекунд (1 unit = 100 мкс).
// threshold_cs хранится в centiseconds (1 cs = 10 мс = 100 units).
// Поэтому умножаем на 100: threshold_cs × 100 = значение в 1C-единицах.
lines.push(`      <gt property="duration" value="${settings.threshold_cs * 100}"/>`);
```

### Тесты

Обновлены два теста в `xmlSerializer.test.ts`:
- `threshold_cs=100` (1 сек): ожидаемое `value="10000"` (было `"100"`)
- `threshold_cs=50` (500 мс): ожидаемое `value="5000"` (было `"50"`)

Добавлены явные комментарии с расчётом к каждому ожидаемому значению.

**Итог:** 50 тестов — 50/50 зелёных.

### Затронутый инвариант данных

Единица `threshold_cs` (centiseconds) как хранимый формат — **остаётся неизменной**.
Конвертация в 1C-units происходит исключительно в `serializeToXml()`. Это сознательное
решение: threshold_cs удобен для UI (целые числа секунд, без больших значений), 1C-units
нужны только для XML.

---

## Bug 2 — Тёмные тултипы: undefined CSS-токены с fallback на VS Code dark (средний)

**Коммит:** `6c0bb98`  
**Файлы:** `frontend/src/features/tj-config-builder/components/XmlPreview.module.css`,
`frontend/src/features/tj-config-builder/components/EventHelp.module.css`,
`frontend/src/styles/optimyzer-design.css`

### Суть

Два компонента использовали токены `--o-surface` и `--o-surface-2` в качестве фона
тултипов. Эти токены никогда не были определены в `optimyzer-design.css`. CSS-fallback
в браузере — пустое значение → унаследованный дефолт webview (`#252526`, цвет VS Code Dark+).
Пользователь видел чёрные тултипы.

**Дерево причин:**
```
XmlPreview.module.css:
  .icon_btn[data-tooltip]::after { background: var(--o-surface, #252526) }
                                                            ↑ VS Code Dark fallback!

EventHelp.module.css:
  .tooltip { background: var(--o-surface-2, #252525) }
                                     ↑ ещё темнее!

optimyzer-design.css:
  --o-surface  — НЕ ОПРЕДЕЛЁН
  --o-surface-2 — НЕ ОПРЕДЕЛЁН
```

Токены `--o-surface*` присутствовали в `design/opt/shared.jsx` (Tailwind-прототип),
но при переносе на CSS Modules в Sprint 0 были упущены.

### Фикс

**Шаг 1 — патч симптомов** в обоих CSS Modules: заменить `var(--o-surface, ...)` на
`var(--o-panel, #ffffff)`. `--o-panel` определён с самого Sprint 0 = белый.

**Шаг 2 — закрыть дыру** в design-системе: добавить все недостающие токены в
`optimyzer-design.css`:

```css
/* Surfaces (явно определены, чтобы fallback-и не падали на тёмный дефолт) */
--o-surface:   #ffffff;   /* для code-editor bg, popover bg */
--o-surface-1: #ffffff;
--o-surface-2: #f5f5f5;   /* слегка серый второй уровень */
--o-input:     #ffffff;   /* фон полей ввода */
```

Шаг 2 критичен: даже если в других компонентах тултипы визуально работали (через
отдельный fallback), появление `--o-surface` в глобальном файле предотвращает
аналогичный баг в будущих компонентах.

### Архитектурное наблюдение

CSS-токены в дизайн-системе (`optimyzer-design.css`) должны определяться **до того,
как они используются**. Текущий подход — один глобальный файл со всеми `:root {...}`
переменными — правильный (ADR-002), но при добавлении компонентов нужна явная проверка
что нужный токен уже в файле. Рекомендация: зафиксировать полный канонический список
токенов в начале файла как «contract», не давать разработчикам угадывать что есть,
а что нет.

---

## Bug 3 — Tauri fs permissions: файл не сохранялся + ложный индикатор успеха (критический)

**Коммит:** `825f770`  
**Файлы:** `frontend/src-tauri/capabilities/default.json`,
`frontend/src/features/tj-config-builder/components/XmlPreview.tsx`

### Суть

В Tauri v2 разрешения для плагина `fs` управляются через `capabilities/*.json`.
`fs:default` — это **pre-set разрешений исключительно для чтения** из app-директорий
(`$APPDATA/com.anymasoft.optimyzer/**`). Запись в произвольный путь (например,
`C:\Program Files\1cv8\conf\logcfg.xml`, выбранный через save-диалог) требует
отдельного явного разрешения `fs:allow-write-text-file` со scope.

**Цепочка провала:**

```
handleSave()
  → save() диалог  ← РАБОТАЕТ, возвращает путь
  → writeTextFile(path, xml) ← БРОСАЕТ исключение (no permission)
  → catch { 
      Blob + URL.createObjectURL + a.click()  ← НЕ РАБОТАЕТ в Tauri webview
                                                (нет браузерного download manager)
      setSaved(true)  ← ЛОЖНЫЙ УСПЕХ! Пользователь видит ✓ но файла нет
    }
```

Пользователь наблюдал: диалог открывается → папку выбирает → кнопка становится зелёной
«Сохранено!» → файла в папке нет.

### Почему баг дожил до пользователя

Sprint 10 разрабатывался с акцентом на UX и XML-корректность. Save-функция была реализована
с Blob-fallback для «на случай если Tauri недоступен», но в реальности:
1. В Tauri webview Blob download никогда не показывает диалог сохранения
2. `catch {}` маскировал permission error
3. Ручной тест «нажать сохранить → проверить папку» не был в чеклисте Sprint 10

### Фикс — две части

**Часть 1: `capabilities/default.json`**

```json
"permissions": [
  "core:default",
  "dialog:default",
  "fs:default",
  {
    "identifier": "fs:allow-write-text-file",
    "allow": [{ "path": "**" }]
  },
  "shell:default"
]
```

`"path": "**"` — разрешить запись в любой путь. Это намеренно широко: инструмент предназначен
для системных администраторов, которые должны иметь возможность сохранить файл куда угодно
(включая `C:\Program Files\...`). Путь дополнительно защищён тем, что он явно выбирается
через native OS save-диалог.

**Часть 2: `XmlPreview.tsx`** — удалить Blob-fallback и ложный setSaved

```typescript
// БЫЛО: try { writeTextFile } catch { Blob + setSaved(true) }

// СТАЛО:
const filePath = await save({ ... });
if (!filePath) return;   // пользователь нажал Отмена
await writeTextFile(filePath, xmlText);
setSaved(true);
setTimeout(() => setSaved(false), 2000);
```

Без try/catch: если `writeTextFile` упадёт (например, нет прав на целевую папку — UAC
заблокировал) — ошибка всплывёт выше и пользователь увидит нативный error. Это честнее,
чем silent failure.

### Важное для следующих фич с записью файлов

Любая операция `writeTextFile / writeFile / copyFile` через `@tauri-apps/plugin-fs`
требует **явного разрешения в `capabilities/default.json`**. `fs:default` = только чтение
из app-директорий. Это не документировано явно в официальном Tauri getting started,
но критично для правильной работы.

Текущий scope `"path": "**"` достаточен для всех сценариев инструмента. Если в будущем
появится security review — можно сузить до `$HOME/**` + `$DESKTOP/**` + `$DOCUMENT/**`,
но это не покроет `C:\Program Files\...` для logcfg.xml, поэтому лучше оставить `**`.

---

## Верификация по официальной документации

Параллельно с bugfix-сессией проведена full cross-check реализации против раздела 3.14
Руководства администратора 1С («Настройка файла logcfg.xml»).

### Результат: 100% соответствие по структуре

| Элемент | Документация (раздел 3.14) | Наша реализация | Статус |
|---|---|---|---|
| XML namespace | `http://v8.1c.ru/v8/tech-log` | `xmlns="http://v8.1c.ru/v8/tech-log"` | ✅ |
| `<config>` как корень | обязательно | есть | ✅ |
| `<log location history>` | внутри `<config>` | есть, history из `history_hours` | ✅ |
| `<event>` → `<eq property="name">` | фильтр по имени | `<eq property="name" value="CALL"/>` | ✅ |
| `<gt property="duration" value>` | фильтр по длительности | `threshold_cs × 100` после фикса | ✅ |
| `<property name="all"/>` | внутри `<log>` | всегда добавляется | ✅ |
| `<property name="plansqltext"/>` | внутри `<log>` | при `capture_plans=true` | ✅ |
| `<plansql/>` | **sibling `<log>` под `<config>`** | position верная (после `</log>`) | ✅ |
| Единицы Duration | 1/10000 сек = 100 мкс/unit | `threshold_cs × 100` | ✅ |

### Незначительные расхождения (не требуют изменений)

**Регистр имён событий.** В официальных примерах `value="dbmssql"` (lowercase), но
документация явно указывает «регистр не различается». Наши `DBMSSQL`, `CALL` и т.д.
в uppercase — стандарт в сообществе 1С (Infostart, KB 1CI) и в официальном PowerShell
скрипте `patch-logcfg-for-plans.ps1`. Оставить как есть.

**`<property name="sql"/>`.** Официальный пример для plans-сценария:
`<property name="sql"/> + <property name="plansqltext"/>`. Наш подход: `<property name="all"/>` 
который уже включает sql. Это расширенная версия — не нарушение, а более полный сбор.

**Событие ATTN.** Присутствует в нашем билдере (13 событий), в таблице документации
нет. Подтверждено в Infostart-сообществе как event платформы 8.3.24+. Более поздние версии
обновили список — наш инструмент актуальнее документации.

---

## Итог по тестам

| Suite | До сессии | После сессии |
|---|---|---|
| Frontend unit (`vitest`) | 50/50 | 50/50 (2 теста обновлены под правильные значения) |
| TypeScript (`tsc --noEmit`) | 0 ошибок | 0 ошибок |
| Backend + Server | без изменений | без изменений |

---

## Технический долг закрыт

| TD | Описание | Статус |
|---|---|---|
| TD-S10-duration | Duration units 100× занижены | ✅ закрыт `38d423a` |
| TD-S10-tooltips | Тёмные тултипы, undefined CSS-токены | ✅ закрыт `6c0bb98` |
| TD-S10-save | writeTextFile без permissions, ложный ✓ | ✅ закрыт `825f770` |

---

## Открытые вопросы для архитектора

### Q1. Права UAC при записи в `C:\Program Files\...`

Сейчас `writeTextFile` с Tauri permission `**` записывает напрямую. Если целевая папка
требует прав администратора (например, стандартный путь `C:\Program Files\1cv8\conf\`),
Tauri бросит access denied — ошибка всплывёт в UI нативным диалогом.

Варианты решения в Sprint 11+:
- **A.** Показать пользователю кнопку «Открыть папку» (shell reveal) после успешного сохранения — пусть вручную копирует из Downloads в Program Files. Минимальный UI.
- **B.** Добавить Tauri command (Rust) `write_file_as_admin` через Windows API `ShellExecuteEx(runas)`. Средняя сложность — UAC промпт появится от имени нашего процесса.
- **C.** Рекомендовать сохранять в `%USERPROFILE%\Documents\` и описать шаги копирования в onboarding-доке. Zero-code, подходит как временное решение.

Текущее поведение (save куда угодно, access denied если нет прав) — приемлемо для тестового
релиза. Для продакшена рекомендую вариант **C** на Sprint 11 + **B** на Sprint 12.

### Q2. Полнота CSS design-token контракта

Инцидент с `--o-surface` показывает: список токенов в `optimyzer-design.css` не является
исчерпывающим и «открытым» для дополнений. Рекомендую зафиксировать policy:

> Никаких новых `--o-*` токенов вне `optimyzer-design.css`. Перед использованием токена
> в компоненте — проверить что он определён в `:root`. Если нет — добавить в тот же PR.

Это легко проверяется grep-ом при code review: `grep --o- *.module.css | grep -v 'var(--o-'`
нашёл бы `--o-surface` без определения в design файле.

### Q3. Тест на реальное сохранение файла

В текущем тестовом плане нет ни одного теста который проверяет `writeTextFile` реально
создаёт файл. Все 50 unit-тестов — чистая логика без Tauri API. Для Sprint 11 стоит
добавить integration smoke test: запустить `tauri dev`, нажать Save, проверить файл в
`%TEMP%`. Можно автоматизировать через Playwright + `@tauri-apps/api/path`.

---

## Файлы изменённые в сессии

| Файл | Тип изменения | Bug |
|---|---|---|
| `frontend/src/features/tj-config-builder/xmlSerializer.ts` | bugfix `× 100` | #1 |
| `frontend/src/features/tj-config-builder/__tests__/xmlSerializer.test.ts` | update expected values | #1 |
| `frontend/src/features/tj-config-builder/components/XmlPreview.module.css` | replace dark fallback | #2 |
| `frontend/src/features/tj-config-builder/components/EventHelp.module.css` | replace dark fallback | #2 |
| `frontend/src/styles/optimyzer-design.css` | add `--o-surface*`, `--o-input` tokens | #2 |
| `frontend/src-tauri/capabilities/default.json` | add `fs:allow-write-text-file` | #3 |
| `frontend/src/features/tj-config-builder/components/XmlPreview.tsx` | remove Blob fallback + false setSaved | #3 |
| `scripts/patch-logcfg-for-plans.ps1` | fix misleading comment (value="10" = 1 мс, не 100 мс) | #1 side-effect |
