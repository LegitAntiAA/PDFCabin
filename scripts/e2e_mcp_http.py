#!/usr/bin/env python
"""End-to-end check of a RUNNING PDFCabin server: REST + all MCP tools over HTTP.

Start the server first (uvicorn app.main:app), then:

    python scripts/e2e_mcp_http.py                     # fast checks (~seconds)
    python scripts/e2e_mcp_http.py --with-ocr          # + pdf_ocr (slow, needs tesseract)
    python scripts/e2e_mcp_http.py --base-url http://127.0.0.1:8420 --token sekret

What it does: checks /api/health, uploads two small generated PDFs via
POST /api/upload, then drives the MCP tools through fastmcp's streamable-HTTP
client (list_documents, pdf_info, pdf_merge, pdf_split, pdf_compress fast,
extract_text, search_documents, create_document, save_document,
delete_document; pdf_ocr with --with-ocr). Every file created along the way
is removed via DELETE /api/file or delete_document, so the user's library
keeps only what lands in docs_dir/trash — the same place the UI "Delete" uses.

Prints one OK/FAIL line per step and finishes with "E2E PASS" (exit 0) or the
list of failed steps with their exceptions (exit 1).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import shutil
import sys
import tempfile

import httpx

# Large clear font for the scanned fixture (OCR needs readable glyphs).
_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\DejaVuSans.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

_SEARCH_WORD = "cranberry"  # unique enough to prove a real index hit


class Critical(Exception):
    """A failure that makes the remaining steps meaningless (health, uploads)."""


def _tool_text(result) -> str:
    """CallToolResult -> plain text, across fastmcp result shapes."""
    if getattr(result, "data", None) is not None:
        return str(result.data)
    return "\n".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )


def _one_line(text: str, limit: int = 110) -> str:
    return text.replace("\n", " | ")[:limit]


# ---------------------------------------------------------------- fixtures


def build_text_pdf(text: str, pages: int) -> bytes:
    from reportlab.pdfgen.canvas import Canvas

    buffer = io.BytesIO()
    canvas = Canvas(buffer)
    for page_no in range(pages):
        canvas.setFont("Helvetica", 24)
        canvas.drawString(72, 720, f"{text} [p{page_no + 1}]")
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def build_scanned_pdf(text: str) -> bytes:
    """Image-only PDF: no text layer, so pdf_ocr has real work to do."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 600), "white")
    draw = ImageDraw.Draw(image)
    font = None
    for candidate in _FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(candidate, 64)
            break
        except OSError:
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=48)
        except TypeError:
            font = ImageFont.load_default()
    draw.text((60, 240), text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, "PDF", resolution=100)
    return buffer.getvalue()


# ---------------------------------------------------------------- reporting


class Report:
    def __init__(self) -> None:
        self.counter = 0
        self.failures: list[tuple[str, str]] = []

    def step(self) -> int:
        self.counter += 1
        return self.counter

    def ok(self, name: str, detail: str) -> None:
        print(f"[{self.counter:02d}] {name:<34} OK   {detail}")

    def fail(self, name: str, error: object) -> None:
        print(f"[{self.counter:02d}] {name:<34} FAIL {error}")
        self.failures.append((name, str(error)))

    def finish(self) -> int:
        if self.failures:
            print("\nFAILED STEPS:")
            for name, error in self.failures:
                print(f"  - {name}: {error}")
            print("\nHint: is the server running (uvicorn app.main:app) and, "
                  "if PDFCABIN_TOKEN is set, was --token passed?")
            print("\nE2E FAIL")
            return 1
        print("\nE2E PASS")
        return 0


# ---------------------------------------------------------------- steps


async def _upload(rest: httpx.AsyncClient, name: str, data: bytes) -> None:
    response = await rest.post(
        "/api/upload", files={"files": (name, data, "application/pdf")}
    )
    if response.status_code != 200:
        raise Critical(f"upload {name}: HTTP {response.status_code} {response.text[:200]}")
    saved = response.json()["saved"][0]["path"]
    if saved != name:
        raise Critical(f"upload {name}: server saved it as '{saved}'")


