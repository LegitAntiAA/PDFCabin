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
    # Donation addresses: the project author's wallets are baked in as defaults
    # (owner's decision — every install, local or Docker, shows the donate heart
    # out of the box). Any PDFCABIN_DONATE_* env var overrides the corresponding
    # default, which keeps the "a fork collects donations for its own build"
    # pattern working without touching the code.
    donate_btc: str = "183Ux9K4eNC8qxgULSN5eFcnvEiJGdzTBX"
    donate_eth: str = "0xb8ec96ef15f6dc79f854c277c71acf6dc581f1ee"
    donate_ton: str = ""
    donate_usdt_bep20: str = "0x34aa51a6352c18cc5aacb4ef70ee8f5d968d1c4a"
    donate_usdt_trc20: str = "TB8PSJu9SKncq2x7bsrqDS1sJTLWqoXCZA"

    @property
    def lang_list(self) -> list[str]:
        return [item.strip() for item in self.langs.split(",") if item.strip()]

    @property
    def donate_addresses(self) -> list[dict[str, str]]:
        addresses = []
        for network, address in (
            ("BTC", self.donate_btc),
            ("ETH (ERC-20)", self.donate_eth),
            ("TON", self.donate_ton),
            ("USDT (BEP-20)", self.donate_usdt_bep20),
            ("USDT (TRC-20)", self.donate_usdt_trc20),
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
