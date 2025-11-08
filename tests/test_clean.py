"""
Comprehensive tests for cicada/clean.py
"""

import json
from unittest.mock import patch

import pytest

from cicada.clean import (
    clean_all_projects,
    clean_index_only,
    clean_pr_index_only,
    clean_repository,
    main,
    remove_mcp_config_entry,
)


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
        with open(temp_config) as f:
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

        with open(config_path) as f:
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

        with open(config_path) as f:
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

        with open(config_path) as f:
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
        with open(repo_path / ".mcp.json") as f:
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
        """Should exit with error code when permission errors occur"""
        repo_path, storage_dir = mock_repo

        # Mock shutil.rmtree to raise PermissionError (works even as root)
        import shutil

        original_rmtree = shutil.rmtree

        def mock_rmtree(path, *args, **kwargs):
            if str(path) == str(storage_dir):
                raise PermissionError(f"Permission denied: {path}")
            return original_rmtree(path, *args, **kwargs)

        with (
            patch("cicada.clean.get_storage_dir", return_value=storage_dir),
            patch("shutil.rmtree", side_effect=mock_rmtree),
            pytest.raises(SystemExit) as exc_info,
        ):
            clean_repository(repo_path, force=True)

        # Should exit with error code 1
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Failed" in captured.out
        assert "⚠ Cleanup completed with errors" in captured.out

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
        """Main should use current directory"""

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

    def test_main_force_flag(self, tmp_path):
        """Main should handle -f/--force flag"""

        cwd = tmp_path / "test_repo"
        cwd.mkdir()

        # Test short flag
        with patch("sys.argv", ["cicada-clean", "-f"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = cwd
                    main()
                    assert mock_clean.call_args[1]["force"] is True

        # Test long flag
        with patch("sys.argv", ["cicada-clean", "--force"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = cwd
                    main()
                    assert mock_clean.call_args[1]["force"] is True

    def test_main_without_force_flag(self, tmp_path):
        """Main should pass force=False when flag not provided"""

        cwd = tmp_path / "test_repo"
        cwd.mkdir()

        with patch("sys.argv", ["cicada-clean"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = cwd
                    with patch("builtins.input", return_value="n"):
                        main()
                        assert mock_clean.call_args[1]["force"] is False

    def test_main_handles_exceptions(self, tmp_path):
        """Main should handle exceptions and exit with error code"""

        cwd = tmp_path / "test_repo"
        cwd.mkdir()

        with patch("sys.argv", ["cicada-clean", "-f"]):
            with patch("cicada.clean.clean_repository") as mock_clean:
                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = cwd
                    mock_clean.side_effect = Exception("Test error")

                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

    def test_main_all_flag(self, tmp_path):
        """Main should call clean_all_projects with --all flag"""
        with patch("sys.argv", ["cicada-clean", "--all", "-f"]):
            with patch("cicada.clean.clean_all_projects") as mock_clean_all:
                main()

                mock_clean_all.assert_called_once_with(force=True)

    def test_main_all_flag_without_force(self, tmp_path):
        """Main should pass force=False to clean_all_projects when -f not provided"""
        with patch("sys.argv", ["cicada-clean", "--all"]):
            with patch("cicada.clean.clean_all_projects") as mock_clean_all:
                with patch("builtins.input", return_value="n"):
                    main()

                mock_clean_all.assert_called_once_with(force=False)

    def test_main_all_flag_handles_exceptions(self):
        """Main should handle exceptions from clean_all_projects"""
        with patch("sys.argv", ["cicada-clean", "--all", "-f"]):
            with patch("cicada.clean.clean_all_projects") as mock_clean_all:
                mock_clean_all.side_effect = Exception("Clean all failed")

                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1


class TestCleanIndexOnly:
    """Tests for clean_index_only function"""

    def test_removes_index_and_hashes_files(self, tmp_path):
        """Should remove index.json and hashes.json files"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        index_path = tmp_path / "index.json"
        index_path.write_text("{}")

        hashes_path = tmp_path / "hashes.json"
        hashes_path.write_text("{}")

        with (
            patch("cicada.clean.get_index_path", return_value=index_path),
            patch("cicada.clean.get_hashes_path", return_value=hashes_path),
        ):
            clean_index_only(repo_path)

        assert not index_path.exists()
        assert not hashes_path.exists()

    def test_handles_missing_index_file(self, tmp_path, capsys):
        """Should handle case when index file doesn't exist"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        index_path = tmp_path / "index.json"  # Doesn't exist
        hashes_path = tmp_path / "hashes.json"

        with (
            patch("cicada.clean.get_index_path", return_value=index_path),
            patch("cicada.clean.get_hashes_path", return_value=hashes_path),
        ):
            clean_index_only(repo_path)

        captured = capsys.readouterr()
        assert "No main index files found" in captured.out

    def test_handles_missing_hashes_file(self, tmp_path, capsys):
        """Should handle case when hashes file doesn't exist"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        index_path = tmp_path / "index.json"
        index_path.write_text("{}")

        hashes_path = tmp_path / "hashes.json"  # Doesn't exist

        with (
            patch("cicada.clean.get_index_path", return_value=index_path),
            patch("cicada.clean.get_hashes_path", return_value=hashes_path),
        ):
            clean_index_only(repo_path)

        assert not index_path.exists()
        captured = capsys.readouterr()
        assert "Removed Main index" in captured.out

    def test_shows_success_message(self, tmp_path, capsys):
        """Should show success message after cleanup"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        index_path = tmp_path / "index.json"
        index_path.write_text("{}")

        hashes_path = tmp_path / "hashes.json"
        hashes_path.write_text("{}")

        with (
            patch("cicada.clean.get_index_path", return_value=index_path),
            patch("cicada.clean.get_hashes_path", return_value=hashes_path),
        ):
            clean_index_only(repo_path)

        captured = capsys.readouterr()
        assert "✓ Cleanup Complete!" in captured.out
        assert "2 items removed" in captured.out

    def test_resolves_repo_path(self, tmp_path):
        """Should resolve repo path to absolute path"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        index_path = tmp_path / "index.json"
        hashes_path = tmp_path / "hashes.json"

        with (
            patch("cicada.clean.get_index_path", return_value=index_path) as mock_get_index,
            patch("cicada.clean.get_hashes_path", return_value=hashes_path),
        ):
            # Pass relative path
            with patch("pathlib.Path.resolve", return_value=repo_path.resolve()):
                clean_index_only(repo_path)

            # Should resolve the path
            assert mock_get_index.call_count == 1


class TestCleanPrIndexOnly:
    """Tests for clean_pr_index_only function"""

    def test_removes_pr_index_file(self, tmp_path, capsys):
        """Should remove pr_index.json file"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        pr_index_path = tmp_path / "pr_index.json"
        pr_index_path.write_text("{}")

        with patch("cicada.clean.get_pr_index_path", return_value=pr_index_path):
            clean_pr_index_only(repo_path)

        assert not pr_index_path.exists()
        captured = capsys.readouterr()
        assert "✓ Removed PR index" in captured.out
        assert "✓ Cleanup Complete!" in captured.out

    def test_handles_missing_pr_index(self, tmp_path, capsys):
        """Should handle case when PR index doesn't exist"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        pr_index_path = tmp_path / "pr_index.json"  # Doesn't exist

        with patch("cicada.clean.get_pr_index_path", return_value=pr_index_path):
            clean_pr_index_only(repo_path)

        captured = capsys.readouterr()
        assert "No PR index file found" in captured.out

    def test_resolves_repo_path(self, tmp_path):
        """Should resolve repo path to absolute path"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        pr_index_path = tmp_path / "pr_index.json"

        with patch("cicada.clean.get_pr_index_path", return_value=pr_index_path) as mock_get_pr:
            with patch("pathlib.Path.resolve", return_value=repo_path.resolve()):
                clean_pr_index_only(repo_path)

            assert mock_get_pr.call_count == 1


class TestCleanAllProjects:
    """Tests for clean_all_projects function"""

    def test_removes_all_project_directories(self, tmp_path, capsys):
        """Should remove all project directories"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        # Create mock project directories
        proj1 = storage_base / "hash1"
        proj1.mkdir()
        (proj1 / "index.json").write_text("{}")

        proj2 = storage_base / "hash2"
        proj2.mkdir()
        (proj2 / "config.yaml").write_text("")

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("builtins.input", return_value="y"),
        ):
            clean_all_projects(force=False)

        assert not proj1.exists()
        assert not proj2.exists()

        captured = capsys.readouterr()
        assert "✓ Cleanup Complete!" in captured.out
        assert "2/2 projects removed" in captured.out

    def test_skips_confirmation_with_force(self, tmp_path):
        """Should skip confirmation prompt when force=True"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        proj1 = storage_base / "hash1"
        proj1.mkdir()

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Should not prompt for input
            clean_all_projects(force=True)

        assert not proj1.exists()

    def test_cancels_on_negative_confirmation(self, tmp_path, capsys):
        """Should cancel when user says no"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        proj1 = storage_base / "hash1"
        proj1.mkdir()

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("builtins.input", return_value="n"),
        ):
            clean_all_projects(force=False)

        # Should still exist
        assert proj1.exists()

        captured = capsys.readouterr()
        assert "Aborted" in captured.out

    def test_handles_nonexistent_storage(self, tmp_path, capsys):
        """Should handle case when storage directory doesn't exist"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            clean_all_projects(force=True)

        captured = capsys.readouterr()
        assert "No Cicada storage found" in captured.out

    def test_handles_empty_storage(self, tmp_path, capsys):
        """Should handle case when storage exists but has no projects"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        with patch("pathlib.Path.home", return_value=tmp_path):
            clean_all_projects(force=True)

        captured = capsys.readouterr()
        assert "No Cicada projects found" in captured.out

    def test_handles_permission_errors(self, tmp_path, capsys):
        """Should handle permission errors and exit with error code"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        proj1 = storage_base / "hash1"
        proj1.mkdir()

        # Mock shutil.rmtree to raise PermissionError (works even as root)
        import shutil

        original_rmtree = shutil.rmtree

        def mock_rmtree(path, *args, **kwargs):
            if "hash1" in str(path):
                raise PermissionError(f"Permission denied: {path}")
            return original_rmtree(path, *args, **kwargs)

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("shutil.rmtree", side_effect=mock_rmtree),
            pytest.raises(SystemExit) as exc_info,
        ):
            clean_all_projects(force=True)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to remove" in captured.out
        assert "⚠ Cleanup completed with errors" in captured.out

    def test_shows_project_list(self, tmp_path, capsys):
        """Should show list of projects to be removed"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        proj1 = storage_base / "abc123"
        proj1.mkdir()

        proj2 = storage_base / "def456"
        proj2.mkdir()

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("builtins.input", return_value="n"),
        ):
            clean_all_projects(force=False)

        captured = capsys.readouterr()
        assert "Found 2 project(s)" in captured.out
        assert "abc123/" in captured.out
        assert "def456/" in captured.out

    def test_accepts_yes_variations(self, tmp_path):
        """Should accept 'yes' as well as 'y'"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        proj1 = storage_base / "hash1"
        proj1.mkdir()

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("builtins.input", return_value="yes"),
        ):
            clean_all_projects(force=False)

        assert not proj1.exists()

    def test_partial_success_with_errors(self, tmp_path, capsys):
        """Should handle partial success when some removals fail"""
        storage_base = tmp_path / ".cicada" / "projects"
        storage_base.mkdir(parents=True)

        proj1 = storage_base / "hash1"
        proj1.mkdir()

        proj2 = storage_base / "hash2"
        proj2.mkdir()

        # Mock shutil.rmtree to raise PermissionError for hash2 only (works even as root)
        import shutil

        original_rmtree = shutil.rmtree

        def mock_rmtree(path, *args, **kwargs):
            if "hash2" in str(path):
                raise PermissionError(f"Permission denied: {path}")
            return original_rmtree(path, *args, **kwargs)

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("shutil.rmtree", side_effect=mock_rmtree),
            pytest.raises(SystemExit) as exc_info,
        ):
            clean_all_projects(force=True)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "1/2 projects removed" in captured.out
