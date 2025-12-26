"""Tests for the ollama module."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from cicada.embeddings.ollama import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_HOST,
    RECOMMENDED_EMBEDDING_MODELS,
    check_ollama_connection,
    fetch_ollama_models,
    get_embedding_models,
    validate_model_available,
)


class TestFetchOllamaModels:
    """Tests for fetch_ollama_models function."""

    def test_fetches_models_successfully(self):
        """Successfully fetches and returns models from Ollama API."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "models": [
                    {"name": "nomic-embed-text:latest", "size": 274302450},
                    {"name": "llama3:latest", "size": 4661224676},
                ]
            }
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_ollama_models()

        assert len(result) == 2
        assert result[0]["name"] == "nomic-embed-text:latest"
        assert result[1]["name"] == "llama3:latest"

    def test_uses_custom_host(self):
        """Uses custom host when provided."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"models": []}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            with patch("urllib.request.Request") as mock_request:
                mock_request.return_value = MagicMock()
                fetch_ollama_models("http://custom-host:11434")

        # Verify the request was made to the custom host
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "http://custom-host:11434/api/tags" in call_args[0]

    def test_raises_connection_error_on_url_error(self):
        """Raises ConnectionError when Ollama is not reachable."""
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            with pytest.raises(ConnectionError) as exc_info:
                fetch_ollama_models()

        assert "Cannot connect to Ollama" in str(exc_info.value)
        assert DEFAULT_OLLAMA_HOST in str(exc_info.value)

    def test_raises_runtime_error_on_invalid_json(self):
        """Raises RuntimeError when response is not valid JSON."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_ollama_models()

        assert "Invalid response from Ollama API" in str(exc_info.value)

    def test_returns_empty_list_when_no_models_key(self):
        """Returns empty list when response has no 'models' key."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"other_key": "value"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_ollama_models()

        assert result == []


class TestGetEmbeddingModels:
    """Tests for get_embedding_models function."""

    def test_filters_embedding_models(self):
        """Filters and prioritizes embedding models."""
        mock_models = [
            {"name": "llama3:latest"},
            {"name": "nomic-embed-text:latest"},
            {"name": "mxbai-embed-large:latest"},
            {"name": "codellama:latest"},
        ]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = get_embedding_models()

        # Embedding models should come first
        assert result[0] == "nomic-embed-text"
        assert result[1] == "mxbai-embed-large"
        # Non-embedding models should come at the end
        assert "llama3" in result
        assert "codellama" in result

    def test_sorts_recommended_models_first(self):
        """Recommended embedding models appear in order of recommendation."""
        mock_models = [
            {"name": "mxbai-embed-large:latest"},
            {"name": "all-minilm:latest"},
            {"name": "nomic-embed-text:latest"},
        ]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = get_embedding_models()

        # Should be in recommendation order
        assert result.index("nomic-embed-text") < result.index("mxbai-embed-large")
        assert result.index("mxbai-embed-large") < result.index("all-minilm")

    def test_skips_empty_model_names(self):
        """Skips models with empty or missing names."""
        mock_models = [
            {"name": "nomic-embed-text:latest"},
            {"name": ""},
            {},
            {"name": "llama3:latest"},
        ]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = get_embedding_models()

        assert "" not in result
        assert len(result) == 2

    def test_includes_recommended_models_without_embed_keyword(self):
        """Includes models in RECOMMENDED_EMBEDDING_MODELS even without 'embed' in name."""
        # all-minilm doesn't have 'embed' in name but is recommended
        mock_models = [
            {"name": "all-minilm:latest"},
            {"name": "custom-model:latest"},
        ]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = get_embedding_models()

        # all-minilm should be first as it's recommended
        assert result[0] == "all-minilm"

    def test_propagates_connection_error(self):
        """Propagates ConnectionError from fetch_ollama_models."""
        with patch(
            "cicada.embeddings.ollama.fetch_ollama_models",
            side_effect=ConnectionError("Cannot connect"),
        ):
            with pytest.raises(ConnectionError):
                get_embedding_models()


class TestCheckOllamaConnection:
    """Tests for check_ollama_connection function."""

    def test_returns_true_when_reachable(self):
        """Returns True when Ollama is reachable."""
        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=[{"name": "test"}]):
            result = check_ollama_connection()

        assert result is True

    def test_returns_false_on_connection_error(self):
        """Returns False when ConnectionError is raised."""
        with patch(
            "cicada.embeddings.ollama.fetch_ollama_models",
            side_effect=ConnectionError("Not reachable"),
        ):
            result = check_ollama_connection()

        assert result is False

    def test_returns_false_on_runtime_error(self):
        """Returns False when RuntimeError is raised."""
        with patch(
            "cicada.embeddings.ollama.fetch_ollama_models",
            side_effect=RuntimeError("Invalid response"),
        ):
            result = check_ollama_connection()

        assert result is False

    def test_uses_custom_host(self):
        """Uses custom host when provided."""
        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=[]) as mock_fetch:
            check_ollama_connection("http://custom:11434")

        mock_fetch.assert_called_once_with("http://custom:11434")


class TestValidateModelAvailable:
    """Tests for validate_model_available function."""

    def test_returns_true_when_model_exists(self):
        """Returns True when model is available."""
        mock_models = [
            {"name": "nomic-embed-text:latest"},
            {"name": "llama3:latest"},
        ]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = validate_model_available("nomic-embed-text")

        assert result is True

    def test_returns_false_when_model_not_found(self):
        """Returns False when model is not available."""
        mock_models = [{"name": "llama3:latest"}]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = validate_model_available("nomic-embed-text")

        assert result is False

    def test_returns_false_on_connection_error(self):
        """Returns False when ConnectionError is raised."""
        with patch(
            "cicada.embeddings.ollama.fetch_ollama_models",
            side_effect=ConnectionError("Not reachable"),
        ):
            result = validate_model_available("any-model")

        assert result is False

    def test_returns_false_on_runtime_error(self):
        """Returns False when RuntimeError is raised."""
        with patch(
            "cicada.embeddings.ollama.fetch_ollama_models",
            side_effect=RuntimeError("Invalid response"),
        ):
            result = validate_model_available("any-model")

        assert result is False

    def test_uses_custom_host(self):
        """Uses custom host when provided."""
        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=[]) as mock_fetch:
            validate_model_available("model", "http://custom:11434")

        mock_fetch.assert_called_once_with("http://custom:11434")

    def test_strips_version_tag_from_model_name(self):
        """Compares base model name without version tag."""
        mock_models = [{"name": "nomic-embed-text:v1.5"}]

        with patch("cicada.embeddings.ollama.fetch_ollama_models", return_value=mock_models):
            result = validate_model_available("nomic-embed-text")

        assert result is True


class TestConstants:
    """Tests for module constants."""

    def test_default_ollama_host(self):
        """Default Ollama host is localhost:11434."""
        assert DEFAULT_OLLAMA_HOST == "http://localhost:11434"

    def test_default_embedding_model(self):
        """Default embedding model is nomic-embed-text."""
        assert DEFAULT_EMBEDDING_MODEL == "nomic-embed-text"

    def test_recommended_models_list(self):
        """Recommended models list is not empty."""
        assert len(RECOMMENDED_EMBEDDING_MODELS) > 0
        assert "nomic-embed-text" in RECOMMENDED_EMBEDDING_MODELS
