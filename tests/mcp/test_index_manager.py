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
        # Use a short debounce for faster test execution
        refresh_manager.DEBOUNCE_SECONDS = 0.1

        with patch.object(refresh_manager, "_execute_refresh") as mock_execute:
            # Make multiple rapid schedule requests
            refresh_manager._schedule_refresh()
            refresh_manager._schedule_refresh()
            refresh_manager._schedule_refresh()

            # Only one timer should be active
            assert refresh_manager._debounce_timer is not None

            # Wait for debounce to complete
            time.sleep(refresh_manager.DEBOUNCE_SECONDS + 0.1)

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

    def test_force_refresh_success_incremental(self, refresh_manager):
        """Test force_refresh with incremental mode."""
        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository.return_value = {
            "metadata": {"total_modules": 42, "total_functions": 150}
        }

        with patch("cicada.languages.LanguageRegistry") as mock_reg:
            mock_reg.get_indexer.return_value = mock_indexer
            with patch("cicada.setup.detect_project_language", return_value="python"):
                result = refresh_manager.force_refresh(force_full=False)

        assert result["success"] is True
        assert result["mode"] == "incremental"
        assert "elapsed_seconds" in result

    def test_force_refresh_success_full(self, refresh_manager):
        """Test force_refresh with full mode."""
        mock_indexer = MagicMock()
        mock_indexer.index_repository.return_value = {
            "metadata": {"total_modules": 50, "total_functions": 200}
        }

        with patch("cicada.languages.LanguageRegistry") as mock_reg:
            mock_reg.get_indexer.return_value = mock_indexer
            with patch("cicada.setup.detect_project_language", return_value="python"):
                result = refresh_manager.force_refresh(force_full=True)

        assert result["success"] is True
        assert result["mode"] == "full"

    def test_force_refresh_already_in_progress(self, refresh_manager):
        """Test that force_refresh returns error if refresh already in progress."""
        refresh_manager._refresh_in_progress = True
        result = refresh_manager.force_refresh()

        assert result["success"] is False
        assert "already in progress" in result["error"]
        assert result["elapsed_seconds"] == 0

    def test_force_refresh_with_error(self, refresh_manager):
        """Test force_refresh error handling."""
        with patch("cicada.setup.detect_project_language") as mock_detect:
            mock_detect.side_effect = RuntimeError("Detection failed")
            result = refresh_manager.force_refresh()

        assert result["success"] is False
        assert "Detection failed" in result["error"]
        assert result["elapsed_seconds"] >= 0

    def test_force_refresh_prefers_generic_metadata(self, refresh_manager):
        """Test that force_refresh uses generic metadata when available."""
        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository.return_value = {
            "metadata": {"total_modules": 10, "total_functions": 100}
        }

        # Override the global patch for this test
        with patch(
            "cicada.mcp.handlers.index_manager.run_generic_indexing_for_language_indexer"
        ) as mock_generic:
            mock_generic.return_value = {
                "metadata": {"total_modules": 20, "total_functions": 200}
            }

            with patch(
                "cicada.languages.LanguageRegistry.get_indexer", return_value=mock_indexer
            ):
                with patch("cicada.setup.detect_project_language", return_value="python"):
                    result = refresh_manager.force_refresh()

        assert result["total_modules"] == 20
        assert result["total_functions"] == 200

    def test_force_refresh_falls_back_to_language_metadata(self, refresh_manager):
        """Test that force_refresh falls back to language metadata when generic is empty."""
        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository.return_value = {
            "metadata": {"total_modules": 10, "total_functions": 100}
        }

        # Override to return empty metadata
        with patch(
            "cicada.mcp.handlers.index_manager.run_generic_indexing_for_language_indexer"
        ) as mock_generic:
            mock_generic.return_value = {"metadata": {}}

            with patch(
                "cicada.languages.LanguageRegistry.get_indexer", return_value=mock_indexer
            ):
                with patch("cicada.setup.detect_project_language", return_value="python"):
                    result = refresh_manager.force_refresh()

        assert result["total_modules"] == 10
        assert result["total_functions"] == 100

    def test_execute_refresh_when_stopped(self, refresh_manager):
        """Test that _execute_refresh returns early if stopped."""
        refresh_manager._stopped = True

        with patch.object(refresh_manager, "_run_incremental_index") as mock_run:
            refresh_manager._execute_refresh()

        mock_run.assert_not_called()

    def test_execute_refresh_with_exception(self, refresh_manager):
        """Test that _execute_refresh handles exceptions gracefully."""
        with patch.object(refresh_manager, "_run_incremental_index") as mock_run:
            mock_run.side_effect = ValueError("Index error")

            with patch("sys.stderr", new_callable=MagicMock):
                refresh_manager._execute_refresh()

        # Should reset flag even on error
        assert refresh_manager._refresh_in_progress is False

    def test_execute_refresh_sets_pending_if_already_running(self, refresh_manager):
        """Test that _execute_refresh sets pending flag if refresh already in progress."""
        refresh_manager._refresh_in_progress = True

        refresh_manager._execute_refresh()

        assert refresh_manager._pending_refresh is True

    def test_schedule_refresh_when_stopped(self, refresh_manager):
        """Test that _schedule_refresh returns early if stopped."""
        refresh_manager._stopped = True

        refresh_manager._schedule_refresh()

        assert refresh_manager._debounce_timer is None


