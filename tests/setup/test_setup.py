"""
Comprehensive tests for cicada/setup.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from cicada.setup import (
    get_mcp_config_for_editor,
    create_config_yaml,
    index_repository,
    setup,
)


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
        with patch("shutil.which", return_value="cicada-server"):
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
        with patch("shutil.which", return_value="cicada-server"):
            config_path, config = get_mcp_config_for_editor("cursor", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".cursor" / "mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_vs_config_structure(self, mock_repo, mock_storage_dir):
        """VS Code config should have correct structure"""
        with patch("shutil.which", return_value="cicada-server"):
            config_path, config = get_mcp_config_for_editor("vs", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".vscode" / "settings.json"
        assert "mcp.servers" in config  # Different key for VS Code
        assert "cicada" in config["mcp.servers"]

        server_config = config["mcp.servers"]["cicada"]
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_gemini_config_structure(self, mock_repo, mock_storage_dir):
        """Gemini config should have correct structure"""
        with patch("shutil.which", return_value="cicada-server"):
            config_path, config = get_mcp_config_for_editor("gemini", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".gemini" / "mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
        assert "command" in server_config
        assert "env" in server_config
        assert server_config["env"]["CICADA_CONFIG_DIR"] == str(mock_storage_dir)

    def test_codex_config_structure(self, mock_repo, mock_storage_dir):
        """Codex config should have correct structure"""
        with patch("shutil.which", return_value="cicada-server"):
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
        with patch("shutil.which", return_value="cicada-server"):
            config_path, config = get_mcp_config_for_editor("opencode", mock_repo, mock_storage_dir)

        assert config_path == mock_repo / ".mcp.json"
        assert "mcpServers" in config
        assert "cicada" in config["mcpServers"]

        server_config = config["mcpServers"]["cicada"]
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


class TestCreateConfigYaml:
    """Tests for create_config_yaml function"""

    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Setup mock paths"""
        repo_path = tmp_path / "repo"
        storage_dir = tmp_path / "storage"
        repo_path.mkdir()
        storage_dir.mkdir()
        return repo_path, storage_dir

    def test_creates_config_file(self, mock_paths):
        """Should create config.yaml in storage directory"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                create_config_yaml(repo_path, storage_dir)

                assert config_path.exists()
                content = config_path.read_text()
                assert str(repo_path) in content
                assert str(index_path) in content

    def test_config_yaml_structure(self, mock_paths):
        """Config YAML should have correct structure"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                create_config_yaml(repo_path, storage_dir)

                content = config_path.read_text()
                assert "repository:" in content
                assert "path:" in content
                assert "storage:" in content
                assert "index_path:" in content
                assert "keyword_extraction:" in content
                assert "keyword_expansion:" in content
                assert "method: regular" in content  # Default extraction
                assert "method: lemmi" in content  # Default expansion

    def test_config_yaml_with_bert_method(self, mock_paths):
        """Config YAML should save KeyBERT extraction method when specified"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                create_config_yaml(
                    repo_path, storage_dir, extraction_method="bert", expansion_method="glove"
                )

                content = config_path.read_text()
                assert "keyword_extraction:" in content
                assert "method: bert" in content
                assert "keyword_expansion:" in content
                assert "method: glove" in content

    def test_config_yaml_with_fasttext_expansion(self, mock_paths):
        """Config YAML should save FastText expansion method when specified"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                create_config_yaml(
                    repo_path, storage_dir, extraction_method="bert", expansion_method="fasttext"
                )

                content = config_path.read_text()
                assert "method: bert" in content
                assert "method: fasttext" in content


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
        """Should call ElixirIndexer with correct parameters"""
        with patch("cicada.setup.ElixirIndexer") as mock_indexer_class:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                mock_indexer = MagicMock()
                mock_indexer_class.return_value = mock_indexer

                index_path = mock_repo / "index.json"
                mock_get_index.return_value = index_path

                index_repository(mock_repo)

                # Verify indexer was created with verbose=True
                mock_indexer_class.assert_called_once_with(verbose=True)

                # Verify incremental_index_repository was called with correct params
                mock_indexer.incremental_index_repository.assert_called_once_with(
                    repo_path=str(mock_repo),
                    output_path=str(index_path),
                    extract_keywords=True,
                    force_full=False,
                )

    def test_handles_indexing_errors(self, mock_repo):
        """Should handle indexing errors appropriately"""
        with patch("cicada.setup.ElixirIndexer") as mock_indexer_class:
            with patch("cicada.setup.get_index_path"):
                mock_indexer = MagicMock()
                mock_indexer.incremental_index_repository.side_effect = Exception("Indexing failed")
                mock_indexer_class.return_value = mock_indexer

                # Should raise the exception (not caught in current implementation)
                with pytest.raises(Exception, match="Indexing failed"):
                    index_repository(mock_repo)


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
                        with patch("pathlib.Path.cwd") as mock_cwd:
                            with patch("builtins.open", mock_open()):
                                mock_cwd.return_value = Path("/mock/cwd")
                                config_path = Path("/mock/cwd/.mcp.json")
                                mock_mcp.return_value = (config_path, {})

                                setup("claude", None)

                                # Should have resolved current directory
                                mock_cwd.assert_called()

    def test_setup_all_three_editors(self, mock_repo):
        """Setup should work for all three editor types"""
        editors = ["claude", "cursor", "vs"]

        for editor in editors:
            with patch("cicada.setup.create_storage_dir"):
                with patch("cicada.setup.index_repository"):
                    with patch("cicada.setup.create_config_yaml"):
                        with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                            config_path = mock_repo / f".{editor}.json"
                            mock_mcp.return_value = (config_path, {})

                            # Should not raise an error
                            setup(editor, mock_repo)


