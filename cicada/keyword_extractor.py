import re
import sys
import warnings
from collections import Counter
from typing import Any

from cicada.utils import split_camel_snake_case


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
        self.CODE_PATTERNS = [
            re.compile(r"\b[a-z]+[A-Z][a-zA-Z]*\b"),
            re.compile(r"\b[A-Z]{2,}[a-z]+[a-zA-Z]*\b"),
            re.compile(r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b"),
            re.compile(r"\b[a-z]+_[a-z_]+\b"),
            re.compile(r"\b[A-Z]{2,}\b"),
        ]
        self.TOKEN_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9_]*\b")

    def _tokenize(self, text: str) -> list[str]:
        return self.TOKEN_PATTERN.findall(text)

    def extract_code_identifiers(self, text: str) -> tuple[list[str], list[str]]:
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
        self, words: list[str], code_identifiers: list[str], code_split_words: list[str], top_n: int
    ) -> tuple[list, dict, dict]:
        """Extract keywords from a list of words."""
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
            "total_tokens": len(words),
            "total_words": len(words),
            "unique_words": len(set(words)),
        }

        return top_keywords, tf_scores, stats

    def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
        raise NotImplementedError


class LightweightKeywordExtractor(BaseKeywordExtractor):
    """Extract keywords from text using lightweight lemmatization."""

    def __init__(self, verbose: bool = False, model_size: str = "small"):
        super().__init__(verbose)
        self.model_size = model_size
        self._lemminflect_loaded = False

        if model_size != "small":
            warnings.warn(
                "The 'model_size' parameter is deprecated and ignored in LightweightKeywordExtractor. "
                "The lightweight extractor does not use size-based models.",
                DeprecationWarning,
                stacklevel=2,
            )

    def _load_lemminflect(self):
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

    def _lemmatize(self, word: str) -> str:
        try:
            for pos in ["VERB", "NOUN", "ADJ"]:
                lemma = self._lemminflect.getLemma(word, upos=pos)
                if lemma:
                    return lemma[0].lower()
            return word.lower()
        except Exception:
            return word.lower()

    def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
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

        top_keywords, tf_scores, stats = self._extract_keywords(
            lemmatized_words, code_identifiers, code_split_words, top_n
        )

        return {
            "top_keywords": top_keywords,
            "lemmatized_words": list(set(lemmatized_words))[:20],
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": dict(sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
            "stats": stats,
        }


class RegularKeywordExtractor(BaseKeywordExtractor):
    """Extract keywords using basic term frequency (TF) without lemmatization."""

    def extract_keywords(self, text: str, top_n: int = 15) -> dict[str, Any]:
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

        code_identifiers, code_split_words = self.extract_code_identifiers(text)
        tokens = self._tokenize(text)
        regular_words = []
        for word in tokens:
            word_lower = word.lower()
            if len(word) > 2 and word_lower not in self.STOPWORDS:
                regular_words.append(word_lower)

        top_keywords, tf_scores, stats = self._extract_keywords(
            regular_words, code_identifiers, code_split_words, top_n
        )

        return {
            "top_keywords": top_keywords,
            "regular_words": list(set(regular_words))[:20],
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": dict(sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
            "stats": stats,
        }
