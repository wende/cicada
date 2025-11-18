"""
Shared extractors for keyword extraction and signature analysis.

This package contains language-agnostic extractors that can be used by any indexer.
"""

# Import language-specific extractors to register them
from . import (
    elixir_signature,  # noqa: F401
    python_signature,  # noqa: F401
)
from .base_signature import FunctionSignatureExtractor, SignatureExtractorRegistry
from .keybert import KeyBERTExtractor
from .keyword import BaseKeywordExtractor, RegularKeywordExtractor

__all__ = [
    "BaseKeywordExtractor",
    "FunctionSignatureExtractor",
    "KeyBERTExtractor",
    "RegularKeywordExtractor",
    "SignatureExtractorRegistry",
]
