"""
Tool Router for Cicada MCP Server.

Routes tool calls to appropriate handlers with argument validation.
"""

from typing import Any

from mcp.types import TextContent

from cicada.mcp.handlers import (
    AnalysisHandler,
    DependencyHandler,
    FunctionSearchHandler,
    GitHistoryHandler,
    ModuleSearchHandler,
    PRHistoryHandler,
)


class ToolRouter:
    """Routes MCP tool calls to appropriate handlers."""

    def __init__(
        self,
        module_handler: ModuleSearchHandler,
        function_handler: FunctionSearchHandler,
        git_handler: GitHistoryHandler,
        pr_handler: PRHistoryHandler,
        dependency_handler: DependencyHandler,
        analysis_handler: AnalysisHandler,
    ):
        """
        Initialize the tool router with handlers.

        Args:
            module_handler: Handler for module-related tools
            function_handler: Handler for function-related tools
            git_handler: Handler for git history tools
            pr_handler: Handler for PR history tools
            dependency_handler: Handler for dependency analysis tools
            analysis_handler: Handler for analysis tools (keywords, dead code)
        """
        self.module_handler = module_handler
        self.function_handler = function_handler
        self.git_handler = git_handler
        self.pr_handler = pr_handler
        self.dependency_handler = dependency_handler
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
                module_name, output_format, visibility, pr_info, staleness_info
            )

        elif name == "search_function":
            function_name = arguments.get("function_name")
            module_path = arguments.get("module_path")
            output_format = arguments.get("format", "markdown")
            include_usage_examples = arguments.get("include_usage_examples", False)
            max_examples = arguments.get("max_examples", 5)

            # Handle backward compatibility for test_files_only (deprecated)
            usage_type = arguments.get("usage_type", "source")
            test_files_only = arguments.get("test_files_only")
            if test_files_only is not None:
                # Convert old boolean parameter to new string parameter
                usage_type = "tests" if test_files_only else "all"

            changed_since = arguments.get("changed_since")
            show_relationships = arguments.get("show_relationships", True)

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
                show_relationships,
                module_path,
            )

        elif name == "search_module_usage":
            module_name = arguments.get("module_name")
            output_format = arguments.get("format", "markdown")
            usage_type = arguments.get("usage_type", "source")

            if not module_name:
                error_msg = "'module_name' is required"
                return [TextContent(type="text", text=error_msg)]

            # Accept both old and new values for backward compatibility
            valid_usage_types = ("all", "tests", "source", "test_only", "production_only")
            if usage_type not in valid_usage_types:
                error_msg = "'usage_type' must be one of: 'all', 'tests', 'source' (deprecated: 'test_only', 'production_only')"
                return [TextContent(type="text", text=error_msg)]

            return await self.module_handler.search_module_usage(
                module_name, output_format, usage_type
            )

        elif name == "find_pr_for_line":
            file_path = arguments.get("file_path")
            line_number = arguments.get("line_number")
            output_format = arguments.get("format", "text")

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            if not line_number:
                error_msg = "'line_number' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self.pr_handler.find_pr_for_line(file_path, line_number, output_format)

        elif name == "get_commit_history":
            file_path = arguments.get("file_path")
            function_name = arguments.get("function_name")
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")
            precise_tracking = arguments.get("precise_tracking", False)
            show_evolution = arguments.get("show_evolution", False)
            max_commits = arguments.get("max_commits", 10)
            since_date = arguments.get("since_date")
            until_date = arguments.get("until_date")
            author = arguments.get("author")
            min_changes = arguments.get("min_changes", 0)

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            # Validate line range parameters
            if (precise_tracking or show_evolution) and (not start_line or not end_line):
                error_msg = "Both 'start_line' and 'end_line' are required for precise_tracking or show_evolution"
                return [TextContent(type="text", text=error_msg)]

            return await self.git_handler.get_file_history(
                file_path,
                function_name,
                start_line,
                end_line,
                precise_tracking,
                show_evolution,
                max_commits,
                since_date,
                until_date,
                author,
                min_changes,
            )

        elif name == "get_blame":
            file_path = arguments.get("file_path")
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            if not start_line or not end_line:
                error_msg = "Both 'start_line' and 'end_line' are required"
                return [TextContent(type="text", text=error_msg)]

            return await self.git_handler.get_function_blame(file_path, start_line, end_line)

        elif name == "get_file_pr_history":
            file_path = arguments.get("file_path")

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self.pr_handler.get_file_pr_history(file_path)

        elif name == "search_by_features" or name == "search_by_keywords":
            # Support both names for backward compatibility
            # search_by_keywords is deprecated but still functional
            keywords = arguments.get("keywords")
            filter_type = arguments.get("filter_type", "all")
            min_score = arguments.get("min_score", 0.0)
            match_source = arguments.get("match_source", "all")

            if not keywords:
                error_msg = "'keywords' is required"
                return [TextContent(type="text", text=error_msg)]

            if not isinstance(keywords, list):
                error_msg = "'keywords' must be a list of strings"
                return [TextContent(type="text", text=error_msg)]

            if filter_type not in ("all", "modules", "functions"):
                error_msg = "'filter_type' must be one of: 'all', 'modules', 'functions'"
                return [TextContent(type="text", text=error_msg)]

            if not isinstance(min_score, (int, float)) or min_score < 0.0 or min_score > 1.0:
                error_msg = "'min_score' must be a number between 0.0 and 1.0"
                return [TextContent(type="text", text=error_msg)]

            if match_source not in ("all", "docs", "strings"):
                error_msg = "'match_source' must be one of: 'all', 'docs', 'strings'"
                return [TextContent(type="text", text=error_msg)]

            return await self.analysis_handler.search_by_keywords(
                keywords, filter_type, min_score, match_source
            )

        elif name == "find_dead_code":
            min_confidence = arguments.get("min_confidence", "high")
            output_format = arguments.get("format", "markdown")

            return await self.analysis_handler.find_dead_code(min_confidence, output_format)

        elif name == "get_module_dependencies":
            module_name = arguments.get("module_name")
            if not module_name:
                raise ValueError("module_name is required")
            output_format = arguments.get("format", "markdown")
            depth = arguments.get("depth", 1)
            granular = arguments.get("granular", False)

            return await self.dependency_handler.get_module_dependencies(
                module_name, output_format, depth, granular
            )

        elif name == "get_function_dependencies":
            module_name = arguments.get("module_name")
            function_name = arguments.get("function_name")
            arity = arguments.get("arity")
            if not module_name:
                raise ValueError("module_name is required")
            if not function_name:
                raise ValueError("function_name is required")
            if arity is None:
                raise ValueError("arity is required")
            output_format = arguments.get("format", "markdown")
            include_context = arguments.get("include_context", False)

            return await self.dependency_handler.get_function_dependencies(
                module_name, function_name, arity, output_format, include_context
            )

        else:
            raise ValueError(f"Unknown tool: {name}")
