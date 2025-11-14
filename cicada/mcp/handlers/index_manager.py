"""
Index Management for Cicada MCP Server.

Handles loading, reloading, and managing the code index and PR index.
"""

import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from cicada.utils import get_pr_index_path, load_index


class IndexManager:
    """Manages the code index and PR index with caching and reloading."""

    SETUP_INSTRUCTIONS = (
        "Please run setup first:\n"
        "  cicada cursor  # For Cursor\n"
        "  cicada claude  # For Claude Code\n"
        "  cicada vs      # For VS Code"
    )

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the index manager.

        Args:
            config: Configuration dictionary containing storage paths
        """
        self.config = config
        self._index = self._load_index()
        self._index_mtime = self._get_index_mtime()
        self._pr_index: dict | None = None  # Lazy load PR index
        self._has_keywords = self._check_keywords_available()

    @property
    def index(self) -> dict[str, Any]:
        """Get the code index."""
        return self._index

    @property
    def pr_index(self) -> dict[str, Any] | None:
        """Lazy load the PR index from JSON file."""
        if self._pr_index is None:
            # Get repo path from config
            repo_path = Path(self.config.get("repository", {}).get("path", "."))

            # Use new storage structure only
            pr_index_path = get_pr_index_path(repo_path)
            self._pr_index = load_index(pr_index_path, verbose=True, raise_on_error=False)
        return self._pr_index

    @property
    def has_keywords(self) -> bool:
        """Check if keywords are available in the index."""
        return self._has_keywords

    def _load_index(self) -> dict[str, Any]:
        """Load the index from JSON file."""
        index_path = Path(self.config["storage"]["index_path"])

        try:
            result = load_index(index_path, raise_on_error=True)
            if result is None:
                raise FileNotFoundError(
                    f"Index file not found: {index_path}\n\n{self.SETUP_INSTRUCTIONS}"
                )
            return result
        except json.JSONDecodeError as e:
            # Index file is corrupted - provide helpful message
            repo_path = self.config.get("repository", {}).get("path", ".")
            raise RuntimeError(
                f"Index file is corrupted: {index_path}\n"
                f"Error: {e}\n\n"
                f"To rebuild the index, run:\n"
                f"  cd {repo_path}\n"
                f"  cicada clean -f  # Safer cleanup\n"
                f"  cicada cursor  # or: cicada claude, cicada vs\n"
            ) from e
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Index file not found: {index_path}\n\n{self.SETUP_INSTRUCTIONS}"
            ) from None

    def _check_keywords_available(self) -> bool:
        """
        Check if any keywords are available in the index.

        This is cached at initialization to avoid repeated checks.
        Checks for both documentation keywords and string keywords.

        Returns:
            True if keywords or string_keywords are available in the index
        """
        for module_data in self._index.get("modules", {}).values():
            if module_data.get("keywords") or module_data.get("string_keywords"):
                return True
            for func in module_data.get("functions", []):
                if func.get("keywords") or func.get("string_keywords"):
                    return True
        return False

    def _get_index_mtime(self) -> float | None:
        """Get index file modification time."""
        try:
            index_path = Path(self.config["storage"]["index_path"])
            return index_path.stat().st_mtime if index_path.exists() else None
        except (OSError, KeyError):
            return None

    def reload_if_changed(self):
        """Reload index if file has been modified."""
        current_mtime = self._get_index_mtime()
        if current_mtime and current_mtime != self._index_mtime:
            try:
                new_index = self._load_index()
                # Only update if reload succeeded (no corruption/incomplete write)
                self._index = new_index
                self._has_keywords = self._check_keywords_available()
                self._index_mtime = current_mtime
                self._pr_index = None  # Invalidate PR index cache as well
            except (json.JSONDecodeError, FileNotFoundError, RuntimeError):
                # Index file is being written or corrupted - keep serving old index
                pass

    def _get_files_to_check(self, modules: list) -> list:
        """Sample modules to check for staleness."""
        max_files_to_check = 50
        if len(modules) > max_files_to_check:
            return random.sample(modules, max_files_to_check)
        return modules

    def _get_newest_file_mtime(self, modules_to_check: list, repo_path: Path) -> float:
        """Get the newest modification time among sampled files."""
        newest_mtime = 0
        for module_data in modules_to_check:
            file_path = repo_path / module_data["file"]
            if file_path.exists():
                file_mtime = os.path.getmtime(file_path)
                newest_mtime = max(newest_mtime, file_mtime)
        return newest_mtime

    def _format_age_string(self, age_seconds: float) -> str:
        """Format age in human-readable format."""
        hours_old = age_seconds / 3600
        if hours_old < 1:
            return f"{int(age_seconds / 60)} minutes"
        elif hours_old < 24:
            return f"{int(hours_old)} hours"
        return f"{int(hours_old / 24)} days"

    def check_staleness(self) -> dict[str, Any] | None:
        """
        Check if the index is stale by comparing file modification times.

        Returns:
            Dictionary with staleness info (is_stale, age_str) or None
        """
        try:
            index_path = Path(self.config["storage"]["index_path"])
            if not index_path.exists():
                return None

            index_mtime = os.path.getmtime(index_path)
            index_age = datetime.now().timestamp() - index_mtime
            repo_path = Path(self.config.get("repository", {}).get("path", "."))

            all_modules = list(self._index.get("modules", {}).values())
            modules_to_check = self._get_files_to_check(all_modules)
            newest_file_mtime = self._get_newest_file_mtime(modules_to_check, repo_path)

            if newest_file_mtime <= index_mtime:
                return None

            age_str = self._format_age_string(index_age)
            return {"is_stale": True, "age_str": age_str}

        except (OSError, KeyError):
            # Expected errors - file permissions, disk issues, config issues
            # Silently ignore these as staleness check is non-critical
            return None
        except Exception as e:
            # Unexpected error - log for debugging but don't break functionality
            print(f"Warning: Unexpected error checking index staleness: {e}", file=sys.stderr)
            return None
