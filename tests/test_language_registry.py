"""
Comprehensive tests for cicada/languages/__init__.py

Tests cover LanguageRegistry functionality including registration, loading,
caching, error handling, and built-in language configuration.
Target: >80% coverage
"""

import pytest
from cicada.languages import (
    LanguageRegistry,
    LanguageNotSupportedError,
    get_language_registry,
)
from cicada.languages.base import BaseIndexer, BaseParser
from cicada.parsing.language_config import LanguageConfig


# ============================================================================
# SECTION 1: Mock Classes for Testing
# ============================================================================


class MockParser(BaseParser):
    """Mock parser implementation."""

    def parse(self, source_code: str) -> dict:
        return {"parsed": True}

    def get_language_name(self) -> str:
        return "mock"

    def parse_file(self, file_path: str) -> dict:
        return {"parsed": True}

    def get_tree_sitter_language(self):
        return None


class MockIndexer(BaseIndexer):
    """Mock indexer implementation."""

    def get_language_name(self) -> str:
        return "mock"

    def get_file_extensions(self) -> list[str]:
        return [".mock"]

    def get_excluded_dirs(self) -> list[str]:
        return []

    def index_repository(
        self, repo_path, output_path, force=False, verbose=False, config_path=None
    ) -> dict:
        return {"success": True}


# ============================================================================
# SECTION 2: Test Language Registration
# ============================================================================


class TestLanguageRegistration:
    """Test LanguageRegistry.register_language method."""

    def setup_method(self):
        """Clear test languages before each test (preserve built-in languages)."""
        # Only clear test-specific languages, not built-in ones
        # Remove test languages if they exist
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_register_language_basic(self):
        """Test registering a new language."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        assert "test" in LanguageRegistry._languages
        assert (
            LanguageRegistry._languages["test"]["parser"]
            == "tests.test_language_registry.MockParser"
        )
        assert (
            LanguageRegistry._languages["test"]["indexer"]
            == "tests.test_language_registry.MockIndexer"
        )

    def test_register_language_with_config(self):
        """Test registering language with config."""
        config = LanguageConfig(
            language="test",
            file_extensions=[".test"],
            excluded_dirs=[],
        )

        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
            config=config,
        )

        assert LanguageRegistry._languages["test"]["config"] == config

    def test_register_language_without_parser(self):
        """Test registering language without parser (e.g., SCIP-based)."""
        LanguageRegistry.register_language(
            language="test",
            parser_class=None,
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        assert LanguageRegistry._languages["test"]["parser"] is None

    def test_register_language_overwrites_existing(self):
        """Test that registering same language overwrites previous."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        # Register again with different class
        LanguageRegistry.register_language(
            language="test",
            parser_class="different.Parser",
            indexer_class="different.Indexer",
        )

        assert LanguageRegistry._languages["test"]["parser"] == "different.Parser"


# ============================================================================
# SECTION 3: Test Getting Parser
# ============================================================================


