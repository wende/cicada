"""Manage scip-python installation.

Provides utilities to check for and install scip-python,
which is distributed via npm.
"""

import shutil
import subprocess


class SCIPPythonInstaller:
    """Manage scip-python installation and availability checks."""

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
    def install_scip_python(verbose: bool = False) -> bool:
        """
        Install scip-python via npm globally.

        Args:
            verbose: If True, print installation progress

        Returns:
            True if installation succeeded, False otherwise

        Raises:
            RuntimeError: If npm is not available
        """
        if not SCIPPythonInstaller.is_npm_available():
            raise RuntimeError(
                "npm is required to install scip-python. "
                "Install Node.js from https://nodejs.org/"
            )

        cmd = ["npm", "install", "-g", "@sourcegraph/scip-python"]

        if verbose:
            print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if verbose:
                print(f"Error installing scip-python: {result.stderr}")
            return False

        return True

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
