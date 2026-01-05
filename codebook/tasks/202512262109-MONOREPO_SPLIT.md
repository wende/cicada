# Monorepo Split: Making cicada-scip Optional

This document describes the changes made to split cicada into a monorepo structure where cicada-scip is an optional dependency.

## Overview

The cicada project has been restructured into a monorepo with two sub-packages:
- **cicada-core**: Base classes and utilities shared across all languages
- **cicada-scip**: SCIP-based language indexing (Python, TypeScript, Go, Rust, etc.)

Tree-sitter based languages (Elixir, Erlang) now work without requiring cicada-scip.

## Package Structure

```
packages/
├── cicada-core/
│   ├── pyproject.toml
│   ├── src/cicada_core/
│   │   ├── __init__.py
│   │   ├── base_indexer.py          # BaseIndexer ABC
│   │   ├── formatter_interface.py   # BaseLanguageFormatter ABC
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── hash_utils.py        # File hashing utilities
│   │       └── storage.py           # Storage path utilities
│   └── tests/
│       ├── conftest.py
│       ├── test_base_indexer.py
│       └── utils/
│           ├── test_hash_utils.py
│           └── test_storage.py
│
└── cicada-scip/
    ├── pyproject.toml
    ├── src/cicada_scip/
    │   ├── __init__.py
    │   ├── scip.proto               # SCIP protocol definition
    │   ├── scip_pb2.py              # Generated protobuf (gitignored)
    │   ├── scip_pb2.pyi             # Generated type stubs (gitignored)
    │   ├── converter.py             # SCIPConverter
    │   ├── reader.py                # SCIPReader
    │   ├── indexer.py               # GenericSCIPIndexer
    │   ├── formatter.py             # Language-specific formatters
    │   └── language_adapters.py     # Language adapter registry
    └── tests/
        ├── conftest.py
        └── test_*.py                # Duplicated SCIP tests
```

## Re-export Modules

The main cicada package now contains re-export modules that wrap imports from cicada_scip in try/except blocks:

### cicada/languages/scip/__init__.py
```python
__all__ = []
SCIP_AVAILABLE = False

try:
    from cicada_scip import SCIPConverter, SCIPReader, GenericSCIPIndexer
    __all__ = ["SCIPConverter", "SCIPReader", "GenericSCIPIndexer"]
    SCIP_AVAILABLE = True
except ImportError:
    pass
```

### Other re-export files
- `cicada/languages/scip/converter.py` - re-exports SCIPConverter, DocumentData, etc.
- `cicada/languages/scip/reader.py` - re-exports SCIPReader
- `cicada/languages/scip/indexer.py` - re-exports GenericSCIPIndexer
- `cicada/languages/scip/formatter.py` - re-exports all language formatters
- `cicada/languages/scip/language_adapters.py` - re-exports adapter classes
- `cicada/languages/scip/scip_pb2.py` - re-exports protobuf definitions

## Conditional Language Registration

In `cicada/languages/__init__.py`, SCIP-based languages are only registered when cicada-scip is available:

```python
from cicada.languages.scip import SCIP_AVAILABLE

# Tree-sitter languages (always available)
LanguageRegistry.register_language(
    language="elixir",
    parser_class="cicada.languages.elixir.parser.ElixirParser",
    indexer_class="cicada.indexer.ElixirIndexer",
    ...
)

LanguageRegistry.register_language(
    language="erlang",
    parser_class="cicada.languages.erlang.parser.ErlangParser",
    indexer_class="cicada.languages.erlang.indexer.ErlangIndexer",
    ...
)

# SCIP-based languages (only when cicada-scip is installed)
if SCIP_AVAILABLE:
    LanguageRegistry.register_language(
        language="python",
        parser_class=None,
        indexer_class="cicada.languages.python.indexer.PythonSCIPIndexer",
        ...
    )
    # ... TypeScript, JavaScript, Go, Rust, Java, Scala, C, C++, Ruby, C#, VB, Dart
```

## Language Availability

