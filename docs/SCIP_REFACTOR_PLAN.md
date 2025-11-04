# SCIP Indexer Refactoring Plan

**Problem:** `PythonSCIPIndexer` has tons of generic SCIP logic that would be copy-pasted for TypeScript (and future SCIP languages).

**Solution:** Extract generic SCIP indexing logic into a reusable base class.

## Architecture

```
cicada/languages/
├── scip/
│   ├── converter.py       # ✅ Already generic
│   ├── reader.py          # ✅ Already generic
│   ├── indexer.py         # 🆕 NEW: Generic SCIP indexer
│   └── installer.py       # 🆕 NEW: Generic SCIP tool installer
├── python/
│   ├── indexer.py         # 🔄 REFACTOR: Thin wrapper over SCIPIndexer
│   └── scip_installer.py  # 🗑️ REMOVE: Move logic to generic installer
└── typescript/
    └── indexer.py         # 🆕 NEW: Thin wrapper over SCIPIndexer
```

## Generic SCIPIndexer

**File:** `cicada/languages/scip/indexer.py`

```python
"""Generic SCIP-based indexer for any language."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class SCIPToolConfig:
    """Configuration for a SCIP tool."""

    tool_name: str              # e.g., "scip-python", "scip-typescript"
    npm_package: str            # e.g., "@sourcegraph/scip-python"
    language_name: str          # e.g., "python", "typescript"
    file_extensions: list[str]  # e.g., [".py"], [".ts", ".tsx"]
    excluded_dirs: set[str]     # e.g., {"__pycache__", ".venv"}

    # Command builder
    def build_command(self, repo_path: Path, output_file: Path) -> list[str]:
        """Build the command to run the SCIP tool."""
        # Default implementation, can be overridden
        return [
            self.tool_name,
            "index",
            str(repo_path),
            "--project-name",
            repo_path.name,
            "--output",
            str(output_file),
        ]


class SCIPIndexer(BaseIndexer):
    """Generic indexer for SCIP-based languages."""

    def __init__(self, config: SCIPToolConfig, verbose: bool = False):
        """
        Initialize SCIP indexer.

        Args:
            config: Language-specific SCIP tool configuration
            verbose: If True, print detailed progress
        """
        self.config = config
        self.verbose = verbose

    def get_language_name(self) -> str:
        return self.config.language_name

    def get_file_extensions(self) -> list[str]:
        return self.config.file_extensions

    def get_excluded_dirs(self) -> list[str]:
        return list(self.config.excluded_dirs)

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index repository using SCIP tool.

        This is the generic SCIP indexing pipeline:
        1. Ensure SCIP tool is installed
        2. Run SCIP tool to generate .scip file
        3. Read .scip file
        4. Convert to Cicada format
        5. Save index
        6. Report statistics
        7. Cleanup temp files
        """
        repo_path = Path(repo_path).resolve()
        output_path = Path(output_path).resolve()

        if verbose or self.verbose:
            print(f"Indexing {self.config.language_name} repository: {repo_path}")

        # 1. Ensure SCIP tool is installed
        self._ensure_tool_installed()

        # 2. Run SCIP tool
        scip_file = self._run_scip_tool(repo_path)

        try:
            # 3. Read SCIP file
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            if verbose or self.verbose:
                summary = reader.get_index_summary(scip_index)
                print(
                    f"  SCIP index: {summary['documents']} documents, "
                    f"{summary['symbols']} symbols"
                )

            # 4. Get keyword extractor from config
            extract_keywords, keyword_extractor = get_keyword_extractor_from_config(
                repo_path, verbose=(verbose or self.verbose)
            )

            # 5. Convert to Cicada format
            converter = SCIPConverter(
                extract_keywords=extract_keywords,
                keyword_extractor=keyword_extractor,
                verbose=self.verbose,
            )
            cicada_index = converter.convert(scip_index, repo_path)

            # 6. Save index
            self._save_index(cicada_index, output_path)

            # 7. Report statistics
            stats = self._build_statistics(cicada_index, scip_index, verbose or self.verbose)

            if verbose or self.verbose:
                print(f"  Index saved to: {output_path}")

            return {
                "success": True,
                "modules_count": stats["modules_count"],
                "functions_count": stats["functions_count"],
                "files_indexed": stats["files_indexed"],
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Failed to process SCIP index: {e}"
            if verbose or self.verbose:
                print(f"  Error: {error_msg}")
            return {
                "success": False,
                "modules_count": 0,
                "functions_count": 0,
                "files_indexed": 0,
                "errors": [error_msg],
            }

        finally:
            # 8. Cleanup
            if scip_file.exists():
                scip_file.unlink()
                if verbose or self.verbose:
                    print(f"  Cleaned up temporary file: {scip_file}")

    def _ensure_tool_installed(self):
        """Ensure SCIP tool is installed."""
        from cicada.languages.scip.installer import SCIPToolInstaller

        installer = SCIPToolInstaller(
            tool_name=self.config.tool_name,
            npm_package=self.config.npm_package,
        )

        if installer.is_installed():
            if self.verbose:
                version = installer.get_version()
                print(f"  Using {self.config.tool_name} {version}")
            return

        # Auto-install
        if not installer.is_npm_available():
            raise RuntimeError(
                f"npm is required to install {self.config.tool_name}.\n"
                f"Install Node.js from: https://nodejs.org/\n"
                f"Or install manually: npm install -g {self.config.npm_package}"
            )

        print(f"Installing {self.config.tool_name} (this may take a minute)...")
        if not installer.install(verbose=self.verbose):
            raise RuntimeError(
                f"Failed to install {self.config.tool_name}.\n"
                f"Try installing manually: npm install -g {self.config.npm_package}"
            )

        print(f"✓ {self.config.tool_name} installed successfully")

    def _run_scip_tool(self, repo_path: Path) -> Path:
        """Run SCIP tool to generate index."""
        import subprocess
        import tempfile

        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".scip", delete=False, dir=repo_path
        ) as tmp:
            scip_file = Path(tmp.name)

        # Build command
        cmd = self.config.build_command(repo_path, scip_file)

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")
            print("  (This may take several minutes for large projects...)")

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"{self.config.tool_name} indexing failed:\n{result.stderr}"
                )

            if not scip_file.exists():
                raise RuntimeError(
                    f"{self.config.tool_name} did not generate {scip_file}"
                )

            return scip_file

        except subprocess.TimeoutExpired as e:
            if scip_file.exists():
                scip_file.unlink()
            raise RuntimeError(
                f"{self.config.tool_name} timed out after 10 minutes. "
                "Try indexing a smaller subset of the project."
            ) from e
        except Exception:
            if scip_file.exists():
                scip_file.unlink()
            raise

    def _build_statistics(self, cicada_index: dict, scip_index, verbose: bool) -> dict:
        """Build and print statistics."""
        all_modules = cicada_index.get("modules", {})
        modules_count = len(all_modules)
        functions_count = cicada_index.get("metadata", {}).get("total_functions", 0)

        # Count files vs classes for better reporting
        file_count = sum(1 for name in all_modules.keys() if name.startswith("_file_"))
        class_count = modules_count - file_count

        if verbose:
            if class_count > 0:
                print(
                    f"  Indexed {file_count} files, {class_count} classes, "
                    f"{functions_count} functions"
                )
            else:
                print(f"  Indexed {modules_count} modules, {functions_count} functions")

        return {
            "modules_count": modules_count,
            "functions_count": functions_count,
            "files_indexed": len(scip_index.documents),
            "file_count": file_count,
            "class_count": class_count,
        }

    def _save_index(self, index: dict, output_path: Path):
        """Save index to JSON file."""
        import json

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
```

