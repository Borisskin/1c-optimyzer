# Third-Party Notices for 1C-Optimyzer

1C-Optimyzer включает или зависит от следующих opensource компонентов.
Все они распространяются под собственными лицензиями.

---

## bsl-language-server

- **Версия:** 0.29.0
- **License:** LGPL-3.0-or-later (GNU Lesser General Public License v3.0 или более поздняя)
- **Источник:** https://github.com/1c-syntax/bsl-language-server
- **Авторы:** Alexey Sosnoviy, Nikita Fedkin and contributors
- **Copyright:** © 2018-2026
- **Использование в продукте:** запускается как subprocess (WebSocket sidecar) для семантического анализа SDBL запросов и BSL кода.
- **Модификации:** отсутствуют — используется upstream релизный JAR без изменений.
- **Расположение:** `frontend/src-tauri/binaries/bsl-ls/bsl-language-server-0.29.0-exec.jar` (bundled при tauri build).

Согласно LGPL-3.0, пользователь имеет право заменить bundled JAR на собственную версию bsl-language-server совместимого мажорного API. Для этого:
1. Скачайте нужную версию с https://github.com/1c-syntax/bsl-language-server/releases.
2. Замените файл `bsl-language-server-0.29.0-exec.jar` в каталоге установки на новый JAR.
3. Переименуйте новый файл в `bsl-language-server-0.29.0-exec.jar` (или измените конфигурацию через `OPTIMYZER_BSL_LS_JAR_PATH` env переменную, начиная с Sprint 7).

Текст лицензии: https://www.gnu.org/licenses/lgpl-3.0.html

---

## Eclipse Temurin JRE 21

- **Версия:** 21.0.11+10 (LTS)
- **License:** GNU General Public License v2.0 with Classpath Exception
- **Источник:** https://adoptium.net/
- **Authors:** Eclipse Foundation, OpenJDK community
- **Использование в продукте:** Java Runtime для запуска bsl-language-server.
- **Модификации:** отсутствуют — используется официальный Temurin Windows x64 JRE.
- **Расположение:** `frontend/src-tauri/binaries/jre-21/` (bundled при tauri build).

Classpath Exception разрешает linking с любыми приложениями (включая проприетарные) без необходимости открывать исходники приложения.

Текст лицензии: см. файл `frontend/src-tauri/binaries/jre-21/legal/java.base/LICENSE` после установки.

---

## sqlglot

- **Минимальная версия:** 30.8.0
- **License:** MIT
- **Источник:** https://github.com/tobymao/sqlglot
- **Автор:** Toby Mao
- **Использование в продукте:** Python библиотека для парсинга и анализа T-SQL запросов из ТЖ событий DBMSSQL (Sprint 6 — в TopSQL screen и QueryAnalyzer T-SQL view).
- **Модификации:** отсутствуют — устанавливается через `pip install sqlglot`.

---

## (Sprint 8) PerformanceStudio

В Sprint 6 НЕ интегрируется. Будет добавлено в Sprint 8 (Plan Analyzer).

- **License:** MIT
- **Источник:** https://github.com/erikdarlingdata/PerformanceStudio
- **Автор:** Erik Darling

---

## (Sprint 8) html-query-plan

В Sprint 6 НЕ интегрируется. Будет добавлено в Sprint 8 (Plan Analyzer).

- **License:** MIT
- **Источник:** https://github.com/JustinPealing/html-query-plan
- **Автор:** Justin Pealing

---

## Лицензия 1C-Optimyzer

Сам 1C-Optimyzer распространяется как **коммерческое программное обеспечение** anymasoft (Сергей Назаров).
Все права защищены © 2025-2026.
