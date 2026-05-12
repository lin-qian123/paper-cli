# paper-cli MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. If the user explicitly authorizes subagents, use superpowers:subagent-driven-development for parallel chunks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working `paper-cli` MVP for local PDF folder import, copied paper bundles, MinerU conversion, metadata-first naming, post-conversion rename, indexes, and diagnostics.

**Architecture:** Implement a focused Python CLI under `src/paper_cli`. Keep domain logic independent from the CLI so import, naming, indexing, conversion, and doctor checks are testable without real network calls. Wrap MinerU behind a converter interface so tests use fake conversion output and real API code stays isolated.

**Tech Stack:** Python 3.11+, `argparse`, `PyYAML`, `pypdf`, `requests`, `pytest`.

---

## File Structure

Create:

```text
pyproject.toml
src/paper_cli/__init__.py
src/paper_cli/__main__.py
src/paper_cli/cli.py
src/paper_cli/config.py
src/paper_cli/models.py
src/paper_cli/fs.py
src/paper_cli/naming.py
src/paper_cli/metadata.py
src/paper_cli/indexes.py
src/paper_cli/importer.py
src/paper_cli/converters/__init__.py
src/paper_cli/converters/base.py
src/paper_cli/converters/mineru.py
src/paper_cli/converters/local_zip.py
src/paper_cli/convert.py
src/paper_cli/doctor.py
tests/conftest.py
tests/test_config.py
tests/test_naming.py
tests/test_metadata.py
tests/test_importer.py
tests/test_indexes.py
tests/test_convert.py
tests/test_doctor.py
```

Responsibilities:

- `cli.py`: command parsing only.
- `config.py`: `paper-cli.yaml` defaults and loading.
- `models.py`: `PaperRecord` dataclass and YAML persistence.
- `fs.py`: PDF discovery, atomic writes, safe moves, duplicate paths.
- `naming.py`: configured template rendering, sanitization, duplicate-name resolution.
- `metadata.py`: fast metadata extraction from filename and PDF metadata.
- `indexes.py`: rebuild `papers.jsonl`, append `jobs.jsonl`.
- `importer.py`: local PDF import workflow.
- `converters/base.py`: converter protocol and result types.
- `converters/mineru.py`: real MinerU API client.
- `converters/local_zip.py`: fake/local converter for tests.
- `convert.py`: pending conversion and post-conversion rename.
- `doctor.py`: library validation checks.

## Chunk 1: Scaffold And Init

