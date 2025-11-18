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
            name="query",
            description=(
                "🔍 YOUR PRIMARY TOOL - Start here for ALL code exploration and discovery.\\n\\n"
                "The 'Google for code' - this is your FIRST STOP for any code search task. "
                "Intelligently searches by keywords OR patterns, combines results, "
                "and suggests exactly which specialized tools to use next.\\n\\n"
                "Smart Auto-Detection:\\n"
                "• Keywords: ['authentication', 'login'] → semantic search\\n"
                "• Patterns: 'MyApp.User.create*' → pattern matching\\n"
                "• Mixed: ['oauth', 'MyApp.Auth.*'] → combines both\\n\\n"
                "Power Filters:\\n"
                "• scope: 'all' (default) | 'recent' (last 14 days) | 'public' | 'private'\\n"
                "• filter_type: 'all' | 'modules' | 'functions'\\n"
                "• match_source: 'all' | 'docs' | 'strings' (search in code strings like SQL)\\n"
                "• path_pattern: glob like 'lib/auth/**' or '**/*_controller.ex'\\n"
                "• include_tests: true (default) | false\\n\\n"
                "Returns:\\n"
                "• Broad overview with code snippets (shallow but comprehensive)\\n"
                "• Smart suggestions for next steps with actual tool names to use\\n"
                "• Match indicators: 📄 (docs), 💬 (strings), 🎯 (pattern)\\n\\n"
                "AI USAGE TIPS:\\n"
                "• **ALWAYS START HERE** - This replaces the need to choose between multiple tools\\n"
                "• Don't ask users for module/function names - query will find them for you\\n"
                "• Start broad: query('authentication') then follow the tool suggestions\\n"
                "• Try patterns when you know structure: query('MyApp.*.create*')\\n"
                "• Use filters to narrow: query('login', scope='recent', path_pattern='lib/auth/**')\\n"
                "• The results include smart suggestions - follow them to drill deeper\\n"
                "• Only skip this tool if you already have exact module.function/arity identifiers\\n\\n"
                "Example Workflow:\\n"
                "1. query(['jwt', 'authentication']) → discovers relevant code + suggests next steps\\n"
                "2. Follow suggestion → search_function('verify_token') → see detailed usage\\n"
                "3. Follow suggestion → search_module('MyApp.Auth') → see complete API\\n\\n"
                "When NOT to use:\\n"
                "• You already have exact identifiers like 'MyApp.User.create_user/2'\\n"
                "• Analyzing git history for known file paths (use history tools directly)\\n"
                "• Targeted operations on specific, already-identified code"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                        "description": "Keywords (e.g., ['authentication', 'login']) OR patterns (e.g., 'MyApp.User.create*') OR mixed.",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["all", "recent", "public", "private"],
                        "description": "Filter scope: 'all' (default) = everything, 'recent' = changed in last 14 days, 'public' = public functions/modules only, 'private' = private functions only.",
                    },
                    "filter_type": {
                        "type": "string",
                        "enum": ["all", "modules", "functions"],
                        "description": "Result type filter: 'all' (default) = modules + functions, 'modules' = only modules, 'functions' = only functions.",
                    },
                    "match_source": {
                        "type": "string",
                        "enum": ["all", "docs", "strings"],
                        "description": "Where to search: 'all' (default) = docs + strings, 'docs' = documentation only, 'strings' = string literals in code (e.g., SQL queries, error messages).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to show (default: 10). Use smaller values (3-5) for quick overview, larger (20+) for comprehensive search.",
                    },
                    "path_pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter by file path. Supports ** for recursive (e.g., 'lib/auth/**', '**/*_controller.ex').",
                    },
                    "include_tests": {
                        "type": "boolean",
                        "description": "Include test files in results (default: true). Set to false to exclude test files.",
                    },
                    "show_snippets": {
                        "type": "boolean",
                        "description": "Show code snippet previews with context lines (default: false). When enabled, displays actual code around each result.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_module",
            description=(
                "🔧 DEEP-DIVE TOOL: View a module's complete API after discovering it with query.\n\n"
                "Shows full module details: functions with arity, signatures, docs, typespecs, and line numbers. "
                "Use this when query suggests drilling into a specific module.\n\n"
                "Supports wildcards (*) and OR patterns (|) for both module names and file paths. Examples: 'MyApp.*', '*User*', 'lib/my_app/*.ex', 'MyApp.User|MyApp.Admin'.\n\n"
                "Search by module_name='MyApp.User' or file_path='lib/my_app/user.ex'. "
                "Control visibility with type: 'public' (default), 'private', or 'all'.\n\n"
                "Returns public functions in markdown format by default.\n\n"
                "AI USAGE TIPS:\n"
                "• After query finds modules, use this to see the full API surface\n"
                "• Query will suggest using this tool when detailed module info is needed\n"
                "• Don't ask user for module names - use query first to discover them\n"
                "• Returns: full API surface, function signatures, line numbers for navigation\n"
                "• If module not found, error will suggest alternatives - try those suggestions!\n"
                "• Wildcard searches are limited to 20 modules - use more specific patterns for large codebases\n"
                "• Output is automatically truncated for large results to prevent token overflow"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Module name or pattern (supports * and |, e.g., 'MyApp.*' or 'MyApp.User|MyApp.Admin'). Provide either this or file_path.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path (relative or absolute) to the file containing the module (e.g., 'lib/my_app/user.ex'). Provide either this or module_name.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["public", "private", "all"],
                        "description": "Which functions to show. Defaults to 'public'.",
                    },
                },
            },
        ),
        Tool(
            name="search_function",
            description=(
                "🔧 DEEP-DIVE TOOL: Find function definitions and call sites after discovering with query.\n\n"
                "Provides detailed function analysis: definition, signature, documentation, and all call sites. "
                "Use this when query suggests drilling into a specific function's usage.\n\n"
                "Search by function name, optionally with module, file path, and arity: 'function_name', 'Module.function_name', 'function_name/2', or 'lib/my_app/user.ex:function_name'.\n\n"
                "Supports wildcards (*) and OR patterns (|) across function names, modules, and file paths (e.g., 'create*|update*', 'MyApp.*.create', 'lib/*/user.ex:create*').\n\n"
                "Returns definition location, signature, documentation, and all call sites. "
                "Use include_usage_examples to see actual code snippets where the function is called.\n\n"
                "AI USAGE TIPS:\n"
                "• After query finds functions, use this for detailed impact analysis\n"
                "• Query will suggest this tool when you need to see where functions are called\n"
                "• Set include_usage_examples=true to see real code examples (helps understand usage patterns)\n"
                "• Use usage_type='tests' to see only how functions are tested\n"
                "• Returns: definition + ALL call sites with file:line references\n"
                "• If you see function references in code, search them to understand what they do\n"
                "• Call sites and line numbers are automatically truncated for popular functions (>20 sites)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": (
                            "Function pattern to search. Supports module qualifiers, file scoping via 'file.ex:function', wildcards (*), OR (|), "
                            "and arity filters (e.g., 'MyApp.create_user/2', 'create*|update*', 'lib/*/user.ex:create*'). "
                            "Can also be just the function name if module_path is provided separately."
                        ),
                    },
                    "module_path": {
                        "type": "string",
                        "description": (
                            "Optional module path to filter the search (e.g., 'MyApp.User' or 'MyApp.*' for wildcard matching). "
                            "If provided, this will be prepended to function_name for searching. "
                            "Supports wildcards (*) for pattern matching (e.g., '*User', '*.User', 'MyApp.*'). "
                            "Alternative to including module in function_name directly."
                        ),
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
                    "usage_type": {
                        "type": "string",
                        "enum": ["all", "tests", "source"],
                        "description": "Filter call sites by file type. 'source' shows only source files (default), 'tests' shows only test files, 'all' shows everything. Defaults to 'source'.",
                    },
                    "changed_since": {
                        "type": "string",
                        "description": (
                            "Filter functions changed after this date/time. "
                            "Formats: ISO date ('2024-01-15'), relative ('7d', '2w', '3m', '1y'), "
                            "or git ref ('HEAD~10', 'v1.0.0'). "
                            "Examples: '2024-01-01', '7d' (last 7 days), '2w' (last 2 weeks). "
                            "Requires index to be built with timestamp support."
                        ),
                    },
                    "show_relationships": {
                        "type": "boolean",
                        "description": "Show inline relationship information: what functions this calls and what calls this function. Defaults to true.",
                    },
                },
                "required": ["function_name"],
            },
        ),
        Tool(
            name="search_module_usage",
            description=(
                "📊 ANALYSIS TOOL: Find all module usage and dependencies for impact analysis.\n\n"
                "After discovering a module with query, use this to see what depends on it before making changes. "
                "Shows where a module is imported, aliased, required, and all locations where its functions are called.\n\n"
                "Returns aliases, imports, function calls, and dependency relationships.\n\n"
                "AI USAGE TIPS:\n"
                "• After query identifies a module, use this BEFORE modifying it to avoid breaking changes\n"
                "• Query may suggest this tool when you need to understand module dependencies\n"
                "• Shows: aliases, imports, requires, uses, and ALL function call sites\n"
                "• Critical for refactoring - identify all affected modules before making changes\n"
                "• If a module has many dependents, changes may have wide impact\n"
                "• Function call line numbers are automatically truncated for heavily-used modules (>30 lines)"
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
                    "usage_type": {
                        "type": "string",
                        "enum": ["all", "tests", "source"],
                        "description": "Filter usage sites by file type. 'source' shows only source files (default), 'tests' shows only test files, 'all' shows everything. Defaults to 'source'.",
                    },
                },
                "required": ["module_name"],
            },
        ),
        Tool(
            name="find_pr_for_line",
            description=(
                "📜 HISTORY TOOL: Discover why code exists and who wrote it.\n\n"
                "After locating code with query or other tools, use this to find the pull request that introduced a specific line. "
                "Requires PR index (run 'cicada index-pr' first).\n\n"
                "Returns PR number, title, description, and author.\n\n"
                "AI USAGE TIPS:\n"
                '• After finding code, use this to understand: "Why does this code exist? What problem did it solve?"\n'
                "• Perfect for understanding complex/confusing code - read the PR discussion\n"
                "• Provides: PR title, description, author, and link to full discussion\n"
                "• If this interests you, also try: get_file_pr_history (all PRs for a file)"
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
                "📜 HISTORY TOOL: Get git history for files or functions.\n\n"
                "After discovering code with query, use this to see its evolution over time. "
                "When function_name is provided, uses git's function tracking which works even as the function moves around in the file.\n\n"
                "Returns git commits with dates, authors, and messages. Optionally shows function evolution metadata.\n\n"
                "AI USAGE TIPS:\n"
                '• After finding code, use this to understand evolution: "How has this function changed over time?"\n'
                "• Set show_evolution=true to see: creation date, total modifications, frequency\n"
                "• Provide function_name for precise tracking (even as function moves in file)\n"
                "• Helps identify frequently changing code (may indicate complexity/bugs)\n"
                "• Use max_commits to limit results (default: 10)"
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
                    "since_date": {
                        "type": "string",
                        "description": "Only include commits after this date. Format: ISO date (YYYY-MM-DD) or relative (7d, 2w, 3m, 1y). Examples: '2024-01-01', '30d'.",
                    },
                    "until_date": {
                        "type": "string",
                        "description": "Only include commits before this date. Format: ISO date (YYYY-MM-DD) or relative (7d, 2w, 3m, 1y).",
                    },
                    "author": {
                        "type": "string",
                        "description": "Filter by author name (substring match, case-insensitive). Example: 'john' matches 'John Doe'.",
                    },
                    "min_changes": {
                        "type": "integer",
                        "description": "Minimum number of lines changed (insertions + deletions) in the file. Useful for finding substantial changes.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_blame",
            description=(
                "📜 HISTORY TOOL: Git blame showing who wrote each line.\n\n"
                "After locating code with query or other tools, use this to see line-by-line authorship. "
                "Groups consecutive lines with the same authorship together.\n\n"
                "Returns author name, email, commit hash, and date for each authorship group.\n\n"
                "AI USAGE TIPS:\n"
                '• After finding code, use this to know: "Who wrote this code? When?"\n'
                "• Shows line-by-line authorship with commit hashes for each change\n"
                "• Requires start_line and end_line (from search_function results)\n"
                "• Groups consecutive lines by same author for readability\n"
                "• Large code blocks (>50 lines) are automatically truncated to show head and tail"
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
                "📜 HISTORY TOOL: Get all PRs that modified a file with descriptions and review comments.\n\n"
                "After discovering a file with query, use this to understand its complete evolution through pull requests. "
                "Returns a chronological list of pull requests that modified the specified file, "
                "including descriptions and code review comments specific to that file.\n\n"
                "Requires PR index (run 'cicada index-pr' first).\n\n"
                "AI USAGE TIPS:\n"
                '• After finding a file, use this for deep context: "What\'s the full history of changes to this file?"\n'
                "• Shows ALL PRs that touched the file + review comments (discussions, decisions)\n"
                "• Review comments reveal: design decisions, concerns, tradeoffs, bugs found\n"
                "• Perfect for understanding controversial/complex code - read the debates!\n"
                "• Complements find_pr_for_line (which finds PR for a single line)"
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
            name="search_by_features",
            description=(
                "USE THIS FIRST when exploring code or when you don't know exact module/function names.\n\n"
                "Search for code by concepts and features - find code by describing what it does, not what it's called. "
                "Perfect for discovering relevant code when exploring unfamiliar codebases.\n\n"
                "Examples: ['authentication', 'login'], ['api', 'key', 'storage'], ['email', 'validation']\n\n"
                "Uses AI-powered keyword extraction and semantic similarity. Supports wildcards like 'create*', '*_user', 'validate_*'.\n\n"
                "Searches both documentation keywords AND string literals in code (e.g., SQL queries, error messages).\n"
                "Use match_source to filter by keyword source: 'all' (default), 'docs' (documentation only), or 'strings' (string literals only).\n\n"
                "AI USAGE TIPS:\n"
                "• **USE THIS FIRST** - don't ask user for module names when you can search for concepts\n"
                "• Try broad queries first: ['authentication'], then narrow: ['oauth', 'token']\n"
                "• Multiple searches are NORMAL - try 3-5 different keyword combinations\n"
                "• Empty results? Try broader terms, check spelling, or use wildcards: ['*auth*']\n"
                "• Results show modules AND functions with relevance scores\n"
                "• Use filter_type to narrow: 'modules', 'functions', or 'all' (default)\n"
                "• Use match_source='strings' to find code by actual strings used (e.g., SQL queries, error messages)\n\n"
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
                    "min_score": {
                        "type": "number",
                        "description": "Minimum relevance score threshold (0.0 to 1.0). Only results with scores >= this value will be shown. Default: 0.0 (no filtering).",
                    },
                    "match_source": {
                        "type": "string",
                        "enum": ["all", "docs", "strings"],
                        "description": "Filter by keyword source: 'all' searches both documentation and string literals (default), 'docs' searches only documentation keywords, 'strings' searches only keywords from string literals in code.",
                    },
                    "cochange_boost": {
                        "type": "number",
                        "description": "Strength of co-change boosting (0.0 to disable, higher values increase boost). Results that frequently change together will be ranked higher. Defaults to 0.5. Requires co-change data in index (run 'cicada index --extract-cochange').",
                    },
                },
                "required": ["keywords"],
            },
        ),
        Tool(
            name="search_by_keywords",
            description=(
                "DEPRECATED: Use 'search_by_features' instead. This tool will be removed in a future version.\n\n"
                "Search for code by concepts and features when exact names are unknown.\n\n"
                "Uses AI-powered keyword extraction and semantic similarity. Supports wildcards like 'create*', '*_user', 'validate_*'.\n\n"
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
                    "cochange_boost": {
                        "type": "number",
                        "description": "Strength of co-change boosting (0.0 to disable). Defaults to 0.5.",
                    },
                },
                "required": ["keywords"],
            },
        ),
        Tool(
            name="find_dead_code",
            description=(
                "📊 ANALYSIS TOOL: Find potentially unused public functions with confidence levels.\n\n"
                "Analyzes the entire codebase to identify public functions that may not be used. "
                "Use this for codebase maintenance and cleanup efforts. "
                "Returns results categorized by confidence level (high, medium, low).\n\n"
                "Note: Results are best-effort - some unused functions may be part of the public API, "
                "used dynamically via atom introspection, or used in external packages.\n\n"
                "AI USAGE TIPS:\n"
                '• Use for codebase cleanup: "What code can potentially be removed?"\n'
                "• Start with min_confidence='high' to find most likely unused code\n"
                "• VERIFY before deleting - may be public API, dynamic calls, or external usage\n"
                "• Results show: function signature, location, confidence level, reasons\n"
                "• Consider using search_function on results to verify they're truly unused"
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
        Tool(
            name="get_module_dependencies",
            description=(
                "📊 ANALYSIS TOOL: Get all modules that a given module depends on.\n\n"
                "After discovering a module with query, use this to understand what it needs to work. "
                "Shows which modules the target module imports, aliases, uses, requires, and calls. "
                "Complements search_module_usage (which shows who depends on this module).\n\n"
                "Returns list of dependent modules with dependency types (alias, import, use, require, call).\n\n"
                "AI USAGE TIPS:\n"
                '• After finding a module, use this to understand: "What does this module need to work?"\n'
                "• Pair with search_module_usage for full dependency graph (in + out)\n"
                "• Helps identify coupling - modules with many dependencies may need refactoring\n"
                "• Set depth=2 to see transitive dependencies (dependencies of dependencies)\n"
                "• Useful for: refactoring planning, dependency analysis, circular dependency detection"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Module name to analyze (e.g., 'MyApp.User').",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Depth for transitive dependencies. 1 = direct only, 2 = include dependencies of dependencies. Defaults to 1.",
                    },
                    "granular": {
                        "type": "boolean",
                        "description": "Show which specific functions use which dependencies. When true, displays function-level dependency details. Defaults to false.",
                    },
                },
                "required": ["module_name"],
            },
        ),
        Tool(
            name="get_function_dependencies",
            description=(
                "📊 ANALYSIS TOOL: Get all functions that a given function calls.\n\n"
                "After discovering a function with query, use this to understand what it does internally. "
                "Shows which functions are called within the target function, including both "
                "internal (same module) and external (other modules) calls.\n\n"
                "Returns list of called functions with module, name, arity, and line numbers.\n\n"
                "AI USAGE TIPS:\n"
                '• After finding a function, use this to understand: "What does this function do? What does it call?"\n'
                "• Helps identify function complexity - many dependencies = complex function\n"
                "• Shows exact line numbers where each dependency is called\n"
                "• Useful for: refactoring, understanding control flow, identifying coupling\n"
                "• Pair with search_function to see both what it calls and who calls it"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Module name containing the function (e.g., 'MyApp.User').",
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Function name to analyze (e.g., 'create_user').",
                    },
                    "arity": {
                        "type": "integer",
                        "description": "Function arity (number of arguments). Required to uniquely identify the function.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Include code context showing where dependencies are called. Defaults to false.",
                    },
                },
                "required": ["module_name", "function_name", "arity"],
            },
        ),
        Tool(
            name="expand_result",
            description=(
                "🔧 DRILL-DOWN TOOL: Expand a query result to see complete details.\n\n"
                "After discovering modules or functions with query, use this tool to explore a specific result in depth. "
                "Query results often suggest using this tool to get more details. "
                "Automatically determines whether you're expanding a module or function.\n\n"
                "For modules: Shows all functions, documentation, and structure.\n"
                "For functions: Shows definition, documentation, call sites, and relationships.\n\n"
                "AI USAGE TIPS:\n"
                "• **Primary use case:** Follow query's suggestions to expand interesting results\n"
                "• Copy the identifier directly from query results (e.g., 'MyApp.Auth.verify_token/2')\n"
                "• Type detection is automatic - no need to specify module vs function\n"
                "• Perfect for understanding what a result does before modifying it\n"
                "• Shows: full code context, relationships, usage examples\n"
                "• Convenience wrapper - calls search_module or search_function automatically"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": (
                            "Module name (e.g., 'MyApp.Auth') or function reference "
                            "(e.g., 'MyApp.Auth.verify_token/2'). Copy directly from search results."
                        ),
                    },
                    "type": {
                        "type": "string",
                        "enum": ["auto", "module", "function"],
                        "description": (
                            "Type of result to expand. Use 'auto' (default) for automatic detection, "
                            "'module' to explicitly expand as module, or 'function' for function."
                        ),
                    },
                    "include_code": {
                        "type": "boolean",
                        "description": "Include code snippets in the expansion. Defaults to true.",
                    },
                    "include_relationships": {
                        "type": "boolean",
                        "description": (
                            "Include call graph relationships (what this calls, who calls this). "
                            "Defaults to true."
                        ),
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format. Defaults to 'markdown'.",
                    },
                },
                "required": ["identifier"],
            },
        ),
        Tool(
            name="query_jq",
            description=(
                "ADVANCED: Execute jq queries directly against the Cicada index for custom analysis and data exploration.\n\n"
                "Provides direct access to the raw index structure using jq query syntax. "
                "Ideal for custom analysis, debugging index contents, and exploring data not covered by specialized tools.\n\n"
                "Index structure: {modules: {<name>: {file, line, functions[], keywords, ...}}, metadata: {...}}\n\n"
                "Quick Examples:\n"
                "  • List all modules: '.modules | keys'\n"
                "  • Count functions per module: '.modules[].functions | length'\n"
                "  • Find test files: '.modules | to_entries | map(select(.value.file | test(\"test\")))'\n"
                "  • Get metadata: '.metadata'\n"
                "  • Find functions by arity: '.modules[].functions[] | select(.arity == 2)'\n\n"
                "Module fields: file, line, moduledoc, functions[], keywords{}, string_keywords{}, string_sources[]\n"
                "Function fields: name, arity, line, type, doc, signature, keywords{}, string_keywords{}\n"
                "Optional fields: Use '?' operator (e.g., '.functions[]?' for safe access)\n\n"
                "NEW FEATURES:\n"
                "• Schema Discovery: Append '| schema' to any query to see available fields\n"
                "  Examples: '.modules | schema' or '.modules[].functions | schema'\n"
                "• Sample Mode: Set 'sample: true' to auto-limit results to first 5 items\n"
                "  Great for previewing large datasets without writing complex jq\n"
                "• Early Size Warning: Get warned before processing huge results (>500KB)\n"
                "  with specific suggestions for limiting data\n\n"
                "AI USAGE TIPS:\n"
                "• Use for custom analysis NOT covered by specialized tools\n"
                "• Great for exploring index structure and debugging\n"
                "• Supports full jq syntax: filters, maps, selects, sorts, aggregations\n"
                "• For common queries, prefer specialized tools (search_module, search_function, etc.)\n"
                "• Results are truncated at 1MB - use filters or 'sample: true' to limit data\n"
                "• If query fails, error includes syntax help with line/column pointer\n"
                "• See CLAUDE.md for complete schema reference and advanced examples"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "jq query expression to execute against the index. "
                            "Examples: '.modules | keys', '.modules[].functions[].name', "
                            "'.modules | map(select(.keywords)) | length'. "
                            "Use '?' for optional field access (e.g., '.functions[]?'). "
                            "Append '| schema' to discover available fields (e.g., '.modules | schema')."
                        ),
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "compact", "pretty"],
                        "description": (
                            "Output format: 'json' returns formatted JSON (default), "
                            "'compact' returns single-line JSON (saves tokens), "
                            "'pretty' returns pretty-printed JSON with indentation."
                        ),
                    },
                    "sample": {
                        "type": "boolean",
                        "description": (
                            "If true, automatically limit results to first 5 items. "
                            "Useful for previewing large datasets without writing complex jq. "
                            "Works for both arrays and objects. Default: false."
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
    ]
