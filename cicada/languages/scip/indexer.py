"""Generic SCIP indexer with enrichment support.

This module provides GenericSCIPIndexer which handles the full SCIP indexing
pipeline: running the SCIP indexer tool, converting to Cicada format, and
optionally enriching with keywords, timestamps, and cochange analysis.
"""

import json
import re
import subprocess
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.hash_utils import (
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada.utils.keyword_utils import read_keyword_extraction_config
from cicada.utils.storage import get_hashes_path

from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.scip.reader import SCIPReader

__all__ = ["GenericSCIPIndexer"]


@dataclass
class ExpansionCallback:
    """Callback data for streaming expansion pipeline."""

    target: dict[str, Any]  # The module/function dict to update
    target_key: str  # "keywords" or "string_keywords"


class GenericSCIPIndexer(BaseIndexer):
    """
    SCIP indexer with enrichment support.

    Subclasses only need to implement:
    - get_language_name()
    - get_file_extensions()
    - get_excluded_dirs()
    - _run_scip_indexer(repo_path) -> Path to .scip file
    """

    # SCIP indexers support incremental indexing
    supports_incremental: bool = True

    def __init__(self, verbose: bool = False):
        super().__init__(verbose)
        self.verbose = verbose
        self.excluded_dirs: set[str] = set()

    @abstractmethod
    def get_language_name(self) -> str:
        """Return language identifier (e.g., 'python', 'typescript')."""
        ...

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """Return list of file extensions (e.g., ['.py'], ['.ts', '.tsx'])."""
        ...

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

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
        """Index repository using SCIP with enrichment."""
        return self.incremental_index_repository(
            repo_path=str(repo_path),
            output_path=str(output_path),
            extract_keywords=True,
            compute_timestamps=True,
            extract_cochange=False,
            force_full=force,
            verbose=verbose,
        )

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        compute_timestamps: bool = True,
        extract_cochange: bool = False,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Index repository with optional enrichment.

        This method:
        1. Checks for file changes using hashes
        2. Runs the SCIP indexer tool
        3. Converts SCIP output to Cicada format
        4. Runs enrichment pipeline if requested (keywords, timestamps, cochange)
        5. Saves the enriched index

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            extract_keywords: If True, extract keywords from documentation, strings, and comments
            compute_timestamps: If True, compute git timestamps for functions
            extract_cochange: If True, analyze git history for co-change patterns
            force_full: If True, force full reindex even if up-to-date
            verbose: If True, print detailed progress information

        Returns:
            Dict with indexing results including the enriched index
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
            # Step 1: Run SCIP indexer
            scip_file = self._run_scip_indexer(repo_path_obj)

            # Step 2: Read SCIP file
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            if self.verbose:
                summary = reader.get_index_summary(scip_index)
                print(
                    f"  SCIP index: {summary['documents']} documents, "
                    f"{summary['symbols']} symbols"
                )

            # Step 3: Convert to Cicada format (raw, no keyword extraction)
            converter = SCIPConverter(
                extract_keywords=False,
                keyword_extractor=None,
                verbose=self.verbose,
            )
            cicada_index = converter.convert(scip_index, repo_path_obj)

            # Step 4: Save file hashes
            if source_files:
                try:
                    current_hashes = compute_hashes_for_files(
                        relative_files, repo_path=str(repo_path_obj)
                    )
                    save_file_hashes(str(hashes_path.parent), current_hashes)
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Failed to save file hashes: {e}")

            # Step 5: Run enrichment pipeline if requested
            if extract_keywords or compute_timestamps or extract_cochange:
                keyword_extractor = None
                keyword_expander = None
                if extract_keywords:
                    try:
                        from cicada.utils.keyword_utils import create_keyword_extractor

                        extraction_method, expansion_method = read_keyword_extraction_config(
                            repo_path_obj
                        )
                        keyword_extractor = create_keyword_extractor(
                            extraction_method, expansion_method, verbose=self.verbose
                        )
                        if self.verbose:
                            print(f"  Keyword extraction: {extraction_method}")
                            if expansion_method != "none":
                                print(f"  Keyword expansion: {expansion_method}")
                    except Exception as e:
                        if self.verbose:
                            print(f"  Warning: Could not initialize keyword extractor: {e}")
                            print("  Continuing without keyword extraction...")
                        extract_keywords = False

                if extract_keywords or compute_timestamps or extract_cochange:
                    if self.verbose:
                        print("  Running enrichment pipeline...")

                    skipped_phases = self._run_enrichment_pipeline(
                        cicada_index,
                        repo_path_obj,
                        extract_keywords=extract_keywords,
                        extract_comment_keywords=extract_keywords,
                        compute_timestamps=compute_timestamps,
                        extract_cochange=extract_cochange,
                        keyword_extractor=keyword_extractor,
                        keyword_expander=keyword_expander,
                    )

                    if skipped_phases and self.verbose:
                        print(f"  Note: Skipped phases: {', '.join(skipped_phases)}")

            # Step 6: Save index
            self._save_index(cicada_index, output_path_obj)

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

    def _save_index(self, index: dict, output_path: Path) -> None:
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
                        print("  Warning: Indexer returned non-zero exit code but produced output")
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

    def _extract_docstring_keywords(
        self, index: dict, keyword_extractor: Any, pipeline: Any
    ) -> None:
        """Extract keywords from module/function names and documentation.

        For SCIP-based languages, we extract keywords from:
        1. Module names (file paths converted to words)
        2. Function names (camelCase/snake_case split into words)
        3. Any documentation strings stored in the index

        Args:
            index: The Cicada index to update
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion
        """
        if self.verbose:
            print("  Extracting keywords from names and documentation...")

        modules = index.get("modules", {})
        if not isinstance(modules, dict):
            return

        total = len(modules)
        processed = 0

        for idx, (module_name, module_data) in enumerate(modules.items(), 1):
            if not isinstance(module_data, dict):
                continue

            # Skip generic files - they get keywords from text content separately
            if module_data.get("module_type") == "generic_file":
                continue

            if self.verbose and idx % 50 == 0:
                print(
                    f"\r    Processed {idx}/{total} modules (Keywords: {pipeline.stats['submitted']})",
                    end="",
                    flush=True,
                )

            try:
                # Extract keywords from module name
                # Convert _file_src.utils.gameState.js -> src utils game state js
                name_text = module_name.replace("_file_", "").replace(".", " ").replace("_", " ")
                # Split camelCase: gameState -> game State
                name_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", name_text).lower()

                name_result = keyword_extractor.extract_keywords(name_text, top_n=10)
                name_keywords = dict(name_result.get("top_keywords", []))

                # Boost name-derived keywords (1.5x factor)
                for kw in name_keywords:
                    name_keywords[kw] = int(name_keywords[kw] * 1.5) or 1

                # Extract keywords from function names and docs
                functions = module_data.get("functions", [])
                for func in functions:
                    if not isinstance(func, dict):
                        continue
                    func_name = func.get("name", "")
                    func_keywords: dict[str, float] = {}

                    if func_name:
                        # Split function name into words
                        func_text = re.sub(r"([a-z])([A-Z])", r"\1 \2", func_name)
                        func_text = func_text.replace("_", " ").lower()
                        func_result = keyword_extractor.extract_keywords(func_text, top_n=5)
                        func_keywords = dict(func_result.get("top_keywords", []))

                    # Extract from function doc if available
                    func_doc = func.get("doc", "")
                    if func_doc and len(func_doc) > 10:
                        doc_result = keyword_extractor.extract_keywords(func_doc, top_n=10)
                        doc_keywords = dict(doc_result.get("top_keywords", []))
                        for kw, score in doc_keywords.items():
                            func_keywords[kw] = func_keywords.get(kw, 0) + score

                    # Store keywords on the function itself
                    if func_keywords:
                        func["keywords"] = func_keywords

                    # Also merge into module keywords
                    for kw, score in func_keywords.items():
                        name_keywords[kw] = name_keywords.get(kw, 0) + score

                # Extract from module doc if available
                module_doc = module_data.get("moduledoc", "") or module_data.get("doc", "")
                if module_doc and len(module_doc) > 10:
                    doc_result = keyword_extractor.extract_keywords(module_doc, top_n=10)
                    doc_keywords = dict(doc_result.get("top_keywords", []))
                    for kw, score in doc_keywords.items():
                        name_keywords[kw] = name_keywords.get(kw, 0) + score

                if name_keywords:
                    # Store keywords on the module
                    module_data["keywords"] = name_keywords.copy()

                    # Track for stats (NoOpExpansionPipeline just counts)
                    pipeline.submit(
                        list(name_keywords.keys()),
                        name_keywords,
                        module_data,
                        top_n=3,
                        threshold=0.2,
                    )
                    processed += 1

            except Exception as e:
                if self.verbose:
                    print(f"\n    Warning: Failed to extract keywords for {module_name}: {e}")

        if self.verbose:
            print(
                f"\r    Processed {total}/{total} modules (Keywords: {pipeline.stats['submitted']})"
            )

    def _extract_string_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from string literals in source files.

        Uses regex-based extraction to find string literals across all
        SCIP-indexed languages, then runs keyword extraction with 1.3x boost.
        """
        from cicada.languages.scip.string_extractor import RegexStringExtractor

        if self._interrupted:
            return 0

        if self.verbose:
            print("  Extracting string keywords...")

        language = self.get_language_name()
        string_extractor = RegexStringExtractor(language=language, min_length=3)
        processed = 0

        try:
            for _module_name, module_data in index.get("modules", {}).items():
                if self._interrupted:
                    break

                if "string_keywords" in module_data:
                    processed += 1
                    continue

                file_path = module_data.get("file")
                if not file_path:
                    continue

                full_path = repo_path / file_path
                if not full_path.exists():
                    continue

                try:
                    source_code = full_path.read_text(encoding="utf-8")
                    strings = string_extractor.extract_from_source(source_code)

                    if not strings:
                        processed += 1
                        continue

                    module_data["string_sources"] = strings

                    all_string_text = " ".join(s["string"] for s in strings)
                    if all_string_text.strip():
                        keywords_result = keyword_extractor.extract_keywords(
                            all_string_text, top_n=15
                        )

                        string_keywords = {}
                        for keyword, score in keywords_result.get("top_keywords", []):
                            string_keywords[keyword] = score * 1.3

                        if string_keywords:
                            module_data["string_keywords"] = string_keywords.copy()
                            callback = ExpansionCallback(
                                target=module_data, target_key="string_keywords"
                            )
                            if pipeline:
                                for cb, res in pipeline.submit(
                                    list(string_keywords.keys()),
                                    string_keywords,
                                    callback,
                                    top_n=3,
                                    threshold=0.2,
                                ):
                                    self._apply_expansion_result(cb, res)

                    processed += 1

                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Failed to extract strings from {file_path}: {e}")

        except KeyboardInterrupt:
            self._interrupted = True
            if self.verbose:
                print("\n    Keyboard interrupt - saving partial results...")

        return processed

    def _extract_comment_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from full-line comments in source files.

        Uses regex to extract full-line comments (lines starting with // or #)
        and runs keyword extraction on the comment text. Only matches lines
        where the comment marker appears at the start (after optional whitespace)
        to avoid false positives from markers inside string literals (e.g., URLs).
        """
        if self._interrupted:
            return 0

        if self.verbose:
            print("  Extracting comment keywords...")

        from cicada.languages.scip.string_extractor import get_comment_marker

        language = self.get_language_name()
        comment_marker = get_comment_marker(language)
        # Anchor to start of line to avoid matching markers inside strings
        comment_pattern = re.compile(r"^\s*" + re.escape(comment_marker) + r"\s*(.*)")
        processed = 0

        try:
            for _module_name, module_data in index.get("modules", {}).items():
                if self._interrupted:
                    break

                if "comment_keywords" in module_data:
                    processed += 1
                    continue

                file_path = module_data.get("file")
                if not file_path:
                    continue

                full_path = repo_path / file_path
                if not full_path.exists():
                    continue

                try:
                    source_code = full_path.read_text(encoding="utf-8")
                    comments: list[str] = []
                    for line in source_code.splitlines():
                        match = comment_pattern.search(line)
                        if match:
                            text = match.group(1).strip()
                            if len(text) >= 3:
                                comments.append(text)

                    if not comments:
                        processed += 1
                        continue

                    all_comment_text = " ".join(comments)
                    if all_comment_text.strip():
                        keywords_result = keyword_extractor.extract_keywords(
                            all_comment_text, top_n=15
                        )

                        comment_keywords = {}
                        for keyword, score in keywords_result.get("top_keywords", []):
                            comment_keywords[keyword] = score

                        if comment_keywords:
                            module_data["comment_keywords"] = comment_keywords.copy()
                            callback = ExpansionCallback(
                                target=module_data, target_key="comment_keywords"
                            )
                            if pipeline:
                                for cb, res in pipeline.submit(
                                    list(comment_keywords.keys()),
                                    comment_keywords,
                                    callback,
                                    top_n=3,
                                    threshold=0.2,
                                ):
                                    self._apply_expansion_result(cb, res)

                    processed += 1

                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Failed to extract comments from {file_path}: {e}")

        except KeyboardInterrupt:
            self._interrupted = True
            if self.verbose:
                print("\n    Keyboard interrupt - saving partial results...")

        return processed
