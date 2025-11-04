"""Tests for Rust SCIP installer (rust-analyzer management)."""

import subprocess
from unittest.mock import patch, MagicMock
import pytest

from cicada.languages.rust.scip_installer import SCIPRustInstaller


class TestCargoAvailability:
    """Test cargo availability detection."""

    def test_is_cargo_available_returns_bool(self):
        """Should return a boolean value."""
        result = SCIPRustInstaller.is_cargo_available()
        assert isinstance(result, bool)

    @patch("shutil.which")
    def test_is_cargo_available_when_cargo_exists(self, mock_which):
        """Should return True when cargo is in PATH."""
        mock_which.return_value = "/usr/bin/cargo"
        assert SCIPRustInstaller.is_cargo_available() is True
        mock_which.assert_called_once_with("cargo")

    @patch("shutil.which")
    def test_is_cargo_available_when_cargo_missing(self, mock_which):
        """Should return False when cargo is not in PATH."""
        mock_which.return_value = None
        assert SCIPRustInstaller.is_cargo_available() is False
        mock_which.assert_called_once_with("cargo")


class TestRustAnalyzerAvailability:
    """Test rust-analyzer availability detection."""

    def test_is_rust_analyzer_installed_returns_bool(self):
        """Should return a boolean value."""
        result = SCIPRustInstaller.is_rust_analyzer_installed()
        assert isinstance(result, bool)

    @patch("shutil.which")
    def test_is_rust_analyzer_installed_when_exists(self, mock_which):
        """Should return True when rust-analyzer is in PATH."""
        mock_which.return_value = "/usr/bin/rust-analyzer"
        assert SCIPRustInstaller.is_rust_analyzer_installed() is True
        mock_which.assert_called_once_with("rust-analyzer")

    @patch("shutil.which")
    def test_is_rust_analyzer_installed_when_missing(self, mock_which):
        """Should return False when rust-analyzer is not in PATH."""
        mock_which.return_value = None
        assert SCIPRustInstaller.is_rust_analyzer_installed() is False
        mock_which.assert_called_once_with("rust-analyzer")


class TestRustAnalyzerInstallation:
    """Test rust-analyzer installation."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_rust_analyzer_success(self, mock_which, mock_run):
        """Should successfully install rust-analyzer via rustup."""
        mock_which.return_value = "/usr/bin/rustup"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = SCIPRustInstaller.install_rust_analyzer(verbose=False)

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["rustup", "component", "add", "rust-analyzer"]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_rust_analyzer_failure(self, mock_which, mock_run):
        """Should return False when installation fails."""
        mock_which.return_value = "/usr/bin/rustup"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Installation failed"
        )

        result = SCIPRustInstaller.install_rust_analyzer(verbose=False)

        assert result is False

    @patch("shutil.which")
    def test_install_rust_analyzer_no_rustup(self, mock_which):
        """Should raise RuntimeError when rustup is not available."""
        mock_which.return_value = None

        with pytest.raises(RuntimeError, match="rustup is required"):
            SCIPRustInstaller.install_rust_analyzer(verbose=False)

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_rust_analyzer_verbose_output(self, mock_which, mock_run, capsys):
        """Should print installation command when verbose=True."""
        mock_which.return_value = "/usr/bin/rustup"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        SCIPRustInstaller.install_rust_analyzer(verbose=True)

        captured = capsys.readouterr()
        assert "Running:" in captured.out
        assert "rustup" in captured.out


class TestRustAnalyzerVersion:
    """Test rust-analyzer version detection."""

    @patch("subprocess.run")
    @patch.object(SCIPRustInstaller, "is_rust_analyzer_installed")
    def test_get_version_when_installed(self, mock_installed, mock_run):
        """Should return version string when rust-analyzer is installed."""
        mock_installed.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0, stdout="rust-analyzer 1.76.0\n", stderr=""
        )

        version = SCIPRustInstaller.get_rust_analyzer_version()

        assert version == "rust-analyzer 1.76.0"
        mock_run.assert_called_once_with(
            ["rust-analyzer", "--version"], capture_output=True, text=True
        )

    @patch.object(SCIPRustInstaller, "is_rust_analyzer_installed")
    def test_get_version_when_not_installed(self, mock_installed):
        """Should return None when rust-analyzer is not installed."""
        mock_installed.return_value = False

        version = SCIPRustInstaller.get_rust_analyzer_version()

        assert version is None

    @patch("subprocess.run")
    @patch.object(SCIPRustInstaller, "is_rust_analyzer_installed")
    def test_get_version_when_command_fails(self, mock_installed, mock_run):
        """Should return None when version command fails."""
        mock_installed.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

        version = SCIPRustInstaller.get_rust_analyzer_version()

        assert version is None


class TestInstallationIntegration:
    """Integration tests for installation workflow."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_complete_installation_workflow(self, mock_which, mock_run):
        """Should complete full installation workflow."""
        # Setup: rustup is available, rust-analyzer is not
        def which_side_effect(cmd):
            if cmd == "rustup":
                return "/usr/bin/rustup"
            elif cmd == "rust-analyzer":
                return None  # Not installed initially
            return None

        mock_which.side_effect = which_side_effect
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Act: Install rust-analyzer
        result = SCIPRustInstaller.install_rust_analyzer(verbose=False)

        # Assert: Installation succeeded
        assert result is True
        mock_run.assert_called_once()


class TestErrorHandling:
    """Test error handling in installation."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_handles_permission_error(self, mock_which, mock_run):
        """Should handle permission errors gracefully."""
        mock_which.return_value = "/usr/bin/rustup"
        mock_run.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            SCIPRustInstaller.install_rust_analyzer(verbose=False)

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_handles_subprocess_error(self, mock_which, mock_run):
        """Should handle subprocess errors."""
        mock_which.return_value = "/usr/bin/rustup"
        mock_run.side_effect = subprocess.CalledProcessError(1, "rustup")

        with pytest.raises(subprocess.CalledProcessError):
            SCIPRustInstaller.install_rust_analyzer(verbose=False)
