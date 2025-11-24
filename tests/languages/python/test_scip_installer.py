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
        """Should return False when scip-python is not in PATH or local."""
        with patch.object(SCIPPythonInstaller, "get_scip_python_path", return_value=None):
            result = SCIPPythonInstaller.is_scip_python_installed()

            assert result is False

    def test_get_scip_python_version_when_installed(self):
        """Should return version string when scip-python is installed."""
        with patch.object(SCIPPythonInstaller, "get_scip_python_path") as mock_path:
            mock_path.return_value = "/usr/local/bin/scip-python"

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "0.3.15\n"
                mock_run.return_value = mock_result

                version = SCIPPythonInstaller.get_scip_python_version()

                assert version == "0.3.15"
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args[0][0] == ["/usr/local/bin/scip-python", "--version"]

    def test_get_scip_python_version_when_not_installed(self):
        """Should return None when scip-python is not installed."""
        with patch.object(SCIPPythonInstaller, "get_scip_python_path") as mock_path:
            mock_path.return_value = None

            version = SCIPPythonInstaller.get_scip_python_version()

            assert version is None

    def test_get_scip_python_version_command_fails(self):
        """Should return None when version command fails."""
        with patch.object(SCIPPythonInstaller, "get_scip_python_path") as mock_path:
            mock_path.return_value = "/usr/local/bin/scip-python"

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_run.return_value = mock_result

                version = SCIPPythonInstaller.get_scip_python_version()

                assert version is None

    def test_get_scip_python_version_strips_whitespace(self):
        """Should strip whitespace from version output."""
        with patch.object(SCIPPythonInstaller, "get_scip_python_path") as mock_path:
            mock_path.return_value = "/usr/local/bin/scip-python"

            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "  0.3.15  \n"
                mock_run.return_value = mock_result

                version = SCIPPythonInstaller.get_scip_python_version()

                assert version == "0.3.15"

    def test_get_scip_python_path_global(self):
        """Should return global path when scip-python is in PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/scip-python"

            path = SCIPPythonInstaller.get_scip_python_path()

            assert path == "/usr/local/bin/scip-python"

    def test_get_scip_python_path_local(self):
        """Should return local path when not in PATH but installed locally."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            with patch("pathlib.Path.exists", return_value=True):
                path = SCIPPythonInstaller.get_scip_python_path()

                assert path == str(SCIPPythonInstaller.LOCAL_BIN_PATH)

    def test_get_scip_python_path_not_found(self):
        """Should return None when scip-python is not installed anywhere."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            with patch("pathlib.Path.exists", return_value=False):
                path = SCIPPythonInstaller.get_scip_python_path()

                assert path is None

    def test_install_locally_success(self):
        """Should install scip-python locally when npm is available."""
        with patch.object(SCIPPythonInstaller, "is_npm_available", return_value=True):
            with patch("pathlib.Path.mkdir"):
                with patch("subprocess.run") as mock_run:
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    with patch("pathlib.Path.exists", return_value=True):
                        result = SCIPPythonInstaller.install_locally()

                        assert result is True
                        mock_run.assert_called_once()

    def test_install_locally_no_npm(self):
        """Should return False when npm is not available."""
        with patch.object(SCIPPythonInstaller, "is_npm_available", return_value=False):
            result = SCIPPythonInstaller.install_locally()

            assert result is False
