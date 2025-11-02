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
    ) -> list[str]:
        """
        Expand keywords using the configured expansion strategy.

        Strategy behavior:
        - lemmi: Returns keywords + inflected forms
        - glove/fasttext: Returns keywords + semantically similar words + inflected forms for all

        Args:
            keywords: List of seed keywords to expand.
            top_n: Maximum number of similar words to return per keyword (for embeddings).
            threshold: Minimum cosine similarity score for embeddings (0.0 to 1.0).

        Returns:
            Deduplicated list of expanded keywords (flat list, not nested).

        Example:
            >>> expander = KeywordExpander(expansion_type="lemmi")
            >>> result = expander.expand_keywords(["run", "database"])
            >>> # Returns: ['run', 'running', 'runs', 'ran', 'database', 'databases', ...]
        """
        from cicada.utils import split_camel_snake_case

        expanded_words = set()

        # Step 1: Split compound identifiers and add all components
        split_keywords = []
        for keyword in keywords:
            # Add original keyword
            expanded_words.add(keyword.lower())

            # Split compound identifiers (e.g., get_keys → get, keys)
            split_text = split_camel_snake_case(keyword)
            words = [
                word.lower() for word in split_text.split() if len(word) > 1 and word.isalpha()
            ]
            split_keywords.extend(words)
            expanded_words.update(words)

        # Step 2: Generate inflections for all keywords (original + split)
        all_keywords = list(set(keywords + split_keywords))
        for keyword in all_keywords:
            inflections = self._get_inflections(keyword)
            expanded_words.update(inflections)

        # Step 3: If using embeddings, add semantically similar words + their inflections
        if self.expansion_type in ["glove", "fasttext"]:
            # Lazy-load embedding model
            if self._embedding_model is None:
                self._embedding_model = self._load_embedding_model()

            if self._embedding_model is not None:
                # Try embedding expansion for split keywords (more likely to be in vocab)
                for keyword in split_keywords:
                    try:
                        # Get most similar words
                        similar_words = self._embedding_model.most_similar(
                            keyword.lower(), topn=top_n * 3
                        )

                        # Filter by threshold and take top N
                        for word, score in similar_words[:top_n]:
                            if score >= threshold:
                                # Add the similar word
                                expanded_words.add(word.lower())
                                # Add inflections of the similar word
                                inflections = self._get_inflections(word)
                                expanded_words.update(inflections)

                    except KeyError:
                        # Keyword not in vocabulary - skip embedding expansion silently
                        # (This is expected for many code identifiers)
                        continue

        return sorted(expanded_words)

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
