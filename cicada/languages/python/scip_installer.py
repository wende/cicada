"""Manage scip-python installation.

Provides utilities to check for scip-python availability and local installation.
"""

import os
import shutil
import subprocess
from pathlib import Path


class SCIPPythonInstaller:
    """Manage scip-python availability and local installation."""

    # Local install directory under ~/.cicada
    LOCAL_NODE_DIR = Path.home() / ".cicada" / "node"
    LOCAL_BIN_DIR = LOCAL_NODE_DIR / "node_modules" / ".bin"

    @staticmethod
    def is_npm_available() -> bool:
        """
        Check if npm is installed and available in PATH.

        Returns:
            True if npm is found, False otherwise
        """
        return shutil.which("npm") is not None

    @classmethod
    def _get_local_scip_python_path(cls) -> str | None:
        """
        Get path to local scip-python executable.

        Handles platform differences (Windows uses .cmd shims).

        Returns:
            Path to local scip-python if found and executable, None otherwise
        """
        bin_dir = cls.LOCAL_BIN_DIR
        if not bin_dir.exists():
            return None

        # On Windows, npm creates .cmd shims; on Unix we expect a direct executable
        candidate = bin_dir / "scip-python.cmd" if os.name == "nt" else bin_dir / "scip-python"

        # Only return the path if it is a regular file and is executable
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

        return None

    @classmethod
    def get_scip_python_path(cls) -> str | None:
        """
        Get path to scip-python executable.

        Checks in order:
        1. Global PATH
        2. Local cicada installation (~/.cicada/node/)

        Returns:
            Path to scip-python if found, None otherwise
        """
        # Check global first
        if global_path := shutil.which("scip-python"):
            return global_path

        # Check local installation (platform-aware)
        return cls._get_local_scip_python_path()

    @classmethod
    def is_local_install(cls, scip_path: str | None) -> bool:
        """
        Check if a scip-python path is from the local ~/.cicada installation.

        Args:
            scip_path: Path to scip-python executable

        Returns:
            True if path is from local cicada installation
        """
        if not scip_path:
            return False
        try:
            # Check if the path (without resolving symlinks) is under ~/.cicada/node
            path = Path(scip_path)
            local_node_dir = cls.LOCAL_NODE_DIR
            # Use is_relative_to for proper path containment check
            return path.is_relative_to(local_node_dir)
        except (ValueError, OSError):
            return False

    @classmethod
    def is_scip_python_installed(cls) -> bool:
        """
        Check if scip-python is installed (globally or locally).

        Returns:
            True if scip-python is found, False otherwise
        """
        return cls.get_scip_python_path() is not None

    @classmethod
    def get_scip_python_version(cls) -> str | None:
        """
        Get installed scip-python version.

        Returns:
            Version string if installed, None otherwise
        """
        scip_path = cls.get_scip_python_path()
        if not scip_path:
            return None

        # Security: scip_path comes from either shutil.which() (PATH lookup)
        # or our own LOCAL_BIN_DIR constant - not from user input
        result = subprocess.run([scip_path, "--version"], capture_output=True, text=True)

        if result.returncode == 0:
            return result.stdout.strip()
        return None

    @classmethod
    def install_locally(cls, verbose: bool = False) -> bool:
        """
        Install scip-python locally to ~/.cicada/node/.

        Args:
            verbose: If True, print progress information

        Returns:
            True if installation succeeded, False otherwise
        """
        if not cls.is_npm_available():
            if verbose:
                print("  npm not found - cannot install scip-python")
            return False

        # Create directory
        cls.LOCAL_NODE_DIR.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"  Installing scip-python to {cls.LOCAL_NODE_DIR}...")

        result = subprocess.run(
            [
                "npm",
                "install",
                "--prefix",
                str(cls.LOCAL_NODE_DIR),
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

        # Verify installation by checking if executable exists
        return cls._get_local_scip_python_path() is not None
