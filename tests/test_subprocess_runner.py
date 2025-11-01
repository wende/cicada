"""
Tests for cicada/utils/subprocess_runner.py
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from cicada.utils.subprocess_runner import (
    SubprocessRunner,
    run_gh_command,
    run_git_command,
)


class TestSubprocessRunner:
    """Tests for SubprocessRunner class"""

    @pytest.mark.parametrize(
        "cwd,verbose,expected_cwd,expected_verbose",
        [
            (None, False, None, False),  # Default initialization
            (".", False, Path("."), False),  # String cwd
            (Path("/tmp"), False, Path("/tmp"), False),  # Path cwd
            (None, True, None, True),  # Verbose flag
        ],
    )
    def test_initialization(self, cwd, verbose, expected_cwd, expected_verbose):
        """Should initialize with correct parameters"""
        runner = SubprocessRunner(cwd=cwd, verbose=verbose)
        if expected_cwd is None:
            assert runner.cwd is None
        else:
            assert runner.cwd == expected_cwd
            assert isinstance(runner.cwd, Path)
        assert runner.verbose == expected_verbose

    @pytest.mark.parametrize(
        "command,expected_type",
        [
            (["echo", "hello"], list),
            ("echo hello", str),
        ],
    )
    def test_run_command_formats(self, command, expected_type, monkeypatch):
        """Should handle both list and string commands"""
        mock_result = Mock(returncode=0, stdout="output")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        runner = SubprocessRunner()
        result = runner.run(command)
        assert result == mock_result

    def test_run_with_cwd(self, monkeypatch, tmp_path):
        """Should pass cwd to subprocess.run"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("cwd"))
            return Mock(returncode=0, stdout="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        runner = SubprocessRunner(cwd=tmp_path)
        runner.run(["ls"])
        assert calls[0] == tmp_path

    def test_verbose_mode(self, monkeypatch, capsys):
        """Should print stdout when verbose=True"""
        mock_result = Mock(returncode=0, stdout="Command output")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        runner = SubprocessRunner(verbose=True)
        runner.run(["echo", "test"])

        captured = capsys.readouterr()
        assert "Command output" in captured.err

    @pytest.mark.parametrize(
        "exception_class,exception_args,expected_message",
        [
            (subprocess.CalledProcessError, (1, "cmd"), "Command failed"),
            (subprocess.TimeoutExpired, ("cmd", 5), "timed out"),
        ],
    )
    def test_error_handling_verbose(
        self, exception_class, exception_args, expected_message, monkeypatch, capsys
    ):
        """Should print error details when verbose=True"""

        def mock_run(*_args, **_kwargs):
            error = exception_class(*exception_args)
            if hasattr(error, "stderr"):
                error.stderr = "Error details"
            raise error

        monkeypatch.setattr(subprocess, "run", mock_run)
        runner = SubprocessRunner(verbose=True)

        with pytest.raises(exception_class):
            runner.run(["cmd"])

        captured = capsys.readouterr()
        assert expected_message in captured.err

    def test_error_handling_non_verbose(self, monkeypatch, capsys):
        """Should not print errors when verbose=False"""

        def mock_run(*_args, **_kwargs):
            raise subprocess.CalledProcessError(1, "cmd")

        monkeypatch.setattr(subprocess, "run", mock_run)
        runner = SubprocessRunner(verbose=False)

        with pytest.raises(subprocess.CalledProcessError):
            runner.run(["cmd"])

        captured = capsys.readouterr()
        assert captured.err == ""

    @pytest.mark.parametrize(
        "method,command_input,expected_prefix",
        [
            ("run_git_command", ["status"], ["git", "status"]),
            ("run_git_command", "status", ["git", "status"]),
            ("run_gh_command", ["pr", "list"], ["gh", "pr", "list"]),
            ("run_gh_command", "pr list", ["gh", "pr", "list"]),
        ],
    )
    def test_command_prefixes(self, method, command_input, expected_prefix, monkeypatch):
        """Should prepend correct command prefix (git/gh)"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            return Mock(returncode=0, stdout="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        runner = SubprocessRunner()
        getattr(runner, method)(command_input)
        assert calls[0] == expected_prefix


class TestConvenienceFunctions:
    """Tests for module-level convenience functions"""

    @pytest.mark.parametrize(
        "func,command,expected_prefix",
        [
            (run_git_command, ["status"], ["git", "status"]),
            (run_gh_command, ["pr", "list"], ["gh", "pr", "list"]),
        ],
    )
    def test_convenience_functions(self, func, command, expected_prefix, monkeypatch):
        """Should delegate to SubprocessRunner correctly"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            return Mock(returncode=0, stdout="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = func(command)
        assert calls[0] == expected_prefix
        assert result is not None

    def test_convenience_function_with_cwd(self, monkeypatch, tmp_path):
        """Should pass cwd parameter correctly"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("cwd"))
            return Mock(returncode=0, stdout="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        run_git_command("status", cwd=tmp_path)
        assert calls[0] == tmp_path

    def test_convenience_function_verbose(self, monkeypatch, capsys):
        """Should handle verbose parameter"""
        mock_result = Mock(returncode=0, stdout="Output")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        run_git_command("status", verbose=True)

        captured = capsys.readouterr()
        assert "Output" in captured.err
