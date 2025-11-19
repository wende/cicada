# PDR 21: SCIP Reusability Analysis for Multi-Language Support

**Date:** 2025-11-19
**Status:** Accepted
**Context:** Investigation into which Cicada features are SCIP-universal vs language-specific

## Summary

This PDR documents our analysis of SCIP (Source Code Intelligence Protocol) to determine which Cicada features can be reused across languages (Python, TypeScript, etc.) vs which require per-language implementation.

## Context

Cicada currently supports Elixir (tree-sitter based) and Python (SCIP based). We're planning to add TypeScript support. Understanding SCIP's capabilities helps us determine:

1. Which features work immediately for any SCIP-indexed language
2. Which features require language-specific parsing
3. The effort required to add new languages

## Investigation Method

We examined three sources:

1. **SCIP Protocol Buffer Schema** (`scip.proto`)
2. **scip-python Implementation** (TypeScript indexer in `~/projects/scip-python`)
3. **Empirical Analysis** of actual SCIP index files from our fixtures

### Key Findings from SCIP Schema

The SCIP `SymbolInformation` message provides:

```protobuf
message SymbolInformation {
  string symbol = 1;
  repeated string documentation = 3;        // ✅ Language-specific docs
  repeated Relationship relationships = 4;
  Kind kind = 5;
  string display_name = 6;
  Document signature_documentation = 7;
  string enclosing_symbol = 8;
}
```

The SCIP `Document` message provides:

```protobuf
message Document {
  string language = 4;
  string relative_path = 1;
  repeated Occurrence occurrences = 2;
  repeated SymbolInformation symbols = 3;
  string text = 5;                          // ❌ NOT populated by scip-python
  PositionEncoding position_encoding = 6;
}
```

### Empirical Findings

Analysis of `tests/fixtures/sample_python/index.scip` revealed:

```python
# ✅ Documentation IS available
symbol_info.documentation = [
  '```python\nclass Calculator:\n```',
  'A simple calculator that performs basic arithmetic operations.'
]

# ❌ Source text NOT stored
document.text = ''  # Always empty

# ❌ Syntax kinds NOT populated
occurrence.syntax_kind = 0  # Always UnspecifiedSyntaxKind

# ✅ Symbol positions ARE available
occurrence.range = [5, 5, 11]  # [start_line, start_col, end_col]
```

From `scip-python/packages/pyright-scip/src/treeVisitor.ts`, documentation extraction:

```typescript
this.document.symbols.push(
    new scip.SymbolInformation({
        symbol: this.getScipSymbol(node).value,
        documentation: _formatHover(hoverResult!),  // ✅ Extracted from Python
    })
);
```

## Decision: Feature Classification

### Category 1: SCIP-Universal Features (57% - 4/7)

These work immediately for any SCIP-indexed language:

#### 1. Documentation Keyword Extraction ✅

**Why:** SCIP provides `SymbolInformation.documentation` field populated by language-specific indexers.

**Implementation:**
- Python: Extracts docstrings (`"""..."""`)
- TypeScript: Would extract JSDoc comments (`/** ... */`)
- Java: Would extract Javadoc comments

**Code:** `cicada/languages/scip/converter.py:204-219, 263-279, 428-446`

```python
# Already working for Python
if symbol_info.documentation:
    moduledoc = "\n".join(symbol_info.documentation)
    module_data["moduledoc"] = moduledoc

    # Extract keywords from documentation
    if self.extract_keywords and self.keyword_extractor:
        results = self.keyword_extractor.extract_keywords(module_text, top_n=10)
```

#### 2. Co-change Analysis ✅

**Why:** Pure git history analysis, completely language-agnostic.

**Implementation:** Analyzes `git log` to track files/functions modified together.

**Code:** `cicada/git/cochange_analyzer.py`

#### 3. Co-occurrence Analysis ✅

**Why:** Operates on extracted keywords regardless of source.

**Implementation:** Builds keyword co-occurrence matrix from any keyword source.

**Code:** `cicada/cooccurrence.py`

#### 4. Incremental Indexing ✅

**Why:** Hash-based file change detection, language-agnostic.

**Implementation:** SHA-256 hashing of file contents to detect changes.

**Code:** `cicada/indexer.py` - `_should_index_file()`

### Category 2: Per-Language Implementation Required (43% - 3/7)

#### 5. Module Usage Tracking ⚠️

**Why:** SCIP tracks imports but NOT alias mappings.

**What SCIP provides:**
- Import statements (via `Occurrence` with `SymbolRole.Import`)
- Imported module symbols

**What SCIP does NOT provide:**
- Alias mappings (`import X as Y` → `{"Y": "X"}`)
- Re-export tracking

