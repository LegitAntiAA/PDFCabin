"""ASGI entrypoint: REST + MCP (streamable HTTP) + static UI on one port."""

from __future__ import annotations

import secrets
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import APP_VERSION, config
from .api import router
from .mcp_server import mcp

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _mcp_asgi_app():
    """The streamable-HTTP ASGI app; name changed across fastmcp versions."""
    if hasattr(mcp, "streamable_http_app"):
        return mcp.streamable_http_app()
    return mcp.http_app(transport="streamable-http")


# One shared instance: the endpoint registered below and the lifespan must be
# the same app object, otherwise the session manager started in the lifespan
# is not the one serving requests (fastmcp creates a fresh manager per call).
mcp_asgi_app = _mcp_asgi_app()

# The MCP session manager is created and started inside the inner app's own
# lifespan. Production starts it via the FastAPI lifespan below; plain ASGI
# transports (e.g. httpx.ASGITransport in tests) never deliver lifespan
# events, so the first authenticated request starts it lazily instead. Both
# paths share this one idempotent entry point. The stack is published before
# it is awaited, so a concurrent first request sees "started" and skips
# rather than double-running the manager.
_mcp_lifespan_stack: AsyncExitStack | None = None


async def _ensure_mcp_started() -> None:
    """Enter the MCP app's lifespan exactly once per process."""
    global _mcp_lifespan_stack
    if _mcp_lifespan_stack is not None:
        return
    stack = AsyncExitStack()
    _mcp_lifespan_stack = stack
    factory = (
        getattr(mcp_asgi_app, "lifespan", None) or mcp_asgi_app.router.lifespan_context
    )
    try:
        await stack.enter_async_context(factory(mcp_asgi_app))
    except BaseException:
        _mcp_lifespan_stack = None
        raise


class BearerTokenMiddleware:
    """Protects the mounted MCP app when PDFCABIN_TOKEN is set.

    A small ASGI wrapper is the version-proof way to guard a mounted app
    (fastmcp auth classes target OAuth flows we do not want here).
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.asgi_app(scope, receive, send)
            return
        await _ensure_mcp_started()
        if not config.settings.token:
            await self.asgi_app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        auth = headers.get("authorization", "")
        provided = auth[7:] if auth.startswith("Bearer ") else None
        if provided is None or not secrets.compare_digest(provided, config.settings.token):
            body = b'{"detail":"Unauthorized: set the Authorization: Bearer <token> header"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await _ensure_mcp_started()
        await self.asgi_app(scope, receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # FastAPI does not run the lifespan of mounted sub-apps; without this the
    # MCP session manager never starts and first calls 500 (python-sdk#1367).
    global _mcp_lifespan_stack
    await _ensure_mcp_started()
    try:
        yield
    finally:
        stack, _mcp_lifespan_stack = _mcp_lifespan_stack, None
        if stack is not None:
            await stack.aclose()


app = FastAPI(
    title="PDFCabin",
    version=APP_VERSION,
    lifespan=lifespan,
    # Swagger UI loads its assets from a CDN — that would break the
    # zero-outbound-requests promise; the raw OpenAPI schema stays available.
    docs_url=None,
    redoc_url=None,
)

# Allow the UI when it is opened straight from the filesystem (origin "null").
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# Service exceptions -> the error contract in spec 6.6.
@app.exception_handler(ValueError)
async def _on_bad_input(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FileNotFoundError)
async def _on_missing_file(_, exc: FileNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FileExistsError)
async def _on_existing_output(_, exc: FileExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

app.include_router(router)
# A plain app.mount("/mcp", ...) is unreachable at its exact URL on
# starlette 1.x: Mount compiles "/mcp" to "^/mcp/(?P<path>.*)$", which does
# not match the bare "/mcp", so requests fell through to the static "/"
# mount (404 on GET, 405 on POST) and never reached the MCP middleware.
# Register the bare path explicitly instead; the inner fastmcp app keeps its
# endpoint at "/mcp", which the untouched scope path still satisfies.
app.add_route(
    "/mcp",
    BearerTokenMiddleware(mcp_asgi_app),
    methods=["GET", "POST", "DELETE"],
)

if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.settings.host, port=config.settings.port)
