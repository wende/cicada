"""
Tests for string literal extraction from Elixir source code.

Author: Claude Code
"""

import pytest
import tree_sitter_elixir as ts_elixir
from tree_sitter import Language, Parser

from cicada.elixir.extractors import StringExtractor, extract_modules


@pytest.fixture
def parser():
    """Create an Elixir parser instance."""
    return Parser(Language(ts_elixir.language()))


@pytest.fixture
def sample_strings_ast(parser):
    """Parse the sample_strings.ex fixture file."""
    with open("tests/fixtures/sample_strings.ex", "rb") as f:
        source_code = f.read()

    tree = parser.parse(source_code)
    return tree.root_node, source_code


def test_string_extractor_initialization():
    """Test StringExtractor initialization with different min_length values."""
    extractor = StringExtractor()
    assert extractor.min_length == 3

    extractor_custom = StringExtractor(min_length=5)
    assert extractor_custom.min_length == 5


def test_extracts_basic_strings(sample_strings_ast):
    """Test that basic strings in function bodies are extracted."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    assert len(modules) == 1

    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # Should extract strings from function bodies
    assert len(strings) > 0

    # Check for specific expected strings
    extracted_content = [s["string"] for s in strings]

    assert "This string SHOULD be extracted" in extracted_content
    assert "SELECT * FROM users WHERE active = true" in extracted_content
    assert "User not found in the database" in extracted_content


def test_skips_documentation_strings(sample_strings_ast):
    """Test that @moduledoc and @doc strings are NOT extracted."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    extracted_content = [s["string"] for s in strings]

    # These doc strings should NOT be extracted
    assert "Test module for string extraction." not in extracted_content
    assert "This documentation should NOT be extracted as a string." not in extracted_content
    assert "Function documentation should also be skipped." not in extracted_content


def test_skips_short_strings(sample_strings_ast):
    """Test that strings shorter than min_length are filtered out."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings with default min_length=3
    extractor = StringExtractor(min_length=3)
    strings = extractor.extract_from_module(do_block, source_code)

    extracted_content = [s["string"] for s in strings]

    # These short strings should be SKIPPED
    assert "a" not in extracted_content
    assert "" not in extracted_content
    assert "No" not in extracted_content

    # This one should be extracted (exactly 3 chars)
    assert "Yes" in extracted_content


def test_includes_module_and_atom_strings(sample_strings_ast):
    """Test that module names and atom-like strings ARE extracted."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    extracted_content = [s["string"] for s in strings]

    # These should ALL be extracted (no atom-like filtering)
    assert "Elixir.MyModule" in extracted_content
    assert ":ok" in extracted_content
    assert ":error" in extracted_content
    assert "ERROR" in extracted_content
    assert "SUCCESS" in extracted_content
    assert "Error message" in extracted_content


def test_tracks_function_context(sample_strings_ast):
    """Test that strings are associated with their containing function."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # Find strings from specific functions
    query_strings = [s for s in strings if s["function"] == "query_function"]
    error_strings = [s for s in strings if s["function"] == "error_messages"]

    # Verify context is tracked correctly
    assert len(query_strings) > 0
    assert any("SELECT" in s["string"] for s in query_strings)

    assert len(error_strings) > 0
    assert any("User not found" in s["string"] for s in error_strings)


def test_extracts_from_private_functions(sample_strings_ast):
    """Test that strings from private functions (defp) are also extracted."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # Find strings from private function
    private_strings = [s for s in strings if s["function"] == "private_function"]

    assert len(private_strings) > 0
    assert any("private function" in s["string"] for s in private_strings)


def test_extracts_multiline_strings(sample_strings_ast):
    """Test that multiline strings are extracted."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    extracted_content = [s["string"] for s in strings]

    # Should extract multiline string (check for part of it)
    assert any("multiline string" in s for s in extracted_content)


def test_extracts_strings_from_nested_structures(sample_strings_ast):
    """Test that strings in maps, lists, and tuples are extracted."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    extracted_content = [s["string"] for s in strings]

    # Strings from nested structures should be extracted
    assert "This is a map value" in extracted_content
    assert "Something went wrong" in extracted_content
    assert "First item in list" in extracted_content
    assert "Second item in list" in extracted_content
    assert "Tuple string one" in extracted_content
    assert "Tuple string two" in extracted_content


def test_line_numbers_are_correct(sample_strings_ast):
    """Test that line numbers are correctly tracked for each string."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # All strings should have valid line numbers
    for string in strings:
        assert "line" in string
        assert string["line"] > 0
        assert isinstance(string["line"], int)


def test_function_with_guards(sample_strings_ast):
    """Test that strings from functions with guards are extracted correctly."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # Find strings from guarded function
    guarded_strings = [s for s in strings if s["function"] == "function_with_guard"]

    assert len(guarded_strings) > 0
    assert any("Integer value received" in s["string"] for s in guarded_strings)


def test_custom_min_length(sample_strings_ast):
    """Test that custom min_length parameter works correctly."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract with min_length=10
    extractor = StringExtractor(min_length=10)
    strings = extractor.extract_from_module(do_block, source_code)

    # All extracted strings should be >= 10 characters
    for string in strings:
        assert len(string["string"]) >= 10

    # "Yes" (3 chars) should not be extracted
    extracted_content = [s["string"] for s in strings]
    assert "Yes" not in extracted_content


def test_empty_module():
    """Test extraction from an empty module."""
    source_code = b"""
    defmodule EmptyModule do
    end
    """

    parser = Parser(Language(ts_elixir.language()))
    tree = parser.parse(source_code)
    root_node = tree.root_node

    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # Should return empty list
    assert strings == []


def test_spec_attribute_does_not_interfere(sample_strings_ast):
    """Test that @spec attributes don't interfere with string extraction."""
    root_node, source_code = sample_strings_ast

    # Get the module node
    modules = extract_modules(root_node, source_code)
    module = modules[0]
    do_block = module["do_block"]

    # Extract strings
    extractor = StringExtractor()
    strings = extractor.extract_from_module(do_block, source_code)

    # Find strings from typed_function (which has @spec)
    typed_strings = [s for s in strings if s["function"] == "typed_function"]

    assert len(typed_strings) > 0
    assert any("Processing input string" in s["string"] for s in typed_strings)
