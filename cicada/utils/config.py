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
        # Default to 'elixir' for backward compatibility
        if "language" not in self.data:
            self.data["language"] = "elixir"

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
                "regular",
                "bert",
                "lemminflect",  # Legacy support
                "nltk",
                "spacy",
                "none",
            ]:
                raise ConfigValidationError(
                    f"Invalid keyword_extraction.method: {kw['method']}. "
                    "Must be one of: regular, bert, lemminflect, nltk, spacy, none"
                )

        # Keyword expansion is optional, but if present, validate structure
        if "keyword_expansion" in self.data:
            kw_exp = self.data["keyword_expansion"]
            if not isinstance(kw_exp, dict):
                raise ConfigValidationError("Field 'keyword_expansion' must be a mapping/object")

            if "method" in kw_exp and kw_exp["method"] not in [
                "lemmi",
                "glove",
                "fasttext",
                "none",
            ]:
                raise ConfigValidationError(
                    f"Invalid keyword_expansion.method: {kw_exp['method']}. "
                    "Must be one of: lemmi, glove, fasttext, none"
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
    def extraction_method(self) -> str:
        """Get the keyword extraction method (default: regular)."""
        # Support legacy 'method' field and new 'method' field
        method = self.data.get("keyword_extraction", {}).get("method", "regular")
        # Map legacy "lemminflect" to "regular"
        if method == "lemminflect":
            method = "regular"
        return method

    @property
    def expansion_method(self) -> str:
        """Get the keyword expansion method (default: lemmi)."""
        return self.data.get("keyword_expansion", {}).get("method", "lemmi")

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
    extraction_method: str = "regular",
    expansion_method: str = "lemmi",
) -> dict[str, Any]:
    """Create a default configuration dictionary.

    Args:
        language: Programming language (e.g., 'elixir', 'python')
        repo_path: Path to the repository
        index_path: Path to store the index
        extraction_method: Keyword extraction method ('regular' or 'bert')
        expansion_method: Keyword expansion method ('lemmi', 'glove', or 'fasttext')

    Returns:
        A configuration dictionary
    """
    return {
        "language": language,
        "repository": {"path": str(repo_path)},
        "storage": {"index_path": str(index_path)},
        "keyword_extraction": {"method": extraction_method},
        "keyword_expansion": {"method": expansion_method},
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
