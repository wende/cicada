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

    Supports both new and legacy config formats:
    - New: keyword_extraction: {method: 'regular'|'bert'}, keyword_expansion: {method: 'lemmi'|'glove'|'fasttext'}
    - Legacy: keyword_extraction: {method: 'lemminflect'|'bert', tier: 'fast'|'regular'|'max'}

    Legacy tier mapping to new format:
    - tier: 'fast'     → regular + lemmi
    - tier: 'regular'  → regular + glove
    - tier: 'max'      → bert + fasttext

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

        config_path = get_config_path(repo_path)
        if not config_path.exists():
            # Default to regular + lemmi if config doesn't exist
            return ("regular", "lemmi")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if config:
            extraction = config.get("keyword_extraction", {})
            expansion = config.get("keyword_expansion", {})

            # Check for legacy tier-based config
            # Old CLI had: --fast, --regular, --max which mapped to (method, tier)
            tier = extraction.get("tier")
            if tier:
                # Legacy config uses tier to determine both extraction and expansion methods
                tier_mapping = {
                    "fast": ("regular", "lemmi"),
                    "regular": ("regular", "glove"),
                    "max": ("bert", "fasttext"),
                }
                if tier in tier_mapping:
                    return tier_mapping[tier]
                # If tier value is unrecognized, fall through to method-based logic

            # New config format or legacy method-based config (without tier)
            extraction_method = extraction.get("method", "regular")
            expansion_method = expansion.get("method", "lemmi")

            # Map legacy "lemminflect" method to "regular"
            if extraction_method == "lemminflect":
                extraction_method = "regular"

            return (extraction_method, expansion_method)

        # Default to regular + lemmi if config empty
        return ("regular", "lemmi")
    except Exception:
        # If anything goes wrong, default to regular + lemmi
        return ("regular", "lemmi")


def create_keyword_extractor(extraction_method: str, expansion_method: str, verbose: bool = False):
    """
    Create a keyword extractor instance based on extraction and expansion methods.

    This is a universal factory function that works for any language indexer.

    Args:
        extraction_method: Extraction method ('regular', 'bert', or 'none')
        expansion_method: Expansion method ('lemmi', 'glove', or 'fasttext')
        verbose: If True, print status messages

    Returns:
        Keyword extractor instance (RegularKeywordExtractor or KeyBERTExtractor),
        or None if extraction_method is 'none'

    Example:
        extraction_method, expansion_method = read_keyword_extraction_config(repo_path)
        extractor = create_keyword_extractor(extraction_method, expansion_method, verbose=True)
        if extractor:
            keywords = extractor.extract_keywords_simple(text)
    """
    if extraction_method == "none":
        return None

    if extraction_method == "bert":
        try:
            from cicada.extractors.keybert import KeyBERTExtractor

            if verbose:
                print("  Using KeyBERT extractor", file=sys.stderr)
            return KeyBERTExtractor(verbose=verbose)
        except ImportError:
            if verbose:
                print(
                    "  Warning: KeyBERT not available, falling back to regular",
                    file=sys.stderr,
                )
            # Fall through to regular extractor
        except Exception as e:
            if verbose:
                print(f"  Warning: Could not initialize keyword extractor: {e}")
                print("  Continuing without keyword extraction")
            return None

    # Default: regular (fast, lightweight, no external dependencies)
    from cicada.extractors.keyword import RegularKeywordExtractor

    if verbose:
        print("  Using regular extractor (lemminflect)", file=sys.stderr)
    return RegularKeywordExtractor(verbose=verbose)


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
    extraction_method, expansion_method = read_keyword_extraction_config(repo_path)
    extract_keywords = extraction_method != "none"
    keyword_extractor = (
        create_keyword_extractor(extraction_method, expansion_method, verbose)
        if extract_keywords
        else None
    )
    return extract_keywords, keyword_extractor
