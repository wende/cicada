"""
Watch Process Manager - Manages a linked watch process for automatic reindexing.

This module provides functionality to spawn and manage a watch process that runs
alongside the MCP server, automatically reindexing when files change.
"""

import atexit
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class WatchProcessManager:
    """
    Manages a linked watch process for automatic reindexing.

    The watch process is spawned as a child process and is automatically
    terminated when the parent process exits.
    """

    def __init__(
        self,
        repo_path: str | Path,
        indexing_mode: str = "keywords",
        debounce: float = 2.0,
        register_atexit: bool = True,
    ):
        """
        Initialize the watch process manager.

        Args:
            repo_path: Path to the repository to watch
            indexing_mode: Indexing mode ("keywords" or "embeddings")
            debounce: Debounce interval in seconds
            register_atexit: Whether to register atexit cleanup handler (disable for testing)
        """
        self.repo_path = Path(repo_path).resolve()
        self.indexing_mode = indexing_mode
        self.debounce = debounce
        self.process: subprocess.Popen[bytes] | None = None
        self._cleanup_registered = False
        self._register_atexit = register_atexit

    def start(self) -> bool:
        """
        Start the watch process.

        Returns:
            True if the process was started successfully, False otherwise
        """
        if self.process is not None:
            logger.warning("Watch process is already running")
            return False

        try:
            # Build the command to run cicada watch
            cmd = [
                sys.executable,
                "-m",
                "cicada.cli",
                "watch",
                str(self.repo_path),
                "--debounce",
                str(self.debounce),
                "--quiet",  # Suppress progress output for background process
            ]

            # Add indexing mode flag
            if self.indexing_mode == "embeddings":
                cmd.append("--embeddings")
            else:
                cmd.append("--keywords")

            # Log to stderr so it doesn't interfere with MCP protocol
            print(
                f"Starting watch process for {self.repo_path} (mode={self.indexing_mode}, debounce={self.debounce}s)...",
                file=sys.stderr,
            )

            # Start the watch process
            # Use stdout=sys.stderr to redirect watch output to stderr
            # This prevents it from interfering with the MCP protocol on stdout
            self.process = subprocess.Popen(
                cmd,
                stdout=sys.stderr,
                stderr=sys.stderr,
                # Create new process group so it doesn't receive signals from parent's terminal
                start_new_session=True,
            )

            # Verify the process actually started and didn't crash immediately
            time.sleep(0.1)  # Brief delay to allow process to crash if it's going to
            if self.process.poll() is not None:
                print(
                    f"Watch process exited immediately with code {self.process.returncode}",
                    file=sys.stderr,
                )
                self.process = None
                return False

            # Register cleanup handler (unless disabled for testing)
            if self._register_atexit and not self._cleanup_registered:
                atexit.register(self._cleanup)
                self._cleanup_registered = True

            print(f"Watch process started (PID: {self.process.pid})", file=sys.stderr)
            return True

        except (FileNotFoundError, PermissionError, OSError) as e:
            # Expected failures - bad config, permissions, or OS-level issues
            logger.error(f"Cannot start watch process: {e}")
            print(f"Error: Cannot start watch process: {e}", file=sys.stderr)
            print("\nPossible causes:", file=sys.stderr)
            print("  - Python interpreter not found", file=sys.stderr)
            print("  - No execute permission", file=sys.stderr)
            print("  - Repository path invalid", file=sys.stderr)
            print("  - System resource issues", file=sys.stderr)
            return False

        except (ImportError, ModuleNotFoundError) as e:
            # Module missing - installation problem
            logger.error(f"Cicada module import failed: {e}")
            print(f"Error: Cicada installation appears corrupted: {e}", file=sys.stderr)
            print("Try reinstalling: uv tool install --force cicada-mcp", file=sys.stderr)
            raise RuntimeError(f"Corrupted installation: {e}") from e

        except (MemoryError, SystemError) as e:
            # System-level failures - cannot recover
            logger.critical(f"System error starting watch process: {e}")
            print(f"CRITICAL: System error prevents watch process: {e}", file=sys.stderr)
            raise RuntimeError(f"System failure: {e}") from e

        except Exception as e:
            # Unknown errors - log details and fail loudly
            logger.exception("Unexpected error starting watch process")
            print(f"ERROR: Unexpected failure starting watch process: {e}", file=sys.stderr)
            raise RuntimeError(f"Unexpected error: {e}") from e

    def stop(self) -> None:
        """Stop the watch process gracefully."""
        if self.process is None:
            return

        pid = self.process.pid  # Save PID before any cleanup
        try:
            print(f"Stopping watch process (PID: {pid})...", file=sys.stderr)

            # Try graceful termination first (SIGTERM)
            if self._terminate_process(signal.SIGTERM):
                print("Watch process stopped gracefully", file=sys.stderr)
            else:
                # Force kill if graceful termination timed out (SIGKILL)
                print("Watch process didn't stop gracefully, forcing...", file=sys.stderr)
                self._terminate_process(signal.SIGKILL, force=True)
                print("Watch process killed", file=sys.stderr)

        except (ProcessLookupError, PermissionError) as e:
            # Expected errors when process is already gone
            logger.warning(f"Process {pid} already terminated: {e}")
            print(f"Warning: Watch process {pid} already terminated", file=sys.stderr)
            # Clear process reference since process is gone
            self.process = None
        except Exception as e:
            # Unexpected errors - log with full context and warn user
            logger.exception(f"Unexpected error stopping watch process {pid}")
            print(f"ERROR: Failed to stop watch process {pid}: {e}", file=sys.stderr)
            print(
                "Warning: Process may still be running. Manual cleanup may be needed.",
                file=sys.stderr,
            )
            raise  # Re-raise to propagate error
        else:
            # Only clear process reference if we successfully stopped it (no exceptions)
            self.process = None

    def _terminate_process(self, sig: signal.Signals, force: bool = False) -> bool:
        """
        Terminate the process using the specified signal.

        This method handles platform differences (Unix vs Windows) and gracefully
        falls back if process group operations aren't available or fail.

        Args:
            sig: Signal to send (SIGTERM for graceful, SIGKILL for force)
            force: If True, waits indefinitely; if False, times out after 5 seconds

        Returns:
            True if process terminated successfully within timeout, False otherwise

        Raises:
            ValueError: If process is None
        """
        if self.process is None:
            raise ValueError("Cannot terminate a None process")

        # Send termination signal
        if not self._send_termination_signal(sig):
            return True  # Process already gone

        # Wait for process to exit
        if force:
            # Force kill - wait without timeout
            self.process.wait()
            return True

        # Graceful termination with timeout
        try:
            self.process.wait(timeout=5)
            return True
        except subprocess.TimeoutExpired:
            return False

    def _send_termination_signal(self, sig: signal.Signals) -> bool:
        """Send termination signal to process.

        Returns:
            True if signal was sent, False if process already gone
        """
        assert self.process is not None, "Process should not be None"
        try:
            # Try process group termination on Unix-like systems
            if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                try:
                    os.killpg(os.getpgid(self.process.pid), sig)
                except (ProcessLookupError, PermissionError, AttributeError):
                    # Fall back to direct process termination
                    self._send_direct_signal(sig)
            else:
                # Windows or platforms without killpg - use direct termination
                self._send_direct_signal(sig)
            return True
        except (ProcessLookupError, PermissionError) as e:
            # Process already gone or cannot signal - consider success
            logger.info(f"Process {self.process.pid} termination: {e}")
            return False

    def _send_direct_signal(self, sig: signal.Signals) -> None:
        """Send signal directly to process."""
        assert self.process is not None, "Process should not be None"
        if sig == signal.SIGTERM:
            self.process.terminate()
        else:
            self.process.kill()

    def _cleanup(self) -> None:
        """Cleanup handler registered with atexit."""
        try:
            self.stop()
        except Exception as e:
            # Don't re-raise during atexit - just log the error and let process exit
            logger.exception("Error during atexit cleanup")
            print(f"Warning: Error stopping watch process during cleanup: {e}", file=sys.stderr)
            # Don't re-raise - let process exit cleanly

    def is_running(self) -> bool:
        """
        Check if the watch process is running.

        Returns:
            True if the process is running, False otherwise
        """
        if self.process is None:
            return False

        # Check if process is still running
        return self.process.poll() is None


# Global watch manager instance
_watch_manager: WatchProcessManager | None = None


def get_watch_manager() -> WatchProcessManager | None:
    """Get the global watch manager instance."""
    return _watch_manager


def set_watch_manager(manager: WatchProcessManager | None) -> None:
    """Set the global watch manager instance."""
    global _watch_manager
    _watch_manager = manager


def start_watch_process(
    repo_path: str | Path, indexing_mode: str = "keywords", debounce: float = 2.0
) -> bool:
    """
    Start a watch process for the given repository.

    This is a convenience function that creates and starts a WatchProcessManager.

    Args:
        repo_path: Path to the repository to watch
        indexing_mode: Indexing mode ("keywords" or "embeddings")
        debounce: Debounce interval in seconds

    Returns:
        True if started successfully, False otherwise
    """
    manager = WatchProcessManager(repo_path, indexing_mode, debounce)
    if manager.start():
        set_watch_manager(manager)
        return True
    return False


def stop_watch_process() -> None:
    """Stop the global watch process if running."""
    manager = get_watch_manager()
    if manager is not None:
        manager.stop()
        set_watch_manager(None)
