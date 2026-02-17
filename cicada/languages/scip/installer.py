"""Generic SCIP tool installer.

Auto-installs SCIP indexer tools for supported languages using their
native package managers (npm, go, gem, etc.).
"""

import contextlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InstallMethod(Enum):
    """Supported installation methods for SCIP tools."""

    NPM = "npm"
    GO = "go"
    GEM = "gem"
    DART_PUB = "dart_pub"
    DOTNET = "dotnet"
    RUSTUP = "rustup"
    COURSIER = "coursier"


@dataclass
class InstallConfig:
    """Configuration for auto-installing a SCIP tool."""

    method: InstallMethod
    package: str
    executable: str
    runtime_check: str | None = None


# Local install directory for npm packages
_LOCAL_NODE_DIR = Path.home() / ".cicada" / "node"


class SCIPToolInstaller:
    """Auto-install SCIP indexer tools using native package managers."""

    @classmethod
    def try_install(cls, config: InstallConfig, verbose: bool = False) -> str | None:
        """Attempt to install a SCIP tool.

        Args:
            config: Installation configuration
            verbose: Print progress information

        Returns:
            Path to installed binary, or None on failure
        """
        if config.runtime_check and not shutil.which(config.runtime_check):
            if verbose:
                print(f"  {config.runtime_check} not found - cannot install {config.executable}")
            return None

        method_map = {
            InstallMethod.NPM: cls._install_npm,
            InstallMethod.GO: cls._install_go,
            InstallMethod.GEM: cls._install_gem,
            InstallMethod.DART_PUB: cls._install_dart_pub,
            InstallMethod.DOTNET: cls._install_dotnet,
            InstallMethod.RUSTUP: cls._install_rustup,
            InstallMethod.COURSIER: cls._install_coursier,
        }

        installer = method_map.get(config.method)
        if not installer:
            return None

        if verbose:
            print(f"  Auto-installing {config.executable} via {config.method.value}...")

        return installer(config, verbose)

    @classmethod
    def _install_npm(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via npm to ~/.cicada/node."""
        _LOCAL_NODE_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["npm", "install", "--prefix", str(_LOCAL_NODE_DIR), config.package],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  npm install failed: {result.stderr}")
            return None

        bin_dir = _LOCAL_NODE_DIR / "node_modules" / ".bin"
        candidate = bin_dir / (config.executable + ".cmd" if os.name == "nt" else config.executable)

        if candidate.is_file() and os.access(candidate, os.X_OK):
            if verbose:
                print(f"  Installed {config.executable} to {candidate}")
            return str(candidate)

        return None

    @classmethod
    def _install_go(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via go install."""
        result = subprocess.run(
            ["go", "install", config.package],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  go install failed: {result.stderr}")
            return None

        gopath = os.environ.get("GOPATH", str(Path.home() / "go"))
        candidate = Path(gopath) / "bin" / config.executable
        if candidate.is_file():
            if verbose:
                print(f"  Installed {config.executable} to {candidate}")
            return str(candidate)

        path = shutil.which(config.executable)
        if path:
            if verbose:
                print(f"  Installed {config.executable} at {path}")
            return path

        return None

    @classmethod
    def _install_gem(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via gem install."""
        result = subprocess.run(
            ["gem", "install", config.package, "--no-document"],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  gem install failed: {result.stderr}")
            return None

        # Probe standard gem bin directories first, then fall back to PATH.
        # Gem bin dirs may not be on PATH in some environments (CI, containers).
        gem_bin_dirs: set[Path] = set()

        # Query gem environment for installation directories
        for key in ("gemdir", "user_gemdir"):
            try:
                env_result = subprocess.run(
                    ["gem", "environment", key],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if env_result.returncode == 0:
                    value = env_result.stdout.strip()
                    if value:
                        gem_bin_dirs.add(Path(value) / "bin")
            except (subprocess.TimeoutExpired, OSError):
                pass

        # Common fallback: ~/.gem/bin
        # Path.home() can raise RuntimeError if $HOME is not set
        with contextlib.suppress(RuntimeError):
            gem_bin_dirs.add(Path.home() / ".gem" / "bin")

        for bin_dir in gem_bin_dirs:
            candidate = bin_dir / config.executable
            if candidate.is_file() and os.access(candidate, os.X_OK):
                if verbose:
                    print(f"  Installed {config.executable} to {candidate}")
                return str(candidate)

        # Fall back to PATH
        path = shutil.which(config.executable)
        if path:
            if verbose:
                print(f"  Installed {config.executable} at {path}")
            return path

        return None

    @classmethod
    def _install_dart_pub(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via dart pub global activate."""
        result = subprocess.run(
            ["dart", "pub", "global", "activate", config.package],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  dart pub global activate failed: {result.stderr}")
            return None

        pub_cache_bin = Path.home() / ".pub-cache" / "bin" / config.executable
        if pub_cache_bin.is_file():
            if verbose:
                print(f"  Installed {config.executable} to {pub_cache_bin}")
            return str(pub_cache_bin)

        path = shutil.which(config.executable)
        if path:
            if verbose:
                print(f"  Installed {config.executable} at {path}")
            return path

        return None

    @classmethod
    def _install_dotnet(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via dotnet tool install -g."""
        result = subprocess.run(
            ["dotnet", "tool", "install", "-g", config.package],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  dotnet tool install failed: {result.stderr}")
            return None

        dotnet_tools = Path.home() / ".dotnet" / "tools" / config.executable
        if dotnet_tools.is_file():
            if verbose:
                print(f"  Installed {config.executable} to {dotnet_tools}")
            return str(dotnet_tools)

        path = shutil.which(config.executable)
        if path:
            if verbose:
                print(f"  Installed {config.executable} at {path}")
            return path

        return None

    @classmethod
    def _install_rustup(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via rustup component add."""
        result = subprocess.run(
            ["rustup", "component", "add", config.package],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  rustup component add failed: {result.stderr}")
            return None

        path = shutil.which(config.executable)
        if path:
            if verbose:
                print(f"  Installed {config.executable} at {path}")
            return path

        return None

    @classmethod
    def _install_coursier(cls, config: InstallConfig, verbose: bool) -> str | None:
        """Install via coursier (cs) install."""
        cs_cmd = shutil.which("cs") or shutil.which("coursier")
        if not cs_cmd:
            if verbose:
                print("  Neither cs nor coursier found - cannot install")
            return None

        # Security audit: cs_cmd is validated via shutil.which() (returns None or
        # valid executable path). config.package comes from hardcoded InstallConfig
        # values in configs.py, not user input. No command injection risk.
        result = subprocess.run(
            [cs_cmd, "install", config.package],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            if verbose:
                print(f"  coursier install failed: {result.stderr}")
            return None

        path = shutil.which(config.executable)
        if path:
            if verbose:
                print(f"  Installed {config.executable} at {path}")
            return path

        return None
