from paper_cli.ai.markdown_blocks import (
    repairable_suspicious_blocks,
    split_markdown_blocks,
    suspicious_findings,
)


def _find(text, tmp_path):
    blocks = split_markdown_blocks(text)
    return suspicious_findings(blocks, tmp_path)


def test_formula_with_spaced_tokens_is_review_only(tmp_path):
    findings = _find(
        "$$\n"
        "s l o p e = { \\frac { A t t _ { n } } { A t t _ { X } } }\n"
        "$$\n",
        tmp_path,
    )

    assert len(findings) == 1
    assert findings[0].block.type == "formula"
    assert "spaced_letters" in findings[0].reasons
    assert findings[0].policy == "review_only"
    assert repairable_suspicious_blocks(findings) == []


def test_math_heavy_paragraph_is_review_only(tmp_path):
    findings = _find(
        "The flux is $1 0 ^ { 8 } \\mathrm { p h o t o n } / \\mathrm { c m } ^ { 2 } / \\mathrm { s }$ at 10 m.\n",
        tmp_path,
    )

    assert len(findings) == 1
    assert findings[0].block.type == "paragraph"
    assert "math_heavy" in findings[0].reasons
    assert findings[0].policy == "review_only"


def test_common_ocr_word_error_is_auto_repair(tmp_path):
    findings = _find("Te detector efciency is diferent for fast neutrons.\n", tmp_path)

    assert len(findings) == 1
    assert "common_ocr_word" in findings[0].reasons
    assert findings[0].policy == "auto_repair"
    assert [block.id for block in repairable_suspicious_blocks(findings)] == [findings[0].block.id]


def test_common_ocr_word_in_long_paragraph_is_review_only(tmp_path):
    findings = _find(
        "Te " + "long extracted paragraph with scientific context " * 12 + "has diferent detector efciency.\n",
        tmp_path,
    )

    assert len(findings) == 1
    assert "common_ocr_word" in findings[0].reasons
    assert findings[0].policy == "review_only"
    assert repairable_suspicious_blocks(findings) == []


def test_repeated_phrase_is_auto_repair(tmp_path):
    findings = _find(
        "The gamma-ray beam is produced using a LINAC The gamma-ray beam is produced using a LINAC to output gamma-rays.\n",
        tmp_path,
    )

    assert len(findings) == 1
    assert "repeated_phrase" in findings[0].reasons
    assert findings[0].policy == "auto_repair"


def test_broken_image_is_structural_warning(tmp_path):
    findings = _find("![](images/missing.jpg)\n", tmp_path)

    assert len(findings) == 1
    assert findings[0].block.type == "image"
    assert "broken_image" in findings[0].reasons
    assert findings[0].policy == "structural_warning"
    assert repairable_suspicious_blocks(findings) == []


def test_reference_section_blocks_are_protected(tmp_path):
    blocks = split_markdown_blocks(
        "## References\n\n"
        "1. A. Author. Tere is a spaced reference t i t l e.\n\n"
        "## Appendix\n\n"
        "Article\n"
    )

    assert blocks[0].type == "reference"
    assert blocks[1].type == "reference"
    assert blocks[2].type == "heading"
    assert blocks[3].type == "paragraph"
    findings = suspicious_findings(blocks, tmp_path)
    by_id = {finding.block.id: finding for finding in findings}
    assert by_id["b00001"].policy == "review_only"
    assert by_id["b00003"].policy == "auto_repair"


def test_html_table_is_typed_as_table(tmp_path):
    blocks = split_markdown_blocks("Table 1 values <table><tr><td>A</td></tr></table>\n")

    assert blocks[0].type == "table"
