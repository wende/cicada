"""End-to-end integration tests for co-change feature."""

import json
import subprocess
from pathlib import Path

import pytest


class TestCoChangeE2E:
    """End-to-end tests for the complete co-change workflow."""

    @pytest.fixture
    def git_repo_with_cochanges(self, tmp_path):
        """Create a git repository with known co-change patterns."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        lib_dir = repo_path / "lib"
        lib_dir.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create module files with meaningful content
        (lib_dir / "auth.ex").write_text(
            """defmodule MyApp.Auth do
  @moduledoc \"\"\"
  Authentication module for user login and validation.
  \"\"\"

  def validate_user(username, password) do
    # Validate user credentials
    :ok
  end

  def login(username, password) do
    # Login user
    {:ok, "token"}
  end
end
"""
        )

        (lib_dir / "credentials.ex").write_text(
            """defmodule MyApp.Credentials do
  @moduledoc \"\"\"
  Credentials checking and password verification.
  \"\"\"

  def check_password(password, hash) do
    # Check password against hash
    true
  end

  def verify_credentials(username, password) do
    # Verify user credentials
    :ok
  end
end
"""
        )

        (lib_dir / "logger.ex").write_text(
            """defmodule MyApp.Logger do
  @moduledoc \"\"\"
  Logging and audit trail for authentication events.
  \"\"\"

  def log_login_attempt(username, success) do
    # Log login attempt
    :ok
  end

  def audit_access(user_id, action) do
    # Audit user access
    :ok
  end