class TestMainFunction:
    """Tests for main CLI entry point"""

    def test_main_validates_elixir_project(self, tmp_path):
        """Main should check for mix.exs file"""
        from cicada.setup import main

        non_elixir_repo = tmp_path / "not_elixir"
        non_elixir_repo.mkdir()

        with patch("sys.argv", ["cicada", "claude", str(non_elixir_repo)]):
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

        with patch("sys.argv", ["cicada", "invalid_editor"]):
            with pytest.raises(SystemExit):
                main()


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
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        config_path = mock_repo / ".mcp.json"
                        mock_mcp.return_value = (config_path, {})

                        # Mock open() to raise PermissionError (actual code uses open + json.dump)
                        def mock_open(*args, **kwargs):
                            raise PermissionError(f"Permission denied: {config_path}")

                        with (
                            patch("builtins.open", side_effect=mock_open),
                            pytest.raises(PermissionError),
                        ):
                            setup("claude", mock_repo)

    def test_config_path_returns_tuple(self, mock_repo, tmp_path):
        """get_mcp_config_for_editor should return tuple"""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        with patch("shutil.which", return_value="cicada-server"):
            result = get_mcp_config_for_editor("claude", mock_repo, storage_dir)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], dict)


class TestLoadExistingConfig:
    """Tests for _load_existing_config helper function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        return repo_path

    def test_loads_valid_json_config(self, mock_repo):
        """Should load valid JSON configuration"""
        from cicada.setup import _load_existing_config

        config_path = mock_repo / ".mcp.json"
        valid_config = {"mcpServers": {"test": "value"}}
        config_path.write_text(json.dumps(valid_config))

        result = _load_existing_config(config_path)

        assert result == valid_config

    def test_returns_empty_dict_when_file_not_exists(self, mock_repo):
        """Should return empty dict when config file doesn't exist"""
        from cicada.setup import _load_existing_config

        config_path = mock_repo / "nonexistent.json"

        result = _load_existing_config(config_path)

        assert result == {}

    def test_handles_malformed_json_gracefully(self, mock_repo, capsys):
        """Should return empty dict and print warning for malformed JSON"""
        from cicada.setup import _load_existing_config

        config_path = mock_repo / ".mcp.json"
        config_path.write_text("{invalid json content}")

        result = _load_existing_config(config_path)

        assert result == {}
        captured = capsys.readouterr()
        assert "Warning: Existing config" in captured.out
        assert "malformed" in captured.out

    def test_handles_oserror_gracefully(self, mock_repo, capsys):
        """Should handle OSError when reading config file"""
        from cicada.setup import _load_existing_config

        config_path = mock_repo / ".mcp.json"
        config_path.write_text("{}")

        # Mock open() to raise PermissionError (actual code uses open + json.load)
        def mock_open(*args, **kwargs):
            raise PermissionError(f"Permission denied: {config_path}")

        with patch("builtins.open", side_effect=mock_open):
            result = _load_existing_config(config_path)

            assert result == {}
            captured = capsys.readouterr()
            assert "Warning: Could not read config file" in captured.out


