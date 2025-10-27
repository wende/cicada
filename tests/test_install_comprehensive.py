#!/usr/bin/env python
"""
Comprehensive unit tests for install.py module.

Tests all installation, configuration, and setup functionality.
"""

import sys
import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.install import (
    run_command,
    check_python,
    install_cicada,
    check_uv_available,
    install_dependencies_uv,
    install_dependencies_pip,
    install_dependencies,
    index_repository,
    detect_installation_method,
    create_mcp_config,
    create_config_yaml,
    create_gitattributes,
)


class TestRunCommand:
    """Test run_command utility function."""

    def test_run_command_success(self):
        """Test successful command execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="success",
                stderr="",
            )

            result = run_command("echo test")

            assert result.returncode == 0
            assert result.stdout == "success"
            mock_run.assert_called_once()

    def test_run_command_with_cwd(self):
        """Test command execution with custom working directory."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            run_command("ls", cwd="/tmp")

            call_args = mock_run.call_args
            assert call_args[1]["cwd"] == "/tmp"

    def test_run_command_failure(self):
        """Test handling of command failure."""
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(
                returncode=1, cmd="fail", stderr="error"
            )

            with pytest.raises(CalledProcessError):
                run_command("fail", check=True)

    def test_run_command_no_check(self):
        """Test command execution without error checking."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="error")

            result = run_command("fail", check=False)

            assert result.returncode == 1


class TestCheckPython:
    """Test Python version checking."""

    def test_check_python_valid_version(self):
        """Test with valid Python version (3.10+)."""
        version_info = Mock(major=3, minor=11)
        with patch("sys.version_info", version_info):
            # Should not raise, should print success message
            check_python()

    def test_check_python_invalid_version_major(self):
        """Test with invalid major version."""
        version_info = Mock(major=2, minor=7)
        with patch("sys.version_info", version_info):
            with pytest.raises(SystemExit):
                check_python()

    def test_check_python_invalid_version_minor(self):
        """Test with invalid minor version."""
        version_info = Mock(major=3, minor=9)
        with patch("sys.version_info", version_info):
            with pytest.raises(SystemExit):
                check_python()


class TestInstallCicada:
    """Test cicada installation logic."""

    def test_install_cicada_already_installed_package(self, tmp_path):
        """Test when cicada is already installed as a package."""
        # Mock the cicada.mcp_server module to simulate installed package
        mock_module = MagicMock()
        mock_module.__file__ = (
            "/usr/local/lib/python3.11/site-packages/cicada/mcp_server.py"
        )

        with patch.dict("sys.modules", {"cicada.mcp_server": mock_module}):
            path, already_installed = install_cicada(str(tmp_path))

            assert already_installed is True
            assert "site-packages" in str(path) or "cicada" in str(path)

    def test_install_cicada_in_current_directory(self, tmp_path):
        """Test when running from cicada directory."""
        # Create fake cicada directory structure
        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()
        (cicada_dir / "mcp_server.py").touch()

        with (
            patch("cicada.install.Path.cwd", return_value=tmp_path),
            patch(
                "importlib.import_module",
                side_effect=ImportError("Mock: module not found"),
            ),
        ):

            path, already_installed = install_cicada(str(tmp_path))

            assert path == tmp_path
            assert already_installed is False

    def test_install_cicada_target_directory_exists(self, tmp_path):
        """Test when target directory already has cicada."""
        target = tmp_path / "cicada_install"
        target.mkdir()
        cicada_dir = target / "cicada"
        cicada_dir.mkdir()
        (cicada_dir / "mcp_server.py").touch()

        import importlib

        original_import = importlib.import_module

        def selective_import(name):
            if name == "cicada.mcp_server":
                raise ImportError("Mock: module not found")
            # Use the original import_module
            return original_import(name)

        with (
            patch("importlib.import_module", side_effect=selective_import),
            patch("cicada.install.Path.cwd", return_value=Path("/other")),
        ):

            path, already_installed = install_cicada(str(target))

            assert path == target
            assert already_installed is False

    def test_install_cicada_clone_from_github(self, tmp_path):
        """Test cloning from GitHub."""
        target = tmp_path / "new_install"
        github_url = "https://github.com/wende/cicada.git"

        import importlib

        original_import = importlib.import_module

        def selective_import(name):
            if name == "cicada.mcp_server":
                raise ImportError("Mock: module not found")
            return original_import(name)

        with (
            patch("importlib.import_module", side_effect=selective_import),
            patch("cicada.install.Path.cwd", return_value=Path("/other")),
            patch("cicada.install.run_command") as mock_run,
        ):

            _path, _already_installed = install_cicada(str(target), github_url)

            # Should have called git clone
            mock_run.assert_called_once()
            assert "git clone" in mock_run.call_args[0][0]
            assert github_url in mock_run.call_args[0][0]
            assert str(target) in mock_run.call_args[0][0]

    def test_install_cicada_no_url_raises_error(self, tmp_path):
        """Test error when cicada not found and no URL provided."""
        target = tmp_path / "new_install"

        import importlib

        original_import = importlib.import_module

        def selective_import(name):
            if name == "cicada.mcp_server":
                raise ImportError("Mock: module not found")
            return original_import(name)

        with (
            patch("importlib.import_module", side_effect=selective_import),
            patch("cicada.install.Path.cwd", return_value=Path("/other")),
        ):

            with pytest.raises(SystemExit):
                install_cicada(str(target), github_url=None)


class TestCheckUvAvailable:
    """Test uv availability detection."""

    def test_check_uv_available_true(self):
        """Test when uv is available."""
        with patch("cicada.install.run_command") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = check_uv_available()

            assert result is True

    def test_check_uv_available_false(self):
        """Test when uv is not available."""
        with patch("cicada.install.run_command") as mock_run:
            mock_run.return_value = Mock(returncode=1)

            result = check_uv_available()

            assert result is False

    def test_check_uv_available_exception(self):
        """Test when uv check raises exception."""
        with patch("cicada.install.run_command", side_effect=Exception("error")):
            result = check_uv_available()

            assert result is False


class TestInstallDependencies:
    """Test dependency installation."""

    def test_install_dependencies_uv(self, tmp_path):
        """Test installing dependencies with uv."""
        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()

        venv_path = cicada_dir / ".venv"
        venv_path.mkdir()
        bin_dir = venv_path / "bin"
        bin_dir.mkdir()
        python_bin = bin_dir / "python"
        python_bin.touch()

        with patch("cicada.install.run_command") as mock_run:
            result = install_dependencies_uv(cicada_dir)

            assert result == python_bin
            mock_run.assert_called_once()
            assert "uv sync" in mock_run.call_args[0][0]

    def test_install_dependencies_pip_new_venv(self, tmp_path):
        """Test installing dependencies with pip (new venv)."""
        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()
        (cicada_dir / "requirements.txt").write_text("pyyaml")

        with patch("cicada.install.run_command") as mock_run:
            _python_bin = install_dependencies_pip(cicada_dir)

            # Should create venv, install requirements, install package
            assert mock_run.call_count >= 2
            assert any("venv" in str(call) for call in mock_run.call_args_list)

    def test_install_dependencies_auto_detect_uv(self, tmp_path):
        """Test auto-detection of uv."""
        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()

        with (
            patch("cicada.install.check_uv_available", return_value=True),
            patch("cicada.install.install_dependencies_uv") as mock_uv,
        ):

            mock_uv.return_value = Path("/python")

            _result = install_dependencies(cicada_dir, use_uv=None)

            mock_uv.assert_called_once()

    def test_install_dependencies_force_pip(self, tmp_path):
        """Test forcing pip even when uv is available."""
        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()

        with (
            patch("cicada.install.check_uv_available", return_value=True),
            patch("cicada.install.install_dependencies_pip") as mock_pip,
        ):

            mock_pip.return_value = Path("/python")

            _result = install_dependencies(cicada_dir, use_uv=False)

            mock_pip.assert_called_once()


class TestIndexRepository:
    """Test repository indexing."""

    def test_index_repository_basic(self, tmp_path):
        """Test basic repository indexing."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()
        indexer_script = cicada_dir / "cicada" / "indexer.py"
        indexer_script.parent.mkdir()
        indexer_script.touch()

        python_bin = "/usr/bin/python"

        with patch("cicada.install.run_command") as mock_run:
            output = index_repository(cicada_dir, python_bin, repo_path)

            assert output == repo_path / ".cicada" / "index.json"
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert str(python_bin) in cmd
            assert str(indexer_script) in cmd
            assert str(repo_path) in cmd

    def test_index_repository_with_pr_info(self, tmp_path):
        """Test repository indexing with PR info."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()
        indexer_script = cicada_dir / "cicada" / "indexer.py"
        indexer_script.parent.mkdir()
        indexer_script.touch()

        with patch("cicada.install.run_command") as mock_run:
            index_repository(cicada_dir, "/python", repo_path, fetch_pr_info=True)

            cmd = mock_run.call_args[0][0]
            assert "--pr-info" in cmd


class TestDetectInstallationMethod:
    """Test installation method detection."""

    def test_detect_uvx_temporary_path(self):
        """Test detection of uvx temporary paths."""
        uvx_paths = [
            "/Users/user/.cache/uv/builds/cicada",
            "/tmp/uvx-cicada/bin/script",
        ]

        for uvx_path in uvx_paths:
            with (
                patch("sys.argv", [uvx_path]),
                patch("sys.executable", "/usr/bin/python"),
            ):

                command, args, _cwd, description = detect_installation_method()

                assert command != "cicada-server"
                assert "mcp_server.py" in str(args[0])
                assert "uvx" in description.lower()

    def test_detect_uv_tools_permanent(self):
        """Test detection of uv tool install."""
        with patch(
            "sys.argv", ["/Users/user/.local/share/uv/tools/cicada/bin/cicada-setup"]
        ):
            command, args, cwd, _description = detect_installation_method()

            assert command == "cicada-server"
            assert args == []
            assert cwd is None

    def test_detect_cicada_server_in_path(self):
        """Test when cicada-server is in PATH."""
        with (
            patch("sys.argv", ["/some/path/script.py"]),
            patch("shutil.which", return_value="/usr/local/bin/cicada-server"),
        ):

            command, args, cwd, description = detect_installation_method()

            assert command == "cicada-server"

    def test_detect_direct_python_fallback(self):
        """Test fallback to direct Python execution."""
        with (
            patch("sys.argv", ["/home/user/cicada/install.py"]),
            patch("shutil.which", return_value=None),
            patch("sys.executable", "/usr/bin/python3"),
        ):

            command, args, cwd, description = detect_installation_method()

            assert command == "/usr/bin/python3"
            assert len(args) > 0
            assert "mcp_server.py" in str(args[0])


class TestCreateMCPConfig:
    """Test MCP configuration creation."""

    def test_create_mcp_config_new_file(self, tmp_path):
        """Test creating new .mcp.json file."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        cicada_dir = tmp_path / "cicada"
        python_bin = "/usr/bin/python"

        with patch("cicada.install.detect_installation_method") as mock_detect:
            mock_detect.return_value = ("cicada-server", [], None, "uv tool install")

            config_path = create_mcp_config(repo_path, cicada_dir, python_bin)

            assert config_path == repo_path / ".mcp.json"
            assert config_path.exists()

            # Verify content
            config = json.loads(config_path.read_text())
            assert "mcpServers" in config
            assert "cicada" in config["mcpServers"]
            assert config["mcpServers"]["cicada"]["command"] == "cicada-server"

    def test_create_mcp_config_merge_existing(self, tmp_path):
        """Test merging with existing .mcp.json."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Create existing config
        existing_config = {"mcpServers": {"other_server": {"command": "other"}}}
        mcp_path = repo_path / ".mcp.json"
        mcp_path.write_text(json.dumps(existing_config))

        with patch("cicada.install.detect_installation_method") as mock_detect:
            mock_detect.return_value = ("cicada-server", [], None, "test")

            create_mcp_config(repo_path, tmp_path / "cicada", "/python")

            # Verify merge
            config = json.loads(mcp_path.read_text())
            assert "other_server" in config["mcpServers"]
            assert "cicada" in config["mcpServers"]

    def test_create_mcp_config_python_mode(self, tmp_path):
        """Test config creation for Python mode."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("cicada.install.detect_installation_method") as mock_detect:
            mock_detect.return_value = (
                "/usr/bin/python",
                ["/path/to/mcp_server.py"],
                "/path/to/cicada",
                "direct python",
            )

            config_path = create_mcp_config(repo_path, tmp_path / "cicada", "/python")

            config = json.loads(config_path.read_text())
            server_config = config["mcpServers"]["cicada"]

            assert server_config["command"] == "/usr/bin/python"
            assert server_config["args"] == ["/path/to/mcp_server.py"]
            assert server_config["cwd"] == "/path/to/cicada"

    def test_create_mcp_config_env_variable(self, tmp_path):
        """Test that CICADA_REPO_PATH env variable is set."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("cicada.install.detect_installation_method") as mock_detect:
            mock_detect.return_value = ("cmd", [], None, "test")

            config_path = create_mcp_config(repo_path, tmp_path, "/python")

            config = json.loads(config_path.read_text())
            assert "env" in config["mcpServers"]["cicada"]
            assert "CICADA_REPO_PATH" in config["mcpServers"]["cicada"]["env"]
            assert config["mcpServers"]["cicada"]["env"]["CICADA_REPO_PATH"] == str(
                repo_path
            )


class TestCreateConfigYAML:
    """Test config.yaml creation."""

    def test_create_config_yaml(self, tmp_path):
        """Test creating config.yaml file."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        index_path = repo_path / ".cicada" / "index.json"

        create_config_yaml(tmp_path / "cicada", repo_path, index_path)

        config_path = repo_path / ".cicada" / "config.yaml"
        assert config_path.exists()

        config = yaml.safe_load(config_path.read_text())
        assert config["repository"]["path"] == str(repo_path)
        assert config["storage"]["index_path"] == str(index_path)


