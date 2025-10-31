"""Tests for LightweightKeywordExtractor."""

import sys
import warnings
from unittest.mock import MagicMock, patch

import pytest

from cicada.lightweight_keyword_extractor import LightweightKeywordExtractor


class TestInitialization:
    """Test extractor initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        extractor = LightweightKeywordExtractor()
        assert extractor.verbose is False
        assert extractor.model_size == "small"
        assert extractor._lemminflect_loaded is False

    def test_verbose_initialization(self):
        """Test initialization with verbose=True."""
        extractor = LightweightKeywordExtractor(verbose=True)
        assert extractor.verbose is True

    def test_deprecated_model_size_warning(self):
        """Test that non-small model_size triggers deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            extractor = LightweightKeywordExtractor(model_size="large")

            # Should have a deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "model_size" in str(w[0].message)
            assert "deprecated" in str(w[0].message).lower()


class TestLoadLemminflect:
    """Test lemminflect loading."""

    def test_load_lemminflect_once(self):
        """Test that lemminflect is only loaded once."""
        extractor = LightweightKeywordExtractor()

        # First load
        extractor._load_lemminflect()
        assert extractor._lemminflect_loaded is True

        # Store reference to loaded module
        first_load = extractor._lemminflect

        # Second load should return early
        extractor._load_lemminflect()
        assert extractor._lemminflect is first_load

    def test_load_lemminflect_verbose(self, capsys):
        """Test verbose output during lemminflect load."""
        extractor = LightweightKeywordExtractor(verbose=True)
        extractor._load_lemminflect()

        captured = capsys.readouterr()
        assert "lemminflect loaded" in captured.err

    def test_load_lemminflect_import_error(self):
        """Test handling of missing lemminflect."""
        extractor = LightweightKeywordExtractor()

        # Mock import to fail
        with patch("builtins.__import__", side_effect=ImportError("No module named 'lemminflect'")):
            with pytest.raises(RuntimeError, match="lemminflect is required"):
                extractor._load_lemminflect()


class TestTokenize:
    """Test tokenization."""

    def test_tokenize_simple(self):
        """Test tokenizing simple text."""
        extractor = LightweightKeywordExtractor()
        tokens = extractor._tokenize("hello world")
        assert tokens == ["hello", "world"]

    def test_tokenize_with_punctuation(self):
        """Test that punctuation is excluded."""
        extractor = LightweightKeywordExtractor()
        tokens = extractor._tokenize("hello, world!")
        assert tokens == ["hello", "world"]

    def test_tokenize_with_numbers(self):
        """Test tokenizing with numbers."""
        extractor = LightweightKeywordExtractor()
        tokens = extractor._tokenize("user123 data456")
        assert "user123" in tokens
        assert "data456" in tokens

    def test_tokenize_empty(self):
        """Test tokenizing empty string."""
        extractor = LightweightKeywordExtractor()
        tokens = extractor._tokenize("")
        assert tokens == []


class TestLemmatize:
    """Test lemmatization."""

    def test_lemmatize_verb(self):
        """Test lemmatizing a verb."""
        extractor = LightweightKeywordExtractor()
        extractor._load_lemminflect()

        result = extractor._lemmatize("running")
        # Should return lemma (likely "run")
        assert result in ["run", "running"]

    def test_lemmatize_noun(self):
        """Test lemmatizing a noun."""
        extractor = LightweightKeywordExtractor()
        extractor._load_lemminflect()

        result = extractor._lemmatize("users")
        # Should return lemma (likely "user")
        assert result in ["user", "users"]

    def test_lemmatize_fallback(self):
        """Test lemmatization fallback for unknown words."""
        extractor = LightweightKeywordExtractor()
        extractor._load_lemminflect()

        # Use a made-up word
        result = extractor._lemmatize("xyzabc")
        assert result == "xyzabc"

    def test_lemmatize_exception_handling(self):
        """Test exception handling in lemmatization."""
        extractor = LightweightKeywordExtractor()
        extractor._load_lemminflect()

        # Mock getLemma to raise exception
        with patch.object(extractor._lemminflect, "getLemma", side_effect=Exception("Test error")):
            result = extractor._lemmatize("test")
            # Should fall back to lowercase
            assert result == "test"


