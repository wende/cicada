# Erlang Support - PRD

## Status: Phase 4 Complete (Semantic Search)

Erlang indexing with EDoc extraction and keyword-based semantic search. Tested on real-world project [PURITY](https://github.com/mpitid/purity) (26 modules, 630 functions).

## Implementation Summary

| Component | Status | Location |
|-----------|--------|----------|
| Parser | ✅ Complete | `cicada/languages/erlang/parser.py` |
| EDoc Extractor | ✅ Complete | `cicada/languages/erlang/extractors/doc.py` |
| Indexer | ✅ Complete | `cicada/languages/erlang/indexer.py` |
| Keyword Extraction | ✅ Complete | Integrated via `keyword_utils` |
| Formatter | ✅ Complete | `cicada/languages/erlang/formatter.py` |
| Language detection | ✅ Complete | `cicada/setup.py` |
| CLI integration | ✅ Complete | `cicada claude` works |

### What's Working

- Module extraction from `-module(name).`
- Export parsing for public/private visibility
- Function names, line numbers, arity
- **EDoc `@doc` extraction for modules and functions**
- **EDoc `@param` and `@returns` tag parsing**
- **Keyword extraction from module/function names and docs**
- **Semantic search enabled via keyword index**
- Erlang notation formatting (`module:func/arity`)
- Detection via `rebar.config`, `erlang.mk`, or `src/*.erl`
- Full CLI workflow (`cicada claude` on Erlang repos)

### What's Not Implemented

- Multiple function clause handling
- `-spec` extraction
- Function call sites / dependencies
- Types, records, behaviours

## Technology Stack

| Component | Solution |
|-----------|----------|
| Grammar | [WhatsApp/tree-sitter-erlang](https://github.com/WhatsApp/tree-sitter-erlang) |
| Python binding | `tree-sitter-language-pack>=0.13.0` |
| Approach | Tree-sitter (same as Elixir) |

No SCIP indexer exists for Erlang, so tree-sitter is the only viable approach.

## Tree-sitter AST Structure

Key node types discovered during POC:

```
source_file
├── module_attribute        # -module(name).
│   └── atom                # module name
├── export_attribute        # -export([...]).
│   └── fa                  # function/arity pair
│       ├── atom            # function name
│       └── arity
│           └── integer     # arity number
└── fun_decl                # function declaration
    └── function_clause
        ├── atom            # function name
        ├── expr_args       # arguments
        │   └── var         # each argument
        └── clause_body
            └── ...         # function body
```

## Syntax Mapping: Erlang → Elixir Concepts

| Concept | Erlang | Elixir |
|---------|--------|--------|
| Module | `-module(name).` | `defmodule Name do` |
| Public func | `func() -> ...` + `-export([func/0]).` | `def func do` |
| Private func | `func() -> ...` (not exported) | `defp func do` |
| Type spec | `-spec func(T) -> R.` | `@spec func(t) :: r` |
| Type def | `-type t() :: ...` | `@type t :: ...` |
| Record | `-record(name, {...}).` | `defstruct [...]` |
| Import | `-import(mod, [f/n]).` | `import Mod` |

## Files Created/Modified

**New files:**
- `cicada/languages/erlang/__init__.py`
- `cicada/languages/erlang/parser.py` (~130 lines)
- `cicada/languages/erlang/indexer.py` (~100 lines)
- `cicada/languages/erlang/formatter.py` (~20 lines)
- `cicada/languages/erlang/extractors/__init__.py`
- `cicada/languages/erlang/extractors/doc.py` (~180 lines)
- `tests/erlang/test_parser.py` (6 tests)
- `tests/erlang/test_indexer.py` (3 tests)
- `tests/fixtures/sample.erl`
- `tests/fixtures/sample_with_docs.erl`

**Modified files:**
- `cicada/languages/__init__.py` - Register Erlang
- `cicada/languages/formatter_registry.py` - Add ErlangFormatter
- `cicada/parsing/language_config.py` - Add `default_erlang()`
- `cicada/setup.py` - Add Erlang detection

## Usage

### CLI

```bash
# Setup Erlang project
cd /path/to/erlang-project
cicada claude

# Output:
# Indexed 26 Erlang modules (630 functions)
```

### Python API

```python
from cicada.languages.erlang.parser import ErlangParser
from cicada.languages.erlang.indexer import ErlangIndexer

# Parse single file
parser = ErlangParser()
modules = parser.parse_file("path/to/module.erl")

# Index entire repository
indexer = ErlangIndexer()
result = indexer.index_repository(
    "/path/to/erlang-project",
    "/path/to/output.json",
    verbose=True
)
```

## Remaining Work (Optional Future Enhancements)

### Phase 5: Dependency Extraction
- [ ] Parse `-import` declarations
- [ ] Extract function call sites
- [ ] Module dependency graph

### Phase 6: Advanced Features
- [ ] Handle multiple function clauses (pattern matching)
- [ ] Extract `-spec` attributes
- [x] ~~Extract function documentation (`%% @doc`)~~ ✅ Done
- [x] ~~Keyword extraction from docs~~ ✅ Done
- [x] ~~Semantic search enabled~~ ✅ Done
- [ ] `-type`, `-opaque` definitions
- [ ] `-record` definitions
- [ ] `-behaviour`/`-callback` support
- [ ] Header file (`.hrl`) imports tracking

## Test Results

Tested on [PURITY](https://github.com/mpitid/purity) (side-effect analyzer for Erlang):

| Metric | Value |
|--------|-------|
| Files indexed | 30 |
| Modules found | 26 |
| Functions parsed | 630 |
| Errors | 0 |

## Dependencies

```toml
# pyproject.toml
"tree-sitter-language-pack>=0.13.0",
```

This package bundles 40+ language grammars including Erlang (31.5MB).
