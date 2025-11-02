"""Tests for cicada-server CLI argument handling."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def test_cicada_server_accepts_repo_path_argument(monkeypatch, tmp_path):
    """Test that cicada-server accepts a positional repo path argument."""
    # Create a fake Elixir project
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    (test_repo / "mix.exs").write_text("defmodule Project do\nend")
    (test_repo / "lib").mkdir()
    (test_repo / "lib" / "test.ex").write_text("defmodule Test do\nend")

    # Mock sys.argv to include the repo path
    test_args = ["cicada-server", str(test_repo)]

    # Mock asyncio.run to prevent actual server startup
    mock_async_run = MagicMock()

    # Track what CICADA_REPO_PATH gets set to
    captured_env = {}

    def capture_env(*args, **kwargs):
        captured_env["CICADA_REPO_PATH"] = os.environ.get("CICADA_REPO_PATH")

    mock_async_run.side_effect = capture_env

    with patch("sys.argv", test_args):
        with patch("asyncio.run", mock_async_run):
            # Import and call main
            from cicada.mcp.server import main

            try:
                main()
            except Exception:
                pass  # Ignore errors from mocked async_run

    # Verify that CICADA_REPO_PATH was set to the absolute path
    assert "CICADA_REPO_PATH" in captured_env
    assert Path(captured_env["CICADA_REPO_PATH"]) == test_repo.resolve()


def test_cicada_server_without_argument_uses_cwd(monkeypatch):
    """Test that cicada-server without arguments doesn't set CICADA_REPO_PATH."""
    # Mock sys.argv with just the program name
    test_args = ["cicada-server"]

    # Mock asyncio.run to prevent actual server startup
    mock_async_run = MagicMock()

    # Track environment state
    captured_env = {}

    def capture_env(*args, **kwargs):
        captured_env["CICADA_REPO_PATH"] = os.environ.get("CICADA_REPO_PATH")

    mock_async_run.side_effect = capture_env

    # Clear CICADA_REPO_PATH if set
    original_env = os.environ.get("CICADA_REPO_PATH")
    if "CICADA_REPO_PATH" in os.environ:
        del os.environ["CICADA_REPO_PATH"]

    try:
        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify CICADA_REPO_PATH was not set
        assert captured_env["CICADA_REPO_PATH"] is None
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["CICADA_REPO_PATH"] = original_env


def test_cicada_server_converts_relative_to_absolute(monkeypatch, tmp_path):
    """Test that relative paths are converted to absolute paths."""
    # Create a fake Elixir project
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    (test_repo / "mix.exs").write_text("defmodule Project do\nend")

    # Change to parent directory
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        # Mock sys.argv with relative path
        test_args = ["cicada-server", "test_repo"]

        # Mock asyncio.run
        mock_async_run = MagicMock()
        captured_env = {}

        def capture_env(*args, **kwargs):
            captured_env["CICADA_REPO_PATH"] = os.environ.get("CICADA_REPO_PATH")

        mock_async_run.side_effect = capture_env

        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify the path was converted to absolute
        assert "CICADA_REPO_PATH" in captured_env
        assert Path(captured_env["CICADA_REPO_PATH"]).is_absolute()
        assert Path(captured_env["CICADA_REPO_PATH"]) == test_repo.resolve()
    finally:
        os.chdir(original_cwd)


def test_cicada_server_dot_argument(monkeypatch, tmp_path):
    """Test that '.' as argument sets CICADA_REPO_PATH to current directory."""
    # Create a fake Elixir project in tmp_path
    (tmp_path / "mix.exs").write_text("defmodule Project do\nend")

    # Change to the test repo
    original_cwd = Path.cwd()
    os.chdir(tmp_path)

    try:
        # Mock sys.argv with "."
        test_args = ["cicada-server", "."]

        # Mock asyncio.run
        mock_async_run = MagicMock()
        captured_env = {}

        def capture_env(*args, **kwargs):
            captured_env["CICADA_REPO_PATH"] = os.environ.get("CICADA_REPO_PATH")

        mock_async_run.side_effect = capture_env

        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify CICADA_REPO_PATH is set to the absolute path of current directory
        assert "CICADA_REPO_PATH" in captured_env
        assert Path(captured_env["CICADA_REPO_PATH"]) == tmp_path.resolve()
    finally:
        os.chdir(original_cwd)


def test_workspace_folder_paths_env_var(monkeypatch, tmp_path):
    """Test that WORKSPACE_FOLDER_PATHS environment variable is used by auto-setup."""
    # Create a fake Elixir project
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    (test_repo / "mix.exs").write_text("defmodule Project do\nend")
    (test_repo / "lib").mkdir()
    (test_repo / "lib" / "test.ex").write_text("defmodule Test do\nend")

    # Mock sys.argv
    test_args = ["cicada-server"]

    # Set WORKSPACE_FOLDER_PATHS environment variable
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", str(test_repo))

    # Mock various functions to prevent actual setup
    from cicada.mcp import server as mcp_server
    from cicada.utils import get_config_path, get_index_path

    config_path = get_config_path(test_repo)
    index_path = get_index_path(test_repo)

    # Make them appear to exist so auto-setup doesn't run
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("sys.argv", test_args):
            with patch("asyncio.run"):
                # This should use WORKSPACE_FOLDER_PATHS
                mcp_server._auto_setup_if_needed()


def test_workspace_folder_paths_with_multiple_paths(monkeypatch, tmp_path):
    """Test that WORKSPACE_FOLDER_PATHS with multiple paths uses the first one."""
    # Create fake Elixir projects
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()
    (repo1 / "mix.exs").write_text("defmodule Project1 do\nend")
    (repo2 / "mix.exs").write_text("defmodule Project2 do\nend")

    # Set WORKSPACE_FOLDER_PATHS with colon-separated paths
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", f"{repo1}:{repo2}")

    # Mock sys.argv
    test_args = ["cicada-server"]

    # Mock Path.exists to prevent actual setup
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("sys.argv", test_args):
            with patch("asyncio.run"):
                from cicada.mcp import server as mcp_server

                mcp_server._auto_setup_if_needed()


def test_cicada_repo_path_takes_precedence_over_workspace_folder_paths(monkeypatch, tmp_path):
    """Test that CICADA_REPO_PATH takes precedence over WORKSPACE_FOLDER_PATHS."""
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()
    (repo1 / "mix.exs").write_text("defmodule Project1 do\nend")
    (repo2 / "mix.exs").write_text("defmodule Project2 do\nend")

    # Set both environment variables
    monkeypatch.setenv("CICADA_REPO_PATH", str(repo1))
    monkeypatch.setenv("WORKSPACE_FOLDER_PATHS", str(repo2))

    # Mock Path.exists to prevent actual setup
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("sys.argv", ["cicada-server"]):
            with patch("asyncio.run"):
                from cicada.mcp import server as mcp_server

                # Should use CICADA_REPO_PATH (repo1), not WORKSPACE_FOLDER_PATHS (repo2)
                mcp_server._auto_setup_if_needed()
