from paper_cli.adapters.local_folder import LocalFolderAdapter
from paper_cli.cli import main
from paper_cli.models import read_paper


def test_local_folder_adapter_imports_pdf(tmp_path):
    library = tmp_path / "library"
    pdf = tmp_path / "A et al. - 2025 - Adapter Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main(["init", str(library)])

    result = LocalFolderAdapter().import_source(library, pdf, collection=None, inbox=True)

    assert len(result.imported) == 1
    bundle = result.imported[0]
    record = read_paper(bundle)
    assert record.source["type"] == "local-folder"
    assert record.name == "A et al. - 2025 - Adapter Paper"
    assert result.skipped == []


def test_local_folder_adapter_reports_skipped_duplicates(tmp_path):
    library = tmp_path / "library"
    first = tmp_path / "A et al. - 2025 - Same.pdf"
    duplicate = tmp_path / "B et al. - 2025 - Same Contents.pdf"
    payload = b"%PDF-1.4\nsame\n"
    first.write_bytes(payload)
    duplicate.write_bytes(payload)
    main(["init", str(library)])
    adapter = LocalFolderAdapter()

    first_result = adapter.import_source(library, first, collection=None, inbox=True)
    second_result = adapter.import_source(library, duplicate, collection=None, inbox=True)

    assert len(first_result.imported) == 1
    assert second_result.imported == []
    assert second_result.skipped == [duplicate]
