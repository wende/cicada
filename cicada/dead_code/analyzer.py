"""
Dead Code Analyzer for Elixir codebases.

Identifies potentially unused public functions using the indexed codebase data.

Author: Cursor(Auto)
"""

from cicada.utils.index_lookup import find_callers_from_reverse_index
from cicada.utils.path_utils import is_test_file


class DeadCodeAnalyzer:
    """Analyzes Elixir code index to find potentially unused public functions."""

    def __init__(self, index: dict, stop_functions: set[str] | None = None):
        """
        Initialize analyzer with code index.

        Args:
            index: The indexed codebase data containing modules and their metadata
            stop_functions: Set of function names to always consider alive
        """
        self.index = index
        self.modules = index.get("modules", {})
        # Default stop functions for Python (and potentially others)
        self.stop_functions = stop_functions or {"__init__", "main"}

    def add_stop_function(self, function_name: str) -> None:
        """
        Add a function name to the stop list.

        Args:
            function_name: Name of function to always consider alive
        """
        self.stop_functions.add(function_name)

    def analyze(self) -> dict:
        """
        Analyze the index to find dead code candidates.

        Returns:
            Dict with analysis results:
            {
                "summary": {
                    "total_public_functions": int,
                    "analyzed_functions": int,
                    "skipped_impl_functions": int,
                    "skipped_test_functions": int,
                    "total_candidates": int
                },
                "candidates": {
                    "high": [...],
                    "medium": [...],
                    "low": [...]
                }
            }
        """
        # Track statistics
        total_public = 0
        skipped_impl = 0
        skipped_files = 0  # test files and .exs files
        analyzed = 0

        # Collect candidates by confidence level
        candidates = {"high": [], "medium": [], "low": []}

        # Analyze each module
        for module_name, module_data in self.modules.items():
            # Check if this is a test file
            is_test = is_test_file(module_data["file"])

            # Analyze each function in the module
            for function in module_data["functions"]:
                # Skip test file functions - don't analyze them as dead code candidates
                # But we still need to search their dependencies later!
                if is_test:
                    func_type = function.get("type")
                    if func_type in ("def", "public"):
                        skipped_files += 1
                    continue

                # Only analyze public functions
                # Elixir: type == "def" (vs "defp" for private)
                # Python: type == "public" (vs "private")
                func_type = function.get("type")
                if func_type not in ("def", "public"):
                    continue

                # Check if it's a stop function (always considered alive)
                if function["name"] in self.stop_functions:
                    continue

                total_public += 1

                # Skip functions with @impl (they're called by behaviors)
                # Note: This is Elixir-specific, Python doesn't use @impl
                if function.get("impl"):
                    skipped_impl += 1
                    continue

                analyzed += 1

                # Find usages of this function
                usage_count = self._find_usages(module_name, function["name"], function["arity"])

                # If function is used, skip it
                if usage_count > 0:
                    continue

                # Function has zero usages - determine confidence level
                confidence = self._calculate_confidence(module_name, module_data)

                # Create candidate entry
                candidate = {
                    "module": module_name,
                    "function": function["name"],
                    "arity": function["arity"],
                    "line": function["line"],
                    "file": module_data["file"],
                    "signature": function.get(
                        "signature", f"{function['type']} {function['name']}"
                    ),
                }

                # Add context for low/medium confidence
                if confidence == "low":
                    # Module is used as value somewhere
                    value_mentioners = self._find_value_mentioners(module_name)
                    candidate["reason"] = "module_passed_as_value"
                    candidate["mentioned_in"] = value_mentioners
                elif confidence == "medium":
                    # Module has behaviors or uses
                    candidate["reason"] = "module_has_behaviors_or_uses"
                    candidate["uses"] = module_data.get("uses", [])
                    candidate["behaviours"] = module_data.get("behaviours", [])
                else:
                    candidate["reason"] = "no_usage_found"

                candidates[confidence].append(candidate)

        # Build summary
        total_candidates = sum(len(candidates[level]) for level in candidates)

        return {
            "summary": {
                "total_public_functions": total_public,
                "analyzed": analyzed,
                "skipped_impl": skipped_impl,
                "skipped_files": skipped_files,
                "total_candidates": total_candidates,
            },
            "candidates": candidates,
        }

    def _find_usages_from_reverse_index(
        self,
        target_module: str,
        target_function: str,
    ) -> int | None:
        """
        Fast usage count lookup using pre-computed reverse_calls index.

        Uses shared utility for key matching and deduplication.

        Note: While primary lookups are O(1), a fallback scan for matching keys
        makes worst-case complexity O(N) where N is the number of keys in reverse_calls.

        Args:
            target_module: Module containing the function
            target_function: Function name

        Returns:
            Number of call sites found, or None if reverse_calls not available
        """
        callers = find_callers_from_reverse_index(self.index, target_module, target_function)
        if callers is None:
            return None

        return len(callers)

    def _find_usages(self, target_module: str, target_function: str, target_arity: int) -> int:
        """
        Find the number of times a function is called across the codebase.

        Uses the same logic as mcp_server._find_call_sites to resolve aliases
        and match function calls.

        Args:
            target_module: Module containing the function
            target_function: Function name
            target_arity: Function arity

        Returns:
            Number of call sites found
        """
        # Fast path: use reverse_calls index if available
        fast_count = self._find_usages_from_reverse_index(target_module, target_function)
        if fast_count is not None:
            return fast_count

        # Fallback: O(n) scan for indexes without reverse_calls
        call_count = 0

        # Get the function definition line to filter out @spec/@doc
        function_def_line = None
        target_file = None
        if target_module in self.modules:
            target_file = self.modules[target_module].get("file")
            for func in self.modules[target_module]["functions"]:
                if func["name"] == target_function and func["arity"] == target_arity:
                    function_def_line = func["line"]
                    break

        # Search through all modules for calls
        for caller_module, module_data in self.modules.items():
            # Get aliases for resolving calls (Elixir-specific)
            aliases = module_data.get("aliases", {})

            # Collect all dependencies (module-level and function-level)
            # This handles both Elixir (module-level) and Python (function-level)
            all_dependencies = []

            # Add module-level dependencies
            # Handle both old list format and new dict format from SCIP converter
            deps = module_data.get("dependencies", [])
            if isinstance(deps, dict):
                # New SCIP format: {"modules": [...], "has_dynamic_calls": bool}
                # Module names are strings, not dicts, so we need to convert them
                # to the old format for compatibility with the rest of the code
                # Note: For now, we skip module-level dependencies from SCIP indexes
                # because they don't include function/arity information.
                # Function-level dependencies (below) will handle actual calls.
                pass
            elif isinstance(deps, list):
                # Old Elixir format: list of dicts with {module, function, arity, line}
                for dep in deps:
                    if isinstance(dep, dict):  # Skip string-only dependencies
                        all_dependencies.append(dep)

            # Add function-level dependencies (for Python/SCIP)
            for func in module_data.get("functions", []):
                for dep in func.get("dependencies", []):
                    if isinstance(dep, dict):
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

                # Module matching logic
                call_module = call.get("module")

                if call_module is None:
                    # Local call - check if it's in the same module
                    if caller_module == target_module:
                        # Filter out calls that are BEFORE the function definition
                        # (@spec, @doc annotations appear 1-5 lines before the def)
                        # Only filter if call is before def and within 5 lines
                        if (
                            function_def_line
                            and call.get("line", 0) < function_def_line
                            and (function_def_line - call.get("line", 0)) <= 5
                        ):
                            continue
                        call_count += 1
                else:
                    # Qualified call - resolve the module name
                    resolved_module = aliases.get(call_module, call_module)

                    # Check if this resolves to our target module
                    if resolved_module == target_module:
                        call_count += 1
                    # Python fallback: Check if module paths match (handles backtick-wrapped paths)
                    elif target_file:
                        # Convert file path to module path
                        # cicada/languages/__init__.py -> cicada.languages
                        # cicada/indexer.py -> cicada.indexer
                        module_path = target_file.replace("/", ".").replace(".py", "")
                        if module_path.endswith(".__init__"):
                            module_path = module_path[: -len(".__init__")]

                        # Check if the call module matches (with or without backticks)
                        if call_module.strip("`") == module_path:
                            call_count += 1

        return call_count

    def _calculate_confidence(self, module_name: str, module_data: dict) -> str:
        """
        Calculate confidence level for a dead code candidate.

        Confidence levels:
        - high: No usage, no dynamic call indicators, no behaviors/uses
        - medium: No usage, but module has behaviors or uses (possible callbacks)
        - low: No usage, but module passed as value (possible dynamic calls)

        Args:
            module_name: Name of the module
            module_data: Module metadata

        Returns:
            Confidence level: "high", "medium", or "low"
        """
        # Check if module is used as a value (lowest confidence)
        if self._is_module_used_as_value(module_name):
            return "low"

        # Check if module has behaviors or uses (medium confidence)
        has_behaviour = len(module_data.get("behaviours", [])) > 0
        has_use = len(module_data.get("uses", [])) > 0

        if has_behaviour or has_use:
            return "medium"

        # No dynamic indicators - high confidence
        return "high"

    def _is_module_used_as_value(self, module_name: str) -> bool:
        """
        Check if a module is mentioned as a value in any other module.

        When a module is passed as a value, its functions might be called
        dynamically, so we can't be certain they're unused.

        Args:
            module_name: Module to check

        Returns:
            True if module appears in value_mentions of any other module
        """
        for _other_module, module_data in self.modules.items():
            if module_name in module_data.get("value_mentions", []):
                return True
        return False

    def _find_value_mentioners(self, module_name: str) -> list[dict]:
        """
        Find all modules that mention this module as a value.

        Args:
            module_name: Module to search for

        Returns:
            List of dicts with {"module": str, "file": str}
        """
        mentioners = []
        for other_module, module_data in self.modules.items():
            if module_name in module_data.get("value_mentions", []):
                mentioners.append({"module": other_module, "file": module_data["file"]})
        return mentioners
