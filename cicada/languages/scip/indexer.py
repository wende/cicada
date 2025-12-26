"""SCIP indexer with enrichment support.

This module provides GenericSCIPIndexer which wraps the raw SCIP indexer
from cicada_scip and adds the enrichment pipeline (keywords, timestamps,
cochange analysis).
"""

from pathlib import Path
from typing import Any

from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.keyword_utils import read_keyword_extraction_config

__all__ = ["GenericSCIPIndexer"]

try:
    from cicada_scip.indexer import GenericSCIPIndexer as RawSCIPIndexer
except ImportError:
    RawSCIPIndexer = None  # type: ignore


class GenericSCIPIndexer(BaseIndexer):
    """
    SCIP indexer with enrichment support.

    This class wraps the raw SCIP indexer from cicada_scip and adds the
    enrichment pipeline (keywords, timestamps, cochange analysis).

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
        if RawSCIPIndexer is None:
            raise ImportError(
                "cicada_scip package not installed. Install with: pip install cicada-scip"
            )
        self._raw_indexer: Any = None
        self.excluded_dirs: set[str] = set()

    def _get_raw_indexer(self) -> Any:
        """Get or create the raw SCIP indexer instance."""
        if self._raw_indexer is None:
            # Create a concrete subclass of RawSCIPIndexer
            parent = self

            class ConcreteRawIndexer(RawSCIPIndexer):  # type: ignore
                def get_language_name(self) -> str:
                    return parent.get_language_name()

                def get_file_extensions(self) -> list[str]:
                    return parent.get_file_extensions()

                def get_excluded_dirs(self) -> list[str]:
                    return parent.get_excluded_dirs()

                def _run_scip_indexer(self, repo_path: Path) -> Path:
                    return parent._run_scip_indexer(repo_path)

            self._raw_indexer = ConcreteRawIndexer(verbose=self.verbose)
        return self._raw_indexer

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run the language-specific SCIP indexer. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement _run_scip_indexer")

    def _run_scip_command(
        self,
        repo_path: Path,
        command: list[str],
        *,
        output_path: Path,
        timeout: int = 600,
    ) -> Path:
        """Run a SCIP indexer command using the raw indexer's helper."""
        raw = self._get_raw_indexer()
        return raw._run_scip_command(
            repo_path=repo_path,
            command=command,
            output_path=output_path,
            timeout=timeout,
        )

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
            extract_string_keywords=True,
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
        extract_string_keywords: bool = False,
        compute_timestamps: bool = True,
        extract_cochange: bool = False,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Index repository with optional enrichment.

        This method:
        1. Runs the raw SCIP indexer to get basic index
        2. Runs enrichment pipeline if requested (keywords, timestamps, cochange)
        3. Saves the enriched index

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            extract_keywords: If True, extract keywords from documentation
            extract_string_keywords: If True, extract keywords from string literals
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

        # Step 1: Run raw SCIP indexer (no enrichment)
        raw = self._get_raw_indexer()
        raw.verbose = verbose
        result = raw.incremental_index_repository(
            repo_path=repo_path,
            output_path=output_path,
            extract_keywords=False,  # Raw indexer doesn't do enrichment
            extract_string_keywords=False,
            compute_timestamps=False,
            extract_cochange=False,
            force_full=force_full,
            verbose=verbose,
        )

        if not result.get("success", False):
            return result

        # If no enrichment requested, we're done
        if (
            not extract_keywords
            and not extract_string_keywords
            and not compute_timestamps
            and not extract_cochange
        ):
            return result

        # Step 2: Get the index for enrichment
        cicada_index = result.get("index")
        if not cicada_index:
            return result

        # Step 3: Initialize keyword extractor if needed
        keyword_extractor = None
        keyword_expander = None
        if extract_keywords or extract_string_keywords:
            try:
                from cicada.utils.keyword_utils import create_keyword_extractor

                extraction_method, expansion_method = read_keyword_extraction_config(repo_path_obj)
                keyword_extractor = create_keyword_extractor(
                    extraction_method, expansion_method, verbose=self.verbose
                )
                # keyword_expander is built into the extractor
                if self.verbose:
                    print(f"  Keyword extraction: {extraction_method}")
                    if expansion_method != "none":
                        print(f"  Keyword expansion: {expansion_method}")
            except Exception as e:
                if self.verbose:
                    print(f"  Warning: Could not initialize keyword extractor: {e}")
                    print("  Continuing without keyword extraction...")
                extract_keywords = False
                extract_string_keywords = False

        # Step 4: Run enrichment pipeline
        if extract_keywords or extract_string_keywords or compute_timestamps or extract_cochange:
            if self.verbose:
                print("  Running enrichment pipeline...")

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

            if skipped_phases and self.verbose:
                print(f"  Note: Skipped phases: {', '.join(skipped_phases)}")

        # Step 5: Save enriched index
        self._save_index(cicada_index, output_path_obj)
        result["index"] = cicada_index

        return result

    def _save_index(self, index: dict, output_path: Path) -> None:
        """Save index to JSON file."""
        import json

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

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
                import re

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

    def _extract_comment_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from comments in source files.

        For SCIP-based languages, this is a no-op since we don't have
        tree-sitter parsing to extract comments. Keywords are extracted
        from names and documentation instead.
        """
        # Comment extraction requires tree-sitter which SCIP languages don't use
        # Keywords are already extracted from names and docs in _extract_docstring_keywords
        return 0
