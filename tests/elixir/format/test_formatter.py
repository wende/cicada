#!/usr/bin/env python
"""
Tests for the formatter module, including call site consolidation.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.format import ModuleFormatter


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

    markdown = ModuleFormatter.format_function_results_markdown("target_function", results)

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

    markdown = ModuleFormatter.format_function_results_markdown("target_function", results)

    # Should have consolidated header
    assert (
        "MyApp.Caller.process/1 at lib/my_app/caller.ex:10, :20" in markdown
    ), "Expected consolidated call sites header in markdown output"

    # Should have both code examples
    assert ":10" in markdown and ":20" in markdown, "Expected both line numbers in output"
    assert "TargetModule.target_function(data)" in markdown, "Expected first code example"
    assert "TargetModule.target_function(other_data)" in markdown, "Expected second code example"


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

    markdown = ModuleFormatter.format_function_results_markdown("target_function", results)

    # Should have Usage Examples section with the first 2
    assert "Usage Examples:" in markdown, "Expected Usage Examples section"
    assert "TargetModule.target_function(data1)" in markdown, "Expected first code example"
    assert "TargetModule.target_function(data2)" in markdown, "Expected second code example"

    # Should have Other Call Sites section with the remaining 3
    assert "Other Call Sites:" in markdown, "Expected Other Call Sites section"
    assert "MyApp.Caller3.execute/0" in markdown, "Expected Caller3 in other call sites"
    assert "MyApp.Caller4.run/1" in markdown, "Expected Caller4 in other call sites"
    assert "MyApp.TestCaller.test_function/1" in markdown, "Expected TestCaller in other call sites"

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
    """Test formatting module with type='private'."""
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

    result = ModuleFormatter.format_module_markdown("TestModule", data, visibility="private")

    # Should show only private functions
    assert "private_func" in result
    assert "public_func" not in result
    assert "Private:" in result


def test_format_module_markdown_with_private_functions_include():
    """Test formatting module with type='all'."""
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

    result = ModuleFormatter.format_module_markdown("TestModule", data, visibility="all")

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

    # Should show 0 counts instead of "*No functions found*"
    assert "0 public • 0 private" in result
    assert "*No functions found*" not in result


def test_format_module_markdown_no_private_when_only_requested():
    """Test formatting when only private requested but none exist."""
    data = {
        "file": "lib/test.ex",
        "line": 1,
        "functions": [{"name": "public_func", "arity": 0, "type": "def", "line": 10, "args": []}],
        "public_functions": 1,
        "private_functions": 0,
    }

    result = ModuleFormatter.format_module_markdown("TestModule", data, visibility="private")

    assert "*No private functions found*" in result


def test_format_module_json_with_private_only():
    """Test JSON formatting with type='private'."""
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

    result = ModuleFormatter.format_module_json("TestModule", data, visibility="private")
    parsed = json.loads(result)

    # Should only have private function
    assert len(parsed["functions"]) == 1
    assert parsed["functions"][0]["type"] == "defp"


def test_format_module_json_with_private_include():
    """Test JSON formatting with type='all'."""
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

    result = ModuleFormatter.format_module_json("TestModule", data, visibility="all")
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

    markdown = ModuleFormatter.format_function_results_markdown(
        "example_func", results, format_opts={"include_docs": True}
    )

    # Should include examples (when include_docs=True)
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
    from cicada.format import JSONFormatter

    formatter = JSONFormatter(indent=2)
    input_json = '{"key":"value","nested":{"a":1}}'

    result = formatter.format_string(input_json)

    # Should be formatted
    assert "\n" in result
    assert '"key": "value"' in result or '"key":"value"' in result


def test_json_formatter_format_string_invalid():
    """Test JSONFormatter with invalid JSON."""
    import pytest

    from cicada.format import JSONFormatter

    formatter = JSONFormatter()

    with pytest.raises(ValueError, match="Invalid JSON"):
        formatter.format_string("{invalid json")


def test_json_formatter_format_dict():
    """Test JSONFormatter format_dict method."""
    from cicada.format import JSONFormatter

    formatter = JSONFormatter(indent=4, sort_keys=True)
    data = {"z": 1, "a": 2, "m": 3}

    result = formatter.format_dict(data)

    # Should be formatted with 4 spaces and sorted
    assert "\n" in result
    parsed = json.loads(result)
    assert list(parsed.keys()) == ["a", "m", "z"] if formatter.sort_keys else list(data.keys())


def test_json_formatter_format_file(tmp_path):
    """Test JSONFormatter format_file method."""
    from cicada.format import JSONFormatter

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
    import pytest

    from cicada.format import JSONFormatter

    formatter = JSONFormatter()
    nonexistent = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        formatter.format_file(nonexistent)


def test_json_formatter_format_file_with_output(tmp_path):
    """Test JSONFormatter writing to output file."""
    from cicada.format import JSONFormatter

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
    import sys

    from cicada.format import main

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
    import sys

    from cicada.format import main

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
    import sys

    from cicada.format import main

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
    import sys

    from cicada.format import main

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
    import sys

    from cicada.format import main

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
    import sys

    import pytest

    from cicada.format import main

    nonexistent = tmp_path / "nonexistent.json"

    test_args = ["formatter.py", str(nonexistent)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_json_formatter_main_invalid_json(tmp_path, monkeypatch):
    """Test main() with invalid JSON file."""
    import sys

    import pytest

    from cicada.format import main

    input_file = tmp_path / "invalid.json"
    input_file.write_text("{invalid json}")

    test_args = ["formatter.py", str(input_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_json_formatter_main_unexpected_error(tmp_path, monkeypatch):
    """Test main() with unexpected error (mocked)."""
    import sys

    import pytest

    from cicada.format import JSONFormatter, main

    input_file = tmp_path / "test.json"
    input_file.write_text('{"key":"value"}')

    test_args = ["formatter.py", str(input_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    # Mock format_file to raise an unexpected exception
    def mock_format_file(*_args, **_kwargs):
        raise RuntimeError("Unexpected error!")

    monkeypatch.setattr(JSONFormatter, "format_file", mock_format_file)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_format_module_markdown_long_moduledoc_truncation():
    """Test that long moduledoc gets truncated at 200 chars when enabled."""
    long_doc = "A" * 300
    data = {"file": "lib/test.ex", "line": 1, "functions": [], "moduledoc": long_doc}

    # Moduledoc is hidden by default, need to enable it
    result = ModuleFormatter.format_module_markdown(
        "TestModule", data, format_opts={"include_moduledoc": True}
    )

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
                        "called_function": "create",
                        "called_arity": 1,
                        "calling_function": {
                            "name": "setup",
                            "arity": 0,
                            "start_line": 5,
                            "end_line": 25,
                        },
                        "lines": [10, 20],
                        "alias_used": "U",
                    }
                ],
            }
        ]
    }

    result = ModuleFormatter.format_module_usage_markdown("MyApp.User", usage_results)
    # Should show the called function at top level
    assert "create/1" in result
    # Should show total calls
    assert "2 calls" in result


def test_format_module_compact():
    """Test compact module format for lists."""
    data = {
        "file": "lib/litmus/try_catch.ex",
        "line": 1,
        "public_functions": 1,
        "private_functions": 14,
        "functions": [
            {"name": "func1", "arity": 1, "type": "def", "line": 10, "args": []},
            {"name": "func2", "arity": 0, "type": "defp", "line": 20, "args": []},
            {"name": "func3", "arity": 1, "type": "defp", "line": 30, "args": []},
        ],
    }

    result = ModuleFormatter.format_module_compact("Litmus.TryCatch", data)

    # Should show file path without line number
    assert "lib/litmus/try_catch.ex" in result
    # Should show module name with dash separators and counts
    assert "Litmus.TryCatch - " in result
    assert " public - " in result
    assert " private" in result
    # Should NOT contain colon (no line number)
    assert ":1" not in result
    # Should be compact (2 lines)
    lines = result.split("\n")
    assert len(lines) == 2


def test_format_function_results_markdown_with_string_sources():
    """Test markdown formatting handles string_sources field."""
    results = [
        {
            "module": "MyApp.SQL",
            "function": {
                "name": "query",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["sql"],
            },
            "file": "lib/sql.ex",
            "call_sites": [],
            "string_sources": [
                {"string": "SELECT * FROM users", "line": 12},
                {"string": "WHERE active = true", "line": 13},
            ],
        }
    ]
    markdown = ModuleFormatter.format_function_results_markdown("query", results)
    # Should not crash when string_sources is present
    assert "MyApp.SQL.query/1" in markdown


def test_format_function_results_markdown_with_match_source_indicators():
    """Test markdown formatting handles match_sources field."""
    results = [
        {
            "module": "MyApp.SQL",
            "function": {
                "name": "query",
                "arity": 1,
                "type": "def",
                "line": 10,
                "args": ["sql"],
            },
            "file": "lib/sql.ex",
            "call_sites": [],
            "matched_keywords": ["select"],
            "match_sources": {"select": "strings"},
        }
    ]
    markdown = ModuleFormatter.format_function_results_markdown("query", results)
    # Should not crash when match_sources is present
    assert "MyApp.SQL.query/1" in markdown


# ===== Co-change formatting tests =====


def test_format_module_markdown_with_cochange_files():
    """Test that cochange_files are displayed in module markdown."""
    data = {
        "file": "lib/auth.ex",
        "line": 1,
        "functions": [
            {
                "name": "authenticate",
                "arity": 2,
                "type": "def",
                "line": 5,
                "args": ["user", "pass"],
            },
        ],
        "cochange_files": [
            {"file": "lib/credentials.ex", "module": "Credentials", "count": 10},
            {"file": "lib/logger.ex", "module": "Logger", "count": 5},
        ],
    }
    markdown = ModuleFormatter.format_module_markdown("Auth", data)

    # Should include the "Often Changed With" section
    assert "Often Changed With" in markdown
    assert "Credentials (10 commits)" in markdown
    assert "Logger (5 commits)" in markdown


def test_format_module_markdown_with_cochange_files_truncation():
    """Test that cochange_files are truncated to top 3 for compactness."""
    data = {
        "file": "lib/auth.ex",
        "line": 1,
        "functions": [],
        "cochange_files": [
            {"file": f"lib/module{i}.ex", "module": f"Module{i}", "count": 10 - i}
            for i in range(1, 9)  # 8 modules
        ],
    }
    markdown = ModuleFormatter.format_module_markdown("Auth", data)

    # Should show top 3
    assert "Module1" in markdown
    assert "Module2" in markdown
    assert "Module3" in markdown
    # Module4 should NOT be in output (limited to 3)
    assert "Module4" not in markdown
    # Should show truncation message
    assert "... and 5 more" in markdown


def test_format_module_markdown_with_cochange_files_uses_filename_fallback():
    """Test that cochange_files use filename when module is not present."""
    data = {
        "file": "lib/auth.ex",
        "line": 1,
        "functions": [],
        "cochange_files": [
            {"file": "lib/some_module.ex", "count": 5},  # No module key
        ],
    }
    markdown = ModuleFormatter.format_module_markdown("Auth", data)

    # Should use filename
    assert "some_module.ex (5 commits)" in markdown


def test_format_module_markdown_without_cochange_files():
    """Test that module markdown works when cochange_files is empty or missing."""
    data = {
        "file": "lib/auth.ex",
        "line": 1,
        "functions": [],
    }
    markdown = ModuleFormatter.format_module_markdown("Auth", data)

    # Should not include co-change section
    assert "Often Changed With" not in markdown


def test_format_cochange_info_with_related_files():
    """Test _format_cochange_info with related_files."""
    cochange_info = {
        "related_files": [
            {"file": "lib/credentials.ex", "module": "Credentials", "count": 10},
            {"file": "lib/logger.ex", "module": "Logger", "count": 5},
        ]
    }
    lines = ModuleFormatter._format_cochange_info(cochange_info)

    assert any("Often changed with" in line for line in lines)
    assert any("Credentials" in line and "10" in line for line in lines)
    assert any("Logger" in line and "5" in line for line in lines)


def test_format_cochange_info_with_related_functions():
    """Test _format_cochange_info with related_functions."""
    cochange_info = {
        "related_functions": [
            {"module": "Credentials", "function": "validate", "arity": 2, "count": 8},
            {"module": "Logger", "function": "log", "arity": 1, "count": 3},
        ]
    }
    lines = ModuleFormatter._format_cochange_info(cochange_info)

    assert any("Related functions" in line for line in lines)
    assert any("Credentials.validate/2" in line and "8" in line for line in lines)
    assert any("Logger.log/1" in line and "3" in line for line in lines)


def test_format_cochange_info_with_both_files_and_functions():
    """Test _format_cochange_info with both related_files and related_functions."""
    cochange_info = {
        "related_files": [
            {"file": "lib/credentials.ex", "module": "Credentials", "count": 10},
        ],
        "related_functions": [
            {"module": "Logger", "function": "log", "arity": 1, "count": 3},
        ],
    }
    lines = ModuleFormatter._format_cochange_info(cochange_info)

    # Both sections should be present
    assert any("Often changed with" in line for line in lines)
    assert any("Related functions" in line for line in lines)


def test_format_cochange_info_empty():
    """Test _format_cochange_info with empty data."""
    cochange_info = {}
    lines = ModuleFormatter._format_cochange_info(cochange_info)

    # Should return empty list
    assert lines == []


def test_format_cochange_info_uses_filename_when_no_module():
    """Test _format_cochange_info uses filename when module is missing."""
    cochange_info = {
        "related_files": [
            {"file": "lib/some_file.ex", "count": 5},  # No module key
        ]
    }
    lines = ModuleFormatter._format_cochange_info(cochange_info)

    # Should use the filename (without .ex) as display name
    assert any("some_file" in line for line in lines)


def test_format_related_items_truncation():
    """Test _format_related_items truncates to top_n."""
    items = [{"name": f"item{i}", "count": 10 - i} for i in range(10)]

    def format_item(item: dict) -> tuple[str, int]:
        return item["name"], item["count"]

    lines = ModuleFormatter._format_related_items(items, "Test items:", format_item, top_n=3)

    # Should have header + 3 items + truncation message
    assert any("Test items:" in line for line in lines)
    assert any("item0" in line for line in lines)
    assert any("item2" in line for line in lines)
    assert any("... and 7 more" in line for line in lines)
    # Should NOT have item3 (beyond top_n)
    assert not any("item3" in line for line in lines)


# Tests for fallback note rendering and keyword splitting


def test_split_function_name_to_keywords_snake_case():
    """Test keyword splitting for snake_case function names."""
    keywords = ModuleFormatter._split_function_name_to_keywords("create_user")
    assert keywords == ["create", "user"]


def test_split_function_name_to_keywords_leading_underscore():
    """Test keyword splitting strips leading underscores."""
    keywords = ModuleFormatter._split_function_name_to_keywords("_extract_cochange")
    assert keywords == ["extract", "cochange"]


def test_split_function_name_to_keywords_camel_case():
    """Test keyword splitting for camelCase function names."""
    keywords = ModuleFormatter._split_function_name_to_keywords("getUserData")
    assert keywords == ["get", "user", "data"]


def test_split_function_name_to_keywords_single_word():
    """Test keyword splitting returns single keyword for simple names."""
    keywords = ModuleFormatter._split_function_name_to_keywords("create")
    assert keywords == ["create"]


def test_split_function_name_to_keywords_mixed_case_underscore():
    """Test keyword splitting for mixed naming conventions."""
    keywords = ModuleFormatter._split_function_name_to_keywords("get_UserData")
    assert keywords == ["get", "user", "data"]


def test_fallback_note_rendered_for_single_result():
    """Ensure fallback_note is rendered when there is a single result."""
    results = [
        {
            "module": "MyApp.Module",
            "moduledoc": None,
            "function": {
                "name": "create_user",
                "arity": 1,
                "type": "def",
                "line": 42,
                "doc": "Creates a user.",
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
            "call_sites_with_examples": [],
            "pr_info": None,
            "detailed_dependencies": None,
        }
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "create_user",
        results,
        fallback_note="no matches in `SomeModule`",
    )

    # Fallback note should be rendered with parentheses
    assert "(no matches in `SomeModule`)" in markdown
    # Result should still be rendered
    assert "MyApp.Module.create_user/1" in markdown


def test_fallback_note_rendered_for_multiple_results():
    """Ensure fallback_note is rendered when there are multiple results."""
    results = [
        {
            "module": "MyApp.Module",
            "moduledoc": None,
            "function": {
                "name": "create",
                "arity": 1,
                "type": "def",
                "line": 42,
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
            "call_sites_with_examples": [],
            "pr_info": None,
            "detailed_dependencies": None,
        },
        {
            "module": "OtherApp.Module",
            "moduledoc": None,
            "function": {
                "name": "create",
                "arity": 2,
                "type": "def",
                "line": 10,
            },
            "file": "lib/other_app/module.ex",
            "call_sites": [],
            "call_sites_with_examples": [],
            "pr_info": None,
            "detailed_dependencies": None,
        },
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "create",
        results,
        fallback_note="no matches with arity /3",
    )

    # Fallback note should be in the "Found X match(es)" line with parentheses
    assert "(no matches with arity /3)" in markdown
    assert "Found 2 match(es)" in markdown
    # Both results should be rendered
    assert "MyApp.Module.create/1" in markdown
    assert "OtherApp.Module.create/2" in markdown


def test_query_suggestion_uses_split_keywords():
    """Verify query suggestion uses split keywords in not-found message."""
    markdown = ModuleFormatter.format_function_results_markdown(
        "_extract_cochange",
        [],  # No results
    )

    # Should suggest query with split keywords
    assert "query(['extract', 'cochange'])" in markdown
    assert "Not found" in markdown


def test_query_suggestion_single_keyword():
    """Verify query suggestion works for single-word function names."""
    markdown = ModuleFormatter.format_function_results_markdown(
        "create",
        [],  # No results
    )

    # Should suggest query with single keyword
    assert "query(['create'])" in markdown


def test_fallback_note_not_rendered_when_none():
    """Ensure no fallback note is rendered when None."""
    results = [
        {
            "module": "MyApp.Module",
            "moduledoc": None,
            "function": {
                "name": "create",
                "arity": 1,
                "type": "def",
                "line": 42,
            },
            "file": "lib/my_app/module.ex",
            "call_sites": [],
            "call_sites_with_examples": [],
            "pr_info": None,
            "detailed_dependencies": None,
        },
    ]

    markdown = ModuleFormatter.format_function_results_markdown(
        "create",
        results,
        fallback_note=None,
    )

    # No parentheses should appear for fallback note
    assert "no matches" not in markdown.lower()
    # Result should still be rendered
    assert "MyApp.Module.create/1" in markdown


# Tests for language detection and function name formatting


def test_get_language_from_func_elixir_def():
    """Test that 'def' type is detected as Elixir."""
    func = {"type": "def", "name": "public_func", "arity": 1}
    language = ModuleFormatter._get_language_from_func(func)
    assert language == "elixir"


def test_get_language_from_func_elixir_defp():
    """Test that 'defp' type is detected as Elixir."""
    func = {"type": "defp", "name": "private_func", "arity": 0}
    language = ModuleFormatter._get_language_from_func(func)
    assert language == "elixir"


def test_get_language_from_func_python_public():
    """Test that 'public' type is detected as Python."""
    func = {"type": "public", "name": "method", "arity": 2}
    language = ModuleFormatter._get_language_from_func(func)
    assert language == "python"


def test_get_language_from_func_python_private():
    """Test that 'private' type is detected as Python."""
    func = {"type": "private", "name": "_internal", "arity": 1}
    language = ModuleFormatter._get_language_from_func(func)
    assert language == "python"


def test_get_language_from_func_unknown_defaults_to_python():
    """Test that unknown function type defaults to Python."""
    func = {"type": "unknown_type", "name": "something", "arity": 0}
    language = ModuleFormatter._get_language_from_func(func)
    assert language == "python"


def test_get_language_from_func_missing_type_defaults_to_python():
    """Test that missing type field defaults to Python."""
    func = {"name": "something", "arity": 0}
    language = ModuleFormatter._get_language_from_func(func)
    assert language == "python"


def test_format_function_name_elixir_with_args():
    """Test formatting Elixir function with args shows args."""
    func = {"type": "def", "name": "add", "arity": 2, "args": ["a", "b"]}
    result = ModuleFormatter._format_function_name(func, "add", 2)
    assert result == "add(a, b)"


def test_format_function_name_elixir_without_args():
    """Test formatting Elixir function without args uses arity notation."""
    func = {"type": "def", "name": "process", "arity": 3}
    result = ModuleFormatter._format_function_name(func, "process", 3)
    assert result == "process/3"


def test_format_function_name_python_filters_self():
    """Test formatting Python method filters out self."""
    func = {"type": "public", "name": "method", "arity": 2, "args": ["self", "value"]}
    result = ModuleFormatter._format_function_name(func, "method", 2)
    assert result == "method(value)"


def test_format_function_name_python_without_args():
    """Test formatting Python function without args shows empty parens."""
    func = {"type": "public", "name": "util", "arity": 1}
    result = ModuleFormatter._format_function_name(func, "util", 1)
    assert result == "util()"
