"""
Comprehensive tests for cicada/watcher.py - File watching and automatic reindexing
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cicada.watcher import ElixirFileEventHandler, FileWatcher

# Mark all tests in this module to run serially in their own xdist group
# This prevents interference with parallel test execution
pytestmark = pytest.mark.xdist_group(name="watch_tests")


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary Elixir repository structure"""
    # Create directory structure
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    # Create some Elixir files
    (lib_dir / "module1.ex").write_text(
        """
defmodule Module1 do
  def hello, do: "world"
end
"""
    )

    (lib_dir / "module2.ex").write_text(
        """
defmodule Module2 do
  def foo, do: :bar
end
"""
    )

    (test_dir / "module1_test.exs").write_text(
        """
defmodule Module1Test do
  use ExUnit.Case
end
"""
    )

    # Create mix.exs
    (tmp_path / "mix.exs").write_text(
        """
defmodule TestProject.MixProject do
  use Mix.Project
end
"""
    )

    # Create excluded directories
    (tmp_path / "deps").mkdir()
    (tmp_path / "_build").mkdir()
    (tmp_path / ".git").mkdir()

    return tmp_path


@pytest.fixture
def mock_watcher():
    """Create a mock watcher for event handler testing"""
    watcher = Mock(spec=FileWatcher)
    watcher._on_file_change = Mock()
    return watcher


@pytest.fixture
def file_watcher(temp_repo):
    """Create a FileWatcher with automatic cleanup"""
    watcher = None

    def _create_watcher(**kwargs):
        nonlocal watcher
        # Always disable signal handlers in tests
        kwargs.setdefault("register_signal_handlers", False)
        watcher = FileWatcher(repo_path=str(temp_repo), register_signal_handlers=False, **kwargs)
        return watcher

    yield _create_watcher

    # Cleanup: ensure watcher is stopped and timers cancelled
    if watcher is not None:
        try:
            with watcher.timer_lock:
                if watcher.debounce_timer is not None:
                    watcher.debounce_timer.cancel()
                    watcher.debounce_timer = None
            if watcher.running:
                watcher.stop_watching()
        except Exception:
            pass  # Ignore cleanup errors


