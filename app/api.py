"""REST API — a thin HTTP facade over app.services.

The MCP tools call the same service functions; there is no duplicated logic.
Error contract (spec 6.6): {"detail": "..."} with 400/401/404/409.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pypdfium2 as pdfium
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from . import APP_VERSION, config, deps
from .services import index, jobs, ocr, pdf_ops

router = APIRouter(prefix="/api", dependencies=[Depends(deps.require_token)])

_BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
_THUMB_WIDTH = 240


# ---------------------------------------------------------------- helpers


def _existing(rel: str):
    path = deps.safe_path(rel)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return path


def _sanitize_name(name: str) -> str:
    """Keep unicode letters, drop path separators and control characters."""
    name = os.path.basename(name.replace("\\", "/")).strip()
    name = _BAD_NAME.sub("_", name).strip().lstrip(".")
    if not name:
        name = "document.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    chunks = []
    total = 0
    while chunk := await upload.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=400,
                detail=f"file exceeds the {config.settings.max_upload_mb} MB upload limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _first_page_has_text(path) -> bool:
    try:
        return bool(next(iter(pdf_ops.extract_text(path, "1").values()), "").strip())
    except (ValueError, FileNotFoundError):
        return False


# ---------------------------------------------------------------- meta


@router.get("/health")
def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "langs": config.settings.lang_list,
        "docs_dir": str(config.docs_dir()),
        "ghostscript": pdf_ops.gs_command() is not None,
    }


@router.get("/donate")
def donate():
    return {"addresses": config.settings.donate_addresses}


@router.get("/stats")
def stats():
    return index.stats()


# ---------------------------------------------------------------- files


@router.get("/files")
def list_files(subdir: str = ""):
    base = deps.safe_path(subdir) if subdir else config.docs_dir()
    if not base.is_dir():
        raise HTTPException(status_code=404, detail="no such directory")
    items = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "trash" and not d.startswith(".")]
        for name in filenames:
            if not name.lower().endswith(".pdf"):
                continue
            path = Path(dirpath) / name
            rel = config.rel_from_docs(path)
            try:
                pages: int | None = pdf_ops.page_count(path)
            except ValueError:
                pages = None
            items.append(
                {
                    "name": name,
                    "path": rel,
                    "size": path.stat().st_size,
                    "mtime": path.stat().st_mtime,
                    "pages": pages,
                    "has_text": index.has_text(rel) or _first_page_has_text(path),
                }
            )
    items.sort(key=lambda item: item["path"])
    return items


@router.post("/upload")
async def upload(files: list[UploadFile] = File(...), overwrite: bool = False):
    limit = config.settings.max_upload_mb * 1024 * 1024
    saved = []
    for upload_file in files:
        data = await _read_limited(upload_file, limit)
        if data[:5] != pdf_ops.PDF_MAGIC:
            raise HTTPException(
                status_code=400, detail=f"'{upload_file.filename}' is not a PDF file"
            )
        name = _sanitize_name(upload_file.filename or "")
        target = config.docs_dir() / name
        if target.exists() and not overwrite:
            raise HTTPException(
                status_code=409, detail=f"'{name}' already exists (pass overwrite=true)"
            )
        target.write_bytes(data)
        saved.append({"path": name, "size": len(data)})
    return {"saved": saved}


@router.get("/file/info")
def file_info(path: str):
    return pdf_ops.pdf_info(_existing(path))


@router.get("/file/thumb")
def file_thumb(path: str, page: int = 1):
    target = _existing(path)
    try:
        doc = pdfium.PdfDocument(str(target))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"cannot open PDF: {exc}") from exc
    try:
        if page < 1 or page > len(doc):
            raise HTTPException(status_code=400, detail=f"page out of range (1..{len(doc)})")
        pdf_page = doc[page - 1]
        scale = _THUMB_WIDTH / max(pdf_page.get_width(), 1.0)
        image = pdf_page.render(scale=scale).to_pil()
    finally:
        doc.close()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.get("/download")
def download(path: str):
    target = _existing(path)
    return FileResponse(target, filename=target.name, media_type="application/pdf")


@router.delete("/file")
def delete_file(path: str):
    """Move a PDF into docs_dir/trash/ (UI "Delete") and drop it from the index."""
    target = _existing(path)
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
    return {"trash": config.rel_from_docs(destination)}


# ---------------------------------------------------------------- operations


class MergeReq(BaseModel):
    # count validation lives in pdf_ops.pdf_merge: ValueError -> 400 (spec 6.6),
    # so a 1-file merge is a 400 with a readable detail, not a bare 422.
    paths: list[str]
    output: str
    overwrite: bool = False


class SplitReq(BaseModel):
    path: str
    # mode validation lives in pdf_ops.pdf_split: ValueError -> 400 (spec 6.6),
    # consistent with merge/angle handling above.
    mode: str
    value: str
    output_dir: str | None = None
    overwrite: bool = False


class RotateReq(BaseModel):
    path: str
    pages: str
    # angle validation lives in pdf_ops.pdf_rotate: ValueError -> 400 (spec 6.6),
    # so angle=45 is a 400 with a readable detail, not a bare 422.
    angle: int
    output: str
    overwrite: bool = False


class DeletePagesReq(BaseModel):
    path: str
    pages: str
    output: str
    overwrite: bool = False


class CompressReq(BaseModel):
    path: str
    # level validation lives in pdf_ops.pdf_compress: ValueError -> 400 (spec 6.6).
    level: str
    output: str | None = None
    overwrite: bool = False


class ExtractReq(BaseModel):
    path: str
    pages: str | None = None


class OcrReq(BaseModel):
    path: str
    languages: list[str] | None = None
    force: bool = False


@router.post("/merge")
def merge(req: MergeReq):
    output = pdf_ops.pdf_merge(
        [deps.safe_path(p) for p in req.paths], deps.safe_path(req.output), req.overwrite
    )
    return {"output": config.rel_from_docs(output)}


@router.post("/split")
def split(req: SplitReq):
    outputs = pdf_ops.pdf_split(
        _existing(req.path),
        req.mode,
        req.value,
        deps.safe_path(req.output_dir) if req.output_dir else None,
        req.overwrite,
    )
    return {"outputs": [config.rel_from_docs(o) for o in outputs]}


@router.post("/rotate")
def rotate(req: RotateReq):
    output = pdf_ops.pdf_rotate(
        _existing(req.path), req.pages, req.angle, deps.safe_path(req.output), req.overwrite
    )
    return {"output": config.rel_from_docs(output)}


@router.post("/delete-pages")
def delete_pages(req: DeletePagesReq):
    output = pdf_ops.pdf_delete_pages(
        _existing(req.path), req.pages, deps.safe_path(req.output), req.overwrite
    )
    return {"output": config.rel_from_docs(output)}


@router.post("/compress")
def compress(req: CompressReq):
    source = _existing(req.path)
    output = deps.safe_path(req.output) if req.output else source.with_name(
        f"{source.stem}_compressed.pdf"
    )
    result = pdf_ops.pdf_compress(source, output, req.level, req.overwrite)
    return {
        "output": config.rel_from_docs(result["output"]),
        "size_before": result["size_before"],
        "size_after": result["size_after"],
    }


@router.post("/extract-text")
def extract_text(req: ExtractReq):
    texts = pdf_ops.extract_text(_existing(req.path), req.pages)
    return {"pages": texts}


@router.post("/ocr")
async def ocr_start(req: OcrReq):
    """Queue OCR; returns 202 + job_id (poll /api/jobs/{id})."""
    source = _existing(req.path)
    languages = ocr.parse_langs(req.languages)
    output = source.with_name(f"{source.stem}_ocr.pdf")
    job_id = await jobs.submit_ocr(source, output, languages, req.force)
    return JSONResponse(status_code=202, content={"job_id": job_id})


# ---------------------------------------------------------------- jobs & search


@router.get("/jobs")
def jobs_list():
    return jobs.list_jobs()


@router.get("/jobs/{job_id}")
def job_get(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="no such job")
    return job


@router.get("/search")
def search(q: str = Query(...), limit: int = Query(20, ge=1, le=100)):
    return index.search(q, limit)
