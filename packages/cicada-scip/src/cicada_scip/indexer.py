"""Generic SCIP indexer for all SCIP-based languages.

This base class contains the shared logic for indexing repositories
using SCIP (Source Code Intelligence Protocol). Language-specific indexers
(Python, TypeScript, etc.) only need to provide minimal configuration.

NOTE: This indexer returns RAW indexes without enrichment (keywords, timestamps,
cochange). Enrichment should be applied separately by the caller using the
main cicada package's enrichment pipeline.
"""

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from cicada_mcp_core import BaseIndexer
from cicada_mcp_core.utils.hash_utils import (
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada_mcp_core.utils.storage import get_hashes_path

from cicada_scip.converter import SCIPConverter
from cicada_scip.reader import SCIPReader


class GenericSCIPIndexer(BaseIndexer, ABC):
    """
    Generic indexer for SCIP-based languages.

    Subclasses only need to implement:
    - get_language_name()
    - get_file_extensions()
    - get_excluded_dirs()
    - _run_scip_indexer(repo_path) -> Path to .scip file

    This indexer produces RAW indexes. For enriched indexes with keywords,
    timestamps, and cochange data, use the enrichment pipeline in main cicada.
    """

    # SCIP indexers support incremental indexing
    supports_incremental: bool = True

    def __init__(self, verbose: bool = False):
        super().__init__(verbose)
        self.verbose = verbose

    @abstractmethod
    def get_language_name(self) -> str:
        """Return language identifier (e.g., 'python', 'typescript')."""
        ...

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """Return list of file extensions (e.g., ['.py'], ['.ts', '.tsx'])."""
        ...

    @abstractmethod
    def get_excluded_dirs(self) -> list[str]:
        """Return list of directory names to exclude from indexing."""
        ...

    @abstractmethod
    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """
        Run the language-specific SCIP indexer.

        Args:
            repo_path: Repository root path

        Returns:
            Path to generated .scip file

        Raises:
            RuntimeError: If indexing fails
        """
        ...

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index repository using SCIP.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            force: If True, force full reindex
            verbose: If True, print detailed progress
            config_path: Optional config file (unused)

        Returns:
            Dict with indexing results
        """
        return self.incremental_index_repository(
            repo_path=str(repo_path),
            output_path=str(output_path),
            force_full=force,
            verbose=verbose,
        )

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,  # noqa: ARG002 - interface compatibility
        extract_string_keywords: bool = False,  # noqa: ARG002 - interface compatibility
        compute_timestamps: bool = False,  # noqa: ARG002 - interface compatibility
        extract_cochange: bool = False,  # noqa: ARG002 - interface compatibility
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Index repository and return RAW index (no enrichment).

        This method:
        1. Checks for file changes using hashes
        2. Runs the SCIP indexer tool
        3. Converts SCIP output to Cicada format
        4. Saves the raw index

        Note: extract_keywords, extract_string_keywords, compute_timestamps,
        and extract_cochange are accepted for interface compatibility but
        ignored. For enrichment, use the main cicada package's enrichment
        pipeline after calling this method.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            extract_keywords: Ignored - for interface compatibility
            extract_string_keywords: Ignored - for interface compatibility
            compute_timestamps: Ignored - for interface compatibility
            extract_cochange: Ignored - for interface compatibility
            force_full: If True, force full reindex even if up-to-date
            verbose: If True, print detailed progress information

        Returns:
            Dict with indexing results including the raw index
        """
        self.verbose = verbose
        repo_path_obj = Path(repo_path).resolve()
        output_path_obj = Path(output_path).resolve()

        if self.verbose:
            print(f"Indexing {self.get_language_name()} repository: {repo_path_obj}")

        # Check if we can skip reindexing
        hashes_path = get_hashes_path(repo_path_obj)
        existing_hashes = load_file_hashes(str(hashes_path.parent))

        # Find all source files
        source_files = list(self._find_source_files(repo_path_obj))
        relative_files = [str(f.relative_to(repo_path_obj)) for f in source_files]

        # Check for changes
        new_files, modified_files, deleted_files = detect_file_changes(
            relative_files, existing_hashes, str(repo_path_obj)
        )

        if not force_full and not new_files and not modified_files and not deleted_files:
            if self.verbose:
                print("  No changes detected. Index is up to date.")
            if output_path_obj.exists():
                with open(output_path_obj) as f:
                    existing_index = json.load(f)
                return {
                    "success": True,
                    "modules_count": len(existing_index.get("modules", {})),
                    "functions_count": existing_index.get("metadata", {}).get("total_functions", 0),
                    "files_indexed": 0,
                    "errors": [],
                    "skipped": True,
                    "index": existing_index,
                }

        if self.verbose:
            if new_files or modified_files or deleted_files:
                print(
                    f"  Changes detected: {len(new_files)} new, "
                    f"{len(modified_files)} modified, {len(deleted_files)} deleted"
                )
            else:
                print("  Performing full index...")

        scip_file: Path | None = None
        try:
            # Run SCIP indexer
            scip_file = self._run_scip_indexer(repo_path_obj)

            # Read SCIP file
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            if self.verbose:
                summary = reader.get_index_summary(scip_index)
                print(
                    f"  SCIP index: {summary['documents']} documents, "
                    f"{summary['symbols']} symbols"
                )

            # Convert to Cicada format (raw, no keyword extraction)
            converter = SCIPConverter(
                extract_keywords=False,
                keyword_extractor=None,
                verbose=self.verbose,
            )
            cicada_index = converter.convert(scip_index, repo_path_obj)

            # Save index
            self._save_index(cicada_index, output_path_obj)

            # Save file hashes
            if source_files:
                try:
                    current_hashes = compute_hashes_for_files(
                        relative_files, repo_path=str(repo_path_obj)
                    )
                    save_file_hashes(str(hashes_path.parent), current_hashes)
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Failed to save file hashes: {e}")

            # Build result summary
            all_modules = cicada_index.get("modules", {})
            modules_count = len(all_modules)
            functions_count = cicada_index.get("metadata", {}).get("total_functions", 0)

            file_count = sum(bool(name.startswith("_file_")) for name in all_modules)
            class_count = modules_count - file_count

            if self.verbose:
                if class_count > 0:
                    print(
                        f"  Indexed {file_count} files, {class_count} classes, "
                        f"{functions_count} functions"
                    )
                else:
                    print(f"  Indexed {modules_count} modules, {functions_count} functions")
                print(f"  Index saved to: {output_path_obj}")

            return {
                "success": True,
                "modules_count": modules_count,
                "functions_count": functions_count,
                "files_indexed": len(scip_index.documents),
                "errors": [],
                "index": cicada_index,
            }

        except Exception as e:
            error_msg = f"Failed to process SCIP index: {e}"
            if self.verbose:
                print(f"  Error: {error_msg}")
            return {
                "success": False,
                "modules_count": 0,
                "functions_count": 0,
                "files_indexed": 0,
                "errors": [error_msg],
            }

        finally:
            if scip_file and scip_file.exists():
                scip_file.unlink()
                if self.verbose:
                    print(f"  Cleaned up temporary file: {scip_file}")

    def _find_source_files(self, repo_path: Path) -> list[Path]:
        """Find all source files in repository."""
        source_files = []
        excluded_dirs = set(self.get_excluded_dirs())

        for ext in self.get_file_extensions():
            for file in repo_path.rglob(f"*{ext}"):
                if all(excluded not in file.parts for excluded in excluded_dirs):
                    source_files.append(file)
        return source_files

    def _save_index(self, index: dict, output_path: Path):
        """Save index to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _run_scip_command(
        self,
        repo_path: Path,
        command: list[str],
        *,
        output_path: Path,
        timeout: int = 600,
    ) -> Path:
        """Run a SCIP indexer command and validate output.

        Args:
            repo_path: Repository root
            command: Command to run (e.g., ["scip-python", "index", ...])
            output_path: Expected path of the generated .scip file
            timeout: Command timeout in seconds

        Returns:
            Path to generated .scip file
        """
        if self.verbose:
            print(f"  Running: {' '.join(command)}")
            print("  (This may take several minutes for large projects...)")

        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Some indexers may return non-zero exit codes due to warnings
            # but still produce valid output
            if result.returncode != 0:
                if output_path.exists() and output_path.stat().st_size > 0:
                    if self.verbose:
                        print(
                            "  Warning: Indexer returned non-zero exit code " "but produced output"
                        )
                        if result.stderr:
                            print(f"  Stderr: {result.stderr.strip()[:200]}")
                else:
                    raise RuntimeError(f"SCIP indexing failed:\n{result.stderr}")

            if not output_path.exists():
                raise RuntimeError(f"SCIP indexer did not generate {output_path}")

            return output_path

        except subprocess.TimeoutExpired as e:
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(
                f"SCIP indexing timed out after {timeout} seconds. "
                "Try indexing a smaller subset of the project."
            ) from e
        except FileNotFoundError as e:
            # Command not found - provide installation instructions
            tool_name = command[0] if command else "unknown"
            install_instructions = self._get_install_instructions(tool_name)
            raise RuntimeError(
                f"SCIP indexer '{tool_name}' not found.\n\n{install_instructions}"
            ) from e
        except Exception:
            if output_path.exists():
                output_path.unlink()
            raise

    def _get_install_instructions(self, tool_name: str) -> str:
        """Get installation instructions for a SCIP indexer tool."""
        instructions = {
            "scip-python": (
                "To install scip-python:\n"
                "  npm install -g @sourcegraph/scip-python\n\n"
                "Or with pipx:\n"
                "  pipx install scip-python\n\n"
                "More info: https://github.com/sourcegraph/scip-python"
            ),
            "npx": (
                "scip-typescript requires Node.js and npm.\n\n"
                "Install Node.js from: https://nodejs.org/\n"
                "Then the indexer will run via: npx @sourcegraph/scip-typescript"
            ),
            "scip-typescript": (
                "To install scip-typescript:\n"
                "  npm install -g @sourcegraph/scip-typescript\n\n"
                "Or run directly with npx:\n"
                "  npx @sourcegraph/scip-typescript index\n\n"
                "More info: https://github.com/sourcegraph/scip-typescript"
            ),
            "scip-dotnet": (
                "To install scip-dotnet:\n"
                "  dotnet tool install -g scip-dotnet\n\n"
                "Then add ~/.dotnet/tools to your PATH:\n"
                '  export PATH="$PATH:$HOME/.dotnet/tools"\n\n'
                "Add this to your ~/.zshrc or ~/.bashrc for persistence.\n"
                "Requires .NET SDK 6.0 or later.\n"
                "More info: https://github.com/sourcegraph/scip-dotnet"
            ),
            "scip-java": (
                "To install scip-java:\n"
                "  Download from: https://github.com/sourcegraph/scip-java/releases\n\n"
                "Or use Coursier:\n"
                "  cs install scip-java\n\n"
                "More info: https://github.com/sourcegraph/scip-java"
            ),
            "scip-ruby": (
                "To install scip-ruby:\n"
                "  gem install scip-ruby\n\n"
                "More info: https://github.com/sourcegraph/scip-ruby"
            ),
            "rust-analyzer": (
                "To install rust-analyzer:\n"
                "  rustup component add rust-analyzer\n\n"
                "Or download from: https://rust-analyzer.github.io/\n\n"
                "More info: https://github.com/rust-lang/rust-analyzer"
            ),
            "scip-go": (
                "To install scip-go:\n"
                "  go install github.com/sourcegraph/scip-go@latest\n\n"
                "More info: https://github.com/sourcegraph/scip-go"
            ),
            "scip-clang": (
                "To install scip-clang:\n"
                "  Download from: https://github.com/nicklockwood/scip-clang/releases\n\n"
                "Requires a compile_commands.json file in your project.\n"
                "More info: https://github.com/nicklockwood/scip-clang"
            ),
            "dart": (
                "scip-dart is built into the Dart SDK.\n\n"
                "Make sure Dart is installed and in your PATH:\n"
                "  https://dart.dev/get-dart\n\n"
                "Then run: dart pub global activate scip_dart"
            ),
        }
        return instructions.get(
            tool_name,
            f"The SCIP indexer '{tool_name}' is not installed or not in PATH.\n\n"
            f"Visit https://scip.dev/ for installation instructions.",
        )