async def _mcp_steps(args, base_url: str, headers: dict, created: list, report: Report) -> None:
    from fastmcp import Client

    if headers:
        from fastmcp.client.transports import StreamableHttpTransport

        transport = StreamableHttpTransport(url=f"{base_url}/mcp", headers=headers)
    else:
        transport = f"{base_url}/mcp"

    async def _run_steps(mcp) -> None:
        # list_documents ---------------------------------------------------
        name = "mcp: list_documents"
        report.step()
        try:
            listing = _tool_text(await mcp.call_tool("list_documents", {}))
            for expected in ("e2e_alpha.pdf", "e2e_beta.pdf"):
                if expected not in listing:
                    raise AssertionError(f"'{expected}' missing from listing")
            report.ok(name, _one_line(listing))
        except Exception as exc:
            report.fail(name, exc)

        # pdf_info -----------------------------------------------------------
        name = "mcp: pdf_info(e2e_alpha.pdf)"
        report.step()
        try:
            info = _tool_text(await mcp.call_tool("pdf_info", {"path": "e2e_alpha.pdf"}))
            if "pages: 2" not in info:
                raise AssertionError(f"expected 'pages: 2' in: {_one_line(info)}")
            report.ok(name, _one_line(info))
        except Exception as exc:
            report.fail(name, exc)

        # pdf_merge ----------------------------------------------------------
        name = "mcp: pdf_merge(alpha+beta)"
        report.step()
        try:
            merged = _tool_text(
                await mcp.call_tool(
                    "pdf_merge",
                    {"paths": ["e2e_alpha.pdf", "e2e_beta.pdf"], "output": "e2e_merged.pdf"},
                )
            )
            if "Created e2e_merged.pdf (3 pages)" not in merged:
                raise AssertionError(f"unexpected answer: {_one_line(merged)}")
            created.append("e2e_merged.pdf")
            report.ok(name, _one_line(merged))
        except Exception as exc:
            report.fail(name, exc)

        # pdf_split ----------------------------------------------------------
        name = "mcp: pdf_split(every_n=2)"
        report.step()
        try:
            split = _tool_text(
                await mcp.call_tool(
                    "pdf_split", {"path": "e2e_merged.pdf", "mode": "every_n", "value": "2"}
                )
            )
            outputs = [
                line.strip() for line in split.splitlines()
                if line.strip() and line.strip() != "Created:"
            ]
            expected = ["e2e_merged_p01-02.pdf", "e2e_merged_p03.pdf"]
            if outputs != expected:
                raise AssertionError(f"expected {expected}, got {outputs}")
            created.extend(outputs)
            report.ok(name, _one_line(split))
        except Exception as exc:
            report.fail(name, exc)

        # pdf_compress -------------------------------------------------------
        name = "mcp: pdf_compress(fast)"
        report.step()
        try:
            compressed = _tool_text(
                await mcp.call_tool(
                    "pdf_compress",
                    {"path": "e2e_merged.pdf", "output": "e2e_merged_small.pdf", "level": "fast"},
                )
            )
            if "Created e2e_merged_small.pdf" not in compressed:
                raise AssertionError(f"unexpected answer: {_one_line(compressed)}")
            created.append("e2e_merged_small.pdf")
            report.ok(name, _one_line(compressed))
        except Exception as exc:
            report.fail(name, exc)

        # extract_text -------------------------------------------------------
        name = "mcp: extract_text(alpha)"
        report.step()
        try:
            text = _tool_text(await mcp.call_tool("extract_text", {"path": "e2e_alpha.pdf"}))
            if _SEARCH_WORD not in text:
                raise AssertionError(f"'{_SEARCH_WORD}' not in extracted text")
            report.ok(name, _one_line(text))
        except Exception as exc:
            report.fail(name, exc)

        # search_documents ---------------------------------------------------
        name = "mcp: search_documents"
        report.step()
        try:
            found = _tool_text(await mcp.call_tool("search_documents", {"query": _SEARCH_WORD}))
            if "No matches" in found:
                # Honest answer: only OCR'd files are indexed, so an empty hit
                # list on a fresh library is correct tool behaviour, not a bug.
                report.ok(name, "no hits (library not indexed yet - expected without OCR)")
            else:
                report.ok(name, _one_line(found))
        except Exception as exc:
            report.fail(name, exc)

        # create_document -> save_document -> delete_document -----------------
        temp_dir = tempfile.mkdtemp(prefix="pdfcabin-e2e-")
        try:
            name = "mcp: create_document(text->pdf)"
            report.step()
            try:
                answer = _tool_text(
                    await mcp.call_tool(
                        "create_document",
                        {"text": f"PDFCabin e2e created document with {_SEARCH_WORD}",
                         "name": "e2e_created.pdf", "overwrite": True},
                    )
                )
                if "Created e2e_created.pdf" not in answer:
                    raise AssertionError(f"unexpected answer: {_one_line(answer)}")
                report.ok(name, _one_line(answer))
            except Exception as exc:
                report.fail(name, exc)

            name = "mcp: save_document(to os path)"
            report.step()
            try:
                save_target = os.path.join(temp_dir, "e2e_saved.pdf")
                saved = _tool_text(
                    await mcp.call_tool(
                        "save_document",
                        {"path": "e2e_created.pdf", "target_path": save_target},
                    )
                )
                with open(save_target, "rb") as fh:
                    if fh.read(5) != b"%PDF-":
                        raise AssertionError("saved file is not a PDF")
                report.ok(name, _one_line(saved))
            except Exception as exc:
                report.fail(name, exc)

            name = "mcp: delete_document(to trash)"
            report.step()
            try:
                trashed = _tool_text(
                    await mcp.call_tool("delete_document", {"path": "e2e_created.pdf"})
                )
                if not trashed.startswith("trash/e2e_created.pdf"):
                    raise AssertionError(f"unexpected answer: {_one_line(trashed)}")
                report.ok(name, _one_line(trashed))
            except Exception as exc:
                report.fail(name, exc)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # pdf_ocr + indexed search (optional) --------------------------------
        if args.with_ocr:
            name = "mcp: pdf_ocr(e2e_scan.pdf, rus+eng)"
            report.step()
            try:
                ocr = _tool_text(
                    await mcp.call_tool(
                        "pdf_ocr", {"path": "e2e_scan.pdf", "languages": "rus+eng"}, timeout=600
                    )
                )
                if "OCR complete" not in ocr:
                    raise AssertionError(f"unexpected answer: {_one_line(ocr)}")
                created.append("e2e_scan_ocr.pdf")
                report.ok(name, _one_line(ocr))
            except Exception as exc:
                report.fail(name, exc)

            name = "mcp: search finds OCR'd scan"
            report.step()
            try:
                found = _tool_text(await mcp.call_tool("search_documents", {"query": _SEARCH_WORD}))
                if "e2e_scan_ocr.pdf" not in found:
                    raise AssertionError(f"scan not searchable after OCR: {_one_line(found)}")
                report.ok(name, _one_line(found))
            except Exception as exc:
                report.fail(name, exc)

    # A broken /mcp mount (or wrong token) surfaces here, not as a traceback.
    try:
        async with Client(transport, timeout=60) as mcp:
            await _run_steps(mcp)
    except Exception as exc:
        report.step()
        report.fail("mcp: connect to /mcp", exc)


