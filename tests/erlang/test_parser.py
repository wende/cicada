"""Minimal test for Erlang parser POC."""

from cicada.languages.erlang.parser import ErlangParser


def test_simple_module():
    """Test parsing a simple Erlang module."""
    parser = ErlangParser()
    result = parser.parse_file("tests/fixtures/sample.erl")

    assert result is not None
    assert len(result) == 1

    module = result[0]
    assert module["module"] == "sample"
    assert len(module["functions"]) == 2

    # Check function extraction
    func_names = {f["name"] for f in module["functions"]}
    assert "hello" in func_names
    assert "add" in func_names


def test_export_detection():
    """Test that exports are detected as public (def)."""
    parser = ErlangParser()
    result = parser.parse_file("tests/fixtures/sample.erl")

    module = result[0]
    for func in module["functions"]:
        # Both hello/1 and add/2 are exported
        assert func["type"] == "def"


def test_function_arity():
    """Test that function arity is correctly extracted."""
    parser = ErlangParser()
    result = parser.parse_file("tests/fixtures/sample.erl")

    module = result[0]
    funcs = {f["name"]: f for f in module["functions"]}

    assert funcs["hello"]["arity"] == 1
    assert funcs["add"]["arity"] == 2


def test_edoc_module_doc():
    """Test that module-level @doc is extracted."""
    parser = ErlangParser()
    result = parser.parse_file("tests/fixtures/sample_with_docs.erl")

    module = result[0]
    assert module["doc"] is not None
    assert "greeting utilities" in module["doc"]


def test_edoc_function_doc():
    """Test that function-level @doc is extracted."""
    parser = ErlangParser()
    result = parser.parse_file("tests/fixtures/sample_with_docs.erl")

    module = result[0]
    funcs = {f["name"]: f for f in module["functions"]}

    # hello has @doc, @param, and @returns
    assert funcs["hello"]["doc"] == "Greets a person by name."
    assert funcs["hello"]["params"][0]["name"] == "Name"
    assert funcs["hello"]["returns"] == "ok"

    # add has @doc with multi-line text
    assert "Adds two numbers" in funcs["add"]["doc"]
    assert "arithmetic function" in funcs["add"]["doc"]

    # private_helper has no @doc (regular comment)
    assert funcs["private_helper"].get("doc") is None


def test_no_doc_without_tag():
    """Test that regular comments without @doc are not extracted."""
    parser = ErlangParser()
    result = parser.parse_file("tests/fixtures/sample.erl")

    module = result[0]
    # sample.erl has no @doc comments
    assert module.get("doc") is None

    for func in module["functions"]:
        assert func.get("doc") is None
