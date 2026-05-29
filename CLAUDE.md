# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

1C-Optimyzer — an APM / technological-journal analyzer for 1C:Enterprise. The shipped product is a **Tauri 2 desktop app** (`frontend/` + a bundled `backend/` Python sidecar) that ingests 1C tech-journal archives into DuckDB and analyzes slow queries, locks, deadlocks, execution plans, and SDBL. A separate **FastAPI cloud** (`server/`) provides AI features, licensing, and billing. All UI and docs are in Russian.

## Repository layout

Five deployable units plus tooling:

| Path | What | Stack |
|------|------|-------|
| `frontend/` | The desktop app (product) | Tauri 2 (Rust) + React 18 + TS + Vite; CodeMirror 6, Recharts, Zustand |
| `backend/` | Local Python **sidecar**, JSON-RPC over stdio; bundled into the app | Python 3.11, DuckDB, pyarrow, sqlglot, anthropic |
| `server/` | Cloud API (`api.optimyzer.pro`): AI, auth, licensing, billing, telemetry | FastAPI, SQLAlchemy 2 + Alembic, SQLite (dev) / PostgreSQL (prod) |
| `cabinet/` | Web account (`account.optimyzer.pro`) | React + Vite |
| `landing/` | Static landing + docs (`optimyzer.pro`) | static HTML |
| `scripts/` | PowerShell dev/infra scripts | — |
| `docs/` | `DECISIONS.md` (ADRs) + `OPUS_HANDOVER_*.md` (authoritative project state) | — |
| `.claude/skills/` | PowerShell skills for manipulating 1C configs/extensions/forms | — |

## Architecture (the part that spans files)

**The desktop app talks to two different backends — always know which one you're touching:**

- `frontend/src/api/backend.ts` → the **local sidecar** (`backend/`, `python -m optimyzer_backend`) over Tauri / JSON-RPC-over-stdio (the Rust layer in `frontend/src-tauri/` spawns and owns the sidecar process). Everything local & offline: archive ingest (`ingest/`, `archive/`), DuckDB queries (`storage/`), log parsing (`parsers/` tj_parser), SQL antipattern detection (`sql_antipatterns/` — `tsql/` + `postgres/`), bsl-language-server SDBL diagnostics (`bsl_ls/`), plan visualization (`planview/`), regression analysis (`regression/`).
- `frontend/src/api/cloud.ts` → the **cloud server** (`server/`) over HTTP at `localhost:8001` (dev) / `api.optimyzer.pro` (prod). All **AI** features plus license/auth/billing/telemetry.

**Asymmetric AI flow (see ADR-057):** AI calls go frontend → cloud server **directly**, bypassing the sidecar. The server holds the `ANTHROPIC_API_KEY` and the AI response cache. Consequence: AI features require the cloud server running; everything else works fully offline against the sidecar.

- `server/services/ai_explainer.py` — all AI orchestration. Each public fn (`explain_query`, `explain_plan_query`, `generate_logcfg`, `explain_regression`) is a thin cache wrapper over an `_uncached` impl. Haiku for logcfg/regression, default model for explain. Anthropic client timeout is 60s.
- `server/services/ai_cache/` — content-canonical sha256 cache keys; bump the `PROMPT_VERSION_*` constants to invalidate; TTL differs per type (plans forever, query 90d, logcfg 30d).
- `frontend/src/api/cloud.ts` `request()` has an AbortController timeout (20s normal, 90s for AI) so a down/wedged server can't hang the UI forever.

**Data stores:** one DuckDB file per ingested archive (analytics); SQLite for desktop app metadata; SQLite/PostgreSQL on the server for accounts + AI cache.

**Bundled binaries** (gitignored; fetched by `scripts/setup-*-binaries.ps1`; live under `frontend/src-tauri/binaries/`): bsl-language-server (Temurin JRE 21) for SDBL diagnostics, PerformanceStudio CLI (`planview.exe`) for MSSQL plan analysis, html-query-plan + pev2 for plan rendering. Missing binaries degrade the matching analyzer only.

## Commands

**Full dev stack:** run `start.bat` from the repo root. It (1) starts/reuses the cloud server on :8001 via `scripts/ensure-server.ps1`, (2) cleans orphaned sidecars via `scripts/kill-zombie-python.ps1`, (3) runs `call npm run tauri dev`, (4) stops the server via `scripts/stop-server.ps1` when the app window closes. **The server's lifecycle is bound to the app window** — do not start it as a standalone detached process that outlives the app; an orphaned server squatting on :8001 is exactly the failure mode `start.bat` exists to prevent.

**frontend/** (run npm in `frontend/`):
- `npm run tauri dev` — desktop app (spawns the sidecar) · `npm run dev` — Vite only
- `npm run build` — `tsc --noEmit && vite build` · `npm run typecheck`
- `npm test` — vitest run · single file: `npx vitest run src/features/tj-config-builder`
- `npm run lint:css` — flags hardcoded colors (must use `--o-*` design tokens)

**backend/** (venv at `backend/.venv`; `pip install -e ".[dev]"`):
- `python -m optimyzer_backend` — run sidecar (reads JSON-RPC 2.0 from stdin, logs to stderr)
- `pytest` — default run excludes integration · `pytest -m integration` (real bsl-LS JVM, slow) · `pytest -m performance`
- single test: `pytest tests/<file>.py::<Class>::<test>` · lint: `ruff check src`

**server/** (venv at `server/.venv`; `pip install -e .[dev]`):
- `alembic upgrade head` (creates the SQLite db) · `uvicorn api.main:app --reload --port 8001`
- `pytest` · single: `pytest tests/test_auth.py -v` · coverage: `pytest --cov-report=html`
- OpenAPI docs at http://127.0.0.1:8001/docs

**cabinet/**: `npm run dev` / `npm run build`.

## Configuration

A single root `.env` (template: `.env.example`) configures all units. The server resolves it by absolute path (`server/api/settings.py`, `PROJECT_ROOT/.env`) regardless of cwd; in code use `from api.settings import settings`. Never auto-remove secrets from `.env` or `.env.example` — confirm in chat first.

## Conventions & gotchas

- **Windows-only dev, everything under `D:\`.** The Bash tool is git-bash (no `cd /d` — use absolute paths or the PowerShell tool). Keep PowerShell-script output ASCII to avoid PS 5.1 encoding issues.
- **1C source files (`.bsl`) must be UTF-8 _with BOM_.** Write/Edit emit no BOM and 1C silently drops exported methods without it — restore the BOM via PowerShell after editing any `.bsl`.
- **Use the `.claude/skills/` 1C toolkit** (`cf-*`, `cfe-*`, `meta-*`, `form-*`, `epf-*`, `role-*`, `skd-*`, …) to create/modify 1C configurations, extensions, and forms instead of hand-editing 1C XML.
- **Product-UI rules:** never surface implementation details in the app (cache, tokens, model, latency, API keys, server commands) — send those to logs/console. Show **raw** SQL (or the ARG_MAX exemplar of a group), never the normalized `?`-placeholder form (normalization is only for GROUP BY hashing).
- **Project state of truth:** `docs/OPUS_HANDOVER_*.md` (latest: `OPUS_HANDOVER_2026_05_29_FULL_AUDIT.md`) and `docs/DECISIONS.md` (ADRs). Read these when picking up work. Internal release tags are `vX.Y.Z-internal`. Commit messages and docs are written in Russian.
