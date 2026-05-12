from paper_cli.config import DEFAULT_NAMING_TEMPLATE
from paper_cli.naming import render_name, sanitize_name


def test_default_english_name_uses_et_al():
    metadata = {
        "language": "en",
        "creators": [{"name": "Vallieres"}],
        "year": 2025,
        "title": "High average-flux laser-driven neutron source",
    }
    assert render_name(DEFAULT_NAMING_TEMPLATE, metadata) == (
        "Vallieres et al. - 2025 - High average-flux laser-driven neutron source"
    )


def test_default_chinese_name_omits_et_al():
    metadata = {
        "language": "zh-CN",
        "creators": [{"name": "张三"}],
        "year": 2024,
        "title": "强场量子电动力学综述",
    }
    assert render_name(DEFAULT_NAMING_TEMPLATE, metadata) == "张三 - 2024 - 强场量子电动力学综述"


def test_sanitize_removes_path_separators():
    assert sanitize_name("A/B:C*D?") == "A-B-C-D"


def test_sanitize_collapses_whitespace_and_limits_length():
    assert sanitize_name("  A   B   ", max_length=3) == "A B"
