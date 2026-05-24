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

## PerformanceStudio (PlanViewer.Cli)

- **Версия:** 1.11.2
- **License:** MIT
- **Источник:** https://github.com/erikdarlingdata/PerformanceStudio
- **Автор:** Erik Darling (Erik Darling Data)
- **Copyright:** © 2024-2026 Erik Darling Data
- **Использование в продукте:** консольная утилита `planview.exe` — анализатор SHOWPLAN XML с 30 antipattern rules (Sprint 7 Phase A). Запускается через subprocess wrapper в `backend/src/optimyzer_backend/planview/cli.py`.
- **Модификации:** отсутствуют — собирается из upstream sources через `dotnet publish`.
- **Расположение:** `frontend/src-tauri/binaries/planview/planview.exe` + self-contained .NET 10 runtime (~96 МБ, bundled при tauri build).

CLI собирается локально через скрипт `scripts/setup-planview-binary.ps1` (требуется .NET 10 SDK, ставится user-mode через dotnet-install.ps1 если отсутствует).

Лицензия MIT разрешает коммерческое использование, копирование и модификации с сохранением copyright notice.

---

## html-query-plan

- **Версия:** 2.6.1
- **License:** MIT
- **Источник:** https://github.com/JustinPealing/html-query-plan
- **Автор:** Justin Pealing
- **Использование в продукте:** SSMS-style визуализация SHOWPLAN XML через XSLT + SVG (Sprint 7 Phase B). Импортируется как npm пакет `html-query-plan` в frontend, рендерит execution plan в React-обёртке `PlanVisualization.tsx`.
- **Модификации:** отсутствуют — установлено через `npm install html-query-plan`.
- **CSS:** `node_modules/html-query-plan/css/qp.css` + `qp_icons.png` (sprite). Vite разрешает PNG относительно CSS, бандлит автоматически.

---

## Лицензия 1C-Optimyzer

Сам 1C-Optimyzer распространяется как **коммерческое программное обеспечение** anymasoft (Сергей Назаров).
Все права защищены © 2025-2026.
