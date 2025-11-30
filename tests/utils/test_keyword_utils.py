"""
Comprehensive tests for cicada/utils/keyword_utils.py
"""

from unittest.mock import MagicMock, patch

import yaml

from cicada.utils.keyword_utils import (
    create_keyword_extractor,
    get_keyword_extractor_from_config,
    read_keyword_extraction_config,
)


class TestReadKeywordExtractionConfig:
    """Tests for read_keyword_extraction_config function"""

    def test_default_when_no_config_file(self, tmp_path, mock_home_dir):
        """Should return default ('regular', 'lemmi') when config doesn't exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

        assert extraction_method == "regular"
        assert expansion_method == "lemmi"

    def test_new_config_format_regular_lemmi(self, tmp_path, mock_home_dir):
        """Should read new config format with regular + lemmi"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir and config
        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)

        config_path = storage_dir / "config.yaml"
        config = {
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
        }

        # Mock get_config_path to return our test config
        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_new_config_format_bert_glove(self, tmp_path, mock_home_dir):
        """Should read new config format with bert + glove"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "glove"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "bert"
            assert expansion_method == "glove"

    def test_new_config_format_bert_fasttext(self, tmp_path, mock_home_dir):
        """Should read new config format with bert + fasttext"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "fasttext"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "bert"
            assert expansion_method == "fasttext"

    def test_legacy_tier_fast(self, tmp_path, mock_home_dir):
        """Should map legacy tier 'fast' to ('regular', 'lemmi')"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {"keyword_extraction": {"method": "lemminflect", "tier": "fast"}}

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_legacy_tier_regular(self, tmp_path, mock_home_dir):
        """Should map legacy tier 'regular' to ('regular', 'glove')"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {"keyword_extraction": {"tier": "regular"}}

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "glove"

    def test_legacy_tier_max(self, tmp_path, mock_home_dir):
        """Should map legacy tier 'max' to ('bert', 'fasttext')"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {"keyword_extraction": {"tier": "max"}}

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "bert"
            assert expansion_method == "fasttext"

    def test_legacy_tier_unrecognized_falls_back_to_method(self, tmp_path, mock_home_dir):
        """Should fall back to method-based logic for unrecognized tier"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "bert", "tier": "unknown"},
            "keyword_expansion": {"method": "glove"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "bert"
            assert expansion_method == "glove"

    def test_legacy_lemminflect_method_maps_to_regular(self, tmp_path, mock_home_dir):
        """Should map legacy 'lemminflect' method to 'regular'"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "lemminflect"},
            "keyword_expansion": {"method": "lemmi"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_empty_config_returns_defaults(self, tmp_path, mock_home_dir):
        """Should return defaults when config exists but is empty"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump({}, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_missing_extraction_config_uses_defaults(self, tmp_path, mock_home_dir):
        """Should use defaults when keyword_extraction section is missing"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {"some_other_config": "value"}

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_yaml_parse_error_returns_defaults(self, tmp_path, mock_home_dir):
        """Should return defaults when YAML parsing fails"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            # Write invalid YAML
            with open(config_path, "w") as f:
                f.write("invalid: yaml: content:\n  - broken")

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_file_read_error_returns_defaults(self, tmp_path, mock_home_dir):
        """Should return defaults when file read fails"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            # Create config file
            config_path.touch()

            # Mock open to raise an exception
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

                assert extraction_method == "regular"
                assert expansion_method == "lemmi"


class TestCreateKeywordExtractor:
    """Tests for create_keyword_extractor function"""

    def test_none_extraction_method_returns_none(self):
        """Should return None when extraction_method is 'none'"""
        extractor = create_keyword_extractor("none", "lemmi", verbose=False)
        assert extractor is None

    def test_regular_extraction_creates_regular_extractor(self):
        """Should create RegularKeywordExtractor for 'regular' method"""
        extractor = create_keyword_extractor("regular", "lemmi", verbose=False)

        assert extractor is not None
        assert extractor.__class__.__name__ == "RegularKeywordExtractor"

    def test_regular_extraction_with_verbose(self, capsys):
        """Should print message when verbose=True for regular extractor"""
        extractor = create_keyword_extractor("regular", "lemmi", verbose=True)

        assert extractor is not None

        # Check stderr output
        captured = capsys.readouterr()
        assert "regular extractor" in captured.err.lower()

    def test_bert_extraction_creates_keybert_extractor(self):
        """Should create KeyBERTExtractor for 'bert' method when available"""
        # Mock KeyBERTExtractor to avoid actual PyTorch import
        mock_extractor = MagicMock()
        mock_extractor.__class__.__name__ = "KeyBERTExtractor"

        with patch(
            "cicada.extractors.keybert.KeyBERTExtractor",
            return_value=mock_extractor,
        ):
            extractor = create_keyword_extractor("bert", "glove", verbose=False)

            assert extractor is not None
            assert extractor.__class__.__name__ == "KeyBERTExtractor"

    def test_bert_extraction_with_verbose(self, capsys):
        """Should print message when verbose=True for bert extractor"""
        # Mock KeyBERTExtractor to avoid actual PyTorch import
        mock_extractor = MagicMock()
        mock_extractor.__class__.__name__ = "KeyBERTExtractor"

        with patch(
            "cicada.extractors.keybert.KeyBERTExtractor",
            return_value=mock_extractor,
        ):
            extractor = create_keyword_extractor("bert", "glove", verbose=True)

            assert extractor is not None

            captured = capsys.readouterr()
            assert "keybert" in captured.err.lower() or "extractor" in captured.err.lower()

    def test_bert_import_error_falls_back_to_regular(self, capsys):
        """Should fall back to regular extractor when KeyBERT import fails"""
        # Create a mock module that raises ImportError when trying to import KeyBERTExtractor
        import sys

        # Save original modules
        original_keybert_module = sys.modules.get("cicada.extractors.keybert")

        # Remove the module to force re-import
        if "cicada.extractors.keybert" in sys.modules:
            del sys.modules["cicada.extractors.keybert"]

        # Create a mock module that raises ImportError
        mock_module = MagicMock()
        mock_module.KeyBERTExtractor = MagicMock(side_effect=ImportError("KeyBERT not available"))

        sys.modules["cicada.extractors.keybert"] = mock_module

        try:
            extractor = create_keyword_extractor("bert", "glove", verbose=True)

            assert extractor is not None
            assert extractor.__class__.__name__ == "RegularKeywordExtractor"

            captured = capsys.readouterr()
            assert "fallback" in captured.err.lower() or "regular" in captured.err.lower()
        finally:
            # Restore original module
            if original_keybert_module is not None:
                sys.modules["cicada.extractors.keybert"] = original_keybert_module
            elif "cicada.extractors.keybert" in sys.modules:
                del sys.modules["cicada.extractors.keybert"]

    def test_bert_initialization_error_returns_none(self, capsys):
        """Should return None and print warning when extractor initialization fails"""
        # Mock KeyBERTExtractor to raise an exception during initialization
        mock_extractor = MagicMock(side_effect=Exception("Model download failed"))

        with patch(
            "cicada.extractors.keybert.KeyBERTExtractor",
            mock_extractor,
        ):
            extractor = create_keyword_extractor("bert", "glove", verbose=True)

            # Should return None when initialization fails
            assert extractor is None

            captured = capsys.readouterr()
            # Check both stdout and stderr for warning messages
            output = (captured.out + captured.err).lower()
            assert "warning" in output or "could not initialize" in output

    def test_unknown_extraction_method_defaults_to_regular(self):
        """Should default to regular extractor for unknown methods"""
        extractor = create_keyword_extractor("unknown_method", "lemmi", verbose=False)

        assert extractor is not None
        assert extractor.__class__.__name__ == "RegularKeywordExtractor"

    def test_different_expansion_methods_accepted(self):
        """Should accept different expansion methods without error"""
        # Test all valid expansion methods
        for expansion in ["lemmi", "glove", "fasttext"]:
            extractor = create_keyword_extractor("regular", expansion, verbose=False)
            assert extractor is not None


class TestGetKeywordExtractorFromConfig:
    """Tests for get_keyword_extractor_from_config function"""

    def test_returns_tuple_of_bool_and_extractor(self, tmp_path, mock_home_dir):
        """Should return (bool, extractor) tuple"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        result = get_keyword_extractor_from_config(repo_path, verbose=False)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)

    def test_extract_keywords_true_for_regular_method(self, tmp_path, mock_home_dir):
        """Should return extract_keywords=True for 'regular' method"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)

            assert extract_keywords is True
            assert extractor is not None

    def test_extract_keywords_true_for_bert_method(self, tmp_path, mock_home_dir):
        """Should return extract_keywords=True for 'bert' method"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "glove"},
        }

        # Mock KeyBERTExtractor to avoid actual PyTorch import
        mock_extractor = MagicMock()
        mock_extractor.__class__.__name__ = "KeyBERTExtractor"

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with patch(
                "cicada.extractors.keybert.KeyBERTExtractor",
                return_value=mock_extractor,
            ):
                with open(config_path, "w") as f:
                    yaml.dump(config, f)

                extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)

                assert extract_keywords is True
                assert extractor is not None

    def test_extract_keywords_false_for_none_method(self, tmp_path, mock_home_dir):
        """Should return extract_keywords=False for 'none' method"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "none"},
            "keyword_expansion": {"method": "lemmi"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)

            assert extract_keywords is False
            assert extractor is None

    def test_extractor_none_when_extraction_disabled(self, tmp_path, mock_home_dir):
        """Should return None extractor when extraction is disabled"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {"keyword_extraction": {"method": "none"}}

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)

            assert extract_keywords is False
            assert extractor is None

    def test_verbose_flag_passed_to_extractor(self, tmp_path, mock_home_dir, capsys):
        """Should pass verbose flag to extractor creation"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "regular"},
            "keyword_expansion": {"method": "lemmi"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            get_keyword_extractor_from_config(repo_path, verbose=True)

            captured = capsys.readouterr()
            assert "extractor" in captured.err.lower()

    def test_default_config_creates_regular_extractor(self, tmp_path, mock_home_dir):
        """Should create regular extractor when using default config"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # No config file exists, should use defaults
        extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)

        assert extract_keywords is True
        assert extractor is not None
        assert extractor.__class__.__name__ == "RegularKeywordExtractor"

    def test_integrates_read_and_create_functions(self, tmp_path, mock_home_dir):
        """Should properly integrate read_keyword_extraction_config and create_keyword_extractor"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        # Test with legacy tier config
        config = {"keyword_extraction": {"tier": "max"}}

        # Mock KeyBERTExtractor to avoid actual PyTorch import
        # tier: max maps to bert + fasttext
        mock_extractor = MagicMock()
        mock_extractor.__class__.__name__ = "KeyBERTExtractor"

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with patch(
                "cicada.extractors.keybert.KeyBERTExtractor",
                return_value=mock_extractor,
            ):
                with open(config_path, "w") as f:
                    yaml.dump(config, f)

                extract_keywords, extractor = get_keyword_extractor_from_config(repo_path)

                # tier: max should map to bert + fasttext
                assert extract_keywords is True
                assert extractor is not None


class TestEdgeCases:
    """Edge case and integration tests"""

    def test_accepts_path_object_and_string(self, tmp_path, mock_home_dir):
        """Should accept both Path and str types for repo_path"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Test with Path object
        result1 = read_keyword_extraction_config(repo_path)

        # Test with string
        result2 = read_keyword_extraction_config(str(repo_path))

        assert result1 == result2
        assert result1 == ("regular", "lemmi")

    def test_config_with_null_values(self, tmp_path, mock_home_dir):
        """Should handle config with null values gracefully"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            # Write YAML with null values
            with open(config_path, "w") as f:
                f.write("keyword_extraction: null\n")

            extraction_method, expansion_method = read_keyword_extraction_config(repo_path)

            # Should handle None/null gracefully and use defaults
            assert extraction_method == "regular"
            assert expansion_method == "lemmi"

    def test_concurrent_config_reads(self, tmp_path, mock_home_dir):
        """Should handle multiple reads of the same config safely"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = mock_home_dir / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        config_path = storage_dir / "config.yaml"

        config = {
            "keyword_extraction": {"method": "bert"},
            "keyword_expansion": {"method": "glove"},
        }

        with patch("cicada.utils.keyword_utils.get_config_path", return_value=config_path):
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            # Read config multiple times
            result1 = read_keyword_extraction_config(repo_path)
            result2 = read_keyword_extraction_config(repo_path)
            result3 = read_keyword_extraction_config(repo_path)

            assert result1 == result2 == result3
            assert result1 == ("bert", "glove")
