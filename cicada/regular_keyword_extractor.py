"""
Regular (Basic) Keyword Extraction
Simple frequency-based keyword extraction without semantic analysis
"""

import re
import sys
from collections import Counter
from typing import Any

from cicada.utils import split_camel_snake_case


class RegularKeywordExtractor:
    """Extract keywords using basic term frequency (TF) without lemmatization."""

    STOPWORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "can",
        "just",
        "up",
        "out",
    }

    # Pre-compiled regex patterns for code identifier extraction
    CODE_PATTERNS = [
        re.compile(r"\b[a-z]+[A-Z][a-zA-Z]*\b"),  # camelCase
        re.compile(r"\b[A-Z]{2,}[a-z]+[a-zA-Z]*\b"),  # HTTPServer
        re.compile(r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b"),  # PascalCase
        re.compile(r"\b[a-z]+_[a-z_]+\b"),  # snake_case
        re.compile(r"\b[A-Z]{2,}\b"),  # UPPERCASE
    ]

    # Pre-compiled tokenization pattern
    TOKEN_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9_]*\b")

    def __init__(self, verbose: bool = False):
        """
        Initialize regular keyword extractor.

        Args:
            verbose: If True, print status messages
        """
        self.verbose = verbose

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        tokens = self.TOKEN_PATTERN.findall(text)
        return tokens

    def extract_code_identifiers(self, text: str) -> tuple[list[str], list[str]]:
        """
        Extract code-specific identifiers and their split words.

        Returns a tuple of (identifiers, split_words) where:
        - identifiers: original camelCase/PascalCase/snake_case identifiers
        - split_words: individual words extracted from those identifiers
        """
        identifiers = []
        for pattern in self.CODE_PATTERNS:
            matches = pattern.findall(text)
            identifiers.extend(matches)
        identifiers = list(set(identifiers))

        split_words = []
        for identifier in identifiers:
            split_text = split_camel_snake_case(identifier)
            words = [
                word.lower() for word in split_text.split() if len(word) > 1 and word.isalpha()
            ]
            split_words.extend(words)
        return identifiers, list(set(split_words))

    def extract_keywords_simple(self, text: str, top_n: int = 10) -> list[str]:
        """
        Extract keywords and return a simple list of keyword strings.

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            List of keyword strings (e.g., ['authentication', 'user', 'validate'])
        """
        if not text or not text.strip():
            return []
        try:
            results = self.extract_keywords(text, top_n=top_n)
            return [keyword for keyword, _ in results["top_keywords"]]
        except Exception as e:
            if self.verbose:
                print(f"Warning: Keyword extraction failed: {e}", file=sys.stderr)
            return []

    def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
        """
        Extract keywords using term frequency with code identifier emphasis.

        Weighting strategy:
        - Full code identifiers (e.g., getUserData, snake_case): 10x weight
        - Code split words (e.g., get, user, data): 3x weight
        - Regular words (lowercase, stopwords removed): 1x weight

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary with extracted keywords and analysis:
            - top_keywords: List of (keyword, count) tuples, sorted by frequency
            - regular_words: Lowercased words after stopword removal
            - code_identifiers: Original identifiers (weighted 10x)
            - code_split_words: Words extracted from identifiers (weighted 3x)
            - tf_scores: Term frequency scores
            - stats: Text statistics
        """
        if not text or not text.strip():
            return {
                "top_keywords": [],
                "regular_words": [],
                "code_identifiers": [],
                "code_split_words": [],
                "tf_scores": {},
                "stats": {
                    "total_tokens": 0,
                    "total_words": 0,
                    "unique_words": 0,
                },
            }

        # Extract code identifiers and split words
        code_identifiers, code_split_words = self.extract_code_identifiers(text)

        # Tokenize and filter regular words
        tokens = self._tokenize(text)
        regular_words = []
        for word in tokens:
            word_lower = word.lower()
            if len(word) > 2 and word_lower not in self.STOPWORDS:
                regular_words.append(word_lower)

        # Apply weighting: identifiers 10x, split words 3x, regular 1x
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        all_keywords = regular_words + (code_identifiers_lower * 10) + (code_split_words * 3)
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(top_n)

        # Calculate TF scores
        total_words = len(all_keywords)
        if total_words > 0:
            tf_scores = {word: (freq / total_words) for word, freq in keyword_freq.items()}
        else:
            tf_scores = {}

        stats = {
            "total_tokens": len(tokens),
            "total_words": len(regular_words),
            "unique_words": len(set(regular_words)),
        }

        return {
            "top_keywords": top_keywords,
            "regular_words": list(set(regular_words))[:20],
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": dict(sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
            "stats": stats,
        }
