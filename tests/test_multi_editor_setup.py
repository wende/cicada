"""
Integration tests for multi-editor setup workflow.

Tests that cicada can be run multiple times with different editors
without breaking, ensuring users can set up multiple environments.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cicada.setup import get_mcp_config_for_editor, setup
from cicada.utils import get_storage_dir


@pytest.fixture
def mock_elixir_repo(tmp_path):
    """
    Create a mock Elixir repository for testing.

    Returns:
        Path: Path to the mock repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Create mix.exs to make it a valid Elixir project
    (repo_path / "mix.exs").write_text(
        """
        defmodule TestProject.MixProject do
          use Mix.Project
          def project do
            [app: :test_project, version: "0.1.0"]
          end
        end
        """
    )

    # Create a simple Elixir module
    lib_dir = repo_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "test_module.ex").write_text(
        """
        defmodule TestModule do
          def hello do
            :world
          end
        end
        """
    )

    return repo_path


class TestMultiEditorSetup:
    """Tests for setting up multiple editors on the same repository"""

    @patch("cicada.setup.index_repository")
    def test_claude_then_cursor_setup(self, mock_index, mock_elixir_repo):
        """Test running setup for Claude then Cursor"""

        # First setup: Claude
        setup("claude", mock_elixir_repo)

        # Verify Claude config exists
        claude_config_path = mock_elixir_repo / ".mcp.json"
        assert claude_config_path.exists(), "Claude config should be created"

        with open(claude_config_path) as f:
            claude_config = json.load(f)

        assert "mcpServers" in claude_config
        assert "cicada" in claude_config["mcpServers"]

        # Verify storage directory was created
        storage_dir = get_storage_dir(mock_elixir_repo)
        assert storage_dir.exists(), "Storage directory should exist"

        # Second setup: Cursor
        setup("cursor", mock_elixir_repo)

        # Verify Cursor config exists
        cursor_config_path = mock_elixir_repo / ".cursor" / "mcp.json"
        assert cursor_config_path.exists(), "Cursor config should be created"

        with open(cursor_config_path) as f:
            cursor_config = json.load(f)

        assert "mcpServers" in cursor_config
        assert "cicada" in cursor_config["mcpServers"]

        # Verify Claude config still exists and is unchanged
        assert claude_config_path.exists(), "Claude config should still exist"

        with open(claude_config_path) as f:
            claude_config_after = json.load(f)

        assert claude_config == claude_config_after, "Claude config should be unchanged"

        # Verify both configs point to the same storage directory
        storage_dir_from_claude = Path(
            claude_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]
        )
        storage_dir_from_cursor = Path(
            cursor_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]
        )

        assert (
            storage_dir_from_claude == storage_dir_from_cursor
        ), "Both editors should use the same storage directory"

    @patch("cicada.setup.index_repository")
    def test_all_three_editors_setup(self, mock_index, mock_elixir_repo):
        """Test running setup for all three editors"""

        # Setup all three editors
        setup("claude", mock_elixir_repo)
        setup("cursor", mock_elixir_repo)
        setup("vs", mock_elixir_repo)

        # Verify all three configs exist
        claude_config_path = mock_elixir_repo / ".mcp.json"
        cursor_config_path = mock_elixir_repo / ".cursor" / "mcp.json"
        vs_config_path = mock_elixir_repo / ".vscode" / "settings.json"

        assert claude_config_path.exists(), "Claude config should exist"
        assert cursor_config_path.exists(), "Cursor config should exist"
        assert vs_config_path.exists(), "VS Code config should exist"

        # Load and verify all configs
        with open(claude_config_path) as f:
            claude_config = json.load(f)

        with open(cursor_config_path) as f:
            cursor_config = json.load(f)

        with open(vs_config_path) as f:
            vs_config = json.load(f)

        # Verify config structure
        assert "mcpServers" in claude_config
        assert "cicada" in claude_config["mcpServers"]

        assert "mcpServers" in cursor_config
        assert "cicada" in cursor_config["mcpServers"]

        assert "mcp.servers" in vs_config
        assert "cicada" in vs_config["mcp.servers"]

        # Verify all three use the same storage directory
        storage_dirs = [
            Path(claude_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]),
            Path(cursor_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]),
            Path(vs_config["mcp.servers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]),
        ]

        assert len(set(storage_dirs)) == 1, "All editors should use the same storage directory"

        # Verify storage directory contains expected files
        storage_dir = storage_dirs[0]
        assert storage_dir.exists()
        assert (storage_dir / "config.yaml").exists()

    @patch("cicada.setup.index_repository")
    def test_rerunning_same_editor_updates_config(self, mock_index, mock_elixir_repo):
        """Test that re-running setup for the same editor updates the config"""

        # First run
        setup("claude", mock_elixir_repo)

        claude_config_path = mock_elixir_repo / ".mcp.json"
        assert claude_config_path.exists()

        # Get initial config
        with open(claude_config_path) as f:
            initial_config = json.load(f)

        # Second run - should update config without breaking
        setup("claude", mock_elixir_repo)

        # Config should still exist and be valid
        assert claude_config_path.exists()

        with open(claude_config_path) as f:
            updated_config = json.load(f)

        # Verify config structure is still valid
        assert "mcpServers" in updated_config
        assert "cicada" in updated_config["mcpServers"]

        # Verify storage directory is still the same
        initial_storage = Path(initial_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"])
        updated_storage = Path(updated_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"])

        assert initial_storage == updated_storage, "Storage directory should remain the same"

    @patch("cicada.setup.index_repository")
    def test_preserves_existing_mcp_config_entries(self, mock_index, mock_elixir_repo):
        """Test that setup preserves other MCP server entries in config"""

        # Create Claude config with another MCP server
        claude_config_path = mock_elixir_repo / ".mcp.json"
        existing_config = {
            "mcpServers": {
                "other-server": {
                    "command": "other-server",
                    "args": ["--flag"],
                }
            }
        }

        with open(claude_config_path, "w") as f:
            json.dump(existing_config, f)

        # Run setup
        setup("claude", mock_elixir_repo)

        # Verify both servers exist in config
        with open(claude_config_path) as f:
            updated_config = json.load(f)

        assert "other-server" in updated_config["mcpServers"], "Existing server should be preserved"
        assert "cicada" in updated_config["mcpServers"], "Cicada server should be added"

        # Verify other-server config is unchanged
        assert (
            updated_config["mcpServers"]["other-server"]
            == existing_config["mcpServers"]["other-server"]
        )

    @patch("cicada.setup.index_repository")
    def test_handles_malformed_existing_config(self, mock_index, mock_elixir_repo):
        """Test that setup handles malformed existing config gracefully"""

        # Create malformed Claude config
        claude_config_path = mock_elixir_repo / ".mcp.json"
        with open(claude_config_path, "w") as f:
            f.write("{ this is not valid json }")

        # Run setup - should not crash
        setup("claude", mock_elixir_repo)

        # Verify config was recreated and is valid
        assert claude_config_path.exists()

        with open(claude_config_path) as f:
            config = json.load(f)  # Should not raise JSONDecodeError

        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

    @patch("cicada.setup.index_repository")
    def test_directory_creation_for_cursor_and_vs(self, mock_index, mock_elixir_repo):
        """Test that setup creates directories for Cursor and VS Code"""

        # Verify directories don't exist initially
        cursor_dir = mock_elixir_repo / ".cursor"
        vscode_dir = mock_elixir_repo / ".vscode"

        assert not cursor_dir.exists()
        assert not vscode_dir.exists()

        # Run setup for Cursor
        setup("cursor", mock_elixir_repo)

        assert cursor_dir.exists(), "Cursor directory should be created"
        assert cursor_dir.is_dir(), "Cursor path should be a directory"

        # Run setup for VS Code
        setup("vs", mock_elixir_repo)

        assert vscode_dir.exists(), "VS Code directory should be created"
        assert vscode_dir.is_dir(), "VS Code path should be a directory"

    @patch("cicada.setup.index_repository")
    def test_indexing_called_once_per_setup(self, mock_index, mock_elixir_repo):
        """Test that indexing is called each time setup runs"""

        # Run setup three times
        setup("claude", mock_elixir_repo)
        setup("cursor", mock_elixir_repo)
        setup("vs", mock_elixir_repo)

        # Verify indexing was called three times
        assert mock_index.call_count == 3, "Indexing should be called once per setup run"

        # Verify all calls had the same repo_path
        for call in mock_index.call_args_list:
            assert call[0][0] == mock_elixir_repo


class TestGetMcpConfigForEditorMultiEditor:
    """Tests for get_mcp_config_for_editor with focus on multi-editor scenarios"""

    def test_different_editors_different_paths(self, mock_elixir_repo, tmp_path):
        """Test that different editors use different config paths"""

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        with patch("shutil.which", return_value="cicada-server"):
            # Get configs for all three editors
            claude_path, _ = get_mcp_config_for_editor("claude", mock_elixir_repo, storage_dir)
            cursor_path, _ = get_mcp_config_for_editor("cursor", mock_elixir_repo, storage_dir)
            vs_path, _ = get_mcp_config_for_editor("vs", mock_elixir_repo, storage_dir)

            # Verify paths are different
            assert claude_path != cursor_path
            assert claude_path != vs_path
            assert cursor_path != vs_path

            # Verify correct paths
            assert claude_path == mock_elixir_repo / ".mcp.json"
            assert cursor_path == mock_elixir_repo / ".cursor" / "mcp.json"
            assert vs_path == mock_elixir_repo / ".vscode" / "settings.json"

    def test_different_editors_same_storage(self, mock_elixir_repo, tmp_path):
        """Test that different editors use the same storage directory"""

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        with patch("shutil.which", return_value="cicada-server"):
            # Get configs for all three editors
            _, claude_config = get_mcp_config_for_editor("claude", mock_elixir_repo, storage_dir)
            _, cursor_config = get_mcp_config_for_editor("cursor", mock_elixir_repo, storage_dir)
            _, vs_config = get_mcp_config_for_editor("vs", mock_elixir_repo, storage_dir)

            # Extract storage directories from configs
            claude_storage = claude_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]
            cursor_storage = cursor_config["mcpServers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]
            vs_storage = vs_config["mcp.servers"]["cicada"]["env"]["CICADA_CONFIG_DIR"]

            # Verify all use the same storage directory
            assert claude_storage == str(storage_dir)
            assert cursor_storage == str(storage_dir)
            assert vs_storage == str(storage_dir)
