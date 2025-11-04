"""Tests for configuration file validation."""

import pytest
import yaml

from cicada.utils.config import (
    Config,
    ConfigValidationError,
    create_default_config,
    load_config,
    save_config,
)


def test_valid_config(tmp_path):
    """Test loading a valid configuration."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
        "keyword_extraction": {"method": "regular"},
        "keyword_expansion": {"method": "glove"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = load_config(config_file)
    assert config.language == "elixir"
    assert config.repo_path == "/path/to/repo"
    assert config.index_path == "/path/to/index.json"
    assert config.extraction_method == "regular"
    assert config.expansion_method == "glove"


def test_missing_language_field(tmp_path):
    """Test that missing 'language' field raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Missing required field 'language'"):
        load_config(config_file)


def test_invalid_language_type(tmp_path):
    """Test that non-string language value raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": 123,  # Should be a string
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="must be a string"):
        load_config(config_file)


def test_unsupported_language(tmp_path):
    """Test that unsupported language raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "cobol",  # Not supported
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Unsupported language 'cobol'"):
        load_config(config_file)


def test_missing_repository_section(tmp_path):
    """Test that missing repository section raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "storage": {"index_path": "/path/to/index.json"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Missing required section 'repository'"):
        load_config(config_file)


def test_missing_repo_path(tmp_path):
    """Test that missing repository.path raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {},  # Missing path
        "storage": {"index_path": "/path/to/index.json"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Missing required field 'repository.path'"):
        load_config(config_file)


def test_missing_storage_section(tmp_path):
    """Test that missing storage section raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Missing required section 'storage'"):
        load_config(config_file)


def test_missing_index_path(tmp_path):
    """Test that missing storage.index_path raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
        "storage": {},  # Missing index_path
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Missing required field 'storage.index_path'"):
        load_config(config_file)


def test_invalid_keyword_method(tmp_path):
    """Test that invalid keyword extraction method raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
        "keyword_extraction": {"method": "invalid_method"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Invalid keyword_extraction.method"):
        load_config(config_file)


def test_invalid_keyword_tier(tmp_path):
    """Test that invalid keyword expansion method raises an error."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
        "keyword_expansion": {"method": "thorough"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ConfigValidationError, match="Invalid keyword_expansion.method"):
        load_config(config_file)


def test_optional_keyword_extraction(tmp_path):
    """Test that keyword_extraction section is optional."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    config = load_config(config_file)
    assert config.extraction_method == "regular"  # Default
    assert config.expansion_method == "lemmi"  # Default


def test_config_file_not_found():
    """Test that missing config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_malformed_yaml(tmp_path):
    """Test that malformed YAML raises an error."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        f.write("{ invalid yaml content")

    with pytest.raises(yaml.YAMLError):
        load_config(config_file)


def test_non_dict_yaml(tmp_path):
    """Test that non-dict YAML content raises an error."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        f.write("- item1\n- item2\n")  # YAML list, not dict

    with pytest.raises(ConfigValidationError, match="must contain a YAML mapping/object"):
        load_config(config_file)


def test_create_default_config():
    """Test creating a default configuration."""
    config_data = create_default_config(
        language="elixir",
        repo_path="/path/to/repo",
        index_path="/path/to/index.json",
        extraction_method="bert",
        expansion_method="fasttext",
    )

    assert config_data["language"] == "elixir"
    assert config_data["repository"]["path"] == "/path/to/repo"
    assert config_data["storage"]["index_path"] == "/path/to/index.json"
    assert config_data["keyword_extraction"]["method"] == "bert"
    assert config_data["keyword_expansion"]["method"] == "fasttext"


def test_save_and_load_config(tmp_path):
    """Test saving and loading configuration."""
    config_file = tmp_path / "subdir" / "config.yaml"
    config_data = create_default_config(
        language="elixir",
        repo_path="/path/to/repo",
        index_path="/path/to/index.json",
    )

    save_config(config_data, config_file)
    assert config_file.exists()

    loaded_config = load_config(config_file)
    assert loaded_config.language == "elixir"
    assert loaded_config.repo_path == "/path/to/repo"
    assert loaded_config.index_path == "/path/to/index.json"


def test_config_dict_access():
    """Test dictionary-like access to configuration."""
    config_data = {
        "language": "elixir",
        "repository": {"path": "/path/to/repo"},
        "storage": {"index_path": "/path/to/index.json"},
        "custom_field": "custom_value",
    }

    config = Config(config_data)

    # Test __getitem__
    assert config["language"] == "elixir"
    assert config["custom_field"] == "custom_value"

    # Test __contains__
    assert "language" in config
    assert "custom_field" in config
    assert "nonexistent" not in config

    # Test get with default
    assert config.get("custom_field") == "custom_value"
    assert config.get("nonexistent", "default") == "default"


def test_config_caching_staleness(tmp_path):
    """Test that config changes are detected between multiple tool calls.

    This edge case test verifies that config is not cached in a way that
    would hide changes made between multiple indexing or tool calls.
    See: https://github.com/anthropics/cicada/issues/XXX
    """
    config_file = tmp_path / "config.yaml"

    # Initial config - fast tier
    initial_config = {
        "language": "elixir",
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(tmp_path / "index.json")},
        "keyword_extraction": {"method": "regular"},
        "keyword_expansion": {"method": "lemmi"},
    }

    with open(config_file, "w") as f:
        yaml.dump(initial_config, f)

    # Load config first time
    config1 = load_config(config_file)
    assert config1.extraction_method == "regular"
    assert config1.expansion_method == "lemmi"

    # Update config - max tier (simulating user running with --max flag)
    updated_config = {
        "language": "elixir",
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(tmp_path / "index.json")},
        "keyword_extraction": {"method": "bert"},
        "keyword_expansion": {"method": "fasttext"},
    }

    with open(config_file, "w") as f:
        yaml.dump(updated_config, f)

    # Load config second time - should see changes
    config2 = load_config(config_file)
    assert config2.extraction_method == "bert", (
        "Config changes should be detected on reload. "
        "If this fails, config may be cached inappropriately."
    )
    assert (
        config2.expansion_method == "fasttext"
    ), "Config expansion method should update when file changes."

    # Verify they're different
    assert config1.extraction_method != config2.extraction_method
    assert config1.expansion_method != config2.expansion_method
