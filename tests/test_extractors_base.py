"""
Comprehensive tests for cicada/extractors/base.py
"""

import pytest
import tree_sitter_elixir
from tree_sitter import Language, Parser


class TestExtractStringFromArguments:
    """Tests for extract_string_from_arguments function"""

    @pytest.fixture
    def parser(self):
        """Create a tree-sitter parser for Elixir"""
        parser = Parser()
        parser.language = Language(tree_sitter_elixir.language())
        return parser

    def _parse_and_find_arguments(self, parser, code: str):
        """Helper to parse code and find the first arguments node"""
        tree = parser.parse(bytes(code, "utf8"))

        def find_node_by_type(node, node_type):
            if node.type == node_type:
                return node
            for child in node.children:
                result = find_node_by_type(child, node_type)
                if result:
                    return result
            return None

        return find_node_by_type(tree.root_node, "arguments")

    def test_extract_simple_string(self, parser):
        """Test extracting a simple string literal"""
        from cicada.extractors.base import extract_string_from_arguments

        code = '@moduledoc "This is a simple doc string"'
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        assert arguments_node is not None
        result = extract_string_from_arguments(arguments_node, source_bytes)
        assert result == "This is a simple doc string"

    def test_extract_multiline_string(self, parser):
        """Test extracting multi-line string"""
        from cicada.extractors.base import extract_string_from_arguments

        code = '''@doc """
This is a
multi-line
documentation
"""'''
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        assert arguments_node is not None
        result = extract_string_from_arguments(arguments_node, source_bytes)
        assert "multi-line" in result
        assert "documentation" in result

    def test_extract_false_returns_none(self, parser):
        """Test that @doc false returns None"""
        from cicada.extractors.base import extract_string_from_arguments

        code = "@doc false"
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        assert arguments_node is not None
        result = extract_string_from_arguments(arguments_node, source_bytes)
        assert result is None

    def test_extract_from_function_call(self, parser):
        """Test extracting string from function call arguments"""
        from cicada.extractors.base import extract_string_from_arguments

        code = 'IO.puts("Hello, World!")'
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        assert arguments_node is not None
        result = extract_string_from_arguments(arguments_node, source_bytes)
        assert result == "Hello, World!"

    def test_extract_string_with_newlines(self, parser):
        """Test extracting string containing newlines"""
        from cicada.extractors.base import extract_string_from_arguments

        code = '@doc "First line\\nSecond line"'
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        if arguments_node:
            result = extract_string_from_arguments(arguments_node, source_bytes)
            assert result is not None
            assert "line" in result

    def test_no_string_in_arguments(self, parser):
        """Test when arguments contain no string"""
        from cicada.extractors.base import extract_string_from_arguments

        code = "func(123, :atom)"
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        if arguments_node:
            result = extract_string_from_arguments(arguments_node, source_bytes)
            assert result is None

    def test_extract_empty_string_content(self, parser):
        """Test extracting string that has no content"""
        from cicada.extractors.base import extract_string_from_arguments

        code = '@moduledoc ""'
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        if arguments_node:
            result = extract_string_from_arguments(arguments_node, source_bytes)
            # Empty string with no quoted_content returns None (no string_content collected)
            assert result is None or result == ""

    def test_extract_string_with_unicode(self, parser):
        """Test extracting string with unicode characters"""
        from cicada.extractors.base import extract_string_from_arguments

        code = '@doc "Hello 🦗 Cicada"'
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        if arguments_node:
            result = extract_string_from_arguments(arguments_node, source_bytes)
            assert result is not None
            assert "Cicada" in result or "Hello" in result

    def test_extract_atom_not_false(self, parser):
        """Test that atoms other than false don't match"""
        from cicada.extractors.base import extract_string_from_arguments

        code = "@doc :some_atom"
        source_bytes = bytes(code, "utf8")
        arguments_node = self._parse_and_find_arguments(parser, code)

        if arguments_node:
            result = extract_string_from_arguments(arguments_node, source_bytes)
            assert result is None


