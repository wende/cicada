"""Tests for cicada.agents.generator module."""

import pytest
import yaml

from cicada.agents.generator import load_template


class TestTemplateLoading:
    """Test template loading from package resources."""

    def test_load_explorer_template_returns_string(self):
        """Test loading cicada-code-explorer template returns string."""
        content = load_template("cicada-code-explorer.md")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_explorer_template_has_valid_yaml(self):
        """Test template has valid YAML frontmatter."""
        content = load_template("cicada-code-explorer.md")

        # Extract YAML frontmatter (between --- markers)
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Template must have YAML frontmatter between --- markers"

        yaml_content = parts[1].strip()
        metadata = yaml.safe_load(yaml_content)

        # Verify required fields
        assert isinstance(metadata, dict)
        assert "name" in metadata
        assert metadata["name"] == "cicada-code-explorer"
        assert "description" in metadata
        assert "model" in metadata
