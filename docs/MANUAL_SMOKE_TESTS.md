# Manual Smoke Tests — Sprint 2

> **Цель:** провести по всем Sprint 2 фичам через UI и убедиться что они работают вместе.
> **Время прогона:** ~15-20 минут.
> **Когда делать:** перед demo recording / перед employment showcase.

---

## 0. Setup

1. Открыть PowerShell в `D:\1C-Optimyzer\1c-optimyzer\`
2. Запустить `.\start.bat`
3. Дождаться открытия окна 1C-Optimyzer (~3-5 сек cold start)
4. Если архив не загружен — увидеть EmptyState с "Загрузите логи ТЖ"

**Загрузить тестовый архив:**
- Drag-drop папки `D:\1C-Optimyzer\1c-optimyzer\logs` в окно ИЛИ
- Нажать «Загрузить папку с логами…» в TopBar → выбрать папку

**Ожидание:**
- ProgressCard в правом верхнем углу с растущим счётчиком событий
- В центре экрана (SQL Console EmptyState) — крупный счётчик `+1 +10` который не замирает
- После завершения — toast "Загружено N событий"
- Status в TopBar: "Готово · DuckDB"

---

## 1. Phase B — SQL Console

**Где:** Sidebar → ANALYZE → SQL Console (или нажать `Ctrl+1`)

### 1.1 Default SQL
- В editor видим preset SELECT по events (Top slow queries) с syntax highlighting
- Цвет ключевых слов (SELECT/FROM/WHERE/ORDER BY) — тёмно-синий или teal
- Колонки `events` / `ts` / `duration_us` подсвечиваются

### 1.2 Run
- Нажать `Ctrl+Enter` (или кнопку «Выполнить»)
- **Ожидание:** через <1 сек появляется таблица с 100 строками, в подзаголовке "N строк · M мс"

### 1.3 Autocomplete
- Поставить курсор после `FROM ` (с пробелом)
- Начать печатать `eve` — должно появиться предложение `events`
- После `SELECT ` Ctrl+Space — список колонок (ts, duration_us, event_type, ...)

### 1.4 Read-only защита
- Заменить query на `DELETE FROM events;`
- Нажать `Ctrl+Enter`
- **Ожидание:** красный error toast "Запрещённое ключевое слово: DELETE. Разрешены только SELECT."
- Заменить на `CREATE TABLE foo (a INT);` → та же ошибка про CREATE
- Заменить на `SELECT 1; DELETE FROM events;` → ошибка "Поддерживается только один SQL-запрос за раз"

### 1.5 Bad SQL
- Заменить на `SELECT FROM WHERE`
- **Ожидание:** error toast (или панель error) с DuckDB сообщением о syntax error

### 1.6 Raw JSON tab
- Запустить успешный SELECT
- Переключиться на вкладку «Сырой JSON»
- **Ожидание:** видим pretty-printed JSON с `ok: true, columns, rows, executed_ms`

---

## 2. Phase F — SQL Templates

**Где:** SQL Console → внизу bar → «ШАБЛОНЫ» dropdown

### 2.1 Templates list
- Открыть dropdown
- **Ожидание:** видим 4-5 категорий tabs (Производительность / Блокировки / Ошибки / Память / Статистика)
- В первой категории 3-4 темплейта

### 2.2 Load template
- Кликнуть «Топ 100 медленных SQL запросов»
- **Ожидание:** в editor загружается новый SQL, dropdown закрывается
- Ctrl+Enter → результат загружается

### 2.3 Categories
- Открыть dropdown, переключить на «Блокировки»
- Кликнуть «Дедлоки по часам»
- **Ожидание:** в editor SQL с `date_trunc('hour', ts) AS hour, COUNT(*) AS deadlocks ...`

---

## 3. Phase D — Pre-built Views

### 3.1 Slow Queries (Ctrl+2)
- Кликнуть в Sidebar «Медленные запросы» (или `Ctrl+2`)
- **Ожидание:** таблица топ-100 DBMSSQL агрегатов с колонками # / Запрос / Calls / Σ ms / avg ms / max ms / Σ rows
- В header subtitle: "N запросов · выполнено за M мс"
- Hover на queryitem — full SQL в title

### 3.2 Locks Timeline (Ctrl+3)
- **Ожидание:** LineChart с двумя сериями (Locks тёмно-теал, Deadlocks красный)
- Если в архиве нет блокировок — empty state "Нет блокировок"
- В subtitle: "X locks · Y deadlocks"

### 3.3 Process Roles (Ctrl+4)
- **Ожидание:** Donut chart слева + таблица per-role метрик справа
- Слайсы donut'а имеют разные цвета (rphost, rmngr, ragent, ...)

### 3.4 Duration Histogram (Ctrl+5)
- **Ожидание:** Bar chart с 7 бакетами (<1 мс, 1-10 мс, …, >60 с)
- Y-ось логарифмическая (маленькие бакеты видны)
- Под графиком таблица с count + percent

### 3.5 Errors Feed (Ctrl+6)
- **Ожидание:** scrollable таблица с EXCP/TDEADLOCK/TLOCK events
- Type badge цветной: красный для EXCP/TDEADLOCK, янтарный для TLOCK
- В правом верхнем углу dropdown «Все типы / EXCP / TDEADLOCK / TLOCK»
- Переключение фильтра меняет содержимое (без перезагрузки страницы)

### 3.6 Activity Heatmap (Ctrl+7)
- **Ожидание:** 7×24 SVG grid (понедельник-воскресенье × часы 00-23)
- Интенсивность цвета — от белой до тёмно-теал
- Hover на cell → tooltip с «Пн 14:00 · N событий»
- В правом верхнем dropdown переключения метрики (count / total duration / peak / errors)

---

## 4. Phase E — Cross-Filtering

### 4.1 Click in Donut
- Открыть Process Roles
- Кликнуть на самый большой slice donut'а (обычно `rphost`)
- **Ожидание:** в FilterBar над контентом появляется chip «Роль: rphost [×]»

### 4.2 Filter propagation
- Перейти на Slow Queries (Ctrl+2)
- **Ожидание:** chip «Роль: rphost» всё ещё виден; таблица содержит только rphost-запросы
- Перейти на Errors Feed → тоже только rphost events

### 4.3 Clear filter
- В FilterBar нажать `×` рядом с chip
- **Ожидание:** chip исчез, таблица перезагрузилась с полным набором
- Альтернатива: «Очистить всё» справа сбрасывает все фильтры

### 4.4 Heatmap → time filter
- Activity Heatmap → кликнуть на яркую cell (например 14:00 четверг)
- **Ожидание:** FilterBar получает chip «Время: 14:00 — 15:00 [×]»
- Перейти на Locks Timeline → видим только bucket'ы в этот час
- Snять filter → видим весь timeline

---

## 5. Phase H — Export

### 5.1 CSV export
- Slow Queries → правый верхний «Экспорт» dropdown
- **Ожидание:** 3 формата: CSV / TSV / JSON
- Кликнуть CSV → Save dialog
- Сохранить как `D:\Desktop\slow_queries.csv`
- Открыть в Excel/LibreOffice → видим header + строки

### 5.2 JSON export
- Activity Heatmap → Экспорт → JSON
- Сохранить как `activity.json`
- Открыть в Notepad — pretty-printed `{columns, rows, exported_at}`

### 5.3 Filtered export
- Установить фильтр (например через Donut click)
- Slow Queries → Экспорт CSV
- **Ожидание:** в CSV только rphost-запросы (то что показано в UI)

---

## 6. Phase G — Multi-archive Comparison

### 6.1 Load second archive
- Текущий архив уже загружен через `D:\...\logs`
- Открыть Sidebar → SQL Console (Ctrl+1)
- В TopBar кликнуть на archive name dropdown (с counter событий)
- **Ожидание:** видим dropdown ArchivesMenu с текущим архивом
- Кликнуть «Загрузить новую папку…»
- Выбрать **ту же папку** `D:\...\logs` ещё раз (для self-comparison)
- Дождаться окончания ingest второго архива

### 6.2 Compare
- Sidebar → CONFIG → «Сравнение архивов» (Ctrl+8)
- **Ожидание:** два ArchivePicker dropdown'а (A и B)
- Выбрать в A первый archive, в B второй
- **Ожидание:** автоматически запускается compare через 1-2 сек
- Tab «Сводка»: таблица метрик с delta = 0 (self-comparison)
- Tab «Slow Queries»: «Различий не найдено»

### 6.3 Real diff (optional)
- Загрузить ещё одну папку с другими логами (если есть)
- Поставить A = старый, B = новый
- В Slow Queries Diff — если есть регрессии, они в красном секции «Регрессии»

---

## 7. Phase I + J — Sidebar и Shortcuts

### 7.1 Sidebar layout
- Открыть Sidebar (если свернут)
- **Ожидание:** ANALYZE group первой, содержит 7 enabled items (SQL Console / Медленные / Блокировки / Роли / Длительности / Ошибки / Активность)
- CONFIG: «Сравнение» enabled
- Остальные items disabled с tooltip «Доступно в будущих обновлениях»

### 7.2 Keyboard shortcuts
- `Ctrl+K` → Command Palette открывается
- `Esc` → закрывается
- `Ctrl+1` → SQL Console
- `Ctrl+2` → Slow Queries
- `Ctrl+8` → Comparison
- `Ctrl+9` → не должно ничего делать (не привязано)

---

## 8. Archive Management

### 8.1 List archives
- TopBar → кликнуть на archive name → ArchivesMenu
- **Ожидание:** список загруженных архивов, размер каждого, "текущий" badge на active

### 8.2 Delete single
- В ArchivesMenu → нажать `×` рядом с архивом
- Confirm dialog → «Удалить»
- **Ожидание:** архив удалён, освобождено N байт
- Если удалён active — Sidebar показывает empty state

### 8.3 Delete all
- ArchivesMenu → «Очистить всё» внизу
- Confirm dialog с числом архивов и размером
- **Ожидание:** все архивы удалены, toast "Удалено N архивов · освобождено M ГБ"

---

## 9. Что в этом списке НЕ покрыто

Дальше — фичи которые **уже работают** но требуют отдельного внимания только при demo:

- **Saved queries** (внизу SQL Console: «Сохранить» / «СОХРАНЁННЫЕ» dropdown) — save/load/delete текущий SQL
- **Drag-and-drop одной папкой** — отдельная проверка drop overlay
- **Live progress counter** во время ingest большого архива (≥1 ГБ) — должен расти каждые 250мс
- **Welcome state** при первом запуске на чистой системе (без archives в SQLite) — показывает «Загрузите папку»

---

## 10. Что делать если что-то сломано

1. Записать **точный repro**: какой view, какие clicks, какой actual vs expected
2. Запустить `pwsh scripts\run-backend-tests.ps1` — если backend tests падают, проблема в backend
3. Открыть DevTools (F12 в окне Tauri если включен) — посмотреть console errors
4. Зафиксировать как issue в репо или в этот файл

---

**Если все пункты 1-8 прошли — Sprint 2 готов к demo recording и portfolio показу.**