**Language-specific implementation needed:**

| Language | Import Syntax | Parser Needed |
|----------|--------------|---------------|
| Python | `import ops as operations`<br>`from utils import avg as average` | Python `ast` module |
| TypeScript | `import { foo as bar } from 'module'`<br>`import * as ops from 'operations'` | TypeScript AST |
| Elixir | `alias MyApp.Operations, as: Ops` | Tree-sitter (already implemented) |

**Current implementation:**
- Python: `cicada/languages/python/alias_extractor.py` (AST-based)
- Elixir: `cicada/elixir/parser.py` (tree-sitter based)

#### 6. String Keyword Extraction ⚠️

**Why:** SCIP does not store source text or string literal values.

**What SCIP provides:**
- Symbol positions (`Occurrence.range`)
- Syntax kind enum (but NOT populated by scip-python)

**What SCIP does NOT provide:**
- Source code text (`Document.text` field is empty)
- String literal content
- String literal positions (syntax_kind not used)

**Implementation approach:**
1. Read source file separately
2. Use language-specific parser to extract strings
3. Apply keyword extraction to string content

**Language-specific parsers:**

| Language | String Syntax | Parser |
|----------|--------------|--------|
| Python | `"string"`, `"""docstring"""`, `f"format {var}"` | Python `ast` module |
| TypeScript | `"string"`, `` `template ${var}` ``, `'string'` | TypeScript AST |
| Elixir | `"string"`, `~s(sigil)`, `"""heredoc"""` | Tree-sitter |

**Current implementation:**
- Python: Would need AST-based string extraction (not yet implemented)
- Elixir: `cicada/elixir/extractors/string.py` (tree-sitter based)

#### 7. Basic Indexing ⚠️

**Why:** Each language needs its own SCIP indexer.

**Available SCIP indexers:**
- Python: `scip-python` (pyright-based)
- TypeScript: `scip-typescript` (from Sourcegraph)
- Java: `scip-java`
- Go: `scip-go`
- Rust: `rust-analyzer` with SCIP export

**Integration required per language:**
- Configure and run language-specific indexer
- Parse SCIP protocol buffer output
- Map to Cicada's unified schema

## Implications for TypeScript Support

When adding TypeScript support:

### ✅ Works Immediately (4 features)
1. **Documentation keyword extraction** - Just run scip-typescript
2. **Co-change analysis** - Already language-agnostic
3. **Co-occurrence analysis** - Already language-agnostic
4. **Incremental indexing** - Already language-agnostic

### ⚠️ Needs Implementation (3 features)

1. **Module usage tracking**
   - Effort: ~1-2 days
   - Implementation: TypeScript AST parser for `import`/`export` statements
   - Pattern: Copy `alias_extractor.py`, adapt for TypeScript syntax

2. **String keyword extraction**
   - Effort: ~1 day
   - Implementation: TypeScript AST for string/template literals
   - Pattern: Copy Elixir's string extractor, adapt for TypeScript

3. **SCIP indexer integration**
   - Effort: ~2-3 days
   - Tasks:
     - Install/configure scip-typescript
     - Test on sample TypeScript projects
     - Handle TypeScript-specific symbol types (interfaces, enums, etc.)
     - Map decorators, generics to Cicada schema

**Total estimated effort:** ~4-6 days for full TypeScript parity

## Technical Details

### SCIP Documentation Format

Python docstrings in SCIP:

```python
# Original Python code:
class Calculator:
    """A simple calculator."""
    pass

# SCIP SymbolInformation.documentation:
[
    '```python\nclass Calculator:\n```',
    'A simple calculator.'
]
```

Format: `[signature_markdown, docstring_text]`

### Why String Literals Aren't SCIP-Universal

From our investigation:

```python
# Examining scip-python output
document.text = ''  # Source NOT stored
occurrence.syntax_kind = 0  # String literals NOT marked

# All occurrences have UnspecifiedSyntaxKind
# Even though SCIP schema defines StringLiteral = 27
```

**Root cause:** scip-python doesn't populate:
- `Document.text` field
- `Occurrence.syntax_kind` field

This is likely for index size optimization - storing all source text would significantly increase index size.

### Alias Extraction Pattern

Current Python implementation serves as a template:

```python
# cicada/languages/python/alias_extractor.py
class PythonAliasExtractor:
    def extract_aliases_from_source(self, source: str) -> dict[str, str]:
        """Extract import aliases using language AST."""
        aliases = {}
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import operations as ops
                for alias in node.names:
                    if alias.asname:
                        aliases[alias.asname] = alias.name

            elif isinstance(node, ast.ImportFrom) and node.module:
                # from utils import avg as average
                for alias in node.names:
                    if alias.asname:
                        aliases[alias.asname] = node.module

        return aliases
```

