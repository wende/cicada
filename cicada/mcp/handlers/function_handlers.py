"""
Function Search Tool Handlers.

Handles tools for searching functions and analyzing their call sites.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from mcp.types import TextContent

from cicada.mcp.pattern_utils import FunctionPattern, parse_function_patterns


class FunctionSearchHandler:
    """Handler for function search and call site analysis."""

    def __init__(self, index: dict[str, Any], config: dict[str, Any]):
        """
        Initialize the function search handler.

        Args:
            index: The code index containing modules and functions
            config: Configuration dictionary
        """
        self.index = index
        self.config = config

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

    async def search_function(
        self,
        function_name: str,
        output_format: str = "markdown",
        include_usage_examples: bool = False,
        max_examples: int = 5,
        usage_type: str = "source",
        changed_since: str | None = None,
        show_relationships: bool = True,
        module_path: str | None = None,
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
            (other params documented in tool definition)
        """
        from cicada.elixir.format import ModuleFormatter

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
                    # Find call sites for this function
                    call_sites = self._find_call_sites(
                        target_module=module_name,
                        target_function=func["name"],
                        target_arity=func["arity"],
                    )

                    # Filter call sites by file type if not 'all'
                    if usage_type != "all":
                        from cicada.mcp.filter_utils import filter_by_file_type

                        call_sites = filter_by_file_type(call_sites, usage_type)

                    # Optionally include usage examples (actual code lines)
                    call_sites_with_examples = []
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

        # Check index staleness (we'll need index_manager reference)
        # For now, we'll skip this or pass it from server
        staleness_info = None

        # Format results
        if output_format == "json":
            result = ModuleFormatter.format_function_results_json(function_name, results)
        else:
            result = ModuleFormatter.format_function_results_markdown(
                function_name, results, staleness_info, show_relationships
            )

        return [TextContent(type="text", text=result)]
