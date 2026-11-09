"""Unit tests for services.pdf_ops (spec 9, cases 1-4)."""

from __future__ import annotations

import pytest

from app.services import pdf_ops


class TestParsePages:
    def test_basic(self):
        assert pdf_ops.parse_pages("1-3,5,8-", 10) == [1, 2, 3, 5, 8, 9, 10]

    def test_open_range_to_end(self):
        assert pdf_ops.parse_pages("8-", 8) == [8]

    def test_single(self):
        assert pdf_ops.parse_pages("2", 3) == [2]

    def test_unsorted_overlap_dedup(self):
        assert pdf_ops.parse_pages("3,1-2,2", 5) == [1, 2, 3]

    def test_empty(self):
        with pytest.raises(ValueError):
            pdf_ops.parse_pages("", 5)
        with pytest.raises(ValueError):
            pdf_ops.parse_pages("  ", 5)

    def test_garbage(self):
        for bad in ("abc", "1,,2", "1-2-3", "-3", "0", "1;2"):
            with pytest.raises(ValueError):
                pdf_ops.parse_pages(bad, 5)

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            pdf_ops.parse_pages("4", 3)
        with pytest.raises(ValueError):
            pdf_ops.parse_pages("2-9", 3)

    def test_descending(self):
        with pytest.raises(ValueError):
            pdf_ops.parse_pages("3-1", 5)


