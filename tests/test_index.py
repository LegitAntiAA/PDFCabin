"""Tests for the SQLite FTS5 index (spec 9, cases 6-7 partially)."""

from __future__ import annotations

import pytest

from app.services import index, pdf_ops


def test_index_and_search(make_pdf, docs_dir):
    make_pdf("report.pdf", "The quick brown fox", pages=2)
    pages = index.index_pdf(docs_dir / "report.pdf")
    assert pages == 2

    hits = index.search("fox")
    assert len(hits) >= 1
    assert hits[0]["path"] == "report.pdf"
    assert "fox" in hits[0]["snippet"]
    assert hits[0]["page"] in (1, 2)


def test_search_cyrillic(make_pdf, docs_dir):
    make_pdf("rus.pdf", "Привет мир, проверка русского поиска", pages=1)
    index.index_pdf(docs_dir / "rus.pdf")
    hits = index.search("русского")
    assert hits, "unicode61 must tokenize Cyrillic"
    assert hits[0]["path"] == "rus.pdf"


def test_search_word_form_only(make_pdf, docs_dir):
    """No stemming (v0.1 is documented as exact word forms)."""
    make_pdf("forms.pdf", "документы лежат в папке", pages=1)
    index.index_pdf(docs_dir / "forms.pdf")
    assert index.search("документы")
    assert not index.search("документ")  # different word form -> no hit


def test_reindex_replaces_old_rows(make_pdf, docs_dir):
    make_pdf("x.pdf", "version one", pages=1)
    index.index_pdf(docs_dir / "x.pdf")
    stats_before = index.stats()
    index.index_pdf(docs_dir / "x.pdf")  # same file again -> no duplicates
    stats_after = index.stats()
    assert stats_after == stats_before


def test_remove_from_index(make_pdf, docs_dir):
    make_pdf("gone.pdf", "bye bye", pages=1)
    index.index_pdf(docs_dir / "gone.pdf")
    index.remove_from_index("gone.pdf")
    assert not index.search("bye")
    assert index.stats()["files"] == 0


def test_search_syntax_chaos(make_pdf, docs_dir):
    """User input with FTS operators must not blow up the query."""
    make_pdf("q.pdf", "plain words here", pages=1)
    index.index_pdf(docs_dir / "q.pdf")
    for bad in ('"unclosed', "AND", "OR NOT", "a - b", "()", "word*"):
        index.search(bad)  # must not raise


def test_empty_query(make_pdf, docs_dir):
    make_pdf("q.pdf", "text", pages=1)
    index.index_pdf(docs_dir / "q.pdf")
    with pytest.raises(ValueError):
        index.search("   ")


def test_has_text_and_stats(make_pdf, docs_dir):
    assert index.stats() == {"files": 0, "pages": 0, "index_ok": False}
    make_pdf("h.pdf", "hello there", pages=3)
    index.index_pdf(docs_dir / "h.pdf")
    assert index.has_text("h.pdf")
    assert not index.has_text("other.pdf")
    stats = index.stats()
    assert stats["files"] == 1 and stats["pages"] == 3 and stats["index_ok"]


def test_search_matches_via_full_pipeline(make_pdf, docs_dir):
    """Spec 9 case 7: extract -> index -> search hits the right page."""
    make_pdf("multi.pdf", "needle on page three", pages=3)
    texts = pdf_ops.extract_text(docs_dir / "multi.pdf")
    from app import config

    rel = config.rel_from_docs(docs_dir / "multi.pdf")
    index.index_pdf(docs_dir / "multi.pdf")
    hits = index.search("needle")
    assert hits
    page = hits[0]["page"]
    assert "needle" in texts[page]
    assert hits[0]["path"] == rel
