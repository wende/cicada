"""Backward compatibility re-export from shared extractors.

These classes have been moved to cicada.extractors for universal language support.
"""

# Re-export from new location for backward compatibility
from cicada.extractors.keyword import BaseKeywordExtractor, RegularKeywordExtractor

__all__ = ["BaseKeywordExtractor", "RegularKeywordExtractor"]
