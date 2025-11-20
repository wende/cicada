"""
MCP Tool Handlers.

This package contains handlers for different MCP tool categories.
Each handler encapsulates the business logic for a specific set of related tools.
"""

from cicada.mcp.handlers.analysis_handlers import AnalysisHandler
from cicada.mcp.handlers.function_handlers import FunctionSearchHandler
from cicada.mcp.handlers.git_handlers import GitHistoryHandler
from cicada.mcp.handlers.module_handlers import ModuleSearchHandler
from cicada.mcp.handlers.pr_handlers import PRHistoryHandler

__all__ = [
    "AnalysisHandler",
    "FunctionSearchHandler",
    "GitHistoryHandler",
    "ModuleSearchHandler",
    "PRHistoryHandler",
]
