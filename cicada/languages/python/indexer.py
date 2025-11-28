"""Python repository indexer using SCIP protocol.

This indexer uses scip-python (powered by Pyright) to generate
type-aware semantic indexes of Python codebases.
"""

import json
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cicada.git.cochange_analyzer import CoChangeAnalyzer
from cicada.git.helper import GitHelper
from cicada.languages.python.scip_installer import SCIPPythonInstaller
from cicada.languages.python.string_extractor import PythonStringExtractor
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.scip.reader import SCIPReader
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.hash_utils import (
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada.utils.keyword_utils import read_keyword_extraction_config
from cicada.utils.storage import get_hashes_path


class PythonSCIPIndexer(BaseIndexer):
    """Index Python repositories using scip-python."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the Python SCIP indexer.

        Args:
            verbose: If True, print detailed progress information
        """
        self.verbose = verbose
        self._interrupted = False
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
            extract_string_keywords=False,
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
        # Reset interruption flag for new indexing run
        self._interrupted = False

        repo_path_obj = Path(repo_path).resolve()
        output_path_obj = Path(output_path).resolve()

        # Start timing
        start_time = time.time()
        last_step_time = start_time

        def log_timing(step_name: str):
            nonlocal last_step_time
            if self.verbose:
                now = time.time()
                elapsed = now - last_step_time
                total = now - start_time
                print(f"  ⏱️  {step_name}: {elapsed:.2f}s (total: {total:.2f}s)")
                last_step_time = now

        if self.verbose:
            print(f"Indexing Python repository: {repo_path_obj}")

        # Check if we can skip reindexing
        hashes_path = get_hashes_path(repo_path_obj)
        existing_hashes = load_file_hashes(str(hashes_path))

        # Find all Python files
        python_files = list(self._find_python_files(repo_path_obj))
        log_timing("File discovery")

        # Convert to relative paths for comparison
        relative_files = [str(f.relative_to(repo_path_obj)) for f in python_files]

        # Check for changes
        new_files, modified_files, deleted_files = detect_file_changes(
            relative_files, existing_hashes, str(repo_path_obj)
        )

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
        log_timing("SCIP-python check")

        # 2. Run scip-python indexer
        scip_file = self._run_scip_python(repo_path_obj)
        log_timing("SCIP-python indexing")

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
                log_timing("SCIP file reading")
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

                    if extraction_method == "bert":
                        from cicada.extractors.keybert import KeyBERTExtractor

                        keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                    else:
                        from cicada.extractors.keyword import RegularKeywordExtractor

                        keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)

                    # Initialize keyword expander
                    from cicada.keyword_expander import KeywordExpander

                    keyword_expander = KeywordExpander(
                        expansion_type=expansion_method, verbose=self.verbose
                    )
                    log_timing("Keyword extractor initialization")
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Keyword extractor initialization failed: {e}")
                    keyword_extractor = None
                    keyword_expander = None

            # 5. Convert to Cicada format (without keyword extraction - that's done separately)
            try:
                converter = SCIPConverter(
                    extract_keywords=False,  # Extraction done separately for timing visibility
                    keyword_extractor=None,
                    verbose=self.verbose,
                )
                cicada_index = converter.convert(scip_index, repo_path_obj)
                log_timing("SCIP to Cicada conversion")
            except Exception as e:
                raise RuntimeError(f"Failed to convert SCIP to Cicada format: {e}") from e

            # 5.5-8. Optional enrichment phases (interruptible - will save partial progress)
            # These phases can be interrupted and we'll still save what we have
            skipped_phases = []

            # 5.5. Extract keywords from docstrings if requested
            if (
                extract_keywords
                and keyword_extractor
                and self._run_interruptible_phase(
                    "docstring keywords",
                    lambda: self._extract_docstring_keywords(
                        cicada_index, keyword_extractor, keyword_expander
                    ),
                    skipped_phases,
                )
            ):
                log_timing("Docstring keyword extraction")

            # 6. Extract string keywords if requested
            if (
                extract_string_keywords
                and keyword_extractor
                and self._run_interruptible_phase(
                    "string keywords",
                    lambda: self._extract_string_keywords(
                        cicada_index, repo_path_obj, keyword_extractor, keyword_expander
                    ),
                    skipped_phases,
                    partial_suffix=" (partial)",
                )
            ):
                log_timing("String keyword extraction")

            # 7. Compute timestamps if requested
            if compute_timestamps and self._run_interruptible_phase(
                "timestamp computation",
                lambda: self._compute_timestamps(cicada_index, repo_path_obj),
                skipped_phases,
            ):
                log_timing("Timestamp computation")

            # 8. Extract co-change relationships if requested
            if extract_cochange and self._run_interruptible_phase(
                "co-change analysis",
                lambda: self._extract_cochange(cicada_index, repo_path_obj),
                skipped_phases,
            ):
                log_timing("Co-change analysis")

            # 9. Save index (always attempt, even if interrupted)
            try:
                self._save_index(cicada_index, output_path_obj)
                log_timing("Index saving")
            except Exception as e:
                raise RuntimeError(f"Failed to save index: {e}") from e

            # 10. Save file hashes (always attempt, even if interrupted)
            try:
                if python_files:  # Only compute hashes if we have files
                    current_hashes = compute_hashes_for_files([str(f) for f in python_files])
                    save_file_hashes(str(hashes_path.parent), current_hashes)
                log_timing("Hash computation and saving")
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

            if self._interrupted:
                if self.verbose:
                    print(
                        f"\n  ✓ Partial index saved ({modules_count} modules, {functions_count} functions)"
                    )
                    if skipped_phases:
                        print(f"  Skipped phases: {', '.join(skipped_phases)}")
                    print(f"  Index saved to: {output_path_obj}")
                    print("  Run again with same options to complete enrichment phases.")
            elif self.verbose:
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

    def _extract_docstring_keywords(self, index: dict, keyword_extractor, keyword_expander) -> None:
        """Extract keywords from module and function docstrings."""
        if self.verbose:
            print("  Extracting keywords from docstrings...")

        modules = index.get("modules", {})
        if not isinstance(modules, dict):
            if self.verbose:
                print(
                    f"    Warning: modules is not a dict (got {type(modules).__name__}), skipping"
                )
            return

        total = len(modules)
        for idx, (module_name, module_data) in enumerate(modules.items(), 1):
            if not isinstance(module_data, dict):
                if self.verbose:
                    print(f"    Warning: module_data for {module_name} is not a dict, skipping")
                continue

            if self.verbose and idx % 50 == 0:
                print(f"    Processed {idx}/{total} modules...")

            try:
                self._extract_module_keywords(module_data, keyword_extractor, keyword_expander)
            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Failed to extract keywords from {module_name}: {e}")

    def _extract_string_keywords(
        self, index: dict, repo_path: Path, keyword_extractor, keyword_expander
    ) -> int:
        """Extract keywords from string literals in Python files.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
            keyword_extractor: Keyword extractor instance
            keyword_expander: Keyword expander instance

        Returns:
            Number of modules processed (may be partial if interrupted)
        """
        modules = list(index.get("modules", {}).items())
        total_modules = len(modules)

        if self.verbose:
            print(f"  Extracting string keywords from {total_modules} modules...")

        string_extractor = PythonStringExtractor(min_length=3)
        processed = 0

        for _module_name, module_data in modules:
            # Check for interruption after each module
            if self._interrupted:
                break

            file_path = module_data.get("file")
            if not file_path:
                processed += 1
                continue

            full_path = repo_path / file_path
            if not full_path.exists():
                processed += 1
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
                    keywords_result = keyword_extractor.extract_keywords(all_string_text, top_n=15)

                    # Apply string keyword boost (1.3x)
                    string_keywords = {}
                    for keyword, score in keywords_result.get("top_keywords", []):
                        string_keywords[keyword] = score * 1.3

                    if string_keywords:
                        string_keywords = self._expand_and_update_keywords(
                            string_keywords, keyword_expander
                        )
                        module_data["string_keywords"] = string_keywords

                processed += 1

                # Progress reporting
                if self.verbose and processed % 50 == 0:
                    print(f"    Processed {processed}/{total_modules} modules...")

            except Exception as e:
                processed += 1
                if self.verbose:
                    print(f"    Warning: Failed to extract strings from {file_path}: {e}")

        return processed

    def _compute_timestamps(self, index: dict, repo_path: Path) -> None:
        """Compute git timestamps for functions.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
        """
        if self.verbose:
            print("  Computing git timestamps...")

        try:
            git_helper = GitHelper(str(repo_path))
        except Exception as e:
            if self.verbose:
                print(f"    Warning: Could not initialize git helper: {e}")
            return

        # Collect all functions with their line numbers
        functions_to_query = []
        for module_name, module_data in index.get("modules", {}).items():
            file_path = module_data.get("file")
            if not file_path:
                continue

            for func in module_data.get("functions", []):
                func_name = func.get("name")
                line = func.get("line")
                if func_name and line:
                    functions_to_query.append(
                        {
                            "file": file_path,
                            "name": func_name,
                            "line": line,
                            "module": module_name,
                            "func_ref": func,
                        }
                    )

        if not functions_to_query:
            return

        # Group functions by file for batched queries
        functions_by_file: dict[str, list[dict]] = {}
        for func_info in functions_to_query:
            file_path = func_info["file"]
            if file_path not in functions_by_file:
                functions_by_file[file_path] = []
            functions_by_file[file_path].append(func_info)

        # Query git for function evolution in batch per file
        try:
            for file_path, file_functions in functions_by_file.items():
                # Prepare function list for batch query
                functions_for_git = [{"name": f["name"], "line": f["line"]} for f in file_functions]

                # Get evolution data for all functions in this file
                evolution_data = git_helper.get_functions_evolution_batch(
                    file_path, functions_for_git
                )

                # Update functions with timestamp data
                for func_info in file_functions:
                    func_name = func_info["name"]
                    evolution = evolution_data.get(func_name)
                    if evolution and isinstance(evolution, dict):
                        # Extract fields like Elixir indexer does
                        func_ref = func_info["func_ref"]
                        created_at = evolution.get("created_at")
                        last_modified = evolution.get("last_modified")

                        if created_at and isinstance(created_at, dict):
                            func_ref["created_at"] = created_at.get("date")
                        if last_modified and isinstance(last_modified, dict):
                            func_ref["last_modified_at"] = last_modified.get("date")
                            func_ref["last_modified_sha"] = last_modified.get("sha")
                        if "total_modifications" in evolution:
                            func_ref["modification_count"] = evolution["total_modifications"]
                        if "modification_frequency" in evolution:
                            func_ref["modification_frequency"] = evolution["modification_frequency"]

        except Exception as e:
            if self.verbose:
                print(f"    Warning: Failed to compute timestamps: {e}")

    def _extract_cochange(self, index: dict, repo_path: Path) -> None:
        """Extract co-change relationships from git history.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
        """
        if self.verbose:
            print("  Analyzing co-change patterns from git history...")

        try:
            analyzer = CoChangeAnalyzer(language="python")
            cochange_data = analyzer.analyze_repository(str(repo_path))

            # Add co-change metadata to index
            index["cochange_metadata"] = cochange_data["metadata"]

            # Integrate file-level co-changes into modules
            file_to_module = {}
            for module_name, module_data in index.get("modules", {}).items():
                file_path = module_data.get("file")
                if file_path:
                    file_to_module[file_path] = module_name

            # Add co-change files to modules
            for _module_name, module_data in index.get("modules", {}).items():
                file_path = module_data.get("file")
                if not file_path:
                    continue

                # Find co-changed files
                cochanges = CoChangeAnalyzer.find_cochange_pairs(
                    file_path, cochange_data["file_pairs"]
                )

                if cochanges:
                    module_data["cochange_files"] = [
                        {
                            "file": related_file,
                            "count": count,
                            "module": file_to_module.get(related_file),
                        }
                        for related_file, count in sorted(cochanges, key=lambda x: -x[1])[:10]
                    ]

            if self.verbose:
                print(
                    f"    Found {cochange_data['metadata']['file_pairs']} file pairs, "
                    f"{cochange_data['metadata']['function_pairs']} function pairs"
                )

        except Exception as e:
            if self.verbose:
                print(f"    Warning: Failed to analyze co-changes: {e}")

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

    def _run_scip_python(self, repo_path: Path) -> Path:
        """
        Run scip-python indexer on repository.

        Args:
            repo_path: Repository root path

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

        if self.verbose:
            print("  Running SCIP")
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
        except KeyboardInterrupt:
            # Clean up and re-raise to propagate to command layer
            if scip_file.exists():
                scip_file.unlink()
            raise
        except Exception:
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
