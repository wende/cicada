"""
File system watcher for automatic code reindexing.

This module provides the FileWatcher class which monitors source files
for changes and automatically triggers incremental reindexing.
Supports multiple languages through the LanguageRegistry.
"""

import json
import logging
import signal
import sys
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from cicada.languages import LanguageRegistry
from cicada.languages.generic.indexer import run_generic_indexing_for_language_indexer
from cicada.parsing.base_indexer import BaseIndexer
from cicada.setup import detect_project_language
from cicada.utils.storage import create_storage_dir

logger = logging.getLogger(__name__)


class SourceFileEventHandler(FileSystemEventHandler):
    """
    Event handler for file system changes.

    Filters events to only process source files for the detected language
    and ignores changes in excluded directories.
    """

    def __init__(
        self, watcher: "FileWatcher", file_extensions: list[str], excluded_dirs: list[str]
    ):
        """
        Initialize the event handler.

        Args:
            watcher: The FileWatcher instance to notify of changes
            file_extensions: List of file extensions to watch (e.g., ['.py'], ['.ex', '.exs'])
            excluded_dirs: List of directory names to exclude
        """
        super().__init__()
        self.watcher = watcher
        self.file_extensions = tuple(file_extensions)
        self.excluded_dirs = set(excluded_dirs)

    def _is_source_file(self, path: str) -> bool:
        """Check if the path is a source file for the configured language."""
        return path.endswith(self.file_extensions)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is in an excluded directory."""
        path_parts = Path(path).parts
        return any(excluded in path_parts for excluded in self.excluded_dirs)

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        Handle file system events.

        Filters events to only process source files not in excluded directories,
        then notifies the watcher to trigger reindexing.

        Args:
            event: The file system event
        """
        # Ignore directory events
        if event.is_directory:
            return

        # Convert src_path to string (it can be bytes or str)
        src_path = str(event.src_path)

        # Only process source files for the configured language
        if not self._is_source_file(src_path):
            return

        # Skip excluded directories
        if self._is_excluded_path(src_path):
            return

        # Notify watcher of the change
        self.watcher._on_file_change(event)


