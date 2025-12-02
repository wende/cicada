"""
Abstract base class for language-specific indexers.

All language implementations must subclass BaseIndexer and implement the abstract methods.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any


class BaseIndexer(ABC):
    """
    Universal indexer interface for all programming languages.

    Each language-specific indexer (e.g., ElixirIndexer, PythonIndexer) must
    inherit from this class and implement all abstract methods.

    The indexer is responsible for:
    1. Finding source files in a repository
    2. Coordinating the parsing of those files (language-specific)
    3. Running universal enrichment pipeline (shared)
    4. Building the unified index structure
    5. Saving the index to disk
    """

    # Override this in subclasses that support incremental indexing
    supports_incremental: bool = False

    def __init__(self, verbose: bool = False):
        """Initialize base indexer with common state."""
        self.verbose = verbose
        self._interrupted = False
        self._start_time = 0.0
        self._last_step_time = 0.0

    @abstractmethod
    def get_language_name(self) -> str:
        """
        Return the language identifier for this indexer.

        Returns:
            Language name in lowercase (e.g., 'elixir', 'python', 'typescript')
        """

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """
        Return file extensions to index for this language.

        Returns:
            List of file extensions including dots (e.g., ['.ex', '.exs'], ['.py'])
        """

    @abstractmethod
    def get_excluded_dirs(self) -> list[str]:
        """
        Return language-specific directories to exclude from indexing.

        Returns:
            List of directory names to exclude (e.g., ['deps', '_build'], ['__pycache__', '.venv'])
        """

    @abstractmethod
    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index a repository and save the results.

        Args:
            repo_path: Path to the repository to index
            output_path: Path where the index.json should be saved
            force: If True, reindex all files regardless of changes
            verbose: If True, print detailed progress information
            config_path: Optional path to config.yaml for custom settings

        Returns:
            Dictionary with indexing results:
                {
                    "success": bool,
                    "modules_count": int,
                    "functions_count": int,
                    "files_indexed": int,
                    "errors": list[str]
                }
        """

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        extract_string_keywords: bool = False,
        compute_timestamps: bool = True,
        extract_cochange: bool = True,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Incrementally index a repository using file hashing.

        This method is optional - only indexers that support incremental indexing
        (supports_incremental = True) need to implement this.

        Default implementation raises NotImplementedError. Subclasses that support
        incremental indexing should override this method and set supports_incremental = True.

        Args:
            repo_path: Path to the repository root
            output_path: Path where the index JSON file will be saved
            extract_keywords: If True, extract keywords from documentation using NLP
            extract_string_keywords: If True, extract keywords from string literals
            compute_timestamps: If True, compute git history timestamps for functions
            extract_cochange: If True, analyze git history for co-change patterns
            force_full: If True, ignore existing hashes and do full reindex
            verbose: If True, print detailed progress information

        Returns:
            Dictionary containing the index data

        Raises:
            NotImplementedError: If the indexer does not support incremental indexing
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support incremental indexing. "
            f"Use index_repository() instead."
        )

    def _find_source_files(self, repo_path: Path) -> list[Path]:
        """
        Find all source files to index in the repository.

        Default implementation finds files by extension and excludes
        directories from get_excluded_dirs(). Can be overridden for
        custom file discovery logic.

        Args:
            repo_path: Repository root path

        Returns:
            List of source file paths to index
        """
        source_files = []
        extensions = self.get_file_extensions()
        excluded = set(self.get_excluded_dirs())

        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                # Check if any parent directory is excluded
                if any(part in excluded for part in file_path.parts):
                    continue
                if file_path.is_file():
                    source_files.append(file_path)

        return sorted(source_files)

    def should_index_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be indexed (optional override).

        Default implementation returns True. Override to implement custom
        filtering logic (e.g., skip files by pattern, check file size, etc.).

        Args:
            file_path: Path to check

        Returns:
            True if file should be indexed, False otherwise
        """
        return True

    def get_default_config(self) -> dict:
        """
        Return default configuration for this language (optional override).

        Returns:
            Dictionary with default config values
        """
        return {
            "language": self.get_language_name(),
            "file_extensions": self.get_file_extensions(),
            "excluded_dirs": self.get_excluded_dirs(),
        }

    # ====================================================================================
    # UNIVERSAL ENRICHMENT PIPELINE (Shared across all languages)
    # ====================================================================================
    # After language-specific parsing, all indexers run the same enrichment
    # pipeline: keywords → timestamps → co-change → co-occurrence
    # ====================================================================================

    def _start_timing(self) -> None:
        """Initialize timing for the indexing pipeline."""
        self._start_time = time.time()
        self._last_step_time = self._start_time

    def _log_timing(self, step_name: str) -> None:
        """Log timing for a pipeline step.

        Args:
            step_name: Name of the step to log
        """
        if self.verbose:
            now = time.time()
            elapsed = now - self._last_step_time
            total = now - self._start_time
            print(f"  ⏱️  {step_name}: {elapsed:.2f}s (total: {total:.2f}s)")
            self._last_step_time = now

    def _run_interruptible_phase(
        self,
        phase_name: str,
        phase_func: Callable[[], Any],
        skipped_phases: list[str],
        partial_suffix: str = "",
    ) -> bool:
        """Run an enrichment phase that can be interrupted.

        Args:
            phase_name: Human-readable name of the phase (e.g., "keyword extraction")
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

    def _run_enrichment_pipeline(
        self,
        index: dict,
        repo_path: Path,
        extract_keywords: bool = False,
        extract_string_keywords: bool = False,
        extract_comment_keywords: bool = False,
        compute_timestamps: bool = False,
        extract_cochange: bool = False,
        keyword_extractor: Any = None,
        keyword_expander: Any = None,
    ) -> list[str]:
        """Run universal enrichment pipeline after language-specific parsing.

        This method runs the same enrichment phases for all languages:
        1. Keyword extraction + expansion (streaming pipeline)
        2. Timestamp computation (git history)
        3. Co-change analysis (git history)
        4. Co-occurrence matrix (keyword relationships)

        Args:
            index: The Cicada index to enrich
            repo_path: Repository root path
            extract_keywords: Whether to extract keywords from docstrings
            extract_string_keywords: Whether to extract keywords from string literals
            extract_comment_keywords: Whether to extract keywords from inline comments
            compute_timestamps: Whether to compute git timestamps for functions
            extract_cochange: Whether to analyze co-change patterns
            keyword_extractor: Keyword extractor instance (optional)
            keyword_expander: Keyword expander instance (optional)

        Returns:
            List of skipped phase names (if interrupted)
        """
        skipped_phases: list[str] = []
        self._start_timing()

        # Phase 1: Extract and expand keywords using streaming pipeline (interruptible)
        # Requires extractor; expander is optional (falls back to extraction-only)
        if (
            extract_keywords or extract_string_keywords or extract_comment_keywords
        ) and keyword_extractor:

            if keyword_expander:
                # Full extraction + expansion with streaming pipeline

                def extract_and_expand_keywords() -> None:
                    """Extract and expand keywords with streaming pipeline."""
                    assert keyword_expander is not None  # Type narrowing for closure
                    if self.verbose:
                        print(
                            f"\n  Extracting and expanding keywords "
                            f"(streaming, {keyword_expander.max_workers} workers)..."
                        )

                    from cicada.parallel_expander import StreamingExpansionPipeline

                    with StreamingExpansionPipeline(
                        keyword_expander, max_pending=100, verbose=self.verbose
                    ) as pipeline:
                        # Extract docstring keywords (sequential) with streaming expansion
                        if extract_keywords:
                            self._extract_docstring_keywords(index, keyword_extractor, pipeline)

                        # Extract string keywords (sequential) with streaming expansion
                        if extract_string_keywords:
                            self._extract_string_keywords(
                                index, repo_path, keyword_extractor, pipeline
                            )

                        if extract_comment_keywords:
                            self._extract_comment_keywords(
                                index, repo_path, keyword_extractor, pipeline
                            )

                        # Finish remaining expansions
                        for callback, result in pipeline.finish():
                            self._apply_expansion_result(callback, result)

                        if self.verbose:
                            print()  # New line after progress updates
                            stats = pipeline.stats
                            print(f"    ✓ Expanded {stats['completed']} keyword sets")

                if self._run_interruptible_phase(
                    "keyword extraction/expansion",
                    extract_and_expand_keywords,
                    skipped_phases,
                    partial_suffix=" (partial)",
                ):
                    self._log_timing("Keyword extraction/expansion (streaming)")

            else:
                # Extraction-only fallback when expander is unavailable

                def extract_keywords_only() -> None:
                    """Extract keywords without expansion (fallback mode)."""
                    if self.verbose:
                        print("\n  Extracting keywords (no expansion - expander unavailable)...")

                    from cicada.parallel_expander import NoOpExpansionPipeline

                    # Use no-op pipeline that stores keywords without expansion
                    with NoOpExpansionPipeline() as pipeline:
                        if extract_keywords:
                            self._extract_docstring_keywords(index, keyword_extractor, pipeline)

                        if extract_string_keywords:
                            self._extract_string_keywords(
                                index, repo_path, keyword_extractor, pipeline
                            )

                        if extract_comment_keywords:
                            self._extract_comment_keywords(
                                index, repo_path, keyword_extractor, pipeline
                            )

                        if self.verbose:
                            print(f"    ✓ Extracted {pipeline.stats['submitted']} keyword sets")

                if self._run_interruptible_phase(
                    "keyword extraction",
                    extract_keywords_only,
                    skipped_phases,
                    partial_suffix=" (partial)",
                ):
                    self._log_timing("Keyword extraction (no expansion)")

        # Phase 2: Compute timestamps if requested (interruptible)
        if compute_timestamps and self._run_interruptible_phase(
            "timestamp computation",
            lambda: self._compute_timestamps(index, repo_path),
            skipped_phases,
        ):
            self._log_timing("Timestamp computation")

        # Phase 3: Extract co-change relationships if requested (interruptible)
        if extract_cochange and self._run_interruptible_phase(
            "co-change analysis",
            lambda: self._extract_cochange(index, repo_path),
            skipped_phases,
        ):
            self._log_timing("Co-change analysis")

        # Phase 4: Build co-occurrence matrix (always runs if keywords extracted)
        if extract_keywords or extract_string_keywords:
            if self.verbose:
                print("Building keyword co-occurrence matrix...")
            try:
                from cicada.cooccurrence import CooccurrenceAnalyzer

                analyzer = CooccurrenceAnalyzer(index)
                index["cooccurrences"] = analyzer.cooccurrence_matrix
                stats = analyzer.get_statistics()
                if self.verbose:
                    print(f"  ✓ Tracked {stats['total_keywords']} keywords")
                    print(f"  ✓ Found {stats['total_cooccurrences']} co-occurrence relationships")
                self._log_timing("Co-occurrence matrix")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Failed to build co-occurrence matrix: {e}")

        return skipped_phases

    def _extract_docstring_keywords(
        self, index: dict, keyword_extractor: Any, pipeline: Any
    ) -> None:
        """Extract keywords from module and function docstrings (language-specific).

        This method should be overridden by indexers that use the streaming pipeline.
        If not overridden, the streaming keyword enrichment phase will be skipped.

        Args:
            index: The Cicada index to update
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion
        """
        if self.verbose:
            print("    Warning: Docstring keyword extraction not implemented for this language")

    def _extract_string_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from string literals in source files (language-specific).

        This method should be overridden by indexers that use the streaming pipeline.
        If not overridden, the streaming keyword enrichment phase will be skipped.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion

        Returns:
            Number of items processed (0 if not implemented)
        """
        if self.verbose:
            print("    Warning: String keyword extraction not implemented for this language")
        return 0

    def _extract_comment_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from inline comments in source files (language-specific)."""
        if self.verbose:
            print("    Warning: Comment keyword extraction not implemented for this language")
        return 0

    def _apply_expansion_result(self, callback: Any, result: dict[str, Any]) -> None:
        """Apply expansion result to target dict.

        Args:
            callback: Callback object with target and target_key attributes
            result: Expansion result dict with 'words' list
        """
        if isinstance(result, dict) and "words" in result:
            # Convert expansion result to dict: word -> max_score
            keywords_dict: dict[str, float] = {}
            for item in result["words"]:
                word = item["word"]
                score = item["score"]
                if word not in keywords_dict or score > keywords_dict[word]:
                    keywords_dict[word] = score
            if keywords_dict:
                callback.target[callback.target_key] = keywords_dict
        else:
            if self.verbose:
                print(
                    f"    Warning: Expansion result is not a dict with 'words' key: "
                    f"got {type(result).__name__}"
                )

    def _compute_timestamps(self, index: dict, repo_path: Path) -> None:
        """Compute git timestamps for functions.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
        """
        if self.verbose:
            print("  Computing git timestamps...")

        try:
            from cicada.git.helper import GitHelper

            git_helper = GitHelper(str(repo_path))
        except Exception as e:
            if self.verbose:
                print(f"    Warning: Could not initialize git helper: {e}")
            return

        # Collect all functions with their line numbers (skip those with existing timestamps)
        functions_to_query = []
        skipped_count = 0
        for module_name, module_data in index.get("modules", {}).items():
            file_path = module_data.get("file")
            if not file_path:
                continue

            for func in module_data.get("functions", []):
                # Skip functions that already have timestamps (copied from existing index)
                if "created_at" in func or "last_modified_at" in func:
                    skipped_count += 1
                    continue

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

        if self.verbose and skipped_count > 0:
            print(f"    Reusing timestamps for {skipped_count} unchanged functions")

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
                        # Extract fields
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
            from cicada.git.cochange_analyzer import CoChangeAnalyzer

            analyzer = CoChangeAnalyzer(language=self.get_language_name())
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
                # Initialize cochange_files for all modules
                module_data["cochange_files"] = []

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

            # Integrate function-level co-changes
            function_pairs = cochange_data.get("function_pairs", {})
            for module_name, module_data in index.get("modules", {}).items():
                if "functions" not in module_data:
                    continue

                for func in module_data["functions"]:
                    # Build function signature (language-specific format)
                    func_sig = self._build_function_signature(module_name, func)
                    if func_sig:
                        # Find co-changed functions
                        cochange_funcs = CoChangeAnalyzer.find_cochange_pairs(
                            func_sig, function_pairs
                        )
                        if cochange_funcs:
                            cochange_functions = []
                            for related_func, count in cochange_funcs:
                                parsed = self._parse_function_signature(related_func)
                                if parsed:
                                    cochange_functions.append({**parsed, "count": count})
                            func["cochange_functions"] = cochange_functions
                        else:
                            func["cochange_functions"] = []
                    else:
                        func["cochange_functions"] = []

            if self.verbose:
                print(
                    f"    Found {cochange_data['metadata']['file_pairs']} file pairs, "
                    f"{cochange_data['metadata']['function_pairs']} function pairs"
                )

        except Exception as e:
            if self.verbose:
                print(f"    Warning: Failed to analyze co-changes: {e}")

    def _build_function_signature(self, module_name: str, func: dict) -> str | None:
        """Build function signature string for co-change lookups.

        Builds signatures in universal "Module.function/arity" format.
        Override this method only if a new language needs a different format.

        Args:
            module_name: Name of the module containing the function
            func: Function dict with name and arity keys

        Returns:
            Function signature string, or None if invalid
        """
        func_name = func.get("name")
        arity = func.get("arity", 0)
        if func_name:
            return f"{module_name}.{func_name}/{arity}"
        return None

    def _parse_function_signature(self, func_sig: str) -> dict | None:
        """Parse function signature into components.

        Parses universal "Module.function/arity" format used by all languages.
        Override this method only if a new language needs a different format.

        Args:
            func_sig: Function signature string (e.g., "MyApp.Auth.validate_user/2")

        Returns:
            Dict with module, function, arity keys, or None if invalid
        """
        if "." not in func_sig or "/" not in func_sig:
            return None

        try:
            module_part, func_part = func_sig.rsplit(".", 1)
            func_name, arity_str = func_part.rsplit("/", 1)
            arity = int(arity_str)
            return {"module": module_part, "function": func_name, "arity": arity}
        except (ValueError, AttributeError):
            return None
