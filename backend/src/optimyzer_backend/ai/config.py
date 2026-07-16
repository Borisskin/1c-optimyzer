"""Конфиг AI для sidecar — замена серверного `api.settings` при BYOK.

Портированный из server/ модуль explainer.py обращается к `settings.<...>` в
двух десятках мест. Чтобы не править их все (и не разойтись с оригиналом при
будущих слияниях), здесь воспроизведён тот же интерфейс: подменяется ровно
одна строка импорта.

Разница с сервером одна, но принципиальная: `anthropic_api_key` — это ключ
ПОЛЬЗОВАТЕЛЯ из локальных настроек, а не наш. Ключ читается лениво (property),
поэтому смена ключа в настройках применяется сразу, без перезапуска sidecar.
"""

from __future__ import annotations

import os


class _AiSettings:
    """Минимальный интерфейс, который использует портированный explainer."""

    # Совпадают с server/api/settings.py, чтобы поведение AI не разъехалось.
    ai_model_default: str = "claude-haiku-4-5"
    ai_max_tokens: int = 4000
    ai_request_timeout_s: int = 60

    @property
    def anthropic_api_key(self) -> str:
        """Ключ пользователя (BYOK). Пусто → AI выключен.

        Семантика трёх состояний (см. ai_settings_rpc.get_stored_api_key):
          None  — настройка не задавалась → откат на ENV (только dev/тесты);
          ""    — пользователь явно удалил ключ → AI выключен, БЕЗ отката;
          "sk-…" — ключ пользователя.
        """
        from optimyzer_backend.rpc.ai_settings_rpc import get_stored_api_key

        stored = get_stored_api_key()
        if stored is None:
            return os.environ.get("ANTHROPIC_API_KEY", "").strip()
        return stored

    @property
    def ai_model(self) -> str:
        """Модель: пользовательская настройка → дефолт."""
        from optimyzer_backend.rpc.ai_settings_rpc import get_stored_model

        return get_stored_model() or self.ai_model_default


settings = _AiSettings()
