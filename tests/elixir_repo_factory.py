"""
Helpers to build sample Elixir repositories for watcher-related tests.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import Mock


LIB_MODULE_1 = """
defmodule Module1 do
  def hello, do: "world"
end
""".strip()

LIB_MODULE_2 = """
defmodule Module2 do
  def foo, do: :bar
end
""".strip()

TEST_MODULE = """
defmodule Module1Test do
  use ExUnit.Case
end
""".strip()

MIX_EXS = """
defmodule TestProject.MixProject do
  use Mix.Project
end
""".strip()


def create_sample_elixir_repo(base_dir: Path | str, name: str = "elixir_repo") -> Path:
    """Create a reusable Elixir repo layout for watcher/watch manager tests."""
    base_path = Path(base_dir)
    repo_path = base_path / name

    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo_path.mkdir(parents=True)

    lib_dir = repo_path / "lib"
    test_dir = repo_path / "test"
    lib_dir.mkdir()
    test_dir.mkdir()

    (lib_dir / "module1.ex").write_text(LIB_MODULE_1)
    (lib_dir / "module2.ex").write_text(LIB_MODULE_2)
    (test_dir / "module1_test.exs").write_text(TEST_MODULE)

    (repo_path / "mix.exs").write_text(MIX_EXS)

    # Common excluded directories needed by watcher filtering logic
    for excluded in ("deps", "_build", ".git"):
        (repo_path / excluded).mkdir()

    return repo_path


def make_mock_watch_process(pid: int = 12345, running: bool = True) -> Mock:
    """Create a subprocess.Popen-style mock with standard attributes."""
    mock_process = Mock()
    mock_process.pid = pid
    mock_process.poll.return_value = None if running else 0
    mock_process.returncode = None if running else 0
    return mock_process
