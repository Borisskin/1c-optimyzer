# Design Reference

Файлы в `opt/*.jsx` — **визуальная спецификация** на английском языке. Они описывают
layout, цвета, шрифты, animations и общую DOM-структуру каждого экрана.

Production UI — **русский (ru-RU)** через `frontend/src/i18n/ru.ts` (ADR-009).
То есть `Load TZ archive…` в `opt/*.jsx` соответствует `t.topbar.loadFolder`
в production коде («Загрузить папку с логами…»).

**Правило:** при изменении дизайн-файлов не нужно немедленно переводить строки —
это reference, не production source of truth. Перевод и связка с `i18n/ru.ts` —
часть имплементации компонента.
