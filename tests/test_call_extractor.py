"""
Tests for cicada/extractors/call.py - function call extraction
"""

import pytest
import tree_sitter_elixir
from tree_sitter import Language, Parser

from cicada.extractors.call import extract_function_calls


class TestExtractFunctionCalls:
    """Tests for extract_function_calls function"""

    @pytest.fixture
    def parser(self):
        """Create a tree-sitter parser for Elixir"""
        parser = Parser()
        parser.language = Language(tree_sitter_elixir.language())
        return parser

    def test_excludes_module_attributes_from_calls(self, parser):
        """
        Test that module attributes (@moduledoc, @doc, @spec) are NOT
        extracted as function calls.

        This test documents the bug where @spec, @doc, and @moduledoc
        are incorrectly classified as function calls.
        """
        code = """
defmodule TestModule do
  @moduledoc "Module documentation"

  @doc "Function documentation"
  @spec add(integer(), integer()) :: integer()
  def add(x, y) do
    x + y
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        calls = extract_function_calls(tree.root_node, source_bytes)

        # Extract just the function names from calls
        call_functions = [call["function"] for call in calls]

        # These should NOT be in the calls list - they are attributes, not calls
        assert "moduledoc" not in call_functions, "@moduledoc is an attribute, not a function call"
        assert "doc" not in call_functions, "@doc is an attribute, not a function call"
        assert "spec" not in call_functions, "@spec is an attribute, not a function call"

        # Type references in specs should also not be treated as calls
        assert (
            "integer" not in call_functions
        ), "integer() in @spec is a type reference, not a function call"

    def test_extracts_actual_function_calls(self, parser):
        """Test that actual function calls ARE correctly extracted"""
        code = """
defmodule TestModule do
  def process(data) do
    validate(data)
    transform(data)
    IO.puts("Done")
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        calls = extract_function_calls(tree.root_node, source_bytes)

        # Extract function names
        call_functions = [call["function"] for call in calls]

        # These SHOULD be in the calls list - they are actual function calls
        assert "validate" in call_functions
        assert "transform" in call_functions
        assert "puts" in call_functions

    def test_spec_with_complex_types(self, parser):
        """
        Test that complex type specs with multiple type references
        are not extracted as function calls.
        """
        code = """
defmodule Benchmark do
  @spec run_benchmark_test(
          module(),
          atom(),
          module(),
          atom(),
          pos_integer(),
          pos_integer(),
          keyword()
        ) :: :ok
  def run_benchmark_test(mod1, fun1, mod2, fun2, runs, iterations, opts) do
    # actual implementation
    :ok
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        calls = extract_function_calls(tree.root_node, source_bytes)

        # Extract function names
        call_functions = [call["function"] for call in calls]

        # None of these type references should be in calls
        assert "spec" not in call_functions
        assert "module" not in call_functions
        assert "atom" not in call_functions
        assert "pos_integer" not in call_functions
        assert "keyword" not in call_functions

        # The actual function name from the spec should also not be a "call"
        # (it's a type signature, not a call)
        assert "run_benchmark_test" not in call_functions or (
            # If it IS in there, it better be from the actual def, not the @spec
            len([c for c in calls if c["function"] == "run_benchmark_test"])
            == 0
        )

    def test_distinguishes_attributes_from_local_functions(self, parser):
        """
        Test that we can distinguish between @doc as an attribute
        and a hypothetical doc() function call.
        """
        code = """
defmodule TestModule do
  @doc "This is an attribute"
  def example do
    doc()  # This IS a function call (hypothetical)
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        calls = extract_function_calls(tree.root_node, source_bytes)

        # Count how many times "doc" appears
        doc_calls = [c for c in calls if c["function"] == "doc"]

        # Should only be 1 (the actual call inside the function body)
        # NOT 2 (which would include the @doc attribute)
        assert len(doc_calls) == 1, (
            f"Expected 1 'doc' call, but found {len(doc_calls)}. "
            f"The @doc attribute should not be counted as a call."
        )

    def test_typespec_returns_not_extracted(self, parser):
        """Test that return type specifications are not extracted as calls"""
        code = """
defmodule Types do
  @spec get_user(integer()) :: {:ok, User.t()} | {:error, String.t()}
  def get_user(id) do
    # implementation
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        calls = extract_function_calls(tree.root_node, source_bytes)
        call_functions = [call["function"] for call in calls]

        # Return type references should not be calls
        assert "t" not in call_functions
        assert "get_user" not in call_functions  # The spec signature itself
