"""
Index Management for Cicada MCP Server.

Handles loading, reloading, and managing the code index and PR index.
"""

import json
import os
import random
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from cicada.languages.generic.indexer import run_generic_indexing_for_language_indexer
from cicada.utils import get_pr_index_path, load_index

# Type hint for IndexManager is forward-referenced with string annotation below


class BackgroundRefreshManager:
    """
    Manages background index refreshing with debouncing.

    This class handles automatic index refreshing when source files change.
    It provides:
    - Debouncing to coalesce rapid file changes
    - Minimum refresh interval (cooldown) to prevent excessive refreshes
    - Thread-safe background execution
    - Graceful shutdown support
    """

    DEBOUNCE_SECONDS = 2.0  # Wait for rapid edits to settle
    MIN_REFRESH_INTERVAL = 15.0  # Cooldown between refreshes (user choice)

    def __init__(
        self,
        index_manager: "IndexManager",
        repo_path: Path,
        index_path: Path,
        config: dict[str, Any],
        on_refresh_complete: Callable[[], None] | None = None,
    ):
        """
        Initialize the background refresh manager.

        Args:
            index_manager: The IndexManager instance to refresh
            repo_path: Path to the repository
            index_path: Path to the index file
            config: Configuration dictionary
            on_refresh_complete: Optional callback when refresh completes
        """
        self.index_manager = index_manager
        self.repo_path = repo_path
        self.index_path = index_path
        self.config = config
        self.on_refresh_complete = on_refresh_complete

        self._refresh_in_progress = False
        self._refresh_lock = threading.Lock()
        self._last_refresh_time = 0.0
        self._pending_refresh = False
        self._debounce_timer: threading.Timer | None = None
        self._stopped = False

    def request_refresh_if_stale(self) -> bool:
        """
        Check if refresh needed and schedule if so. Non-blocking.

        Returns:
            True if a refresh was scheduled, False otherwise
        """
        # Acquire lock to safely read shared state
        with self._refresh_lock:
            if self._stopped:
                return False

            if self._refresh_in_progress:
                return False

            now = time.time()
            if now - self._last_refresh_time < self.MIN_REFRESH_INTERVAL:
                return False

        # Staleness check doesn't need lock (reads from index_manager)
        staleness = self.index_manager.check_staleness()
        if not staleness or not staleness.get("is_stale"):
            return False

        self._schedule_refresh()
        return True

    def _schedule_refresh(self) -> None:
        """Schedule a debounced refresh."""
        with self._refresh_lock:
            if self._stopped:
                return
            if self._debounce_timer:
                self._debounce_timer.cancel()

            self._debounce_timer = threading.Timer(
                self.DEBOUNCE_SECONDS,
                self._execute_refresh,
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _execute_refresh(self) -> None:
        """Execute the actual refresh in background."""
        with self._refresh_lock:
            if self._stopped:
                return
            if self._refresh_in_progress:
                self._pending_refresh = True
                return
            self._refresh_in_progress = True

        try:
            self._run_incremental_index()
            self._last_refresh_time = time.time()

            if self.on_refresh_complete:
                self.on_refresh_complete()
        except Exception as e:
            print(f"Background refresh failed: {e}", file=sys.stderr)
        finally:
            with self._refresh_lock:
                self._refresh_in_progress = False
                if self._pending_refresh and not self._stopped:
                    self._pending_refresh = False
                    self._schedule_refresh()

    def _run_incremental_index(self) -> None:
        """Run incremental indexing."""
        from cicada.languages import LanguageRegistry
        from cicada.setup import detect_project_language

        language = detect_project_language(self.repo_path)
        # Cast to Any - concrete indexers have methods not in BaseIndexer
        indexer: Any = cast(Any, LanguageRegistry.get_indexer(language))

        indexer.incremental_index_repository(
            repo_path=str(self.repo_path),
            output_path=str(self.index_path),
            extract_keywords=True,
            extract_string_keywords=True,
            force_full=False,
            verbose=False,
        )
        run_generic_indexing_for_language_indexer(
            indexer,
            self.repo_path,
            self.index_path,
            verbose=False,
        )

    def force_refresh(self, force_full: bool = False) -> dict[str, Any]:
        """
        Force an immediate refresh (synchronous).

        This bypasses debouncing and cooldown. Used by the refresh_index tool.

        Args:
            force_full: If True, force a full reindex instead of incremental

        Returns:
            Dictionary with refresh status and stats
        """
        # Thread-safe: check and acquire refresh lock
        with self._refresh_lock:
            if self._refresh_in_progress:
                return {
                    "success": False,
                    "error": "A refresh is already in progress. Please try again shortly.",
                    "elapsed_seconds": 0,
                }
            self._refresh_in_progress = True

        try:
            from cicada.languages import LanguageRegistry
            from cicada.setup import detect_project_language

            start_time = time.time()

            try:
                language = detect_project_language(self.repo_path)
                # Cast to Any - concrete indexers have methods not in BaseIndexer
                indexer: Any = cast(Any, LanguageRegistry.get_indexer(language))

                if force_full:
                    result = indexer.index_repository(
                        repo_path=str(self.repo_path),
                        output_path=str(self.index_path),
                        extract_keywords=True,
                        extract_string_keywords=True,
                        verbose=False,
                    )
                else:
                    result = indexer.incremental_index_repository(
                        repo_path=str(self.repo_path),
                        output_path=str(self.index_path),
                        extract_keywords=True,
                        extract_string_keywords=True,
                        force_full=False,
                        verbose=False,
                    )

                generic_result = run_generic_indexing_for_language_indexer(
                    indexer,
                    self.repo_path,
                    self.index_path,
                    verbose=False,
                )

                elapsed = time.time() - start_time
                with self._refresh_lock:
                    self._last_refresh_time = time.time()

                # Extract stats from result
                metadata = {}
                if generic_result and generic_result.get("metadata"):
                    metadata = generic_result["metadata"]
                elif result and result.get("metadata"):
                    metadata = result["metadata"]
                return {
                    "success": True,
                    "elapsed_seconds": round(elapsed, 2),
                    "total_modules": metadata.get("total_modules", 0),
                    "total_functions": metadata.get("total_functions", 0),
                    "mode": "full" if force_full else "incremental",
                }
            except Exception as e:
                elapsed = time.time() - start_time
                return {
                    "success": False,
                    "error": str(e),
                    "elapsed_seconds": round(elapsed, 2),
                }
        finally:
            with self._refresh_lock:
                self._refresh_in_progress = False

    def stop(self) -> None:
        """Stop any pending refresh operations."""
        with self._refresh_lock:
            self._stopped = True
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None


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

        # Initialize background refresh manager
        repo_path = Path(self.config.get("repository", {}).get("path", "."))
        index_path = self._get_index_path()

        self._refresh_manager = BackgroundRefreshManager(
            index_manager=self,
            repo_path=repo_path,
            index_path=index_path,
            config=config,
            on_refresh_complete=self._on_background_refresh_complete,
        )

    def _get_index_path(self) -> Path:
        """Get the index file path from config."""
        if "storage" in self.config and "index_path" in self.config["storage"]:
            return Path(self.config["storage"]["index_path"])
        repo_path = Path(self.config.get("repository", {}).get("path", "."))
        from cicada.utils.storage import get_index_path

        return get_index_path(repo_path)

    def _on_background_refresh_complete(self) -> None:
        """Callback when background refresh completes.

        The reload_if_changed() method will pick up the new mtime
        on the next tool call, so nothing special needed here.
        """

    def request_background_refresh_if_stale(self) -> bool:
        """
        Request background refresh if stale. Non-blocking.

        Returns:
            True if a refresh was scheduled, False otherwise
        """
        return self._refresh_manager.request_refresh_if_stale()

    def force_refresh(self, force_full: bool = False) -> dict[str, Any]:
        """
        Force an immediate index refresh (synchronous).

        Args:
            force_full: If True, force a full reindex instead of incremental

        Returns:
            Dictionary with refresh status and stats
        """
        result = self._refresh_manager.force_refresh(force_full)
        # Reload the index after forced refresh
        if result.get("success"):
            self.reload_if_changed()
        return result

    def stop_background_refresh(self) -> None:
        """Stop any pending background refresh operations."""
        self._refresh_manager.stop()

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
            self._pr_index = load_index(
                pr_index_path, verbose=True, raise_on_error=False, index_name="PR index"
            )
        return self._pr_index

    @property
    def has_keywords(self) -> bool:
        """Check if keywords are available in the index."""
        return self._has_keywords

    @property
    def repo_path(self) -> Path:
        """Get the repository path from config."""
        return Path(self.config.get("repository", {}).get("path", "."))

    @property
    def indexing_mode(self) -> str:
        """Get the configured indexing mode."""
        from cicada.index_mode import read_indexing_mode_config

        return read_indexing_mode_config(self.repo_path)

    @property
    def has_embeddings(self) -> bool:
        """Check if embeddings are available for this repository."""
        from cicada.utils.storage import get_embeddings_path

        embeddings_path = get_embeddings_path(self.repo_path)
        return embeddings_path.exists()

    def _load_index(self) -> dict[str, Any]:
        """Load the index from JSON file."""
        # Get repo path from config
        repo_path = Path(self.config.get("repository", {}).get("path", "."))

        # Use centralized storage (or fall back to config if specified)
        if "storage" in self.config and "index_path" in self.config["storage"]:
            index_path = Path(self.config["storage"]["index_path"])
        else:
            from cicada.utils.storage import get_index_path

            index_path = get_index_path(repo_path)

        try:
            result = load_index(index_path, raise_on_error=True)
            if result is None:
                raise FileNotFoundError(
                    f"Index file not found: {index_path}\n\n{self.SETUP_INSTRUCTIONS}"
                )
            return result
        except json.JSONDecodeError as e:
            # Index file is corrupted - provide helpful message
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
        newest_mtime = 0.0
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
