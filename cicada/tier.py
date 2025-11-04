"""
Tier Configuration Module - Centralized tier resolution and conversion logic.

This module provides a single source of truth for:
- Tier validation (fast, regular, max)
- Tier resolution from arguments or config files
- Tier <-> (extraction_method, expansion_method) conversions
"""

import sys
from pathlib import Path


def validate_tier_flags(args) -> None:
    """Validate that only one tier flag is specified.

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Raises:
        SystemExit: If more than one tier flag is specified
    """
    tier_count = sum([args.fast, getattr(args, "regular", False), args.max])
    if tier_count > 1:
        print(
            "Error: Can only specify one tier flag (--fast, --regular, or --max)",
            file=sys.stderr,
        )
        sys.exit(1)


def get_tier_from_args(args) -> str | None:
    """Extract tier from command-line arguments.

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Returns:
        Tier string ("fast", "regular", or "max"), or None if no tier flag specified
    """
    if args.fast:
        return "fast"
    elif args.max:
        return "max"
    elif getattr(args, "regular", False):
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
    tier_map = {
        "fast": ("regular", "lemmi"),
        "regular": ("bert", "glove"),
        "max": ("bert", "fasttext"),
    }
    return tier_map.get(tier, ("regular", "lemmi"))


def methods_to_tier(extraction_method: str, expansion_method: str) -> str:
    """Convert (extraction_method, expansion_method) to tier.

    Args:
        extraction_method: 'regular' or 'bert'
        expansion_method: 'lemmi', 'glove', or 'fasttext'

    Returns:
        Tier string: "fast", "regular", or "max"
    """
    if extraction_method == "regular":
        return "fast"
    elif extraction_method == "bert":
        if expansion_method == "fasttext":
            return "max"
        else:  # glove or other
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
                        Returns ('regular', 'lemmi') as default if config not found.
    """
    try:
        import yaml

        from cicada.utils.storage import get_config_path

        config_path = get_config_path(repo_path)
        if not config_path.exists():
            # Default to regular + lemmi if config doesn't exist
            return ("regular", "lemmi")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if config:
            extraction_method = config.get("keyword_extraction", {}).get("method", "regular")
            expansion_method = config.get("keyword_expansion", {}).get("method", "lemmi")
            return (extraction_method, expansion_method)

        # Default to regular + lemmi if config sections not found
        return ("regular", "lemmi")
    except Exception:
        # If anything goes wrong, default to regular + lemmi
        return ("regular", "lemmi")


def determine_tier(args, repo_path: Path | None = None) -> str:
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


def get_extraction_expansion_methods(args) -> tuple[str | None, str | None]:
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
