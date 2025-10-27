"""
Elixir Repository Indexer.

Walks an Elixir repository and indexes all modules and functions.
"""

import argparse
import os
from datetime import datetime
from pathlib import Path
from cicada.parser import ElixirParser
from cicada.utils import save_index


class ElixirIndexer:
    """Indexes Elixir repositories to extract module and function information."""

    def __init__(self):
        """Initialize the indexer with a parser."""
        self.parser = ElixirParser()
        self.excluded_dirs = {
            "deps",
            "_build",
            "node_modules",
            ".git",
            "assets",
            "priv",
        }

    def index_repository(self, repo_path: str, output_path: str = ".cicada/index.json"):
        """
        Index an Elixir repository.

        Args:
            repo_path: Path to the Elixir repository root
            output_path: Path where the index JSON file will be saved

        Returns:
            Dictionary containing the index data
        """
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        print(f"Indexing repository: {repo_path}")

        # Find all Elixir files
        elixir_files = self._find_elixir_files(repo_path)
        total_files = len(elixir_files)

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
                            "value_mentions": module_data.get("value_mentions", []),
                            "calls": module_data.get("calls", []),
                        }

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

    args = parser.parse_args()

    indexer = ElixirIndexer()
    _ = indexer.index_repository(args.repo, args.output)


if __name__ == "__main__":
    main()