### Task 1: Python package scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/paper_cli/__init__.py`
- Create: `src/paper_cli/__main__.py`
- Create: `src/paper_cli/cli.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**
  ```python
  # tests/test_config.py
  import subprocess
  import sys

  def test_module_help_runs():
      result = subprocess.run(
          [sys.executable, "-m", "paper_cli", "--help"],
          text=True,
          capture_output=True,
      )
      assert result.returncode == 0
      assert "paper-cli" in result.stdout
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_config.py::test_module_help_runs -v`
  Expected: FAIL with missing module or missing CLI.

- [ ] **Step 3: Write minimal implementation**
  `pyproject.toml`:
  ```toml
  [build-system]
  requires = ["setuptools>=69"]
  build-backend = "setuptools.build_meta"

  [project]
  name = "paper-cli"
  version = "0.1.0"
  description = "Agent-native local literature management CLI"
  requires-python = ">=3.11"
  dependencies = ["PyYAML>=6.0.1", "pypdf>=4.0.0", "requests>=2.31.0"]

  [project.optional-dependencies]
  dev = ["pytest>=8.0.0"]

  [project.scripts]
  paper = "paper_cli.cli:main"

  [tool.setuptools.packages.find]
  where = ["src"]

  [tool.pytest.ini_options]
  pythonpath = ["src"]
  testpaths = ["tests"]
  ```
  `src/paper_cli/__main__.py`:
  ```python
  from .cli import main

  if __name__ == "__main__":
      raise SystemExit(main())
  ```
  `src/paper_cli/cli.py`:
  ```python
  import argparse

  def build_parser() -> argparse.ArgumentParser:
      parser = argparse.ArgumentParser(prog="paper-cli")
      parser.add_argument("--version", action="store_true")
      return parser

  def main(argv: list[str] | None = None) -> int:
      parser = build_parser()
      args = parser.parse_args(argv)
      if args.version:
          print("paper-cli 0.1.0")
      return 0
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/test_config.py::test_module_help_runs -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add pyproject.toml src tests/test_config.py
  git commit -m "chore: scaffold python cli"
  ```

### Task 2: Library config and `paper init`

**Files:**
- Create: `src/paper_cli/config.py`
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**
  ```python
  from paper_cli.cli import main
  from paper_cli.config import load_config

  def test_init_creates_library_layout(tmp_path):
      library = tmp_path / "library"
      assert main(["init", str(library)]) == 0
      assert (library / "paper-cli.yaml").exists()
      assert (library / "collections").is_dir()
      assert (library / "inbox").is_dir()
      assert (library / "indexes" / "papers.jsonl").exists()
      assert (library / "indexes" / "jobs.jsonl").exists()
      config = load_config(library)
      assert config["schema_version"] == 1
      assert "naming" in config
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_config.py::test_init_creates_library_layout -v`
  Expected: FAIL because `init` is missing.

- [ ] **Step 3: Implement config and init**
  `config.py` exposes:
  ```python
  DEFAULT_NAMING_TEMPLATE = '''{{if language == "zh"}}
  {{ firstCreator suffix=" - " }}
  {{elseif language == "zh-CN"}}
  {{ firstCreator suffix=" - " }}
  {{else}}
  {{creators max="1" suffix=" et al. - "}}
  {{ endif }}
  {{ year suffix=" - " }}
  {{ title truncate="100" }}'''

  def default_config() -> dict: ...
  def write_default_config(library_dir: Path) -> None: ...
  def load_config(library_dir: Path) -> dict: ...
  ```
  Update `cli.py` with an `init` subparser.

- [ ] **Step 4: Run tests**
  Run: `pytest tests/test_config.py -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/config.py src/paper_cli/cli.py tests/test_config.py
  git commit -m "feat: initialize paper library"
  ```

## Chunk 2: Naming And Metadata

### Task 3: Naming template renderer

**Files:**
- Create: `src/paper_cli/naming.py`
- Test: `tests/test_naming.py`

- [ ] **Step 1: Write failing tests**
  ```python
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
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest tests/test_naming.py -v`
  Expected: FAIL because `naming.py` is missing.

- [ ] **Step 3: Implement only the MVP template features**
  Support `if/elseif/else/endif`, `firstCreator`, `creators max="1" suffix=...`, `year suffix=...`, and `title truncate=...`. Do not add a general-purpose template engine.

- [ ] **Step 4: Run tests**
  Run: `pytest tests/test_naming.py -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/naming.py tests/test_naming.py
  git commit -m "feat: add metadata naming renderer"
  ```

### Task 4: Fast metadata extraction

**Files:**
- Create: `src/paper_cli/metadata.py`
- Test: `tests/test_metadata.py`

- [ ] **Step 1: Write failing tests**
  ```python
  from pathlib import Path
  from paper_cli.metadata import metadata_from_filename

  def test_parse_author_year_title_filename():
      meta = metadata_from_filename(Path("Vallieres et al. - 2025 - High average-flux laser-driven neutron source.pdf"))
      assert meta["creators"][0]["name"] == "Vallieres"
      assert meta["year"] == 2025
      assert meta["title"] == "High average-flux laser-driven neutron source"

  def test_fallback_title_from_stem():
      meta = metadata_from_filename(Path("unknown-paper.pdf"))
      assert meta["title"] == "unknown-paper"
      assert meta["creators"] == []
      assert meta["year"] is None
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest tests/test_metadata.py -v`
  Expected: FAIL because `metadata.py` is missing.

- [ ] **Step 3: Implement metadata helpers**
  Expose:
  ```python
  def metadata_from_filename(path: Path) -> dict: ...
  def metadata_from_pdf(path: Path) -> dict: ...
  def fast_metadata(path: Path) -> dict: ...
  ```
  `metadata_from_pdf` should use `pypdf.PdfReader` defensively and return partial metadata.

- [ ] **Step 4: Run tests**
  Run: `pytest tests/test_metadata.py -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/metadata.py tests/test_metadata.py
  git commit -m "feat: extract fast paper metadata"
  ```

## Chunk 3: Bundles, Import, And Indexes

### Task 5: Models and YAML persistence

**Files:**
- Create: `src/paper_cli/models.py`
- Test: `tests/test_importer.py`

- [ ] **Step 1: Write failing test**
  ```python
  from paper_cli.models import PaperRecord, write_paper, read_paper

  def test_paper_yaml_round_trip(tmp_path):
      record = PaperRecord.new(
          paper_id="sha256:abc",
          name="Example et al. - 2025 - Paper",
          collection="plasma/lwfa",
          imported_from="/tmp/source.pdf",
      )
      write_paper(tmp_path, record)
      loaded = read_paper(tmp_path)
      assert loaded.id == "sha256:abc"
      assert loaded.status["conversion"] == "pending"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_importer.py::test_paper_yaml_round_trip -v`
  Expected: FAIL because `models.py` is missing.

- [ ] **Step 3: Implement `PaperRecord`**
  Use a dataclass with `new()`, `to_dict()`, and `from_dict()` helpers plus `read_paper()` and `write_paper()`.

- [ ] **Step 4: Run test**
  Run: `pytest tests/test_importer.py::test_paper_yaml_round_trip -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/models.py tests/test_importer.py
  git commit -m "feat: persist paper metadata"
  ```

### Task 6: Local PDF import

**Files:**
- Create: `src/paper_cli/fs.py`
- Create: `src/paper_cli/importer.py`
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_importer.py`

