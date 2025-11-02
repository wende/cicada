"""
Keyword expansion using lemminflect and word embeddings.

This module provides keyword expansion through three strategies:
1. Lemmi: Generate inflected forms using lemminflect (e.g., run → running, runs, ran)
2. GloVe: Semantic similarity via GloVe + inflected forms
3. FastText: Semantic similarity via FastText + inflected forms

Example:
    >>> expander = KeywordExpander(expansion_type="glove", verbose=True)
    >>> expanded = expander.expand_keywords(["database"], top_n=3)
    >>> print(expanded)
    ['database', 'databases', 'postgresql', 'mysql', 'storage']
"""

from __future__ import annotations

from typing import Any


class KeywordExpander:
    """
    Expands keywords using lemminflect and optionally word embeddings.

    Supports three expansion strategies:
    - lemmi: Inflected forms only (run → running, runs, ran)
    - glove: GloVe embeddings + inflected forms (128MB)
    - fasttext: FastText embeddings + inflected forms (958MB)
    """

    # Class-level cache for loaded models
    _model_cache: dict[str, Any] = {}
    _lemminflect_cache: Any = None

    # Model configurations for word embeddings
    EMBEDDING_MODELS = {
        "glove": {
            "name": "glove-wiki-gigaword-100",
            "size_mb": 128,
            "description": "GloVe embeddings (100-dim, fast)",
        },
        "fasttext": {
            "name": "fasttext-wiki-news-subwords-300",
            "size_mb": 958,
            "description": "FastText embeddings (300-dim, better rare words)",
        },
    }

    # Expansion penalty multipliers (reduce noise from derived terms)
    INFLECTION_PENALTY = 0.7  # Penalty for morphological variations (run → runs, running)
    SEMANTIC_EXPANSION_PENALTY = 0.9  # Penalty for embedding-based similar words
    TOP_N = 5  # Number of top expansions to consider

    def __init__(self, expansion_type: str = "lemmi", verbose: bool = False):
        """
        Initialize keyword expander.

        Args:
            expansion_type: Type of expansion to perform.
                          - "lemmi": Lemminflect inflections only
                          - "glove": GloVe embeddings + lemminflect (128MB)
                          - "fasttext": FastText embeddings + lemminflect (958MB)
            verbose: Whether to print progress messages during model loading.

        Raises:
            ValueError: If expansion_type is not supported.
        """
        if expansion_type not in ["lemmi", "glove", "fasttext"]:
            raise ValueError(
                f"Unsupported expansion_type: {expansion_type}. "
                f"Supported types: lemmi, glove, fasttext"
            )

        self.expansion_type = expansion_type
        self.verbose = verbose
        self._embedding_model: Any = None

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
            if self.verbose:
                print("✓ lemminflect loaded")
            return lemminflect
        except ImportError as e:
            raise ImportError(
                "lemminflect is required for keyword expansion. "
                "Install with: pip install lemminflect"
            ) from e

    def _load_embedding_model(self) -> Any:
        """
        Lazy-load word embedding model (glove or fasttext).

        Returns:
            Loaded gensim KeyedVectors model.

        Raises:
            ImportError: If gensim is not installed.
            Exception: If model download or loading fails.
        """
        # Only load embeddings for glove/fasttext (not for lemmi-only)
        if self.expansion_type == "lemmi":
            return None

        # Check class-level cache first
        if self.expansion_type in self._model_cache:
            if self.verbose:
                print(f"✓ Using cached {self.expansion_type} model")
            return self._model_cache[self.expansion_type]

        try:
            import gensim.downloader as api
        except ImportError as e:
            raise ImportError(
                "gensim is required for embedding-based expansion. "
                "Install with: pip install gensim"
            ) from e

        # Get model configuration
        model_config = self.EMBEDDING_MODELS[self.expansion_type]
        model_name: str = model_config["name"]  # type: ignore[assignment]
        size_mb: int = model_config["size_mb"]  # type: ignore[assignment]

        # Check if model is already downloaded to disk
        from pathlib import Path

        gensim_data_dir = Path.home() / "gensim-data" / model_name
        is_cached = gensim_data_dir.exists()

        if self.verbose:
            if is_cached:
                print(f"Loading {self.expansion_type} model from cache...")
            else:
                print(f"Loading {self.expansion_type} model...")
                print(f"Downloading {size_mb}MB (first time only)...")
                print("Progress bar will appear during download.")

        try:
            # Load model using gensim's downloader
            model = api.load(model_name)

            # Cache at class level
            self._model_cache[self.expansion_type] = model

            if self.verbose:
                print(f"✓ {self.expansion_type.title()} model loaded successfully")

            return model

        except Exception as e:
            raise Exception(f"Failed to load {self.expansion_type} model: {str(e)}") from e

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
        return_scores: bool = False,
        keyword_scores: dict[str, float] | None = None,
        min_score: float = 0.0,
        code_identifiers: list[str] | None = None,
    ) -> list[str] | dict[str, Any]:
        """
        Expand keywords using the configured expansion strategy.

        Strategy behavior:
        - lemmi: Returns keywords + inflected forms
        - glove/fasttext: Returns keywords + semantically similar words + inflected forms for all
        - Code identifiers are NOT inflected or expanded (kept as exact matches)

        Args:
            keywords: List of seed keywords to expand.
            top_n: Maximum number of similar words to return per keyword (for embeddings).
            threshold: Minimum cosine similarity score for embeddings (0.0 to 1.0).
            return_scores: If True, return detailed dict with scores. If False, return simple list.
            keyword_scores: Optional dict mapping keywords to their extraction scores.
                          These scores multiply with expansion similarity scores.
            min_score: Minimum score threshold for expanded keywords (filters out low-scoring terms).
            code_identifiers: List of code identifiers that should NOT be inflected or expanded.

        Returns:
            If return_scores=False: Deduplicated list of expanded keywords (flat list).
            If return_scores=True: Dict with 'words' (list of dicts with word/score/source) and 'simple' (flat list).

        Example:
            >>> expander = KeywordExpander(expansion_type="lemmi")
            >>> result = expander.expand_keywords(["run", "database"])
            >>> # Returns: ['run', 'running', 'runs', 'ran', 'database', 'databases', ...]

            >>> result = expander.expand_keywords(["run"], return_scores=True, keyword_scores={"run": 0.95})
            >>> # Returns: {
            >>>   'words': [
            >>>     {'word': 'run', 'score': 0.95, 'source': 'original'},
            >>>     {'word': 'running', 'score': 0.95, 'source': 'inflection', 'parent': 'run'}
            >>>   ],
            >>>   'simple': ['run', 'running', ...]
            >>> }
        """
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
            if return_scores:
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
                if return_scores and word not in word_details:
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
            parent_score = (
                word_details.get(keyword_lower, {}).get("score", 1.0) if return_scores else 1.0
            )

            inflections = self._get_inflections(keyword)
            for inflection in inflections:
                expanded_words.add(inflection)
                if return_scores and inflection not in word_details:
                    # Inflections inherit parent's score with penalty
                    word_details[inflection] = {
                        "score": parent_score * self.INFLECTION_PENALTY,
                        "source": "inflection",
                        "parent": keyword,
                    }

        # Step 3: If using embeddings, add semantically similar words + their inflections
        if self.expansion_type in ["glove", "fasttext"]:
            # Lazy-load embedding model
            if self._embedding_model is None:
                self._embedding_model = self._load_embedding_model()

            if self._embedding_model is not None:
                # Try embedding expansion for all keywords (original + split)
                # BUT: Skip semantic expansion for code identifiers (they should remain exact)
                for keyword in all_keywords:
                    keyword_lower = keyword.lower()

                    # Skip semantic expansion for code identifiers
                    if keyword_lower in code_identifiers_set:
                        continue

                    # Get parent keyword's score to multiply with similarity
                    parent_score = (
                        word_details.get(keyword_lower, {}).get("score", 1.0)
                        if return_scores
                        else 1.0
                    )

                    try:
                        # Get most similar words
                        similar_words = self._embedding_model.most_similar(
                            keyword_lower, topn=top_n * 3
                        )

                        # Filter by threshold and take top N
                        for word, similarity_score in similar_words[: self.TOP_N]:
                            if similarity_score >= threshold:
                                # Add the similar word
                                word_lower = word.lower()
                                expanded_words.add(word_lower)
                                if return_scores and word_lower not in word_details:
                                    # Final score = extraction score × similarity score × semantic penalty
                                    final_score = (
                                        parent_score
                                        * float(similarity_score)
                                        * self.SEMANTIC_EXPANSION_PENALTY
                                    )
                                    word_details[word_lower] = {
                                        "score": final_score,
                                        "source": "embedding",
                                        "parent": keyword,
                                    }

                                # Add inflections of the similar word
                                inflections = self._get_inflections(word)
                                embedding_score = (
                                    word_details.get(word_lower, {}).get(
                                        "score",
                                        parent_score
                                        * float(similarity_score)
                                        * self.SEMANTIC_EXPANSION_PENALTY,
                                    )
                                    if return_scores
                                    else parent_score
                                    * float(similarity_score)
                                    * self.SEMANTIC_EXPANSION_PENALTY
                                )
                                for inflection in inflections:
                                    expanded_words.add(inflection)
                                    if return_scores and inflection not in word_details:
                                        # Embedding inflections inherit the embedding's score with inflection penalty
                                        word_details[inflection] = {
                                            "score": embedding_score * self.INFLECTION_PENALTY,
                                            "source": "embedding_inflection",
                                            "parent": word_lower,
                                        }

                    except KeyError:
                        # Keyword not in vocabulary - skip embedding expansion silently
                        # (This is expected for many code identifiers)
                        continue

        simple_list = sorted(expanded_words)

        if return_scores:
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
        else:
            # Apply min_score filter if specified
            if min_score > 0.0:
                simple_list = [
                    word
                    for word in simple_list
                    if word_details.get(word, {}).get("score", 1.0) >= min_score
                ]
            return simple_list

    def get_expansion_info(self) -> dict[str, Any]:
        """
        Get information about the expansion configuration.

        Returns:
            Dictionary with expansion metadata (type, model info if applicable).
        """
        info: dict[str, Any] = {
            "type": self.expansion_type,
        }

        if self.expansion_type != "lemmi" and self._embedding_model is not None:
            info["embedding_vocab_size"] = len(self._embedding_model.key_to_index)
            info["embedding_vector_size"] = self._embedding_model.vector_size

        return info
