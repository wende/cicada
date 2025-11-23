"""Manage scip-python installation.

Provides utilities to check for scip-python availability.
"""

import shutil
import subprocess


class SCIPPythonInstaller:
    """Manage scip-python availability checks."""

    @staticmethod
    def is_npm_available() -> bool:
        """
        Check if npm is installed and available in PATH.

        Returns:
            True if npm is found, False otherwise
        """
        return shutil.which("npm") is not None

    @staticmethod
    def is_scip_python_installed() -> bool:
        """
        Check if scip-python is installed and available in PATH.

        Returns:
            True if scip-python is found, False otherwise
        """
        return shutil.which("scip-python") is not None

    @staticmethod
    def get_scip_python_version() -> str | None:
        """
        Get installed scip-python version.

        Returns:
            Version string if installed, None otherwise
        """
        if not SCIPPythonInstaller.is_scip_python_installed():
            return None

        result = subprocess.run(["scip-python", "--version"], capture_output=True, text=True)

        if result.returncode == 0:
            return result.stdout.strip()
        return None
