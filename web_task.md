# web_task.md — техническое задание на интеграцию веб-UI с бэкендом PDFCabin

> **Кому:** нейросети, делающей веб-UI.
> **Этот файл — только техника подключения.** Дизайн, экраны, палитра, поведения UX — зафиксированы владельцем в **разделе 7 мастер-плана** (`C:\Users\LegitAA\.zcode\workspace\draft-6f4c7bdf-1f34-46d9-9b5c-f3650fc76195\task.md`) — он авторитетен, придумывать дизайн не нужно. Здесь — как подключиться к работающему бэкенду и не наступить на грабли.
> **Статус бэкенда:** готов и верифицирован (pytest 57/0/0, E2E всех эндпоинтов и 8 MCP-тулов на живом сервере). API стабилен — UI не должен требовать его изменений.

---

## 1. Deliverables

Файлы в `web/` репозитория, каждый **полностью заменяет** то, что там лежит (сейчас placeholder):

- `web/index.html`
- `web/app.js`
- `web/style.css`
- `web/logo.svg`
- `web/favicon.svg`

Файл `web/PLACEHOLDER.md` удалить. Ничего вне `web/` не создавать и не менять.

## 2. Жёсткие технические правила

- Ванильный JS, **без билд-степа, без npm, без CDN, без фреймворков**.
- **Ни одного внешнего URL** в файлах UI (шрифты системные, иконки — inline SVG path, стиль lucide). Проверка приёмки: `grep -rniE "https?://" web/` должен быть пуст (допустимо только `xmlns` в SVG).
- Все пути в HTML относительные: `./app.js`, `./style.css`.
- Ноль телеметрии/аналитики — это часть позиционирования продукта.
- Бэкенд (`app/`, `tests/`, `scripts/`, `README*`) не менять. Если кажется, что нужно изменение API — остановись и опиши проблему (см. §9), не обходи хаком.

## 3. Как запустить бэкенд локально (Windows, Git Bash)

```bash
cd "C:\Users\LegitAA\.zcode\workspace\draft-06e73ee7-32aa-459e-9912-0523cda68a6e\pdfcabin"

# OCR-окружение (нужно только для операций OCR; без него сервер тоже работает,
# но OCR вернёт ошибку "tesseract is not installed"):
export PATH="/c/Users/LegitAA/pdfcabin-tools/mmenv/Library/bin:$PATH"
export TESSDATA_PREFIX="C:\Users\LegitAA\pdfcabin-tools\mmenv\Library\share\tessdata"

./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8420
```

- После старта UI **уже раздаётся самим бэкендом**: открой `http://localhost:8420/` (это твой основной режим разработки).
- Порт **8421 на этой машине занят посторонним процессом пользователя — не используй его**. 8420 свободен.
- Сценарии с env для проверки отдельных фич:
  - токен: `PDFCABIN_TOKEN=test123` перед запуском сервера;
  - донат-иконка: `PDFCABIN_DONATE_BTC=bc1qexample...` (и/или `PDFCABIN_DONATE_TON`, `PDFCABIN_DONATE_USDT`).
- Пример файла-скана для теста OCR (Pillow установлен в venv):

```python
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGB", (1000, 500), "white")
d = ImageDraw.Draw(img)
f = ImageFont.truetype(r"C:\Windows\Fonts\calibri.ttf", 48)
d.text((50, 200), "Проверка связи 2026", fill="black", font=f)
img.save("scan_test.pdf", "PDF", resolution=100)
```

## 4. Подключение к API: база, CORS, авторизация

### 4.1 База URL (два режима работы страницы)

