# Python SCIP Support Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding Python language support to Cicada using the SCIP (Code Intelligence Protocol). This will enable type-aware code navigation, documentation extraction, and reference tracking for Python projects through the existing MCP server infrastructure.

## Background

### Current State
- Cicada currently supports Elixir via tree-sitter-based static analysis
- Language-agnostic architecture with `BaseParser` and `BaseIndexer` abstractions
- Universal index schema (`UniversalIndexSchema`) that supports any language
- MCP server exposes code search tools to AI assistants

### Why SCIP for Python?
- **Type-aware navigation**: Leverages Pyright's type checking for accurate references
- **Mature tooling**: scip-python is production-ready from Sourcegraph
- **Cross-repository support**: Stable symbol identifiers for library code
- **Language-agnostic protocol**: Same approach can extend to TypeScript, Rust, Go
- **Better than tree-sitter**: Python's dynamic typing benefits from semantic analysis

## Technical Architecture

### SCIP Protocol Overview
- **Format**: Protocol Buffer (binary)
- **File Extension**: `.scip`
- **Official Spec**: https://github.com/sourcegraph/scip/blob/main/scip.proto
- **Created by**: Sourcegraph (replacement for LSIF)
- **Performance**: 4x smaller, 10x faster than LSIF

### Data Structure Mapping

| SCIP Concept | Cicada Schema | Implementation Notes |
|--------------|---------------|---------------------|
| `Document` | Module file | One-to-one mapping |
| `SymbolInformation` (class) | `ModuleData` | Class treated as module |
| `SymbolInformation` (function) | `FunctionData` | Direct mapping |
| `documentation` | `doc`/`moduledoc` | Markdown format preserved |
| `signature_documentation` | `signature` | Function signature with types |
| `Occurrence` (Definition) | Function `line` number | SCIP has character-level positions |
| `Occurrence` (Reference) | `calls` array | Call site tracking |
| Symbol relationships | `imports`, `dependencies` | Via SCIP `Relationship` |

### SCIP Symbol Format
```
scip-python python <package> <version> <path>/<symbol>
Example: scip-python python myproject 1.0 mymodule/MyClass#method().
```

Cicada converts to: `MyClass.method/2`

## Implementation Phases

### Phase 1: SCIP Foundation (3-5 days)

#### 1.1 Dependencies
Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing
    "protobuf>=4.0.0",
]

[tool.uv]
dev-dependencies = [
    # ... existing
    "grpcio-tools>=1.50.0",  # For protobuf codegen
]
```

#### 1.2 SCIP Module Structure
Create `cicada/scip/` directory:
```
cicada/scip/
├── __init__.py           # Exports SCIPReader, SCIPConverter
├── scip.proto            # Vendored from sourcegraph/scip
├── scip_pb2.py           # Generated Python bindings
├── reader.py             # SCIPReader class
├── converter.py          # SCIPConverter class
└── symbol_parser.py      # Parse SCIP symbol format
```

#### 1.3 Generate Protobuf Bindings
```bash
# Download proto file
wget -O cicada/scip/scip.proto \
  https://raw.githubusercontent.com/sourcegraph/scip/main/scip.proto

# Generate Python bindings
python -m grpc_tools.protoc \
  -I cicada/scip \
  --python_out=cicada/scip \
  cicada/scip/scip.proto
```

#### 1.4 SCIPReader Implementation
**File**: `cicada/scip/reader.py`

```python
from pathlib import Path
from cicada.scip import scip_pb2

class SCIPReader:
    """Read and parse SCIP index files."""

    def read_index(self, scip_file: Path) -> scip_pb2.Index:
        """
        Load and parse a .scip file.

        Args:
            scip_file: Path to .scip file

        Returns:
            Parsed SCIP Index protobuf message

        Raises:
            FileNotFoundError: If .scip file doesn't exist
            DecodeError: If file is corrupted
        """
        with open(scip_file, 'rb') as f:
            index = scip_pb2.Index()
            index.ParseFromString(f.read())
            return index

    def print_index_summary(self, index: scip_pb2.Index) -> str:
        """Generate human-readable summary of index contents."""
        # For debugging/logging
        pass
```

#### 1.5 SCIP Symbol Parser
**File**: `cicada/scip/symbol_parser.py`

```python
from dataclasses import dataclass

