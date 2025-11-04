# SCIP Generic Implementation Plan

**Objective:** Extract generic SCIP indexing logic into a reusable base class to eliminate code duplication and enable trivial addition of new SCIP-supported languages.

**Status:** ⚠️ TDD Suite Complete - Implementation In Progress
**Updated:** 2025-11-03
**Branch:** `feat/language-agnostic`

---

## 🎯 Current Status (Updated After TDD)

### ✅ Completed (2025-11-03)

1. **Comprehensive TDD Test Suite** (89 tests)
   - 70 regular tests driving implementation
   - 19 meta-tests proving language-agnosticism
   - See `SCIP_TDD_FINDINGS.md` for detailed results

2. **Lookup Utilities** (`cicada/utils/index_utils.py`)
   - All 10 lookup functions implemented and tested
   - 19/21 lookup tests passing

3. **Language-Agnostic Validation**
   - 18/19 meta-tests passing (95% success)
   - Proven: Python and TypeScript produce structurally identical outputs
   - No language-specific leakage detected

### 🔄 In Progress

- Call site extraction from SCIP occurrences (24 tests awaiting)
- Formatter API compatibility fixes (7 tests failing)
- Minor bug fixes (language detection, line numbers)

### 📊 Test Results Summary

```
Total Tests:     89 (70 TDD + 19 meta)
Passing:         61 (68%)
Failing/Error:   28 (32% - mostly awaiting call site extraction)
Existing Suite:  1382 passing (no regressions!)
```

### 🎓 Key Learnings from TDD

1. **SCIP layer is 95% language-agnostic** - already works identically for Python/TypeScript
2. **Most infrastructure exists** - converter, reader, schema all working
3. **One major gap:** Call site extraction (not yet implemented)
4. **Minor issues:** Language detection bug, formatter API mismatch, line number off-by-one

### 📋 Updated Implementation Priority

**REVISED PLAN:**
Focus on completing features identified by tests rather than full indexer refactor.

**Phase 0:** Fix Critical Issues (4-6 hours)
- Implement call site extraction ⚠️ HIGH PRIORITY
- Fix language detection bug
- Fix formatter compatibility

**Phase 1:** Generic Indexer Refactor (8-12 hours)
- Original plan still valid
- Can proceed after Phase 0 complete

---

## Overview

Currently, `PythonSCIPIndexer` contains 272 lines of code, most of which is generic SCIP logic that would need to be copy-pasted for each new language (TypeScript, Go, Rust, Java, etc.).

**Goal:** Extract ~200 lines of generic logic into `cicada/languages/scip/indexer.py`, reducing language wrappers to 6-20 lines of pure configuration.

**Benefits:**
- **DRY:** Generic logic written once, reused everywhere
- **Consistency:** All SCIP languages behave identically
- **Maintainability:** Bug fixes apply to all languages automatically
- **Extensibility:** New SCIP languages become trivial (6 lines of code)

---

## Phase 0: Critical Fixes (Identified by TDD)

**Priority:** HIGH - Must complete before generic refactor
**Estimated Time:** 4-6 hours
**Tests Awaiting:** 28 tests (24 errors + 4 failures)

### Step 0.1: Implement Call Site Extraction

**Status:** ⚠️ NOT IMPLEMENTED
**Impact:** HIGH - 24 tests failing/erroring
**File:** `cicada/languages/scip/converter.py`
**Estimated Time:** 4 hours

**Current Issue:**
The SCIP converter doesn't extract call sites from SCIP occurrences. The data exists in the `.scip` file but isn't being processed.

**SCIP Provides:**
```python
for occurrence in document.occurrences:
    if occurrence.symbol_roles & scip_pb2.SymbolRole.ReadAccess:  # 0x8
        # This is a call site!
        caller_line = occurrence.range[0]
        callee_symbol = occurrence.symbol
```

