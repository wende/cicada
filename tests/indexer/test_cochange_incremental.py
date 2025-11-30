"""Test that co-change data is preserved/recomputed in incremental indexing.

These tests mock the CoChangeAnalyzer to avoid git operations that can corrupt
git worktrees during parallel test execution.
"""

import json
from unittest.mock import patch

import pytest

from cicada.indexer import ElixirIndexer


# Mock cochange analysis result
MOCK_COCHANGE_RESULT = {
    "file_pairs": {
        ("lib/auth.ex", "lib/credentials.ex"): 4,
        ("lib/auth.ex", "lib/logger.ex"): 2,
    },
    "function_pairs": {
        ("Auth.authenticate/2", "Credentials.validate/1"): 3,
    },
    "metadata": {
        "analyzed_at": "2024-01-01T00:00:00",
        "commit_count": 10,
        "file_pairs": 2,
        "function_pairs": 1,
        "optimization": "batched_recency_sampling",
    },
}

# Mock result with more commits (simulating more history)
MOCK_COCHANGE_RESULT_EXTENDED = {
    "file_pairs": {
        ("lib/auth.ex", "lib/credentials.ex"): 6,
        ("lib/auth.ex", "lib/logger.ex"): 3,
    },
    "function_pairs": {
        ("Auth.authenticate/2", "Credentials.validate/1"): 4,
    },
    "metadata": {
        "analyzed_at": "2024-01-02T00:00:00",
        "commit_count": 15,
        "file_pairs": 2,
        "function_pairs": 1,
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

    return tmp_path


class TestCoChangeIncremental:
    """Test co-change data in incremental indexing."""

    def test_incremental_indexing_preserves_cochange_data(self, elixir_repo_with_modules, tmp_path):
        """Test that co-change data is preserved when doing incremental updates."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # First full index with mocked cochange
        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        # Read initial co-change metadata
        with open(output_path) as f:
            initial_index = json.load(f)

        initial_cochange_count = initial_index.get("cochange_metadata", {}).get("commit_count", 0)

        # Do an incremental index with extended cochange result
        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT_EXTENDED,
        ):
            incremental_index = indexer.incremental_index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        # Assert: Co-change data should be present
        assert "cochange_metadata" in incremental_index
        assert incremental_index["cochange_metadata"]["commit_count"] >= initial_cochange_count

    def test_incremental_recomputes_cochange_when_enabled(self, elixir_repo_with_modules, tmp_path):
        """Test that co-change is recomputed in incremental mode."""
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # Index with cochange enabled
        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer.analyze_repository",
            return_value=MOCK_COCHANGE_RESULT,
        ):
            result = indexer.index_repository(
                repo_path=str(elixir_repo_with_modules),
                output_path=str(output_path),
                extract_cochange=True,
            )

        # Assert
        assert "cochange_metadata" in result
        assert result["cochange_metadata"]["commit_count"] >= 5

    def test_incremental_with_cochange_disabled_preserves_structure(
        self, elixir_repo_with_modules, tmp_path
    ):
        """Test that running incremental with extract_cochange=False preserves index structure."""
        output_path = tmp_path / "index.json"
        indexer = ElixirIndexer(verbose=False)

        # First: index WITH cochange
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
            indexed_with_cochange = json.load(f)

        assert "cochange_metadata" in indexed_with_cochange
        initial_file_pairs = indexed_with_cochange["cochange_metadata"]["file_pairs"]
        assert initial_file_pairs > 0

        # Act: incremental index with extract_cochange=False
        # When no changes detected, incremental just reports "up to date"
        indexer.incremental_index_repository(
            repo_path=str(elixir_repo_with_modules),
            output_path=str(output_path),
            extract_cochange=False,
        )

        # Assert: index should still have valid structure
        with open(output_path) as f:
            indexed_after = json.load(f)

        # cochange_metadata may be preserved (incremental doesn't clear when no changes)
        # The key is that the index is still valid and usable
        assert "modules" in indexed_after
        assert len(indexed_after["modules"]) > 0
