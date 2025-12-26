"""Tests for the embeddings indexer module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestEmbeddingsIndexer:
    """Tests for EmbeddingsIndexer class."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock Store."""
        with patch("cicada.embeddings.indexer.Store") as mock:
            store_instance = MagicMock()
            mock.return_value = store_instance
            yield store_instance

    @pytest.fixture
    def sample_index(self):
        """Create a sample index for testing."""
        return {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User management module.",
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "type": "def",
                            "doc": "Creates a user.",
                        },
                        {
                            "name": "get",
                            "arity": 1,
                            "line": 20,
                            "type": "def",
                        },
                    ],
                },
                "MyApp.Repo": {
                    "file": "lib/my_app/repo.ex",
                    "line": 1,
                    "functions": [],
                },
            },
            "metadata": {
                "language": "elixir",
            },
        }

    def test_indexer_initialization(self, tmp_path, mock_store):
        """Test that indexer initializes correctly."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)

        assert indexer.repo_path == tmp_path
        assert indexer.verbose is False

    def test_index_from_parsed_data(self, tmp_path, mock_store, sample_index):
        """Test indexing from parsed data."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)
        indexer.index_from_parsed_data(sample_index)

        # Should have called add for:
        # - 2 modules (MyApp.User, MyApp.Repo)
        # - 2 functions (create, get)
        assert mock_store.add.call_count == 4

    def test_index_module_with_functions(self, tmp_path, mock_store, sample_index):
        """Test that module indexing includes functions."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)
        indexer._index_module("MyApp.User", sample_index["modules"]["MyApp.User"])

        # Should have called add for the module + 2 functions
        assert mock_store.add.call_count == 3

    def test_clear_removes_embeddings_file(self, tmp_path, mock_store):
        """Test that clear removes the embeddings file."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        # Create a fake embeddings file
        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "embeddings.jsonl"
        embeddings_file.write_text("test data")

        with patch("cicada.embeddings.indexer.get_embeddings_path", return_value=embeddings_file):
            indexer = EmbeddingsIndexer(tmp_path, verbose=False)
            indexer.embeddings_path = embeddings_file
            indexer.clear()

        assert not embeddings_file.exists()


class TestGetEmbeddingsPath:
    """Tests for get_embeddings_path via storage module."""

    def test_get_embeddings_path(self, tmp_path):
        """Test that get_embeddings_path returns correct path."""
        from cicada.utils.storage import get_embeddings_path

        result = get_embeddings_path(tmp_path)

        # cicada-vector uses vectors.jsonl as its storage format
        assert result.name == "vectors.jsonl"
        assert ".cicada" in str(result)
        assert "projects" in str(result)
