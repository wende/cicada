"""
Tests for detailed_dependencies display in function formatter.

Covers the Bug #13 fix for what_it_calls parameter.
Tests internal/external dependency separation, 5-item display limit, and truncation messaging.
"""

from cicada.format.formatter import ModuleFormatter


def _make_function_result(
    module_name: str,
    function_name: str,
    arity: int = 0,
    file_path: str | None = None,
    detailed_dependencies: dict | None = None,
    dependencies: list | None = None,
) -> dict:
    """
    Helper to construct a function search result for testing.

    Args:
        module_name: Module name (e.g., "MyApp.Auth")
        function_name: Function name (e.g., "authenticate")
        arity: Function arity (default: 0)
        file_path: File path (default: auto-generated from module)
        detailed_dependencies: New-style dependencies dict (internal/external/total_count)
        dependencies: Old-style flat list of dependencies

    Returns:
        Function result dictionary suitable for ModuleFormatter._format_function_entry
    """
    if file_path is None:
        # Auto-generate file path from module name
        file_path = f"lib/{module_name.lower().replace('.', '/')}.ex"

    result = {
        "module": module_name,
        "function": {
            "name": function_name,
            "arity": arity,
            "line": 10,
            "type": "def",
        },
        "file": file_path,
    }

    if detailed_dependencies is not None:
        result["detailed_dependencies"] = detailed_dependencies
    if dependencies is not None:
        result["dependencies"] = dependencies

    return result