async def _cleanup(rest: httpx.AsyncClient, created: list, report: Report) -> None:
    name = "cleanup: DELETE /api/file -> trash"
    report.step()
    if not created:
        report.ok(name, "nothing to clean up")
        return
    problems = []
    for rel in created:
        try:
            response = await rest.delete("/api/file", params={"path": rel})
            if response.status_code != 200:
                problems.append(f"{rel} -> HTTP {response.status_code}")
        except Exception as exc:
            problems.append(f"{rel} -> {exc}")
    if problems:
        report.fail(name, "; ".join(problems))
    else:
        report.ok(name, f"{len(created)} file(s) moved to docs trash")


async def e2e(args) -> Report:
    report = Report()
    base_url = args.base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    created: list[str] = []
    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=60) as rest:
        try:
            # health -----------------------------------------------------------
            name = "rest: GET /api/health"
            report.step()
            try:
                response = await rest.get("/api/health")
                if response.status_code != 200:
                    raise AssertionError(f"HTTP {response.status_code}")
                body = response.json()
                if body.get("status") != "ok":
                    raise AssertionError(f"unexpected body: {body}")
                report.ok(
                    name,
                    f"version={body.get('version')} langs={','.join(body.get('langs', []))} "
                    f"ghostscript={body.get('ghostscript')}",
                )
            except Exception as exc:
                report.fail(name, exc)
                raise Critical(f"/api/health did not answer: {exc}") from exc

            # uploads ------------------------------------------------------------
            name = "rest: upload alpha+beta(+scan)"
            report.step()
            try:
                alpha_bytes = build_text_pdf(f"PDFCabin e2e alpha {_SEARCH_WORD}", 2)
                await _upload(rest, "e2e_alpha.pdf", alpha_bytes)
                await _upload(rest, "e2e_beta.pdf", build_text_pdf("PDFCabin e2e beta", 1))
                created.extend(["e2e_alpha.pdf", "e2e_beta.pdf"])
                detail = "e2e_alpha.pdf (2 pages), e2e_beta.pdf (1 page)"
                if args.with_ocr:
                    scan_bytes = build_scanned_pdf(f"PDFCabin e2e scan {_SEARCH_WORD}")
                    await _upload(rest, "e2e_scan.pdf", scan_bytes)
                    created.append("e2e_scan.pdf")
                    detail += ", e2e_scan.pdf (image-only)"
                report.ok(name, detail)
            except Exception as exc:
                report.fail(name, exc)
                raise Critical(f"upload step failed: {exc}") from exc

            await _mcp_steps(args, base_url, headers, created, report)
        except Critical:
            pass  # already reported; remaining steps would only cascade
        finally:
            await _cleanup(rest, created, report)
    return report


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="E2E check of a running PDFCabin server (REST + MCP over HTTP)."
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8420", help="server root (default %(default)s)"
    )
    parser.add_argument(
        "--token", default="", help="bearer token, if the server runs with PDFCABIN_TOKEN"
    )
    parser.add_argument(
        "--with-ocr", action="store_true", help="also run pdf_ocr (slow; needs tesseract on PATH)"
    )
    args = parser.parse_args()

    print("== PDFCabin E2E ==")
    print(f"base-url: {args.base_url}  ocr: {'on' if args.with_ocr else 'off'}\n")

    report = await e2e(args)
    return report.finish()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
