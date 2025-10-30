"""
Comprehensive tests for cicada/clean.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cicada.clean import remove_mcp_config_entry, clean_repository, main


class TestRemoveMcpConfigEntry:
    """Tests for remove_mcp_config_entry function"""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config file"""
        config_path = tmp_path / ".mcp.json"
        config = {
            "mcpServers": {
                "cicada": {"command": "cicada-server", "env": {}},
                "other": {"command": "other-server"},
            }
        }
        config_path.write_text(json.dumps(config, indent=2))
        return config_path

    def test_removes_cicada_entry_from_claude_config(self, temp_config):
        """Should remove cicada entry from Claude config"""
        result = remove_mcp_config_entry(temp_config)
        assert result is True

        # Verify cicada was removed but other server remains
        with open(temp_config, "r") as f:
            config = json.load(f)

        assert "cicada" not in config["mcpServers"]
        assert "other" in config["mcpServers"]

    def test_returns_false_when_file_not_exists(self, tmp_path):
        """Should return False when config file doesn't exist"""
        non_existent = tmp_path / "non_existent.json"
        result = remove_mcp_config_entry(non_existent)
        assert result is False

    def test_handles_cursor_config(self, tmp_path):
        """Should handle Cursor config correctly"""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir()

        config = {
            "mcpServers": {
                "cicada": {"command": "cicada-server"},
                "other": {"command": "other"},
            }
        }
        config_path.write_text(json.dumps(config))

        result = remove_mcp_config_entry(config_path)
        assert result is True

        with open(config_path, "r") as f:
            updated = json.load(f)

        assert "cicada" not in updated["mcpServers"]
        assert "other" in updated["mcpServers"]

    def test_handles_vscode_config(self, tmp_path):
        """Should handle VS Code config correctly"""
        config_path = tmp_path / ".vscode" / "settings.json"
        config_path.parent.mkdir()

        config = {
            "mcp.servers": {
                "cicada": {"command": "cicada-server"},
                "other": {"command": "other"},
            }
        }
        config_path.write_text(json.dumps(config))

        result = remove_mcp_config_entry(config_path)
        assert result is True

        with open(config_path, "r") as f:
            updated = json.load(f)

        assert "cicada" not in updated["mcp.servers"]
        assert "other" in updated["mcp.servers"]

    def test_returns_false_when_no_cicada_entry(self, tmp_path):
        """Should return False when no cicada entry exists"""
        config_path = tmp_path / ".mcp.json"
        config = {"mcpServers": {"other": {"command": "other-server"}}}
        config_path.write_text(json.dumps(config))

        result = remove_mcp_config_entry(config_path)
        assert result is False

    def test_handles_malformed_json(self, tmp_path, capsys):
        """Should handle malformed JSON gracefully"""
        config_path = tmp_path / ".mcp.json"
        config_path.write_text("{invalid json}")

        result = remove_mcp_config_entry(config_path)
        assert result is False

        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_handles_io_error(self, tmp_path, capsys):
        """Should handle IO errors gracefully"""
        config_path = tmp_path / ".mcp.json"
        config_path.write_text('{"mcpServers": {}}')

        # Make file unreadable
        config_path.chmod(0o000)

        try:
            result = remove_mcp_config_entry(config_path)
            assert result is False
        finally:
            # Restore permissions for cleanup
            config_path.chmod(0o644)

    def test_preserves_other_config_sections(self, tmp_path):
        """Should preserve other configuration sections"""
        config_path = tmp_path / ".mcp.json"
        config = {
            "mcpServers": {"cicada": {"command": "cicada-server"}},
            "otherSettings": {"key": "value"},
        }
        config_path.write_text(json.dumps(config))

        remove_mcp_config_entry(config_path)

        with open(config_path, "r") as f:
            updated = json.load(f)

        assert "otherSettings" in updated
        assert updated["otherSettings"]["key"] == "value"


