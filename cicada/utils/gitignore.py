"""Shared .gitignore filtering for all indexers.

Provides GitIgnoreFilter which loads .gitignore and .git/info/exclude patterns
using pathspec, so that all language indexers consistently skip gitignored files.
"""

from __future__ import annotations

import contextlib
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
        self._spec = self._load_patterns(repo_path)

    @staticmethod
    def _load_patterns(repo_path: Path) -> PathSpec:
        patterns: list[str] = [".git/"]

        # Load .gitignore
        gitignore = repo_path / ".gitignore"
        if gitignore.is_file():
            with contextlib.suppress(OSError):
                patterns.extend(gitignore.read_text().splitlines())

        # Load .git/info/exclude
        exclude = repo_path / ".git" / "info" / "exclude"
        if exclude.is_file():
            with contextlib.suppress(OSError):
                for line in exclude.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)

        return PathSpec.from_lines("gitwildmatch", patterns)

    def is_ignored(self, relative_path: str) -> bool:
        """Check if a file path is ignored."""
        return self._spec.match_file(relative_path)

    def is_dir_ignored(self, relative_dir: str) -> bool:
        """Check if a directory is ignored."""
        return self._spec.match_file(relative_dir) or self._spec.match_file(f"{relative_dir}/")
