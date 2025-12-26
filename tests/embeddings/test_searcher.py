"""Tests for the embeddings searcher module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestEmbeddingsSearcher:
    """Tests for EmbeddingsSearcher class."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock Store with search results."""
        with patch("cicada.embeddings.searcher.Store") as mock:
            store_instance = MagicMock()
            mock.return_value = store_instance
            yield store_instance

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results from cicada-vector."""
        return [
            (
                "function:MyApp.User.create/1",
                0.95,
                {
                    "type": "function",
                    "name": "MyApp.User.create/1",
                    "module": "MyApp.User",
                    "function": "create",
                    "arity": 1,
                    "file": "lib/my_app/user.ex",
                    "line": 10,
                    "visibility": "def",
                },
            ),
            (
                "module:MyApp.User",
                0.85,
                {
                    "type": "module",
                    "name": "MyApp.User",
                    "module": "MyApp.User",
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                },
            ),
        ]

    def test_searcher_raises_when_no_embeddings(self, tmp_path):
        """Test that searcher raises FileNotFoundError when embeddings don't exist."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        with pytest.raises(FileNotFoundError) as exc_info:
            EmbeddingsSearcher(tmp_path)

        assert "Embeddings not found" in str(exc_info.value)

    def test_search_returns_results(self, tmp_path, mock_store, sample_search_results):
        """Test that search returns results in correct format."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        # Create a fake embeddings file
        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        mock_store.search.return_value = sample_search_results

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            searcher = EmbeddingsSearcher(tmp_path)
            searcher.embeddings_path = embeddings_file
            results = searcher.search("user authentication", top_n=10)

        assert len(results) == 2
        assert results[0]["type"] == "function"
        assert results[0]["name"] == "MyApp.User.create/1"
        assert results[0]["score"] == 0.95
        assert results[0]["semantic_match"] is True

    def test_search_filters_by_type(self, tmp_path, mock_store, sample_search_results):
        """Test that search filters results by type."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        mock_store.search.return_value = sample_search_results

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            searcher = EmbeddingsSearcher(tmp_path)
            searcher.embeddings_path = embeddings_file

            # Filter to modules only
            results = searcher.search("user", filter_type="modules")

        assert len(results) == 1
        assert results[0]["type"] == "module"

    def test_search_handles_list_query(self, tmp_path, mock_store, sample_search_results):
        """Test that search handles list queries."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        mock_store.search.return_value = sample_search_results

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            searcher = EmbeddingsSearcher(tmp_path)
            searcher.embeddings_path = embeddings_file
            results = searcher.search(["user", "authentication"], top_n=10)

        # Should have combined the query terms
        mock_store.search.assert_called_once()
        call_args = mock_store.search.call_args
        assert "user" in call_args[0][0] or "user" in call_args[1].get("query", "")

    def test_search_filters_by_functions_type(self, tmp_path, mock_store):
        """Test that search filters to functions only."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        # Include both modules and functions in results
        search_results = [
            (
                "function:MyApp.User.create/1",
                0.95,
                {
                    "type": "function",
                    "name": "MyApp.User.create/1",
                    "module": "MyApp.User",
                    "function": "create",
                    "arity": 1,
                    "file": "lib/my_app/user.ex",
                    "line": 10,
                    "visibility": "def",
                },
            ),
            (
                "module:MyApp.User",
                0.85,
                {
                    "type": "module",
                    "name": "MyApp.User",
                    "module": "MyApp.User",
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                },
            ),
        ]

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        mock_store.search.return_value = search_results

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            searcher = EmbeddingsSearcher(tmp_path)
            searcher.embeddings_path = embeddings_file

            # Filter to functions only
            results = searcher.search("user", filter_type="functions")

        assert len(results) == 1
        assert results[0]["type"] == "function"

    def test_search_respects_top_n_limit(self, tmp_path, mock_store):
        """Test that search respects top_n limit."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        # Return more results than top_n
        search_results = [
            (f"function:Mod{i}.func/1", 0.95 - i * 0.1, {"type": "function", "name": f"func{i}"})
            for i in range(10)
        ]

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        mock_store.search.return_value = search_results

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            searcher = EmbeddingsSearcher(tmp_path)
            searcher.embeddings_path = embeddings_file

            # Request only top 3
            results = searcher.search("query", top_n=3)

        assert len(results) == 3

    def test_search_includes_doc_field(self, tmp_path, mock_store):
        """Test that search includes doc field when present in metadata."""
        from cicada.embeddings.searcher import EmbeddingsSearcher

        search_results = [
            (
                "function:MyApp.User.create/1",
                0.95,
                {
                    "type": "function",
                    "name": "MyApp.User.create/1",
                    "module": "MyApp.User",
                    "function": "create",
                    "arity": 1,
                    "file": "lib/my_app/user.ex",
                    "line": 10,
                    "visibility": "def",
                    "doc": "Creates a new user with the given attributes.",
                },
            ),
        ]

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        mock_store.search.return_value = search_results

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            searcher = EmbeddingsSearcher(tmp_path)
            searcher.embeddings_path = embeddings_file
            results = searcher.search("create user", top_n=10)

        assert len(results) == 1
        assert results[0]["doc"] == "Creates a new user with the given attributes."


class TestHasEmbeddings:
    """Tests for has_embeddings function."""

    def test_has_embeddings_when_file_exists(self, tmp_path):
        """Test has_embeddings returns True when file exists."""
        from cicada.embeddings.searcher import has_embeddings

        # Create embeddings file
        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("")

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            result = has_embeddings(tmp_path)

        assert result is True

    def test_has_embeddings_when_file_missing(self, tmp_path):
        """Test has_embeddings returns False when file doesn't exist."""
        from cicada.embeddings.searcher import has_embeddings

        embeddings_file = tmp_path / "nonexistent" / "embeddings.jsonl"

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            result = has_embeddings(tmp_path)

        assert result is False