@dataclass
class ParsedSymbol:
    """Parsed SCIP symbol identifier."""
    scheme: str        # e.g., "scip-python"
    package: str       # e.g., "myproject"
    version: str       # e.g., "1.0"
    descriptors: list[str]  # e.g., ["mymodule", "MyClass", "method()"]

    @property
    def module_name(self) -> str:
        """Extract module/class name (e.g., 'MyClass')."""
        # Parse descriptors to extract class/module
        pass

    @property
    def function_name(self) -> str:
        """Extract function name (e.g., 'method')."""
        # Parse descriptors to extract function
        pass

def parse_scip_symbol(symbol: str) -> ParsedSymbol:
    """
    Parse SCIP symbol string into components.

    Example:
        scip-python python myproject 1.0 mymodule/MyClass#method().
        -> ParsedSymbol(scheme='scip-python', package='myproject', ...)
    """
    pass
```

#### 1.6 SCIP → Cicada Converter
**File**: `cicada/scip/converter.py`

```python
from cicada.scip import scip_pb2
from cicada.parsing.schema import UniversalIndexSchema, ModuleData, FunctionData

class SCIPConverter:
    """Convert SCIP Index to Cicada's UniversalIndexSchema."""

    def convert(self, scip_index: scip_pb2.Index, repo_path: Path) -> dict:
        """
        Convert SCIP Index to Cicada index format.

        Args:
            scip_index: Parsed SCIP protobuf
            repo_path: Repository root path

        Returns:
            Dict in UniversalIndexSchema format
        """
        modules = {}

        for doc in scip_index.documents:
            module_data = self._convert_document(doc, repo_path)
            if module_data:
                modules[module_data['name']] = module_data

        metadata = self._build_metadata(scip_index, repo_path)

        return {
            "modules": modules,
            "metadata": metadata
        }

    def _convert_document(self, doc: scip_pb2.Document, repo_path: Path) -> dict:
        """Convert a SCIP Document to ModuleData."""
        # 1. Extract all SymbolInformation for this document
        # 2. Separate classes from functions
        # 3. Build module hierarchy
        # 4. Extract occurrences (definitions, references)
        # 5. Map to ModuleData format
        pass

    def _convert_symbol_info(self, symbol_info: scip_pb2.SymbolInformation) -> dict:
        """Convert SymbolInformation to FunctionData or ModuleData."""
        parsed = parse_scip_symbol(symbol_info.symbol)

        # Determine if class or function
        if symbol_info.kind == scip_pb2.SymbolInformation.Class:
            return self._build_module_data(symbol_info, parsed)
        elif symbol_info.kind == scip_pb2.SymbolInformation.Method:
            return self._build_function_data(symbol_info, parsed)
        # Handle other kinds...

    def _extract_occurrences(self, doc: scip_pb2.Document) -> dict:
        """
        Extract function calls from Occurrence data.

        Returns:
            Dict mapping symbol -> list of call sites
        """
        calls = {}
        for occurrence in doc.occurrences:
            if scip_pb2.SymbolRole.Reference in occurrence.symbol_roles:
                # This is a reference/call site
                calls.setdefault(occurrence.symbol, []).append({
                    'line': occurrence.range.start_line,
                    'character': occurrence.range.start_character
                })
        return calls

    def _build_metadata(self, scip_index: scip_pb2.Index, repo_path: Path) -> dict:
        """Build metadata section of index."""
        return {
            "indexed_at": datetime.now().isoformat(),
            "language": "python",
            "version": "2.0",
            "repo_path": str(repo_path),
            "scip_version": scip_index.metadata.version,
            "tool_info": {
                "name": scip_index.metadata.tool_info.name,
                "version": scip_index.metadata.tool_info.version
            }
        }
```

### Phase 2: Python Indexer (3-4 days)

#### 2.1 Python Module Structure
Create `cicada/languages/python/` directory:
```
cicada/languages/python/
├── __init__.py          # Exports PythonSCIPIndexer
├── indexer.py           # PythonSCIPIndexer class
└── scip_installer.py    # Auto-install scip-python
```

#### 2.2 SCIP-Python Installer
**File**: `cicada/languages/python/scip_installer.py`

```python
import shutil
import subprocess
from pathlib import Path

