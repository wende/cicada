"""Python repository indexer using SCIP protocol.

This indexer uses scip-python (powered by Pyright) to generate
type-aware semantic indexes of Python codebases.
"""

import json
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cicada.parallel_expander import StreamingExpansionPipeline

from cicada.languages.python.scip_installer import SCIPPythonInstaller
from cicada.languages.python.string_extractor import PythonStringExtractor
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.scip.reader import SCIPReader
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.hash_utils import (
    compute_hashes_for_files,
    load_file_hashes,
    save_file_hashes,
)
from cicada.utils.keyword_utils import read_keyword_extraction_config
from cicada.utils.storage import get_hashes_path


def compute_target_directory(changed_files: list[str]) -> str | None:
    """
    Compute minimal common directory from list of changed files.

    For incremental SCIP indexing, we want to limit analysis to the smallest
    directory tree that contains all changed files.

    Args:
        changed_files: List of relative file paths that changed

    Returns:
        Common parent directory path, or None if files span the entire repo
        (no benefit to using --target-only in that case)
    """
    if not changed_files:
        return None

    # Get parent directories of all changed files
    parent_dirs = [str(Path(f).parent) for f in changed_files]

    # Find common prefix path
    if len(parent_dirs) == 1:
        return parent_dirs[0] if parent_dirs[0] != "." else None

    # Split paths into parts and find common prefix
    split_paths = [Path(p).parts for p in parent_dirs]
    common_parts: list[str] = []

    for parts in zip(*split_paths, strict=False):
        if len(set(parts)) == 1:
            common_parts.append(parts[0])
        else:
            break

    if not common_parts:
        # Files span different top-level directories - no benefit
        return None

    common_path = str(Path(*common_parts))
    # Don't return "." as it's the repo root
    return common_path if common_path != "." else None


@dataclass
class ExpansionCallback:
    """Callback data for streaming expansion pipeline."""

    target: dict[str, Any]  # The module/function dict to update
    target_key: str  # "keywords" or "string_keywords"


