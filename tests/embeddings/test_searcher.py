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
