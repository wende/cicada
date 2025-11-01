"""
Call site formatting utilities.

This module provides utilities for grouping and formatting call sites,
eliminating duplication in the formatter module.
"""

from typing import Any


class CallSiteFormatter:
    """
    Formats and groups call sites for display.

    This class consolidates the call site grouping and formatting logic
    that appears multiple times in the formatter module.
    """

    @staticmethod
    def group_by_caller(call_sites: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Group call sites by their caller (calling_module + calling_function).

        When the same function is called multiple times from the same caller,
        this consolidates those calls into a single entry with multiple line numbers.

        Args:
            call_sites: List of call site dictionaries with keys:
                - calling_module: Module making the call
                - calling_function: Function making the call (dict with name, arity)
                - file: File path
                - line: Line number
                - code_line: Optional code snippet

        Returns:
            List of grouped call site dictionaries with keys:
                - calling_module: Module making the call
                - calling_function: Function making the call
                - file: File path
                - lines: List of line numbers (sorted)
                - code_lines: List of {line, code} dicts (if present)

        Example:
            call_sites = [
                {'calling_module': 'MyApp.User', 'calling_function': {'name': 'create', 'arity': 2},
                 'file': 'lib/user.ex', 'line': 10},
                {'calling_module': 'MyApp.User', 'calling_function': {'name': 'create', 'arity': 2},
                 'file': 'lib/user.ex', 'line': 20},
            ]
            grouped = CallSiteFormatter.group_by_caller(call_sites)
            # Returns:
            # [{
            #     'calling_module': 'MyApp.User',
            #     'calling_function': {'name': 'create', 'arity': 2},
            #     'file': 'lib/user.ex',
            #     'lines': [10, 20]
            # }]
        """
        grouped: dict[tuple, dict[str, Any]] = {}

        for site in call_sites:
            # Create a key based on caller identity
            calling_func = site.get("calling_function")
            if calling_func:
                key = (
                    site["calling_module"],
                    calling_func["name"],
                    calling_func["arity"],
                )
            else:
                key = (site["calling_module"], None, None)

            if key not in grouped:
                grouped[key] = {
                    "calling_module": site["calling_module"],
                    "calling_function": calling_func,
                    "file": site["file"],
                    "lines": [],
                    "code_lines": [],
                }

            grouped[key]["lines"].append(site["line"])
            if "code_line" in site:
                grouped[key]["code_lines"].append({"line": site["line"], "code": site["code_line"]})

        # Convert back to list and sort lines
        result = []
        for data in grouped.values():
            data["lines"].sort()
            data["code_lines"].sort(key=lambda x: x["line"])
            result.append(data)

        return result
