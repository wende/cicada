"""
Elixir Repository Indexer.

Walks an Elixir repository and indexes all modules and functions.
"""

import argparse
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

from cicada.cooccurrence import CooccurrenceAnalyzer
from cicada.elixir.dependency_analyzer import (
    calculate_function_end_line,
    extract_function_dependencies,
    extract_module_dependencies,
)
from cicada.elixir.parser import ElixirParser
from cicada.git import GitHelper
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


class ElixirIndexer:
    """Indexes Elixir repositories to extract module and function information."""

    # Progress reporting interval - report every N files processed
    PROGRESS_REPORT_INTERVAL = 10

    # Keyword expansion parameters
    DEFAULT_EXPANSION_TOP_N = 3
    DEFAULT_EXPANSION_THRESHOLD = 0.2

    def __init__(self, verbose: bool = False):
        """Initialize the indexer with a parser."""
        self.parser = ElixirParser()
        self.verbose = verbose
        self.excluded_dirs = {
            "deps",
            "_build",
            "node_modules",
            ".git",
            "assets",
            "priv",
        }
        self._interrupted = False

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
                    return_scores=True,
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
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        extract_string_keywords: bool = False,
        compute_timestamps: bool = False,
        extract_cochange: bool = False,
    ):
        """
        Index an Elixir repository.

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
                    from cicada.elixir.extractors.keybert import KeyBERTExtractor

                    keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                else:
                    # Use regular (TF-based) extractor as default
                    from cicada.elixir.extractors.keyword import RegularKeywordExtractor

                    keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)

                # Initialize expansion method
                from cicada.keyword_expander import KeywordExpander

                keyword_expander = KeywordExpander(
                    expansion_type=expansion_method, verbose=self.verbose
                )

            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not initialize keyword extractor/expander: {e}")
                    print("Continuing without keyword extraction...")
                extract_keywords = False
                extract_string_keywords = False

        # Initialize string extractor if requested
        string_extractor = None
        if extract_string_keywords:
            try:
                from cicada.elixir.extractors import StringExtractor

                string_extractor = StringExtractor(min_length=3)
                if self.verbose:
                    print("String keyword extraction enabled")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not initialize string extractor: {e}")
                    print("Continuing without string keyword extraction...")
                extract_string_keywords = False

        # Initialize git helper if timestamps are requested
        git_helper = None
        if compute_timestamps:
            try:
                git_helper = GitHelper(str(repo_path_obj))
                if self.verbose:
                    print("Git history tracking enabled - computing function timestamps")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not initialize git helper: {e}")
                    print("Continuing without timestamp computation...")
                compute_timestamps = False

        # Find all Elixir files
        elixir_files = self._find_elixir_files(repo_path_obj)
        total_files = len(elixir_files)

        if self.verbose:
            print(f"Found {total_files} Elixir files")

        # Parse all files
        all_modules = {}
        total_functions = 0
        files_processed = 0
        keyword_extraction_failures = 0
        timestamps_computed = 0

        # Multi-line progress tracking (2 lines: files + timestamps)
        progress_lines_active = False

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

                        # Extract and expand keywords if enabled
                        module_keywords = None
                        module_extracted_keywords = None
                        if keyword_extractor and module_data.get("moduledoc"):
                            try:
                                # Step 1: Extract keywords with scores
                                extraction_result = keyword_extractor.extract_keywords(
                                    module_data["moduledoc"], top_n=10
                                )
                                extracted_keywords = [
                                    kw for kw, _ in extraction_result["top_keywords"]
                                ]
                                keyword_scores = {
                                    kw.lower(): score
                                    for kw, score in extraction_result["top_keywords"]
                                }

                                # Store extracted keywords (pre-expansion) for co-occurrence tracking
                                module_extracted_keywords = keyword_scores

                                # Step 2: Expand keywords with scores
                                if keyword_expander and extracted_keywords:
                                    expansion_result = keyword_expander.expand_keywords(
                                        extracted_keywords,
                                        top_n=self.DEFAULT_EXPANSION_TOP_N,
                                        threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                                        return_scores=True,
                                        keyword_scores=keyword_scores,
                                    )
                                    # Convert to dict: word -> max_score
                                    module_keywords = {}
                                    # When return_scores=True, expansion_result is a dict
                                    if not isinstance(expansion_result, dict):
                                        raise TypeError(
                                            "Expected dict from expand_keywords with return_scores=True"
                                        )
                                    for item in expansion_result["words"]:
                                        word = item["word"]
                                        score = item["score"]
                                        if (
                                            word not in module_keywords
                                            or score > module_keywords[word]
                                        ):
                                            module_keywords[word] = score
                                else:
                                    module_keywords = keyword_scores
                            except Exception as e:
                                keyword_extraction_failures += 1
                                if self.verbose:
                                    print(
                                        f"Warning: Keyword extraction failed for module {module_name}: {e}",
                                        file=sys.stderr,
                                    )

                        # Enrich function metadata (keywords and timestamps)
                        for func in functions:
                            func_name = func.get("name", "")

                            # Extract and expand keywords from function docs or test descriptions
                            doc_text = func.get("doc") or func.get("test_description")
                            if keyword_extractor and doc_text:
                                try:
                                    # Include function name in text for keyword extraction
                                    # This ensures the function name identifier gets 10x weight
                                    text_for_keywords = f"{func_name} {doc_text}"
                                    # Step 1: Extract keywords with scores
                                    extraction_result = keyword_extractor.extract_keywords(
                                        text_for_keywords, top_n=10
                                    )
                                    extracted_keywords = [
                                        kw for kw, _ in extraction_result["top_keywords"]
                                    ]
                                    keyword_scores = {
                                        kw.lower(): score
                                        for kw, score in extraction_result["top_keywords"]
                                    }

                                    # Store extracted keywords (pre-expansion) for co-occurrence tracking
                                    func["extracted_keywords"] = keyword_scores

                                    # Step 2: Expand keywords with scores
                                    if keyword_expander and extracted_keywords:
                                        expansion_result = keyword_expander.expand_keywords(
                                            extracted_keywords,
                                            top_n=self.DEFAULT_EXPANSION_TOP_N,
                                            threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                                            return_scores=True,
                                            keyword_scores=keyword_scores,
                                        )
                                        # Convert to dict: word -> max_score
                                        func_keywords = {}
                                        # When return_scores=True, expansion_result is a dict
                                        if not isinstance(expansion_result, dict):
                                            raise TypeError(
                                                "Expected dict from expand_keywords with return_scores=True"
                                            )
                                        for item in expansion_result["words"]:
                                            word = item["word"]
                                            score = item["score"]
                                            if (
                                                word not in func_keywords
                                                or score > func_keywords[word]
                                            ):
                                                func_keywords[word] = score
                                    else:
                                        func_keywords = keyword_scores

                                    if func_keywords:
                                        func["keywords"] = func_keywords
                                except Exception as e:
                                    keyword_extraction_failures += 1
                                    if self.verbose:
                                        print(
                                            f"Warning: Keyword extraction failed for {module_name}.{func_name}: {e}",
                                            file=sys.stderr,
                                        )

                        # Compute git history timestamps if enabled (BATCHED by file for speed)
                        if git_helper and functions:
                            timestamps_computed += len(functions)
                            if self.verbose and timestamps_computed % 50 == 0:
                                # Update timestamp progress on second line (current cursor position)
                                print(
                                    f"\r\033[K  Computing timestamps: {timestamps_computed} functions...",
                                    end="",
                                    flush=True,
                                )

                            try:
                                # Batch query all functions in this file at once (10x faster)
                                evolutions = git_helper.get_functions_evolution_batch(
                                    file_path=str(file_path.relative_to(repo_path_obj)),
                                    functions=functions,
                                )

                                # Apply evolution data to each function
                                for func in functions:
                                    func_name = func.get("name")
                                    if func_name and func_name in evolutions:
                                        evolution = evolutions[func_name]
                                        if evolution:
                                            func["created_at"] = evolution["created_at"]["date"]
                                            func["last_modified_at"] = evolution["last_modified"][
                                                "date"
                                            ]
                                            func["last_modified_sha"] = evolution["last_modified"][
                                                "sha"
                                            ]
                                            if evolution["last_modified"].get("pr"):
                                                func["last_modified_pr"] = evolution[
                                                    "last_modified"
                                                ]["pr"]
                                            func["modification_count"] = evolution[
                                                "total_modifications"
                                            ]
                            except Exception:
                                # Silently skip timestamp computation errors for this file
                                pass

                        # Extract string keywords if enabled
                        module_string_keywords = None
                        module_extracted_string_keywords = None
                        module_string_sources = []
                        if string_extractor and keyword_extractor:
                            try:
                                # Re-parse file to extract strings (need AST access)
                                import tree_sitter_elixir as ts_elixir
                                from tree_sitter import Language, Parser

                                with open(file_path, "rb") as f:
                                    source_code = f.read()

                                ts_parser = Parser(Language(ts_elixir.language()))
                                tree = ts_parser.parse(source_code)

                                # Find the module node
                                from cicada.elixir.extractors import extract_modules

                                parsed_modules = extract_modules(tree.root_node, source_code)
                                if parsed_modules:
                                    for parsed_mod in parsed_modules:
                                        if parsed_mod["module"] == module_name:
                                            do_block = parsed_mod.get("do_block")
                                            if do_block:
                                                # Extract strings from module
                                                extracted_strings = (
                                                    string_extractor.extract_from_module(
                                                        do_block, source_code
                                                    )
                                                )

                                                # Group strings by function
                                                function_strings_map = {}
                                                module_level_strings = []

                                                for string_info in extracted_strings:
                                                    func_name = string_info.get("function")
                                                    if func_name:
                                                        if func_name not in function_strings_map:
                                                            function_strings_map[func_name] = []
                                                        function_strings_map[func_name].append(
                                                            string_info
                                                        )
                                                    else:
                                                        module_level_strings.append(string_info)

                                                # Extract keywords from module-level strings
                                                if module_level_strings:
                                                    combined_text = " ".join(
                                                        [s["string"] for s in module_level_strings]
                                                    )
                                                    extraction_result = (
                                                        keyword_extractor.extract_keywords(
                                                            combined_text, top_n=10
                                                        )
                                                    )
                                                    extracted_keywords = [
                                                        kw
                                                        for kw, _ in extraction_result[
                                                            "top_keywords"
                                                        ]
                                                    ]
                                                    keyword_scores = {
                                                        kw.lower(): score
                                                        * 1.3  # 1.3x boost for strings
                                                        for kw, score in extraction_result[
                                                            "top_keywords"
                                                        ]
                                                    }

                                                    # Store extracted string keywords (pre-expansion) for co-occurrence
                                                    module_extracted_string_keywords = (
                                                        keyword_scores
                                                    )

                                                    # Expand keywords
                                                    if keyword_expander and extracted_keywords:
                                                        expansion_result = keyword_expander.expand_keywords(
                                                            extracted_keywords,
                                                            top_n=self.DEFAULT_EXPANSION_TOP_N,
                                                            threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                                                            return_scores=True,
                                                            keyword_scores=keyword_scores,
                                                        )
                                                        module_string_keywords = {}
                                                        # Type assertion: expansion_result is dict when return_scores=True
                                                        assert isinstance(expansion_result, dict)
                                                        for item in expansion_result["words"]:
                                                            word = item["word"]
                                                            score = item["score"]
                                                            if (
                                                                word not in module_string_keywords
                                                                or score
                                                                > module_string_keywords[word]
                                                            ):
                                                                module_string_keywords[word] = score
                                                    else:
                                                        module_string_keywords = keyword_scores

                                                    module_string_sources = module_level_strings

                                                # Extract keywords from function strings
                                                for func in functions:
                                                    func_name = func.get("name")
                                                    if func_name in function_strings_map:
                                                        func_string_list = function_strings_map[
                                                            func_name
                                                        ]
                                                        combined_text = " ".join(
                                                            [s["string"] for s in func_string_list]
                                                        )

                                                        # Extract keywords
                                                        extraction_result = (
                                                            keyword_extractor.extract_keywords(
                                                                combined_text, top_n=10
                                                            )
                                                        )
                                                        extracted_keywords = [
                                                            kw
                                                            for kw, _ in extraction_result[
                                                                "top_keywords"
                                                            ]
                                                        ]
                                                        keyword_scores = {
                                                            kw.lower(): score
                                                            * 1.3  # 1.3x boost for strings
                                                            for kw, score in extraction_result[
                                                                "top_keywords"
                                                            ]
                                                        }

                                                        # Store extracted string keywords (pre-expansion) for co-occurrence
                                                        func["extracted_string_keywords"] = (
                                                            keyword_scores
                                                        )

                                                        # Expand keywords
                                                        if keyword_expander and extracted_keywords:
                                                            expansion_result = keyword_expander.expand_keywords(
                                                                extracted_keywords,
                                                                top_n=self.DEFAULT_EXPANSION_TOP_N,
                                                                threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                                                                return_scores=True,
                                                                keyword_scores=keyword_scores,
                                                            )
                                                            func_string_keywords = {}
                                                            # Type assertion: expansion_result is dict when return_scores=True
                                                            assert isinstance(
                                                                expansion_result, dict
                                                            )
                                                            for item in expansion_result["words"]:
                                                                word = item["word"]
                                                                score = item["score"]
                                                                if (
                                                                    word not in func_string_keywords
                                                                    or score
                                                                    > func_string_keywords[word]
                                                                ):
                                                                    func_string_keywords[word] = (
                                                                        score
                                                                    )
                                                        else:
                                                            func_string_keywords = keyword_scores

                                                        # Store in function
                                                        if func_string_keywords:
                                                            func["string_keywords"] = (
                                                                func_string_keywords
                                                            )
                                                        func["string_sources"] = func_string_list

                                            break

                            except Exception as e:
                                keyword_extraction_failures += 1
                                if self.verbose:
                                    print(
                                        f"Warning: String keyword extraction failed for module {module_name}: {e}",
                                        file=sys.stderr,
                                    )

                        # Extract dependencies
                        module_dependencies, functions = self._extract_dependencies(
                            module_data, functions
                        )

                        # Store module info
                        module_info = {
                            "file": str(file_path.relative_to(repo_path_obj)),
                            "line": module_data["line"],
                            "moduledoc": module_data.get("moduledoc"),
                            "functions": functions,
                            "total_functions": len(functions),
                            "public_functions": public_count,
                            "private_functions": private_count,
                            "aliases": module_data.get("aliases", {}),
                            "imports": module_data.get("imports", []),
                            "requires": module_data.get("requires", []),
                            "uses": module_data.get("uses", []),
                            "behaviours": module_data.get("behaviours", []),
                            "value_mentions": module_data.get("value_mentions", []),
                            "calls": module_data.get("calls", []),
                            "dependencies": module_dependencies,
                        }

                        # Add module keywords if extracted
                        if module_keywords:
                            module_info["keywords"] = module_keywords

                        # Add module extracted keywords (pre-expansion) for co-occurrence tracking
                        if module_extracted_keywords:
                            module_info["extracted_keywords"] = module_extracted_keywords

                        # Add module string keywords and sources if extracted
                        if module_string_keywords:
                            module_info["string_keywords"] = module_string_keywords
                        if module_extracted_string_keywords:
                            module_info["extracted_string_keywords"] = (
                                module_extracted_string_keywords
                            )
                        if module_string_sources:
                            module_info["string_sources"] = module_string_sources

                        all_modules[module_name] = module_info

                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting (in-place update with multi-line support)
                if self.verbose and files_processed % self.PROGRESS_REPORT_INTERVAL == 0:
                    # Initialize multi-line display if timestamps are being computed
                    if git_helper and not progress_lines_active:
                        print()  # Reserve line for timestamp progress
                        progress_lines_active = True

                    if progress_lines_active:
                        # Update file progress on first line
                        print(
                            f"\033[1A\r\033[K  Processed {files_processed}/{total_files} files...",
                            end="",
                            flush=True,
                        )
                        print()  # Move back to second line
                    else:
                        # Simple single-line update
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

        # Build final index
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

        # Build co-occurrence matrix if keywords were extracted
        if extract_keywords or extract_string_keywords:
            if self.verbose:
                print("Building keyword co-occurrence matrix...")
            try:
                analyzer = CooccurrenceAnalyzer(index)
                index["cooccurrences"] = analyzer.cooccurrence_matrix
                stats = analyzer.get_statistics()
                if self.verbose:
                    print(f"  ✓ Tracked {stats['total_keywords']} keywords")
                    print(f"  ✓ Found {stats['total_cooccurrences']} co-occurrence relationships")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Failed to build co-occurrence matrix: {e}", file=sys.stderr)

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

            # Report keyword extraction failures if any
            if extract_keywords and keyword_extraction_failures > 0:
                print(
                    f"\n⚠️  Warning: Keyword extraction failed for {keyword_extraction_failures} module(s) or function(s)"
                )
                print("   Some documentation may not be indexed for keyword search.")

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
            extract_cochange: If True, analyze git history for co-change patterns
            force_full: If True, ignore existing hashes and do full reindex

        Returns:
            Dictionary containing the index data
        """
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

        # Check for version mismatch - if cicada version differs, force full reindex
        if existing_index:
            stored_version = existing_index.get("metadata", {}).get("cicada_version")
            current_version = get_version_string()
            if version_mismatch(stored_version, current_version):
                if self.verbose:
                    print(
                        f"Warning: Cicada version mismatch. "
                        f"Index was built with {stored_version}, current version is {current_version}. "
                        f"Performing full reindex..."
                    )
                existing_index = None
                existing_hashes = {}

        # If no existing data, do full index
        if not existing_index or not existing_hashes:
            if self.verbose:
                print("No existing index or hashes found. Performing full index...")
            return self.index_repository(
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
                    from cicada.elixir.extractors.keybert import KeyBERTExtractor

                    keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                else:
                    # Use regular (TF-based) extractor as default
                    from cicada.elixir.extractors.keyword import RegularKeywordExtractor

                    keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)

                # Initialize expansion method
                from cicada.keyword_expander import KeywordExpander

                keyword_expander = KeywordExpander(
                    expansion_type=expansion_method, verbose=self.verbose
                )

            except Exception as e:
                print(f"Warning: Could not initialize keyword extractor/expander: {e}")
                print("Continuing without keyword extraction...")
                extract_keywords = False
                extract_string_keywords = False

        # Note: String keyword extraction not yet implemented for incremental mode
        if extract_string_keywords and self.verbose:
            print("Warning: String keyword extraction not supported in incremental mode")
            extract_string_keywords = False

        # Initialize git helper if timestamp computation is enabled
        git_helper = None
        if compute_timestamps:
            try:
                from cicada.git.helper import GitHelper

                git_helper = GitHelper(str(repo_path_obj))
                if self.verbose:
                    print("Git history tracking enabled - computing function timestamps")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not initialize git helper: {e}")
                    print("Continuing without timestamp computation...")
                compute_timestamps = False

        # Initialize git helper if timestamp computation is enabled
        git_helper = None
        if compute_timestamps:
            try:
                from cicada.git.helper import GitHelper

                git_helper = GitHelper(str(repo_path_obj))
                if self.verbose:
                    print("Git history tracking enabled - computing function timestamps")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not initialize git helper: {e}")
                    print("Continuing without timestamp computation...")
                compute_timestamps = False

        # Process changed files
        all_modules = {}
        total_functions = 0
        files_processed = 0
        keyword_extraction_failures = 0
        timestamps_computed = 0

        # Multi-line progress tracking (2 lines: files + timestamps)
        progress_lines_active = False

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

                        # Extract and expand keywords if enabled
                        module_keywords = None
                        module_extracted_keywords = None  # For co-occurrence tracking
                        if keyword_extractor:
                            try:
                                # Always extract keywords from module name
                                name_keywords = self._extract_name_keywords(
                                    module_name, keyword_extractor, keyword_expander
                                )

                                # Extract keywords from documentation if available
                                doc_keywords = {}
                                doc_extracted_keywords = {}  # Pre-expansion for co-occurrence
                                if module_data.get("moduledoc"):
                                    # Step 1: Extract keywords with scores
                                    extraction_result = keyword_extractor.extract_keywords(
                                        module_data["moduledoc"], top_n=10
                                    )
                                    extracted_keywords = [
                                        kw for kw, _ in extraction_result["top_keywords"]
                                    ]
                                    keyword_scores = {
                                        kw.lower(): score
                                        for kw, score in extraction_result["top_keywords"]
                                    }

                                    # Store pre-expansion doc keywords for co-occurrence tracking
                                    doc_extracted_keywords = keyword_scores.copy()

                                    # Step 2: Expand keywords with scores
                                    if keyword_expander and extracted_keywords:
                                        expansion_result = keyword_expander.expand_keywords(
                                            extracted_keywords,
                                            top_n=self.DEFAULT_EXPANSION_TOP_N,
                                            threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                                            return_scores=True,
                                            keyword_scores=keyword_scores,
                                        )
                                        # Convert to dict: word -> max_score
                                        # When return_scores=True, expansion_result is a dict
                                        if not isinstance(expansion_result, dict):
                                            raise TypeError(
                                                "Expected dict from expand_keywords with return_scores=True"
                                            )
                                        for item in expansion_result["words"]:
                                            word = item["word"]
                                            score = item["score"]
                                            if (
                                                word not in doc_keywords
                                                or score > doc_keywords[word]
                                            ):
                                                doc_keywords[word] = score
                                    else:
                                        doc_keywords = keyword_scores

                                # Merge name and doc keywords (take max score for duplicates)
                                module_keywords = dict(name_keywords)  # Start with name keywords
                                for word, score in doc_keywords.items():
                                    if word not in module_keywords or score > module_keywords[word]:
                                        module_keywords[word] = score

                                # Store extracted keywords (pre-expansion) for co-occurrence tracking
                                module_extracted_keywords = dict(
                                    name_keywords
                                )  # Start with name keywords
                                for word, score in doc_extracted_keywords.items():
                                    if (
                                        word not in module_extracted_keywords
                                        or score > module_extracted_keywords[word]
                                    ):
                                        module_extracted_keywords[word] = score

                            except Exception:
                                keyword_extraction_failures += 1

                        # Extract and expand keywords from function docs
                        if keyword_extractor:
                            for func in functions:
                                if func.get("doc"):
                                    try:
                                        func_name = func.get("name", "")
                                        text_for_keywords = f"{func_name} {func['doc']}"
                                        # Step 1: Extract keywords with scores
                                        extraction_result = keyword_extractor.extract_keywords(
                                            text_for_keywords, top_n=10
                                        )
                                        extracted_keywords = [
                                            kw for kw, _ in extraction_result["top_keywords"]
                                        ]
                                        keyword_scores = {
                                            kw.lower(): score
                                            for kw, score in extraction_result["top_keywords"]
                                        }

                                        # Step 2: Expand keywords with scores
                                        if keyword_expander and extracted_keywords:
                                            expansion_result = keyword_expander.expand_keywords(
                                                extracted_keywords,
                                                top_n=self.DEFAULT_EXPANSION_TOP_N,
                                                threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                                                return_scores=True,
                                                keyword_scores=keyword_scores,
                                            )
                                            # Convert to dict: word -> max_score
                                            func_keywords = {}
                                            # When return_scores=True, expansion_result is a dict
                                            if not isinstance(expansion_result, dict):
                                                raise TypeError(
                                                    "Expected dict from expand_keywords with return_scores=True"
                                                )
                                            for item in expansion_result["words"]:
                                                word = item["word"]
                                                score = item["score"]
                                                if (
                                                    word not in func_keywords
                                                    or score > func_keywords[word]
                                                ):
                                                    func_keywords[word] = score
                                        else:
                                            func_keywords = keyword_scores

                                        if func_keywords:
                                            func["keywords"] = func_keywords
                                    except Exception:
                                        keyword_extraction_failures += 1

                        # Compute git history timestamps if enabled (BATCHED by file for speed)
                        if git_helper and functions:
                            timestamps_computed += len(functions)
                            if self.verbose and timestamps_computed % 50 == 0:
                                # Update timestamp progress on second line (current cursor position)
                                print(
                                    f"\r\033[K  Computing timestamps: {timestamps_computed} functions...",
                                    end="",
                                    flush=True,
                                )

                            try:
                                # Batch query all functions in this file at once (10x faster)
                                evolutions = git_helper.get_functions_evolution_batch(
                                    file_path=relative_file,
                                    functions=functions,
                                )

                                # Apply evolution data to each function
                                for func in functions:
                                    func_name = func.get("name")
                                    if func_name and func_name in evolutions:
                                        evolution = evolutions[func_name]
                                        if evolution:
                                            func["created_at"] = evolution["created_at"]["date"]
                                            func["last_modified_at"] = evolution["last_modified"][
                                                "date"
                                            ]
                                            func["last_modified_sha"] = evolution["last_modified"][
                                                "sha"
                                            ]
                                            if evolution["last_modified"].get("pr"):
                                                func["last_modified_pr"] = evolution[
                                                    "last_modified"
                                                ]["pr"]
                                            func["modification_count"] = evolution[
                                                "total_modifications"
                                            ]
                            except Exception:
                                # Silently skip timestamp computation errors for this file
                                pass

                        # Extract dependencies
                        module_dependencies, functions = self._extract_dependencies(
                            module_data, functions
                        )

                        # Store module info
                        module_info = {
                            "file": relative_file,
                            "line": module_data["line"],
                            "moduledoc": module_data.get("moduledoc"),
                            "functions": functions,
                            "total_functions": len(functions),
                            "public_functions": public_count,
                            "private_functions": private_count,
                            "aliases": module_data.get("aliases", {}),
                            "imports": module_data.get("imports", []),
                            "requires": module_data.get("requires", []),
                            "uses": module_data.get("uses", []),
                            "behaviours": module_data.get("behaviours", []),
                            "value_mentions": module_data.get("value_mentions", []),
                            "calls": module_data.get("calls", []),
                            "dependencies": module_dependencies,
                        }

                        # Add module keywords if extracted
                        if module_keywords:
                            module_info["keywords"] = module_keywords

                        # Add module extracted keywords (pre-expansion) for co-occurrence tracking
                        if module_extracted_keywords:
                            module_info["extracted_keywords"] = module_extracted_keywords

                        all_modules[module_name] = module_info
                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting (in-place update with multi-line support)
                if self.verbose and files_processed % self.PROGRESS_REPORT_INTERVAL == 0:
                    # Initialize multi-line display if timestamps are being computed
                    if git_helper and not progress_lines_active:
                        print()  # Reserve line for timestamp progress
                        progress_lines_active = True

                    if progress_lines_active:
                        # Update file progress on first line
                        print(
                            f"\033[1A\r\033[K  Processed {files_processed}/{len(files_to_process)} files...",
                            end="",
                            flush=True,
                        )
                        print()  # Move back to second line
                    else:
                        # Simple single-line update
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

        # Build index for changed files
        new_index = {
            "modules": all_modules,
            "metadata": {
                "indexed_at": datetime.now().isoformat(),
                "repo_path": str(repo_path_obj),
                "cicada_version": get_version_string(),
            },
        }

        # Merge with existing index
        if self.verbose:
            print("\nMerging with existing index...")
        merged_index = merge_indexes_incremental(existing_index, new_index, deleted_files)

        # Rebuild co-occurrence matrix if keywords were extracted
        if extract_keywords or extract_string_keywords:
            if self.verbose:
                print("Rebuilding keyword co-occurrence matrix...")
            try:
                analyzer = CooccurrenceAnalyzer(merged_index)
                merged_index["cooccurrences"] = analyzer.cooccurrence_matrix
                stats = analyzer.get_statistics()
                if self.verbose:
                    print(f"  ✓ Tracked {stats['total_keywords']} keywords")
                    print(f"  ✓ Found {stats['total_cooccurrences']} co-occurrence relationships")
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Failed to build co-occurrence matrix: {e}", file=sys.stderr)

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

        # Report keyword extraction failures if any
        if extract_keywords and keyword_extraction_failures > 0:
            print(
                f"\n⚠️  Warning: Keyword extraction failed for {keyword_extraction_failures} module(s) or function(s)"
            )

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
        default=".cicada/index.json",
        help="Output path for the index file (default: .cicada/index.json)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full reindex, ignoring existing hashes (default: incremental)",
    )

    args = parser.parse_args()

    indexer = ElixirIndexer()

    # Use incremental indexing by default (unless --full flag is set)
    indexer.incremental_index_repository(
        args.repo,
        args.output,
        extract_keywords=True,
        force_full=args.full,
    )


if __name__ == "__main__":
    main()
