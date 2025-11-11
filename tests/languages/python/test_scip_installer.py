"""Comprehensive tests for SCIP Python installer utilities."""

import pytest
from unittest.mock import patch, Mock

from cicada.languages.python.scip_installer import SCIPPythonInstaller


class TestSCIPPythonInstaller:
    """Test SCIP-Python installer utilities."""

    def test_is_npm_available_when_found(self):
        """Should return True when npm is in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/npm"

            result = SCIPPythonInstaller.is_npm_available()

            assert result is True
            mock_which.assert_called_once_with("npm")

    def test_is_npm_available_when_not_found(self):
        """Should return False when npm is not in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = SCIPPythonInstaller.is_npm_available()

            assert result is False

    def test_is_scip_python_installed_when_found(self):
        """Should return True when scip-python is in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/scip-python"

            result = SCIPPythonInstaller.is_scip_python_installed()

            assert result is True
            mock_which.assert_called_once_with("scip-python")

    def test_is_scip_python_installed_when_not_found(self):
        """Should return False when scip-python is not in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            result = SCIPPythonInstaller.is_scip_python_installed()

            assert result is False

    def test_install_scip_python_success(self):
        """Should successfully install scip-python via npm."""
        with patch.object(SCIPPythonInstaller, "is_npm_available") as mock_npm:
            mock_npm.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                result = SCIPPythonInstaller.install_scip_python()

                assert result is True
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args[0][0] == ["npm", "install", "-g", "@sourcegraph/scip-python"]

    def test_install_scip_python_npm_not_available(self):
        """Should raise RuntimeError when npm is not available."""
        with patch.object(SCIPPythonInstaller, "is_npm_available") as mock_npm:
            mock_npm.return_value = False

            with pytest.raises(RuntimeError) as exc_info:
                SCIPPythonInstaller.install_scip_python()

            assert "npm is required" in str(exc_info.value)
            assert "https://nodejs.org" in str(exc_info.value)

    def test_install_scip_python_installation_fails(self):
        """Should return False when npm install fails."""
        with patch.object(SCIPPythonInstaller, "is_npm_available") as mock_npm:
            mock_npm.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "npm ERR! installation failed"
                mock_run.return_value = mock_result

                result = SCIPPythonInstaller.install_scip_python()

                assert result is False

    def test_install_scip_python_verbose_output(self, capsys):
        """Should print output when verbose is True."""
        with patch.object(SCIPPythonInstaller, "is_npm_available") as mock_npm:
            mock_npm.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                SCIPPythonInstaller.install_scip_python(verbose=True)

                captured = capsys.readouterr()
                assert "Running:" in captured.out
                assert "npm install -g @sourcegraph/scip-python" in captured.out

    def test_install_scip_python_verbose_error(self, capsys):
        """Should print error when verbose and installation fails."""
        with patch.object(SCIPPythonInstaller, "is_npm_available") as mock_npm:
            mock_npm.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "Installation error"
                mock_run.return_value = mock_result

                result = SCIPPythonInstaller.install_scip_python(verbose=True)

                assert result is False
                captured = capsys.readouterr()
                assert "Error installing scip-python" in captured.out
                assert "Installation error" in captured.out

    def test_get_scip_python_version_when_installed(self):
        """Should return version string when scip-python is installed."""
        with patch.object(SCIPPythonInstaller, "is_scip_python_installed") as mock_installed:
            mock_installed.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "0.3.15\n"
                mock_run.return_value = mock_result

                version = SCIPPythonInstaller.get_scip_python_version()

                assert version == "0.3.15"
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args[0][0] == ["scip-python", "--version"]

    def test_get_scip_python_version_when_not_installed(self):
        """Should return None when scip-python is not installed."""
        with patch.object(SCIPPythonInstaller, "is_scip_python_installed") as mock_installed:
            mock_installed.return_value = False

            version = SCIPPythonInstaller.get_scip_python_version()

            assert version is None

    def test_get_scip_python_version_command_fails(self):
        """Should return None when version command fails."""
        with patch.object(SCIPPythonInstaller, "is_scip_python_installed") as mock_installed:
            mock_installed.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_run.return_value = mock_result

                version = SCIPPythonInstaller.get_scip_python_version()

                assert version is None

    def test_get_scip_python_version_strips_whitespace(self):
        """Should strip whitespace from version output."""
        with patch.object(SCIPPythonInstaller, "is_scip_python_installed") as mock_installed:
            mock_installed.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "  0.3.15  \n"
                mock_run.return_value = mock_result

                version = SCIPPythonInstaller.get_scip_python_version()

                assert version == "0.3.15"

    def test_install_scip_python_subprocess_args(self):
        """Should pass correct arguments to subprocess.run."""
        with patch.object(SCIPPythonInstaller, "is_npm_available") as mock_npm:
            mock_npm.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                SCIPPythonInstaller.install_scip_python()

                # Verify subprocess.run was called with correct args
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["capture_output"] is True
                assert call_kwargs["text"] is True
