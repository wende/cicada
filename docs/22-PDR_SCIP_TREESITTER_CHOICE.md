# PDR 22: SCIP vs Tree-sitter for Multi-Language Support

**Date:** 2025-11-26
**Status:** Research Complete
**Context:** Evaluation of parsing approaches for adding new language support to Cicada

## Summary

This PDR documents our research into tree-sitter implementations across languages and compares them to SCIP for adding multi-language support. The key finding is that **SCIP is the recommended approach for mainstream languages** due to existing infrastructure in Cicada and semantic analysis capabilities, while **tree-sitter remains valuable for niche languages** without SCIP indexers.

## Context

Cicada currently uses two different parsing approaches:

| Language | Approach | Implementation |
|----------|----------|----------------|
| Elixir | Tree-sitter | 13 custom extractors with manual AST traversal |
| Python | SCIP | Universal converter via scip-python/Pyright |

The question: For new languages (Go, TypeScript, Rust, etc.), which approach should we use?

## Research Findings

### Tree-sitter Availability

**Package Options:**

| Package | Status | Languages |
|---------|--------|-----------|
| `tree-sitter-language-pack` | Active (v0.11.0, Nov 2025) | **160+ languages** |
| `tree-sitter-languages` | **Unmaintained** | ~50 languages |
| Individual packages | Active | Per-language |

**Node Type Comparison:**

| Language | Function | Class | Import |
|----------|----------|-------|--------|
| Elixir | `call` (needs identifier check) | `call` (defmodule) | `call` (alias/import) |
| Python | `function_definition` | `class_definition` | `import_statement` |
| Go | `function_declaration` | N/A (`struct_type`) | `import_declaration` |
| JavaScript | `function_declaration` | `class_declaration` | `import_statement` |
| TypeScript | `function_declaration` | `class_declaration` | `import_statement` |
| Rust | `function_item` | `struct_item` | `use_declaration` |
| Java | `method_declaration` | `class_declaration` | `import_declaration` |

**Key Insight:** Elixir is unique in using macro-based syntax where `defmodule`, `def`, etc. appear as `call` nodes requiring special identifier checking. Other languages have explicit, dedicated node types making extraction simpler.

### SCIP Indexer Availability

All indexers are **Generally Available** from Sourcegraph:

| Language | SCIP Indexer | Installation |
|----------|--------------|--------------|
| Go | `scip-go` | `go install github.com/sourcegraph/scip-go/cmd/scip-go@latest` |
| TypeScript/JS | `scip-typescript` | npm |
| Java/Scala/Kotlin | `scip-java` | Gradle/Maven plugin |
| C/C++ | `scip-clang` | Binary |
| Rust | `rust-analyzer` | Binary (SCIP output) |
| Python | `scip-python` | npm (already in Cicada) |
| Ruby | `scip-ruby` | Gem |
| C# | `scip-dotnet` | NuGet |

### Tree-sitter vs SCIP Comparison

| Aspect | Tree-sitter | SCIP |
|--------|-------------|------|
| **Analysis depth** | Syntactic (CST only) | Semantic (type-aware) |
| **Accuracy** | May have false +/- | Compiler-accurate |
| **Dependencies** | Minimal (Python pkg) | External tool required |
| **Dev effort** | Custom extractors/language | Reuse existing SCIP converter |
| **Cross-repo refs** | No | Yes (most languages) |
| **Incremental** | Yes (real-time) | Requires rebuild |
| **Language coverage** | 160+ languages | ~10 languages |
| **Documentation** | Manual extraction | Automatic (docstrings, JSDoc) |
| **Type information** | Not available | Full type data |

## Decision

### Recommended Approach by Language Type

#### Use SCIP (Preferred for mainstream languages)

| Language | Indexer | Effort | Notes |
|----------|---------|--------|-------|
| **Go** | scip-go | Low | Reuse existing SCIP converter |
| **TypeScript/JS** | scip-typescript | Low | Same converter infrastructure |
| **Java** | scip-java | Medium | Requires Gradle/Maven setup |
| **Rust** | rust-analyzer | Medium | Different SCIP output format |
| **Ruby** | scip-ruby | Low | Direct SCIP output |
| **C#** | scip-dotnet | Medium | .NET toolchain required |
| **C/C++** | scip-clang | High | Complex build systems |

**Why SCIP for these languages:**
1. Cicada already has working SCIP converter (see PDR 21)
2. 57% of features work immediately (doc keywords, co-change, co-occurrence, incremental indexing)
3. Semantic analysis provides compiler-accurate results
4. Lower per-language development effort (4-6 days vs 2-3 weeks)

#### Use Tree-sitter (For niche languages)

| Language | Rationale |
|----------|-----------|
| **Elixir** | Already implemented, no SCIP indexer exists |
| **Gleam** | No SCIP indexer, tree-sitter available |
| **Nim** | No SCIP indexer |
| **Zig** | No SCIP indexer |
| **Shell scripts** | No SCIP, tree-sitter covers bash/fish/etc. |

