# Source Adapter Contract

Source adapters import paper records from external or local sources into the common paper bundle format.

## Current Reference Adapter

The current reference adapter is `LocalFolderAdapter`:

```python
from paper_cli.adapters.local_folder import LocalFolderAdapter

result = LocalFolderAdapter().import_source(
    library_dir,
    input_path,
    collection=None,
    inbox=True,
)
```

It scans a local PDF file or folder, copies new PDFs into bundles, skips duplicate PDFs by SHA-256, and leaves index rebuilding to the importer facade.

## Interface

Adapters expose:

```python
name: str

def import_source(
    library_dir: Path,
    input_path: Path,
    *,
    collection: str | None,
    inbox: bool,
) -> ImportResult:
    ...
```

`ImportResult` contains:

- `imported`: newly created bundle paths.
- `skipped`: source paths skipped by the adapter, currently used for duplicate PDFs.

## Facade

The CLI still calls `paper_cli.importer.import_path()`. That facade delegates to `LocalFolderAdapter` and rebuilds indexes. Future adapters should keep the same paper bundle, `paper.yaml`, and index contracts.

## Future Adapters

Planned adapters include:

- Zotero read-only import.
- Attanger-style attachment root mapping.
- BibTeX import.
- CSL JSON import.

Adapters should not mutate external source libraries. They should copy PDFs or reference source metadata into paper bundles using explicit provenance fields.
