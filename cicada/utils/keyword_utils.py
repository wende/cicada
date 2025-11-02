"""Universal keyword extraction utilities.

This module provides language-agnostic keyword extraction initialization
that can be used by any indexer (Elixir, Python, TypeScript, etc.).
"""

import sys
from pathlib import Path

from cicada.utils.storage import get_config_path


def read_keyword_extraction_config(repo_path: Path) -> tuple[str, str]:
    """
    Read keyword extraction configuration from config.yaml.

    Args:
        repo_path: Path to the repository

    Returns:
        tuple[str, str]: (method, tier) where method is 'lemminflect' or 'bert',
                        and tier is 'fast', 'regular', or 'max'.
                        Returns ('lemminflect', 'regular') as default if config not found.
    """
    try:
        import yaml

        config_path = get_config_path(repo_path)
        if not config_path.exists():
            # Default to lemminflect if config doesn't exist
            return ("lemminflect", "regular")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if config and "keyword_extraction" in config:
            method = config["keyword_extraction"].get("method", "lemminflect")
            tier = config["keyword_extraction"].get("tier", "regular")
            return (method, tier)

        # Default to lemminflect if keyword_extraction section not found
        return ("lemminflect", "regular")
    except Exception:
        # If anything goes wrong, default to lemminflect
        return ("lemminflect", "regular")


def create_keyword_extractor(method: str, tier: str, verbose: bool = False):
    """
    Create a keyword extractor instance based on method and tier.

    This is a universal factory function that works for any language indexer.

    Args:
        method: Extraction method ('lemminflect', 'bert', or 'none')
        tier: Model tier ('fast', 'regular', or 'max')
        verbose: If True, print status messages

    Returns:
        Keyword extractor instance (LightweightKeywordExtractor or KeyBERTExtractor),
        or None if method is 'none'

    Example:
        method, tier = read_keyword_extraction_config(repo_path)
        extractor = create_keyword_extractor(method, tier, verbose=True)
        if extractor:
            keywords = extractor.extract_keywords_simple(text)
    """
    if method == "none":
        return None

    if method == "bert":
        try:
            from cicada.keybert_extractor import KeyBERTExtractor

            if verbose:
                print(f"  Using KeyBERT extractor ({tier} tier)", file=sys.stderr)
            return KeyBERTExtractor(model_tier=tier, verbose=verbose)
        except ImportError:
            if verbose:
                print(
                    "  Warning: KeyBERT not available, falling back to lemminflect",
                    file=sys.stderr,
                )
            # Fall through to lemminflect

    # Default: lemminflect (fast, lightweight, no external dependencies)
    from cicada.lightweight_keyword_extractor import LightweightKeywordExtractor

    if verbose:
        print(f"  Using lightweight extractor (lemminflect)", file=sys.stderr)
    return LightweightKeywordExtractor(verbose=verbose)


def get_keyword_extractor_from_config(repo_path: Path, verbose: bool = False):
    """
    Convenience function to read config and create extractor in one call.

    Args:
        repo_path: Path to the repository
        verbose: If True, print status messages

    Returns:
        tuple[bool, extractor]: (extract_keywords, keyword_extractor)
        - extract_keywords: True if extraction is enabled
        - keyword_extractor: Extractor instance or None

    Example:
        extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)
        if extract_keywords and extractor:
            keywords = extractor.extract_keywords_simple(text)
    """
    method, tier = read_keyword_extraction_config(repo_path)
    extract_keywords = method != "none"
    keyword_extractor = (
        create_keyword_extractor(method, tier, verbose) if extract_keywords else None
    )
    return extract_keywords, keyword_extractor