## Language-Specific Wrappers

### Python Indexer (Refactored)

**File:** `cicada/languages/python/indexer.py`

```python
"""Python repository indexer using SCIP protocol."""

from cicada.languages.scip.indexer import SCIPIndexer, SCIPToolConfig
from cicada.parsing.base_indexer import BaseIndexer


# Python-specific configuration
PYTHON_SCIP_CONFIG = SCIPToolConfig(
    tool_name="scip-python",
    npm_package="@sourcegraph/scip-python",
    language_name="python",
    file_extensions=[".py"],
    excluded_dirs={
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
    },
)


class PythonSCIPIndexer(SCIPIndexer):
    """Index Python repositories using scip-python."""

    def __init__(self, verbose: bool = False):
        """Initialize Python SCIP indexer."""
        super().__init__(config=PYTHON_SCIP_CONFIG, verbose=verbose)
```

**That's it! 6 lines vs 272 lines!**

### TypeScript Indexer (New)

**File:** `cicada/languages/typescript/indexer.py`

```python
"""TypeScript repository indexer using SCIP protocol."""

from cicada.languages.scip.indexer import SCIPIndexer, SCIPToolConfig


# TypeScript-specific configuration
TYPESCRIPT_SCIP_CONFIG = SCIPToolConfig(
    tool_name="scip-typescript",
    npm_package="@sourcegraph/scip-typescript",
    language_name="typescript",
    file_extensions=[".ts", ".tsx"],
    excluded_dirs={
        "node_modules",
        ".git",
        "dist",
        "build",
        ".next",
        "out",
        "coverage",
        ".turbo",
    },
)


class TypeScriptSCIPIndexer(SCIPIndexer):
    """Index TypeScript repositories using scip-typescript."""

    def __init__(self, verbose: bool = False):
        """Initialize TypeScript SCIP indexer."""
        super().__init__(config=TYPESCRIPT_SCIP_CONFIG, verbose=verbose)
```

