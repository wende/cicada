"""Manage rust-analyzer installation for SCIP generation.

Provides utilities to check for rust-analyzer availability.
Since rust-analyzer has built-in SCIP support, we just need to verify it's installed.
"""

import shutil
import subprocess


class SCIPRustInstaller:
    """Manage rust-analyzer installation and availability checks."""

    @staticmethod
    def is_cargo_available() -> bool:
        """
        Check if cargo is installed and available in PATH.

        Returns:
            True if cargo is found, False otherwise
        """
        return shutil.which("cargo") is not None

    @staticmethod
    def is_rust_analyzer_installed() -> bool:
        """
        Check if rust-analyzer is installed and available in PATH.

        Returns:
            True if rust-analyzer is found, False otherwise
        """
        return shutil.which("rust-analyzer") is not None

    @staticmethod
    def install_rust_analyzer(verbose: bool = False) -> bool:
        """
        Install rust-analyzer via rustup.

        Args:
            verbose: If True, print installation progress

        Returns:
            True if installation succeeded, False otherwise

        Raises:
            RuntimeError: If rustup is not available
        """
        if not shutil.which("rustup"):
            raise RuntimeError(
                "rustup is required to install rust-analyzer. "
                "Install Rust from https://rustup.rs/"
            )

        cmd = ["rustup", "component", "add", "rust-analyzer"]

        if verbose:
            print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if verbose:
                print(f"Error installing rust-analyzer: {result.stderr}")
            return False

        return True

    @staticmethod
    def get_rust_analyzer_version() -> str | None:
        """
        Get installed rust-analyzer version.

        Returns:
            Version string if installed, None otherwise
        """
        if not SCIPRustInstaller.is_rust_analyzer_installed():
            return None

        result = subprocess.run(
            ["rust-analyzer", "--version"], capture_output=True, text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
