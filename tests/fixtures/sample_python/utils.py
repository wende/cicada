"""Utility functions for calculator operations.

Helper functions that build on basic operations.
"""

from typing import List, Union
import operations


# Constant for testing imports
MAX_PRECISION = 10


def chain_add(numbers: List[Union[int, float]]) -> Union[int, float]:
    """
    Add a list of numbers by chaining add operations.

    Args:
        numbers: List of numbers to add

    Returns:
        Sum of all numbers
    """
    if not numbers:
        return 0

    result = numbers[0]
    for num in numbers[1:]:
        result = operations.add(result, num)  # Cross-file call
    return result


def average(numbers: List[Union[int, float]]) -> float:
    """
    Calculate average of numbers using operations module.

    Args:
        numbers: List of numbers

    Returns:
        Average value

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot average empty list")

    total = chain_add(numbers)  # Internal call
    return operations.divide(total, len(numbers))  # Cross-file call


def format_result(value: Union[int, float], precision: int = 2) -> str:
    """
    Format a numeric result as a string.

    Args:
        value: Number to format
        precision: Decimal places (default: 2)

    Returns:
        Formatted string
    """
    if precision > MAX_PRECISION:
        precision = MAX_PRECISION
    return f"{value:.{precision}f}"


def _internal_helper(x: float, y: float) -> float:
    """Private helper that uses operations."""
    temp = operations.multiply(x, 2)  # Cross-file call from private function
    return operations.add(temp, y)
