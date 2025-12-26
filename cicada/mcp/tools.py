"""
Tool definitions for Cicada MCP Server.

This module contains all tool schemas that define the interface
for the Cicada MCP server without any implementation logic.
"""

from mcp.types import Tool

# =============================================================================
# Tool Descriptions
# =============================================================================

QUERY_DESCRIPTION = (
    "YOUR PRIMARY TOOL - Start here for ALL code exploration and discovery.\\n\\n"
    "The 'Google for code' - this is your FIRST STOP for any code search task. "
    "Intelligently searches by keywords OR patterns, combines results, "
    "and suggests exactly which specialized tools to use next.\\n\\n"
    "Smart Auto-Detection:\\n"
    "• Keywords: ['authentication', 'login'] → semantic search\\n"
    "• Patterns: 'MyApp.User.create*' → pattern matching\\n"
    "• Mixed: ['oauth', 'MyApp.Auth.*'] → combines both\\n\\n"
    "Power Filters:\\n"
    "• scope: 'all' (default) | 'public' | 'private'\\n"
    "• result_type: 'all' | 'modules' | 'functions'\\n"
    "• match_source: 'all' | 'docs' | 'strings' (search in code strings like SQL)\\n"
    "• recent: false (default) | true (last 14 days only)\\n"
    "• glob: glob pattern like 'lib/auth/**' or '**/*_controller.ex'\\n"
    "• path: base directory to search in (e.g., 'lib/auth')\\n"
    "• type: file type shorthand (e.g., 'py', 'ex', 'ts')\\n\\n"
    "Returns:\\n"
    "• Compact results with essential info (verbose=true for full details)\\n"
    "• Smart suggestions for next steps with actual tool names to use\\n"
    "• Match indicators: (d) docs, (s) strings, (d+s) both\\n"
    "• Search source: (k) keyword, (s) semantic, (k+s) both (hybrid mode)\\n\\n"
    "AI USAGE TIPS:\\n"
    "• **ALWAYS START HERE** - This replaces the need to choose between multiple tools\\n"
    "• Don't ask users for module/function names - query will find them for you\\n"
    "• Start broad: query('authentication') then follow the tool suggestions\\n"
    "• Try patterns when you know structure: query('MyApp.*.create*')\\n"
    "• Use filters to narrow: query('login', scope='recent', glob='lib/auth/**')\\n"
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
)

SEARCH_MODULE_DESCRIPTION = (
    "DEEP-DIVE TOOL: View a module's complete API and dependencies after discovering it with query.\n\n"
    "Shows full module details: functions with arity, signatures, docs, typespecs, and line numbers. "
    "Analyze both what this module depends on (what_it_calls) and what depends on it (what_calls_it). "
    "Use this when query suggests drilling into a specific module.\n\n"
    "Supports wildcards (*) and OR patterns (|) for both module names and file paths. Examples: 'MyApp.*', '*User*', 'lib/my_app/*.ex', 'MyApp.User|MyApp.Admin'.\n\n"
    "Search by module_name='MyApp.User' or file_path='lib/my_app/user.ex'. "
    "Control visibility with type: 'public' (default), 'private', or 'all'.\n\n"
    "Returns compact output by default (name/arity only). Use verbose=true for full details.\n\n"
    "AI USAGE TIPS:\n"
    "• After query finds modules, use this to see the full API surface\n"
    "• Query will suggest using this tool when detailed module info is needed\n"
    "• Don't ask user for module names - use query first to discover them\n"
    "• Use what_calls_it=true BEFORE modifying a module to see impact (what depends on it)\n"
    "• Use what_it_calls=true to see what this module depends on\n"
    "• Returns: function list with line numbers (add verbose=true for signatures/docs)\n"
    "• If module not found, error will suggest alternatives - try those suggestions!\n"
    "• Wildcard searches are limited to 20 modules - use more specific patterns for large codebases\n"
    "• Output is automatically truncated for large results to prevent token overflow"
)

