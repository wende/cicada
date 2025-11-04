"""Basic arithmetic operations module.

Provides fundamental math operations with type hints and documentation.
"""

from typing import Union


def add(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    """
    Add two numbers together.

    Args:
        x: First number
        y: Second number

    Returns:
        Sum of x and y
    """
    return x + y


def subtract(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    """
    Subtract y from x.

    Args:
        x: Number to subtract from
        y: Number to subtract

    Returns:
        Difference of x and y
    """
    return x - y


def multiply(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    """
    Multiply two numbers.

    Args:
        x: First number
        y: Second number

    Returns:
        Product of x and y
    """
    return x * y


def divide(x: Union[int, float], y: Union[int, float]) -> float:
    """
    Divide x by y with error handling.

    Args:
        x: Numerator
        y: Denominator

    Returns:
        Result of division

    Raises:
        ValueError: If y is zero
    """
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y


def _internal_operation(value: float) -> float:
    """Private internal operation."""
    return abs(value)