- [ ] **Step 1: Write failing test**
  ```python
  from paper_cli.cli import main

  def test_import_pdf_copies_bundle(tmp_path):
      library = tmp_path / "library"
      source = tmp_path / "Vallieres et al. - 2025 - High average-flux laser-driven neutron source.pdf"
      source.write_bytes(b"%PDF-1.4\\n%fake\\n")
      assert main(["init", str(library)]) == 0
      assert main(["--library", str(library), "import", str(source), "--collection", "plasma/lwfa"]) == 0
      bundle = library / "collections" / "plasma" / "lwfa" / "Vallieres et al. - 2025 - High average-flux laser-driven neutron source"
      assert (bundle / "original.pdf").read_bytes() == source.read_bytes()
      assert (bundle / "paper.yaml").exists()
      assert (bundle / "notes" / "README.md").exists()
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_importer.py::test_import_pdf_copies_bundle -v`
  Expected: FAIL because import command is missing.

- [ ] **Step 3: Implement importer**
  Expose:
  ```python
  def discover_pdfs(path: Path) -> list[Path]: ...
  def paper_id_for_file(path: Path) -> str: ...
  def import_pdf(library_dir: Path, pdf_path: Path, collection: str | None, inbox: bool = False) -> Path: ...
  ```
  Use SHA-256 of file bytes for stable ID. Copy source as `original.pdf`. Create `notes/README.md`.

- [ ] **Step 4: Add CLI subcommand**
  Support:
  ```bash
  paper --library <library> import <pdf-or-folder> --collection <path>
  paper --library <library> import <pdf-or-folder> --inbox
  ```

- [ ] **Step 5: Run tests**
  Run: `pytest tests/test_importer.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/fs.py src/paper_cli/importer.py src/paper_cli/cli.py tests/test_importer.py
  git commit -m "feat: import local pdf bundles"
  ```

### Task 7: Rebuildable indexes

**Files:**
- Create: `src/paper_cli/indexes.py`
- Modify: `src/paper_cli/importer.py`
- Test: `tests/test_indexes.py`

- [ ] **Step 1: Write failing test**
  ```python
  import json
  from paper_cli.cli import main

  def test_import_updates_papers_index(tmp_path):
      library = tmp_path / "library"
      pdf = tmp_path / "A et al. - 2025 - Indexed Paper.pdf"
      pdf.write_bytes(b"%PDF-1.4\\n")
      main(["init", str(library)])
      main(["--library", str(library), "import", str(pdf), "--inbox"])
      lines = (library / "indexes" / "papers.jsonl").read_text().splitlines()
      assert len(lines) == 1
      row = json.loads(lines[0])
      assert row["name"] == "A et al. - 2025 - Indexed Paper"
      assert row["status"]["conversion"] == "pending"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_indexes.py -v`
  Expected: FAIL because indexes are not updated.

- [ ] **Step 3: Implement index rebuild**
  Expose:
  ```python
  def find_paper_dirs(library_dir: Path) -> list[Path]: ...
  def rebuild_papers_index(library_dir: Path) -> None: ...
  def append_job(library_dir: Path, event: dict) -> None: ...
  ```
  Call `rebuild_papers_index()` after import and conversion.

