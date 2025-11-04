"""Manage scip-ruby installation.

Provides utilities to check for and install scip-ruby,
which is distributed as a Ruby gem.
"""

import shutil
import subprocess


class SCIPRubyInstaller:
    """Manage scip-ruby installation and availability checks."""

    @staticmethod
    def is_gem_available() -> bool:
        """
        Check if gem (Ruby package manager) is installed and available in PATH.

        Returns:
            True if gem is found, False otherwise
        """
        return shutil.which("gem") is not None

    @staticmethod
    def is_bundle_available() -> bool:
        """
        Check if bundle (Bundler) is installed and available in PATH.

        Returns:
            True if bundle is found, False otherwise
        """
        return shutil.which("bundle") is not None

    @staticmethod
    def is_scip_ruby_installed() -> bool:
        """
        Check if scip-ruby is installed and available in PATH.

        Returns:
            True if scip-ruby is found, False otherwise
        """
        # Check both direct binary and bundler exec
        if shutil.which("scip-ruby") is not None:
            return True

        # Check if it's available via bundle exec
        if SCIPRubyInstaller.is_bundle_available():
            try:
                result = subprocess.run(
                    ["bundle", "exec", "scip-ruby", "--help"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

        return False

    @staticmethod
    def install_scip_ruby(verbose: bool = False) -> bool:
        """
        Install scip-ruby via gem.

        Args:
            verbose: If True, print installation progress

        Returns:
            True if installation succeeded, False otherwise

        Raises:
            RuntimeError: If gem is not available
        """
        if not SCIPRubyInstaller.is_gem_available():
            raise RuntimeError(
                "gem is required to install scip-ruby. "
                "Install Ruby from https://www.ruby-lang.org/"
            )

        cmd = ["gem", "install", "scip-ruby"]

        if verbose:
            print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            if verbose:
                print(f"Error installing scip-ruby: {result.stderr}")
            return False

        return True

    @staticmethod
    def get_scip_ruby_version() -> str | None:
        """
        Get installed scip-ruby version.

        Returns:
            Version string if installed, None otherwise
        """
        if not SCIPRubyInstaller.is_scip_ruby_installed():
            return None

        # Try direct command first
        if shutil.which("scip-ruby"):
            result = subprocess.run(
                ["scip-ruby", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()

        # Try via bundle exec
        if SCIPRubyInstaller.is_bundle_available():
            try:
                result = subprocess.run(
                    ["bundle", "exec", "scip-ruby", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except subprocess.TimeoutExpired:
                pass

        return None