For TypeScript, replace with:

```typescript
// Pseudocode for TypeScript version
import * as ts from 'typescript';

class TypeScriptAliasExtractor {
    extractAliases(sourceText: string): Map<string, string> {
        const sourceFile = ts.createSourceFile('temp.ts', sourceText, ...);
        const aliases = new Map();

        ts.forEachChild(sourceFile, node => {
            if (ts.isImportDeclaration(node)) {
                // Handle: import { foo as bar } from 'module'
                // Extract alias mappings
            }
        });

        return aliases;
    }
}
```

## Alternatives Considered

### Alternative 1: Wait for SCIP to Add String Literal Support

**Pros:**
- Would make string extraction universal
- No per-language parsers needed

**Cons:**
- No timeline for SCIP enhancement
- Index size would increase significantly
- May never happen (by design)

**Decision:** Not viable, implement per-language solution

### Alternative 2: Extract Strings from Source at Query Time

**Pros:**
- No need to store strings in index
- Always up-to-date

**Cons:**
- Slower queries (must parse on every search)
- Requires source files available at query time
- More complex caching needed

**Decision:** Rejected, extract at index time like Elixir

### Alternative 3: Skip String Keyword Extraction for SCIP Languages

**Pros:**
- Simpler implementation
- Smaller index size

**Cons:**
- Feature incompleteness vs Elixir
- Loses valuable search capability (SQL queries, log messages, etc.)

**Decision:** Rejected, string keywords are too valuable

## Recommendations

### For TypeScript Implementation

1. **Phase 1: SCIP-Universal Features** (Day 1)
   - Run scip-typescript on sample projects
   - Verify doc keyword extraction works
   - Test co-change, co-occurrence, incremental indexing

2. **Phase 2: Alias Extraction** (Days 2-3)
   - Create `cicada/languages/typescript/alias_extractor.ts`
   - Use TypeScript compiler API
   - Handle ES6 modules, CommonJS, namespaces

3. **Phase 3: String Extraction** (Day 4)
   - Create `cicada/languages/typescript/string_extractor.ts`
   - Extract template literals, regular strings
   - Handle JSX string attributes

4. **Phase 4: Testing & Integration** (Days 5-6)
   - End-to-end tests with real TypeScript projects
   - MCP tool verification
   - Documentation updates

### For Future Language Support

Any language with a SCIP indexer can be added following this pattern:

| Feature | SCIP-Universal | Effort |
|---------|---------------|---------|
| Doc keywords | ✅ Yes | Free |
| Co-change | ✅ Yes | Free |
| Co-occurrence | ✅ Yes | Free |
| Incremental indexing | ✅ Yes | Free |
| Module usage | ⚠️ No | 1-2 days |
| String keywords | ⚠️ No | 1 day |
| Basic indexing | ⚠️ No | 2-3 days |

**Total per-language effort:** 4-6 days for full parity

### SCIP Indexer Availability

Languages with existing SCIP indexers (can be added to Cicada):

- ✅ TypeScript/JavaScript (scip-typescript)
- ✅ Java (scip-java)
- ✅ Go (scip-go)
- ✅ Rust (rust-analyzer)
- ✅ C++ (scip-clang)
- ✅ Scala (scip-scala)
- ⚠️ Ruby (experimental)

## Conclusion

**Key insight:** 57% of Cicada features (4/7) are SCIP-universal and work immediately for any SCIP-indexed language. The remaining 43% (3/7) require straightforward per-language implementations following established patterns.

**Documentation IS SCIP-universal** - This was the key finding. SCIP indexers extract language-specific documentation (docstrings, JSDoc, Javadoc) into a universal format that our keyword extraction pipeline can process immediately.

**String literals are NOT SCIP-universal** - Despite SCIP having syntax kind enums for strings, indexers don't populate this data. String extraction requires reading source files and using language-specific parsers.

**TypeScript support is feasible** - With 4/7 features working immediately and clear implementation patterns for the remaining 3, adding TypeScript support is estimated at 4-6 days of focused development.

## References

- SCIP Protocol: https://github.com/sourcegraph/scip
- scip-python: `~/projects/scip-python/packages/pyright-scip/`
- SCIP Schema: `cicada/languages/scip/scip_pb2.py`
- Python Alias Extractor: `cicada/languages/python/alias_extractor.py`
- SCIP Converter: `cicada/languages/scip/converter.py`

## Revision History

- 2025-11-19: Initial analysis and investigation
- 2025-11-19: Empirical validation with scip-python output
- 2025-11-19: Documentation finalized