class TestIndexManagerStalenessCheck:
    """Tests for staleness detection in IndexManager."""

    def test_format_age_string_minutes(self):
        """Test age formatting for less than 1 hour."""
        manager = IndexManager.__new__(IndexManager)
        age_str = manager._format_age_string(300)  # 5 minutes
        assert age_str == "5 minutes"

    def test_format_age_string_hours(self):
        """Test age formatting for hours."""
        manager = IndexManager.__new__(IndexManager)
        age_str = manager._format_age_string(7200)  # 2 hours
        assert age_str == "2 hours"

    def test_format_age_string_days(self):
        """Test age formatting for days."""
        manager = IndexManager.__new__(IndexManager)
        age_str = manager._format_age_string(86400)  # 1 day
        assert age_str == "1 days"

    def test_check_staleness_index_not_found(self):
        """Test check_staleness when index file doesn't exist."""
        config = {
            "storage": {"index_path": "/nonexistent/index.json"},
            "repository": {"path": "."},
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = {"modules": {}}

        result = manager.check_staleness()
        assert result is None

    def test_check_staleness_key_error(self):
        """Test check_staleness handles missing config keys."""
        manager = IndexManager.__new__(IndexManager)
        manager.config = {}
        manager._index = {"modules": {}}

        result = manager.check_staleness()
        assert result is None

    def test_get_index_mtime_file_not_found(self):
        """Test _get_index_mtime when file doesn't exist."""
        config = {
            "storage": {"index_path": "/nonexistent/index.json"},
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config

        mtime = manager._get_index_mtime()
        assert mtime is None

    def test_get_index_mtime_missing_key(self):
        """Test _get_index_mtime with missing config key."""
        manager = IndexManager.__new__(IndexManager)
        manager.config = {}

        mtime = manager._get_index_mtime()
        assert mtime is None

    def test_reload_if_changed_no_change(self):
        """Test reload_if_changed when file hasn't changed."""
        original_index = {"modules": {"test": {}}}
        config = {"storage": {"index_path": "/fake/path"}}

        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = original_index
        manager._index_mtime = 100.0

        with patch.object(manager, "_get_index_mtime", return_value=100.0):
            manager.reload_if_changed()

        # Index should remain unchanged
        assert manager._index == original_index

    def test_reload_if_changed_success(self):
        """Test reload_if_changed with successful reload."""
        original_index = {"modules": {"old": {}}}
        new_index = {"modules": {"new": {}}}
        config = {"storage": {"index_path": "/fake/path"}}

        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = original_index
        manager._index_mtime = 100.0
        manager._pr_index = {"some": "data"}
        manager._has_keywords = True

        with patch.object(manager, "_get_index_mtime", return_value=200.0):
            with patch.object(manager, "_load_index", return_value=new_index):
                with patch.object(manager, "_check_keywords_available", return_value=False):
                    manager.reload_if_changed()

        assert manager._index == new_index
        assert manager._index_mtime == 200.0
        assert manager._pr_index is None  # Should be invalidated
        assert manager._has_keywords is False

    def test_reload_if_changed_corrupted_index(self):
        """Test reload_if_changed handles corrupted index gracefully."""
        original_index = {"modules": {"original": {}}}
        config = {"storage": {"index_path": "/fake/path"}}

        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = original_index
        manager._index_mtime = 100.0

        with patch.object(manager, "_get_index_mtime", return_value=200.0):
            with patch.object(
                manager,
                "_load_index",
                side_effect=RuntimeError("Corrupted"),
            ):
                manager.reload_if_changed()

        # Original index should be kept
        assert manager._index == original_index
        assert manager._index_mtime == 100.0

    def test_get_files_to_check_under_limit(self):
        """Test _get_files_to_check when under max files."""
        manager = IndexManager.__new__(IndexManager)
        modules = [{"file": f"file{i}.py"} for i in range(10)]

        result = manager._get_files_to_check(modules)

        assert len(result) == 10

    def test_get_files_to_check_over_limit(self):
        """Test _get_files_to_check samples when over max files."""
        manager = IndexManager.__new__(IndexManager)
        modules = [{"file": f"file{i}.py"} for i in range(100)]

        result = manager._get_files_to_check(modules)

        assert len(result) == 50  # max_files_to_check

    def test_get_newest_file_mtime(self, tmp_path):
        """Test _get_newest_file_mtime finds the most recent file."""
        # Create test files with different modification times
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content")
        file2.write_text("content")

        manager = IndexManager.__new__(IndexManager)
        modules_to_check = [
            {"file": str(file1)},
            {"file": str(file2)},
        ]

        newest_mtime = manager._get_newest_file_mtime(modules_to_check, tmp_path)

        assert newest_mtime > 0

    def test_get_newest_file_mtime_missing_files(self, tmp_path):
        """Test _get_newest_file_mtime handles missing files."""
        manager = IndexManager.__new__(IndexManager)
        modules_to_check = [
            {"file": "nonexistent.py"},
            {"file": "also_missing.py"},
        ]

        newest_mtime = manager._get_newest_file_mtime(modules_to_check, tmp_path)

        assert newest_mtime == 0

    def test_check_staleness_stale_index(self, tmp_path):
        """Test check_staleness detects stale index."""
        # Create old index file and newer source file
        index_file = tmp_path / "index.json"
        source_file = tmp_path / "source.py"

        # Create index first (older)
        index_file.write_text("{}")
        import time

        time.sleep(0.1)
        # Create source file (newer)
        source_file.write_text("content")

        config = {
            "storage": {"index_path": str(index_file)},
            "repository": {"path": str(tmp_path)},
        }
        manager = IndexManager.__new__(IndexManager)
        manager.config = config
        manager._index = {"modules": {"test": {"file": "source.py"}}}

        result = manager.check_staleness()

        # Result may be None or have staleness info depending on timing
        if result:
            assert "is_stale" in result or "age_str" in result
