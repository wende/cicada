"""
Keyword Extraction using KeyBERT
Semantic keyword extraction using transformer-based embeddings
"""

import os
import sys
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

    def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
        """
        Extract keywords using KeyBERT semantic analysis with code identifier emphasis.

        Weighting strategy:
        - Full code identifiers (e.g., getUserData, snake_case): 10x weight
        - Code split words (e.g., get, user, data): 3x weight
        - KeyBERT semantic keywords: Base score from embedding similarity

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

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

        # 2. Use KeyBERT to extract semantic keywords
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

        # 3. Build weighted keyword scores
        keyword_scores: dict[str, float] = {}

        # Add KeyBERT keywords with their semantic similarity scores
        for keyword, score in keybert_keywords:
            keyword_lower: str = keyword.lower()
            keyword_scores[keyword_lower] = score

        # 4. Apply code identifier boosting
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        for identifier in code_identifiers_lower:
            if identifier in keyword_scores:
                keyword_scores[identifier] *= self.CODE_IDENTIFIER_BOOST
            else:
                # Add with high base score if not found by KeyBERT
                keyword_scores[identifier] = self.BASE_SCORE_IDENTIFIER * self.CODE_IDENTIFIER_BOOST

        # 5. Apply split word boosting
        code_split_words_lower = [word.lower() for word in code_split_words]
        for word in code_split_words_lower:
            if word in keyword_scores:
                keyword_scores[word] *= self.CODE_SPLIT_WORD_BOOST
            else:
                keyword_scores[word] = self.BASE_SCORE_SPLIT_WORD * self.CODE_SPLIT_WORD_BOOST

        # 6. Sort by weighted score and take top_n
        top_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # 7. Calculate basic statistics
        words = text.split()
        unique_words = {w.lower() for w in words if w.isalpha()}
        sentences = text.count(".") + text.count("!") + text.count("?")

        stats = {
            "total_tokens": len(words),
            "total_words": len([w for w in words if w.isalpha()]),
            "unique_words": len(unique_words),
            "sentences": max(1, sentences),
        }

        return {
            "top_keywords": top_keywords,
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": {},  # Using semantic scores instead
            "stats": stats,
        }
