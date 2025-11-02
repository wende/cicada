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
                        "description": "Path to the file containing the module (e.g., 'lib/my_app/user.ex'). Provide either this or module_name.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                    "private_functions": {
                        "type": "string",
                        "enum": ["exclude", "include", "only"],
                        "description": "Control private function visibility. Defaults to 'exclude'.",
                    },
                },
            },
        ),
        Tool(
            name="search_function",
            description=(
                "PREFERRED for Elixir: Find function definitions and call sites across the codebase.\n\n"
                "Search by function name, optionally with module and arity: 'function_name', 'Module.function_name', or 'function_name/2'.\n\n"
                "Returns definition location, signature, documentation, and all call sites. "
                "Use include_usage_examples to see actual code snippets where the function is called."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Function name to search. Can include module and/or arity: 'MyApp.create_user', 'create_user/2', 'MyApp.create_user/2'.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                    "include_usage_examples": {
                        "type": "boolean",
                        "description": "Include actual code snippets showing how the function is called. Defaults to false.",
                    },
                    "max_examples": {
                        "type": "integer",
                        "description": "Maximum number of code examples to include. Defaults to 5.",
                    },
                    "test_files_only": {
                        "type": "boolean",
                        "description": "Only show call sites from test files. Defaults to false.",
                    },
                },
                "required": ["function_name"],
            },
        ),
        Tool(
            name="search_module_usage",
            description=(
                "PREFERRED for Elixir: Find all module usage and dependencies for impact analysis.\n\n"
                "Shows where a module is imported, aliased, required, and all locations where its functions are called.\n\n"
                "Returns aliases, imports, function calls, and dependency relationships."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Module name to search (e.g., 'MyApp.User').",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                },
                "required": ["module_name"],
            },
        ),
        Tool(
            name="find_pr_for_line",
            description=(
                "PREFERRED for git history: Discover why code exists and who wrote it.\n\n"
                "Find the pull request that introduced a specific line of code. "
                "Requires PR index (run 'cicada index-pr' first).\n\n"
                "Returns PR number, title, description, and author."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root).",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number in the file (1-indexed).",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "json", "markdown"],
                        "description": "Output format. Defaults to 'text'.",
                    },
                },
                "required": ["file_path", "line_number"],
            },
        ),
        Tool(
            name="get_commit_history",
            description=(
                "PREFERRED for git history: Get commit log for files or functions.\n\n"
                "Get the git commit history for a file or function. When function_name is provided, uses git's "
                "function tracking which works even as the function moves around in the file.\n\n"
                "Returns commits with dates, authors, and messages. Optionally shows function evolution metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root).",
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Optional: Function name for function-level tracking. Uses git log -L :funcname:file for precise tracking.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional: Starting line for line-range tracking. Required with end_line for line-based history.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional: Ending line for line-range tracking. Required with start_line for line-based history.",
                    },
                    "precise_tracking": {
                        "type": "boolean",
                        "description": "Deprecated - function tracking is automatic when function_name provided.",
                    },
                    "show_evolution": {
                        "type": "boolean",
                        "description": "Show function evolution metadata (creation date, last modification, modification frequency). Defaults to false.",
                    },
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to return. Defaults to 10.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_blame",
            description=(
                "PREFERRED for authorship: Git blame showing who wrote each line.\n\n"
                "Get line-by-line authorship information for a code section using git blame. "
                "Groups consecutive lines with the same authorship together.\n\n"
                "Returns author name, email, commit hash, and date for each authorship group."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root).",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-indexed).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (1-indexed, inclusive).",
                    },
                },
                "required": ["file_path", "start_line", "end_line"],
            },
        ),
        Tool(
            name="get_file_pr_history",
            description=(
                "Get all PRs that modified a file with descriptions and review comments.\n\n"
                "Returns a chronological list of pull requests that modified the specified file, "
                "including descriptions and code review comments specific to that file.\n\n"
                "Requires PR index (run 'cicada index-pr' first)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root or absolute).",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="search_by_keywords",
            description=(
                "Semantic search for code by concept/topic when exact names are unknown.\n\n"
                "Search for modules and functions by keywords extracted from documentation. "
                "Uses semantic similarity to find related functions even if they don't match the exact name.\n\n"
                "Requires keywords in index (run 'cicada index' first - uses semantic extraction by default)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keywords to search for (e.g., ['authentication', 'login']).",
                    },
                    "filter_type": {
                        "type": "string",
                        "enum": ["all", "modules", "functions"],
                        "description": "Filter results to include only modules, only functions, or all results (default: 'all').",
                    },
                },
                "required": ["keywords"],
            },
        ),
        Tool(
            name="find_dead_code",
            description=(
                "Find potentially unused public functions with confidence levels.\n\n"
                "Analyzes the codebase to identify public functions that may not be used. "
                "Returns results categorized by confidence level (high, medium, low).\n\n"
                "Note: Results are best-effort - some unused functions may be part of the public API, "
                "used dynamically via atom introspection, or used in external packages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "min_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Minimum confidence level for dead code detection. Defaults to 'high'.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                },
            },
        ),
    ]
