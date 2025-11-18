"""
Module Search Tool Handlers.

Handles tools for searching modules and analyzing module usage.
"""

from typing import Any, cast

from mcp.types import TextContent

from cicada.elixir.format import ModuleFormatter
from cicada.mcp.pattern_utils import has_wildcards, match_any_pattern, split_or_patterns
from cicada.utils import find_similar_names


class ModuleSearchHandler:
    """Handler for module search and usage analysis."""

    # Constants
    MAX_WILDCARD_RESULTS = 20  # Maximum modules to show in wildcard search
    COMPACT_FORMAT_THRESHOLD = 4  # Number of modules to trigger compact format
    APPROXIMATE_FUNCTION_LENGTH = 100  # Estimated lines for functions without known end

    def __init__(
        self,
        index: dict[str, Any],
        config: dict[str, Any],
        dependency_handler: Any | None = None,
    ):
        """
        Initialize the module search handler.

        Args:
            index: The code index containing modules and functions
            config: Configuration dictionary
            dependency_handler: Optional DependencyHandler for detailed dependency info
        """
        self.index = index
        self.config = config
        self.dependency_handler = dependency_handler

    def _collect_transitive_dependencies(
        self,
        module_name: str,
        direct_dependencies: list[str],
        max_depth: int,
    ) -> dict[str, list[str]]:
        """
        Collect transitive dependencies up to a specified depth.

        Args:
            module_name: The root module name (to avoid including it in results)
            direct_dependencies: List of direct dependency module names
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary mapping transitive dependency names to lists of modules that depend on them
        """
        visited = {module_name}  # Avoid cycles
        transitive_deps: dict[str, set[str]] = {}

        def collect_recursive(mod: str, current_depth: int) -> None:
            should_stop = current_depth >= max_depth or mod in visited
            if should_stop:
                return

            visited.add(mod)

            mod_data = self.index["modules"].get(mod)
            if not mod_data:
                return

            deps = mod_data.get("dependencies", {}).get("modules", [])
            for dep in deps:
                is_direct = dep in direct_dependencies
                is_self = dep == module_name

                if is_direct or is_self:
                    continue

                if dep not in transitive_deps:
                    transitive_deps[dep] = set()
                transitive_deps[dep].add(mod)
                collect_recursive(dep, current_depth + 1)

        for dep in direct_dependencies:
            collect_recursive(dep, 1)

        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in transitive_deps.items()}

    def _build_granular_dependency_info(
        self,
        module_data: dict[str, Any],
        direct_dependencies: list[str],
    ) -> dict[str, list[str]]:
        """
        Build granular information showing which functions use which dependencies.

        Args:
            module_data: Module dictionary from index
            direct_dependencies: List of direct dependency module names

        Returns:
            Dictionary mapping dependency module names to lists of function signatures
        """
        granular_info: dict[str, list[str]] = {}

        for func in module_data.get("functions", []):
            func_sig = f"{func['name']}/{func['arity']}"
            func_deps = func.get("dependencies", [])

            for dep in func_deps:
                dep_module = dep["module"]

                is_direct_dependency = dep_module in direct_dependencies
                if not is_direct_dependency:
                    continue

                # Initialize list for this dependency module if needed
                if dep_module not in granular_info:
                    granular_info[dep_module] = []

                # Add function signature if not already present
                if func_sig not in granular_info[dep_module]:
                    granular_info[dep_module].append(func_sig)

        return granular_info

    async def _get_module_dependencies(
        self,
        module_name: str,
        module_data: dict[str, Any],
        depth: int,
        granular: bool,
    ) -> dict[str, Any] | None:
        """
        Get detailed dependency information for a module.

        Args:
            module_name: Module name
            module_data: Module dictionary from index
            depth: Dependency depth (1 = direct only, 2+ = transitive)
            granular: Whether to show which functions use which dependencies

        Returns:
            Dictionary with dependency information
        """
        dependencies_data = module_data.get("dependencies", {})
        dependent_modules = dependencies_data.get("modules", [])

        if not dependent_modules:
            return None

        result = {
            "direct": dependent_modules.copy(),
            "transitive": {},
            "granular": {},
        }

        # Build transitive dependencies if depth > 1
        if depth > 1:
            result["transitive"] = self._collect_transitive_dependencies(
                module_name, dependent_modules, depth
            )

        # Build granular info if requested
        if granular:
            result["granular"] = self._build_granular_dependency_info(
                module_data, dependent_modules
            )

        return result

    def _calculate_function_end_line(
        self, functions: list[Any], current_index: int, func_line: int
    ) -> int:
        """
        Calculate the end line for a function.

        Args:
            functions: List of all functions in the module
            current_index: Index of current function
            func_line: Start line of current function

        Returns:
            Estimated end line of the function
        """
        has_next_function = current_index + 1 < len(functions)
        if has_next_function:
            return functions[current_index + 1]["line"] - 1

        return func_line + self.APPROXIMATE_FUNCTION_LENGTH

    def _find_function_at_line(self, module_name: str, line: int) -> dict | None:
        """
        Find the function that contains a specific line number.

        Args:
            module_name: The module to search in
            line: The line number

        Returns:
            Dictionary with 'name', 'arity', 'start_line', 'end_line', or None if not found
        """
        if module_name not in self.index["modules"]:
            return None

        module_data = cast(dict[str, Any], self.index["modules"][module_name])
        functions: list[Any] = module_data.get("functions", [])

        # Find the function whose definition line is closest before the target line
        best_match: dict[str, Any] | None = None
        for i, func in enumerate(functions):
            func_line = func["line"]
            is_before_or_at_target = func_line <= line
            is_closer_match = best_match is None or func_line > best_match["line"]

            if is_before_or_at_target and is_closer_match:
                end_line = self._calculate_function_end_line(functions, i, func_line)
                best_match = {
                    "name": func["name"],
                    "arity": func["arity"],
                    "line": func_line,
                    "start_line": func_line,
                    "end_line": end_line,
                }

        return best_match

    def lookup_module_with_error(
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

    def resolve_file_to_module(self, file_path: str) -> str | None:
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

    async def search_module(
        self,
        module_name: str,
        output_format: str = "markdown",
        visibility: str = "public",
        pr_info: dict | None = None,
        staleness_info: dict | None = None,
        what_it_calls: bool = False,
        dependency_depth: int = 1,
        show_function_usage: bool = False,
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

            # Apply limit to prevent overwhelming results
            total_matches = len(matching_modules)
            truncated = total_matches > self.MAX_WILDCARD_RESULTS
            if truncated:
                matching_modules = matching_modules[: self.MAX_WILDCARD_RESULTS]

            # Format all matching modules
            # Use compact format when showing multiple modules
            use_compact = (
                total_matches >= self.COMPACT_FORMAT_THRESHOLD and output_format == "markdown"
            )

            results: list[str] = []
            for mod_name, mod_data in matching_modules:
                if output_format == "json":
                    result = ModuleFormatter.format_module_json(mod_name, mod_data, visibility)
                elif use_compact:
                    result = ModuleFormatter.format_module_compact(mod_name, mod_data)
                else:
                    result = ModuleFormatter.format_module_markdown(mod_name, mod_data, visibility)
                results.append(result)

            # Combine results with separator for markdown, or as array for JSON
            if output_format == "json":
                # For JSON, wrap in array notation
                combined = "[\n" + ",\n".join(results) + "\n]"
            else:
                # For markdown, separate with horizontal rules (or blank lines for compact)
                header = f"Found {total_matches} module(s) matching pattern '{module_name}'"
                if truncated:
                    header += f" (showing first {self.MAX_WILDCARD_RESULTS}, use more specific pattern to see others)"
                header += ":\n\n"

                if use_compact:
                    # Compact format: separate with horizontal rules (no extra newlines)
                    combined = header + "\n---\n".join(results)
                    # Add info message about compacted results
                    combined += "\n---\nResults compacted. Use a more specific module name to see full information."
                else:
                    # Full format: separate with horizontal rules
                    combined = header + "\n\n---\n\n".join(results)

            return [TextContent(type="text", text=combined)]

        # Exact match lookup (no wildcards)
        if module_name in self.index["modules"]:
            data = self.index["modules"][module_name]

            # Get detailed dependency info if requested
            detailed_dependencies = None
            if what_it_calls and self.dependency_handler:
                detailed_dependencies = await self._get_module_dependencies(
                    module_name, data, dependency_depth, show_function_usage
                )

            if output_format == "json":
                result = ModuleFormatter.format_module_json(
                    module_name, data, visibility, detailed_dependencies
                )
            else:
                result = ModuleFormatter.format_module_markdown(
                    module_name,
                    data,
                    visibility,
                    pr_info,
                    staleness_info,
                    detailed_dependencies,
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

    async def search_module_usage(
        self, module_name: str, output_format: str = "markdown", usage_type: str = "source"
    ) -> list[TextContent]:
        """
        Search for all locations where a module is used (aliased/imported and called).

        Args:
            module_name: The module to search for (e.g., "MyApp.User")
            output_format: Output format ('markdown' or 'json')
            usage_type: Filter by file type ('source', 'tests', 'all')

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
            def record_simple_usage(
                category: str,
                _module_data: dict = module_data,
                _caller_module: str = caller_module,
            ) -> None:
                if module_name in _module_data.get(category, []):
                    usage_results[category].append(
                        {
                            "importing_module": _caller_module,
                            "file": _module_data["file"],
                        }
                    )

            for category in ("imports", "requires", "uses", "value_mentions"):
                record_simple_usage(category)

            # Check function calls
            calls = module_data.get("calls", [])
            module_calls = {}  # Track calls grouped by (called_function, calling_function)

            for call in calls:
                call_module = call.get("module")

                # Resolve the call's module name using aliases
                if call_module:
                    resolved_module = aliases.get(call_module, call_module)

                    if resolved_module == module_name:
                        # Find which function in the calling module contains this call
                        calling_function = self._find_function_at_line(caller_module, call["line"])

                        # Create keys for both the called function and calling function
                        called_func_key = f"{call['function']}/{call['arity']}"
                        if calling_function:
                            calling_func_key = (
                                f"{calling_function['name']}/{calling_function['arity']}"
                            )
                            compound_key = f"{called_func_key}|{calling_func_key}"
                        else:
                            # Module-level call (not inside any function)
                            calling_func_key = None
                            compound_key = f"{called_func_key}|module_level"

                        if compound_key not in module_calls:
                            module_calls[compound_key] = {
                                "called_function": call["function"],
                                "called_arity": call["arity"],
                                "calling_function": calling_function,  # Full info including line range
                                "lines": [],
                                "alias_used": (
                                    call_module if call_module != resolved_module else None
                                ),
                            }

                        module_calls[compound_key]["lines"].append(call["line"])

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
