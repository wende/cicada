"""
Ollama API utilities for embeddings configuration.

Provides functions to interact with Ollama API for discovering available models.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"

# Common embedding models to highlight
RECOMMENDED_EMBEDDING_MODELS = [
    "nomic-embed-text",
    "mxbai-embed-large",
    "all-minilm",
    "snowflake-arctic-embed",
]


def fetch_ollama_models(ollama_host: str = DEFAULT_OLLAMA_HOST) -> list[dict[str, Any]]:
    """
    Fetch available models from Ollama API.

    Args:
        ollama_host: Ollama host URL

    Returns:
        List of model dictionaries with 'name' and other metadata

    Raises:
        ConnectionError: If Ollama is not reachable
        RuntimeError: If the API response is invalid
    """
    url = f"{ollama_host}/api/tags"

    try:
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode())
            return result.get("models", [])
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot connect to Ollama at {ollama_host}: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid response from Ollama API: {e}") from e


def get_embedding_models(ollama_host: str = DEFAULT_OLLAMA_HOST) -> list[str]:
    """
    Get list of available embedding model names from Ollama.

    Filters to only show models that are likely embedding models
    (contain 'embed' in name) and sorts recommended models first.

    Args:
        ollama_host: Ollama host URL

    Returns:
        List of model names suitable for embeddings, sorted by recommendation

    Raises:
        ConnectionError: If Ollama is not reachable
    """
    models = fetch_ollama_models(ollama_host)
    model_names = [m.get("name", "").split(":")[0] for m in models]

    # Filter to embedding models (contain 'embed' or are in recommended list)
    embedding_models = []
    other_models = []

    for name in model_names:
        if not name:
            continue
        name_lower = name.lower()
        if "embed" in name_lower or name in RECOMMENDED_EMBEDDING_MODELS:
            embedding_models.append(name)
        else:
            other_models.append(name)

    # Sort: recommended first, then alphabetically
    def sort_key(name: str) -> tuple[int, int, str]:
        if name in RECOMMENDED_EMBEDDING_MODELS:
            return (0, RECOMMENDED_EMBEDDING_MODELS.index(name), name)
        return (1, 0, name)

    embedding_models.sort(key=lambda n: sort_key(n))

    # Include all models since user might want to use a non-embedding model
    # (some LLMs can do embeddings too)
    return embedding_models + sorted(other_models)


def check_ollama_connection(ollama_host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """
    Check if Ollama is reachable at the given host.

    Args:
        ollama_host: Ollama host URL

    Returns:
        True if Ollama is reachable, False otherwise
    """
    try:
        fetch_ollama_models(ollama_host)
        return True
    except (ConnectionError, RuntimeError):
        return False


def validate_model_available(model_name: str, ollama_host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """
    Check if a specific model is available in Ollama.

    Args:
        model_name: Name of the model to check
        ollama_host: Ollama host URL

    Returns:
        True if model is available, False otherwise
    """
    try:
        models = fetch_ollama_models(ollama_host)
        model_names = [m.get("name", "").split(":")[0] for m in models]
        return model_name in model_names
    except (ConnectionError, RuntimeError):
        return False
