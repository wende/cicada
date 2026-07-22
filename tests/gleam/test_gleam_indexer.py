import json
from pathlib import Path

import cicada.languages.gleam.indexer as gleam_indexer_module
from cicada.languages.gleam.indexer import GleamIndexer


def test_index_repository(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    gleam_file = src / "validator.gleam"
    gleam_file.write_text(
        """//// Validation helpers.

/// Validate a payload.
pub fn validate(payload: String) -> Bool {
  payload != ""
}

fn normalize(payload: String) -> String {
  payload
}
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "index.json"

    result = GleamIndexer().index_repository(tmp_path, output_path)

    assert result["success"] is True
    assert result["modules_count"] == 1
    assert result["functions_count"] == 2

    data = json.loads(output_path.read_text(encoding="utf-8"))
    module = data["modules"]["validator"]
    assert module["file"] == "src/validator.gleam"
    assert module["moduledoc"] == "Validation helpers."

    functions = {function["name"]: function for function in module["functions"]}
    assert functions["validate"]["type"] == "def"
    assert functions["normalize"]["type"] == "defp"


def test_indexer_reports_language_metadata():
    indexer = GleamIndexer()

    assert indexer.get_language_name() == "gleam"
    assert indexer.get_file_extensions() == [".gleam"]
    assert "_build" in indexer.get_excluded_dirs()


def test_index_repository_records_parse_errors_and_keeps_valid_modules(tmp_path: Path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    valid_file = src / "valid.gleam"
    valid_file.write_text("pub fn ok() -> Bool {\n  True\n}\n", encoding="utf-8")
    invalid_file = src / "invalid.gleam"
    invalid_file.write_text("pub fn broken() {\n", encoding="utf-8")
    output_path = tmp_path / "index.json"
    indexer = GleamIndexer()
    original_parse_file = indexer.parser.parse_file

    def parse_file(path, repo_path=None):
        if Path(path) == invalid_file:
            raise ValueError("parse error")
        return original_parse_file(path, repo_path=repo_path)

    monkeypatch.setattr(indexer.parser, "parse_file", parse_file)

    result = indexer.index_repository(tmp_path, output_path)

    assert result["success"] is False
    assert any(str(invalid_file) in error and "parse error" in error for error in result["errors"])

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["modules"]["valid"]["functions"][0]["name"] == "ok"


def test_index_repository_skips_files_without_parse_result(tmp_path: Path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "empty.gleam").write_text("pub fn ignored() { Nil }\n", encoding="utf-8")
    output_path = tmp_path / "index.json"
    indexer = GleamIndexer()
    monkeypatch.setattr(indexer.parser, "parse_file", lambda *_args, **_kwargs: None)

    result = indexer.index_repository(tmp_path, output_path)

    assert result["success"] is True
    assert result["modules_count"] == 0
    assert result["functions_count"] == 0

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["modules"] == {}


def test_indexer_verbose_output(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.gleam").write_text("pub fn main() { Nil }\n", encoding="utf-8")
    output_path = tmp_path / "index.json"

    GleamIndexer().index_repository(tmp_path, output_path, verbose=True)

    captured = capsys.readouterr()
    assert "Indexed 1 Gleam modules" in captured.out


def test_merge_repository_verbose_output(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    (src / "embedded.gleam").write_text("pub fn main() { Nil }\n", encoding="utf-8")
    output_path = tmp_path / "index.json"
    output_path.write_text(json.dumps({"modules": {}, "metadata": {"language": "elixir"}}))

    GleamIndexer().merge_repository(tmp_path, output_path, verbose=True)

    captured = capsys.readouterr()
    assert "Indexed 1 embedded Gleam modules" in captured.out


def test_indexer_keyword_extraction(tmp_path: Path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth_handler.gleam").write_text(
        """//// Authentication helpers.

/// Validate an authentication token.
pub fn validate_token(token: String) -> Bool {
  token != ""
}
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "index.json"

    class FakeKeywordExtractor:
        def extract_keywords_simple(self, text):
            return [f"kw:{text.split()[0].lower()}"]

    monkeypatch.setattr(
        gleam_indexer_module,
        "get_keyword_extractor_from_config",
        lambda *_args, **_kwargs: (True, FakeKeywordExtractor()),
    )

    result = GleamIndexer().index_repository(tmp_path, output_path)

    assert result["success"] is True
    data = json.loads(output_path.read_text(encoding="utf-8"))
    keywords = data["modules"]["auth_handler"]["keywords"]
    assert keywords["auth"] == 1.5
    assert keywords["handler"] == 1.5
    assert keywords["validate"] == 1.0
    assert keywords["token"] == 1.0
    assert keywords["kw:authentication"] == 1.0
    assert keywords["kw:validate"] == 0.5


def test_indexer_leaves_keywords_empty_when_extraction_disabled(tmp_path: Path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "ui.gleam").write_text(
        """pub fn ok() {
  Nil
}
""",
        encoding="utf-8",
    )
    output_path = tmp_path / "index.json"
    monkeypatch.setattr(
        gleam_indexer_module,
        "get_keyword_extractor_from_config",
        lambda *_args, **_kwargs: (False, None),
    )

    result = GleamIndexer().index_repository(tmp_path, output_path)

    assert result["success"] is True
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["modules"]["ui"]["keywords"] == {}


def test_merge_repository_adds_gleam_modules_to_existing_index(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "policy.gleam").write_text(
        'pub fn check(value: String) -> Bool {\n  value != ""\n}\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "index.json"
    output_path.write_text(
        json.dumps(
            {
                "modules": {
                    "Existing.Elixir": {
                        "file": "lib/existing.ex",
                        "line": 1,
                        "functions": [],
                    }
                },
                "metadata": {"language": "elixir"},
            }
        ),
        encoding="utf-8",
    )

    result = GleamIndexer().merge_repository(tmp_path, output_path)

    assert result["success"] is True
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert "Existing.Elixir" in data["modules"]
    assert data["modules"]["policy"]["language"] == "gleam"
    assert data["modules"]["policy"]["functions"][0]["name"] == "check"
    assert data["metadata"]["embedded_languages"]["gleam"]["functions_count"] == 1


def test_merge_repository_removes_stale_gleam_modules(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "current.gleam").write_text("pub fn run() { Nil }\n", encoding="utf-8")
    output_path = tmp_path / "index.json"
    output_path.write_text(
        json.dumps(
            {
                "modules": {
                    "current": {
                        "file": "src/current.gleam",
                        "line": 1,
                        "functions": [],
                        "language": "gleam",
                    },
                    "deleted": {
                        "file": "src/deleted.gleam",
                        "line": 1,
                        "functions": [],
                        "language": "gleam",
                    },
                    "README.md": {
                        "file": "README.md",
                        "line": 1,
                        "functions": [],
                        "module_type": "generic_file",
                    },
                },
                "metadata": {"language": "elixir"},
            }
        ),
        encoding="utf-8",
    )

    result = GleamIndexer().merge_repository(tmp_path, output_path)

    assert result["success"] is True
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert "current" in data["modules"]
    assert "deleted" not in data["modules"]
    assert "README.md" in data["modules"]
