"""Slow OCR tests — need a real tesseract with rus+eng (spec 9, case 6)."""

from __future__ import annotations

import asyncio

import pytest


async def _wait_done(client, job_id: str, timeout: float = 240.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] in ("done", "error"):
            return job
        await asyncio.sleep(1.0)
    raise TimeoutError(f"job {job_id} did not settle in {timeout}s")


@pytest.mark.slow
async def test_ocr_russian_scan_indexed_and_searchable(client, scanned_pdf):
    """Spec 9 case 6-7 + DoD: russian scan -> searchable text -> FTS hit."""
    scanned_pdf("scan.pdf", "Проверка связи 2026")

    queued = await client.post("/api/ocr", json={"path": "scan.pdf"})
    assert queued.status_code == 202
    job = await _wait_done(client, queued.json()["job_id"])
    assert job["status"] == "done", job
    assert job["result"]["output"] == "scan_ocr.pdf"

    extracted = await client.post("/api/extract-text", json={"path": "scan_ocr.pdf"})
    assert extracted.status_code == 200
    text = " ".join(extracted.json()["pages"].values())
    # tesseract on small fixtures wavers between digits and Cyrillic forms;
    # assert that at least one expected token made it into the text layer
    tokens = [t for t in ("2026", "Проверка", "роверка", "связи") if t in text]
    assert tokens, f"OCR text: {text[:200]!r}"

    hits = (await client.get("/api/search", params={"q": tokens[0]})).json()
    assert hits and hits[0]["path"] == "scan_ocr.pdf"


@pytest.mark.slow
async def test_ocr_prior_text_needs_force(client, make_pdf):
    make_pdf("text.pdf", "plain text layer")
    queued = await client.post("/api/ocr", json={"path": "text.pdf"})
    assert queued.status_code == 202
    job = await _wait_done(client, queued.json()["job_id"])
    assert job["status"] == "error"
    assert "already has a text layer" in job["error"]

    forced = await client.post("/api/ocr", json={"path": "text.pdf", "force": True})
    assert forced.status_code == 202
    job = await _wait_done(client, forced.json()["job_id"])
    assert job["status"] == "done", job


@pytest.mark.slow
async def test_ocr_unknown_language_is_400(client, scanned_pdf):
    scanned_pdf("scan2.pdf")
    response = await client.post("/api/ocr", json={"path": "scan2.pdf", "languages": ["klingon"]})
    assert response.status_code == 400
    assert "not installed" in response.json()["detail"]
