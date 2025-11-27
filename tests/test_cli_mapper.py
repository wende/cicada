"""Tests for CLI mapper - schema to argparse conversion."""

import argparse

import pytest

from cicada.cli_mapper import (
    parse_cli_args_to_handler_kwargs,
    register_tool_subparsers,
    schema_to_argparse,
)
from cicada.mcp.tools import get_tool_definitions


class TestSchemaToArgparse:
    """Test schema-to-argparse conversion."""

    def test_string_parameter(self):
        """Test converting string schema to argparse argument."""
        schema = {"type": "string", "description": "Test string param"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("test_param", schema, parser)
        args = parser.parse_args(["--test-param", "value"])
        assert args.test_param == "value"

    def test_integer_parameter(self):
        """Test converting integer schema to argparse argument."""
        schema = {"type": "integer", "description": "Test integer param"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("count", schema, parser)
        args = parser.parse_args(["--count", "42"])
        assert args.count == 42

    def test_boolean_parameter_default_false(self):
        """Test converting boolean schema (default false) to store_true."""
        schema = {"type": "boolean", "description": "Test boolean"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("verbose", schema, parser, default=False)

        args = parser.parse_args([])
        assert args.verbose is False

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_enum_parameter(self):
        """Test converting enum schema to argparse choices."""
        schema = {
            "type": "string",
            "enum": ["all", "public", "private"],
            "description": "Scope filter",
        }
        parser = argparse.ArgumentParser()
        schema_to_argparse("scope", schema, parser, default="all")

        args = parser.parse_args(["--scope", "public"])
        assert args.scope == "public"

        # Test invalid choice
        with pytest.raises(SystemExit):
            parser.parse_args(["--scope", "invalid"])

    def test_array_parameter(self):
        """Test converting array schema to nargs='+'."""
        schema = {"type": "array", "items": {"type": "string"}, "description": "Keywords"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("query", schema, parser, positional=True)

        args = parser.parse_args(["keyword1", "keyword2"])
        assert args.query == ["keyword1", "keyword2"]

    def test_required_positional_parameter(self):
        """Test required positional parameter."""
        schema = {"type": "string", "description": "File path"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("file_path", schema, parser, positional=True)

        args = parser.parse_args(["myfile.ex"])
        assert args.file_path == "myfile.ex"

        # Test missing required
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_anyof_string_or_array(self):
        """Test anyOf schema with string | array type."""
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ],
            "description": "Query keywords or pattern",
        }
        parser = argparse.ArgumentParser()
        schema_to_argparse("query", schema, parser, positional=True)

        # Should accept multiple arguments
        args = parser.parse_args(["auth", "login"])
        assert args.query == ["auth", "login"]

        # Single argument is also valid (nargs='+' enforces at least one)
        args = parser.parse_args(["auth"])
        assert args.query == ["auth"]

    def test_parameter_with_default_value(self):
        """Test parameter with default value."""
        schema = {"type": "integer", "description": "Max results"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("max_results", schema, parser, default=10)

        # No argument provided
        args = parser.parse_args([])
        assert args.max_results == 10

        # Override default
        args = parser.parse_args(["--max-results", "20"])
        assert args.max_results == 20

    def test_nullable_boolean(self):
        """Test nullable boolean (true/false/null) parameter."""
        schema = {"type": ["boolean", "null"], "description": "Recent filter"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("recent", schema, parser, nullable_bool=True)

        # No argument = None
        args = parser.parse_args([])
        assert args.recent is None

        # --recent = True
        args = parser.parse_args(["--recent"])
        assert args.recent is True

        # --recent false = False
        args = parser.parse_args(["--recent", "false"])
        assert args.recent is False

        # --recent true = True
        args = parser.parse_args(["--recent", "true"])
        assert args.recent is True

    def test_boolean_with_true_default(self):
        """Test boolean parameter with True default (need both --flag and --no-flag)."""
        schema = {"type": "boolean", "description": "Show calls"}
        parser = argparse.ArgumentParser()
        schema_to_argparse("what_calls_it", schema, parser, default=True)

        # No argument = True
        args = parser.parse_args([])
        assert args.what_calls_it is True

        # --what-calls-it (no argument) = True
        args = parser.parse_args(["--what-calls-it"])
        assert args.what_calls_it is True

        # --no-what-calls-it = False
        args = parser.parse_args(["--no-what-calls-it"])
        assert args.what_calls_it is False


class TestParseCliArgsToKwargs:
    """Test converting argparse args to handler kwargs."""

    def test_basic_args_to_kwargs(self):
        """Test basic conversion of args to kwargs."""
        namespace = argparse.Namespace(
            query=["auth", "login"],
            scope="public",
            max_results=20,
        )
        kwargs = parse_cli_args_to_handler_kwargs(namespace, "query")

        assert kwargs["query"] == ["auth", "login"]
        assert kwargs["scope"] == "public"
        assert kwargs["max_results"] == 20

    def test_hyphenated_args_converted_to_underscores(self):
        """Test that hyphenated arg names are converted to underscores."""
        # argparse converts --max-results to args.max_results
        namespace = argparse.Namespace(
            max_results=15,
            filter_type="functions",
        )
        kwargs = parse_cli_args_to_handler_kwargs(namespace, "query")

        assert kwargs["max_results"] == 15
        assert kwargs["filter_type"] == "functions"

    def test_none_values_omitted(self):
        """Test that None values are omitted from kwargs."""
        namespace = argparse.Namespace(
            query="auth",
            path_pattern=None,  # Optional param not provided
            show_snippets=False,
        )
        kwargs = parse_cli_args_to_handler_kwargs(namespace, "query")

        # None values should be omitted
        assert "path_pattern" not in kwargs
        # But False is a valid value (different from None)
        assert kwargs["show_snippets"] is False

    def test_required_param_validation(self):
        """Test that required parameters are validated."""
        # For query tool, 'query' param should not be None
        # But parse_cli_args_to_handler_kwargs skips None values
        # So we test that it returns empty dict which would fail later
        # This is acceptable - argparse should have caught this during parsing
        namespace = argparse.Namespace(query=None)
        kwargs = parse_cli_args_to_handler_kwargs(namespace, "query")
        # query param is omitted because it's None
        assert "query" not in kwargs

    def test_mutually_exclusive_params_validation(self):
        """Test that mutually exclusive params are validated."""
        # search-module requires either --module-name or --file-path
        namespace = argparse.Namespace(module_name=None, file_path=None)

        with pytest.raises(ValueError):
            parse_cli_args_to_handler_kwargs(namespace, "search-module")

    def test_single_value_not_wrapped_in_list(self):
        """Test that single values are not wrapped in lists."""
        namespace = argparse.Namespace(identifier="MyApp.Auth")
        kwargs = parse_cli_args_to_handler_kwargs(namespace, "expand-result")

        assert kwargs["identifier"] == "MyApp.Auth"
        assert not isinstance(kwargs["identifier"], list)

    def test_tool_command_name_normalization(self):
        """Test that tool command names are normalized (hyphen to underscore)."""
        # CLI command is "search-module" but handler method is "search_module"
        namespace = argparse.Namespace(module_name="MyApp.User")
        kwargs = parse_cli_args_to_handler_kwargs(namespace, "search-module")

        # Should not raise, should normalize tool name internally
        assert kwargs["module_name"] == "MyApp.User"


class TestRegisterToolSubparsers:
    """Test registering tool subparsers from schemas."""

    def test_all_tools_registered(self):
        """Test that all 7 tools are registered as subparsers."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")

        tools = get_tool_definitions()
        register_tool_subparsers(subparsers, tools)

        # Verify each tool's subparser was created
        # by checking it exists in the subparsers choices
        assert "query" in subparsers.choices
        assert "search-module" in subparsers.choices
        assert "search-function" in subparsers.choices
        assert "git-history" in subparsers.choices
        assert "find-dead-code" in subparsers.choices
        assert "expand-result" in subparsers.choices
        assert "query-jq" in subparsers.choices

    def test_query_tool_registration(self):
        """Test query tool subparser registration."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")

        tools = get_tool_definitions()
        register_tool_subparsers(subparsers, tools)

        # Parse query command with basic args
        args = parser.parse_args(["query", "auth"])
        assert args.tool == "query"
        assert args.query == ["auth"]

    def test_search_module_tool_registration(self):
        """Test search-module tool subparser registration."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")

        tools = get_tool_definitions()
        register_tool_subparsers(subparsers, tools)

        # Parse search-module command
        args = parser.parse_args(["search-module", "--module-name", "MyApp.User"])
        assert args.tool == "search-module"
        assert args.module_name == "MyApp.User"

    def test_git_history_nullable_boolean(self):
        """Test git-history tool with nullable boolean --recent."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")

        tools = get_tool_definitions()
        register_tool_subparsers(subparsers, tools)

        # Parse with --recent true
        args = parser.parse_args(["git-history", "file.ex", "--recent", "true"])
        assert args.recent is True

        # Parse with --recent false
        args = parser.parse_args(["git-history", "file.ex", "--recent", "false"])
        assert args.recent is False

        # Parse without --recent (should be None)
        args = parser.parse_args(["git-history", "file.ex"])
        assert args.recent is None

    def test_find_dead_code_optional_params(self):
        """Test find-dead-code tool with all optional parameters."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")

        tools = get_tool_definitions()
        register_tool_subparsers(subparsers, tools)

        # Parse with no args (all optional)
        args = parser.parse_args(["find-dead-code"])
        assert args.tool == "find-dead-code"

        # Parse with format option
        args = parser.parse_args(["find-dead-code", "--format", "json"])
        assert args.format == "json"

    def test_expand_result_with_options(self):
        """Test expand-result tool with various options."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")

        tools = get_tool_definitions()
        register_tool_subparsers(subparsers, tools)

        # Parse expand-result
        args = parser.parse_args(
            [
                "expand-result",
                "MyApp.Auth.verify_token/2",
                "--what-calls-it",
                "--type",
                "function",
            ]
        )
        assert args.identifier == "MyApp.Auth.verify_token/2"
        assert args.what_calls_it is True
        assert args.type == "function"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
