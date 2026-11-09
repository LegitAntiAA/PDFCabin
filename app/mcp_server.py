"""FastMCP server: 8 tools — one facade over app.services (the same functions REST uses).

Principles (spec 6.7): few but smart tools, meaningful docstrings (the agent reads
them to pick a tool), compact answers, library-relative paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP

from . import config
from .services import index, jobs, ocr, pdf_ops

mcp = FastMCP("PDFCabin")

_MAX_TEXT_CHARS = 24000  # keep answers compact: agents pay with context window


def _path(rel: str) -> Path:
    return config.resolve_in_docs(rel)


def _walk_pdfs():
    docs = config.docs_dir()
    for dirpath, dirnames, filenames in os.walk(docs):
        dirnames[:] = [d for d in dirnames if d != "trash" and not d.startswith(".")]
        for name in sorted(filenames):
            if name.lower().endswith(".pdf"):
                yield Path(dirpath) / name


@mcp.tool
def list_documents() -> str:
    """List PDF documents in the PDFCabin library with their page counts.

    Call this first to discover what exists; every other tool takes a `path`
    relative to the library root, exactly as returned here.
    """
    lines = []
    for path in _walk_pdfs():
        try:
            pages = pdf_ops.page_count(path)
        except ValueError:
            pages = "?"  # unreadable file — still listed
        lines.append(f"{config.rel_from_docs(path)} ({pages} pages)")
    return "\n".join(lines) or "The library is empty — no PDF files yet."


@mcp.tool
def pdf_info(path: str) -> str:
    """Metadata about one PDF: page count, size, encryption, title/author, has_text.

    has_text tells whether the file already carries a text layer: False means
    a scan that needs pdf_ocr before text extraction or search will work.
    """
    target = _path(path)
    info = pdf_ops.pdf_info(target)
    try:
        first_page_text = next(iter(pdf_ops.extract_text(target, "1").values()), "")
        has_text = bool(first_page_text.strip())
    except ValueError:
        has_text = False
    return (
        f"path: {path}\npages: {info['pages']}\nsize: {info['size_bytes']} bytes\n"
        f"encrypted: {info['encrypted']}\ntitle: {info['title'] or '-'}\n"
        f"author: {info['author'] or '-'}\nhas_text: {has_text}"
    )


@mcp.tool
def pdf_merge(paths: list[str], output: str) -> str:
    """Merge several PDFs (in the given order) into one new file.

    `paths` is a list of library-relative paths; `output` must not exist yet.
    """
    result = pdf_ops.pdf_merge([_path(p) for p in paths], _path(output))
    return f"Created {config.rel_from_docs(result)} ({pdf_ops.page_count(result)} pages)."


@mcp.tool
def pdf_split(path: str, mode: str, value: str) -> str:
    """Split a PDF into several new files, named after the source (doc.pdf -> doc_p01-03.pdf).

    mode="ranges": value is a 1-based page spec like "1-3,5" — each range or page
    becomes its own file. mode="every_n": value is an integer N — pages are grouped
    N at a time ("2" turns a 5-page PDF into 3 files).
    """
    outputs = pdf_ops.pdf_split(_path(path), mode, value)
    return "Created:\n" + "\n".join(config.rel_from_docs(item) for item in outputs)


@mcp.tool
def pdf_compress(path: str, output: str, level: str = "fast") -> str:
    """Compress a PDF and report the size saving.

    level="fast" (default) is lossless and safe for text PDFs. level="strong"
    (needs Ghostscript) downsamples images — use it for scans; it can visibly
    degrade text-heavy PDFs.
    """
    result = pdf_ops.pdf_compress(_path(path), _path(output), level)
    saved = result["size_before"] - result["size_after"]
    percent = round(100 * saved / result["size_before"], 1) if result["size_before"] else 0.0
    return (
        f"Created {config.rel_from_docs(result['output'])}: "
        f"{result['size_before']} -> {result['size_after']} bytes ({percent}% smaller)."
    )


@mcp.tool
async def pdf_ocr(path: str, languages: str = "rus+eng", force: bool = False) -> str:
    """Run OCR on a scanned PDF to add a searchable text layer, then index the text.

    Blocks until finished (OCR is CPU-bound and runs one job at a time).
    languages: "+"-separated tesseract codes such as "rus+eng" (default) or "eng".
    force=True re-OCRs files that already contain a text layer. After success the
    document is searchable via search_documents.
    """
    source = _path(path)
    if not source.is_file():
        raise ValueError(f"file not found: {path}")
    languages_list = ocr.parse_langs(languages)
    output = source.with_name(f"{source.stem}_ocr.pdf")
    job_id = await jobs.submit_ocr(source, output, languages_list, force)
    job = await jobs.wait_job(job_id)
    if job["status"] == "error":
        raise ValueError(f"OCR failed: {job['error']}")
    return (
        f"OCR complete: {config.rel_from_docs(output)} "
        f"({job['result']['pages_indexed']} pages, languages: {'+'.join(languages_list)}). "
        "The text is now searchable."
    )


@mcp.tool
def extract_text(path: str, pages: str | None = None) -> str:
    """Read the text of a PDF ("read this document for me").

    pages: 1-based spec like "1-3,5" or "8-" (to the end); omit for all pages.
    Very long output is truncated — pass a `pages` range for precise reading.
    Returns "no text layer" if the PDF is a scan; run pdf_ocr first.
    """
    texts = pdf_ops.extract_text(_path(path), pages)
    if not any(texts.values()):
        return "No text layer found — this looks like a scan; run pdf_ocr first."
    rendered = "\n\n".join(
        f"--- page {page_no} ---\n{text}" for page_no, text in texts.items()
    )
    if len(rendered) > _MAX_TEXT_CHARS:
        rendered = rendered[:_MAX_TEXT_CHARS] + "\n… [truncated — pass a `pages` range]"
    return rendered


@mcp.tool
def search_documents(query: str, limit: int = 20) -> str:
    """Full-text search across indexed PDFs.

    Files enter the index when OCR completes (pdf_ocr); to make a file that
    already has a text layer searchable, run pdf_ocr with force=True.
    Returns path, page number and a snippet with the matched words in <mark>
    tags. Matching is by exact word forms (no stemming) — search the word as
    it appears in the document.
    """
    results = index.search(query, limit)
    if not results:
        return (
            "No matches. Only indexed files are searchable — run pdf_ocr on scans, "
            "or the file may simply not contain the word."
        )
    return "\n\n".join(f"{item['path']} p.{item['page']}: {item['snippet']}" for item in results)
