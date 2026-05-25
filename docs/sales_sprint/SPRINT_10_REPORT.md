# Sprint 10 — TJ Config Builder: Итоговый отчёт

**Дата:** 2026-05-25  
**Тег:** `v0.10.0-internal`  
**Тип спринта:** Feature sprint — подготовительный инструмент

---

## Краткий итог

Sprint 10 добавляет экран «Конструктор logcfg.xml» — первый инструмент в группе ПОДГОТОВКА.
Цель: пользователь выбирает или строит настройку технологического журнала 1С, получает
готовый logcfg.xml одним кликом. Без правки файлов вручную, без знания XML-синтаксиса.

**Тесты до → после:**
- Frontend unit tests: 72 → 121 (+49: xmlSerializer 21 + volumeEstimator 14 + templates 14)
- Backend RPC: +9 (test_logcfg_rpc.py)
- Server AI: +20 (test_ai_generate_logcfg.py)
- **Итого: +78 новых тестов**

**TypeScript:** 0 ошибок. `tsc --noEmit` чистый.

---

## Phase A — Server AI endpoint + Backend RPC

### Server: `/v1/ai/generate_logcfg`

**`server/schemas/ai.py`** — новые Pydantic модели:
```
EventConfig          — { enabled: bool, threshold_cs?: int }
LogcfgEvents         — 13 полей (CALL..TTIMEOUT), все Optional[EventConfig]
LogcfgConfig         — events + capture_plans + log_directory + max_size_gb
EventRationale       — { event, threshold, why }
LogcfgGenerateRequest  — problem_description (10–2000) + platform_version + dbms
LogcfgGenerateResponse — config + explanation + events_rationale + estimated_use_duration
                         + warnings + model_used + duration_ms
```

**`server/services/ai_explainer.py`** — `generate_logcfg()`:
- Модель: `claude-haiku-4-5` (быстро, дёшево для структурированной генерации)
- System prompt: эксперт по ТЖ 1С, знает все 13 событий, пороги в centiseconds
- Фильтрация неизвестных событий AI (known_events Set) — защита от галлюцинаций
- Retry на invalid JSON: до 2 попыток с explicit "ответь ТОЛЬКО JSON"
- Graceful degradation: если AI недоступен → объяснение ошибки в response

**`server/api/routers/ai.py`** — `POST /v1/ai/generate_logcfg`:
- 503 при AiNotConfiguredError (нет ANTHROPIC_API_KEY)
- 502 при AiExplainerError (AI вернул ошибку / timeout)

**`server/tests/test_ai_generate_logcfg.py`** — 20 тестов:
- TestGenerateLogcfgSuccess (5): basic, explanation, capture_plans, both_db_events, platform_version
- TestEventFiltering (2): unknown_event_ignored, disabled_event
- TestGenerateLogcfgErrors (5): no_api_key, invalid_json_retry, both_invalid, empty_events, missing_config
- TestLogcfgSchemas (7): Pydantic validation

### Backend RPC: `logcfg.detect_platform`

**`backend/rpc/logcfg_rpc.py`** — три стратегии определения версии 1С:
1. **Strategy 1 — Folder scan** (confidence=high): сканирует `C:/Program Files/1cv8`
   и `C:/Program Files (x86)/1cv8`, берёт наибольшую версию по semver.
2. **Strategy 2 — TCP probe** (confidence=medium): localhost:1541 (rphost агент).
   Если порт открыт — сервер 1С запущен, версию возвращаем эвристически из folders
   или константу 8.3.24.
3. **Strategy 3 — Fallback** (confidence=low): константа 8.3.24 как safe default.

**`backend/tests/test_logcfg_rpc.py`** — 9 тестов:
- TestDetectPlatformRpc (7): single_version, multiple_versions_highest, no_versions_agent_alive,
  nothing_found_fallback, base_path_not_exists, ignores_non_version_dirs, version_format
- TestProbeTcp (2): failure, invalid_host

---

## Phase B — Frontend: types, xmlSerializer, volumeEstimator, templates

### `features/tj-config-builder/types.ts`