**Why Tree-sitter for these:**
1. No SCIP indexers available
2. Tree-sitter is the only option for syntactic analysis
3. 160+ language grammars available

## Effort Estimates

### Adding a Language via SCIP

| Phase | Effort | Tasks |
|-------|--------|-------|
| Phase 1: SCIP Setup | 1 day | Install indexer, test on sample projects |
| Phase 2: Alias Extraction | 1-2 days | Language-specific import alias parser |
| Phase 3: String Extraction | 1 day | Language-specific string literal parser |
| Phase 4: Testing | 1-2 days | Integration tests, MCP tool verification |
| **Total** | **4-6 days** | |

### Adding a Language via Tree-sitter

| Phase | Effort | Tasks |
|-------|--------|-------|
| Phase 1: Parser Setup | 1 day | Add tree-sitter grammar, create parser class |
| Phase 2: Module Extractor | 2-3 days | Extract modules/classes/namespaces |
| Phase 3: Function Extractor | 2-3 days | Extract functions, methods, parameters |
| Phase 4: Dependency Extractors | 3-4 days | Imports, calls, type references |
| Phase 5: Doc Extractor | 1-2 days | Docstrings, comments |
| Phase 6: String Extractor | 1 day | String literals |
| Phase 7: Testing | 2-3 days | Unit tests, integration tests |
| **Total** | **12-17 days** | |

**SCIP is 3x faster to implement** for languages with existing indexers.

## Alternatives Considered

### Alternative 1: Tree-sitter for All Languages

**Pros:**
- Consistent architecture across all languages
- No external tool dependencies
- 160+ language grammars available

**Cons:**
- 3x more development effort per language
- No semantic/type information
- Must maintain 10+ separate extractor sets

**Verdict:** REJECTED - Development overhead not justified when SCIP provides better results with less effort.

### Alternative 2: SCIP Only (Drop Elixir Tree-sitter)

**Pros:**
- Unified codebase
- Consistent feature set

**Cons:**
- No SCIP indexer exists for Elixir
- Would require maintaining custom Elixir SCIP indexer
- Current implementation works well

**Verdict:** REJECTED - Keep tree-sitter for Elixir, no practical alternative.

### Alternative 3: Hybrid Approach (Recommended)

**Approach:**
- SCIP for languages with mature indexers
- Tree-sitter for languages without SCIP support
- Shared infrastructure (keyword extraction, co-change, co-occurrence)

**Pros:**
- Best tool for each language
- Minimizes development effort
- Maximum language coverage

**Cons:**
- Two parsing paths to maintain
- Slight architectural complexity

**Verdict:** ACCEPTED - Pragmatic approach leveraging best available tools.

## Implementation Priority

Based on user demand and effort required:

| Priority | Language | Approach | Effort | Rationale |
|----------|----------|----------|--------|-----------|
| 1 | TypeScript | SCIP | 4-6 days | High demand, JS ecosystem |
| 2 | Go | SCIP | 4-6 days | Popular systems language |
| 3 | Rust | SCIP | 5-7 days | Growing adoption |
| 4 | Java | SCIP | 6-8 days | Enterprise demand |
| - | Ruby | SCIP | 4-6 days | On request |
| - | C/C++ | SCIP | 8-10 days | Complex, on request |

## Key Insights

1. **Elixir is architecturally unique**: Its macro-based syntax where `defmodule`, `def` appear as `call` nodes is unusual. Other languages have explicit node types making tree-sitter extraction simpler.

2. **SCIP converter is language-agnostic**: The existing converter (`cicada/languages/scip/converter.py`) handles symbol parsing, arity detection, and call site extraction universally. Only minor language-specific adjustments needed.

3. **57% of features are SCIP-universal**: Documentation keywords, co-change, co-occurrence, and incremental indexing work immediately for any SCIP-indexed language (see PDR 21).

4. **Tree-sitter shines for prototyping**: No external tools, immediate parsing. Good for quick experimentation with new languages.

5. **SCIP provides semantic understanding**: Type information, cross-file resolution, and compiler accuracy that tree-sitter cannot provide.

## References

- [py-tree-sitter Documentation](https://tree-sitter.github.io/py-tree-sitter/)
- [tree-sitter-language-pack on PyPI](https://pypi.org/project/tree-sitter-language-pack/)
- [Sourcegraph SCIP Protocol](https://github.com/sourcegraph/scip)
- [Sourcegraph Indexers Reference](https://sourcegraph.com/docs/code_navigation/references/indexers)
- [Tree-sitter Limitations (Jake Zimmerman)](https://blog.jez.io/tree-sitter-limitations/)
- [Static Node Types (Tree-sitter)](https://tree-sitter.github.io/tree-sitter/using-parsers/6-static-node-types.html)
- [SCIP Announcement (Sourcegraph)](https://sourcegraph.com/blog/announcing-scip)
- PDR 21: SCIP Reusability Analysis (`docs/21-SCIP_REUSABILITY_ANALYSIS.md`)

## Revision History

- 2025-11-26: Initial research and documentation
