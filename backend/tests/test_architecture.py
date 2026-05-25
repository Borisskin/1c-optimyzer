"""Sprint 9 Phase D.3 — Architectural import sanity tests.

Проверяет что все основные модули импортируются без ошибок и RPC handlers
зарегистрированы. Ловит случаи когда синтаксическая ошибка или
circular import ломают весь backend при старте.
"""
from __future__ import annotations


class TestModuleImports:
    """Базовая проверка импортируемости всех публичных модулей."""

    def test_optimyzer_backend_root(self) -> None:
        import optimyzer_backend  # noqa: F401

    def test_parsers_module(self) -> None:
        import optimyzer_backend.parsers  # noqa: F401

    def test_sql_antipatterns_module(self) -> None:
        import optimyzer_backend.sql_antipatterns  # noqa: F401

    def test_sql_antipatterns_tsql(self) -> None:
        import optimyzer_backend.sql_antipatterns.tsql  # noqa: F401

    def test_sql_antipatterns_postgres(self) -> None:
        import optimyzer_backend.sql_antipatterns.postgres  # noqa: F401

    def test_rpc_dispatcher(self) -> None:
        import optimyzer_backend.rpc  # noqa: F401

    def test_storage_modules(self) -> None:
        import optimyzer_backend.storage.duckdb_store  # noqa: F401
        import optimyzer_backend.storage.sqlite_store  # noqa: F401

    def test_ingest_modules(self) -> None:
        import optimyzer_backend.ingest  # noqa: F401

    def test_explainer_module(self) -> None:
        import optimyzer_backend.explainer  # noqa: F401

    def test_models_module(self) -> None:
        import optimyzer_backend.models  # noqa: F401

    def test_pg_module(self) -> None:
        import optimyzer_backend.pg  # noqa: F401

    def test_planview_module(self) -> None:
        import optimyzer_backend.planview  # noqa: F401

    def test_query_analyzer_module(self) -> None:
        import optimyzer_backend.query_analyzer  # noqa: F401


class TestRpcHandlersRegistered:
    """Проверяет что RPC dispatcher инициализировался и обработчики зарегистрированы.

    RPC handlers регистрируются через @rpc() декоратор при импорте модуля.
    Чтобы _REGISTRY был полным — нужно импортировать все rpc-модули.
    В production это делает __main__.py/handlers.py, здесь делаем явно.
    """

    @classmethod
    def _ensure_handlers_loaded(cls) -> None:
        """Импортируем все RPC модули чтобы задействовались декораторы @rpc()."""
        import optimyzer_backend.rpc.sql_antipatterns_rpc  # noqa: F401
        import optimyzer_backend.rpc.plan_analyzer_rpc  # noqa: F401
        import optimyzer_backend.rpc.handlers  # noqa: F401
        import optimyzer_backend.rpc.sql_rpc  # noqa: F401
        import optimyzer_backend.rpc.views_rpc  # noqa: F401
        import optimyzer_backend.rpc.pg_rpc  # noqa: F401
        import optimyzer_backend.rpc.explainer_rpc  # noqa: F401
        import optimyzer_backend.rpc.query_analyzer_rpc  # noqa: F401
        import optimyzer_backend.rpc.configuration_rpc  # noqa: F401

    def test_handlers_count_above_threshold(self) -> None:
        """После импорта всех RPC модулей должно быть > 20 методов."""
        self._ensure_handlers_loaded()
        from optimyzer_backend.rpc.dispatcher import _REGISTRY
        assert len(_REGISTRY) > 20, f"Only {len(_REGISTRY)} handlers registered, expected > 20"

    def test_critical_handlers_present(self) -> None:
        """Ключевые RPC методы должны быть зарегистрированы."""
        self._ensure_handlers_loaded()
        from optimyzer_backend.rpc.dispatcher import _REGISTRY
        critical_handlers = [
            "sql_antipatterns.detect",
            "plan_analyzer.analyze_file",
            "plan_analyzer.analyze_xml",
        ]
        for h in critical_handlers:
            assert h in _REGISTRY, f"Critical handler {h!r} not registered"

    def test_sql_antipatterns_detect_callable(self) -> None:
        """sql_antipatterns.detect должен быть вызываемым и работать."""
        from optimyzer_backend.rpc.sql_antipatterns_rpc import detect_rpc
        result = detect_rpc(sql="SELECT 1", engine="mssql")
        assert result["ok"] is True
        assert result["engine"] == "mssql"
        assert isinstance(result["findings"], list)


class TestSqlAntipatternsSanity:
    """Минимальные проверки что engine работает."""

    def test_detect_antipatterns_mssql_returns_list(self) -> None:
        from optimyzer_backend.sql_antipatterns import detect_antipatterns
        result = detect_antipatterns("SELECT * FROM _Reference15", engine="mssql")
        assert isinstance(result, list)

    def test_detect_antipatterns_postgres_returns_list(self) -> None:
        from optimyzer_backend.sql_antipatterns import detect_antipatterns
        result = detect_antipatterns("SELECT * FROM _reference15", engine="postgres")
        assert isinstance(result, list)

    def test_unwrap_sp_executesql_works(self) -> None:
        from optimyzer_backend.rpc.sql_antipatterns_rpc import _unwrap_sp_executesql
        wrapped = "exec sp_executesql N'SELECT 1'"
        unwrapped = _unwrap_sp_executesql(wrapped)
        assert unwrapped == "SELECT 1"

    def test_unwrap_odbc_format_works(self) -> None:
        from optimyzer_backend.rpc.sql_antipatterns_rpc import _unwrap_sp_executesql
        wrapped = "{call sp_executesql(N'SELECT TOP 1 _IDRRef FROM _Reference15', N'')}"
        unwrapped = _unwrap_sp_executesql(wrapped)
        assert unwrapped == "SELECT TOP 1 _IDRRef FROM _Reference15"