```typescript
EventType = "CALL"|"SCALL"|"SDBL"|"DBMSSQL"|"DBPOSTGRS"|"TDEADLOCK"|"TLOCK"|
            "EXCP"|"EXCPCNTX"|"ADMIN"|"MEM"|"ATTN"|"TTIMEOUT"
EVENTS_WITH_DURATION: Set<EventType>  — события с полем Duration (для поля порога)
LogcfgConfig   — events + capture_plans + log_directory + max_size_gb
Template       — id + name + description + estimated_volume + volume_hint + config
VolumeEstimate — quiet + typical + busy (МБ/ч) + warning_if_too_large
```

### `features/tj-config-builder/xmlSerializer.ts`

Pure TypeScript без XML-библиотек. Генерирует канонический `logcfg.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">
  <log location="C:\1C-TechLog" history="24">
    <event><eq property="Name" value="CALL"/><gt property="Duration" value="100"/></event>
    <property name="all"/>
    <property name="plansqltext"/>  <!-- если capture_plans -->
  </log>
  <plansql/>  <!-- если capture_plans -->
</config>
```

21 unit-тест: корректность XML header, namespace, location escape, threshold=0 без `<gt>`,
disabled events пропускаются, capture_plans adds plansqltext + plansql, escapeXml для спецсимволов.

### `features/tj-config-builder/volumeEstimator.ts`

Heuristic-оценка объёма логов (МБ/час) для трёх уровней нагрузки (×0.1 / ×1.0 / ×3.0):
- `EVENTS_PER_MINUTE` + `AVG_SIZE_BYTES` для каждого события
- `thresholdMultiplier(cs)` — 5 уровней: 0→1.0, 1→0.5, 100→0.2, 1000→0.05, 10000→0.01
- `planSizeMultiplier` — DBMSSQL/DBPOSTGRS с capture_plans ×4
- `warning_if_too_large` = busy > 1000 МБ/час (1 ГБ/ч)

14 unit-тестов: empty config → 0, disabled events → 0, threshold reduction, plans multiplier,
warning threshold, formatVolume (< 1 МБ/ч, МБ/ч, ГБ/ч).

### `features/tj-config-builder/templates.ts`

6 встроенных шаблонов (`BUILTIN_TEMPLATES`):

| id | Название | Объём | Описание |
|----|----------|-------|---------|
| `minimal` | Минимальный | low | EXCP + TDEADLOCK. Постоянный сбор в проде |
| `slow_operations` | Медленные операции | medium | CALL+SQL+ошибки. Стандарт для торможений |
| `full_diagnostic` | Полная диагностика | very_high | Всё + планы. Глубокое расследование |
| `deadlocks_only` | Только блокировки | medium | TDEADLOCK+TLOCK+SQL. Конфликты |
| `expert_audit` | Аудит (1С:Эксперт) | high | Канонический набор курса 1С:Эксперт |
| `pre_release_baseline` | Baseline перед релизом | low | Сравнение до/после обновления |

14 unit-тестов: 6 шаблонов exist, каждый имеет ≥1 события, volume/config structure.

---

## Phase C — UI: Graphical Builder

### Компоненты (CSS Modules, только `--o-*` tokens)

| Компонент | Назначение |
|-----------|-----------|
| `TemplatesSelector` | Горизонтальные chips с цветными dot-индикаторами объёма |
| `VolumePreview` | Sticky карточка: Тихая / Типичная / Пиковая нагрузка + предупреждение |
| `EventHelp` | CSS hover-тултип для каждого из 13 событий ТЖ (описание + когда использовать) |
| `EventRow` | Чекбокс + монospace имя + число-поле порога (cs) + help иконка |
| `EventsGroup` | Основные 8 событий + кнопка «Ещё N» без disclosure-треугольников |
| `PlansToggle` | Переключатель plansqltext с предупреждением об объёме |
| `StorageSettings` | Поле папки + лимит ГБ |
| `Actions` | Сбросить + «Скачать logcfg.xml» (Blob URL download) |
| `GraphicalBuilderTab` | Двухколоночный layout: события/настройки | sticky VolumePreview |

