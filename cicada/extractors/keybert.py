"""
Keyword Extraction using KeyBERT
Semantic keyword extraction using transformer-based embeddings
"""

import os
import re
import sys
from collections import Counter
from typing import Any

# Disable tokenizers parallelism to avoid fork warnings
# Must be set before importing transformers/keybert
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from cicada.extractors.keyword import BaseKeywordExtractor
from cicada.utils import extract_code_identifiers


class KeyBERTExtractor(BaseKeywordExtractor):
    """Extract keywords from text using KeyBERT semantic analysis."""

    # Single model configuration
    MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 133MB, balanced performance

    # Weighting strategy constants for keyword extraction
    KEYBERT_CANDIDATE_MULTIPLIER = 3  # Extract 3x keywords for weighted reranking
    CODE_IDENTIFIER_BOOST = 10  # 10x weight for exact code identifiers
    CODE_SPLIT_WORD_BOOST = 3  # 3x weight for identifier components
    BASE_SCORE_IDENTIFIER = 0.5  # Base score for identifiers not found by BERT
    BASE_SCORE_SPLIT_WORD = 0.3  # Base score for split words not found by BERT

    # Class variable to hold KeyBERT class (lazily loaded)
    _KeyBERT: type | None = None

    def __init__(self, verbose: bool = False):
        super().__init__(verbose)
        self.verbose = verbose

        # Print message BEFORE the slow import
        if self.verbose:
            print(
                f"Loading KeyBERT model ({self.MODEL_NAME})",
                file=sys.stderr,
            )
            print("This can take up to a couple of minutes.", file=sys.stderr)

        # Lazy import KeyBERT (only once per class)
        if KeyBERTExtractor._KeyBERT is None:
            try:
                from keybert import KeyBERT

                KeyBERTExtractor._KeyBERT = KeyBERT
            except ImportError as e:
                raise ImportError(
                    "KeyBERT is not installed. Install it with:\n"
                    "  uv add keybert\n"
                    "or\n"
                    "  pip install keybert"
                ) from e

        # Initialize KeyBERT with the model
        try:
            self.kw_model = KeyBERTExtractor._KeyBERT(model=self.MODEL_NAME)
            if self.verbose:
                print("✓ Model loaded successfully", file=sys.stderr)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load KeyBERT model '{self.MODEL_NAME}'. "
                f"Ensure the model is downloaded and available. Error: {e}"
            ) from e

    def _calculate_term_frequencies(self, text: str) -> dict[str, int]:
        """Calculate term frequencies for all words in the text.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary mapping lowercase words to their raw frequency counts
        """
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]*\b", text.lower())
        term_freq = Counter(tokens)
        return dict(term_freq)

    def _apply_code_boosting(
        self,
        keyword_scores: dict[str, float],
        code_identifiers: list[str],
        code_split_words: list[str],
        tf_scores: dict[str, int],
    ) -> None:
        """Apply boosting to code identifiers and split words in-place.

        Args:
            keyword_scores: Dictionary of keyword scores to modify in-place
            code_identifiers: List of code identifiers to boost
            code_split_words: List of split words from identifiers to boost
            tf_scores: Term frequency scores for calculating base scores
        """
        # Apply code identifier boosting
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        for identifier in code_identifiers_lower:
            if identifier in keyword_scores:
                keyword_scores[identifier] *= self.CODE_IDENTIFIER_BOOST
            else:
                # Add with base score × frequency if not found by KeyBERT
                freq = tf_scores.get(identifier, 1)
                keyword_scores[identifier] = (
                    self.BASE_SCORE_IDENTIFIER * freq * self.CODE_IDENTIFIER_BOOST
                )

        # Apply split word boosting (but only if not already a code identifier)
        code_split_words_lower = [word.lower() for word in code_split_words]
        code_identifiers_set = set(code_identifiers_lower)  # For O(1) lookup
        for word in code_split_words_lower:
            # Skip words that are already code identifiers (avoid double-boosting)
            if word in code_identifiers_set:
                continue
            if word in keyword_scores:
                keyword_scores[word] *= self.CODE_SPLIT_WORD_BOOST
            else:
                freq = tf_scores.get(word, 1)
                keyword_scores[word] = (
                    self.BASE_SCORE_SPLIT_WORD * freq * self.CODE_SPLIT_WORD_BOOST
                )

    def _calculate_statistics(self, text: str) -> dict[str, int]:
        """Calculate basic text statistics.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary with basic statistics (total_tokens, total_words, unique_words, sentences)
        """
        words = text.split()
        unique_words = {w.lower() for w in words if w.isalpha()}
        sentences = text.count(".") + text.count("!") + text.count("?")

        return {
            "total_tokens": len(words),
            "total_words": len([w for w in words if w.isalpha()]),
            "unique_words": len(unique_words),
            "sentences": max(1, sentences),
        }

    def extract_keywords(
        self, text: str, top_n: int = 15, min_score: float = 0.0
    ) -> dict[str, Any]:
        """
        Extract keywords using KeyBERT semantic analysis with code identifier emphasis and frequency weighting.

        Weighting strategy:
        - Semantic score × raw frequency (repetition increases score, document length doesn't matter)
        - Full code identifiers (e.g., getUserData, snake_case): 10x weight
        - Code split words (e.g., get, user, data): 3x weight

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return
            min_score: Minimum score threshold for keywords (filters out low-scoring terms)

        Returns:
            Dictionary with extracted keywords and analysis:
            - top_keywords: List of (keyword, score) tuples, sorted by weighted score
            - code_identifiers: Original identifiers (weighted 10x)
            - code_split_words: Words extracted from identifiers (weighted 3x)
            - stats: Basic text statistics
        """
        if not text or not text.strip():
            return {
                "top_keywords": [],
                "code_identifiers": [],
                "code_split_words": [],
                "tf_scores": {},
                "stats": {
                    "total_tokens": 0,
                    "total_words": 0,
                    "unique_words": 0,
                    "sentences": 0,
                },
            }

        # 1. Extract code identifiers and their split words
        code_identifiers, code_split_words = extract_code_identifiers(text)

        # 2. Calculate term frequencies for all words (raw counts, not normalized)
        tf_scores = self._calculate_term_frequencies(text)

        # 3. Use KeyBERT to extract semantic keywords
        try:
            keybert_keywords: list[tuple[str, float]] = self.kw_model.extract_keywords(  # type: ignore[assignment]
                text,
                top_n=top_n * self.KEYBERT_CANDIDATE_MULTIPLIER,
                keyphrase_ngram_range=(1, 1),  # Single words only
            )
        except Exception as e:
            if self.verbose:
                print(f"Warning: KeyBERT extraction failed: {e}", file=sys.stderr)
            keybert_keywords = []

        # 4. Build weighted keyword scores (semantic × frequency)
        keyword_scores: dict[str, float] = {}

        # Add KeyBERT keywords with semantic score × frequency
        for keyword, semantic_score in keybert_keywords:
            keyword_lower: str = keyword.lower()
            freq = tf_scores.get(keyword_lower, 1)  # Default frequency of 1
            keyword_scores[keyword_lower] = semantic_score * freq

        # 5. Apply code identifier and split word boosting
        self._apply_code_boosting(keyword_scores, code_identifiers, code_split_words, tf_scores)

        # 6. Filter by minimum score threshold and sort by weighted score
        filtered_scores = {k: v for k, v in keyword_scores.items() if v >= min_score}
        top_keywords = sorted(filtered_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # 7. Calculate basic statistics
        stats = self._calculate_statistics(text)

        return {
            "top_keywords": top_keywords,
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": tf_scores,
            "stats": stats,
        }
