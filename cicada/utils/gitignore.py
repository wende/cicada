"""Shared .gitignore filtering for all indexers.

Provides GitIgnoreFilter which loads .gitignore and .git/info/exclude patterns
using pathspec, so that all language indexers consistently skip gitignored files.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from pathspec import PathSpec


class GitIgnoreFilter:
    """Filter files and directories based on .gitignore patterns.

    Loads patterns from:
    - .gitignore (repo root)
    - .git/info/exclude

    Always ignores .git/ itself.
    """

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path
        self._spec = self._load_patterns(repo_path)

    @staticmethod
    def _read_pattern_file(path: Path) -> list[str]:
        patterns: list[str] = []
        with contextlib.suppress(OSError):
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        return patterns

    @classmethod
    def load_pattern_lines(cls, repo_path: Path) -> list[str]:
        """Load normalized gitignore-style patterns from repo files."""
        patterns: list[str] = [".git/"]

        # Load .gitignore
        gitignore = repo_path / ".gitignore"
        if gitignore.is_file():
            patterns.extend(cls._read_pattern_file(gitignore))

        # Load .git/info/exclude
        exclude = repo_path / ".git" / "info" / "exclude"
        if exclude.is_file():
            patterns.extend(cls._read_pattern_file(exclude))

        return patterns

    @classmethod
    def _load_patterns(cls, repo_path: Path) -> PathSpec:
        patterns = cls.load_pattern_lines(repo_path)
        return PathSpec.from_lines("gitwildmatch", patterns)

    def is_ignored(self, relative_path: str) -> bool:
        """Check if a file path is ignored."""
        return self._spec.match_file(relative_path)

    def is_dir_ignored(self, relative_dir: str) -> bool:
        """Check if a directory is ignored."""
        return self._spec.match_file(relative_dir) or self._spec.match_file(f"{relative_dir}/")

    def get_ignored_files(self, suffixes: tuple[str, ...] | None = None) -> list[str]:
        """Return ignored files currently present in the repository.

        Args:
            suffixes: Optional tuple of filename suffixes to include

        Returns:
            Sorted list of ignored file paths relative to repo root.
        """
        ignored_files: list[str] = []

        for root, _dirs, files in os.walk(self._repo_path):
            root_path = Path(root)
            rel_root = root_path.relative_to(self._repo_path)
            rel_root_str = "" if rel_root == Path(".") else rel_root.as_posix()

            for filename in files:
                if suffixes and not filename.endswith(suffixes):
                    continue

                rel_path = f"{rel_root_str}/{filename}" if rel_root_str else filename
                if self.is_ignored(rel_path):
                    ignored_files.append(rel_path)

        return sorted(set(ignored_files))
