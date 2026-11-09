# BUGS.md — значимые баги PDFCabin

## BUG-001 — VERIFIED FIXED (Debugger, интегрировано Root)
- **Компонент:** app/main.py — монтирование MCP (fastmcp 4.1.6 + FastAPI 0.162.2 + starlette 1.10.0)
- **Симптом:** GET /mcp → 404 {"detail":"Not Found"}, POST /mcp → 405 {"detail":"Method Not Allowed"} — в формате FastAPI, минуя BearerTokenMiddleware (401 не отдаётся). При этом Mount /mcp присутствовал в app.routes.
- **Root cause (подтверждён трассировкой matches() и regex-пробами):** Starlette 1.10 компилирует Mount("/mcp") как ^/mcp/(?P<path>.*)$ — голый путь /mcp не матчится; запросы проваливались в статический Mount("/") и умирали в FastAPI-хендлерах (404/405 JSON). Гипотезы A (_IncludedRouter), C (404 из sub-app), D (класс-инстанс middleware) — опровергнуты изоляциями.
- **Скрытый дефект №2 (устранён тем же патчем):** _mcp_asgi_app() создавался дважды (mount + lifespan) → отдельные session manager'ы → 500 под нагрузкой.
- **Фикс:** один общий инстанс mcp_asgi_app; app.add_route("/mcp", BearerTokenMiddleware(...), methods=[GET, POST, DELETE]) вместо mount; идемпотентный _ensure_mcp_started() (FastAPI-lifespan в проде + ленивый старт для ASGI-транспортов без lifespan).
- **Верификация:** test_api.py 13/13; test_mcp.py (fast) 5/5; реальный uvicorn — POST /mcp initialize → 200 JSON-RPC (serverInfo PDFCabin), при PDFCABIN_TOKEN без Bearer → 401 + WWW-Authenticate: Bearer, /api/health и / → 200. Повторно подтверждено Root: полный fast-набор 53/0/4, ruff чисто.
- **Известный остаток:** /mcp/ (со слэшем) уходит в статику — клиенты MCP используют ровно /mcp; при потребности добавить редирект.

## BUG-002 — FIXED (Root)
- **Компонент:** app/api.py
- **Симптом:** NameError: JSONResponse в POST /api/ocr (не было импорта).
- **Фикс:** импорт JSONResponse добавлен. Верификация: в составе прогона pytest.

## BUG-003 — FIXED (Root)
- **Компонент:** app/services/pdf_ops.py
- **Симптом:** pdf_info/page_count не проверяли магию %PDF-: файл с мусором отдачал ValueError «cannot open PDF» вместо NotPdfError; несоответствие контракту «не PDF → 400 с понятным текстом».
- **Фикс:** assert_is_pdf() в начале обеих функций. Верификация: test_not_pdf.

## BUG-004 — FIXED (Engineer 1)
- **Компонент:** tests/conftest.py
- **Симптом:** 2 ERROR в test_health/test_upload_and_list: фикстура no_network вообще отсутствовала в conftest (потеряна при перезаписи файла Root'ом), тесты ссылались на несуществующую фикстуру.
- **Фикс:** фикстура добавлена — патчит socket.create_connection и socket.getaddrinfo (C-метод socket.socket.connect непатчим в принципе, отражено в докстринге). Верификация: оба теста зелёные в составе fast-набора 53/0/4.
- **Ограничение (задокументировано):** «сырые» socket().connect() фикстура не ловит; все высокоуровневые HTTP-клиенты проходят через два патченных входа — privacy-клейм охраняется на практике.
