"""
Keyword Extraction using spaCy
Advanced NLP-based keyword extraction for programming documentation
"""

import spacy
from collections import Counter
import re
import sys


class KeywordExtractor:
    """Extract keywords from text using spaCy NLP."""

    def __init__(self, verbose: bool = False):
        """
        Initialize spaCy model.

        Args:
            verbose: If True, print status messages during initialization
        """
        self.verbose = verbose

        if self.verbose:
            print("Loading spaCy model...", file=sys.stderr)

        try:
            self.nlp = spacy.load("en_core_web_sm")
            if self.verbose:
                print("✓ Model loaded successfully", file=sys.stderr)
        except OSError as e:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Please install it with: python -m spacy download en_core_web_sm"
            ) from e

    def split_camel_snake_case(self, text):
        """
        Split camelCase, PascalCase, and snake_case identifiers into separate words.

        Examples:
            camelCase -> camel case
            PascalCase -> Pascal Case
            snake_case -> snake case
            HTTPServer -> HTTP Server
            getHTTPResponseCode -> get HTTP Response Code
        """
        # Split on underscores (snake_case)
        text = text.replace("_", " ")

        # Split on transitions from lowercase to uppercase (camelCase)
        text = re.sub("([a-z])([A-Z])", r"\1 \2", text)

        # Split on transitions from uppercase sequence to a capitalized word (HTTPServer -> HTTP Server)
        text = re.sub("([A-Z]+)([A-Z][a-z])", r"\1 \2", text)

        return text

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
            r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b",  # PascalCase (e.g., UserController)
            r"\b[a-z]+_[a-z_]+\b",  # snake_case (e.g., get_user_data)
            r"\b[A-Z]{2,}\b",  # All UPPERCASE (e.g., HTTP, API)
        ]

        identifiers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            identifiers.extend(matches)

        identifiers = list(set(identifiers))

        # Split identifiers into individual words
        split_words = []
        for identifier in identifiers:
            split_text = self.split_camel_snake_case(identifier)
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
        Extract keywords using multiple strategies

        Args:
            text: Input text to analyze
            top_n: Number of top keywords to return

        Returns:
            Dictionary with extracted keywords and analysis
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

        # 8. Calculate keyword frequency (combining nouns, verbs, proper nouns, and split code words)
        all_keywords = nouns + verbs + proper_nouns + code_split_words
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
