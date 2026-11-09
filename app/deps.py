"""HTTP-layer dependencies: token auth and the safe-path wrapper."""

import secrets

from fastapi import HTTPException, Request

from . import config


async def require_token(request: Request) -> None:
    """FastAPI dependency: enforce Bearer auth when PDFCABIN_TOKEN is set."""
    expected = config.settings.token
    if not expected:
        return
    auth = request.headers.get("Authorization", "")
    provided = auth[7:] if auth.startswith("Bearer ") else None
    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: set the Authorization: Bearer <token> header",
            headers={"WWW-Authenticate": "Bearer"},
        )


def safe_path(rel: str):
    """config.resolve_in_docs, mapped to the HTTP error contract."""
    try:
        return config.resolve_in_docs(rel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