class TestBuildServerConfig:
    """Tests for _build_server_config helper function"""

    def test_builds_config_with_command_only(self, tmp_path):
        """Should build config with only command when no args or cwd"""
        from cicada.setup import _build_server_config

        repo_path = tmp_path / "repo"
        storage_dir = tmp_path / "storage"

        result = _build_server_config("test-command", [], None, repo_path, storage_dir)

        assert result["command"] == "test-command"
        assert "args" not in result
        assert "cwd" not in result
        assert result["env"]["CICADA_CONFIG_DIR"] == str(storage_dir)

    def test_builds_config_with_args(self, tmp_path):
        """Should include args when provided"""
        from cicada.setup import _build_server_config

        repo_path = tmp_path / "repo"
        storage_dir = tmp_path / "storage"
        args = ["-m", "cicada.mcp_server"]

        result = _build_server_config("python3", args, None, repo_path, storage_dir)

        assert result["command"] == "python3"
        assert result["args"] == args
        assert "cwd" not in result

    def test_builds_config_with_cwd(self, tmp_path):
        """Should include cwd when provided"""
        from cicada.setup import _build_server_config

        repo_path = tmp_path / "repo"
        storage_dir = tmp_path / "storage"
        cwd = "/custom/working/dir"

        result = _build_server_config("test-command", [], cwd, repo_path, storage_dir)

        assert result["command"] == "test-command"
        assert result["cwd"] == cwd

    def test_builds_config_with_all_parameters(self, tmp_path):
        """Should build complete config with all parameters"""
        from cicada.setup import _build_server_config

        repo_path = tmp_path / "repo"
        storage_dir = tmp_path / "storage"
        args = ["--verbose", "--debug"]
        cwd = "/custom/dir"

        result = _build_server_config("test-cmd", args, cwd, repo_path, storage_dir)

        assert result["command"] == "test-cmd"
        assert result["args"] == args
        assert result["cwd"] == cwd
        assert result["env"]["CICADA_CONFIG_DIR"] == str(storage_dir)


