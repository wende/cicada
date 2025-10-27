"""
Comprehensive tests for cicada/utils/subprocess_runner.py
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock
from cicada.utils.subprocess_runner import (
    SubprocessRunner,
    run_git_command,
    run_gh_command,
)


class TestSubprocessRunner:
    """Tests for SubprocessRunner class"""

    def test_init_default(self):
        """Test default initialization"""
        runner = SubprocessRunner()
        assert runner.cwd is None
        assert runner.verbose is False

    def test_init_with_cwd_string(self, tmp_path):
        """Test initialization with cwd as string"""
        runner = SubprocessRunner(cwd=str(tmp_path))
        assert runner.cwd == tmp_path
        assert isinstance(runner.cwd, Path)

    def test_init_with_cwd_path(self, tmp_path):
        """Test initialization with cwd as Path"""
        runner = SubprocessRunner(cwd=tmp_path)
        assert runner.cwd == tmp_path

    def test_init_with_verbose(self):
        """Test initialization with verbose flag"""
        runner = SubprocessRunner(verbose=True)
        assert runner.verbose is True

    def test_run_simple_command_list(self, monkeypatch):
        """Test running a simple command as list"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        result = runner.run(["echo", "hello"])

        assert result == mock_result

    def test_run_simple_command_string(self, monkeypatch):
        """Test running a simple command as string"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        runner = SubprocessRunner()
        result = runner.run("echo hello")

        assert result == mock_result

    def test_run_with_cwd(self, monkeypatch, tmp_path):
        """Test running command with custom working directory"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("cwd"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner(cwd=tmp_path)
        runner.run(["ls"])

        assert calls[0] == tmp_path

    def test_run_verbose_with_output(self, monkeypatch, capsys):
        """Test verbose mode prints stdout"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        runner = SubprocessRunner(verbose=True)
        runner.run(["echo", "test"])

        captured = capsys.readouterr()
        assert "Command output" in captured.err

    def test_run_verbose_without_output(self, monkeypatch, capsys):
        """Test verbose mode with no stdout"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = None

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        runner = SubprocessRunner(verbose=True)
        runner.run(["echo", "test"])

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_run_with_capture_output_false(self, monkeypatch):
        """Test running without capturing output"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("capture_output"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run(["ls"], capture_output=False)

        assert calls[0] is False

    def test_run_with_text_false(self, monkeypatch):
        """Test running with text=False (bytes mode)"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("text"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = b""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run(["ls"], text=False)

        assert calls[0] is False

    def test_run_with_check_false(self, monkeypatch):
        """Test running with check=False"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("check"))
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        result = runner.run(["false"], check=False)

        assert calls[0] is False
        assert result.returncode == 1

    def test_run_with_timeout(self, monkeypatch):
        """Test running with timeout parameter"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("timeout"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run(["sleep", "1"], timeout=5)

        assert calls[0] == 5

    def test_run_called_process_error_verbose(self, monkeypatch, capsys):
        """Test CalledProcessError handling with verbose mode"""

        def mock_run(*args, **kwargs):
            error = subprocess.CalledProcessError(1, "cmd")
            error.stderr = "Error message"
            raise error

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner(verbose=True)

        with pytest.raises(subprocess.CalledProcessError):
            runner.run(["false"])

        captured = capsys.readouterr()
        assert "Command failed" in captured.err
        assert "Error message" in captured.err

    def test_run_called_process_error_no_stderr(self, monkeypatch, capsys):
        """Test CalledProcessError without stderr"""

        def mock_run(*args, **kwargs):
            error = subprocess.CalledProcessError(1, "cmd")
            error.stderr = None
            raise error

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner(verbose=True)

        with pytest.raises(subprocess.CalledProcessError):
            runner.run(["false"])

        captured = capsys.readouterr()
        assert "Command failed" in captured.err

    def test_run_called_process_error_non_verbose(self, monkeypatch, capsys):
        """Test CalledProcessError without verbose mode"""

        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "cmd")

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner(verbose=False)

        with pytest.raises(subprocess.CalledProcessError):
            runner.run(["false"])

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_run_timeout_expired_verbose(self, monkeypatch, capsys):
        """Test TimeoutExpired handling with verbose mode"""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("cmd", 5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner(verbose=True)

        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(["sleep", "10"], timeout=5)

        captured = capsys.readouterr()
        assert "timed out" in captured.err

    def test_run_timeout_expired_non_verbose(self, monkeypatch, capsys):
        """Test TimeoutExpired without verbose mode"""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("cmd", 5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner(verbose=False)

        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(["sleep", "10"], timeout=5)

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_run_git_command_with_list(self, monkeypatch):
        """Test running git command with list args"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run_git_command(["status", "--short"])

        assert calls[0] == ["git", "status", "--short"]

    def test_run_git_command_with_string(self, monkeypatch):
        """Test running git command with string args"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run_git_command("status --short")

        assert calls[0] == "git status --short"

    def test_run_git_command_with_check_false(self, monkeypatch):
        """Test running git command with check=False"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("check"))
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run_git_command("status", check=False)

        assert calls[0] is False

    def test_run_gh_command_with_list(self, monkeypatch):
        """Test running gh command with list args"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run_gh_command(["pr", "list"])

        assert calls[0] == ["gh", "pr", "list"]

    def test_run_gh_command_with_string(self, monkeypatch):
        """Test running gh command with string args"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run_gh_command("api repos/owner/repo")

        assert calls[0] == "gh api repos/owner/repo"

    def test_run_gh_command_with_check_false(self, monkeypatch):
        """Test running gh command with check=False"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("check"))
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = SubprocessRunner()
        runner.run_gh_command("pr list", check=False)

        assert calls[0] is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions"""

    def test_run_git_command_function(self, monkeypatch):
        """Test run_git_command convenience function"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = run_git_command(["status"])

        assert calls[0] == ["git", "status"]
        assert result is not None

    def test_run_git_command_with_cwd(self, monkeypatch, tmp_path):
        """Test run_git_command with cwd parameter"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("cwd"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        run_git_command("status", cwd=tmp_path)

        assert calls[0] == tmp_path

    def test_run_git_command_with_check_false(self, monkeypatch):
        """Test run_git_command with check=False"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("check"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        run_git_command("status", check=False)

        assert calls[0] is False

    def test_run_git_command_with_verbose(self, monkeypatch, capsys):
        """Test run_git_command with verbose=True"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Git output"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        run_git_command("status", verbose=True)

        captured = capsys.readouterr()
        assert "Git output" in captured.err

    def test_run_gh_command_function(self, monkeypatch):
        """Test run_gh_command convenience function"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(args[0])
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = run_gh_command(["pr", "list"])

        assert calls[0] == ["gh", "pr", "list"]
        assert result is not None

    def test_run_gh_command_with_cwd(self, monkeypatch, tmp_path):
        """Test run_gh_command with cwd parameter"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("cwd"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        run_gh_command("pr list", cwd=tmp_path)

        assert calls[0] == tmp_path

    def test_run_gh_command_with_check_false(self, monkeypatch):
        """Test run_gh_command with check=False"""
        calls = []

        def mock_run(*args, **kwargs):
            calls.append(kwargs.get("check"))
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        run_gh_command("pr list", check=False)

        assert calls[0] is False

    def test_run_gh_command_with_verbose(self, monkeypatch, capsys):
        """Test run_gh_command with verbose=True"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "GH output"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: mock_result)

        run_gh_command("pr list", verbose=True)

        captured = capsys.readouterr()
        assert "GH output" in captured.err
