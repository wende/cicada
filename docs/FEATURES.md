# Cicada Feature Implementation Matrix

**Last Updated:** 2025-01-04
**Branch:** `feat/language-agnostic`

This document tracks feature implementation status across all supported and planned languages.

---

## Feature Implementation Status

| Feature | Elixir | Python | TypeScript |
|---------|--------|--------|------------|
| **1. Code indexing** | ✅ 100% | ✅ 100% | ⚠️ Ready* |
| **2. AST-aware code search** | ✅ 100% | ✅ 100% | ⚠️ Ready* |
| **3. Function signature resolution** | ✅ 100% | ✅ 100% | ⚠️ Ready* |
| **4. Function and module usage search** | ✅ 100% | ⚠️ 60% | ⚠️ 60%* |
| **5. Intelligent call site tracking** | ✅ 100% | ⚠️ 60% | ⚠️ 60%* |
| **6. PR attribution & review** | ✅ 100% | ✅ 100% | ✅ 100%* |
| **7. Function evolution tracking** | ✅ 100% | ✅ 100% | ✅ 100%* |
| **8. Semantic module analysis** | ✅ 100% | ⚠️ 40% | ⚠️ 40%* |
| **9. Semantic keyword search** | ✅ 100% | ✅ 100% | ✅ 100%* |
| **10. Find dead code** | ✅ 100% | ⚠️ Blocked‡ | ⚠️ Blocked‡ |
| **11. Function usage in tests** | ✅ 100% | 🔜 Planned | 🔜 Planned |
| **Overall Completion** | **100%** | **85%** | **85%*** |

### Legend

- ✅ **100%** - Fully implemented and production-ready
- ⚠️ **XX%** - Partially implemented (see notes below)
- ⚠️ **Ready*** - Infrastructure ready, needs indexer wrapper (5-8 hours)
- ⚠️ **Blocked** - Depends on another incomplete feature
- 🔜 **Planned** - Planned for future release
- ❌ **Not Available** - Not planned or not applicable

### Notes

- `*` **TypeScript (Ready)**: All infrastructure exists and proven working via test fixtures. Just needs indexer wrapper (~20 lines of config) + CLI integration. Will inherit all Python features and gaps. **Estimated: 5-8 hours.**

- `‡` **Blocked by Feature #5**: Dead code detection requires complete call site tracking (Feature #5) to identify unused functions.

---

## Implementation Details by Language

### Elixir (100% Complete) 🎉

**Status:** Production-ready, primary language
**Implementation:** Tree-sitter AST parsing + custom extractors
**Test Coverage:** 86/86 tests passing (100%)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Code indexing | ✅ Complete | Tree-sitter AST parsing + incremental indexing |
| AST-aware search | ✅ Complete | Full AST extraction with module/function discovery |
| Function signatures | ✅ Complete | Type specs, parameters, return types, arity |
| Usage search | ✅ Complete | Find all function calls and module imports |
| Call site tracking | ✅ Complete | Alias resolution, cross-file tracking |
| PR attribution | ✅ Complete | Git blame + GitHub CLI integration |
| Function evolution | ✅ Complete | Git history with function-level tracking |
| Module analysis | ✅ Complete | Dependency graphs, import tracking, relationships |
| Keyword search | ✅ Complete | KeyBERT + GloVe expansion |
| Dead code detection | ✅ Complete | Three confidence levels, behavior-aware |
| Function usage in tests | ✅ Complete | Test file filtering + call site analysis |

**Strengths:**
- Incremental indexing (15-25x faster reindexing)
- Full module dependency tracking
- Comprehensive call site analysis
- Alias resolution across modules
- Test coverage tracking and analysis

---

### Python (85% Complete) 🚧

**Status:** MVP ready, some gaps
**Implementation:** SCIP protocol via scip-python (Pyright)
**Test Coverage:** 62/63 tests passing (98%)
**Requires:** Node.js/npm for scip-python