class TestCreateConfigYamlVerbose:
    """Tests for create_config_yaml verbose parameter"""

    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Setup mock paths"""
        repo_path = tmp_path / "repo"
        storage_dir = tmp_path / "storage"
        repo_path.mkdir()
        storage_dir.mkdir()
        return repo_path, storage_dir

    def test_prints_message_when_verbose_true(self, mock_paths, capsys):
        """Should print success message when verbose=True"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                create_config_yaml(repo_path, storage_dir, verbose=True)

                captured = capsys.readouterr()
                assert "✓ Config file created" in captured.out
                assert str(config_path) in captured.out

    def test_silent_when_verbose_false(self, mock_paths, capsys):
        """Should not print message when verbose=False"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                create_config_yaml(repo_path, storage_dir, verbose=False)

                captured = capsys.readouterr()
                assert captured.out == ""

    def test_creates_file_regardless_of_verbose(self, mock_paths):
        """Should create config file regardless of verbose setting"""
        repo_path, storage_dir = mock_paths

        with patch("cicada.setup.get_config_path") as mock_get_config:
            with patch("cicada.setup.get_index_path") as mock_get_index:
                config_path = storage_dir / "config.yaml"
                index_path = storage_dir / "index.json"
                mock_get_config.return_value = config_path
                mock_get_index.return_value = index_path

                # Test verbose=False
                create_config_yaml(repo_path, storage_dir, verbose=False)
                assert config_path.exists()

                # Clean up
                config_path.unlink()

                # Test verbose=True
                create_config_yaml(repo_path, storage_dir, verbose=True)
                assert config_path.exists()


class TestIndexRepositoryForceFullParameter:
    """Tests for index_repository force_full parameter"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")
        return repo_path

    def test_calls_incremental_index_with_force_full_false(self, mock_repo):
        """Should pass force_full=False by default"""
        with patch("cicada.setup.ElixirIndexer") as mock_indexer_class:
            with patch("cicada.setup.get_index_path"):
                mock_indexer = MagicMock()
                mock_indexer_class.return_value = mock_indexer

                index_repository(mock_repo, force_full=False)

                mock_indexer.incremental_index_repository.assert_called_once()
                call_kwargs = mock_indexer.incremental_index_repository.call_args[1]
                assert call_kwargs["force_full"] is False

    def test_calls_incremental_index_with_force_full_true(self, mock_repo):
        """Should pass force_full=True when specified"""
        with patch("cicada.setup.ElixirIndexer") as mock_indexer_class:
            with patch("cicada.setup.get_index_path"):
                mock_indexer = MagicMock()
                mock_indexer_class.return_value = mock_indexer

                index_repository(mock_repo, force_full=True)

                mock_indexer.incremental_index_repository.assert_called_once()
                call_kwargs = mock_indexer.incremental_index_repository.call_args[1]
                assert call_kwargs["force_full"] is True

    def test_prints_error_message_on_failure(self, mock_repo, capsys):
        """Should print error messages when indexing fails"""
        with patch("cicada.setup.ElixirIndexer") as mock_indexer_class:
            with patch("cicada.setup.get_index_path"):
                mock_indexer = MagicMock()
                mock_indexer.incremental_index_repository.side_effect = Exception("Test error")
                mock_indexer_class.return_value = mock_indexer

                with pytest.raises(Exception, match="Test error"):
                    index_repository(mock_repo)

                captured = capsys.readouterr()
                assert "Error: Failed to index repository" in captured.out
                assert "Test error" in captured.out
                assert (
                    "Please check that the repository contains valid Elixir files" in captured.out
                )


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

    def test_shows_condensed_output_when_index_exists(self, mock_repo, capsys):
        """Should show condensed output when index_exists=True"""
        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        storage_dir = mock_repo.parent / "storage"
                        mock_create_storage.return_value = storage_dir
                        config_path = mock_repo / ".mcp.json"
                        mock_mcp.return_value = (config_path, {"mcpServers": {}})

                        setup(
                            "claude",
                            mock_repo,
                            extraction_method="bert",
                            expansion_method="glove",
                            index_exists=True,
                        )

                        captured = capsys.readouterr()
                        assert "✓ Found existing index" in captured.out
                        assert "Storage:" in captured.out
                        assert "Restart CLAUDE" in captured.out

    def test_calls_create_config_yaml_with_verbose_false_when_index_exists(self, mock_repo):
        """Should call create_config_yaml with verbose=False when index_exists=True"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.create_config_yaml") as mock_create_config:
                with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                    config_path = mock_repo / ".mcp.json"
                    mock_mcp.return_value = (config_path, {"mcpServers": {}})

                    setup("claude", mock_repo, index_exists=True)

                    # Verify verbose=False was passed
                    mock_create_config.assert_called_once()
                    call_kwargs = mock_create_config.call_args[1]
                    assert call_kwargs["verbose"] is False


class TestSetupKeywordParameters:
    """Tests for setup() keyword_method and keyword_tier parameters"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")
        return repo_path

    def test_passes_extraction_method_to_create_config_yaml(self, mock_repo):
        """Should pass extraction_method and expansion_method to create_config_yaml"""
        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml") as mock_create_config:
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        storage_dir = mock_repo.parent / "storage"
                        mock_create_storage.return_value = storage_dir
                        config_path = mock_repo / ".mcp.json"
                        mock_mcp.return_value = (config_path, {"mcpServers": {}})

                        setup(
                            "claude", mock_repo, extraction_method="bert", expansion_method="glove"
                        )

                        mock_create_config.assert_called()
                        # Check positional args: repo_path, storage_dir, extraction_method, expansion_method
                        call_args = mock_create_config.call_args[0]
                        assert call_args[2] == "bert"  # extraction_method is 3rd positional arg
                        assert call_args[3] == "glove"  # expansion_method is 4th positional arg

    def test_defaults_when_no_method_specified(self, mock_repo):
        """Should use default methods when not specified"""
        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml") as mock_create_config:
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        storage_dir = mock_repo.parent / "storage"
                        mock_create_storage.return_value = storage_dir
                        config_path = mock_repo / ".mcp.json"
                        mock_mcp.return_value = (config_path, {"mcpServers": {}})

                        setup("claude", mock_repo)

                        # Should pass None for both (create_config_yaml handles defaults)
                        mock_create_config.assert_called()
                        call_args = mock_create_config.call_args[0]
                        assert call_args[2] is None  # extraction_method is 3rd positional arg
                        assert call_args[3] is None  # expansion_method is 4th positional arg


