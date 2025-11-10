"""
Comprehensive tests for cicada/tier.py - Tier configuration and resolution
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cicada.tier import (
    validate_tier_flags,
    get_tier_from_args,
    tier_to_methods,
    methods_to_tier,
    read_keyword_extraction_config,
    determine_tier,
    get_extraction_expansion_methods,
)


class TestValidateTierFlags:
    """Tests for validate_tier_flags() - Ensures only one tier flag specified"""

    def test_validate_tier_flags_valid_cases(self):
        """Test valid tier flag combinations"""
        valid_cases = [
            Namespace(fast=True, max=False, regular=False),  # Only fast
            Namespace(fast=False, max=True, regular=False),  # Only max
            Namespace(fast=False, max=False, regular=True),  # Only regular
            Namespace(fast=False, max=False, regular=False),  # No flags
        ]

        for args in valid_cases:
            validate_tier_flags(args)  # Should not raise

    def test_validate_tier_flags_invalid_cases(self):
        """Test invalid tier flag combinations that should exit with error"""
        invalid_cases = [
            Namespace(fast=True, max=True, regular=False),  # Both fast and max
            Namespace(fast=True, max=True, regular=True),  # All three flags
            Namespace(fast=False, max=True, regular=True),  # Max and regular
        ]

        for args in invalid_cases:
            with pytest.raises(SystemExit) as exc_info:
                validate_tier_flags(args)
            assert exc_info.value.code == 1

    def test_validate_tier_flags_missing_regular_attribute(self):
        """Should handle args without regular attribute (optional flag)"""
        args = Namespace(fast=False, max=False)
        # Should not raise - getattr with default handles missing attribute
        validate_tier_flags(args)


class TestGetTierFromArgs:
    """Tests for get_tier_from_args() - Extracts tier from CLI arguments"""

    def test_get_tier_from_args(self):
        """Test tier extraction from arguments"""
        test_cases = [
            (Namespace(fast=True, max=False, regular=False), "fast"),
            (Namespace(fast=False, max=True, regular=False), "max"),
            (Namespace(fast=False, max=False, regular=True), "regular"),
            (Namespace(fast=False, max=False, regular=False), None),
            (Namespace(fast=False, max=False), None),  # Missing regular attribute
            (Namespace(fast=True, max=True, regular=False), "fast"),  # Fast takes precedence
        ]

        for args, expected in test_cases:
            assert get_tier_from_args(args) == expected


class TestTierToMethods:
    """Tests for tier_to_methods() - Converts tier name to (extraction, expansion) methods"""

    def test_tier_to_methods(self):
        """Test tier to methods conversion"""
        test_cases = [
            ("fast", ("regular", "lemmi")),
            ("regular", ("bert", "glove")),
            ("max", ("bert", "fasttext")),
            ("unknown", ("regular", "lemmi")),  # Default for unknown
            ("", ("regular", "lemmi")),  # Default for empty
        ]

        for tier, expected in test_cases:
            assert tier_to_methods(tier) == expected


class TestMethodsToTier:
    """Tests for methods_to_tier() - Converts (extraction, expansion) methods back to tier name"""

    def test_methods_to_tier(self):
        """Test methods to tier conversion"""
        test_cases = [
            ("regular", "lemmi", "fast"),  # Regular extraction maps to fast
            ("regular", "glove", "fast"),
            ("regular", "fasttext", "fast"),
            ("bert", "fasttext", "max"),  # Bert + fasttext = max
            ("bert", "glove", "regular"),  # Bert + glove = regular
            ("bert", "unknown", "regular"),  # Bert + other = regular
            ("unknown", "lemmi", "regular"),  # Unknown defaults to regular
        ]

        for extraction, expansion, expected in test_cases:
            assert methods_to_tier(extraction, expansion) == expected


class TestDetermineTier:
    """Tests for determine_tier() - Main tier resolution logic"""

    def test_determine_tier_from_args_fast(self):
        """Should use args tier when specified (--fast)"""
        args = Namespace(fast=True, max=False, regular=False)
        assert determine_tier(args, None) == "fast"

    def test_determine_tier_from_args_max(self):
        """Should use args tier when specified (--max)"""
        args = Namespace(fast=False, max=True, regular=False)
        assert determine_tier(args, None) == "max"

    def test_determine_tier_from_args_regular(self):
        """Should use args tier when specified (--regular)"""
        args = Namespace(fast=False, max=False, regular=True)
        assert determine_tier(args, None) == "regular"

    def test_determine_tier_args_precedence_over_config(self, tmp_path):
        """Should prioritize args tier over config"""
        # Create config with max tier
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
keyword_extraction:
  method: bert
keyword_expansion:
  method: fasttext
"""
        )

        args = Namespace(fast=True, max=False, regular=False)

        # Mock get_config_path to return our test config
        # Note: get_config_path is imported inside read_keyword_extraction_config
        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            tier = determine_tier(args, tmp_path)
            # Args (fast) should take precedence over config (max)
            assert tier == "fast"

    def test_determine_tier_from_config(self, tmp_path):
        """Should fall back to config when no args tier specified"""
        # Create config with max tier
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
keyword_extraction:
  method: bert