class TestPdfOperations:
    def test_merge_three_in_order(self, make_pdf, docs_dir):
        make_pdf("a.pdf", "AAA", pages=2)
        make_pdf("b.pdf", "BBB", pages=1)
        make_pdf("c.pdf", "CCC", pages=3)
        out = pdf_ops.pdf_merge(
            [docs_dir / "a.pdf", docs_dir / "b.pdf", docs_dir / "c.pdf"],
            docs_dir / "merged.pdf",
        )
        info = pdf_ops.pdf_info(out)
        assert info["pages"] == 6
        text = pdf_ops.extract_text(out)
        assert text[1].startswith("AAA")
        assert text[3].startswith("BBB")
        assert text[4].startswith("CCC")

    def test_merge_needs_two(self, make_pdf, docs_dir):
        make_pdf("a.pdf")
        with pytest.raises(ValueError):
            pdf_ops.pdf_merge([docs_dir / "a.pdf"], docs_dir / "m.pdf")

    def test_merge_output_exists(self, make_pdf, docs_dir):
        make_pdf("a.pdf")
        make_pdf("b.pdf")
        (docs_dir / "out.pdf").write_bytes(b"%PDF-1.4 stub")
        with pytest.raises(FileExistsError):
            pdf_ops.pdf_merge(
                [docs_dir / "a.pdf", docs_dir / "b.pdf"], docs_dir / "out.pdf"
            )
        pdf_ops.pdf_merge(
            [docs_dir / "a.pdf", docs_dir / "b.pdf"], docs_dir / "out.pdf", overwrite=True
        )

    def test_split_ranges_names(self, make_pdf, docs_dir):
        make_pdf("doc.pdf", pages=6)
        outputs = pdf_ops.pdf_split(docs_dir / "doc.pdf", "ranges", "1-3,5")
        names = [p.name for p in outputs]
        assert names == ["doc_p01-03.pdf", "doc_p05.pdf"]
        assert all(p.is_file() for p in outputs)
        assert pdf_ops.pdf_info(outputs[0])["pages"] == 3
        assert pdf_ops.pdf_info(outputs[1])["pages"] == 1

    def test_split_every_n(self, make_pdf, docs_dir):
        make_pdf("doc.pdf", pages=5)
        outputs = pdf_ops.pdf_split(docs_dir / "doc.pdf", "every_n", "2")
        assert [pdf_ops.pdf_info(p)["pages"] for p in outputs] == [2, 2, 1]
        assert outputs[0].name == "doc_p01-02.pdf"
        assert outputs[2].name == "doc_p05.pdf"

    def test_split_bad_mode(self, make_pdf, docs_dir):
        make_pdf("doc.pdf")
        with pytest.raises(ValueError):
            pdf_ops.pdf_split(docs_dir / "doc.pdf", "nope", "1")

    def test_split_output_exists(self, make_pdf, docs_dir):
        make_pdf("doc.pdf", pages=2)
        (docs_dir / "doc_p01-02.pdf").write_bytes(b"%PDF-1.4 stub")
        with pytest.raises(FileExistsError):
            pdf_ops.pdf_split(docs_dir / "doc.pdf", "ranges", "1-2")

    def test_rotate(self, make_pdf, docs_dir):
        pikepdf = pytest.importorskip("pikepdf")
        make_pdf("r.pdf", pages=3)
        out = pdf_ops.pdf_rotate(docs_dir / "r.pdf", "2", 90, docs_dir / "r90.pdf")
        with pikepdf.open(out) as pdf:
            assert int(pdf.pages[1].Rotate) == 90

    def test_rotate_bad_angle(self, make_pdf, docs_dir):
        make_pdf("r.pdf")
        with pytest.raises(ValueError):
            pdf_ops.pdf_rotate(docs_dir / "r.pdf", "1", 45, docs_dir / "x.pdf")

    def test_delete_pages(self, make_pdf, docs_dir):
        make_pdf("d.pdf", pages=5)
        out = pdf_ops.pdf_delete_pages(docs_dir / "d.pdf", "2,4", docs_dir / "d2.pdf")
        assert pdf_ops.pdf_info(out)["pages"] == 3

    def test_delete_all_forbidden(self, make_pdf, docs_dir):
        make_pdf("d.pdf", pages=2)
        with pytest.raises(ValueError):
            pdf_ops.pdf_delete_pages(docs_dir / "d.pdf", "1-2", docs_dir / "x.pdf")

    def test_compress_fast_smaller_or_equal(self, make_pdf, docs_dir):
        make_pdf("c.pdf", "Hello " * 50, pages=3)
        result = pdf_ops.pdf_compress(docs_dir / "c.pdf", docs_dir / "c_fast.pdf", "fast")
        assert result["size_after"] <= result["size_before"]
        assert pdf_ops.pdf_info(result["output"])["pages"] == 3  # valid output

    def test_compress_strong_without_gs(self, make_pdf, docs_dir, monkeypatch):
        make_pdf("c.pdf")
        monkeypatch.setattr(pdf_ops, "gs_command", lambda: None)
        with pytest.raises(ValueError, match="Ghostscript"):
            pdf_ops.pdf_compress(docs_dir / "c.pdf", docs_dir / "c_strong.pdf", "strong")

    def test_same_input_output_rejected(self, make_pdf, docs_dir):
        make_pdf("s.pdf")
        with pytest.raises(ValueError, match="differ"):
            pdf_ops.pdf_compress(docs_dir / "s.pdf", docs_dir / "s.pdf", "fast")

    def test_info(self, make_pdf, docs_dir):
        make_pdf("i.pdf", pages=2)
        info = pdf_ops.pdf_info(docs_dir / "i.pdf")
        assert info["pages"] == 2
        assert info["size_bytes"] > 0
        assert info["encrypted"] is False

    def test_extract_text_pages(self, make_pdf, docs_dir):
        make_pdf("t.pdf", "Sample text", pages=3)
        texts = pdf_ops.extract_text(docs_dir / "t.pdf", "1,3")
        assert set(texts) == {1, 3}
        assert "Sample text [p1]" in texts[1]

    def test_not_pdf(self, docs_dir):
        (docs_dir / "fake.pdf").write_bytes(b"GIF89a not a pdf")
        with pytest.raises(pdf_ops.NotPdfError):
            pdf_ops.pdf_info(docs_dir / "fake.pdf")

    def test_missing_file(self, docs_dir):
        with pytest.raises(FileNotFoundError):
            pdf_ops.pdf_info(docs_dir / "nope.pdf")