**Implementation Required:**
```python
class SCIPConverter:
    def __init__(self, extract_keywords=False, keyword_extractor=None,
                 extract_references=True, verbose=False):  # ADD extract_references
        self.extract_references = extract_references

    def _extract_call_sites(self, doc: scip_pb2.Document) -> dict[str, list[dict]]:
        """Extract call sites from SCIP occurrences.

        Returns:
            Dict mapping function symbol → list of call site dicts
            Each call site: {
                "callee": str,        # Symbol being called
                "caller_file": str,   # File containing the call
                "caller_line": int,   # Line number of call
            }
        """
        call_sites = {}

        for occurrence in doc.occurrences:
            # Check if this is a read/call (not definition)
            if occurrence.symbol_roles & scip_pb2.SymbolRole.ReadAccess:
                symbol = occurrence.symbol
                line = occurrence.range[0] if occurrence.range else 0

                # Find which function this call is inside
                caller_function = self._find_enclosing_function(doc, line)

                if caller_function:
                    call_sites.setdefault(caller_function, []).append({
                        "callee": symbol,
                        "file": doc.relative_path,
                        "line": line,
                    })

        return call_sites

    def _find_enclosing_function(self, doc: scip_pb2.Document, line: int) -> str | None:
        """Find which function contains the given line."""
        # Find function definition that encloses this line
        # Return function symbol
```

**Integration:**
```python
def convert(self, scip_index, repo_path):
    # ... existing code ...

    if self.extract_references:
        call_sites = self._extract_call_sites(doc)

        # Add call sites to function dicts
        for func_data in module_dict["functions"]:
            func_symbol = func_data.get("symbol")  # Need to track symbols
            if func_symbol in call_sites:
                func_data["calls"] = call_sites[func_symbol]
```

**Tests That Will Pass:**
- `test_extract_call_sites_from_occurrences()`
- `test_call_site_includes_caller_location()`
- `test_call_site_includes_callee_name()`
- And 21 more reference tests

**Acceptance Criteria:**
- [ ] `_extract_call_sites()` method implemented
- [ ] `_find_enclosing_function()` helper implemented
- [ ] `calls` field populated in function dictionaries
- [ ] 24 reference tests pass

---

### Step 0.2: Fix Language Detection Bug

**Status:** ⚠️ BUG
**Impact:** MEDIUM - 1 meta-test failing
**File:** `cicada/languages/scip/converter.py`
**Estimated Time:** 30 minutes

**Current Issue:**
TypeScript indexes show `language: "python"` in metadata instead of `"typescript"`.

**Root Cause:**
Converter hardcodes language or doesn't extract from SCIP metadata.

**Current Code:**
```python
metadata = {
    "language": "python",  # ← HARDCODED!
    # ...
}
```

**Fix:**
```python
def convert(self, scip_index, repo_path):
    # Extract language from SCIP metadata
    language = self._detect_language(scip_index)

    metadata = {
        "language": language,
        # ...
    }

def _detect_language(self, scip_index) -> str:
    """Detect language from SCIP metadata."""
    # Option 1: Parse from project_root
    if hasattr(scip_index, "metadata") and scip_index.metadata:
        root = scip_index.metadata.project_root
        # Extract language from path or tool info

    # Option 2: Check documents[0].language field
    if scip_index.documents:
        return scip_index.documents[0].language

    return "unknown"
```

**Tests That Will Pass:**
- `test_metadata_structure_identical()` (meta-test)

**Acceptance Criteria:**
- [ ] Language extracted from SCIP metadata
- [ ] TypeScript shows `language: "typescript"`
- [ ] Python shows `language: "python"`
- [ ] Meta-test passes (19/19)

---

### Step 0.3: Fix Formatter API Compatibility

**Status:** ⚠️ API MISMATCH
**Impact:** MEDIUM - 7 formatting tests failing
**File:** `cicada/format/formatter.py` OR test files
**Estimated Time:** 1 hour

**Current Issue:**
Tests expect `formatter.format_module()` but actual API is `format_module_json()` or similar.

**Investigation Needed:**
```bash
# Check actual ModuleFormatter API
grep -n "class ModuleFormatter" cicada/format/formatter.py
grep -n "def format" cicada/format/formatter.py
```

**Solution Option A:** Add missing method
```python
class ModuleFormatter:
    def format_module(self, module_name: str, module_data: dict) -> str:
        """Format module as markdown text."""
        # Implementation
```

**Solution Option B:** Update tests to use correct API
```python
# In tests
output = formatter.format_module_json(module_name, module_data)
# OR
output = formatter.format_markdown(module_name, module_data)
```

**Tests That Will Pass:**
- `test_module_formatter_with_scip_data()`
- `test_markdown_output_complete()`
- And 5 more formatting tests

**Acceptance Criteria:**
- [ ] Formatter API matches test expectations
- [ ] 7 formatting tests pass
- [ ] SCIP data formats correctly

---

### Step 0.4: Fix Minor Bugs

**Status:** ⚠️ BUGS
**Impact:** LOW - 2-3 tests failing
**Estimated Time:** 1 hour

