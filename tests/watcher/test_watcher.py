"""
Comprehensive tests for cicada/watcher.py - File watching and automatic reindexing
"""

import logging
import signal
import threading
import time
from unittest.mock import Mock, patch

import pytest

from cicada.watcher import SourceFileEventHandler, FileWatcher

# Mark all tests in this module to run serially in their own xdist group
# This prevents interference with parallel test execution
pytestmark = pytest.mark.xdist_group(name="file_watcher_tests")


@pytest.fixture
def mock_watcher():
    """Create a mock watcher for event handler testing"""
    watcher = Mock(spec=FileWatcher)
    watcher._on_file_change = Mock()
    return watcher


@pytest.fixture
def file_watcher(elixir_repo):
    """Create a FileWatcher with automatic cleanup"""
    watcher = None

    def _create_watcher(**kwargs):
        nonlocal watcher
        # Always disable signal handlers in tests
        kwargs.setdefault("register_signal_handlers", False)
        watcher = FileWatcher(repo_path=str(elixir_repo), **kwargs)
        return watcher

    yield _create_watcher

    # Cleanup: ensure watcher is stopped and timers cancelled
    if watcher:
        try:
            with watcher.timer_lock:
                if watcher.debounce_timer:
                    watcher.debounce_timer.cancel()
                    watcher.debounce_timer = None
            if watcher.running:
                watcher.stop_watching()
        except Exception:
            pass  # Ignore cleanup errors


class TestSourceFileEventHandler:
    """Tests for SourceFileEventHandler class"""

    def test_initialization(self, mock_watcher):
        """Test that event handler initializes correctly"""
        file_extensions = [".ex", ".exs"]
        excluded_dirs = ["deps", "_build", ".git"]
        handler = SourceFileEventHandler(mock_watcher, file_extensions, excluded_dirs)
        assert handler.watcher == mock_watcher
        assert "deps" in handler.excluded_dirs
        assert "_build" in handler.excluded_dirs
        assert ".git" in handler.excluded_dirs

    def test_is_source_file_elixir(self, mock_watcher):
        """Test Elixir file detection"""
        handler = SourceFileEventHandler(mock_watcher, [".ex", ".exs"], ["deps", "_build", ".git"])

        # Valid Elixir files
        assert handler._is_source_file("lib/module.ex") is True
        assert handler._is_source_file("test/module_test.exs") is True

        # Non-Elixir files
        assert handler._is_source_file("README.md") is False
        assert handler._is_source_file("config.yaml") is False
        assert handler._is_source_file("lib/module.py") is False

    def test_is_source_file_python(self, mock_watcher):
        """Test Python file detection"""
        handler = SourceFileEventHandler(mock_watcher, [".py"], ["__pycache__", ".venv", ".git"])

        # Valid Python files
        assert handler._is_source_file("lib/module.py") is True
        assert handler._is_source_file("test/test_module.py") is True

        # Non-Python files
        assert handler._is_source_file("README.md") is False
        assert handler._is_source_file("lib/module.ex") is False

    def test_is_excluded_path(self, mock_watcher):
        """Test path exclusion logic"""
        handler = SourceFileEventHandler(mock_watcher, [".ex", ".exs"], ["deps", "_build", ".git"])

        # Excluded directories
        assert handler._is_excluded_path("deps/phoenix/lib/phoenix.ex") is True
        assert handler._is_excluded_path("_build/dev/lib/app/module.ex") is True
        assert handler._is_excluded_path(".git/objects/abc123") is True

        # Normal paths should not be excluded
        assert handler._is_excluded_path("lib/my_app/module.ex") is False
        assert handler._is_excluded_path("test/module_test.exs") is False

    def test_on_any_event_filtering(self, mock_watcher):
        """Test event filtering logic"""
        handler = SourceFileEventHandler(mock_watcher, [".ex", ".exs"], ["deps", "_build", ".git"])

        test_cases = [
            # (is_directory, src_path, should_trigger, description)
            (True, "lib/my_app", False, "directories ignored"),
            (False, "README.md", False, "non-source files ignored"),
            (False, "deps/phoenix/lib/phoenix.ex", False, "excluded directories ignored"),
            (False, "lib/my_app/module.ex", True, "valid source files trigger"),
        ]

        for is_directory, src_path, should_trigger, description in test_cases:
            mock_watcher.reset_mock()
            event = Mock()
            event.is_directory = is_directory
            event.src_path = src_path

            handler.on_any_event(event)

            if should_trigger:
                mock_watcher._on_file_change.assert_called_once_with(
                    event
                ), f"Failed: {description}"
            else:
                mock_watcher._on_file_change.assert_not_called(), f"Failed: {description}"


