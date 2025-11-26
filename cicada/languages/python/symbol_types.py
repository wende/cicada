"""Python SCIP symbol type detection.

Python symbol descriptor patterns (from scip-python/Pyright):
- calculator/__init__: -> module (ends with :)
- calculator/Calculator# -> class (ends with #)
- calculator/Calculator#add(). -> method (contains #, ends with ().)
- calculator/helper_function(). -> function (no #, ends with ().)
- calculator/Calculator#add().(x) -> parameter (ends with .(name))
- calculator/Calculator#value. -> attribute (ends with . but not ().)

Note: Python uses (). suffix for callables (functions and methods).
This differs from TypeScript which uses just . suffix.
"""

import re
from typing import Literal

SymbolType = Literal["class", "method", "function", "module", "parameter", "attribute", "unknown"]


def get_symbol_type(descriptor: str) -> SymbolType:
    """
    Determine symbol type for Python SCIP symbols.

    Args:
        descriptor: The descriptor portion of the SCIP symbol (parts[4:] joined)

    Returns:
        Symbol type: 'class', 'method', 'function', 'module', 'parameter',
                    'attribute', or 'unknown'
    """
    # Parameter: ends with .(param_name)
    if re.match(r".*\.\([^)]+\)$", descriptor):
        return "parameter"

    # Module/namespace: ends with :
    if descriptor.endswith(":"):
        return "module"

    # Class: ends with # (no method following)
    if descriptor.endswith("#"):
        return "class"

    # Method: contains # and ends with ().
    if "#" in descriptor and descriptor.endswith("()."):
        return "method"

    # Function: no # but ends with ().
    if "#" not in descriptor and descriptor.endswith("()."):
        return "function"

    # Attribute/variable: ends with . (but not ().)
    if descriptor.endswith(".") and not descriptor.endswith("()."):
        return "attribute"

    return "unknown"


def is_callable(descriptor: str) -> bool:
    """
    Check if a Python symbol descriptor represents a callable.

    Args:
        descriptor: The descriptor portion of the SCIP symbol

    Returns:
        True if the symbol is a function or method
    """
    symbol_type = get_symbol_type(descriptor)
    return symbol_type in ("function", "method")