- [ ] **Step 4: Run tests**
  Run: `pytest tests/test_indexes.py -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/indexes.py src/paper_cli/importer.py tests/test_indexes.py
  git commit -m "feat: rebuild paper indexes"
  ```

## Chunk 4: Conversion, Rename, Status, And Doctor

### Task 8: Converter interface and fake converter

**Files:**
- Create: `src/paper_cli/converters/__init__.py`
- Create: `src/paper_cli/converters/base.py`
- Create: `src/paper_cli/converters/local_zip.py`
- Test: `tests/test_convert.py`

- [ ] **Step 1: Write failing test**
  ```python
  from paper_cli.converters.local_zip import LocalFixtureConverter

  def test_local_fixture_converter_writes_markdown_and_images(tmp_path):
      source_pdf = tmp_path / "original.pdf"
      source_pdf.write_bytes(b"%PDF-1.4\\n")
      out = tmp_path / "out"
      fixture = tmp_path / "fixture"
      fixture.mkdir()
      (fixture / "paper.md").write_text("# Better Title\\n", encoding="utf-8")
      (fixture / "images").mkdir()
      result = LocalFixtureConverter(fixture).convert(source_pdf, out)
      assert result.ok is True
      assert (out / "paper.md").exists()
      assert (out / "images").is_dir()
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_convert.py::test_local_fixture_converter_writes_markdown_and_images -v`
  Expected: FAIL because converter files are missing.

- [ ] **Step 3: Implement base and local converter**
  `base.py` contains `ConversionResult` dataclass and a `Converter` protocol. `local_zip.py` copies fixture `paper.md` and `images/` into the destination.

- [ ] **Step 4: Run test**
  Run: `pytest tests/test_convert.py::test_local_fixture_converter_writes_markdown_and_images -v`
  Expected: PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add src/paper_cli/converters tests/test_convert.py
  git commit -m "feat: add conversion adapter interface"
  ```

### Task 9: Pending conversion and post-conversion rename

**Files:**
- Create: `src/paper_cli/convert.py`
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_convert.py`

- [ ] **Step 1: Write failing test**
  ```python
  from paper_cli.cli import main

  def test_convert_pending_writes_markdown_and_renames(tmp_path):
      library = tmp_path / "library"
      pdf = tmp_path / "Unknown.pdf"
      pdf.write_bytes(b"%PDF-1.4\\n")
      fixture = tmp_path / "fixture"
      fixture.mkdir()
      (fixture / "paper.md").write_text("# Better Paper Title\\nAuthors: Zhang\\nYear: 2025\\n", encoding="utf-8")
      (fixture / "images").mkdir()
      main(["init", str(library)])
      main(["--library", str(library), "import", str(pdf), "--inbox"])
      assert main(["--library", str(library), "convert", "--pending", "--fixture-output", str(fixture)]) == 0
      renamed = library / "inbox" / "Zhang et al. - 2025 - Better Paper Title"
      assert (renamed / "paper.md").exists()
      assert (renamed / "conversion.json").exists()
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_convert.py::test_convert_pending_writes_markdown_and_renames -v`
  Expected: FAIL because convert command is missing.

- [ ] **Step 3: Implement conversion workflow**
  Expose:
  ```python
  def convert_pending(library_dir: Path, converter: Converter) -> list[Path]: ...
  def extract_metadata_from_markdown(markdown: str) -> dict: ...
  def maybe_rename_bundle(library_dir: Path, bundle_dir: Path, record: PaperRecord) -> Path: ...
  ```
  MVP metadata extraction:
  - First `# Heading` becomes title.
  - `Authors:` line sets first creator.
  - `Year:` line sets year.

- [ ] **Step 4: Add CLI convert command**
  Support `paper --library <library> convert --pending --fixture-output <dir>` for tests and dry runs.

- [ ] **Step 5: Run tests**
  Run: `pytest tests/test_convert.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/convert.py src/paper_cli/cli.py tests/test_convert.py
  git commit -m "feat: convert pending paper bundles"
  ```

### Task 10: Real MinerU adapter

