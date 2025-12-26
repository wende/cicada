"""
Embeddings indexer for semantic code search.

Indexes modules and functions from the parsed code index into cicada-vector Store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cicada_vector import Store

from cicada.embeddings.text_builder import (
    build_document_id,
    build_function_text,
    build_metadata,
    build_module_text,
)
from cicada.utils.storage import get_embeddings_path


class EmbeddingsIndexer:
    """
    Indexes code into cicada-vector Store for semantic search.

    Creates embeddings for modules and functions from an already-parsed index.
    """

    def __init__(self, repo_path: str | Path, verbose: bool = False):
        """
        Initialize the embeddings indexer.

        Args:
            repo_path: Path to the repository
            verbose: Whether to print progress information
        """
        self.repo_path = Path(repo_path).resolve()
        self.verbose = verbose
        self.embeddings_path = get_embeddings_path(repo_path)

        # Ensure parent directory exists
        self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize the store
        self.store = Store(str(self.embeddings_path.parent))

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
