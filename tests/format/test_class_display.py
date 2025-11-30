"""Tests for Python class display in module formatter."""

import json

from cicada.format import ModuleFormatter


def test_format_module_with_classes_markdown():
    """Test that classes are displayed in markdown format."""
    module_data = {
        "file": "cicada/git/history_analyzer.py",
        "line": 1,
        "functions": [],  # No module-level functions
        "moduledoc": "Git history analysis module.",
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
        "classes": [
            {
                "name": "HistoryAnalyzer",
                "line": 17,
                "doc": "Analyzes git history for files and functions.",
                "public_methods": 3,
                "private_methods": 9,
                "total_methods": 12,
            }
        ],
    }

    result = ModuleFormatter.format_module_markdown(
        "cicada.git.history_analyzer", module_data, visibility="public"
    )

    # Check that the output contains the expected sections
    assert "cicada/git/history_analyzer.py:1" in result
    assert "cicada.git.history_analyzer" in result
    assert "0 public • 0 private" in result  # Module-level functions

    # Check that Classes section is present
    assert "**Classes:**" in result
    assert "HistoryAnalyzer (line 17)" in result
    assert "3 public • 9 private" in result  # Class methods
    assert "Analyzes git history" in result  # Class doc preview


def test_format_module_with_multiple_classes():
    """Test formatting a module with multiple classes."""
    module_data = {
        "file": "myapp/models.py",
        "line": 1,
        "functions": [],
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
        "classes": [
            {
                "name": "User",
                "line": 10,
                "doc": "User model representing a registered user.",
                "public_methods": 5,
                "private_methods": 2,
                "total_methods": 7,
            },
            {
                "name": "Post",
                "line": 50,
                "doc": "Post model for user-generated content.",
                "public_methods": 4,
                "private_methods": 1,
                "total_methods": 5,
            },
        ],
    }

    result = ModuleFormatter.format_module_markdown("myapp.models", module_data)

    # Check both classes are displayed
    assert "User (line 10)" in result
    assert "5 public • 2 private" in result
    assert "Post (line 50)" in result
    assert "4 public • 1 private" in result


def test_format_module_without_classes():
    """Test that modules without classes still work correctly."""
    module_data = {
        "file": "myapp/utils.py",
        "line": 1,
        "functions": [{"name": "helper_func", "arity": 1, "type": "public", "line": 5}],
        "total_functions": 1,
        "public_functions": 1,
        "private_functions": 0,
    }

    result = ModuleFormatter.format_module_markdown("myapp.utils", module_data)

    # Should not contain Classes section
    assert "**Classes:**" not in result
    # Should contain function information
    assert "myapp/utils.py:1" in result


def test_format_module_with_classes_json():
    """Test that classes are included in JSON format."""
    module_data = {
        "file": "cicada/git/history_analyzer.py",
        "line": 1,
        "functions": [],
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
        "classes": [
            {
                "name": "HistoryAnalyzer",
                "line": 17,
                "doc": "Analyzes git history.",
                "public_methods": 3,
                "private_methods": 9,
                "total_methods": 12,
            }
        ],
    }

    result = ModuleFormatter.format_module_json("cicada.git.history_analyzer", module_data)

    # Parse JSON
    parsed = json.loads(result)

    # Check that classes field is present
    assert "classes" in parsed
    assert len(parsed["classes"]) == 1
    assert parsed["classes"][0]["name"] == "HistoryAnalyzer"
    assert parsed["classes"][0]["public_methods"] == 3
    assert parsed["classes"][0]["private_methods"] == 9


def test_format_module_without_classes_json():
    """Test that JSON format works without classes field."""
    module_data = {
        "file": "myapp/utils.py",
        "line": 1,
        "functions": [],
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
    }

    result = ModuleFormatter.format_module_json("myapp.utils", module_data)

    # Parse JSON
    parsed = json.loads(result)

    # Classes field should not be present
    assert "classes" not in parsed


def test_format_module_with_long_class_doc():
    """Test that long class docs are truncated."""
    long_doc = "This is a very long documentation string that should be truncated " * 5
    module_data = {
        "file": "myapp/models.py",
        "line": 1,
        "functions": [],
        "total_functions": 0,
        "public_functions": 0,
        "private_functions": 0,
        "classes": [
            {
                "name": "LongDoc",
                "line": 10,
                "doc": long_doc,
                "public_methods": 2,
                "private_methods": 0,
                "total_methods": 2,
            }
        ],
    }

    result = ModuleFormatter.format_module_markdown("myapp.models", module_data)

    # Check that doc is truncated (80 chars + "...")
    assert "..." in result
    # Should not contain the full doc
    assert len([line for line in result.split("\n") if "very long" in line][0]) <= 100
