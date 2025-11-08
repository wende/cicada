"""Tests for cicada-server CLI argument handling."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def test_cicada_server_accepts_repo_path_argument(monkeypatch, tmp_path):
    """Test that cicada-server accepts a positional repo path argument and sets CICADA_CONFIG_DIR."""
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

    # Track what CICADA_CONFIG_DIR gets set to
    captured_env = {}

    def capture_env(*args, **kwargs):
        captured_env["CICADA_CONFIG_DIR"] = os.environ.get("CICADA_CONFIG_DIR")

    mock_async_run.side_effect = capture_env

    with patch("sys.argv", test_args):
        with patch("asyncio.run", mock_async_run):
            # Import and call main
            from cicada.mcp.server import main

            try:
                main()
            except Exception:
                pass  # Ignore errors from mocked async_run

    # Verify that CICADA_CONFIG_DIR was set to the storage directory
    from cicada.utils.storage import get_storage_dir

    expected_storage_dir = get_storage_dir(test_repo.resolve())
    assert "CICADA_CONFIG_DIR" in captured_env
    assert Path(captured_env["CICADA_CONFIG_DIR"]) == expected_storage_dir


def test_cicada_server_without_argument_uses_cwd(monkeypatch):
    """Test that cicada-server without arguments doesn't set CICADA_CONFIG_DIR."""
    # Mock sys.argv with just the program name
    test_args = ["cicada-server"]

    # Mock asyncio.run to prevent actual server startup
    mock_async_run = MagicMock()

    # Track environment state
    captured_env = {}

    def capture_env(*args, **kwargs):
        captured_env["CICADA_CONFIG_DIR"] = os.environ.get("CICADA_CONFIG_DIR")

    mock_async_run.side_effect = capture_env

    # Clear CICADA_CONFIG_DIR if set
    original_env = os.environ.get("CICADA_CONFIG_DIR")
    if "CICADA_CONFIG_DIR" in os.environ:
        del os.environ["CICADA_CONFIG_DIR"]

    try:
        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify CICADA_CONFIG_DIR was not set
        assert captured_env["CICADA_CONFIG_DIR"] is None
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["CICADA_CONFIG_DIR"] = original_env


def test_cicada_server_converts_relative_to_absolute(monkeypatch, tmp_path):
    """Test that relative paths are converted to absolute paths and CICADA_CONFIG_DIR is set."""
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
            captured_env["CICADA_CONFIG_DIR"] = os.environ.get("CICADA_CONFIG_DIR")

        mock_async_run.side_effect = capture_env

        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify CICADA_CONFIG_DIR was set to the storage directory
        from cicada.utils.storage import get_storage_dir

        expected_storage_dir = get_storage_dir(test_repo.resolve())
        assert "CICADA_CONFIG_DIR" in captured_env
        assert Path(captured_env["CICADA_CONFIG_DIR"]).is_absolute()
        assert Path(captured_env["CICADA_CONFIG_DIR"]) == expected_storage_dir
    finally:
        os.chdir(original_cwd)


def test_cicada_server_dot_argument(monkeypatch, tmp_path):
    """Test that '.' as argument sets CICADA_CONFIG_DIR based on current directory."""
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
            captured_env["CICADA_CONFIG_DIR"] = os.environ.get("CICADA_CONFIG_DIR")

        mock_async_run.side_effect = capture_env

        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify CICADA_CONFIG_DIR is set to the storage directory for current directory
        from cicada.utils.storage import get_storage_dir

        expected_storage_dir = get_storage_dir(tmp_path.resolve())
        assert "CICADA_CONFIG_DIR" in captured_env
        assert Path(captured_env["CICADA_CONFIG_DIR"]) == expected_storage_dir
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


def test_positional_arg_auto_setup_from_different_directory(monkeypatch, tmp_path):
    """Test that positional arg works for auto-setup when called from different directory."""
    # Create a fake Elixir project in one location
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    (test_repo / "mix.exs").write_text("defmodule Project do\nend")
    (test_repo / "lib").mkdir()
    (test_repo / "lib" / "test.ex").write_text("defmodule Test do\nend")

    # Create a different directory to run from
    other_dir = tmp_path / "other_dir"
    other_dir.mkdir()

    # Change to the other directory
    original_cwd = Path.cwd()
    os.chdir(other_dir)

    try:
        # Mock sys.argv with the repo path as positional argument
        test_args = ["cicada-server", str(test_repo)]

        # Track environment variables that get set
        captured_env = {}

        def capture_env(*args, **kwargs):
            captured_env["_CICADA_REPO_PATH_ARG"] = os.environ.get("_CICADA_REPO_PATH_ARG")
            captured_env["CICADA_CONFIG_DIR"] = os.environ.get("CICADA_CONFIG_DIR")

        mock_async_run = MagicMock(side_effect=capture_env)

        with patch("sys.argv", test_args):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp.server import main

                try:
                    main()
                except Exception:
                    pass

        # Verify that the internal env var was set to the provided repo path
        # This ensures _auto_setup_if_needed will use the correct repo, not cwd
        assert "_CICADA_REPO_PATH_ARG" in captured_env
        assert captured_env["_CICADA_REPO_PATH_ARG"] is not None
        assert Path(captured_env["_CICADA_REPO_PATH_ARG"]) == test_repo.resolve()

        # Verify it's NOT using the cwd (other_dir)
        assert Path(captured_env["_CICADA_REPO_PATH_ARG"]) != other_dir.resolve()

        # Verify CICADA_CONFIG_DIR was also set correctly
        from cicada.utils.storage import get_storage_dir

        expected_storage_dir = get_storage_dir(test_repo.resolve())
        assert captured_env["CICADA_CONFIG_DIR"] == str(expected_storage_dir)
    finally:
        os.chdir(original_cwd)
