from __future__ import annotations

from pathlib import Path

from .base import ImportResult


class LocalFolderAdapter:
    name = "local-folder"

    def import_source(
        self,
        library_dir: Path,
        input_path: Path,
        *,
        collection: str | None,
        inbox: bool,
    ) -> ImportResult:
        from paper_cli.fs import discover_pdfs
        from paper_cli.importer import import_pdf

        result = ImportResult()
        for pdf in discover_pdfs(input_path):
            bundle_dir = import_pdf(library_dir, pdf, collection=collection, inbox=inbox)
            if bundle_dir is None:
                result.skipped.append(pdf)
            else:
                result.imported.append(bundle_dir)
        return result
