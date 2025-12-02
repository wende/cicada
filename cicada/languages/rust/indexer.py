"""SCIP-based indexer skeleton for Rust."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cicada.languages import BaseIndexer


class RustSCIPIndexer(BaseIndexer):
    """Minimal CICADA indexer placeholder for upcoming Rust support."""

    def __init__(self, verbose: bool = False):
        super().__init__(verbose=verbose)
        self._language_name = "rust"
        self._file_extensions = [".rs"]
        self._excluded_dirs = ["target", ".git", "vendor"]

    def get_language_name(self) -> str:
        return self._language_name

    def get_file_extensions(self) -> list[str]:
        return list(self._file_extensions)

    def get_excluded_dirs(self) -> list[str]:
        return list(self._excluded_dirs)

    def index_repository(  # pragma: no cover - will be implemented with full Rust support
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Placeholder entry point until full Rust indexing is implemented."""
        raise NotImplementedError(
            "Rust indexing is not implemented yet. Follow the Rust support plan to add full functionality."
        )
