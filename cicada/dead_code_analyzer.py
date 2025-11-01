"""
Dead Code Analyzer for Elixir codebases.

Identifies potentially unused public functions using the indexed codebase data.

Author: Cursor(Auto)
"""


class DeadCodeAnalyzer:
    """Analyzes Elixir code index to find potentially unused public functions."""

    def __init__(self, index: dict):
        """
        Initialize analyzer with code index.

        Args:
            index: The indexed codebase data containing modules and their metadata
        """
        self.index = index
        self.modules = index.get("modules", {})

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
            # Skip test files and .exs files entirely
            if self._is_test_file(module_data["file"]):
                skipped_files += sum(1 for f in module_data["functions"] if f["type"] == "def")
                continue

            # Analyze each function in the module
            for function in module_data["functions"]:
                # Only analyze public functions
                if function["type"] != "def":
                    continue

                total_public += 1

                # Skip functions with @impl (they're called by behaviors)
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

    def _is_test_file(self, file_path: str) -> bool:
        """
        Check if a file should be skipped from dead code analysis.

        Files are skipped if they are:
        - Test files (in 'test/' directory or '_test.ex' suffix)
        - Script files (.exs extension)

        Args:
            file_path: Path to the file

        Returns:
            True if the file should be skipped
        """
        file_lower = file_path.lower()
        return (
            # Test files
            "/test/" in file_lower
            or file_lower.startswith("test/")
            or file_lower.endswith(("_test.ex", ".exs"))
        )

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
        call_count = 0

        # Get the function definition line to filter out @spec/@doc
        function_def_line = None
        if target_module in self.modules:
            for func in self.modules[target_module]["functions"]:
                if func["name"] == target_function and func["arity"] == target_arity:
                    function_def_line = func["line"]
                    break

        # Search through all modules for calls
        for caller_module, module_data in self.modules.items():
            # Get aliases for resolving calls
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
                        # Filter out calls that are BEFORE the function definition
                        # (@spec, @doc annotations appear 1-5 lines before the def)
                        # Only filter if call is before def and within 5 lines
                        if (
                            function_def_line
                            and call["line"] < function_def_line
                            and (function_def_line - call["line"]) <= 5
                        ):
                            continue
                        call_count += 1
                else:
                    # Qualified call - resolve the module name
                    resolved_module = aliases.get(call_module, call_module)

                    # Check if this resolves to our target module
                    if resolved_module == target_module:
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
