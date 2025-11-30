"""
Elixir Repository Indexer.

Walks an Elixir repository and indexes all modules and functions.
"""

import argparse
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cicada.languages.elixir.dependency_analyzer import (
    calculate_function_end_line,
    extract_function_dependencies,
    extract_module_dependencies,
)
from cicada.languages.elixir.parser import ElixirParser
from cicada.parsing.base_indexer import BaseIndexer
from cicada.tier import read_keyword_extraction_config
from cicada.utils import (
    load_index,
    merge_indexes_incremental,
    save_index,
    validate_index_structure,
)
from cicada.utils.hash_utils import (
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada.version_check import get_version_string, version_mismatch


@dataclass
class ExpansionCallback:
    """Callback data for streaming expansion pipeline."""

    target: dict[str, Any]  # The module/function dict to update
    target_key: str  # "keywords" or "string_keywords"


@dataclass
class ExpansionTask:
    """Represents a deferred keyword expansion task."""

    extracted_keywords: list[str]
    keyword_scores: dict[str, float]
    target: dict[str, Any]  # The module/function dict to update
    target_key: str  # "keywords" or "string_keywords"
    # For tracking extracted keywords (pre-expansion)
    extracted_key: str | None = None


class ElixirIndexer(BaseIndexer):
    """Indexes Elixir repositories to extract module and function information."""

    # ElixirIndexer supports incremental indexing
    supports_incremental: bool = True

    # Progress reporting interval - report every N files processed
    PROGRESS_REPORT_INTERVAL = 10

    # Keyword expansion parameters
    DEFAULT_EXPANSION_TOP_N = 3
    DEFAULT_EXPANSION_THRESHOLD = 0.2

    def __init__(self, verbose: bool = False):
        """Initialize the indexer with a parser."""
        super().__init__(verbose=verbose)
        self.parser = ElixirParser()
        self.excluded_dirs = {
            "deps",
            "_build",
            "node_modules",
            ".git",
            "assets",
            "priv",
        }

    def get_language_name(self) -> str:
        """Return the language identifier for this indexer."""
        return "elixir"

    def get_file_extensions(self) -> list[str]:
        """Return file extensions to index for Elixir."""
        return [".ex", ".exs"]

    def get_excluded_dirs(self) -> list[str]:
        """Return Elixir-specific directories to exclude from indexing."""
        return ["deps", "_build", "node_modules", ".git", "assets", "priv"]

    # ====================================================================================
    # Streaming keyword extraction (overrides base class)
    # ====================================================================================

    def _extract_docstring_keywords(
        self, index: dict, keyword_extractor: Any, pipeline: Any
    ) -> None:
        """Extract keywords from module and function docstrings (Elixir-specific).

        Args:
            index: The Cicada index to update
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion
        """
        if self.verbose:
            print("  Extracting keywords from docstrings...")

        modules = index.get("modules", {})
        total = len(modules)

        for idx, (module_name, module_data) in enumerate(modules.items(), 1):
            if self.verbose and idx % 50 == 0:
                print(
                    f"\r    Processed {idx}/{total} modules (Keywords: {pipeline.stats['submitted']})",
                    end="",
                    flush=True,
                )

            try:
                # Always extract keywords from module name (for discoverability)
                name_text = module_name.replace(".", " ")
                name_result = keyword_extractor.extract_keywords(name_text, top_n=5)
                name_keywords = dict(name_result.get("top_keywords", []))

                # Boost name-derived keywords (1.5x factor)
                for kw in name_keywords:
                    name_keywords[kw] = name_keywords[kw] * 1.5

                # Extract module-level keywords from moduledoc
                doc_keywords = {}
                moduledoc = module_data.get("moduledoc")
                if moduledoc:
                    result = keyword_extractor.extract_keywords(moduledoc, top_n=10)
                    doc_keywords = dict(result.get("top_keywords", []))

                # Merge name and doc keywords (take max score for duplicates)
                keywords = dict(name_keywords)
                for word, score in doc_keywords.items():
                    if word not in keywords or score > keywords[word]:
                        keywords[word] = score

                if keywords:
                    # Store extracted keywords and submit expansion
                    module_data["keywords"] = keywords.copy()
                    callback = ExpansionCallback(target=module_data, target_key="keywords")
                    for cb, res in pipeline.submit(
                        list(keywords.keys()), keywords, callback, top_n=3, threshold=0.2
                    ):
                        self._apply_expansion_result(cb, res)

                # Extract function-level keywords
                for func in module_data.get("functions", []):
                    doc_text = func.get("doc") or func.get("test_description")
                    if doc_text:
                        # Include function name for better keyword extraction
                        func_name = func.get("name", "")
                        text_for_keywords = f"{func_name} {doc_text}"
                        result = keyword_extractor.extract_keywords(text_for_keywords, top_n=10)
                        func_keywords = dict(result.get("top_keywords", []))

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
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from string literals in Elixir files (Elixir-specific).

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
            keyword_extractor: Keyword extractor instance
            pipeline: Streaming expansion pipeline for parallel expansion

        Returns:
            Number of modules processed
        """
        from cicada.languages.elixir.extractors import StringExtractor, extract_modules

        if self.verbose:
            print("  Extracting string keywords...")

        string_extractor = StringExtractor(min_length=3)
        processed = 0

        for module_name, module_data in index.get("modules", {}).items():
            file_path_str = module_data.get("file")
            if not file_path_str:
                continue

            full_path = repo_path / file_path_str
            if not full_path.exists():
                continue

            try:
                # Re-parse file to extract strings (need AST access)
                import tree_sitter_elixir as ts_elixir
                from tree_sitter import Language, Parser

                with open(full_path, "rb") as f:
                    source_code = f.read()

                ts_parser = Parser(Language(ts_elixir.language()))  # type: ignore[deprecated]
                tree = ts_parser.parse(source_code)

                parsed_modules = extract_modules(tree.root_node, source_code)
                if not parsed_modules:
                    continue

                for parsed_mod in parsed_modules:
                    if parsed_mod["module"] != module_name:
                        continue

                    do_block = parsed_mod.get("do_block")
                    if not do_block:
                        continue

                    # Extract strings from module
                    extracted_strings = string_extractor.extract_from_module(do_block, source_code)

                    # Group strings by function
                    function_strings_map = {}
                    module_level_strings = []

                    for string_info in extracted_strings:
                        func_name = string_info.get("function")
                        if func_name:
                            if func_name not in function_strings_map:
                                function_strings_map[func_name] = []
                            function_strings_map[func_name].append(string_info)
                        else:
                            module_level_strings.append(string_info)

                    # Extract keywords from module-level strings
                    if module_level_strings:
                        combined_text = " ".join([s["string"] for s in module_level_strings])
                        result = keyword_extractor.extract_keywords(combined_text, top_n=10)
                        keywords = {
                            kw: score * 1.3  # 1.3x boost for strings
                            for kw, score in result.get("top_keywords", [])
                        }

                        if keywords:
                            module_data["string_sources"] = module_level_strings
                            module_data["string_keywords"] = keywords.copy()
                            callback = ExpansionCallback(
                                target=module_data, target_key="string_keywords"
                            )
                            for cb, res in pipeline.submit(
                                list(keywords.keys()), keywords, callback, top_n=3, threshold=0.2
                            ):
                                self._apply_expansion_result(cb, res)

                    # Extract keywords from function strings
                    for func in module_data.get("functions", []):
                        func_name = func.get("name")
                        if func_name not in function_strings_map:
                            continue

                        func_string_list = function_strings_map[func_name]
                        combined_text = " ".join([s["string"] for s in func_string_list])

                        result = keyword_extractor.extract_keywords(combined_text, top_n=10)
                        keywords = {
                            kw: score * 1.3  # 1.3x boost for strings
                            for kw, score in result.get("top_keywords", [])
                        }

                        if keywords:
                            func["string_sources"] = func_string_list
                            func["string_keywords"] = keywords.copy()
                            callback = ExpansionCallback(target=func, target_key="string_keywords")
                            for cb, res in pipeline.submit(
                                list(keywords.keys()), keywords, callback, top_n=3, threshold=0.2
                            ):
                                self._apply_expansion_result(cb, res)

                    processed += 1
                    break  # Found the module, no need to check other parsed modules

            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Failed to extract strings from {file_path_str}: {e}")

        return processed

    def _extract_comment_keywords(
        self,
        index: dict,
        repo_path: Path,
        keyword_extractor: Any,
        pipeline: Any,
    ) -> int:
        """Extract keywords from inline comments (Elixir-specific)."""
        from cicada.languages.elixir.extractors import CommentExtractor, extract_modules

        if self.verbose:
            print("  Extracting comment keywords...")

        comment_extractor = CommentExtractor(min_length=3, merge_consecutive=True)
        processed = 0

        for module_name, module_data in index.get("modules", {}).items():
            file_path_str = module_data.get("file")
            if not file_path_str:
                continue

            full_path = repo_path / file_path_str
            if not full_path.exists():
                continue

            try:
                import tree_sitter_elixir as ts_elixir
                from tree_sitter import Language, Parser

                with open(full_path, "rb") as f:
                    source_code = f.read()

                ts_parser = Parser(Language(ts_elixir.language()))  # type: ignore[deprecated]
                tree = ts_parser.parse(source_code)

                parsed_modules = extract_modules(tree.root_node, source_code)
                if not parsed_modules:
                    continue

                for parsed_mod in parsed_modules:
                    if parsed_mod["module"] != module_name:
                        continue

                    do_block = parsed_mod.get("do_block")
                    if not do_block:
                        continue

                    # Extract comments and associate with functions
                    comments_by_function = comment_extractor.extract_from_module(
                        do_block, source_code, module_data.get("functions", [])
                    )

                    for func in module_data.get("functions", []):
                        func_name = func.get("name")
                        if not func_name or func_name not in comments_by_function:
                            continue

                        func_comments = comments_by_function[func_name]
                        if not func_comments:
                            continue

                        combined_text = " ".join(c["comment"] for c in func_comments)
                        if not combined_text.strip():
                            func["comment_sources"] = func_comments
                            continue

                        result = keyword_extractor.extract_keywords(combined_text, top_n=10)
                        keywords = {
                            kw: score * 1.2  # 1.2x boost for comments
                            for kw, score in result.get("top_keywords", [])
                        }

                        if keywords:
                            func["comment_sources"] = func_comments
                            func["extracted_comment_keywords"] = keywords.copy()
                            callback = ExpansionCallback(target=func, target_key="comment_keywords")
                            for cb, res in pipeline.submit(
                                list(keywords.keys()),
                                keywords,
                                callback,
                                top_n=3,
                                threshold=0.2,
                            ):
                                self._apply_expansion_result(cb, res)
                        else:
                            func["comment_sources"] = func_comments

                    processed += 1
                    break  # Found module, stop searching parsed modules

            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Failed to extract comments from {file_path_str}: {e}")

        return processed

    # ====================================================================================
    # Legacy methods
    # ====================================================================================

    def _extract_dependencies(self, module_data: dict, functions: list) -> tuple[dict, list]:
        """
        Extract module and function level dependencies.

        Args:
            module_data: Parsed module data containing calls, aliases, etc.
            functions: List of function data dictionaries

        Returns:
            Tuple of (module_dependencies, modified_functions_list)
        """
        # Extract module-level dependencies
        module_dependencies = extract_module_dependencies(module_data)

        # Extract function-level dependencies
        all_calls = module_data.get("calls", [])
        for i, func in enumerate(functions):
            # Calculate function end line
            next_func_line = functions[i + 1]["line"] if i + 1 < len(functions) else None
            func_end_line = calculate_function_end_line(func, next_func_line)

            # Extract dependencies for this function
            func_deps = extract_function_dependencies(module_data, func, all_calls, func_end_line)
            func["dependencies"] = func_deps

        return module_dependencies, functions

    def _extract_name_keywords(
        self,
        identifier: str,
        keyword_extractor,
        keyword_expander,
        boost_factor: float = 1.5,
    ) -> dict[str, float]:
        """
        Extract keywords from an identifier (module name, function name, etc.).

        This ensures all modules/functions are discoverable by their names,
        even without documentation.

        Args:
            identifier: The identifier to extract keywords from (e.g., "ThenvoiCom.LlmClientTest")
            keyword_extractor: Keyword extractor instance (KeyBERT or Regular)
            keyword_expander: Keyword expander instance
            boost_factor: Multiplier for name-derived keywords (default: 1.5x)

        Returns:
            Dictionary mapping keywords to scores
        """
        if not identifier or not keyword_extractor:
            return {}

        # Import the split_identifier utility
        from cicada.utils import split_identifier

        # Split the identifier into words (handles camelCase, PascalCase, snake_case, dots)
        # First split by dots (module separators)
        parts = identifier.split(".")
        all_words = []
        for part in parts:
            words = split_identifier(part, lowercase=True)
            all_words.extend(words)

        # Filter out very short words (< 3 chars) to avoid noise
        meaningful_words = [w for w in all_words if len(w) >= 3]

        if not meaningful_words:
            return {}

        # Create a synthetic "text" from the words for keyword extraction
        synthetic_text = " ".join(meaningful_words)

        try:
            # Extract keywords using the same pipeline as documentation
            extraction_result = keyword_extractor.extract_keywords(synthetic_text, top_n=10)
            keyword_scores = {
                kw.lower(): score * boost_factor for kw, score in extraction_result["top_keywords"]
            }

            # Expand keywords if expander is available
            if keyword_expander and keyword_scores:
                extracted_keywords = list(keyword_scores.keys())
                expansion_result = keyword_expander.expand_keywords(
                    extracted_keywords,
                    top_n=self.DEFAULT_EXPANSION_TOP_N,
                    threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                    keyword_scores=keyword_scores,
                )

                # Convert expansion result to dict
                expanded_keywords = {}
                if isinstance(expansion_result, dict):
                    for item in expansion_result["words"]:
                        word = item["word"]
                        score = item["score"]
                        if word not in expanded_keywords or score > expanded_keywords[word]:
                            expanded_keywords[word] = score
                    return expanded_keywords

            return keyword_scores

        except Exception as e:
            if self.verbose:
                print(
                    f"Warning: Name keyword extraction failed for '{identifier}': {e}",
                    file=sys.stderr,
                )
            return {}

    def _handle_interrupt(self, _signum, _frame):
        """Handle interrupt signals (Ctrl-C, SIGTERM) gracefully."""
        print("\n\n⚠️  Interrupt received. Finishing current file and saving progress...")
        print("   Press Ctrl-C again to force quit (may lose progress)\n")
        self._interrupted = True
        # Restore default handler so second Ctrl-C will kill immediately
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

    def _check_and_report_interruption(self, files_processed: int, total_files: int) -> bool:
        """
        Check if interrupted and report status.

        Args:
            files_processed: Number of files processed so far
            total_files: Total number of files to process

        Returns:
            True if interrupted, False otherwise
        """
        if self._interrupted:
            print(f"\n⚠️  Interrupted after processing {files_processed}/{total_files} files")
            print("   Saving partial progress...")
            return True
        return False

    def _integrate_cochange_data(self, all_modules: dict, cochange_data: dict, repo_path: Path):
        """
        Integrate co-change data into module and function structures.

        Args:
            all_modules: Dictionary of all indexed modules
            cochange_data: Co-change analysis results from CoChangeAnalyzer
            repo_path: Path to repository root
        """
        file_to_module = self._build_file_to_module_mapping(all_modules, repo_path)
        self._integrate_file_cochanges(
            all_modules, cochange_data["file_pairs"], file_to_module, repo_path
        )
        self._integrate_function_cochanges(all_modules, cochange_data["function_pairs"])

    def _build_file_to_module_mapping(self, all_modules: dict, repo_path: Path) -> dict[str, str]:
        """Build reverse mapping from file path to module name.

        Args:
            all_modules: Dictionary of all indexed modules
            repo_path: Path to repository root

        Returns:
            Dictionary mapping file paths to module names
        """
        file_to_module = {}
        for module_name, module_info in all_modules.items():
            if "file" in module_info:
                file_path = self._normalize_file_path(module_info["file"], repo_path)
                file_to_module[file_path] = module_name
        return file_to_module

    def _normalize_file_path(self, file_path: str, repo_path: Path) -> str:
        """Normalize file path to be relative to repo root.

        Args:
            file_path: Absolute or relative file path
            repo_path: Path to repository root

        Returns:
            File path relative to repo root
        """
        if file_path.startswith(str(repo_path)):
            return str(Path(file_path).relative_to(repo_path))
        return file_path

    def _integrate_file_cochanges(
        self,
        all_modules: dict,
        file_pairs: dict[tuple[str, str], int],
        file_to_module: dict[str, str],
        repo_path: Path,
    ):
        """Integrate file-level co-changes into modules.

        Args:
            all_modules: Dictionary of all indexed modules
            file_pairs: Dictionary of file pair co-change counts
            file_to_module: Mapping from file paths to module names
            repo_path: Path to repository root
        """
        from cicada.git.cochange_analyzer import CoChangeAnalyzer

        for _module_name, module_info in all_modules.items():
            module_file = self._normalize_file_path(module_info.get("file", ""), repo_path)

            # Find all files that co-changed with this module's file
            cochange_files = [
                {"file": related_file, "count": count}
                for related_file, count in CoChangeAnalyzer.find_cochange_pairs(
                    module_file, file_pairs
                )
            ]

            # Sort by count (descending) and add to module
            cochange_files.sort(key=lambda x: x["count"], reverse=True)
            module_info["cochange_files"] = cochange_files

    def _integrate_function_cochanges(
        self, all_modules: dict, function_pairs: dict[tuple[str, str], int]
    ):
        """Integrate function-level co-changes into functions.

        Args:
            all_modules: Dictionary of all indexed modules
            function_pairs: Dictionary of function pair co-change counts
        """
        for module_name, module_info in all_modules.items():
            if "functions" not in module_info:
                continue

            for func_info in module_info["functions"]:
                func_sig = f"{module_name}.{func_info['name']}/{func_info.get('arity', 0)}"
                cochange_functions = self._extract_related_functions(func_sig, function_pairs)
                func_info["cochange_functions"] = cochange_functions

    def _extract_related_functions(
        self, func_sig: str, function_pairs: dict[tuple[str, str], int]
    ) -> list[dict]:
        """Extract functions that co-changed with the given function signature.

        Args:
            func_sig: Function signature (e.g., "MyApp.Auth.validate_user/2")
            function_pairs: Dictionary of function pair co-change counts

        Returns:
            List of related function dicts with module, function, arity, count keys
        """
        from cicada.git.cochange_analyzer import CoChangeAnalyzer

        cochange_functions = []

        # Find all functions that co-changed with this function
        for related_func, count in CoChangeAnalyzer.find_cochange_pairs(func_sig, function_pairs):
            parsed = self._parse_function_signature(related_func)
            if parsed:
                cochange_functions.append({**parsed, "count": count})

        # Sort by count (descending)
        cochange_functions.sort(key=lambda x: x["count"], reverse=True)
        return cochange_functions

    def _parse_function_signature(self, func_sig: str) -> dict | None:
        """Parse function signature (Module.function/arity) into components.

        Args:
            func_sig: Function signature like "MyApp.Auth.validate_user/2"

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

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
        extract_cochange: bool = True,
    ) -> dict:
        """
        Index an Elixir repository (implements BaseIndexer interface).

        This method provides the standard interface for all indexers.
        For Elixir, it delegates to incremental_index_repository.

        Args:
            repo_path: Path to the repository to index
            output_path: Path where the index.json should be saved
            force: If True, reindex all files regardless of changes
            verbose: If True, print detailed progress information
            config_path: Optional path to config.yaml for custom settings
            extract_cochange: If True, analyze git history for co-change patterns (Elixir-specific)

        Returns:
            Dictionary with indexing results
        """
        # Set verbose flag if specified
        if verbose:
            self.verbose = verbose

        # Use incremental indexing (respects force flag)
        return self.incremental_index_repository(
            repo_path=str(repo_path),
            output_path=str(output_path),
            extract_keywords=True,  # Always extract keywords
            extract_cochange=extract_cochange,
            force_full=force,
        )

    def _index_repository_full(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        extract_string_keywords: bool = False,
        compute_timestamps: bool = False,
        extract_cochange: bool = False,
    ):
        """
        Index an Elixir repository (full indexing, non-incremental).

        This is the legacy method kept for backward compatibility and internal use.

        Args:
            repo_path: Path to the Elixir repository root
            output_path: Path where the index JSON file will be saved
            extract_keywords: If True, extract keywords from documentation using NLP
            extract_string_keywords: If True, extract keywords from string literals in function bodies
            compute_timestamps: If True, compute git history timestamps for functions
            extract_cochange: If True, analyze git history for co-change patterns

        Returns:
            Dictionary containing the index data
        """
        repo_path_obj = Path(repo_path).resolve()

        if not repo_path_obj.exists():
            raise ValueError(f"Repository path does not exist: {repo_path_obj}")

        # Start timing for the pipeline
        self._start_timing()

        if self.verbose:
            print(f"Indexing repository: {repo_path_obj}")
            if extract_keywords:
                # Read and display keyword extraction config
                extraction_method, expansion_method = read_keyword_extraction_config(repo_path_obj)
                from cicada.tier import methods_to_tier

                tier = methods_to_tier(extraction_method, expansion_method)
                print(f"Tier: {tier.upper()}")

        # Set up signal handlers for graceful interruption
        # Only works in main thread - skip if called from background thread
        try:
            signal.signal(signal.SIGINT, self._handle_interrupt)
            signal.signal(signal.SIGTERM, self._handle_interrupt)
        except ValueError:
            # Running in background thread - signal handlers unavailable
            pass
        self._interrupted = False

        # Initialize keyword extractor and expander if requested
        keyword_extractor = None
        keyword_expander = None
        if extract_keywords or extract_string_keywords:
            try:
                # Read keyword extraction config from config.yaml
                extraction_method, expansion_method = read_keyword_extraction_config(repo_path_obj)

                # Initialize extraction method
                if extraction_method == "bert":
                    from cicada.extractors.keybert import KeyBERTExtractor

                    keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                else:
                    # Use regular (TF-based) extractor as default
                    from cicada.extractors.keyword import RegularKeywordExtractor

                    keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)

                # Initialize expansion method (parallel for better performance)
                from cicada.parallel_expander import ParallelKeywordExpander

                keyword_expander = ParallelKeywordExpander(
                    expansion_type=expansion_method, verbose=self.verbose
                )

            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not initialize keyword extractor/expander: {e}")
                    print("Continuing without keyword extraction...")
                extract_keywords = False
                extract_string_keywords = False

        # Find all Elixir files
        elixir_files = self._find_elixir_files(repo_path_obj)
        total_files = len(elixir_files)

        if self.verbose:
            print(f"Found {total_files} Elixir files")

        # Parse all files
        all_modules = {}
        total_functions = 0
        files_processed = 0

        for file_path in elixir_files:
            try:
                modules = self.parser.parse_file(str(file_path))

                if modules:
                    for module_data in modules:
                        module_name = module_data["module"]
                        functions = module_data["functions"]

                        # Calculate stats
                        public_count = sum(1 for f in functions if f["type"] == "def")
                        private_count = sum(1 for f in functions if f["type"] == "defp")

                        # Extract dependencies
                        module_deps, func_level_deps = self._extract_dependencies(
                            module_data, functions
                        )

                        # Build module info (basic structure - enrichment happens in pipeline)
                        module_info = {
                            "file": str(file_path.relative_to(repo_path_obj)),
                            "line": module_data.get("line", 1),
                            "functions": functions,
                            "dependencies": module_deps,
                            "function_dependencies": func_level_deps,
                            "public_count": public_count,
                            "private_count": private_count,
                            # Module usage tracking fields (for what_calls_it)
                            "aliases": module_data.get("aliases", {}),
                            "imports": module_data.get("imports", []),
                            "requires": module_data.get("requires", []),
                            "uses": module_data.get("uses", []),
                            "behaviours": module_data.get("behaviours", []),
                            "value_mentions": module_data.get("value_mentions", []),
                            "calls": module_data.get("calls", []),
                        }

                        # Add moduledoc if present
                        if module_data.get("moduledoc"):
                            module_info["moduledoc"] = module_data["moduledoc"]

                        # Add to all modules
                        all_modules[module_name] = module_info
                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting
                if self.verbose and files_processed % self.PROGRESS_REPORT_INTERVAL == 0:
                    print(
                        f"\r  Processed {files_processed}/{total_files} files...",
                        end="",
                        flush=True,
                    )

                # Check for interruption after each file
                if self._check_and_report_interruption(files_processed, total_files):
                    break

            except Exception as e:
                if self.verbose:
                    print(f"  Skipping {file_path}: {e}")
                # Check for interruption even after error
                if self._check_and_report_interruption(files_processed, total_files):
                    break
                continue

        if self.verbose and files_processed > 0:
            print()  # New line after progress reporting

        self._log_timing("File parsing")

        # Build basic index from parsed files
        index = {
            "modules": all_modules,
            "metadata": {
                "indexed_at": datetime.now().isoformat(),
                "total_modules": len(all_modules),
                "total_functions": total_functions,
                "repo_path": str(repo_path_obj),
                "cicada_version": get_version_string(),
            },
        }

        # Run universal enrichment pipeline (keywords, timestamps, co-change, co-occurrence)
        self._run_enrichment_pipeline(
            index,
            repo_path_obj,
            extract_keywords=extract_keywords,
            extract_string_keywords=extract_string_keywords,
            extract_comment_keywords=extract_keywords,
            compute_timestamps=compute_timestamps,
            extract_cochange=extract_cochange,
            keyword_extractor=keyword_extractor,
            keyword_expander=keyword_expander,
        )

        # Save to file
        output_path_obj = Path(output_path)

        # Check if .cicada directory exists (first run detection)
        save_index(index, output_path_obj, create_dirs=True)

        # Compute and save hashes for all PROCESSED files for future incremental updates
        if self.verbose:
            print("Computing file hashes for incremental updates...")
        # Only hash files that were actually processed
        processed_files = [
            str(f.relative_to(repo_path_obj)) for f in elixir_files[:files_processed]
        ]
        file_hashes = compute_hashes_for_files(processed_files, str(repo_path_obj))
        # Save hashes to centralized storage directory
        from cicada.utils import get_storage_dir

        storage_dir = get_storage_dir(repo_path_obj)
        save_file_hashes(str(storage_dir), file_hashes)

        # Report completion status
        if self.verbose:
            if self._interrupted:
                print("\n✓ Partial index saved!")
                print(
                    f"  Processed: {files_processed}/{total_files} files ({files_processed/total_files*100:.1f}%)"
                )
                print(f"  Modules: {len(all_modules)}")
                print(f"  Functions: {total_functions}")
                print(
                    f"\n💡 Run the command again to continue indexing remaining {total_files - files_processed} file(s)"
                )
            else:
                print("\nIndexing complete!")
                print(f"  Modules: {len(all_modules)}")
                print(f"  Functions: {total_functions}")

            print(f"\nIndex saved to: {output_path_obj}")
            print(f"Hashes saved to: {output_path_obj.parent}/hashes.json")

        return index

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
    ):
        """
        Incrementally index an Elixir repository using file hashing.

        Only processes files that have been added, modified, or deleted since
        the last indexing run. Falls back to full indexing if no previous
        index or hashes exist.

        Args:
            repo_path: Path to the Elixir repository root
            output_path: Path where the index JSON file will be saved
            extract_keywords: If True, extract keywords from documentation using NLP
            extract_string_keywords: If True, extract keywords from string literals
            compute_timestamps: If True, compute git history timestamps for functions (default: True)
            extract_cochange: If True, analyze git history for co-change patterns (enabled by default)
            force_full: If True, ignore existing hashes and do full reindex
            verbose: If True, print detailed progress information (default: True)

        Returns:
            Dictionary containing the index data
        """
        # Update verbosity setting from parameter
        self.verbose = verbose

        repo_path_obj = Path(repo_path).resolve()
        output_path_obj = Path(output_path)
        # Use centralized storage directory for hashes
        from cicada.utils import get_storage_dir

        storage_dir = get_storage_dir(repo_path_obj)

        if not repo_path_obj.exists():
            raise ValueError(f"Repository path does not exist: {repo_path_obj}")

        # Load existing index and hashes
        existing_index = load_index(output_path_obj) if not force_full else None
        existing_hashes = load_file_hashes(str(storage_dir)) if not force_full else {}

        # Validate existing index structure if loaded
        if existing_index:
            is_valid, error = validate_index_structure(existing_index)
            if not is_valid:
                if self.verbose:
                    print(
                        f"Warning: Existing index is corrupted ({error}). Performing full reindex..."
                    )
                existing_index = None

        # Check for version mismatch - warn but continue with incremental indexing
        if existing_index:
            stored_version = existing_index.get("metadata", {}).get("cicada_version")
            current_version = get_version_string()
            if version_mismatch(stored_version, current_version) and self.verbose:
                print(
                    f"WARNING: Cicada version mismatch. "
                    f"Index was built with {stored_version}, current version is {current_version}."
                )

        # If no existing data, do full index
        if not existing_index or not existing_hashes:
            if self.verbose:
                print("No existing index or hashes found. Performing full index...")
            return self._index_repository_full(
                str(repo_path_obj),
                str(output_path_obj),
                extract_keywords,
                extract_string_keywords,
                compute_timestamps,
                extract_cochange,
            )

        if self.verbose:
            # Read and display keyword extraction config
            extraction_method, expansion_method = read_keyword_extraction_config(repo_path_obj)
            print(f"Performing incremental index of: {repo_path_obj}")
            from cicada.tier import methods_to_tier

            tier = methods_to_tier(extraction_method, expansion_method)
            print(f"Tier: {tier.upper()}")

        # Set up signal handlers for graceful interruption
        # Only works in main thread - skip if called from background thread
        try:
            signal.signal(signal.SIGINT, self._handle_interrupt)
            signal.signal(signal.SIGTERM, self._handle_interrupt)
        except ValueError:
            # Running in background thread - signal handlers unavailable
            pass
        self._interrupted = False

        # Find all current Elixir files
        elixir_files = self._find_elixir_files(repo_path_obj)
        # Convert to relative paths
        relative_files = [str(f.relative_to(repo_path_obj)) for f in elixir_files]

        # Detect file changes
        if self.verbose:
            print("Detecting file changes...")
        new_files, modified_files, deleted_files = detect_file_changes(
            relative_files, existing_hashes, str(repo_path_obj)
        )

        # Calculate what needs to be processed
        files_to_process = new_files + modified_files
        total_changes = len(new_files) + len(modified_files) + len(deleted_files)

        if total_changes == 0:
            print("No changes detected. Index is up to date.")
            return existing_index

        if self.verbose:
            print("Changes detected:")
            print(f"  New files: {len(new_files)}")
            print(f"  Modified files: {len(modified_files)}")
            print(f"  Deleted files: {len(deleted_files)}")

        if files_to_process:
            print(f"\nProcessing {len(files_to_process)} changed file(s)...")

        # Initialize keyword extractor and expander if requested
        keyword_extractor = None
        keyword_expander = None
        if extract_keywords:
            try:
                # Read keyword extraction config from config.yaml
                extraction_method, expansion_method = read_keyword_extraction_config(repo_path_obj)

                # Initialize extraction method
                if extraction_method == "bert":
                    from cicada.extractors.keybert import KeyBERTExtractor

                    keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                else:
                    # Use regular (TF-based) extractor as default
                    from cicada.extractors.keyword import RegularKeywordExtractor

                    keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)

                # Initialize expansion method (parallel for better performance)
                from cicada.parallel_expander import ParallelKeywordExpander

                keyword_expander = ParallelKeywordExpander(
                    expansion_type=expansion_method, verbose=self.verbose
                )

            except Exception as e:
                print(f"Warning: Could not initialize keyword extractor/expander: {e}")
                print("Continuing without keyword extraction...")
                extract_keywords = False
                extract_string_keywords = False

        # Process changed files (basic parsing only - enrichment runs separately)
        all_modules = {}
        total_functions = 0
        files_processed = 0

        for relative_file in files_to_process:
            file_path = repo_path_obj / relative_file
            try:
                modules = self.parser.parse_file(str(file_path))

                if modules:
                    for module_data in modules:
                        module_name = module_data["module"]
                        functions = module_data["functions"]

                        # Calculate stats
                        public_count = sum(1 for f in functions if f["type"] == "def")
                        private_count = sum(1 for f in functions if f["type"] == "defp")

                        # Extract dependencies
                        module_deps, func_level_deps = self._extract_dependencies(
                            module_data, functions
                        )

                        # Build module info (basic structure - enrichment happens in pipeline)
                        module_info = {
                            "file": relative_file,
                            "line": module_data.get("line", 1),
                            "functions": functions,
                            "dependencies": module_deps,
                            "function_dependencies": func_level_deps,
                            "public_count": public_count,
                            "private_count": private_count,
                            # Module usage tracking fields (for what_calls_it)
                            "aliases": module_data.get("aliases", {}),
                            "imports": module_data.get("imports", []),
                            "requires": module_data.get("requires", []),
                            "uses": module_data.get("uses", []),
                            "behaviours": module_data.get("behaviours", []),
                            "value_mentions": module_data.get("value_mentions", []),
                            "calls": module_data.get("calls", []),
                        }

                        # Add moduledoc if present
                        if module_data.get("moduledoc"):
                            module_info["moduledoc"] = module_data["moduledoc"]

                        all_modules[module_name] = module_info
                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting
                if self.verbose and files_processed % self.PROGRESS_REPORT_INTERVAL == 0:
                    print(
                        f"\r  Processed {files_processed}/{len(files_to_process)} files...",
                        end="",
                        flush=True,
                    )

                # Check for interruption after each file
                if self._check_and_report_interruption(files_processed, len(files_to_process)):
                    break

            except Exception as e:
                print(f"  Skipping {file_path}: {e}")
                # Check for interruption even after error
                if self._check_and_report_interruption(files_processed, len(files_to_process)):
                    break
                continue

        if self.verbose and files_processed > 0:
            print()  # New line after progress reporting

        # Build index for changed files
        new_index = {
            "modules": all_modules,
            "metadata": {
                "indexed_at": datetime.now().isoformat(),
                "repo_path": str(repo_path_obj),
                "cicada_version": get_version_string(),
            },
        }

        # Run enrichment pipeline on new modules (keywords, timestamps, co-change)
        # This uses the streaming parallel expansion for keywords
        if all_modules:
            self._run_enrichment_pipeline(
                new_index,
                repo_path_obj,
                extract_keywords=extract_keywords,
                extract_string_keywords=extract_string_keywords,
                extract_comment_keywords=extract_keywords,
                compute_timestamps=compute_timestamps,
                extract_cochange=extract_cochange,
                keyword_extractor=keyword_extractor,
                keyword_expander=keyword_expander,
            )

        # Merge enriched new_index with existing index
        if self.verbose:
            print("Merging with existing index...")
        merged_index = merge_indexes_incremental(existing_index, new_index, deleted_files)

        # Update hashes for all current files
        if self.verbose:
            print("Updating file hashes...")
        updated_hashes = dict(existing_hashes)

        # Compute hashes only for files that were actually processed
        actually_processed = files_to_process[:files_processed]
        new_hashes = compute_hashes_for_files(actually_processed, str(repo_path_obj))
        updated_hashes.update(new_hashes)

        # Remove hashes for deleted files
        for deleted_file in deleted_files:
            updated_hashes.pop(deleted_file, None)

        # Save index and hashes
        save_index(merged_index, output_path_obj, create_dirs=True)
        save_file_hashes(str(storage_dir), updated_hashes)

        # Report completion status
        if self._interrupted:
            remaining = len(files_to_process) - files_processed
            print("\n✓ Partial index saved!")
            print(f"  Processed: {files_processed}/{len(files_to_process)} changed file(s)")
            print(f"  Total modules: {merged_index['metadata']['total_modules']}")
            print(f"  Total functions: {merged_index['metadata']['total_functions']}")
            print(f"  Files deleted: {len(deleted_files)}")
            print(
                f"\n💡 Run the command again to continue indexing remaining {remaining} changed file(s)"
            )
        else:
            print("\nIncremental indexing complete!")
            print(f"  Total modules: {merged_index['metadata']['total_modules']}")
            print(f"  Total functions: {merged_index['metadata']['total_functions']}")
            print(f"  Files processed: {files_processed}")
            print(f"  Files deleted: {len(deleted_files)}")

        return merged_index

    def _find_elixir_files(self, repo_path: Path) -> list:
        """Find all Elixir source files in the repository."""
        elixir_files = []

        for root, dirs, files in os.walk(repo_path):
            # Remove excluded directories from the search
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            # Find .ex and .exs files
            for file in files:
                if file.endswith((".ex", ".exs")):
                    file_path = Path(root) / file
                    elixir_files.append(file_path)

        return sorted(elixir_files)


def main():
    """Main entry point for the indexer CLI."""
    from cicada.version_check import check_for_updates

    # Check for updates (non-blocking, fails silently)
    check_for_updates()

    from cicada.utils.storage import get_index_path

    parser = argparse.ArgumentParser(
        description="Index current Elixir repository to extract modules and functions"
    )
    _ = parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the Elixir repository to index (default: current directory)",
    )
    _ = parser.add_argument(
        "--output",
        default=None,
        help="Output path for the index file. If omitted, uses centralized storage at ~/.cicada/projects/<hash>/index.json",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full reindex, ignoring existing hashes (default: incremental)",
    )

    args = parser.parse_args()

    # Use centralized storage by default
    output_path = args.output or str(get_index_path(args.repo))

    indexer = ElixirIndexer()

    # Use incremental indexing by default (unless --full flag is set)
    indexer.incremental_index_repository(
        args.repo,
        output_path,
        extract_keywords=True,
        force_full=args.full,
    )


if __name__ == "__main__":
    main()
