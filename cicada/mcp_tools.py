"""
Tool definitions for Cicada MCP Server.

This module contains all tool schemas that define the interface
for the Cicada MCP server without any implementation logic.
"""

from mcp.types import Tool


def get_tool_definitions() -> list[Tool]:
    """Return all tool definitions for the Cicada MCP server."""
    return [
        Tool(
            name="search_module",
            description=(
                "PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers.\n\n"
                "Search by module_name='MyApp.User' or file_path='lib/my_app/user.ex'. "
                "Control visibility with private_functions: 'exclude' (default), 'include', or 'only'.\n\n"
                "Returns public functions in markdown format by default. Start here when exploring modules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Full module name to search (e.g., 'MyApp.User'). Provide either this or file_path.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to an Elixir file (e.g., 'lib/my_app/user.ex'). Provide either this or module_name.",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'markdown' (default) or 'json'",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                    "private_functions": {
                        "type": "string",
                        "description": "How to handle private functions: 'exclude' (default, hide private functions), 'include' (show all functions), or 'only' (show only private functions)",
                        "enum": ["exclude", "include", "only"],
                        "default": "exclude",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="search_function",
            description=(
                "PREFERRED for Elixir: Find function definitions and call sites across the codebase.\n\n"
                "Search formats: 'create_user', 'create_user/2', or 'MyApp.User.create_user'. "
                "Returns definition with full signature, docs, typespecs, and call sites (module, function, line number). "
                "Set include_usage_examples=true and max_examples=N for code snippets, test_files_only=true for test usage only.\n\n"
                "Tip: Start without usage examples for quick overview, then enable for usage patterns."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Function name to search. Formats: 'create_user', 'create_user/2' (all modules), or 'MyApp.User.create_user', 'MyApp.User.create_user/2' (specific module)",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'markdown' (default) or 'json'",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                    "include_usage_examples": {
                        "type": "boolean",
                        "description": "Include actual code lines showing how the function is called (default: false)",
                        "default": False,
                    },
                    "max_examples": {
                        "type": "integer",
                        "description": "Maximum number of usage examples to show per function (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "test_files_only": {
                        "type": "boolean",
                        "description": "Only show calls from test files (files with 'test' in their path) (default: false)",
                        "default": False,
                    },
                },
                "required": ["function_name"],
            },
        ),
        Tool(
            name="search_module_usage",
            description=(
                "PREFERRED for Elixir: Find all module usage and dependencies for impact analysis.\n\n"
                "Provide module_name='MyApp.User' to see aliases, imports, requires, uses, function calls, and line numbers. "
                "Essential for understanding scope before refactoring."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Full module name to search for usage (e.g., 'MyApp.User')",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'markdown' (default) or 'json'",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["module_name"],
            },
        ),
        Tool(
            name="find_pr_for_line",
            description=(
                "PREFERRED for git history: Discover why code exists and who wrote it.\n\n"
                "Provide file_path and line_number to get PR number, title, author, commit SHA, message, date, and PR link. "
                "Better than git blame - shows full PR context. Cached for fast lookups."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root or absolute)",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number (1-indexed)",
                        "minimum": 1,
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'text' (default), 'json', or 'markdown'",
                        "enum": ["text", "json", "markdown"],
                        "default": "text",
                    },
                },
                "required": ["file_path", "line_number"],
            },
        ),
        Tool(
            name="get_commit_history",
            description=(
                "PREFERRED for git history: Get commit log for files or functions.\n\n"
                "Provide file_path for full history. Add function_name for heuristic search, or start_line/end_line with precise_tracking=True for git log -L. "
                "Returns commit SHA, author, date, message. Set show_evolution=True for creation/modification metadata.\n\n"
                "Complements find_pr_for_line with full commit history."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root)",
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Optional: function name for heuristic search (filters by function name in commits)",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional: starting line number of function (for precise tracking)",
                        "minimum": 1,
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional: ending line number of function (for precise tracking)",
                        "minimum": 1,
                    },
                    "precise_tracking": {
                        "type": "boolean",
                        "description": "Use git log -L for exact line-range tracking (requires start_line and end_line). More accurate than heuristic search. (default: False)",
                        "default": False,
                    },
                    "show_evolution": {
                        "type": "boolean",
                        "description": "Include function evolution metadata: creation date, last modified, total modifications (requires start_line and end_line). (default: False)",
                        "default": False,
                    },
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_blame",
            description=(
                "PREFERRED for authorship: Git blame showing who wrote each line.\n\n"
                "Provide file_path, start_line, and end_line to see author, email, commit SHA, date, and code content grouped by author/commit."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root)",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number of the code section",
                        "minimum": 1,
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number of the code section",
                        "minimum": 1,
                    },
                },
                "required": ["file_path", "start_line", "end_line"],
            },
        ),
        Tool(
            name="get_file_pr_history",
            description=(
                "Get all PRs that modified a file with descriptions and review comments.\n\n"
                "Provide file_path to see PR number, title, URL, body, author, merge status, and review comments (with line numbers). "
                "Sorted newest first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root or absolute)",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="search_by_keywords",
            description=(
                "Semantic search for code by concept/topic when exact names are unknown.\n\n"
                "Supports wildcards: keywords=['create*', 'test_*'] or concepts: keywords=['authentication', 'user']. "
                "Returns top 5 results by confidence with matched keywords and location."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keywords to search for (e.g., ['performance', 'benchmark', 'test'] or ['create*', 'test_*'] for wildcards)",
                    },
                },
                "required": ["keywords"],
            },
        ),
        Tool(
            name="find_dead_code",
            description=(
                "Find potentially unused public functions with confidence levels.\n\n"
                "Returns unused functions grouped by confidence: high (likely dead), medium (possible callbacks), low (possible dynamic calls). "
                "Filter with min_confidence='high' (default), 'medium', or 'low'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "min_confidence": {
                        "type": "string",
                        "description": "Minimum confidence level: 'high' (default, zero usage + no indicators), 'medium' (zero usage + behaviors/uses), 'low' (all candidates)",
                        "enum": ["high", "medium", "low"],
                        "default": "high",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'markdown' (default) or 'json'",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": [],
            },
        ),
    ]
