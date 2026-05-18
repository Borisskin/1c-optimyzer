# Sprint 0 Closure Notes — для архитектора Opus

> Дополнение к `OPUS_HANDOVER_SPRINT_0.md`. Описывает то, что произошло **после** handover'а:
> финальные правки запуска, успешный smoke test, и **3 критичных замечания пользователя**,
> переопределяющих scope Sprint 1.

**Дата закрытия:** 2026-05-18, 16:09 MSK.
**Smoke test (DoD #18 из Sprint 0):** ✅ закрыт — окно Tauri открылось, sidebar/topbar/statusbar/OQL Console отрисованы корректно.

---

## TL;DR для архитектора

1. **Sprint 0 smoke test закрыт** — приложение запускается одной командой `.\start.bat` из PyCharm terminal.
2. **Найдено 3 P0-замечания от пользователя**, требующих включения в scope Sprint 1:
   - **(P0) Локализация:** весь UI на английском — нужен перевод на русский.
   - **(P0 bug) Drag-and-drop .zip не работает:** drop файла в окно не вызывает обработчик.
   - **(P0 архитектурное):** **папка с подпапками** должна быть основным способом загрузки логов, а не zip-архив. Реальные клиенты не пакуют логи специально — это антипаттерн. У пользователя 11 ГБ логов в файловой структуре.
3. Предложенный в `OPUS_HANDOVER_SPRINT_0.md` scope Sprint 1 (OQL DSL + CodeMirror) сохраняет приоритет, но **должен быть расширен** этими 3 пунктами или часть OQL-фич сдвинута в Sprint 2.

---

## Что было сделано в финальной сессии (запуск)

После того как код Sprint 0 был зафиксирован, потребовалось пройти `npm install` + первую сборку `cargo build` на Windows. Это вскрыло ряд инфраструктурных проблем, которые я закрыл:

### 1. Запуск из PyCharm terminal — `start.bat` в корне

**Контекст:** пользователь работает из PyCharm terminal (PowerShell), не хочет переключаться на VS Developer Prompt или signoff/reboot. Требование — **одна команда**.

**Решение:** [start.bat](start.bat) в корне репозитория.
```bat
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
cd /d "%~dp0frontend"
npm run tauri dev
```

Подводный камень: `vcvars64.bat` **перезаписывает** PATH целиком (включая `~/.cargo/bin`). Поэтому после его вызова нужно явно вернуть путь к cargo.

Дополнительно `scripts/tauri-dev.cmd` оставлен как verbose-вариант с error checking, но основной entry point — `start.bat` в корне.

### 2. Permanent MSVC env in user profile

Чтобы будущие сессии (после relogin) видели MSVC сразу без `start.bat`, в user profile через `[Environment]::SetEnvironmentVariable(..., 'User')` записаны:
- PATH (16 MSVC/SDK entries, включая `HostX64\x64`, Windows Kits 10)
- INCLUDE, LIB, LIBPATH
- VCINSTALLDIR, VCToolsInstallDir, VCToolsVersion
- WindowsSdkDir, WindowsSDKVersion, WindowsSDKLibVersion, UCRTVersion, UniversalCRTSdkDir
- VSINSTALLDIR, DevEnvDir
- Platform, VSCMD_ARG_HOST_ARCH, VSCMD_ARG_TGT_ARCH

⚠️ **NB:** уже запущенные процессы (`claude.exe`, текущий PowerShell, PyCharm) этих переменных не видят — они кэшируют env при старте. После relogin они подхватятся, но в текущей сессии работа идёт через `start.bat`.

### 3. Иконка приложения

`tauri-build` требует `frontend/src-tauri/icons/icon.ico` для генерации Windows Resource file. Файла не было.

**Решение:** сгенерировал [icon.ico](../frontend/src-tauri/icons/icon.ico) (6.6 КБ, 7 размеров: 16, 24, 32, 48, 64, 128, 256) программно через PowerShell + `System.Drawing` — синий фон #4A90E2, белые буквы `1C`. Не финальный дизайн — placeholder до Sprint 3 (брендинг).

### 4. Удаление `externalBin` из tauri.conf.json

`externalBin: ["binaries/optimyzer-backend"]` в `tauri.conf.json` требует **уже собранного** PyInstaller-бандла на этапе сборки Tauri shell. В Sprint 0 бандл не делается (Sprint 3 plan per ARCHITECT_NOTES.md).

**Решение:** убрал поле `externalBin` из `tauri.conf.json`. Sidecar в dev запускается как `python -m optimyzer_backend` через `Command::new()` напрямую (см. ниже).

⚠️ **Для Sprint 3 / production bundle:** когда появится PyInstaller-бандл, `externalBin` нужно вернуть с правильным именем (`binaries/optimyzer-backend-x86_64-pc-windows-msvc.exe` для Windows MSI target).

### 5. Sidecar: исправлены 2 бага в `sidecar.rs`

**Баг 1:** `current_dir()?.join("../backend")` от cwd cargo (`frontend/src-tauri/`) даёт несуществующий `frontend/backend`. Реальный путь — `1c-optimyzer/backend`.
**Фикс:** через `env!("CARGO_MANIFEST_DIR")` — теперь путь компилируется как абсолютный и не зависит от cwd.

**Баг 2:** sidecar звал системный `python`, в котором не установлены `duckdb`, `pyparsing` и прочие зависимости backend. В системном PYTHONPATH этих пакетов нет, а в `backend/.venv/` они стоят.
**Фикс:** добавлен fallback — сначала ищется `backend/.venv/Scripts/python.exe` (Windows) / `backend/.venv/bin/python` (Unix), если есть — используется он, иначе системный `python`.

См. [frontend/src-tauri/src/sidecar.rs](../frontend/src-tauri/src/sidecar.rs).

---

## Критичные замечания пользователя (NEW INPUT для Sprint 1)

Эти 3 пункта появились в момент первого визуального контакта с приложением и являются P0 для Sprint 1.

### 1. Локализация UI на русский (P0)

**Текущее состояние:** весь UI на английском — дизайн портирован из `design/opt/*.jsx` 1:1 (английские строки в дизайн-концепте).

**Что нужно перевести (по скриншоту первого запуска, неполный список):**

- **TopBar:** `Load TZ archive...`, `Search anything...`, `Idle`, `AI Pro`
- **Sidebar items (18 экранов):** все английские названия — `Manage`, `Connections`, `Diagnostics`, `Profiles`, `Alerts`, `Cluster`, ..., `OptimyzerQL Console`
- **OQL Console header:** `free tier`, `Sprint 0 · preset only`, `declarative query language over technical journal · DSL parser — Sprint 1`
- **Editor chrome:** `read-only`, `ln · col · rows`
- **Result tabs:** `Table`, `Chart`, `Timeline`, `Raw JSON`
- **Empty state:** `Load a TZ archive to start querying`, `Drag-and-drop .zip into the window, or click below`, `Load TZ archive...`
- **Bottom bar:** `PRESETS`, `First 100 events`, `Longest 100 events`, `Deadlocks`
- **StatusBar:** `idle · no archive loaded`, `DuckDB: 0 events`, `SAVED · SPRINT 2`, `v0.1.0-dev`
- **Buttons:** `Templates`, `Docs`, `Share`, `Run`
- **Toasts** (если есть): все сообщения

**Архитектурный вопрос для Opus:**
- A) Hardcoded ru-RU strings (быстрее, проще, MVP-уровень).
- B) i18n-фреймворк (`react-i18next` или `lingui`) — задел на en-US/ru-RU/etc для коммерческой версии.

