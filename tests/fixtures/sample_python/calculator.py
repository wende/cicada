"""Simple calculator module for testing Python SCIP indexing.

This module provides basic arithmetic operations through the Calculator class.
"""

from typing import List, Union
import operations
from utils import chain_add, format_result


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
        Add two numbers using operations module.

        Args:
            x: First number
            y: Second number

        Returns:
            Sum of x and y
        """
        return operations.add(x, y)  # Cross-file call

    def multiply(self, x: int, y: int) -> int:
        """
        Multiply two numbers using operations module.

        Args:
            x: First number
            y: Second number

        Returns:
            Product of x and y
        """
        return operations.multiply(x, y)  # Cross-file call

    def divide(self, x: Union[int, float], y: Union[int, float]) -> float:
        """
        Divide x by y.

        Args:
            x: Numerator
            y: Denominator

        Returns:
            Result of division
        """
        return operations.divide(x, y)  # Cross-file call

    def sum_list(self, numbers: List[Union[int, float]]) -> Union[int, float]:
        """
        Sum a list of numbers using utils module.

        Args:
            numbers: List of numbers

        Returns:
            Sum of all numbers
        """
        return chain_add(numbers)  # Cross-file call to utils

    def format_value(self, value: Union[int, float]) -> str:
        """
        Format a value using utils module.

        Args:
            value: Number to format

        Returns:
            Formatted string
        """
        return format_result(value)  # Cross-file call to utils

    def _private_method(self) -> str:
        """Private method (should be marked as private in index)."""
        return "private"

    def calculate_expression(self, x: int, y: int, z: int) -> int:
        """
        Calculate a complex expression using multiple operations.

        Args:
            x: First operand
            y: Second operand
            z: Third operand

        Returns:
            Result of (x + y) * z
        """
        # Multiple calls in one function
        sum_result = self.add(x, y)  # First call
        product = self.multiply(sum_result, z)  # Second call
        return product

    def sum_three(self, x: int, y: int, z: int) -> int:
        """
        Sum three numbers by calling add multiple times.

        Args:
            x: First number
            y: Second number
            z: Third number

        Returns:
            Sum of x, y, and z
        """
        # Same function called multiple times
        temp = self.add(x, y)  # First call to add()
        result = self.add(temp, z)  # Second call to add()
        return result


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
