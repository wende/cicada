"""
File system watcher for automatic Elixir code reindexing.

This module provides the FileWatcher class which monitors Elixir source files
for changes and automatically triggers incremental reindexing.
"""

import logging
import signal
import sys
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from cicada.indexer import ElixirIndexer
from cicada.utils.storage import create_storage_dir

logger = logging.getLogger(__name__)


class ElixirFileEventHandler(FileSystemEventHandler):
    """
    Event handler for file system changes.

    Filters events to only process Elixir source files (.ex, .exs)
    and ignores changes in excluded directories.
    """

    def __init__(self, watcher: "FileWatcher"):
        """
        Initialize the event handler.

        Args:
            watcher: The FileWatcher instance to notify of changes
        """
        super().__init__()
        self.watcher = watcher
        self.excluded_dirs = {
            "deps",
            "_build",
            "node_modules",
            ".git",
            "assets",
            "priv",
        }

    def _is_elixir_file(self, path: str) -> bool:
        """Check if the path is an Elixir source file."""
        return path.endswith((".ex", ".exs"))

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is in an excluded directory."""
        path_parts = Path(path).parts
        return any(excluded in path_parts for excluded in self.excluded_dirs)

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        Handle file system events.

        Filters events to only process Elixir files not in excluded directories,
        then notifies the watcher to trigger reindexing.

        Args:
            event: The file system event
        """
        # Ignore directory events
        if event.is_directory:
            return

        # Convert src_path to string (it can be bytes or str)
        src_path = str(event.src_path)

        # Only process Elixir source files
        if not self._is_elixir_file(src_path):
            return

        # Skip excluded directories
        if self._is_excluded_path(src_path):
            return

        # Notify watcher of the change
        self.watcher._on_file_change(event)


class FileWatcher:
    """
    Watches Elixir source files and triggers automatic reindexing on changes.

    The watcher monitors .ex and .exs files in a repository, excluding
    standard directories like deps, _build, and node_modules. When changes
    are detected, it debounces the events and triggers incremental reindexing.
    """

    def __init__(
        self,
        repo_path: str,
        debounce_seconds: float = 2.0,
        verbose: bool = True,
        tier: str = "regular",
        register_signal_handlers: bool = True,
    ):
        """
        Initialize the file watcher.

        Args:
            repo_path: Path to the repository to watch
            debounce_seconds: Seconds to wait before triggering reindex after changes
            verbose: Whether to show detailed indexing progress
            tier: Indexing tier (fast, regular, or max)
            register_signal_handlers: Whether to register SIGINT/SIGTERM handlers (disable for testing)
        """
        self.repo_path = Path(repo_path).resolve()
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self.tier = tier

        self.observer: Observer | None = None  # type: ignore[valid-type]
        self.indexer: ElixirIndexer | None = None
        self.debounce_timer: threading.Timer | None = None
        self.timer_lock = threading.Lock()
        self.running = False
        self.shutdown_event = threading.Event()

        # Set up signal handlers for graceful shutdown (unless disabled for testing)
        if register_signal_handlers:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, _signum: int, _frame) -> None:
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        print("\n\nReceived interrupt signal. Stopping watcher...")
        self.shutdown_event.set()
        self.stop_watching()
        sys.exit(0)

    def start_watching(self) -> None:
        """
        Start watching for file changes.

        This method:
        1. Creates storage directory if needed
        2. Runs an initial index to ensure up-to-date state
        3. Starts the file system observer
        4. Blocks until interrupted (Ctrl-C)
        """
        if self.running:
            logger.warning("Watcher is already running")
            return

        print(f"Initializing watch mode for {self.repo_path}")
        print(f"Debounce interval: {self.debounce_seconds}s")
        print()

        # Ensure storage directory exists
        create_storage_dir(self.repo_path)

        # Get index path
        from cicada.utils.storage import get_index_path

        index_path = get_index_path(self.repo_path)

        # Create indexer instance
        self.indexer = ElixirIndexer(verbose=self.verbose)

        # Run initial index
        print("Running initial index...")
        try:
            self.indexer.incremental_index_repository(
                repo_path=str(self.repo_path),
                output_path=str(index_path),
                extract_keywords=True,
                force_full=False,
            )
            print("\nInitial indexing complete!")
            print()
        except KeyboardInterrupt:
            print("\n\nInitial indexing interrupted. Exiting...")
            return
        except Exception as e:
            # Check if an index already exists
            if index_path.exists():
                print("\n" + "=" * 70)
                print("WARNING: Initial indexing failed!")
                print("=" * 70)
                print(f"Error: {e}")
                print("\nAn existing index was found, so watch mode will continue.")
                print("However, the index may be outdated. Consider running:")
                print(f"  cicada index {self.repo_path}")
                print("=" * 70)
                print()
                logger.exception("Initial indexing failed")
            else:
                print("\n" + "=" * 70)
                print("ERROR: Initial indexing failed and no existing index found!")
                print("=" * 70)
                print(f"Error: {e}")
                print("\nWatch mode cannot start without an index.")
                print("Please fix the error and try again, or run:")
                print(f"  cicada index {self.repo_path}")
                print("=" * 70)
                logger.exception("Initial indexing failed")
                sys.exit(1)

        # Set up file system observer
        event_handler = ElixirFileEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.repo_path), recursive=True)

        # Start observing
        self.observer.start()
        self.running = True

        print("=" * 70)
        print("Watching for changes to Elixir files (.ex, .exs)")
        print("=" * 70)
        print("Press Ctrl-C to stop")
        print()

        # Block until interrupted
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping watcher...")
        finally:
            self.stop_watching()

    def stop_watching(self) -> None:
        """Stop watching for file changes and clean up resources."""
        if not self.running:
            return

        self.running = False

        # Cancel pending debounce timer
        with self.timer_lock:
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()
                self.debounce_timer = None

        # Stop observer
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        print("Watcher stopped.")

    def _on_file_change(self, event: FileSystemEvent) -> None:
        """
        Handle file change events with debouncing.

        When a file changes, this method cancels any pending reindex timer
        and starts a new one. This ensures that rapid successive changes
        only trigger a single reindex operation.

        Args:
            event: The file system event
        """
        with self.timer_lock:
            # Cancel existing timer
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()

            # Start new timer (daemon thread won't prevent process exit)
            self.debounce_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_reindex,
            )
            self.debounce_timer.daemon = True
            self.debounce_timer.start()

    def _trigger_reindex(self) -> None:
        """
        Trigger incremental reindexing.

        This method is called after the debounce period has elapsed.
        It runs the incremental indexer and handles any errors gracefully.
        """
        with self.timer_lock:
            self.debounce_timer = None

        print("\n" + "=" * 70)
        print("File changes detected - reindexing...")
        print("=" * 70)
        print()

        try:
            if self.indexer is not None:
                from cicada.utils.storage import get_index_path

                index_path = get_index_path(self.repo_path)
                self.indexer.incremental_index_repository(
                    repo_path=str(self.repo_path),
                    output_path=str(index_path),
                    extract_keywords=True,
                    force_full=False,
                )
                print()
                print("=" * 70)
                print("Reindexing complete!")
                print("=" * 70)
                print()
        except Exception as e:
            print()
            print("=" * 70)
            print(f"Error during reindexing: {e}")
            print("=" * 70)
            print("Continuing to watch for changes...")
            print()
            logger.exception("Reindexing failed")
