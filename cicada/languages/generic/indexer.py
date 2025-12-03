"""
Generic file indexer for text files not handled by language-specific indexers.

This indexer indexes all text files (markdown, config files, docs, etc.)
that are not already covered by language-specific indexers.
"""

import json
import mimetypes
from pathlib import Path

import pathspec

from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.hash_utils import (
    compute_hashes_for_files,
    load_file_hashes,
    save_file_hashes,
)
from cicada.utils.keyword_utils import read_keyword_extraction_config
from cicada.utils.storage import get_hashes_path

# Maximum number of lines to index (skip very large files)
MAX_LINES = 10000


class GenericFileIndexer(BaseIndexer):
    """Index text files not handled by language-specific indexers."""

    supports_incremental = True

    def __init__(self, excluded_extensions: set[str] | None = None, verbose: bool = False):
        """
        Initialize the generic file indexer.

        Args:
            excluded_extensions: Extensions already handled by language-specific
                                indexers (e.g., {".ex", ".py", ".erl"}).
                                Files with these extensions will be skipped.
            verbose: If True, print detailed progress information
        """
        super().__init__(verbose=verbose)
        self.excluded_extensions = excluded_extensions or set()
        self.excluded_dirs = {
            ".git",
            ".cicada",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".egg-info",
            ".tox",
            ".ruff_cache",
            "htmlcov",
            "_build",
            "deps",
            ".elixir_ls",
            ".cache",
            ".coverage",
        }
        # Binary mime type prefixes to skip
        self._binary_mime_prefixes = ("image/", "audio/", "video/", "application/octet-stream")

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "generic"

    def get_file_extensions(self) -> list[str]:
        """Return empty list - we don't filter by extension."""
        return []

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _load_gitignore(self, repo_path: Path) -> pathspec.PathSpec:
        """
        Parse .gitignore and return a PathSpec for matching.

        Args:
            repo_path: Repository root path

        Returns:
            PathSpec object for matching gitignored paths
        """
        patterns = [".git/", ".git"]  # Always ignore .git directory

        gitignore_path = repo_path / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            patterns.append(line)
            except (OSError, UnicodeDecodeError):
                pass  # Ignore errors reading gitignore

        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if a file is a text file (not binary).

        Uses mimetypes to guess the file type. For unknown types,
        checks for null bytes in the first 8KB.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file appears to be a text file
        """
        # First check mimetype
        mime_type, _ = mimetypes.guess_type(str(file_path))

        if mime_type:
            # Skip known binary types
            if mime_type.startswith(self._binary_mime_prefixes):
                return False
            # Accept known text types
            if mime_type.startswith("text/"):
                return True
            # Accept common text-like application types
            if mime_type in (
                "application/json",
                "application/xml",
                "application/javascript",
                "application/x-yaml",
                "application/toml",
            ):
                return True

        # For unknown types, check for null bytes in first 8KB
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                # Binary files typically contain null bytes
                return b"\x00" not in chunk
        except OSError:
            return False

    def _find_source_files(self, repo_path: Path) -> list[Path]:
        """
        Find all text files to index, respecting gitignore and exclusions.

        Args:
            repo_path: Repository root path

        Returns:
            List of file paths to index
        """
        gitignore_spec = self._load_gitignore(repo_path)
        files_to_index = []

        for file_path in repo_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Get relative path for pattern matching
            try:
                rel_path = file_path.relative_to(repo_path)
            except ValueError:
                continue

            # Skip files in excluded directories
            if any(part in self.excluded_dirs for part in rel_path.parts):
                continue

            # Skip gitignored files
            if gitignore_spec.match_file(str(rel_path)):
                continue

            # Skip files with excluded extensions (already handled by language indexers)
            if file_path.suffix.lower() in self.excluded_extensions:
                continue

            # Skip binary files
            if not self._is_text_file(file_path):
                continue

            files_to_index.append(file_path)

        return sorted(files_to_index)

    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file without loading it all into memory."""
        try:
            with open(file_path, "rb") as f:
                return sum(1 for _ in f)
        except OSError:
            return 0

    def _read_file_content(self, file_path: Path) -> str | None:
        """
        Read file content, returning None if file is too large or unreadable.

        Args:
            file_path: Path to the file

        Returns:
            File content as string, or None if file should be skipped
        """
        # Check line count first
        line_count = self._count_lines(file_path)
        if line_count > MAX_LINES:
            if self.verbose:
                print(f"    Skipping {file_path.name}: {line_count} lines > {MAX_LINES}")
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,  # noqa: ARG002 - required by base class
    ) -> dict:
        """
        Index repository and save the results.

        This delegates to incremental_index_repository for actual indexing.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            force: If True, force full reindex
            verbose: If True, print detailed progress
            config_path: Optional config file path (unused)

        Returns:
            Dict with indexing results
        """
        return self.incremental_index_repository(
            repo_path=str(repo_path),
            output_path=str(output_path),
            extract_keywords=True,
            extract_string_keywords=False,
            compute_timestamps=False,
            extract_cochange=False,
            force_full=force,
            verbose=verbose,
        )

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = True,
        extract_string_keywords: bool = False,  # noqa: ARG002 - required by base class
        compute_timestamps: bool = False,  # noqa: ARG002 - required by base class
        extract_cochange: bool = False,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Index text files with all features.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            extract_keywords: Whether to extract keywords from file content
            extract_string_keywords: Unused for generic files
            compute_timestamps: Unused for generic files
            extract_cochange: Whether to analyze co-change patterns
            force_full: If True, force full reindex
            verbose: If True, print detailed progress

        Returns:
            Dict with indexing results
        """
        self.verbose = verbose
        self._interrupted = False

        repo_path_obj = Path(repo_path).resolve()
        output_path_obj = Path(output_path).resolve()

        self._start_timing()

        if self.verbose:
            print(f"Indexing generic files in: {repo_path_obj}")

        # Load existing index if it exists
        existing_index: dict = {}
        if output_path_obj.exists():
            try:
                with open(output_path_obj) as f:
                    existing_index = json.load(f)
            except (OSError, json.JSONDecodeError):
                existing_index = {}

        # Get hashes for incremental indexing
        # Use a separate hashes file for generic indexer
        hashes_path = get_hashes_path(repo_path_obj)
        hashes_path = hashes_path.parent / "generic_hashes.json"
        existing_hashes = load_file_hashes(str(hashes_path))

        # Find all text files to index
        text_files = self._find_source_files(repo_path_obj)
        self._log_timing("File discovery")

        if self.verbose:
            print(f"  Found {len(text_files)} text files to index")

        # Convert to relative paths
        relative_files = [str(f.relative_to(repo_path_obj)) for f in text_files]

        # Compute current hashes
        current_hashes = compute_hashes_for_files(relative_files, str(repo_path_obj))

        # Detect changes
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
                print("  No changes detected. Generic index is up to date.")
            return {
                "success": True,
                "modules_count": len(existing_index.get("modules", {})),
                "functions_count": 0,
                "files_indexed": 0,
                "errors": [],
                "skipped": True,
            }

        if self.verbose:
            if new_files or modified_files or deleted_files:
                print(
                    f"  Changes detected: {len(new_files)} new, "
                    f"{len(modified_files)} modified, {len(deleted_files)} deleted"
                )
            else:
                print("  Performing full index...")

        # Initialize keyword extractor
        keyword_extractor = None
        if extract_keywords:
            try:
                extraction_method, _ = read_keyword_extraction_config(repo_path_obj)
                if extraction_method == "bert":
                    from cicada.extractors.keybert import KeyBERTExtractor

                    keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                else:
                    from cicada.extractors.keyword import RegularKeywordExtractor

                    keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)
                self._log_timing("Keyword extractor initialization")
            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Keyword extractor initialization failed: {e}")

        # Build index
        modules: dict = existing_index.get("modules", {}).copy() if not force_full else {}

        # Remove deleted files from index
        for deleted_file in deleted_files:
            if deleted_file in modules:
                del modules[deleted_file]

        # Determine which files to process
        files_to_process = relative_files if force_full else (new_files + modified_files)

        # Index files
        processed = 0
        for rel_file in files_to_process:
            file_path = repo_path_obj / rel_file
            content = self._read_file_content(file_path)

            if content is None:
                continue

            # Create module entry (file-level only)
            module_data: dict = {
                "file": rel_file,
                "line": 1,
                "functions": [],  # Generic files have no functions
            }

            # Extract keywords from file content
            if keyword_extractor and content.strip():
                try:
                    result = keyword_extractor.extract_keywords(content, top_n=15)
                    keywords = {}
                    for keyword, score in result.get("top_keywords", []):
                        keywords[keyword] = score
                    if keywords:
                        module_data["keywords"] = keywords
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Failed to extract keywords from {rel_file}: {e}")

            modules[rel_file] = module_data
            processed += 1

            if self.verbose and processed % 100 == 0:
                print(
                    f"\r    Processed {processed}/{len(files_to_process)} files", end="", flush=True
                )

        if self.verbose and processed > 0:
            print()  # New line after progress

        self._log_timing("File indexing")

        # Build the final index
        index = {
            "modules": modules,
            "metadata": {
                "language": "generic",
                "total_modules": len(modules),
                "total_functions": 0,
            },
        }

        # Run co-change analysis if requested
        if extract_cochange:
            self._extract_cochange(index, repo_path_obj)
            self._log_timing("Co-change analysis")

        # Save index
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path_obj, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        self._log_timing("Index saving")

        # Save hashes
        save_file_hashes(str(hashes_path), current_hashes)

        if self.verbose:
            print(f"  Indexed {len(modules)} generic files")
            print(f"  Index saved to: {output_path_obj}")

        return {
            "success": True,
            "modules_count": len(modules),
            "functions_count": 0,
            "files_indexed": processed,
            "errors": [],
        }

    def merge_into_existing_index(
        self, existing_index_path: Path, repo_path: Path, verbose: bool = True
    ) -> dict:
        """
        Run generic indexing and merge results into an existing index.

        This is the main entry point for integrating with language-specific indexers.
        It indexes all text files not covered by the primary indexer and merges
        the results into the same index.json file.

        Args:
            existing_index_path: Path to the existing index.json
            repo_path: Repository root path
            verbose: If True, print progress

        Returns:
            Dict with indexing results
        """
        self.verbose = verbose

        if self.verbose:
            print("\nIndexing generic files...")

        # Load existing index
        try:
            with open(existing_index_path, encoding="utf-8") as f:
                existing_index = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            if self.verbose:
                print(f"  Warning: Could not load existing index: {e}")
            existing_index = {"modules": {}, "metadata": {}}

        # Get hashes for incremental indexing
        hashes_path = get_hashes_path(repo_path)
        hashes_path = hashes_path.parent / "generic_hashes.json"
        existing_hashes = load_file_hashes(str(hashes_path))

        # Find text files
        text_files = self._find_source_files(repo_path)

        if self.verbose:
            print(f"  Found {len(text_files)} text files")

        # Convert to relative paths
        relative_files = [str(f.relative_to(repo_path)) for f in text_files]

        # Compute current hashes
        current_hashes = compute_hashes_for_files(relative_files, str(repo_path))

        # Detect changes
        current_file_set = set(current_hashes.keys())
        old_file_set = set(existing_hashes.keys())
        deleted_files = list(old_file_set - current_file_set)
        new_files = [f for f in current_hashes if f not in existing_hashes]
        modified_files = [
            f
            for f in current_hashes
            if f in existing_hashes and current_hashes[f] != existing_hashes[f]
        ]

        if not new_files and not modified_files and not deleted_files:
            if self.verbose:
                print("  No changes in generic files")
            return {
                "success": True,
                "files_indexed": 0,
                "skipped": True,
            }

        if self.verbose:
            print(
                f"  Changes: {len(new_files)} new, "
                f"{len(modified_files)} modified, {len(deleted_files)} deleted"
            )

        # Initialize keyword extractor
        keyword_extractor = None
        try:
            extraction_method, _ = read_keyword_extraction_config(repo_path)
            if extraction_method == "bert":
                from cicada.extractors.keybert import KeyBERTExtractor

                keyword_extractor = KeyBERTExtractor(verbose=False)
            else:
                from cicada.extractors.keyword import RegularKeywordExtractor

                keyword_extractor = RegularKeywordExtractor(verbose=False)
        except Exception:
            from cicada.extractors.keyword import RegularKeywordExtractor

            keyword_extractor = RegularKeywordExtractor(verbose=False)

        # Get modules from existing index
        modules = existing_index.get("modules", {})

        # Remove deleted files
        for deleted_file in deleted_files:
            if deleted_file in modules:
                del modules[deleted_file]

        # Process new and modified files
        files_to_process = new_files + modified_files
        processed = 0

        for rel_file in files_to_process:
            file_path = repo_path / rel_file
            content = self._read_file_content(file_path)

            if content is None:
                continue

            # Create module entry
            module_data: dict = {
                "file": rel_file,
                "line": 1,
                "functions": [],
            }

            # Extract keywords
            if keyword_extractor and content.strip():
                try:
                    result = keyword_extractor.extract_keywords(content, top_n=15)
                    keywords = {}
                    for keyword, score in result.get("top_keywords", []):
                        keywords[keyword] = score
                    if keywords:
                        module_data["keywords"] = keywords
                except Exception:
                    pass

            modules[rel_file] = module_data
            processed += 1

        # Update the existing index
        existing_index["modules"] = modules

        # Update metadata
        if "metadata" not in existing_index:
            existing_index["metadata"] = {}
        existing_index["metadata"]["total_modules"] = len(modules)

        # Save merged index
        with open(existing_index_path, "w", encoding="utf-8") as f:
            json.dump(existing_index, f, indent=2, ensure_ascii=False)

        # Save hashes
        save_file_hashes(str(hashes_path), current_hashes)

        if self.verbose:
            print(f"  ✓ Indexed {processed} generic files")

        return {
            "success": True,
            "files_indexed": processed,
        }
