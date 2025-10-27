#!/usr/bin/env python
"""
Tests for the formatter module, including call site consolidation.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.formatter import ModuleFormatter


def test_group_call_sites_by_caller_single_caller():
    """Test that multiple call sites from the same caller are grouped together."""
    call_sites = [
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 261,
            "code_line": "    GenServer.cast(pid, :update_presence)",
        },
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 312,
            "code_line": "    GenServer.cast(pid, :update_presence)",
        },
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 358,
            "code_line": "    GenServer.cast(pid, :update_presence)",
        },
        {
            "calling_module": "ThenvoiComWeb.Api.V1.UserRoomsChannel",
            "calling_function": {"name": "handle_info", "arity": 2},
            "file": "lib/thenvoi_com_web/channels/api/v1/user_rooms_channel.ex",
            "line": 387,
            "code_line": "    GenServer.cast(pid, :update_presence)",
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have exactly 1 grouped entry
    assert len(grouped) == 1, f"Expected 1 grouped entry, got {len(grouped)}"

    # Should have all 4 lines
    assert grouped[0]["lines"] == [
        261,
        312,
        358,
        387,
    ], f"Expected lines [261, 312, 358, 387], got {grouped[0]['lines']}"

    # Should have all 4 code lines
    assert (
        len(grouped[0]["code_lines"]) == 4
    ), f"Expected 4 code lines, got {len(grouped[0]['code_lines'])}"

    # Verify the caller info is preserved
    assert grouped[0]["calling_module"] == "ThenvoiComWeb.Api.V1.UserRoomsChannel"
    assert grouped[0]["calling_function"]["name"] == "handle_info"
    assert grouped[0]["calling_function"]["arity"] == 2


def test_group_call_sites_by_caller_multiple_callers():
    """Test that call sites from different callers are kept separate."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 10,
        },
        {
            "calling_module": "MyApp.ModuleB",
            "calling_function": {"name": "func2", "arity": 2},
            "file": "lib/my_app/module_b.ex",
            "line": 20,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 15,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have 2 grouped entries (ModuleA.func1/1 and ModuleB.func2/2)
    assert len(grouped) == 2, f"Expected 2 grouped entries, got {len(grouped)}"

    # Find the ModuleA group
    module_a_group = [g for g in grouped if g["calling_module"] == "MyApp.ModuleA"][0]
    assert module_a_group["lines"] == [
        10,
        15,
    ], f"Expected lines [10, 15] for ModuleA, got {module_a_group['lines']}"

    # Find the ModuleB group
    module_b_group = [g for g in grouped if g["calling_module"] == "MyApp.ModuleB"][0]
    assert module_b_group["lines"] == [
        20
    ], f"Expected lines [20] for ModuleB, got {module_b_group['lines']}"


def test_group_call_sites_by_caller_same_module_different_functions():
    """Test that call sites from the same module but different functions are kept separate."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 10,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func2", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 20,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 15,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have 2 grouped entries (func1/1 and func2/1)
    assert len(grouped) == 2, f"Expected 2 grouped entries, got {len(grouped)}"

    # Find the func1 group
    func1_group = [g for g in grouped if g["calling_function"]["name"] == "func1"][0]
    assert func1_group["lines"] == [
        10,
        15,
    ], f"Expected lines [10, 15] for func1, got {func1_group['lines']}"

    # Find the func2 group
    func2_group = [g for g in grouped if g["calling_function"]["name"] == "func2"][0]
    assert func2_group["lines"] == [
        20
    ], f"Expected lines [20] for func2, got {func2_group['lines']}"


def test_group_call_sites_by_caller_no_calling_function():
    """Test that call sites without calling_function are grouped by module only."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "file": "lib/my_app/module_a.ex",
            "line": 10,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "file": "lib/my_app/module_a.ex",
            "line": 20,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Should have 1 grouped entry (same module, no function info)
    assert len(grouped) == 1, f"Expected 1 grouped entry, got {len(grouped)}"

    # Should have both lines
    assert grouped[0]["lines"] == [
        10,
        20,
    ], f"Expected lines [10, 20], got {grouped[0]['lines']}"

    # calling_function should be None
    assert grouped[0]["calling_function"] is None


def test_group_call_sites_lines_are_sorted():
    """Test that line numbers in grouped results are sorted."""
    call_sites = [
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 100,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 50,
        },
        {
            "calling_module": "MyApp.ModuleA",
            "calling_function": {"name": "func1", "arity": 1},
            "file": "lib/my_app/module_a.ex",
            "line": 75,
        },
    ]

    grouped = ModuleFormatter._group_call_sites_by_caller(call_sites)

    # Lines should be sorted
    assert grouped[0]["lines"] == [
        50,
        75,
        100,
    ], f"Expected sorted lines [50, 75, 100], got {grouped[0]['lines']}"


