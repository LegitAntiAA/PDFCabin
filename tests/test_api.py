"""REST API tests (spec 9, cases 8-9) against the ASGI app."""

from __future__ import annotations

from app import config


async def test_health(client, no_network):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["langs"] == ["rus", "eng"]
    assert "ghostscript" in body


async def test_token_required_on_api(client, monkeypatch):
    monkeypatch.setattr(config.settings, "token", "sekret")
    assert (await client.get("/api/health")).status_code == 401
    assert (
        await client.get("/api/health", headers={"Authorization": "Bearer wrong"})
    ).status_code == 401
    ok = await client.get("/api/health", headers={"Authorization": "Bearer sekret"})
    assert ok.status_code == 200


async def test_token_required_on_mcp(client, monkeypatch):
    monkeypatch.setattr(config.settings, "token", "sekret")
    response = await client.get("/mcp")
    assert response.status_code == 401
    assert b"Bearer" in response.content
    with_header = await client.get("/mcp", headers={"Authorization": "Bearer sekret"})
    assert with_header.status_code != 401


async def test_path_traversal_blocked(client):
    for evil in ("../x.pdf", "a/../../x.pdf", "C:/Windows/win.ini", ""):
        response = await client.get("/api/file/info", params={"path": evil})
        assert response.status_code in (400, 422), evil
        assert "detail" in response.json()
    # pre-encoded traversal that never touches params re-encoding
    raw = await client.get("/api/file/info?path=..%2Fx.pdf")
    assert raw.status_code == 400


async def test_upload_and_list(client, no_network):
    pdf_bytes = _minimal_pdf()
    ok = await client.post(
        "/api/upload", files={"files": ("отчёт декабрь.pdf", pdf_bytes, "application/pdf")}
    )
    assert ok.status_code == 200
    assert ok.json()["saved"][0]["path"] == "отчёт декабрь.pdf"

    fake = await client.post(
        "/api/upload", files={"files": ("photo.gif", b"GIF89a-nope", "image/gif")}
    )
    assert fake.status_code == 400

    dup = await client.post(
        "/api/upload", files={"files": ("отчёт декабрь.pdf", pdf_bytes, "application/pdf")}
    )
    assert dup.status_code == 409
    over = await client.post(
        "/api/upload",
        files={"files": ("отчёт декабрь.pdf", pdf_bytes, "application/pdf")},
        params={"overwrite": "true"},
    )
    assert over.status_code == 200

    listing = (await client.get("/api/files")).json()
    assert [item["path"] for item in listing] == ["отчёт декабрь.pdf"]
    item = listing[0]
    assert item["pages"] == 1 and item["has_text"] is True and item["size"] > 0


def _minimal_pdf() -> bytes:
    """Tiny valid single-page PDF with one word of text."""
    import io

    from reportlab.pdfgen.canvas import Canvas

    buffer = io.BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 700, "findme")
    canvas.save()
    return buffer.getvalue()


async def test_info_and_thumb_and_download(client, make_pdf):
    make_pdf("doc.pdf", pages=2)
    info = (await client.get("/api/file/info", params={"path": "doc.pdf"})).json()
    assert info["pages"] == 2

    thumb = await client.get("/api/file/thumb", params={"path": "doc.pdf"})
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/png"
    assert thumb.content[:4] == b"\x89PNG"

    bad_page = await client.get("/api/file/thumb", params={"path": "doc.pdf", "page": 9})
    assert bad_page.status_code == 400

    download = await client.get("/api/download", params={"path": "doc.pdf"})
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF")

    missing = await client.get("/api/file/info", params={"path": "nope.pdf"})
    assert missing.status_code == 404


async def test_merge_split_rotate_delete_pages_compress(client, make_pdf):
    make_pdf("a.pdf", pages=2)
    make_pdf("b.pdf", pages=1)

    merged = await client.post(
        "/api/merge", json={"paths": ["a.pdf", "b.pdf"], "output": "m.pdf"}
    )
    assert merged.status_code == 200
    assert merged.json()["output"] == "m.pdf"

    conflict = await client.post(
        "/api/merge", json={"paths": ["a.pdf", "b.pdf"], "output": "m.pdf"}
    )
    assert conflict.status_code == 409

    one = await client.post(
        "/api/merge", json={"paths": ["a.pdf"], "output": "x.pdf"}
    )
    assert one.status_code == 400  # merge needs >= 2 files

    split = await client.post(
        "/api/split", json={"path": "m.pdf", "mode": "ranges", "value": "1,3"}
    )
    assert split.status_code == 200
    # pdf_split groups consecutive runs (spec example "1-3,5" -> "_p01-03.pdf"),
    # so a value with no adjacent pages is the unambiguous API-level case.
    assert split.json()["outputs"] == ["m_p01.pdf", "m_p03.pdf"]

    bad_mode = await client.post(
        "/api/split", json={"path": "m.pdf", "mode": "nope", "value": "1"}
    )
    assert bad_mode.status_code == 400

    rotated = await client.post(
        "/api/rotate", json={"path": "a.pdf", "pages": "1", "angle": 90, "output": "r.pdf"}
    )
    assert rotated.status_code == 200

    bad_angle = await client.post(
        "/api/rotate", json={"path": "a.pdf", "pages": "1", "angle": 45, "output": "r2.pdf"}
    )
    assert bad_angle.status_code == 400

    deleted = await client.post(
        "/api/delete-pages", json={"path": "m.pdf", "pages": "3", "output": "m2.pdf"}
    )
    assert deleted.status_code == 200

    compressed = await client.post(
        "/api/compress", json={"path": "m2.pdf", "level": "fast", "output": "c.pdf"}
    )
    assert compressed.status_code == 200
    body = compressed.json()
    assert {"output", "size_before", "size_after"} <= set(body)

    bad_level = await client.post(
        "/api/compress", json={"path": "m2.pdf", "level": "extreme", "output": "x.pdf"}
    )
    assert bad_level.status_code == 400

    strong = await client.post(
        "/api/compress", json={"path": "m2.pdf", "level": "strong", "output": "cs.pdf"}
    )
    # 400 (ghostscript missing locally) or 200 (gs installed) — both valid, never a crash.
    assert strong.status_code in (200, 400)