class SCIPPythonInstaller:
    """Manage scip-python installation."""

    @staticmethod
    def is_npm_available() -> bool:
        """Check if npm is installed."""
        return shutil.which('npm') is not None

    @staticmethod
    def is_scip_python_installed() -> bool:
        """Check if scip-python is installed globally."""
        return shutil.which('scip-python') is not None

    @staticmethod
    def install_scip_python(verbose: bool = False) -> bool:
        """
        Install scip-python via npm.

        Returns:
            True if successful, False otherwise
        """
        if not SCIPPythonInstaller.is_npm_available():
            raise RuntimeError(
                "npm is required to install scip-python. "
                "Install Node.js from https://nodejs.org/"
            )

        cmd = ['npm', 'install', '-g', '@sourcegraph/scip-python']

        if verbose:
            print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error installing scip-python: {result.stderr}")
            return False

        return True

    @staticmethod
    def get_scip_python_version() -> str | None:
        """Get installed scip-python version."""
        if not SCIPPythonInstaller.is_scip_python_installed():
            return None

        result = subprocess.run(
            ['scip-python', '--version'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
```

#### 2.3 Python SCIP Indexer
**File**: `cicada/languages/python/indexer.py`

```python
import subprocess
import tempfile
from pathlib import Path
from cicada.parsing.base_indexer import BaseIndexer
from cicada.scip.reader import SCIPReader
from cicada.scip.converter import SCIPConverter
from cicada.languages.python.scip_installer import SCIPPythonInstaller

class PythonSCIPIndexer(BaseIndexer):
    """Index Python repositories using scip-python."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.excluded_dirs = {
            "__pycache__", ".venv", "venv", ".git",
            "node_modules", ".pytest_cache", ".mypy_cache",
            "dist", "build", ".egg-info", ".tox"
        }

    def get_language_name(self) -> str:
        return "python"

    def get_file_extensions(self) -> list[str]:
        return [".py"]

    def get_excluded_dirs(self) -> list[str]:
        return list(self.excluded_dirs)

    def index_repository(
        self,
        repo_path: Path,
        output_path: Path,
        force: bool = False,
        **kwargs
    ) -> dict:
        """
        Index Python repository using scip-python.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            force: If True, reindex even if up-to-date

        Returns:
            Generated index dict

        Raises:
            RuntimeError: If scip-python not available
        """
        # 1. Ensure scip-python is installed
        self._ensure_scip_python_installed()

        # 2. Run scip-python indexer
        scip_file = self._run_scip_python(repo_path)

        try:
            # 3. Read .scip file
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            # 4. Convert to Cicada format
            converter = SCIPConverter()
            cicada_index = converter.convert(scip_index, repo_path)

            # 5. Add keyword extraction if enabled
            if kwargs.get('extract_keywords'):
                cicada_index = self._add_keywords(cicada_index, kwargs)

            # 6. Save to output path
            self._save_index(cicada_index, output_path)

            if self.verbose:
                print(f"✓ Indexed {len(cicada_index['modules'])} modules")

            return cicada_index

        finally:
            # 7. Cleanup temporary .scip file
            if scip_file.exists():
                scip_file.unlink()

    def _ensure_scip_python_installed(self):
        """Ensure scip-python is installed, auto-install if needed."""
        if SCIPPythonInstaller.is_scip_python_installed():
            if self.verbose:
                version = SCIPPythonInstaller.get_scip_python_version()
                print(f"Using scip-python {version}")
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

        Returns:
            Path to generated .scip file
        """
        # Use temporary file for .scip output
        scip_file = repo_path / "index.scip"

        cmd = [
            'scip-python',
            'index',
            str(repo_path),
            '--project-name', repo_path.name,
            '--output', str(scip_file)
        ]

        if self.verbose:
            print(f"Running: {' '.join(cmd)}")
            print("(This may take several minutes for large projects...)")

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"scip-python indexing failed:\n{result.stderr}"
            )

        if not scip_file.exists():
            raise RuntimeError(
                f"scip-python did not generate {scip_file}"
            )

        return scip_file

    def _add_keywords(self, index: dict, kwargs: dict) -> dict:
        """Add keyword extraction to index."""
        # Use existing keyword extraction infrastructure
        from cicada.lightweight_keyword_extractor import extract_keywords

        for module_name, module_data in index['modules'].items():
            # Extract keywords from module doc
            if module_data.get('moduledoc'):
                module_data['keywords'] = extract_keywords(
                    module_data['moduledoc'],
                    method=kwargs.get('keyword_method', 'lemminflect')
                )

            # Extract keywords from function docs
            for func in module_data.get('functions', []):
                if func.get('doc'):
                    func['keywords'] = extract_keywords(
                        func['doc'],
                        method=kwargs.get('keyword_method', 'lemminflect')
                    )

        return index

    def _save_index(self, index: dict, output_path: Path):
        """Save index to JSON file."""
        import json

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
```

#### 2.4 Register Python Language
**File**: `cicada/languages/__init__.py`

After Elixir registration (around line 187), add:

```python
# Register Python (SCIP-based)
LanguageRegistry.register_language(
    language="python",
    parser_class=None,  # No parser needed for SCIP
    indexer_class="cicada.languages.python.indexer.PythonSCIPIndexer",
    config=LanguageConfig.default_python(),
)
```

### Phase 3: CLI & Setup Integration (2-3 days)

#### 3.1 Language Detection
**File**: `cicada/setup.py`

Add function:

```python
def detect_project_language(repo_path: Path) -> str:
    """
    Detect project language from marker files.

    Args:
        repo_path: Repository root path

    Returns:
        Language name ('elixir' or 'python')

    Raises:
        ValueError: If no recognized project type found
    """
    # Check for Python markers
    python_markers = [
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "Pipfile",
        "poetry.lock"
    ]

    for marker in python_markers:
        if (repo_path / marker).exists():
            return "python"

    # Check for Elixir marker
    if (repo_path / "mix.exs").exists():
        return "elixir"

    # No recognized language
    raise ValueError(
        f"Could not detect project language in {repo_path}\n"
        "Expected Python markers (pyproject.toml, setup.py, etc.) "
        "or Elixir marker (mix.exs)"
    )
```

Update `index_repository()` to use auto-detection:

```python
def index_repository(
    repo_path: Path,
    output_path: Path = None,
    language: str = None,  # Now optional
    **kwargs
) -> dict:
    """Index repository (auto-detect language if not specified)."""

    # Auto-detect language if not provided
    if language is None:
        language = detect_project_language(repo_path)
        print(f"Detected {language} project")

    # Get appropriate indexer
    indexer = LanguageRegistry.get_indexer(language)

    # Run indexing
    return indexer.index_repository(repo_path, output_path, **kwargs)
```

#### 3.2 Update CLI Commands
**File**: `cicada/cli.py`

Update `handle_index()`:

```python
def handle_index(args):
    """Handle 'cicada index' command."""
    from cicada.setup import index_repository, detect_project_language

    repo_path = Path(args.path).resolve()

    # Auto-detect language or use provided
    if args.language:
        language = args.language
    else:
        try:
            language = detect_project_language(repo_path)
            print(f"Detected {language} project")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # Show progress for Python (can be slow)
    if language == "python":
        print("Indexing Python project with scip-python...")
        print("This may take several minutes for large projects.")

    # Run indexing
    index = index_repository(
        repo_path=repo_path,
        language=language,
        verbose=args.verbose,
        extract_keywords=True
    )

    print(f"✓ Indexed {index['metadata']['total_modules']} modules")
    print(f"✓ Indexed {index['metadata']['total_functions']} functions")
```

Add CLI argument:

```python
parser_index = subparsers.add_parser('index', help='Index repository')
parser_index.add_argument('path', nargs='?', default='.', help='Repository path')
parser_index.add_argument('--language', choices=['elixir', 'python'], help='Force language')
parser_index.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
```

#### 3.3 Update Interactive Setup
**File**: `cicada/interactive_setup.py`

Add language detection to setup flow:

```python
def interactive_setup():
    """Interactive setup wizard."""

    # ... existing code ...

    # Detect language
    try:
        language = detect_project_language(repo_path)
        print(f"✓ Detected {language} project")
    except ValueError:
        # Ask user
        language = input("Project language (elixir/python): ").strip().lower()
        if language not in ['elixir', 'python']:
            print("Unsupported language")
            sys.exit(1)

    # Language-specific messages
    if language == "python":
        print("\nPython support requires:")
        print("  • Node.js and npm (for scip-python)")
        print("  • scip-python will be installed automatically")

        if not SCIPPythonInstaller.is_npm_available():
            print("\n⚠ Warning: npm not found")
            print("Install Node.js from: https://nodejs.org/")
            sys.exit(1)

    # ... rest of setup ...
```

### Phase 4: Testing & Documentation (2-3 days)

#### 4.1 Test Fixtures
Create `tests/fixtures/sample_python/`:

```python
# tests/fixtures/sample_python/mymodule.py
"""Sample Python module for testing."""

def public_function(x: int, y: str) -> bool:
    """
    Public function with type hints.

    Args:
        x: Integer parameter
        y: String parameter

    Returns:
        Boolean result
    """
    return len(y) > x

def _private_function():
    """Private function (leading underscore)."""
    pass

class MyClass:
    """Sample class."""

    def method(self, param: str) -> None:
        """Instance method."""
        result = public_function(1, param)
        return result

    @staticmethod
    def static_method():
        """Static method."""
        pass
```

#### 4.2 Unit Tests
**File**: `tests/test_scip_reader.py`

```python
import pytest
from pathlib import Path
from cicada.scip.reader import SCIPReader

def test_read_scip_file():
    """Test reading a .scip file."""
    # Generate test .scip file or use fixture
    pass

def test_invalid_scip_file():
    """Test error handling for corrupted file."""
    pass
```

**File**: `tests/test_scip_converter.py`

```python
import pytest
from cicada.scip.converter import SCIPConverter
from cicada.scip import scip_pb2

def test_convert_document():
    """Test converting SCIP Document to ModuleData."""
    pass

def test_convert_symbol_info():
    """Test converting SymbolInformation to FunctionData."""
    pass

def test_extract_occurrences():
    """Test extracting call references."""
    pass
```

**File**: `tests/test_python_indexer.py`

```python
import pytest
from pathlib import Path
from cicada.languages.python.indexer import PythonSCIPIndexer

@pytest.fixture
def sample_python_repo():
    return Path(__file__).parent / "fixtures" / "sample_python"

def test_index_python_repository(sample_python_repo):
    """Test full Python repository indexing."""
    indexer = PythonSCIPIndexer(verbose=True)

    output = sample_python_repo / ".cicada" / "index.json"
    index = indexer.index_repository(
        repo_path=sample_python_repo,
        output_path=output
    )

    # Verify structure
    assert "modules" in index
    assert "metadata" in index
    assert index["metadata"]["language"] == "python"

    # Verify content
    # ... assertions for expected modules/functions ...

def test_scip_python_not_installed(monkeypatch):
    """Test error handling when scip-python not available."""
    # Mock is_scip_python_installed to return False
    pass
```

#### 4.3 Integration Tests
**File**: `tests/test_python_integration.py`

```python
def test_mcp_tools_with_python_index():
    """Test that MCP tools work with Python index."""
    # Index sample Python project
    # Start MCP server
    # Call search_module, search_function, etc.
    # Verify results
    pass

def test_auto_language_detection():
    """Test automatic Python project detection."""
    pass

def test_cli_index_python():
    """Test 'cicada index' on Python project."""
    pass
```

#### 4.4 Documentation Updates

**Update README.md**:
```markdown
## Supported Languages

- **Elixir**: Tree-sitter based static analysis
- **Python**: SCIP-based type-aware indexing (requires Node.js/npm)

## Python Setup

1. Install Node.js from https://nodejs.org/
2. Run `cicada install` in your Python project
3. cicada will automatically install scip-python
4. Index generation may take several minutes for large projects

## Example Usage

```bash
# Index Python project
cicada index /path/to/python/project

# Or let cicada auto-detect language
cicada install  # Interactive setup
```
```

**Update CLAUDE.md**:
```markdown
## Language Support

### Python (SCIP-based)
- Uses scip-python indexer powered by Pyright
- Type-aware navigation and references
- Requires Node.js/npm (auto-installs scip-python)
- Indexing may be slower than Elixir (minutes vs seconds)
- Supports: classes, methods, functions, docstrings, type hints, imports

### Elixir (Tree-sitter)
- Fast static analysis
- No external dependencies
- Supports: modules, functions, docs, specs, calls
```

**Update MCP Tool Descriptions** (`cicada/mcp_tools.py`):
```python
# Change from:
"PREFERRED for Elixir: View a module's complete API..."

# To:
"PREFERRED for Elixir/Python: View a module's complete API..."
```

Add Python examples to tool descriptions.

## Testing Strategy

### Unit Tests
- SCIP reader/parser functionality
- SCIP → Cicada conversion accuracy
- Symbol format parsing
- Error handling

### Integration Tests
- End-to-end indexing of sample Python projects
- MCP server tools with Python index
- CLI commands with Python projects
- Auto-detection and installation flow

### Manual Testing
- Small project (~10 files)
- Medium project (~100 files)
- Large project (~1000 files)
- Projects with complex inheritance
- Projects with type hints
- Projects without type hints

## Performance Considerations

### Expected Performance (based on scip-python benchmarks)
- Small project (< 100 files): 30-60 seconds
- Medium project (100-1000 files): 2-5 minutes
- Large project (> 1000 files): 5-15 minutes

### Optimization Strategies
1. **Caching**: Store .scip file temporarily for incremental updates
2. **Parallelization**: Run scip-python in background
3. **Progress indicators**: Show status during long operations
4. **Timeout handling**: 10-minute timeout for very large projects
5. **Selective indexing**: Support --target-only flag for subdirectories

## Rollout Plan

### Phase 1: Internal Testing (Week 1-2)
- Implement core SCIP infrastructure
- Test with internal Python projects
- Verify conversion accuracy

### Phase 2: Beta Testing (Week 3)
- Test with popular Python libraries (requests, Flask, Django)
- Gather performance metrics
- Fix bugs and edge cases

### Phase 3: Documentation (Week 4)
- Complete user-facing documentation
- Add troubleshooting guide
- Create video demos

### Phase 4: Release (Week 5)
- Merge to main branch
- Update PyPI package
- Announce Python support

## Future Enhancements

### Short-term (1-2 months)
- Support for other SCIP-enabled languages:
  - TypeScript (scip-typescript)
  - Rust (rust-analyzer SCIP export)
  - Go (scip-go)

### Medium-term (3-6 months)
- Incremental indexing optimization
- Hybrid tree-sitter/SCIP mode (fast fallback)
- Workspace-level indexing (monorepos)
- Custom SCIP indexer configuration

### Long-term (6-12 months)
- IDE integration (LSP server)
- Real-time index updates
- Cross-repository navigation
- Semantic code search improvements

## Success Metrics

### Functionality
- [ ] Python projects can be indexed
- [ ] All MCP tools work with Python
- [ ] Type-aware navigation accuracy > 95%
- [ ] Documentation extraction accuracy > 99%
- [ ] Call reference tracking accuracy > 90%

### Performance
- [ ] Indexing time < 10 minutes for 1000-file projects
- [ ] Memory usage < 2GB for large projects
- [ ] Index size < 5MB per 100 files

### User Experience
- [ ] Auto-detection works reliably
- [ ] Auto-installation succeeds > 95% of time
- [ ] Clear error messages for all failure modes
- [ ] Documentation covers common issues

## Risk Mitigation

### Risk: npm/Node.js not available
**Mitigation**: Clear error message with installation link, check early in setup

### Risk: scip-python installation fails
**Mitigation**: Fallback instructions for manual installation, detailed troubleshooting

### Risk: SCIP indexing times out
**Mitigation**: Configurable timeout, incremental indexing, progress indicators

### Risk: SCIP format changes
**Mitigation**: Vendor scip.proto, version checking, graceful degradation

### Risk: Limited Python version support
**Mitigation**: Document Python 3.10+ requirement, version checking

## References

- SCIP Protocol: https://github.com/sourcegraph/scip
- scip-python: https://github.com/sourcegraph/scip-python
- SCIP Blog Post: https://sourcegraph.com/blog/announcing-scip
- Pyright: https://github.com/microsoft/pyright
- Protocol Buffers: https://developers.google.com/protocol-buffers

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-02 | Use SCIP over tree-sitter | Type-aware navigation is critical for Python |
| 2025-11-02 | Auto-install scip-python | Better UX than manual installation |
| 2025-11-02 | Convert to index.json only | Consistent with current architecture |
| 2025-11-02 | Medium priority implementation | After current work completes |

## Implementation Timeline

**Total Estimated Time**: 10-15 days (2-3 weeks)

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: SCIP Foundation | 3-5 days | SCIPReader, SCIPConverter, protobuf bindings |
| Phase 2: Python Indexer | 3-4 days | PythonSCIPIndexer, installer, registry |
| Phase 3: CLI Integration | 2-3 days | Auto-detection, setup flow, error handling |
| Phase 4: Testing & Docs | 2-3 days | Test suite, documentation, examples |

**Status**: 📋 Planned (Medium Priority)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-02
**Next Review**: Upon implementation start