class TestCleanRepository:
    """Tests for clean_repository function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository with Cicada setup"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage directory
        storage_dir = tmp_path / ".cicada" / "projects" / "test_hash"
        storage_dir.mkdir(parents=True)
        (storage_dir / "index.json").write_text("{}")
        (storage_dir / "config.yaml").write_text("")

        # Create old .cicada directory
        old_cicada = repo_path / ".cicada"
        old_cicada.mkdir()
        (old_cicada / "index.json").write_text("{}")

        # Create MCP configs
        claude_config = repo_path / ".mcp.json"
        claude_config.write_text(
            json.dumps({"mcpServers": {"cicada": {"command": "cicada-server"}}})
        )

        cursor_dir = repo_path / ".cursor"
        cursor_dir.mkdir()
        cursor_config = cursor_dir / "mcp.json"
        cursor_config.write_text(
            json.dumps({"mcpServers": {"cicada": {"command": "cicada-server"}}})
        )

        vscode_dir = repo_path / ".vscode"
        vscode_dir.mkdir()
        vscode_config = vscode_dir / "settings.json"
        vscode_config.write_text(
            json.dumps({"mcp.servers": {"cicada": {"command": "cicada-server"}}})
        )

        return repo_path, storage_dir

    def test_removes_all_cicada_files_with_force(self, mock_repo):
        """Should remove all Cicada files when force=True"""
        repo_path, storage_dir = mock_repo

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            clean_repository(repo_path, force=True)

        # Storage directory should be removed
        assert not storage_dir.exists()

        # Old .cicada should be removed
        assert not (repo_path / ".cicada").exists()

        # MCP configs should have cicada entry removed
        with open(repo_path / ".mcp.json", "r") as f:
            config = json.load(f)
            assert "cicada" not in config.get("mcpServers", {})

    def test_prompts_for_confirmation_without_force(self, mock_repo):
        """Should prompt for confirmation when force=False"""
        repo_path, storage_dir = mock_repo

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            with patch("builtins.input", return_value="n"):
                clean_repository(repo_path, force=False)

        # Nothing should be removed
        assert storage_dir.exists()
        assert (repo_path / ".cicada").exists()

    def test_removes_files_when_user_confirms(self, mock_repo):
        """Should remove files when user confirms"""
        repo_path, storage_dir = mock_repo

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            with patch("builtins.input", return_value="y"):
                clean_repository(repo_path, force=False)

        # Files should be removed
        assert not storage_dir.exists()
        assert not (repo_path / ".cicada").exists()

    def test_accepts_yes_variations(self, mock_repo):
        """Should accept 'yes' as well as 'y'"""
        repo_path, storage_dir = mock_repo

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            with patch("builtins.input", return_value="yes"):
                clean_repository(repo_path, force=False)

        assert not storage_dir.exists()

    def test_handles_nonexistent_storage_dir(self, tmp_path):
        """Should handle case when storage directory doesn't exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        storage_dir = tmp_path / ".cicada" / "projects" / "nonexistent"

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            # Should not raise an error
            clean_repository(repo_path, force=True)

    def test_handles_permission_errors(self, mock_repo, capsys):
        """Should handle permission errors gracefully"""
        repo_path, storage_dir = mock_repo

        # Make storage directory unremovable
        storage_dir.chmod(0o000)

        try:
            with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
                clean_repository(repo_path, force=True)

            captured = capsys.readouterr()
            assert "Failed" in captured.out
        finally:
            # Restore permissions for cleanup
            storage_dir.chmod(0o755)

    def test_displays_items_to_be_removed(self, mock_repo, capsys):
        """Should display all items that will be removed"""
        repo_path, storage_dir = mock_repo

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            with patch("builtins.input", return_value="n"):
                clean_repository(repo_path, force=False)

        captured = capsys.readouterr()
        assert "Storage directory" in captured.out
        assert "Legacy .cicada directory" in captured.out
        assert "Claude Code config" in captured.out

    def test_shows_success_message(self, mock_repo, capsys):
        """Should show success message after cleanup"""
        repo_path, storage_dir = mock_repo

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            clean_repository(repo_path, force=True)

        captured = capsys.readouterr()
        assert "Cleanup Complete" in captured.out

    def test_handles_empty_repository(self, tmp_path, capsys):
        """Should handle repository with no Cicada setup"""
        repo_path = tmp_path / "empty_repo"
        repo_path.mkdir()
        storage_dir = tmp_path / ".cicada" / "projects" / "empty_hash"

        with patch("cicada.clean.get_storage_dir", return_value=storage_dir):
            clean_repository(repo_path, force=True)

        captured = capsys.readouterr()
        assert "No Cicada configuration found" in captured.out


class TestMainFunction:
    """Tests for main CLI entry point"""

    def test_main_uses_current_directory_by_default(self, tmp_path):
        """Main should use current directory if no path provided"""
        from cicada.clean import main

        # Create a real temporary directory to use as cwd
        cwd = tmp_path / "cwd"
        cwd.mkdir()

        with patch("sys.argv", ["cicada-clean", "-f"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = cwd
                    main()

                    mock_clean.assert_called_once()
                    args = mock_clean.call_args
                    assert args[0][0] == cwd
                    assert args[1]["force"] is True

    def test_main_accepts_repo_argument(self, tmp_path):
        """Main should accept repository path as argument"""
        from cicada.clean import main

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        with patch("sys.argv", ["cicada-clean", str(repo_path), "-f"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                main()

                mock_clean.assert_called_once()
                args = mock_clean.call_args
                assert args[0][0] == repo_path

    def test_main_force_flag(self, tmp_path):
        """Main should handle -f/--force flag"""
        from cicada.clean import main

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Test short flag
        with patch("sys.argv", ["cicada-clean", str(repo_path), "-f"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                main()
                assert mock_clean.call_args[1]["force"] is True

        # Test long flag
        with patch("sys.argv", ["cicada-clean", str(repo_path), "--force"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                main()
                assert mock_clean.call_args[1]["force"] is True

    def test_main_without_force_flag(self, tmp_path):
        """Main should pass force=False when flag not provided"""
        from cicada.clean import main

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        with patch("sys.argv", ["cicada-clean", str(repo_path)]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                with patch("builtins.input", return_value="n"):
                    main()
                    assert mock_clean.call_args[1]["force"] is False

    def test_main_validates_path_exists(self):
        """Main should validate that path exists"""
        from cicada.clean import main

        with patch("sys.argv", ["cicada-clean", "/nonexistent/path", "-f"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_validates_path_is_directory(self, tmp_path):
        """Main should validate that path is a directory"""
        from cicada.clean import main

        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with patch("sys.argv", ["cicada-clean", str(file_path), "-f"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_handles_exceptions(self, tmp_path):
        """Main should handle exceptions and exit with error code"""
        from cicada.clean import main

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        with patch("sys.argv", ["cicada-clean", str(repo_path), "-f"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                mock_clean.side_effect = Exception("Test error")

                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
