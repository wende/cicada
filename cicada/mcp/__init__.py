"""Cicada MCP (Model Context Protocol) Server package.

This package contains the MCP server implementation for Cicada,
providing Elixir code search and analysis capabilities via the MCP standard.
"""

# Note: Avoid importing server.py at package level to prevent circular dependencies
# and optional dependency issues. Users should import directly:
# from cicada.mcp.server import CicadaServer, async_main, main
# from cicada.mcp.tools import get_tool_definitions