class TestSetupSettingsChangeDetection:
    """Tests for setup() settings change detection and reindexing"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository with existing config"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")
        return repo_path

    def test_detects_method_change_and_prompts_user(self, mock_repo, capsys):
        """Should detect extraction method change and prompt for confirmation"""
        import yaml

        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.get_config_path") as mock_get_config:
                with patch("cicada.setup.get_index_path") as mock_get_index:
                    with patch("cicada.setup.index_repository") as mock_index:
                        with patch("cicada.setup.create_config_yaml"):
                            with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                                with patch("builtins.input", return_value="n"):
                                    storage_dir = mock_repo.parent / "storage"
                                    storage_dir.mkdir()
                                    mock_create_storage.return_value = storage_dir

                                    config_path = storage_dir / "config.yaml"
                                    index_path = storage_dir / "index.json"
                                    mock_get_config.return_value = config_path
                                    mock_get_index.return_value = index_path

                                    # Create existing config with regular extraction
                                    config_path.write_text(
                                        yaml.dump(
                                            {
                                                "keyword_extraction": {"method": "regular"},
                                                "keyword_expansion": {"method": "lemmi"},
                                            }
                                        )
                                    )
                                    index_path.touch()

                                    mcp_config_path = mock_repo / ".mcp.json"
                                    mock_mcp.return_value = (mcp_config_path, {"mcpServers": {}})

                                    # Try to change to bert
                                    with pytest.raises(SystemExit):
                                        setup(
                                            "claude",
                                            mock_repo,
                                            extraction_method="bert",
                                            expansion_method="glove",
                                        )

                                    captured = capsys.readouterr()
                                    assert (
                                        "WARNING" in captured.out
                                        or "Settings changed" in captured.out
                                    )
                                    assert "Setup cancelled" in captured.out

    def test_proceeds_with_reindex_when_user_confirms(self, mock_repo):
        """Should reindex with force_full=True when user confirms settings change"""
        import yaml

        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.get_config_path") as mock_get_config:
                with patch("cicada.setup.get_index_path") as mock_get_index:
                    with patch("cicada.setup.index_repository") as mock_index:
                        with patch("cicada.setup.create_config_yaml"):
                            with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                                with patch("builtins.input", return_value="y"):
                                    storage_dir = mock_repo.parent / "storage"
                                    storage_dir.mkdir()
                                    mock_create_storage.return_value = storage_dir

                                    config_path = storage_dir / "config.yaml"
                                    index_path = storage_dir / "index.json"
                                    mock_get_config.return_value = config_path
                                    mock_get_index.return_value = index_path

                                    # Create existing config
                                    config_path.write_text(
                                        yaml.dump(
                                            {
                                                "keyword_extraction": {"method": "regular"},
                                                "keyword_expansion": {"method": "lemmi"},
                                            }
                                        )
                                    )
                                    index_path.touch()

                                    mcp_config_path = mock_repo / ".mcp.json"
                                    mock_mcp.return_value = (mcp_config_path, {"mcpServers": {}})

                                    setup(
                                        "claude",
                                        mock_repo,
                                        extraction_method="bert",
                                        expansion_method="glove",
                                    )

                                    # Should call index_repository with force_full=True
                                    mock_index.assert_called_once()
                                    call_kwargs = mock_index.call_args[1]
                                    assert call_kwargs["force_full"] is True

    def test_skips_reindex_when_settings_unchanged(self, mock_repo, capsys):
        """Should skip reindexing when settings haven't changed"""
        import yaml

        with patch("cicada.setup.create_storage_dir") as mock_create_storage:
            with patch("cicada.setup.get_config_path") as mock_get_config:
                with patch("cicada.setup.get_index_path") as mock_get_index:
                    with patch("cicada.setup.index_repository") as mock_index:
                        with patch("cicada.setup.create_config_yaml"):
                            with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                                storage_dir = mock_repo.parent / "storage"
                                storage_dir.mkdir()
                                mock_create_storage.return_value = storage_dir

                                config_path = storage_dir / "config.yaml"
                                index_path = storage_dir / "index.json"
                                mock_get_config.return_value = config_path
                                mock_get_index.return_value = index_path

                                # Create existing config with bert extraction and glove expansion
                                config_path.write_text(
                                    yaml.dump(
                                        {
                                            "keyword_extraction": {"method": "bert"},
                                            "keyword_expansion": {"method": "glove"},
                                        }
                                    )
                                )
                                index_path.touch()

                                mcp_config_path = mock_repo / ".mcp.json"
                                mock_mcp.return_value = (mcp_config_path, {"mcpServers": {}})

                                # Setup with same settings
                                setup(
                                    "claude",
                                    mock_repo,
                                    extraction_method="bert",
                                    expansion_method="glove",
                                )

                                # Should NOT call index_repository
                                mock_index.assert_not_called()

                                captured = capsys.readouterr()
                                assert "✓ Using existing index" in captured.out