async def test_extract_text_endpoint(client, make_pdf):
    make_pdf("t.pdf", "findme now", pages=2)
    response = await client.post("/api/extract-text", json={"path": "t.pdf", "pages": "1"})
    assert response.status_code == 200
    pages = response.json()["pages"]
    assert "findme" in pages["1"]


async def test_delete_moves_to_trash(client, make_pdf):
    make_pdf("bye.pdf")
    response = await client.delete("/api/file", params={"path": "bye.pdf"})
    assert response.status_code == 200
    assert response.json()["trash"].startswith("trash/bye.pdf")
    listing = (await client.get("/api/files")).json()
    assert listing == []
    gone = await client.get("/api/file/info", params={"path": "bye.pdf"})
    assert gone.status_code == 404


async def test_ocr_job_lifecycle(client, make_pdf, monkeypatch):
    """202 + job id + completion, with the real OCR engine stubbed out."""
    from app.services import ocr as ocr_service

    make_pdf("s.pdf")

    def fake_ocr_and_index(input_path, output_path, languages, force):
        import shutil

        shutil.copyfile(input_path, output_path)
        return 1

    monkeypatch.setattr(ocr_service, "ocr_and_index", fake_ocr_and_index)

    queued = await client.post("/api/ocr", json={"path": "s.pdf"})
    assert queued.status_code == 202
    job_id = queued.json()["job_id"]

    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert job["kind"] == "ocr"

    for _ in range(50):
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] in ("done", "error"):
            break
    assert job["status"] == "done"
    assert job["result"]["pages_indexed"] == 1

    unknown = await client.get("/api/jobs/zzz")
    assert unknown.status_code == 404

    all_jobs = (await client.get("/api/jobs")).json()
    assert any(j["id"] == job_id for j in all_jobs)


async def test_search_endpoint(client, make_pdf):
    make_pdf("searchme.pdf", "a unique zebra walks", pages=1)
    await client.post("/api/extract-text", json={"path": "searchme.pdf"})  # sanity
    from app.services import index

    index.index_pdf(config.docs_dir() / "searchme.pdf")
    hits = (await client.get("/api/search", params={"q": "zebra"})).json()
    assert hits and hits[0]["path"] == "searchme.pdf"
    assert "<mark>" in hits[0]["snippet"]

    empty = await client.get("/api/search", params={"q": "   "})
    assert empty.status_code == 400


async def test_stats_and_donate(client, make_pdf, monkeypatch):
    make_pdf("st.pdf", pages=2)
    stats = (await client.get("/api/stats")).json()
    assert {"files", "pages", "index_ok"} <= set(stats)

    # owner's addresses are baked in as defaults; env/monkeypatch overrides them
    for field in (
        "donate_btc", "donate_eth", "donate_ton", "donate_usdt_bep20", "donate_usdt_trc20"
    ):
        monkeypatch.setattr(config.settings, field, "")
    empty = (await client.get("/api/donate")).json()
    assert empty == {"addresses": []}

    monkeypatch.setattr(config.settings, "donate_btc", "bc1qtest")
    monkeypatch.setattr(config.settings, "donate_usdt_trc20", "TQtest")
    donate = (await client.get("/api/donate")).json()
    assert donate["addresses"] == [
        {"network": "BTC", "address": "bc1qtest"},
        {"network": "USDT (TRC-20)", "address": "TQtest"},
    ]


async def test_root_serves_static(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert b"PDFCabin" in response.content


async def test_parallel_thumbs_never_crash(client, make_pdf):
    """Regression BUG-005: pdfium is not thread-safe; parallel thumbnail renders
    (browser loads all cards at once) crashed with access violations -> 500."""
    import asyncio

    from app import config
    from app.services import pdf_ops

    make_pdf("par.pdf", pages=3)
    pdf_ops.pdf_compress(config.docs_dir() / "par.pdf", config.docs_dir() / "par_c.pdf", "fast")

    names = ["par.pdf", "par_c.pdf"] * 4
    responses = await asyncio.gather(
        *(client.get("/api/file/thumb", params={"path": name}) for name in names)
    )
    for response in responses:
        assert response.status_code == 200, response.text[:200]
        assert response.content[:4] == b"\x89PNG"
