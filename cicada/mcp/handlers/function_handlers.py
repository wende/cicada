"""
Function Search Tool Handlers.

Handles tools for searching functions and analyzing their call sites.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from mcp.types import TextContent

from cicada.mcp.filter_utils import filter_by_file_type
from cicada.mcp.pattern_utils import FunctionPattern, parse_function_patterns


class FunctionSearchHandler:
    """Handler for function search and call site analysis."""

    # Constants for dependency context
    DEPENDENCY_CONTEXT_LINES_BEFORE = 2
    DEPENDENCY_CONTEXT_LINES_AFTER = 1

    # Constants for call site context extraction
    CALL_CONTEXT_LINES = 2  # Lines before and after the call line

    def __init__(
        self,
        index: dict[str, Any],
        config: dict[str, Any],
    ):
        """
        Initialize the function search handler.

        Args:
            index: The code index containing modules and functions
            config: Configuration dictionary
        """
        self.index = index
        self.config = config

    def _extract_dependency_contexts(
        self, dependencies: list[dict[str, Any]], file_path: str
    ) -> dict[int, str]:
        """
        Extract code context for dependency call sites.

        Args:
            dependencies: List of dependency dictionaries with 'line' keys
            file_path: Path to the source file (relative to repo root)

        Returns:
            Dictionary mapping line numbers to context strings
        """
        context_lines = {}
        repo_path = self.config.get("repository", {}).get("path", ".")
        full_path = Path(repo_path) / file_path

        try:
            with open(full_path) as f:
                source_lines = f.readlines()

            for dep in dependencies:
                line_num = dep["line"]
                is_valid_line = 1 <= line_num <= len(source_lines)

                if not is_valid_line:
                    continue

                start_line = max(0, line_num - self.DEPENDENCY_CONTEXT_LINES_BEFORE)
                end_line = min(len(source_lines), line_num + self.DEPENDENCY_CONTEXT_LINES_AFTER)
                context = "".join(source_lines[start_line:end_line])
                context_lines[line_num] = context.rstrip()

        except OSError:
            # If we can't read the file, return empty dict
            pass

        return context_lines

    def _enrich_dependency_with_context(
        self, dep: dict[str, Any], context_lines: dict[int, str]
    ) -> dict[str, Any]:
        """
        Add context to a dependency if available.

        Args:
            dep: Dependency dictionary
            context_lines: Dictionary mapping line numbers to context strings

        Returns:
            Dependency dictionary with optional 'context' key added
        """
        enriched_dep = dep.copy()
        if dep["line"] in context_lines:
            enriched_dep["context"] = context_lines[dep["line"]]
        return enriched_dep

    def _get_detailed_dependencies(
        self,
        module_name: str,
        func: dict[str, Any],
        file_path: str,
        include_context: bool,
    ) -> dict[str, Any] | None:
        """
        Get detailed dependency information for a function.

        Args:
            module_name: Module containing the function
            func: Function dictionary from index
            file_path: Path to the source file
            include_context: Whether to include code context for each dependency

        Returns:
            Dictionary with dependency information and optional context
        """
        dependencies = func.get("dependencies", [])
        if not dependencies:
            return None

        # Extract context if requested
        context_lines = (
            self._extract_dependency_contexts(dependencies, file_path) if include_context else {}
        )

        # Group dependencies into internal (same module) and external (other modules)
        internal_deps = []
        external_deps = []

        for dep in dependencies:
            enriched_dep = (
                self._enrich_dependency_with_context(dep, context_lines)
                if include_context
                else dep.copy()
            )

            if dep["module"] == module_name:
                internal_deps.append(enriched_dep)
            else:
                external_deps.append(enriched_dep)

        return {
            "internal": internal_deps,
            "external": external_deps,
            "total_count": len(dependencies),
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

        # Get the target module's file path for cross-referencing
        target_file = None
        if target_module in self.index["modules"]:
            target_file = self.index["modules"][target_module].get("file")

        for caller_module, module_data in self.index["modules"].items():
            # Get aliases for this module to resolve calls
            aliases = module_data.get("aliases", {})

            # Collect all dependencies (module-level and function-level)
            all_dependencies = []

            # Add module-level dependencies (for Elixir compatibility)
            for dep in module_data.get("dependencies", []):
                if isinstance(dep, dict):  # Skip string-only dependencies
                    all_dependencies.append(dep)

            # Add function-level dependencies (for Python/SCIP)
            for func in module_data.get("functions", []):
                for dep in func.get("dependencies", []):
                    if isinstance(dep, dict):  # Skip string-only dependencies
                        all_dependencies.append(dep)

            # BACKWARD COMPATIBILITY: Also check old 'calls' format (Elixir module-level)
            # This is for older indexes or test fixtures that haven't been updated
            for call in module_data.get("calls", []):
                if isinstance(call, dict) and call.get("function"):
                    all_dependencies.append(call)

            # Check all dependencies in this module
            for call in all_dependencies:
                if call.get("function") != target_function:
                    continue

                if call.get("arity") != target_arity:
                    continue

                # Resolve the call's module name using aliases
                call_module = call.get("module")

                is_match = False
                call_type = "unknown"
                alias_used = None

                if call_module is None:
                    # Local call - check if it's in the same module
                    if caller_module == target_module:
                        is_match = True
                        call_type = "local"
                else:
                    # Qualified call - resolve the module name
                    resolved_module = aliases.get(call_module, call_module)

                    # Check if this resolves to our target module (name match)
                    if resolved_module == target_module:
                        is_match = True
                        call_type = "qualified"
                        alias_used = call_module if call_module != resolved_module else None
                    # For Python/SCIP: also check if the call's module corresponds to the target file
                    # This handles cases where dependencies store Python module paths with backticks
                    # (e.g., `cicada.parsing.base_indexer`) but the target is a class (e.g., `BaseIndexer`)
                    elif target_file and call_module:
                        # Look up the dependency's module in the index
                        dep_module_data = self.index["modules"].get(call_module.strip("`"))
                        if dep_module_data and dep_module_data.get("file") == target_file:
                            # The dependency references a module in the same file as our target
                            is_match = True
                            call_type = "qualified"

                if not is_match:
                    continue

                # Filter out calls that are part of the function definition
                # (@spec, @doc appear 1-5 lines before the def)
                # Only filter for local calls (same module)
                call_line = call.get("line", 0)
                if (
                    call_type == "local"
                    and function_def_line
                    and abs(call_line - function_def_line) <= 5
                ):
                    continue

                # Find the calling function
                calling_function = self._find_function_at_line(caller_module, call_line)

                call_sites.append(
                    {
                        "calling_module": caller_module,
                        "calling_function": calling_function,
                        "file": module_data["file"],
                        "line": call_line,
                        "call_type": call_type,
                        "alias_used": alias_used,
                    }
                )

        return call_sites

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

    def _calculate_min_indentation(self, lines: list[str]) -> int:
        """
        Calculate the minimum indentation level across non-empty lines.

        Args:
            lines: List of code lines

        Returns:
            Minimum indentation (number of leading spaces), or 0 if no non-empty lines
        """
        min_indent: int | None = None

        for line in lines:
            if not line.strip():  # Skip empty/whitespace-only lines
                continue

            leading_spaces = len(line) - len(line.lstrip())
            min_indent = leading_spaces if min_indent is None else min(min_indent, leading_spaces)

        return 0 if min_indent is None else min_indent

    def _dedent_lines(self, lines: list[str], indent_amount: int) -> list[str]:
        """
        Remove common leading indentation from lines.

        Args:
            lines: List of code lines
            indent_amount: Number of spaces to remove from the start of each line

        Returns:
            Dedented lines
        """
        if indent_amount == 0:
            return lines

        dedented = []
        for line in lines:
            if len(line) >= indent_amount:
                dedented.append(line[indent_amount:])
            else:
                dedented.append(line)

        return dedented

    def _extract_complete_call(self, lines: list[str], start_line: int) -> str | None:
        """
        Extract code with context around the call line.

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

        # Calculate context range
        start_idx = max(0, call_idx - self.CALL_CONTEXT_LINES)
        end_idx = min(len(lines), call_idx + self.CALL_CONTEXT_LINES + 1)

        # Extract the lines with context
        extracted_lines = [lines[i].rstrip("\n") for i in range(start_idx, end_idx)]

        if not extracted_lines:
            return None

        # Remove common indentation
        min_indent = self._calculate_min_indentation(extracted_lines)
        dedented_lines = self._dedent_lines(extracted_lines, min_indent)

        return "\n".join(dedented_lines)

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

    def _parse_changed_since(self, changed_since: str) -> datetime:
        """
        Parse changed_since parameter into datetime.

        This is imported from git_handlers logic but kept here for simplicity.
        In a more refined refactoring, this could be a shared utility.

        Supports:
        - ISO dates: '2024-01-15'
        - Relative: '7d', '2w', '3m', '1y'

        Returns:
            datetime object (timezone-aware) representing the cutoff date

        Raises:
            ValueError: If format is invalid
        """
        from datetime import timedelta

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

        raise ValueError(f"Invalid changed_since format: {changed_since}")

    def _build_private_pattern_string(self, pattern: FunctionPattern) -> str:
        """
        Build a private function pattern string from a public pattern.

        Args:
            pattern: The original function pattern

        Returns:
            Pattern string with underscore prefix, preserving file scope if present
            (e.g., "lib/foo.ex:Module._func*" or "lib/foo.ex:_func*/2")
        """
        private_pattern = f"_{pattern.name}"

        if pattern.module:
            module_part = (
                pattern.module.replace("*.", "", 1)
                if pattern.module.startswith("*.")
                else pattern.module
            )
            private_pattern = f"{module_part}.{private_pattern}"

        if pattern.arity is not None:
            private_pattern += f"/{pattern.arity}"

        # Preserve file constraint if present
        if pattern.file:
            private_pattern = f"{pattern.file}:{private_pattern}"

        return private_pattern

    def _has_matching_private_function(
        self, private_pattern_str: str, cutoff_date: datetime | None
    ) -> bool:
        """
        Check if any private functions match the given pattern.

        Args:
            private_pattern_str: The private function pattern to match

        Returns:
            True if at least one matching private function exists
        """
        private_patterns = parse_function_patterns(private_pattern_str)

        for module_name, module_data in self.index["modules"].items():
            for func in module_data["functions"]:
                if not any(
                    p.matches(module_name, module_data["file"], func) for p in private_patterns
                ):
                    continue

                if cutoff_date:
                    func_modified = func.get("last_modified_at")
                    if not func_modified:
                        continue

                    func_modified_dt = datetime.fromisoformat(func_modified)
                    if func_modified_dt.tzinfo is None:
                        func_modified_dt = func_modified_dt.replace(tzinfo=timezone.utc)

                    if func_modified_dt < cutoff_date:
                        continue

                return True

        return False

    def _suggest_private_function(
        self,
        results: list,
        parsed_patterns: list[FunctionPattern],
        cutoff_date: datetime | None,
    ) -> str | None:
        """
        Suggest a private function pattern if no public functions were found.

        Args:
            results: The search results (empty if no matches)
            parsed_patterns: List of parsed function patterns from the search query

        Returns:
            Private function pattern string if matches found, None otherwise
        """
        if results or not parsed_patterns:
            return None

        for pattern in parsed_patterns:
            if not (pattern.name and not pattern.name.startswith("_") and "*" in pattern.name):
                continue

            private_pattern = self._build_private_pattern_string(pattern)

            if self._has_matching_private_function(private_pattern, cutoff_date):
                return private_pattern

        return None

    def _search_with_patterns(
        self,
        patterns: list[FunctionPattern],
        seen_functions: set[tuple[str, str, int]],
        cutoff_date: datetime | None,
        what_calls_it: bool,
        usage_type: str,
    ) -> list[dict]:
        """
        Execute a search with the given patterns, returning matching results.

        This helper method encapsulates the core search loop for reuse in fallback searches.
        """
        results = []
        for module_name, module_data in self.index["modules"].items():
            for func in module_data["functions"]:
                if any(p.matches(module_name, module_data["file"], func) for p in patterns):
                    # Apply cutoff_date filter
                    if cutoff_date:
                        func_modified = func.get("last_modified_at")
                        if not func_modified:
                            continue
                        func_modified_dt = datetime.fromisoformat(func_modified)
                        if func_modified_dt.tzinfo is None:
                            func_modified_dt = func_modified_dt.replace(tzinfo=timezone.utc)
                        if func_modified_dt < cutoff_date:
                            continue

                    key = (module_name, func["name"], func["arity"])
                    if key in seen_functions:
                        continue
                    seen_functions.add(key)

                    # Find call sites if what_calls_it is enabled
                    call_sites = []
                    if what_calls_it:
                        call_sites = self._find_call_sites(
                            target_module=module_name,
                            target_function=func["name"],
                            target_arity=func["arity"],
                        )
                        if usage_type != "all":
                            call_sites = filter_by_file_type(call_sites, usage_type)

                    results.append(
                        {
                            "module": module_name,
                            "moduledoc": module_data.get("moduledoc"),
                            "function": func,
                            "file": module_data["file"],
                            "call_sites": call_sites,
                            "call_sites_with_examples": [],
                            "pr_info": None,
                            "detailed_dependencies": None,
                        }
                    )
        return results

    async def search_function(
        self,
        function_name: str,
        output_format: str = "markdown",
        include_usage_examples: bool = False,
        max_examples: int = 5,
        usage_type: str = "source",
        changed_since: str | None = None,
        what_calls_it: bool = True,
        module_path: str | None = None,
        what_it_calls: bool = False,
        include_code_context: bool = False,
        format_opts: dict | None = None,
        glob: str | None = None,
        head_limit: int | None = None,
        offset: int = 0,
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

        Args:
            function_name: Function name or pattern (can include module qualifier)
            module_path: Optional module path to prepend if function_name doesn't include it
            glob: Optional glob pattern to filter results by file path
            head_limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            (other params documented in tool definition)
        """
        from cicada.format import ModuleFormatter

        # Handle both calling conventions:
        # 1. function_name="Module.function" (already qualified)
        # 2. function_name="function", module_path="Module" (separate parameters)
        if module_path and "." not in function_name and ":" not in function_name:
            # Split OR patterns and qualify each term individually
            if "|" in function_name:
                terms = function_name.split("|")
                qualified_terms = [f"{module_path}.{term}" for term in terms]
                effective_pattern = "|".join(qualified_terms)
            else:
                effective_pattern = f"{module_path}.{function_name}"
        else:
            effective_pattern = function_name

        # Support OR syntax by splitting first, then parsing each component individually
        parsed_patterns: list[FunctionPattern] = parse_function_patterns(effective_pattern)

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

                    # Find call sites if what_calls_it is enabled
                    call_sites = []
                    call_sites_with_examples = []
                    if what_calls_it:
                        call_sites = self._find_call_sites(
                            target_module=module_name,
                            target_function=func["name"],
                            target_arity=func["arity"],
                        )

                        # Filter call sites by file type if not 'all'
                        if usage_type != "all":
                            call_sites = filter_by_file_type(call_sites, usage_type)

                        # Optionally include usage examples (actual code lines)
                        if include_usage_examples and call_sites:
                            # Consolidate call sites by calling module (one example per module)
                            consolidated_sites = self._consolidate_call_sites_by_module(call_sites)
                            # Limit the number of examples
                            call_sites_with_examples = consolidated_sites[:max_examples]
                            # Extract code lines for each call site
                            self._add_code_examples(call_sites_with_examples)

                    # Get PR context for this function (we'll need pr_handler reference)
                    # For now, we'll skip this or pass it from server
                    pr_info = None

                    # Get detailed dependency info if what_it_calls is enabled
                    detailed_dependencies = None
                    if what_it_calls:
                        detailed_dependencies = self._get_detailed_dependencies(
                            module_name,
                            func,
                            module_data["file"],
                            include_code_context,
                        )

                    results.append(
                        {
                            "module": module_name,
                            "moduledoc": module_data.get("moduledoc"),
                            "function": func,
                            "file": module_data["file"],
                            "call_sites": call_sites,
                            "call_sites_with_examples": call_sites_with_examples,
                            "pr_info": pr_info,
                            "detailed_dependencies": detailed_dependencies,
                        }
                    )

        # Apply glob filter if specified
        if glob:
            from cicada.utils.path_utils import matches_glob_pattern

            results = [r for r in results if matches_glob_pattern(str(r["file"]), glob)]

        # Check index staleness (we'll need index_manager reference)
        # For now, we'll skip this or pass it from server
        staleness_info = None

        # Apply automatic fallback searches when no results found
        fallback_note = None
        if not results:
            from cicada.mcp.fallbacks import apply_fallbacks

            def search_fn(patterns: list[FunctionPattern]) -> list[dict]:
                return self._search_with_patterns(
                    patterns, seen_functions, cutoff_date, what_calls_it, usage_type
                )

            fallback_result = apply_fallbacks(
                parsed_patterns,
                search_fn,
                context={"module_path": module_path},
            )
            results = fallback_result.results
            fallback_note = fallback_result.note

        # If still no results, generate suggestion for private function (for display only)
        private_suggestion = self._suggest_private_function(results, parsed_patterns, cutoff_date)

        # Apply pagination (offset + head_limit)
        if offset > 0:
            results = results[offset:]
        if head_limit is not None and head_limit > 0:
            results = results[:head_limit]

        # Get language from index metadata
        language = self.index.get("metadata", {}).get("language", "elixir")

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_function_results_json(function_name, results)
        else:
            result = ModuleFormatter.format_function_results_markdown(
                function_name,
                results,
                staleness_info,
                what_it_calls,
                language,
                private_suggestion,
                format_opts=format_opts,
                fallback_note=fallback_note,
            )

        return [TextContent(type="text", text=result)]