Учитывая, что Sergey — соло-фаундер и Module 1 = "локальный standalone tool для русскоязычных 1С-экспертов", **вариант A практичнее**. i18n можно добавить в Module 2+ когда станет ясна география пользователей.

⚠️ **Дизайн-документы (`design/opt/*.jsx`) тоже нужно обновить** или зафиксировать в ADR: "design-файлы — английский reference; production strings — русский".

### 2. Bug: drag-and-drop .zip не работает (P0)

**Симптом:** пользователь перетаскивает `.zip` в окно приложения — не происходит **ничего** (нет toast'а, нет прогресс-индикатора, статус остаётся `idle · no archive loaded`).

**Я НЕ диагностировал** этот баг (пользователь сказал «больше ничего не делай, пиши отчёт»). Гипотезы для расследования в Sprint 1:

1. **Tauri 2 drag-and-drop event** в `tauri.conf.json` — нужен `dragDropEnabled: true` на window. Сейчас в конфиге его нет (default может отличаться от Tauri 1).
2. **Frontend handler** в `frontend/src/components/overlays/DropZone.tsx` (или эквивалент) может слушать DOM `dragover`/`drop` events — но Tauri 2 поглощает их и эмиттит **свои** через `onDragDropEvent` API. DOM-listener не сработает.
3. **CSP** в `tauri.conf.json` — `connect-src 'self' ipc: http://ipc.localhost` — но для drop файлов из ОС CSP не должен мешать.
4. **Click на кнопку `Load TZ archive...` тоже не проверен** пользователем — возможно баг шире (вообще загрузка не работает, не только drag-and-drop).

**Что нужно архитектору решить:**
- Использовать Tauri 2 native drag-and-drop API (`onDragDropEvent`) или поднимать DOM events явно в `tauri.conf.json`?
- Стандартизировать flow: drop → frontend получает path → `backend.load_archive(path)` через RPC → backend парсит → progress events назад во frontend.

### 3. Архитектурный сдвиг: folder ingestion как основной способ (P0)

> Цитата пользователя:
> «у меня общие логи размером 11 Гб - надо предусмотреть не только архивы (это даже вряд ли будут делать - какой смысл предварительно упаковывать, чтобы программа потом распаковывала) - а лучше указывать папку с подпапками и логами, а программа будет ее рекурсивно обходить и читать логи».

**Это меняет основной use case.** В Sprint 0 фокус был на zip-архивах (`backend/archive/extractor.py` с zip-slip защитой), а реальный workflow клиентов 1С:

- Технологический журнал 1С пишется регулярно (например, по часам) в структуру вида:
  ```
  D:\logs-1c\rphost_1234\
  ├── 26050118.log
  ├── 26050119.log
  ├── 26050120.log
  ├── ...
  D:\logs-1c\rphost_5678\
  ├── 26050118.log
  ├── ...
  ```
- Размер реальных кейсов — 10+ ГБ.
- Никто не пакует их в zip ради анализа. Это лишняя итерация (упаковать → разархивировать) на 11 ГБ — медленно и бессмысленно.

**Что нужно (предложение для Sprint 1 — финальное решение за архитектором):**

1. **Новый RPC метод** `load_directory(path: str) → archive_id` — рекурсивный обход `path`, фильтр по `*.log` (или сигнатуре первой строки `\d{2}:\d{2}\.\d+,...`), стриминговая обработка файлов.
2. **`load_archive(zip_path)` оставить** как опцию для legacy-кейсов / экспорта от поддержки 1С (иногда логи пересылают в zip).
3. **UI:**
   - Кнопка переименовать: `Load TZ archive...` → `Загрузить ТЖ...` (dropdown с 2 пунктами: «Папка с логами», «ZIP-архив»).
   - Drop zone в окне принимает и папки, и файлы.
4. **Backend изменения:**
   - `archive/extractor.py` → переименовать в `ingest/` или `sources/`. Внутри 2 импла: `ZipSource` (текущий) и `DirectorySource` (новый).
   - Унифицированный интерфейс: `iter_log_files() → Iterator[LogFile]`.
   - **Streaming:** нельзя загружать все 11 ГБ в память. Парсер должен работать построчно через `pathlib.Path.open(buffering=...)`.
5. **Progress reporting:**
   - Backend эмиттит JSON-RPC notifications `progress` (без id) с полями `{processed_bytes, total_bytes, files_done, files_total}`.
   - Frontend подписывается, обновляет прогресс-бар в TopBar / StatusBar.

**Влияние на DuckDB:**
- 11 ГБ raw логов → возможно 50–200 млн событий → DuckDB ≈ 5–20 ГБ.
- `executemany` (Sprint 0) **точно не справится** на таком объёме. Нужен **DuckDB Appender API** (упомянуто в `ARCHITECT_NOTES.md` как Sprint 2 backlog — теперь становится Sprint 1 must-have, минимум для папок).
- Path к `.duckdb` файлу — в Settings (Sprint 3 plan, но для 11+ ГБ может потребоваться раньше: пользователь захочет указать диск D:\).

**Acceptance gate Sprint 1 обновляется:**
- Sprint 0 gate (`≥95% events parsed from real archive`) **становится частью** load_directory acceptance.
- Q1 (real archive fixture) **расширяется** до Q1': папка с реальными логами от Сергея (~11 ГБ). Очевидно, целиком в `backend/tests/fixtures/` его класть нельзя — нужна отдельная стратегия для big-data acceptance (отдельный диск, не в репо, путь в `.env.test`).

---

## Обновлённый scope Sprint 1 (предложение для Opus)

Старый scope из `OPUS_HANDOVER_SPRINT_0.md`:
- OQL parser, OQL compiler → SQL, CodeMirror, autocomplete, templates library, saved queries, validate RPC.

**Перевзвешено с учётом новых P0:**

### Must-have (P0)

1. **Folder ingestion** (новое) — `load_directory` RPC, `DirectorySource`, streaming-парсинг, progress events.
2. **DuckDB Appender API** (повышенный приоритет) — без него 11 ГБ не пройдут.
3. **Locale ru-RU pass** (новое) — все строки переведены на русский. Decision A vs B (i18n) — от архитектора.
4. **Drag-and-drop fix** (баг) — диагностика + фикс. Поддержка drop папок, не только zip.
5. **OQL parser + compiler** (исходный план) — но возможно урезать scope (без `join code_graph`, без `metrics` — заглушки).
6. **CodeMirror editor** (исходный план) — обязателен для useful experience.

### Should-have (P1)

7. Autocomplete (sources, operators, schema fields).
8. Templates library в bottom bar.
9. Saved queries (SQLite + UI).

### Nice-to-have (defer to Sprint 2 если не успеваем)

10. `validate_oql_query` RPC + inline error markers.

### Acceptance gate Sprint 1

- ✅ Загрузка реальной папки с логами Сергея (~11 ГБ), ≥95% events parsed без exceptions.
- ✅ OQL query `events | take 100` выполняется и возвращает результат.
- ✅ UI полностью на русском (по приёмочному обходу 5 главных экранов).
- ✅ Drag-and-drop папки в окно работает.

---

## Открытые вопросы (дополнение к docs/QUESTIONS.md)

### Q6 (P0): Locale strategy
A) Hardcoded ru-RU. B) i18n framework (react-i18next/lingui).
**Моя рекомендация:** A для Sprint 1, B — в Module 2+ когда понятна аудитория.