def test_format_function_results_markdown_with_consolidated_call_sites():
    """Test that the markdown formatter uses consolidated call sites."""
    results = [
        {
            "module": "MyApp.TargetModule",
            "function": {
                "name": "target_function",
                "arity": 2,
                "type": "def",
                "line": 42,
                "args": ["arg1", "arg2"],
            },
            "file": "lib/my_app/target_module.ex",
            "call_sites": [
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "handle_info", "arity": 2},
                    "file": "lib/my_app/caller.ex",
                    "line": 10,
                },
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "handle_info", "arity": 2},
                    "file": "lib/my_app/caller.ex",
                    "line": 20,
                },
                {
                    "calling_module": "MyApp.Caller",
                    "calling_function": {"name": "handle_info", "arity": 2},
                    "file": "lib/my_app/caller.ex",
                    "line": 30,
                },
            ],
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "target_function", results
    )

    # Should have a single consolidated line for the caller
    assert (
        "MyApp.Caller.handle_info/2 at lib/my_app/caller.ex:10, :20, :30" in markdown
    ), "Expected consolidated call sites in markdown output"

    # Should NOT have multiple separate lines for the same caller
    lines = markdown.split("\n")
    caller_lines = [line for line in lines if "MyApp.Caller.handle_info/2" in line]
    assert (
        len(caller_lines) == 1
    ), f"Expected 1 line for caller, got {len(caller_lines)}: {caller_lines}"


