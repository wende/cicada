"""
Embeddings indexer for semantic code search.

Indexes modules and functions from the parsed code index into cicada-vector Store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cicada_vector import Store

from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_HOST
from cicada.embeddings.text_builder import (
    build_document_id,
    build_function_text,
    build_metadata,
    build_module_text,
)
from cicada.utils.storage import get_embeddings_path


def _read_embeddings_config(repo_path: Path) -> dict[str, str]:
    """
    Read embeddings configuration from config.yaml.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with 'ollama_host' and 'model' keys
    """
    import yaml

    from cicada.utils.storage import get_config_path

    config_path = get_config_path(repo_path)
    if not config_path.exists():
        return {"ollama_host": DEFAULT_OLLAMA_HOST, "model": DEFAULT_EMBEDDING_MODEL}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
            embeddings_config = config.get("embeddings", {})
            return {
                "ollama_host": embeddings_config.get("ollama_host", DEFAULT_OLLAMA_HOST),
                "model": embeddings_config.get("model", DEFAULT_EMBEDDING_MODEL),
            }
    except Exception:
        return {"ollama_host": DEFAULT_OLLAMA_HOST, "model": DEFAULT_EMBEDDING_MODEL}


class EmbeddingsIndexer:
    """
    Indexes code into cicada-vector Store for semantic search.

    Creates embeddings for modules and functions from an already-parsed index.
    """

    def __init__(
        self,
        repo_path: str | Path,
        verbose: bool = False,
        ollama_host: str | None = None,
        model: str | None = None,
    ):
        """
        Initialize the embeddings indexer.

        Args:
            repo_path: Path to the repository
            verbose: Whether to print progress information
            ollama_host: Ollama host URL (reads from config if not provided)
            model: Embedding model name (reads from config if not provided)
        """
        self.repo_path = Path(repo_path).resolve()
        self.verbose = verbose
        self.embeddings_path = get_embeddings_path(repo_path)

        # Read config if parameters not provided
        if ollama_host is None or model is None:
            config = _read_embeddings_config(self.repo_path)
            ollama_host = ollama_host or config["ollama_host"]
            model = model or config["model"]

        self.ollama_host = ollama_host
        self.model = model

        # Ensure parent directory exists
        self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize the store with Ollama configuration
        self.store = Store(
            str(self.embeddings_path.parent),
            ollama_host=self.ollama_host,
            ollama_model=self.model,
        )

        if self.verbose:
            print(f"Using Ollama at {self.ollama_host} with model {self.model}")

    def index_from_parsed_data(self, index: dict[str, Any]) -> None:
        """
        Index embeddings from already-parsed module data.

        Iterates through all modules and functions in the index and creates
        embeddings for each one.

        Args:
            index: Parsed index dictionary with modules and metadata
        """
        modules = index.get("modules", {})
        total_modules = len(modules)
        total_functions = 0

        if self.verbose:
            print(f"Indexing embeddings for {total_modules} modules...")

        for i, (module_name, module_data) in enumerate(modules.items(), 1):
            if self.verbose and i % 10 == 0:
                print(f"  Processing module {i}/{total_modules}...")

            self._index_module(module_name, module_data)

            # Count functions
            functions = module_data.get("functions", [])
            total_functions += len(functions)

        if self.verbose:
            print(f"Indexed {total_modules} modules and {total_functions} functions")

    def _index_module(self, module_name: str, module_data: dict[str, Any]) -> None:
        """
        Index a single module and its functions.

        Args:
            module_name: Full module name
            module_data: Module data from the index
        """
        file_path = module_data.get("file", "")
        module_line = module_data.get("line", 1)

        # Index the module itself
        module_text = build_module_text(module_name, module_data)
        module_id = build_document_id("module", module_name)
        module_meta = build_metadata("module", module_name, file_path, module_line)

        self.store.add(id=module_id, text=module_text, meta=module_meta)

        # Index each function in the module
        for func_data in module_data.get("functions", []):
            self._index_function(module_name, file_path, func_data)

    def _index_function(self, module_name: str, file_path: str, func_data: dict[str, Any]) -> None:
        """
        Index a single function.

        Args:
            module_name: Full module name containing the function
            file_path: Path to the source file
            func_data: Function data from the index
        """
        func_line = func_data.get("line", 1)

        func_text = build_function_text(module_name, func_data)
        func_id = build_document_id("function", module_name, func_data)
        func_meta = build_metadata("function", module_name, file_path, func_line, func_data)

        self.store.add(id=func_id, text=func_text, meta=func_meta)

    def remove_file_embeddings(self, file_path: str) -> int:
        """
        Remove embeddings for all modules/functions in a file.

        Used for incremental indexing when a file has changed.

        Args:
            file_path: Relative path to the file

        Returns:
            Number of embeddings removed
        """
        # Note: cicada-vector Store may not support deletion directly
        # This is a placeholder for incremental indexing support
        # For now, we rely on full reindexing with --force
        return 0

    def clear(self) -> None:
        """
        Clear all embeddings from the store.

        Removes the embeddings file entirely for a fresh start.
        """
        if self.embeddings_path.exists():
            self.embeddings_path.unlink()
            if self.verbose:
                print("Cleared embeddings store")
