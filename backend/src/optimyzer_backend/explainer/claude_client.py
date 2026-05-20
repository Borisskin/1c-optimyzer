"""Sprint 3 Phase F — Claude API client для AI-generated explanations.

Backend-only по ADR-024: API ключ читается из env `ANTHROPIC_API_KEY`,
никогда не уходит в frontend. Если ключ не настроен — `enabled=False`,
RPC возвращает graceful fallback "AI not configured".
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_dotenv_once() -> None:
    """Простой .env loader без зависимостей.

    Python не читает .env автоматически. Чтобы пользователю не приходилось
    выставлять переменную окружения вручную, загружаем .env-файл из:
      - текущей рабочей директории (откуда запущен backend)
      - корня репозитория (4 уровня вверх от этого файла)
    Существующие переменные окружения НЕ перезаписываем.
    """
    if os.environ.get("_OPTIMYZER_DOTENV_LOADED") == "1":
        return
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[4] / ".env",  # backend/src/optimyzer_backend/explainer → repo root
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Снять кавычки если есть
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                # Перезаписываем пустые значения (Windows/CI окружение иногда
                # устанавливает ANTHROPIC_API_KEY="" — это блокирует загрузку
                # из .env). Не-пустые env vars сохраняем.
                if key and not os.environ.get(key):
                    os.environ[key] = value
            logger.info(f"Loaded .env from {path}")
            break
        except OSError:
            continue
    os.environ["_OPTIMYZER_DOTENV_LOADED"] = "1"


@dataclass
class AiExplanationResult:
    ok: bool
    text: str = ""
    error: str | None = None
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_ms: float = 0.0


SYSTEM_PROMPT = """Ты — старший специалист по производительности 1С, который объясняет проблему обычному 1С-программисту понятным языком.

Правила:
1. Пиши на русском, conversational, как коллеге.
2. НЕ используй жаргон без объяснения: если используешь "латч", "MVCC", "уровень изоляции" — объясни в скобках простыми словами.
3. Структура ответа:
   - Что произошло (2-3 предложения по существу)
   - Почему так получилось (объяснение причины)
   - Что делать (3 конкретных action items от простого к сложному)
4. Не пиши "возможно", "может быть" — пиши уверенно, ты эксперт.
5. Не упоминай APDEX/SLA если их нет в контексте.
6. Не ссылайся на учебные курсы / методички / сертификации — пользователю нужен ответ по существу, а не reference на курс.
7. Длина ответа: 200-400 слов.
"""


class ClaudeExplainerClient:
    """Wrapper над anthropic SDK с graceful degradation."""

    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TIMEOUT_S = 30.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        # api_key=None → читаем .env + env var. api_key="..." (включая пустую
        # строку) → используем как явный override (нужно для тестов).
        if api_key is None:
            _load_dotenv_once()
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
