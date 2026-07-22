"""
Comprehensive tests for cicada/setup.py

Tests cover:
- Indexing mode configuration (keywords/embeddings)
- MCP config generation for all editors
- Repository indexing
- Setup function orchestration
- Error handling
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from cicada.setup import (
    create_config_yaml,
    get_mcp_config_for_editor,
    index_repository,
    setup,
)


# ============================================================================
# Indexing Mode Configuration Tests (dev branch feature)
# ============================================================================


def test_create_config_yaml_defaults(tmp_path):
    """Config should default to keywords mode."""
    from cicada.setup import create_config_yaml

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    with (
        patch("cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"),
        patch("cicada.setup.get_index_path", return_value=storage_dir / "index.json"),
    ):
        create_config_yaml(repo_path, storage_dir, verbose=False)

    config_content = (storage_dir / "config.yaml").read_text()
    assert "indexing:" in config_content
    assert "mode: keywords" in config_content


def test_create_config_yaml_embeddings(tmp_path):
    """Config should support embeddings mode."""
    from cicada.setup import create_config_yaml

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    with (
        patch("cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"),
        patch("cicada.setup.get_index_path", return_value=storage_dir / "index.json"),
    ):
        create_config_yaml(repo_path, storage_dir, indexing_mode="embeddings", verbose=False)

    config_content = (storage_dir / "config.yaml").read_text()
    assert "mode: embeddings" in config_content


def test_setup_passes_indexing_mode(tmp_path):
    """Setup should pass indexing_mode to create_config_yaml."""
    from cicada.setup import setup

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "mix.exs").touch()
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    with (
        patch("cicada.setup.detect_project_language", return_value="elixir"),
        patch("cicada.setup.create_storage_dir", return_value=storage_dir),
        patch("cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"),
        patch("cicada.setup.get_index_path", return_value=storage_dir / "index.json"),
        patch("cicada.setup.create_config_yaml") as mock_create,
    ):
        setup("claude", repo_path, indexing_mode="keywords", index_exists=True)

    call_args = mock_create.call_args[0]
    assert call_args[2] == "keywords"


# ============================================================================
# MCP Config Generation Tests
# ============================================================================


class TestGetMcpConfigForEditor:
    """Tests for get_mcp_config_for_editor function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock mix file")
        return repo_path

    @pytest.fixture
    def mock_storage_dir(self, tmp_path):
        """Create a mock storage directory"""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        return storage_dir

    def test_claude_config_structure(self, mock_repo, mock_storage_dir):
        """Claude config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert "command" in server_config
        assert "env" in server_config
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_cursor_config_structure(self, mock_repo, mock_storage_dir):
        """Cursor config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("cursor", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".cursor" / "mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_vs_config_structure(self, mock_repo, mock_storage_dir):
        """VS Code config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("vs", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".vscode" / "settings.json"
        assert "mcp.servers" in config  # Different key for VS Code
        assert "cicada" in config["mcp.servers"]

        server_config = config["mcp.servers"]["cicada"]
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_gemini_config_structure(self, mock_repo, mock_storage_dir):
        """Gemini config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("gemini", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".gemini" / "settings.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert "command" in server_config
        assert "env" in server_config
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_codex_config_structure(self, mock_repo, mock_storage_dir):
        """Codex config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("codex", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".codex" / "mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert "command" in server_config
        assert "env" in server_config
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_opencode_config_structure(self, mock_repo, mock_storage_dir):
        """OpenCode config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("opencode", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert "command" in server_config
        assert "env" in server_config
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_zed_config_structure(self, mock_repo, mock_storage_dir):
        """Zed config should have correct structure"""
        config_path, config = get_mcp_config_for_editor("zed", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".zed" / "settings.json"
        assert "context_servers" in config  # Zed uses context_servers key
        assert "cicada" in config["context_servers"]

        server_config = config["context_servers"]["cicada"]
        assert "command" in server_config
        assert "env" in server_config
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_with_cicada_server_installed(self, mock_repo, mock_storage_dir):
        """Should always use uvx cicada-mcp for maximum compatibility"""
        _, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        server_config = config["mcpServers"]["cicada"]
        assert server_config["command"] == "uvx"
        assert server_config["args"] == ["cicada-mcp"]

    def test_without_cicada_server_installed(self, mock_repo, mock_storage_dir):
        """Should always use uvx cicada-mcp regardless of installation status"""
        _, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        server_config = config["mcpServers"]["cicada"]
        assert server_config["command"] == "uvx"
        assert server_config["args"] == ["cicada-mcp"]

    def test_preserves_existing_config(self, mock_repo, mock_storage_dir):
        """Should preserve existing configuration when adding cicada"""
        # Create existing config for Claude
        config_path = mock_repo / ".mcp.json"
        existing_config = {
            "mcpServers": {"other-server": {"command": "other-command", "args": ["--flag"]}}
        }
        config_path.write_text(json.dumps(existing_config))

        _, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        # Should preserve other-server
        assert "other-server" in config["mcpServers"]
        assert config["mcpServers"]["other-server"]["command"] == "other-command"
        # Should add cicada
        assert "cicada" in config["mcpServers"]

    def test_handles_malformed_json(self, mock_repo, mock_storage_dir):
        """Should handle malformed JSON by creating new config"""
        config_path = mock_repo / ".mcp.json"
        config_path.write_text("{invalid json}")

        _, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        # Should create valid config despite malformed input
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

    def test_handles_io_error(self, mock_repo, mock_storage_dir):
        """Should handle IO errors gracefully"""
        # No existing file - should create new config
        _, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

    def test_invalid_editor_type(self, mock_repo, mock_storage_dir):
        """Should raise ValueError for unsupported editor"""
        with pytest.raises(ValueError, match="Unsupported editor"):
            get_mcp_config_for_editor("invalid", mock_repo, mock_storage_dir)

    def test_updates_existing_cicada_config(self, mock_repo, mock_storage_dir):
        """Should update existing cicada configuration"""
        config_path = mock_repo / ".mcp.json"
        existing_config = {"mcpServers": {"cicada": {"command": "old-command", "env": {}}}}
        config_path.write_text(json.dumps(existing_config))

        _, config = get_mcp_config_for_editor("claude", mock_repo, mock_storage_dir)

        # Should replace old cicada config
        server_config = config["mcpServers"]["cicada"]
        assert server_config["command"] == "uvx"
        assert server_config["args"] == ["cicada-mcp"]
        assert "CICADA_CONFIG_DIR" in server_config["env"]


# ============================================================================
# Repository Indexing Tests
# ============================================================================


class TestIndexRepository:
    """Tests for index_repository function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock Elixir repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock mix file")

        lib_dir = repo_path / "lib"
        lib_dir.mkdir()
        (lib_dir / "test.ex").write_text("defmodule Test do\nend\n")

        return repo_path

    def test_calls_indexer_with_correct_params(self, mock_repo):
        """Should call LanguageRegistry.get_indexer with correct parameters"""
        with patch("cicada.setup.LanguageRegistry.get_indexer") as mock_get_indexer:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                with patch("cicada.setup.get_config_path") as mock_get_config:
                    mock_indexer = MagicMock()
                    # Mock incremental_index_repository since setup.py now uses it
                    mock_indexer.incremental_index_repository = MagicMock()
                    mock_get_indexer.return_value = mock_indexer

                    index_path = mock_repo / "index.json"
                    mock_get_index.return_value = index_path

                    config_path = mock_repo / "config.yaml"
                    mock_get_config.return_value = config_path

                    index_repository(mock_repo, language="elixir")

                # Verify indexer was fetched for the correct language
                mock_get_indexer.assert_called_once_with("elixir")

                # Verify incremental_index_repository was called with all features enabled
                mock_indexer.incremental_index_repository.assert_called_once_with(
                    repo_path=str(mock_repo),
                    output_path=str(index_path),
                    extract_keywords=True,
                    compute_timestamps=True,
                    extract_cochange=True,
                    force_full=False,
                    verbose=True,
                )

    def test_handles_indexing_errors(self, mock_repo):
        """Should handle indexing errors appropriately"""
        with patch("cicada.setup.LanguageRegistry.get_indexer") as mock_get_indexer:
            with patch("cicada.setup.get_index_path"):
                with patch("cicada.setup.get_config_path"):
                    mock_indexer = MagicMock()
                    mock_indexer.incremental_index_repository = MagicMock(
                        side_effect=Exception("Indexing failed")
                    )
                    mock_get_indexer.return_value = mock_indexer

                    # Should raise the exception (not caught in current implementation)
                    with pytest.raises(Exception, match="Indexing failed"):
                        index_repository(mock_repo, language="elixir")

    def test_calls_non_incremental_indexer(self, mock_repo):
        """Should call index_repository for indexers without incremental support."""
        with (
            patch("cicada.setup.LanguageRegistry.get_indexer") as mock_get_indexer,
            patch("cicada.setup.get_index_path") as mock_get_index,
            patch("cicada.setup.get_config_path") as mock_get_config,
        ):
            mock_indexer = MagicMock()
            mock_indexer.supports_incremental = False
            mock_indexer.index_repository = MagicMock()
            mock_indexer.get_file_extensions.return_value = [".gleam"]
            mock_get_indexer.return_value = mock_indexer

            index_path = mock_repo / "index.json"
            mock_get_index.return_value = index_path

            config_path = mock_repo / "config.yaml"
            mock_get_config.return_value = config_path

            index_repository(mock_repo, language="gleam")

            mock_indexer.index_repository.assert_called_once_with(
                repo_path=str(mock_repo),
                output_path=str(index_path),
                force=False,
                verbose=True,
                config_path=str(config_path),
            )
            mock_indexer.incremental_index_repository.assert_not_called()

    def test_calls_legacy_indexer_without_incremental_flag(self, mock_repo):
        """Should treat indexers without supports_incremental as non-incremental."""
        with (
            patch("cicada.setup.LanguageRegistry.get_indexer") as mock_get_indexer,
            patch("cicada.setup.get_index_path") as mock_get_index,
            patch("cicada.setup.get_config_path") as mock_get_config,
        ):
            mock_indexer = MagicMock()
            del mock_indexer.supports_incremental
            mock_indexer.index_repository = MagicMock()
            mock_indexer.get_file_extensions.return_value = [".legacy"]
            mock_get_indexer.return_value = mock_indexer

            index_path = mock_repo / "index.json"
            mock_get_index.return_value = index_path
            config_path = mock_repo / "config.yaml"
            mock_get_config.return_value = config_path

            index_repository(mock_repo, language="legacy")

            mock_indexer.index_repository.assert_called_once_with(
                repo_path=str(mock_repo),
                output_path=str(index_path),
                force=False,
                verbose=True,
                config_path=str(config_path),
            )


# ============================================================================
# Setup Function Tests
# ============================================================================


class TestSetupFunction:
    """Tests for main setup function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock mix file")
        return repo_path

    def test_setup_creates_all_files(self, mock_repo):
        """Setup should create storage dir, index, config, and MCP config"""
        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.index_repository") as mock_index:
                with patch("cicada.setup.create_config_yaml") as mock_create_config:
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        storage_dir = mock_repo.parent / "storage"
                        mock_create_storage.return_value = storage_dir

                        config_path = mock_repo / ".mcp.json"
                        config_content = {"mcpServers": {"cicada": {}}}
                        mock_mcp.return_value = (config_path, config_content)

                        setup("claude", mock_repo)

                        # Verify all functions were called
                        mock_create_storage.assert_called_once()
                        mock_index.assert_called_once()
                        mock_create_config.assert_called_once()
                        mock_mcp.assert_called_once()

    def test_setup_writes_mcp_config(self, mock_repo):
        """Setup should write MCP config file"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        config_path = mock_repo / ".mcp.json"
                        config_content = {"mcpServers": {"cicada": {"command": "test"}}}
                        mock_mcp.return_value = (config_path, config_content)

                        setup("claude", mock_repo)

                        assert config_path.exists()
                        written_config = json.loads(config_path.read_text())
                        assert written_config == config_content

    def test_setup_uses_cwd_by_default(self):
        """Setup should use current directory if no path provided"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch("cicada.setup.detect_project_language", return_value="elixir"):
                            with patch("pathlib.Path.cwd") as mock_cwd:
                                with patch("builtins.open", mock_open()):
                                    mock_cwd.return_value = Path("/mock/cwd")
                                    config_path = Path("/mock/cwd/.mcp.json")
                                    mock_mcp.return_value = (config_path, {})

                                    setup("claude", None)

                                    # Should have resolved current directory
                                    mock_cwd.assert_called()

    def test_setup_all_editors(self, mock_repo):
        """Setup should work for all editor types"""
        editors = ["claude", "cursor", "vs", "gemini", "codex", "zed"]

        for editor in editors:
            with patch("cicada.setup.create_storage_dir"):
                with patch("cicada.setup.index_repository"):
                    with patch("cicada.setup.create_config_yaml"):
                        with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                            config_path = mock_repo / f".{editor}.json"
                            mock_mcp.return_value = (config_path, {})

                            # Should not raise an error
                            setup(editor, mock_repo)


# ============================================================================
# Main CLI Entry Point Tests
# ============================================================================


class TestMainFunction:
    """Tests for main CLI entry point"""

    def test_main_validates_project(self, tmp_path):
        """Main should check for valid project files"""
        from cicada.setup import main

        non_valid_repo = tmp_path / "not_valid"
        non_valid_repo.mkdir()

        with patch("sys.argv", ["cicada", "claude", str(non_valid_repo)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_main_accepts_editor_argument(self, tmp_path):
        """Main should accept editor as first argument"""
        from cicada.setup import main

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")

        with patch("sys.argv", ["cicada", "claude", str(repo_path)]):
            with patch("cicada.setup.setup") as mock_setup:
                main()

                mock_setup.assert_called_once()
                args = mock_setup.call_args
                assert args[0][0] == "claude"

    def test_main_validates_editor_choice(self):
        """Main should only accept valid editor choices"""
        from cicada.setup import main

        with patch("sys.argv", ["cicada", "invalid_editor"]), pytest.raises(SystemExit):
            main()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        return repo_path

    def test_handles_permission_error_on_config_write(self, mock_repo):
        """Should handle permission errors when writing config"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.detect_project_language", return_value="elixir"):
                        with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                            config_path = mock_repo / ".mcp.json"
                            mock_mcp.return_value = (config_path, {})

                            # Mock open() to raise PermissionError
                            def mock_open_error(*args, **kwargs):
                                raise PermissionError(f"Permission denied: {config_path}")

                            with (
                                patch("builtins.open", side_effect=mock_open_error),
                                pytest.raises(PermissionError),
                            ):
                                setup("claude", mock_repo)

    def test_config_path_returns_tuple(self, mock_repo, tmp_path):
        """get_mcp_config_for_editor should return tuple"""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        result = get_mcp_config_for_editor("claude", mock_repo, storage_dir)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], dict)


# ============================================================================
# Setup Index Exists Tests
# ============================================================================


class TestSetupIndexExists:
    """Tests for setup() with index_exists parameter"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")
        return repo_path

    def test_skips_indexing_when_index_exists(self, mock_repo, capsys):
        """Should skip indexing when index_exists=True"""
        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.index_repository") as mock_index:
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        storage_dir = mock_repo.parent / "storage"
                        mock_create_storage.return_value = storage_dir
                        config_path = mock_repo / ".mcp.json"
                        mock_mcp.return_value = (config_path, {"mcpServers": {}})

                        setup("claude", mock_repo, index_exists=True)

                        # Should NOT call index_repository
                        mock_index.assert_not_called()

                        captured = capsys.readouterr()
                        assert "✓ Found existing index" in captured.out
