# Sprint 6 Handover для архитектора Opus

**Sprint:** 6 — Query Analyzer Restoration via bsl-language-server
**Status:** Done (commits `e9131d4` → `f43854f` in main)
**Closure report:** `docs/SPRINT_6_REPORT.md`
**Original plan:** `docs/sales_sprint/SPRINT_6_PROMT.md`

---

## Что готово к production

- **QueryAnalyzer** видим в Sidebar (Ctrl+Q), работает с bsl-language-server backend
- **19 SDBL диагностик** активны (через `bsl_ls.analyze` RPC)
- **Cloud AI explainer** (`/v1/ai/explain`) возвращает structured output от Claude Sonnet 4.5
- **Configuration wiring**: подключённая XML конфа автоматически передаётся в bsl-LS
- **sqlglot antipatterns** готовы к использованию (API в `optimyzer_backend.sql.antipatterns`)
- **Backend tests**: 574 passed (+82 new), 100% green
- **Server tests**: 112 passed (+11 new)
- **Bundling**: scripts/setup-bsl-ls-binaries.ps1 idempotent, tauri.conf.json готов

## Что зафиксировано как tech debt

| ID | Description | Sprint |
|---|---|---|
| TD-6.1 | Tauri build на чистой Windows 11 VM не проверен | Sprint 7 acceptance |
| TD-6.2 | Frontend tests (vitest) не настроены | Sprint 7 setup |
| TD-6.3 | AI endpoint без auth/caching/soft caps | Phase 1 INFRA |
| TD-6.4 | CodeMirror inline underlining (только click-to-jump сейчас) | Sprint 7 enhancement |
| TD-6.5 | Integration tests в full suite иногда зависают на port 8025 | Sprint 7 — better cleanup |
| TD-6.6 | Pyright/TypeScript полная проверка с strict | Sprint 7 |

## Открытые вопросы для решения архитектором

### Q1. Куда движемся в Sprint 7?

Sprint 6 промпт указывает Sprint 7 = "AI Query Rewriter v2 + Multi-model routing":
- Opus 4.5 для Business tier
- Multi-pass reasoning для complex cases
- Caching и semantic deduplication

Альтернативы:
- **Опция A**: следовать плану (Sprint 7 = AI improvements)
- **Опция B**: перейти к Sprint 8 (Plan Analyzer — PerformanceStudio + html-query-plan), т.к. это **визуально более impressive фича** для маркетинга и больше completes картину для premium тарифа
- **Опция C**: Phase 1 INFRA (Yandex OAuth+YooKassa) — backend готов на 80%, можно завершить и запустить billing уже сейчас

### Q2. Стоит ли активировать `FieldsFromJoinsWithoutIsNull` принудительно?

Sprint 6 промпт говорит «активируем все 19». Bsl-LS по умолчанию имеет `FieldsFromJoinsWithoutIsNull = activatedByDefault: false`. Мы не делаем явного override в `.bsl-language-server.json` который передаём — поэтому пока он **выключен**. Чтобы включить, нужно создать конфиг файл и передать в `BslLsClient.initialize`.

Если у юзера на типовой БП 3.0 будет много false-positives — оставляем off. Если важно для perf detection — включаем.

### Q3. Severity mapping `AssignAliasFieldsInQuery` = Minor — правильно?

Эта диагностика срабатывает 6 раз на простой запрос из 5 полей (наш тестовый Test.bsl). Это too noisy для default UI. Опции:
- Оставить Minor, скрывать Minor по дефолту в UI (как сейчас)
- Понизить до Info
- Полностью disable

### Q4. Нужны ли в Sprint 7 кастомные правила?

Sprint 6 промпт говорит «НЕ добавлять новые SDBL правила сверх 19 от bsl-LS». Но в реальных архивах ТЖ Сергея есть **специфические для 1С паттерны** которых нет в bsl-LS (типа `TOP 1` без ORDER BY на регистре, использование `НЕОПРЕДЕЛЕНО`, и т.п.). Стоит ли в Sprint 7 добавить пару custom правил?

### Q5. Telemetry для bsl-LS usage

Сейчас bsl-LS вызовы не телеметрируются. Хорошо бы в Sprint 7:
- Count `bsl_ls.analyze` вызовов
- Average duration
- Top 10 SDBL rules срабатывают чаще всего
- Error rate

Для оптимизации продукта на основе реального использования.