class TestElixirFileEventHandler:
    """Tests for ElixirFileEventHandler class"""

    def test_initialization(self, mock_watcher):
        """Test that event handler initializes correctly"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler.watcher == mock_watcher
        assert "deps" in handler.excluded_dirs
        assert "_build" in handler.excluded_dirs
        assert ".git" in handler.excluded_dirs

    def test_is_elixir_file_ex(self, mock_watcher):
        """Test that .ex files are recognized as Elixir files"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_elixir_file("lib/module.ex") is True

    def test_is_elixir_file_exs(self, mock_watcher):
        """Test that .exs files are recognized as Elixir files"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_elixir_file("test/module_test.exs") is True

    def test_is_elixir_file_non_elixir(self, mock_watcher):
        """Test that non-Elixir files are rejected"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_elixir_file("README.md") is False
        assert handler._is_elixir_file("config.yaml") is False
        assert handler._is_elixir_file("lib/module.py") is False

    def test_is_excluded_path_deps(self, mock_watcher):
        """Test that deps directory is excluded"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_excluded_path("deps/phoenix/lib/phoenix.ex") is True

    def test_is_excluded_path_build(self, mock_watcher):
        """Test that _build directory is excluded"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_excluded_path("_build/dev/lib/app/module.ex") is True

    def test_is_excluded_path_git(self, mock_watcher):
        """Test that .git directory is excluded"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_excluded_path(".git/objects/abc123") is True

    def test_is_excluded_path_normal(self, mock_watcher):
        """Test that normal paths are not excluded"""
        handler = ElixirFileEventHandler(mock_watcher)
        assert handler._is_excluded_path("lib/my_app/module.ex") is False
        assert handler._is_excluded_path("test/module_test.exs") is False

    def test_on_any_event_ignores_directories(self, mock_watcher):
        """Test that directory events are ignored"""
        handler = ElixirFileEventHandler(mock_watcher)
        event = Mock()
        event.is_directory = True
        event.src_path = "lib/my_app"

        handler.on_any_event(event)
        mock_watcher._on_file_change.assert_not_called()

    def test_on_any_event_ignores_non_elixir_files(self, mock_watcher):
        """Test that non-Elixir files are ignored"""
        handler = ElixirFileEventHandler(mock_watcher)
        event = Mock()
        event.is_directory = False
        event.src_path = "README.md"

        handler.on_any_event(event)
        mock_watcher._on_file_change.assert_not_called()

    def test_on_any_event_ignores_excluded_directories(self, mock_watcher):
        """Test that files in excluded directories are ignored"""
        handler = ElixirFileEventHandler(mock_watcher)
        event = Mock()
        event.is_directory = False
        event.src_path = "deps/phoenix/lib/phoenix.ex"

        handler.on_any_event(event)
        mock_watcher._on_file_change.assert_not_called()

    def test_on_any_event_processes_valid_elixir_files(self, mock_watcher):
        """Test that valid Elixir files trigger the watcher"""
        handler = ElixirFileEventHandler(mock_watcher)
        event = Mock()
        event.is_directory = False
        event.src_path = "lib/my_app/module.ex"

        handler.on_any_event(event)
        mock_watcher._on_file_change.assert_called_once_with(event)


class TestFileWatcher:
    """Tests for FileWatcher class"""

    def test_initialization_defaults(self, temp_repo):
        """Test FileWatcher initialization with default parameters"""
        watcher = FileWatcher(repo_path=str(temp_repo), register_signal_handlers=False)

        assert watcher.repo_path == temp_repo
        assert watcher.debounce_seconds == 2.0
        assert watcher.verbose is True
        assert watcher.tier == "regular"
        assert watcher.running is False
        assert watcher.observer is None
        assert watcher.indexer is None

    def test_initialization_custom_parameters(self, temp_repo):
        """Test FileWatcher initialization with custom parameters"""
        watcher = FileWatcher(
            repo_path=str(temp_repo),
            debounce_seconds=5.0,
            verbose=False,
            tier="fast",
        )

        assert watcher.debounce_seconds == 5.0
        assert watcher.verbose is False
        assert watcher.tier == "fast"

    def test_on_file_change_starts_debounce_timer(self, temp_repo):
        """Test that file changes start a debounce timer"""
        watcher = FileWatcher(
            repo_path=str(temp_repo), register_signal_handlers=False, debounce_seconds=0.1
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

    def test_on_file_change_cancels_previous_timer(self, temp_repo):
        """Test that new file changes cancel previous debounce timers"""
        watcher = FileWatcher(
            repo_path=str(temp_repo), register_signal_handlers=False, debounce_seconds=1.0
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

    @patch("cicada.watcher.ElixirIndexer")
    def test_trigger_reindex_calls_indexer(self, mock_indexer_class, temp_repo):
        """Test that _trigger_reindex calls the incremental indexer"""
        mock_indexer = Mock()
        mock_indexer_class.return_value = mock_indexer

        watcher = FileWatcher(repo_path=str(temp_repo), register_signal_handlers=False)
        watcher.indexer = mock_indexer

        # Trigger reindex
        watcher._trigger_reindex()

        # Verify indexer was called with correct parameters
        assert mock_indexer.incremental_index_repository.called
        call_kwargs = mock_indexer.incremental_index_repository.call_args.kwargs
        assert call_kwargs["repo_path"] == str(temp_repo)
        assert call_kwargs["extract_keywords"] is True
        assert call_kwargs["force_full"] is False
        assert "output_path" in call_kwargs

    @patch("cicada.watcher.ElixirIndexer")
    def test_trigger_reindex_handles_errors_gracefully(self, mock_indexer_class, temp_repo):
        """Test that errors during reindexing don't crash the watcher"""
        mock_indexer = Mock()
        mock_indexer.incremental_index_repository.side_effect = Exception("Test error")
        mock_indexer_class.return_value = mock_indexer

        watcher = FileWatcher(repo_path=str(temp_repo), register_signal_handlers=False)
        watcher.indexer = mock_indexer

        # Should not raise exception
        watcher._trigger_reindex()

        # Verify indexer was called even though it errored
        mock_indexer.incremental_index_repository.assert_called_once()

    def test_stop_watching_cancels_timer(self, temp_repo):
        """Test that stop_watching cancels the debounce timer"""
        watcher = FileWatcher(
            repo_path=str(temp_repo), register_signal_handlers=False, debounce_seconds=10.0
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

    @patch("cicada.watcher.Observer")
    def test_stop_watching_stops_observer(self, mock_observer_class, temp_repo):
        """Test that stop_watching stops the file system observer"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(repo_path=str(temp_repo), register_signal_handlers=False)
        watcher.running = True
        watcher.observer = mock_observer

        # Stop watching
        watcher.stop_watching()

        # Verify observer was stopped
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert watcher.observer is None

    def test_debouncing_delays_reindex(self, temp_repo):
        """Test that debouncing actually delays the reindex trigger"""
        reindex_called = threading.Event()

        def mock_trigger_reindex():
            reindex_called.set()

        watcher = FileWatcher(
            repo_path=str(temp_repo), register_signal_handlers=False, debounce_seconds=0.2
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

    def test_multiple_rapid_changes_debounce_correctly(self, temp_repo):
        """Test that multiple rapid changes only trigger one reindex"""
        reindex_count = []

        def mock_trigger_reindex():
            reindex_count.append(1)

        watcher = FileWatcher(
            repo_path=str(temp_repo), register_signal_handlers=False, debounce_seconds=0.2
        )
        watcher._trigger_reindex = mock_trigger_reindex

        event = Mock()
        event.src_path = "lib/module.ex"

        # Trigger multiple changes rapidly
        for _ in range(5):
            watcher._on_file_change(event)
            time.sleep(0.05)  # 50ms between changes

        # Wait for debounce to expire
        time.sleep(0.3)

        # Should have only triggered once
        assert len(reindex_count) == 1
