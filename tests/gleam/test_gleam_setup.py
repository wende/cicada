from cicada.setup import detect_project_language


def test_detect_gleam_toml(tmp_path):
    (tmp_path / "gleam.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")

    assert detect_project_language(tmp_path) == "gleam"


def test_detect_gleam_source_fallback(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.gleam").write_text("pub fn main() { Nil }\n", encoding="utf-8")

    assert detect_project_language(tmp_path) == "gleam"