keyword_expansion:
  method: fasttext
"""
        )

        args = Namespace(fast=False, max=False, regular=False)

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            tier = determine_tier(args, tmp_path)
            # Should read from config: bert + fasttext = max
            assert tier == "max"

    def test_determine_tier_default_when_no_config(self):
        """Should default to 'regular' when no tier specified and no config"""
        args = Namespace(fast=False, max=False, regular=False)
        # No repo_path provided
        tier = determine_tier(args, None)
        assert tier == "regular"

    def test_determine_tier_default_when_config_missing(self, tmp_path):
        """Should default to 'fast' when config file doesn't exist"""
        args = Namespace(fast=False, max=False, regular=False)

        # Config path that doesn't exist
        non_existent_config = tmp_path / "nonexistent" / "config.yaml"
        with patch("cicada.utils.storage.get_config_path", return_value=non_existent_config):
            tier = determine_tier(args, tmp_path)
            # Should default to fast since config doesn't exist
            # (read_keyword_extraction_config returns ("regular", "lemmi") which maps to "fast")
            assert tier == "fast"

    def test_determine_tier_handles_none_repo_path(self):
        """Should handle None repo_path gracefully"""
        args = Namespace(fast=False, max=False, regular=False)
        tier = determine_tier(args, repo_path=None)
        assert tier == "regular"


class TestGetExtractionExpansionMethods:
    """Tests for get_extraction_expansion_methods() - Convenience function for backward compatibility"""

    def test_get_extraction_expansion_methods(self):
        """Test extraction/expansion methods retrieval"""
        test_cases = [
            (Namespace(fast=False, max=False, regular=False), (None, None)),
            (Namespace(fast=True, max=False, regular=False), ("regular", "lemmi")),
            (Namespace(fast=False, max=False, regular=True), ("bert", "glove")),
            (Namespace(fast=False, max=True, regular=False), ("bert", "fasttext")),
        ]

        for args, expected in test_cases:
            assert get_extraction_expansion_methods(args) == expected

    def test_get_extraction_expansion_methods_integration(self):
        """Should integrate correctly with get_tier_from_args and tier_to_methods"""
        args = Namespace(fast=True, max=False, regular=False)

        # Manual check: get_tier_from_args -> tier_to_methods
        tier = get_tier_from_args(args)
        expected = tier_to_methods(tier)

        # Should match get_extraction_expansion_methods result
        result = get_extraction_expansion_methods(args)
        assert result == expected


class TestReadKeywordExtractionConfig:
    """Tests for read_keyword_extraction_config() - Already tested in test_indexer_comprehensive.py

    Note: This function was moved from indexer.py to tier.py during the watch PR.
    Tests for this function already exist in test_indexer_comprehensive.py:
    - test_read_keyword_extraction_config_with_existing_config
    - test_read_keyword_extraction_config_with_yaml_error

    We'll add a few integration tests here to ensure it works correctly with the tier module.
    """

    def test_read_keyword_extraction_config_returns_tuple(self, tmp_path):
        """Should return tuple of (extraction_method, expansion_method)"""
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
keyword_extraction:
  method: bert
keyword_expansion:
  method: glove
"""
        )

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            result = read_keyword_extraction_config(tmp_path)
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result == ("bert", "glove")

    def test_read_keyword_extraction_config_defaults_when_missing(self, tmp_path):
        """Should return default ('regular', 'lemmi') when config doesn't exist"""
        non_existent_config = tmp_path / "nonexistent" / "config.yaml"

        with patch("cicada.utils.storage.get_config_path", return_value=non_existent_config):
            result = read_keyword_extraction_config(tmp_path)
            assert result == ("regular", "lemmi")

    def test_read_keyword_extraction_config_integrates_with_methods_to_tier(self, tmp_path):
        """Should integrate correctly with methods_to_tier()"""
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
keyword_extraction:
  method: bert
keyword_expansion:
  method: fasttext
"""
        )

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            extraction, expansion = read_keyword_extraction_config(tmp_path)
            tier = methods_to_tier(extraction, expansion)
            # bert + fasttext should map to 'max'
            assert tier == "max"
