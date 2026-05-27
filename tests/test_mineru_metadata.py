from paper_cli.converters.mineru_metadata import extract_mineru_metadata


def test_mineru_metadata_keeps_explicit_heading_authors_and_year():
    metadata, sources, confidence = extract_mineru_metadata(
        "# Better Title\nAuthors: Alice Zhang and Bob Li\nYear: 2025\n"
    )

    assert metadata["title"] == "Better Title"
    assert [creator["name"] for creator in metadata["creators"]] == ["Alice Zhang", "Bob Li"]
    assert metadata["year"] == 2025
    assert sources["creators"] == "mineru"
    assert confidence["creators"] == "high"


def test_mineru_metadata_extracts_title_page_author_line_without_authors_label():
    metadata, sources, confidence = extract_mineru_metadata(
        "# Correct Paper Title\n\nAlice Zhang, Bob Li, and Carol Wang\nInstitute of Example\n"
    )

    assert [creator["name"] for creator in metadata["creators"]] == [
        "Alice Zhang",
        "Bob Li",
        "Carol Wang",
    ]
    assert sources["creators"] == "mineru-title-page"
    assert confidence["creators"] == "medium"


def test_mineru_metadata_extracts_doi_and_arxiv():
    metadata, sources, confidence = extract_mineru_metadata(
        "# Title\nDOI: 10.1234/example.paper.2026.\narXiv:2401.12345v2\n"
    )

    assert metadata["doi"] == "10.1234/example.paper.2026"
    assert metadata["arxiv"] == "2401.12345v2"
    assert sources["doi"] == "mineru"
    assert confidence["arxiv"] == "high"


def test_mineru_metadata_rejects_journal_label_title_when_existing_title_is_better():
    metadata, sources, _ = extract_mineru_metadata(
        "# SCIENTIFIC REPORTS\n",
        existing={"title": "Real Physics Title"},
    )

    assert "title" not in metadata
    assert "title" not in sources


def test_mineru_metadata_rejects_affiliation_and_email_as_authors():
    metadata, _, _ = extract_mineru_metadata(
        "# Correct Paper Title\n\nInstitute of Example, Department of Physics\nalice@example.edu\n"
    )

    assert "creators" not in metadata
