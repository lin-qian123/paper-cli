from pathlib import Path

import pytest

from paper_cli.validation.qed import run_qed_validation, select_qed_sample


def make_qed_source(tmp_path, count=5):
    source = tmp_path / "QED"
    source.mkdir()
    for index in range(count):
        (source / f"paper-{index}.pdf").write_bytes(f"%PDF-1.4\n{index}\n".encode())
    return source


def test_select_qed_sample_is_deterministic(tmp_path):
    source = make_qed_source(tmp_path, count=10)

    first = select_qed_sample(source, count=3, seed=42)
    second = select_qed_sample(source, count=3, seed=42)

    assert first == second
    assert len(first) == 3


def test_qed_validation_no_convert_creates_sample_library_and_report(tmp_path):
    source = make_qed_source(tmp_path, count=4)
    root = tmp_path / "cache"
    root.mkdir()

    payload = run_qed_validation(
        source=source,
        library_root=root,
        count=3,
        seed=123,
        name="qed-test",
        no_convert=True,
    )

    assert payload["ok"] is True
    assert payload["sampled"] == 3
    assert payload["imported"] == 3
    assert payload["duplicate_imported"] == 0
    assert payload["final_status"]["pending"] == 3
    assert Path(payload["sample_list"]).exists()
    assert Path(payload["sample_input"]).is_dir()
    assert Path(payload["report"]).exists()
    assert len(list(source.glob("*.pdf"))) == 4


def test_qed_validation_refuses_to_overwrite_without_replace(tmp_path):
    source = make_qed_source(tmp_path, count=2)
    root = tmp_path / "cache"
    root.mkdir()
    (root / "qed-test").mkdir()

    with pytest.raises(FileExistsError):
        run_qed_validation(
            source=source,
            library_root=root,
            count=1,
            seed=1,
            name="qed-test",
            no_convert=True,
        )
