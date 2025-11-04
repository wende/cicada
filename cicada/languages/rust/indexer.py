"""Rust repository indexer using SCIP protocol.

This indexer uses rust-analyzer (which has built-in SCIP support) to generate
type-aware semantic indexes of Rust codebases.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from cicada.languages.rust.scip_installer import SCIPRustInstaller
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.scip.reader import SCIPReader
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.keyword_utils import get_keyword_extractor_from_config


class RustSCIPIndexer(BaseIndexer):
    """Index Rust repositories using rust-analyzer's SCIP output."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the Rust SCIP indexer.

        Args:
            verbose: If True, print detailed progress information
        """
        self.verbose = verbose
        self.excluded_dirs = {
            "target",
            ".git",
            "node_modules",
            ".cargo",
            "vendor",
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

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index Rust repository using rust-analyzer.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            force: If True, reindex even if up-to-date (MVP: always reindex)
            verbose: If True, print detailed progress
            config_path: Optional config file (MVP: unused)

        Returns:
            Dict with indexing results

        Raises:
            RuntimeError: If rust-analyzer is not available or indexing fails
        """
        repo_path = Path(repo_path).resolve()
        output_path = Path(output_path).resolve()

        if verbose or self.verbose:
            print(f"Indexing Rust repository: {repo_path}")

        # 1. Ensure rust-analyzer is installed
        self._ensure_rust_analyzer_installed()

        # 2. Run rust-analyzer SCIP indexer
        scip_file = self._run_rust_analyzer(repo_path)

        try:
            # 3. Read .scip file
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            if verbose or self.verbose:
                summary = reader.get_index_summary(scip_index)
                print(
                    f"  SCIP index: {summary['documents']} documents, "
                    f"{summary['symbols']} symbols"
                )

            # 4. Initialize keyword extractor from config (universal)
            extract_keywords, keyword_extractor = get_keyword_extractor_from_config(
                repo_path, verbose=(verbose or self.verbose)
            )

            # 5. Convert to Cicada format with optional keyword extraction
            converter = SCIPConverter(
                extract_keywords=extract_keywords,
                keyword_extractor=keyword_extractor,
                verbose=self.verbose,
            )
            cicada_index = converter.convert(scip_index, repo_path)

            # 6. Save to output path
            self._save_index(cicada_index, output_path)

            # 7. Build result summary
            all_modules = cicada_index.get("modules", {})
            modules_count = len(all_modules)
            functions_count = cicada_index.get("metadata", {}).get("total_functions", 0)

            # Count files vs structs/traits for better reporting
            file_count = sum(1 for name in all_modules if name.startswith("_file_"))
            struct_count = modules_count - file_count

            if verbose or self.verbose:
                if struct_count > 0:
                    print(
                        f"  Indexed {file_count} files, {struct_count} structs/traits, {functions_count} functions"
                    )
                else:
                    print(f"  Indexed {modules_count} modules, {functions_count} functions")
                print(f"  Index saved to: {output_path}")

            return {
                "success": True,
                "modules_count": modules_count,
                "functions_count": functions_count,
                "files_indexed": len(scip_index.documents),
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Failed to process SCIP index: {e}"
            if verbose or self.verbose:
                print(f"  Error: {error_msg}")
            return {
                "success": False,
                "modules_count": 0,
                "functions_count": 0,
                "files_indexed": 0,
                "errors": [error_msg],
            }

        finally:
            # 8. Cleanup temporary .scip file
            if scip_file.exists():
                scip_file.unlink()
                if verbose or self.verbose:
                    print(f"  Cleaned up temporary file: {scip_file}")

    def _ensure_rust_analyzer_installed(self):
        """
        Ensure rust-analyzer is installed, auto-install if needed.

        Raises:
            RuntimeError: If rustup/cargo is not available or installation fails
        """
        if SCIPRustInstaller.is_rust_analyzer_installed():
            if self.verbose:
                version = SCIPRustInstaller.get_rust_analyzer_version()
                print(f"  Using rust-analyzer {version}")
            return

        # Check cargo/rustup availability
        if not SCIPRustInstaller.is_cargo_available():
            raise RuntimeError(
                "Rust toolchain is required for rust-analyzer.\n"
                "Install Rust from: https://rustup.rs/\n"
                "Or install rust-analyzer manually: rustup component add rust-analyzer"
            )

        # Auto-install
        print("Installing rust-analyzer (this should be quick)...")
        success = SCIPRustInstaller.install_rust_analyzer(verbose=self.verbose)

        if not success:
            raise RuntimeError(
                "Failed to install rust-analyzer.\n"
                "Try installing manually: rustup component add rust-analyzer"
            )

        print("✓ rust-analyzer installed successfully")

    def _run_rust_analyzer(self, repo_path: Path) -> Path:
        """
        Run rust-analyzer SCIP indexer on repository.

        Args:
            repo_path: Repository root path

        Returns:
            Path to generated .scip file

        Raises:
            RuntimeError: If rust-analyzer execution fails
        """
        # Create temporary file for .scip output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".scip", delete=False, dir=repo_path
        ) as tmp:
            scip_file = Path(tmp.name)

        cmd = [
            "rust-analyzer",
            "scip",
            str(repo_path),
        ]

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")
            print("  (This may take several minutes for large projects...)")

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"rust-analyzer indexing failed:\n{result.stderr}")

            # rust-analyzer writes to index.scip by default, need to rename
            default_scip = repo_path / "index.scip"
            if default_scip.exists():
                default_scip.rename(scip_file)
            elif not scip_file.exists():
                raise RuntimeError(f"rust-analyzer did not generate SCIP file")

            return scip_file

        except subprocess.TimeoutExpired as e:
            if scip_file.exists():
                scip_file.unlink()
            # Also clean up default index.scip if it was created
            default_scip = repo_path / "index.scip"
            if default_scip.exists():
                default_scip.unlink()
            raise RuntimeError(
                "rust-analyzer indexing timed out after 10 minutes. "
                "Try indexing a smaller subset of the project."
            ) from e
        except Exception:
            if scip_file.exists():
                scip_file.unlink()
            # Clean up default index.scip if it exists
            default_scip = repo_path / "index.scip"
            if default_scip.exists():
                default_scip.unlink()
            raise

    def _save_index(self, index: dict, output_path: Path):
        """
        Save index to JSON file.

        Args:
            index: Cicada index dictionary
            output_path: Path to save to
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
