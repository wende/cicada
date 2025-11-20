"""
Tool Router for Cicada MCP Server.

Routes tool calls to appropriate handlers with argument validation.
"""

from typing import Any, cast

from mcp.types import TextContent

from cicada.mcp.handlers import (
    AnalysisHandler,
    FunctionSearchHandler,
    GitHistoryHandler,
    ModuleSearchHandler,
    PRHistoryHandler,
)

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

    async def route_tool(
        self,
        name: str,
        arguments: dict,
        pr_info_callback: Any = None,
        staleness_info_callback: Any = None,
    ) -> list[TextContent]:
        """
        Route tool call to appropriate handler.

        Args:
            name: Tool name
            arguments: Tool arguments
            pr_info_callback: Optional callback to get PR info for a file
            staleness_info_callback: Optional callback to check index staleness

        Returns:
            List of TextContent responses

        Raises:
            ValueError: If tool name is unknown or arguments are invalid
        """
        if name == "search_module":
            module_name = arguments.get("module_name")
            file_path = arguments.get("file_path")
            output_format = arguments.get("format", "markdown")

            # Resolve visibility parameter with backward compatibility
            visibility = self._resolve_visibility_parameter(arguments)

            # Get dependency parameters
            what_calls_it = arguments.get("what_calls_it", False)
            usage_type = arguments.get("usage_type", "source")
            what_it_calls = arguments.get("what_it_calls", False)
            dependency_depth = arguments.get("dependency_depth", 1)
            show_function_usage = arguments.get("show_function_usage", False)

            # Validate that at least one is provided
            if not module_name and not file_path:
                error_msg = "Either 'module_name' or 'file_path' must be provided"
                return [TextContent(type="text", text=error_msg)]

            # If file_path is provided, resolve it to module_name
            if file_path:
                resolved_module = self.module_handler.resolve_file_to_module(file_path)
                if not resolved_module:
                    error_msg = f"Could not find module in file: {file_path}"
                    return [TextContent(type="text", text=error_msg)]
                module_name = resolved_module

            # Get PR info and staleness info if callbacks provided
            pr_info = None
            staleness_info = None
            if pr_info_callback and module_name:
                # Get module data to extract file path
                module_data = self.module_handler.index["modules"].get(module_name)
                if module_data:
                    pr_info = pr_info_callback(module_data["file"])
            if staleness_info_callback:
                staleness_info = staleness_info_callback()

            assert module_name is not None, "module_name must be provided"
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
            )

        elif name == "search_function":
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

            if not function_name:
                error_msg = "'function_name' is required"
                return [TextContent(type="text", text=error_msg)]

            # Validate usage_type
            valid_usage_types = ("all", "tests", "source")
            if usage_type not in valid_usage_types:
                error_msg = "'usage_type' must be one of: 'all', 'tests', 'source'"
                return [TextContent(type="text", text=error_msg)]

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
            )

        elif name == "git_history":
            file_path = arguments.get("file_path")
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")
            function_name = arguments.get("function_name")
            show_evolution = arguments.get("show_evolution", False)
            max_results = arguments.get("max_results", 10)
            recent = arguments.get("recent")
            author = arguments.get("author")

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self.git_handler.git_history(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                function_name=function_name,
                show_evolution=show_evolution,
                max_results=max_results,
                recent=recent,
                author=author,
            )

        elif name == "query":
            query = arguments.get("query")
            scope = arguments.get("scope", "all")
            recent = arguments.get("recent", False)
            filter_type = arguments.get("filter_type", "all")
            match_source = arguments.get("match_source", "all")
            max_results = arguments.get("max_results", 10)
            path_pattern = arguments.get("path_pattern")
            show_snippets = arguments.get("show_snippets", False)

            # Validate required argument
            if not query:
                error_msg = "'query' is required"
                return [TextContent(type="text", text=error_msg)]

            # Validate query type
            if not isinstance(query, (str, list)):
                error_msg = "'query' must be a string or list of strings"
                return [TextContent(type="text", text=error_msg)]

            if isinstance(query, list) and not all(isinstance(q, str) for q in query):
                error_msg = "'query' list must contain only strings"
                return [TextContent(type="text", text=error_msg)]

            # Validate enum parameters
            if scope not in ("all", "public", "private"):
                error_msg = "'scope' must be one of: 'all', 'public', 'private'"
                return [TextContent(type="text", text=error_msg)]

            # Validate recent parameter
            if not isinstance(recent, bool):
                error_msg = "'recent' must be a boolean"
                return [TextContent(type="text", text=error_msg)]

            if filter_type not in ("all", "modules", "functions"):
                error_msg = "'filter_type' must be one of: 'all', 'modules', 'functions'"
                return [TextContent(type="text", text=error_msg)]

            if match_source not in ("all", "docs", "strings"):
                error_msg = "'match_source' must be one of: 'all', 'docs', 'strings'"
                return [TextContent(type="text", text=error_msg)]

            # Validate max_results
            if not isinstance(max_results, int) or max_results < 1:
                error_msg = "'max_results' must be a positive integer"
                return [TextContent(type="text", text=error_msg)]

            # Validate show_snippets
            if not isinstance(show_snippets, bool):
                error_msg = "'show_snippets' must be a boolean"
                return [TextContent(type="text", text=error_msg)]

            return await self.analysis_handler.query(
                query,
                scope,
                recent,
                filter_type,
                match_source,
                max_results,
                path_pattern,
                show_snippets,
            )

        elif name == "find_dead_code":
            min_confidence = arguments.get("min_confidence", "high")
            output_format = arguments.get("format", "markdown")

            return await self.analysis_handler.find_dead_code(min_confidence, output_format)

        elif name == "query_jq":
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

        elif name == "expand_result":
            identifier = arguments.get("identifier")
            result_type = arguments.get("type", "auto")
            include_code = arguments.get("include_code", True)
            what_calls_it = arguments.get("what_calls_it", True)
            output_format = arguments.get("format", "markdown")
            what_it_calls = arguments.get("what_it_calls", False)
            dependency_depth = arguments.get("dependency_depth", 1)
            show_function_usage = arguments.get("show_function_usage", False)
            include_code_context = arguments.get("include_code_context", False)

            # Validate required parameter
            if not identifier:
                error_msg = "'identifier' is required"
                return [TextContent(type="text", text=error_msg)]

            # Validate enum parameters
            if result_type not in ("auto", "module", "function"):
                error_msg = "'type' must be one of: 'auto', 'module', 'function'"
                return [TextContent(type="text", text=error_msg)]

            if output_format not in ("markdown", "json"):
                error_msg = "'format' must be one of: 'markdown', 'json'"
                return [TextContent(type="text", text=error_msg)]

            # Validate boolean parameters
            if not isinstance(include_code, bool):
                error_msg = "'include_code' must be a boolean"
                return [TextContent(type="text", text=error_msg)]

            if not isinstance(what_calls_it, bool):
                error_msg = "'what_calls_it' must be a boolean"
                return [TextContent(type="text", text=error_msg)]

            if not isinstance(what_it_calls, bool):
                error_msg = "'what_it_calls' must be a boolean"
                return [TextContent(type="text", text=error_msg)]

            # Auto-detect type if needed
            if result_type == "auto":
                # If it has arity notation (e.g., /2), it's a function
                if "/" in identifier:
                    result_type = "function"
                # Check if it exists as a module in the index
                elif identifier in self.module_handler.index.get("modules", {}):
                    result_type = "module"
                else:
                    # If not found as module, assume function (will error appropriately later)
                    result_type = "function"

            # Route to appropriate handler
            if result_type == "module":
                # Check if module exists
                if identifier not in self.module_handler.index.get("modules", {}):
                    error_msg = f"Module not found: {identifier}"
                    return [TextContent(type="text", text=error_msg)]

                # Use existing module search handler
                return await self.module_handler.search_module(
                    identifier,
                    output_format=output_format,
                    visibility="all",  # Show all functions (public and private)
                    pr_info=None,
                    staleness_info=None,
                    # Note: what_calls_it not supported in expand_result context to avoid
                    # expanding usage info for every result in large result sets, which would
                    # significantly increase token usage and response time.
                    what_calls_it=False,
                    usage_type="source",
                    what_it_calls=what_it_calls,
                    dependency_depth=dependency_depth,
                    show_function_usage=show_function_usage,
                )
            else:  # function
                # Parse function reference to extract components
                function_name = identifier
                module_path = None

                # If it contains a module path, split on the last dot
                if "." in identifier:
                    parts = identifier.rsplit(".", 1)
                    if len(parts) == 2:
                        module_path = parts[0]
                        function_name = parts[1]

                if not function_name:
                    error_msg = f"Invalid function reference: {identifier}"
                    return [TextContent(type="text", text=error_msg)]

                # Use existing function search handler
                return await self.function_handler.search_function(
                    function_name=function_name,
                    output_format=output_format,
                    include_usage_examples=what_calls_it,  # Show usage if requested
                    max_examples=5,
                    usage_type="all",
                    changed_since=None,
                    what_calls_it=what_calls_it,
                    module_path=module_path,
                    what_it_calls=what_it_calls,
                    include_code_context=include_code_context,
                )

        else:
            raise ValueError(f"Unknown tool: {name}")
