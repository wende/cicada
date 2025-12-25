"""
Tests for cicada/index_mode.py - Indexing mode configuration and resolution.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cicada.index_mode import (
    INDEX_MODE_EMBEDDINGS,
    INDEX_MODE_KEYWORDS,
    determine_indexing_mode,
    ensure_supported_mode,
    get_mode_from_args,
    read_indexing_mode_config,
    validate_mode_flags,
)


class TestValidateModeFlags:
    def test_valid_cases(self):
        valid_cases = [
            Namespace(keywords=True, embeddings=False),
            Namespace(keywords=False, embeddings=True),
            Namespace(keywords=False, embeddings=False),
        ]

        for args in valid_cases:
            validate_mode_flags(args)

    def test_invalid_cases(self):
        args = Namespace(keywords=True, embeddings=True)
        with pytest.raises(SystemExit) as exc_info:
            validate_mode_flags(args)
        assert exc_info.value.code == 1

    def test_require_force_requires_flag(self):
        args = Namespace(keywords=False, embeddings=False, force=True)
        with pytest.raises(SystemExit) as exc_info:
            validate_mode_flags(args, require_force=True)
        assert exc_info.value.code == 2

    def test_require_force_requires_force(self):
        args = Namespace(keywords=True, embeddings=False, force=False)
        with pytest.raises(SystemExit) as exc_info:
            validate_mode_flags(args, require_force=True)
        assert exc_info.value.code == 2


class TestGetModeFromArgs:
    def test_get_mode_from_args(self):
        test_cases = [
            (Namespace(keywords=True, embeddings=False), INDEX_MODE_KEYWORDS),
            (Namespace(keywords=False, embeddings=True), INDEX_MODE_EMBEDDINGS),
            (Namespace(keywords=False, embeddings=False), None),
        ]

        for args, expected in test_cases:
            assert get_mode_from_args(args) == expected


class TestReadIndexingModeConfig:
    def test_read_mode_from_new_config(self, tmp_path):
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
indexing:
  mode: embeddings
"""
        )

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            assert read_indexing_mode_config(tmp_path) == INDEX_MODE_EMBEDDINGS

    def test_read_mode_from_legacy_config(self, tmp_path):
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
keyword_extraction:
  method: regular
keyword_expansion:
  method: lemmi
"""
        )

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            assert read_indexing_mode_config(tmp_path) == INDEX_MODE_KEYWORDS

    def test_default_when_config_missing(self, tmp_path):
        config_file = tmp_path / "missing" / "config.yaml"
        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            assert read_indexing_mode_config(tmp_path) == INDEX_MODE_KEYWORDS


class TestDetermineIndexingMode:
    def test_args_override_config(self, tmp_path):
        args = Namespace(keywords=True, embeddings=False)
        assert determine_indexing_mode(args, tmp_path) == INDEX_MODE_KEYWORDS

    def test_config_used_when_no_args(self, tmp_path):
        config_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
indexing:
  mode: embeddings
"""
        )

        args = Namespace(keywords=False, embeddings=False)
        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            assert determine_indexing_mode(args, tmp_path) == INDEX_MODE_EMBEDDINGS

    def test_default_when_no_args_or_config(self):
        args = Namespace(keywords=False, embeddings=False)
        assert determine_indexing_mode(args, None) == INDEX_MODE_KEYWORDS


class TestEnsureSupportedMode:
    def test_keywords_ok(self):
        ensure_supported_mode(INDEX_MODE_KEYWORDS)

    def test_embeddings_raises(self):
        with pytest.raises(NotImplementedError):
            ensure_supported_mode(INDEX_MODE_EMBEDDINGS)
