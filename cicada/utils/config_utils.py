"""
Configuration utility functions.

Centralized functions for reading and parsing Cicada configuration files.
"""

from pathlib import Path

from cicada.utils.storage import get_config_path


def read_keyword_extraction_config(repo_path: Path) -> tuple[str, str]:
    """
    Read keyword extraction configuration from config.yaml.

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
            extraction_method = config.get("keyword_extraction", {}).get("method", "regular")
            expansion_method = config.get("keyword_expansion", {}).get("method", "lemmi")
            return (extraction_method, expansion_method)

        # Default to regular + lemmi if config sections not found
        return ("regular", "lemmi")
    except Exception:
        # If anything goes wrong, default to regular + lemmi
        return ("regular", "lemmi")