class TestSearchPrsSemantically:
    """Tests for search_prs_semantically function."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock Store with search results."""
        with patch("cicada.embeddings.searcher.Store") as mock:
            store_instance = MagicMock()
            mock.return_value = store_instance
            yield store_instance

    def test_returns_empty_when_no_embeddings(self, tmp_path):
        """Returns empty list when embeddings don't exist."""
        from cicada.embeddings.searcher import search_prs_semantically

        embeddings_file = tmp_path / "nonexistent" / "vectors.jsonl"

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            result = search_prs_semantically(tmp_path, "query")

        assert result == []

    def test_returns_pr_results(self, tmp_path, mock_store):
        """Returns PRSearchResult objects for PR matches."""
        from cicada.embeddings.searcher import search_prs_semantically

        # Mock search results with PRs
        pr_results = [
            (
                "pr:42",
                0.95,
                {
                    "type": "pr",
                    "pr_number": 42,
                    "title": "Add authentication",
                    "state": "merged",
                    "author": "testuser",
                    "merged_at": "2024-01-01",
                    "created_at": "2023-12-01",
                },
            ),
            (
                "pr:43",
                0.85,
                {
                    "type": "pr",
                    "pr_number": 43,
                    "title": "Fix bug",
                    "state": "closed",
                    "author": "dev",
                },
            ),
        ]

        mock_store.search.return_value = pr_results

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "vectors.jsonl"
        embeddings_file.write_text("")

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            results = search_prs_semantically(tmp_path, "authentication")

        assert len(results) == 2
        assert results[0].pr_number == 42
        assert results[0].title == "Add authentication"
        assert results[0].score == 0.95
        assert results[0].state == "merged"
        assert results[0].author == "testuser"
        assert results[0].merged_at == "2024-01-01"
        assert results[0].created_at == "2023-12-01"

    def test_filters_non_pr_results(self, tmp_path, mock_store):
        """Filters out non-PR results from search."""
        from cicada.embeddings.searcher import search_prs_semantically

        # Mix of PR and non-PR results
        mixed_results = [
            (
                "function:MyApp.Auth.login/2",
                0.98,
                {"type": "function", "name": "login"},
            ),
            (
                "pr:42",
                0.85,
                {
                    "type": "pr",
                    "pr_number": 42,
                    "title": "Add auth",
                    "state": "merged",
                    "author": "dev",
                },
            ),
            (
                "module:MyApp.Auth",
                0.80,
                {"type": "module", "name": "Auth"},
            ),
        ]

        mock_store.search.return_value = mixed_results

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "vectors.jsonl"
        embeddings_file.write_text("")

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            results = search_prs_semantically(tmp_path, "auth")

        assert len(results) == 1
        assert results[0].pr_number == 42

    def test_respects_top_n_limit(self, tmp_path, mock_store):
        """Respects top_n limit for PR results."""
        from cicada.embeddings.searcher import search_prs_semantically

        # Generate many PR results
        pr_results = [
            (
                f"pr:{i}",
                0.95 - i * 0.05,
                {
                    "type": "pr",
                    "pr_number": i,
                    "title": f"PR {i}",
                    "state": "merged",
                    "author": "dev",
                },
            )
            for i in range(10)
        ]

        mock_store.search.return_value = pr_results

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "vectors.jsonl"
        embeddings_file.write_text("")

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            results = search_prs_semantically(tmp_path, "query", top_n=3)

        assert len(results) == 3

    def test_returns_empty_on_exception(self, tmp_path, mock_store):
        """Returns empty list when an exception occurs."""
        from cicada.embeddings.searcher import search_prs_semantically

        mock_store.search.side_effect = Exception("Search failed")

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "vectors.jsonl"
        embeddings_file.write_text("")

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            results = search_prs_semantically(tmp_path, "query")

        assert results == []

    def test_handles_missing_optional_fields(self, tmp_path, mock_store):
        """Handles PRs with missing optional fields."""
        from cicada.embeddings.searcher import search_prs_semantically

        # PR with minimal fields
        pr_results = [
            (
                "pr:1",
                0.90,
                {
                    "type": "pr",
                    "pr_number": 1,
                    "title": "Minimal PR",
                    # No state, author, merged_at, created_at
                },
            ),
        ]

        mock_store.search.return_value = pr_results

        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "vectors.jsonl"
        embeddings_file.write_text("")

        with patch("cicada.embeddings.searcher.get_embeddings_path", return_value=embeddings_file):
            results = search_prs_semantically(tmp_path, "query")

        assert len(results) == 1
        assert results[0].pr_number == 1
        assert results[0].state == "unknown"
        assert results[0].author == "unknown"
        assert results[0].merged_at is None
        assert results[0].created_at is None
