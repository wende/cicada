"""Base keyword extraction classes.

Provides term frequency based keyword extraction that works on any text.
"""

import sys
from collections import Counter
from typing import Any

from cicada.utils import extract_code_identifiers as util_extract_code_identifiers


class BaseKeywordExtractor:
    """Base class for keyword extraction."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.STOPWORDS = {
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

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        import re

        return re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]*\b", text)

    def extract_keywords_simple(self, text: str, top_n: int = 10) -> list[str]:
        if not text or not text.strip():
            return []
        try:
            results = self.extract_keywords(text, top_n=top_n)
            return [keyword for keyword, _ in results["top_keywords"]]
        except Exception as e:
            if self.verbose:
                print(f"Warning: Keyword extraction failed: {e}", file=sys.stderr)
            return []

    def _extract_keywords(
        self,
        words: list[str],
        code_identifiers: list[str],
        code_split_words: list[str],
        top_n: int,
        total_tokens: int,
    ) -> tuple[list, dict, dict]:
        """Extract keywords from a list of words.

        Args:
            words: Filtered words (after stopword removal)
            code_identifiers: Extracted code identifiers
            code_split_words: Words split from code identifiers
            top_n: Number of top keywords to return
            total_tokens: Total token count before filtering (for stats)
        """
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        all_keywords = words + (code_identifiers_lower * 10) + (code_split_words * 3)
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(top_n)

        total_words = len(all_keywords)
        if total_words > 0:
            tf_scores = {word: (freq / total_words) for word, freq in keyword_freq.items()}
        else:
            tf_scores = {}

        stats = {
            "total_tokens": total_tokens,
            "total_words": len(words),
            "unique_words": len(set(words)),
        }

        return top_keywords, tf_scores, stats

    def extract_keywords(
        self, text: str, top_n: int = 15, min_score: float = 0.0
    ) -> dict[str, Any]:
        raise NotImplementedError


class RegularKeywordExtractor(BaseKeywordExtractor):
    """Extract keywords using basic term frequency (TF) without lemmatization."""

    def extract_keywords(
        self, text: str, top_n: int = 15, min_score: float = 0.0
    ) -> dict[str, Any]:
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

        code_identifiers, code_split_words = util_extract_code_identifiers(text)
        tokens = self._tokenize(text)
        total_tokens = len(tokens)
        regular_words = []
        for word in tokens:
            word_lower = word.lower()
            if len(word) > 2 and word_lower not in self.STOPWORDS:
                regular_words.append(word_lower)

        top_keywords, tf_scores, stats = self._extract_keywords(
            regular_words, code_identifiers, code_split_words, top_n, total_tokens
        )

        # Filter by minimum score threshold (min_score is a frequency count for RegularKeywordExtractor)
        filtered_keywords = [(word, score) for word, score in top_keywords if score >= min_score]

        return {
            "top_keywords": filtered_keywords,
            "regular_words": list(set(regular_words))[:20],
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": dict(sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
            "stats": stats,
        }
