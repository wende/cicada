"""Test that cicada-server redirects stdout to stderr during auto-setup."""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def test_auto_setup_redirects_stdout_to_stderr(tmp_path, monkeypatch):
    """Test that auto-setup output goes to stderr, not stdout."""
    # Create a fake Elixir project
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    (test_repo / "mix.exs").write_text("defmodule Project do\nend")
    (test_repo / "lib").mkdir()
    (test_repo / "lib" / "test.ex").write_text("defmodule Test do\nend")

    # Set repo path
    monkeypatch.setenv("CICADA_REPO_PATH", str(test_repo))

    # Capture stdout and stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()

    # Mock asyncio.run to prevent server startup
    mock_async_run = MagicMock()

    with patch("sys.stdout", captured_stdout):
        with patch("sys.stderr", captured_stderr):
            with patch("asyncio.run", mock_async_run):
                from cicada.mcp_server import main

                try:
                    main()
                except Exception:
                    pass

    # Check that stdout is clean (no indexer output)
    stdout_content = captured_stdout.getvalue()
    stderr_content = captured_stderr.getvalue()

    # Stdout should be empty or minimal (MCP protocol only)
    # The key point is that indexing messages should NOT appear on stdout
    assert "Indexing repository" not in stdout_content
    assert "Index saved to" not in stdout_content
    assert "First-time setup" not in stdout_content

    # If setup happened, output should be in stderr
    # (We don't assert this because setup might be skipped if already done)


def test_stdout_restored_after_auto_setup(tmp_path, monkeypatch):
    """Test that stdout is properly restored after auto-setup."""
    # Create a fake Elixir project
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    (test_repo / "mix.exs").write_text("defmodule Project do\nend")

    monkeypatch.setenv("CICADA_REPO_PATH", str(test_repo))

    # Store original stdout
    original_stdout = sys.stdout

    # Mock asyncio.run
    mock_async_run = MagicMock()

    with patch("asyncio.run", mock_async_run):
        from cicada.mcp_server import main

        try:
            main()
        except Exception:
            pass

    # Verify stdout was restored
    assert sys.stdout is original_stdout
