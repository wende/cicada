"""Rust SCIP symbol type detection.

Rust symbol descriptor patterns (from rust-analyzer):
- crate/module/Struct# -> class (struct/enum/trait)
- crate/module/Struct#method(). -> method
- crate/module/function(). -> function
- crate/module/macro! -> macro (treated as function)
"""

import re
from typing import Literal

SymbolType = Literal[
    "class", "method", "function", "module", "parameter", "attribute", "macro", "unknown"
]


def get_symbol_type(descriptor: str) -> SymbolType:
    """
    Determine symbol type for Rust SCIP symbols.

    Args:
        descriptor: The descriptor portion of the SCIP symbol

    Returns:
        Symbol type
    """
    # Parameter: ends with .(param_name) or (param_name)
    # rust-analyzer specific format for params needs verification, but assuming standard SCIP
    if re.match(r".*\.\([^)]+\)$", descriptor):
        return "parameter"

    # Module: usually implicit in SCIP structure, but if explicit
    # rust-analyzer uses `mod` maybe?
    # For now, if it ends with /, it's a namespace/module, but SCIP symbols usually don't end with / unless it's a package?
    # Python uses : for modules. Rust might not output explicit module symbols in the same way or use different suffix.
    # But let's stick to common patterns.

    # Class/Struct/Enum/Trait: ends with #
    if descriptor.endswith("#"):
        return "class"

    # Method: contains # and ends with ().
    if "#" in descriptor and descriptor.endswith("()."):
        return "method"

    # Function: no # but ends with ().
    if "#" not in descriptor and descriptor.endswith("()."):
        return "function"

    # Macro
    if "!" in descriptor:
        return "function"  # Treat macros as functions for now

    # Attribute/field: ends with . (but not ().)
    if descriptor.endswith(".") and not descriptor.endswith("()."):
        return "attribute"

    return "unknown"
