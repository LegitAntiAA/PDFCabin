"""Configuration (PDFCABIN_* env vars) and the docs-directory path guard.

`resolve_in_docs` is the single choke point for every user-supplied path:
REST and MCP both go through it, so path traversal fails in one place.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDFCABIN_")

    docs_dir: Path = Path("./docs")
    token: str = ""
    host: str = "127.0.0.1"
    port: int = 8420
    langs: str = "rus,eng"
    max_upload_mb: int = 200
    donate_btc: str = ""
    donate_ton: str = ""
    donate_usdt: str = ""

    @property
    def lang_list(self) -> list[str]:
        return [item.strip() for item in self.langs.split(",") if item.strip()]

    @property
    def donate_addresses(self) -> list[dict[str, str]]:
        addresses = []
        for network, address in (
            ("BTC", self.donate_btc),
            ("TON", self.donate_ton),
            ("USDT TRC-20", self.donate_usdt),
        ):
            if address.strip():
                addresses.append({"network": network, "address": address.strip()})
        return addresses


settings = Settings()


def docs_dir() -> Path:
    """Resolved docs directory, created on demand.

    Read at call time (not import time) so tests can retarget it via monkeypatch.
    """
    path = Path(settings.docs_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_in_docs(rel: str) -> Path:
    """Resolve a library-relative path inside docs_dir.

    Raises ValueError on empty paths and traversal attempts.
    """
    if not rel or not rel.strip():
        raise ValueError("path is required")
    base = docs_dir()
    rel = rel.strip().replace("\\", "/").lstrip("/")
    candidate = (base / rel).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("path escapes the documents directory")
    return candidate


def rel_from_docs(path: Path) -> str:
    """docs_dir-relative POSIX path, used in API responses and the search index."""
    return path.resolve().relative_to(docs_dir()).as_posix()
