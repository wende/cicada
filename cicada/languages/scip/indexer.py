"""Generic SCIP indexer for all SCIP-based languages.

This base class contains all the shared logic for indexing repositories
using SCIP (Source Code Intelligence Protocol). Language-specific indexers
(Python, TypeScript, etc.) only need to provide minimal configuration.
"""

import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from cicada.git.cochange_analyzer import CoChangeAnalyzer
from cicada.git.helper import GitHelper
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


class GenericSCIPIndexer(BaseIndexer, ABC):
    """
    Generic indexer for SCIP-based languages.

    Subclasses only need to implement:
    - get_language_name()
    - get_file_extensions()
    - get_excluded_dirs()
    - _run_scip_indexer(repo_path) -> Path to .scip file
    - _extract_string_keywords() (optional)
    """

    def __init__(self, verbose: bool = False):
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

    def _extract_string_keywords(
        self, index: dict, repo_path: Path, keyword_extractor, keyword_expander
    ) -> None:
        """
        Extract keywords from string literals (optional, language-specific).

        Default implementation does nothing. Override in subclasses as needed.
        """

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
            extract_keywords=True,
            extract_string_keywords=False,
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
        Index repository with all features.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            extract_keywords: Whether to extract keywords from docstrings
            extract_string_keywords: Whether to extract keywords from string literals
            compute_timestamps: Whether to compute git timestamps for functions
            extract_cochange: Whether to analyze co-change patterns
            force_full: If True, force full reindex even if up-to-date
            verbose: If True, print detailed progress information

        Returns:
            Dict with indexing results
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
                    f"  SCIP index: {summary['documents']} documents, {summary['symbols']} symbols"
                )

            # Initialize keyword extractor
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

                    from cicada.keyword_expander import KeywordExpander

                    keyword_expander = KeywordExpander(
                        expansion_type=expansion_method, verbose=self.verbose
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Keyword extractor initialization failed: {e}")

            # Convert to Cicada format
            converter = SCIPConverter(
                extract_keywords=extract_keywords,
                keyword_extractor=keyword_extractor,
                verbose=self.verbose,
            )
            cicada_index = converter.convert(scip_index, repo_path_obj)

            # Extract string keywords if requested
            if extract_string_keywords and keyword_extractor:
                try:
                    self._extract_string_keywords(
                        cicada_index, repo_path_obj, keyword_extractor, keyword_expander
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: String keyword extraction failed: {e}")

            # Compute timestamps if requested
            if compute_timestamps:
                try:
                    self._compute_timestamps(cicada_index, repo_path_obj)
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Timestamp computation failed: {e}")

            # Extract co-change relationships if requested
            if extract_cochange:
                try:
                    self._extract_cochange(cicada_index, repo_path_obj)
                except Exception as e:
                    if self.verbose:
                        print(f"    Warning: Co-change analysis failed: {e}")

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

    def _compute_timestamps(self, index: dict, repo_path: Path) -> None:
        """Compute git timestamps for functions."""
        if self.verbose:
            print("  Computing git timestamps...")

        # Collect all functions
        functions_by_file: dict[str, list[dict]] = {}
        for _module_name, module_data in index.get("modules", {}).items():
            file_path = module_data.get("file")
            if not file_path:
                continue

            for func in module_data.get("functions", []):
                func_name = func.get("name")
                line = func.get("line")
                if func_name and line:
                    if file_path not in functions_by_file:
                        functions_by_file[file_path] = []
                    functions_by_file[file_path].append(
                        {"name": func_name, "line": line, "func_ref": func}
                    )

        if not functions_by_file:
            if self.verbose:
                print("  No functions found; skipping git timestamp computation.")
            return

        try:
            git_helper = GitHelper(str(repo_path))
        except Exception as e:
            if self.verbose:
                print(f"    Warning: Could not initialize git helper: {e}")
            return

        # Query git for function evolution
        try:
            for file_path, file_functions in functions_by_file.items():
                functions_for_git = [{"name": f["name"], "line": f["line"]} for f in file_functions]
                evolution_data = git_helper.get_functions_evolution_batch(
                    file_path, functions_for_git
                )

                for func_info in file_functions:
                    func_name = func_info["name"]
                    evolution = evolution_data.get(func_name)
                    if evolution and isinstance(evolution, dict):
                        # Extract individual fields from evolution data
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
        """Extract co-change relationships from git history."""
        if self.verbose:
            print("  Analyzing co-change patterns from git history...")

        try:
            analyzer = CoChangeAnalyzer(language=self.get_language_name())
            cochange_data = analyzer.analyze_repository(str(repo_path))

            index["cochange_metadata"] = cochange_data["metadata"]

            # Build file to module mapping
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

            if result.returncode != 0:
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
        except Exception:
            if output_path.exists():
                output_path.unlink()
            raise
