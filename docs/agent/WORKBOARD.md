# PDFCabin — рабочий борд (обновляет Root)

Обновлено: 2026-11-09, поздний вечер. Синхронизировано с реальностью: код backend написан, идёт фаза отладки/верификации через субагентов.

## Активные задачи

| ID | Задача | Роль/владелец | Статус | Блокеры | Следующее действие |
|---|---|---|---|---|---|
| T-01 | Окружение: python 3.11.9, venv, зависимости (fastmcp 4.1.6, pikepdf 10.18, ocrmypdf 17.14, pypdfium2 5.15) | Root | DONE | — | — |
| T-02 | Tesseract 5.5.3 rus+eng + Ghostscript (micromamba/conda-forge, user-dir, без админа) | Root | DONE | — | — |
| T-03 | Каркас репо: git init, pyproject, ruff.toml, .gitignore, LICENSE, web/ placeholder | Root | DONE | — | — |
| T-04 | services/ (pdf_ops, index FTS5, ocr, jobs) | Root (до реструктуризации) | DONE (код), верификация у QA | — | — |
| T-05 | REST API + main.py + config | Root (до реструктуризации) | DONE (код) | — | — |
| T-06 | MCP-сервер, 8 тулов | Root (до реструктуризации) | DONE (код) | — | — |
| T-07 | Тесты 5 файлов (pdf_ops, index, api, mcp, ocr-slow) | Root (до реструктуризации) | DONE (код) | — | — |
| T-08 | README.md EN + README.ru.md | Engineer-техписатель (субагент) | DONE, интегрировано (6 MINOR от Reviewer применены) | — | — |
| T-09 | Dockerfile, docker-compose.yml, CI, .dockerignore | Engineer-DevOps (субагент) | DONE, интегрировано (MINOR-2, MINOR-5 применены) | — | — |
| T-10 | **BUG-001**: /mcp mount 404/405 (Starlette 1.10 Mount-семантика) | **Debugger** (субагент) | DONE — VERIFIED (root cause + фикс main.py + реальные прогоны) | — | — |
| T-11 | Зелёный pytest (fast) + чистый ruff + scripts/e2e_mcp_http.py | **Engineer 1** (субагент) | DONE — 53/0/4, ruff чисто, E2E 10/10 и 12/12 с OCR | — | — |
| T-12 | Независимое ревью README×2 / Docker / CI против спеки | **Reviewer** (субагент) | DONE — 0 BLOCKER/MAJOR, 6 MINOR применены | — | — |
| T-13 | Полное верификационное тестирование: pytest вкл. slow OCR-кириллица, ruff, E2E-прогон uvicorn + 8 тулов, DoD-чеклист | **QA** (субагент) | DONE — 57/0/0, ruff чисто, E2E 12/12, кириллица подтверждена вручную, DoD: всё локальное VERIFIED | — | — |
| T-14 | Отклонения спеки → task.md (раздел 18 написан), docker build = Not executed (нет docker) | Root | DONE | — | — |
| T-15 | Итоговый отчёт + локальный git commit (без push) | Root | DONE — initial commit сделан локально; push — решение владельца | — | — |
| T-16 | Приёмка веб-UI от нейросети-дизайнера в реальном браузере | **User Tester** (субагент) | DONE — 9 PASS / 2 BLOCKED (ограничения тестового рантайма, не продукта) / 0 багов UI; BUG-005 (гонка pdfium) найден и VERIFIED FIXED; LOW-наблюдения: нет тостов успеха (соответствует спеке 7.1.5 — там тосты только для ошибок), слоган не переводится (брендинг — так и должно быть) | — | ручная проверка владельцем: file chooser upload + file:// (1 минута в обычном браузере) |
| T-17 | Скриншоты UI → screenshots/ + подключение в README×2 | Root | DONE — 6 скриншотов, mcp-demo.gif остаётся TODO (нужна запись экрана) | — | GIF после первого реального MCP-подключения Claude |

## Вне скоупа этой сессии
- web/ (index.html, app.js, style.css, logo.svg, favicon.svg) — делает другая нейросеть по разделу 7 спеки. В репо лежит placeholder.
- Публичный push на GitHub — только по команде владельца.
- Скриншоты/GIF, сабмиты в каталоги — после готовности UI (шаги 7–8 раздела 13).

## Принципы (напоминание)
- REST и MCP — два фасада над одними services/.
- Все пути через config.resolve_in_docs (traversal → 400).
- Ноль исходящих сетевых запросов.
- Отчётность: Telegram каждые ~10 мин активной разработки, docs/agent/ актуальны.
