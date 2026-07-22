"""Gleam indexer implementation."""

from pathlib import Path
from typing import Any

from cicada.languages.gleam.parser import GleamParser
from cicada.parsing.base_indexer import BaseIndexer
from cicada.parsing.language_config import LanguageConfig
from cicada.utils import load_index, save_index
from cicada.utils.keyword_utils import get_keyword_extractor_from_config


class GleamIndexer(BaseIndexer):
    """Indexer for Gleam projects."""

    def __init__(self):
        self.parser = GleamParser()
        self.config = LanguageConfig.default_gleam()
        self.keyword_extractor: Any = None

    def get_language_name(self) -> str:
        return "gleam"

    def get_file_extensions(self) -> list[str]:
        return self.config.file_extensions

    def get_excluded_dirs(self) -> list[str]:
        return self.config.excluded_dirs

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,  # noqa: ARG002 - interface compatibility
        verbose: bool = False,
        config_path: str | Path | None = None,  # noqa: ARG002 - interface compatibility
    ) -> dict:
        """Index a Gleam repository."""
        repo_path = Path(repo_path)
        output_path = Path(output_path)
        modules, source_count, functions_count, errors = self._collect_modules(repo_path, verbose)

        index_data = {
            "modules": modules,
            "metadata": {
                "language": "gleam",
                "files_indexed": source_count,
                "modules_count": len(modules),
                "functions_count": functions_count,
            },
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_index(index_data, output_path)

        if verbose:
            print(f"Indexed {len(modules)} Gleam modules ({functions_count} functions)")

        return {
            "success": len(errors) == 0,
            "modules_count": len(modules),
            "functions_count": functions_count,
            "files_indexed": source_count,
            "errors": errors,
        }

    def merge_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        verbose: bool = False,
    ) -> dict:
        """Merge native Gleam modules into an existing multi-language index."""
        repo_path = Path(repo_path)
        output_path = Path(output_path)
        modules, source_count, functions_count, errors = self._collect_modules(repo_path, verbose)

        index_data = load_index(output_path) or {"modules": {}, "metadata": {}}
        index_modules = index_data.setdefault("modules", {})
        stale_modules = [
            name
            for name, module in index_modules.items()
            if module.get("language") == "gleam" and name not in modules
        ]
        for name in stale_modules:
            index_modules.pop(name, None)

        index_modules.update(modules)
        metadata = index_data.setdefault("metadata", {})
        embedded = metadata.setdefault("embedded_languages", {})
        embedded["gleam"] = {
            "files_indexed": source_count,
            "modules_count": len(modules),
            "functions_count": functions_count,
        }
        save_index(index_data, output_path)

        if verbose:
            print(f"Indexed {len(modules)} embedded Gleam modules ({functions_count} functions)")

        return {
            "success": len(errors) == 0,
            "modules_count": len(modules),
            "functions_count": functions_count,
            "files_indexed": source_count,
            "errors": errors,
        }

    def _collect_modules(
        self, repo_path: Path, verbose: bool
    ) -> tuple[dict[str, dict], int, int, list[str]]:
        extract_keywords, self.keyword_extractor = get_keyword_extractor_from_config(
            repo_path, verbose=verbose
        )

        source_files = self._find_source_files(repo_path)
        modules = {}
        errors = []
        functions_count = 0

        for file_path in source_files:
            try:
                result = self.parser.parse_file(str(file_path), repo_path=repo_path)
                if not result:
                    continue

                for module_data in result:
                    module_name = module_data["module"]
                    rel_path = str(file_path.relative_to(repo_path))
                    functions = module_data.get("functions", [])
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
                        "language": "gleam",
                    }
                    functions_count += len(functions)
            except Exception as exc:
                errors.append(f"{file_path}: {exc}")

        return modules, len(source_files), functions_count, errors

    def _extract_keywords(
        self,
        module_name: str,
        module_doc: str | None,
        functions: list[dict],
    ) -> dict[str, float]:
        keywords: dict[str, float] = {}

        for part in module_name.lower().replace("/", "_").split("_"):
            if len(part) > 2:
                keywords[part] = keywords.get(part, 0) + 1.5

        if module_doc and self.keyword_extractor:
            for keyword in self.keyword_extractor.extract_keywords_simple(module_doc):
                keywords[keyword] = keywords.get(keyword, 0) + 1.0

        for function in functions:
            for part in function.get("name", "").lower().split("_"):
                if len(part) > 2:
                    keywords[part] = keywords.get(part, 0) + 1.0

            function_doc = function.get("doc")
            if function_doc and self.keyword_extractor:
                for keyword in self.keyword_extractor.extract_keywords_simple(function_doc):
                    keywords[keyword] = keywords.get(keyword, 0) + 0.5

        return keywords
