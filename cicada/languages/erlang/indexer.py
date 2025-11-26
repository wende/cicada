"""Erlang indexer implementation."""

import json
from pathlib import Path

from cicada.languages.erlang.parser import ErlangParser
from cicada.parsing.base_indexer import BaseIndexer


class ErlangIndexer(BaseIndexer):
    """Indexer for Erlang projects."""

    def __init__(self):
        self.parser = ErlangParser()

    def get_language_name(self) -> str:
        return "erlang"

    def get_file_extensions(self) -> list[str]:
        return [".erl", ".hrl"]

    def get_excluded_dirs(self) -> list[str]:
        return ["_build", "deps", ".git", "node_modules", "ebin"]

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index an Erlang repository.

        Args:
            repo_path: Path to the repository to index
            output_path: Path where the index.json should be saved
            force: If True, reindex all files regardless of changes
            verbose: If True, print detailed progress information
            config_path: Optional path to config.yaml for custom settings

        Returns:
            Dictionary with indexing results
        """
        repo_path = Path(repo_path)
        output_path = Path(output_path)

        # Find source files using inherited method
        source_files = self._find_source_files(repo_path)

        modules = {}
        errors = []
        functions_count = 0

        for file_path in source_files:
            try:
                result = self.parser.parse_file(str(file_path))
                if result:
                    for module_data in result:
                        module_name = module_data["module"]
                        rel_path = str(file_path.relative_to(repo_path))

                        modules[module_name] = {
                            "file": rel_path,
                            "line": module_data.get("line", 1),
                            "moduledoc": module_data.get("doc"),
                            "functions": module_data.get("functions", []),
                            "keywords": {},
                        }
                        functions_count += len(module_data.get("functions", []))
            except Exception as e:
                errors.append(f"{file_path}: {e}")

        # Build index data
        index_data = {
            "modules": modules,
            "metadata": {
                "language": "erlang",
                "files_indexed": len(source_files),
                "modules_count": len(modules),
                "functions_count": functions_count,
            },
        }

        # Ensure output directory exists and save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(index_data, f, indent=2)

        if verbose:
            print(f"Indexed {len(modules)} Erlang modules ({functions_count} functions)")

        return {
            "success": len(errors) == 0,
            "modules_count": len(modules),
            "functions_count": functions_count,
            "files_indexed": len(source_files),
            "errors": errors,
        }
