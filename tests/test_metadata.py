import logging
from pathlib import Path

from paper_cli.metadata import fast_metadata, metadata_from_filename


def test_parse_author_year_title_filename():
    meta = metadata_from_filename(
        Path("Vallieres et al. - 2025 - High average-flux laser-driven neutron source.pdf")
    )
    assert meta["creators"][0]["name"] == "Vallieres"
    assert meta["year"] == 2025
    assert meta["title"] == "High average-flux laser-driven neutron source"
    assert meta["language"] == "en"


def test_parse_chinese_author_year_title_filename():
    meta = metadata_from_filename(Path("张三 - 2024 - 强场量子电动力学综述.pdf"))
    assert meta["creators"][0]["name"] == "张三"
    assert meta["year"] == 2024
    assert meta["title"] == "强场量子电动力学综述"
    assert meta["language"] == "zh-CN"


def test_fallback_title_from_stem():
    meta = metadata_from_filename(Path("unknown-paper.pdf"))
    assert meta["title"] == "unknown-paper"
    assert meta["creators"] == []
    assert meta["year"] is None


def test_invalid_pdf_metadata_does_not_emit_warning(tmp_path, caplog):
    pdf = tmp_path / "invalid.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    caplog.set_level(logging.WARNING)
    meta = fast_metadata(pdf)
    assert meta["title"] == "invalid"
    assert "EOF marker" not in caplog.text
