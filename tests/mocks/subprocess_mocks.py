"""
Author: Cursor(Auto)

Mock infrastructure for SubprocessRunner testing.

Provides configurable mocks for subprocess operations that can be reused
across different test scenarios without tight coupling to implementation details.
"""

import subprocess
from typing import Any


class MockCompletedProcess:
    """
    Mock subprocess.CompletedProcess for testing.

    Provides a realistic interface that matches subprocess.CompletedProcess
    while allowing easy configuration of return values.
    """

    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        args: str | list[str] | None = None,
    ):
        """
        Initialize mock completed process.

        Args:
            returncode: Process exit code
            stdout: Standard output content
            stderr: Standard error content
            args: Command arguments that were executed
        """
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.args = args or []


class MockSubprocessRunner:
    """
    Configurable mock for SubprocessRunner.

    Allows setting up expected command responses and verifying that
    commands were called with correct parameters.
    """

    def __init__(self):
        """Initialize the mock subprocess runner."""
        self.git_responses: dict[str, MockCompletedProcess] = {}
        self.gh_responses: dict[str, MockCompletedProcess] = {}
        self.generic_responses: dict[str, MockCompletedProcess] = {}
        self.call_history: list[dict[str, Any]] = []

    def add_git_response(
        self, command: str | list[str], response: MockCompletedProcess
    ) -> None:
        """
        Add a git command response.

        Args:
            command: Git command (without 'git' prefix)
            response: Mock response to return
        """
        key = self._normalize_command(command)
        self.git_responses[key] = response

    def add_gh_response(
        self, command: str | list[str], response: MockCompletedProcess
    ) -> None:
        """
        Add a GitHub CLI command response.

        Args:
            command: gh command (without 'gh' prefix)
            response: Mock response to return
        """
        key = self._normalize_command(command)
        self.gh_responses[key] = response

    def add_generic_response(
        self, command: str | list[str], response: MockCompletedProcess
    ) -> None:
        """
        Add a generic command response.

        Args:
            command: Full command
            response: Mock response to return
        """
        key = self._normalize_command(command)
        self.generic_responses[key] = response

    def _normalize_command(self, command: str | list[str]) -> str:
        """
        Normalize command to string for consistent lookup.

        Args:
            command: Command as string or list

        Returns:
            Normalized command string
        """
        if isinstance(command, list):
            return " ".join(str(arg) for arg in command)
        return str(command)

    def run(
        self,
        cmd: str | list[str],
        capture_output: bool = True,
        text: bool = True,
        check: bool = True,
        timeout: int | None = None,
    ) -> MockCompletedProcess:
        """
        Mock implementation of SubprocessRunner.run.

        Args:
            cmd: Command to execute
            capture_output: Whether to capture output (ignored in mock)
            text: Whether to return text (ignored in mock)
            check: Whether to raise exception on non-zero exit
            timeout: Optional timeout (ignored in mock)

        Returns:
            Mock completed process

        Raises:
            subprocess.CalledProcessError: If check=True and returncode != 0
        """
        # Record the call
        self.call_history.append(
            {
                "cmd": cmd,
                "capture_output": capture_output,
                "text": text,
                "check": check,
                "timeout": timeout,
            }
        )

        # Look up response
        cmd_str = self._normalize_command(cmd)
        response = self._find_response(cmd_str)

        if response is None:
            # Default response for unmatched commands
            response = MockCompletedProcess(
                returncode=0, stdout="", stderr="", args=cmd
            )

        # Raise exception if check=True and command failed
        if check and response.returncode != 0:
            error = subprocess.CalledProcessError(
                response.returncode, cmd, response.stdout, response.stderr
            )
            raise error

        return response

    def run_git_command(
        self,
        args: str | list[str],
        check: bool = True,
    ) -> MockCompletedProcess:
        """
        Mock implementation of SubprocessRunner.run_git_command.

        Args:
            args: Git command arguments (without 'git')
            check: Whether to raise exception on non-zero exit

        Returns:
            Mock completed process
        """
        # Convert to full git command
        if isinstance(args, str):
            cmd = f"git {args}"
        else:
            cmd = ["git"] + args

        return self.run(cmd, check=check)

    def run_gh_command(
        self,
        args: str | list[str],
        check: bool = True,
    ) -> MockCompletedProcess:
        """
        Mock implementation of SubprocessRunner.run_gh_command.

        Args:
            args: gh command arguments (without 'gh')
            check: Whether to raise exception on non-zero exit

        Returns:
            Mock completed process
        """
        # Convert to full gh command
        if isinstance(args, str):
            cmd = f"gh {args}"
        else:
            cmd = ["gh"] + args

        return self.run(cmd, check=check)

    def _find_response(self, cmd_str: str) -> MockCompletedProcess | None:
        """
        Find response for a command.

        Args:
            cmd_str: Normalized command string

        Returns:
            Mock response or None if not found
        """
        # Try exact match first
        if cmd_str in self.git_responses:
            return self.git_responses[cmd_str]
        if cmd_str in self.gh_responses:
            return self.gh_responses[cmd_str]
        if cmd_str in self.generic_responses:
            return self.generic_responses[cmd_str]

        # Try partial matches for more flexible testing
        for key, response in self.git_responses.items():
            if self._command_matches(cmd_str, key):
                return response
        for key, response in self.gh_responses.items():
            if self._command_matches(cmd_str, key):
                return response
        for key, response in self.generic_responses.items():
            if self._command_matches(cmd_str, key):
                return response

        return None

    def _command_matches(self, cmd: str, pattern: str) -> bool:
        """
        Check if command matches pattern (supports partial matching).

        Args:
            cmd: Command to check
            pattern: Pattern to match against

        Returns:
            True if command matches pattern
        """
        # For exact matching, check if the pattern is contained in the command
        # This handles cases where the pattern is a subset of the full command
        return pattern in cmd

    def verify_called_with(
        self, expected_cmd: str | list[str], call_index: int = -1
    ) -> bool:
        """
        Verify that a command was called with expected arguments.

        Args:
            expected_cmd: Expected command
            call_index: Which call to check (-1 for last call)

        Returns:
            True if command matches
        """
        if not self.call_history:
            return False

        if call_index < 0:
            call_index = len(self.call_history) + call_index

        if call_index >= len(self.call_history):
            return False

        actual_cmd = self.call_history[call_index]["cmd"]
        expected_str = self._normalize_command(expected_cmd)
        actual_str = self._normalize_command(actual_cmd)

        return expected_str == actual_str

    def get_call_count(self) -> int:
        """
        Get total number of commands executed.

        Returns:
            Number of calls made
        """
        return len(self.call_history)

    def get_calls_for_command(self, command_pattern: str) -> list[dict[str, Any]]:
        """
        Get all calls matching a command pattern.

        Args:
            command_pattern: Pattern to match

        Returns:
            List of matching calls
        """
        return [
            call
            for call in self.call_history
            if self._command_matches(
                self._normalize_command(call["cmd"]), command_pattern
            )
        ]

    def reset(self) -> None:
        """Reset all recorded calls and responses."""
        self.call_history.clear()
        self.git_responses.clear()
        self.gh_responses.clear()
        self.generic_responses.clear()


# Factory functions for common scenarios


def create_git_command_mock(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> MockCompletedProcess:
    """
    Create a mock git command response.

    Args:
        returncode: Process exit code
        stdout: Standard output
        stderr: Standard error

    Returns:
        Mock completed process
    """
    return MockCompletedProcess(returncode=returncode, stdout=stdout, stderr=stderr)


def create_gh_command_mock(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> MockCompletedProcess:
    """
    Create a mock GitHub CLI command response.

    Args:
        returncode: Process exit code
        stdout: Standard output
        stderr: Standard error

    Returns:
        Mock completed process
    """
    return MockCompletedProcess(returncode=returncode, stdout=stdout, stderr=stderr)