**6 lines! Adding a new SCIP language is trivial!**

## Generic SCIP Tool Installer

**File:** `cicada/languages/scip/installer.py`

```python
"""Generic installer for SCIP tools."""

import shutil
import subprocess


class SCIPToolInstaller:
    """Generic installer for npm-based SCIP tools."""

    def __init__(self, tool_name: str, npm_package: str):
        """
        Initialize installer.

        Args:
            tool_name: CLI tool name (e.g., "scip-python")
            npm_package: npm package name (e.g., "@sourcegraph/scip-python")
        """
        self.tool_name = tool_name
        self.npm_package = npm_package

    def is_npm_available(self) -> bool:
        """Check if npm is available."""
        return shutil.which("npm") is not None

    def is_installed(self) -> bool:
        """Check if SCIP tool is installed."""
        return shutil.which(self.tool_name) is not None

    def get_version(self) -> str:
        """Get installed tool version."""
        try:
            result = subprocess.run(
                [self.tool_name, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def install(self, verbose: bool = False) -> bool:
        """
        Install SCIP tool via npm.

        Returns:
            True if installation succeeded, False otherwise
        """
        try:
            cmd = ["npm", "install", "-g", self.npm_package]

            if verbose:
                print(f"  Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=not verbose,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            return result.returncode == 0

        except Exception as e:
            if verbose:
                print(f"  Installation error: {e}")
            return False
```

## Migration Plan

1. **Create generic SCIP indexer** (`cicada/languages/scip/indexer.py`)
2. **Create generic installer** (`cicada/languages/scip/installer.py`)
3. **Refactor PythonSCIPIndexer** to use generic base
4. **Update tests** - should still pass with minimal changes
5. **Create TypeScriptSCIPIndexer** using generic base
6. **Delete** `cicada/languages/python/scip_installer.py`
7. **Update TYPESCRIPT_OBJECTIVE.md** with new architecture

## Benefits

✅ **DRY:** Generic logic written once, reused everywhere
✅ **Maintainability:** Bug fixes apply to all SCIP languages
✅ **Extensibility:** Adding new SCIP languages is trivial (6 lines!)
✅ **Testability:** Test generic indexer once, language wrappers are simple
✅ **Consistency:** All SCIP languages behave identically

## Future SCIP Languages

With this architecture, adding any SCIP-supported language is trivial:

- **Go:** `scip-go` (6 lines)
- **Rust:** `scip-rust` (6 lines)
- **Java:** `scip-java` (6 lines)
- **Ruby:** `scip-ruby` (6 lines)
- **C++:** `scip-clang` (6 lines)

Each one is just a config + 1-line wrapper!
