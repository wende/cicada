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
async def test_unknown_tool(router):
    """Test ValueError for unknown tool name."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await router.route_tool("nonexistent_tool", {})