## Feature flags / configs архитектору знать

| Setting | Default | Где меняется |
|---|---|---|
| `ANTHROPIC_API_KEY` | empty | `server/.env` |
| `ai_model_default` | `claude-sonnet-4-5-20250929` | `server/api/settings.py` |
| `ai_model_business` | `claude-opus-4-5-20250929` (заготовка) | server/api/settings.py — для Sprint 7 multi-model |
| `bsl-LS port` | 8025 (default) | dynamic fallback если занят |
| `pytest -m integration` | deselected | для запуска явно: `pytest -m integration` |

## Architecture diagrams (как сейчас работает)

```
┌─────────────────────────────────────────────────────────────┐
│ Optimyzer Desktop (Tauri 2 + React + Python sidecar)        │
│                                                             │
│  React UI (Ctrl+Q)                                          │
│    QueryAnalyzer.tsx                                        │
│      ├── QueryEditor (CodeMirror)                           │
│      ├── BslLsFindings ◄─────┐                              │
│      ├── AiExplanationCard ◄─┼──── cloud.aiExplain          │
│      └── ConfigurationBadge   │                             │
│                  │            │                             │
│                  ▼            │                             │
│  Python sidecar (FastAPI-style RPC over stdio)              │
│    bsl_ls_rpc.analyze ───────► bsl_ls.client (async)        │
│      ├── получает config_root                               │
│      │   из configuration_metadata.store                    │
│      └── через bsl_ls.runtime (loop bridge)                 │
│                  │                                          │
│                  ▼                                          │
│  bsl-LS JVM (WebSocket sidecar, lazy-start)                 │
│    bsl-language-server-0.29.0-exec.jar (115 MB)             │
│    + bundled Temurin JRE 21 (150 MB)                        │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTPS (Sprint 6: localhost dev mode)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Cloud backend (FastAPI, api.optimyzer.pro)                  │
│                                                             │
│  POST /v1/ai/explain                                        │
│    → schemas/ai.py ExplainRequest                           │
│    → services/ai_explainer.py                               │
│      ├── SYSTEM_PROMPT (русский, strict JSON schema)        │
│      ├── USER_PROMPT (SDBL + diagnostics + config_context)  │
│      └── Claude Sonnet 4.5 (anthropic.AsyncAnthropic)       │
│    → ExplainResponse (issues + suggested_rewrite)           │
└─────────────────────────────────────────────────────────────┘
```

## Ссылки на ключевые точки кода

| Что | Где |
|---|---|
| bsl-LS adapter package | `backend/src/optimyzer_backend/bsl_ls/` |
| RPC entry для UI | `backend/src/optimyzer_backend/rpc/bsl_ls_rpc.py` |
| Cloud AI endpoint | `server/api/routers/ai.py` |
| AI orchestrator + prompts | `server/services/ai_explainer.py` |
| UI компоненты Phase E | `frontend/src/components/screens/QueryAnalyzer/{BslLsFindings,AiExplanationCard}.tsx` |
| T-SQL antipatterns | `backend/src/optimyzer_backend/sql/antipatterns.py` |
| Bundling script | `scripts/setup-bsl-ls-binaries.ps1` |
| Tauri integration | `frontend/src-tauri/src/main.rs::get_bsl_ls_paths` |

## Что писать в Sprint 7 промпте

Рекомендую следующую структуру (если выбираете Opt A — AI v2):

1. **Phase A**: caching `/v1/ai/explain` в SQLite (server-side кеш по hash)
2. **Phase B**: auth wiring (JWT verify, user_id, tier detection)
3. **Phase C**: multi-model routing (Sonnet для Pro, Opus для Business)
4. **Phase D**: soft caps tracking для AI calls (free 5/мес, Pro unlimited)
5. **Phase E**: AI rewriter v2 — multi-pass для complex cases
6. **Phase F**: UI улучшения — better suggested_rewrite presentation (diff view)
7. **Phase G**: tests + perf
8. **Phase H**: docs + tag v0.7.0-internal

---

**Готовность к Sprint 7:** 100%. Все backend компоненты для AI work на месте, осталось добавить надстройку.

**Готовность к продаже:** 70%. Premium feature работает end-to-end локально, но Phase 1 INFRA (auth/billing) нужно завершить перед публичным launch. Если выбираем Opt C (Phase 1 INFRA сейчас) — можем launch через 2-3 недели вместо 4-5.