def test_format_function_results_markdown_with_code_lines():
    """Test that consolidated call sites properly display code examples."""
    call_sites = [
        {
            "calling_module": "MyApp.Caller",
            "calling_function": {"name": "process", "arity": 1},
            "file": "lib/my_app/caller.ex",
            "line": 10,
            "code_line": "    TargetModule.target_function(data)",
        },
        {
            "calling_module": "MyApp.Caller",
            "calling_function": {"name": "process", "arity": 1},
            "file": "lib/my_app/caller.ex",
            "line": 20,
            "code_line": "    TargetModule.target_function(other_data)",
        },
    ]

    results = [
        {
            "module": "MyApp.TargetModule",
            "function": {
                "name": "target_function",
                "arity": 1,
                "type": "def",
                "line": 42,
                "args": ["arg1"],
            },
            "file": "lib/my_app/target_module.ex",
            "call_sites": call_sites,
            "call_sites_with_examples": call_sites,  # Both call sites have examples
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "target_function", results
    )

    # Should have consolidated header
    assert (
        "MyApp.Caller.process/1 at lib/my_app/caller.ex:10, :20" in markdown
    ), "Expected consolidated call sites header in markdown output"

    # Should have both code examples
    assert (
        ":10" in markdown and ":20" in markdown
    ), "Expected both line numbers in output"
    assert (
        "TargetModule.target_function(data)" in markdown
    ), "Expected first code example"
    assert (
        "TargetModule.target_function(other_data)" in markdown
    ), "Expected second code example"


def test_format_function_results_markdown_with_additional_call_sites():
    """Test that when showing code examples, other call sites are also listed."""
    # Create 5 call sites total
    all_call_sites = [
        {
            "calling_module": "MyApp.Caller1",
            "calling_function": {"name": "process", "arity": 1},
            "file": "lib/my_app/caller1.ex",
            "line": 10,
            "code_line": "    TargetModule.target_function(data1)",
        },
        {
            "calling_module": "MyApp.Caller2",
            "calling_function": {"name": "handle", "arity": 2},
            "file": "lib/my_app/caller2.ex",
            "line": 20,
            "code_line": "    TargetModule.target_function(data2)",
        },
        {
            "calling_module": "MyApp.Caller3",
            "calling_function": {"name": "execute", "arity": 0},
            "file": "lib/my_app/caller3.ex",
            "line": 30,
        },
        {
            "calling_module": "MyApp.Caller4",
            "calling_function": {"name": "run", "arity": 1},
            "file": "lib/my_app/caller4.ex",
            "line": 40,
        },
        {
            "calling_module": "MyApp.TestCaller",
            "calling_function": {"name": "test_function", "arity": 1},
            "file": "test/my_app/test_caller_test.ex",
            "line": 50,
        },
    ]

    # Only first 2 have code examples
    call_sites_with_examples = all_call_sites[:2]

    results = [
        {
            "module": "MyApp.TargetModule",
            "function": {
                "name": "target_function",
                "arity": 1,
                "type": "def",
                "line": 42,
                "args": ["arg1"],
            },
            "file": "lib/my_app/target_module.ex",
            "call_sites": all_call_sites,
            "call_sites_with_examples": call_sites_with_examples,
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "target_function", results
    )

    # Should have Usage Examples section with the first 2
    assert "Usage Examples:" in markdown, "Expected Usage Examples section"
    assert (
        "TargetModule.target_function(data1)" in markdown
    ), "Expected first code example"
    assert (
        "TargetModule.target_function(data2)" in markdown
    ), "Expected second code example"

    # Should have Other Call Sites section with the remaining 3
    assert "Other Call Sites:" in markdown, "Expected Other Call Sites section"
    assert "MyApp.Caller3.execute/0" in markdown, "Expected Caller3 in other call sites"
    assert "MyApp.Caller4.run/1" in markdown, "Expected Caller4 in other call sites"
    assert (
        "MyApp.TestCaller.test_function/1" in markdown
    ), "Expected TestCaller in other call sites"

    # Verify that Caller1 and Caller2 are NOT in Other Call Sites
    # (they should only appear in Usage Examples)
    lines = markdown.split("\n")
    other_call_sites_start = None
    for i, line in enumerate(lines):
        if "**Other Call Sites:**" in line:
            other_call_sites_start = i
            break

    if other_call_sites_start:
        other_call_sites_section = "\n".join(lines[other_call_sites_start:])
        assert (
            "MyApp.Caller1.process/1" not in other_call_sites_section
        ), "Caller1 should not appear in Other Call Sites (only in Usage Examples)"
        assert (
            "MyApp.Caller2.handle/2" not in other_call_sites_section
        ), "Caller2 should not appear in Other Call Sites (only in Usage Examples)"


def test_format_module_markdown_with_private_functions_only():
    """Test formatting module with private_functions='only'."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "functions": [
            {"name": "public_func", "arity": 0, "type": "def", "line": 10, "args": []},
            {
                "name": "private_func",
                "arity": 1,
                "type": "defp",
                "line": 20,
                "args": ["arg1"],
            },
        ],
        "public_functions": 1,
        "private_functions": 1,
    }

    result = ModuleFormatter.format_module_markdown(
        "TestModule", data, private_functions="only"
    )

    # Should show only private functions
    assert "private_func" in result
    assert "public_func" not in result
    assert "Private:" in result


def test_format_module_markdown_with_private_functions_include():
    """Test formatting module with private_functions='include'."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "functions": [
            {"name": "public_func", "arity": 0, "type": "def", "line": 10, "args": []},
            {
                "name": "private_func",
                "arity": 1,
                "type": "defp",
                "line": 20,
                "args": ["arg1"],
            },
        ],
        "public_functions": 1,
        "private_functions": 1,
    }

    result = ModuleFormatter.format_module_markdown(
        "TestModule", data, private_functions="include"
    )

    # Should show both public and private
    assert "private_func" in result
    assert "public_func" in result
    assert "Public:" in result
    assert "Private:" in result


def test_format_module_markdown_no_functions():
    """Test formatting module with no functions."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "functions": [],
        "public_functions": 0,
        "private_functions": 0,
    }

    result = ModuleFormatter.format_module_markdown("TestModule", data)

    assert "*No functions found*" in result


def test_format_module_markdown_no_private_when_only_requested():
    """Test formatting when only private requested but none exist."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "functions": [
            {"name": "public_func", "arity": 0, "type": "def", "line": 10, "args": []}
        ],
        "public_functions": 1,
        "private_functions": 0,
    }

    result = ModuleFormatter.format_module_markdown(
        "TestModule", data, private_functions="only"
    )

    assert "*No private functions found*" in result


