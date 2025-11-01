"""Configuration file schema and validation for Cicada.

This module provides a centralized way to load, validate, and manage
configuration files across the Cicada codebase.
"""

from pathlib import Path
from typing import Any

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""


class Config:
    """Represents a validated Cicada configuration."""

    def __init__(self, data: dict[str, Any]):
        """Initialize a Config from a dictionary.

        Args:
            data: The raw configuration dictionary

        Raises:
            ConfigValidationError: If the configuration is invalid
        """
        self.data = data
        self._validate()

    def _validate(self):
        """Validate the configuration structure and required fields.

        Raises:
            ConfigValidationError: If validation fails
        """
        # Require 'language' field
        if "language" not in self.data:
            raise ConfigValidationError(
                "Missing required field 'language' in config.yaml. "
                "Please specify the programming language (e.g., 'elixir', 'python')."
            )

        language = self.data["language"]
        if not isinstance(language, str):
            raise ConfigValidationError(
                f"Field 'language' must be a string, got {type(language).__name__}"
            )

        # Validate supported languages
        from cicada.languages import get_language_registry

        registry = get_language_registry()
        if not registry.is_language_supported(language):
            supported = ", ".join(registry.get_supported_languages())
            raise ConfigValidationError(
                f"Unsupported language '{language}'. Supported languages: {supported}"
            )

        # Validate repository section
        if "repository" not in self.data:
            raise ConfigValidationError("Missing required section 'repository'")

        if "path" not in self.data["repository"]:
            raise ConfigValidationError("Missing required field 'repository.path' in config.yaml")

        # Validate storage section
        if "storage" not in self.data:
            raise ConfigValidationError("Missing required section 'storage'")

        if "index_path" not in self.data["storage"]:
            raise ConfigValidationError(
                "Missing required field 'storage.index_path' in config.yaml"
            )

        # Keyword extraction is optional, but if present, validate structure
        if "keyword_extraction" in self.data:
            kw = self.data["keyword_extraction"]
            if not isinstance(kw, dict):
                raise ConfigValidationError("Field 'keyword_extraction' must be a mapping/object")

            if "method" in kw and kw["method"] not in [
                "lemminflect",
                "bert",
                "nltk",
                "spacy",
                "none",
            ]:
                raise ConfigValidationError(
                    f"Invalid keyword_extraction.method: {kw['method']}. "
                    "Must be one of: lemminflect, bert, nltk, spacy, none"
                )

            if "tier" in kw and kw["tier"] not in ["fast", "regular", "max"]:
                raise ConfigValidationError(
                    f"Invalid keyword_extraction.tier: {kw['tier']}. "
                    "Must be one of: fast, regular, max"
                )

    @property
    def language(self) -> str:
        """Get the configured language."""
        return self.data["language"]

    @property
    def repo_path(self) -> str:
        """Get the repository path."""
        return self.data["repository"]["path"]

    @property
    def index_path(self) -> str:
        """Get the index storage path."""
        return self.data["storage"]["index_path"]

    @property
    def keyword_method(self) -> str:
        """Get the keyword extraction method (default: lemminflect)."""
        return self.data.get("keyword_extraction", {}).get("method", "lemminflect")

    @property
    def keyword_tier(self) -> str:
        """Get the keyword extraction tier (default: regular)."""
        return self.data.get("keyword_extraction", {}).get("tier", "regular")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get a configuration value by key (dict-like access)."""
        return self.data[key]

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the configuration."""
        return key in self.data


def load_config(config_path: str | Path) -> Config:
    """Load and validate a configuration file.

    Args:
        config_path: Path to the config.yaml file

    Returns:
        A validated Config object

    Raises:
        FileNotFoundError: If the config file doesn't exist
        ConfigValidationError: If the configuration is invalid
        yaml.YAMLError: If the YAML is malformed
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ConfigValidationError(
            f"Config file must contain a YAML mapping/object, got {type(data).__name__}"
        )

    return Config(data)


def create_default_config(
    language: str,
    repo_path: str | Path,
    index_path: str | Path,
    keyword_method: str = "lemminflect",
    keyword_tier: str = "regular",
) -> dict[str, Any]:
    """Create a default configuration dictionary.

    Args:
        language: Programming language (e.g., 'elixir', 'python')
        repo_path: Path to the repository
        index_path: Path to store the index
        keyword_method: Keyword extraction method
        keyword_tier: Keyword extraction tier

    Returns:
        A configuration dictionary
    """
    return {
        "language": language,
        "repository": {"path": str(repo_path)},
        "storage": {"index_path": str(index_path)},
        "keyword_extraction": {"method": keyword_method, "tier": keyword_tier},
    }


def save_config(config_data: dict[str, Any], config_path: str | Path):
    """Save a configuration dictionary to a YAML file.

    Args:
        config_data: The configuration dictionary
        config_path: Path where to save the config file
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