**Files:**
- Create: `src/paper_cli/converters/mineru.py`
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_convert.py`

- [ ] **Step 1: Write failing unit tests with mocked HTTP**
  Test missing `MINERU_API_KEY` returns a structured failure and makes no network calls. Add a second test that monkeypatches `requests.post`, `requests.put`, and `requests.get` to simulate upload, polling, ZIP download, and output normalization.

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_convert.py -v`
  Expected: FAIL because MinerU adapter is missing.

- [ ] **Step 3: Implement `MinerUConverter`**
  Requirements:
  - Read key from `MINERU_API_KEY`.
  - Use `MINERU_API_BASE` or default `https://mineru.net/api/v4`.
  - Call `/file-urls/batch`.
  - Upload PDF to the presigned URL.
  - Poll `/extract-results/batch/<batch_id>`.
  - Download ZIP.
  - Extract into a temp directory.
  - Normalize first Markdown file to `paper.md`.
  - Normalize `images/` if present.

- [ ] **Step 4: Wire CLI default converter**
  `paper convert --pending` uses real MinerU unless `--fixture-output` is provided.

- [ ] **Step 5: Run tests without real network**
  Run: `pytest tests/test_convert.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/converters/mineru.py src/paper_cli/cli.py tests/test_convert.py
  git commit -m "feat: add mineru conversion adapter"
  ```

### Task 11: List, status, and doctor

**Files:**
- Create: `src/paper_cli/doctor.py`
- Modify: `src/paper_cli/cli.py`
- Test: `tests/test_doctor.py`

- [ ] **Step 1: Write failing doctor test**
  ```python
  from paper_cli.doctor import run_doctor

  def test_doctor_reports_missing_original_pdf(tmp_path):
      bundle = tmp_path / "library" / "inbox" / "Broken"
      bundle.mkdir(parents=True)
      (bundle / "paper.yaml").write_text("schema_version: 1\\nid: abc\\nname: Broken\\n", encoding="utf-8")
      issues = run_doctor(tmp_path / "library")
      assert any(issue.code == "missing-original-pdf" for issue in issues)
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/test_doctor.py -v`
  Expected: FAIL because doctor is missing.

- [ ] **Step 3: Implement doctor checks**
  Start with missing `paper.yaml`, invalid YAML, duplicate IDs, missing `original.pdf`, conversion done but missing `paper.md`, and stale index count mismatch.

- [ ] **Step 4: Add CLI commands**
  Add `paper list`, `paper status`, and `paper doctor`.

- [ ] **Step 5: Run tests**
  Run: `pytest tests/test_doctor.py tests/test_indexes.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  ```bash
  git add src/paper_cli/doctor.py src/paper_cli/cli.py tests/test_doctor.py
  git commit -m "feat: add library inspection commands"
  ```

## Chunk 5: Documentation And End-To-End Verification

### Task 12: Docs and final verification

**Files:**
- Modify: `README.md`
- Modify: `TODO.md`
- Modify: `docs/zh/README.zh.md`
- Modify: `docs/zh/TODO.zh.md`

- [ ] **Step 1: Update usage docs**
  Add install command, local workflow example, `MINERU_API_KEY` requirement, and fixture conversion note.

- [ ] **Step 2: Update TODO state**
  Mark implemented commands complete in English and Chinese TODO files.

- [ ] **Step 3: Run full tests**
  Run: `pytest -v`
  Expected: PASS.

- [ ] **Step 4: Run CLI smoke commands**
  ```bash
  python3 -m paper_cli --help
  python3 -m paper_cli init /tmp/paper-cli-demo
  python3 -m paper_cli --library /tmp/paper-cli-demo status
  ```
  Expected: all exit 0.

- [ ] **Step 5: Commit**
  ```bash
  git add README.md TODO.md docs/zh/README.zh.md docs/zh/TODO.zh.md
  git commit -m "docs: document mvp usage"
  ```

## Final Verification

- [ ] Run: `pytest -v`
- [ ] Run: `python3 -m paper_cli --help`
- [ ] Run a local fixture end-to-end import and conversion.
- [ ] Confirm `git status --short` is clean.
- [ ] Update `TODO.md` and `docs/zh/TODO.zh.md` with final implementation state.

## Notes For Implementation

- Keep real MinerU calls serial for MVP.
- Do not add Zotero code in this implementation pass.
- Do not add SQLite in MVP unless JSONL proves insufficient during implementation.
- Preserve English docs as engineering source of truth, but keep Chinese docs aligned after meaningful changes.
