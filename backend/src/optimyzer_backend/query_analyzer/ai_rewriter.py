"""Sprint 4 — AI rewriter через Claude.

Принимает SDBL-запрос + список findings, возвращает переписанный вариант
+ список изменений + рекомендации разработчику.

Если ANTHROPIC_API_KEY не настроен — `enabled=False`, rewrite возвращает
{"ok": False, "error": "AI not configured"}. UI должен показать кнопку
disabled с tooltip.

Backend-only по ADR-024 (как Sprint 3 explainer).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Ты — старший 1С-эксперт по производительности запросов на языке 1С (SDBL).

Тебе дан запрос с найденными антипаттернами производительности. Перепиши запрос так, чтобы устранить все указанные проблемы, сохранив бизнес-логику.

Правила переписывания:
1. Полностью сохрани смысл запроса — результат должен быть эквивалентен.
2. Используй типичные приёмы оптимизации 1С:
   - Вынос виртуальных таблиц (Остатки, Обороты) во временные таблицы с индексами.
   - Замена соединений с подзапросами на временные таблицы.
   - Замена `В` с подзапросом на `ВНУТРЕННЕЕ СОЕДИНЕНИЕ`.
   - `ОБЪЕДИНИТЬ ВСЕ` вместо `ОБЪЕДИНИТЬ` когда дубли невозможны.
   - Вынос `ВЫРАЗИТЬ(... КАК ...)` из условия `ГДЕ` в `ВЫБРАТЬ` или separate выборку.
   - Индексирование временных таблиц по полям соединения.
3. Пиши на чистом 1С-Запросе (SDBL) с правильными русскими ключевыми словами.
4. НЕ добавляй комментарии в код запроса — комментарии вынеси в массив `changes`.

Формат ответа — СТРОГО валидный JSON, без markdown-блоков, без текста до или после:

{
  "rewritten_query": "ВЫБРАТЬ\\n...",
  "changes": [
    {"what": "Вынес виртуальную таблицу Остатки во временную таблицу с индексом",
     "why": "Виртуальная таблица в JOIN заставляет СУБД повторно вычислять её",
     "lines_in_original": [4, 5]}
  ],
  "estimated_improvement": "Запрос должен работать 5-50x быстрее на больших объёмах",
  "notes_for_developer": "Проверьте что параметр &Дата установлен корректно"
}

Если запрос НЕ может быть улучшен — верни тот же запрос с пустым массивом changes и объяснением в notes_for_developer.
"""


@dataclass
class RewriteResult:
    ok: bool
    rewritten_query: str = ""
    changes: list[dict[str, Any]] | None = None
    estimated_improvement: str = ""
    notes_for_developer: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_ms: float = 0.0
    error: str | None = None


class QueryRewriter:
    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TIMEOUT_S = 30.0

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        if api_key is None:
            self._load_dotenv()
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.api_key = api_key.strip()
        self.model = model or os.environ.get("ANTHROPIC_MODEL", self.DEFAULT_MODEL)
        self._client: Any = None
        if not self.api_key:
            self.enabled = False
            return
        try:
            from anthropic import Anthropic  # type: ignore[import-untyped]

            self._client = Anthropic(api_key=self.api_key)
            self.enabled = True
        except ImportError:
            logger.warning("anthropic SDK не установлен; AI rewriter disabled")
            self.enabled = False

    @staticmethod
    def _load_dotenv() -> None:
        """Делегируем существующему loader'у из claude_client."""
        from optimyzer_backend.explainer.claude_client import _load_dotenv_once

        _load_dotenv_once()

    def rewrite(self, query_text: str, findings: list[dict[str, Any]]) -> RewriteResult:
        if not self.enabled:
            return RewriteResult(ok=False, error="AI not configured (no ANTHROPIC_API_KEY in env)")

        user_prompt = self._build_user_prompt(query_text, findings)

        start = time.monotonic()
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.DEFAULT_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                timeout=self.DEFAULT_TIMEOUT_S,
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return RewriteResult(
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                model=self.model,
                elapsed_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        text = _extract_text(response)
        parsed = _parse_json_response(text)
        if parsed is None:
            return RewriteResult(
                ok=False,
                error="AI вернул невалидный JSON",
                model=self.model,
                elapsed_ms=elapsed,
                tokens_in=getattr(response.usage, "input_tokens", 0),
                tokens_out=getattr(response.usage, "output_tokens", 0),
            )

        return RewriteResult(
            ok=True,
            rewritten_query=str(parsed.get("rewritten_query", "")),
            changes=parsed.get("changes") or [],
            estimated_improvement=str(parsed.get("estimated_improvement", "")),
            notes_for_developer=str(parsed.get("notes_for_developer", "")),
            model=self.model,
            tokens_in=getattr(response.usage, "input_tokens", 0),
            tokens_out=getattr(response.usage, "output_tokens", 0),
            elapsed_ms=elapsed,
        )

    def _build_user_prompt(self, query_text: str, findings: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        parts.append("Исходный запрос:")
        parts.append("```sdbl")
        parts.append(query_text)
        parts.append("```")
        parts.append("")
        parts.append("Найденные проблемы:")
        if findings:
            for i, f in enumerate(findings, 1):
                rule_id = f.get("rule_id", "?")
                msg = f.get("message", "")
                ls = f.get("line_start", "?")
                le = f.get("line_end", "?")
                parts.append(f"{i}. [{rule_id}] {msg} (строки {ls}-{le})")
        else:
            parts.append("(пусто — найди проблемы сам)")
        parts.append("")
        parts.append("Перепиши запрос устранив все проблемы. Ответь СТРОГО JSON без markdown.")
        return "\n".join(parts)


def _extract_text(response: Any) -> str:
    try:
        content = response.content
        if isinstance(content, list):
            parts = []
            for c in content:
                if hasattr(c, "text"):
                    parts.append(c.text)
                elif isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c.get("text", ""))
            return "\n".join(parts)
        return str(content)
    except Exception:
        return str(response)


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_json_response(text: str) -> dict[str, Any] | None:
    """Парсим JSON. Если AI обернул в markdown — извлекаем из ```json``` блока."""
    text = text.strip()
    # Прямой parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Из markdown-блока
    m = _JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Эвристика: найти первую { и последнюю }
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidate = text[first : last + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None
