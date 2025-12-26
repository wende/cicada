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

    def test_indexer_with_verbose_mode(self, tmp_path, mock_store, capsys):
        """Test that indexer outputs progress in verbose mode."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=True)

        captured = capsys.readouterr()
        assert "Using Ollama" in captured.out

    def test_indexer_with_force_clears_embeddings(self, tmp_path, mock_store):
        """Test that force mode clears existing embeddings."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        # Create fake embeddings file
        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        vectors_file = embeddings_dir / "vectors.jsonl"
        vectors_file.write_text("existing data")

        with patch("cicada.embeddings.indexer.get_embeddings_path") as mock_path:
            mock_path.return_value = embeddings_dir / "vectors.jsonl"
            indexer = EmbeddingsIndexer(tmp_path, force=True, verbose=False)
            indexer.embeddings_path = embeddings_dir / "vectors.jsonl"
            # The embeddings_path.parent is used for vectors_file in _clear_embeddings

        # Should have been cleared
        assert not vectors_file.exists()

    def test_index_from_parsed_data_verbose(self, tmp_path, mock_store, sample_index, capsys):
        """Test verbose output during indexing."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=True)
        indexer.index_from_parsed_data(sample_index)

        captured = capsys.readouterr()
        assert "Indexing embeddings" in captured.out
        assert "Indexed 2 modules" in captured.out

    def test_remove_file_embeddings(self, tmp_path, mock_store):
        """Test that remove_file_embeddings returns 0 (placeholder)."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        indexer = EmbeddingsIndexer(tmp_path, verbose=False)
        result = indexer.remove_file_embeddings("lib/my_app/user.ex")

        assert result == 0

    def test_clear_with_verbose(self, tmp_path, mock_store, capsys):
        """Test that clear outputs message in verbose mode."""
        from cicada.embeddings.indexer import EmbeddingsIndexer

        # Create fake embeddings file
        embeddings_dir = tmp_path / ".cicada" / "projects" / "test"
        embeddings_dir.mkdir(parents=True)
        embeddings_file = embeddings_dir / "vectors.jsonl"
        embeddings_file.write_text("existing data")

        with patch("cicada.embeddings.indexer.get_embeddings_path", return_value=embeddings_file):
            indexer = EmbeddingsIndexer(tmp_path, verbose=True)
            indexer.embeddings_path = embeddings_file
            # Capture after init
            capsys.readouterr()

            indexer.clear()

        captured = capsys.readouterr()
        assert "Cleared embeddings store" in captured.out
        assert not embeddings_file.exists()


class TestReadEmbeddingsConfig:
    """Tests for _read_embeddings_config function."""

    def test_returns_defaults_when_no_config(self, tmp_path):
        """Returns default values when config file doesn't exist."""
        from cicada.embeddings.indexer import _read_embeddings_config
        from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_HOST

        with patch("cicada.utils.storage.get_config_path") as mock_config:
            mock_config.return_value = tmp_path / "nonexistent" / "config.yaml"
            result = _read_embeddings_config(tmp_path)

        assert result["ollama_host"] == DEFAULT_OLLAMA_HOST
        assert result["model"] == DEFAULT_EMBEDDING_MODEL

    def test_reads_config_from_yaml(self, tmp_path):
        """Reads embeddings configuration from config.yaml."""
        from cicada.embeddings.indexer import _read_embeddings_config

        # Create a config file with embeddings section
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
embeddings:
  ollama_host: http://custom-host:11434
  model: custom-model
"""
        )

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            result = _read_embeddings_config(tmp_path)

        assert result["ollama_host"] == "http://custom-host:11434"
        assert result["model"] == "custom-model"

    def test_uses_defaults_for_missing_embeddings_keys(self, tmp_path):
        """Uses defaults when embeddings keys are missing from config."""
        from cicada.embeddings.indexer import _read_embeddings_config
        from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_HOST

        # Create a config file without embeddings section
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
other_section:
  key: value
"""
        )

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            result = _read_embeddings_config(tmp_path)

        assert result["ollama_host"] == DEFAULT_OLLAMA_HOST
        assert result["model"] == DEFAULT_EMBEDDING_MODEL

    def test_returns_defaults_on_parse_error(self, tmp_path):
        """Returns defaults when config file has parse errors."""
        from cicada.embeddings.indexer import _read_embeddings_config
        from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_HOST

        # Create an invalid YAML file
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content:")

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            result = _read_embeddings_config(tmp_path)

        assert result["ollama_host"] == DEFAULT_OLLAMA_HOST
        assert result["model"] == DEFAULT_EMBEDDING_MODEL

    def test_handles_empty_config_file(self, tmp_path):
        """Handles empty config file gracefully."""
        from cicada.embeddings.indexer import _read_embeddings_config
        from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_HOST

        # Create an empty config file
        config_dir = tmp_path / ".cicada" / "projects" / "test"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("")

        with patch("cicada.utils.storage.get_config_path", return_value=config_file):
            result = _read_embeddings_config(tmp_path)

        assert result["ollama_host"] == DEFAULT_OLLAMA_HOST
        assert result["model"] == DEFAULT_EMBEDDING_MODEL


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
