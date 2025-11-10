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

from cicada.dependency_analyzer import (
    calculate_function_end_line,
    extract_function_dependencies,
    extract_module_dependencies,
)
from cicada.git_helper import GitHelper
from cicada.parser import ElixirParser
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

    def index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        compute_timestamps: bool = False,
    ):
        """
        Index an Elixir repository.

        Args:
            repo_path: Path to the Elixir repository root
            output_path: Path where the index JSON file will be saved
            extract_keywords: If True, extract keywords from documentation using NLP
            compute_timestamps: If True, compute git history timestamps for functions

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
                print(
                    f"Keyword extraction: {extraction_method.upper()} + {expansion_method.upper()}"
                )

        # Set up signal handlers for graceful interruption
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
        self._interrupted = False

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

                            # Extract and expand keywords from function docs
                            if keyword_extractor and func.get("doc"):
                                try:
                                    # Include function name in text for keyword extraction
                                    # This ensures the function name identifier gets 10x weight
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
                                except Exception as e:
                                    keyword_extraction_failures += 1
                                    if self.verbose:
                                        print(
                                            f"Warning: Keyword extraction failed for {module_name}.{func_name}: {e}",
                                            file=sys.stderr,
                                        )

                            # Compute git history timestamps if enabled
                            if git_helper and func_name:
                                try:
                                    # Get function evolution metadata
                                    evolution = git_helper.get_function_evolution(
                                        file_path=str(file_path.relative_to(repo_path_obj)),
                                        function_name=func_name,
                                    )

                                    if evolution:
                                        # Add timestamp fields to function
                                        func["created_at"] = evolution["created_at"]["date"]
                                        func["last_modified_at"] = evolution["last_modified"][
                                            "date"
                                        ]
                                        func["last_modified_sha"] = evolution["last_modified"][
                                            "sha"
                                        ]
                                        func["modification_count"] = evolution[
                                            "total_modifications"
                                        ]
                                except Exception as e:
                                    if self.verbose:
                                        print(
                                            f"Warning: Could not compute timestamps for {module_name}.{func_name}: {e}",
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

                        all_modules[module_name] = module_info

                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting
                if self.verbose and files_processed % self.PROGRESS_REPORT_INTERVAL == 0:
                    print(f"  Processed {files_processed}/{total_files} files...")

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

        # Save to file
        output_path_obj = Path(output_path)

        # Check if .cicada directory exists (first run detection)
        is_first_run = not output_path_obj.parent.exists()

        # On first run, add .cicada/ to .gitignore if it exists
        if is_first_run:
            from cicada.utils.path_utils import ensure_gitignore_has_cicada

            if ensure_gitignore_has_cicada(repo_path_obj) and self.verbose:
                print("✓ Added .cicada/ to .gitignore")

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
            return self.index_repository(str(repo_path_obj), str(output_path_obj), extract_keywords)

        if self.verbose:
            # Read and display keyword extraction config
            extraction_method, expansion_method = read_keyword_extraction_config(repo_path_obj)
            print(f"Performing incremental index of: {repo_path_obj}")
            print(f"Keyword extraction: {extraction_method.upper()} + {expansion_method.upper()}")

        # Set up signal handlers for graceful interruption
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
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

                # Initialize expansion method
                from cicada.keyword_expander import KeywordExpander

                keyword_expander = KeywordExpander(
                    expansion_type=expansion_method, verbose=self.verbose
                )

            except Exception as e:
                print(f"Warning: Could not initialize keyword extractor/expander: {e}")
                print("Continuing without keyword extraction...")
                extract_keywords = False

        # Process changed files
        all_modules = {}
        total_functions = 0
        files_processed = 0
        keyword_extraction_failures = 0

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

                        all_modules[module_name] = module_info
                        total_functions += len(functions)

                files_processed += 1

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