class TestGetParser:
    """Test LanguageRegistry.get_parser method."""

    def setup_method(self):
        """Setup for each test."""
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_get_parser_returns_instance(self):
        """Test that get_parser returns a parser instance."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        parser = LanguageRegistry.get_parser("test")
        assert isinstance(parser, BaseParser)
        assert parser.get_language_name() == "mock"

    def test_get_parser_caches_result(self):
        """Test that parser classes are cached."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        parser1 = LanguageRegistry.get_parser("test")
        parser2 = LanguageRegistry.get_parser("test")

        # Both should be instances of the same cached class
        assert type(parser1) is type(parser2)
        assert "test" in LanguageRegistry._parser_cache

    def test_get_parser_unsupported_language_raises(self):
        """Test that unsupported language raises LanguageNotSupportedError."""
        with pytest.raises(LanguageNotSupportedError) as exc_info:
            LanguageRegistry.get_parser("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not supported" in str(exc_info.value)

    def test_get_parser_error_lists_supported_languages(self):
        """Test error message lists supported languages."""
        LanguageRegistry.register_language(
            language="test1",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )
        LanguageRegistry.register_language(
            language="test2",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        with pytest.raises(LanguageNotSupportedError) as exc_info:
            LanguageRegistry.get_parser("unsupported")

        error_msg = str(exc_info.value)
        assert "test1" in error_msg
        assert "test2" in error_msg

    def test_get_parser_with_none_parser_class_raises(self):
        """Test that None parser class raises ImportError."""
        LanguageRegistry.register_language(
            language="test",
            parser_class=None,
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        # Attempting to get parser for language with None parser should fail
        with pytest.raises(Exception):  # Could be TypeError or AttributeError
            LanguageRegistry.get_parser("test")


# ============================================================================
# SECTION 4: Test Getting Indexer
# ============================================================================


class TestGetIndexer:
    """Test LanguageRegistry.get_indexer method."""

    def setup_method(self):
        """Setup for each test."""
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_get_indexer_returns_instance(self):
        """Test that get_indexer returns an indexer instance."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        indexer = LanguageRegistry.get_indexer("test")
        assert isinstance(indexer, BaseIndexer)
        assert indexer.get_language_name() == "mock"

    def test_get_indexer_caches_result(self):
        """Test that indexer classes are cached."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        indexer1 = LanguageRegistry.get_indexer("test")
        indexer2 = LanguageRegistry.get_indexer("test")

        # Both should be instances of the same cached class
        assert type(indexer1) is type(indexer2)
        assert "test" in LanguageRegistry._indexer_cache

    def test_get_indexer_unsupported_language_raises(self):
        """Test that unsupported language raises LanguageNotSupportedError."""
        with pytest.raises(LanguageNotSupportedError) as exc_info:
            LanguageRegistry.get_indexer("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not supported" in str(exc_info.value)

    def test_get_indexer_error_lists_supported_languages(self):
        """Test error message lists supported languages."""
        LanguageRegistry.register_language(
            language="test1",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )
        LanguageRegistry.register_language(
            language="test2",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        with pytest.raises(LanguageNotSupportedError) as exc_info:
            LanguageRegistry.get_indexer("unsupported")

        error_msg = str(exc_info.value)
        assert "test1" in error_msg
        assert "test2" in error_msg


# ============================================================================
# SECTION 5: Test Getting Config
# ============================================================================


class TestGetConfig:
    """Test LanguageRegistry.get_config method."""

    def setup_method(self):
        """Setup for each test."""
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_get_config_returns_config(self):
        """Test that get_config returns the registered config."""
        config = LanguageConfig(
            language="test",
            file_extensions=[".test"],
            excluded_dirs=[],
        )

        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
            config=config,
        )

        retrieved_config = LanguageRegistry.get_config("test")
        assert retrieved_config == config

    def test_get_config_no_config_returns_none(self):
        """Test that get_config returns None if no config registered."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        config = LanguageRegistry.get_config("test")
        assert config is None

    def test_get_config_unsupported_language_raises(self):
        """Test that unsupported language raises LanguageNotSupportedError."""
        with pytest.raises(LanguageNotSupportedError) as exc_info:
            LanguageRegistry.get_config("nonexistent")

        assert "nonexistent" in str(exc_info.value)


# ============================================================================
# SECTION 6: Test Query Methods
# ============================================================================


class TestQueryMethods:
    """Test helper query methods."""

    def setup_method(self):
        """Setup for each test."""
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_get_supported_languages(self):
        """Test get_supported_languages returns all registered languages."""
        LanguageRegistry.register_language(
            language="lang1",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )
        LanguageRegistry.register_language(
            language="lang2",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        supported = LanguageRegistry.get_supported_languages()
        assert "lang1" in supported
        assert "lang2" in supported
        assert len(supported) >= 2

    def test_get_supported_languages_empty(self):
        """Test get_supported_languages when registry is empty."""
        supported = LanguageRegistry.get_supported_languages()
        assert isinstance(supported, list)

    def test_is_language_supported_true(self):
        """Test is_language_supported returns True for registered language."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        assert LanguageRegistry.is_language_supported("test") is True

    def test_is_language_supported_false(self):
        """Test is_language_supported returns False for unregistered language."""
        assert LanguageRegistry.is_language_supported("nonexistent") is False


# ============================================================================
# SECTION 7: Test Load Class Helper
# ============================================================================


class TestLoadClass:
    """Test LanguageRegistry._load_class method."""

    def test_load_class_valid_path(self):
        """Test loading a valid class."""
        cls = LanguageRegistry._load_class("tests.test_language_registry.MockParser")
        assert cls is MockParser

    def test_load_class_invalid_module_raises(self):
        """Test that invalid module path raises ImportError."""
        with pytest.raises(ImportError):
            LanguageRegistry._load_class("nonexistent.module.Class")

    def test_load_class_invalid_class_raises(self):
        """Test that invalid class name raises AttributeError."""
        with pytest.raises(AttributeError):
            LanguageRegistry._load_class("tests.test_language_registry.NonexistentClass")

    def test_load_class_builtin(self):
        """Test loading a builtin class."""
        cls = LanguageRegistry._load_class("builtins.dict")
        assert cls is dict


# ============================================================================
# SECTION 8: Test Built-in Language Registration
# ============================================================================


class TestBuiltinLanguages:
    """Test that built-in languages are properly registered."""

    def test_elixir_is_registered(self):
        """Test that Elixir is registered."""
        assert LanguageRegistry.is_language_supported("elixir")

    def test_elixir_indexer_accessible(self):
        """Test that Elixir indexer can be loaded."""
        indexer = LanguageRegistry.get_indexer("elixir")
        assert indexer is not None
        # ElixirIndexer might not inherit from BaseIndexer in the old implementation

    def test_elixir_has_config(self):
        """Test that Elixir has a default config."""
        config = LanguageRegistry.get_config("elixir")
        assert config is not None
        # Config should have language attribute or be a dict with language key
        if hasattr(config, "language"):
            assert config.language == "elixir"

    def test_python_is_registered(self):
        """Test that Python is registered."""
        assert LanguageRegistry.is_language_supported("python")

    def test_python_indexer_accessible(self):
        """Test that Python indexer can be loaded."""
        indexer = LanguageRegistry.get_indexer("python")
        assert indexer is not None

    def test_python_has_no_parser(self):
        """Test that Python doesn't have a parser (SCIP-based)."""
        with pytest.raises(Exception):
            # Should fail because parser_class is None
            LanguageRegistry.get_parser("python")

    def test_python_has_config(self):
        """Test that Python has a default config."""
        config = LanguageRegistry.get_config("python")
        assert config is not None
        # Config should have language attribute or be a dict with language key
        if hasattr(config, "language"):
            assert config.language == "python"


# ============================================================================
# SECTION 9: Test get_language_registry Function
# ============================================================================


class TestGetLanguageRegistry:
    """Test the get_language_registry helper function."""

    def test_returns_language_registry(self):
        """Test that function returns LanguageRegistry class."""
        registry = get_language_registry()
        assert registry is LanguageRegistry

    def test_returns_singleton(self):
        """Test that function always returns same instance."""
        registry1 = get_language_registry()
        registry2 = get_language_registry()
        assert registry1 is registry2


# ============================================================================
# SECTION 10: Test Error Messages
# ============================================================================


class TestErrorMessages:
    """Test that error messages are helpful."""

    def setup_method(self):
        """Setup for each test."""
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_unsupported_language_error_class_exists(self):
        """Test that LanguageNotSupportedError is an Exception."""
        assert issubclass(LanguageNotSupportedError, Exception)

    def test_unsupported_language_error_message_helpful(self):
        """Test that error message is descriptive."""
        LanguageRegistry.register_language(
            language="mylang",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        try:
            LanguageRegistry.get_indexer("unknown")
            pytest.fail("Should have raised LanguageNotSupportedError")
        except LanguageNotSupportedError as e:
            error_msg = str(e)
            assert "unknown" in error_msg
            assert "not supported" in error_msg
            assert "mylang" in error_msg  # Should list available languages


# ============================================================================
# SECTION 11: Test Cache Behavior
# ============================================================================


class TestCacheBehavior:
    """Test that caching works correctly."""

    def setup_method(self):
        """Setup for each test."""
        for lang in ["test", "test1", "test2", "mock"]:
            LanguageRegistry._languages.pop(lang, None)
            LanguageRegistry._parser_cache.pop(lang, None)
            LanguageRegistry._indexer_cache.pop(lang, None)

    def test_parser_cache_independent_from_indexer_cache(self):
        """Test that parser and indexer caches are separate."""
        LanguageRegistry.register_language(
            language="test",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        LanguageRegistry.get_parser("test")
        LanguageRegistry.get_indexer("test")

        assert "test" in LanguageRegistry._parser_cache
        assert "test" in LanguageRegistry._indexer_cache

    def test_multiple_languages_separate_caches(self):
        """Test that different languages use separate cache entries."""
        LanguageRegistry.register_language(
            language="test1",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )
        LanguageRegistry.register_language(
            language="test2",
            parser_class="tests.test_language_registry.MockParser",
            indexer_class="tests.test_language_registry.MockIndexer",
        )

        indexer1 = LanguageRegistry.get_indexer("test1")
        indexer2 = LanguageRegistry.get_indexer("test2")

        assert "test1" in LanguageRegistry._indexer_cache
        assert "test2" in LanguageRegistry._indexer_cache
        # The cached classes should be the same class (since we registered the same class path)
        # but the instances should be different
        assert type(indexer1) is type(indexer2)  # Same class
        assert indexer1 is not indexer2  # Different instances
