"""Test file for alias extraction."""

# Different types of Python imports
import operations
import operations as ops
from utils import chain_add
from utils import average as avg
from calculator import Calculator as Calc


def test_alias_usage():
    """Test using different import patterns."""
    # Using full module name
    result1 = operations.add(1, 2)

    # Using alias
    result2 = ops.multiply(3, 4)

    # Using imported function directly
    result3 = chain_add([1, 2, 3])

    # Using imported function with alias
    result4 = avg([10, 20, 30])

    # Using class with alias
    Calc(100)

    # Use the results to avoid unused variable warnings
    _ = result1 + result2 + result3 + result4
