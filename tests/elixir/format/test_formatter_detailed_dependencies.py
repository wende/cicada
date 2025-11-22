"""Tests for detailed dependency formatting in ModuleFormatter."""

import json

from cicada.format.formatter import ModuleFormatter


def _sample_module_data():
    """Return a minimal module payload for formatter tests."""
    return {
        "file": "lib/my_app/module.ex",
        "line": 12,
        "functions": [
            {"name": "foo", "arity": 1, "line": 20, "type": "def", "args": ["a"]},
            {"name": "bar", "arity": 0, "line": 30, "type": "defp"},
        ],
        "public_functions": 1,
        "private_functions": 1,
    }


def _sample_dependencies():
    """Return a detailed dependency payload used by multiple tests."""
    return {
        "direct": ["MyApp.DepA", "MyApp.DepB"],
        "transitive": {"MyApp.DepC": ["MyApp.DepA"], "MyApp.DepD": ["MyApp.DepB", "MyApp.DepC"]},
        "granular": {
            "MyApp.DepA": ["MyApp.Module.foo/1", "MyApp.Module.other/2"],
            "MyApp.DepB": ["MyApp.Module.foo/1"],
        },
    }


def test_format_module_markdown_includes_detailed_dependencies():
    """Markdown formatter should render direct, transitive, and granular dependency sections."""
    module_data = _sample_module_data()
    dependencies = _sample_dependencies()

    output = ModuleFormatter.format_module_markdown(
        "MyApp.Module", module_data, detailed_dependencies=dependencies
    )

    # Direct dependencies section
    assert "## Dependencies (2)" in output
    assert "• MyApp.DepA" in output
    assert "• MyApp.DepB" in output

    # Transitive dependencies section sorted alphabetically
    assert "## Transitive Dependencies (2)" in output
    assert "• MyApp.DepC (via MyApp.DepA)" in output
    assert "• MyApp.DepD (via MyApp.DepB, MyApp.DepC)" in output

    # Granular function usage section
    assert "## Function Usage" in output
    assert "### MyApp.DepA" in output
    assert "• MyApp.Module.foo/1" in output
    assert "### MyApp.DepB" in output


def test_format_module_json_includes_dependencies_block():
    """JSON formatter should include the dependencies block when provided."""
    module_data = _sample_module_data()
    dependencies = _sample_dependencies()

    output_json = ModuleFormatter.format_module_json(
        "MyApp.Module", module_data, visibility="all", detailed_dependencies=dependencies
    )
    payload = json.loads(output_json)

    assert payload["module"] == "MyApp.Module"
    assert payload["location"] == "lib/my_app/module.ex:12"
    assert payload["counts"] == {"public": 1, "private": 1}

    # Dependencies should be included verbatim
    assert payload["dependencies"] == dependencies
    assert len(payload["functions"]) == 2