### Q7 (P0): Big-data fixture strategy
Как тестировать 11 ГБ acceptance, если в репо такое не положишь? Варианты:
- A) Отдельный путь в `.env.test`, фикстура лежит у Сергея локально.
- B) Сэмпл (1 ГБ) в git LFS.
- C) Генерируемый synthetic dataset 10 ГБ через скрипт (но это не real-data).
Лучше A — для acceptance нужен **именно real-data**, не synthetic.

### Q8 (P1): Прогресс-бар UX
Где показывать прогресс долгой загрузки?
- A) Modal с прогресс-баром (блокирует UI на 10+ минут — плохо).
- B) Inline в StatusBar (показано в дизайне, минимально инвазивный).
- C) Notification в правом верхнем углу + StatusBar.
Скорее всего C — пользователь может работать с уже загруженным (если есть) пока новые логи обрабатываются.

### Q9 (P2): Каскадная загрузка
Что если пользователь загружает 2-ю папку поверх первой? Replace / append / новая «сессия»? В дизайне не отражено.

---

## Структура запуска (актуально для следующей сессии)

```
D:\1C-Optimyzer\1c-optimyzer\
├── start.bat                          ← PyCharm: .\start.bat
├── scripts\
│   ├── tauri-dev.cmd                  ← verbose alternative с error checking
│   ├── setup-backend.ps1
│   └── ...
├── backend\
│   └── .venv\Scripts\python.exe       ← venv с duckdb, pyparsing и т.д.
├── frontend\
│   ├── package.json
│   └── src-tauri\
│       ├── tauri.conf.json            ← externalBin удалён (Sprint 0)
│       ├── icons\icon.ico             ← placeholder, 6.6 КБ
│       └── src\sidecar.rs             ← путь через CARGO_MANIFEST_DIR, venv detection
└── docs\
    ├── SPRINT_0_REPORT.md
    ├── OPUS_HANDOVER_SPRINT_0.md
    ├── SPRINT_0_CLOSURE_NOTES.md      ← этот файл
    ├── DECISIONS.md
    ├── QUESTIONS.md (нужно дополнить Q6-Q9)
    └── ARCHITECT_NOTES.md
```

---

## Что архитектор должен сделать перед Sprint 1 prompt

1. **Прочитать этот файл + `OPUS_HANDOVER_SPRINT_0.md`** в указанном порядке.
2. **Решить Q6** (locale strategy) — это влияет на оценку трудоёмкости.
3. **Уточнить у Сергея Q7** (где лежит 11 ГБ фикстура, есть ли возможность дать к ней доступ).
4. **Решить trade-off:** OQL parser полный vs урезанный (без `code_graph`/`metrics` joins). Полный OQL + folder ingestion + locale + appender — возможно не уложится в спринт.
5. **Спроектировать Sprint 1 prompt** для исполнителя с учётом расширенного scope.

---

## Git state

- Ветка: `feat/sprint-0-foundation`
- Базовая ветка: `main`
- **NB:** правки финальной сессии (start.bat, icon.ico, sidecar.rs fixes, tauri.conf.json: externalBin removed) **ещё не закоммичены**. Перед PR нужно отдельный коммит `chore: dev startup fixes (Windows MSVC, sidecar paths, icon)`.

---

**Готово к Sprint 1 prompt.** Никаких blocking-вопросов для старта дизайна нет — Q6/Q7 нужны для уточнения оценки, но проектирование можно начинать без них.
