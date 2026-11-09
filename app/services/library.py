"""Document-library operations shared by REST and MCP (no duplicated logic).

Saving/creating/renaming/trash lives here; the HTTP layer and the MCP tools
are thin facades over these functions (spec 6.6/6.7). Errors use the service
contract: ValueError for bad input, FileNotFoundError for missing files,
FileExistsError for collisions (overwrite only with overwrite=true).
"""

from __future__ import annotations

import functools
import glob
import os
import re
import shutil
from pathlib import Path

from .. import config
from . import index, pdf_ops

_BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')

# A TTF with Cyrillic coverage for generated PDFs. DejaVuSans.ttf is not
# committed to the repo; fall back to a system font, then to latin-only
# Helvetica.
_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\DejaVuSans.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/**/DejaVuSans.ttf",
)

_APP_FONT_NAME = "AppFont"
_APP_FONT_REGISTERED = False
_LINES_PER_PAGE = 45
_BODY_SIZE = 11
_LEADING = 15
_MARGIN = 72


@functools.lru_cache(maxsize=1)
def find_unicode_font() -> str | None:
    """First available unicode-capable TTF on this system, or None."""
    for candidate in _FONT_CANDIDATES:
        matches = glob.glob(candidate, recursive=True)
        if matches:
            return matches[0]
    return None


def sanitize_name(name: str) -> str:
    """Keep unicode letters, drop path separators and control characters."""
    name = os.path.basename(name.replace("\\", "/")).strip()
    name = _BAD_NAME.sub("_", name).strip().lstrip(".")
    if not name:
        name = "document.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def upload_limit_bytes() -> int:
    return config.settings.max_upload_mb * 1024 * 1024


# ---------------------------------------------------------------- create


def _ensure_app_font() -> str:
    """Register the unicode font once; fall back to latin-only Helvetica."""
    global _APP_FONT_REGISTERED
    font_file = find_unicode_font()
    if not font_file:
        return "Helvetica"
    if not _APP_FONT_REGISTERED:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        try:
            pdfmetrics.registerFont(TTFont(_APP_FONT_NAME, font_file))
        except Exception:  # unreadable/corrupt font file -> Helvetica
            return "Helvetica"
        _APP_FONT_REGISTERED = True
    return _APP_FONT_NAME


def _wrap_line(line: str, font_name: str, max_width: float) -> list[str]:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    if not line.strip():
        return [""]
    wrapped: list[str] = []
    current = ""
    for word in line.split():
        candidate = f"{current} {word}" if current else word
        if stringWidth(candidate, font_name, _BODY_SIZE) <= max_width:
            current = candidate
            continue
        if current:
            wrapped.append(current)
        if stringWidth(word, font_name, _BODY_SIZE) <= max_width:
            current = word
        else:  # one unbreakable long token — hard-split by characters
            current = ""
            for char in word:
                if stringWidth(current + char, font_name, _BODY_SIZE) <= max_width:
                    current += char
                else:
                    wrapped.append(current)
                    current = char
    if current:
        wrapped.append(current)
    return wrapped


