# Open Questions — 1C-Optimyzer

> Вопросы, требующие решения от владельца или дополнительной разведки.

## Q1: Реальный архив ТЖ для acceptance testing — когда и где получим?

**Status:** open, **blocking** для Definition of Done пункта 19 (real-data acceptance gate).

**Context:** Sprint 0 закрывается только когда парсер успешно обрабатывает реальный архив ТЖ (>=95% events распарсены без exceptions). Без архива от Сергея этот gate не пройти.

**Что нужно:**
- Zip-архив с папкой logcfg (или любой структурой папок rphost_xxxx с .log файлами)
- Желательно >= 100 МБ распакованного ТЖ для разумного теста скорости
- События разных типов (минимум CALL, DBMSSQL, желательно EXCP/TLOCK/TDEADLOCK)
- Версия платформы 1С: предпочтительно 8.3.20+
- Может быть санитизирован (имена пользователей, базы — replaced) — нам важна структура ТЖ, не содержимое бизнес-данных

**Куда положить:** `backend/tests/fixtures/real-archive/` (в .gitignore, локально только) либо `D:\1C-Optimyzer\fixtures\` вне репо.

**Если архив недоступен в Sprint 0** — закрываем Sprint 0 с пометкой "real-data acceptance — pending, blocked on owner-provided fixture", и держим этот gate открытым для Sprint 1 closure.

## Q2: Целевая версия платформы 1С

Парсер pattern-сензитивен к версии. Sprint 0 закладывается на 8.3.20+ (последние 5–6 минорных). Подтвердить с владельцем — есть ли смысл поддерживать более старые версии (8.3.18, 8.3.16)?

## Q3: Кодировка файлов ТЖ

ТЖ обычно UTF-8, но на старых системах может быть Windows-1251 или OEM. Sprint 0 — assume UTF-8 с fallback на Windows-1251 (errors='replace'). Auto-detect через chardet — отложен на Sprint 1, если возникнет реальная проблема.

## Q4: Размер архивов в production

ТЖ за час нагрузочной системы — ~100–300 МБ. За день — единицы–десятки ГБ. Sprint 0 — correctness first; цель ≥10K events/sec на single core. Sprint 2 — performance tuning, parallelism, columnar inserts.

## Q5: Sanitization паролей/credentials в SQL

ТЖ может содержать SQL с паролями (хотя обычно платформа заменяет их на `?`). Sprint 0 — полагаемся на платформенную sanitization. Полная sanitization — Sprint 2 (regex-based filter перед insert).
