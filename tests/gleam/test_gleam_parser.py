from pathlib import Path

from cicada.languages.gleam.parser import GleamParser


class LegacyPoint:
    def __init__(self, row: int):
        self.row = row


class LegacyNode:
    """Small stand-in for older Tree-sitter nodes with callable attributes."""

    def __init__(
        self,
        kind: str,
        *,
        text_range: tuple[int, int] = (0, 0),
        children: list["LegacyNode"] | None = None,
        row: int = 0,
        use_row_attr: bool = False,
    ):
        self.kind = kind
        self.start_byte, self.end_byte = text_range
        self._children = children or []
        self.start_position = LegacyPoint(row) if use_row_attr else (row, 0)

    def child_count(self):
        return len(self._children)

    def child(self, index: int):
        return self._children[index]


def write_sample(tmp_path: Path) -> Path:
    source = tmp_path / "src" / "wardwright" / "model.gleam"
    source.parent.mkdir(parents=True)
    source.write_text(
        """//// Model management helpers.
//// Used by the Wardwright admin UI.

pub type Model {
  Model(name: String)
}

/// Build a model from a name.
pub fn make_model(name: String) -> Model {
  Model(name: name)
}

/// Prefix a model name.
/// Keeps display naming consistent.
fn display_name(model: Model, prefix: String) -> String {
  prefix <> model.name
}
""",
        encoding="utf-8",
    )
    return source


def test_parse_module_name_and_docs(tmp_path):
    parser = GleamParser()
    source = write_sample(tmp_path)

    result = parser.parse_file(source, repo_path=tmp_path)

    assert result is not None
    assert result[0]["module"] == "wardwright/model"
    assert result[0]["file"] == "src/wardwright/model.gleam"
    assert result[0]["doc"] == "Model management helpers.\nUsed by the Wardwright admin UI."


def test_parse_function_visibility_arity_args_and_docs(tmp_path):
    parser = GleamParser()
    source = write_sample(tmp_path)

    module = parser.parse_file(source, repo_path=tmp_path)[0]
    functions = {function["name"]: function for function in module["functions"]}

    assert functions["make_model"]["type"] == "def"
    assert functions["make_model"]["arity"] == 1
    assert functions["make_model"]["args"] == ["name"]
    assert functions["make_model"]["doc"] == "Build a model from a name."

    assert functions["display_name"]["type"] == "defp"
    assert functions["display_name"]["arity"] == 2
    assert functions["display_name"]["args"] == ["model", "prefix"]
    assert functions["display_name"]["doc"] == (
        "Prefix a model name.\nKeeps display naming consistent."
    )


def test_parse_clears_orphan_doc_before_next_function(tmp_path):
    source = tmp_path / "src" / "orphan.gleam"
    source.parent.mkdir()
    source.write_text(
        """/// This doc belongs to no function.
pub const default_name = "default"

// Plain comments should not become function docs.
pub fn next() {
  Nil
}
""",
        encoding="utf-8",
    )

    module = GleamParser().parse_file(source, repo_path=tmp_path)[0]
    functions = {function["name"]: function for function in module["functions"]}

    assert "doc" not in functions["next"]


def test_parse_root_level_module_name(tmp_path):
    source = tmp_path / "tools.gleam"
    source.write_text("pub fn run() { Nil }\n", encoding="utf-8")

    module = GleamParser().parse_file(source, repo_path=tmp_path)[0]

    assert module["module"] == "tools"
    assert module["file"] == "tools.gleam"


def test_parse_without_repo_path_uses_local_file_identity(tmp_path):
    source = tmp_path / "standalone.gleam"
    source.write_text("pub fn run() { Nil }\n", encoding="utf-8")

    module = GleamParser().parse_file(source)[0]

    assert module["module"] == "standalone"
    assert module["file"] == str(source)


def test_empty_doc_comment_does_not_attach_blank_function_doc(tmp_path):
    source = tmp_path / "src" / "blank_doc.gleam"
    source.parent.mkdir()
    source.write_text(
        """///
pub fn next() {
  Nil
}
""",
        encoding="utf-8",
    )

    module = GleamParser().parse_file(source, repo_path=tmp_path)[0]
    functions = {function["name"]: function for function in module["functions"]}

    assert "doc" not in functions["next"]


def test_parser_reports_language_metadata():
    parser = GleamParser()

    assert parser.get_language_name() == "gleam"
    assert parser.get_file_extensions() == [".gleam"]
    assert parser.get_tree_sitter_language() is not None


def test_parse_file_outside_repo_uses_file_name_and_absolute_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = tmp_path / "external.gleam"
    source.write_text("pub fn run() { Nil }\n", encoding="utf-8")

    module = GleamParser().parse_file(source, repo_path=repo)[0]

    assert module["module"] == "external"
    assert module["file"] == str(source)


def test_legacy_tree_sitter_node_shape_still_extracts_function_data():
    source = b"pub fn run(value) { value }"
    parameter = LegacyNode("function_parameter", text_range=(11, 16))
    parameters = LegacyNode("function_parameters", children=[parameter])
    node = LegacyNode(
        "function",
        children=[
            LegacyNode("visibility_modifier", text_range=(0, 3)),
            LegacyNode("identifier", text_range=(7, 10)),
            parameters,
        ],
        row=3,
    )

    function = GleamParser()._extract_function(node, source)

    assert function == {
        "name": "run",
        "arity": 1,
        "line": 4,
        "type": "def",
        "args": ["value"],
    }


def test_legacy_tree_sitter_row_attribute_and_missing_name_paths():
    parser = GleamParser()
    nameless_node = LegacyNode("function", children=[LegacyNode("function_parameters")])

    assert parser._extract_function(nameless_node, b"fn () { Nil }") is None
    assert parser._start_line(LegacyNode("function", row=8, use_row_attr=True)) == 9


def test_tree_sitter_value_helper_reports_missing_attribute():
    parser = GleamParser()

    try:
        parser._value(object(), "missing")
    except AttributeError as exc:
        assert str(exc) == "missing"
    else:
        raise AssertionError("expected AttributeError for missing tree-sitter attribute")
