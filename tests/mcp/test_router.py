"""Tests for cicada/mcp/router.py - routing and validation."""

import pytest
from unittest.mock import AsyncMock, Mock
from mcp.types import TextContent

from cicada.mcp.router import (
    ToolRouter,
    _validate_jq_query,
    _check_bracket_nesting,
    MAX_JQ_QUERY_LENGTH,
    MAX_JQ_NESTING_DEPTH,
)


@pytest.fixture
def router():
    """Create a router with mocked handlers."""
    return ToolRouter(
        module_handler=Mock(),
        function_handler=Mock(),
        git_handler=Mock(),
        pr_handler=Mock(),
        dependency_handler=Mock(),
        analysis_handler=Mock(),
    )


@pytest.mark.asyncio
async def test_unknown_tool(router):
    """Test ValueError for unknown tool name."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await router.route_tool("nonexistent_tool", {})


class TestJqQueryValidation:
    """Test jq query validation functions."""

    def test_validate_empty_query(self):
        """Test that empty query returns error."""
        assert _validate_jq_query(None) == "'query' is required"
        # Empty string is also treated as "required" before the strip check
        result = _validate_jq_query("")
        assert "'query'" in result
        result = _validate_jq_query("   ")
        assert "empty" in result

    def test_validate_non_string_query(self):
        """Test that non-string query returns error."""
        assert _validate_jq_query(123) == "'query' must be a string"

    def test_validate_too_long_query(self):
        """Test that too long query returns error."""
        long_query = "." * (MAX_JQ_QUERY_LENGTH + 1)
        result = _validate_jq_query(long_query)
        assert "exceeds maximum length" in result

    def test_validate_valid_query(self):
        """Test that valid query returns None."""
        assert _validate_jq_query(".foo") is None
        assert _validate_jq_query(".[] | select(.x > 0)") is None

    def test_validate_deeply_nested_query(self):
        """Test that deeply nested query returns error."""
        deep_query = "[" * (MAX_JQ_NESTING_DEPTH + 1) + "]" * (MAX_JQ_NESTING_DEPTH + 1)
        result = _validate_jq_query(deep_query)
        assert "nesting depth" in result


class TestBracketNesting:
    """Test bracket nesting validation."""

    def test_balanced_brackets(self):
        """Test that balanced brackets pass validation."""
        depth, error = _check_bracket_nesting("[]")
        assert error is None
        assert depth == 1

        depth, error = _check_bracket_nesting("[[[]]]")
        assert error is None
        assert depth == 3

    def test_mixed_balanced_brackets(self):
        """Test that mixed balanced brackets pass."""
        depth, error = _check_bracket_nesting("[()]")
        assert error is None
        depth, error = _check_bracket_nesting("[({})]")
        assert error is None

    def test_unbalanced_closing(self):
        """Test that unexpected closing bracket fails."""
        depth, error = _check_bracket_nesting("]")
        assert "unexpected ']'" in error

    def test_mismatched_brackets(self):
        """Test that mismatched brackets fail."""
        depth, error = _check_bracket_nesting("[)")
        assert "Mismatched brackets" in error

    def test_unclosed_brackets(self):
        """Test that unclosed brackets fail."""
        depth, error = _check_bracket_nesting("[")
        assert "Unclosed brackets" in error

    def test_unterminated_string(self):
        """Test that unterminated string fails."""
        depth, error = _check_bracket_nesting('"unclosed')
        assert "Unterminated string" in error

    def test_brackets_in_strings_ignored(self):
        """Test that brackets inside strings are ignored."""
        depth, error = _check_bracket_nesting('"[]]"')
        assert error is None

    def test_escaped_quotes(self):
        """Test that escaped quotes are handled."""
        depth, error = _check_bracket_nesting('"test\\"quote"')
        assert error is None

    def test_empty_query(self):
        """Test that empty query has zero depth."""
        depth, error = _check_bracket_nesting("")
        assert error is None
        assert depth == 0