| Feature | Status | Implementation | Known Issues |
|---------|--------|----------------|--------------|
| Code indexing | ✅ 100% | scip-python (Pyright) generates SCIP index | Full reindex only (no incremental) |
| AST-aware search | ✅ 100% | SCIP converter extracts all symbols | None |
| Function signatures | ✅ 100% | Full type hint extraction via Pyright | None |
| Usage search | ⚠️ 60% | Basic function lookup works | Cross-file usage incomplete |
| Call site tracking | ⚠️ 60% | Basic detection works | Cross-file tracking incomplete |
| PR attribution | ✅ 100% | Language-independent (Git) | None |
| Function evolution | ✅ 100% | Language-independent (Git) | None |
| Module analysis | ⚠️ 40% | Structure extraction works | Import tracking not implemented |
| Keyword search | ✅ 100% | KeyBERT + GloVe on docstrings | None |
| Dead code detection | ⚠️ Blocked | Infrastructure exists | Needs complete call tracking |
| Function usage in tests | 🔜 Planned | Test file filtering + call analysis | Depends on Feature #5 |

**Working Well:**
- ✅ Type-aware indexing via Pyright (Feature #1)
- ✅ Function/module discovery (Feature #2)
- ✅ Full function signatures with type hints (Feature #3)
- ✅ Docstring extraction
- ✅ Class/module structure
- ✅ Semantic keyword search (Feature #9)
- ✅ PR/Git features (Features #6, #7)

**Known Gaps:**
- ⚠️ Usage search incomplete (Feature #4) - cross-file tracking missing
- ⚠️ Call site tracking 60% (Feature #5) - 10 tests skipped
- ⚠️ Module analysis 40% (Feature #8) - import tracking not implemented
- ⚠️ Dead code blocked (Feature #10) - needs Feature #5
- ⚠️ Full reindex only (no incremental updates yet)
- ⚠️ Indexing slower than Elixir (2-5 minutes for medium projects)

**Priority Fixes:**
1. **Call site extraction** (4-6 hours) - Complete Feature #5, enables Feature #4 and #10
2. **Dependency extraction** (2-3 hours) - Complete Feature #8 (module analysis)
3. **Incremental indexing** (8-12 hours) - Performance improvement for Feature #1

---

### TypeScript (85% Complete*) 🏗️

**Status:** Infrastructure ready, needs wrapper
**Implementation:** SCIP protocol via scip-typescript
**Test Coverage:** Proven via test fixtures + 19 meta-tests
**Requires:** Node.js/npm for scip-typescript

| Feature | Status | Implementation | Notes |
|---------|--------|----------------|-------|
| Code indexing | ⚠️ Ready* | scip-typescript via npm | Needs indexer wrapper |
| AST-aware search | ⚠️ Ready* | Generic SCIP converter | Proven working in tests |
| Function signatures | ⚠️ Ready* | TypeScript type extraction | Proven in fixtures |
| Usage search | ⚠️ 60%* | Same as Python | Inherits Python gaps |
| Call site tracking | ⚠️ 60%* | Same as Python | Inherits Python gaps |
| PR attribution | ✅ 100%* | Language-independent | Ready to use |
| Function evolution | ✅ 100%* | Language-independent | Ready to use |
| Module analysis | ⚠️ 40%* | Same as Python | Inherits Python gaps |
| Keyword search | ✅ 100%* | Same as Python | Ready to use |
| Dead code detection | ⚠️ Blocked* | Same as Python | Needs call tracking |
| Function usage in tests | 🔜 Planned* | Same as Python | Depends on Feature #5 |

**What Exists:**
- ✅ Test fixtures with TypeScript code
- ✅ SCIP indexes generated successfully
- ✅ Converter handles TypeScript identically to Python
- ✅ 19/19 meta-tests prove language-agnostic architecture works

**What's Needed (5-8 hours):**
1. Create `cicada/languages/typescript/indexer.py` (~20 lines)
2. Update language detection for `.ts`/`.tsx` files
3. Add TypeScript to CLI commands
4. Auto-install scip-typescript via npm
5. Integration testing

**Will Inherit:**
- ✅ Features #1, #2, #3: Indexing, search, signatures (100%)
- ✅ Features #6, #7: PR attribution, function evolution (100%)
- ✅ Feature #9: Keyword search (100%)
- ⚠️ Features #4, #5: Usage search, call tracking (60%)
- ⚠️ Feature #8: Module analysis (40%)
- ⚠️ Feature #10: Dead code (blocked)

**Timeline:** 5-8 hours to MVP TypeScript support

---

### Future SCIP Languages (Go, Rust, Java, etc.)

**Status:** Not currently planned
**Potential Implementation:** SCIP protocol via language-specific indexers

If we were to add additional SCIP-supported languages in the future:
- Would require generic SCIP indexer refactor (8-12 hours one-time cost)
- Each new language would then be ~6-20 lines of configuration
- Would inherit all SCIP layer features and gaps
- Estimated: 1-2 hours per language after refactor

**Currently focusing on:** Completing Elixir, Python, and TypeScript support first.

---

## Critical Gaps Affecting Multiple Languages

### 🔴 Priority 1: Call Site Extraction

**Affects:** Python, TypeScript (all SCIP languages)
**Impact:** HIGH - Core "find usages" feature incomplete
**Status:** 60% complete
**Blocker for:** Dead code detection

**What's Missing:**
- Cross-file call tracking incomplete
- `calls` field not consistently populated in function data
- Enclosing function detection has edge cases

**Tests Awaiting:** 10 skipped tests in `test_scip_references.py`

**Fix Required:**
- Complete `_extract_call_sites()` in `cicada/languages/scip/converter.py`
- Fix `_find_enclosing_function()` helper
- Enable cross-file reference tests

**Estimated Time:** 4-6 hours
**Benefit:** Fixes call tracking for ALL SCIP languages at once!

---

### 🟡 Priority 2: Dependency Extraction

**Affects:** Python, TypeScript (all SCIP languages)
**Impact:** MEDIUM - Module analysis incomplete
**Status:** Not implemented

**What's Missing:**
- Import statement extraction from SCIP occurrences
- Module dependency mapping
- `dependencies` field population

**Fix Required:**
- Extract `Import` role from SCIP occurrences
- Map imported symbols to source modules
- Populate dependency relationships

**Estimated Time:** 2-3 hours
**Benefit:** Enables full module analysis for ALL SCIP languages!

---

### 🟢 Priority 3: Generic SCIP Refactor

**Affects:** Developer experience, new language addition
**Impact:** LOW - Code quality improvement
**Status:** Not started (see `docs/SCIP_IMPLEMENTATION_PLAN.md`)

**What It Enables:**
- Reduce Python indexer from 272 lines to ~20 lines
- New SCIP languages become trivial (6 lines of config)
- 78% code reduction at scale (for 5 languages)

**Estimated Time:** 8-12 hours
**Benefit:** Would make adding additional SCIP languages trivial (1 hour each)

---

## Feature Descriptions

### 1. Code Indexing
Generate structured index of codebase for fast lookups.

**Capabilities:**
- Parse source files and extract structure
- Generate searchable index with modules, functions, calls
- Store metadata (line numbers, types, signatures)
- Support incremental updates (Elixir only)
- Keyword extraction for semantic search
- Fast index generation

**Implementation:**
- **Elixir:** Tree-sitter AST parsing (incremental, 15-25x faster reindexing)
- **Python:** SCIP via scip-python/Pyright (full reindex only, 2-5 min)
- **TypeScript:** SCIP via scip-typescript (needs wrapper)

**CLI Commands:** `cicada index`, `cicada index --fast/--regular/--max`

---

### 2. AST-aware Code Search
Find modules, classes, and function definitions across the codebase.

**Capabilities:**
- Module search with complete API listing
- Function/class discovery by name
- File path and line number navigation
- Public/private function filtering
- Documentation preview
- Arity-based function search (e.g., `add/2`)
- Fast symbol lookup

**What "AST-aware" Means:**
Unlike grep/text search, this understands code structure:
- Distinguishes function definitions from calls
- Understands module boundaries
- Respects scope (public vs private)
- Extracts structured metadata (not just text)

**MCP Tools:** `search_module`, `search_function`
**Example:** "Show me all functions in the User module" → Returns structured list with signatures, not raw code

---

### 3. Function Signature Resolution
Extract complete function signatures with types, parameters, and documentation.

**Capabilities:**
- Parameter names and types
- Return type extraction
- Type hints/annotations
- Arity information (number of parameters)
- Default values
- Docstring/documentation
- Type specifications (Elixir `@spec`, Python type hints, TypeScript types)

**What "Signature Resolution" Means:**
The ability to extract and parse function signatures from various type systems:
- **Python:** `def add(x: int, y: int) -> int` → Extract `x: int`, `y: int`, returns `int`
- **TypeScript:** `function add(x: number, y: number): number` → Same structure
- **Elixir:** `@spec add(integer, integer) :: integer` → Parse type specs

**Implementation:**
- **Elixir:** Parse `@spec` attributes and function heads
- **Python:** Extract type hints via Pyright/SCIP
- **TypeScript:** Extract TypeScript types via SCIP

**MCP Tools:** `search_function` (includes signature in results)
**Example:** "What's the signature of the authenticate function?" → Returns full type information

---

### 4. Function and Module Usage Search
Find where functions are called and modules are imported across the entire codebase.

**Capabilities:**
- Find all call sites for any function
- See actual usage examples with context
- Track which modules use which other modules
- Cross-file reference tracking
- Line numbers for each usage
- Caller context (which function calls what)
- Import/alias tracking

**What "Usage Search" Means:**
Answer questions like:
- "Where is `authenticate/2` called?" → List all call sites
- "Which modules import `MyApp.User`?" → List all importers
- "Show me examples of how to use this function" → Real code snippets
- "What depends on this module?" → Full dependency list

**Difference from Call Site Tracking (Feature #5):**
- **Usage Search:** High-level "show me all usages" (user-facing)
- **Call Site Tracking:** Technical implementation (alias resolution, cross-file tracking)

**MCP Tools:** `search_function` (call sites section), `search_module_usage`
**Example:** "Where is the process_payment function used?" → Returns all files and line numbers

---

### 5. Intelligent Call Site Tracking
Technical infrastructure for accurate cross-file call tracking with alias resolution.

**Capabilities:**
- Alias resolution (track imports/uses)
- Cross-file reference tracking
- Handle renamed imports
- Track qualified vs unqualified calls
- Map symbols across modules
- Handle complex import patterns

**What "Intelligent" Means:**
Not just text matching - understands import semantics:

**Example (Elixir):**
```elixir
# file_a.ex
alias MyApp.User, as: U
U.authenticate(user)  # Track this as MyApp.User.authenticate
```

**Example (Python):**
```python
# file_a.py
from myapp.user import authenticate as auth
auth(user)  # Track this as myapp.user.authenticate
```

The system resolves `U.authenticate` → `MyApp.User.authenticate` and `auth` → `myapp.user.authenticate`.

**Why This Matters:**
- Text search for "authenticate" misses aliased calls
- Must resolve aliases to find all true usages
- Enables accurate usage search (Feature #4)
- Enables dead code detection (Feature #10)

**Implementation:**
- **Elixir:** Parse `alias`, `import`, `use` directives
- **Python/TypeScript:** Parse SCIP symbol references with alias mapping

**Status:**
- ✅ Elixir: 100% complete with full alias resolution
- ⚠️ Python/TypeScript: 60% (basic detection, cross-file gaps)

---

### 6. PR Attribution & Review Context
Discover which pull request introduced any line and view historical code review discussions inline.

**Capabilities:**
- Line-level PR attribution via git blame
- Author and commit information
- Direct links to GitHub PRs
- PR descriptions and metadata
- Code review comments mapped to line numbers
- Timeline of changes

**MCP Tools:** `find_pr_for_line`, `get_file_pr_history`
**Requirements:** GitHub CLI + PR index

---

### 7. Function Evolution Tracking
See when functions were created, how often they're modified, and their complete git history.

**Capabilities:**
- Complete commit history for files
- Function-level tracking (follows refactors)
- Creation and modification timeline
- Author attribution
- Commit messages and dates
- Frequency analysis

**MCP Tools:** `get_commit_history`, `get_blame`
**Requirements:** `.gitattributes` configuration for function-level tracking

---

### 8. Semantic Module Analysis
Understand module dependencies, imports, and relationships through structural analysis.

**What "Semantic" Means:**
Goes beyond text search to understand the **meaning** and **relationships** in your code:

**Text Search Limitations:**
```python
# file_a.py
import user_service
from auth import verify
```
- Text search: Finds the word "user_service" and "verify"
- No understanding of what imports what
- No dependency graph
- Can't answer "What depends on auth?"

**Semantic Analysis:**
- **Parses import statements** → Knows file_a.py depends on user_service and auth
- **Builds dependency graph** → Can show all modules that import auth
- **Tracks relationships** → "auth is a dependency of file_a.py"
- **Understands direction** → file_a.py imports from auth (not vice versa)

**Capabilities:**
- **Dependency Graphs:** Visual map of module relationships
- **Import Tracking:** See all import statements for a module
- **Dependency Mapping:** Find all modules that depend on X
- **Module Usage Patterns:** How modules interact with each other
- **Cross-Module Relationships:** Understand coupling between modules
- **Find All Callers:** Which modules call functions from module X
- **Circular Dependency Detection:** Identify import cycles

**Real-World Questions It Answers:**
- "If I change module X, what else breaks?" → Show all dependent modules
- "What does module Y depend on?" → Show all imports
- "Which modules use the User module?" → List all importers
- "Is there a circular dependency?" → Detect import cycles

**Example:**
```
search_module_usage("MyApp.User")
→ Returns:
  - Imported by: MyApp.Auth, MyApp.Posts, MyApp.Comments
  - Calls functions: MyApp.Repo, MyApp.Crypto
  - Dependency graph: [visual representation]
```

**Implementation:**
- **Elixir:** Parse `alias`, `import`, `use`, `require` + track function calls
- **Python/TypeScript:** Extract from SCIP `Import` role (partially implemented)

**Status:**
- ✅ Elixir: 100% complete with full dependency tracking
- ⚠️ Python/TypeScript: 40% (structure extraction works, import tracking incomplete)

**MCP Tools:** `search_module_usage`

---

### 9. Semantic Keyword Search (EXPERIMENTAL)
AI-powered semantic search across codebase using extracted keywords from documentation.

**Capabilities:**
- Find code by concepts, not just names
- Wildcard pattern matching (`create*`, `*_user`)
- Semantic relevance scoring
- Filter by modules, functions, or all
- Three model tiers (fast/regular/max)
- KeyBERT extraction + GloVe expansion

**MCP Tools:** `search_by_keywords`
**Requirements:** Index with keyword extraction (`--fast`, `--regular`, or `--max`)

---

### 10. Find Dead Code
Identify potentially unused functions with confidence levels.

**Capabilities:**
- Three confidence levels (high/medium/low)
- Smart detection of callbacks and behaviors
- Recognition of dynamic call patterns
- Module-level grouping with line numbers
- Excludes test files and `@impl` functions
- Safe suggestions (avoids false positives)

**MCP Tools:** `find_dead_code` (CLI and MCP)
**Requirements:** Complete call site tracking

---

### 11. Function Usage in Tests
Understand how functions are tested and discover test coverage patterns.

**Capabilities:**
- Find all test files that use a specific function
- See actual test examples and usage patterns
- Identify functions without test coverage
- Track test-to-production code ratio
- Discover test naming conventions
- View test context and assertions
- Map functions to their test files

**What "Function Usage in Tests" Means:**
Answer questions like:
- "Which tests call the `authenticate` function?" → List all test files and line numbers
- "Does this function have test coverage?" → Show test examples or flag as untested
- "How is this function tested?" → Show real test code snippets
- "What's the test coverage pattern for this module?" → Show which functions have tests

**Real-World Questions It Answers:**
- "Before refactoring this function, what tests will break?" → Show all affected tests
- "How should I test this function?" → Show examples from similar functions
- "Which functions lack test coverage?" → Identify untested code
- "What's the test coverage for critical path functions?" → Analyze test patterns

**Example:**
```
search_function("process_payment")
→ Returns:
  - Definition: src/payments.py:145
  - Tests found: 5 test files
    - tests/test_payments.py:23 (test_process_payment_success)
    - tests/test_payments.py:45 (test_process_payment_failure)
    - tests/integration/test_checkout.py:89 (test_full_checkout_flow)
    - tests/test_refunds.py:12 (test_refund_after_payment)
    - tests/test_analytics.py:56 (test_payment_tracking)
  - Coverage: 85% of function paths tested
```

**Implementation:**
- **Elixir:** Fully implemented - analyzes call sites in test files (`*_test.exs`)
- **Python/TypeScript:** Planned - will filter by test patterns (`test_*.py`, `*_test.py`, `*.spec.ts`)
- Extract test function names and assertions
- Map production functions to their test usages

**Status:**
- ✅ Elixir: 100% complete with full test coverage tracking
- 🔜 Python/TypeScript: Planned (depends on Feature #5 completion)
- Leverages existing usage search infrastructure

**Benefits:**
- Improve test discoverability
- Reduce fear of refactoring (know what tests exist)
- Learn testing patterns from existing code
- Identify gaps in test coverage
- Better understand code quality

**MCP Tools:** `search_function` (with test filter option), `find_test_coverage`
**Requirements:** Complete call site tracking (Feature #5)

---

## Testing Summary

| Language | Tests | Status | Pass Rate | Coverage |
|----------|-------|--------|-----------|----------|
| **Elixir** | 86 | All passing | 100% | All 11 features |
| **Python** | 63 | 62 passing, 1 failing | 98% | 7/10 features complete |
| **SCIP (generic)** | 138 | 128 passing, 10 skipped | 93% | Language-agnostic layer |
| **Overall** | ~1400 | ~1390 passing | ~99% | Comprehensive |

**Feature Test Coverage:**
- ✅ Code indexing: Full coverage (Elixir + Python)
- ✅ AST-aware search: Full coverage (all languages)
- ✅ Function signatures: Full coverage (all languages)
- ⚠️ Usage search: Partial (10 tests skipped for cross-file tracking)
- ⚠️ Call site tracking: Partial (60% complete for Python/TypeScript)
- ✅ PR attribution: Full coverage (language-independent)
- ✅ Function evolution: Full coverage (language-independent)
- ⚠️ Module analysis: Partial (import tracking incomplete)
- ✅ Keyword search: Full coverage (all languages)
- ⚠️ Dead code detection: Blocked by call site tracking
- ✅ Function usage in tests: Full coverage (Elixir), planned for Python/TypeScript

---

## Roadmap

### Immediate (Current Sprint)
1. **Fix call site extraction** (4-6 hours) → Benefits all SCIP languages
2. **Add TypeScript support** (5-8 hours) → Deliver on roadmap promise
3. **Complete dependency extraction** (2-3 hours) → Full module analysis

### Short-Term (Next Release)
1. **Generic SCIP refactor** (8-12 hours) → Reduces code duplication
2. **Incremental indexing for Python** → 15-25x faster reindexing
3. **Enhanced module analysis** → Complete import/dependency tracking

### Long-Term
1. **Real-time incremental indexing** → Watch mode for instant updates
2. **Web UI for exploration** → Visual codebase navigation
3. **Additional SCIP languages** → If demand warrants (Go, Rust, Java, etc.)

---

## Language Selection Guide

**Choose Elixir Support If:**
- ✅ You need 100% feature completion
- ✅ You want incremental indexing (fastest)
- ✅ You need comprehensive dependency analysis
- ✅ You want dead code detection

**Choose Python Support If:**
- ✅ You need type-aware indexing (Pyright)
- ✅ You're okay with MVP features (85% complete)
- ✅ You can wait for call tracking improvements
- ⚠️ You accept full reindex only (for now)

**Choose TypeScript Support If:**
- ⚠️ You can wait 5-8 hours for implementation
- ✅ You're okay with Python feature parity (85%)
- ✅ You need it soon (quickest to add)

**Future Languages:**
- Currently not planned
- Focus is on completing Elixir, Python, and TypeScript support

---

## Contributing

Want to help improve feature coverage?

**High Impact:**
- Fix call site extraction ([see issue](#))
- Implement dependency extraction ([see issue](#))
- Add TypeScript indexer wrapper ([see issue](#))

**Medium Impact:**
- Add incremental indexing for Python
- Complete generic SCIP refactor
- Add Go language support

**Documentation:**
- Update this table as features are completed
- Add examples for each feature
- Create language-specific guides

---

## References

- **Architecture:** `docs/UNIVERSAL_SCIP.md`
- **Implementation Status:** `docs/IMPLEMENTATION_STATUS.md`
- **SCIP Plan:** `docs/SCIP_IMPLEMENTATION_PLAN.md`
- **README:** Main feature descriptions
- **MCP Tools:** `docs/MCP-Tools-Reference.md`
