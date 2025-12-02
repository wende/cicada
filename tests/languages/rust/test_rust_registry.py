"""Tests covering basic Rust language wiring in the registry."""

import pytest

from cicada.languages import LanguageRegistry


@pytest.fixture
def registry():
    return LanguageRegistry


def test_rust_language_is_registered(registry):
    """Rust should be listed as a supported language."""
    assert registry.is_language_supported(
        "rust"
    ), "Rust must be registered in the language registry"


def test_registry_returns_rust_indexer(registry):
    """The registry should return a RustSCIPIndexer instance when requested."""
    from cicada.languages.rust.indexer import RustSCIPIndexer

    indexer = registry.get_indexer("rust")
    assert isinstance(indexer, RustSCIPIndexer)


def test_rust_indexer_metadata_exposes_expected_defaults():
    """Rust indexer exposes core metadata used by orchestration layers."""
    from cicada.languages.rust.indexer import RustSCIPIndexer

    indexer = RustSCIPIndexer()
    assert indexer.get_language_name() == "rust"
    assert indexer.get_file_extensions() == [".rs"]
    excluded = set(indexer.get_excluded_dirs())
    assert "target" in excluded
    assert ".git" in excluded
