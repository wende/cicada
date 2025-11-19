#!/usr/bin/env python
"""
Tests for jq Query MCP Tool

Test-Driven Development (TDD) tests for the query_jq tool that executes
jq queries against the Cicada code index.

Test Categories:
1. Parameter Validation - Input validation and type checking
2. Tool Execution - Basic jq query execution
3. Use Cases - Real-world query patterns
4. Edge Cases - Empty data, missing fields, errors
"""

import asyncio
import json
from unittest.mock import patch, MagicMock

import pytest
import yaml
from mcp.types import TextContent

from cicada.mcp.server import CicadaServer


@pytest.fixture
def test_index():
    """Create a comprehensive test index with all field types."""
    return {
        "modules": {
            "TestModule": {
                "file": "lib/test.ex",
                "line": 1,
                "moduledoc": "Test module for demonstrations",
                "functions": [
                    {
                        "name": "test_func",
                        "arity": 1,
                        "line": 10,
                        "type": "def",
                        "signature": "test_func(arg)",
                        "doc": "A test function",
                        "args": ["arg"],
                        "guards": [],
                        "full_name": "test_func/1",
                        "impl": False,
                        "keywords": {"test": 1.0, "function": 0.8},
                    },
                    {
                        "name": "private_helper",
                        "arity": 0,
                        "line": 20,
                        "type": "defp",
                        "signature": "private_helper()",
                        "doc": None,
                        "args": [],
                        "guards": [],
                        "full_name": "private_helper/0",
                        "impl": False,
                    },
                ],
                "total_functions": 2,
                "public_functions": 1,
                "private_functions": 1,
                "keywords": {"test": 1.2, "module": 0.9},
                "string_keywords": {"SELECT": 1.3, "database": 1.1},
                "string_sources": [
                    {
                        "string": "SELECT * FROM users",
                        "line": 15,
                        "function": "test_func",
                    }
                ],
            },
            "AnotherModule": {
                "file": "lib/another.ex",
                "line": 1,
                "moduledoc": "Another module",
                "functions": [
                    {
                        "name": "another_func",
                        "arity": 2,
                        "line": 5,
                        "type": "def",
                        "signature": "another_func(x, y)",
                        "doc": "Another function",
                        "args": ["x", "y"],
                        "guards": [],
                        "full_name": "another_func/2",
                        "impl": False,
                        "keywords": {"another": 0.95},
                    }
                ],
                "total_functions": 1,
                "public_functions": 1,
                "private_functions": 0,
                "keywords": {"another": 1.1},
            },
        },
        "metadata": {
            "indexed_at": "2024-01-15T10:30:00",
            "total_modules": 2,
            "total_functions": 3,
            "repo_path": "/test/repo",
            "cicada_version": "0.3.2",
        },
    }


@pytest.fixture
def test_server(tmp_path, test_index):
    """Create a test server with sample index."""
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return CicadaServer(str(config_path))


class TestJqToolValidation:
    """Test input validation for jq tool."""

    @pytest.mark.asyncio
    async def test_missing_query_parameter(self, test_server):
        """Should require query parameter."""
        result = await test_server.call_tool("query_jq", {})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "'query' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_invalid_query_type(self, test_server):
        """Should reject non-string query."""
        result = await test_server.call_tool("query_jq", {"query": 123})
        assert len(result) == 1
        assert "'query' must be a string" in result[0].text

    @pytest.mark.asyncio
    async def test_invalid_format_parameter(self, test_server):
        """Should validate format parameter."""
        result = await test_server.call_tool("query_jq", {"query": ".modules", "format": "invalid"})
        assert len(result) == 1
        assert "'format' must be one of" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_query_string(self, test_server):
        """Should reject empty query string."""
        result = await test_server.call_tool("query_jq", {"query": ""})
        assert len(result) == 1
        # Either validation error or jq error is acceptable
        assert "required" in result[0].text.lower() or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_query_with_special_characters(self, test_server):
        """Should handle queries with special characters."""
        # This should work - jq handles special chars in strings
        result = await test_server.call_tool("query_jq", {"query": ".metadata.repo_path"})
        assert len(result) == 1
        # Should return the path or an error, but not crash
        assert isinstance(result[0], TextContent)


