"""Simple calculator module for testing Python SCIP indexing.

This module provides basic arithmetic operations through the Calculator class.
"""


class Calculator:
    """A simple calculator that performs basic arithmetic operations."""

    def __init__(self, initial_value: int = 0):
        """
        Initialize calculator with an optional starting value.

        Args:
            initial_value: The starting value (default: 0)
        """
        self.value = initial_value

    def add(self, x: int, y: int) -> int:
        """
        Add two numbers.

        Args:
            x: First number
            y: Second number

        Returns:
            Sum of x and y
        """
        return x + y

    def multiply(self, x: int, y: int) -> int:
        """
        Multiply two numbers.

        Args:
            x: First number
            y: Second number

        Returns:
            Product of x and y
        """
        return x * y

    def _private_method(self) -> str:
        """Private method (should be marked as private in index)."""
        return "private"


def helper_function(data: list) -> int:
    """
    Top-level function to process data.

    Args:
        data: List of items

    Returns:
        Length of the list
    """
    return len(data)


def _private_function() -> None:
    """Private function (leading underscore)."""
    pass
