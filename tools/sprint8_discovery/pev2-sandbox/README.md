# pev2 sandbox — Sprint 8 Phase A feasibility check

## Установлено

```
npm install pev2 vue@3 d3 --no-audit --no-fund
```

Результат: **91 packages** added in ~6s. Размер `node_modules` ≈ 50 МБ.

## Как запустить demo

```powershell
# 1. Запустить локальный HTTP server (нужен для ES module imports)
cd D:\1C-Optimyzer\tools\sprint8_discovery\pev2-sandbox
npx serve .

# 2. Открыть http://localhost:3000/index.html в Chrome
```

Альтернатива: использовать `python -m http.server 8000` если есть Python.

## Что покажет demo

Файл `index.html` рендерит **pev2** компонент с реальным JSON-планом из нашей PG-разведки:
- План: `LEFT JOIN _document201 + _reference68` с фильтром по дате
- Node types в плане: `Limit`, `Nested Loop (Left Join)`, `Index Scan` (`_document201_bydocdate_trlr`), `Memoize`, `Index Only Scan`
- Метрики: Total Cost, Plan Rows vs Actual Rows, Shared Hit Blocks, Planning Time, Execution Time

## React integration assessment (для Phase B planning)

pev2 = Vue 3 SFC component. Наш frontend = React 18. Три варианта:

### 1. Web Component wrapper (рекомендуется)
- Обернуть pev2 в Vue Custom Element через `defineCustomElement()`
- Использовать `<pev2-plan>` в React как обычный HTML-tag
- Прозрачная интеграция, vue tree-shaken
- Риск: pev2 internals могут использовать Vue-specific APIs (slots, provide/inject) что плохо переживают custom-element-isolation

### 2. iframe с отдельным Vue dev-сервером
- Самый простой, полная изоляция
- Минус: коммуникация React ↔ iframe через postMessage
- Плюс: гарантированно работает, можно update pev2 независимо

### 3. Vue mount внутри React DOM node
- В React компоненте — `useEffect` создаёт Vue app и mount в ref'е
- Сложно cleanup, потенциальные memory leaks
- Не рекомендуется

**Вердикт:** для Sprint 8 Phase B берём **вариант 1 (Web Component)** как primary, имея в виду вариант 2 (iframe) как fallback если custom element упрётся в Vue-specific limitations.

## Backup plan (если pev2 не интегрируется)

1. `pg-explain-visualizer` (npm) — простой dependency-free renderer
2. Кастомный D3.js renderer для PG plan tree — наш control, 1-2 недели работы
3. Server-side рендеринг через `pg_flame` или похожие CLI tools