#### Bug A: Line Number Off-by-One
**Test:** `test_index_includes_line_numbers()`
**Issue:** Calculator class shows line 6 instead of expected line 7

**Possible Fix:**
```python
def _get_definition_line(self, symbol: str, doc: scip_pb2.Document) -> int:
    for occurrence in doc.occurrences:
        if occurrence.symbol == symbol and (
            occurrence.symbol_roles & scip_pb2.SymbolRole.Definition
        ):
            # Check if SCIP uses 0-indexed lines
            line = occurrence.range[0] if occurrence.range else 0
            return line + 1  # Convert to 1-indexed?
```

#### Bug B: Location Lookup
**Test:** `test_lookup_by_location()`
**Issue:** Reverse lookup not finding symbols at correct line

**Fix:** Adjust line matching in `lookup_by_location()` utility

**Acceptance Criteria:**
- [ ] Line numbers match source file (1-indexed)
- [ ] Location lookup finds correct symbols
- [ ] 2-3 integration tests pass

---

## Phase 1: Create Generic SCIP Infrastructure

### Step 1.1: Create `SCIPToolConfig` dataclass

**File:** `cicada/languages/scip/indexer.py` (new)

**Implementation:**

```python
"""Generic SCIP-based indexer for any language."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SCIPToolConfig:
    """Configuration for a SCIP tool.

    This dataclass encapsulates all language-specific configuration needed
    to run a SCIP indexer. Each language (Python, TypeScript, Go, etc.)
    provides its own config instance.
    """

    tool_name: str              # CLI command name (e.g., "scip-python")
    npm_package: str            # npm package to install (e.g., "@sourcegraph/scip-python")
    language_name: str          # Language identifier (e.g., "python", "typescript")
    file_extensions: list[str]  # File extensions (e.g., [".py"], [".ts", ".tsx"])
    excluded_dirs: set[str]     # Directories to exclude (e.g., {"node_modules", "dist"})

    def build_command(self, repo_path: Path, output_file: Path) -> list[str]:
        """Build the command to run the SCIP tool.

        Default implementation works for most SCIP tools. Override in
        subclass if a language needs custom command structure.

        Args:
            repo_path: Path to repository root
            output_file: Path where .scip file should be written

        Returns:
            Command and arguments as list of strings
        """
        return [
            self.tool_name,
            "index",
            str(repo_path),
            "--project-name",
            repo_path.name,
            "--output",
            str(output_file),
        ]
```

**Why this design:**
- Separates configuration from logic
- Easy to extend with custom command builders
- Clear documentation of what each field means
- Type hints for better IDE support

**Acceptance Criteria:**
- [ ] `SCIPToolConfig` dataclass created with all required fields
- [ ] `build_command()` method with sensible defaults
- [ ] Docstrings explain each field's purpose
- [ ] Type hints are comprehensive

---

### Step 1.2: Create `SCIPIndexer` base class

**File:** `cicada/languages/scip/indexer.py` (continue in same file)

**Implementation:** Extract from `PythonSCIPIndexer` lines 58-164 (generic SCIP pipeline)

**Key methods:**

```python
class SCIPIndexer(BaseIndexer):
    """Generic indexer for SCIP-based languages.

    This class implements the complete SCIP indexing pipeline:
    1. Ensure SCIP tool is installed (auto-install if needed)
    2. Run SCIP tool to generate .scip file
    3. Read .scip file using SCIPReader
    4. Convert to Cicada format using SCIPConverter
    5. Save index to disk
    6. Report statistics
    7. Cleanup temporary files

    Language-specific indexers inherit from this class and provide
    a SCIPToolConfig instance with their specific settings.
    """

    def __init__(self, config: SCIPToolConfig, verbose: bool = False):
        """Initialize SCIP indexer.

        Args:
            config: Language-specific SCIP tool configuration
            verbose: If True, print detailed progress information
        """
        self.config = config
        self.verbose = verbose

    def get_language_name(self) -> str:
        """Return language identifier."""
        return self.config.language_name

    def get_file_extensions(self) -> list[str]:
        """Return file extensions for this language."""
        return self.config.file_extensions

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.config.excluded_dirs)

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """Index repository using SCIP tool.

        This is the main entry point for SCIP-based indexing.
        The pipeline is completely generic and works for any SCIP language.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            force: If True, reindex even if up-to-date (MVP: always reindex)
            verbose: If True, print detailed progress
            config_path: Optional config file (MVP: unused)

        Returns:
            Dict with indexing results:
                - success: bool
                - modules_count: int
                - functions_count: int
                - files_indexed: int
                - errors: list[str]
        """
        # Implementation extracted from PythonSCIPIndexer
        # See SCIP_REFACTOR_PLAN.md for detailed pseudocode

    def _ensure_tool_installed(self):
        """Ensure SCIP tool is installed, auto-install if needed."""
        # Uses generic SCIPToolInstaller

    def _run_scip_tool(self, repo_path: Path) -> Path:
        """Run SCIP tool to generate .scip index."""
        # Generic implementation using config.build_command()

    def _build_statistics(self, cicada_index: dict, scip_index, verbose: bool) -> dict:
        """Build and print statistics."""
        # Extracted from PythonSCIPIndexer

    def _save_index(self, index: dict, output_path: Path):
        """Save index to JSON file."""
        # Extracted from PythonSCIPIndexer
```

