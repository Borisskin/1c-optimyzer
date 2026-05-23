"""Sprint 4 — Query Analyzer RPC methods.

Public RPC:
    query_analyzer.analyze(query_text)
        → findings list + summary. Синхронный, < 5 сек на правилах.

    query_analyzer.rewrite(query_text, findings)
        → AI-переписанный вариант. Cache-aware. Может занимать до 30 сек.

    query_analyzer.status()
        → {"native_rules_count": N, "bsl_ls_available": bool, "ai_enabled": bool,
           "cache_entries": N}

    query_analyzer.reload_rules()
        → reload markdown rules without restart

    query_analyzer.generate_solution(finding_id, base_context)
        → placeholder Sprint 8 (всегда 501)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optimyzer_backend.query_analyzer.aggregator import QueryAnalyzer
from optimyzer_backend.query_analyzer.ai_rewriter import QueryRewriter
from optimyzer_backend.query_analyzer.query_cache import (
    QueryRewriteCache,
    QueryRewriteEntry,
    compute_cache_key,
    normalize_query,
)
from optimyzer_backend.query_analyzer.solution_generator import SolutionGenerator
from optimyzer_backend.rpc.dispatcher import rpc

# ---------- Singletons (lazy-init) ----------

_analyzer: QueryAnalyzer | None = None
_rewriter: QueryRewriter | None = None
_cache: QueryRewriteCache | None = None
_solution_gen: SolutionGenerator | None = None


def _rules_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "query_analyzer_rules"


def _semantic_rules_dir() -> Path:
    """Sprint 5: путь к semantic rules внутри пакета."""
    return Path(__file__).resolve().parents[1] / "query_analyzer" / "semantic_rules"


def _cache_path() -> Path:
    # Тот же файл что у Sprint 3 explainer — отдельная таблица query_rewrite_cache
    return Path(__file__).resolve().parents[3] / "data" / "explainer_cache.db"


def get_analyzer() -> QueryAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = QueryAnalyzer(
            rules_dir=_rules_dir(),
            semantic_rules_dir=_semantic_rules_dir(),
        )
    return _analyzer


def _get_active_config_store() -> "object | None":
    """Sprint 5: если configuration подключена — возвращаем store, иначе None.

    None → analyze() автоматически skip'ает semantic rules.
    """
    from optimyzer_backend.configuration_metadata.api import get_default_store

    store = get_default_store()
    return store if store.is_indexed() else None


def get_rewriter() -> QueryRewriter:
    global _rewriter
    if _rewriter is None:
        _rewriter = QueryRewriter()
    return _rewriter


def get_cache() -> QueryRewriteCache:
    global _cache
    if _cache is None:
        _cache = QueryRewriteCache(_cache_path())
    return _cache


def get_solution_gen() -> SolutionGenerator:
    global _solution_gen
    if _solution_gen is None:
        _solution_gen = SolutionGenerator()
    return _solution_gen


# ---------- RPC handlers ----------


@rpc("query_analyzer.analyze")
def analyze_rpc(query_text: str) -> dict[str, Any]:
    """Synchronous rule-based анализ. Возвращает findings + summary.

    Sprint 5: если configuration подключена через configuration.connect —
    автоматически запускаются semantic rules. Если нет — semantic rules
    silent.
    """
    if not isinstance(query_text, str):
        return {"ok": False, "error": "query_text must be string"}
    result = get_analyzer().analyze(query_text, config_store=_get_active_config_store())
    result["ok"] = True
    return result


@rpc("query_analyzer.rewrite")
def rewrite_rpc(
    query_text: str,
    findings: list[dict[str, Any]] | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """AI rewriter. Может занимать до 30 сек. Cache-aware."""
    findings = findings or []
    finding_ids = [str(f.get("rule_id", "")) for f in findings if f.get("rule_id")]
    cache_key = compute_cache_key(query_text, finding_ids)
    cache = get_cache()

    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return {
                "ok": True,
                "from_cache": True,
                "rewritten_query": cached.rewritten_query,
                "changes": json.loads(cached.changes_json) if cached.changes_json else [],
                "notes_for_developer": cached.notes_for_developer or "",
                "estimated_improvement": cached.estimated_improvement or "",
                "model": cached.model,
                "tokens_in": cached.tokens_in,
                "tokens_out": cached.tokens_out,
                "created_at": cached.created_at,
            }

    rewriter = get_rewriter()
    result = rewriter.rewrite(query_text, findings)
    if not result.ok:
        return {
            "ok": False,
            "error": result.error,
            "enabled": rewriter.enabled,
        }

    import hashlib

    query_hash = hashlib.sha256(normalize_query(query_text).encode("utf-8")).hexdigest()
    findings_hash = hashlib.sha256(",".join(sorted(finding_ids)).encode("utf-8")).hexdigest()
    cache.put(
        QueryRewriteEntry(
            cache_key=cache_key,
            query_hash=query_hash,
            findings_hash=findings_hash,
            rewritten_query=result.rewritten_query,
            changes_json=json.dumps(result.changes or [], ensure_ascii=False),
            notes_for_developer=result.notes_for_developer,
            estimated_improvement=result.estimated_improvement,
            model=result.model,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            created_at="",
        )
    )

    return {
        "ok": True,
        "from_cache": False,
        "rewritten_query": result.rewritten_query,
        "changes": result.changes or [],
        "notes_for_developer": result.notes_for_developer,
        "estimated_improvement": result.estimated_improvement,
        "model": result.model,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "elapsed_ms": result.elapsed_ms,
    }


@rpc("query_analyzer.status")
def status_rpc() -> dict[str, Any]:
    analyzer = get_analyzer()
    rewriter = get_rewriter()
    cache = get_cache()
    store = _get_active_config_store()
    return {
        "ok": True,
        "native_rules_count": len(analyzer.native_rules),
        "semantic_rules_count": len(analyzer.semantic_rules),
        "bsl_ls_available": analyzer.bsl_ls_available,
        "ai_enabled": rewriter.enabled,
        "model": rewriter.model if rewriter.enabled else None,
        "cache_entries": cache.stats()["entries"],
        "configuration_connected": store is not None,
    }


@rpc("query_analyzer.reload_rules")
def reload_rules_rpc() -> dict[str, Any]:
    analyzer = get_analyzer()
    analyzer.reload_rules()
    return {
        "ok": True,
        "rules_count": len(analyzer.native_rules),
        "semantic_rules_count": len(analyzer.semantic_rules),
    }


@rpc("query_analyzer.generate_solution")
def generate_solution_rpc(finding_id: str, base_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sprint 4: placeholder. Всегда возвращает 501."""
    return get_solution_gen().generate_solution(finding_id, base_context or {})


@rpc("query_analyzer.cache_clear_all")
def cache_clear_all_rpc() -> dict[str, Any]:
    """Очистка кеша rewriter'а — destructive, вызывает повторные API calls."""
    removed = get_cache().clear_all()
    return {"ok": True, "removed": removed}
