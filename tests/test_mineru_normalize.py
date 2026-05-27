import io
import zipfile

import pytest

from paper_cli.converters.mineru_normalize import (
    normalize_mineru_directory,
    normalize_mineru_zip,
)


def test_normalize_mineru_zip_writes_bundle_contract(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("result/full.md", "# Converted\n")
        archive.writestr("result/images/fig.png", b"png")
        archive.writestr("result/layout.json", "{}")

    output = normalize_mineru_zip(buffer.getvalue(), tmp_path / "bundle")

    bundle = tmp_path / "bundle"
    assert output.markdown_path == bundle / "paper.md"
    assert (bundle / "paper.md").read_text(encoding="utf-8") == "# Converted\n"
    assert (bundle / "images" / "fig.png").exists()
    assert (bundle / "raw" / "mineru" / "layout.json").exists()


def test_normalize_mineru_directory_replaces_previous_images_and_raw(tmp_path):
    source = tmp_path / "source" / "nested"
    source.mkdir(parents=True)
    (source / "paper.md").write_text("# Local\n", encoding="utf-8")
    (source / "images").mkdir()
    (source / "images" / "new.png").write_bytes(b"new")
    (source / "content_list.json").write_text("[]", encoding="utf-8")
    bundle = tmp_path / "bundle"
    (bundle / "images").mkdir(parents=True)
    (bundle / "images" / "old.png").write_bytes(b"old")
    (bundle / "raw" / "mineru").mkdir(parents=True)
    (bundle / "raw" / "mineru" / "old.json").write_text("{}", encoding="utf-8")

    normalize_mineru_directory(tmp_path / "source", bundle)

    assert (bundle / "paper.md").read_text(encoding="utf-8") == "# Local\n"
    assert (bundle / "images" / "new.png").exists()
    assert not (bundle / "images" / "old.png").exists()
    assert (bundle / "raw" / "mineru" / "content_list.json").exists()
    assert not (bundle / "raw" / "mineru" / "old.json").exists()


def test_normalize_mineru_directory_requires_markdown(tmp_path):
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValueError):
        normalize_mineru_directory(source, tmp_path / "bundle")