**Source for extraction:** `cicada/languages/python/indexer.py` lines 58-272

**What to extract:**
1. `index_repository()` method (lines 58-164)
2. `_ensure_scip_python_installed()` → `_ensure_tool_installed()` (lines 165-196)
3. `_run_scip_python()` → `_run_scip_tool()` (lines 198-258)
4. `_save_index()` method (lines 260-271)
5. Statistics building logic (lines 122-136) → `_build_statistics()`

**What to make generic:**
- Replace `scip-python` with `self.config.tool_name`
- Replace `@sourcegraph/scip-python` with `self.config.npm_package`
- Replace `"python"` with `self.config.language_name`
- Use `self.config.build_command()` instead of hardcoded command

**Acceptance Criteria:**
- [ ] `SCIPIndexer` class created inheriting from `BaseIndexer`
- [ ] All abstract methods from `BaseIndexer` implemented
- [ ] Generic `index_repository()` pipeline working
- [ ] Tool installation handled generically
- [ ] SCIP execution handled generically
- [ ] Statistics and reporting handled generically
- [ ] No language-specific logic remains

---

### Step 1.3: Create `SCIPToolInstaller` class

**File:** `cicada/languages/scip/installer.py` (new)

**Implementation:** Extract from `cicada/languages/python/scip_installer.py`

```python
"""Generic installer for npm-based SCIP tools."""

import shutil
import subprocess


class SCIPToolInstaller:
    """Generic installer for npm-based SCIP tools.

    All SCIP tools (scip-python, scip-typescript, scip-go, etc.) are
    distributed via npm. This class provides a generic installation
    mechanism that works for all of them.
    """

    def __init__(self, tool_name: str, npm_package: str):
        """Initialize installer.

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
        """Install SCIP tool via npm.

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

**Source:** `cicada/languages/python/scip_installer.py` (make generic)

**What to change:**
- Replace `SCIPPythonInstaller` → `SCIPToolInstaller`
- Remove hardcoded `scip-python` and `@sourcegraph/scip-python`
- Accept tool name and package as constructor parameters
- Remove `@staticmethod` decorators, use instance methods

**Acceptance Criteria:**
- [ ] `SCIPToolInstaller` class created
- [ ] All methods from `SCIPPythonInstaller` ported and made generic
- [ ] Constructor accepts `tool_name` and `npm_package` parameters
- [ ] No language-specific logic remains
- [ ] Comprehensive docstrings added

---

## Phase 2: Refactor Python to Use Generic Base

### Step 2.1: Update `PythonSCIPIndexer` to inherit from `SCIPIndexer`

**File:** `cicada/languages/python/indexer.py`

**Current:** 272 lines of code
**Target:** ~20 lines of configuration + wrapper

**Implementation:**

```python
"""Python repository indexer using SCIP protocol."""

from cicada.languages.scip.indexer import SCIPIndexer, SCIPToolConfig


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
    """Index Python repositories using scip-python.

    This is a thin wrapper around the generic SCIPIndexer that provides
    Python-specific configuration. All indexing logic is inherited from
    the base class.
    """

    def __init__(self, verbose: bool = False):
        """Initialize Python SCIP indexer.

        Args:
            verbose: If True, print detailed progress information
        """
        super().__init__(config=PYTHON_SCIP_CONFIG, verbose=verbose)
