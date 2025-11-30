"""Erlang indexer implementation."""

import json
from pathlib import Path
from typing import Any

from cicada.languages.erlang.parser import ErlangParser
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.keyword_utils import get_keyword_extractor_from_config


class ErlangIndexer(BaseIndexer):
    """Indexer for Erlang projects."""

    def __init__(self):
        self.parser = ErlangParser()
        self.keyword_extractor: Any = None

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
        force: bool = False,  # noqa: ARG002 - interface compatibility
        verbose: bool = False,
        config_path: str | Path | None = None,  # noqa: ARG002 - interface compatibility
    ) -> dict:
        """
        Index an Erlang repository.

        Args:
            repo_path: Path to the repository to index
            output_path: Path where the index.json should be saved
            force: Ignored - incremental indexing not implemented, always
                does full reindex. Accepted for interface compatibility.
            verbose: If True, print detailed progress information
            config_path: Ignored - config-based indexing not implemented.
                Accepted for interface compatibility.

        Returns:
            Dictionary with indexing results
        """
        repo_path = Path(repo_path)
        output_path = Path(output_path)

        # Initialize keyword extractor from config
        extract_keywords, self.keyword_extractor = get_keyword_extractor_from_config(
            repo_path, verbose=verbose
        )

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
                        functions = module_data.get("functions", [])

                        # Extract keywords from module doc and function docs
                        keywords = {}
                        if extract_keywords and self.keyword_extractor:
                            keywords = self._extract_keywords(
                                module_name,
                                module_data.get("doc"),
                                functions,
                            )

                        modules[module_name] = {
                            "file": rel_path,
                            "line": module_data.get("line", 1),
                            "moduledoc": module_data.get("doc"),
                            "functions": functions,
                            "keywords": keywords,
                        }
                        functions_count += len(functions)
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

    def _extract_keywords(
        self,
        module_name: str,
        module_doc: str | None,
        functions: list[dict],
    ) -> dict[str, float]:
        """
        Extract keywords from module name, module doc, and function docs.

        Args:
            module_name: Name of the module
            module_doc: Module-level documentation (or None)
            functions: List of function dicts with optional 'doc' field

        Returns:
            Dictionary mapping keywords to scores
        """
        keywords: dict[str, float] = {}

        # Extract from module name (split on underscore)
        name_parts = module_name.lower().split("_")
        for part in name_parts:
            if len(part) > 2:
                keywords[part] = keywords.get(part, 0) + 1.5  # Boost name keywords

        # Extract from module doc
        if module_doc and self.keyword_extractor:
            doc_keywords = self.keyword_extractor.extract_keywords_simple(module_doc)
            for kw in doc_keywords:
                keywords[kw] = keywords.get(kw, 0) + 1.0

        # Extract from function docs
        for func in functions:
            # Add function name
            func_name = func.get("name", "").lower()
            name_parts = func_name.split("_")
            for part in name_parts:
                if len(part) > 2:
                    keywords[part] = keywords.get(part, 0) + 1.0

            # Add function doc keywords
            func_doc = func.get("doc")
            if func_doc and self.keyword_extractor:
                doc_keywords = self.keyword_extractor.extract_keywords_simple(func_doc)
                for kw in doc_keywords:
                    keywords[kw] = keywords.get(kw, 0) + 0.5

        return keywords
