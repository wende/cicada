"""Manage scip-python installation.

Provides utilities to check for scip-python availability and local installation.
"""

import shutil
import subprocess
from pathlib import Path


class SCIPPythonInstaller:
    """Manage scip-python availability and local installation."""

    # Local install directory under ~/.cicada
    LOCAL_NODE_DIR = Path.home() / ".cicada" / "node"
    LOCAL_BIN_PATH = LOCAL_NODE_DIR / "node_modules" / ".bin" / "scip-python"

    @staticmethod
    def is_npm_available() -> bool:
        """
        Check if npm is installed and available in PATH.

        Returns:
            True if npm is found, False otherwise
        """
        return shutil.which("npm") is not None

    @staticmethod
    def is_npx_available() -> bool:
        """
        Check if npx is installed and available in PATH.

        Returns:
            True if npx is found, False otherwise
        """
        return shutil.which("npx") is not None

    @staticmethod
    def get_scip_python_path() -> str | None:
        """
        Get path to scip-python executable.

        Checks in order:
        1. Global PATH
        2. Local cicada installation (~/.cicada/node/)

        Returns:
            Path to scip-python if found, None otherwise
        """
        # Check global first
        global_path = shutil.which("scip-python")
        if global_path:
            return global_path

        # Check local installation
        if SCIPPythonInstaller.LOCAL_BIN_PATH.exists():
            return str(SCIPPythonInstaller.LOCAL_BIN_PATH)

        return None

    @staticmethod
    def is_scip_python_installed() -> bool:
        """
        Check if scip-python is installed (globally or locally).

        Returns:
            True if scip-python is found, False otherwise
        """
        return SCIPPythonInstaller.get_scip_python_path() is not None

    @staticmethod
    def get_scip_python_version() -> str | None:
        """
        Get installed scip-python version.

        Returns:
            Version string if installed, None otherwise
        """
        scip_path = SCIPPythonInstaller.get_scip_python_path()
        if not scip_path:
            return None

        result = subprocess.run([scip_path, "--version"], capture_output=True, text=True)

        if result.returncode == 0:
            return result.stdout.strip()
        return None

    @staticmethod
    def install_locally(verbose: bool = False) -> bool:
        """
        Install scip-python locally to ~/.cicada/node/.

        Args:
            verbose: If True, print progress information

        Returns:
            True if installation succeeded, False otherwise
        """
        if not SCIPPythonInstaller.is_npm_available():
            if verbose:
                print("  npm not found - cannot install scip-python")
            return False

        # Create directory
        SCIPPythonInstaller.LOCAL_NODE_DIR.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"  Installing scip-python to {SCIPPythonInstaller.LOCAL_NODE_DIR}...")

        result = subprocess.run(
            [
                "npm",
                "install",
                "--prefix",
                str(SCIPPythonInstaller.LOCAL_NODE_DIR),
                "@sourcegraph/scip-python",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  Failed to install scip-python: {result.stderr}")
            return False

        if verbose:
            print("  scip-python installed successfully")

        return SCIPPythonInstaller.LOCAL_BIN_PATH.exists()
