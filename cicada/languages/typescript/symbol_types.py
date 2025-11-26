"""TypeScript/JavaScript SCIP symbol type detection.

TypeScript symbol descriptor patterns (from scip-typescript):
- src/file.ts:moduleName: -> module (ends with :)
- src/file.ts:ClassName# -> class (ends with #)
- src/file.ts:ClassName#methodName. -> method (contains #, ends with .)
- src/file.ts:functionName. -> function (no #, ends with .)
- src/file.ts:ClassName#methodName.(param). -> parameter

Note: TypeScript doesn't use ()., it uses just . for functions/methods.
This differs from Python which uses (). suffix for callables.
"""

import re
from typing import Literal

SymbolType = Literal["class", "method", "function", "module", "parameter", "attribute", "unknown"]


def get_symbol_type(descriptor: str) -> SymbolType:
    """
    Determine symbol type for TypeScript/JavaScript SCIP symbols.

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

    # Class/Interface/Type: ends with #
    if descriptor.endswith("#"):
        return "class"

    # Method: contains # and ends with . (TypeScript style - no parens)
    if "#" in descriptor and descriptor.endswith("."):
        return "method"

    # Function: no # but ends with . (TypeScript style - no parens)
    if "#" not in descriptor and descriptor.endswith("."):
        return "function"

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