class FileWatcher:
    """
    Watches source files and triggers automatic reindexing on changes.

    The watcher detects the project language and monitors appropriate source files,
    excluding language-specific directories. When changes are detected, it debounces
    the events and triggers incremental reindexing.
    """

    def __init__(
        self,
        repo_path: str,
        debounce_seconds: float = 2.0,
        verbose: bool = True,
        indexing_mode: str = "keywords",
        register_signal_handlers: bool = True,
    ):
        """
        Initialize the file watcher.

        Args:
            repo_path: Path to the repository to watch
            debounce_seconds: Seconds to wait before triggering reindex after changes
            verbose: Whether to show detailed indexing progress
        indexing_mode: Indexing mode ("keywords" or "embeddings")
            register_signal_handlers: Whether to register SIGINT/SIGTERM handlers (disable for testing)
        """
        self.repo_path = Path(repo_path).resolve()
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self.indexing_mode = indexing_mode

        # Detect project language and get appropriate indexer
        self.language = detect_project_language(self.repo_path)
        self.indexer: BaseIndexer | None = None
        self.file_extensions: list[str] = []
        self.excluded_dirs: list[str] = []

        self.observer: Observer | None = None  # type: ignore[valid-type]
        self.debounce_timer: threading.Timer | None = None
        self.timer_lock = threading.Lock()
        self._reindex_lock = threading.Lock()  # Prevent concurrent reindexing
        self._pending_lock = threading.Lock()  # Protect _pending_reindex flag
        self._pending_reindex = False  # Track if reindex needed after current one completes
        self.running = False
        self.shutdown_event = threading.Event()
        self._consecutive_failures = 0  # Track consecutive reindex failures

        # Set up signal handlers for graceful shutdown (unless disabled for testing)
        if register_signal_handlers:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, _frame) -> None:
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal")
        print(f"\n\nReceived {signal_name} signal. Stopping watcher...")

        self.shutdown_event.set()

        try:
            self.stop_watching()
        except Exception as e:
            logger.exception(f"Error during signal handler cleanup: {e}")
            print(f"Warning: Error during cleanup: {e}", file=sys.stderr)
            # Still exit even if cleanup fails
        finally:
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

        if self.verbose:
            print(f"Initializing watch mode for {self.repo_path}")
            print(f"Detected language: {self.language}")
            print(f"Debounce interval: {self.debounce_seconds}s")
            print()

        # Ensure storage directory exists
        create_storage_dir(self.repo_path)

        # Get index path
        from cicada.utils.storage import get_index_path

        index_path = get_index_path(self.repo_path)

        # Create language-specific indexer instance
        self.indexer = LanguageRegistry.get_indexer(self.language)
        self.indexer.verbose = self.verbose
        self.file_extensions = self.indexer.get_file_extensions()
        self.excluded_dirs = self.indexer.get_excluded_dirs()

        # Run initial index
        if self.verbose:
            print("Running initial index...")
        try:
            self._run_indexer(index_path)

            # Generate embeddings if in embeddings mode
            if self.indexing_mode == "embeddings":
                self._regenerate_embeddings(index_path)

            if self.verbose:
                print("\nInitial indexing complete!")
                print()
        except KeyboardInterrupt:
            print("\n\nInitial indexing interrupted. Exiting...")
            return
        except (MemoryError, OSError) as e:
            # System-level failures - don't continue regardless of existing index
            print("\n" + "=" * 70)
            print("CRITICAL: System error during initial indexing!")
            print("=" * 70)
            print(f"Error: {e}")
            print("\nWatch mode cannot start due to system-level failure.")
            if isinstance(e, MemoryError):
                print("Your system is out of memory. Close other applications and try again.")
            elif isinstance(e, OSError):
                print(f"File system error: {e}")
                print("Check disk space, permissions, and filesystem health.")
            print("=" * 70)
            logger.critical(f"System error during initial indexing: {e}", exc_info=True)
            sys.exit(1)
        except Exception as e:
            # Other failures - check if we can use existing index
            logger.exception("Initial indexing failed")
            self._handle_initial_index_failure(e, index_path)

        # Set up file system observer with language-specific extensions
        event_handler = SourceFileEventHandler(self, self.file_extensions, self.excluded_dirs)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.repo_path), recursive=True)

        # Start observing
        self.observer.start()
        self.running = True

        # Format extensions for display
        extensions_str = ", ".join(self.file_extensions)
        print()
        print("=" * 70)
        print(f"Watching for changes to {self.language.capitalize()} files ({extensions_str})")
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
                try:
                    self.debounce_timer.cancel()
                    # Note: cancel() only prevents future execution,
                    # callback might still be running
                    logger.debug("Cancelled pending debounce timer")
                except Exception as e:
                    logger.warning(f"Error cancelling timer: {e}")
                finally:
                    self.debounce_timer = None

        # Stop observer
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)

            if self.observer.is_alive():
                logger.warning("Observer thread did not stop within timeout")
                print("Warning: File watcher thread did not stop cleanly", file=sys.stderr)
                # Still clear reference to allow GC, but log the issue

            self.observer = None

        print("Watcher stopped.")

    def _handle_initial_index_failure(self, error: Exception, index_path: Path) -> None:
        """Handle failure during initial indexing.

        Args:
            error: The exception that occurred
            index_path: Path to the index file

        Raises:
            SystemExit: If watch mode cannot continue
        """
        if not index_path.exists():
            # No existing index - must exit
            print("\n" + "=" * 70)
            print("ERROR: Initial indexing failed and no existing index found!")
            print("=" * 70)
            print(f"Error: {error}")
            print("\nWatch mode cannot start without an index.")
            print("Please fix the error and try again, or run:")
            print(f"  cicada index {self.repo_path}")
            print("=" * 70)
            sys.exit(1)

        # Try to load existing index to verify it's usable
        try:
            with open(index_path) as f:
                index = json.load(f)
            if not index or not index.get("modules"):
                raise ValueError("Existing index is empty or corrupted")

            # Existing index appears valid
            print("\n" + "=" * 70)
            print("WARNING: Initial indexing failed!")
            print("=" * 70)
            print(f"Error: {error}")
            print("\nAn existing index was found and verified as usable.")
            print("Watch mode will continue, but the index may be outdated.")
            print("\nTo fix this issue, run:")
            print(f"  cicada clean && cicada index {self.repo_path}")
            print("=" * 70)
            print()
        except Exception as load_error:
            # Existing index is corrupted or unusable
            print("\n" + "=" * 70)
            print("ERROR: Initial indexing failed and existing index is corrupted!")
            print("=" * 70)
            print(f"Indexing error: {error}")
            print(f"Index validation error: {load_error}")
            print("\nCannot start watch mode. Please fix the issue:")
            print(f"  cicada clean && cicada index {self.repo_path}")
            print("=" * 70)
            logger.error(f"Existing index corrupted: {load_error}")
            sys.exit(1)

    def _run_indexer(self, index_path: Path) -> None:
        """Run the appropriate indexing process (incremental or full).

        Uses the indexer's supports_incremental flag to determine which
        method to call. Falls back to basic indexing if incremental is
        not supported.

        Args:
            index_path: Path to the index file
        """
        if self.indexer is None:
            return

        # Use incremental indexing if supported, otherwise fall back to basic
        if self.indexer.supports_incremental:
            self.indexer.incremental_index_repository(
                repo_path=str(self.repo_path),
                output_path=str(index_path),
                extract_keywords=True,
                force_full=False,
            )
        else:
            self.indexer.index_repository(
                repo_path=str(self.repo_path),
                output_path=str(index_path),
                force=False,
                verbose=self.verbose,
            )

        run_generic_indexing_for_language_indexer(
            self.indexer,
            self.repo_path,
            index_path,
            verbose=self.verbose,
        )

    def _regenerate_embeddings(self, index_path: Path) -> None:
        """Regenerate embeddings from the updated index.

        Args:
            index_path: Path to the index file
        """
        try:
            # Load the updated index
            with open(index_path) as f:
                index = json.load(f)

            if not index or not index.get("modules"):
                if self.verbose:
                    print("Skipping embeddings: no modules in index")
                return

            if self.verbose:
                print("\nRegenerating embeddings for semantic search...")

            from cicada.embeddings.indexer import EmbeddingsIndexer

            # Force=True to regenerate embeddings from scratch
            embeddings_indexer = EmbeddingsIndexer(self.repo_path, verbose=self.verbose, force=True)
            embeddings_indexer.index_from_parsed_data(index)

            if self.verbose:
                print("Embeddings regenerated successfully.")

        except ImportError as e:
            if self.verbose:
                print(f"Skipping embeddings: cicada-vector not available ({e})")
        except Exception as e:
            # Don't fail the whole reindex if embeddings fail
            logger.warning(f"Failed to regenerate embeddings: {e}")
            if self.verbose:
                print(f"Warning: Failed to regenerate embeddings: {e}")
                print("Keyword index was updated successfully.")

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
            self._cancel_pending_timer()
            self._start_new_timer()

    def _cancel_pending_timer(self) -> None:
        """Cancel any pending debounce timer."""
        if self.debounce_timer is None:
            return

        try:
            self.debounce_timer.cancel()
            logger.debug("Cancelled previous debounce timer due to new file change")
        except Exception as e:
            logger.warning(f"Error cancelling previous timer: {e}")

    def _start_new_timer(self) -> None:
        """Start a new debounce timer."""
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

        Uses a reindex lock to prevent concurrent indexing. If a reindex is
        already in progress, we mark that another reindex is needed and return.
        When the current reindex completes, it will check for pending reindex
        and run again if needed.
        """
        with self.timer_lock:
            self.debounce_timer = None

        # Try to acquire reindex lock without blocking
        acquired = self._reindex_lock.acquire(blocking=False)
        if not acquired:
            # Another reindex is already in progress - mark that we need to reindex later
            with self._pending_lock:
                self._pending_reindex = True
            if self.verbose:
                logger.debug("Reindex already in progress, will reindex again when complete")
            return

        try:
            # Clear pending flag since we're about to reindex
            with self._pending_lock:
                self._pending_reindex = False

            self._perform_reindex()

            # Check if another reindex is needed (file changes during current reindex)
            while True:
                with self._pending_lock:
                    if not self._pending_reindex:
                        break
                    self._pending_reindex = False

                if self.verbose:
                    print("\n" + "=" * 70)
                    print("Additional changes detected during reindex - reindexing again...")
                    print("=" * 70)
                    print()
                self._perform_reindex()

        finally:
            self._reindex_lock.release()

    def _perform_reindex(self) -> None:
        """
        Perform the actual reindexing operation.

        This method handles the indexer invocation and error handling.
        It should only be called while holding the _reindex_lock.
        """
        if self.verbose:
            print("\n" + "=" * 70)
            print("File changes detected - reindexing...")
            print("=" * 70)
            print()

        try:
            if self.indexer is not None:
                from cicada.utils.storage import get_index_path

                index_path = get_index_path(self.repo_path)
                self._run_indexer(index_path)

                # Regenerate embeddings if in embeddings mode
                if self.indexing_mode == "embeddings":
                    self._regenerate_embeddings(index_path)

                if self.verbose:
                    print()
                    print("=" * 70)
                    print("Reindexing complete!")
                    print("=" * 70)
                    print()

                # Reset failure counter on success
                self._consecutive_failures = 0

        except KeyboardInterrupt:
            # Don't catch interrupts - let them propagate
            print("\n\nReindexing interrupted.")
            raise

        except (MemoryError, OSError) as e:
            # System-level errors - warn but continue (might be transient)
            print()
            print("=" * 70)
            print(f"SYSTEM ERROR during reindexing: {e}")
            print("=" * 70)
            if isinstance(e, MemoryError):
                print("Your system is out of memory.")
            elif isinstance(e, OSError):
                print(f"File system error: {e}")
            print("\nWatcher will continue, but next reindex may also fail.")
            print("If this persists, stop the watcher and check system resources.")
            print("=" * 70)
            print()
            logger.error(f"System error during reindex: {e}", exc_info=True)

        except Exception as e:
            # Unexpected errors - track consecutive failures
            print()
            print("=" * 70)
            print(f"ERROR during reindexing: {e}")
            print("=" * 70)
            print("Continuing to watch for changes...")
            print()
            logger.exception("Reindexing failed")

            # Track consecutive failures
            self._consecutive_failures += 1

            if self._consecutive_failures >= 3:
                print("=" * 70)
                print("WARNING: Reindexing has failed 3 consecutive times!")
                print("=" * 70)
                print("The watcher may be broken. Consider stopping it and investigating.")
                print("Check logs for details. You may need to run:")
                print(f"  cicada clean && cicada index {self.repo_path}")
                print("=" * 70)
                logger.error("Multiple consecutive reindex failures detected")
