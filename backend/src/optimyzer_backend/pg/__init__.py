"""Sprint 8 Phase B — PostgreSQL integration: connections + re-EXPLAIN service.

Этот пакет добавляет **opt-in** функциональность для PG баз:
  - Юзер настраивает read-only PG connection в Settings (host/port/db/user/password)
  - Password хранится в OS keychain (Windows Credential Manager / macOS Keychain / Linux secret service)
  - Backend может выполнить EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE) повторно
    для SELECT-запросов из ТЖ архива → JSON план → pev2 интерактивная визуализация

Модули:
  - safety:      is_safe_to_re_explain() — проверка что SQL безопасен для re-EXPLAIN
  - connections: PgConnection model + helper для CRUD + keychain
  - re_explain:  re_explain_safe() async — реальный запрос к PG через asyncpg

Безопасность: re-EXPLAIN запускается только для SELECT/WITH. DML (INSERT/UPDATE/DELETE)
и DDL отвергаются — даже EXPLAIN ANALYZE на них имеет side effects.

Все методы синхронные кроме re_explain_safe() (она async — asyncpg).
"""