| Language | Backend | Requires cicada-scip |
|----------|---------|---------------------|
| Elixir | tree-sitter | No |
| Erlang | tree-sitter | No |
| Python | SCIP | Yes |
| TypeScript | SCIP | Yes |
| JavaScript | SCIP | Yes |
| Go | SCIP | Yes |
| Rust | SCIP | Yes |
| Java | SCIP | Yes |
| Scala | SCIP | Yes |
| C | SCIP | Yes |
| C++ | SCIP | Yes |
| Ruby | SCIP | Yes |
| C# | SCIP | Yes |
| Visual Basic | SCIP | Yes |
| Dart | SCIP | Yes |

## Installation Options

### Minimal (tree-sitter only)
```bash
pip install cicada-mcp
# Supports: Elixir, Erlang
```

### Full (all languages)
```bash
pip install cicada-mcp[scip]
# Supports: All languages including Python, TypeScript, Go, Rust, etc.
```

### Development
```bash
uv sync --dev
# Installs cicada-scip for full test coverage
```

## pyproject.toml Changes

### Main package dependencies
```toml
[project]
dependencies = [
    "cicada-core",
    # cicada-scip is optional - see [project.optional-dependencies]
    "mcp>=0.1.0",
    # ... other deps (protobuf removed - it's a dependency of cicada-scip)
]

[project.optional-dependencies]
scip = ["cicada-scip>=0.1.0"]
dev = ["cicada-scip>=0.1.0", "pytest>=8.0"]

[dependency-groups]
dev = [
    "cicada-scip",  # SCIP package for full test coverage
    "pytest>=8.4.2",
    # ... other dev deps
]
```

### UV workspace configuration
```toml
[tool.uv.workspace]
members = ["packages/cicada-core", "packages/cicada-scip"]

[tool.uv.sources]
cicada-core = { workspace = true }
cicada-scip = { workspace = true }
```

## Makefile Changes

- `generate-scip-proto` now generates protobuf files in `packages/cicada-scip/src/cicada_scip/`
- `clean` target updated to clean package protobuf files instead of main cicada

## Testing

### Main test suite
```bash
make test
# Runs all tests with cicada-scip installed (3825 tests)
```

### Package-specific tests
```bash
# cicada-core (72 tests)
cd packages/cicada-core && uv run pytest

# cicada-scip (158 pass, 111 skipped - skipped tests require full cicada)
cd packages/cicada-scip && uv run pytest
```

### Verifying optional dependency works
```python
from cicada.languages import LanguageRegistry
from cicada.languages.scip import SCIP_AVAILABLE

print(f"SCIP_AVAILABLE: {SCIP_AVAILABLE}")
print(f"Supported languages: {LanguageRegistry.get_supported_languages()}")

# Without cicada-scip: ['elixir', 'erlang']
# With cicada-scip: ['elixir', 'erlang', 'python', 'typescript', ...]
```

## Migration Notes

### For users
- No changes needed for Elixir/Erlang users
- Python/TypeScript/etc. users need to install with `[scip]` extra or install cicada-scip separately

### For developers
- Import paths remain the same (re-exports handle the mapping)
- Test with both configurations to ensure optional dependency handling works
- Package tests are marked as duplicated and will be cleaned up incrementally

## Files Changed

### New files
- `packages/cicada-core/` - entire directory
- `packages/cicada-scip/` - entire directory
- `cicada/languages/scip/scip_pb2.py` - re-export module (was generated, now tracked)
- `cicada/languages/scip/scip_pb2.pyi` - re-export type stubs

### Modified files
- `pyproject.toml` - workspace config, optional dependencies
- `Makefile` - protobuf generation path, clean target
- `.gitignore` - updated protobuf ignore patterns
- `cicada/languages/__init__.py` - conditional SCIP language registration
- `cicada/languages/scip/__init__.py` - re-export with SCIP_AVAILABLE flag
- `cicada/languages/scip/converter.py` - re-export module
- `cicada/languages/scip/reader.py` - re-export module
- `cicada/languages/scip/indexer.py` - re-export module
- `cicada/languages/scip/formatter.py` - re-export module
- `cicada/languages/scip/language_adapters.py` - re-export module
- `cicada/languages/formatter_interface.py` - imports from cicada_core
