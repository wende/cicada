"""Python repository indexer using SCIP protocol.

This indexer uses scip-python (powered by Pyright) to generate
type-aware semantic indexes of Python codebases.
"""

import json
import tempfile
from pathlib import Path

from cicada.languages.python.scip_installer import SCIPPythonInstaller
from cicada.languages.python.string_extractor import PythonStringExtractor
from cicada.languages.scip.indexer import GenericSCIPIndexer


class PythonSCIPIndexer(GenericSCIPIndexer):
    """Index Python repositories using scip-python."""

    def __init__(self, verbose: bool = False):
        """Initialize the Python SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = {
            "__pycache__",
            ".venv",
            "venv",
            ".git",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".egg-info",
            ".tox",
            ".ruff_cache",
            "htmlcov",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "python"

    def get_file_extensions(self) -> list[str]:
        """Return Python file extensions."""
        return [".py"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-python indexer."""
        self._ensure_scip_python_installed()
        return self._run_scip_python(repo_path)

    def _extract_string_keywords(
        self, index: dict, repo_path: Path, keyword_extractor, keyword_expander
    ) -> None:
        """Extract keywords from string literals in Python files.

        Args:
            index: The Cicada index to update
            repo_path: Repository root path
            keyword_extractor: Keyword extractor instance
            keyword_expander: Keyword expander instance
        """
        if self.verbose:
            print("  Extracting string keywords...")

        string_extractor = PythonStringExtractor(min_length=3)

        for _module_name, module_data in index.get("modules", {}).items():
            file_path = module_data.get("file")
            if not file_path:
                continue

            full_path = repo_path / file_path
            if not full_path.exists():
                continue

            try:
                source_code = full_path.read_text(encoding="utf-8")
                strings = string_extractor.extract_from_source(source_code)

                if not strings:
                    continue

                # Store string sources
                module_data["string_sources"] = strings

                # Extract keywords from all strings
                all_string_text = " ".join(s["string"] for s in strings)
                if all_string_text.strip():
                    keywords_result = keyword_extractor.extract_keywords(all_string_text, top_n=15)

                    # Apply string keyword boost (1.3x)
                    string_keywords = {}
                    for keyword, score in keywords_result.get("top_keywords", []):
                        string_keywords[keyword] = score * 1.3

                    if string_keywords:
                        # Expand keywords
                        if keyword_expander:
                            expanded = keyword_expander.expand_keywords(
                                list(string_keywords.keys())
                            )
                            for kw, score in expanded.items():
                                if kw not in string_keywords:
                                    string_keywords[kw] = score * 0.5

                        module_data["string_keywords"] = string_keywords

            except Exception as e:
                if self.verbose:
                    print(f"    Warning: Failed to extract strings from {file_path}: {e}")

    def _ensure_scip_python_installed(self):
        """
        Ensure scip-python is installed, auto-install if needed.

        Raises:
            RuntimeError: If npm is not available or installation fails
        """
        if SCIPPythonInstaller.is_scip_python_installed():
            if self.verbose:
                version = SCIPPythonInstaller.get_scip_python_version()
                print(f"  Using scip-python {version}")
            return

        # Check npm availability
        if not SCIPPythonInstaller.is_npm_available():
            raise RuntimeError(
                "npm is required to install scip-python.\n"
                "Install Node.js from: https://nodejs.org/\n"
                "Or install scip-python manually: npm install -g @sourcegraph/scip-python"
            )

        # Auto-install
        print("Installing scip-python (this may take a minute)...")
        success = SCIPPythonInstaller.install_scip_python(verbose=self.verbose)

        if not success:
            raise RuntimeError(
                "Failed to install scip-python.\n"
                "Try installing manually: npm install -g @sourcegraph/scip-python"
            )

        print("✓ scip-python installed successfully")

    def _run_scip_python(self, repo_path: Path) -> Path:
        """
        Run scip-python indexer on repository.

        Args:
            repo_path: Repository root path

        Returns:
            Path to generated .scip file

        Raises:
            RuntimeError: If scip-python execution fails
        """
        # Create temporary pyrightconfig.json to exclude .venv and dependencies
        pyright_config_path = repo_path / "pyrightconfig.json"
        temp_pyright_config = False

        if not pyright_config_path.exists():
            temp_pyright_config = True
            pyright_config = {"exclude": list(self.excluded_dirs)}
            with open(pyright_config_path, "w") as f:
                json.dump(pyright_config, f, indent=2)
            if self.verbose:
                print("  Created temporary pyrightconfig.json to exclude dependencies")

        # Create temporary file for .scip output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".scip", delete=False, dir=repo_path
        ) as tmp:
            scip_file = Path(tmp.name)

        cmd = [
            "scip-python",
            "index",
            str(repo_path),
            "--project-name",
            repo_path.name,
            "--output",
            str(scip_file),
        ]

        try:
            return self._run_scip_command(
                repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
            )
        finally:
            # Clean up temporary pyrightconfig if we created it
            if temp_pyright_config and pyright_config_path.exists():
                pyright_config_path.unlink()
