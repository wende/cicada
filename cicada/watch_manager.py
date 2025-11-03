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
        tier: str = "regular",
        debounce: float = 2.0,
        register_atexit: bool = True,
    ):
        """
        Initialize the watch process manager.

        Args:
            repo_path: Path to the repository to watch
            tier: Indexing tier (fast, regular, or max)
            debounce: Debounce interval in seconds
            register_atexit: Whether to register atexit cleanup handler (disable for testing)
        """
        self.repo_path = Path(repo_path).resolve()
        self.tier = tier
        self.debounce = debounce
        self.process: subprocess.Popen | None = None
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
            ]

            # Add tier flag
            if self.tier == "fast":
                cmd.append("--fast")
            elif self.tier == "max":
                cmd.append("--max")
            else:
                cmd.append("--regular")

            # Log to stderr so it doesn't interfere with MCP protocol
            print(
                f"Starting watch process for {self.repo_path} (tier={self.tier}, debounce={self.debounce}s)...",
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

            # Register cleanup handler (unless disabled for testing)
            if self._register_atexit and not self._cleanup_registered:
                atexit.register(self._cleanup)
                self._cleanup_registered = True

            print(f"Watch process started (PID: {self.process.pid})", file=sys.stderr)
            return True

        except Exception as e:
            logger.exception("Failed to start watch process")
            print(f"Error starting watch process: {e}", file=sys.stderr)
            return False

    def stop(self) -> None:
        """Stop the watch process gracefully."""
        if self.process is None:
            return

        try:
            print(f"Stopping watch process (PID: {self.process.pid})...", file=sys.stderr)

            # Try graceful shutdown first with SIGTERM
            try:
                # Send SIGTERM to the process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                # Process already gone or can't signal - try direct termination
                self.process.terminate()

            # Wait up to 5 seconds for graceful shutdown
            try:
                self.process.wait(timeout=5)
                print("Watch process stopped gracefully", file=sys.stderr)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                print("Watch process didn't stop gracefully, forcing...", file=sys.stderr)
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    self.process.kill()
                self.process.wait()
                print("Watch process killed", file=sys.stderr)

        except Exception as e:
            logger.exception("Error stopping watch process")
            print(f"Error stopping watch process: {e}", file=sys.stderr)
        finally:
            self.process = None

    def _cleanup(self) -> None:
        """Cleanup handler registered with atexit."""
        self.stop()

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
    repo_path: str | Path, tier: str = "regular", debounce: float = 2.0
) -> bool:
    """
    Start a watch process for the given repository.

    This is a convenience function that creates and starts a WatchProcessManager.

    Args:
        repo_path: Path to the repository to watch
        tier: Indexing tier (fast, regular, or max)
        debounce: Debounce interval in seconds

    Returns:
        True if started successfully, False otherwise
    """
    manager = WatchProcessManager(repo_path, tier, debounce)
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
