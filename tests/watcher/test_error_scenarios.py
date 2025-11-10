"""
Test to verify Issue 2.1 fix - Dangerous Fallback with Broken Index

This test file verifies that the error handling in cicada/watcher.py start_watching()
properly handles different failure scenarios according to the fix requirements.
"""

import json
from unittest.mock import Mock, patch

import pytest

from cicada.watcher import FileWatcher


class TestWatcherErrorScenarios:
    """Test Issue 2.1 fix - Dangerous Fallback with Broken Index"""

    @patch("sys.exit")
    @patch("cicada.watcher.ElixirIndexer")
    def test_critical_errors_cause_immediate_exit(self, mock_indexer_class, mock_exit, elixir_repo):
        """Test that critical errors during initial indexing cause immediate exit"""
        test_cases = [
            (MemoryError("Out of memory"), "MemoryError"),
            (OSError("Disk full"), "OSError"),
        ]

        for error, description in test_cases:
            mock_exit.reset_mock()
            # Make sys.exit actually stop execution in the test
            mock_exit.side_effect = SystemExit(1)

            mock_indexer = Mock()
            mock_indexer.incremental_index_repository.side_effect = error
            mock_indexer_class.return_value = mock_indexer

            watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)

            with pytest.raises(SystemExit):
                watcher.start_watching()

            mock_exit.assert_called_once_with(1), f"Should exit for {description}"

    @patch("sys.exit")
    @patch("cicada.watcher.ElixirIndexer")
    def test_keyboard_interrupt_not_caught(self, mock_indexer_class, mock_exit, elixir_repo):
        """Test that KeyboardInterrupt is properly handled and not caught as generic Exception"""
        mock_indexer = Mock()
        mock_indexer.incremental_index_repository.side_effect = KeyboardInterrupt()
        mock_indexer_class.return_value = mock_indexer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.shutdown_event.set()  # Set shutdown to exit immediately
        watcher.start_watching()

        # Should return early without sys.exit
        mock_exit.assert_not_called()

    @patch("sys.exit")
    @patch("cicada.watcher.ElixirIndexer")
    def test_index_fallback_scenarios(self, mock_indexer_class, mock_exit, elixir_repo):
        """Test various index fallback scenarios when initial indexing fails"""
        from cicada.utils.storage import create_storage_dir, get_index_path

        mock_indexer = Mock()
        mock_indexer.incremental_index_repository.side_effect = Exception("Initial indexing failed")
        mock_indexer_class.return_value = mock_indexer

        # Make sys.exit actually stop execution
        mock_exit.side_effect = SystemExit(1)

        # Test 1: Corrupted index causes exit
        create_storage_dir(elixir_repo)
        index_path = get_index_path(elixir_repo)
        index_path.write_text("corrupted json {{{")

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        with pytest.raises(SystemExit):
            watcher.start_watching()
        mock_exit.assert_called_once_with(1)
        mock_exit.reset_mock()

        # Test 2: Empty index (no modules) causes exit
        index_path.write_text("{}")
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        with pytest.raises(SystemExit):
            watcher.start_watching()
        mock_exit.assert_called_once_with(1)
        mock_exit.reset_mock()

        # Test 3: No existing index causes exit
        index_path.unlink()
        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        with pytest.raises(SystemExit):
            watcher.start_watching()
        mock_exit.assert_called_once_with(1)

    @patch("cicada.watcher.ElixirIndexer")
    @patch("cicada.watcher.Observer")
    @patch("sys.exit")
    def test_valid_index_allows_continuation(
        self, mock_exit, mock_observer_class, mock_indexer_class, elixir_repo
    ):
        """Test that valid existing index allows continuation with warning"""
        from cicada.utils.storage import create_storage_dir, get_index_path

        # Create valid index
        create_storage_dir(elixir_repo)
        index_path = get_index_path(elixir_repo)
        valid_index = {
            "modules": {"TestModule": {"path": "lib/test.ex", "functions": []}},
            "pr_index": {},
        }
        index_path.write_text(json.dumps(valid_index))

        mock_indexer = Mock()
        mock_indexer.incremental_index_repository.side_effect = Exception("Initial indexing failed")
        mock_indexer_class.return_value = mock_indexer

        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        watcher = FileWatcher(repo_path=str(elixir_repo), register_signal_handlers=False)
        watcher.shutdown_event.set()  # Exit immediately
        watcher.start_watching()

        # Should NOT exit - continues with existing valid index
        mock_exit.assert_not_called()
        # Observer should have been started
        mock_observer.start.assert_called_once()


if __name__ == "__main__":
    # Run with pytest for proper test discovery and execution
    import sys

    pytest.main([__file__, "-v"])
