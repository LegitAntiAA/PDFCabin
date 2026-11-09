"""SQLite FTS5 full-text index over extracted/OCR'd PDF text.

The index lives in index.db inside the docs directory. The `pages` table
keeps one row per page (stats), `pages_fts` keeps the searchable text of
pages that actually have text. unicode61 handles Cyrillic out of the box;
search is by exact word forms (no stemming) — documented in the README.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .. import config
from .pdf_ops import extract_text

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS pages(
        id INTEGER PRIMARY KEY,
        path TEXT NOT NULL,
        page INTEGER NOT NULL,
        mtime REAL NOT NULL
    )""",
    """CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
        text, path UNINDEXED, page UNINDEXED,
        tokenize = 'unicode61'
    )""",
    "CREATE INDEX IF NOT EXISTS pages_path ON pages(path)",
)


def db_path() -> Path:
    return config.docs_dir() / "index.db"


@contextmanager
def _conn():
    connection = sqlite3.connect(db_path())
    try:
        for statement in _SCHEMA:
            connection.execute(statement)
        with connection:  # transaction
            yield connection
    finally:
        connection.close()


def index_pdf(path: Path) -> int:
    """(Re)index one PDF: extract text per page, replace old rows. Returns page count."""
    rel = config.rel_from_docs(path)
    mtime = path.stat().st_mtime
    texts = extract_text(path)
    with _conn() as conn:
        conn.execute("DELETE FROM pages WHERE path = ?", (rel,))
        conn.execute("DELETE FROM pages_fts WHERE path = ?", (rel,))
        for page_no, text in texts.items():
            conn.execute(
                "INSERT INTO pages(path, page, mtime) VALUES(?, ?, ?)",
                (rel, page_no, mtime),
            )
            if text:
                conn.execute(
                    "INSERT INTO pages_fts(text, path, page) VALUES(?, ?, ?)",
                    (text, rel, page_no),
                )
    return len(texts)


def search(query: str, limit: int = 20) -> list[dict]:
    """FTS5 search; the user query is quoted token-by-token to stay syntax-error free."""
    query = (query or "").strip()
    if not query:
        raise ValueError("search query is empty")
    match_query = " ".join('"' + token.replace('"', '""') + '"' for token in query.split())
    with _conn() as conn:
        rows = conn.execute(
            "SELECT path, page, "
            "snippet(pages_fts, 0, '<mark>', '</mark>', '…', 12) "
            "FROM pages_fts WHERE pages_fts MATCH ? LIMIT ?",
            (match_query, limit),
        ).fetchall()
    return [{"path": row[0], "page": row[1], "snippet": row[2]} for row in rows]


def remove_from_index(rel_path: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
        conn.execute("DELETE FROM pages_fts WHERE path = ?", (rel_path,))


def has_text(rel_path: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM pages_fts WHERE path = ? LIMIT 1", (rel_path,)
        ).fetchone()
    return row is not None


def stats() -> dict:
    if not db_path().exists():
        return {"files": 0, "pages": 0, "index_ok": False}
    with _conn() as conn:
        files, pages = conn.execute(
            "SELECT COUNT(DISTINCT path), COUNT(*) FROM pages"
        ).fetchone()
    return {"files": files, "pages": pages, "index_ok": True}
