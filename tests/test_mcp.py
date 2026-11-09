"""MCP tool tests via the in-process fastmcp client (spec 9, case 10)."""

from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app import config
from app.mcp_server import mcp
from app.services.library import find_unicode_font

EXPECTED_TOOLS = {
    "list_documents",
    "pdf_info",
    "pdf_merge",
    "pdf_split",
    "pdf_compress",
    "pdf_ocr",
    "extract_text",
    "search_documents",
    "upload_document",
    "create_document",
    "save_document",
    "delete_document",
    "rename_document",
    "pdf_rotate",
    "pdf_delete_pages",
}


def _text(result) -> str:
    """CallToolResult -> plain text, across fastmcp result shapes."""
    if getattr(result, "data", None) is not None:
        return str(result.data)
    return "\n".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )


async def test_exactly_fifteen_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == EXPECTED_TOOLS


async def test_list_documents_and_info(make_pdf):
    make_pdf("doc.pdf", pages=2)
    async with Client(mcp) as client:
        listing = _text(await client.call_tool("list_documents", {}))
        assert "doc.pdf (2 pages)" in listing

        info = _text(await client.call_tool("pdf_info", {"path": "doc.pdf"}))
        assert "pages: 2" in info
        assert "has_text: True" in info


async def test_merge_split_compress_extract(make_pdf):
    make_pdf("a.pdf", "alpha text", pages=2)
    make_pdf("b.pdf", "beta text", pages=1)
    async with Client(mcp) as client:
        merged = _text(
            await client.call_tool(
                "pdf_merge", {"paths": ["a.pdf", "b.pdf"], "output": "m.pdf"}
            )
        )
        assert "Created m.pdf (3 pages)" in merged

        split = _text(
            await client.call_tool("pdf_split", {"path": "m.pdf", "mode": "every_n", "value": "2"})
        )
        assert "m_p01-02.pdf" in split and "m_p03.pdf" in split

        compressed = _text(
            await client.call_tool(
                "pdf_compress", {"path": "a.pdf", "output": "a_c.pdf", "level": "fast"}
            )
        )
        assert "Created a_c.pdf" in compressed

        text = _text(await client.call_tool("extract_text", {"path": "a.pdf", "pages": "1"}))
        assert "alpha text" in text


async def test_search_after_indexing(make_pdf):
    make_pdf("zebra.pdf", "the striped zebra hides", pages=2)
    async with Client(mcp) as client:
        misses = _text(await client.call_tool("search_documents", {"query": "zebra"}))
        assert "No matches" in misses  # not indexed yet -> honest answer

        from app.services import index

        index.index_pdf(config.docs_dir() / "zebra.pdf")
        hits = _text(await client.call_tool("search_documents", {"query": "zebra"}))
        assert "zebra.pdf" in hits and "<mark>" in hits


async def test_error_reaches_the_agent(make_pdf):
    make_pdf("a.pdf")
    async with Client(mcp) as client:
        with pytest.raises(ToolError):  # fastmcp surfaces tool failures as ToolError
            await client.call_tool(
                "pdf_merge", {"paths": ["a.pdf", "missing.pdf"], "output": "x.pdf"}
            )


def _pdf_bytes(text: str = "mcp file transfer", pages: int = 1) -> bytes:
    import io

    from reportlab.pdfgen.canvas import Canvas

    buffer = io.BytesIO()
    canvas = Canvas(buffer)
    for page_no in range(pages):
        canvas.setFont("Helvetica", 24)
        canvas.drawString(72, 700, f"{text} [p{page_no + 1}]")
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


async def test_upload_document_from_os_path(docs_dir, tmp_path):
    source = tmp_path / "incoming.pdf"
    source.write_bytes(_pdf_bytes())
    async with Client(mcp) as client:
        saved = _text(await client.call_tool("upload_document", {"source_path": str(source)}))
        assert saved.startswith("Saved incoming.pdf (")
        assert "pages: 1" in _text(await client.call_tool("pdf_info", {"path": "incoming.pdf"}))

        with pytest.raises(ToolError):  # name collision without overwrite
            await client.call_tool("upload_document", {"source_path": str(source)})
        again = _text(
            await client.call_tool(
                "upload_document", {"source_path": str(source), "overwrite": True}
            )
        )
        assert again.startswith("Saved incoming.pdf (")

        not_pdf = tmp_path / "photo.gif"
        not_pdf.write_bytes(b"GIF89a-nope")
        with pytest.raises(ToolError, match="not a PDF file"):
            await client.call_tool("upload_document", {"source_path": str(not_pdf)})

        # a file that already lives in the library is refused, not copied onto itself
        with pytest.raises(ToolError, match="already in the library"):
            await client.call_tool(
                "upload_document", {"source_path": str(config.docs_dir() / "incoming.pdf")}
            )