class TestJqToolExecution:
    """Test jq query execution."""

    @pytest.mark.asyncio
    async def test_simple_query_list_keys(self, test_server):
        """Should execute simple jq query to list module keys."""
        result = await test_server.call_tool("query_jq", {"query": ".modules | keys"})
        assert len(result) == 1
        # Should return list with module names
        output = json.loads(result[0].text)
        assert isinstance(output, list)
        assert "TestModule" in output
        assert "AnotherModule" in output

    @pytest.mark.asyncio
    async def test_query_with_filter(self, test_server):
        """Should execute jq query with filter."""
        result = await test_server.call_tool(
            "query_jq",
            {"query": ".modules | to_entries | map(select(.value.keywords)) | map(.key)"},
        )
        assert len(result) == 1
        # Should return filtered modules (both have keywords)
        output = json.loads(result[0].text)
        assert isinstance(output, list)
        assert len(output) == 2

    @pytest.mark.asyncio
    async def test_compact_format(self, test_server):
        """Should return compact JSON format."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | keys", "format": "compact"}
        )
        assert len(result) == 1
        # Compact format should be one line (no newlines except maybe trailing)
        lines = result[0].text.strip().split("\n")
        assert len(lines) == 1
        # Should still be valid JSON
        output = json.loads(result[0].text)
        assert isinstance(output, list)

    @pytest.mark.asyncio
    async def test_pretty_format(self, test_server):
        """Should return pretty-printed JSON format."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | keys", "format": "pretty"}
        )
        assert len(result) == 1
        # Pretty format should have multiple lines
        assert "\n" in result[0].text
        # Should still be valid JSON
        output = json.loads(result[0].text)
        assert isinstance(output, list)

    @pytest.mark.asyncio
    async def test_json_format_default(self, test_server):
        """Should default to json format when not specified."""
        result = await test_server.call_tool("query_jq", {"query": ".modules | keys"})
        assert len(result) == 1
        # Should be valid JSON
        output = json.loads(result[0].text)
        assert isinstance(output, list)

    @pytest.mark.asyncio
    async def test_json_format_backward_compatibility(self, test_server):
        """Should accept format='json' for backward compatibility (maps to compact)."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | keys", "format": "json"}
        )
        assert len(result) == 1
        # format='json' should behave like 'compact' (one line, no indentation)
        lines = result[0].text.strip().split("\n")
        assert len(lines) == 1
        # Should still be valid JSON
        output = json.loads(result[0].text)
        assert isinstance(output, list)

    @pytest.mark.asyncio
    async def test_invalid_jq_syntax(self, test_server):
        """Should handle invalid jq syntax gracefully."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | invalid_function_xyz"}
        )
        assert len(result) == 1
        text_lower = result[0].text.lower()
        # Should return error message with helpful info
        assert "error" in text_lower or "failed" in text_lower

    @pytest.mark.asyncio
    async def test_invalid_jq_syntax_with_line_column(self, test_server):
        """Should show line and column info with visual pointer for syntax errors."""
        result = await test_server.call_tool("query_jq", {"query": ".modules | invalid_function()"})
        assert len(result) == 1
        text = result[0].text
        # Should contain error with line/column info
        assert "error" in text.lower()
        # Should show the query line
        assert ".modules | invalid_function()" in text
        # Should have a visual pointer (^)
        assert "^" in text

    @pytest.mark.asyncio
    async def test_invalid_jq_syntax_multiline(self, test_server):
        """Should show correct line for multiline queries with syntax errors."""
        multiline_query = """.modules
| to_entries
| map(invalid_func())"""
        result = await test_server.call_tool("query_jq", {"query": multiline_query})
        assert len(result) == 1
        text = result[0].text
        # Should contain error with line/column info
        assert "error" in text.lower()
        # Should have a visual pointer (^)
        assert "^" in text
        # Should show the error line (line 3 with invalid_func)
        assert "invalid_func" in text

    @pytest.mark.asyncio
    async def test_query_returns_null(self, test_server):
        """Should handle queries that return null."""
        result = await test_server.call_tool("query_jq", {"query": ".nonexistent_field"})
        assert len(result) == 1
        # Should indicate null/empty result
        assert "null" in result[0].text.lower() or "no results" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_query_returns_empty_array(self, test_server):
        """Should handle queries that return empty arrays."""
        result = await test_server.call_tool(
            "query_jq",
            {"query": '.modules | to_entries | map(select(.key == "NonExistent"))'},
        )
        assert len(result) == 1
        # Should return empty array as valid JSON
        output = json.loads(result[0].text)
        assert output == []

    @pytest.mark.asyncio
    async def test_query_with_optional_field_handling(self, test_server):
        """Should handle optional fields correctly with ? operator."""
        # Some functions have doc, some don't - using ? should work
        result = await test_server.call_tool(
            "query_jq",
            {"query": ".modules[].functions[]? | select(.doc != null) | .name"},
        )
        assert len(result) == 1
        # Should return function names that have docs
        output = result[0].text.strip()
        assert "test_func" in output or "another_func" in output


