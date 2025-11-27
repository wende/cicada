"""Tests for cicada.agents.installer module."""

from pathlib import Path

import pytest

from cicada.agents.installer import install_agent


class TestInstallAgent:
    """Test agent installation."""

    def test_install_agent_creates_directory(self, tmp_path):
        """Test that install_agent creates agents directory."""
        install_agent(tmp_path, "cicada-code-explorer.md")

        agents_dir = tmp_path / "agents"
        assert agents_dir.is_dir(), "agents directory should be created"

    def test_install_agent_creates_file(self, tmp_path):
        """Test that install_agent creates the agent file."""
        install_agent(tmp_path, "cicada-code-explorer.md")

        agent_file = tmp_path / "agents" / "cicada-code-explorer.md"
        assert agent_file.exists(), "cicada-code-explorer.md should be created"
        assert agent_file.is_file(), "cicada-code-explorer.md should be a file"

    def test_install_agent_writes_template_content(self, tmp_path):
        """Test that install_agent writes template content."""
        install_agent(tmp_path, "cicada-code-explorer.md")

        agent_file = tmp_path / "agents" / "cicada-code-explorer.md"
        content = agent_file.read_text()

        # Verify content contains expected parts
        assert "cicada-code-explorer" in content
        assert "Fast code exploration" in content
