"""
Keyword Extraction using KeyBERT
Semantic keyword extraction using transformer-based embeddings
"""

import re
import sys
from typing import Any

from cicada.utils import split_camel_snake_case


class KeyBERTExtractor:
    """Extract keywords from text using KeyBERT semantic analysis."""

    # Model configurations for different performance tiers
    KEYBERT_MODELS = {
        "fast": "all-MiniLM-L6-v2",  # 80MB, fast extraction
        "regular": "BAAI/bge-small-en-v1.5",  # 133MB, balanced
        "max": "paraphrase-mpnet-base-v2",  # 420MB, highest quality
    }

    # Weighting strategy constants for keyword extraction
    # These control how different types of keywords are prioritized
    KEYBERT_CANDIDATE_MULTIPLIER = 3  # Extract 3x keywords for weighted reranking
    CODE_IDENTIFIER_BOOST = 10  # 10x weight for exact code identifiers (e.g., function names)
    CODE_SPLIT_WORD_BOOST = 3  # 3x weight for identifier components (e.g., "user" from "getUserId")
    BASE_SCORE_IDENTIFIER = 0.5  # Base score for identifiers not found by BERT
    BASE_SCORE_SPLIT_WORD = 0.3  # Base score for split words not found by BERT

    # Class variable to hold KeyBERT class (lazily loaded)
    _KeyBERT: type | None = None

    def __init__(self, verbose: bool = False, model_tier: str | None = None):
        """
        Initialize KeyBERT model.

        Args:
            verbose: If True, print status messages during initialization
            model_tier: Model tier to use ('fast', 'regular', or 'max').
                       If None, must be specified via config file.

        Raises:
            ImportError: If KeyBERT is not installed
            ValueError: If model_tier is invalid or not specified
            RuntimeError: If model loading fails
        """
        self.verbose = verbose

        # Validate model tier first
        if model_tier and model_tier not in self.KEYBERT_MODELS:
            raise ValueError(
                f"Invalid model tier '{model_tier}'. "
                f"Must be one of: {', '.join(self.KEYBERT_MODELS.keys())}"
            )

        if model_tier is None:
            raise ValueError(
                "model_tier must be specified. Pass it directly or load from config file."
            )

        self.model_tier = model_tier
        self.model_name = self.KEYBERT_MODELS[model_tier]

        # Print message BEFORE the slow import
        if self.verbose:
            print(
                f"Loading KeyBERT model ({model_tier}: {self.model_name})",
                file=sys.stderr,
            )
            print("This can take up to a couple of minutes.", file=sys.stderr)

        # Lazy import KeyBERT (only once per class)
        # This import can take significant time on first load
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

        # Initialize KeyBERT with the selected model
        # Assume model is pre-downloaded (user will handle caching separately)
        try:
            self.kw_model = KeyBERTExtractor._KeyBERT(model=self.model_name)
            if self.verbose:
                print("✓ Model loaded successfully", file=sys.stderr)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load KeyBERT model '{self.model_name}'. "
                f"Ensure the model is downloaded and available. Error: {e}"
            ) from e

    def extract_code_identifiers(self, text: str) -> tuple[list[str], list[str]]:
        """
        Extract code-specific identifiers and their split words.

        Returns a tuple of (identifiers, split_words) where:
        - identifiers: original camelCase/PascalCase/snake_case identifiers
        - split_words: individual words extracted from those identifiers
        """
        # Match camelCase, snake_case, PascalCase, and mixed patterns
        patterns = [
            r"\b[a-z]+[A-Z][a-zA-Z]*\b",  # camelCase (e.g., getUserData)
            r"\b[A-Z]{2,}[a-z]+[a-zA-Z]*\b",  # Uppercase prefix + PascalCase (e.g., HTTPServer, XMLParser)
            r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b",  # PascalCase (e.g., UserController, PostgreSQL)
            r"\b[a-z]+_[a-z_]+\b",  # snake_case (e.g., get_user_data)
            r"\b[A-Z]{2,}\b",  # All UPPERCASE (e.g., HTTP, API, SQL)
        ]

        identifiers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            identifiers.extend(matches)

        identifiers = list(set(identifiers))

        # Split identifiers into individual words
        split_words = []
        for identifier in identifiers:
            split_text = split_camel_snake_case(identifier)
            # Extract individual words (lowercase, length > 1)
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
            # Extract just the keyword strings from top_keywords tuples
            return [keyword for keyword, _ in results["top_keywords"]]
        except Exception as e:
            if self.verbose:
                print(f"Warning: Keyword extraction failed: {e}", file=sys.stderr)
            return []

    def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
        """
        Extract keywords using KeyBERT semantic analysis with code identifier emphasis.

        Weighting strategy:
        - Full code identifiers (e.g., getUserData, snake_case): 10x weight (exact match priority)
        - Code split words (e.g., get, user, data): 3x weight (fuzzy match support)
        - KeyBERT semantic keywords: Base score from embedding similarity

        Magic numbers explained:
        - 3x multiplier: For candidate selection (top_n * 3) to have enough keywords
          before applying weights. This ensures we don't miss important keywords that
          might rank higher after code identifier boosting.
        - 0.5 base score: Default confidence for code identifiers not found by KeyBERT.
          After 10x boost, gives them a score of 5.0, prioritizing them over most
          regular keywords.
        - 0.3 base score: Default confidence for code split words not found by KeyBERT.
          After 3x boost, gives them a score of 0.9, placing them between regular
          keywords (0.4-0.7) and full identifiers (5.0).

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary with extracted keywords and analysis:
            - top_keywords: List of (keyword, score) tuples, sorted by weighted score
            - code_identifiers: Original identifiers (weighted 10x)
            - code_split_words: Words extracted from identifiers (weighted 3x)
            - noun_chunks: 2-word phrases from KeyBERT (if any)
            - Other fields (nouns, verbs, etc.) are empty (KeyBERT doesn't do POS tagging)
            - stats: Basic text statistics
        """
        if not text or not text.strip():
            return {
                "top_keywords": [],
                "nouns": [],
                "verbs": [],
                "adjectives": [],
                "proper_nouns": [],
                "noun_chunks": [],
                "entities": [],
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
        code_identifiers, code_split_words = self.extract_code_identifiers(text)

        # 2. Use KeyBERT to extract semantic keywords
        # Extract more than needed to have candidates for weighting
        try:
            # KeyBERT return type can vary, use type ignore for external library
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
        # Code identifiers get strong boost as they're likely important API/function names
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        for identifier in code_identifiers_lower:
            if identifier in keyword_scores:
                keyword_scores[identifier] *= self.CODE_IDENTIFIER_BOOST
            else:
                # Add with high base score if not found by KeyBERT
                keyword_scores[identifier] = self.BASE_SCORE_IDENTIFIER * self.CODE_IDENTIFIER_BOOST

        # 5. Apply split word boosting (lower than full identifiers)
        # Split words are components of identifiers, somewhat important but less than full names
        code_split_words_lower = [word.lower() for word in code_split_words]
        for word in code_split_words_lower:
            if word in keyword_scores:
                keyword_scores[word] *= self.CODE_SPLIT_WORD_BOOST
            else:
                keyword_scores[word] = self.BASE_SCORE_SPLIT_WORD * self.CODE_SPLIT_WORD_BOOST

        # 5. Sort by weighted score and take top_n
        top_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # 6. No noun_chunks since we're using single words only
        noun_chunks = []

        # 7. Calculate basic statistics
        words = text.split()
        unique_words = {w.lower() for w in words if w.isalpha()}
        sentences = text.count(".") + text.count("!") + text.count("?")

        stats = {
            "total_tokens": len(words),
            "total_words": len([w for w in words if w.isalpha()]),
            "unique_words": len(unique_words),
            "sentences": max(1, sentences),  # At least 1 sentence
        }

        return {
            "top_keywords": top_keywords,
            "nouns": [],  # KeyBERT doesn't extract POS tags
            "verbs": [],
            "adjectives": [],
            "proper_nouns": [],
            "noun_chunks": noun_chunks,
            "entities": [],  # KeyBERT doesn't do NER
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": {},  # Using semantic scores instead
            "stats": stats,
        }