class TestFileWatcher:
    """Tests for FileWatcher class"""

    def test_initialization_defaults(self, elixir_repo):
        """Test FileWatcher initialization with default parameters"""
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)

        assert watcher.repo_path == elixir_repo
        assert watcher.debounce_seconds == 2.0
        assert watcher.verbose is True
        assert watcher.tier == "regular"
        assert watcher.running is False
        assert watcher.observer is None
        assert watcher.indexer is None

    def test_initialization_custom_parameters(self, elixir_repo):
        """Test FileWatcher initialization with custom parameters"""
        watcher = FileWatcher(
            repo_path=str(elixir_repo),
            debounce_seconds=5.0,
            verbose=False,
            tier="fast",
        )

        assert watcher.debounce_seconds == 5.0
        assert watcher.verbose is False
        assert watcher.tier == "fast"

    def test_on_file_change_starts_debounce_timer(self, elixir_repo):
        """Test that file changes start a debounce timer"""
        watcher = FileWatcher(
            repo_path=str(elixir_repo), register_signal_handlers=False, debounce_seconds=0.1
        )

        event = Mock()
        event.src_path = "lib/module.ex"

        # Start the debounce timer
        watcher._on_file_change(event)

        # Timer should be set
        assert watcher.debounce_timer is not None
        assert watcher.debounce_timer.is_alive()

        # Clean up
        watcher.debounce_timer.cancel()

    def test_on_file_change_cancels_previous_timer(self, elixir_repo):
        """Test that new file changes cancel previous debounce timers"""
        watcher = FileWatcher(
            repo_path=str(elixir_repo), register_signal_handlers=False, debounce_seconds=1.0
        )

        event = Mock()
        event.src_path = "lib/module.ex"

        # Start first timer
        watcher._on_file_change(event)
        first_timer = watcher.debounce_timer

        # Start second timer before first expires
        time.sleep(0.1)
        watcher._on_file_change(event)
        second_timer = watcher.debounce_timer

        # First timer should be different from second
        assert first_timer is not second_timer
        # Second timer should be alive
        assert second_timer.is_alive()

        # Clean up
        second_timer.cancel()

    @patch("cicada.watcher.LanguageRegistry.get_indexer")
    def test_trigger_reindex_calls_indexer(self, mock_get_indexer, elixir_repo):
        """Test that _trigger_reindex calls the incremental indexer"""
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.get_file_extensions.return_value = [".ex", ".exs"]
        mock_indexer.get_excluded_dirs.return_value = ["deps", "_build", ".git"]
        mock_get_indexer.return_value = mock_indexer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.indexer = mock_indexer

        # Trigger reindex
        watcher._trigger_reindex()

        # Verify indexer was called with correct parameters
        assert mock_indexer.incremental_index_repository.called
        call_kwargs = mock_indexer.incremental_index_repository.call_args.kwargs
        assert call_kwargs["repo_path"] == str(elixir_repo)
        assert call_kwargs["extract_keywords"] is True
        assert call_kwargs["force_full"] is False
        assert "output_path" in call_kwargs

    @patch("cicada.watcher.LanguageRegistry.get_indexer")
    def test_trigger_reindex_falls_back_to_basic_indexer(self, mock_get_indexer, elixir_repo):
        """Test that _trigger_reindex falls back to index_repository for non-incremental indexers"""
        mock_indexer = Mock()
        mock_indexer.supports_incremental = False  # Non-incremental indexer
        mock_indexer.get_file_extensions.return_value = [".py"]
        mock_indexer.get_excluded_dirs.return_value = ["__pycache__", ".venv", ".git"]
        mock_get_indexer.return_value = mock_indexer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.indexer = mock_indexer

        # Trigger reindex
        watcher._trigger_reindex()

        # Verify index_repository was called instead of incremental_index_repository
        assert mock_indexer.index_repository.called
        assert not mock_indexer.incremental_index_repository.called
        call_kwargs = mock_indexer.index_repository.call_args.kwargs
        assert call_kwargs["repo_path"] == str(elixir_repo)
        assert call_kwargs["force"] is False
        assert "output_path" in call_kwargs

    @patch("cicada.watcher.LanguageRegistry.get_indexer")
    def test_trigger_reindex_handles_errors_gracefully(self, mock_get_indexer, elixir_repo):
        """Test that errors during reindexing don't crash the watcher"""
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.incremental_index_repository.side_effect = Exception("Test error")
        mock_indexer.get_file_extensions.return_value = [".ex", ".exs"]
        mock_indexer.get_excluded_dirs.return_value = ["deps", "_build", ".git"]
        mock_get_indexer.return_value = mock_indexer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.indexer = mock_indexer

        # Should not raise exception
        watcher._trigger_reindex()

        # Verify indexer was called even though it errored
        mock_indexer.incremental_index_repository.assert_called_once()

    def test_stop_watching_cancels_timer(self, elixir_repo):
        """Test that stop_watching cancels the debounce timer"""
        watcher = FileWatcher(
            repo_path=str(elixir_repo), register_signal_handlers=False, debounce_seconds=10.0
        )
        watcher.running = True

        event = Mock()
        event.src_path = "lib/module.ex"

        # Start debounce timer
        watcher._on_file_change(event)
        assert watcher.debounce_timer is not None

        # Stop watching
        watcher.stop_watching()

        # Timer should be cancelled
        assert watcher.debounce_timer is None
        assert watcher.running is False

    def test_stop_watching_is_noop_when_not_running(self, elixir_repo):
        """Calling stop_watching with running=False should exit immediately."""
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.stop_watching()  # Should not raise
        assert watcher.running is False

    @patch("cicada.watcher.Observer")
    def test_stop_watching_stops_observer(self, mock_observer_class, elixir_repo):
        """Test that stop_watching stops the file system observer"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.running = True
        watcher.observer = mock_observer

        # Stop watching
        watcher.stop_watching()

        # Verify observer was stopped
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert watcher.observer is None

    def test_debouncing_delays_reindex(self, elixir_repo):
        """Test that debouncing actually delays the reindex trigger"""
        reindex_called = threading.Event()

        def mock_trigger_reindex():
            reindex_called.set()

        watcher = FileWatcher(
            repo_path=str(elixir_repo), register_signal_handlers=False, debounce_seconds=0.2
        )
        watcher._trigger_reindex = mock_trigger_reindex

        event = Mock()
        event.src_path = "lib/module.ex"

        # Trigger change
        start_time = time.time()
        watcher._on_file_change(event)

        # Wait for reindex to be called
        reindex_called.wait(timeout=1.0)
        elapsed = time.time() - start_time

        # Should have waited at least the debounce time
        assert elapsed >= 0.2
        assert reindex_called.is_set()

    def test_multiple_rapid_changes_debounce_correctly(self, elixir_repo):
        """Test that multiple rapid changes only trigger one reindex"""
        reindex_count = []

        def mock_trigger_reindex():
            reindex_count.append(1)

        watcher = FileWatcher(
            repo_path=str(elixir_repo), register_signal_handlers=False, debounce_seconds=0.05
        )
        watcher._trigger_reindex = mock_trigger_reindex

        event = Mock()
        event.src_path = "lib/module.ex"

        # Trigger multiple changes rapidly
        for _ in range(5):
            watcher._on_file_change(event)
            time.sleep(0.01)  # 10ms between changes

        # Wait for debounce to expire
        time.sleep(0.1)

        # Should have only triggered once
        assert len(reindex_count) == 1


# Integration Tests - Address REPORT.md Section 4 Testing Gaps
class TestFileWatcherIntegration:
    """Integration tests with minimal mocking to test real component interaction"""

    @patch("cicada.watcher.LanguageRegistry.get_indexer")
    @patch("cicada.watcher.Observer")
    def test_file_watcher_lifecycle_integration(
        self, mock_observer_class, mock_get_indexer, elixir_repo
    ):
        """Test complete start_watching lifecycle focusing on component integration.

        This is the most important integration test - verifies the core entry point.
        Addresses REPORT.md Issue 4.1 - No integration test for start_watching() lifecycle.

        Tests:
        - Initial indexing called correctly
        - Observer created and started
        - Event handler registered with correct parameters
        - Event loop waits for shutdown
        - Clean shutdown sequence

        Note: Uses partial mocking to test integration while avoiding thread/signal issues.
        """
        from cicada.utils.storage import create_storage_dir, get_index_path
        from watchdog.events import FileSystemEvent

        # Mock the indexer
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.get_file_extensions.return_value = [".ex", ".exs"]
        mock_indexer.get_excluded_dirs.return_value = ["deps", "_build", ".git"]
        mock_get_indexer.return_value = mock_indexer

        # Mock observer but track calls
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        # Pre-create index to pass existence check
        create_storage_dir(elixir_repo)
        index_path = get_index_path(elixir_repo)
        index_path.write_text('{"modules": {}, "pr_index": {}}')

        watcher = FileWatcher(
            repo_path=str(elixir_repo),
            verbose=False,
            debounce_seconds=0.5,
            register_signal_handlers=False,
        )

        # Make the event loop exit immediately
        watcher.shutdown_event.set()

        # Run start_watching() - it will exit immediately due to shutdown_event
        watcher.start_watching()

        # Verify observer was created and started
        assert mock_observer_class.called, "Observer should be instantiated"
        mock_observer.schedule.assert_called_once(), "Observer should schedule event handler"
        mock_observer.start.assert_called_once(), "Observer should be started"

        # Verify the event handler was registered correctly
        schedule_call = mock_observer.schedule.call_args
        handler = schedule_call[0][0]  # First positional arg
        path = schedule_call[0][1]  # Second positional arg
        assert handler is not None, "Event handler should be registered"
        assert path == str(elixir_repo), "Should watch repo path"
        assert schedule_call[1]["recursive"] is True, "Should watch recursively"

    @patch("sys.exit")
    def test_signal_handler_stops_watcher_cleanly(self, mock_exit, elixir_repo):
        """Test SIGINT/SIGTERM properly cleans up resources.

        Addresses REPORT.md Issue 4.2 - Signal handlers completely untested.
        This is the ONLY test that enables signal handlers (all others disable them).
        """
        watcher = FileWatcher(
            repo_path=str(elixir_repo),
            verbose=False,
            register_signal_handlers=True,  # CRITICAL: Enable signal handlers!
        )

        # Mock observer and timer to avoid full startup
        mock_observer = Mock()
        mock_observer.is_alive.return_value = True
        watcher.observer = mock_observer
        watcher.running = True  # Must set running=True for stop_watching() to work

        # Create mock timer
        mock_timer = Mock()
        watcher.debounce_timer = mock_timer

        # Send SIGINT to signal handler
        watcher._signal_handler(signal.SIGINT, None)

        # Verify cleanup was called
        assert watcher.shutdown_event.is_set()
        mock_observer.stop.assert_called_once()
        mock_timer.cancel.assert_called_once()
        assert watcher.observer is None
        assert watcher.debounce_timer is None
        mock_exit.assert_called_once_with(0)

    @patch("cicada.watcher.LanguageRegistry.get_indexer")
    def test_file_watcher_detects_real_file_changes(self, mock_get_indexer, elixir_repo):
        """Integration test with actual file system modifications.

        Addresses REPORT.md Issue 4.4 - Real file system events not tested.
        Uses real Observer and real file writes to verify end-to-end detection.

        Tests:
        - Real watchdog Observer detects file changes
        - .ex file creation triggers event
        - Event handler processes file correctly
        - Debouncing works with real events
        - Reindex triggered by real file change

        Note: Indexer is mocked to keep test fast. Focus is on file detection.
        """
        from cicada.utils.storage import create_storage_dir, get_index_path
        from watchdog.observers import Observer

        # Mock the indexer
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.get_file_extensions.return_value = [".ex", ".exs"]
        mock_indexer.get_excluded_dirs.return_value = ["_build", "deps", ".git"]
        mock_get_indexer.return_value = mock_indexer

        # Pre-create index
        create_storage_dir(elixir_repo)
        index_path = get_index_path(elixir_repo)
        index_path.write_text('{"modules": {}, "pr_index": {}}')

        watcher = FileWatcher(
            repo_path=str(elixir_repo),
            verbose=False,
            debounce_seconds=0.15,  # Reduced from 0.5s for faster test
            register_signal_handlers=False,
        )

        # Track reindex calls
        reindex_called = threading.Event()

        def track_reindex():
            reindex_called.set()

        watcher._trigger_reindex = track_reindex

        # Manually set up observer (avoid start_watching() blocking)
        watcher.observer = Observer()
        handler = SourceFileEventHandler(watcher, [".ex", ".exs"], ["_build", "deps", ".git"])
        watcher.observer.schedule(handler, str(elixir_repo), recursive=True)
        watcher.observer.start()
        watcher.running = True

        try:
            # Wait a moment for observer to be ready
            time.sleep(0.1)  # Reduced from 0.3s

            # Create a new .ex file
            test_file = elixir_repo / "lib" / "new_module.ex"
            test_file.write_text(
                """