async def test_save_document_to_os_path(make_pdf, docs_dir, tmp_path):
    make_pdf("exportme.pdf", "export body")
    original = (docs_dir / "exportme.pdf").read_bytes()
    target = tmp_path / "deep" / "nested" / "copy.pdf"
    async with Client(mcp) as client:
        saved = _text(
            await client.call_tool(
                "save_document", {"path": "exportme.pdf", "target_path": str(target)}
            )
        )
        assert str(target) in saved
        assert target.read_bytes() == original  # parents created, bytes intact

        with pytest.raises(ToolError):  # collision without overwrite
            await client.call_tool(
                "save_document", {"path": "exportme.pdf", "target_path": str(target)}
            )
        await client.call_tool(
            "save_document",
            {"path": "exportme.pdf", "target_path": str(target), "overwrite": True},
        )
        assert target.read_bytes() == original


_HAS_UNICODE_FONT = find_unicode_font() is not None


@pytest.mark.skipif(not _HAS_UNICODE_FONT, reason="no unicode font on this system")
async def test_create_document_cyrillic_and_pagination(docs_dir):
    long_text = "\n".join(f"строка номер {i}" for i in range(1, 101))
    async with Client(mcp) as client:
        created = _text(
            await client.call_tool(
                "create_document",
                {"text": f"Уникальный жираф в тексте\n{long_text}", "name": "created.pdf"},
            )
        )
        assert "Created created.pdf (3 pages)" in created  # 101 lines / 45 per page

        text = _text(await client.call_tool("extract_text", {"path": "created.pdf"}))
        assert "жираф" in text and "строка номер 100" in text

        with pytest.raises(ToolError):  # exists now
            await client.call_tool("create_document", {"text": "again", "name": "created.pdf"})
        overwritten = _text(
            await client.call_tool(
                "create_document",
                {"text": "свежий текст", "name": "created.pdf", "overwrite": True},
            )
        )
        assert "Created created.pdf (1 pages)" in overwritten


async def test_delete_document_moves_to_trash(make_pdf):
    make_pdf("trashme.pdf")
    async with Client(mcp) as client:
        result = _text(await client.call_tool("delete_document", {"path": "trashme.pdf"}))
        assert result.startswith("trash/trashme.pdf")
        with pytest.raises(ToolError):  # gone from the library
            await client.call_tool("pdf_info", {"path": "trashme.pdf"})


async def test_rename_document_updates_search_index(make_pdf):
    make_pdf("old_name.pdf", "the rename word lives here")
    make_pdf("occupied.pdf")
    from app.services import index

    index.index_pdf(config.docs_dir() / "old_name.pdf")
    async with Client(mcp) as client:
        new_path = _text(
            await client.call_tool(
                "rename_document", {"path": "old_name.pdf", "new_name": "new name.pdf"}
            )
        )
        assert new_path == "new name.pdf"

        hits = _text(await client.call_tool("search_documents", {"query": "rename word"}))
        assert "new name.pdf" in hits
        assert "old_name.pdf" not in hits

        with pytest.raises(ToolError):  # collision with an existing name
            await client.call_tool(
                "rename_document", {"path": "new name.pdf", "new_name": "occupied.pdf"}
            )
        renamed = _text(
            await client.call_tool(
                "rename_document",
                {"path": "new name.pdf", "new_name": "occupied.pdf", "overwrite": True},
            )
        )
        assert renamed == "occupied.pdf"


async def test_rotate_and_delete_pages_tools(make_pdf):
    make_pdf("ops.pdf", pages=4)
    async with Client(mcp) as client:
        rotated = _text(
            await client.call_tool(
                "pdf_rotate",
                {"path": "ops.pdf", "pages": "1", "angle": 90, "output": "ops_r.pdf"},
            )
        )
        assert "Created ops_r.pdf (4 pages)" in rotated

        deleted = _text(
            await client.call_tool(
                "pdf_delete_pages", {"path": "ops.pdf", "pages": "1,3", "output": "ops_d.pdf"}
            )
        )
        assert "Created ops_d.pdf (2 pages)" in deleted

        with pytest.raises(ToolError):  # invalid angle -> clear tool error
            await client.call_tool(
                "pdf_rotate",
                {"path": "ops.pdf", "pages": "1", "angle": 45, "output": "bad.pdf"},
            )


@pytest.mark.slow
async def test_ocr_and_search_end_to_end(scanned_pdf):
    """Spec 9 case 10: OCR through MCP, then search finds the text."""
    scanned_pdf("scan.pdf", "SIGNAL 2026")
    async with Client(mcp) as client:
        result = _text(await client.call_tool("pdf_ocr", {"path": "scan.pdf"}))
        assert "OCR complete" in result

        hits = _text(await client.call_tool("search_documents", {"query": "SIGNAL"}))
        assert "scan_ocr.pdf" in hits
