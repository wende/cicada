"""
Lightweight Keyword Extraction using lemminflect
Fast keyword extraction for programming documentation
"""

from collections import Counter
import re
import sys
import warnings

from cicada.utils import split_camel_snake_case


class LightweightKeywordExtractor:
    """Extract keywords from text using lightweight lemmatization."""

    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "this", "that", "these", "those", "it",
        "its", "they", "them", "their", "what", "which", "who", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "can", "just", "up", "out",
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

    def __init__(self, verbose: bool = False, model_size: str = "small"):
        """
        Initialize lightweight keyword extractor.

        Args:
            verbose: If True, print status messages during initialization
            model_size: Deprecated parameter kept for backward compatibility.
                       This parameter is ignored in the lightweight extractor.
        """
        self.verbose = verbose
        self.model_size = model_size
        self._lemminflect_loaded = False

        # Deprecation warning for model_size parameter
        if model_size != "small":
            warnings.warn(
                "The 'model_size' parameter is deprecated and ignored in LightweightKeywordExtractor. "
                "The lightweight extractor does not use size-based models.",
                DeprecationWarning,
                stacklevel=2
            )

    def _load_lemminflect(self):
        """Lazy load lemminflect library."""
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
        """Tokenize text into words."""
        tokens = self.TOKEN_PATTERN.findall(text)
        return tokens

    def _lemmatize(self, word: str) -> str:
        """
        Lemmatize a word using lemminflect with fallback.

        Tries lemmatization with VERB, NOUN, and ADJ POS tags.
        Falls back to lowercase if lemmatization fails.

        Args:
            word: Word to lemmatize

        Returns:
            Lemmatized word (lowercase)
        """
        try:
            # Try different POS tags for better coverage
            for pos in ["VERB", "NOUN", "ADJ"]:
                lemma = self._lemminflect.getLemma(word, upos=pos)
                if lemma:
                    return lemma[0].lower()
            # Fallback to lowercase if no lemma found
            return word.lower()
        except Exception:
            # Graceful fallback if lemminflect fails
            return word.lower()

    def extract_code_identifiers(self, text):
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
        - Regular lemmatized words: 1x weight

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary with extracted keywords and analysis:
            - top_keywords: List of (keyword, count) tuples, sorted by frequency
            - lemmatized_words: Regular words after lemmatization
            - code_identifiers: Original identifiers (weighted 10x)
            - code_split_words: Words extracted from identifiers (weighted 3x)
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

        self._load_lemminflect()
        code_identifiers, code_split_words = self.extract_code_identifiers(text)
        tokens = self._tokenize(text)
        lemmatized_words = []
        for word in tokens:
            word_lower = word.lower()
            if len(word) > 2 and word_lower not in self.STOPWORDS:
                lemma = self._lemmatize(word)
                lemmatized_words.append(lemma)

        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        all_keywords = (
            lemmatized_words + (code_identifiers_lower * 10) + (code_split_words * 3)
        )
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(top_n)

        # Fix: Calculate TF scores based on all keywords, not just lemmatized_words
        # This ensures weighted keywords are included in the calculation
        total_words = len(all_keywords)
        if total_words > 0:
            tf_scores = {
                word: (freq / total_words) for word, freq in keyword_freq.items()
            }
        else:
            tf_scores = {}

        stats = {
            "total_tokens": len(tokens),
            "total_words": len(lemmatized_words),
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