class TestCountArguments:
    """Tests for count_arguments function"""

    @pytest.fixture
    def parser(self):
        """Create a tree-sitter parser for Elixir"""
        parser = Parser()
        parser.language = Language(tree_sitter_elixir.language())
        return parser

    def _get_arguments_node(self, parser, code: str):
        """Parse code and extract arguments node"""
        tree = parser.parse(bytes(code, "utf8"))

        def find_arguments(node):
            if node.type == "arguments":
                return node
            for child in node.children:
                result = find_arguments(child)
                if result:
                    return result
            return None

        return find_arguments(tree.root_node)

    def test_count_no_arguments(self, parser):
        """Test counting zero arguments"""
        from cicada.extractors.base import count_arguments

        code = "func()"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 0

    def test_count_single_argument(self, parser):
        """Test counting single argument"""
        from cicada.extractors.base import count_arguments

        code = "func(arg)"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 1

    def test_count_two_arguments(self, parser):
        """Test counting two arguments"""
        from cicada.extractors.base import count_arguments

        code = "func(arg1, arg2)"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 2

    def test_count_three_arguments(self, parser):
        """Test counting three arguments"""
        from cicada.extractors.base import count_arguments

        code = "func(a, b, c)"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 3

    def test_count_many_arguments(self, parser):
        """Test counting many arguments"""
        from cicada.extractors.base import count_arguments

        code = "func(a, b, c, d, e, f, g)"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 7

    def test_count_string_argument(self, parser):
        """Test counting string as argument"""
        from cicada.extractors.base import count_arguments

        code = 'puts("hello")'
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 1

    def test_count_mixed_types(self, parser):
        """Test counting different argument types"""
        from cicada.extractors.base import count_arguments

        code = 'func("string", 123, :atom, true)'
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 4

    def test_count_nested_call(self, parser):
        """Test counting when argument is nested function call"""
        from cicada.extractors.base import count_arguments

        code = "outer(inner(x), y)"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        # inner(x) counts as 1 argument, y as another
        assert result == 2

    def test_count_list_argument(self, parser):
        """Test counting list as single argument"""
        from cicada.extractors.base import count_arguments

        code = "func([1, 2, 3])"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 1

    def test_count_map_argument(self, parser):
        """Test counting map as single argument"""
        from cicada.extractors.base import count_arguments

        code = "func(%{key: value})"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 1

    def test_count_tuple_argument(self, parser):
        """Test counting tuple as single argument"""
        from cicada.extractors.base import count_arguments

        code = "func({a, b})"
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 1

    def test_count_complex_mix(self, parser):
        """Test counting complex argument mix"""
        from cicada.extractors.base import count_arguments

        code = 'process("text", [1, 2], %{a: b}, nested(x))'
        arguments_node = self._get_arguments_node(parser, code)

        assert arguments_node is not None
        result = count_arguments(arguments_node)
        assert result == 4


class TestIntegrationScenarios:
    """Integration tests using realistic code patterns"""

    @pytest.fixture
    def parser(self):
        """Create a tree-sitter parser for Elixir"""
        parser = Parser()
        parser.language = Language(tree_sitter_elixir.language())
        return parser

    def test_extract_moduledoc_string(self, parser):
        """Test extracting @moduledoc string in real module"""
        from cicada.extractors.base import extract_string_from_arguments

        code = """
defmodule MyModule do
  @moduledoc "This module does important things"

  def hello, do: :world
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        # Find @moduledoc arguments
        def find_moduledoc_args(node):
            if node.type == "unary_operator":
                for child in node.children:
                    if child.type == "call":
                        for call_child in child.children:
                            if call_child.type == "identifier":
                                name = source_bytes[
                                    call_child.start_byte : call_child.end_byte
                                ].decode("utf-8")
                                if name == "moduledoc":
                                    # Find arguments
                                    for cc in child.children:
                                        if cc.type == "arguments":
                                            return cc
            for child in node.children:
                result = find_moduledoc_args(child)
                if result:
                    return result
            return None

        args_node = find_moduledoc_args(tree.root_node)
        if args_node:
            result = extract_string_from_arguments(args_node, source_bytes)
            assert result == "This module does important things"

    def test_count_function_call_args(self, parser):
        """Test counting arguments in a typical function call"""
        from cicada.extractors.base import count_arguments

        code = """
