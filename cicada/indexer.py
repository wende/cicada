"""
Elixir Repository Indexer.

Walks an Elixir repository and indexes all modules and functions.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from cicada.parser import ElixirParser
from cicada.utils import save_index


class ElixirIndexer:
    """Indexes Elixir repositories to extract module and function information."""

    def __init__(self):
        """Initialize the indexer with a parser."""
        self.parser = ElixirParser()
        self.verbose = False
        self.excluded_dirs = {
            "deps",
            "_build",
            "node_modules",
            ".git",
            "assets",
            "priv",
        }

    def index_repository(
        self,
        repo_path: str,
        output_path: str = ".cicada/index.json",
        extract_keywords: bool = False,
        spacy_model: str = "small",
    ):
        """
        Index an Elixir repository.

        Args:
            repo_path: Path to the Elixir repository root
            output_path: Path where the index JSON file will be saved
            extract_keywords: If True, extract keywords from documentation using NLP
            spacy_model: Size of spaCy model to use for keyword extraction
                        ('small', 'medium', or 'large'). Default is 'small'.

        Returns:
            Dictionary containing the index data
        """
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        print(f"Indexing repository: {repo_path}")

        # Initialize keyword extractor if requested
        keyword_extractor = None
        if extract_keywords:
            try:
                from cicada.keyword_extractor import KeywordExtractor

                keyword_extractor = KeywordExtractor(
                    verbose=True, model_size=spacy_model
                )
            except Exception as e:
                print(f"Warning: Could not initialize keyword extractor: {e}")
                print("Continuing without keyword extraction...")
                extract_keywords = False

        # Find all Elixir files
        elixir_files = self._find_elixir_files(repo_path)
        total_files = len(elixir_files)

        print(f"Found {total_files} Elixir files")
        if extract_keywords:
            print("Keyword extraction enabled")

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

                        # Extract keywords if enabled
                        module_keywords = None
                        if keyword_extractor and module_data.get("moduledoc"):
                            try:
                                module_keywords = (
                                    keyword_extractor.extract_keywords_simple(
                                        module_data["moduledoc"], top_n=10
                                    )
                                )
                            except Exception as e:
                                keyword_extraction_failures += 1
                                if self.verbose:
                                    print(
                                        f"Warning: Keyword extraction failed for module {module_name}: {e}",
                                        file=sys.stderr,
                                    )

                        # Extract keywords from function docs
                        if keyword_extractor:
                            for func in functions:
                                if func.get("doc"):
                                    try:
                                        # Include function name in text for keyword extraction
                                        # This ensures the function name identifier gets 10x weight
                                        func_name = func.get("name", "")
                                        text_for_keywords = f"{func_name} {func['doc']}"
                                        func_keywords = (
                                            keyword_extractor.extract_keywords_simple(
                                                text_for_keywords, top_n=10
                                            )
                                        )
                                        if func_keywords:
                                            func["keywords"] = func_keywords
                                    except Exception as e:
                                        keyword_extraction_failures += 1
                                        if self.verbose:
                                            print(
                                                f"Warning: Keyword extraction failed for {module_name}.{func_name}: {e}",
                                                file=sys.stderr,
                                            )

                        # Store module info
                        module_info = {
                            "file": str(file_path.relative_to(repo_path)),
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
                        }

                        # Add module keywords if extracted
                        if module_keywords:
                            module_info["keywords"] = module_keywords

                        all_modules[module_name] = module_info

                        total_functions += len(functions)

                files_processed += 1

                # Progress reporting
                if files_processed % 10 == 0:
                    print(f"  Processed {files_processed}/{total_files} files...")

            except Exception as e:
                print(f"  Skipping {file_path}: {e}")
                continue

        # Build final index
        index = {
            "modules": all_modules,
            "metadata": {
                "indexed_at": datetime.now().isoformat(),
                "total_modules": len(all_modules),
                "total_functions": total_functions,
                "repo_path": str(repo_path),
            },
        }

        # Save to file
        output_path = Path(output_path)

        # Check if .cicada directory exists (first run detection)
        is_first_run = not output_path.parent.exists()

        # On first run, add .cicada/ to .gitignore if it exists
        if is_first_run:
            from cicada.utils.path_utils import ensure_gitignore_has_cicada

            if ensure_gitignore_has_cicada(repo_path):
                print("✓ Added .cicada/ to .gitignore")

        save_index(index, output_path, create_dirs=True)

        print(f"\nIndexing complete!")
        print(f"  Modules: {len(all_modules)}")
        print(f"  Functions: {total_functions}")

        # Report keyword extraction failures if any
        if extract_keywords and keyword_extraction_failures > 0:
            print(
                f"\n⚠️  Warning: Keyword extraction failed for {keyword_extraction_failures} module(s) or function(s)"
            )
            print("   Some documentation may not be indexed for keyword search.")

        print(f"\nIndex saved to: {output_path}")

        return index

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
        "--extract-keywords",
        action="store_true",
        help="Extract keywords from documentation using NLP (adds ~1-2s per 100 docs)",
    )
    parser.add_argument(
        "--spacy-model",
        choices=["small", "medium", "large"],
        default="small",
        help="Size of spaCy model to use for keyword extraction (default: small). "
        "Medium and large models provide better accuracy but are slower.",
    )

    args = parser.parse_args()

    indexer = ElixirIndexer()
    indexer.index_repository(
        args.repo,
        args.output,
        extract_keywords=args.extract_keywords,
        spacy_model=args.spacy_model,
    )


if __name__ == "__main__":
    main()
