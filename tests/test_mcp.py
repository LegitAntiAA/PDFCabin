"""MCP tool tests via the in-process fastmcp client (spec 9, case 10)."""

from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app import config
from app.mcp_server import mcp

EXPECTED_TOOLS = {
    "list_documents",
    "pdf_info",
    "pdf_merge",
    "pdf_split",
    "pdf_compress",
    "pdf_ocr",
    "extract_text",
    "search_documents",
}


def _text(result) -> str:
    """CallToolResult -> plain text, across fastmcp result shapes."""
    if getattr(result, "data", None) is not None:
        return str(result.data)
    return "\n".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )


async def test_exactly_eight_tools():
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


@pytest.mark.slow
async def test_ocr_and_search_end_to_end(scanned_pdf):
    """Spec 9 case 10: OCR through MCP, then search finds the text."""
    scanned_pdf("scan.pdf", "SIGNAL 2026")
    async with Client(mcp) as client:
        result = _text(await client.call_tool("pdf_ocr", {"path": "scan.pdf"}))
        assert "OCR complete" in result

        hits = _text(await client.call_tool("search_documents", {"query": "SIGNAL"}))
        assert "scan_ocr.pdf" in hits
