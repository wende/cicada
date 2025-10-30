"""
Keyword Extraction using spaCy
Advanced NLP-based keyword extraction for programming documentation

DEPRECATED: This module is being replaced by lightweight_keyword_extractor.py
which provides faster performance using lemminflect instead of spaCy.

The spaCy-based extractor has been kept for backward compatibility and for
cases where advanced NLP features are needed. For most use cases, prefer
LightweightKeywordExtractor from cicada.lightweight_keyword_extractor.

Performance comparison:
- LightweightKeywordExtractor: ~0.1s startup time
- KeywordExtractor (spaCy): ~2s startup time

See: cicada.lightweight_keyword_extractor.LightweightKeywordExtractor
"""

from collections import Counter
import re
import sys
import subprocess

from cicada.utils import split_camel_snake_case

# Lazy import spacy only when needed
spacy = None


def _ensure_spacy_imported():
    """Import spacy only when needed."""
    global spacy
    if spacy is None:
        import spacy as spacy_module
        spacy = spacy_module


class KeywordExtractor:
    """Extract keywords from text using spaCy NLP."""

    # spaCy model names for different sizes
    SPACY_MODELS = {
        "small": "en_core_web_sm",
        "medium": "en_core_web_md",
        "large": "en_core_web_lg",
    }

    def __init__(self, verbose: bool = False, model_size: str = "small"):
        """
        Initialize keyword extractor with lazy model loading.

        Args:
            verbose: If True, print status messages during initialization
            model_size: Size of spaCy model to use ('small', 'medium', or 'large')
                       Default is 'small'. Medium and large models provide better
                       accuracy but are slower and require more memory.
        """
        self.verbose = verbose

        # Validate model size
        if model_size not in self.SPACY_MODELS:
            raise ValueError(
                f"Invalid model size '{model_size}'. "
                f"Must be one of: {', '.join(self.SPACY_MODELS.keys())}"
            )

        self.model_size = model_size
        self.model_name = self.SPACY_MODELS[model_size]
        self.nlp = None  # Lazy-loaded on first use

    def _ensure_model_loaded(self):
        """
        Ensure the spaCy model is loaded, downloading if necessary.
        Only called when model is actually needed (lazy loading).
        """
        if self.nlp is not None:
            return  # Already loaded

        # Ensure spacy is imported
        _ensure_spacy_imported()

        if self.verbose:
            print(f"Loading spaCy model ({self.model_size})...", file=sys.stderr)

        try:
            # Import the model directly as a Python package (fast failure if not installed)
            import importlib

            model_module = importlib.import_module(self.model_name)
            self.nlp = model_module.load()
            if self.verbose:
                print("✓ Model loaded successfully", file=sys.stderr)
        except (ImportError, AttributeError):
            # Model not installed, download it
            if self.verbose:
                print(
                    f"Model '{self.model_name}' not found. Downloading...",
                    file=sys.stderr,
                )

            if not self._download_model():
                raise RuntimeError(
                    f"Failed to download spaCy model '{self.model_name}'. "
                    f"Please install it manually with: python -m spacy download {self.model_name}"
                )

            # Try importing again after download
            try:
                import importlib

                model_module = importlib.import_module(self.model_name)
                self.nlp = model_module.load()
                if self.verbose:
                    print("✓ Model loaded successfully", file=sys.stderr)
            except (ImportError, AttributeError) as e:
                raise RuntimeError(
                    f"Failed to load spaCy model '{self.model_name}' after download. "
                    f"Please try installing it manually: python -m spacy download {self.model_name}"
                ) from e

    def _download_model(self) -> bool:
        """
        Download the spaCy model using uv pip install.

        Returns:
            True if download succeeded, False otherwise
        """
        # Model URLs for direct installation
        model_urls = {
            "en_core_web_sm": "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
            "en_core_web_md": "https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl",
            "en_core_web_lg": "https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl",
        }

        if self.model_name not in model_urls:
            if self.verbose:
                print(f"Unknown model: {self.model_name}", file=sys.stderr)
            return False

        model_url = model_urls[self.model_name]

        # Use uv pip install (works in uv-managed environments)
        try:
            if self.verbose:
                print(f"Running: uv pip install {model_url}", file=sys.stderr)

            result = subprocess.run(
                ["uv", "pip", "install", model_url],
                capture_output=True,
                text=True,
                check=True,
            )

            if self.verbose and result.stdout:
                print(result.stdout, file=sys.stderr)

            return True
        except FileNotFoundError:
            if self.verbose:
                print(
                    "uv not found. Please install uv or manually install the model:",
                    file=sys.stderr,
                )
                print(f"  uv pip install {model_url}", file=sys.stderr)
            return False
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"uv pip install failed: {e.stderr}", file=sys.stderr)
            return False
        except Exception as e:
            if self.verbose:
                print(f"Unexpected error during download: {e}", file=sys.stderr)
            return False

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
            self._ensure_model_loaded()
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
        - Regular words (nouns, verbs): 1x weight

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary with extracted keywords and analysis:
            - top_keywords: List of (keyword, count) tuples, sorted by frequency
            - code_identifiers: Original identifiers (weighted 10x)
            - code_split_words: Words extracted from identifiers (weighted 3x)
            - nouns, verbs, adjectives: Linguistic categories
            - entities: Named entities found
            - tf_scores: Term frequency scores
            - stats: Text statistics
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
                "tf_scores": {},
                "stats": {
                    "total_tokens": 0,
                    "total_words": 0,
                    "unique_words": 0,
                    "sentences": 0,
                },
            }
        # Ensure model is loaded (lazy loading on first use)
        self._ensure_model_loaded()

        # Process with spaCy
        doc = self.nlp(text)

        # 1. Extract nouns (concepts)
        nouns = [
            token.lemma_.lower()
            for token in doc
            if token.pos_ == "NOUN" and not token.is_stop and len(token.text) > 2
        ]

        # 2. Extract verbs (actions)
        verbs = [
            token.lemma_.lower()
            for token in doc
            if token.pos_ == "VERB" and not token.is_stop and len(token.text) > 2
        ]

        # 3. Extract adjectives (descriptors)
        adjectives = [
            token.lemma_.lower()
            for token in doc
            if token.pos_ == "ADJ" and not token.is_stop
        ]

        # 4. Extract proper nouns (named entities, technologies)
        proper_nouns = [token.text for token in doc if token.pos_ == "PROPN"]

        # 5. Extract noun chunks (multi-word concepts)
        noun_chunks = [
            chunk.text.lower()
            for chunk in doc.noun_chunks
            if len(chunk.text.split()) > 1
        ]

        # 6. Extract named entities
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        # 7. Extract code identifiers and their split words
        code_identifiers, code_split_words = self.extract_code_identifiers(text)

        # 8. Calculate keyword frequency (combining nouns, verbs, proper nouns, identifiers, and split code words)
        # Give full code identifiers 10x weight for exact matching
        # Give code split words 3x weight for fuzzy matching
        code_identifiers_lower = [ident.lower() for ident in code_identifiers]
        all_keywords = (
            nouns
            + verbs
            + proper_nouns
            + (code_identifiers_lower * 10)
            + (code_split_words * 3)
        )
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(top_n)

        # 9. Calculate TF scores (simple version)
        total_words = len(
            [token for token in doc if not token.is_stop and not token.is_punct]
        )
        tf_scores = {word: (freq / total_words) for word, freq in keyword_freq.items()}

        # Statistics
        stats = {
            "total_tokens": len(doc),
            "total_words": total_words,
            "unique_words": len(set([t.text.lower() for t in doc if not t.is_punct])),
            "sentences": len(list(doc.sents)),
        }

        return {
            "top_keywords": top_keywords,
            "nouns": list(set(nouns))[:20],
            "verbs": list(set(verbs))[:20],
            "adjectives": list(set(adjectives))[:15],
            "proper_nouns": list(set(proper_nouns)),
            "noun_chunks": list(set(noun_chunks))[:15],
            "entities": entities,
            "code_identifiers": code_identifiers,
            "code_split_words": code_split_words,
            "tf_scores": dict(
                sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "stats": stats,
        }