end
"""
        )

        # Commit 1: Auth and Credentials together
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add auth and credentials"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 2: Update Auth and Credentials together
        (lib_dir / "auth.ex").write_text((lib_dir / "auth.ex").read_text() + "\n  # Updated auth\n")
        (lib_dir / "credentials.ex").write_text(
            (lib_dir / "credentials.ex").read_text() + "\n  # Updated credentials\n"
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update auth and credentials"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 3: Update Auth and Credentials again
        (lib_dir / "auth.ex").write_text(
            (lib_dir / "auth.ex").read_text() + "\n  # Second update\n"
        )
        (lib_dir / "credentials.ex").write_text(
            (lib_dir / "credentials.ex").read_text() + "\n  # Second update\n"
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Another auth and credentials update"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit 4: Update Auth and Logger together (less frequent)
        (lib_dir / "auth.ex").write_text(
            (lib_dir / "auth.ex").read_text() + "\n  # Auth with logger\n"
        )
        (lib_dir / "logger.ex").write_text(
            (lib_dir / "logger.ex").read_text() + "\n  # Logger update\n"
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update auth and logger"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    def test_full_cochange_workflow(self, git_repo_with_cochanges, tmp_path):
        """Test complete workflow: index with co-change -> search -> verify boosting."""
        from cicada.indexer import ElixirIndexer
        from cicada.keyword_search import KeywordSearcher
        from cicada.elixir.format import ModuleFormatter

        # Step 1: Index with co-change extraction
        repo_path = git_repo_with_cochanges
        index_path = tmp_path / "index.json"

        indexer = ElixirIndexer(verbose=False)
        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(index_path),
            extract_keywords=True,
            extract_cochange=True,
        )

        # Step 2: Verify index contains co-change data
        with open(index_path) as f:
            index = json.load(f)

        # Verify co-change metadata exists
        assert "cochange_metadata" in index
        assert index["cochange_metadata"]["commit_count"] == 4
        assert index["cochange_metadata"]["file_pairs"] > 0

        # Verify module co-change data
        auth_module = index["modules"]["MyApp.Auth"]
        assert "cochange_files" in auth_module

        # Auth should co-change with Credentials (3 times) and Logger (2 times: initial + commit 4)
        cochange_files = {cf["file"]: cf["count"] for cf in auth_module["cochange_files"]}
        assert "lib/credentials.ex" in cochange_files
        assert cochange_files["lib/credentials.ex"] == 3
        assert "lib/logger.ex" in cochange_files
        assert cochange_files["lib/logger.ex"] == 2  # Initial commit + commit 4

        # Step 3: Search with co-change boosting
        searcher_with_boost = KeywordSearcher(index, cochange_boost=0.5)
        searcher_without_boost = KeywordSearcher(index, cochange_boost=0.0)

        # Search for "authentication" - should match Auth module
        results_with = searcher_with_boost.search(["authentication"], top_n=10)
        results_without = searcher_without_boost.search(["authentication"], top_n=10)

        # Both should have results
        assert len(results_with) > 0
        assert len(results_without) > 0

        # With boost should have higher scores due to co-change relationships
        auth_result_with = next(r for r in results_with if r["module"] == "MyApp.Auth")
        auth_result_without = next(r for r in results_without if r["module"] == "MyApp.Auth")

        assert auth_result_with["score"] > auth_result_without["score"]

        # Step 4: Verify co-change info is populated in results
        assert "cochange_info" in auth_result_with
        assert "related_files" in auth_result_with["cochange_info"]

        # Verify the related files are sorted by count (Credentials before Logger)
        related_files = auth_result_with["cochange_info"]["related_files"]
        assert len(related_files) >= 2
        assert related_files[0]["module"] == "MyApp.Credentials"
        assert related_files[0]["count"] == 3
        assert related_files[1]["module"] == "MyApp.Logger"
        assert related_files[1]["count"] == 2

        # Step 5: Verify formatting displays co-change info
        formatted = ModuleFormatter.format_keyword_search_results_markdown(
            results_with, show_scores=True
        )

        # Check that formatted output contains co-change information
        assert "Often changed with:" in formatted
        assert "MyApp.Credentials" in formatted
        assert "3 commits" in formatted or "2 commits" in formatted  # Should show both

    def test_cochange_boost_affects_ranking(self, git_repo_with_cochanges, tmp_path):
        """Test that co-change boost can affect search result ranking."""
        from cicada.indexer import ElixirIndexer
        from cicada.keyword_search import KeywordSearcher

        # Index with co-change
        repo_path = git_repo_with_cochanges
        index_path = tmp_path / "index.json"

        indexer = ElixirIndexer(verbose=False)
        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(index_path),
            extract_keywords=True,
            extract_cochange=True,
        )

        with open(index_path) as f:
            index = json.load(f)

        # Search for generic terms that might match multiple modules
        searcher_with_boost = KeywordSearcher(index, cochange_boost=1.0)  # High boost
        searcher_without_boost = KeywordSearcher(index, cochange_boost=0.0)  # No boost

        results_with = searcher_with_boost.search(["user", "check"], top_n=10)
        results_without = searcher_without_boost.search(["user", "check"], top_n=10)

        # Results should exist
        assert len(results_with) > 0
        assert len(results_without) > 0

        # Extract scores for comparison
        scores_with = {r["module"]: r["score"] for r in results_with}
        scores_without = {r["module"]: r["score"] for r in results_without}

        # Modules with more co-changes should get a bigger boost
        if "MyApp.Auth" in scores_with and "MyApp.Auth" in scores_without:
            # Auth has co-changes, so it should be boosted
            assert scores_with["MyApp.Auth"] > scores_without["MyApp.Auth"]

    def test_index_without_cochange_has_no_metadata(self, git_repo_with_cochanges, tmp_path):
        """Test that indexing without co-change flag produces no co-change data."""
        from cicada.indexer import ElixirIndexer

        repo_path = git_repo_with_cochanges
        index_path = tmp_path / "index.json"

        # Index WITHOUT co-change extraction
        indexer = ElixirIndexer(verbose=False)
        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(index_path),
            extract_keywords=True,
            extract_cochange=False,  # Disabled
        )

        # Verify no co-change data in index
        with open(index_path) as f:
            index = json.load(f)

        assert "cochange_metadata" not in index

        # Modules should not have co-change data
        for module_data in index["modules"].values():
            assert "cochange_files" not in module_data

    def test_search_without_cochange_data_still_works(self, git_repo_with_cochanges, tmp_path):
        """Test that search works normally when index has no co-change data."""
        from cicada.indexer import ElixirIndexer
        from cicada.keyword_search import KeywordSearcher

        repo_path = git_repo_with_cochanges
        index_path = tmp_path / "index.json"

        # Index without co-change
        indexer = ElixirIndexer(verbose=False)
        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(index_path),
            extract_keywords=True,
            extract_cochange=False,
        )

        with open(index_path) as f:
            index = json.load(f)

        # Search with boost enabled (should not crash)
        searcher = KeywordSearcher(index, cochange_boost=0.5)
        results = searcher.search(["authentication"], top_n=10)

        # Should still get results based on keyword matching
        assert len(results) > 0
        assert any(r["module"] == "MyApp.Auth" for r in results)

        # Results should not have cochange_info (no data available)
        for result in results:
            assert "cochange_info" not in result
