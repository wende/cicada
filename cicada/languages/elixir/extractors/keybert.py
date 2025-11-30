"""Backward compatibility re-export from shared extractors.

KeyBERTExtractor has been moved to cicada.extractors for universal language support.
"""

# Re-export from new location for backward compatibility
from cicada.extractors.keybert import KeyBERTExtractor

__all__ = ["KeyBERTExtractor"]
