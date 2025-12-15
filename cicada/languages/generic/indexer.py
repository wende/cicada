"""
Generic indexer for repository text files.

This indexer runs after language-specific indexers and adds documentation/config
files (README.md, docs/*.md, etc.) to the unified index. It extracts keywords
using RegularKeywordExtractor so that plain-text resources are searchable.
"""

from __future__ import annotations

import contextlib
import mimetypes
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from pathspec import PathSpec

from cicada.extractors.keyword import RegularKeywordExtractor
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils import load_index, save_index
from cicada.utils.index_utils import get_index_stats


class GenericFileIndexer(BaseIndexer):
    """Indexes repository text files that aren't handled by language indexers."""

    supports_incremental = True
    MAX_LINES = 10_000
    _BINARY_PREFIXES = ("image/", "audio/", "video/")

    def __init__(
        self,
        excluded_extensions: set[str] | None = None,
        verbose: bool = False,
    ):
        super().__init__(verbose=verbose)
        self.excluded_extensions = {ext.lower() for ext in (excluded_extensions or set())}

    def get_language_name(self) -> str:
        return "generic"

    def get_file_extensions(self) -> list[str]:
        # Not used - overridden file discovery handles all text files.
        return []

    def get_excluded_dirs(self) -> list[str]:
        # Directory exclusion is handled via .gitignore/pathspec filtering.
        return []

    def _load_gitignore(self, repo_path: Path) -> PathSpec:
        """Load gitignore patterns and ensure git metadata files are always ignored."""
        patterns = [".git/", ".gitmodules", ".gitattributes"]
        gitignore_path = repo_path / ".gitignore"
        if gitignore_path.exists():
            with contextlib.suppress(OSError):
                patterns.extend(gitignore_path.read_text().splitlines())
        return PathSpec.from_lines("gitwildmatch", patterns)

    def _is_text_file(self, file_path: Path) -> bool:
        """Heuristic check to ensure the file is text-based."""
        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
        except Exception:
            mime_type = None

        if mime_type and (
            mime_type.startswith(self._BINARY_PREFIXES) or mime_type == "application/octet-stream"
        ):
            return False

        try:
            with open(file_path, "rb") as handle:
                chunk = handle.read(8192)
                if b"\x00" in chunk:
                    return False
        except OSError:
            return False

        return True

    def _read_text_file(self, file_path: Path) -> tuple[str, int] | None:
        """Read a text file while enforcing the size limit."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as handle:
                content_parts: list[str] = []
                line_count = 0
                for line in handle:
                    line_count += 1
                    if line_count > self.MAX_LINES:
                        return None
                    content_parts.append(line)
        except OSError:
            return None

        return ("".join(content_parts), line_count)

    def _normalize_relative(self, repo_path: Path, target: Path) -> str:
        return target.relative_to(repo_path).as_posix()

    def _should_ignore(self, spec: PathSpec, relative_path: str) -> bool:
        return spec.match_file(relative_path) or spec.match_file(f"{relative_path}/")

    def _find_source_files(self, repo_path: Path) -> list[Path]:
        """Collect gitignored-aware list of candidate text files."""
        spec = self._load_gitignore(repo_path)
        files: list[Path] = []

        for root, dirs, filenames in os.walk(repo_path):
            root_path = Path(root)
            rel_root = root_path.relative_to(repo_path).as_posix() if root_path != repo_path else ""

            # Remove ignored directories to avoid needless traversal.
            for dirname in list(dirs):
                rel_dir = f"{rel_root}/{dirname}" if rel_root else dirname
                if self._should_ignore(spec, rel_dir):
                    dirs.remove(dirname)

            for filename in filenames:
                file_path = root_path / filename
                rel_path = f"{rel_root}/{filename}" if rel_root else filename  # Always POSIX-style

                if self._should_ignore(spec, rel_path):
                    continue

                suffix = file_path.suffix.lower()
                if suffix and suffix in self.excluded_extensions:
                    continue

                if not self._is_text_file(file_path):
                    continue

                if not self.should_index_file(file_path):
                    continue

                files.append(file_path)

        # Sort for deterministic ordering
        return sorted(files, key=lambda path: path.relative_to(repo_path).as_posix())

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,  # noqa: ARG002 - interface requirement
        verbose: bool = False,
        config_path: str | Path | None = None,  # noqa: ARG002 - unused
    ) -> dict[str, Any]:
        """
        Index generic text files and merge them into an existing index.
        """
        self.verbose = verbose
        repo = Path(repo_path).resolve()
        output = Path(output_path)

        index_data = load_index(output) or {"modules": {}, "metadata": {}}
        modules = index_data.setdefault("modules", {})
        metadata = index_data.setdefault("metadata", {})

        extractor = RegularKeywordExtractor(verbose=self.verbose)
        source_files = self._find_source_files(repo)

        new_modules: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        for file_path in source_files:
            rel_path = self._normalize_relative(repo, file_path)
            read_result = self._read_text_file(file_path)
            if read_result is None:
                continue

            content, line_count = read_result
            keyword_data = extractor.extract_keywords(content, top_n=25)
            keyword_scores = dict(keyword_data.get("top_keywords", []))

            module_entry: dict[str, Any] = {
                "file": rel_path,
                "line": 1,
                "functions": [],
                "calls": [],
                "total_functions": 0,
                "public_functions": 0,
                "private_functions": 0,
                "module_type": "generic_file",
                "line_count": line_count,
            }
            if keyword_scores:
                module_entry["keywords"] = keyword_scores
            if stats := keyword_data.get("stats"):
                module_entry["text_stats"] = stats

            new_modules[rel_path] = module_entry

        # Remove stale generic modules
        stale = [
            name
            for name, data in modules.items()
            if data.get("module_type") == "generic_file" and name not in new_modules
        ]
        for name in stale:
            modules.pop(name, None)

        modules.update(new_modules)

        # Update metadata counts to reflect merged modules
        stats = get_index_stats(index_data)
        metadata["total_modules"] = stats["total_modules"]
        metadata["total_functions"] = stats["total_functions"]
        metadata["public_functions"] = stats["public_functions"]
        metadata["private_functions"] = stats["private_functions"]
        metadata["indexed_at"] = datetime.now().isoformat()

        try:
            save_index(index_data, output)
        except Exception as exc:  # pragma: no cover - IO errors handled by caller
            errors.append(str(exc))
            raise

        return {
            "success": not errors,
            "modules_count": len(new_modules),
            "functions_count": 0,
            "files_indexed": len(new_modules),
            "errors": errors,
            "metadata": metadata,
        }

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,  # noqa: ARG002 - interface compatibility
        extract_string_keywords: bool = False,  # noqa: ARG002
        compute_timestamps: bool = False,  # noqa: ARG002
        extract_cochange: bool = False,  # noqa: ARG002
        force_full: bool = False,  # noqa: ARG002
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Generic indexing always reprocesses the current text file set."""
        return self.index_repository(repo_path, output_path, verbose=verbose)


def _normalize_extensions(excluded_extensions: Iterable[str] | None) -> set[str]:
    if not excluded_extensions:
        return set()
    return {ext.lower() for ext in excluded_extensions if ext}


def run_generic_indexing(
    repo_path: str | Path,
    index_path: str | Path,
    excluded_extensions: Iterable[str] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Convenience helper to run the generic indexer for a repository.
    """
    indexer = GenericFileIndexer(
        excluded_extensions=_normalize_extensions(excluded_extensions),
        verbose=verbose,
    )
    return indexer.index_repository(
        repo_path=str(repo_path),
        output_path=str(index_path),
        verbose=verbose,
    )


def run_generic_indexing_for_language_indexer(
    language_indexer: BaseIndexer,
    repo_path: str | Path,
    index_path: str | Path,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run generic indexing using the extensions reported by a primary language indexer.
    """
    return run_generic_indexing(
        repo_path=repo_path,
        index_path=index_path,
        excluded_extensions=language_indexer.get_file_extensions(),
        verbose=verbose,
    )


__all__ = [
    "GenericFileIndexer",
    "run_generic_indexing",
    "run_generic_indexing_for_language_indexer",
]
