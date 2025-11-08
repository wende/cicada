"""
Tier Configuration Module - Centralized tier resolution and conversion logic.

This module provides a single source of truth for:
- Tier validation (fast, regular, max)
- Tier resolution from arguments or config files
- Tier <-> (extraction_method, expansion_method) conversions
"""

import argparse
import sys
from pathlib import Path

# Tier to methods mapping
TIER_METHODS = {
    "fast": ("regular", "lemmi"),
    "regular": ("bert", "glove"),
    "max": ("bert", "fasttext"),
}

# Default methods if no configuration exists
DEFAULT_METHODS = ("regular", "lemmi")


def validate_tier_flags(args: argparse.Namespace) -> None:
    """Validate that only one tier flag is specified.

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Raises:
        SystemExit: If more than one tier flag is specified
    """
    tier_flags = [args.fast, getattr(args, "regular", False), args.max]

    if sum(tier_flags) > 1:
        print(
            "Error: Can only specify one tier flag (--fast, --regular, or --max)",
            file=sys.stderr,
        )
        sys.exit(1)


def get_tier_from_args(args: argparse.Namespace) -> str | None:
    """Extract tier from command-line arguments.

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Returns:
        Tier string ("fast", "regular", or "max"), or None if no tier flag specified
    """
    if args.fast:
        return "fast"
    if args.max:
        return "max"
    if getattr(args, "regular", False):
        return "regular"
    return None


def tier_to_methods(tier: str) -> tuple[str, str]:
    """Convert tier to (extraction_method, expansion_method).

    Args:
        tier: Tier string ("fast", "regular", or "max")

    Returns:
        Tuple of (extraction_method, expansion_method)
        - extraction_method is 'regular' or 'bert'
        - expansion_method is 'lemmi', 'glove', or 'fasttext'

    Tier mappings:
        - fast: regular extraction + lemmi expansion
        - regular: bert extraction + glove expansion
        - max: bert extraction + fasttext expansion
    """
    return TIER_METHODS.get(tier, DEFAULT_METHODS)


def methods_to_tier(extraction_method: str, expansion_method: str) -> str:
    """Convert (extraction_method, expansion_method) to tier.

    Args:
        extraction_method: 'regular' or 'bert'
        expansion_method: 'lemmi', 'glove', or 'fasttext'

    Returns:
        Tier string: "fast", "regular", or "max"
    """
    method_pair = (extraction_method, expansion_method)

    # Find matching tier in our mapping
    for tier, methods in TIER_METHODS.items():
        if methods == method_pair:
            return tier

    # Fallback logic for partial matches
    if extraction_method == "regular":
        return "fast"

    if extraction_method == "bert":
        if expansion_method == "fasttext":
            return "max"
        return "regular"

    # Default to regular for unknown combinations
    return "regular"


def read_keyword_extraction_config(repo_path: Path) -> tuple[str, str]:
    """Read keyword extraction configuration from config.yaml.

    Args:
        repo_path: Path to the repository

    Returns:
        tuple[str, str]: (extraction_method, expansion_method) where:
                        - extraction_method is 'regular' or 'bert'
                        - expansion_method is 'lemmi', 'glove', or 'fasttext'
                        Returns DEFAULT_METHODS if config not found.
    """
    try:
        import yaml

        from cicada.utils.storage import get_config_path

        config_path = get_config_path(repo_path)
        if not config_path.exists():
            return DEFAULT_METHODS

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config:
            return DEFAULT_METHODS

        extraction_method = config.get("keyword_extraction", {}).get("method", DEFAULT_METHODS[0])
        expansion_method = config.get("keyword_expansion", {}).get("method", DEFAULT_METHODS[1])
        return (extraction_method, expansion_method)

    except Exception:
        # If anything goes wrong, use defaults
        return DEFAULT_METHODS


def determine_tier(args: argparse.Namespace, repo_path: Path | None = None) -> str:
    """Determine indexing tier from args or existing config.

    This is the main function for tier resolution. It:
    1. Checks command-line arguments first (--fast, --regular, --max)
    2. Falls back to reading from config.yaml if no args provided
    3. Defaults to "regular" if no config found

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes
        repo_path: Optional repository path to read config from

    Returns:
        Tier string: "fast", "regular", or "max"
    """
    # Check args first
    tier = get_tier_from_args(args)
    if tier is not None:
        return tier

    # If no tier flag specified, try to load from existing config
    if repo_path is not None:
        extraction_method, expansion_method = read_keyword_extraction_config(repo_path)
        return methods_to_tier(extraction_method, expansion_method)

    # Default to regular tier
    return "regular"


def get_extraction_expansion_methods(
    args: argparse.Namespace,
) -> tuple[str | None, str | None]:
    """Map tier flags to extraction and expansion methods.

    This is a convenience function for backward compatibility.
    Returns (None, None) if no tier flag is specified, allowing callers
    to distinguish between "no tier specified" and "default tier".

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Returns:
        Tuple of (extraction_method, expansion_method), or (None, None) if no tier flag
    """
    tier = get_tier_from_args(args)
    if tier is None:
        return None, None
    return tier_to_methods(tier)
