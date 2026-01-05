# Architecture

Cicada's architecture combines two parsing approaches to maximize language coverage while minimizing development effort. This document explains the key design decisions and package structure.

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Cicada MCP Server                     │
│                                                              │
│  ┌────────────────┐         ┌──────────────────────────┐   │
│  │  MCP Protocol  │────────>│   Query Orchestrator     │   │
│  │  (JSON-RPC)    │         │   - search_module        │   │
│  └────────────────┘         │   - search_function      │   │
│                              │   - query                │   │
│                              │   - git_history          │   │
│                              └──────────┬───────────────┘   │
│                                         │                   │
│                    ┌────────────────────┴─────────────┐     │
│                    │                                  │     │
│          ┌─────────▼──────────┐          ┌──────────▼────────┐
│          │ Tree-sitter Backend│          │   SCIP Backend    │
│          │                    │          │                   │
│          │ • Elixir (built-in)│          │ • Python          │
│          │ • Erlang (built-in)│          │ • TypeScript/JS   │
│          │                    │          │ • Go, Rust, Java  │
│          │ Pros:              │          │ • C/C++, Ruby     │
│          │ • No dependencies  │          │ • C#, VB, Dart    │
│          │ • 160+ grammars    │          │                   │
│          │                    │          │ Pros:             │
│          │ Cons:              │          │ • Type-aware      │
│          │ • Manual AST walk  │          │ • Compiler accurate
│          │ • Syntactic only   │          │ • Reusable code   │
│          └────────────────────┘          └───────────────────┘
└─────────────────────────────────────────────────────────────┘
```

---

## Parsing Strategy: Hybrid Approach

Cicada uses **two complementary parsing approaches** to support 15 languages:

### Tree-sitter (2 languages)
- **Languages:** Elixir, Erlang
- **Use Case:** Languages without SCIP indexers
- **Characteristics:**
  - Syntactic parsing only (no type information)
  - Custom extractors per language (13 for Elixir)
  - No external dependencies
  - Fast, incremental parsing
  - 160+ grammar availability

### SCIP (13 languages)
- **Languages:** Python, TypeScript, JavaScript, Go, Rust, Java, Scala, C, C++, Ruby, C#, VB, Dart
- **Use Case:** Mainstream languages with mature tooling
- **Characteristics:**
  - Semantic parsing (type-aware)
  - Compiler-accurate results
  - Shared converter infrastructure
  - Cross-repository references
  - Requires external indexer per language

---

## Why Both Approaches?

### Decision Rationale

| Factor | Tree-sitter | SCIP | Winner |
|--------|-------------|------|--------|
| **Development effort** | 12-17 days per language | 4-6 days per language | SCIP (3x faster) |
| **Accuracy** | Syntactic approximations | Compiler-accurate | SCIP |
| **Type information** | Not available | Full type data | SCIP |
| **Dependencies** | None | External tool per language | Tree-sitter |
| **Language coverage** | 160+ grammars available | ~10 mature indexers | Tree-sitter |
| **Incremental indexing** | Real-time | Rebuild required | Tree-sitter |

**Conclusion:** Use SCIP where available for better results with less effort. Use tree-sitter for languages without SCIP indexers.

### Elixir: Why Tree-sitter?

Elixir is architecturally unique:
- **No SCIP indexer exists** for Elixir
- **Macro-based syntax:** `defmodule`, `def`, etc. appear as generic `call` nodes
- **13 custom extractors:** Already implemented and working well
- **Core language:** Cicada's original use case

Tree-sitter remains the best option for Elixir.

---

## Package Structure: cicada-core + cicada-scip

Cicada is split into a monorepo with two packages to make SCIP support optional:

```
packages/
├── cicada-core/              # Base classes and utilities
│   ├── base_indexer.py       # BaseIndexer ABC
│   ├── formatter_interface.py # BaseLanguageFormatter ABC
│   └── utils/
│       ├── hash_utils.py     # File hashing
│       └── storage.py        # Storage paths
│
└── cicada-scip/              # SCIP-based language support
    ├── converter.py          # Universal SCIP → Cicada converter
    ├── reader.py             # SCIP index reader
    ├── indexer.py            # Generic SCIP indexer
    ├── formatter.py          # Language formatters
    └── language_adapters.py  # Language-specific config
```

### Why Split Packages?

**Without cicada-scip:**
- Smaller installation (tree-sitter languages only)
- No protobuf dependencies
- Elixir and Erlang work out of the box

**With cicada-scip:**
- All 15 languages supported
- Requires external SCIP indexers
- Slightly larger install

### Installation Options

```bash
# Minimal (tree-sitter only: Elixir, Erlang)
pip install cicada-mcp

# Full (all 15 languages)
pip install cicada-mcp[scip]
```

### Conditional Language Registration

At runtime, Cicada detects if `cicada-scip` is installed:

```python
from cicada.languages.scip import SCIP_AVAILABLE

if SCIP_AVAILABLE:
    # Register Python, TypeScript, Go, Rust, etc.
    LanguageRegistry.register_language("python", ...)
else:
    # Only Elixir and Erlang available
