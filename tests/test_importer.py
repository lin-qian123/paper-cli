from paper_cli.models import PaperRecord, read_paper, write_paper


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
    assert loaded.collection == "plasma/lwfa"
