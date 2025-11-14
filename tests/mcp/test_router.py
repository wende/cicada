"""Minimal tests for cicada/mcp/router.py to improve coverage."""

import pytest
from unittest.mock import AsyncMock, Mock
from mcp.types import TextContent

from cicada.mcp.router import ToolRouter


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
async def test_get_module_dependencies_missing_module_name(router):
    """Test ValueError when module_name is missing."""
    with pytest.raises(ValueError, match="module_name is required"):
        await router.route_tool("get_module_dependencies", {})


@pytest.mark.asyncio
async def test_get_function_dependencies_missing_params(router):
    """Test ValueError for missing required parameters."""
    with pytest.raises(ValueError, match="module_name is required"):
        await router.route_tool("get_function_dependencies", {})

    with pytest.raises(ValueError, match="function_name is required"):
        await router.route_tool("get_function_dependencies", {"module_name": "M"})

    with pytest.raises(ValueError, match="arity is required"):
        await router.route_tool(
            "get_function_dependencies", {"module_name": "M", "function_name": "f"}
        )


@pytest.mark.asyncio
async def test_unknown_tool(router):
    """Test ValueError for unknown tool name."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await router.route_tool("nonexistent_tool", {})
