"""
Tests for IndexManager keyword availability detection.

Ensures that IndexManager correctly detects both documentation keywords
and string keywords for enabling keyword search functionality.
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cicada.mcp.handlers.index_manager import BackgroundRefreshManager, IndexManager


class TestIndexManagerKeywordDetection:
    """Test IndexManager's keyword availability detection."""

    def test_no_keywords_at_all(self):
        """Index with no keywords should return False."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "functions": [
                        {"name": "func1", "line": 1},
                    ]
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is False

    def test_has_doc_keywords_only(self):
        """Index with only documentation keywords should return True."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "keywords": {"user": 0.9, "account": 0.8},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_has_string_keywords_only(self):
        """Index with only string keywords should return True."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "string_keywords": {"database": 0.9, "query": 0.8},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        # This should now return True after the fix
        assert manager._check_keywords_available() is True

    def test_has_both_keyword_types(self):
        """Index with both keyword types should return True."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "keywords": {"user": 0.9, "account": 0.8},
                    "string_keywords": {"database": 0.9, "query": 0.8},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_function_level_doc_keywords(self):
        """Function-level documentation keywords should be detected."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "functions": [
                        {
                            "name": "func1",
                            "line": 1,
                            "keywords": {"process": 0.9, "data": 0.8},
                        },
                    ]
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_function_level_string_keywords(self):
        """Function-level string keywords should be detected."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "functions": [
                        {
                            "name": "func1",
                            "line": 1,
                            "string_keywords": {"SELECT": 0.9, "FROM": 0.8},
                        },
                    ]
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        # This should now return True after the fix
        assert manager._check_keywords_available() is True

    def test_mixed_module_and_function_keywords(self):
        """Mix of module and function-level keywords should be detected."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "Module1": {
                    "string_keywords": {"config": 0.9},
                    "functions": [
                        {"name": "func1", "line": 1},
                    ],
                },
                "Module2": {
                    "functions": [
                        {
                            "name": "func2",
                            "line": 10,
                            "keywords": {"validate": 0.8},
                        },
                    ]
                },
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is True

    def test_empty_keyword_dicts(self):
        """Empty keyword dictionaries should return False."""
        config = {
            "storage": {"index_path": "/fake/path"},
        }
        index = {
            "modules": {
                "MyModule": {
                    "keywords": {},
                    "string_keywords": {},
                    "functions": [
                        {
                            "name": "func1",
                            "line": 1,
                            "keywords": {},
                            "string_keywords": {},
                        },
                    ],
                }
            }
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = index

        assert manager._check_keywords_available() is False


class TestBackgroundRefreshManager:
    """Tests for BackgroundRefreshManager."""

    @pytest.fixture
    def mock_index_manager(self):
        """Create a mock IndexManager."""
        manager = MagicMock()
        manager.check_staleness.return_value = {"is_stale": True, "age_str": "5 minutes"}
        return manager

    @pytest.fixture
    def refresh_manager(self, mock_index_manager, tmp_path):
        """Create a BackgroundRefreshManager for testing."""
        config = {
            "indexing": {
                "extract_keywords": False,
                "extract_string_keywords": False,
            }
        }
        return BackgroundRefreshManager(
            index_manager=mock_index_manager,
            repo_path=tmp_path,
            index_path=tmp_path / "index.json",
            config=config,
        )

    def test_request_refresh_when_stale(self, refresh_manager, mock_index_manager):
        """Test that refresh is requested when index is stale."""
        with patch.object(refresh_manager, "_schedule_refresh") as mock_schedule:
            result = refresh_manager.request_refresh_if_stale()
            assert result is True
            mock_schedule.assert_called_once()

    def test_no_refresh_when_not_stale(self, refresh_manager, mock_index_manager):
        """Test that refresh is not requested when index is fresh."""
        mock_index_manager.check_staleness.return_value = None

        with patch.object(refresh_manager, "_schedule_refresh") as mock_schedule:
            result = refresh_manager.request_refresh_if_stale()
            assert result is False
            mock_schedule.assert_not_called()

    def test_no_refresh_during_cooldown(self, refresh_manager, mock_index_manager):
        """Test that refresh respects cooldown period."""
        # Simulate that a refresh just happened
        refresh_manager._last_refresh_time = time.time()

        with patch.object(refresh_manager, "_schedule_refresh") as mock_schedule:
            result = refresh_manager.request_refresh_if_stale()
            assert result is False
            mock_schedule.assert_not_called()

    def test_no_refresh_when_in_progress(self, refresh_manager, mock_index_manager):
        """Test that refresh is not requested when one is already in progress."""
        refresh_manager._refresh_in_progress = True

        with patch.object(refresh_manager, "_schedule_refresh") as mock_schedule:
            result = refresh_manager.request_refresh_if_stale()
            assert result is False
            mock_schedule.assert_not_called()

    def test_stop_cancels_pending_timer(self, refresh_manager):
        """Test that stop() cancels pending debounce timer."""
        # Schedule a refresh
        refresh_manager._debounce_timer = threading.Timer(10.0, lambda: None)
        refresh_manager._debounce_timer.start()

        refresh_manager.stop()

        assert refresh_manager._stopped is True
        assert refresh_manager._debounce_timer is None

    def test_no_refresh_after_stop(self, refresh_manager, mock_index_manager):
        """Test that no refresh happens after stop() is called."""
        refresh_manager.stop()

        with patch.object(refresh_manager, "_schedule_refresh") as mock_schedule:
            result = refresh_manager.request_refresh_if_stale()
            assert result is False
            mock_schedule.assert_not_called()

    def test_debounce_coalesces_requests(self, refresh_manager, mock_index_manager):
        """Test that multiple rapid requests are debounced."""
        with patch.object(refresh_manager, "_execute_refresh") as mock_execute:
            # Make multiple rapid schedule requests
            refresh_manager._schedule_refresh()
            refresh_manager._schedule_refresh()
            refresh_manager._schedule_refresh()

            # Only one timer should be active
            assert refresh_manager._debounce_timer is not None

            # Wait for debounce to complete
            time.sleep(refresh_manager.DEBOUNCE_SECONDS + 0.5)

            # Should have been called only once
            assert mock_execute.call_count == 1

        refresh_manager.stop()

    def test_callback_called_on_refresh_complete(self, mock_index_manager, tmp_path):
        """Test that on_refresh_complete callback is called."""
        callback_called = []

        def on_complete():
            callback_called.append(True)

        config = {"indexing": {}}
        manager = BackgroundRefreshManager(
            index_manager=mock_index_manager,
            repo_path=tmp_path,
            index_path=tmp_path / "index.json",
            config=config,
            on_refresh_complete=on_complete,
        )

        with patch.object(manager, "_run_incremental_index"):
            manager._execute_refresh()

        assert len(callback_called) == 1
        manager.stop()
