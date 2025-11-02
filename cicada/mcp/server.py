#!/usr/bin/env python
"""
Cicada MCP Server - Elixir Module Search.

Provides an MCP tool to search for Elixir modules and their functions.

Author: Cursor(Auto)
"""

import contextlib
import os
import sys
import time
from pathlib import Path
from typing import Any, cast

import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cicada.command_logger import get_logger
from cicada.format import ModuleFormatter
from cicada.git_helper import GitHelper
from cicada.mcp.tools import get_tool_definitions
from cicada.pr_finder import PRFinder
from cicada.utils import get_config_path, get_pr_index_path, load_index


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
        # Check if CICADA_CONFIG_DIR is set (new temp directory approach)
        config_dir = os.environ.get("CICADA_CONFIG_DIR")
        if config_dir:
            return str(Path(config_dir) / "config.yaml")

        # Determine repository path from environment or current directory
        repo_path = os.environ.get("CICADA_REPO_PATH")

        # Check if WORKSPACE_FOLDER_PATHS is available (Cursor-specific)
        if not repo_path:
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

        # Use new storage structure only
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

            if not function_name:
                error_msg = "'function_name' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_function(
                function_name,
                output_format,
                include_usage_examples,
                max_examples,
                test_files_only,
            )
        elif name == "search_module_usage":
            module_name = arguments.get("module_name")
            output_format = arguments.get("format", "markdown")

            if not module_name:
                error_msg = "'module_name' is required"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_module_usage(module_name, output_format)
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
        elif name == "search_by_keywords":
            keywords = arguments.get("keywords")
            filter_type = arguments.get("filter_type", "all")

            if not keywords:
                error_msg = "'keywords' is required"
                return [TextContent(type="text", text=error_msg)]

            if not isinstance(keywords, list):
                error_msg = "'keywords' must be a list of strings"
                return [TextContent(type="text", text=error_msg)]

            if filter_type not in ("all", "modules", "functions"):
                error_msg = "'filter_type' must be one of: 'all', 'modules', 'functions'"
                return [TextContent(type="text", text=error_msg)]

            return await self._search_by_keywords(keywords, filter_type)
        elif name == "find_dead_code":
            min_confidence = arguments.get("min_confidence", "high")
            output_format = arguments.get("format", "markdown")

            return await self._find_dead_code(min_confidence, output_format)
        else:
            raise ValueError(f"Unknown tool: {name}")

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
        """Search for a module and return its information."""
        # Exact match lookup
        if module_name in self.index["modules"]:
            data = self.index["modules"][module_name]

            if output_format == "json":
                result = ModuleFormatter.format_module_json(module_name, data, private_functions)
            else:
                result = ModuleFormatter.format_module_markdown(
                    module_name, data, private_functions
                )

            return [TextContent(type="text", text=result)]

        # Module not found
        total_modules = self.index["metadata"]["total_modules"]

        if output_format == "json":
            error_result = ModuleFormatter.format_error_json(module_name, total_modules)
        else:
            error_result = ModuleFormatter.format_error_markdown(module_name, total_modules)

        return [TextContent(type="text", text=error_result)]

    async def _search_function(
        self,
        function_name: str,
        output_format: str = "markdown",
        include_usage_examples: bool = False,
        max_examples: int = 5,
        test_files_only: bool = False,
    ) -> list[TextContent]:
        """Search for a function across all modules and return matches with call sites."""
        # Parse the function name - supports multiple formats:
        # - "func_name" or "func_name/arity" (search all modules)
        # - "Module.func_name" or "Module.func_name/arity" (search specific module)
        target_module = None
        target_name = function_name
        target_arity = None

        # Check for Module.function format
        if "." in function_name:
            # Split on last dot to separate module from function
            parts = function_name.rsplit(".", 1)
            if len(parts) == 2:
                target_module = parts[0]
                target_name = parts[1]

        # Check for arity
        if "/" in target_name:
            parts = target_name.split("/")
            target_name = parts[0]
            with contextlib.suppress(ValueError, IndexError):
                target_arity = int(parts[1])

        # Search across all modules for function definitions
        results = []
        for module_name, module_data in self.index["modules"].items():
            # If target_module is specified, only search in that module
            if target_module and module_name != target_module:
                continue

            for func in module_data["functions"]:
                # Match by name and optionally arity
                if func["name"] == target_name and (
                    target_arity is None or func["arity"] == target_arity
                ):
                    # Find call sites for this function
                    call_sites = self._find_call_sites(
                        target_module=module_name,
                        target_function=target_name,
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

                    results.append(
                        {
                            "module": module_name,
                            "moduledoc": module_data.get("moduledoc"),
                            "function": func,
                            "file": module_data["file"],
                            "call_sites": call_sites,
                            "call_sites_with_examples": call_sites_with_examples,
                        }
                    )

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_function_results_json(function_name, results)
        else:
            result = ModuleFormatter.format_function_results_markdown(function_name, results)

        return [TextContent(type="text", text=result)]

    async def _search_module_usage(
        self, module_name: str, output_format: str = "markdown"
    ) -> list[TextContent]:
        """
        Search for all locations where a module is used (aliased/imported and called).

        Args:
            module_name: The module to search for (e.g., "MyApp.User")
            output_format: Output format ('markdown' or 'json')

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

        Returns:
            TextContent with formatted commit history

        Note:
            - If function_name is provided, uses git's function tracking
            - Function tracking works even as the function moves in the file
            - Line numbers are used as fallback if function tracking fails
            - Requires .gitattributes with "*.ex diff=elixir" for function tracking
        """
        if not self.git_helper:
            error_msg = "Git history is not available (repository may not be a git repo)"
            return [TextContent(type="text", text=error_msg)]

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
                commits = self.git_helper.get_file_history(file_path, max_commits)
                title = f"Git History for {file_path}"

            if not commits:
                result = f"No commit history found for {file_path}"
                return [TextContent(type="text", text=result)]

            # Format the results as markdown
            lines = [f"# {title}\n"]

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
        self, keywords: list[str], filter_type: str = "all"
    ) -> list[TextContent]:
        """
        Search for modules and functions by keywords.

        Args:
            keywords: List of keywords to search for
            filter_type: Filter results by type ('all', 'modules', 'functions'). Defaults to 'all'.

        Returns:
            TextContent with formatted search results
        """
        from cicada.keyword_search import KeywordSearcher

        # Check if keywords are available (cached at initialization)
        if not self._has_keywords:
            error_msg = (
                "No keywords found in index. Please rebuild the index with keyword extraction:\n\n"
                "  cicada index           # Default: BERT + GloVe (regular tier)\n"
                "  cicada index --fast    # Fast: Token-based + lemminflect\n"
                "  cicada index --max     # Max: BERT + FastText\n\n"
                "This will extract keywords from documentation for semantic search."
            )
            return [TextContent(type="text", text=error_msg)]

        # Perform the search
        searcher = KeywordSearcher(self.index)
        results = searcher.search(keywords, top_n=5, filter_type=filter_type)

        if not results:
            result = f"No results found for keywords: {', '.join(keywords)}"
            return [TextContent(type="text", text=result)]

        # Format results
        from cicada.format import ModuleFormatter

        formatted_result = ModuleFormatter.format_keyword_search_results_markdown(keywords, results)

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
    repo_path_str = os.environ.get("CICADA_REPO_PATH")

    # Check if WORKSPACE_FOLDER_PATHS is available (Cursor-specific)
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

        abs_path = Path(repo_path).resolve()
        # Set environment variable to override default
        os.environ["CICADA_REPO_PATH"] = str(abs_path)

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