SEARCH_FUNCTION_DESCRIPTION = (
    "DEEP-DIVE TOOL: Find function definitions and call sites after discovering with query.\n\n"
    "Provides function analysis: definition location and all call sites. "
    "Use this when query suggests drilling into a specific function's usage.\n\n"
    "Search by function name, optionally with module, file path, and arity: 'function_name', 'Module.function_name', 'function_name/2', or 'lib/my_app/user.ex:function_name'.\n\n"
    "Supports wildcards (*) and OR patterns (|) across function names, modules, and file paths (e.g., 'create*|update*', 'MyApp.*.create', 'lib/*/user.ex:create*').\n\n"
    "Returns compact output by default (location + call sites). Use verbose=true for signatures and documentation.\n\n"
    "AI USAGE TIPS:\n"
    "• After query finds functions, use this for detailed impact analysis\n"
    "• Query will suggest this tool when you need to see where functions are called\n"
    "• Set include_usage_examples=true to see real code examples (helps understand usage patterns)\n"
    "• Use usage_type='tests' to see only how functions are tested\n"
    "• Returns: definition + ALL call sites with file:line references (add verbose=true for docs/specs)\n"
    "• If you see function references in code, search them to understand what they do\n"
    "• Call sites and line numbers are automatically truncated for popular functions (>20 sites)"
)

GIT_HISTORY_DESCRIPTION = (
    "UNIFIED HISTORY TOOL: One tool for all git history queries - replaces get_blame, get_commit_history, find_pr_for_line, and get_file_pr_history.\n\n"
    "Smart routing based on parameters:\n"
    "• start_line only → single line blame + find PR\n"
    "• start_line + end_line → line range blame with PR enrichment\n"
    "• function_name → function tracking with evolution metadata\n"
    "• file_path only → file-level history (PRs preferred, commits fallback)\n\n"
    "Automatically uses PR index when available for enriched results.\n\n"
    "Returns compact output by default (PR number, title, author). Use verbose=true for descriptions and comments.\n\n"
    "AI USAGE TIPS:\n"
    "• Single line authorship: git_history(file_path='lib/auth.ex', start_line=42)\n"
    "• Line range blame: git_history(file_path='lib/auth.ex', start_line=40, end_line=60)\n"
    "• Function evolution: git_history(file_path='lib/auth.ex', function_name='create_user', show_evolution=true)\n"
    "• File PR history: git_history(file_path='lib/auth.ex')\n"
    "• Recent changes only: git_history(file_path='lib/auth.ex', recent=true)\n"
    "• Older changes: git_history(file_path='lib/auth.ex', recent=false)\n"
    "• All time: git_history(file_path='lib/auth.ex', recent=null)\n"
    "• By author: git_history(file_path='lib/auth.ex', author='john')"
)

EXPAND_RESULT_DESCRIPTION = (
    "DRILL-DOWN TOOL: Expand a query result to see complete details.\n\n"
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
)

REFRESH_INDEX_DESCRIPTION = (
    "Force refresh the code index to pick up recent file changes.\n\n"
    "Use when auto-refresh hasn't caught recent edits, or when you need "
    "the index to be immediately up-to-date.\n\n"
    "By default, runs an incremental refresh (only reindexes changed files). "
    "Use force_full=true for a complete reindex if incremental seems stale.\n\n"
    "AI USAGE TIPS:\n"
    "• Use after making code changes if query results seem stale\n"
    "• Incremental refresh is fast (~1-2s for small changes)\n"
    "• Full refresh is slower but comprehensive\n"
    "• Returns: success status, time taken, module/function counts"
)

QUERY_JQ_DESCRIPTION = (
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
)


