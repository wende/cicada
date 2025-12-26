"""
Indexing Mode Configuration Module.

Provides a single source of truth for:
- Mode validation (keywords, embeddings)
- Mode resolution from arguments or config files
- Config compatibility with legacy keyword_extraction settings
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

INDEX_MODE_KEYWORDS = "keywords"
INDEX_MODE_EMBEDDINGS = "embeddings"
INDEX_MODE_OPTIONS = (INDEX_MODE_KEYWORDS, INDEX_MODE_EMBEDDINGS)


def validate_mode_flags(args: argparse.Namespace, *, require_force: bool = False) -> None:
    """Validate that only one indexing mode flag is specified.

    Args:
        args: Parsed command-line arguments with keywords/embeddings attributes
        require_force: Whether --force is required when specifying mode flags

    Raises:
        SystemExit: If validation fails
    """
    keywords_flag = bool(getattr(args, "keywords", False))
    embeddings_flag = bool(getattr(args, "embeddings", False))
    mode_count = int(keywords_flag) + int(embeddings_flag)

    if mode_count > 1:
        print(
            "Error: Can only specify one mode flag (--keywords or --embeddings).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not require_force:
        return

    force_enabled = getattr(args, "force", False) is True
    mode_specified = mode_count == 1

    if force_enabled and not mode_specified:
        print(
            "Error: --force requires specifying a mode flag (--keywords or --embeddings).",
            file=sys.stderr,
        )
        sys.exit(2)

    if mode_specified and not force_enabled:
        print(
            "Error: Mode flags now require --force to override the configured mode.",
            file=sys.stderr,
        )
        print(
            "Run 'cicada index --force --keywords|--embeddings' to select a mode.",
            file=sys.stderr,
        )
        sys.exit(2)


def mode_flag_specified(args: argparse.Namespace) -> bool:
    """Return True when any mode flag is present."""
    return bool(getattr(args, "keywords", False) or getattr(args, "embeddings", False))


def get_mode_from_args(args: argparse.Namespace) -> str | None:
    """Extract mode from command-line arguments."""
    if getattr(args, "keywords", False):
        return INDEX_MODE_KEYWORDS
    if getattr(args, "embeddings", False):
        return INDEX_MODE_EMBEDDINGS
    return None


def read_indexing_mode_config(repo_path: Path) -> str:
    """Read indexing mode configuration from config.yaml.

    Args:
        repo_path: Path to the repository

    Returns:
        Mode string ("keywords" or "embeddings"). Defaults to "keywords".
    """
    try:
        import yaml

        from cicada.utils.storage import get_config_path

        config_path = get_config_path(repo_path)
        if not config_path.exists():
            return INDEX_MODE_KEYWORDS

        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

        mode = config.get("indexing", {}).get("mode")
        if mode in INDEX_MODE_OPTIONS:
            return mode

        # Legacy configs used keyword_extraction/keyword_expansion; treat as keywords.
        if config.get("keyword_extraction") or config.get("keyword_expansion"):
            return INDEX_MODE_KEYWORDS

        return INDEX_MODE_KEYWORDS
    except Exception:
        return INDEX_MODE_KEYWORDS


def determine_indexing_mode(args: argparse.Namespace, repo_path: Path | None = None) -> str:
    """Determine indexing mode from args or existing config."""
    mode = get_mode_from_args(args)
    if mode is not None:
        return mode

    if repo_path is not None:
        return read_indexing_mode_config(repo_path)

    return INDEX_MODE_KEYWORDS


def ensure_supported_mode(mode: str) -> None:
    """Validate that the requested mode is supported."""
    if mode not in INDEX_MODE_OPTIONS:
        raise ValueError(f"Invalid indexing mode: {mode}. Use 'keywords' or 'embeddings'.")