```

---

## SCIP Converter: Universal Design

The SCIP converter (`cicada_scip/converter.py`) is **language-agnostic** by design:

### What It Handles Automatically

1. **Symbol Parsing:** Extracts modules, classes, functions from any SCIP index
2. **Arity Detection:** Counts function parameters across all languages
3. **Call Site Extraction:** Finds function calls and references
4. **Documentation:** Extracts docstrings, JSDoc, Javadoc, etc.
5. **Type Information:** Captures type signatures and specs

### Language-Specific Adapters

Only minimal customization needed per language:

```python
# Language adapter example
{
    "language": "python",
    "scip_command": ["npx", "-y", "@sourcegraph/scip-python", "index"],
    "file_extensions": [".py"],
    "needs_alias_extraction": True,  # Python imports need special handling
    "needs_string_extraction": True, # Extract from string literals
}
```

### 57% Feature Coverage Immediately

When adding a new SCIP language, these features work automatically:
- Module and function indexing
- Documentation keyword extraction
- Co-change analysis
- Co-occurrence detection
- Incremental indexing

Only need language-specific:
- Import alias extraction (~1 day)
- String literal extraction (~1 day)
- Testing (~1-2 days)

**Total effort: 4-6 days vs 12-17 days for tree-sitter**

---

## Language Implementation Priority

Based on user demand and development effort:

| Priority | Language | Approach | Status | Rationale |
|----------|----------|----------|--------|-----------|
| ✅ | Elixir | Tree-sitter | Complete | Original use case |
| ✅ | Python | SCIP | Complete | High demand |
| ✅ | Erlang | Tree-sitter | Complete | BEAM ecosystem |
| ✅ | TypeScript/JS | SCIP | Complete | Web development |
| ✅ | Go | SCIP | Complete | Systems programming |
| ✅ | Rust | SCIP | Complete | Growing adoption |
| ✅ | Java/Scala | SCIP | Complete | Enterprise |
| ✅ | C/C++ | SCIP | Complete | Systems programming |
| ✅ | Ruby/C#/VB/Dart | SCIP | Complete | Ecosystem coverage |

Future considerations (tree-sitter only):
- Gleam (no SCIP indexer)
- Zig (no SCIP indexer)
- Shell scripts (bash, fish, etc.)

---

## Indexing Pipeline

### Tree-sitter Flow

```
Source Code
    │
    ├─> Tree-sitter Parser
    │       │
    │       ├─> Module Extractor (e.g., defmodule in Elixir)
    │       ├─> Function Extractor (e.g., def, defp)
    │       ├─> Dependency Extractor (e.g., alias, import)
    │       ├─> Doc Extractor (e.g., @doc, @moduledoc)
    │       └─> String Extractor (string literals)
    │
    └─> Cicada Index (JSON)
            │
            ├─> modules: {name, functions, keywords}
            ├─> functions: {name, arity, line, doc, calls}
            └─> metadata: {language, version, hash}
```

### SCIP Flow

```
Source Code
    │
    ├─> External SCIP Indexer (e.g., scip-python, scip-typescript)
    │       │
    │       └─> SCIP Index (index.scip)
    │
    ├─> Universal SCIP Converter
    │       │
    │       ├─> Parse protobuf
    │       ├─> Extract symbols (modules, classes, functions)
    │       ├─> Detect arity from parameters
    │       ├─> Extract documentation
    │       └─> Find call sites
    │
    ├─> Language-Specific Extractors (parallel)
    │       │
    │       ├─> Alias Extractor (imports, using, require)
    │       └─> String Extractor (SQL, error messages)
    │
    └─> Cicada Index (JSON)
            │
            ├─> modules: {name, functions, keywords}
            ├─> functions: {name, arity, line, doc, calls}
            └─> metadata: {language, version, hash}
```

---

## Storage & Indexing

### Index Location

All indexes stored outside repositories:

```
~/.cicada/
└── projects/
    └── <repo_hash>/          # One per repository
        ├── index.json         # Main code index
        ├── config.yaml        # Project configuration
        ├── hashes.json        # File change tracking
        ├── pr_index.json      # GitHub PR attribution
        └── index.scip         # SCIP index (if used)
```

### Incremental Indexing

Only reindexes changed files:

1. Hash each file (SHA-256)
2. Compare against `hashes.json`
3. Reindex only modified files
4. Merge with existing index

Typical incremental index: <5 seconds

---

## Future Architecture Considerations

### Potential Improvements

1. **Unified Extractor Interface:** Abstract tree-sitter and SCIP behind common interface
2. **Plugin System:** Allow user-defined language extractors
3. **Caching Layer:** Cache parsed ASTs for faster reindexing
4. **Distributed Indexing:** Split large codebases across multiple processes

### Non-Goals

- **Real-time LSP:** Cicada is designed for AI assistants, not IDEs
- **Full compiler:** Leverage existing tools (SCIP indexers) rather than build compilers
- **Cross-language analysis:** Focus remains on per-language indexing

---

## Related Documentation

- [Language Support](LANGUAGE_SUPPORT.md) - Complete list of supported languages
- [MCP Tools Reference](MCP_TOOLS.md) - How tools use the index
- [Performance Guide](PERFORMANCE.md) - Indexing performance characteristics