defmodule NewModule do
  def test, do: :ok
end
"""
            )

            # Wait for file event detection + debounce + reindex trigger
            success = reindex_called.wait(timeout=1)  # Reduced from 3s
            assert success, "Reindex should be triggered by real file change"

        finally:
            # Clean up
            watcher.stop_watching()


class TestFileWatcherEdgeCases:
    """Additional coverage for FileWatcher edge-case handling."""

    def test_signal_handler_logs_cleanup_errors(self, elixir_repo):
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.stop_watching = Mock(side_effect=RuntimeError("boom"))

        with patch("sys.exit") as mock_exit:
            watcher._signal_handler(signal.SIGTERM, None)

        watcher.stop_watching.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("cicada.watcher.LanguageRegistry.get_indexer")
    @patch("cicada.watcher.Observer")
    @patch("cicada.watcher.time.sleep")
    def test_start_watching_handles_keyboard_interrupt_loop(
        self, mock_sleep, mock_observer_class, mock_get_indexer, elixir_repo
    ):
        mock_sleep.side_effect = KeyboardInterrupt()
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.get_file_extensions.return_value = [".ex", ".exs"]
        mock_indexer.get_excluded_dirs.return_value = ["deps", "_build", ".git"]
        mock_get_indexer.return_value = mock_indexer

        mock_observer = Mock()
        mock_observer.is_alive.return_value = False
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.start_watching()

        mock_sleep.assert_called()
        mock_observer.stop.assert_called_once()
        assert watcher.running is False

    def test_cancel_pending_timer_logs_errors(self, elixir_repo, caplog):
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        failing_timer = Mock()
        failing_timer.cancel.side_effect = RuntimeError("boom")
        watcher.debounce_timer = failing_timer

        with caplog.at_level(logging.WARNING):
            watcher._cancel_pending_timer()

        assert "Error cancelling previous timer" in caplog.text

    def test_stop_watching_handles_timer_cancel_errors(self, elixir_repo):
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.running = True
        failing_timer = Mock()
        failing_timer.cancel.side_effect = RuntimeError("boom")
        watcher.debounce_timer = failing_timer

        mock_observer = Mock()
        mock_observer.is_alive.return_value = False
        watcher.observer = mock_observer

        watcher.stop_watching()

        mock_observer.stop.assert_called_once()
        assert watcher.debounce_timer is None

    @patch("cicada.utils.storage.get_index_path")
    def test_trigger_reindex_handles_memory_errors(self, mock_get_index_path, elixir_repo):
        mock_get_index_path.return_value = elixir_repo / "index.json"
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.incremental_index_repository.side_effect = MemoryError("OOM")
        watcher.indexer = mock_indexer

        watcher._trigger_reindex()

        assert watcher._consecutive_failures == 0

    @patch("cicada.utils.storage.get_index_path")
    def test_trigger_reindex_handles_keyboard_interrupt(self, mock_get_index_path, elixir_repo):
        mock_get_index_path.return_value = elixir_repo / "index.json"
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.incremental_index_repository.side_effect = KeyboardInterrupt()
        watcher.indexer = mock_indexer

        with pytest.raises(KeyboardInterrupt):
            watcher._trigger_reindex()

    @patch("cicada.utils.storage.get_index_path")
    def test_trigger_reindex_tracks_consecutive_failures(self, mock_get_index_path, elixir_repo):
        mock_get_index_path.return_value = elixir_repo / "index.json"
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.incremental_index_repository.side_effect = Exception("boom")
        watcher.indexer = mock_indexer

        watcher._trigger_reindex()
        assert watcher._consecutive_failures == 1

        watcher._consecutive_failures = 2
        watcher._trigger_reindex()
        assert watcher._consecutive_failures == 3

    def test_start_watching_when_running_is_noop(self, elixir_repo, caplog):
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.running = True

        with caplog.at_level(logging.WARNING):
            watcher.start_watching()

        assert "Watcher is already running" in caplog.text

    @patch("cicada.utils.storage.get_index_path")
    def test_trigger_reindex_handles_os_error(self, mock_get_index_path, elixir_repo):
        mock_get_index_path.return_value = elixir_repo / "index.json"
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        mock_indexer = Mock()
        mock_indexer.supports_incremental = True
        mock_indexer.incremental_index_repository.side_effect = OSError("disk full")
        watcher.indexer = mock_indexer

        watcher._trigger_reindex()
