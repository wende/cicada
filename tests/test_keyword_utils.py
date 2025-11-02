"""Tests for universal keyword extraction utilities."""

import tempfile
from pathlib import Path

import pytest
import yaml

from cicada.utils.keyword_utils import (
    create_keyword_extractor,
    get_keyword_extractor_from_config,
    read_keyword_extraction_config,
)
from cicada.utils.storage import get_config_path


class TestReadKeywordExtractionConfig:
    """Test reading keyword extraction configuration."""

    def test_read_config_with_lemminflect(self, tmp_path):
        """Test reading config with lemminflect method."""
        # Create config file
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
            "keyword_extraction": {"method": "lemminflect", "tier": "regular"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock get_config_path to return our test file
        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            method, tier = read_keyword_extraction_config(tmp_path)
            assert method == "lemminflect"
            assert tier == "regular"
        finally:
            kw_utils.get_config_path = original_get_config

    def test_read_config_with_bert(self, tmp_path):
        """Test reading config with BERT method."""
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
            "keyword_extraction": {"method": "bert", "tier": "fast"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            method, tier = read_keyword_extraction_config(tmp_path)
            assert method == "bert"
            assert tier == "fast"
        finally:
            kw_utils.get_config_path = original_get_config

    def test_read_config_defaults(self, tmp_path):
        """Test default values when config doesn't exist."""
        method, tier = read_keyword_extraction_config(tmp_path)
        assert method == "lemminflect"
        assert tier == "regular"

    def test_read_config_missing_keyword_section(self, tmp_path):
        """Test defaults when keyword_extraction section is missing."""
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            method, tier = read_keyword_extraction_config(tmp_path)
            assert method == "lemminflect"
            assert tier == "regular"
        finally:
            kw_utils.get_config_path = original_get_config


class TestCreateKeywordExtractor:
    """Test keyword extractor factory function."""

    def test_create_lemminflect_extractor(self):
        """Test creating lemminflect extractor."""
        extractor = create_keyword_extractor("lemminflect", "regular", verbose=False)
        assert extractor is not None

        from cicada.lightweight_keyword_extractor import LightweightKeywordExtractor

        assert isinstance(extractor, LightweightKeywordExtractor)

    def test_create_none_extractor(self):
        """Test that 'none' method returns None."""
        extractor = create_keyword_extractor("none", "regular", verbose=False)
        assert extractor is None

    @pytest.mark.slow
    @pytest.mark.skipif(
        "SKIP_SLOW_TESTS" in __import__("os").environ, reason="Skipping slow BERT loading test"
    )
    def test_create_bert_extractor_if_installed(self):
        """Test BERT extractor creation (slow - loads models)."""
        # This test loads actual BERT models if installed (takes 4-5 seconds)
        # Marked as @pytest.mark.slow and skipped in CI
        try:
            extractor = create_keyword_extractor("bert", "fast", verbose=False)
            assert extractor is not None
        except Exception as e:
            pytest.fail(f"BERT extractor creation should not crash: {e}")

    def test_extractor_functional(self):
        """Test that created extractor actually works."""
        extractor = create_keyword_extractor("lemminflect", "regular", verbose=False)
        keywords = extractor.extract_keywords_simple("This is a test function for authentication")
        assert isinstance(keywords, list)
        assert len(keywords) > 0


class TestGetKeywordExtractorFromConfig:
    """Test convenience function for getting extractor from config."""

    def test_get_extractor_enabled(self, tmp_path):
        """Test getting extractor when extraction is enabled."""
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
            "keyword_extraction": {"method": "lemminflect", "tier": "regular"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            extract_keywords, extractor = get_keyword_extractor_from_config(tmp_path, verbose=False)
            assert extract_keywords is True
            assert extractor is not None
        finally:
            kw_utils.get_config_path = original_get_config

    def test_get_extractor_disabled(self, tmp_path):
        """Test getting extractor when extraction is disabled (method=none)."""
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
            "keyword_extraction": {"method": "none", "tier": "regular"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            extract_keywords, extractor = get_keyword_extractor_from_config(tmp_path, verbose=False)
            assert extract_keywords is False
            assert extractor is None
        finally:
            kw_utils.get_config_path = original_get_config
