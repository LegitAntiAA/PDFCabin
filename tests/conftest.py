"""Shared fixtures: retargeted docs dir, PDF generators (reportlab/Pillow)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import config
from app.services.library import find_unicode_font

# A TTF with Cyrillic coverage for reportlab, discovered by the app itself
# (DejaVuSans.ttf is not committed to the repo, spec 9); None -> latin-only
# Helvetica fixtures.
UNICODE_FONT = find_unicode_font()


@pytest.fixture
def docs_dir(tmp_path: Path, monkeypatch) -> Path:
    """A fresh docs directory for every test, wired into the app config."""
    target = tmp_path / "docs"
    target.mkdir()
    monkeypatch.setattr(config.settings, "docs_dir", target)
    return target


@pytest.fixture
def make_pdf(docs_dir: Path):
    """Create a text PDF inside docs_dir and return its library-relative path."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "FixtureFont"
    if UNICODE_FONT:
        pdfmetrics.registerFont(TTFont(font_name, UNICODE_FONT))
    else:  # no unicode font available -> latin-only fixtures
        font_name = "Helvetica"

    def _make(name: str, text: str = "Hello PDFCabin", pages: int = 1) -> str:
        from reportlab.pdfgen.canvas import Canvas

        target = docs_dir / name
        canvas = Canvas(str(target), pagesize=A4)
        for page_no in range(pages):
            canvas.setFont(font_name, 24)
            canvas.drawString(72, 760, f"{text} [p{page_no + 1}]")
            canvas.showPage()
        canvas.save()
        return name

    return _make


@pytest.fixture
def scanned_pdf(docs_dir: Path):
    """A PDF whose pages are images with drawn text — no text layer, OCR-able."""

    def _make(name: str, text: str = "Hello PDFCabin") -> str:
        from PIL import Image, ImageDraw, ImageFont

        width, height = 1000, 500
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        font = None
        if UNICODE_FONT:
            for size in (48, 36, 24):
                try:
                    font = ImageFont.truetype(UNICODE_FONT, size)
                    break
                except OSError:
                    continue
        if font is None:
            font = ImageFont.load_default()
        draw.text((50, 200), text, fill="black", font=font)
        target = docs_dir / name
        image.save(str(target), "PDF", resolution=100)
        return name

    return _make


@pytest.fixture
def client(docs_dir, monkeypatch):
    """httpx client bound to the FastAPI app (no live server needed)."""
    import httpx

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def no_network(monkeypatch):
    """Fail the test if anything tries to resolve hosts or open connections.

    The app promises zero outbound requests (privacy claim, spec 2), so any
    network attempt inside a test is a bug. Only the Python-level entry
    points are patched: socket.socket.connect lives on the C type and
    cannot be monkeypatched; every high-level client (httpx, urllib,
    requests) goes through create_connection or getaddrinfo anyway.
    """
    import socket

    def _blocker(attr):
        def _blocked(*args, **kwargs):
            raise AssertionError(
                f"outgoing network access attempted via socket.{attr}: "
                f"{args!r} {kwargs!r}"
            )

        return _blocked

    monkeypatch.setattr(socket, "create_connection", _blocker("create_connection"))
    monkeypatch.setattr(socket, "getaddrinfo", _blocker("getaddrinfo"))
    yield