def test_detailed_dependencies_internal_first():
    """Test that internal dependencies are listed before external ones."""
    result = _make_function_result(
        "MyApp.Auth",
        "authenticate",
        arity=2,
        detailed_dependencies={
            "internal": [
                {"module": "MyApp.Auth", "function": "validate", "arity": 1, "line": 20},
                {"module": "MyApp.Auth", "function": "check_token", "arity": 1, "line": 25},
            ],
            "external": [
                {"module": "MyApp.User", "function": "get", "arity": 1, "line": 15},
                {"module": "MyApp.Session", "function": "create", "arity": 1, "line": 30},
            ],
            "total_count": 4,
        },
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Find the "Calls these functions:" section
    assert "Calls these functions:" in output

    # Find positions of internal and external dependencies in the output
    validate_pos = output.find("MyApp.Auth.validate/1")
    check_token_pos = output.find("MyApp.Auth.check_token/1")
    get_pos = output.find("MyApp.User.get/1")
    create_pos = output.find("MyApp.Session.create/1")

    # Internal dependencies should appear before external ones
    assert validate_pos < get_pos, "Internal dependency should appear before external"
    assert check_token_pos < create_pos, "Internal dependency should appear before external"


def test_detailed_dependencies_five_item_limit():
    """Test that only 5 dependencies are shown with proper truncation."""
    # Create 4 internal + 4 external = 8 total dependencies
    result = _make_function_result(
        "MyApp.Processor",
        "process",
        arity=1,
        detailed_dependencies={
            "internal": [
                {"module": "MyApp.Processor", "function": "step1", "arity": 1, "line": 20},
                {"module": "MyApp.Processor", "function": "step2", "arity": 1, "line": 25},
                {"module": "MyApp.Processor", "function": "step3", "arity": 1, "line": 30},
                {"module": "MyApp.Processor", "function": "step4", "arity": 1, "line": 35},
            ],
            "external": [
                {"module": "MyApp.Logger", "function": "log", "arity": 1, "line": 40},
                {"module": "MyApp.Metrics", "function": "track", "arity": 1, "line": 45},
                {"module": "MyApp.Cache", "function": "get", "arity": 1, "line": 50},
                {"module": "MyApp.DB", "function": "query", "arity": 1, "line": 55},
            ],
            "total_count": 8,
        },
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Count actual dependency lines shown (marked with bullet points)
    dep_lines = [
        line for line in output.split("\n") if line.strip().startswith("•") and "/" in line
    ]
    assert len(dep_lines) == 5, f"Should show exactly 5 dependencies, got {len(dep_lines)}"

    # Should show all 4 internal dependencies
    assert "MyApp.Processor.step1/1" in output
    assert "MyApp.Processor.step2/1" in output
    assert "MyApp.Processor.step3/1" in output
    assert "MyApp.Processor.step4/1" in output

    # Should show only 1 external (5 - 4 internal = 1 remaining slot)
    assert "MyApp.Logger.log/1" in output

    # Should NOT show the remaining external dependencies
    assert "MyApp.Metrics.track/1" not in output
    assert "MyApp.Cache.get/1" not in output
    assert "MyApp.DB.query/1" not in output

    # Should show truncation message
    assert "... and 3 more" in output


def test_detailed_dependencies_truncation_message():
    """Test that truncation message shows correct count."""
    # Create 2 internal + 10 external = 12 total
    result = _make_function_result(
        "MyApp.Handler",
        "handler",
        arity=1,
        detailed_dependencies={
            "internal": [
                {"module": "MyApp.Handler", "function": "validate", "arity": 1, "line": 20},
                {"module": "MyApp.Handler", "function": "process", "arity": 1, "line": 25},
            ],
            "external": [
                {"module": f"MyApp.Dep{i}", "function": "func", "arity": 1, "line": 30 + i}
                for i in range(10)
            ],
            "total_count": 12,
        },
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Should show 2 internal + 3 external = 5 total
    # Total count is 12, shown is 5, so should see "... and 7 more"
    assert "... and 7 more" in output


def test_detailed_dependencies_no_truncation_when_under_limit():
    """Test that no truncation message appears when total <= 5."""
    result = _make_function_result(
        "MyApp.Simple",
        "simple",
        detailed_dependencies={
            "internal": [
                {"module": "MyApp.Simple", "function": "helper1", "arity": 0, "line": 20},
                {"module": "MyApp.Simple", "function": "helper2", "arity": 0, "line": 25},
            ],
            "external": [
                {"module": "MyApp.Other", "function": "func", "arity": 1, "line": 30},
            ],
            "total_count": 3,
        },
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Should NOT show truncation message
    assert "... and" not in output
    assert "more" not in output

    # Should show all 3 dependencies
    assert "MyApp.Simple.helper1/0" in output
    assert "MyApp.Simple.helper2/0" in output
    assert "MyApp.Other.func/1" in output


def test_legacy_dependencies_format_still_works():
    """Test backward compatibility with legacy dependencies list format."""
    # Old format: just a flat list of dependencies
    result = _make_function_result(
        "MyApp.Legacy",
        "legacy_func",
        arity=1,
        dependencies=[
            {"module": "MyApp.User", "function": "get", "arity": 1, "line": 15},
            {"module": "MyApp.Auth", "function": "check", "arity": 1, "line": 20},
        ],
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Should still show dependencies section
    assert "Calls these functions:" in output
    assert "MyApp.User.get/1" in output
    assert "MyApp.Auth.check/1" in output


def test_legacy_dependencies_truncation():
    """Test that legacy format also respects 5-item limit."""
    # Old format with 8 dependencies
    result = _make_function_result(
        "MyApp.Legacy",
        "legacy_many",
        dependencies=[
            {"module": f"MyApp.Dep{i}", "function": "func", "arity": 1, "line": 20 + i}
            for i in range(8)
        ],
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Count dependency lines
    dep_lines = [
        line for line in output.split("\n") if line.strip().startswith("•") and "/" in line
    ]
    assert len(dep_lines) == 5, f"Should show exactly 5 dependencies, got {len(dep_lines)}"

    # Should show truncation
    assert "... and 3 more" in output


def test_no_dependencies_section_when_empty():
    """Test that dependencies section is omitted when there are no dependencies."""
    # detailed_dependencies with empty lists
    result = _make_function_result(
        "MyApp.Isolated",
        "isolated",
        detailed_dependencies={
            "internal": [],
            "external": [],
            "total_count": 0,
        },
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=True
    )
    output = "\n".join(lines)

    # Should NOT show dependencies section
    assert "Calls these functions:" not in output


def test_show_relationships_false_hides_dependencies():
    """Test that dependencies are hidden when show_relationships=False."""
    result = _make_function_result(
        "MyApp.Func",
        "func",
        detailed_dependencies={
            "internal": [
                {"module": "MyApp.Func", "function": "helper", "arity": 0, "line": 20},
            ],
            "external": [],
            "total_count": 1,
        },
    )

    lines = ModuleFormatter._format_function_entry(
        result, single_result=False, show_relationships=False
    )
    output = "\n".join(lines)

    # Should NOT show dependencies
    assert "Calls these functions:" not in output
    assert "MyApp.Func.helper/0" not in output
