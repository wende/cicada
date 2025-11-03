"""
Tests for cicada/watch_manager.py - Watch process management
"""

import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cicada.watch_manager import (
    WatchProcessManager,
    get_watch_manager,
    set_watch_manager,
    start_watch_process,
    stop_watch_process,
)

# Mark all tests in this module to run serially in their own xdist group
# This prevents interference with parallel test execution
pytestmark = pytest.mark.xdist_group(name="watch_tests")


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository for testing"""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "module.ex").write_text("defmodule Test do\nend\n")
    (tmp_path / "mix.exs").write_text("defmodule Test.MixProject do\nend\n")
    return tmp_path


@pytest.fixture(autouse=True)
def cleanup_watch_managers():
    """Automatically clean up any watch managers after each test"""
    yield
    # Clean up global watch manager
    from cicada.watch_manager import get_watch_manager, set_watch_manager

    manager = get_watch_manager()
    if manager is not None and manager.process is not None:
        try:
            manager.stop()
        except Exception:
            pass
    set_watch_manager(None)


class TestWatchProcessManager:
    """Tests for WatchProcessManager class"""

    def test_initialization(self, temp_repo):
        """Test WatchProcessManager initialization"""
        manager = WatchProcessManager(temp_repo, register_atexit=False)

        assert manager.repo_path == temp_repo
        assert manager.tier == "regular"
        assert manager.debounce == 2.0
        assert manager.process is None
        assert manager._cleanup_registered is False

    def test_initialization_with_custom_parameters(self, temp_repo):
        """Test initialization with custom parameters"""
        manager = WatchProcessManager(temp_repo, tier="fast", debounce=5.0, register_atexit=False)

        assert manager.tier == "fast"
        assert manager.debounce == 5.0

    @patch("subprocess.Popen")
    def test_start_creates_process(self, mock_popen, temp_repo):
        """Test that start() creates a subprocess"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        result = manager.start()

        assert result is True
        assert manager.process == mock_process
        mock_popen.assert_called_once()

        # Verify the command includes expected arguments
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "watch" in cmd
        assert str(temp_repo) in cmd
        assert "--debounce" in cmd
        assert "2.0" in cmd
        assert "--regular" in cmd

    @patch("subprocess.Popen")
    def test_start_with_fast_tier(self, mock_popen, temp_repo):
        """Test that fast tier is passed to the watch command"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, tier="fast")
        manager.start()

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "--fast" in cmd

    @patch("subprocess.Popen")
    def test_start_with_max_tier(self, mock_popen, temp_repo):
        """Test that max tier is passed to the watch command"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, tier="max")
        manager.start()

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "--max" in cmd

    @patch("subprocess.Popen")
    def test_start_already_running_returns_false(self, mock_popen, temp_repo):
        """Test that start() returns False if process is already running"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()

        # Try to start again
        result = manager.start()
        assert result is False
        # Should only call Popen once
        assert mock_popen.call_count == 1

    @patch("subprocess.Popen")
    def test_start_exception_returns_false(self, mock_popen, temp_repo):
        """Test that start() returns False on exception"""
        mock_popen.side_effect = Exception("Test error")

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        result = manager.start()

        assert result is False
        assert manager.process is None

    @patch("subprocess.Popen")
    @patch("os.killpg")
    @patch("os.getpgid")
    def test_stop_terminates_process(self, mock_getpgid, mock_killpg, mock_popen, temp_repo):
        """Test that stop() terminates the process"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process
        mock_getpgid.return_value = 12345

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()
        manager.stop()

        # Should have tried to send SIGTERM to process group
        mock_killpg.assert_called()
        mock_process.wait.assert_called()
        assert manager.process is None

    @patch("subprocess.Popen")
    def test_stop_no_process_is_safe(self, mock_popen, temp_repo):
        """Test that stop() is safe when no process is running"""
        manager = WatchProcessManager(temp_repo, register_atexit=False)
        # Should not raise exception
        manager.stop()

    @patch("subprocess.Popen")
    def test_is_running_when_process_active(self, mock_popen, temp_repo):
        """Test is_running() when process is active"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()

        assert manager.is_running() is True

    @patch("subprocess.Popen")
    def test_is_running_when_process_stopped(self, mock_popen, temp_repo):
        """Test is_running() when process has stopped"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process has exited
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()

        assert manager.is_running() is False

    def test_is_running_no_process(self, temp_repo):
        """Test is_running() when no process exists"""
        manager = WatchProcessManager(temp_repo, register_atexit=False)
        assert manager.is_running() is False


class TestGlobalWatchManager:
    """Tests for global watch manager functions"""

    def teardown_method(self):
        """Clean up global state after each test"""
        set_watch_manager(None)

    def test_get_set_watch_manager(self, temp_repo):
        """Test getting and setting the global watch manager"""
        manager = WatchProcessManager(temp_repo, register_atexit=False)

        set_watch_manager(manager)
        assert get_watch_manager() == manager

        set_watch_manager(None)
        assert get_watch_manager() is None

    @patch("subprocess.Popen")
    def test_start_watch_process_creates_manager(self, mock_popen, temp_repo):
        """Test that start_watch_process creates and stores a manager"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        result = start_watch_process(temp_repo)

        assert result is True
        manager = get_watch_manager()
        assert manager is not None
        assert manager.repo_path == temp_repo

    @patch("subprocess.Popen")
    def test_start_watch_process_with_parameters(self, mock_popen, temp_repo):
        """Test start_watch_process with custom parameters"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        result = start_watch_process(temp_repo, tier="fast", debounce=5.0)

        assert result is True
        manager = get_watch_manager()
        assert manager.tier == "fast"
        assert manager.debounce == 5.0

    @patch("subprocess.Popen")
    @patch("os.killpg")
    @patch("os.getpgid")
    def test_stop_watch_process_stops_manager(
        self, mock_getpgid, mock_killpg, mock_popen, temp_repo
    ):
        """Test that stop_watch_process stops the global manager"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        mock_getpgid.return_value = 12345

        start_watch_process(temp_repo)
        stop_watch_process()

        assert get_watch_manager() is None

    def test_stop_watch_process_no_manager_is_safe(self):
        """Test that stop_watch_process is safe when no manager exists"""
        # Should not raise exception
        stop_watch_process()