```

**Changes:**
1. Replace entire file contents (272 lines → 20 lines)
2. Import `SCIPIndexer` and `SCIPToolConfig`
3. Define `PYTHON_SCIP_CONFIG` with Python-specific settings
4. Make `PythonSCIPIndexer` inherit from `SCIPIndexer`
5. Constructor just calls `super().__init__()`

**Acceptance Criteria:**
- [ ] File reduced from 272 to ~20 lines
- [ ] All functionality preserved (behavior unchanged)
- [ ] No duplication of generic SCIP logic
- [ ] Clear separation of config vs logic

---

### Step 2.2: Delete `cicada/languages/python/scip_installer.py`

**Rationale:** Replaced by generic `SCIPToolInstaller`

**Steps:**
1. Verify no other files import from `scip_installer.py`
2. Delete the file
3. Update any imports if needed

**Acceptance Criteria:**
- [ ] File deleted
- [ ] No broken imports
- [ ] All tests still pass

---

### Step 2.3: Update imports in `cicada/commands.py`

**File:** `cicada/commands.py`

**Current import:**
```python
from cicada.languages.python.indexer import PythonSCIPIndexer
```

**No change needed** - `PythonSCIPIndexer` is still exported from the same module

**Acceptance Criteria:**
- [ ] Imports still work correctly
- [ ] `PythonSCIPIndexer` can be instantiated as before

---

## Phase 3: Testing

### Step 3.1: Verify existing Python tests pass

**Files to test:**
- `tests/languages/python/test_python_support.py` (if exists)
- `tests/test_cli.py` (language detection tests)
- `tests/languages/scip/test_scip_converter.py`

**Command:**
```bash
uv run pytest tests/languages/python/ tests/test_cli.py -v
```

**Expected:** All tests pass with no modifications

**If tests fail:**
1. Check if test was testing implementation details (bad)
2. Fix test to test behavior instead
3. Or fix implementation if behavior actually changed

**Acceptance Criteria:**
- [ ] All existing Python indexer tests pass
- [ ] No test modifications required (tests test behavior, not implementation)
- [ ] Coverage remains at or above 80%

---

### Step 3.2: Add tests for generic `SCIPIndexer`

**File:** `tests/languages/scip/test_scip_indexer.py` (new)

**Test cases:**

```python
"""Tests for generic SCIPIndexer base class."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cicada.languages.scip.indexer import SCIPIndexer, SCIPToolConfig


class TestSCIPToolConfig:
    """Test SCIPToolConfig dataclass."""

    def test_config_creation(self):
        """Should create config with all required fields"""
        config = SCIPToolConfig(
            tool_name="scip-test",
            npm_package="@sourcegraph/scip-test",
            language_name="test",
            file_extensions=[".test"],
            excluded_dirs={"node_modules"},
        )
        assert config.tool_name == "scip-test"
        assert config.npm_package == "@sourcegraph/scip-test"

    def test_build_command_default(self, tmp_path):
        """Should build correct default command"""
        config = SCIPToolConfig(
            tool_name="scip-test",
            npm_package="@sourcegraph/scip-test",
            language_name="test",
            file_extensions=[".test"],
            excluded_dirs=set(),
        )

        output_file = tmp_path / "index.scip"
        cmd = config.build_command(tmp_path, output_file)

        assert cmd[0] == "scip-test"
        assert cmd[1] == "index"
        assert str(tmp_path) in cmd
        assert str(output_file) in cmd


class TestSCIPIndexer:
    """Test generic SCIPIndexer base class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock SCIP config for testing"""
        return SCIPToolConfig(
            tool_name="scip-test",
            npm_package="@sourcegraph/scip-test",
            language_name="test",
            file_extensions=[".test"],
            excluded_dirs={"node_modules"},
        )

    def test_get_language_name(self, mock_config):
        """Should return language name from config"""
        indexer = SCIPIndexer(config=mock_config, verbose=False)
        assert indexer.get_language_name() == "test"

    def test_get_file_extensions(self, mock_config):
        """Should return file extensions from config"""
        indexer = SCIPIndexer(config=mock_config, verbose=False)
        assert indexer.get_file_extensions() == [".test"]

    def test_get_excluded_dirs(self, mock_config):
        """Should return excluded dirs from config"""
        indexer = SCIPIndexer(config=mock_config, verbose=False)
        assert "node_modules" in indexer.get_excluded_dirs()

    def test_index_repository_full_pipeline(self, tmp_path, mock_config):
        """Should execute full SCIP indexing pipeline"""
        # This is an integration-style test
        # Mock out the SCIP tool itself, but test the pipeline

        with (
            patch.object(SCIPIndexer, "_ensure_tool_installed"),
            patch.object(SCIPIndexer, "_run_scip_tool") as mock_run,
            patch("cicada.languages.scip.reader.SCIPReader") as mock_reader,
            patch("cicada.languages.scip.converter.SCIPConverter") as mock_converter,
        ):
            # Setup mocks
            scip_file = tmp_path / "test.scip"
            scip_file.write_text("mock scip data")
            mock_run.return_value = scip_file

            mock_scip_index = MagicMock()
            mock_scip_index.documents = ["file1.test", "file2.test"]
            mock_reader.return_value.read_index.return_value = mock_scip_index

            mock_cicada_index = {
                "modules": {"Module1": {}, "Module2": {}},
                "metadata": {"total_functions": 10},
            }
            mock_converter.return_value.convert.return_value = mock_cicada_index

            # Execute
            indexer = SCIPIndexer(config=mock_config, verbose=False)
            output_path = tmp_path / "index.json"
            result = indexer.index_repository(
                repo_path=tmp_path,
                output_path=output_path,
            )

            # Verify
            assert result["success"] is True
            assert result["modules_count"] == 2
            assert result["functions_count"] == 10
            assert output_path.exists()
```

**Acceptance Criteria:**
- [ ] Test file created with comprehensive test cases
- [ ] Tests verify generic behavior (not language-specific)
- [ ] Tests use mocking appropriately
- [ ] All tests pass
- [ ] Coverage of `scip/indexer.py` is >90%

---

### Step 3.3: Add tests for `SCIPToolInstaller`

**File:** `tests/languages/scip/test_scip_installer.py` (new)

**Test cases:**

```python
"""Tests for generic SCIPToolInstaller."""

import pytest
from unittest.mock import patch, MagicMock
from cicada.languages.scip.installer import SCIPToolInstaller


class TestSCIPToolInstaller:
    """Test generic SCIP tool installer."""

    def test_is_npm_available_true(self):
        """Should detect when npm is available"""
        with patch("shutil.which", return_value="/usr/bin/npm"):
            installer = SCIPToolInstaller("scip-test", "@sourcegraph/scip-test")
            assert installer.is_npm_available() is True

    def test_is_npm_available_false(self):
        """Should detect when npm is not available"""
        with patch("shutil.which", return_value=None):
            installer = SCIPToolInstaller("scip-test", "@sourcegraph/scip-test")
            assert installer.is_npm_available() is False

    def test_is_installed_true(self):
        """Should detect when tool is installed"""
        with patch("shutil.which", return_value="/usr/local/bin/scip-test"):
            installer = SCIPToolInstaller("scip-test", "@sourcegraph/scip-test")
            assert installer.is_installed() is True

    def test_is_installed_false(self):
        """Should detect when tool is not installed"""
        with patch("shutil.which", return_value=None):
            installer = SCIPToolInstaller("scip-test", "@sourcegraph/scip-test")
            assert installer.is_installed() is False

    def test_install_success(self):
        """Should successfully install tool via npm"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            installer = SCIPToolInstaller("scip-test", "@sourcegraph/scip-test")
            success = installer.install(verbose=False)

            assert success is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["npm", "install", "-g", "@sourcegraph/scip-test"]

    def test_install_failure(self):
        """Should handle installation failure"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            installer = SCIPToolInstaller("scip-test", "@sourcegraph/scip-test")
            success = installer.install(verbose=False)

            assert success is False
```

**Acceptance Criteria:**
- [ ] Test file created with comprehensive test cases
- [ ] Tests cover success and failure paths
- [ ] All tests pass
- [ ] Coverage of `scip/installer.py` is >90%

---

## Phase 4: Documentation

### Step 4.1: Update `SCIP_REFACTOR_PLAN.md`

**Changes:**
- Add "IMPLEMENTED" status marker at top
- Add "See SCIP_IMPLEMENTATION_PLAN.md for execution details" note
- Keep as reference documentation

**Acceptance Criteria:**
- [ ] Status updated to reflect completion
- [ ] Cross-reference to implementation plan added

---

### Step 4.2: Update `TYPESCRIPT_OBJECTIVE.md`

**Changes:**
- Update Phase 0 checklist to mark items as complete
- Update Phase 1 to reflect that prerequisites are done
- Adjust timeline estimates (remove Phase 0 time)

**Acceptance Criteria:**
- [ ] Checklist updated
- [ ] Timeline reflects current status
- [ ] Prerequisites section updated

---

### Step 4.3: Add docstring to `SCIPIndexer`

**Requirements:**
- Explain the purpose of the generic indexer
- Document the SCIP indexing pipeline
- Provide example of creating a language wrapper
- Link to UNIVERSAL_SCIP.md for architecture overview

**Example:**

```python
class SCIPIndexer(BaseIndexer):
    """Generic indexer for SCIP-based languages.

    This class implements a universal SCIP indexing pipeline that works for
    ANY language with a SCIP indexer (Python, TypeScript, Go, Rust, Java, etc.).

    The indexing pipeline:
        1. Ensure SCIP tool is installed (auto-install via npm if needed)
        2. Run SCIP tool to generate .scip file
        3. Read .scip protobuf file
        4. Convert to Cicada index format
        5. Save index to disk
        6. Report statistics
        7. Cleanup temporary files

    Adding a New Language
    ---------------------
    To add support for a new SCIP language, create a thin wrapper:

        from cicada.languages.scip.indexer import SCIPIndexer, SCIPToolConfig

        GO_CONFIG = SCIPToolConfig(
            tool_name="scip-go",
            npm_package="@sourcegraph/scip-go",
            language_name="go",
            file_extensions=[".go"],
            excluded_dirs={"vendor", "bin"},
        )

        class GoSCIPIndexer(SCIPIndexer):
            def __init__(self, verbose: bool = False):
                super().__init__(config=GO_CONFIG, verbose=verbose)

    That's it! No SCIP logic needs to be duplicated.

    See Also
    --------
    - UNIVERSAL_SCIP.md: Architecture overview
    - SCIP_REFACTOR_PLAN.md: Refactoring rationale
    - SCIPToolConfig: Language-specific configuration
    """
```

**Acceptance Criteria:**
- [ ] Comprehensive docstring added
- [ ] Pipeline steps documented
- [ ] Example of creating language wrapper included
- [ ] Cross-references to architecture docs

---

## Phase 5: Validation

### Step 5.1: Run full test suite

**Command:**
```bash
make test
```

**Expected:** All 1343+ tests pass

**If tests fail:**
1. Identify which test failed
2. Determine if test is testing implementation (bad) or behavior (good)
3. Fix implementation or update test as appropriate
4. Re-run tests

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] Coverage remains ≥80%
- [ ] No new warnings or errors

---

### Step 5.2: Test with real Python project (dogfooding)

**Test:** Index cicada itself

```bash
cd /Users/wende/projects/cicada2
cicada clean -f
cicada index --nlp  # Should use PythonSCIPIndexer
```

**Expected Output:**
```
Indexing python repository: /Users/wende/projects/cicada2
  Using scip-python 0.3.5
  Running: scip-python index /Users/wende/projects/cicada2 ...
  (This may take several minutes for large projects...)
  SCIP index: 76 documents, 3456 symbols
  Indexed 76 files, 230 classes, 1899 functions
  Index saved to: ~/.cicada/projects/<hash>/index.json
  Cleaned up temporary file: tmp*.scip
```

**Verification:**
```bash
# Verify index was created
ls -lh ~/.cicada/projects/*/index.json

# Verify searches work
cicada search create_storage_dir

# Verify module lookup works
cicada module cicada.utils.storage
```

**Acceptance Criteria:**
- [ ] Indexing completes successfully
- [ ] Output matches expected format
- [ ] Index file created at correct location
- [ ] MCP searches work correctly
- [ ] No errors or warnings

---

### Step 5.3: Verify code reduction

**Measurement:**

```bash
# Before refactor
wc -l cicada/languages/python/indexer.py
# Expected: 272 lines

# After refactor
wc -l cicada/languages/python/indexer.py
# Expected: ~20 lines

wc -l cicada/languages/scip/indexer.py
# Expected: ~200 lines

wc -l cicada/languages/scip/installer.py
# Expected: ~50 lines
```

**Math:**
- Before: 272 lines (Python only)
- After: 20 (Python wrapper) + 200 (generic base) + 50 (generic installer) = 270 lines
- **Net:** ~Same lines for Python, but future languages are 6 lines instead of 272!

**For 5 SCIP languages (Python, TypeScript, Go, Rust, Java):**
- Without refactor: 272 × 5 = **1,360 lines**
- With refactor: 250 (generic) + 20 + 6 + 6 + 6 + 6 = **294 lines**
- **Savings: 78% code reduction**

**Acceptance Criteria:**
- [ ] Python indexer reduced from 272 to ~20 lines
- [ ] Generic infrastructure totals ~250 lines
- [ ] Overall architecture enables 78% code reduction at scale

---

## Success Criteria

The refactor is complete when:

- [x] Phase 1: Generic infrastructure created
  - [ ] `SCIPToolConfig` dataclass implemented
  - [ ] `SCIPIndexer` base class implemented
  - [ ] `SCIPToolInstaller` class implemented

- [x] Phase 2: Python refactored to use generic base
  - [ ] `PythonSCIPIndexer` reduced to ~20 lines
  - [ ] `scip_installer.py` deleted
  - [ ] All functionality preserved

- [x] Phase 3: Tests pass
  - [ ] All existing tests pass
  - [ ] New tests for `SCIPIndexer` added
  - [ ] New tests for `SCIPToolInstaller` added
  - [ ] Coverage ≥80%

- [x] Phase 4: Documentation updated
  - [ ] `SCIP_REFACTOR_PLAN.md` marked as implemented
  - [ ] `TYPESCRIPT_OBJECTIVE.md` updated
  - [ ] Comprehensive docstrings added

- [x] Phase 5: Validation complete
  - [ ] Full test suite passes (1343+ tests)
  - [ ] Dogfooding on cicada codebase works
  - [ ] Code reduction verified (78% for 5 languages)

---

## Risk Mitigation

### Risk: Tests break during refactor

**Mitigation:**
1. Work in feature branch (`feat/generic-scip-indexer`)
2. Run tests after each phase
3. If tests fail, fix immediately before proceeding
4. Use git to revert if needed

### Risk: Behavior changes unintentionally

**Mitigation:**
1. Extract logic exactly as-is first (no improvements)
2. Make it generic second
3. Run before/after comparison tests
4. Verify output format unchanged

### Risk: Performance regression

**Mitigation:**
1. No algorithmic changes, just refactoring
2. If anything, slight improvement (less object creation)
3. Measure indexing time before/after on cicada codebase

### Risk: Import issues

**Mitigation:**
1. Keep `PythonSCIPIndexer` in same module path
2. Add explicit `__init__.py` exports if needed
3. Test imports in isolation

---

## Timeline

**Total Estimate: 8-12 hours**

| Phase | Task | Time | Running Total |
|-------|------|------|---------------|
| 1.1 | Create `SCIPToolConfig` | 1h | 1h |
| 1.2 | Create `SCIPIndexer` | 3h | 4h |
| 1.3 | Create `SCIPToolInstaller` | 1h | 5h |
| 2.1 | Refactor `PythonSCIPIndexer` | 1h | 6h |
| 2.2 | Delete `scip_installer.py` | 15min | 6.25h |
| 2.3 | Update imports | 15min | 6.5h |
| 3.1 | Verify existing tests | 30min | 7h |
| 3.2 | Add `SCIPIndexer` tests | 2h | 9h |
| 3.3 | Add `SCIPToolInstaller` tests | 1h | 10h |
| 4 | Documentation | 1h | 11h |
| 5 | Validation | 1h | 12h |

**Best case:** 8 hours (no major issues)
**Expected:** 10 hours (minor issues during refactor)
**Worst case:** 12 hours (test failures require investigation)

---

## Next Steps

After this refactor is complete:

1. **TypeScript Integration (Phase 1 of TYPESCRIPT_OBJECTIVE.md)**
   - Estimated: 5 hours
   - Just 6 lines of code thanks to this refactor!

2. **Future Languages (trivial)**
   - Go: 6 lines, 1 hour
   - Rust: 6 lines, 1 hour
   - Java: 6 lines, 1 hour

The refactor is the **unlock** - everything after this is trivial.

---

## References

- **Architecture Docs:**
  - `UNIVERSAL_SCIP.md` - Big picture explanation
  - `SCIP_REFACTOR_PLAN.md` - Technical design
  - `TYPESCRIPT_OBJECTIVE.md` - TypeScript roadmap

- **Source Code:**
  - `cicada/languages/python/indexer.py` - Current implementation (to extract from)
  - `cicada/languages/python/scip_installer.py` - Current installer (to extract from)
  - `cicada/languages/scip/converter.py` - Already generic SCIP converter
  - `cicada/languages/scip/reader.py` - Already generic SCIP reader

- **Tests:**
  - `tests/languages/python/test_python_support.py` - Existing Python tests
  - `tests/languages/scip/test_scip_converter.py` - SCIP converter tests
  - `tests/test_cli.py` - CLI integration tests
