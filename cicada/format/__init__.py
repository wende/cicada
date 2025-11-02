"""Format module for Cicada - handles formatting, colors, and ASCII art."""

from .ascii_art import generate_gradient_ascii_art
from .colors import BOLD, CYAN, GREEN, GREY, PRIMARY, RESET, SELECTED, YELLOW
from .formatter import JSONFormatter, ModuleFormatter, main

__all__ = [
    "generate_gradient_ascii_art",
    "BOLD",
    "CYAN",
    "GREEN",
    "GREY",
    "PRIMARY",
    "RESET",
    "SELECTED",
    "YELLOW",
    "ModuleFormatter",
    "JSONFormatter",
    "main",
]
