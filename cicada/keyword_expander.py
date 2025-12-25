"""
Keyword expansion using lemminflect.

This module provides keyword expansion through inflected forms:
- Lemmi: Generate inflected forms using lemminflect (e.g., run → running, runs, ran)

Example:
    >>> expander = KeywordExpander(expansion_type="lemmi", verbose=True)
    >>> expanded = expander.expand_keywords(["database"], top_n=3)
    >>> print(expanded)
    ['database', 'databases']
"""

from __future__ import annotations

import threading
from typing import Any


class KeywordExpander:
    """
    Expands keywords using lemminflect inflections.

    Supports inflection-based expansion:
    - lemmi: Inflected forms only (run → running, runs, ran)
    """

    # Class-level cache for loaded models
    _lemminflect_cache: Any = None
    _worker_init_lock = threading.Lock()
    _initialized_workers: set[int] = set()  # Thread IDs that have been initialized
    _worker_counter = 0
    _total_workers: int | None = None

    # Expansion penalty multipliers (reduce noise from derived terms)
    INFLECTION_PENALTY = 0.7  # Penalty for morphological variations (run → runs, running)
    TOP_N = 5  # Number of top expansions to consider

    def __init__(self, expansion_type: str = "lemmi", verbose: bool = False):
        """
        Initialize keyword expander.

        Args:
            expansion_type: Type of expansion to perform. Currently only "lemmi" is supported.
            verbose: Whether to print progress messages during model loading.

        Raises:
            ValueError: If expansion_type is not supported.
        """
        if expansion_type not in ["lemmi"]:
            raise ValueError(
                f"Unsupported expansion_type: {expansion_type}. " f"Supported types: lemmi"
            )

        self.expansion_type = expansion_type
        self.verbose = verbose

    def _load_lemminflect(self) -> Any:
        """
        Lazy-load lemminflect library (cached at class level).

        Returns:
            lemminflect module

        Raises:
            ImportError: If lemminflect is not installed.
        """
        if KeywordExpander._lemminflect_cache is not None:
            return KeywordExpander._lemminflect_cache

        try:
            import lemminflect

            KeywordExpander._lemminflect_cache = lemminflect
            return lemminflect
        except ImportError as e:
            raise ImportError(
                "lemminflect is required for keyword expansion. "
                "Install with: pip install lemminflect"
            ) from e

    def _maybe_print_worker_init(self) -> None:
        """Print worker initialization message once per thread (if verbose)."""
        if not self.verbose:
            return

        thread_id = threading.get_ident()

        # Check if this thread has already been initialized
        if thread_id in KeywordExpander._initialized_workers:
            return

        # Register this worker and print initialization message
        with KeywordExpander._worker_init_lock:
            # Double-check after acquiring lock
            if thread_id in KeywordExpander._initialized_workers:
                return

            KeywordExpander._initialized_workers.add(thread_id)
            KeywordExpander._worker_counter += 1
            worker_num = KeywordExpander._worker_counter
            total = KeywordExpander._total_workers

            if total is not None:
                print(f"\r✓ keyword expander loaded ({worker_num}/{total})", end="", flush=True)
            else:
                print(f"\r✓ keyword expander loaded ({worker_num})", end="", flush=True)

    def _get_inflections(self, word: str) -> set[str]:
        """
        Generate inflected forms of a word using lemminflect.

        Args:
            word: Base word to inflect

        Returns:
            Set of inflected forms (including the original word)
        """
        lemminflect = self._load_lemminflect()
        inflections = {word.lower()}

        try:
            # Try different POS tags to get comprehensive inflections
            for pos in ["VERB", "NOUN", "ADJ"]:
                # Get inflections for all forms of this POS
                all_inflections = lemminflect.getAllInflections(word, upos=pos)
                if all_inflections:
                    for form_list in all_inflections.values():
                        inflections.update([f.lower() for f in form_list])
        except Exception:
            # If inflection fails, just return the original word
            pass

        return inflections

    def expand_keywords(
        self,
        keywords: list[str],
        top_n: int = 3,
        threshold: float = 0.7,
        keyword_scores: dict[str, float] | None = None,
        min_score: float = 0.0,
        code_identifiers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Expand keywords using inflected forms.

        Strategy behavior:
        - lemmi: Returns keywords + inflected forms
        - Code identifiers are NOT inflected or expanded (kept as exact matches)

        Args:
            keywords: List of seed keywords to expand.
            top_n: Unused (kept for backward compatibility).
            threshold: Unused (kept for backward compatibility).
            keyword_scores: Optional dict mapping keywords to their extraction scores.
                          These scores multiply with expansion similarity scores.
            min_score: Minimum score threshold for expanded keywords (filters out low-scoring terms).
            code_identifiers: List of code identifiers that should NOT be inflected or expanded.

        Returns:
            Dict with 'words' (list of dicts with word/score/source) and 'simple' (flat list).

        Example:
            >>> expander = KeywordExpander(expansion_type="lemmi")
            >>> result = expander.expand_keywords(["run"], keyword_scores={"run": 0.95})
            >>> # Returns: {
            >>>   'words': [
            >>>     {'word': 'run', 'score': 0.95, 'source': 'original'},
            >>>     {'word': 'running', 'score': 0.95, 'source': 'inflection', 'parent': 'run'}
            >>>   ],
            >>>   'simple': ['run', 'running', ...]
            >>> }
        """
        # Print worker initialization message (once per thread)
        self._maybe_print_worker_init()

        from cicada.utils import split_camel_snake_case

        # Default all keyword scores to 1.0 if not provided
        if keyword_scores is None:
            keyword_scores = {kw.lower(): 1.0 for kw in keywords}
        else:
            # Normalize keys to lowercase
            keyword_scores = {k.lower(): v for k, v in keyword_scores.items()}

        # Normalize code identifiers to lowercase set for fast lookup
        code_identifiers_set = set()
        if code_identifiers:
            code_identifiers_set = {ident.lower() for ident in code_identifiers}

        expanded_words = set()
        word_details: dict[str, dict[str, Any]] = {}  # word -> {score, source, parent}

        # Step 1: Split compound identifiers and add all components
        split_keywords = []
        for keyword in keywords:
            # Add original keyword with its extraction score
            word_lower = keyword.lower()
            expanded_words.add(word_lower)
            extraction_score = keyword_scores.get(word_lower, 1.0)
            word_details[word_lower] = {
                "score": extraction_score,
                "source": "original",
            }

            # Split compound identifiers (e.g., get_keys → get, keys)
            split_text = split_camel_snake_case(keyword)
            words = [
                word.lower() for word in split_text.split() if len(word) > 1 and word.isalpha()
            ]
            split_keywords.extend(words)
            for word in words:
                expanded_words.add(word)
                if word not in word_details:
                    # Split words inherit parent's extraction score
                    word_details[word] = {
                        "score": extraction_score,
                        "source": "split",
                        "parent": keyword,
                    }

        # Step 2: Generate inflections for all keywords (original + split)
        # BUT: Skip inflections for code identifiers (they should remain exact)
        all_keywords = list(set(keywords + split_keywords))
        for keyword in all_keywords:
            keyword_lower = keyword.lower()

            # Skip inflections for code identifiers
            if keyword_lower in code_identifiers_set:
                continue

            # Get the parent's score (either from original keywords or split words)
            parent_score = word_details.get(keyword_lower, {}).get("score", 1.0)

            inflections = self._get_inflections(keyword)
            for inflection in inflections:
                expanded_words.add(inflection)
                if inflection not in word_details:
                    # Inflections inherit parent's score with penalty
                    word_details[inflection] = {
                        "score": parent_score * self.INFLECTION_PENALTY,
                        "source": "inflection",
                        "parent": keyword,
                    }

        simple_list = sorted(expanded_words)

        # Build detailed list with scores
        detailed_list = [
            {"word": word, **word_details.get(word, {"score": 1.0, "source": "unknown"})}
            for word in simple_list
        ]

        # Apply min_score filter if specified
        if min_score > 0.0:
            detailed_list = [
                item
                for item in detailed_list
                if isinstance(item.get("score"), (int, float))
                and float(item.get("score", 0.0)) >= min_score
            ]
            simple_list = [item["word"] for item in detailed_list]

        return {
            "words": detailed_list,
            "simple": simple_list,
        }

    def get_expansion_info(self) -> dict[str, Any]:
        """
        Get information about the expansion configuration.

        Returns:
            Dictionary with expansion metadata (type).
        """
        info: dict[str, Any] = {
            "type": self.expansion_type,
        }

        return info