def create_pdf_from_text(text: str, target: Path) -> int:
    """Render plain text as a paginated A4 PDF (72pt margins); returns pages."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    font_name = _ensure_app_font()
    lines: list[str] = []
    for raw in (text or "").replace("\t", "    ").splitlines():
        lines.extend(_wrap_line(raw, font_name, A4[0] - 2 * _MARGIN))
    if not lines:
        lines = [""]

    canvas = Canvas(str(target), pagesize=A4)
    pages = 0
    for start in range(0, len(lines), _LINES_PER_PAGE):
        canvas.setFont(font_name, _BODY_SIZE)
        y = A4[1] - _MARGIN - _BODY_SIZE
        for line_text in lines[start:start + _LINES_PER_PAGE]:
            canvas.drawString(_MARGIN, y, line_text)
            y -= _LEADING
        canvas.showPage()
        pages += 1
    canvas.save()
    return pages


# ---------------------------------------------------------------- save / move


def save_pdf(data: bytes, name: str, overwrite: bool = False) -> tuple[Path, str]:
    """Validate and store PDF bytes under a sanitized docs-relative name.

    Returns (absolute path, library-relative name). Raises ValueError/NotPdfError
    for bad input or size, FileExistsError for an existing name.
    """
    if len(data) > upload_limit_bytes():
        raise ValueError(
            f"file exceeds the {config.settings.max_upload_mb} MB upload limit"
        )
    if data[:5] != pdf_ops.PDF_MAGIC:
        raise pdf_ops.NotPdfError(f"'{name}' is not a PDF file")
    clean = sanitize_name(name)
    target = config.docs_dir() / clean
    if target.exists() and not overwrite:
        raise FileExistsError(f"'{clean}' already exists (pass overwrite=true)")
    target.write_bytes(data)
    return target, clean


def import_from_os_path(
    source_path: str | os.PathLike, name: str | None = None, overwrite: bool = False
) -> tuple[Path, str]:
    """Copy a local PDF (OS path on the server's machine) into the library.

    name defaults to the sanitized source file name. Raises FileNotFoundError
    for a missing source, NotPdfError for a non-PDF, ValueError when the source
    already is the target library file, FileExistsError for a name collision.
    """
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"source file not found: {source}")
    if source.stat().st_size > upload_limit_bytes():
        raise ValueError(
            f"file exceeds the {config.settings.max_upload_mb} MB upload limit"
        )
    with open(source, "rb") as fh:
        if fh.read(5) != pdf_ops.PDF_MAGIC:
            raise pdf_ops.NotPdfError(f"'{source.name}' is not a PDF file")
    clean = sanitize_name(name) if name else sanitize_name(source.name)
    target = config.docs_dir() / clean
    if source.resolve() == target.resolve():
        raise ValueError(
            f"'{clean}' is already in the library - pick a different name for it"
        )
    if target.exists() and not overwrite:
        raise FileExistsError(f"'{clean}' already exists (pass overwrite=true)")
    shutil.copyfile(source, target)
    return target, clean


def export_to_os_path(
    path: str, target_path: str | os.PathLike, overwrite: bool = False
) -> Path:
    """Copy a library PDF to an arbitrary OS path (parents created on demand)."""
    source = config.resolve_in_docs(path)
    if not source.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    destination = Path(target_path).expanduser()
    if destination.resolve() == source.resolve():
        raise ValueError("target_path points at the library file itself")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"'{destination}' already exists (pass overwrite=true)")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def move_to_trash(path: str) -> str:
    """Move a library PDF into docs_dir/trash/ and drop it from the index.

    Returns the trash-relative path (e.g. "trash/old.pdf" or
    "trash/sub_1/old.pdf" on collision with a trashed namesake).
    """
    target = config.resolve_in_docs(path)
    if not target.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    rel = config.rel_from_docs(target)
    trash = config.docs_dir() / "trash"
    destination = trash / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    counter = 1
    while destination.exists():
        destination = trash / f"{target.stem}_{counter}{target.suffix}"
        counter += 1
    target.rename(destination)
    index.remove_from_index(rel)
    return config.rel_from_docs(destination)


def rename_document(path: str, new_name: str, overwrite: bool = False) -> Path:
    """Rename a library PDF in place and update the search index.

    new_name is sanitized (no separators — the file stays in its folder).
    Returns the new absolute path.
    """
    target = config.resolve_in_docs(path)
    if not target.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    clean = sanitize_name(new_name)
    destination = target.with_name(clean)
    if destination == target:  # sanitize mapped the name onto itself
        return target
    if destination.exists() and not overwrite:
        raise FileExistsError(f"'{clean}' already exists (pass overwrite=true)")
    old_rel = config.rel_from_docs(target)
    if overwrite and destination.exists():
        destination.unlink()  # Path.rename refuses to replace on Windows
    target.rename(destination)
    index.rename_in_index(old_rel, config.rel_from_docs(destination))
    return destination
