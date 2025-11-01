"""
Subprocess execution utilities.

This module provides centralized subprocess execution with consistent
error handling and logging patterns.
"""

import shlex
import subprocess
import sys
from pathlib import Path


class SubprocessRunner:
    """
    Centralized subprocess execution with error handling.

    This class provides consistent subprocess execution patterns used
    throughout the codebase, reducing duplication and ensuring uniform
    error handling.
    """

    def __init__(self, cwd: str | Path | None = None, verbose: bool = False):
        """
        Initialize the subprocess runner.

        Args:
            cwd: Working directory for commands (default: current directory)
            verbose: If True, print command output to stderr
        """
        self.cwd = Path(cwd) if cwd else None
        self.verbose = verbose

    def run(
        self,
        cmd: str | list[str],
        capture_output: bool = True,
        text: bool = True,
        check: bool = True,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with error handling.

        Args:
            cmd: Command to execute (string or list)
            capture_output: Whether to capture stdout/stderr
            text: Whether to return output as text (vs bytes)
            check: Whether to raise exception on non-zero exit
            timeout: Optional timeout in seconds

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
            subprocess.TimeoutExpired: If timeout is reached
        """
        # Convert string commands to list for safety and compatibility
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.cwd,
                capture_output=capture_output,
                text=text,
                check=check,
                timeout=timeout,
            )

            if self.verbose and result.stdout:
                print(result.stdout, file=sys.stderr)

            return result

        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"Command failed: {cmd}", file=sys.stderr)
                if e.stderr:
                    print(f"Error: {e.stderr}", file=sys.stderr)
            raise
        except subprocess.TimeoutExpired:
            if self.verbose:
                print(f"Command timed out: {cmd}", file=sys.stderr)
            raise

    def run_git_command(
        self,
        args: str | list[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a git command with consistent error handling.

        Args:
            args: Git command arguments (without 'git')
            check: Whether to raise exception on non-zero exit

        Returns:
            CompletedProcess instance

        Example:
            runner.run_git_command(['status', '--short'])
            runner.run_git_command('log --oneline -n 5')
        """
        cmd = f"git {args}" if isinstance(args, str) else ["git"] + args

        return self.run(cmd, check=check)

    def run_gh_command(
        self,
        args: str | list[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a GitHub CLI command with consistent error handling.

        Args:
            args: gh command arguments (without 'gh')
            check: Whether to raise exception on non-zero exit

        Returns:
            CompletedProcess instance

        Example:
            runner.run_gh_command(['pr', 'list'])
            runner.run_gh_command('api repos/owner/repo/pulls')
        """
        cmd = f"gh {args}" if isinstance(args, str) else ["gh"] + args

        return self.run(cmd, check=check)


# Convenience functions for simple use cases


def run_git_command(
    args: str | list[str],
    cwd: str | Path | None = None,
    check: bool = True,
    verbose: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a git command (convenience function).

    Args:
        args: Git command arguments (without 'git')
        cwd: Working directory
        check: Whether to raise exception on non-zero exit
        verbose: Whether to print output

    Returns:
        CompletedProcess instance
    """
    runner = SubprocessRunner(cwd=cwd, verbose=verbose)
    return runner.run_git_command(args, check=check)


def run_gh_command(
    args: str | list[str],
    cwd: str | Path | None = None,
    check: bool = True,
    verbose: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a GitHub CLI command (convenience function).

    Args:
        args: gh command arguments (without 'gh')
        cwd: Working directory
        check: Whether to raise exception on non-zero exit
        verbose: Whether to print output

    Returns:
        CompletedProcess instance
    """
    runner = SubprocessRunner(cwd=cwd, verbose=verbose)
    return runner.run_gh_command(args, check=check)
