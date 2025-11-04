"""Main entry point for calculator application.

Demonstrates usage of all modules and cross-file dependencies.
"""

from calculator import Calculator
from operations import add, subtract, multiply
from utils import chain_add, average


def run_calculations() -> None:
    """Run sample calculations using all modules."""
    # Create calculator instance
    calc = Calculator(initial_value=10)

    # Multiple calls to the same function (operations.add via calc.add)
    result1 = calc.add(5, 3)  # First call to calc.add
    result2 = calc.add(10, 20)  # Second call to calc.add
    result3 = calc.add(result1, result2)  # Third call to calc.add

    # Direct calls to operations module
    sum_val = add(100, 200)  # Call operations.add directly
    diff = subtract(sum_val, 50)
    product = multiply(diff, 2)

    # Use utils module
    numbers = [1, 2, 3, 4, 5]
    total = chain_add(numbers)  # Call utils.chain_add
    avg = average(numbers)  # Call utils.average

    # Multiple calls to calc methods
    calc.multiply(5, 6)
    calc.multiply(3, 4)
    calc.divide(100, 4)

    # Format results
    formatted = calc.format_value(avg)

    print(f"Results: {result3}, {product}, {total}, {formatted}")


def process_data(data: list) -> dict:
    """
    Process input data and return results.

    Args:
        data: Input data list

    Returns:
        Dictionary with processed results
    """
    if not data:
        return {}

    total = chain_add(data)  # Another call to chain_add
    avg_val = average(data)  # Another call to average

    return {
        "total": total,
        "average": avg_val,
        "count": len(data),
    }


def _internal_main_helper(x: int, y: int) -> int:
    """Private helper function."""
    return add(x, y)  # Call operations.add from private function


if __name__ == "__main__":
    run_calculations()
    sample_data = [10, 20, 30, 40, 50]
    results = process_data(sample_data)
    print(f"Data processing results: {results}")