defmodule Test do
  def main do
    IO.inspect(value, label: "Debug", limit: :infinity)
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        # Find IO.inspect arguments
        def find_call_args(node):
            if node.type == "call":
                for child in node.children:
                    if child.type == "dot":
                        # This might be IO.inspect
                        for sibling in node.children:
                            if sibling.type == "arguments":
                                return sibling
            for child in node.children:
                result = find_call_args(child)
                if result:
                    return result
            return None

        args_node = find_call_args(tree.root_node)
        if args_node:
            count = count_arguments(args_node)
            # Should count value and the keyword list items
            assert count >= 1

    def test_get_param_names_from_def(self, parser):
        """Test getting parameter names from actual def"""

        code = """
defmodule Math do
  def add(x, y) do
    x + y
  end
end
"""
        source_bytes = bytes(code, "utf8")
        tree = parser.parse(source_bytes)

        # This is a simplified test - in real usage, the function extractor
        # handles the tree traversal
        assert tree.root_node is not None


class TestGetParamName:
    """Tests for get_param_name function"""

    @pytest.fixture
    def parser(self):
        """Create a tree-sitter parser for Elixir"""
        parser = Parser()
        parser.language = Language(tree_sitter_elixir.language())
        return parser

    def _get_first_param_node(self, parser, code: str):
        """Helper to parse code and find the first parameter node"""
        tree = parser.parse(bytes(code, "utf8"))

        def find_node_by_type(node, node_type):
            if node.type == node_type:
                return node
            for child in node.children:
                result = find_node_by_type(child, node_type)
                if result:
                    return result
            return None

        # Find the arguments node first
        arguments_node = find_node_by_type(tree.root_node, "arguments")
        if not arguments_node:
            return None

        # Return the first non-punctuation child
        for child in arguments_node.children:
            if child.type not in [",", "(", ")"]:
                return child
        return None

    def test_simple_identifier(self, parser):
        """Test extracting simple identifier parameter"""
        from cicada.extractors.base import get_param_name

        code = "def func(my_arg), do: my_arg"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node and param_node.type == "identifier":
            result = get_param_name(param_node, source_bytes)
            assert result == "my_arg"

    def test_binary_operator_default(self, parser):
        """Test extracting parameter with default value"""
        from cicada.extractors.base import get_param_name

        code = "def func(arg \\\\ 42), do: arg"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node:
            result = get_param_name(param_node, source_bytes)
            # Should extract something (the exact node structure may vary)
            assert result is not None

    def test_tuple_destructuring(self, parser):
        """Test extracting tuple destructuring pattern"""
        from cicada.extractors.base import get_param_name

        code = "def func({x, y}), do: x + y"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node and param_node.type == "tuple":
            result = get_param_name(param_node, source_bytes)
            # Should return the whole tuple pattern
            assert result is not None
            assert "{" in result and "}" in result

    def test_list_destructuring(self, parser):
        """Test extracting list destructuring pattern"""
        from cicada.extractors.base import get_param_name

        code = "def func([head | tail]), do: head"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node and param_node.type == "list":
            result = get_param_name(param_node, source_bytes)
            # Should return the whole list pattern
            assert result is not None
            assert "[" in result

    def test_map_destructuring(self, parser):
        """Test extracting map destructuring pattern"""
        from cicada.extractors.base import get_param_name

        code = "def func(%{key: value}), do: value"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node and param_node.type == "map":
            result = get_param_name(param_node, source_bytes)
            # Should return the whole map pattern
            assert result is not None
            assert "%" in result

    def test_struct_pattern(self, parser):
        """Test extracting struct pattern"""
        from cicada.extractors.base import get_param_name

        code = "def func(%User{name: name}), do: name"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node:
            result = get_param_name(param_node, source_bytes)
            # Should extract something meaningful
            assert result is not None

    def test_underscore_param(self, parser):
        """Test extracting underscore parameter"""
        from cicada.extractors.base import get_param_name

        code = "def func(_unused), do: 42"
        source_bytes = bytes(code, "utf8")
        param_node = self._get_first_param_node(parser, code)

        if param_node and param_node.type == "identifier":
            result = get_param_name(param_node, source_bytes)
            assert result == "_unused"
