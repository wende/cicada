"""Rust repository indexer using SCIP protocol.

This indexer uses rust-analyzer's native SCIP support to generate
type-aware semantic indexes of Rust codebases.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer


class RustSCIPIndexer(GenericSCIPIndexer):
    """Index Rust repositories using rust-analyzer's SCIP support."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the Rust SCIP indexer.

        Args:
            verbose: If True, print detailed progress information
        """
        super().__init__(verbose=verbose)
        self.excluded_dirs = {
            "target",
            ".git",
            "vendor",
            "node_modules",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "rust"

    def get_file_extensions(self) -> list[str]:
        """Return Rust file extensions."""
        return [".rs"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _is_rust_analyzer_installed(self) -> bool:
        """Check if rust-analyzer is available in PATH."""
        return shutil.which("rust-analyzer") is not None

    def _get_rust_analyzer_path(self) -> str | None:
        """Get path to rust-analyzer executable."""
        return shutil.which("rust-analyzer")

    def _get_rust_analyzer_version(self) -> str | None:
        """Get installed rust-analyzer version."""
        ra_path = self._get_rust_analyzer_path()
        if not ra_path:
            return None

        try:
            result = subprocess.run(
                [ra_path, "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                # Parse "rust-analyzer 0.3.2127-standalone"
                return result.stdout.strip().replace("rust-analyzer ", "")
            return None
        except Exception:
            return None

    def _ensure_rust_analyzer_installed(self) -> None:
        """
        Ensure rust-analyzer is available, attempting auto-install via rustup.

        Raises:
            RuntimeError: If rust-analyzer is not installed and cannot be auto-installed
        """
        if not self._is_rust_analyzer_installed():
            from cicada.languages.scip.installer import (
                InstallConfig,
                InstallMethod,
                SCIPToolInstaller,
            )

            config = InstallConfig(
                method=InstallMethod.RUSTUP,
                package="rust-analyzer",
                executable="rust-analyzer",
                runtime_check="rustup",
            )
            installed = SCIPToolInstaller.try_install(config, verbose=self.verbose)
            if not installed:
                raise RuntimeError(
                    "rust-analyzer is required for Rust indexing but was not found.\n"
                    "Install it with:\n"
                    "  rustup component add rust-analyzer\n"
                    "Or:\n"
                    "  brew install rust-analyzer"
                )

        if self.verbose:
            version = self._get_rust_analyzer_version()
            print(f"  Using rust-analyzer {version or 'unknown version'}")

    def _run_rust_analyzer_scip(self, repo_path: Path) -> Path:
        """
        Run rust-analyzer to generate SCIP index.

        Args:
            repo_path: Path to repository root

        Returns:
            Path to generated .scip file

        Raises:
            RuntimeError: If rust-analyzer fails or is not found
        """
        ra_path = self._get_rust_analyzer_path()
        if not ra_path:
            raise RuntimeError(
                "rust-analyzer not found. Call _ensure_rust_analyzer_installed() first."
            )

        # Create temp file for SCIP output
        with tempfile.NamedTemporaryFile(suffix=".scip", delete=False) as temp_file:
            scip_output_path = Path(temp_file.name)

        if self.verbose:
            print(f"  Running rust-analyzer scip on {repo_path}...")
            print("  (This may take several minutes for large projects...)")

        try:
            # rust-analyzer scip <path> --output <output.scip>
            result = subprocess.run(
                [ra_path, "scip", str(repo_path), "--output", str(scip_output_path)],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                if scip_output_path.exists():
                    scip_output_path.unlink()
                raise RuntimeError(
                    f"rust-analyzer scip failed (exit code {result.returncode}):\n"
                    f"{result.stderr}"
                )

            if not scip_output_path.exists():
                raise RuntimeError(
                    "rust-analyzer scip did not generate output file. "
                    "This may happen if the project has no Cargo.toml or has build errors."
                )

            return scip_output_path

        except subprocess.TimeoutExpired as err:
            if scip_output_path.exists():
                scip_output_path.unlink()
            raise RuntimeError(
                "rust-analyzer scip timed out after 10 minutes. "
                "Try indexing a smaller subset of the project."
            ) from err
        except Exception:
            if scip_output_path.exists():
                scip_output_path.unlink()
            raise

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """
        Run rust-analyzer SCIP indexer.

        This is the main entry point called by GenericSCIPIndexer.

        Args:
            repo_path: Path to repository root

        Returns:
            Path to generated .scip file
        """
        self._ensure_rust_analyzer_installed()
        return self._run_rust_analyzer_scip(repo_path)
