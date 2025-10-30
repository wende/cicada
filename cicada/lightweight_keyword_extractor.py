"""
Lightweight Keyword Extraction using lemminflect
Fast keyword extraction for programming documentation without heavy NLP dependencies
"""

from collections import Counter
import re
import sys

from cicada.utils import split_camel_snake_case


class LightweightKeywordExtractor:
    """Extract keywords from text using lightweight lemmatization."""

    # Minimal stopword list covering most common English words
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

    def __init__(self, verbose: bool = False, model_size: str = "small"):
        """
        Initialize lightweight keyword extractor.

        Args:
            verbose: If True, print status messages during initialization
            model_size: Ignored for compatibility with KeywordExtractor API
        """
        self.verbose = verbose
        self.model_size = model_size
        self._lemminflect_loaded = False

    def _load_lemminflect(self):
        """Lazy load lemminflect on first use."""
        if self._lemminflect_loaded:
            return

        try:
            import lemminflect

            self._lemminflect = lemminflect
            self._lemminflect_loaded = True
            if self.verbose:
                print("✓ lemminflect loaded", file=sys.stderr)
        except ImportError as e:
            raise RuntimeError(
                "lemminflect is required but not installed. "
                "Please install it with: uv pip install lemminflect"
            ) from e

    def _tokenize(self, text: str) -> list[str]:
        """
        Simple regex-based tokenization.

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens (words)
        """
        # Split on whitespace and punctuation, keep alphanumeric + underscores
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]*\b", text)
        return tokens

    def _lemmatize(self, word: str) -> str:
        """
        Lemmatize a single word using lemminflect.

        Args:
            word: Word to lemmatize

        Returns:
            Lemmatized form of the word
        """
        # Try to get lemma (try VERB first, then NOUN as fallback)
        lemma = self._lemminflect.getLemma(word, upos="VERB")
        if not lemma:
            lemma = self._lemminflect.getLemma(word, upos="NOUN")

        if lemma:
            return lemma[0].lower()
        return word.lower()

    def extract_code_identifiers(self, text):
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
                word.lower()
                for word in split_text.split()
                if len(word) > 1 and word.isalpha()
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

    def extract_keywords(self, text, top_n=15):
        """
        Extract keywords using multiple strategies with emphasis on code identifiers.

        Weighting strategy:
        - Full code identifiers (e.g., getUserData, snake_case): 10x weight (exact match priority)
        - Code split words (e.g., get, user, data): 3x weight (fuzzy match support)
        - Regular words (lemmatized): 1x weight

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary with extracted keywords and analysis:
            - top_keywords: List of (keyword, count) tuples, sorted by frequency
            - code_identifiers: Original identifiers (weighted 10x)
            - code_split_words: Words extracted from identifiers (weighted 3x)
            - lemmatized_words: Lemmatized regular words
            - tf_scores: Term frequency scores
            - stats: Text statistics
        """
        if not text or not text.strip():
            return {
                "top_keywords": [],
                "lemmatized_words": [],
                "code_identifiers": [],
                "code_split_words": [],
                "tf_scores": {},
                "stats": {
                    "total_tokens": 0,
                    "total_words": 0,
                    "unique_words": 0,
                },
            }

        # Lazy load lemminflect
        self._load_lemminflect()

        # 1. Extract code identifiers and their split words (MOST IMPORTANT)
        code_identifiers, code_split_words = self.extract_code_identifiers(text)

        # 2. Tokenize text
        tokens = self._tokenize(text)

        # 3. Lemmatize and filter stopwords/short words
        lemmatized_words = []
        for word in tokens:
            word_lower = word.lower()
            if len(word) > 2 and word_lower not in self.STOPWORDS:
                lemma = self._lemmatize(word)
                lemmatized_words.append(lemma)

        # 4. Calculate keyword frequency with weighting
        # Give full code identifiers 10x weight for exact matching
        # Give code split words 3x weight for fuzzy matching
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        all_keywords = (
            lemmatized_words + (code_identifiers_lower * 10) + (code_split_words * 3)
        )
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(top_n)

        # 5. Calculate TF scores (simple version)
        total_words = len(lemmatized_words)
        if total_words > 0:
            tf_scores = {
                word: (freq / total_words) for word, freq in keyword_freq.items()
            }
        else:
            tf_scores = {}

        # Statistics
        stats = {
            "total_tokens": len(tokens),
            "total_words": total_words,
            "unique_words": len(set(lemmatized_words)),
        }

        return {
            "top_keywords": top_keywords,
            "lemmatized_words": list(set(lemmatized_words))[:20],
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": dict(
                sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "stats": stats,
        }
