"""Tests for cicada/elixir/extractors/doc.py"""

import pytest

from cicada.elixir.extractors.doc import (
    _extract_examples_from_doc,
    match_docs_to_functions,
)


class TestExtractExamplesFromDoc:
    """Test _extract_examples_from_doc function."""

    def test_doc_without_examples_returns_none(self):
        """Test doc without examples section returns (doc, None)."""
        doc_text = "This is simple documentation without examples."

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert doc_without_examples == "This is simple documentation without examples."
        assert examples is None

    def test_doc_with_examples_heading_splits_correctly(self):
        """Test doc with ## Examples heading is split correctly."""
        doc_text = """
This is documentation.

## Examples

    iex> my_func()
    :ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert "This is documentation." in doc_without_examples
        assert "## Examples" not in doc_without_examples
        assert examples is not None
        assert "iex> my_func()" in examples
        assert ":ok" in examples

    def test_doc_with_single_hash_examples(self):
        """Test doc with # Examples (single hash)."""
        doc_text = """
This is documentation.

# Examples

    iex> my_func()
    :ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert "This is documentation." in doc_without_examples
        assert examples is not None
        assert "iex> my_func()" in examples

    def test_examples_section_case_insensitive(self):
        """Test Examples heading is case-insensitive."""
        doc_text = """
This is documentation.

## EXAMPLES

    iex> my_func()
    :ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert examples is not None
        assert "iex> my_func()" in examples

    def test_examples_stops_at_next_heading(self):
        """Test examples section stops at next ## heading."""
        doc_text = """
This is documentation.

## Examples

    iex> my_func()
    :ok

## Returns

Returns a value.
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert "This is documentation." in doc_without_examples
        assert "Returns a value." in doc_without_examples
        assert examples is not None
        assert "iex> my_func()" in examples
        assert "Returns a value" not in examples

    def test_examples_with_no_content_returns_none(self):
        """Test examples section with no content returns None."""
        doc_text = """
This is documentation.

## Examples
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert "This is documentation." in doc_without_examples
        assert examples is None

    def test_examples_with_only_whitespace_returns_none(self):
        """Test examples section with only whitespace returns None."""
        doc_text = """
This is documentation.

## Examples



"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert "This is documentation." in doc_without_examples
        # Examples should be None or empty after stripping
        assert examples is None or examples.strip() == ""

    def test_examples_dedents_correctly(self):
        """Test examples content is dedented correctly."""
        doc_text = """
This is documentation.

## Examples

    iex> my_func()
    :ok

    iex> another()
    :also_ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert examples is not None
        # Verify exact dedented output with preserved structure (empty lines)
        expected_examples = "iex> my_func()\n:ok\n\niex> another()\n:also_ok"
        assert examples == expected_examples

    def test_doc_dedents_text_outside_examples(self):
        """Test doc text is dedented using textwrap.dedent."""
        doc_text = """
    This is indented documentation.

    ## Examples

        iex> my_func()
        :ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        # Doc should be dedented
        assert doc_without_examples.startswith("This is indented")
        assert not doc_without_examples.startswith("    ")

    def test_preserves_empty_lines_in_examples(self):
        """Test empty lines are preserved in examples."""
        doc_text = """
Documentation.

## Examples

    iex> func1()
    :ok

    iex> func2()
    :ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert examples is not None
        # Should preserve the empty line between examples
        lines = examples.split("\n")
        assert any(line.strip() == "" for line in lines)

    def test_handles_examples_at_end_of_doc(self):
        """Test examples section at the end of doc (no following sections)."""
        doc_text = """
This is documentation.

## Examples

    iex> my_func()
    :ok
"""

        doc_without_examples, examples = _extract_examples_from_doc(doc_text)

        assert "This is documentation." in doc_without_examples
        assert examples is not None
        assert "iex> my_func()" in examples


class TestMatchDocsToFunctions:
    """Test match_docs_to_functions function."""

    def test_matches_doc_to_function_directly_above(self):
        """Test matching @doc to function directly above it."""
        functions = [{"line": 10, "name": "my_func"}]
        docs = {9: {"text": "Function documentation", "line": 9}}

        match_docs_to_functions(functions, docs)

        assert functions[0]["doc"] == "Function documentation"

    def test_matches_doc_with_spec_between(self):
        """Test matching @doc to function with @spec in between."""
        functions = [{"line": 12, "name": "my_func"}]
        docs = {9: {"text": "Function documentation", "line": 9}}

        match_docs_to_functions(functions, docs)

        assert functions[0]["doc"] == "Function documentation"

    def test_matches_doc_with_examples(self):
        """Test matching @doc with examples field."""
        functions = [{"line": 10, "name": "my_func"}]
        docs = {
            9: {
                "text": "Function documentation",
                "examples": "iex> my_func()\n:ok",
                "line": 9,
            }
        }

        match_docs_to_functions(functions, docs)

        assert functions[0]["doc"] == "Function documentation"
        assert functions[0]["examples"] == "iex> my_func()\n:ok"

    def test_does_not_match_doc_too_far_away(self):
        """Test doc more than 50 lines away is not matched."""
        functions = [{"line": 100, "name": "my_func"}]
        docs = {10: {"text": "Function documentation", "line": 10}}

        match_docs_to_functions(functions, docs)

        # Doc is 90 lines away, should not match (limit is 50)
        assert "doc" not in functions[0]

    def test_matches_multiple_functions(self):
        """Test matching docs to multiple functions."""
        functions = [
            {"line": 10, "name": "func1"},
            {"line": 20, "name": "func2"},
        ]
        docs = {
            9: {"text": "First doc", "line": 9},
            19: {"text": "Second doc", "line": 19},
        }

        match_docs_to_functions(functions, docs)

        assert functions[0]["doc"] == "First doc"
        assert functions[1]["doc"] == "Second doc"

    def test_backward_compatibility_with_string_docs(self):
        """Test backward compatibility when docs are strings instead of dicts."""
        functions = [{"line": 10, "name": "my_func"}]
        docs = {9: "Function documentation"}  # Old format: string instead of dict

        match_docs_to_functions(functions, docs)

        assert functions[0]["doc"] == "Function documentation"

    def test_no_match_when_no_docs(self):
        """Test functions without matching docs remain unchanged."""
        functions = [{"line": 10, "name": "my_func"}]
        docs = {}

        match_docs_to_functions(functions, docs)

        assert "doc" not in functions[0]

    def test_matches_closest_doc(self):
        """Test matches the closest @doc when multiple are in range."""
        functions = [{"line": 15, "name": "my_func"}]
        docs = {
            5: {"text": "Far doc", "line": 5},
            14: {"text": "Close doc", "line": 14},
        }

        match_docs_to_functions(functions, docs)

        # Should match the closest doc (line 14)
        assert functions[0]["doc"] == "Close doc"
