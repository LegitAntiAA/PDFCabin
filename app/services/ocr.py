"""OCR service: ocrmypdf (tesseract) wrapper + indexing of the result."""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from pathlib import Path

import ocrmypdf
from ocrmypdf.exceptions import MissingDependencyError, PriorOcrFoundError

from .. import config
from . import index
from .pdf_ops import assert_is_pdf


class PriorTextError(ValueError):
    """The PDF already has a text layer; rerun with force=True."""


# Windows installers (UB-Mannheim tesseract, Ghostscript) are not always on the
# PATH of the running process; prepend their standard locations when present.
_KNOWN_TOOL_GLOBS = (
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files\gs\gs*\bin",
)

_LANG_RE = re.compile(r"^([a-z0-9_]+)\s*$", re.MULTILINE)

_installed_langs: list[str] | None = None


def _ensure_tool_dirs() -> None:
    parts = os.environ.get("PATH", "").split(os.pathsep)
    for pattern in _KNOWN_TOOL_GLOBS:
        for directory in glob.glob(pattern):
            if os.path.isdir(directory) and directory not in parts:
                parts.insert(0, directory)
    os.environ["PATH"] = os.pathsep.join(parts)


def installed_langs() -> list[str]:
    """Languages reported by `tesseract --list-langs` (cached after the first call)."""
    global _installed_langs
    if _installed_langs is None:
        _ensure_tool_dirs()
        tesseract = shutil.which("tesseract")
        if not tesseract:
            raise ValueError("tesseract is not installed or not on PATH; OCR is unavailable")
        result = subprocess.run(
            [tesseract, "--list-langs"], capture_output=True, text=True, timeout=60
        )
        langs = sorted(
            set(_LANG_RE.findall(result.stdout or ""))
            | set(_LANG_RE.findall(result.stderr or ""))
        )
        _installed_langs = langs
    return _installed_langs


def default_langs() -> list[str]:
    """Configured languages (PDFCABIN_LANGS) intersected with what tesseract has."""
    available = set(installed_langs())
    configured = [lang for lang in config.settings.lang_list if lang in available]
    if not configured:
        raise ValueError(
            f"none of the configured OCR languages ({config.settings.langs}) are installed; "
            f"available: {', '.join(sorted(available)) or 'unknown'}"
        )
    return configured


def parse_langs(spec: str | list[str] | None) -> list[str]:
    """Accept "rus+eng", ["rus", "eng"] or None (-> configured default); validate availability."""
    if spec is None:
        return default_langs()
    if isinstance(spec, str):
        raw = spec.replace(",", "+").split("+")
    else:
        raw = [str(item) for item in spec]
    langs = [item.strip() for item in raw if item.strip()]
    if not langs:
        return default_langs()
    available = set(installed_langs())
    missing = [lang for lang in langs if lang not in available]
    if missing:
        raise ValueError(
            f"tesseract language(s) not installed: {', '.join(missing)}; "
            f"available: {', '.join(sorted(available))}"
        )
    return langs


def run_ocr(input_path: Path, output_path: Path, languages: list[str], force: bool = False) -> Path:
    """Run ocrmypdf; raises PriorTextError when a text layer already exists."""
    assert_is_pdf(input_path)
    _ensure_tool_dirs()
    kwargs: dict = {
        "languages": languages,
        "output_type": "pdf",  # searchable PDF without the PDF/A ghostscript pass
        "optimize": 1,
        "jobs": 2,
        "progress_bar": False,
    }
    if force:
        kwargs["redo_ocr"] = True
    try:
        ocrmypdf.ocr(str(input_path), str(output_path), **kwargs)
    except PriorOcrFoundError as exc:
        raise PriorTextError("file already has a text layer; rerun with force=true") from exc
    except MissingDependencyError as exc:
        raise ValueError(f"OCR dependency missing: {exc}") from exc
    return output_path


def ocr_and_index(input_path: Path, output_path: Path, languages: list[str], force: bool) -> int:
    """Full OCR pipeline used by the job queue: OCR then (re)index the output."""
    run_ocr(input_path, output_path, languages, force=force)
    return index.index_pdf(output_path)
