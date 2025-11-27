"""Tests for agents command integration."""

from unittest.mock import patch

import pytest

from cicada.commands import handle_agents_install, get_argument_parser


class TestAgentsInstall:
    """Test agents install command."""

    @patch("cicada.agents.installer.install_agent")
    def test_agents_install_calls_installer(self, mock_install):
        """Test that agents install handler calls install_agent."""
        # Call the install handler
        handle_agents_install()

        # Verify install_agent was called
        mock_install.assert_called_once()

    def test_agents_install_prints_success(self, tmp_path, capsys, monkeypatch):
        """Test that command prints success message."""
        # Mock current directory to temp path
        monkeypatch.chdir(tmp_path)

        handle_agents_install()

        # Capture output
        captured = capsys.readouterr()

        # Verify success message
        assert "✓ Installed cicada-code-explorer.md" in captured.out
        assert "Installation complete" in captured.out

    def test_agents_command_in_argument_parser(self):
        """Test that agents command is in argument parser."""
        parser = get_argument_parser()
        args = parser.parse_args(["agents", "install"])

        assert args.command == "agents"
        assert args.agents_command == "install"

    def test_agents_install_local_by_default(self, tmp_path, capsys, monkeypatch):
        """Test that installation is local to project."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Call handler
        handle_agents_install()

        # Verify installation in project .claude
        agent_file = tmp_path / ".claude" / "agents" / "cicada-code-explorer.md"
        assert agent_file.exists()

        # Verify success message
        captured = capsys.readouterr()
        assert "Installation complete" in captured.out