UI обязан работать и **с сервера**, и **с файловой системы** (file://). Решение — одна константа в начале `app.js`:

```js
const API_BASE = location.protocol.startsWith("http")
  ? ""                                                   // страница отдана бэкендом — тот же origin
  : (localStorage.getItem("pdfcabin_api_base") || "http://localhost:8420"); // file:// — явная база
```

Все запросы строятся как `fetch(API_BASE + "/api/...")`. Ничего другого конфигурировать не нужно.

### 4.2 CORS

На бэкенде CORS уже включён (`allow_origins=["*"]`, credentials выключены) — запросы с `file://` (origin `null`) проходят. Добавлять прокси/расширения браузера не нужно.

### 4.3 Авторизация

- По умолчанию токен **не задан** — все запросы идут без заголовков.
- Если `PDFCABIN_TOKEN` задан, **каждый** запрос к `/api/*` (и `/mcp`, но UI его не использует) без валидного заголовка возвращает `401` + `WWW-Authenticate: Bearer`.
- Поведение UI: любой 401 → показать форму ввода токена → сохранить в `localStorage["pdfcabin_token"]` → повторить исходный запрос **один раз** с заголовком `Authorization: Bearer <token>`. Заголовок добавляется ко всем запросам, включая XHR-аплоад и поллинг джобов.

### 4.4 Формат ошибок (единый)

Все ошибки бэкенда: JSON `{"detail": "<человекочитаемый текст>"}`. Коды: `400` (плохой вход / не-PDF / traversal), `401` (токен), `404` (файл/джоба не найдена), `409` (файл-результат уже существует; повторить с `overwrite: true`). Текст `detail` показывать в тосте как есть.

### 4.5 Контракт localStorage (имена ключей фиксированы)

| Ключ | Значения | Смысл |
|---|---|---|
| `pdfcabin_lang` | `"en"` (default) / `"ru"` | язык UI |
| `pdfcabin_theme` | `"dark"` (default) / `"light"` | тема |
| `pdfcabin_token` | строка | bearer-токен |
| `pdfcabin_api_base` | URL | только для режима file:// |

## 5. Справочник REST API (реальные формы запросов/ответов)

Все `path` — **относительные POSIX-пути от корня библиотеки docs** (как их отдаёт `/api/files`; без ведущего `/`, без `..`). Кириллица в query-параметрах кодируется автоматически, если использовать `URLSearchParams`/`URL` — делай так.

| Метод/путь | Вход | Ответ |
|---|---|---|
| `GET /api/health` | — | `{"status":"ok","version":"0.1.0","langs":["rus","eng"],"docs_dir":"…","ghostscript":true}` |
| `GET /api/files` | `?subdir=` (обычно не нужен) | `[{"name":"док.pdf","path":"док.pdf","size":12345,"mtime":1731…,"pages":3,"has_text":true}]` — `pages` может быть `null` у нечитаемого файла |
| `POST /api/upload` | multipart, **имя поля `files`** (несколько), query `?overwrite=true|false` | `{"saved":[{"path":"имя.pdf","size":123}]}`; `400` не-PDF (сервер проверяет магию) или превышение лимита; `409` имя занято |
| `GET /api/file/info` | `?path=` | `{"pages":3,"size_bytes":123,"encrypted":false,"title":"","author":"","created":""}` (строки могут быть пустыми) |
| `GET /api/file/thumb` | `?path=&page=1` | `image/png` шириной 240px; `400` если страница вне диапазона |
| `GET /api/download` | `?path=` | файл `application/pdf` |
| `DELETE /api/file` | `?path=` | `{"trash":"trash/имя.pdf"}` — **сервер сам перемещает файл в trash/, UI просто обновляет список** |
| `POST /api/merge` | `{"paths":["a.pdf","b.pdf"],"output":"m.pdf","overwrite":false}` | `{"output":"m.pdf"}`; `400` если файлов <2; `409` если `output` существует |
| `POST /api/split` | `{"path","mode":"ranges"|"every_n","value":"1-3,5" (или "3"),"output_dir"?,"overwrite"?}` | `{"outputs":["doc_p01-03.pdf","doc_p05.pdf"]}` — **соседние страницы группируются в один файл** (`1-3,5` → 2 файла) |
| `POST /api/rotate` | `{"path","pages":"1,3","angle":90|180|270,"output":"r.pdf","overwrite"?}` | `{"output":"r.pdf"}` |
| `POST /api/delete-pages` | `{"path","pages":"2,4","output":"d2.pdf","overwrite"?}` | `{"output":"d2.pdf"}` |
| `POST /api/compress` | `{"path","level":"fast"|"strong","output"?,"overwrite"?}` | `{"output":"doc_compressed.pdf","size_before":N,"size_after":M}`; `strong` без установленного Ghostscript → `400` (проверяй `health.ghostscript` заранее) |
| `POST /api/extract-text` | `{"path","pages":"1-3,5"}` (pages опционален) | `{"pages":{"1":"текст","2":"…"}}` — **ключи-строки** |
| `POST /api/ocr` | `{"path","languages":["rus","eng"],"force":false}` (оба поля опциональны) | **`202`** `{"job_id":"hex12"}`; `400` если язык не установлен у tesseract или в файле уже есть текст без `force` |
| `GET /api/jobs` | — | массив джобов, **активные первыми**, затем завершённые |
| `GET /api/jobs/{id}` | — | джоба или `404`, структура ниже |
| `GET /api/search` | `?q=…&limit=20` (1..100) | `[{"path":"scan_ocr.pdf","page":1,"snippet":"…<mark>слово</mark>…"}]` |
| `GET /api/stats` | — | `{"files":1,"pages":3,"index_ok":true}` |
| `GET /api/donate` | — | `{"addresses":[{"network":"BTC","address":"…"}]}`; подписи сетей приходят из конфига автора (сейчас: `BTC`, `ETH (ERC-20)`, `USDT (BEP-20)`, `USDT (TRC-20)`); адреса вшиты по умолчанию, пусто → `{"addresses":[]}` |

Синтаксис `pages` везде один: `1-3,5,8-` (1-базовый, включительно, `8-` = до конца).

### 5.1 Структура джобы (для поллинга OCR)

```json
{
  "id": "a1b2c3d4e5f6",
  "kind": "ocr",
  "params": {"path": "scan.pdf", "languages": ["rus", "eng"], "force": false},
  "status": "queued | running | done | error",
  "progress": 0,
  "created_at": 1731150000.0,
  "finished_at": null,
  "result": null,
  "error": null
}
```

При `done`: `result.output` — имя созданного файла (`scan_ocr.pdf`), `result.pages_indexed` — число страниц. При `error`: текст в `error` (показать в тосте). OCR занимает секунды-минуты (реальный tesseract), поэтому поллинг `GET /api/jobs/{id}` раз в ~1.5 с, только пока есть джобы в `queued|running`.

## 6. Технические грабли (проверено на этом бэкенде)

1. **Прогресс аплоада** — только XHR (`xhr.upload.onprogress`); `fetch` upload-progress не даёт. Пример обёртки:

```js
function uploadWithProgress(files, token, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => (xhr.status < 400 ? resolve(JSON.parse(xhr.responseText)) : reject(safeJson(xhr)));
    xhr.onerror = () => reject(new Error("network error"));
    const form = new FormData();
    for (const f of files) form.append("files", f, f.name);
    xhr.send(form);
  });
}
```

2. **Сниппеты поиска** приходят с тегами `<mark>…</mark>` от FTS5. Рендер только так (иначе XSS на именах/тексте PDF):

```js
function renderSnippet(s) {
  const esc = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc.replaceAll("&lt;mark&gt;", "<mark>").replaceAll("&lt;/mark&gt;", "</mark>");
}
```

3. **Превью-кэш**: `GET /api/file/thumb` рендерит PNG на лету — кэшируй в памяти `Map` по ключу `` `${path}#${page}` ``, иначе скролл списка будет дёргать сервер на каждый чих.
4. **409 на имени** (upload/merge/…): тост с текстом `detail` + возможность повторить с `overwrite: true` (чекбокс/кнопка «Заменить»).
5. **`has_text`**: `true` → бейдж `OCR ✓`, `false` → `SCANNED`. После завершения OCR **обнови список** (`GET /api/files`) — у нового `*_ocr.pdf` бейдж сменится.
6. **`/api/health.ghostscript === false`** → в модалке Compress предупреждай, что `strong` недоступен (сервер вернёт 400).
7. Файлы, подложенные в `docs/` напрямую (мимо upload), появляются в списке, но в поиск не попадают до OCR — это норма v0.1, не баг.

## 7. Техническая приёмка (чеклист)

Прогнать на живом сервере (§3) и зафиксировать результат по каждому пункту:

1. `grep -rniE "https?://" web/` — пусто (кроме `xmlns` в SVG).
2. `http://localhost:8420/` открывает рабочую страницу; в network-панели нет запросов на внешние хосты.
3. Страница, открытая как `file://`, работает против `http://localhost:8420` (механизм §4.1).
4. Upload: PDF с кириллическим именем → карточка с превью/размером/страницами; не-PDF → тост с `detail`, запрос не отправляется (клиентская проверка расширения).
5. Merge (≥2), Split, Rotate, Delete-pages, Compress fast → тост успеха + обновление списка; конфликт имён → 409 обработан.
6. OCR: `202` → поллинг → `done` → в списке `scan_ocr.pdf` с бейджем `OCR ✓` → поиск по слову из скана находит сниппет с подсветкой → клик скачивает файл.
7. Delete → карточка исчезла (на сервере файл в `trash/`).
8. Donate: без env-адресов иконки нет; с `PDFCABIN_DONATE_BTC=...` — сердечко в шапке → модалка со списком адресов и кнопкой Copy.
9. Токен: сервер с `PDFCABIN_TOKEN=test123` → первый запрос 401 → форма → сохранение → ретрай успешен, дальше всё (включая XHR-аплоад и поллинг) ходит с заголовком.
10. Тема и язык переключаются и переживают перезагрузку (localStorage-ключи из §4.5).

## 8. Структура app.js

Один файл, без фреймворков, ориентир 800–1000 строк: константы (`API_BASE`, `I18N` словарь en/ru) → обёртки API (fetch с токеном + XHR-аплоад) → state → render-функции → обработчики. Словарь `I18N` покрывает **все** строки UI, включая тексты тостов `Copy address` / `Скопировать адрес`.

## 9. Если что-то не сходится

API стабилен и покрыт тестами. Если обнаружишь расхождение с этим документом или недостающий для UI эндпоинт — **не обходить хаком, не менять бэкенд**: опиши проблему (эндпоинт, ожидание, факт, curl-воспроизведение) в отчёте/в конце этого файла (раздел «Отклонения UI»), решение согласует владелец.

## 10. Запрещено

- менять что-либо вне `web/`;
- добавлять зависимости, билд-степ, CDN, внешние шрифты/иконки/скрипты;
- телеметрия, «анонимная статистика», внешние запросы — запрещены полностью;
- трогать `/mcp` и MCP-часть (агенты подключаются напрямую, UI им не нужен).

---

## Отклонения UI (заполняет нейросеть UI при несовпадениях)

_(пока пусто)_
