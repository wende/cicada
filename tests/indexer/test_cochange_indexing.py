"""Tests for co-change data in index schema.

These tests mock the CoChangeAnalyzer to avoid git operations that can corrupt
git worktrees during parallel test execution.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from cicada.indexer import ElixirIndexer


# Mock cochange analysis result
MOCK_COCHANGE_RESULT = {
    "file_pairs": {
        ("lib/auth.ex", "lib/credentials.ex"): 4,
        ("lib/auth.ex", "lib/logger.ex"): 2,
        ("lib/module_a.ex", "lib/module_b.ex"): 3,
    },
    "function_pairs": {
        ("ModuleA.func_one/1", "ModuleB.func_three/1"): 2,
        ("Auth.authenticate/2", "Credentials.validate/1"): 3,
    },
    "metadata": {
        "analyzed_at": "2024-01-01T00:00:00",
        "commit_count": 10,
        "file_pairs": 3,
        "function_pairs": 2,
        "optimization": "batched_recency_sampling",
    },
}


@pytest.fixture
def elixir_repo_with_modules(tmp_path):
    """Create an Elixir repo with modules for indexing (no git required)."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()

    # Create mix.exs
    (tmp_path / "mix.exs").write_text(
        """
defmodule TestApp.MixProject do
  use Mix.Project

  def project do
    [app: :test_app, version: "0.1.0"]
  end
end
"""
    )

    # Create Auth module
    (lib_dir / "auth.ex").write_text(
        """
defmodule Auth do
  @moduledoc "Authentication module"

  def authenticate(user, password) do
    Credentials.validate(user, password)
  end

  def logout(user) do
    :ok
  end
end
"""
    )

    # Create Credentials module
    (lib_dir / "credentials.ex").write_text(
        """
defmodule Credentials do
  @moduledoc "Credentials validation"

  def validate(user, password) do
    {:ok, user}
  end
end
"""
    )

    # Create Logger module
    (lib_dir / "logger.ex").write_text(
        """
defmodule Logger do
  @moduledoc "Logging utilities"

  def log(message) do
    IO.puts(message)
  end
end
"""
    )

    # Create ModuleA
    (lib_dir / "module_a.ex").write_text(
        """
defmodule ModuleA do
  def func_one(arg), do: arg
  def func_two(arg), do: arg * 2
end
"""
    )

    # Create ModuleB
    (lib_dir / "module_b.ex").write_text(
        """
defmodule ModuleB do
  def func_three(arg), do: arg + 1
end
"""
    )

    return tmp_path


class TestCoChangeIndexing:
    """Test suite for co-change data in index."""

    def test_index_includes_cochange_metadata_at_root(self, elixir_repo_with_modules, tmp_path):
        """Test that index includes cochange_metadata at root level."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        with open(output_path) as f:
            index = json.load(f)

        assert "cochange_metadata" in index
        metadata = index["cochange_metadata"]
        assert "analyzed_at" in metadata
        assert "commit_count" in metadata
        assert "file_pairs" in metadata
        assert "function_pairs" in metadata
        assert metadata["commit_count"] >= 5

    def test_modules_have_cochange_files_array(self, elixir_repo_with_modules, tmp_path):
        """Test that modules have cochange_files array."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        with open(output_path) as f:
            index = json.load(f)

        # Auth module should exist and have cochange_files
        if "Auth" in index["modules"]:
            module_auth = index["modules"]["Auth"]
            assert "cochange_files" in module_auth

        if "Credentials" in index["modules"]:
            module_creds = index["modules"]["Credentials"]
            assert "cochange_files" in module_creds

    def test_functions_have_cochange_functions_array(self, elixir_repo_with_modules, tmp_path):
        """Test that functions have cochange_functions array."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        with open(output_path) as f:
            index = json.load(f)

        # ModuleA should exist with functions that have cochange_functions
        if "ModuleA" in index["modules"]:
            module_a = index["modules"]["ModuleA"]
            for func in module_a.get("functions", []):
                assert "cochange_functions" in func

    def test_cochange_counts_are_accurate(self, elixir_repo_with_modules, tmp_path):
        """Test that co-change counts are accurate with mocked data."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        with open(output_path) as f:
            index = json.load(f)

        # Auth module should have co-change data
        module_auth = index["modules"]["Auth"]
        assert "cochange_files" in module_auth
        assert len(module_auth["cochange_files"]) > 0

        # Auth should co-change with credentials.ex
        cochange_creds = next(
            (cf for cf in module_auth["cochange_files"] if "credentials.ex" in cf["file"]), None
        )
        assert cochange_creds is not None
        assert cochange_creds["count"] >= 2

    def test_index_without_cochange_has_no_cochange_fields(
        self, elixir_repo_with_modules, tmp_path
    ):
        """Test that index without extract_cochange doesn't have co-change fields."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # Don't need to mock - cochange analyzer shouldn't be called
        indexer.index_repository(
            repo_path=str(elixir_repo_with_modules),
            output_path=str(output_path),
            extract_cochange=False,
        )

        with open(output_path) as f:
            index = json.load(f)

        assert "cochange_metadata" not in index

        for module in index["modules"].values():
            if isinstance(module, dict):
                assert "cochange_files" not in module

    def test_cochange_handles_repo_gracefully(self, elixir_repo_with_modules, tmp_path):
        """Test that co-change analysis handles various repo states gracefully."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        with open(output_path) as f:
            index = json.load(f)

        assert "cochange_metadata" in index
        assert index["cochange_metadata"]["commit_count"] > 0
        assert index["cochange_metadata"]["file_pairs"] >= 0

        for module in index["modules"].values():
            if isinstance(module, dict):
                assert "cochange_files" in module
                assert isinstance(module["cochange_files"], list)