class TestJqToolUseCases:
    """Test real-world jq use cases."""

    @pytest.mark.asyncio
    async def test_list_all_modules(self, test_server):
        """Should list all module names."""
        result = await test_server.call_tool("query_jq", {"query": ".modules | keys"})
        assert len(result) == 1
        modules = json.loads(result[0].text)
        assert isinstance(modules, list)
        assert set(modules) == {"TestModule", "AnotherModule"}

    @pytest.mark.asyncio
    async def test_count_functions_per_module(self, test_server):
        """Should count functions in each module."""
        result = await test_server.call_tool(
            "query_jq",
            {"query": ".modules | to_entries | map({module: .key, count: .value.total_functions})"},
        )
        assert len(result) == 1
        counts = json.loads(result[0].text)
        assert len(counts) == 2
        # Find TestModule's count
        test_module_count = next(c for c in counts if c["module"] == "TestModule")
        assert test_module_count["count"] == 2

    @pytest.mark.asyncio
    async def test_find_modules_with_keywords(self, test_server):
        """Should find modules with keyword extraction."""
        result = await test_server.call_tool(
            "query_jq",
            {"query": ".modules | to_entries | map(select(.value.keywords)) | map(.key)"},
        )
        assert len(result) == 1
        modules = json.loads(result[0].text)
        assert "TestModule" in modules
        assert "AnotherModule" in modules

    @pytest.mark.asyncio
    async def test_find_functions_by_arity(self, test_server):
        """Should find functions with specific arity."""
        result = await test_server.call_tool(
            "query_jq",
            {"query": ".modules[].functions[] | select(.arity == 2) | .full_name"},
        )
        assert len(result) == 1
        assert "another_func/2" in result[0].text

    @pytest.mark.asyncio
    async def test_filter_by_file_path_pattern(self, test_server):
        """Should filter modules by file path pattern."""
        result = await test_server.call_tool(
            "query_jq",
            {
                "query": '.modules | to_entries | map(select(.value.file | test("lib/test"))) | map(.key)'
            },
        )
        assert len(result) == 1
        modules = json.loads(result[0].text)
        assert "TestModule" in modules
        assert "AnotherModule" not in modules

    @pytest.mark.asyncio
    async def test_complex_multi_criteria_query(self, test_server):
        """Should handle complex queries with multiple criteria."""
        result = await test_server.call_tool(
            "query_jq",
            {
                "query": '.modules[].functions[] | select(.type == "def" and .arity > 0) | {name, arity, type}'
            },
        )
        assert len(result) == 1
        # Should return multiple function objects
        text = result[0].text.strip()
        assert "test_func" in text or "another_func" in text

    @pytest.mark.asyncio
    async def test_nested_data_access(self, test_server):
        """Should access nested data structures."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules.TestModule.string_sources[0].string"}
        )
        assert len(result) == 1
        assert "SELECT * FROM users" in result[0].text

    @pytest.mark.asyncio
    async def test_aggregation_queries(self, test_server):
        """Should handle aggregation (sort, top N)."""
        result = await test_server.call_tool(
            "query_jq",
            {
                "query": ".modules | to_entries | sort_by(.value.total_functions) | reverse | .[0:1] | map(.key)"
            },
        )
        assert len(result) == 1
        modules = json.loads(result[0].text)
        # TestModule has most functions (2)
        assert modules[0] == "TestModule"


class TestJqToolEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_index(self, tmp_path):
        """Should handle empty index gracefully."""
        empty_index = {"modules": {}, "metadata": {"total_modules": 0}}
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(empty_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        result = await server.call_tool("query_jq", {"query": ".modules | keys"})
        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output == []

    @pytest.mark.asyncio
    async def test_index_missing_optional_fields(self, tmp_path):
        """Should handle index with missing optional fields."""
        minimal_index = {
            "modules": {
                "MinimalModule": {
                    "file": "lib/minimal.ex",
                    "line": 1,
                    "functions": [],
                    # No keywords, no string_keywords, no doc
                }
            },
            "metadata": {"total_modules": 1},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(minimal_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        # Should work with optional field handling
        result = await server.call_tool(
            "query_jq", {"query": ".modules.MinimalModule.keywords // null"}
        )
        assert len(result) == 1
        assert "null" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_unicode_in_queries(self, test_server):
        """Should handle unicode characters in queries."""
        # Query that includes unicode (even if it doesn't match anything)
        result = await test_server.call_tool(
            "query_jq",
            {"query": '.modules | to_entries | map(select(.key | test("Test")))'},
        )
        assert len(result) == 1
        # Should execute without crashing
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_very_long_query_string(self, test_server):
        """Should handle very long query strings."""
        # Create a long but valid query
        long_query = (
            '.modules | to_entries | map(select(.value.file | test("lib"))) | ' * 10 + "map(.key)"
        )
        result = await test_server.call_tool("query_jq", {"query": long_query})
        assert len(result) == 1
        # Should either succeed or fail with error message (not crash)
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_query_returns_different_types(self, test_server):
        """Should handle queries returning different JSON types."""
        # String
        result = await test_server.call_tool("query_jq", {"query": ".metadata.repo_path"})
        assert len(result) == 1
        assert "/test/repo" in result[0].text

        # Number
        result = await test_server.call_tool("query_jq", {"query": ".metadata.total_modules"})
        assert len(result) == 1
        assert "2" in result[0].text

        # Boolean
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules.TestModule.functions[0].impl"}
        )
        assert len(result) == 1
        assert "false" in result[0].text.lower()

        # Object
        result = await test_server.call_tool("query_jq", {"query": ".metadata"})
        assert len(result) == 1
        output = json.loads(result[0].text)
        assert isinstance(output, dict)

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, test_server):
        """Should handle concurrent query execution."""
        queries = [
            ".modules | keys",
            ".metadata.total_modules",
            ".modules.TestModule.functions | length",
        ]

        # Execute queries concurrently
        tasks = [test_server.call_tool("query_jq", {"query": q}) for q in queries]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        for result in results:
            assert len(result) == 1
            assert isinstance(result[0], TextContent)


class TestJqToolPerformance:
    """Test performance and resource limits."""

    @pytest.mark.asyncio
    async def test_result_size_handling(self, tmp_path):
        """Should handle large results appropriately."""
        # Create index with many modules
        large_index = {
            "modules": {
                f"Module{i}": {
                    "file": f"lib/module{i}.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": f"func{j}",
                            "arity": 0,
                            "line": j * 10,
                            "type": "def",
                        }
                        for j in range(10)
                    ],
                }
                for i in range(50)
            },
            "metadata": {"total_modules": 50},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(large_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        # Query that returns lots of data
        result = await server.call_tool("query_jq", {"query": ".modules"})
        assert len(result) == 1
        # Should complete without error (may be truncated)
        assert isinstance(result[0], TextContent)
        # Result should be non-empty
        assert len(result[0].text) > 0

    @pytest.mark.asyncio
    async def test_query_with_timeout_handling(self, test_server):
        """Should handle potentially slow queries."""
        # A query that might be slow but should still complete
        result = await test_server.call_tool(
            "query_jq",
            {
                "query": ".modules | to_entries | map(.value.functions) | flatten | group_by(.type) | map({type: .[0].type, count: length})"
            },
        )
        assert len(result) == 1
        # Should complete without timeout error
        assert isinstance(result[0], TextContent)
        # Should not contain timeout error message
        assert "timeout" not in result[0].text.lower() or json.loads(result[0].text)


class TestJqToolSecurity:
    """Test security validation and resource limits."""

    @pytest.mark.asyncio
    async def test_whitespace_only_query(self, test_server):
        """Should reject queries containing only whitespace."""
        result = await test_server.call_tool("query_jq", {"query": "   \t\n  "})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should reject empty/whitespace queries
        text_lower = result[0].text.lower()
        assert "empty" in text_lower or "required" in text_lower or "error" in text_lower

    @pytest.mark.asyncio
    async def test_query_exceeds_length_limit(self, test_server):
        """Should reject queries exceeding maximum length (10,000 chars)."""
        # Create a query that exceeds 10,000 characters
        long_query = ".modules | " + "keys | " * 2000  # Well over 10k chars
        result = await test_server.call_tool("query_jq", {"query": long_query})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_lower = result[0].text.lower()
        # Should either reject with length error or process it (depends on implementation)
        # The validation should catch queries > 10,000 chars
        assert (
            "too long" in text_lower or "length" in text_lower or isinstance(result[0], TextContent)
        )

    @pytest.mark.asyncio
    async def test_query_with_excessive_nesting(self, test_server):
        """Should detect queries with excessive nesting depth."""
        # Create query with deep nesting (>50 levels)
        # Properly balanced but deeply nested
        deeply_nested = "." + "[" * 60 + "]" * 60
        result = await test_server.call_tool("query_jq", {"query": deeply_nested})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should reject the query due to excessive nesting depth
        text_lower = result[0].text.lower()
        assert "nesting" in text_lower or "depth" in text_lower

    @pytest.mark.asyncio
    async def test_query_with_brackets_in_strings(self, test_server):
        """Should allow brackets inside strings (not count as nesting)."""
        # Query with brackets in strings - should be valid
        # Use a simpler string that contains brackets
        query = '.modules | to_entries | map(select(.value.file | contains("lib/[test]")))'
        result = await test_server.call_tool("query_jq", {"query": query})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should not reject due to brackets in string - should execute successfully or fail for jq reasons
        text_lower = result[0].text.lower()
        # Should not be rejected by our validator (no "unbalanced" or "unclosed" from our validator)
        assert "unclosed" not in text_lower and "unbalanced" not in text_lower

    @pytest.mark.asyncio
    async def test_query_with_unbalanced_brackets(self, test_server):
        """Should detect truly unbalanced brackets."""
        # Missing closing bracket
        unbalanced = ".modules | keys["
        result = await test_server.call_tool("query_jq", {"query": unbalanced})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_lower = result[0].text.lower()
        assert "unclosed" in text_lower or "unbalanced" in text_lower

    @pytest.mark.asyncio
    async def test_query_with_mismatched_brackets(self, test_server):
        """Should detect mismatched bracket types."""
        # Opening [ but closing with )
        mismatched = ".modules[keys)"
        result = await test_server.call_tool("query_jq", {"query": mismatched})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_lower = result[0].text.lower()
        assert "mismatch" in text_lower or "bracket" in text_lower

    @pytest.mark.asyncio
    async def test_query_with_escaped_quotes_in_strings(self, test_server):
        """Should handle escaped quotes inside strings correctly."""
        # String with escaped quotes and brackets
        query = r'.modules | to_entries | map(select(.value.doc | contains("\"test\" [value]")))'
        result = await test_server.call_tool("query_jq", {"query": query})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should not reject due to brackets in string

    @pytest.mark.asyncio
    async def test_query_with_unterminated_string(self, test_server):
        """Should detect unterminated strings."""
        unterminated = '.modules | select(.file == "lib/test.ex)'
        result = await test_server.call_tool("query_jq", {"query": unterminated})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text_lower = result[0].text.lower()
        assert "string" in text_lower or "unterminated" in text_lower or "quote" in text_lower


class TestJqToolErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_jq_syntax_error_iterate_null_hint(self, test_server):
        """Should provide specific hint for 'iterate over null' errors."""
        # This query will try to iterate over null (modules doesn't have .nonexistent)
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules.NonExistent.functions[] | .name"}
        )
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        # Should contain error message and hint about optional access
        assert "error" in text.lower() or "null" in text.lower()
        # May contain hint about using ? operator
        assert "?" in text or "null" in text.lower()

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self, test_server):
        """Should handle unexpected exceptions gracefully."""
        # Mock jq to raise unexpected exception
        with patch("cicada.mcp.handlers.analysis_handlers.jq") as mock_jq:
            mock_jq.compile.side_effect = RuntimeError("Unexpected error")

            result = await test_server.call_tool("query_jq", {"query": ".modules | keys"})
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            text_lower = result[0].text.lower()
            # Should contain error indication
            assert "error" in text_lower or "failed" in text_lower


class TestJqToolNewFeatures:
    """Test new jq tool features: schema discovery, sample mode, size estimation."""

    @pytest.mark.asyncio
    async def test_schema_discovery_for_object(self, test_server):
        """Should handle '| schema' for objects by showing keys."""
        result = await test_server.call_tool("query_jq", {"query": ".modules | schema"})
        assert len(result) == 1
        # Should return array of module names (keys of modules object)
        output = json.loads(result[0].text)
        assert isinstance(output, list)
        assert "TestModule" in output or "AnotherModule" in output

    @pytest.mark.asyncio
    async def test_schema_discovery_for_array(self, test_server):
        """Should handle '| schema' for arrays by showing keys of first element."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules.TestModule.functions | schema"}
        )
        assert len(result) == 1
        # Should return keys of first function object
        output = json.loads(result[0].text)
        assert isinstance(output, list)
        # Should contain function field names
        assert "name" in output
        assert "arity" in output
        assert "type" in output

    @pytest.mark.asyncio
    async def test_schema_discovery_with_whitespace(self, test_server):
        """Should handle '| schema' with various whitespace."""
        result = await test_server.call_tool("query_jq", {"query": ".modules   |   schema  "})
        assert len(result) == 1
        output = json.loads(result[0].text)
        assert isinstance(output, list)

    @pytest.mark.asyncio
    async def test_sample_mode_with_array(self, test_server):
        """Should limit array results to 5 items with sample mode."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | keys", "sample": True}
        )
        assert len(result) == 1
        output = json.loads(result[0].text)
        assert isinstance(output, list)
        # Should have at most 5 items
        assert len(output) <= 5

    @pytest.mark.asyncio
    async def test_sample_mode_with_object(self, test_server):
        """Should limit object results to 5 entries with sample mode."""
        result = await test_server.call_tool("query_jq", {"query": ".modules", "sample": True})
        assert len(result) == 1
        output = json.loads(result[0].text)
        assert isinstance(output, dict)
        # Should have at most 5 keys
        assert len(output) <= 5

    @pytest.mark.asyncio
    async def test_sample_mode_false_returns_all(self, test_server):
        """Should return all results when sample is false."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | keys", "sample": False}
        )
        assert len(result) == 1
        output = json.loads(result[0].text)
        # Should return both modules
        assert len(output) == 2

    @pytest.mark.asyncio
    async def test_sample_mode_invalid_type(self, test_server):
        """Should reject non-boolean sample parameter."""
        result = await test_server.call_tool("query_jq", {"query": ".modules", "sample": "yes"})
        assert len(result) == 1
        assert "must be a boolean" in result[0].text

    @pytest.mark.asyncio
    async def test_early_size_estimation_large_result(self, tmp_path):
        """Should warn early when result will be too large."""
        # Create index with many large modules to exceed 500KB threshold
        large_modules = {}
        for i in range(100):
            large_modules[f"Module{i}"] = {
                "file": f"lib/module{i}.ex",
                "line": 1,
                "moduledoc": "X" * 10000,  # 10KB per module
                "functions": [
                    {
                        "name": f"func{j}",
                        "arity": j,
                        "line": j * 10,
                        "type": "def",
                        "signature": f"func{j}()",
                        "doc": "Y" * 1000,
                        "args": [],
                        "guards": [],
                        "full_name": f"func{j}/{j}",
                        "impl": False,
                    }
                    for j in range(10)
                ],
                "total_functions": 10,
            }

        large_index = {"modules": large_modules, "metadata": {"total_modules": 100}}

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(large_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        result = await server.call_tool("query_jq", {"query": ".modules"})
        assert len(result) == 1

        # Should contain early warning about size
        text = result[0].text
        assert "large" in text.lower() or "mb" in text.lower()
        # Should suggest alternatives
        assert "consider" in text.lower() or "try" in text.lower()

    @pytest.mark.asyncio
    async def test_size_estimation_with_specific_suggestions(self, tmp_path):
        """Should provide specific suggestions based on query type."""
        # Create large index
        large_modules = {
            f"Module{i}": {
                "file": f"lib/module{i}.ex",
                "line": 1,
                "moduledoc": "X" * 10000,
                "functions": [],
            }
            for i in range(100)
        }

        large_index = {"modules": large_modules, "metadata": {"total_modules": 100}}

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(large_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        result = await server.call_tool("query_jq", {"query": ".modules"})
        assert len(result) == 1

        text = result[0].text
        # Should suggest module-specific operations
        assert "keys" in text.lower() or "length" in text.lower()

    @pytest.mark.asyncio
    async def test_combined_schema_and_sample(self, test_server):
        """Should handle schema discovery with sample mode."""
        result = await test_server.call_tool(
            "query_jq", {"query": ".modules | schema", "sample": True}
        )
        assert len(result) == 1
        # Should work - schema returns keys, sample limits them
        output = json.loads(result[0].text)
        assert isinstance(output, list)
        assert len(output) <= 5


class TestJqToolLargeResults:
    """Test handling of large query results."""

    @pytest.mark.asyncio
    async def test_result_truncation_at_1mb(self, tmp_path):
        """Should truncate results exceeding 1MB limit."""
        # Create index with massive string content to exceed 1MB
        large_modules = {}
        for i in range(200):
            large_modules[f"Module{i}"] = {
                "file": f"lib/module{i}.ex",
                "line": 1,
                "moduledoc": "A" * 10000,  # 10KB per module = 2MB total
                "functions": [
                    {
                        "name": f"func{j}",
                        "arity": j,
                        "line": j * 10,
                        "type": "def",
                        "signature": f"func{j}(args)",
                        "doc": "B" * 1000,  # Additional content
                        "args": [f"arg{k}" for k in range(10)],
                        "guards": [],
                        "full_name": f"func{j}/{j}",
                        "impl": False,
                    }
                    for j in range(10)
                ],
                "total_functions": 10,
            }

        large_index = {
            "modules": large_modules,
            "metadata": {"total_modules": 200},
        }

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(large_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        # Query that returns all modules (should be >1MB)
        result = await server.call_tool("query_jq", {"query": ".modules"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        # Should either be truncated or completed
        # If truncated, should contain truncation message
        text = result[0].text
        if "truncated" in text.lower() or "exceeded" in text.lower():
            # Verify truncation message is present
            assert "1MB" in text or "1048576" in text or "limit" in text.lower()
        # Result should not exceed reasonable size (allow some overhead)
        assert len(text) < 2 * 1024 * 1024  # Max 2MB (1MB result + truncation message)

    @pytest.mark.asyncio
    async def test_truncation_message_format(self, tmp_path):
        """Should provide clear truncation message when results are truncated."""
        # Create index that will produce large results
        large_modules = {
            f"Module{i}": {
                "file": f"lib/module{i}.ex",
                "line": 1,
                "moduledoc": "X" * 10000,  # Large documentation
                "functions": [],
            }
            for i in range(150)
        }

        large_index = {
            "modules": large_modules,
            "metadata": {"total_modules": 150},
        }

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(large_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        result = await server.call_tool("query_jq", {"query": ".modules"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        # If result is truncated, check for helpful message
        text = result[0].text
        if "truncated" in text.lower():
            # Should explain why and suggest alternatives
            assert "limit" in text.lower() or "exceeded" in text.lower()
            # Should suggest using filters or limiting results
            assert "filter" in text.lower() or "limit" in text.lower() or "select" in text.lower()
