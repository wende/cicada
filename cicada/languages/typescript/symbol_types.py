"""TypeScript/JavaScript SCIP symbol type detection.

TypeScript symbol descriptor patterns (from scip-typescript):
- `file.ts`/ -> module (ends with /)
- `file.ts`/ClassName# -> class (ends with #)
- `file.ts`/ClassName#methodName(). -> method (contains #, ends with ().)
- `file.ts`/functionName(). -> function (no #, ends with ().)
- `file.ts`/ClassName#property. -> property (contains #, ends with . but not ().)
- `file.ts`/ClassName#methodName().(param) -> parameter

Note: TypeScript DOES use (). suffix for callables, similar to Python.
Properties use just . suffix (without ()).
"""

import re
from typing import Literal

SymbolType = Literal["class", "method", "function", "module", "parameter", "unknown"]


def get_symbol_type(descriptor: str) -> SymbolType:
    """
    Determine symbol type for TypeScript/JavaScript SCIP symbols.

    Args:
        descriptor: The descriptor portion of the SCIP symbol (parts[4:] joined)

    Returns:
        Symbol type: 'class', 'method', 'function', 'module', 'parameter',
                    or 'unknown'
    """
    # Parameter: ends with .(param_name) or ().(param_name)
    if re.match(r".*\(\)\.\([^)]+\)$", descriptor) or re.match(r".*\.\([^)]+\)$", descriptor):
        return "parameter"

    # Module/namespace: ends with / or :
    if descriptor.endswith(("/", ":")):
        return "module"

    # Class/Interface/Type: ends with #
    if descriptor.endswith("#"):
        return "class"

    # Method: contains # and ends with (). (callable)
    if "#" in descriptor and descriptor.endswith("()."):
        return "method"

    # Function: no # but ends with (). (callable)
    if "#" not in descriptor and descriptor.endswith("()."):
        return "function"

    # Property: contains # and ends with . (not ().)
    if "#" in descriptor and descriptor.endswith(".") and not descriptor.endswith("()."):
        return "unknown"  # Property - not a callable

    return "unknown"


def is_callable(descriptor: str) -> bool:
    """
    Check if a TypeScript symbol descriptor represents a callable.

    Args:
        descriptor: The descriptor portion of the SCIP symbol

    Returns:
        True if the symbol is a function or method
    """
    symbol_type = get_symbol_type(descriptor)
    return symbol_type in ("function", "method")
