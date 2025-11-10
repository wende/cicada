#!/usr/bin/env python
"""
Cicada MCP Server - Elixir Module Search.

Provides an MCP tool to search for Elixir modules and their functions.

Author: Cursor(Auto)
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cicada.command_logger import get_logger
from cicada.format import ModuleFormatter
from cicada.git_helper import GitHelper
from cicada.mcp.pattern_utils import (
    FunctionPattern,
    has_wildcards,
    match_any_pattern,
    parse_function_patterns,
    split_or_patterns,
)
from cicada.mcp.tools import get_tool_definitions
from cicada.pr_finder import PRFinder
from cicada.utils import find_similar_names, get_config_path, get_pr_index_path, load_index


class CicadaServer:
    """MCP server for Elixir module search."""

    def __init__(self, config_path: str | None = None):
        """
        Initialize the server with configuration.

        Args:
            config_path: Path to config file. If None, uses environment variables
                        or default path.
        """
        if config_path is None:
            config_path = self._get_config_path()

        self.config = self._load_config(config_path)
        self.index = self._load_index()
        self._pr_index: dict | None = None  # Lazy load PR index only when needed
        self.server = Server("cicada")

        # Cache keyword availability check
        self._has_keywords = self._check_keywords_available()

        # Initialize git helper
        repo_path = self.config.get("repository", {}).get("path", ".")
        self.git_helper: GitHelper | None = None
        try:
            self.git_helper = GitHelper(repo_path)
        except Exception as e:
            # If git initialization fails, set to None
            # (e.g., not a git repository)
            print(f"Warning: Git helper not available: {e}", file=sys.stderr)

        # Initialize command logger
        self.logger = get_logger()

        # Register handlers
        _ = self.server.list_tools()(self.list_tools)
        _ = self.server.call_tool()(self.call_tool_with_logging)

    def _get_config_path(self) -> str:
        """
        Determine the config file path from environment or defaults.

        Returns:
            Path to the config file
        """
        # Check if CICADA_CONFIG_DIR is set (direct path to storage directory)
        config_dir = os.environ.get("CICADA_CONFIG_DIR")
        if config_dir:
            return str(Path(config_dir) / "config.yaml")

        # Determine repository path from environment or current directory
        repo_path = None

        # Check if WORKSPACE_FOLDER_PATHS is available (Cursor-specific)
        workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
        if workspace_paths:
            # WORKSPACE_FOLDER_PATHS might be a single path or multiple paths
            # Take the first one if multiple
            # Use os.pathsep for platform-aware splitting (';' on Windows, ':' on Unix)
            repo_path = (
                workspace_paths.split(os.pathsep)[0]
                if os.pathsep in workspace_paths
                else workspace_paths
            )

        # Fall back to current working directory
        if not repo_path:
            repo_path = str(Path.cwd().resolve())

        # Calculate config path from repository path
        config_path = get_config_path(repo_path)
        return str(config_path)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n\n"
                f"Please run setup first:\n"
                f"  cicada cursor  # For Cursor\n"
                f"  cicada claude  # For Claude Code\n"
                f"  cicada vs      # For VS Code"
            )

        with open(config_file) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}

    def _load_index(self) -> dict[str, Any]:
        """Load the index from JSON file."""
        import json

        index_path = Path(self.config["storage"]["index_path"])

        try:
            result = load_index(index_path, raise_on_error=True)
            if result is None:
                raise FileNotFoundError(
                    f"Index file not found: {index_path}\n\n"
                    f"Please run setup first:\n"
                    f"  cicada cursor  # For Cursor\n"
                    f"  cicada claude  # For Claude Code\n"
                    f"  cicada vs      # For VS Code"
                )
            return result
        except json.JSONDecodeError as e:
            # Index file is corrupted - provide helpful message
            repo_path = self.config.get("repository", {}).get("path", ".")
            raise RuntimeError(
                f"Index file is corrupted: {index_path}\n"
                f"Error: {e}\n\n"
                f"To rebuild the index, run:\n"
                f"  cd {repo_path}\n"
                f"  cicada clean -f  # Safer cleanup\n"
                f"  cicada cursor  # or: cicada claude, cicada vs\n"
            ) from e
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Index file not found: {index_path}\n\n"
                f"Please run setup first:\n"
                f"  cicada cursor  # For Cursor\n"
                f"  cicada claude  # For Claude Code\n"
                f"  cicada vs      # For VS Code"
            ) from None

    @property
    def pr_index(self) -> dict[str, Any] | None:
        """Lazy load the PR index from JSON file."""
        if self._pr_index is None:
            # Get repo path from config
            repo_path = Path(self.config.get("repository", {}).get("path", "."))

            # Use new storage structure only
            pr_index_path = get_pr_index_path(repo_path)
            self._pr_index = load_index(pr_index_path, verbose=True, raise_on_error=False)
        return self._pr_index

    def _load_pr_index(self) -> dict[str, Any] | None:
        """Load the PR index from JSON file."""
        # Get repo path from config
        repo_path = Path(self.config.get("repository", {}).get("path", "."))

        # Use new storage structure only
        pr_index_path = get_pr_index_path(repo_path)
        return load_index(pr_index_path, verbose=True, raise_on_error=False)

    def _check_keywords_available(self) -> bool:
        """
        Check if any keywords are available in the index.

        This is cached at initialization to avoid repeated checks.

        Returns:
            True if keywords are available in the index
        """
        for module_data in self.index.get("modules", {}).values():
            if module_data.get("keywords"):
                return True
            for func in module_data.get("functions", []):
                if func.get("keywords"):
                    return True
        return False

    def _check_index_staleness(self) -> dict[str, Any] | None:
        """
        Check if the index is stale by comparing file modification times.

        Returns:
            Dictionary with staleness info (is_stale, index_age, newest_file_age) or None
        """
        try:
            import os
            import random
            from datetime import datetime

            # Get index file path and modification time
            index_path = Path(self.config["storage"]["index_path"])
            if not index_path.exists():
                return None

            index_mtime = os.path.getmtime(index_path)
            index_age = datetime.now().timestamp() - index_mtime

            # Get repo path
            repo_path = Path(self.config.get("repository", {}).get("path", "."))

            # Check a sample of indexed files to see if any are newer than the index
            # Use random sampling for better coverage
            max_files_to_check = 50
            all_modules = list(self.index.get("modules", {}).values())

            if len(all_modules) > max_files_to_check:
                modules_to_check = random.sample(all_modules, max_files_to_check)
            else:
                modules_to_check = all_modules

            newest_file_mtime = 0

            for module_data in modules_to_check:
                file_path = repo_path / module_data["file"]
                if file_path.exists():
                    file_mtime = os.path.getmtime(file_path)
                    newest_file_mtime = max(newest_file_mtime, file_mtime)

            # Check if any files are newer than the index
            is_stale = newest_file_mtime > index_mtime

            if is_stale:
                # Calculate how old the index is in human-readable format
                hours_old = index_age / 3600
                if hours_old < 1:
                    age_str = f"{int(index_age / 60)} minutes"
                elif hours_old < 24:
                    age_str = f"{int(hours_old)} hours"
                else:
                    age_str = f"{int(hours_old / 24)} days"

                return {
                    "is_stale": True,
                    "age_str": age_str,
                }

            return None
        except (OSError, KeyError):
            # Expected errors - file permissions, disk issues, config issues
            # Silently ignore these as staleness check is non-critical
            return None
        except Exception as e:
            # Unexpected error - log for debugging but don't break functionality
            import sys

            print(f"Warning: Unexpected error checking index staleness: {e}", file=sys.stderr)
            return None

    async def list_tools(self) -> list[Tool]:
        """List available MCP tools."""
        return get_tool_definitions()

    async def call_tool_with_logging(self, name: str, arguments: dict) -> list[TextContent]:
        """Wrapper for call_tool that logs execution details."""
        from datetime import datetime

        # Record start time
        start_time = time.perf_counter()
        timestamp = datetime.now()
        error_msg = None
        response = None

        try:
            # Call the actual tool handler
            response = await self.call_tool(name, arguments)
            return response
        except Exception as e:
            # Capture error if tool execution fails
            error_msg = str(e)
            raise
        finally:
            # Calculate execution time in milliseconds
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # Log the command execution (async to prevent event loop blocking)
            await self.logger.log_command_async(
                tool_name=name,
                arguments=arguments,
                response=response,
                execution_time_ms=execution_time_ms,
                timestamp=timestamp,
                error=error_msg,
            )

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        if name == "search_module":
            module_name = arguments.get("module_name")
            file_path = arguments.get("file_path")
            output_format = arguments.get("format", "markdown")
            private_functions = arguments.get("private_functions", "exclude")

            # Validate that at least one is provided
            if not module_name and not file_path:
                error_msg = "Either 'module_name' or 'file_path' must be provided"
                return [TextContent(type="text", text=error_msg)]

            # If file_path is provided, resolve it to module_name
            if file_path:
                resolved_module = self._resolve_file_to_module(file_path)
                if not resolved_module:
                    error_msg = f"Could not find module in file: {file_path}"
                    return [TextContent(type="text", text=error_msg)]
                module_name = resolved_module

            assert module_name is not None, "module_name must be provided"
            return await self._search_module(module_name, output_format, private_functions)
        elif name == "search_function":
            function_name = arguments.get("function_name")
            output_format = arguments.get("format", "markdown")
            include_usage_examples = arguments.get("include_usage_examples", False)
            max_examples = arguments.get("max_examples", 5)
            test_files_only = arguments.get("test_files_only", False)
            changed_since = arguments.get("changed_since")
            show_relationships = arguments.get("show_relationships", True)

            if not function_name:
                error_msg = "'function_name' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_function(
                function_name,
                output_format,
                include_usage_examples,
                max_examples,
                test_files_only,
                changed_since,
                show_relationships,
            )
        elif name == "search_module_usage":
            module_name = arguments.get("module_name")
            output_format = arguments.get("format", "markdown")
            usage_type = arguments.get("usage_type", "all")

            if not module_name:
                error_msg = "'module_name' is required"
                return [TextContent(type="text", text=error_msg)]

            if usage_type not in ("all", "test_only", "production_only"):
                error_msg = "'usage_type' must be one of: 'all', 'test_only', 'production_only'"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_module_usage(module_name, output_format, usage_type)
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

            return await self._find_pr_for_line(file_path, line_number, output_format)
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

            return await self._get_file_history(
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

            return await self._get_function_history(file_path, start_line, end_line)
        elif name == "get_file_pr_history":
            file_path = arguments.get("file_path")

            if not file_path:
                error_msg = "'file_path' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._get_file_pr_history(file_path)
        elif name == "search_by_features" or name == "search_by_keywords":
            # Support both names for backward compatibility
            # search_by_keywords is deprecated but still functional
            keywords = arguments.get("keywords")
            filter_type = arguments.get("filter_type", "all")
            min_score = arguments.get("min_score", 0.0)

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

            return await self._search_by_keywords(keywords, filter_type, min_score)
        elif name == "find_dead_code":
            min_confidence = arguments.get("min_confidence", "high")
            output_format = arguments.get("format", "markdown")

            return await self._find_dead_code(min_confidence, output_format)
        elif name == "get_module_dependencies":
            module_name = arguments.get("module_name")
            if not module_name:
                raise ValueError("module_name is required")
            output_format = arguments.get("format", "markdown")
            depth = arguments.get("depth", 1)
            granular = arguments.get("granular", False)

            return await self._get_module_dependencies(module_name, output_format, depth, granular)
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

            return await self._get_function_dependencies(
                module_name, function_name, arity, output_format, include_context
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

    def _lookup_module_with_error(
        self, module_name: str, include_suggestions: bool = True
    ) -> tuple[dict | None, str | None]:
        """
        Look up a module in the index with error handling.

        Args:
            module_name: Module name to look up
            include_suggestions: Whether to include similar module suggestions in error

        Returns:
            Tuple of (module_data, error_message). If found, returns (data, None).
            If not found, returns (None, error_message).
        """
        module_data = self.index["modules"].get(module_name)
        if module_data:
            return module_data, None

        # Module not found - create error message
        error_msg = f"Module not found: {module_name}"
        if include_suggestions:
            similar = find_similar_names(module_name, list(self.index["modules"].keys()))
            if similar:
                error_msg += "\n\nDid you mean one of these?\n" + "\n".join(
                    f"  - {name}" for name in similar[:5]
                )
        return None, error_msg

    def _resolve_file_to_module(self, file_path: str) -> str | None:
        """Resolve a file path to a module name by searching the index."""
        # Normalize the file path (remove leading ./ and trailing whitespace)
        normalized_path = file_path.strip().lstrip("./")

        # Search through all modules to find one matching this file path
        for module_name, module_data in self.index["modules"].items():
            module_file = module_data["file"]

            # Check for exact match
            if module_file == normalized_path:
                return module_name

            # Also check if the provided path ends with the module file
            # (handles cases where user provides absolute path)
            if normalized_path.endswith(module_file):
                return module_name

            # Check if the module file ends with the provided path
            # (handles cases where user provides just filename or partial path)
            if module_file.endswith(normalized_path):
                return module_name

        return None

    async def _search_module(
        self,
        module_name: str,
        output_format: str = "markdown",
        private_functions: str = "exclude",
    ) -> list[TextContent]:
        """
        Search for a module and return its information.

        Supports wildcards (*) and OR patterns (|) for both module names and file paths.
        Examples:
            - "MyApp.*" - matches all modules starting with MyApp.
            - "*User*" - matches all modules containing User
            - "lib/my_app/*.ex" - matches all modules in that directory
            - "MyApp.User|MyApp.Post" - matches either module
            - "*User*|*Post*" - matches modules containing User OR Post
        """
        # Check for wildcard or OR patterns
        if has_wildcards(module_name):
            # Split by OR patterns
            patterns = split_or_patterns(module_name)

            # Find all matching modules
            matching_modules = []
            for mod_name, mod_data in self.index["modules"].items():
                # Check if module name or file path matches any pattern
                if match_any_pattern(patterns, mod_name) or match_any_pattern(
                    patterns, mod_data["file"]
                ):
                    matching_modules.append((mod_name, mod_data))

            # If no matches found, return error
            if not matching_modules:
                total_modules = self.index["metadata"]["total_modules"]
                if output_format == "json":
                    error_result = ModuleFormatter.format_error_json(module_name, total_modules)
                else:
                    error_result = ModuleFormatter.format_error_markdown(module_name, total_modules)
                return [TextContent(type="text", text=error_result)]

            # Format all matching modules
            results: list[str] = []
            for mod_name, mod_data in matching_modules:
                if output_format == "json":
                    result = ModuleFormatter.format_module_json(
                        mod_name, mod_data, private_functions
                    )
                else:
                    result = ModuleFormatter.format_module_markdown(
                        mod_name, mod_data, private_functions
                    )
                results.append(result)

            # Combine results with separator for markdown, or as array for JSON
            if output_format == "json":
                # For JSON, wrap in array notation
                combined = "[\n" + ",\n".join(results) + "\n]"
            else:
                # For markdown, separate with horizontal rules
                header = (
                    f"Found {len(matching_modules)} module(s) matching pattern '{module_name}':\n\n"
                )
                combined = header + "\n\n---\n\n".join(results)

            return [TextContent(type="text", text=combined)]

        # Exact match lookup (no wildcards)
        if module_name in self.index["modules"]:
            data = self.index["modules"][module_name]

            # Get PR context for the file
            pr_info = self._get_recent_pr_info(data["file"])

            # Check index staleness
            staleness_info = self._check_index_staleness()

            if output_format == "json":
                result = ModuleFormatter.format_module_json(module_name, data, private_functions)
            else:
                result = ModuleFormatter.format_module_markdown(
                    module_name, data, private_functions, pr_info, staleness_info
                )

            return [TextContent(type="text", text=result)]

        # Module not found - compute suggestions and provide helpful error message
        total_modules = self.index["metadata"]["total_modules"]

        if output_format == "json":
            error_result = ModuleFormatter.format_error_json(module_name, total_modules)
        else:
            # Compute fuzzy match suggestions
            available_modules = list(self.index["modules"].keys())
            similar_matches = find_similar_names(module_name, available_modules, max_suggestions=3)
            suggestions = [name for name, _score in similar_matches]

            error_result = ModuleFormatter.format_error_markdown(
                module_name, total_modules, suggestions
            )

        return [TextContent(type="text", text=error_result)]

    async def _search_function(
        self,
        function_name: str,
        output_format: str = "markdown",
        include_usage_examples: bool = False,
        max_examples: int = 5,
        test_files_only: bool = False,
        changed_since: str | None = None,
        show_relationships: bool = True,
    ) -> list[TextContent]:
        """
        Search for a function across all modules and return matches with call sites.

        Supports wildcards (*) and OR patterns (|) for function names, module names, and file paths.
        Examples:
            - "create*" - matches all functions starting with create
            - "*user*" - matches all functions containing user
            - "MyApp.User.create*" - matches create* functions in MyApp.User module
            - "create*|update*" - matches functions starting with create OR update
            - "MyApp.*.create/1" - matches create/1 in any module under MyApp
            - "lib/*/user.ex:create*" - matches create* functions in files matching path pattern
        """
        # Support OR syntax by splitting first, then parsing each component individually
        parsed_patterns: list[FunctionPattern] = parse_function_patterns(function_name)

        # Search across all modules for function definitions
        results = []
        seen_functions: set[tuple[str, str, int]] = set()
        # Parse changed_since filter if provided
        cutoff_date = None
        if changed_since:
            cutoff_date = self._parse_changed_since(changed_since)

        for module_name, module_data in self.index["modules"].items():
            for func in module_data["functions"]:
                if any(
                    pattern.matches(module_name, module_data["file"], func)
                    for pattern in parsed_patterns
                ):
                    # Filter by changed_since if provided
                    if cutoff_date:
                        func_modified = func.get("last_modified_at")
                        if not func_modified:
                            continue  # Skip functions without timestamp

                        func_modified_dt = datetime.fromisoformat(func_modified)
                        # Ensure timezone-aware for comparison
                        if func_modified_dt.tzinfo is None:
                            func_modified_dt = func_modified_dt.replace(tzinfo=timezone.utc)

                        if func_modified_dt < cutoff_date:
                            continue  # Function too old, skip

                    key = (module_name, func["name"], func["arity"])
                    if key in seen_functions:
                        continue
                    seen_functions.add(key)
                    # Find call sites for this function
                    call_sites = self._find_call_sites(
                        target_module=module_name,
                        target_function=func["name"],
                        target_arity=func["arity"],
                    )

                    # Filter for test files only if requested
                    if test_files_only:
                        call_sites = self._filter_test_call_sites(call_sites)

                    # Optionally include usage examples (actual code lines)
                    call_sites_with_examples = []
                    if include_usage_examples and call_sites:
                        # Consolidate call sites by calling module (one example per module)
                        consolidated_sites = self._consolidate_call_sites_by_module(call_sites)
                        # Limit the number of examples
                        call_sites_with_examples = consolidated_sites[:max_examples]
                        # Extract code lines for each call site
                        self._add_code_examples(call_sites_with_examples)

                    # Get PR context for this function
                    pr_info = self._get_recent_pr_info(module_data["file"])

                    # Get function dependencies if show_relationships is enabled
                    dependencies = []
                    if show_relationships:
                        dependencies = func.get("dependencies", [])

                    results.append(
                        {
                            "module": module_name,
                            "moduledoc": module_data.get("moduledoc"),
                            "function": func,
                            "file": module_data["file"],
                            "call_sites": call_sites,
                            "call_sites_with_examples": call_sites_with_examples,
                            "pr_info": pr_info,
                            "dependencies": dependencies,
                        }
                    )

        # Check index staleness
        staleness_info = self._check_index_staleness()

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_function_results_json(function_name, results)
        else:
            result = ModuleFormatter.format_function_results_markdown(
                function_name, results, staleness_info, show_relationships
            )

        return [TextContent(type="text", text=result)]

    async def _search_module_usage(
        self, module_name: str, output_format: str = "markdown", usage_type: str = "all"
    ) -> list[TextContent]:
        """
        Search for all locations where a module is used (aliased/imported and called).

        Args:
            module_name: The module to search for (e.g., "MyApp.User")
            output_format: Output format ('markdown' or 'json')
            usage_type: Filter by file type ('all', 'test_only', 'production_only')

        Returns:
            TextContent with usage information
        """
        # Check if the module exists in the index
        if module_name not in self.index["modules"]:
            error_msg = f"Module '{module_name}' not found in index."
            return [TextContent(type="text", text=error_msg)]

        usage_results = {
            "aliases": [],  # Modules that alias the target module
            "imports": [],  # Modules that import the target module
            "requires": [],  # Modules that require the target module
            "uses": [],  # Modules that use the target module
            "value_mentions": [],  # Modules that mention the target as a value
            "function_calls": [],  # Direct function calls to the target module
        }

        # Search through all modules to find usage
        for caller_module, module_data in self.index["modules"].items():
            # Skip the module itself
            if caller_module == module_name:
                continue

            # Check aliases
            aliases = module_data.get("aliases", {})
            for alias_name, full_module in aliases.items():
                if full_module == module_name:
                    usage_results["aliases"].append(
                        {
                            "importing_module": caller_module,
                            "alias_name": alias_name,
                            "full_module": full_module,
                            "file": module_data["file"],
                        }
                    )

            # Check imports
            imports = module_data.get("imports", [])
            if module_name in imports:
                usage_results["imports"].append(
                    {
                        "importing_module": caller_module,
                        "file": module_data["file"],
                    }
                )

            # Check requires
            requires = module_data.get("requires", [])
            if module_name in requires:
                usage_results["requires"].append(
                    {
                        "importing_module": caller_module,
                        "file": module_data["file"],
                    }
                )

            # Check uses
            uses = module_data.get("uses", [])
            if module_name in uses:
                usage_results["uses"].append(
                    {
                        "importing_module": caller_module,
                        "file": module_data["file"],
                    }
                )

            # Check value mentions
            value_mentions = module_data.get("value_mentions", [])
            if module_name in value_mentions:
                usage_results["value_mentions"].append(
                    {
                        "importing_module": caller_module,
                        "file": module_data["file"],
                    }
                )

            # Check function calls
            calls = module_data.get("calls", [])
            module_calls = {}  # Track calls grouped by function

            for call in calls:
                call_module = call.get("module")

                # Resolve the call's module name using aliases
                if call_module:
                    resolved_module = aliases.get(call_module, call_module)

                    if resolved_module == module_name:
                        # Track which function is being called
                        func_key = f"{call['function']}/{call['arity']}"

                        if func_key not in module_calls:
                            module_calls[func_key] = {
                                "function": call["function"],
                                "arity": call["arity"],
                                "lines": [],
                                "alias_used": (
                                    call_module if call_module != resolved_module else None
                                ),
                            }

                        module_calls[func_key]["lines"].append(call["line"])

            # Add call information if there are any calls
            if module_calls:
                usage_results["function_calls"].append(
                    {
                        "calling_module": caller_module,
                        "file": module_data["file"],
                        "calls": list(module_calls.values()),
                    }
                )

        # Apply usage type filter if not 'all'
        if usage_type != "all":
            from cicada.mcp.filter_utils import filter_by_file_type

            # Filter each category that has file information
            for category in [
                "aliases",
                "imports",
                "requires",
                "uses",
                "value_mentions",
                "function_calls",
            ]:
                usage_results[category] = filter_by_file_type(usage_results[category], usage_type)

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_module_usage_json(module_name, usage_results)
        else:
            result = ModuleFormatter.format_module_usage_markdown(module_name, usage_results)

        return [TextContent(type="text", text=result)]

    def _add_code_examples(self, call_sites: list):
        """
        Add actual code lines to call sites.

        Args:
            call_sites: List of call site dictionaries to enhance with code examples

        Modifies call_sites in-place by adding 'code_line' key with the actual source code.
        Extracts complete function calls from opening '(' to closing ')'.
        """
        # Get the repo path from the index metadata (fallback to config if not available)
        repo_path_str = self.index.get("metadata", {}).get("repo_path")
        if not repo_path_str:
            # Fallback to config if available
            repo_path_str = self.config.get("repository", {}).get("path")

        if not repo_path_str:
            # Can't add examples without repo path
            return

        repo_path = Path(repo_path_str)

        for site in call_sites:
            file_path = repo_path / site["file"]
            line_number = site["line"]

            try:
                # Read all lines from the file
                with open(file_path) as f:
                    lines = f.readlines()

                # Extract complete function call
                code_lines = self._extract_complete_call(lines, line_number)
                if code_lines:
                    site["code_line"] = code_lines
            except (OSError, FileNotFoundError, IndexError):
                # If we can't read the file/line, just skip adding the code example
                pass

    def _extract_complete_call(self, lines: list[str], start_line: int) -> str | None:
        """
        Extract code with ±2 lines of context around the call line.

        Args:
            lines: All lines from the file
            start_line: Line number where the call starts (1-indexed)

        Returns:
            Code snippet with context, dedented to remove common leading whitespace
        """
        if start_line < 1 or start_line > len(lines):
            return None

        # Convert to 0-indexed
        call_idx = start_line - 1

        # Calculate context range (±2 lines)
        context_lines = 2
        start_idx = max(0, call_idx - context_lines)
        end_idx = min(len(lines), call_idx + context_lines + 1)

        # Extract the lines with context
        extracted_lines = []
        for i in range(start_idx, end_idx):
            extracted_lines.append(lines[i].rstrip("\n"))

        # Dedent: strip common leading whitespace
        if extracted_lines:
            # Find minimum indentation (excluding empty/whitespace-only lines)
            min_indent: int | float = float("inf")
            for line in extracted_lines:
                if line.strip():  # Skip empty/whitespace-only lines
                    leading_spaces = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, leading_spaces)

            # Strip the common indentation from all lines
            if min_indent != float("inf") and min_indent > 0:
                dedented_lines = []
                min_indent_int = int(min_indent)
                for line in extracted_lines:
                    if len(line) >= min_indent_int:
                        dedented_lines.append(line[min_indent_int:])
                    else:
                        dedented_lines.append(line)
                extracted_lines = dedented_lines

        return "\n".join(extracted_lines) if extracted_lines else None

    def _find_call_sites(self, target_module: str, target_function: str, target_arity: int) -> list:
        """
        Find all locations where a function is called.

        Args:
            target_module: The module containing the function (e.g., "MyApp.User")
            target_function: The function name (e.g., "create_user")
            target_arity: The function arity

        Returns:
            List of call sites with resolved module names
        """
        call_sites = []

        # Find the function definition line to filter out @spec/@doc
        function_def_line = None
        if target_module in self.index["modules"]:
            for func in self.index["modules"][target_module]["functions"]:
                if func["name"] == target_function and func["arity"] == target_arity:
                    function_def_line = func["line"]
                    break

        for caller_module, module_data in self.index["modules"].items():
            # Get aliases for this module to resolve calls
            aliases = module_data.get("aliases", {})

            # Check all calls in this module
            for call in module_data.get("calls", []):
                if call["function"] != target_function:
                    continue

                if call["arity"] != target_arity:
                    continue

                # Resolve the call's module name using aliases
                call_module = call.get("module")

                if call_module is None:
                    # Local call - check if it's in the same module
                    if caller_module == target_module:
                        # Filter out calls that are part of the function definition
                        # (@spec, @doc appear 1-5 lines before the def)
                        if function_def_line and abs(call["line"] - function_def_line) <= 5:
                            continue

                        # Find the calling function
                        calling_function = self._find_function_at_line(caller_module, call["line"])

                        call_sites.append(
                            {
                                "calling_module": caller_module,
                                "calling_function": calling_function,
                                "file": module_data["file"],
                                "line": call["line"],
                                "call_type": "local",
                            }
                        )
                else:
                    # Qualified call - resolve the module name
                    resolved_module = aliases.get(call_module, call_module)

                    # Check if this resolves to our target module
                    if resolved_module == target_module:
                        # Find the calling function
                        calling_function = self._find_function_at_line(caller_module, call["line"])

                        call_sites.append(
                            {
                                "calling_module": caller_module,
                                "calling_function": calling_function,
                                "file": module_data["file"],
                                "line": call["line"],
                                "call_type": "qualified",
                                "alias_used": (
                                    call_module if call_module != resolved_module else None
                                ),
                            }
                        )

        return call_sites

    def _parse_changed_since(self, changed_since: str) -> datetime:
        """
        Parse changed_since parameter into datetime.

        Supports:
        - ISO dates: '2024-01-15'
        - Relative: '7d', '2w', '3m', '1y'
        - Git refs: 'HEAD~10', 'v1.0.0' (if git_helper available)

        Returns:
            datetime object (timezone-aware) representing the cutoff date

        Raises:
            ValueError: If format is invalid or amount is negative/zero
        """
        # ISO date format (YYYY-MM-DD)
        if "-" in changed_since and len(changed_since) >= 10:
            try:
                dt = datetime.fromisoformat(changed_since)
                # Ensure timezone-aware - if naive, assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass

        # Relative format (7d, 2w, 3m, 1y)
        if len(changed_since) >= 2 and changed_since[-1] in "dwmy":
            try:
                amount = int(changed_since[:-1])
                unit = changed_since[-1]

                # Validate positive amount
                if amount <= 0:
                    raise ValueError(f"Time amount must be positive, got: {amount}{unit}")

                now = datetime.now(timezone.utc)
                if unit == "d":
                    return now - timedelta(days=amount)
                elif unit == "w":
                    return now - timedelta(weeks=amount)
                elif unit == "m":
                    return now - timedelta(days=amount * 30)
                elif unit == "y":
                    return now - timedelta(days=amount * 365)
            except ValueError as e:
                # Re-raise if it's our validation error
                if "Time amount must be positive" in str(e):
                    raise
                # Otherwise, try next format (likely invalid int parsing)

        # Git ref format (requires git_helper)
        if self.git_helper:
            try:
                # Validate git ref format to prevent command injection
                # Refs should not start with - or -- (could be flags)
                if changed_since.startswith("-"):
                    raise ValueError(f"Invalid git ref format (starts with '-'): {changed_since}")

                # Get timestamp of the ref using git show
                repo_path = self.git_helper.repo_path
                result = subprocess.run(
                    ["git", "show", "-s", "--format=%ai", changed_since],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                dt = datetime.fromisoformat(result.stdout.strip())
                # Git returns timezone-aware datetime, ensure it has tzinfo
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except subprocess.CalledProcessError:
                # Git command failed - invalid ref or other git error
                pass
            except ValueError:
                # Re-raise validation errors
                raise
            except Exception:
                # Other errors (e.g., datetime parsing) - try next format
                pass

        raise ValueError(f"Invalid changed_since format: {changed_since}")

    def _get_recent_pr_info(self, file_path: str) -> dict | None:
        """
        Get the most recent PR that modified a file.

        Args:
            file_path: Relative path to the file

        Returns:
            Dictionary with PR info (number, title, date, comment_count) or None
        """
        if not self.pr_index:
            return None

        # Look up PRs for this file
        file_to_prs = self.pr_index.get("file_to_prs", {})
        pr_numbers = file_to_prs.get(file_path, [])

        if not pr_numbers:
            return None

        # Get the most recent PR (last in list)
        prs_data = self.pr_index.get("prs", {})
        most_recent_pr_num = pr_numbers[-1]
        pr = prs_data.get(str(most_recent_pr_num))

        if not pr:
            return None

        # Count comments for this file
        comments = pr.get("comments", [])
        file_comments = [c for c in comments if c.get("path") == file_path]

        return {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr.get("author", "unknown"),
            "comment_count": len(file_comments),
            "url": pr.get("url", ""),
        }

    def _find_function_at_line(self, module_name: str, line: int) -> dict | None:
        """
        Find the function that contains a specific line number.

        Args:
            module_name: The module to search in
            line: The line number

        Returns:
            Dictionary with 'name' and 'arity', or None if not found
        """
        if module_name not in self.index["modules"]:
            return None

        module_data = cast(dict[str, Any], self.index["modules"][module_name])
        functions: list[Any] = module_data.get("functions", [])

        # Find the function whose definition line is closest before the target line
        best_match: dict[str, Any] | None = None
        for func in functions:
            func_line = func["line"]
            # The function must be defined before or at the line
            # Keep the closest one
            if func_line <= line and (best_match is None or func_line > best_match["line"]):
                best_match = {
                    "name": func["name"],
                    "arity": func["arity"],
                    "line": func_line,
                }

        return best_match

    def _consolidate_call_sites_by_module(self, call_sites: list) -> list:
        """
        Consolidate call sites by calling module, keeping only one example per module.
        Prioritizes keeping test files separate from regular code files.

        Args:
            call_sites: List of call site dictionaries

        Returns:
            Consolidated list with one call site per unique calling module
        """
        seen_modules = {}
        consolidated = []

        for site in call_sites:
            module = site["calling_module"]

            # If we haven't seen this module yet, add it
            if module not in seen_modules:
                seen_modules[module] = site
                consolidated.append(site)

        return consolidated

    def _filter_test_call_sites(self, call_sites: list) -> list:
        """
        Filter call sites to only include calls from test files.

        A file is considered a test file if 'test' appears anywhere in its path.

        Args:
            call_sites: List of call site dictionaries

        Returns:
            Filtered list containing only call sites from test files
        """
        return [site for site in call_sites if "test" in site["file"].lower()]

    async def _find_pr_for_line(
        self, file_path: str, line_number: int, output_format: str = "text"
    ) -> list[TextContent]:
        """
        Find the PR that introduced a specific line of code.

        Args:
            file_path: Path to the file
            line_number: Line number (1-indexed)
            output_format: Output format ('text', 'json', or 'markdown')

        Returns:
            TextContent with PR information
        """
        try:
            # Get repo path from config
            repo_path = self.config.get("repository", {}).get("path", ".")
            index_path = get_pr_index_path(repo_path)

            # Check if index exists
            if not index_path.exists():
                error_msg = (
                    "PR index not found. Please run:\n"
                    "  cicada index-pr\n\n"
                    f"This will create the PR index at {index_path}"
                )
                return [TextContent(type="text", text=error_msg)]

            # Initialize PRFinder with index enabled
            pr_finder = PRFinder(
                repo_path=repo_path,
                use_index=True,
                index_path=str(index_path),
                verbose=False,
            )

            # Find PR for the line using index
            result = pr_finder.find_pr_for_line(file_path, line_number)

            # If no PR found in index, check if it exists via network
            if result.get("pr") is None and result.get("commit"):
                # Try network lookup to see if PR actually exists
                pr_finder_network = PRFinder(
                    repo_path=repo_path,
                    use_index=False,
                    verbose=False,
                )
                network_result = pr_finder_network.find_pr_for_line(file_path, line_number)

                if network_result.get("pr") is not None:
                    # PR exists but not in index - suggest update
                    error_msg = (
                        "PR index is incomplete. Please run:\n"
                        "  cicada index-pr\n\n"
                        "This will update the index with recent PRs (incremental by default)."
                    )
                    return [TextContent(type="text", text=error_msg)]
                else:
                    # No PR associated with this commit
                    result["pr"] = None  # Ensure it's explicitly None
                    result["note"] = "No PR associated with this line"

            # Format the result
            formatted_result = pr_finder.format_result(result, output_format)

            return [TextContent(type="text", text=formatted_result)]

        except Exception as e:
            error_msg = f"Error finding PR: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def _get_file_history(
        self,
        file_path: str,
        function_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        _precise_tracking: bool = False,
        show_evolution: bool = False,
        max_commits: int = 10,
        since_date: str | None = None,
        until_date: str | None = None,
        author: str | None = None,
        min_changes: int = 0,
    ) -> list[TextContent]:
        """
        Get git commit history for a file or function.

        Args:
            file_path: Path to the file
            function_name: Optional function name for function tracking (git log -L :funcname:file)
            start_line: Optional starting line for fallback line-based tracking
            end_line: Optional ending line for fallback line-based tracking
            precise_tracking: Deprecated (function tracking is always used when function_name provided)
            show_evolution: Include function evolution metadata
            max_commits: Maximum number of commits to return
            since_date: Only include commits after this date (ISO format or relative like '7d', '2w')
            until_date: Only include commits before this date (ISO format or relative)
            author: Filter by author name (substring match)
            min_changes: Minimum number of lines changed

        Returns:
            TextContent with formatted commit history

        Note:
            - If function_name is provided, uses git's function tracking
            - Function tracking works even as the function moves in the file
            - Line numbers are used as fallback if function tracking fails
            - Requires .gitattributes with "*.ex diff=elixir" for function tracking
            - Date filters only work with file-level history (not function/line tracking)
        """
        if not self.git_helper:
            error_msg = "Git history is not available (repository may not be a git repo)"
            return [TextContent(type="text", text=error_msg)]

        # Parse date filters if provided
        since_datetime = None
        until_datetime = None
        if since_date:
            since_datetime = self._parse_changed_since(since_date)
        if until_date:
            until_datetime = self._parse_changed_since(until_date)

        # Check if any filters are being used (only supported for file-level history)
        has_filters = since_date or until_date or author or min_changes > 0
        if has_filters and (function_name or (start_line and end_line)):
            warning_msg = "⚠️  Date/author/min_changes filters only work with file-level history (without function_name or line range)\n\n"
        else:
            warning_msg = ""

        try:
            evolution = None
            tracking_method = "file"

            # Determine which tracking method to use
            # Priority: function name > line numbers > file level
            if function_name:
                # Use function-based tracking (git log -L :funcname:file)
                commits = self.git_helper.get_function_history_precise(
                    file_path,
                    start_line=start_line,
                    end_line=end_line,
                    function_name=function_name,
                    max_commits=max_commits,
                )
                title = f"Git History for {function_name} in {file_path}"
                tracking_method = "function"

                # Get evolution metadata if requested
                if show_evolution:
                    evolution = self.git_helper.get_function_evolution(
                        file_path,
                        start_line=start_line,
                        end_line=end_line,
                        function_name=function_name,
                    )

            elif start_line and end_line:
                # Use line-based tracking (git log -L start,end:file)
                commits = self.git_helper.get_function_history_precise(
                    file_path,
                    start_line=start_line,
                    end_line=end_line,
                    max_commits=max_commits,
                )
                title = f"Git History for {file_path} (lines {start_line}-{end_line})"
                tracking_method = "line"

                if show_evolution:
                    evolution = self.git_helper.get_function_evolution(
                        file_path, start_line=start_line, end_line=end_line
                    )
            else:
                # File-level history
                if has_filters:
                    commits = self.git_helper.get_file_history_filtered(
                        file_path,
                        max_commits=max_commits,
                        since_date=since_datetime,
                        until_date=until_datetime,
                        author=author,
                        min_changes=min_changes,
                    )
                else:
                    commits = self.git_helper.get_file_history(file_path, max_commits)
                title = f"Git History for {file_path}"

            if not commits:
                result = f"No commit history found for {file_path}"
                return [TextContent(type="text", text=result)]

            # Format the results as markdown
            lines = [f"# {title}\n"]

            # Add warning if filters were specified but not used
            if warning_msg:
                lines.append(warning_msg)

            # Add filter information if filters were used
            if has_filters and not (function_name or (start_line and end_line)):
                filter_parts = []
                if since_date:
                    filter_parts.append(f"since {since_date}")
                if until_date:
                    filter_parts.append(f"until {until_date}")
                if author:
                    filter_parts.append(f"author: {author}")
                if min_changes > 0:
                    filter_parts.append(f"min changes: {min_changes}")
                lines.append(f"*Filters: {', '.join(filter_parts)}*\n")

            # Add tracking method info
            if tracking_method == "function":
                lines.append(
                    "*Using function tracking (git log -L :funcname:file) - tracks function even as it moves*\n"
                )
            elif tracking_method == "line":
                lines.append("*Using line-based tracking (git log -L start,end:file)*\n")

            # Add evolution metadata if available
            if evolution:
                lines.append("## Function Evolution\n")
                created = evolution["created_at"]
                modified = evolution["last_modified"]

                lines.append(
                    f"- **Created:** {created['date'][:10]} by {created['author']} (commit `{created['sha']}`)"
                )
                lines.append(
                    f"- **Last Modified:** {modified['date'][:10]} by {modified['author']} (commit `{modified['sha']}`)"
                )
                lines.append(
                    f"- **Total Modifications:** {evolution['total_modifications']} commit(s)"
                )

                if evolution.get("modification_frequency"):
                    freq = evolution["modification_frequency"]
                    lines.append(f"- **Modification Frequency:** {freq:.2f} commits/month")

                lines.append("")  # Empty line

            lines.append(f"Found {len(commits)} commit(s)\n")

            for i, commit in enumerate(commits, 1):
                lines.append(f"## {i}. {commit['summary']}")
                lines.append(f"- **Commit:** `{commit['sha']}`")
                lines.append(f"- **Author:** {commit['author']} ({commit['author_email']})")
                lines.append(f"- **Date:** {commit['date']}")

                # Add relevance indicator for function searches
                if "relevance" in commit:
                    relevance_emoji = "🎯" if commit["relevance"] == "mentioned" else "📝"
                    relevance_text = (
                        "Function mentioned"
                        if commit["relevance"] == "mentioned"
                        else "File changed"
                    )
                    lines.append(f"- **Relevance:** {relevance_emoji} {relevance_text}")

                # Add full commit message if it's different from summary
                if commit["message"] != commit["summary"]:
                    lines.append(f"\n**Full message:**\n```\n{commit['message']}\n```")

                lines.append("")  # Empty line between commits

            result = "\n".join(lines)
            return [TextContent(type="text", text=result)]

        except Exception as e:
            error_msg = f"Error getting file history: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def _get_function_history(
        self, file_path: str, start_line: int, end_line: int
    ) -> list[TextContent]:
        """
        Get line-by-line authorship for a code section using git blame.

        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number

        Returns:
            TextContent with formatted blame information
        """
        if not self.git_helper:
            error_msg = "Git blame is not available (repository may not be a git repo)"
            return [TextContent(type="text", text=error_msg)]

        try:
            blame_groups = self.git_helper.get_function_history(file_path, start_line, end_line)

            if not blame_groups:
                result = f"No blame information found for {file_path} lines {start_line}-{end_line}"
                return [TextContent(type="text", text=result)]

            # Format the results as markdown
            lines = [f"# Git Blame for {file_path} (lines {start_line}-{end_line})\n"]
            lines.append(f"Found {len(blame_groups)} authorship group(s)\n")

            for i, group in enumerate(blame_groups, 1):
                # Group header
                line_range = (
                    f"lines {group['line_start']}-{group['line_end']}"
                    if group["line_start"] != group["line_end"]
                    else f"line {group['line_start']}"
                )
                lines.append(f"## Group {i}: {group['author']} ({line_range})")

                lines.append(f"- **Author:** {group['author']} ({group['author_email']})")
                lines.append(f"- **Commit:** `{group['sha']}`")
                lines.append(f"- **Date:** {group['date'][:10]}")
                lines.append(f"- **Lines:** {group['line_count']}\n")

                # Show code lines
                lines.append("**Code:**")
                lines.append("```elixir")
                for line_info in group["lines"]:
                    # Show line number and content
                    lines.append(f"{line_info['content']}")
                lines.append("```\n")

            result = "\n".join(lines)
            return [TextContent(type="text", text=result)]

        except Exception as e:
            error_msg = f"Error getting blame information: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    async def _get_file_pr_history(self, file_path: str) -> list[TextContent]:
        """
        Get all PRs that modified a specific file with descriptions and comments.

        Args:
            file_path: Path to the file (relative to repo root or absolute)

        Returns:
            TextContent with formatted PR history
        """
        if not self.pr_index:
            error_msg = (
                "PR index not available. Please run:\n"
                "  cicada index-pr\n\n"
                "This will create the PR index at .cicada/pr_index.json"
            )
            return [TextContent(type="text", text=error_msg)]

        # Normalize file path
        repo_path = Path(self.config.get("repository", {}).get("path", "."))
        file_path_obj = Path(file_path)

        if file_path_obj.is_absolute():
            try:
                file_path_obj = file_path_obj.relative_to(repo_path)
            except ValueError:
                error_msg = f"File path {file_path} is not within repository {repo_path}"
                return [TextContent(type="text", text=error_msg)]

        file_path_str = str(file_path_obj)

        # Look up PRs that touched this file
        file_to_prs = self.pr_index.get("file_to_prs", {})
        pr_numbers = file_to_prs.get(file_path_str, [])

        if not pr_numbers:
            result = f"No pull requests found that modified: {file_path_str}"
            return [TextContent(type="text", text=result)]

        # Get PR details
        prs_data = self.pr_index.get("prs", {})

        # Format results as markdown
        lines = [f"# Pull Request History for {file_path_str}\n"]
        lines.append(f"Found {len(pr_numbers)} pull request(s)\n")

        for pr_num in pr_numbers:
            pr = prs_data.get(str(pr_num))
            if not pr:
                continue

            # PR Header
            status = "merged" if pr.get("merged") else pr.get("state", "unknown")
            lines.append(f"## PR #{pr['number']}: {pr['title']}")
            lines.append(f"- **Author:** @{pr['author']}")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **URL:** {pr['url']}\n")

            # PR Description (trimmed to first 10 lines)
            description = pr.get("description", "").strip()
            if description:
                lines.append("### Description")
                desc_lines = description.split("\n")
                if len(desc_lines) > 10:
                    trimmed_desc = "\n".join(desc_lines[:10])
                    lines.append(f"{trimmed_desc}")
                    lines.append(f"\n*... (trimmed, {len(desc_lines) - 10} more lines)*\n")
                else:
                    lines.append(f"{description}\n")

            # Review Comments for this file only
            comments = pr.get("comments", [])
            file_comments = [c for c in comments if c.get("path") == file_path_str]

            if file_comments:
                lines.append(f"### Review Comments ({len(file_comments)})")

                for comment in file_comments:
                    author = comment.get("author", "unknown")
                    body = comment.get("body", "").strip()
                    line_num = comment.get("line")
                    original_line = comment.get("original_line")
                    resolved = comment.get("resolved", False)

                    # Comment header with line info
                    if line_num:
                        line_info = f"Line {line_num}"
                    elif original_line:
                        line_info = f"Original line {original_line} (unmapped)"
                    else:
                        line_info = "No line info"

                    resolved_marker = " ✓ Resolved" if resolved else ""
                    lines.append(f"\n**@{author}** ({line_info}){resolved_marker}:")

                    # Indent comment body
                    for line in body.split("\n"):
                        lines.append(f"> {line}")

                lines.append("")  # Empty line after comments

            lines.append("---\n")  # Separator between PRs

        result = "\n".join(lines)
        return [TextContent(type="text", text=result)]

    async def _search_by_keywords(
        self, keywords: list[str], filter_type: str = "all", min_score: float = 0.0
    ) -> list[TextContent]:
        """
        Search for modules and functions by keywords.

        Args:
            keywords: List of keywords to search for
            filter_type: Filter results by type ('all', 'modules', 'functions'). Defaults to 'all'.
            min_score: Minimum relevance score threshold (0.0 to 1.0). Defaults to 0.0.

        Returns:
            TextContent with formatted search results
        """
        from cicada.keyword_search import KeywordSearcher
        from cicada.mcp.filter_utils import filter_by_score_threshold

        # Check if keywords are available (cached at initialization)
        if not self._has_keywords:
            error_msg = (
                "No keywords found in index. Please rebuild the index with keyword extraction:\n\n"
                "  cicada index           # Default: reuse configured tier\n"
                "  cicada index --force --regular   # BERT + GloVe (regular tier)\n"
                "  cicada index --force --fast      # Fast: Token-based + lemminflect\n"
                "  cicada index --force --max       # Max: BERT + FastText\n\n"
                "This will extract keywords from documentation for semantic search."
            )
            return [TextContent(type="text", text=error_msg)]

        # Perform the search
        searcher = KeywordSearcher(self.index)
        results = searcher.search(keywords, top_n=20, filter_type=filter_type)

        # Apply score threshold filter
        if min_score > 0.0:
            results = filter_by_score_threshold(results, min_score)

        if not results:
            if min_score > 0.0:
                result = f"No results found for keywords: {', '.join(keywords)} with min_score >= {min_score}"
            else:
                result = f"No results found for keywords: {', '.join(keywords)}"
            return [TextContent(type="text", text=result)]

        # Format results
        from cicada.format import ModuleFormatter

        formatted_result = ModuleFormatter.format_keyword_search_results_markdown(
            keywords, results, show_scores=True
        )

        return [TextContent(type="text", text=formatted_result)]

    async def _find_dead_code(self, min_confidence: str, output_format: str) -> list[TextContent]:
        """
        Find potentially unused public functions.

        Args:
            min_confidence: Minimum confidence level ('high', 'medium', or 'low')
            output_format: Output format ('markdown' or 'json')

        Returns:
            TextContent with formatted dead code analysis
        """
        from cicada.dead_code.analyzer import DeadCodeAnalyzer
        from cicada.dead_code.finder import (
            filter_by_confidence,
            format_json,
            format_markdown,
        )

        # Run analysis
        analyzer = DeadCodeAnalyzer(self.index)
        results = analyzer.analyze()

        # Filter by confidence
        results = filter_by_confidence(results, min_confidence)

        # Format output
        output = format_json(results) if output_format == "json" else format_markdown(results)

        return [TextContent(type="text", text=output)]

    async def _get_module_dependencies(
        self, module_name: str, output_format: str, depth: int, granular: bool = False
    ) -> list[TextContent]:
        """
        Get all modules that a given module depends on.

        Args:
            module_name: Module name to analyze
            output_format: Output format ('markdown' or 'json')
            depth: Depth for transitive dependencies (1 = direct only, 2 = include dependencies of dependencies)
            granular: Show which specific functions use which dependencies

        Returns:
            TextContent with formatted dependency information
        """
        import json

        # Look up the module in the index
        module_data, error_msg = self._lookup_module_with_error(module_name)
        if error_msg:
            return [TextContent(type="text", text=error_msg)]

        # module_data is guaranteed to be non-None here
        assert module_data is not None

        # Get dependencies from the index
        dependencies = module_data.get("dependencies", {})
        direct_modules = dependencies.get("modules", [])

        # Collect granular dependency information if requested
        granular_info: dict[str, list[dict[str, Any]]] = {}
        if granular:
            # Build a mapping of dependency_module -> [functions that use it]
            for func in module_data.get("functions", []):
                func_deps = func.get("dependencies", [])
                for dep in func_deps:
                    dep_module = dep.get("module", "")
                    if dep_module in direct_modules:
                        if dep_module not in granular_info:
                            granular_info[dep_module] = []
                        granular_info[dep_module].append(
                            {
                                "function": func.get("name"),
                                "arity": func.get("arity"),
                                "line": func.get("line"),
                                "calls": f"{dep.get('function')}/{dep.get('arity')}",
                                "call_line": dep.get("line"),
                            }
                        )

        # If depth > 1, collect transitive dependencies
        all_modules = set(direct_modules)
        if depth > 1:
            visited = {module_name}  # Avoid circular dependencies
            to_visit = list(direct_modules)

            for _ in range(depth - 1):
                next_level = []
                for dep_module in to_visit:
                    if dep_module in visited:
                        continue
                    visited.add(dep_module)

                    dep_data = self.index["modules"].get(dep_module)
                    if dep_data:
                        dep_dependencies = dep_data.get("dependencies", {})
                        dep_modules = dep_dependencies.get("modules", [])
                        all_modules.update(dep_modules)
                        next_level.extend(dep_modules)

                to_visit = next_level

        # Format output
        if output_format == "json":
            result = {
                "module": module_name,
                "dependencies": {
                    "direct": sorted(direct_modules),
                    "all": sorted(all_modules) if depth > 1 else sorted(direct_modules),
                    "depth": depth,
                },
            }
            if granular:
                result["granular"] = granular_info  # type: ignore
            output = json.dumps(result, indent=2)
        else:
            # Markdown format
            lines = [f"# Dependencies for {module_name}\n"]

            if direct_modules:
                lines.append(f"## Direct Dependencies ({len(direct_modules)})\n")
                for dep in sorted(direct_modules):
                    lines.append(f"- {dep}")
                    # Add granular information if available
                    if granular and dep in granular_info:
                        uses = granular_info[dep]
                        lines.append(f"  Used by {len(uses)} function(s):")
                        for use in uses[:3]:  # Limit to 3 examples
                            lines.append(
                                f"    • {use['function']}/{use['arity']} (line {use['line']}) → calls {use['calls']} (line {use['call_line']})"
                            )
                        if len(uses) > 3:
                            lines.append(f"    ... and {len(uses) - 3} more")
                lines.append("")

            if depth > 1 and len(all_modules) > len(direct_modules):
                transitive = sorted(all_modules - set(direct_modules))
                lines.append(f"## Transitive Dependencies ({len(transitive)})\n")
                for dep in transitive:
                    lines.append(f"- {dep}")
                lines.append("")

            if not direct_modules:
                lines.append("*No dependencies found*")

            output = "\n".join(lines)

        return [TextContent(type="text", text=output)]

    def _format_dependency_with_context(
        self,
        dep: dict,
        context_lines: dict,
        include_context: bool,
        include_module: bool = False,
    ) -> list[str]:
        """
        Format a single dependency with optional code context.

        Args:
            dep: Dependency dict with module, function, arity, line
            context_lines: Dict mapping line numbers to code context
            include_context: Whether to include code context
            include_module: Whether to include module name in output

        Returns:
            List of formatted lines
        """
        lines = []
        line_info = f"(line {dep['line']})"

        if include_module:
            lines.append(f"- {dep['module']}.{dep['function']}/{dep['arity']} {line_info}")
        else:
            lines.append(f"- {dep['function']}/{dep['arity']} {line_info}")

        if include_context and dep["line"] in context_lines:
            lines.append("  ```elixir")
            lines.append(f"  {context_lines[dep['line']]}")
            lines.append("  ```")

        return lines

    async def _get_function_dependencies(
        self,
        module_name: str,
        function_name: str,
        arity: int,
        output_format: str,
        include_context: bool,
    ) -> list[TextContent]:
        """
        Get all functions that a given function calls.

        Args:
            module_name: Module name containing the function
            function_name: Function name to analyze
            arity: Function arity
            output_format: Output format ('markdown' or 'json')
            include_context: Whether to include code context

        Returns:
            TextContent with formatted dependency information
        """
        import json

        # Look up the module in the index (no suggestions for function lookup)
        module_data, error_msg = self._lookup_module_with_error(
            module_name, include_suggestions=False
        )
        if error_msg:
            return [TextContent(type="text", text=error_msg)]

        # module_data is guaranteed to be non-None here
        assert module_data is not None

        # Find the function
        functions = module_data.get("functions", [])
        target_func = None
        for func in functions:
            if func["name"] == function_name and func["arity"] == arity:
                target_func = func
                break

        if not target_func:
            error_msg = (
                f"Function not found: {module_name}.{function_name}/{arity}\n\n"
                f"Available functions in {module_name}:\n"
            )
            available = [f"  - {f['name']}/{f['arity']}" for f in functions[:10]]
            error_msg += "\n".join(available)
            return [TextContent(type="text", text=error_msg)]

        # Get function dependencies
        dependencies = target_func.get("dependencies", [])

        # If include_context is True, fetch the source code
        context_lines = {}
        if include_context and dependencies:
            # Read the source file
            repo_path = self.config.get("repository", {}).get("path", ".")
            file_path = Path(repo_path) / module_data["file"]
            try:
                with open(file_path) as f:
                    source_lines = f.readlines()
                    # Get context for each dependency call
                    for dep in dependencies:
                        line_num = dep["line"]
                        if 1 <= line_num <= len(source_lines):
                            # Get 3 lines of context (before, current, after)
                            start = max(0, line_num - 2)
                            end = min(len(source_lines), line_num + 1)
                            context = "".join(source_lines[start:end])
                            context_lines[line_num] = context.rstrip()
            except OSError:
                pass  # If we can't read the file, just skip context

        # Format output
        if output_format == "json":
            result = {
                "module": module_name,
                "function": f"{function_name}/{arity}",
                "dependencies": dependencies,
            }
            output = json.dumps(result, indent=2)
        else:
            # Markdown format
            lines = [f"# Dependencies for {module_name}.{function_name}/{arity}\n"]

            if dependencies:
                # Group by internal vs external
                internal = [d for d in dependencies if d["module"] == module_name]
                external = [d for d in dependencies if d["module"] != module_name]

                if internal:
                    lines.append(f"## Internal Calls ({len(internal)})\n")
                    for dep in internal:
                        lines.extend(
                            self._format_dependency_with_context(
                                dep, context_lines, include_context, include_module=False
                            )
                        )
                    lines.append("")

                if external:
                    lines.append(f"## External Calls ({len(external)})\n")
                    for dep in external:
                        lines.extend(
                            self._format_dependency_with_context(
                                dep, context_lines, include_context, include_module=True
                            )
                        )
                    lines.append("")
            else:
                lines.append("*No dependencies found*")

            output = "\n".join(lines)

        return [TextContent(type="text", text=output)]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


async def async_main():
    """Async main entry point."""
    try:
        # Check if setup is needed before starting server
        # Redirect stdout to stderr during setup to avoid polluting MCP protocol
        original_stdout = sys.stdout
        try:
            sys.stdout = sys.stderr
            _auto_setup_if_needed()
        finally:
            sys.stdout = original_stdout

        server = CicadaServer()
        await server.run()
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def _auto_setup_if_needed():
    """
    Automatically run setup if the repository hasn't been indexed yet.

    This enables zero-config MCP usage - just point the MCP config to cicada-server
    and it will index the repository on first run.
    """
    from cicada.setup import create_config_yaml, index_repository
    from cicada.utils import (
        create_storage_dir,
        get_config_path,
        get_index_path,
    )

    # Determine repository path from environment or current directory
    repo_path_str = None

    # First check if repo path was provided via positional argument (internal env var)
    repo_path_str = os.environ.get("_CICADA_REPO_PATH_ARG")

    # Fall back to WORKSPACE_FOLDER_PATHS (Cursor-specific)
    if not repo_path_str:
        workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
        if workspace_paths:
            # WORKSPACE_FOLDER_PATHS might be a single path or multiple paths
            # Take the first one if multiple
            # Use os.pathsep for platform-aware splitting (';' on Windows, ':' on Unix)
            repo_path_str = (
                workspace_paths.split(os.pathsep)[0]
                if os.pathsep in workspace_paths
                else workspace_paths
            )

    repo_path = Path(repo_path_str).resolve() if repo_path_str else Path.cwd().resolve()

    # Check if config and index already exist
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if config_path.exists() and index_path.exists():
        # Already set up, nothing to do
        return

    # Setup needed - create storage and index (silent mode)
    # Validate it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(
            f"Error: {repo_path} does not appear to be an Elixir project (mix.exs not found)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Create storage directory
        storage_dir = create_storage_dir(repo_path)

        # Index repository (silent mode)
        index_repository(repo_path, verbose=False)

        # Create config.yaml (silent mode)
        create_config_yaml(repo_path, storage_dir, verbose=False)

    except Exception as e:
        print(f"Cicada auto-setup error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Synchronous entry point for use with setuptools console_scripts."""
    import asyncio
    import sys

    # Accept optional positional argument for repo path
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        # Convert to absolute path
        from pathlib import Path

        from cicada.utils.storage import get_storage_dir

        abs_path = Path(repo_path).resolve()
        # Set environment variables for both storage directory and repo path
        # The repo path is needed by _auto_setup_if_needed() for first-time setup
        storage_dir = get_storage_dir(abs_path)
        os.environ["CICADA_CONFIG_DIR"] = str(storage_dir)
        os.environ["_CICADA_REPO_PATH_ARG"] = str(abs_path)

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
