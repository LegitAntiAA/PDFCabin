"""In-process background job queue.

OCR is CPU-bound, so a single worker slot (asyncio.Semaphore(1)) keeps the
queue honest: jobs run one at a time, first come first served. Jobs live in
memory and are dropped 24h after completion.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

from .. import config
from . import ocr

JOBS: dict[str, dict] = {}
_ocr_slot = asyncio.Semaphore(1)
_MAX_AGE_SECONDS = 24 * 3600


def _cleanup() -> None:
    now = time.time()
    for job_id, job in list(JOBS.items()):
        finished = job.get("finished_at")
        if finished and now - finished > _MAX_AGE_SECONDS:
            JOBS.pop(job_id, None)


def get(job_id: str) -> dict | None:
    return JOBS.get(job_id)


def list_jobs() -> list[dict]:
    active = [j for j in JOBS.values() if j["status"] in ("queued", "running")]
    finished = [j for j in JOBS.values() if j["status"] not in ("queued", "running")]
    newest = lambda j: j["created_at"]  # noqa: E731
    return sorted(active, key=newest, reverse=True) + sorted(finished, key=newest, reverse=True)


async def submit_ocr(
    input_path: Path, output_path: Path, languages: list[str], force: bool
) -> str:
    """Queue an OCR job and return its id immediately (REST returns 202)."""
    _cleanup()
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "id": job_id,
        "kind": "ocr",
        "params": {
            "path": config.rel_from_docs(input_path),
            "languages": languages,
            "force": force,
        },
        "status": "queued",
        "progress": 0,
        "created_at": time.time(),
        "finished_at": None,
        "result": None,
        "error": None,
    }
    asyncio.create_task(_run_ocr(job_id, input_path, output_path, languages, force))
    return job_id


async def _run_ocr(
    job_id: str, input_path: Path, output_path: Path, languages: list[str], force: bool
) -> None:
    job = JOBS[job_id]
    async with _ocr_slot:
        job["status"] = "running"
        try:
            pages = await asyncio.to_thread(
                ocr.ocr_and_index, input_path, output_path, languages, force
            )
            job["status"] = "done"
            job["progress"] = 100
            job["result"] = {
                "output": config.rel_from_docs(output_path),
                "pages_indexed": pages,
            }
        except Exception as exc:  # job failures are reported to the client, never raised
            job["status"] = "error"
            job["error"] = str(exc) or exc.__class__.__name__
        finally:
            job["finished_at"] = time.time()


async def wait_job(job_id: str, timeout: float = 3600.0) -> dict:
    """Block until the job settles — used by the synchronous MCP pdf_ocr tool."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = JOBS.get(job_id)
        if job is None:
            raise ValueError(f"unknown job: {job_id}")
        if job["status"] in ("done", "error"):
            return job
        await asyncio.sleep(0.4)
    raise TimeoutError(f"job {job_id} did not finish within {int(timeout)}s")
