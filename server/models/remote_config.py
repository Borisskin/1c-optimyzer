"""RemoteConfig — серверный конфиг управления desktop без релиза (S13).

Singleton-строка. Управляется из админки (HTTP Basic) через /v1/admin/config,
отдаётся desktop через GET /v1/config. Дефолт — режим discovery (всё бесплатно,
щедрые лимиты, все рабочие фичи включены). `config_version` инкрементится при
каждом изменении — desktop сравнивает версию и применяет новый конфиг.
"""

from __future__ import annotations

import enum

from sqlalchemy import JSON, Boolean, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class MonetizationMode(str, enum.Enum):
    DISCOVERY = "discovery"   # всё бесплатно, щедрые лимиты — дефолт S13
    PAID = "paid"             # тарифы включены (S16)
    MIXED = "mixed"           # часть фич/лимитов платно


class RemoteConfig(Base, UUIDPrimaryKey, TimestampMixin):
    """Singleton-строка конфигурации продукта."""

    __tablename__ = "remote_config"

    monetization_mode: Mapped[MonetizationMode] = mapped_column(
        Enum(MonetizationMode, name="monetization_mode"),
        nullable=False,
        default=MonetizationMode.DISCOVERY,
    )
    # Глобальный экстренный стоп AI — срубить расходы не ломая остальное.
    ai_kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Лимиты AI. На discovery — None означает безлимит.
    # {"ai_per_day": int|None, "ai_per_month": int|None, "per_type": {<type>: int|None}}
    limits: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Тумблеры модулей: {"tj_analysis": bool, "plans": bool, "logcfg": bool,
    # "regressions": bool, "query_analyzer": bool, "sql_console": bool}
    feature_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Модель на тип AI — СЕРВЕРНАЯ деталь, desktop её НЕ получает.
    # {"explain": str, "plan": str, "regression": str, "logcfg": str}
    ai_model_per_type: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Версии промптов для инвалидации кэша из админки. {"query": "v1", ...}
    prompt_versions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Инкрементируется при каждом изменении — desktop отслеживает.
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
