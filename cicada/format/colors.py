"""
Shared ANSI color codes for Cicada CLI.

This module provides consistent color definitions across all Cicada modules
to eliminate code duplication and ensure brand consistency.
"""

# Brand colors - primary palette
ORANGE = "\033[38;2;217;119;87m"  # #D97757 - Primary brand color (orange)
YELLOW = "\033[38;2;229;200;144m"  # #E5C890 - Selected items/highlights
SELECTED = YELLOW  # Alias for menu selections
CYAN = ORANGE  # Deprecated alias - kept for backwards compatibility

# Standard terminal colors
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
GRAY = "\033[90m"
GREY = GRAY  # British spelling alias

# Modifiers
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Composite styles (for convenience)
PRIMARY = ORANGE  # Alias for primary brand color
