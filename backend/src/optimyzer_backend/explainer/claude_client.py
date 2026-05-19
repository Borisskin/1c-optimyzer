"""Sprint 3 Phase F — Claude API client для AI-generated explanations.

Backend-only по ADR-024: API ключ читается из env `ANTHROPIC_API_KEY`,
никогда не уходит в frontend. Если ключ не настроен — `enabled=False`,
RPC возвращает graceful fallback "AI not configured".
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AiExplanationResult:
    ok: bool
    text: str = ""
    error: str | None = None
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_ms: float = 0.0


SYSTEM_PROMPT = """Ты — старший 1С-эксперт по технологическим вопросам, который объясняет проблему производительности middle-программисту 1С БЕЗ сертификации эксперта.

Правила:
1. Пиши на русском, conversational, как коллеге.
2. НЕ используй жаргон без объяснения: если используешь "латч", "MVCC", "уровень изоляции" — объясни в скобках простыми словами.
3. Структура ответа:
   - Что произошло (2-3 предложения по существу)
   - Почему так получилось (объяснение причины)
   - Что делать (3 конкретных action items от простого к сложному)
4. Не пиши "возможно", "может быть" — пиши уверенно, ты эксперт.
5. Не упоминай APDEX/SLA если их нет в контексте.
6. Если знаешь конкретный пункт курса 1С:Эксперт — упомяни.
7. Длина ответа: 200-400 слов.
"""


class ClaudeExplainerClient:
    """Wrapper над anthropic SDK с graceful degradation."""

    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TIMEOUT_S = 15.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "").strip()
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
            logger.warning("anthropic SDK не установлен; AI explainer disabled")
            self.enabled = False

    def generate(
        self,
        *,
        anatomy_kind: str,
        anatomy_data: dict[str, Any],
        rule_context: str | None = None,
    ) -> AiExplanationResult:
        """Генерирует conversational объяснение через Claude API."""
        if not self.enabled:
            return AiExplanationResult(
                ok=False,
                error="AI not configured (no ANTHROPIC_API_KEY in env)",
            )

        import time

        prompt = self._build_user_prompt(anatomy_kind, anatomy_data, rule_context)

        start = time.monotonic()
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.DEFAULT_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.DEFAULT_TIMEOUT_S,
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return AiExplanationResult(
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                model=self.model,
                elapsed_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        text = _extract_text(response)
        return AiExplanationResult(
            ok=True,
            text=text,
            model=self.model,
            tokens_in=getattr(response.usage, "input_tokens", 0),
            tokens_out=getattr(response.usage, "output_tokens", 0),
            elapsed_ms=elapsed,
        )

    def _build_user_prompt(
        self,
        anatomy_kind: str,
        anatomy_data: dict[str, Any],
        rule_context: str | None,
    ) -> str:
        parts: list[str] = []
        if rule_context:
            parts.append(
                "Готовый шаблон правила для этого паттерна (используй как опору, расширь и адаптируй):\n\n"
                + rule_context
            )
        else:
            parts.append(
                "Произошло событие, для которого нет готового правила в каталоге. "
                "Объясни его на основании данных ниже."
            )

        parts.append(f"\nТип анализа: **{anatomy_kind}**")
        parts.append("\nДанные события / операции (JSON):\n")
        import json as _json

        # Ограничиваем размер payload — не передаём весь raw extra если он гигантский
        summary = _summarize_for_prompt(anatomy_data)
        parts.append("```json\n" + _json.dumps(summary, ensure_ascii=False, indent=2) + "\n```")
        parts.append(
            "\nОбъясни происходящее на русском, как старший коллега объясняет middle-разработчику. "
            "Структура: 'Что произошло' / 'Почему так получилось' / 'Что делать (3 шага)'. "
            "Длина 200-400 слов."
        )
        return "\n".join(parts)


def _extract_text(response: Any) -> str:
    """Извлечь plain text из anthropic SDK response."""
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


def _summarize_for_prompt(data: dict[str, Any], *, max_str_len: int = 500) -> dict[str, Any]:
    """Усечь длинные строки и большие массивы для AI prompt — экономия токенов."""
    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str) and len(v) > max_str_len:
            out[k] = v[:max_str_len] + "…"
        elif isinstance(v, list) and len(v) > 10:
            out[k] = v[:10] + [f"… ещё {len(v) - 10} элементов"]
        elif isinstance(v, dict):
            out[k] = _summarize_for_prompt(v, max_str_len=max_str_len)
        else:
            out[k] = v
    return out
