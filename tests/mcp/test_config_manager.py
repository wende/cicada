"""Tests for cicada/mcp/config_manager.py"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cicada.mcp.config_manager import ConfigManager


class TestGetConfigPath:
    """Test ConfigManager.get_config_path() method."""

    def test_uses_cicada_config_dir_when_set(self, monkeypatch, tmp_path):
        """Test that CICADA_CONFIG_DIR takes precedence."""
        config_dir = tmp_path / "storage"
        config_dir.mkdir()

        monkeypatch.setenv("CICADA_CONFIG_DIR", str(config_dir))

        result = ConfigManager.get_config_path()

        assert result == str(config_dir / "config.yaml")

    def test_resolves_link_when_cicada_config_dir_is_linked(self, monkeypatch, tmp_path):
        """Test that CICADA_CONFIG_DIR resolves links to source storage."""
        # Create source storage directory with config
        source_storage = tmp_path / "source_storage"
        source_storage.mkdir()
        source_config = source_storage / "config.yaml"
        source_config.write_text("repository:\n  path: /source/repo\n")

        # Create linked storage directory with link.yaml
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_data = {
            "source_repo_path": "/source/repo",
            "source_storage_dir": str(source_storage),
            "linked_at": "2025-11-24T12:00:00",
        }
        with open(link_file, "w") as f:
            yaml.dump(link_data, f)

        # Set CICADA_CONFIG_DIR to linked storage
        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should return source config path, not linked storage path
        assert result == str(source_storage / "config.yaml")
        assert result != str(linked_storage / "config.yaml")

    def test_falls_back_when_link_yaml_is_corrupted(self, monkeypatch, tmp_path):
        """Test that corrupted link.yaml falls back to using config_dir directly."""
        # Create linked storage directory with corrupted link.yaml
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_file.write_text("invalid: yaml: [unclosed")

        # Set CICADA_CONFIG_DIR to linked storage
        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should fall back to linked storage config path
        assert result == str(linked_storage / "config.yaml")

    def test_falls_back_when_link_yaml_missing_source_storage_dir(self, monkeypatch, tmp_path):
        """Test that link.yaml without source_storage_dir falls back."""
        # Create linked storage directory with incomplete link.yaml
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_data = {
            "source_repo_path": "/source/repo",
            # Missing source_storage_dir field
            "linked_at": "2025-11-24T12:00:00",
        }
        with open(link_file, "w") as f:
            yaml.dump(link_data, f)

        # Set CICADA_CONFIG_DIR to linked storage
        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should fall back to linked storage config path
        assert result == str(linked_storage / "config.yaml")

    def test_falls_back_when_source_storage_dir_is_null(self, monkeypatch, tmp_path):
        """Test that link.yaml with null source_storage_dir falls back."""
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_data = {
            "source_repo_path": "/source/repo",
            "source_storage_dir": None,
            "linked_at": "2025-11-24T12:00:00",
        }
        with open(link_file, "w") as f:
            yaml.dump(link_data, f)

        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should fall back to linked storage config path
        assert result == str(linked_storage / "config.yaml")

    def test_falls_back_when_source_storage_dir_is_empty_string(self, monkeypatch, tmp_path):
        """Test that link.yaml with empty source_storage_dir falls back."""
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_data = {
            "source_repo_path": "/source/repo",
            "source_storage_dir": "",
            "linked_at": "2025-11-24T12:00:00",
        }
        with open(link_file, "w") as f:
            yaml.dump(link_data, f)

        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should fall back to linked storage config path
        assert result == str(linked_storage / "config.yaml")

    def test_falls_back_when_source_storage_dir_is_whitespace(self, monkeypatch, tmp_path):
        """Test that link.yaml with whitespace-only source_storage_dir falls back."""
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_data = {
            "source_repo_path": "/source/repo",
            "source_storage_dir": "   ",
            "linked_at": "2025-11-24T12:00:00",
        }
        with open(link_file, "w") as f:
            yaml.dump(link_data, f)

        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should fall back to linked storage config path
        assert result == str(linked_storage / "config.yaml")

    def test_falls_back_when_source_storage_dir_is_number(self, monkeypatch, tmp_path):
        """Test that link.yaml with non-string source_storage_dir falls back."""
        linked_storage = tmp_path / "linked_storage"
        linked_storage.mkdir()
        link_file = linked_storage / "link.yaml"
        link_data = {
            "source_repo_path": "/source/repo",
            "source_storage_dir": 12345,
            "linked_at": "2025-11-24T12:00:00",
        }
        with open(link_file, "w") as f:
            yaml.dump(link_data, f)

        monkeypatch.setenv("CICADA_CONFIG_DIR", str(linked_storage))

        result = ConfigManager.get_config_path()

        # Should fall back to linked storage config path
        assert result == str(linked_storage / "config.yaml")

    def test_uses_workspace_folder_paths_single_path(self, monkeypatch):
        """Test WORKSPACE_FOLDER_PATHS with a single path."""
        workspace_path = "/home/user/project"

        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", workspace_path)
        monkeypatch.delenv("CICADA_CONFIG_DIR", raising=False)

        with patch("cicada.mcp.config_manager.get_config_path") as mock_get:
            mock_get.return_value = Path("/home/.cicada/projects/hash/config.yaml")
            result = ConfigManager.get_config_path()

            # Verify get_config_path was called with the workspace path
            mock_get.assert_called_once_with(workspace_path)

    def test_uses_workspace_folder_paths_multiple_paths_unix(self, monkeypatch):
        """Test WORKSPACE_FOLDER_PATHS with multiple paths (Unix separator)."""
        workspace_paths = "/home/user/project1:/home/user/project2"

        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", workspace_paths)
        monkeypatch.delenv("CICADA_CONFIG_DIR", raising=False)

        with patch("cicada.mcp.config_manager.get_config_path") as mock_get:
            mock_get.return_value = Path("/home/.cicada/projects/hash/config.yaml")
            result = ConfigManager.get_config_path()

            # Should use the first path
            mock_get.assert_called_once_with("/home/user/project1")

    def test_uses_workspace_folder_paths_multiple_paths_windows(self, monkeypatch):
        """Test WORKSPACE_FOLDER_PATHS with multiple paths (Windows separator)."""
        # Mock os.pathsep to test Windows behavior on any platform
        monkeypatch.setattr("os.pathsep", ";")
        workspace_paths = r"C:\Users\user\project1;C:\Users\user\project2"

        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", workspace_paths)
        monkeypatch.delenv("CICADA_CONFIG_DIR", raising=False)

        with patch("cicada.mcp.config_manager.get_config_path") as mock_get:
            mock_get.return_value = Path(r"C:\Users\.cicada\projects\hash\config.yaml")

            with patch("cicada.mcp.config_manager.os.pathsep", ";"):
                result = ConfigManager.get_config_path()

                # Should use the first path
                mock_get.assert_called_once_with(r"C:\Users\user\project1")

    def test_falls_back_to_cwd_when_no_env_vars(self, monkeypatch):
        """Test fallback to current working directory."""
        monkeypatch.delenv("CICADA_CONFIG_DIR", raising=False)
        monkeypatch.delenv("WORKSPACE_FOLDER_PATHS", raising=False)

        with patch("cicada.mcp.config_manager.get_config_path") as mock_get:
            mock_get.return_value = Path("/current/dir/.cicada/config.yaml")

            with patch("pathlib.Path.cwd") as mock_cwd:
                # Mock both cwd and resolve to control the exact path
                mock_resolved = Path("/resolved/current/dir")
                mock_path_instance = mock_cwd.return_value
                mock_path_instance.resolve.return_value = mock_resolved

                result = ConfigManager.get_config_path()

                # Should call get_config_path with the resolved cwd
                mock_get.assert_called_once()
                call_arg = str(mock_get.call_args[0][0])
                assert call_arg == str(mock_resolved)

    def test_handles_pathsep_correctly_for_platform(self, monkeypatch):
        """Test that os.pathsep is used correctly for the current platform."""
        # Create paths with the correct separator for the current platform
        paths = ["/path/one", "/path/two"]
        workspace_paths = os.pathsep.join(paths)

        monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", workspace_paths)
        monkeypatch.delenv("CICADA_CONFIG_DIR", raising=False)

        with patch("cicada.mcp.config_manager.get_config_path") as mock_get:
            mock_get.return_value = Path("/home/.cicada/projects/hash/config.yaml")
            result = ConfigManager.get_config_path()

            # Should use the first path
            mock_get.assert_called_once_with(paths[0])


class TestLoadConfig:
    """Test ConfigManager.load_config() method."""

    def test_loads_valid_yaml_config(self, tmp_path):
        """Test loading a valid YAML configuration file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "repo_path": "/path/to/repo",
            "index_path": "/path/to/index.json",
            "extract_keywords": True,
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = ConfigManager.load_config(str(config_file))

        assert result == config_data
        assert result["repo_path"] == "/path/to/repo"
        assert result["extract_keywords"] is True

    def test_raises_file_not_found_for_missing_config(self, tmp_path):
        """Test that FileNotFoundError is raised for missing config."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager.load_config(str(config_file))

        error_msg = str(exc_info.value)
        assert "Config file not found" in error_msg
        assert "cicada cursor" in error_msg
        assert "cicada claude" in error_msg
        assert "cicada vs" in error_msg

    def test_raises_yaml_error_for_malformed_yaml(self, tmp_path):
        """Test that malformed YAML raises YAMLError."""
        config_file = tmp_path / "malformed.yaml"
        # Invalid YAML: unclosed bracket
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            ConfigManager.load_config(str(config_file))

    def test_returns_empty_dict_for_empty_file(self, tmp_path):
        """Test that empty YAML file returns empty dict."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = ConfigManager.load_config(str(config_file))

        assert result == {}

    def test_returns_empty_dict_for_null_yaml(self, tmp_path):
        """Test that null YAML content returns empty dict."""
        config_file = tmp_path / "null.yaml"
        config_file.write_text("null\n")

        result = ConfigManager.load_config(str(config_file))

        assert result == {}

    def test_returns_empty_dict_for_non_dict_yaml(self, tmp_path):
        """Test that non-dict YAML (list, string, etc.) returns empty dict."""
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2\n")

        result = ConfigManager.load_config(str(config_file))

        assert result == {}

    def test_loads_nested_config_structure(self, tmp_path):
        """Test loading a config with nested structures."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "repo_path": "/path/to/repo",
            "options": {
                "extract_keywords": True,
                "extract_cochange": False,
                "verbose": True,
            },
            "filters": ["*.ex", "*.exs"],
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = ConfigManager.load_config(str(config_file))

        assert result == config_data
        assert result["options"]["extract_keywords"] is True
        assert result["filters"] == ["*.ex", "*.exs"]

    def test_handles_unicode_in_config(self, tmp_path):
        """Test loading config with unicode characters."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "repo_path": "/path/to/repo",
            "description": "Testing with unicode: 你好, Ωμέγα, 🚀",
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)

        result = ConfigManager.load_config(str(config_file))

        assert result["description"] == "Testing with unicode: 你好, Ωμέγα, 🚀"

    def test_preserves_types_in_config(self, tmp_path):
        """Test that different YAML types are preserved correctly."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "string_value": "hello",
            "int_value": 42,
            "float_value": 3.14,
            "bool_true": True,
            "bool_false": False,
            "null_value": None,
            "list_value": [1, 2, 3],
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = ConfigManager.load_config(str(config_file))

        assert isinstance(result["string_value"], str)
        assert isinstance(result["int_value"], int)
        assert isinstance(result["float_value"], float)
        assert isinstance(result["bool_true"], bool)
        assert isinstance(result["bool_false"], bool)
        assert result["null_value"] is None
        assert isinstance(result["list_value"], list)
