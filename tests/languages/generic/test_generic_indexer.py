import json

from cicada.languages.generic.indexer import GenericFileIndexer


def test_indexes_text_files_and_preserves_existing_modules(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "README.md").write_text("Setup instructions for installing Cicada.", encoding="utf-8")
    docs_dir = repo / "docs"
    docs_dir.mkdir()
    (docs_dir / "note.md").write_text("Detailed install guide.", encoding="utf-8")
    (docs_dir / "ignored.md").write_text("Should be ignored.", encoding="utf-8")

    (repo / ".gitignore").write_text("docs/ignored.md\n", encoding="utf-8")
    (repo / "script.py").write_text("print('hello')", encoding="utf-8")

    output_path = tmp_path / "index.json"
    existing_index = {
        "modules": {
            "Existing.Module": {
                "file": "lib/existing.ex",
                "line": 1,
                "functions": [],
            }
        },
        "metadata": {
            "language": "elixir",
            "indexed_at": "yesterday",
            "total_modules": 1,
            "total_functions": 0,
            "public_functions": 0,
            "private_functions": 0,
        },
    }
    output_path.write_text(json.dumps(existing_index))

    indexer = GenericFileIndexer(excluded_extensions={".py"})
    result = indexer.index_repository(repo, output_path, verbose=False)

    data = json.loads(output_path.read_text())
    modules = data["modules"]

    assert "README.md" in modules
    assert "docs/note.md" in modules
    assert ".gitignore" in modules
    assert "docs/ignored.md" not in modules
    assert "script.py" not in modules
    assert "Existing.Module" in modules

    readme_entry = modules["README.md"]
    assert readme_entry["module_type"] == "generic_file"
    assert readme_entry["functions"] == []
    assert readme_entry["line"] == 1
    assert isinstance(readme_entry.get("keywords"), dict)
    assert readme_entry["keywords"]

    assert result["files_indexed"] == 3
    assert data["metadata"]["language"] == "elixir"
    assert data["metadata"]["total_modules"] == len(modules)


def test_skips_large_and_binary_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    large_file = repo / "large.txt"
    large_file.write_text("line\n" * 10050, encoding="utf-8")

    binary_file = repo / "binary.txt"
    with open(binary_file, "wb") as handle:
        handle.write(b"\x00\x01\x02\x03")

    (repo / "notes").write_text("plain text file", encoding="utf-8")

    output_path = tmp_path / "index.json"
    indexer = GenericFileIndexer()
    indexer.index_repository(repo, output_path, verbose=False)

    data = json.loads(output_path.read_text())
    modules = data["modules"]

    assert "notes" in modules
    assert "large.txt" not in modules
    assert "binary.txt" not in modules


def test_removes_stale_generic_modules_when_files_deleted(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    readme = repo / "README.md"
    readme.write_text("Initial text", encoding="utf-8")

    output_path = tmp_path / "index.json"
    indexer = GenericFileIndexer()
    indexer.index_repository(repo, output_path, verbose=False)

    data = json.loads(output_path.read_text())
    assert "README.md" in data["modules"]

    readme.unlink()
    indexer.index_repository(repo, output_path, verbose=False)

    updated = json.loads(output_path.read_text())
    assert "README.md" not in updated["modules"]
