import json

from cicada.setup import _merge_embedded_gleam_index


def test_merge_embedded_gleam_skips_primary_gleam(tmp_path):
    output_path = tmp_path / "index.json"

    result = _merge_embedded_gleam_index(tmp_path, output_path, "gleam", verbose=False)

    assert result == []
    assert not output_path.exists()


def test_merge_embedded_gleam_for_non_gleam_primary(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "tools.gleam").write_text("pub fn run() { Nil }\n", encoding="utf-8")
    output_path = tmp_path / "index.json"
    output_path.write_text(json.dumps({"modules": {}, "metadata": {"language": "elixir"}}))

    result = _merge_embedded_gleam_index(tmp_path, output_path, "elixir", verbose=False)

    assert result == [".gleam"]
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["modules"]["tools"]["functions"][0]["name"] == "run"


def test_merge_embedded_gleam_skips_non_gleam_primary_without_gleam_files(tmp_path):
    output_path = tmp_path / "index.json"
    original = {"modules": {}, "metadata": {"language": "elixir"}}
    output_path.write_text(json.dumps(original), encoding="utf-8")

    result = _merge_embedded_gleam_index(tmp_path, output_path, "elixir", verbose=False)

    assert result == []
    assert json.loads(output_path.read_text(encoding="utf-8")) == original


def test_merge_embedded_gleam_raises_on_merge_failure(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "tools.gleam").write_text("pub fn run() { Nil }\n", encoding="utf-8")
    output_path = tmp_path / "index.json"
    output_path.write_text(json.dumps({"modules": {}, "metadata": {"language": "elixir"}}))

    def merge_repository(*_args, **_kwargs):
        return {"success": False, "errors": ["first failure", "second failure"]}

    monkeypatch.setattr(
        "cicada.languages.gleam.indexer.GleamIndexer.merge_repository",
        merge_repository,
    )

    try:
        _merge_embedded_gleam_index(tmp_path, output_path, "elixir", verbose=False)
    except RuntimeError as exc:
        assert str(exc) == "first failure; second failure"
    else:
        raise AssertionError("expected RuntimeError")
