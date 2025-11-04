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
        """Test reading config with regular extraction and lemmi expansion."""
        # Create config file
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock get_config_path to return our test file
        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            extraction_method, expansion_method = read_keyword_extraction_config(tmp_path)
            assert extraction_method == "regular"
            assert expansion_method == "lemmi"
        finally:
            kw_utils.get_config_path = original_get_config

    def test_read_config_with_bert(self, tmp_path):
        """Test reading config with BERT extraction and glove expansion."""
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "language": "python",
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(config_dir / "index.json")},
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "glove"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        import cicada.utils.keyword_utils as kw_utils

        original_get_config = kw_utils.get_config_path
        kw_utils.get_config_path = lambda _: config_file

        try:
            extraction_method, expansion_method = read_keyword_extraction_config(tmp_path)
            assert extraction_method == "bert"
            assert expansion_method == "glove"
        finally:
            kw_utils.get_config_path = original_get_config

    def test_read_config_defaults(self, tmp_path):
        """Test default values when config doesn't exist."""
        extraction_method, expansion_method = read_keyword_extraction_config(tmp_path)
        assert extraction_method == "regular"
        assert expansion_method == "lemmi"

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
            extraction_method, expansion_method = read_keyword_extraction_config(tmp_path)
            assert extraction_method == "regular"
            assert expansion_method == "lemmi"
        finally:
            kw_utils.get_config_path = original_get_config


class TestCreateKeywordExtractor:
    """Test keyword extractor factory function."""

    def test_create_lemminflect_extractor(self):
        """Test creating regular extractor."""
        extractor = create_keyword_extractor("regular", "lemmi", verbose=False)
        assert extractor is not None

        from cicada.languages.elixir.extractors.keyword import RegularKeywordExtractor

        assert isinstance(extractor, RegularKeywordExtractor)

    def test_create_none_extractor(self):
        """Test that 'none' method returns None."""
        extractor = create_keyword_extractor("none", "lemmi", verbose=False)
        assert extractor is None

    def test_create_bert_extractor(self):
        """Test BERT extractor factory creation (with mock)."""
        from unittest.mock import MagicMock, patch

        # Mock KeyBERTExtractor to avoid loading actual models
        mock_extractor = MagicMock()
        with patch(
            "cicada.languages.elixir.extractors.keybert.KeyBERTExtractor",
            return_value=mock_extractor,
        ):
            extractor = create_keyword_extractor("bert", "glove", verbose=False)
            assert extractor is not None
            assert extractor is mock_extractor

    def test_extractor_functional(self):
        """Test that created extractor actually works."""
        extractor = create_keyword_extractor("regular", "lemmi", verbose=False)
        keywords = extractor.extract_keywords_simple("This is a test function for authentication")
        assert isinstance(keywords, dict)
        assert len(keywords) > 0
        # Verify it returns keyword -> score mappings
        for keyword, score in keywords.items():
            assert isinstance(keyword, str)
            assert isinstance(score, (int, float))
            assert score > 0


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
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
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
            "keyword_extraction": {"method": "none"},
            "keyword_expansion": {"method": "lemmi"},
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