def test_format_module_json_with_private_only():
    """Test JSON formatting with private_functions='only'."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "moduledoc": "Test module",
        "functions": [
            {"name": "public_func", "arity": 0, "type": "def", "line": 10, "args": []},
            {
                "name": "private_func",
                "arity": 1,
                "type": "defp",
                "line": 20,
                "args": ["arg1"],
            },
        ],
        "public_functions": 1,
        "private_functions": 1,
    }

    result = ModuleFormatter.format_module_json(
        "TestModule", data, private_functions="only"
    )
    parsed = json.loads(result)

    # Should only have private function
    assert len(parsed["functions"]) == 1
    assert parsed["functions"][0]["type"] == "defp"


def test_format_module_json_with_private_include():
    """Test JSON formatting with private_functions='include'."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "moduledoc": "Test module",
        "functions": [
            {"name": "public_func", "arity": 0, "type": "def", "line": 10, "args": []},
            {
                "name": "private_func",
                "arity": 1,
                "type": "defp",
                "line": 20,
                "args": ["arg1"],
            },
        ],
        "public_functions": 1,
        "private_functions": 1,
    }

    result = ModuleFormatter.format_module_json(
        "TestModule", data, private_functions="include"
    )
    parsed = json.loads(result)

    # Should have both functions
    assert len(parsed["functions"]) == 2