class PythonSCIPIndexer(BaseIndexer):
    """Index Python repositories using scip-python."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the Python SCIP indexer.

        Args:
            verbose: If True, print detailed progress information
        """
        super().__init__(verbose=verbose)
        self.excluded_dirs = {
            "__pycache__",
            ".venv",
            "venv",
            ".git",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".egg-info",
            ".tox",
            ".ruff_cache",
            "htmlcov",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "python"

    def get_file_extensions(self) -> list[str]:
        """Return Python file extensions."""
        return [".py"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_interruptible_phase(
        self,
        phase_name: str,
        phase_func: Callable[[], Any],
        skipped_phases: list[str],
        partial_suffix: str = "",
    ) -> bool:
        """Run an enrichment phase that can be interrupted.

        Args:
            phase_name: Human-readable name of the phase (e.g., "string keywords")
            phase_func: Callable that performs the phase work
            skipped_phases: List to append skipped phase names to
            partial_suffix: Suffix to add if interrupted mid-phase (e.g., " (partial)")

        Returns:
            True if the phase completed successfully, False otherwise
        """
        if self._interrupted:
            skipped_phases.append(phase_name)
            return False

        try:
            phase_func()
            return True
        except KeyboardInterrupt:
            self._interrupted = True
            skipped_phases.append(f"{phase_name}{partial_suffix}")
            if self.verbose:
                print(f"\n  ⚠️  Interrupted during {phase_name}")
            return False
        except Exception as e:
            if self.verbose:
                print(f"    Warning: {phase_name.capitalize()} failed: {e}")
            skipped_phases.append(phase_name)
            return False

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index Python repository using scip-python.

        This is the basic interface that delegates to incremental_index_repository.

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
            extract_keywords=True,
            extract_string_keywords=True,  # Enable string keyword extraction
            compute_timestamps=True,  # Enabled by default for timestamp tracking
            extract_cochange=False,
            force_full=force,
            verbose=verbose,
        )

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        extract_string_keywords: bool = False,
        compute_timestamps: bool = True,
        extract_cochange: bool = False,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Index Python repository with all features.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            extract_keywords: Whether to extract keywords from docstrings
            extract_string_keywords: Whether to extract keywords from string literals
            compute_timestamps: Whether to compute git timestamps for functions
            extract_cochange: Whether to analyze co-change patterns
            force_full: If True, force full reindex even if up-to-date
            verbose: If True, print detailed progress information (default: True)

        Returns:
            Dict with indexing results
        """
        # Update verbosity setting from parameter
        self.verbose = verbose

        # Reset interrupted flag at start of new run
        self._interrupted = False

        repo_path_obj = Path(repo_path).resolve()
        output_path_obj = Path(output_path).resolve()

        # Start timing
        self._start_timing()

        if self.verbose:
            print(f"Indexing Python repository: {repo_path_obj}")

        # Check if we can skip reindexing
        hashes_path = get_hashes_path(repo_path_obj)
        existing_hashes = load_file_hashes(str(hashes_path))

        # Find all Python files
        python_files = list(self._find_python_files(repo_path_obj))
        self._log_timing("File discovery")

        # Convert to relative paths for comparison
        relative_files = [str(f.relative_to(repo_path_obj)) for f in python_files]

        # Compute current hashes ONCE at the start - these will be saved at the end
        # This prevents race conditions where files change during indexing
        current_hashes = compute_hashes_for_files(relative_files, str(repo_path_obj))

        # Detect changes by comparing current hashes against existing hashes
        current_file_set = set(current_hashes.keys())
        old_file_set = set(existing_hashes.keys())
        deleted_files = list(old_file_set - current_file_set)
        new_files = [f for f in current_hashes if f not in existing_hashes]
        modified_files = [
            f
            for f in current_hashes
            if f in existing_hashes and current_hashes[f] != existing_hashes[f]
        ]

        if not force_full and not new_files and not modified_files and not deleted_files:
            if self.verbose:
                print("  No changes detected. Index is up to date.")
            # Load and return existing index
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
                }

        if self.verbose:
            if new_files or modified_files or deleted_files:
                print(
                    f"  Changes detected: {len(new_files)} new, {len(modified_files)} modified, {len(deleted_files)} deleted"
                )
            else:
                print("  Performing full index...")

        # 1. Ensure scip-python is installed
        self._ensure_scip_python_installed()
        self._log_timing("SCIP-python check")

        # 2. Run scip-python indexer
        # For incremental indexing, limit SCIP to changed file directories
        target_only = None
        if not force_full and (new_files or modified_files):
            changed_files = new_files + modified_files
            target_only = compute_target_directory(changed_files)
            if self.verbose and target_only:
                print(f"  Limiting SCIP analysis to: {target_only}")
            elif self.verbose and not target_only:
                print("  Changed files span repo root, running full SCIP")
                if len(changed_files) <= 5:
                    print(f"    Files: {changed_files}")

        scip_file = self._run_scip_python(repo_path_obj, target_only=target_only)
        self._log_timing("SCIP-python indexing")

        try:
            # 3. Read .scip file
            try:
                reader = SCIPReader()
                scip_index = reader.read_index(scip_file)

                if self.verbose:
                    summary = reader.get_index_summary(scip_index)
                    print(
                        f"  SCIP index: {summary['documents']} documents, "
                        f"{summary['symbols']} symbols"
                    )
                self._log_timing("SCIP file reading")
            except Exception as e:
                raise RuntimeError(f"Failed to read SCIP index: {e}") from e

            # 4. Initialize keyword extractor from config
            keyword_extractor = None
            keyword_expander = None
            if extract_keywords or extract_string_keywords:
                try:
                    extraction_method, expansion_method = read_keyword_extraction_config(
                        repo_path_obj
                    )
                    from cicada.extractors.keyword import RegularKeywordExtractor

                    keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)

                    # Initialize parallel keyword expander with streaming pipeline
                    from cicada.parallel_expander import ParallelKeywordExpander

                    keyword_expander = ParallelKeywordExpander(
                        expansion_type=expansion_method, verbose=self.verbose
                    )
                    self._log_timing("Keyword extractor initialization")
                except NotImplementedError:
                    raise
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Keyword extractor initialization failed: {e}")
                    keyword_extractor = None
                    keyword_expander = None

            # 5. Convert to Cicada format (without keyword extraction - that's done separately)
            try:
                converter = SCIPConverter(
                    extract_keywords=False,  # Don't extract during conversion - too slow
                    keyword_extractor=None,
                    verbose=self.verbose,
                )
                cicada_index = converter.convert(scip_index, repo_path_obj)
                self._log_timing("SCIP to Cicada conversion")
            except Exception as e:
                raise RuntimeError(f"Failed to convert SCIP to Cicada format: {e}") from e

            # 5b. Copy keywords from existing index for unchanged modules (optimization)
            changed_files = set(new_files + modified_files)
            copied_count = self._copy_unchanged_keywords(
                cicada_index, output_path_obj, changed_files
            )
            if self.verbose and copied_count > 0:
                print(f"  ✓ Reused keywords from {copied_count} unchanged modules")

            # 5-8. Run universal enrichment pipeline (shared across all languages)
            # Note: _run_enrichment_pipeline will skip modules that already have keywords
            skipped_phases = self._run_enrichment_pipeline(
                cicada_index,
                repo_path_obj,
                extract_keywords=extract_keywords,
                extract_string_keywords=extract_string_keywords,
                extract_comment_keywords=extract_keywords,
                compute_timestamps=compute_timestamps,
                extract_cochange=extract_cochange,
                keyword_extractor=keyword_extractor,
                keyword_expander=keyword_expander,
            )

            # 9. Save index
            try:
                self._save_index(cicada_index, output_path_obj)
                self._log_timing("Index saving")
            except Exception as e:
                raise RuntimeError(f"Failed to save index: {e}") from e

            # 10. Save file hashes (use hashes computed at start to avoid race conditions)
            # If files change DURING indexing, the pending reindex will detect them
            try:
                if current_hashes:  # current_hashes computed at start of indexing
                    save_file_hashes(str(hashes_path), current_hashes)
                self._log_timing("Hash saving")
            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Failed to save file hashes: {e}")

            # 11. Build result summary
            all_modules = cicada_index.get("modules", {})
            modules_count = len(all_modules)
            functions_count = cicada_index.get("metadata", {}).get("total_functions", 0)

            # Count files vs classes for better reporting
            file_count = sum(1 for name in all_modules if name.startswith("_file_"))
            class_count = modules_count - file_count

            if self.verbose:
                if class_count > 0:
                    print(
                        f"  Indexed {file_count} files, {class_count} classes, {functions_count} functions"
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
                "interrupted": self._interrupted,
                "skipped_phases": skipped_phases,
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
            # Cleanup temporary .scip file
            if scip_file.exists():
                scip_file.unlink()
                if self.verbose:
                    print(f"  Cleaned up temporary file: {scip_file}")

    def _copy_unchanged_keywords(
        self, new_index: dict, existing_index_path: Path, changed_files: set[str]
    ) -> int:
        """Copy keywords from existing index for modules whose files haven't changed.

        This optimization avoids re-extracting keywords for unchanged modules,
        significantly speeding up incremental indexing.

        Args:
            new_index: The freshly built index to update
            existing_index_path: Path to the existing index.json
            changed_files: Set of relative file paths that have changed

        Returns:
            Number of modules that had keywords copied
        """
        if not existing_index_path.exists():
            return 0

        try:
            with open(existing_index_path) as f:
                existing_index = json.load(f)
        except (OSError, json.JSONDecodeError):
            return 0

        existing_modules = existing_index.get("modules", {})
        new_modules = new_index.get("modules", {})
        copied_count = 0

        for module_name, module_data in new_modules.items():
            file_path = module_data.get("file", "")

            # Skip if file has changed - needs fresh keyword extraction
            if file_path in changed_files:
                continue

            # Find corresponding module in existing index
            existing_module = existing_modules.get(module_name)
            if not existing_module:
                continue

            # Track if we actually copied anything for this module
            copied_something = False

            # Copy module-level keywords if present
            if "keywords" in existing_module:
                module_data["keywords"] = existing_module["keywords"]
                copied_something = True
            if "string_keywords" in existing_module:
                module_data["string_keywords"] = existing_module["string_keywords"]
                copied_something = True

            # Copy function-level keywords and timestamps
            existing_funcs = {f["name"]: f for f in existing_module.get("functions", [])}
            for func in module_data.get("functions", []):
                existing_func = existing_funcs.get(func["name"])
                if existing_func:
                    # Copy keywords
                    if "keywords" in existing_func:
                        func["keywords"] = existing_func["keywords"]
                        copied_something = True
                    if "string_keywords" in existing_func:
                        func["string_keywords"] = existing_func["string_keywords"]
                        copied_something = True
                    # Copy timestamps
                    for ts_field in [
                        "created_at",
                        "last_modified_at",
                        "last_modified_sha",
                        "modification_count",
                        "modification_frequency",
                    ]:
                        if ts_field in existing_func:
                            func[ts_field] = existing_func[ts_field]
                            copied_something = True

            # Only increment count if we actually copied at least one field
            if copied_something:
                copied_count += 1

        return copied_count

    def _find_python_files(self, repo_path: Path) -> list[Path]:
        """Find all Python files in repository.

        Args:
            repo_path: Repository root path

        Returns:
            List of Python file paths
        """
        python_files = []
        for py_file in repo_path.rglob("*.py"):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in self.excluded_dirs):
                continue
            python_files.append(py_file)
        return python_files

    def _expand_and_update_keywords(
        self, keywords: dict[str, float], keyword_expander
    ) -> dict[str, float]:
        """Expand keywords and update scores with expanded terms.

        Args:
            keywords: Dictionary of keyword -> score mappings
            keyword_expander: Keyword expander instance (optional)

        Returns:
            Updated keywords dictionary with expanded terms
        """
        if not keyword_expander or not keywords:
            return keywords

        expansion_result = keyword_expander.expand_keywords(
            list(keywords.keys()),
            keyword_scores=keywords,
        )

        updated_keywords = keywords.copy()
        for item in expansion_result["words"]:
            word = item["word"]
            score = item["score"]
            if word not in updated_keywords or score > updated_keywords[word]:
                updated_keywords[word] = score

        return updated_keywords

    def _extract_keywords_from_text(
        self, text: str, keyword_extractor, keyword_expander, top_n: int = 10
    ) -> dict[str, float] | None:
        """Extract and expand keywords from text. Returns None if no keywords."""
        if not text:
            return None

        result = keyword_extractor.extract_keywords(text, top_n=top_n)
        keywords = dict(result.get("top_keywords", []))

        if not keywords:
            return None

        return self._expand_and_update_keywords(keywords, keyword_expander)

    def _extract_module_keywords(
        self, module_data: dict, keyword_extractor, keyword_expander
    ) -> None:
        """Extract keywords for a single module and its functions."""
        # Module-level: combine moduledoc + all function docs
        module_doc = module_data.get("moduledoc", "")
        functions = module_data.get("functions", [])
        func_docs = " ".join(f.get("doc", "") for f in functions)
        combined_text = f"{module_doc} {func_docs}".strip()

        keywords = self._extract_keywords_from_text(
            combined_text, keyword_extractor, keyword_expander, top_n=10
        )
        if keywords:
            module_data["keywords"] = keywords

        # Function-level keywords
        for func in functions:
            func_keywords = self._extract_keywords_from_text(
                func.get("doc", ""), keyword_extractor, keyword_expander, top_n=5
            )
            if func_keywords:
                func["keywords"] = func_keywords

    def _extract_docstring_keywords(
        self, index: dict, keyword_extractor, pipeline: "StreamingExpansionPipeline"
    ) -> None:
        """Extract keywords from module and function docstrings.

        Extraction is sequential, expansion is submitted to streaming pipeline.

        Args:
            index: The Cicada index to update
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion
        """
        if self.verbose:
            print("  Extracting keywords from docstrings...")

        modules = index.get("modules", {})

        # Defensive check: ensure modules is a dict
        if not isinstance(modules, dict):
            if self.verbose:
                print(
                    f"    Warning: modules is not a dict (got {type(modules).__name__}), skipping keyword extraction"
                )
            return

        total = len(modules)

        skipped_count = 0
        for idx, (module_name, module_data) in enumerate(modules.items(), 1):
            # Defensive check: ensure module_data is a dict
            if not isinstance(module_data, dict):
                if self.verbose:
                    print(f"    Warning: module_data for {module_name} is not a dict, skipping")
                continue

            # Skip modules that already have keywords (copied from existing index)
            if "keywords" in module_data:
                skipped_count += 1
                continue

            if self.verbose and idx % 50 == 0 and pipeline:
                print(
                    f"\r    Processed {idx}/{total} items (files + classes) - Expansion jobs: {pipeline.stats['submitted']}, Reused: {skipped_count}",
                    end="",
                    flush=True,
                )

            try:
                # Extract module-level keywords from moduledoc + function docs
                module_doc = module_data.get("moduledoc", "")
                functions = module_data.get("functions", [])
                func_docs = " ".join(f.get("doc", "") for f in functions)
                combined_text = f"{module_doc} {func_docs}".strip()

                if combined_text:
                    result = keyword_extractor.extract_keywords(combined_text, top_n=10)
                    keywords = {}
                    for keyword, score in result.get("top_keywords", []):
                        keywords[keyword] = score

                    if keywords:
                        # Store extracted keywords and submit expansion
                        module_data["keywords"] = keywords.copy()
                        callback = ExpansionCallback(target=module_data, target_key="keywords")
                        for cb, res in pipeline.submit(
                            list(keywords.keys()), keywords, callback, top_n=3, threshold=0.2
                        ):
                            self._apply_expansion_result(cb, res)

                # Extract function-level keywords
                for func in functions:
                    func_doc = func.get("doc", "")
                    if func_doc:
                        result = keyword_extractor.extract_keywords(func_doc, top_n=5)
                        func_keywords = {}
                        for keyword, score in result.get("top_keywords", []):
                            func_keywords[keyword] = score

                        if func_keywords:
                            # Store extracted keywords and submit expansion
                            func["keywords"] = func_keywords.copy()
                            callback = ExpansionCallback(target=func, target_key="keywords")
                            for cb, res in pipeline.submit(
                                list(func_keywords.keys()),
                                func_keywords,
                                callback,
                                top_n=3,
                                threshold=0.2,
                            ):
                                self._apply_expansion_result(cb, res)

            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Failed to extract keywords from {module_name}: {e}")

    def _extract_string_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor,
        pipeline: "StreamingExpansionPipeline",
    ) -> int:
        """Extract keywords from string literals in Python files.

        Extraction is sequential, expansion is submitted to streaming pipeline.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion

        Returns:
            Number of modules processed
        """
        # Check if interrupted before starting
        if self._interrupted:
            return 0

        if self.verbose:
            print("  Extracting string keywords...")

        string_extractor = PythonStringExtractor(min_length=3)
        processed = 0

        try:
            for _module_name, module_data in index.get("modules", {}).items():
                # Check for interrupt
                if self._interrupted:
                    break

                # Skip modules that already have string_keywords (copied from existing index)
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

                    # Store string sources
                    module_data["string_sources"] = strings

                    # Extract keywords from all strings
                    all_string_text = " ".join(s["string"] for s in strings)
                    if all_string_text.strip():
                        keywords_result = keyword_extractor.extract_keywords(
                            all_string_text, top_n=15
                        )

                        # Apply string keyword boost (1.3x)
                        string_keywords = {}
                        for keyword, score in keywords_result.get("top_keywords", []):
                            string_keywords[keyword] = score * 1.3

                        if string_keywords:
                            # Store extracted keywords and submit expansion
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

    def _ensure_scip_python_installed(self):
        """
        Ensure scip-python is installed.

        Checks for existing installation (global or local), and auto-installs
        locally to ~/.cicada/node/ if not found and npm is available.

        Raises:
            RuntimeError: If scip-python is not available and cannot be installed
        """
        if SCIPPythonInstaller.is_scip_python_installed():
            if self.verbose:
                version = SCIPPythonInstaller.get_scip_python_version()
                scip_path = SCIPPythonInstaller.get_scip_python_path()
                if SCIPPythonInstaller.is_local_install(scip_path):
                    print(f"  Using scip-python {version} (local)")
                else:
                    print(f"  Using scip-python {version}")
            return

        # Try to auto-install locally
        if SCIPPythonInstaller.is_npm_available():
            if self.verbose:
                print("  scip-python not found, installing locally...")
            if SCIPPythonInstaller.install_locally(verbose=self.verbose):
                return

        raise RuntimeError(
            "scip-python is required to index Python repositories.\n"
            "npm is required to install it. Please install Node.js, then run:\n"
            "  cicada index <path>  # will auto-install scip-python\n"
            "Or install manually:\n"
            "  npm install -g @sourcegraph/scip-python"
        )

    def _run_scip_python(self, repo_path: Path, target_only: str | None = None) -> Path:
        """
        Run scip-python indexer on repository.

        Args:
            repo_path: Repository root path
            target_only: Optional path to limit SCIP analysis to (for incremental indexing).
                        When provided, only files under this path are analyzed by SCIP.
                        Cross-references from other directories may become stale.

        Returns:
            Path to generated .scip file

        Raises:
            RuntimeError: If scip-python execution fails
        """
        # Create temporary pyrightconfig.json to exclude .venv and dependencies
        pyright_config_path = repo_path / "pyrightconfig.json"
        temp_pyright_config = False

        if not pyright_config_path.exists():
            temp_pyright_config = True
            pyright_config = {"exclude": list(self.excluded_dirs)}
            with open(pyright_config_path, "w") as f:
                json.dump(pyright_config, f, indent=2)
            if self.verbose:
                print("  Created temporary pyrightconfig.json to exclude dependencies")

        # Create temporary file for .scip output in system temp directory
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scip", delete=False) as tmp:
            scip_file = Path(tmp.name)

        # Get scip-python path (global or local)
        # Note: _ensure_scip_python_installed() must be called before this method
        scip_python_path = SCIPPythonInstaller.get_scip_python_path()
        if scip_python_path is None:
            raise RuntimeError("scip-python not found - call _ensure_scip_python_installed() first")

        cmd: list[str] = [
            scip_python_path,
            "index",
            str(repo_path),
            "--project-name",
            repo_path.name,
            "--output",
            str(scip_file),
        ]

        if target_only:
            cmd.extend(["--target-only", target_only])

        if self.verbose:
            if target_only:
                print(f"  Running SCIP on {target_only} (partial incremental indexing)")
            else:
                print("  Running SCIP (This may take several minutes for large projects...)")

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"scip-python indexing failed:\n{result.stderr}")

            if not scip_file.exists():
                raise RuntimeError(f"scip-python did not generate {scip_file}")

            return scip_file

        except subprocess.TimeoutExpired as e:
            if scip_file.exists():
                scip_file.unlink()
            raise RuntimeError(
                "scip-python indexing timed out after 10 minutes. "
                "Try indexing a smaller subset of the project."
            ) from e
        except BaseException:
            # Cleanup on any exception including KeyboardInterrupt
            if scip_file.exists():
                scip_file.unlink()
            raise
        finally:
            # Clean up temporary pyrightconfig if we created it
            if temp_pyright_config and pyright_config_path.exists():
                pyright_config_path.unlink()

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
