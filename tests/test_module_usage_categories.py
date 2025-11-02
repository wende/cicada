"""
Test module usage categories: aliases, imports, requires, uses, and value mentions.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.format import ModuleFormatter
from cicada.parser import ElixirParser


def test_parser_extracts_all_categories():
    """Test that the parser extracts all usage categories."""
    parser = ElixirParser()

    # Parse the AB module which has examples of all categories
    test_file = Path(__file__).parent / "fixtures" / "test_module_with_usage_categories.ex"
    modules = parser.parse_file(str(test_file))

    assert modules is not None
    assert len(modules) == 1

    module = modules[0]

    # Check that all new fields are present
    assert "aliases" in module
    assert "imports" in module
    assert "requires" in module
    assert "uses" in module
    assert "value_mentions" in module

    # Verify aliases (AB has a multi-line alias block)
    assert isinstance(module["aliases"], dict)
    assert "TypeParser" in module["aliases"]
    assert module["aliases"]["TypeParser"] == "AB.TypeParser"
    assert "Generators" in module["aliases"]
    assert module["aliases"]["Generators"] == "AB.Generators"

    # Verify imports (AB imports ExUnit.Assertions)
    assert isinstance(module["imports"], list)
    assert "ExUnit.Assertions" in module["imports"]

    # Verify uses (AB uses ExUnitProperties)
    assert isinstance(module["uses"], list)
    assert "ExUnitProperties" in module["uses"]

    # Verify requires (AB doesn't have any requires, should be empty)
    assert isinstance(module["requires"], list)
    assert len(module["requires"]) == 0

    # Verify value mentions (AB uses TypeParser as a value)
    assert isinstance(module["value_mentions"], list)
    # TypeParser is mentioned as a value in defdelegate

    print("✓ Parser correctly extracts all usage categories")


def test_formatter_displays_categories():
    """Test that the formatter displays all categories correctly."""
    # Create sample usage results
    usage_results = {
        "aliases": [
            {
                "importing_module": "TestModule",
                "alias_name": "TP",
                "full_module": "AB.TypeParser",
                "file": "test/test_file.ex",
            }
        ],
        "imports": [
            {
                "importing_module": "AnotherModule",
                "file": "lib/another.ex",
            }
        ],
        "requires": [
            {
                "importing_module": "RequiringModule",
                "file": "lib/requiring.ex",
            }
        ],
        "uses": [
            {
                "importing_module": "UsingModule",
                "file": "lib/using.ex",
            }
        ],
        "value_mentions": [
            {
                "importing_module": "MentioningModule",
                "file": "lib/mentioning.ex",
            }
        ],
        "function_calls": [],
    }

    # Format as markdown
    result = ModuleFormatter.format_module_usage_markdown("AB.TypeParser", usage_results)

    # Verify all sections are present
    assert "# Usage of `AB.TypeParser`" in result
    assert "## Aliases (1 module(s)):" in result
    assert "## Imports (1 module(s)):" in result
    assert "## Requires (1 module(s)):" in result
    assert "## Uses (1 module(s)):" in result
    assert "## As Value (1 module(s)):" in result

    # Verify module names are in the output
    assert "TestModule" in result
    assert "AnotherModule" in result
    assert "RequiringModule" in result
    assert "UsingModule" in result
    assert "MentioningModule" in result

    # Verify alias information
    assert "as `TP`" in result

    print("✓ Formatter correctly displays all usage categories")


def test_formatter_json_output():
    """Test that the JSON formatter includes all categories."""
    usage_results = {
        "aliases": [
            {
                "importing_module": "Mod1",
                "alias_name": "A",
                "full_module": "Test",
                "file": "f1.ex",
            }
        ],
        "imports": [{"importing_module": "Mod2", "file": "f2.ex"}],
        "requires": [{"importing_module": "Mod3", "file": "f3.ex"}],
        "uses": [{"importing_module": "Mod4", "file": "f4.ex"}],
        "value_mentions": [{"importing_module": "Mod5", "file": "f5.ex"}],
        "function_calls": [],
    }

    result = ModuleFormatter.format_module_usage_json("TestModule", usage_results)
    parsed = json.loads(result)

    # Verify all categories are in the JSON output
    assert "aliases" in parsed
    assert "imports" in parsed
    assert "requires" in parsed
    assert "uses" in parsed
    assert "value_mentions" in parsed
    assert "function_calls" in parsed

    # Verify summary includes all counts
    assert "summary" in parsed
    assert parsed["summary"]["aliased_by"] == 1
    assert parsed["summary"]["imported_by"] == 1
    assert parsed["summary"]["required_by"] == 1
    assert parsed["summary"]["used_by"] == 1
    assert parsed["summary"]["mentioned_as_value_by"] == 1
    assert parsed["summary"]["called_by"] == 0

    print("✓ JSON formatter correctly includes all usage categories")


def test_empty_categories_not_shown():
    """Test that empty categories are not shown in markdown output."""
    usage_results = {
        "aliases": [],
        "imports": [],
        "requires": [],
        "uses": [],
        "value_mentions": [],
        "function_calls": [],
    }

    result = ModuleFormatter.format_module_usage_markdown("EmptyModule", usage_results)

    # Should not have any category headers
    assert "## Aliases" not in result
    assert "## Imports" not in result
    assert "## Requires" not in result
    assert "## Uses" not in result
    assert "## As Value" not in result

    # Should show "no usage found" message
    assert "*No usage found for this module*" in result

    print("✓ Empty categories are correctly hidden")


if __name__ == "__main__":
    print("Running module usage categories tests...\n")

    try:
        test_parser_extracts_all_categories()
        test_formatter_displays_categories()
        test_formatter_json_output()
        test_empty_categories_not_shown()

        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
