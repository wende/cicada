# Architecture

High-level overview of Cicada's project structure and design.

## Project Structure

```
cicada/
├── cicada/                    # Main package
│   ├── mcp/                   # MCP server implementation
│   ├── languages/             # Language-specific parsers
│   │   ├── elixir/           # Tree-sitter based
│   │   ├── erlang/           # Tree-sitter based
│   │   ├── python/           # SCIP based
│   │   └── scip/             # Universal SCIP support
│   ├── git/                   # Git history & PR indexing
│   ├── format/                # Output formatting
│   └── utils/                 # Shared utilities
│
├── packages/                  # Monorepo packages
│   ├── cicada-core/          # Base classes (optional dependency)
│   └── cicada-scip/          # SCIP support (optional dependency)
│
├── codebook/                  # User documentation
├── tests/                     # Test suite
└── extensions/                # (To be removed - see docs migration)
```

---

## Core Components

### 1. MCP Server (`cicada/mcp/`)
- JSON-RPC protocol handler
- Tool registration and routing
- Request/response formatting

### 2. Language Backends (`cicada/languages/`)
- **Tree-sitter:** Elixir, Erlang (no dependencies)
- **SCIP:** 13 languages (requires external indexers)

### 3. Git Integration (`cicada/git/`)
- File history tracking
- PR attribution (via GitHub API)
- Blame analysis

### 4. Query System (`cicada/keyword_search.py`, `cicada/query/`)
- Keyword extraction and matching
- Pattern-based search
- Result ranking and scoring

---

## Design Philosophy

### Hybrid Parsing Strategy

Cicada uses **two complementary approaches**:

1. **Tree-sitter** for languages without SCIP indexers
   - Syntactic parsing only
   - No external dependencies
   - Custom extractors per language

2. **SCIP** for mainstream languages
   - Semantic (type-aware) parsing
   - Compiler-accurate results
   - Shared converter infrastructure

**Why both?** SCIP provides better results 3x faster to implement, but only ~10 languages have mature indexers. Tree-sitter fills the gap.

### Optional Dependencies

```bash
# Minimal install (tree-sitter only: Elixir, Erlang)
pip install cicada-mcp

# Full install (all 15 languages)
pip install cicada-mcp[scip]
```

The monorepo split (`cicada-core` + `cicada-scip`) allows users to install only what they need.

---

## Data Flow

```
Source Code
    │
    ├─> Parser (tree-sitter OR SCIP)
    │       │
    │       └─> Extract: modules, functions, docs, calls
    │
    ├─> Keyword Extractor
    │       │
    │       └─> Extract: code identifiers, docstrings, strings
    │
    ├─> Git Analyzer
    │       │
    │       └─> Extract: history, PRs, blame data
    │
    └─> Index Builder
            │
            └─> ~/.cicada/projects/<hash>/index.json
                    │
                    └─> MCP Server (queries via tools)
```

---

## Key Design Decisions

### 1. Index Storage Outside Repo
- **Location:** `~/.cicada/projects/<repo_hash>/`
- **Why:** Keeps repository clean, enables multi-worktree support

### 2. Incremental Indexing
- **Method:** SHA-256 file hashing
- **Benefit:** Only reindex changed files (<5s typical)

### 3. Universal SCIP Converter
- **Approach:** Language-agnostic symbol parser
- **Benefit:** New SCIP languages need minimal customization (4-6 days vs 12-17 days)

### 4. Token Optimization
- **Default:** Compact output for AI agents
- **Option:** Verbose mode for human consumption
- **Benefit:** 40-80% token savings in common cases

---

## Performance Characteristics

| Operation | Small Project | Large Project |
|-----------|--------------|---------------|
| Initial index | 5-10 seconds | 30-60 seconds |
| Incremental | <5 seconds | 5-15 seconds |
| Query | <1 second | <2 seconds |

---

## Detailed Documentation

For in-depth architecture information:

- **[Full Architecture Guide](codebook/ARCHITECTURE.md)** - Design rationale, parsing strategies, package structure
- **[Language Support](codebook/LANGUAGE_SUPPORT.md)** - Complete language implementation details
- **[Performance Guide](codebook/PERFORMANCE.md)** - Optimization strategies and benchmarks

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process
