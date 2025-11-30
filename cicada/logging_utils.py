"""Logging utilities for Cicada CLI."""

import logging
import sys
from argparse import Namespace


def configure_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: If True, set logging level to DEBUG, otherwise WARNING
    """
    level = logging.DEBUG if verbose else logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s" if verbose else "%(message)s",
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )


def get_verbose_flag(args: Namespace) -> bool:
    """Extract verbose flag from parsed arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if verbose flag is set, False otherwise
    """
    return getattr(args, "verbose", False)
