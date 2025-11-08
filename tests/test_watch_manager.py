"""
Tests for cicada/watch_manager.py - Watch process management
"""

import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch

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
pytestmark = pytest.mark.xdist_group(name="watch_manager_tests")


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
    manager = get_watch_manager()
    if manager and manager.process:
        try:
            manager.stop()
        except Exception:
            pass
    set_watch_manager(None)


class TestWatchProcessManager:
    """Tests for WatchProcessManager class"""

    @staticmethod
    def _create_mock_process(pid=12345, running=True):
        """Helper to create a mock subprocess with standard behavior"""
        mock_process = Mock()
        mock_process.pid = pid
        mock_process.poll.return_value = None if running else 0
        mock_process.returncode = None if running else 0
        return mock_process

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
        mock_process = self._create_mock_process(pid=12345, running=True)
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
    def test_start_with_tier_flags(self, mock_popen, temp_repo):
        """Test that tier flags are passed correctly to the watch command"""
        test_cases = [
            ("fast", "--fast"),
            ("max", "--max"),
            ("regular", "--regular"),
        ]

        for tier, expected_flag in test_cases:
            mock_popen.reset_mock()
            mock_process = self._create_mock_process(pid=12345, running=True)
            mock_popen.return_value = mock_process

            manager = WatchProcessManager(temp_repo, tier=tier, register_atexit=False)
            manager.start()

            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            assert expected_flag in cmd, f"Expected {expected_flag} for tier {tier}"

    @patch("subprocess.Popen")
    def test_start_already_running_returns_false(self, mock_popen, temp_repo):
        """Test that start() returns False if process is already running"""
        mock_process = self._create_mock_process(running=True)
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        result = manager.start()
        assert result is True

        # Try to start again
        result = manager.start()
        assert result is False
        # Should only call Popen once
        assert mock_popen.call_count == 1

    @patch("subprocess.Popen")
    def test_start_error_handling(self, mock_popen, temp_repo):
        """Test start() error handling for various exception types"""
        # Test cases: (exception, expected_result, should_raise, error_pattern)
        test_cases = [
            # Benign errors return False
            (FileNotFoundError("Python not found"), False, False, None),
            (PermissionError("No execute permission"), False, False, None),
            (OSError("No such file"), False, False, None),
            # Critical errors raise RuntimeError
            (ImportError("Cannot import cicada"), None, True, "Corrupted installation"),
            (
                ModuleNotFoundError("Module 'cicada' not found"),
                None,
                True,
                "Corrupted installation",
            ),
            (MemoryError("Out of memory"), None, True, "System failure"),
            (SystemError("Low-level error"), None, True, "System failure"),
            (Exception("Test error"), None, True, "Unexpected error"),
        ]

        for exception, expected_result, should_raise, error_pattern in test_cases:
            mock_popen.side_effect = exception
            manager = WatchProcessManager(temp_repo, register_atexit=False)

            if should_raise:
                with pytest.raises(RuntimeError, match=error_pattern):
                    manager.start()
            else:
                result = manager.start()
                assert result == expected_result

            assert manager.process is None

    @patch("subprocess.Popen")
    @patch("os.killpg")
    @patch("os.getpgid")
    def test_stop_terminates_process(self, mock_getpgid, mock_killpg, mock_popen, temp_repo):
        """Test that stop() terminates the process"""
        mock_process = self._create_mock_process(running=True)
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
    def test_is_running_states(self, mock_popen, temp_repo):
        """Test is_running() in different process states"""
        # Test when process is active
        mock_process = self._create_mock_process(running=True)
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()
        assert manager.is_running() is True

        # Test when process has stopped
        mock_process.poll.return_value = 0
        assert manager.is_running() is False

        # Test with no process
        manager.process = None
        assert manager.is_running() is False


class TestGlobalWatchManager:
    """Tests for global watch manager functions"""

    @staticmethod
    def _create_mock_process(pid=12345, running=True):
        """Helper to create a mock subprocess with standard behavior"""
        mock_process = Mock()
        mock_process.pid = pid
        mock_process.poll.return_value = None if running else 0
        return mock_process

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
    def test_start_watch_process(self, mock_popen, temp_repo):
        """Test start_watch_process creates manager with correct parameters"""
        mock_process = self._create_mock_process(running=True)
        mock_popen.return_value = mock_process

        # Test with default parameters
        result = start_watch_process(temp_repo)
        assert result is True
        manager = get_watch_manager()
        assert manager is not None
        assert manager.repo_path == temp_repo

        # Test with custom parameters
        result = start_watch_process(temp_repo, tier="fast", debounce=5.0)
        assert result is True
        manager = get_watch_manager()
        assert manager.tier == "fast"
        assert manager.debounce == 5.0

    @patch("subprocess.Popen")
    @patch("os.killpg")
    @patch("os.getpgid")
    def test_stop_watch_process(self, mock_getpgid, mock_killpg, mock_popen, temp_repo):
        """Test that stop_watch_process stops the global manager"""
        mock_process = self._create_mock_process(running=True)
        mock_popen.return_value = mock_process
        mock_getpgid.return_value = 12345

        start_watch_process(temp_repo)
        stop_watch_process()

        assert get_watch_manager() is None

    def test_stop_watch_process_no_manager_is_safe(self):
        """Test that stop_watch_process is safe when no manager exists"""
        # Should not raise exception
        stop_watch_process()