### UX-решения

- **Download-only**: файл скачивается через `Blob + URL.createObjectURL`. Никакого "Apply locally" — пользователь сам кладёт в нужную папку.
- **Без disclosure-треугольников** (memory rule): EventsGroup использует `useState` + кнопка-текст.
- **Threshold = пусто → null** (без ограничения): поле с placeholder `∞`, значение null → нет `<gt>` в XML.

---

## Phase D — AI Wizard

### `AiWizardTab`

Форма: textarea описания (10–2000 символов) + select СУБД + кнопка «Сгенерировать».

Вызов `cloud.aiGenerateLogcfg()` → `POST /v1/ai/generate_logcfg`:
- Loading: спиннер + текст «AI анализирует описание…»
- Done: explanation + таблица rationale (event | threshold | why) + warnings + срок сбора
- Error: читаемое сообщение (сервер недоступен / no API key / HTTP ошибка)
- Кнопка **«Применить в конструкторе»** → переключает на GraphicalBuilderTab с AI-конфигом

### `cloud.ts` — новые типы и метод

```typescript
AiLogcfgGenerateRequest   — { problem_description, platform_version?, dbms? }
AiLogcfgGenerateResponse  — { config, explanation, events_rationale, warnings, ... }
cloud.aiGenerateLogcfg()  — POST /v1/ai/generate_logcfg
```

---

## Главный экран: `TjConfigBuilderScreen`

Путь: `frontend/src/components/screens/TjConfigBuilder/TjConfigBuilder.tsx`

**Структура:**
1. Заголовок + subtitle + badge версии платформы 1С (из `logcfg.detect_platform` RPC)
2. `TemplatesSelector` — 6 chips, клик загружает конфиг шаблона
3. Два таба: «Графический конструктор» / «AI-мастер»
4. Единый `config: LogcfgConfig` state — оба таба работают с ним

**Sidebar интеграция:**
- Группа: `ПОДГОТОВКА` (первая в sidebar, выше АНАЛИЗ)
- Ярлык: `Ctrl+L`
- Иконка: `Settings2` (3 вертикальных слайдера с ручками)
- Экран доступен **без загруженного архива** (логика в App.tsx)

---

## Phase E — Документация

- `docs/sales_sprint/SPRINT_10_REPORT.md` (этот файл)
- ADR-053..056 в `docs/DECISIONS.md`
- Тег `v0.10.0-internal`

---

## Scope-out (не входило в Sprint 10)

| Фича | Причина |
|------|---------|
| Apply locally (авто-копирование файла) | Tauri fs plugin, UAC — вне scope, risk |
| Валидация пути папки логов | Nice-to-have, Sprint 11+ |
| История сохранённых конфигураций | Отдельная фича, Sprint 11+ |
| Подсказка по размеру диска (disk free) | Tauri system-info plugin, Sprint 11+ |
| Импорт существующего logcfg.xml | Парсинг XML, Sprint 11+ |

---

## Breaking Changes

Нет. Экран изолирован в `features/tj-config-builder/`. Изменения в `App.tsx`, `nav.ts`,
`appStore.ts`, `i18n/ru.ts` аддитивны и не ломают существующие экраны.

---

## Артефакты

| Путь | Тип | Описание |
|------|-----|---------|
| `frontend/src/features/tj-config-builder/` | feature module | 4 TS + 3 test files + 10 компонентов |
| `frontend/src/components/screens/TjConfigBuilder/` | screen | TjConfigBuilder.tsx + .module.css |
| `backend/src/optimyzer_backend/rpc/logcfg_rpc.py` | RPC handler | detect_platform |
| `backend/tests/test_logcfg_rpc.py` | tests | 9 unit-тестов |
| `server/schemas/ai.py` | Pydantic | LogcfgConfig + GenerateRequest/Response |
| `server/services/ai_explainer.py` | AI service | generate_logcfg() через Haiku |
| `server/api/routers/ai.py` | FastAPI | POST /v1/ai/generate_logcfg |
| `server/tests/test_ai_generate_logcfg.py` | tests | 20 unit-тестов |
