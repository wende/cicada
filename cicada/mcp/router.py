"""
Tool Router for Cicada MCP Server.

Routes tool calls to appropriate handlers with argument validation.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, cast

from mcp.types import TextContent

from cicada.mcp.handlers import (
    AnalysisHandler,
    FunctionSearchHandler,
    GitHistoryHandler,
    ModuleSearchHandler,
    PRHistoryHandler,
)

if TYPE_CHECKING:
    from cicada.git.helper import GitHelper
    from cicada.mcp.handlers.index_manager import IndexManager

# Security limits for jq queries to prevent resource exhaustion
MAX_JQ_QUERY_LENGTH = 10_000  # Maximum characters in a jq query
MAX_JQ_NESTING_DEPTH = 50  # Maximum bracket/parenthesis nesting imbalance


def _validate_jq_query(query: str | None) -> str | None:
    """Validate jq query. Returns error message or None if valid."""
    if not query:
        return "'query' is required"
    if not isinstance(query, str):
        return "'query' must be a string"
    if not query.strip():
        return "'query' cannot be empty"
    if len(query) > MAX_JQ_QUERY_LENGTH:
        return (
            f"'query' exceeds maximum length of {MAX_JQ_QUERY_LENGTH:,} characters.\n"
            f"Current: {len(query):,}. Please simplify your query."
        )

    # Check for balanced brackets and excessive nesting, ignoring content in strings
    max_depth, error = _check_bracket_nesting(query)
    if error:
        return error
    if max_depth > MAX_JQ_NESTING_DEPTH:
        return (
            f"Query nesting depth ({max_depth}) exceeds maximum ({MAX_JQ_NESTING_DEPTH}). "
            f"Please simplify your query."
        )
    return None


def _check_bracket_nesting(query: str) -> tuple[int, str | None]:
    """
    Check bracket/paren nesting depth and balance.

    Properly handles strings by ignoring brackets/parens inside quoted strings.
    Detects unbalanced brackets/parens and excessive nesting depth.

    Args:
        query: The jq query string to validate

    Returns:
        Tuple of (max_depth, error_message). error_message is None if valid.
    """
    depth = 0
    max_depth = 0
    stack: list[str] = []
    in_string = False
    escape_next = False

    bracket_pairs = {"[": "]", "(": ")", "{": "}"}
    closing_brackets = {"]", ")", "}"}

    for i, char in enumerate(query):
        # Handle string escaping
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        # Toggle string state on unescaped quotes
        if char == '"':
            in_string = not in_string
            continue

        # Skip bracket/paren processing inside strings
        if in_string:
            continue

        # Track opening brackets/parens
        if char in bracket_pairs:
            stack.append(char)
            depth += 1
            max_depth = max(max_depth, depth)

        # Track closing brackets/parens
        elif char in closing_brackets:
            if not stack:
                return (max_depth, f"Unbalanced brackets: unexpected '{char}' at position {i}")

            opening = stack.pop()
            expected_closing = bracket_pairs[opening]
            if char != expected_closing:
                return (
                    max_depth,
                    f"Mismatched brackets: '{opening}' at position {i - depth} "
                    f"closed with '{char}' instead of '{expected_closing}'",
                )
            depth -= 1

    # Check if we ended inside a string (check this first - it's the root cause)
    if in_string:
        return (max_depth, "Unterminated string in query")

    # Check for unclosed brackets
    if stack:
        unclosed = ", ".join(f"'{b}'" for b in stack)
        return (max_depth, f"Unclosed brackets: {unclosed}")

    return (max_depth, None)


class ToolRouter:
    """Routes MCP tool calls to appropriate handlers."""

    def __init__(
        self,
        module_handler: ModuleSearchHandler,
        function_handler: FunctionSearchHandler,
        git_handler: GitHistoryHandler,
        pr_handler: PRHistoryHandler,
        analysis_handler: AnalysisHandler,
    ):
        """
        Initialize the tool router with handlers.

        Args:
            module_handler: Handler for module-related tools
            function_handler: Handler for function-related tools
            git_handler: Handler for git history tools
            pr_handler: Handler for PR history tools
            analysis_handler: Handler for analysis tools (query, dead code)
        """
        self.module_handler = module_handler
        self.function_handler = function_handler
        self.git_handler = git_handler
        self.pr_handler = pr_handler
        self.analysis_handler = analysis_handler

    @staticmethod
    def _resolve_visibility_parameter(arguments: dict) -> str:
        """Resolve visibility parameter with backward compatibility.

        Args:
            arguments: Tool arguments dictionary

        Returns:
            Resolved visibility value: 'public', 'private', or 'all'
        """
        type_param = arguments.get("type")
        private_functions = arguments.get("private_functions")

        if type_param:
            return type_param
        elif private_functions:
            # Map old parameter values to new ones
            mapping = {"exclude": "public", "only": "private", "include": "all"}
            return mapping.get(private_functions, "public")
        else:
            return "public"

    async def _handle_search_module(
        self,
        arguments: dict,
        pr_info_callback: Any = None,
        staleness_info_callback: Any = None,
    ) -> list[TextContent]:
        """Handle search_module tool call."""
        from cicada.utils.path_utils import resolve_glob_pattern

        module_name = arguments.get("module_name")
        file_path = arguments.get("file_path")
        output_format = arguments.get("format", "markdown")
        visibility = self._resolve_visibility_parameter(arguments)

        # Get dependency parameters
        what_calls_it = arguments.get("what_calls_it", False)
        usage_type = arguments.get("usage_type", "source")
        what_it_calls = arguments.get("what_it_calls", False)
        dependency_depth = arguments.get("dependency_depth", 1)
        show_function_usage = arguments.get("show_function_usage", False)

        # Get compaction parameters
        include_docs = arguments.get("include_docs", False)
        include_specs = arguments.get("include_specs", False)
        include_moduledoc = arguments.get("include_moduledoc", False)
        verbose = arguments.get("verbose", False)

        # Grep-like parameters
        glob_pattern = arguments.get("glob")
        path = arguments.get("path")
        effective_glob = resolve_glob_pattern(glob_pattern, path, None)
        head_limit = arguments.get("head_limit")
        offset = arguments.get("offset", 0)

        # Validate pagination parameters
        if head_limit is not None and (not isinstance(head_limit, int) or head_limit < 1):
            return [TextContent(type="text", text="'head_limit' must be a positive integer")]
        if not isinstance(offset, int) or offset < 0:
            return [TextContent(type="text", text="'offset' must be a non-negative integer")]

        if not module_name and not file_path:
            return [
                TextContent(
                    type="text", text="Either 'module_name' or 'file_path' must be provided"
                )
            ]

        # If file_path is provided, resolve it to module_name
        if file_path:
            resolved_module = self.module_handler.resolve_file_to_module(file_path)
            if not resolved_module:
                return [
                    TextContent(type="text", text=f"Could not find module in file: {file_path}")
                ]
            module_name = resolved_module

        # Get PR info and staleness info if callbacks provided
        pr_info = None
        staleness_info = None
        if pr_info_callback and module_name:
            module_data = self.module_handler.index["modules"].get(module_name)
            if module_data:
                pr_info = pr_info_callback(module_data["file"])
        if staleness_info_callback:
            staleness_info = staleness_info_callback()

        assert module_name is not None
        format_opts = {
            "include_docs": include_docs or verbose,
            "include_specs": include_specs or verbose,
            "include_moduledoc": include_moduledoc or verbose,
        }

        return await self.module_handler.search_module(
            module_name,
            output_format,
            visibility,
            pr_info,
            staleness_info,
            what_calls_it,
            usage_type,
            what_it_calls,
            dependency_depth,
            show_function_usage,
            format_opts,
            glob=effective_glob,
            head_limit=head_limit,
            offset=offset,
        )

    async def _handle_search_function(self, arguments: dict) -> list[TextContent]:
        """Handle search_function tool call."""
        from cicada.utils.path_utils import resolve_glob_pattern

        function_name = arguments.get("function_name")
        module_path = arguments.get("module_path")
        output_format = arguments.get("format", "markdown")
        include_usage_examples = arguments.get("include_usage_examples", False)
        max_examples = arguments.get("max_examples", 5)
        usage_type = arguments.get("usage_type", "source")
        changed_since = arguments.get("changed_since")
        what_calls_it = arguments.get("what_calls_it", True)
        what_it_calls = arguments.get("what_it_calls", False)
        include_code_context = arguments.get("include_code_context", False)
        include_docs = arguments.get("include_docs", False)
        include_specs = arguments.get("include_specs", False)
        verbose = arguments.get("verbose", False)

        # Grep-like parameters
        glob_pattern = arguments.get("glob")
        path = arguments.get("path")
        effective_glob = resolve_glob_pattern(glob_pattern, path, None)
        head_limit = arguments.get("head_limit")
        offset = arguments.get("offset", 0)

        # Validate pagination parameters
        if head_limit is not None and (not isinstance(head_limit, int) or head_limit < 1):
            return [TextContent(type="text", text="'head_limit' must be a positive integer")]
        if not isinstance(offset, int) or offset < 0:
            return [TextContent(type="text", text="'offset' must be a non-negative integer")]

        if not function_name:
            return [TextContent(type="text", text="'function_name' is required")]

        if usage_type not in ("all", "tests", "source"):
            return [
                TextContent(
                    type="text", text="'usage_type' must be one of: 'all', 'tests', 'source'"
                )
            ]

        format_opts = {
            "include_docs": include_docs or verbose,
            "include_specs": include_specs or verbose,
        }

        return await self.function_handler.search_function(
            function_name,
            output_format,
            include_usage_examples,
            max_examples,
            usage_type,
            changed_since,
            what_calls_it,
            module_path,
            what_it_calls,
            include_code_context,
            format_opts=format_opts,
            glob=effective_glob,
            head_limit=head_limit,
            offset=offset,
        )

    async def _handle_git_history(self, arguments: dict) -> list[TextContent]:
        """Handle git_history tool call."""
        file_path = arguments.get("file_path")
        if not file_path:
            return [TextContent(type="text", text="'file_path' is required")]

        return await self.git_handler.git_history(
            file_path=file_path,
            start_line=arguments.get("start_line"),
            end_line=arguments.get("end_line"),
            function_name=arguments.get("function_name"),
            show_evolution=arguments.get("show_evolution", False),
            max_results=arguments.get("max_results", 10),
            recent=arguments.get("recent"),
            author=arguments.get("author"),
            include_pr_description=arguments.get("include_pr_description", False),
            include_review_comments=arguments.get("include_review_comments", False),
            verbose=arguments.get("verbose", False),
        )

    async def _handle_query(self, arguments: dict) -> list[TextContent]:
        """Handle query tool call."""
        from cicada.utils.path_utils import resolve_glob_pattern

        query = arguments.get("query")
        scope = arguments.get("scope", "all")
        recent = arguments.get("recent", False)

        # Handle result_type vs filter_type (deprecated alias)
        result_type = arguments.get("result_type") or arguments.get("filter_type", "all")

        match_source = arguments.get("match_source", "all")

        # Handle head_limit vs max_results (alias)
        max_results = arguments.get("head_limit") or arguments.get("max_results", 10)

        # Handle glob vs path_pattern (deprecated alias)
        glob_pattern = arguments.get("glob") or arguments.get("path_pattern")
        path = arguments.get("path")
        file_type = arguments.get("type")

        # Resolve glob/path/type into effective glob pattern
        effective_glob = resolve_glob_pattern(glob_pattern, path, file_type)

        offset = arguments.get("offset", 0)
        show_snippets = arguments.get("show_snippets", False)
        context_before = arguments.get("context_before")
        context_after = arguments.get("context_after")

        # Auto-enable snippets if any context flag is explicitly set
        if context_before is not None or context_after is not None or "context_lines" in arguments:
            show_snippets = True

        context_lines = arguments.get("context_lines", 2)
        verbose = arguments.get("verbose", False)

        # Regex stub
        regex = arguments.get("regex", False)
        if regex:
            return [
                TextContent(
                    type="text",
                    text="Error: 'regex' parameter is not yet implemented. "
                    "Use pattern matching with wildcards (*) instead.",
                )
            ]

        # Validation
        if not query:
            return [TextContent(type="text", text="'query' is required")]
        if not isinstance(query, (str, list)):
            return [TextContent(type="text", text="'query' must be a string or list of strings")]
        if isinstance(query, list) and not all(
            isinstance(q, str) or (isinstance(q, list) and all(isinstance(s, str) for s in q))
            for q in query
        ):
            return [
                TextContent(
                    type="text",
                    text="'query' list must contain strings or lists of strings (for synonyms)",
                )
            ]
        if scope not in ("all", "public", "private"):
            return [
                TextContent(type="text", text="'scope' must be one of: 'all', 'public', 'private'")
            ]
        if not isinstance(recent, bool):
            return [TextContent(type="text", text="'recent' must be a boolean")]
        if result_type not in ("all", "modules", "functions"):
            return [
                TextContent(
                    type="text",
                    text="'result_type' must be one of: 'all', 'modules', 'functions'",
                )
            ]
        if match_source not in ("all", "docs", "strings", "comments"):
            return [
                TextContent(
                    type="text",
                    text="'match_source' must be one of: 'all', 'docs', 'strings', 'comments'",
                )
            ]
        if not isinstance(max_results, int) or max_results < 1:
            return [TextContent(type="text", text="'max_results' must be a positive integer")]
        if not isinstance(offset, int) or offset < 0:
            return [TextContent(type="text", text="'offset' must be a non-negative integer")]
        if not isinstance(show_snippets, bool):
            return [TextContent(type="text", text="'show_snippets' must be a boolean")]
        if not isinstance(context_lines, int) or context_lines < 0:
            return [TextContent(type="text", text="'context_lines' must be a non-negative integer")]
        if context_before is not None and (
            not isinstance(context_before, int) or context_before < 0
        ):
            return [
                TextContent(type="text", text="'context_before' must be a non-negative integer")
            ]
        if context_after is not None and (not isinstance(context_after, int) or context_after < 0):
            return [TextContent(type="text", text="'context_after' must be a non-negative integer")]

        return await self.analysis_handler.query(
            query,
            scope,
            recent,
            result_type,
            match_source,
            max_results,
            effective_glob,
            show_snippets,
            verbose,
            offset,
            context_lines,
            context_before,
            context_after,
        )

    async def _handle_query_jq(self, arguments: dict) -> list[TextContent]:
        """Handle query_jq tool call."""
        query = arguments.get("query")
        output_format = arguments.get("format", "compact")
        sample = arguments.get("sample", False)

        if error := _validate_jq_query(query):
            return [TextContent(type="text", text=error)]

        # Backward compatibility: 'json' maps to 'compact'
        if output_format == "json":
            output_format = "compact"
        if output_format not in ("compact", "pretty"):
            return [
                TextContent(
                    type="text", text="'format' must be one of: 'json', 'compact', 'pretty'"
                )
            ]
        if not isinstance(sample, bool):
            return [TextContent(type="text", text="'sample' must be a boolean")]

        return await self.analysis_handler.query_jq(cast(str, query), output_format, sample)

    async def _handle_expand_result(self, arguments: dict) -> list[TextContent]:
        """Handle expand_result tool call."""
        identifier = arguments.get("identifier")
        result_type = arguments.get("type", "auto")
        what_calls_it = arguments.get("what_calls_it", True)
        output_format = arguments.get("format", "markdown")
        what_it_calls = arguments.get("what_it_calls", False)
        dependency_depth = arguments.get("dependency_depth", 1)
        show_function_usage = arguments.get("show_function_usage", False)
        include_code_context = arguments.get("include_code_context", False)

        # Validation
        if not identifier:
            return [TextContent(type="text", text="'identifier' is required")]
        if result_type not in ("auto", "module", "function"):
            return [
                TextContent(type="text", text="'type' must be one of: 'auto', 'module', 'function'")
            ]
        if output_format not in ("markdown", "json"):
            return [TextContent(type="text", text="'format' must be one of: 'markdown', 'json'")]

        # Boolean validation
        for name, value in [
            ("what_calls_it", what_calls_it),
            ("what_it_calls", what_it_calls),
        ]:
            if not isinstance(value, bool):
                return [TextContent(type="text", text=f"'{name}' must be a boolean")]

        # Auto-detect type if needed
        if result_type == "auto":
            if "/" in identifier:
                result_type = "function"
            elif identifier in self.module_handler.index.get("modules", {}):
                result_type = "module"
            else:
                result_type = "function"

        # Route to appropriate handler
        if result_type == "module":
            if identifier not in self.module_handler.index.get("modules", {}):
                return [TextContent(type="text", text=f"Module not found: {identifier}")]

            return await self.module_handler.search_module(
                identifier,
                output_format=output_format,
                visibility="all",
                pr_info=None,
                staleness_info=None,
                what_calls_it=False,
                usage_type="source",
                what_it_calls=what_it_calls,
                dependency_depth=dependency_depth,
                show_function_usage=show_function_usage,
                format_opts={
                    "include_moduledoc": True,
                    "include_docs": True,
                    "include_specs": True,
                },
            )
        else:
            function_name = identifier
            module_path = None
            if "." in identifier:
                parts = identifier.rsplit(".", 1)
                if len(parts) == 2:
                    module_path, function_name = parts[0], parts[1]

            if not function_name:
                return [TextContent(type="text", text=f"Invalid function reference: {identifier}")]

            return await self.function_handler.search_function(
                function_name=function_name,
                output_format=output_format,
                include_usage_examples=what_calls_it,
                max_examples=5,
                usage_type="all",
                changed_since=None,
                what_calls_it=what_calls_it,
                module_path=module_path,
                what_it_calls=what_it_calls,
                include_code_context=include_code_context,
                format_opts={"include_docs": True, "include_specs": True},
            )

    async def _handle_refresh_index(
        self, arguments: dict, refresh_callback: Any
    ) -> list[TextContent]:
        """Handle refresh_index tool call."""
        force_full = arguments.get("force_full", False)

        if not isinstance(force_full, bool):
            return [TextContent(type="text", text="'force_full' must be a boolean")]
        if not refresh_callback:
            return [TextContent(type="text", text="Index refresh not available")]

        result = refresh_callback(force_full)

        if result.get("success"):
            response = (
                f"Index refreshed successfully ({result['mode']} mode)\n\n"
                f"- Time: {result['elapsed_seconds']}s\n"
                f"- Modules: {result['total_modules']}\n"
                f"- Functions: {result['total_functions']}"
            )
        else:
            response = f"Index refresh failed: {result.get('error', 'Unknown error')}"

        return [TextContent(type="text", text=response)]

    async def route_tool(
        self,
        name: str,
        arguments: dict,
        pr_info_callback: Any = None,
        staleness_info_callback: Any = None,
        refresh_callback: Any = None,
    ) -> list[TextContent]:
        """
        Route tool call to appropriate handler.

        Args:
            name: Tool name
            arguments: Tool arguments
            pr_info_callback: Optional callback to get PR info for a file
            staleness_info_callback: Optional callback to check index staleness
            refresh_callback: Optional callback to force index refresh

        Returns:
            List of TextContent responses

        Raises:
            ValueError: If tool name is unknown or arguments are invalid
        """
        if name == "search_module":
            return await self._handle_search_module(
                arguments, pr_info_callback, staleness_info_callback
            )
        elif name == "search_function":
            return await self._handle_search_function(arguments)
        elif name == "git_history":
            return await self._handle_git_history(arguments)
        elif name == "query":
            return await self._handle_query(arguments)
        elif name == "query_jq":
            return await self._handle_query_jq(arguments)
        elif name == "expand_result":
            return await self._handle_expand_result(arguments)
        elif name == "refresh_index":
            return await self._handle_refresh_index(arguments, refresh_callback)
        else:
            raise ValueError(f"Unknown tool: {name}")


def create_tool_router(config: dict) -> tuple[ToolRouter, IndexManager, GitHelper | None]:
    """Create a ToolRouter with all required handlers from config.

    This factory function centralizes the handler initialization logic
    that is shared between the MCP server and CLI run command.

    Args:
        config: Configuration dictionary with repository settings

    Returns:
        Tuple of (ToolRouter, IndexManager, GitHelper or None)
    """
    from cicada.git.helper import GitHelper
    from cicada.mcp.handlers.index_manager import IndexManager

    # Initialize index manager
    index_manager = IndexManager(config)

    # Get repo path from config for git helper
    repo_path = config.get("repository", {}).get("path", ".")

    # Initialize git helper (may fail if not a git repo)
    git_helper: GitHelper | None = None
    try:
        git_helper = GitHelper(repo_path)
    except Exception as e:
        print(f"Warning: Git helper not available: {e}", file=sys.stderr)

    # Initialize handlers
    module_handler = ModuleSearchHandler(index_manager.index, config)
    function_handler = FunctionSearchHandler(index_manager.index, config)
    git_handler = GitHistoryHandler(git_helper, config)
    pr_handler = PRHistoryHandler(index_manager.pr_index, config)
    analysis_handler = AnalysisHandler(index_manager)

    # Create router
    router = ToolRouter(
        module_handler=module_handler,
        function_handler=function_handler,
        git_handler=git_handler,
        pr_handler=pr_handler,
        analysis_handler=analysis_handler,
    )

    return router, index_manager, git_helper