class TestWatchProcessErrorPaths:
    """Tests for error paths in watch process management"""

    @patch("subprocess.Popen")
    def test_process_early_exit_detection(self, mock_popen, temp_repo):
        """Test detection of processes that exit immediately after starting"""
        test_cases = [
            (1, "Non-zero exit code"),
            (0, "Zero exit code"),
            (-1, "Negative exit code"),
        ]

        for exit_code, description in test_cases:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = exit_code
            mock_process.returncode = exit_code
            mock_popen.return_value = mock_process

            manager = WatchProcessManager(temp_repo, register_atexit=False)
            result = manager.start()

            # Should detect the early exit and return False
            assert result is False, f"Should detect early exit for {description}"
            assert manager.process is None

    @patch("subprocess.Popen")
    @patch("os.killpg")
    @patch("os.getpgid")
    def test_stop_error_scenarios(self, mock_getpgid, mock_killpg, mock_popen, temp_repo):
        """Test stop() behavior in various error scenarios"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        mock_getpgid.return_value = 12345

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()

        # Test 1: Process already gone
        mock_killpg.side_effect = ProcessLookupError("Process not found")
        manager.stop()
        assert manager.process is None
        mock_killpg.reset_mock()

        # Test 2: Permission denied (should fallback to terminate)
        manager.start()
        mock_killpg.side_effect = PermissionError("Permission denied")
        manager.stop()
        assert manager.process is None
        mock_process.terminate.assert_called()
        mock_killpg.reset_mock()
        mock_process.reset_mock()

        # Test 3: Timeout requires force kill
        manager.start()
        mock_killpg.side_effect = None
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5), None]
        manager.stop()
        assert mock_killpg.call_count == 2  # SIGTERM then SIGKILL
        assert manager.process is None

    @patch("subprocess.Popen")
    def test_platform_specific_stop_behavior(self, mock_popen, temp_repo):
        """Test stopping behavior on different platforms"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()

        # Simulate Windows (no killpg)
        with patch("os.killpg", create=False):
            manager.stop()

        # Should fall back to terminate()
        mock_process.terminate.assert_called()
        assert manager.process is None

    @patch("subprocess.Popen")
    def test_stop_process_reference_management(self, mock_popen, temp_repo):
        """Test process reference management during stop() errors.

        Addresses REPORT.md Issue 1.1 - verifies correct handling of process
        reference during different error scenarios.
        """
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)
        manager.start()

        # Test 1: Unexpected errors preserve process reference for retry
        mock_process.wait.side_effect = RuntimeError("Unexpected error")
        with pytest.raises(RuntimeError, match="Unexpected error"):
            manager.stop()
        assert manager.process is not None  # Preserved for retry
        assert manager.process.pid == 12345

        # Test 2: Retry after failed termination
        mock_process.wait.side_effect = None  # Reset to normal
        manager.stop()
        assert manager.process is None  # Now cleared

        # Test 3: Expected errors (process gone) clear reference immediately
        manager.start()
        mock_process.wait.side_effect = ProcessLookupError("Process not found")
        manager.stop()  # Should NOT raise exception
        assert manager.process is None  # Cleared (process is gone)

    @patch("subprocess.Popen")
    def test_cleanup_and_terminate_edge_cases(self, mock_popen, temp_repo):
        """Test edge cases for cleanup and terminate methods.

        Addresses REPORT.md Issues 1.4 and 5.2.
        """
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = WatchProcessManager(temp_repo, register_atexit=False)

        # Test 1: _cleanup handles stop() exceptions gracefully (Issue 1.4)
        manager.start()
        mock_process.wait.side_effect = RuntimeError("Cannot stop")
        manager._cleanup()  # Should not raise
        assert manager.process is not None  # Process preserved (stop failed)

        # Test 2: _terminate_process validates None process (Issue 5.2)
        manager.process = None
        import signal

        with pytest.raises(ValueError, match="Cannot terminate a None process"):
            manager._terminate_process(signal.SIGTERM)


# Integration Tests - Address REPORT.md Section 4 Testing Gaps
class TestMCPWatchIntegration:
    """Integration tests for MCP server + watch process coordination"""

    def test_mcp_server_starts_watch_process_and_cleans_up(self, temp_repo):
        """Test watch process lifecycle when started from MCP server context.

        Addresses REPORT.md Issue 4.3 - MCP + watch integration not tested.
        Verifies watch process lifecycle when started from MCP server context.

        Tests:
        - Watch process starts successfully
        - Process is actually running (not just claimed to be)
        - Stop cleans up process completely
        - No orphaned processes left behind

        Note: This tests the watch process management functions that would be
        called by the MCP server, without actually running the MCP server.
        """

        # Use REAL WatchProcessManager and actually spawn subprocess
        # This is the critical difference from unit tests - we verify real process behavior
        success = start_watch_process(repo_path=str(temp_repo), tier="fast", debounce=2.0)

        assert success, "Watch process should start successfully"

        # Verify process is actually running
        manager = get_watch_manager()
        assert manager is not None, "Global watch manager should be set"
        assert manager.process is not None, "Watch subprocess should be created"
        assert manager.process.poll() is None, "Watch process should still be running"

        # Verify we can get the PID (proves process is real)
        pid = manager.process.pid
        assert pid > 0, "Process should have valid PID"

        # Simulate MCP exit - cleanup in finally block
        stop_watch_process()

        # Verify watch stopped completely
        assert get_watch_manager() is None, "Global watch manager should be cleared"

        # Give process a moment to terminate
        time.sleep(0.5)

        # Verify process is no longer running by checking if PID exists
        try:
            import os
            import signal

            # Try to send signal 0 (does nothing, just checks if process exists)
            os.kill(pid, 0)
            # If we get here, process still exists - that's bad
            pytest.fail(f"Watch process (PID {pid}) should be terminated but is still running")
        except ProcessLookupError:
            # Expected - process is gone
            pass