class TestMainErrorCases:
    """Tests for main() error handling"""

    def test_main_validates_path_exists(self, tmp_path):
        """Main should exit with error if path doesn't exist"""
        from cicada.setup import main

        nonexistent = tmp_path / "does_not_exist"

        with patch("sys.argv", ["cicada", "claude", str(nonexistent)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_main_validates_path_is_directory(self, tmp_path):
        """Main should exit with error if path is not a directory"""
        from cicada.setup import main

        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")

        with patch("sys.argv", ["cicada", "claude", str(file_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_main_handles_setup_failure(self, tmp_path, capsys):
        """Main should handle setup() exceptions and exit gracefully"""
        from cicada.setup import main

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")

        with patch("sys.argv", ["cicada", "claude", str(repo_path)]):
            with patch("cicada.setup.setup", side_effect=Exception("Setup failed")):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error: Setup failed: Setup failed" in captured.out


class TestSetupPermanentInstallationTip:
    """Tests for permanent installation tip in setup()"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")
        return repo_path

    def test_shows_installation_tip_when_cicada_not_installed(self, mock_repo, capsys):
        """Should show installation tip when cicada-mcp/cicada-server not in PATH"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch("shutil.which", return_value=None):
                            config_path = mock_repo / ".mcp.json"
                            mock_mcp.return_value = (config_path, {"mcpServers": {}})

                            setup("claude", mock_repo)

                            captured = capsys.readouterr()
                            assert (
                                "💡 Tip: For best experience, install Cicada permanently"
                                in captured.out
                            )
                            assert "uv tool install" in captured.out
                            assert "cicada-index" in captured.out

    def test_hides_installation_tip_when_cicada_mcp_installed(self, mock_repo, capsys):
        """Should not show tip when cicada-mcp is installed"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch(
                            "shutil.which",
                            side_effect=lambda x: "cicada-mcp" if x == "cicada-mcp" else None,
                        ):
                            config_path = mock_repo / ".mcp.json"
                            mock_mcp.return_value = (config_path, {"mcpServers": {}})

                            setup("claude", mock_repo)

                            captured = capsys.readouterr()
                            assert "💡 Tip: For best experience" not in captured.out

    def test_hides_installation_tip_when_cicada_server_installed(self, mock_repo, capsys):
        """Should not show tip when cicada-server is installed (backwards compat)"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.index_repository"):
                with patch("cicada.setup.create_config_yaml"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch(
                            "shutil.which",
                            side_effect=lambda x: "cicada-server" if x == "cicada-server" else None,
                        ):
                            config_path = mock_repo / ".mcp.json"
                            mock_mcp.return_value = (config_path, {"mcpServers": {}})

                            setup("claude", mock_repo)

                            captured = capsys.readouterr()
                            assert "💡 Tip: For best experience" not in captured.out


class TestUpdateClaudeMd:
    """Tests for update_claude_md() function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "mix.exs").write_text("# Mock")
        return repo_path

    def test_setup_claude_calls_update_claude_md(self, mock_repo):
        """Test that setup() calls update_claude_md() when editor is 'claude'"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.create_config_yaml"):
                with patch("cicada.setup.index_repository"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch("cicada.setup.update_claude_md") as mock_update:
                            config_path = mock_repo / ".mcp.json"
                            mock_mcp.return_value = (config_path, {"mcpServers": {}})

                            setup(
                                "claude",
                                mock_repo,
                                extraction_method="regular",
                                expansion_method="lemmi",
                            )

                            # Verify update_claude_md was called with correct repo_path
                            mock_update.assert_called_once_with(mock_repo)

    def test_setup_cursor_does_not_call_update_claude_md(self, mock_repo):
        """Test that setup() does NOT call update_claude_md() when editor is 'cursor'"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.create_config_yaml"):
                with patch("cicada.setup.index_repository"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch("cicada.setup.update_claude_md") as mock_update:
                            cursor_config_dir = mock_repo / ".cursor"
                            cursor_config_dir.mkdir()
                            config_path = cursor_config_dir / "mcp.json"
                            mock_mcp.return_value = (config_path, {"mcpServers": {}})

                            setup(
                                "cursor",
                                mock_repo,
                                extraction_method="regular",
                                expansion_method="lemmi",
                            )

                            # Verify update_claude_md was NOT called
                            mock_update.assert_not_called()

    def test_setup_vs_does_not_call_update_claude_md(self, mock_repo):
        """Test that setup() does NOT call update_claude_md() when editor is 'vs'"""
        with patch("cicada.setup.create_storage_dir"):
            with patch("cicada.setup.create_config_yaml"):
                with patch("cicada.setup.index_repository"):
                    with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                        with patch("cicada.setup.update_claude_md") as mock_update:
                            vscode_config_dir = mock_repo / ".vscode"
                            vscode_config_dir.mkdir()
                            config_path = vscode_config_dir / "settings.json"
                            mock_mcp.return_value = (config_path, {"mcp.servers": {}})

                            setup(
                                "vs",
                                mock_repo,
                                extraction_method="regular",
                                expansion_method="lemmi",
                            )

                            # Verify update_claude_md was NOT called
                            mock_update.assert_not_called()

    def test_setup_claude_with_existing_index_calls_update_claude_md(self, mock_repo, tmp_path):
        """Test that setup() calls update_claude_md() even when index_exists=True"""
        storage_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        (storage_dir / "index.json").write_text("{}")
        (storage_dir / "config.yaml").write_text("repository:\n  path: /tmp/test\n")

        with patch("cicada.setup.create_storage_dir", return_value=storage_dir):
            with patch("cicada.setup.create_config_yaml"):
                with patch(
                    "cicada.setup.get_config_path", return_value=storage_dir / "config.yaml"
                ):
                    with patch(
                        "cicada.setup.get_index_path", return_value=storage_dir / "index.json"
                    ):
                        with patch("cicada.setup.get_mcp_config_for_editor") as mock_mcp:
                            config_path = mock_repo / ".mcp.json"
                            mock_mcp.return_value = (config_path, {"mcpServers": {}})

                            # Create CLAUDE.md
                            claude_md = mock_repo / "CLAUDE.md"
                            claude_md.write_text("# Project\n")

                            # Call setup with index_exists=True
                            setup(
                                "claude",
                                mock_repo,
                                extraction_method="regular",
                                expansion_method="lemmi",
                                index_exists=True,
                            )

                            # Verify CLAUDE.md was updated
                            content = claude_md.read_text()
                            assert "<cicada>" in content
                            assert "ALWAYS use cicada-mcp tools" in content
