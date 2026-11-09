"""Pure PDF operations built on pikepdf / ghostscript / pypdfium2.

Every function takes absolute paths (already resolved by the API/MCP layer)
and raises ValueError for bad input, FileNotFoundError for missing files and
FileExistsError when an existing output would be overwritten.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium

PDF_MAGIC = b"%PDF-"
_PAGES_RE = re.compile(r"(\d+)(?:\s*-\s*(\d*)\s*)?$")

# PDFium is not thread-safe: concurrent FPDF_LoadPage calls crash with access
# violations under parallel thumbnail requests (BUG-005). Every pdfium call
# in the process must hold this lock.
PDFIUM_LOCK = threading.Lock()


class NotPdfError(ValueError):
    """The file does not start with the %PDF- magic."""


def assert_is_pdf(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    with open(path, "rb") as fh:
        if fh.read(5) != PDF_MAGIC:
            raise NotPdfError(f"'{path.name}' is not a PDF file")


def parse_pages(spec: str, total: int) -> list[int]:
    """Parse a 1-based page spec like ``1-3,5,8-`` into a sorted list.

    A trailing open range (``8-``) means "until the last page".
    """
    if spec is None or not spec.strip():
        raise ValueError("pages spec is empty")
    selected: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"empty page range in '{spec}'")
        match = _PAGES_RE.fullmatch(part)
        if not match:
            raise ValueError(f"bad page range: '{part}'")
        first = int(match.group(1))
        if first < 1:
            raise ValueError("pages are 1-based")
        if match.group(2):
            last = int(match.group(2))
        elif part.endswith("-"):
            last = total
        else:
            last = first
        if last < first:
            raise ValueError(f"descending range: '{part}'")
        if last > total:
            raise ValueError(f"page range '{part}' exceeds document ({total} pages)")
        selected.update(range(first, last + 1))
    return sorted(selected)


def _ensure_output_free(output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {output.name} (pass overwrite=true)")
    output.parent.mkdir(parents=True, exist_ok=True)


def _check_distinct(input_path: Path, output: Path) -> None:
    if output.resolve() == input_path.resolve():
        raise ValueError("output must differ from the input file")


def pdf_info(path: Path) -> dict:
    assert_is_pdf(path)
    try:
        with pikepdf.open(path) as pdf:
            info = {
                "pages": len(pdf.pages),
                "size_bytes": path.stat().st_size,
                "encrypted": bool(pdf.is_encrypted),
                "title": "",
                "author": "",
                "created": "",
            }
            try:
                docinfo = pdf.docinfo
                info["title"] = str(docinfo.get("/Title", "") or "")
                info["author"] = str(docinfo.get("/Author", "") or "")
                info["created"] = str(docinfo.get("/CreationDate", "") or "")
            except (KeyError, RuntimeError):
                pass
            return info
    except pikepdf.PasswordError as exc:
        raise ValueError("PDF is password-protected") from exc
    except pikepdf.PdfError as exc:
        raise ValueError(f"cannot open PDF: {exc}") from exc


def page_count(path: Path) -> int:
    assert_is_pdf(path)
    try:
        with pikepdf.open(path) as pdf:
            return len(pdf.pages)
    except pikepdf.PasswordError as exc:
        raise ValueError("PDF is password-protected") from exc
    except pikepdf.PdfError as exc:
        raise ValueError(f"cannot open PDF: {exc}") from exc


def pdf_merge(paths: list[Path], output: Path, overwrite: bool = False) -> Path:
    if len(paths) < 2:
        raise ValueError("merge needs at least two input files")
    for src_path in paths:
        assert_is_pdf(src_path)
    _ensure_output_free(output, overwrite)
    out = pikepdf.Pdf.new()
    sources = [pikepdf.open(src_path) for src_path in paths]
    try:
        for src in sources:
            out.pages.extend(src.pages)
        out.save(output)
    finally:
        for src in sources:
            src.close()
        out.close()
    return output


def _consecutive_groups(pages: list[int]) -> list[list[int]]:
    groups: list[list[int]] = []
    for page in pages:
        if groups and page == groups[-1][-1] + 1:
            groups[-1].append(page)
        else:
            groups.append([page])
    return groups


def pdf_split(
    path: Path,
    mode: str,
    value: str,
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> list[Path]:
    assert_is_pdf(path)
    out_dir = Path(output_dir) if output_dir else path.parent
    with pikepdf.open(path) as src:
        total = len(src.pages)
        if mode == "ranges":
            groups = _consecutive_groups(parse_pages(value, total))
        elif mode == "every_n":
            try:
                step = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"every_n expects an integer, got '{value}'") from exc
            if step < 1:
                raise ValueError("every_n must be >= 1")
            groups = [
                list(range(start, min(start + step, total + 1)))
                for start in range(1, total + 1, step)
            ]
        else:
            raise ValueError("mode must be 'ranges' or 'every_n'")
        targets = []
        for group in groups:
            if len(group) > 1:
                name = f"{path.stem}_p{group[0]:02d}-{group[-1]:02d}.pdf"
            else:
                name = f"{path.stem}_p{group[0]:02d}.pdf"
            targets.append((group, out_dir / name))
        for _, target in targets:  # check all before writing any
            _ensure_output_free(target, overwrite)
        outputs = []
        for group, target in targets:
            out = pikepdf.Pdf.new()
            for page_no in group:
                out.pages.append(src.pages[page_no - 1])
            out.save(target)
            out.close()
            outputs.append(target)
    return outputs


def pdf_rotate(path: Path, pages: str, angle: int, output: Path, overwrite: bool = False) -> Path:
    if angle not in (90, 180, 270):
        raise ValueError("angle must be one of 90, 180, 270")
    assert_is_pdf(path)
    _check_distinct(path, output)
    _ensure_output_free(output, overwrite)
    with pikepdf.open(path) as src:
        for page_no in parse_pages(pages, len(src.pages)):
            src.pages[page_no - 1].rotate(angle)
        src.save(output)
    return output


def pdf_delete_pages(path: Path, pages: str, output: Path, overwrite: bool = False) -> Path:
    assert_is_pdf(path)
    _check_distinct(path, output)
    _ensure_output_free(output, overwrite)
    with pikepdf.open(path) as src:
        total = len(src.pages)
        to_delete = set(parse_pages(pages, total))
        if len(to_delete) == total:
            raise ValueError("cannot delete all pages")
        out = pikepdf.Pdf.new()
        for page_no in range(1, total + 1):
            if page_no not in to_delete:
                out.pages.append(src.pages[page_no - 1])
        out.save(output)
        out.close()
    return output


def gs_command() -> str | None:
    """Name of a runnable ghostscript binary, or None when it is not installed."""
    for candidate in ("gs", "gswin64c", "gswin32c"):
        if shutil.which(candidate):
            return candidate
    return None


def pdf_compress(path: Path, output: Path, level: str, overwrite: bool = False) -> dict:
    assert_is_pdf(path)
    _check_distinct(path, output)
    _ensure_output_free(output, overwrite)
    size_before = path.stat().st_size
    if level == "fast":
        with pikepdf.open(path) as pdf:
            pdf.save(
                output,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                recompress_flate=True,
            )
    elif level == "strong":
        cmd = gs_command()
        if cmd is None:
            raise ValueError(
                "Ghostscript is not installed or not on PATH; it is required for "
                "level='strong' (level='fast' works without it)"
            )
        result = subprocess.run(
            [
                cmd, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.6",
                "-dPDFSETTINGS=/ebook", "-dDownsampleColorImages=true",
                "-dColorImageResolution=150", "-dNOPAUSE", "-dBATCH", "-dQUIET",
                f"-sOutputFile={output}", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0 or not output.exists():
            raise ValueError(f"ghostscript failed: {result.stderr.strip()[:400]}")
    else:
        raise ValueError("level must be 'fast' or 'strong'")
    return {"output": output, "size_before": size_before, "size_after": output.stat().st_size}


def extract_text(path: Path, pages: str | None = None) -> dict[int, str]:
    assert_is_pdf(path)
    with PDFIUM_LOCK:  # pdfium calls are serialized process-wide (see PDFIUM_LOCK)
        try:
            doc = pdfium.PdfDocument(str(path))
        except Exception as exc:
            raise ValueError(f"cannot open PDF: {exc}") from exc
        try:
            total = len(doc)
            wanted = parse_pages(pages, total) if pages else range(1, total + 1)
            result: dict[int, str] = {}
            for page_no in wanted:
                page = doc[page_no - 1]
                try:
                    text_page = page.get_textpage()
                    try:
                        result[page_no] = text_page.get_text_range().strip()
                    finally:
                        text_page.close()
                finally:
                    page.close()
            return result
        finally:
            doc.close()
