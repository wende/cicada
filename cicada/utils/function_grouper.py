"""
Function grouping utilities.

This module provides utilities for grouping functions by name and arity,
eliminating duplication across formatter and other modules.
"""

from typing import Any


class FunctionGrouper:
    """
    Groups functions by their name and arity.

    This eliminates duplication of the grouping logic that appears
    multiple times in the formatter module.
    """

    @staticmethod
    def group_by_name_arity(
        functions: list[dict[str, Any]],
    ) -> dict[tuple[str, int], list[dict[str, Any]]]:
        """
        Group functions by their (name, arity) tuple.

        Multiple function clauses with the same name and arity are grouped
        together. This handles languages that allow multiple definitions
        for the same function signature (e.g., pattern matching clauses).

        Args:
            functions: List of function dictionaries with 'name' and 'arity' keys

        Returns:
            Dictionary mapping (name, arity) tuples to lists of function clauses

        Example:
            functions = [
                {'name': 'create', 'arity': 1, 'line': 10},
                {'name': 'create', 'arity': 1, 'line': 15},  # Second clause
                {'name': 'create', 'arity': 2, 'line': 20},
            ]
            grouped = FunctionGrouper.group_by_name_arity(functions)
            # Returns:
            # {
            #     ('create', 1): [{'name': 'create', 'arity': 1, ...}, {...}],
            #     ('create', 2): [{'name': 'create', 'arity': 2, ...}]
            # }
        """
        grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}

        for func in functions:
            key = (func["name"], func["arity"])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(func)

        return grouped