def get_tool_definitions() -> list[Tool]:
    """Return all tool definitions for the Cicada MCP server."""
    return [
        Tool(
            name="query",
            description=QUERY_DESCRIPTION,
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
                        "enum": ["all", "public", "private"],
                        "description": "Filter scope: 'all' (default) = everything, 'public' = public functions/modules only, 'private' = private functions only.",
                    },
                    "recent": {
                        "type": "boolean",
                        "description": "Filter to recently changed code only (last 14 days). Defaults to false.",
                    },
                    "result_type": {
                        "type": "string",
                        "enum": ["all", "modules", "functions"],
                        "description": "Result type filter: 'all' (default) = modules + functions, 'modules' = only modules, 'functions' = only functions.",
                    },
                    "filter_type": {
                        "type": "string",
                        "enum": ["all", "modules", "functions"],
                        "description": "Deprecated alias for result_type. Kept for backward compatibility.",
                    },
                    "match_source": {
                        "type": "string",
                        "enum": ["all", "docs", "strings", "comments"],
                        "description": "Where to search: 'all' (default) = docs + strings + comments, 'docs' = documentation only, 'strings' = string literals in code (e.g., SQL queries, error messages), 'comments' = inline comments (# ...).",
                    },
                    "glob": {
                        "type": "string",
                        "description": "Glob pattern to filter by file path. Supports *, **, {a,b}, and ! negation (e.g., 'lib/auth/**', '**/*.{ex,exs}', '!**/test/**').",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base directory to search in. Prepended to glob pattern (e.g., path='lib/auth' + glob='*.ex' -> 'lib/auth/*.ex').",
                    },
                    "type": {
                        "type": "string",
                        "description": "File type shorthand. Maps to glob pattern (e.g., 'py' -> '**/*.py', 'ex' -> '**/*.{ex,exs}'). Common types: py, ex, erl, ts, js, rust, go, java.",
                    },
                    "path_pattern": {
                        "type": "string",
                        "description": "Deprecated alias for glob. Kept for backward compatibility.",
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "Maximum results to show (default: 10). Alias for max_results.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to show (default: 10). Use smaller values (3-5) for quick overview, larger (20+) for comprehensive search.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N results (default: 0). Use with head_limit/max_results for pagination.",
                    },
                    "show_snippets": {
                        "type": "boolean",
                        "description": "Show code snippet previews with context lines (default: false). When enabled, displays actual code around each result.",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Context lines around definition (default: 2). Symmetric like -C. Auto-enables snippets.",
                        "cli_short": "C",
                    },
                    "context_before": {
                        "type": "integer",
                        "description": "Lines before definition (-B). Overrides context_lines. Auto-enables snippets.",
                        "cli_short": "B",
                    },
                    "context_after": {
                        "type": "integer",
                        "description": "Lines after definition (-A). Overrides context_lines. Auto-enables snippets.",
                        "cli_short": "A",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output with full documentation previews and confidence percentages. Defaults to false.",
                    },
                    "regex": {
                        "type": "boolean",
                        "description": "STUB: Treat query keywords as regex patterns. Not yet implemented.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_module",
            description=SEARCH_MODULE_DESCRIPTION,
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
                    "what_calls_it": {
                        "type": "boolean",
                        "description": "Show where this module is used: aliases, imports, requires, uses, and all function call sites. Critical for impact analysis before refactoring. Defaults to false.",
                    },
                    "usage_type": {
                        "type": "string",
                        "enum": ["all", "tests", "source"],
                        "description": "When what_calls_it is true, filter usage sites by file type. 'source' shows only source files (default), 'tests' shows only test files, 'all' shows everything. Defaults to 'source'.",
                    },
                    "what_it_calls": {
                        "type": "boolean",
                        "description": "Show which modules this module depends on (what it imports/aliases/uses). Defaults to false.",
                    },
                    "dependency_depth": {
                        "type": "integer",
                        "description": "When what_it_calls is true, controls transitive dependency depth. 1 = direct only, 2+ = include dependencies of dependencies. Defaults to 1.",
                    },
                    "show_function_usage": {
                        "type": "boolean",
                        "description": "When what_it_calls is true, show which specific functions use which dependencies. Defaults to false.",
                    },
                    "include_docs": {
                        "type": "boolean",
                        "description": "Include function documentation in output. Defaults to false.",
                    },
                    "include_specs": {
                        "type": "boolean",
                        "description": "Include full type signatures in output. Defaults to false.",
                    },
                    "include_moduledoc": {
                        "type": "boolean",
                        "description": "Include module documentation in output. Defaults to false.",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output (includes docs, specs, moduledoc). Defaults to false.",
                    },
                    # Grep-like parameters
                    "glob": {
                        "type": "string",
                        "description": "Glob pattern to filter results by file path. Supports *, **, {a,b}, and ! negation.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base directory to filter results. Prepended to glob pattern.",
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "Maximum results to show (default: 20 for wildcard searches).",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N results (default: 0). Use with head_limit for pagination.",
                    },
                },
            },
        ),
        Tool(
            name="search_function",
            description=SEARCH_FUNCTION_DESCRIPTION,
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
                    "what_calls_it": {
                        "type": "boolean",
                        "description": "Show call sites (which functions call this function). Defaults to true.",
                    },
                    "what_it_calls": {
                        "type": "boolean",
                        "description": "Show what functions this function calls (its dependencies), grouped by internal/external with line numbers. Defaults to false.",
                    },
                    "include_code_context": {
                        "type": "boolean",
                        "description": "When what_it_calls is true, include code snippets showing where each dependency is called. Defaults to false.",
                    },
                    "include_docs": {
                        "type": "boolean",
                        "description": "Include function documentation in output. Defaults to false for compact output.",
                    },
                    "include_specs": {
                        "type": "boolean",
                        "description": "Include full type specs/signatures. Defaults to false (shows name/arity only).",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable all optional content (docs, specs, examples). Equivalent to include_docs=true, include_specs=true.",
                    },
                    # Grep-like parameters
                    "glob": {
                        "type": "string",
                        "description": "Glob pattern to filter results by file path. Supports *, **, {a,b}, and ! negation.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base directory to filter results. Prepended to glob pattern.",
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "Maximum results to show.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Skip first N results (default: 0). Use with head_limit for pagination.",
                    },
                },
                "required": ["function_name"],
            },
        ),
        Tool(
            name="git_history",
            description=GIT_HISTORY_DESCRIPTION,
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root).",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional: Line number for single line, or range start. If provided without end_line, queries single line + finds PR.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional: Range end for line-based tracking. Use with start_line for range blame.",
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Optional: Function name for function-level tracking. Uses git log -L for precise tracking.",
                    },
                    "show_evolution": {
                        "type": "boolean",
                        "description": "Show evolution metadata (creation date, last modification, frequency). Defaults to false.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum commits/PRs to return. Defaults to 10.",
                    },
                    "recent": {
                        "type": ["boolean", "null"],
                        "description": "Time filter: true = last N days only (default 14), false = older than N days, null/omitted = all time (default).",
                    },
                    "recent_days": {
                        "type": "integer",
                        "description": "Number of days for 'recent' filter. Defaults to 14. Only used when recent=true or recent=false.",
                    },
                    "author": {
                        "type": "string",
                        "description": "Filter by author name (substring match, case-insensitive).",
                    },
                    "include_pr_description": {
                        "type": "boolean",
                        "description": "Include PR descriptions in output. Defaults to false.",
                    },
                    "include_review_comments": {
                        "type": "boolean",
                        "description": "Include PR review comments in output. Defaults to false.",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Enable verbose output (includes PR descriptions and comments). Defaults to false.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="expand_result",
            description=EXPAND_RESULT_DESCRIPTION,
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
                    "what_calls_it": {
                        "type": "boolean",
                        "description": "For functions: show call sites (which functions call this). For modules: not applicable. Defaults to true.",
                    },
                    "what_it_calls": {
                        "type": "boolean",
                        "description": "Show dependencies. For functions: what functions it calls. For modules: what modules it depends on. Defaults to false.",
                    },
                    "dependency_depth": {
                        "type": "integer",
                        "description": "For modules with what_it_calls=true, controls transitive dependency depth. 1 = direct only, 2+ = include dependencies of dependencies. Defaults to 1.",
                    },
                    "show_function_usage": {
                        "type": "boolean",
                        "description": "For modules with what_it_calls=true, show which specific functions use which dependencies. Defaults to false.",
                    },
                    "include_code_context": {
                        "type": "boolean",
                        "description": "For functions with what_it_calls=true, include code snippets showing where dependencies are called. Defaults to false.",
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
            name="refresh_index",
            description=REFRESH_INDEX_DESCRIPTION,
            inputSchema={
                "type": "object",
                "properties": {
                    "force_full": {
                        "type": "boolean",
                        "description": "Force full reindex instead of incremental (slower but comprehensive). Defaults to false.",
                    },
                },
            },
        ),
        Tool(
            name="query_jq",
            description=QUERY_JQ_DESCRIPTION,
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
                        "enum": ["compact", "pretty"],
                        "description": (
                            "Output format: 'compact' returns single-line JSON (default, saves tokens), "
                            "'pretty' returns pretty-printed JSON with indentation (use only when user explicitly requests readable formatting)."
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