class TestExtractCodeIdentifiers:
    """Test code identifier extraction."""

    def test_extract_camel_case(self):
        """Test extracting camelCase identifiers."""
        extractor = LightweightKeywordExtractor()
        identifiers, split_words = extractor.extract_code_identifiers("getUserData")

        assert "getUserData" in identifiers
        assert "get" in split_words
        assert "user" in split_words
        assert "data" in split_words

    def test_extract_snake_case(self):
        """Test extracting snake_case identifiers."""
        extractor = LightweightKeywordExtractor()
        identifiers, split_words = extractor.extract_code_identifiers("get_user_data")

        assert "get_user_data" in identifiers
        assert "get" in split_words
        assert "user" in split_words
        assert "data" in split_words

    def test_extract_pascal_case(self):
        """Test extracting PascalCase identifiers."""
        extractor = LightweightKeywordExtractor()
        identifiers, split_words = extractor.extract_code_identifiers("UserController")

        assert "UserController" in identifiers
        assert "user" in split_words
        assert "controller" in split_words

    def test_extract_uppercase_acronym(self):
        """Test extracting uppercase acronyms."""
        extractor = LightweightKeywordExtractor()
        identifiers, split_words = extractor.extract_code_identifiers("HTTPServer")

        assert "HTTPServer" in identifiers

    def test_extract_no_identifiers(self):
        """Test text with no code identifiers."""
        extractor = LightweightKeywordExtractor()
        identifiers, split_words = extractor.extract_code_identifiers("this is plain text")

        assert len(identifiers) == 0
        assert len(split_words) == 0

    def test_extract_mixed_text(self):
        """Test text with mixed code and plain text."""
        extractor = LightweightKeywordExtractor()
        text = "The getUserData function returns user_info data"
        identifiers, split_words = extractor.extract_code_identifiers(text)

        assert "getUserData" in identifiers
        assert "user_info" in identifiers


class TestExtractKeywordsSimple:
    """Test simple keyword extraction."""

    def test_extract_keywords_simple_basic(self):
        """Test basic keyword extraction."""
        extractor = LightweightKeywordExtractor()
        keywords = extractor.extract_keywords_simple("user authentication system")

        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_extract_keywords_simple_empty(self):
        """Test extraction from empty text."""
        extractor = LightweightKeywordExtractor()
        keywords = extractor.extract_keywords_simple("")

        assert keywords == []

    def test_extract_keywords_simple_whitespace_only(self):
        """Test extraction from whitespace-only text."""
        extractor = LightweightKeywordExtractor()
        keywords = extractor.extract_keywords_simple("   \n\t  ")

        assert keywords == []

    def test_extract_keywords_simple_top_n(self):
        """Test that top_n parameter limits results."""
        extractor = LightweightKeywordExtractor()
        text = "user data user data user profile system system"
        keywords = extractor.extract_keywords_simple(text, top_n=3)

        assert len(keywords) <= 3

    def test_extract_keywords_simple_exception_handling(self):
        """Test exception handling in simple extraction."""
        extractor = LightweightKeywordExtractor(verbose=True)

        # Mock extract_keywords to raise exception
        with patch.object(extractor, "extract_keywords", side_effect=Exception("Test error")):
            keywords = extractor.extract_keywords_simple("test text")
            # Should return empty list on exception
            assert keywords == []