class TestCreateGitattributes:
    """Test .gitattributes creation."""

    def test_create_gitattributes_new_file(self, tmp_path):
        """Test creating new .gitattributes file."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        gitattributes_path = create_gitattributes(repo_path)

        assert gitattributes_path.exists()
        content = gitattributes_path.read_text()
        assert "*.ex diff=elixir" in content
        assert "*.exs diff=elixir" in content

    def test_create_gitattributes_existing_without_patterns(self, tmp_path):
        """Test adding patterns to existing .gitattributes."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Create existing file without Elixir patterns
        gitattributes = repo_path / ".gitattributes"
        gitattributes.write_text("*.md linguist-documentation\n")

        create_gitattributes(repo_path)

        content = gitattributes.read_text()
        assert "*.md linguist-documentation" in content
        assert "*.ex diff=elixir" in content
        assert "*.exs diff=elixir" in content

    def test_create_gitattributes_already_has_patterns(self, tmp_path):
        """Test when .gitattributes already has Elixir patterns."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Create file with Elixir patterns
        gitattributes = repo_path / ".gitattributes"
        gitattributes.write_text("*.ex diff=elixir\n*.exs diff=elixir\n")

        original_content = gitattributes.read_text()

        create_gitattributes(repo_path)

        # Should not add duplicates
        new_content = gitattributes.read_text()
        assert new_content == original_content


class TestMainFunction:
    """Test main CLI entry point."""

    def test_main_with_minimal_args(self, tmp_path):
        """Test main function with minimal arguments."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        cicada_dir = tmp_path / "cicada"
        cicada_dir.mkdir()
        (cicada_dir / "cicada").mkdir()
        (cicada_dir / "cicada" / "mcp_server.py").touch()

        with (
            patch("sys.argv", ["install.py", str(repo_path)]),
            patch("cicada.install.check_python"),
            patch("cicada.install.install_cicada", return_value=(cicada_dir, False)),
            patch("cicada.install.install_dependencies", return_value=Path("/python")),
            patch("cicada.install.index_repository", return_value=Path("index.json")),
            patch("cicada.install.create_config_yaml"),
            patch("cicada.install.create_gitattributes"),
            patch("cicada.install.create_mcp_config", return_value=Path("mcp.json")),
        ):

            from cicada.install import main

            main()

            # Should complete without errors

    def test_main_with_skip_install(self, tmp_path):
        """Test main with --skip-install flag."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        with (
            patch("sys.argv", ["install.py", str(repo_path), "--skip-install"]),
            patch("cicada.install.check_python"),
            patch("cicada.install.install_cicada") as mock_install,
            patch("cicada.install.index_repository", return_value=Path("index.json")),
            patch("cicada.install.create_config_yaml"),
            patch("cicada.install.create_gitattributes"),
            patch("cicada.install.create_mcp_config", return_value=Path("mcp.json")),
            patch("sys.executable", "/usr/bin/python"),
        ):

            mock_install.return_value = (tmp_path / "cicada", False)

            from cicada.install import main

            main()

            # install_dependencies should not be called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
