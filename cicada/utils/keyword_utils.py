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

    Returns ("none", "none") for embeddings mode to skip keyword extraction,
    since embeddings are generated separately from the parsed index structure.
    """
    try:
        import yaml

        config_path = get_config_path(repo_path)
        if not config_path.exists():
            return ("regular", "lemmi")

        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

        mode = config.get("indexing", {}).get("mode")
        if mode == "embeddings":
            # Hybrid search: embeddings mode still needs keywords for combined results
            return ("regular", "lemmi")

        # Legacy configs used keyword_extraction/keyword_expansion; treat as keywords.
        if config.get("keyword_extraction") or config.get("keyword_expansion"):
            return ("regular", "lemmi")

        return ("regular", "lemmi")
    except Exception:
        return ("regular", "lemmi")


def create_keyword_extractor(extraction_method: str, expansion_method: str, verbose: bool = False):
    """
    Create a keyword extractor instance based on extraction and expansion methods.

    This is a universal factory function that works for any language indexer.

    Args:
        extraction_method: Extraction method ('regular' or 'none')
        expansion_method: Expansion method ('lemmi')
        verbose: If True, print status messages

    Returns:
        Keyword extractor instance (RegularKeywordExtractor),
        or None if extraction_method is 'none'

    Example:
        extraction_method, expansion_method = read_keyword_extraction_config(repo_path)
        extractor = create_keyword_extractor(extraction_method, expansion_method, verbose=True)
        if extractor:
            keywords = extractor.extract_keywords_simple(text)
    """
    if extraction_method == "none":
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