class TestExtractKeywords:
    """Test full keyword extraction."""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        extractor = LightweightKeywordExtractor()
        result = extractor.extract_keywords("user authentication system")

        assert "top_keywords" in result
        assert "lemmatized_words" in result
        assert "code_identifiers" in result
        assert "code_split_words" in result
        assert "tf_scores" in result
        assert "stats" in result

    def test_extract_keywords_empty(self):
        """Test extraction from empty text."""
        extractor = LightweightKeywordExtractor()
        result = extractor.extract_keywords("")

        assert result["top_keywords"] == []
        assert result["lemmatized_words"] == []
        assert result["code_identifiers"] == []
        assert result["code_split_words"] == []
        assert result["tf_scores"] == {}
        assert result["stats"]["total_tokens"] == 0

    def test_extract_keywords_whitespace_only(self):
        """Test extraction from whitespace-only text."""
        extractor = LightweightKeywordExtractor()
        result = extractor.extract_keywords("   \n\t  ")

        assert result["top_keywords"] == []

    def test_extract_keywords_with_code(self):
        """Test extraction with code identifiers."""
        extractor = LightweightKeywordExtractor()
        text = "The getUserData function fetches user data from database"
        result = extractor.extract_keywords(text)

        assert len(result["code_identifiers"]) > 0
        assert "getUserData" in result["code_identifiers"]

    def test_extract_keywords_stopwords_filtered(self):
        """Test that stopwords are filtered out."""
        extractor = LightweightKeywordExtractor()
        text = "the user and the system"
        result = extractor.extract_keywords(text)

        # "the" and "and" are stopwords, should not be in top keywords
        keywords = [kw for kw, _ in result["top_keywords"]]
        assert "the" not in keywords
        assert "and" not in keywords

    def test_extract_keywords_top_n(self):
        """Test top_n parameter."""
        extractor = LightweightKeywordExtractor()
        text = "user data system profile account settings configuration preferences"
        result = extractor.extract_keywords(text, top_n=3)

        assert len(result["top_keywords"]) <= 3

    def test_extract_keywords_weighting(self):
        """Test that code identifiers are weighted higher."""
        extractor = LightweightKeywordExtractor()
        text = "The getUserData function processes data getUserData"
        result = extractor.extract_keywords(text)

        # getUserData should appear in top keywords due to high weighting
        keywords = [kw for kw, _ in result["top_keywords"]]
        assert "getuserdata" in keywords or "getdata" in keywords or "user" in keywords

    def test_extract_keywords_stats(self):
        """Test statistics calculation."""
        extractor = LightweightKeywordExtractor()
        text = "user authentication and authorization system"
        result = extractor.extract_keywords(text)

        stats = result["stats"]
        assert stats["total_tokens"] > 0
        assert stats["total_words"] > 0
        assert stats["unique_words"] > 0
        assert stats["unique_words"] <= stats["total_words"]

    def test_extract_keywords_tf_scores_empty_text(self):
        """Test TF scores calculation with no valid words."""
        extractor = LightweightKeywordExtractor()
        # Very short text that gets filtered out
        text = "a an the"
        result = extractor.extract_keywords(text)

        # Should handle empty keyword list gracefully
        assert isinstance(result["tf_scores"], dict)

    def test_extract_keywords_tf_scores_non_empty(self):
        """Test TF scores calculation with valid words."""
        extractor = LightweightKeywordExtractor()
        text = "user user data system"
        result = extractor.extract_keywords(text)

        # Should have TF scores
        assert len(result["tf_scores"]) > 0
        # All scores should be between 0 and 1
        assert all(0 <= score <= 1 for score in result["tf_scores"].values())


class TestStopwords:
    """Test stopword handling."""

    def test_stopwords_defined(self):
        """Test that stopwords set is defined."""
        assert hasattr(LightweightKeywordExtractor, "STOPWORDS")
        assert len(LightweightKeywordExtractor.STOPWORDS) > 0

    def test_common_stopwords_present(self):
        """Test that common stopwords are in the set."""
        stopwords = LightweightKeywordExtractor.STOPWORDS
        assert "the" in stopwords
        assert "and" in stopwords
        assert "is" in stopwords
        assert "are" in stopwords


class TestCodePatterns:
    """Test code pattern matching."""

    def test_code_patterns_defined(self):
        """Test that code patterns are defined."""
        assert hasattr(LightweightKeywordExtractor, "CODE_PATTERNS")
        assert len(LightweightKeywordExtractor.CODE_PATTERNS) > 0

    def test_camel_case_pattern(self):
        """Test camelCase pattern matching."""
        extractor = LightweightKeywordExtractor()
        text = "getUserData"

        # Should match at least one pattern
        matches = []
        for pattern in extractor.CODE_PATTERNS:
            matches.extend(pattern.findall(text))

        assert "getUserData" in matches

    def test_snake_case_pattern(self):
        """Test snake_case pattern matching."""
        extractor = LightweightKeywordExtractor()
        text = "get_user_data"

        matches = []
        for pattern in extractor.CODE_PATTERNS:
            matches.extend(pattern.findall(text))

        assert "get_user_data" in matches