def test_format_function_results_markdown_with_guards():
    """Test markdown formatting with function guards."""
    results = [
        {
            "module": "MyApp.Module",
            "function": {
                "name": "guarded_func",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["n"],
                "guards": ["is_integer(n)", "n > 0"],
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown("guarded_func", results)

    # Should include guards
    assert "when" in markdown.lower()
    assert "is_integer(n)" in markdown
    assert "n > 0" in markdown


def test_format_function_results_markdown_with_examples():
    """Test markdown formatting with function examples."""
    results = [
        {
            "module": "MyApp.Module",
            "function": {
                "name": "example_func",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["x"],
                "examples": "iex> example_func(5)\n10",
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown("example_func", results)

    # Should include examples
    assert "Examples:" in markdown
    assert "iex> example_func(5)" in markdown


def test_format_function_results_markdown_multiple_results():
    """Test markdown formatting with multiple function results."""
    results = [
        {
            "module": "MyApp.Module1",
            "function": {
                "name": "func",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["x"],
            },
            "file": "lib/my_app/module1.ex",
            "call_sites": [],
        },
        {
            "module": "MyApp.Module2",
            "function": {
                "name": "func",
                "arity": 1,
                "type": "def",
                "line": 20,
                "args": ["x"],
            },
            "file": "lib/my_app/module2.ex",
            "call_sites": [],
        },
    ]

    markdown = ModuleFormatter.format_function_results_markdown("func", results)

    # Should have separator and both results
    assert "---" in markdown
    assert "MyApp.Module1" in markdown
    assert "MyApp.Module2" in markdown
    assert "Found 2 match(es):" in markdown


def test_format_function_results_json_with_examples():
    """Test JSON formatting with examples."""
    results = [
        {
            "module": "MyApp.Module",
            "function": {
                "name": "example_func",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["x"],
                "examples": "iex> example_func(5)\n10",
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
        }
    ]

    result_json = ModuleFormatter.format_function_results_json("example_func", results)
    parsed = json.loads(result_json)

    # Should include examples
    assert "examples" in parsed["results"][0]
    assert parsed["results"][0]["examples"] == "iex> example_func(5)\n10"


def test_format_function_results_json_with_return_type():
    """Test JSON formatting with return type."""
    results = [
        {
            "module": "MyApp.Module",
            "function": {
                "name": "typed_func",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["x"],
                "return_type": "integer()",
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
        }
    ]

    result_json = ModuleFormatter.format_function_results_json("typed_func", results)
    parsed = json.loads(result_json)

    # Should include return_type
    assert "return_type" in parsed["results"][0]
    assert parsed["results"][0]["return_type"] == "integer()"


def test_format_function_results_json_with_guards():
    """Test JSON formatting with guards."""
    results = [
        {
            "module": "MyApp.Module",
            "function": {
                "name": "guarded_func",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["n"],
                "guards": ["is_integer(n)", "n > 0"],
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
        }
    ]

    result_json = ModuleFormatter.format_function_results_json("guarded_func", results)
    parsed = json.loads(result_json)

    # Should include guards
    assert "guards" in parsed["results"][0]
    assert parsed["results"][0]["guards"] == ["is_integer(n)", "n > 0"]


def test_format_function_results_json_not_found():
    """Test JSON formatting when no results found."""
    result_json = ModuleFormatter.format_function_results_json("nonexistent", [])
    parsed = json.loads(result_json)

    assert "error" in parsed
    assert parsed["error"] == "Function not found"


def test_json_formatter_format_string():
    """Test JSONFormatter format_string method."""
    from cicada.formatter import JSONFormatter

    formatter = JSONFormatter(indent=2)
    input_json = '{"key":"value","nested":{"a":1}}'

    result = formatter.format_string(input_json)

    # Should be formatted
    assert "\n" in result
    assert '"key": "value"' in result or '"key":"value"' in result


def test_json_formatter_format_string_invalid():
    """Test JSONFormatter with invalid JSON."""
    from cicada.formatter import JSONFormatter
    import pytest

    formatter = JSONFormatter()

    with pytest.raises(ValueError, match="Invalid JSON"):
        formatter.format_string("{invalid json")


def test_json_formatter_format_dict():
    """Test JSONFormatter format_dict method."""
    from cicada.formatter import JSONFormatter

    formatter = JSONFormatter(indent=4, sort_keys=True)
    data = {"z": 1, "a": 2, "m": 3}

    result = formatter.format_dict(data)

    # Should be formatted with 4 spaces and sorted
    assert "\n" in result
    parsed = json.loads(result)
    assert (
        list(parsed.keys()) == ["a", "m", "z"]
        if formatter.sort_keys
        else list(data.keys())
    )


def test_json_formatter_format_file(tmp_path):
    """Test JSONFormatter format_file method."""
    from cicada.formatter import JSONFormatter

    # Create test JSON file
    input_file = tmp_path / "input.json"
    input_file.write_text('{"key":"value","nested":{"a":1}}')

    formatter = JSONFormatter(indent=2)
    result = formatter.format_file(input_file)

    # Should be formatted
    assert "\n" in result
    assert "key" in result


def test_json_formatter_format_file_not_found(tmp_path):
    """Test JSONFormatter with non-existent file."""
    from cicada.formatter import JSONFormatter
    import pytest

    formatter = JSONFormatter()
    nonexistent = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        formatter.format_file(nonexistent)


def test_json_formatter_format_file_with_output(tmp_path):
    """Test JSONFormatter writing to output file."""
    from cicada.formatter import JSONFormatter

    # Create test JSON file
    input_file = tmp_path / "input.json"
    input_file.write_text('{"key":"value"}')

    output_file = tmp_path / "output.json"

    formatter = JSONFormatter(indent=2)
    _ = formatter.format_file(input_file, output_file)

    # Output file should exist
    assert output_file.exists()

    # Content should be formatted
    output_content = output_file.read_text()
    assert "\n" in output_content


def test_json_formatter_main_with_output(tmp_path, monkeypatch, capsys):
    """Test main() function with output file."""
    from cicada.formatter import main
    import sys

    # Create test file
    input_file = tmp_path / "test.json"
    input_file.write_text('{"key":"value"}')

    output_file = tmp_path / "output.json"

    # Mock sys.argv
    test_args = ["formatter.py", str(input_file), "-o", str(output_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    # Should not raise
    main()

    # Output file should exist
    assert output_file.exists()


def test_json_formatter_main_to_stdout(tmp_path, monkeypatch, capsys):
    """Test main() function printing to stdout."""
    from cicada.formatter import main
    import sys

    # Create test file
    input_file = tmp_path / "test.json"
    input_file.write_text('{"key":"value"}')

    # Mock sys.argv
    test_args = ["formatter.py", str(input_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    main()

    # Should print to stdout
    captured = capsys.readouterr()
    assert "key" in captured.out


def test_json_formatter_main_with_indent(tmp_path, monkeypatch):
    """Test main() function with custom indent."""
    from cicada.formatter import main
    import sys

    input_file = tmp_path / "test.json"
    input_file.write_text('{"key":"value"}')

    output_file = tmp_path / "output.json"

    test_args = ["formatter.py", str(input_file), "-o", str(output_file), "-i", "4"]
    monkeypatch.setattr(sys, "argv", test_args)

    main()

    # Check indentation in output
    content = output_file.read_text()
    assert "    " in content  # 4 spaces


def test_json_formatter_main_with_sort_keys(tmp_path, monkeypatch):
    """Test main() function with sort_keys."""
    from cicada.formatter import main
    import sys

    input_file = tmp_path / "test.json"
    input_file.write_text('{"z":1,"a":2}')

    output_file = tmp_path / "output.json"

    test_args = ["formatter.py", str(input_file), "-o", str(output_file), "--sort-keys"]
    monkeypatch.setattr(sys, "argv", test_args)

    main()

    # Keys should be sorted
    content = output_file.read_text()
    parsed = json.loads(content)
    assert list(parsed.keys()) == ["a", "z"]


def test_json_formatter_main_with_compact(tmp_path, monkeypatch):
    """Test main() function with compact flag."""
    from cicada.formatter import main
    import sys

    input_file = tmp_path / "test.json"
    input_file.write_text('{"key": "value"}')

    output_file = tmp_path / "output.json"

    test_args = ["formatter.py", str(input_file), "-o", str(output_file), "--compact"]
    monkeypatch.setattr(sys, "argv", test_args)

    main()

    # Should be compact (no newlines except at end)
    content = output_file.read_text().strip()
    assert content.count("\n") == 0


def test_json_formatter_main_file_not_found(tmp_path, monkeypatch):
    """Test main() with non-existent file."""
    from cicada.formatter import main
    import sys
    import pytest

    nonexistent = tmp_path / "nonexistent.json"

    test_args = ["formatter.py", str(nonexistent)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_json_formatter_main_invalid_json(tmp_path, monkeypatch):
    """Test main() with invalid JSON file."""
    from cicada.formatter import main
    import sys
    import pytest

    input_file = tmp_path / "invalid.json"
    input_file.write_text("{invalid json}")

    test_args = ["formatter.py", str(input_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_json_formatter_main_unexpected_error(tmp_path, monkeypatch):
    """Test main() with unexpected error (mocked)."""
    from cicada.formatter import main, JSONFormatter
    import sys
    import pytest

    input_file = tmp_path / "test.json"
    input_file.write_text('{"key":"value"}')

    test_args = ["formatter.py", str(input_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    # Mock format_file to raise an unexpected exception
    def mock_format_file(*args, **kwargs):
        raise RuntimeError("Unexpected error!")

    monkeypatch.setattr(JSONFormatter, "format_file", mock_format_file)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_format_module_markdown_long_moduledoc_truncation():
    """Test that long moduledoc gets truncated at 200 chars."""
    long_doc = "A" * 300
    data = {"file": "lib/test.ex", "line": 1, "functions": [], "moduledoc": long_doc}

    result = ModuleFormatter.format_module_markdown("TestModule", data)

    # Should truncate at 200 chars with ellipsis
    assert ("A" * 200 + "...") in result
    # Should NOT contain all 300 As
    assert ("A" * 300) not in result


def test_format_error_json_basic():
    """Test format_error_json method."""
    result = ModuleFormatter.format_error_json("MyApp.Missing", 100)
    parsed = json.loads(result)

    assert parsed["error"] == "Module not found"
    assert parsed["query"] == "MyApp.Missing"
    assert parsed["hint"] == "Use the exact module name as it appears in the code"
    assert parsed["total_modules_available"] == 100


# Complex call site formatting tests removed - those code paths are tested by integration tests


def test_format_module_usage_markdown_with_alias_different_name():
    """Test usage markdown with alias that has different name."""
    usage_results = {
        "aliases": [
            {
                "importing_module": "MyApp.Account",
                "alias_name": "U",  # Different from default "User"
                "file": "lib/account.ex",
            }
        ]
    }

    result = ModuleFormatter.format_module_usage_markdown("MyApp.User", usage_results)
    # Should show the alias name since it's different
    assert "as `U`" in result


def test_format_module_usage_markdown_function_calls_with_alias():
    """Test usage markdown with function calls using aliases."""
    usage_results = {
        "function_calls": [
            {
                "calling_module": "MyApp.Account",
                "file": "lib/account.ex",
                "calls": [
                    {
                        "function": "create",
                        "arity": 1,
                        "lines": [10, 20],
                        "alias_used": "U",
                    }
                ],
            }
        ]
    }

    result = ModuleFormatter.format_module_usage_markdown("MyApp.User", usage_results)
    assert "(via `U`)" in result
