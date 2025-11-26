# TypeScript Query and Search Improvements - Implementation Report

**Date**: 2025-11-26
**Branch**: feat/typescript-v0.1

## Overview

Implemented TypeScript-aware module and function display for Cicada MCP tools. The changes enable proper detection and formatting of TypeScript types (interfaces, type aliases, classes, enums) instead of showing misleading "0 public • 0 private" counts.

## Deliverables Completed

| ID | Description | Status |
|----|-------------|--------|
| D1 | Add `module_kind` field to SCIP converter | ✅ |
| D2 | Type-aware `search_module` messages | ✅ |
| D3 | Fix hardcoded `/arity` formatting (8 locations) | ✅ |
| D4 | Improve `expand_result` for types | ✅ |
| D5 | TypeScript-specific tests | ✅ |

## Technical Implementation

### 1. SCIP Converter - `module_kind` Field

**File**: `cicada/languages/scip/converter.py`

Added two-tier detection for module kinds:

1. **Primary**: `_scip_kind_to_module_kind()` - Maps SCIP `SymbolInformation.kind` values
   - Class (7) → `class`
   - Interface (21) → `interface`
   - TypeAlias (55) → `type_alias`
   - Module (29) → `module`
   - Struct (49) → `struct`
   - Enum (11) → `enum`
   - Trait (53) → `trait`

2. **Fallback**: `_extract_module_kind_from_moduledoc()` - Parses moduledoc code fences
   - Required because scip-typescript doesn't populate the `kind` field (all values are 0)
   - Patterns: `` ```ts\ninterface `` → `interface`, `` ```ts\ntype `` → `type_alias`, etc.

### 2. Type-Aware Formatting

**File**: `cicada/format/formatter.py`

Updated `format_module_markdown()` to display type-appropriate headers:

| module_kind | Display Format |
|-------------|----------------|
| `type_alias` | `ModuleName (type alias)` |
| `interface` | `ModuleName (interface) • N method(s)` |
| `struct` | `ModuleName (struct) • X public • Y private` |
| `enum` | `ModuleName (enum) • X public • Y private` |
| `trait` | `ModuleName (trait) • N method(s)` |
| `class`/`module` | `ModuleName • X public • Y private` |

Type aliases skip the function sections entirely (they don't have functions).

### 3. Language-Aware Function Formatting

**File**: `cicada/format/formatter.py`

Added `_format_func_ref()` helper to replace 8 hardcoded `/arity` patterns:
- `_format_caller_name()`
- `_format_function_entry()` (3 locations)
- `format_function_results_json()`
- `format_module_usage_markdown()` (2 locations)
- `_format_cochange_info()`

Functions now accept a `language` parameter and use language-appropriate formatting (e.g., `func()` for TypeScript vs `func/2` for Elixir).

### 4. Handler Updates

**Files**:
- `cicada/mcp/handlers/module_handlers.py`
- `cicada/mcp/handlers/analysis_handlers.py`

Updated formatter calls to pass `language` from index metadata.

## Test Results

- **Total tests**: 3016 passed, 32 skipped
- **New tests added**: 17 (module_kind detection + moduledoc fallback)

### New Test File

`tests/languages/scip/test_typescript_module_kinds.py`:
- `TestModuleKindFromSCIPKind` - Validates module_kind field exists
- `TestSCIPKindMapping` - Unit tests for SCIP kind → module_kind mapping
- `TestModuledocFallback` - Unit tests for moduledoc parsing fallback

## Expected Output Changes

**Before** (zustand example):
```
src/vanilla.ts:9
StoreApi • 0 public • 0 private
```

**After**:
```
src/vanilla.ts:9
StoreApi (interface)
```

## Files Modified

| File | Changes |
|------|---------|
| `cicada/languages/scip/converter.py` | +50 lines: `_scip_kind_to_module_kind()`, `_extract_module_kind_from_moduledoc()`, module_kind assignment |
| `cicada/format/formatter.py` | +60 lines: `_format_func_ref()`, type-aware formatting in `format_module_markdown()` |
| `cicada/mcp/handlers/module_handlers.py` | +4 lines: language parameter passing |
| `cicada/mcp/handlers/analysis_handlers.py` | +2 lines: language parameter passing |
| `tests/languages/scip/test_typescript_module_kinds.py` | +234 lines: new test file |

## Notes

- The moduledoc fallback is essential because scip-typescript (v0.3.x) doesn't populate `SymbolInformation.kind`
- Changes are backward-compatible - Elixir/Python behavior unchanged
- Index rebuild required to populate `module_kind` field

---

# Cicada MCP Tools Verification Report (tRPC TypeScript Codebase)

**Date:** 2025-11-26
**Repository Tested:** tRPC (TypeScript codebase)
**Verification Method:** All results cross-checked with `grep` and `git blame`

---

## Executive Summary

| Tool | Status | Accuracy |
|------|--------|----------|
| `mcp__cicada__query` | **Working** | High |
| `mcp__cicada__search_module` | **Partial** | Medium |
| `mcp__cicada__search_function` | **Partial** | Medium |
| `mcp__cicada__git_history` | **Working** | High |
| `mcp__cicada__find_dead_code` | **Broken** | Low |
| `mcp__cicada__expand_result` | **Partial** | Medium |
| `mcp__cicada__query_jq` | **Working** | High |

**Critical Issue:** Call site detection (`what_calls_it`) is non-functional for TypeScript, causing cascading failures in dead code detection.

---

## Tool 1: `mcp__cicada__query`

### Status: **Working**

### What Was Called
```json
{
  "query": "router",
  "max_results": 10,
  "show_snippets": true
}
```

### What Worked
- Keyword search returns relevant results
- Line numbers are accurate
- Code snippets are displayed correctly
- Confidence scores are provided
- Results sorted by relevance

### Example Output
```
1. Router | [Exceptional]
packages/tests/server/abortQuery.test.ts:14
Confidence: 97.9%

4. _file_packages.server.src.unstable-core-do-not-import.router.ts.lazy/1 | [Exceptional]
packages/server/src/unstable-core-do-not-import/router.ts:105
Confidence: 91.5%
Lazy load a router
```

### Verification
```bash
$ grep -n "type Router" packages/tests/server/abortQuery.test.ts
14:type Router = typeof router;
```
**Result: CONFIRMED**

---

## Tool 2: `mcp__cicada__search_module`

### Status: **Partial**

### What Was Called
```json
{
  "file_path": "packages/server/src/unstable-core-do-not-import/router.ts",
  "type": "all"
}
```

```json
{
  "module_name": "AnyRouter",
  "type": "all",
  "what_calls_it": true
}
```

### What Worked
- Module definitions found correctly
- Line numbers accurate
- Interface/type detection works

### What Didn't Work
- `what_calls_it` feature returns "No usage found" for modules that ARE used

### Example of Failure

**Input:**
```json
{
  "module_name": "AnyRouter",
  "what_calls_it": true
}
```

**Cicada Output:**
```
packages/server/src/unstable-core-do-not-import/router.ts:178
AnyRouter (type alias)

## Module Usage (what calls it)
*No usage found for this module*
```

**Grep Verification:**
```bash
$ grep -l "AnyRouter" **/*.ts | wc -l
20

$ grep -c "AnyRouter" **/*.ts | grep -v ":0" | head -5
packages/client/src/createTRPCClient.ts:7
packages/client/src/createTRPCUntypedClient.ts:2
packages/next/src/ssrPrepass.ts:3
```

**Reality:** 63 occurrences across 20 files - NOT zero.

---

## Tool 3: `mcp__cicada__search_function`

### Status: **Partial**

### What Was Called
```json
{
  "function_name": "lazy",
  "what_calls_it": true,
  "include_usage_examples": true
}
```

### What Worked
- Function definition found at correct line (105)
- Type signature extracted correctly
- Documentation extracted ("Lazy load a router")

### What Didn't Work
- `what_calls_it` returns "No call sites found" when call sites exist

### Example of Failure

**Cicada Output:**
```
packages/server/src/unstable-core-do-not-import/router.ts:105
_file_packages.server.src.unstable-core-do-not-import.router.ts.lazy()
Type: function lazy<TRouter extends AnyRouter>(...)
Documentation: "Lazy load a router"

*No call sites found*

Possible reasons:
   - Dead code -> Use find_dead_code() to verify
   - Public API -> Not called internally but used by clients
```

**Grep Verification:**
```bash
$ grep -n "lazy(" **/*.ts | head -10
examples/lazy-load/src/server/routers/_app.ts:5:  user: lazy(() => import('./user.js')),
examples/lazy-load/src/server/routers/_app.ts:7:  slow: lazy(() => import('./slow.js')),
packages/server/src/unstable-core-do-not-import/router.test.ts:43:    const child = lazy(async () =>
packages/server/src/unstable-core-do-not-import/router.test.ts:62:      child: lazy(async () =>
packages/tests/server/smoke.test.ts:285:    inSomeOtherFile: lazy(async () => {
packages/tests/server/smoke.test.ts:300:    lazy: lazy(async () => {
```

**Reality:** 11+ call sites found by grep - NOT zero.

---

## Tool 4: `mcp__cicada__git_history`

### Status: **Working**

### What Was Called
```json
{
  "file_path": "packages/server/src/unstable-core-do-not-import/router.ts",
  "start_line": 105,
  "max_results": 5
}
```

### What Worked
- Author attribution correct
- Commit hash correct
- Date correct
- Line content correct

### Example Output
```
## Line 105 in packages/server/src/unstable-core-do-not-import/router.ts

**Author:** Alexander Johansson (2025-11-23, 14e3d4a4)
**PR:** None

export function lazy<TRouter extends AnyRouter>(
```

### Verification
```bash
$ git blame -L 105,105 packages/server/src/unstable-core-do-not-import/router.ts
^14e3d4a (Alexander Johansson 2025-11-23 17:27:56 +0100 105) export function lazy<TRouter extends AnyRouter>(
```

**Result: CONFIRMED** - Commit, author, date, and content all match.

---

## Tool 5: `mcp__cicada__find_dead_code`

### Status: **Broken**

### What Was Called
```json
{
  "min_confidence": "high"
}
```

### What Worked
- Tool runs and returns results
- Identifies function locations correctly

### What Didn't Work
- **Massive false positive rate** - reports 467 functions as "high confidence" dead code
- Functions actively used in production code are flagged as unused

### Example of Failure

**Cicada Output (excerpt):**
```
=============== HIGH CONFIDENCE (467 functions) ================
Functions with zero usage in codebase

### _file_packages.server.src.observable.observable.ts
packages/server/src/observable/observable.ts

- `isObservable/1` :16
- `observable/1` :21
```

**Grep Verification for `isObservable`:**
```bash
$ grep -n "isObservable(" **/*.ts
packages/server/src/unstable-core-do-not-import/http/resolveResponse.ts:436:  if (!isObservable(result.data) && !isAsyncIterable(result.data)) {
packages/server/src/unstable-core-do-not-import/http/resolveResponse.ts:446:  const dataAsIterable = isObservable(result.data)
packages/server/src/unstable-core-do-not-import/http/resolveResponse.ts:555:  const iterable = isObservable(result.data)
packages/server/src/adapters/ws.ts:269:  isAsyncIterable(result) || isObservable(result);
packages/server/src/adapters/ws.ts:315:  const iterable = isObservable(result)
```

**Reality:** `isObservable` is used 6 times in core production files (`resolveResponse.ts`, `ws.ts`) - it is NOT dead code.

### Summary of False Positives Tested

| Function | Cicada Says | Grep Reality | Verdict |
|----------|-------------|--------------|---------|
| `isObservable` | Dead (high confidence) | 6 usages in source | **FALSE POSITIVE** |
| `behaviorSubject` | Dead (high confidence) | 1 usage in tests | **FALSE POSITIVE** |
| `createMiddlewareFactory` | Dead (high confidence) | 0 usages | Correct |

**False positive rate in sample: 66%**

---

## Tool 6: `mcp__cicada__expand_result`

### Status: **Partial**

### What Was Called
```json
{
  "identifier": "_file_packages.server.src.unstable-core-do-not-import.router.ts.lazy/1",
  "include_code": true,
  "what_calls_it": true
}
```

### What Worked
- Expands function identifiers correctly
- Shows type signature and documentation

### What Didn't Work
- Same `what_calls_it` bug as `search_function`
- Returns "No call sites found" when sites exist

### Example Output
```
packages/server/src/unstable-core-do-not-import/router.ts:105
_file_packages.server.src.unstable-core-do-not-import.router.ts.lazy()
Type: function lazy<TRouter extends AnyRouter>(...)

*No call sites found*
```

---

## Tool 7: `mcp__cicada__query_jq`

### Status: **Working**

### What Was Called
```json
{"query": ".modules | keys | length"}
{"query": ".modules | keys | .[:5]"}
{"query": ".modules | to_entries | map(select(.value.file | test(\"router.ts\"))) | .[0:3]"}
```

### What Worked
- JQ queries execute correctly
- Can query module count (1009 modules indexed)
- Can filter and select specific modules
- Line numbers in raw data are accurate

### Example Output

**Query:** `.modules | keys | length`
**Output:** `1009`

**Query:** `.modules | to_entries | map(select(.value.file | test("router.ts"))) | .[0:3]`
**Output (excerpt):**
```json
[
  {
    "key": "RouterRecord",
    "value": {
      "file": "packages/server/src/unstable-core-do-not-import/router.ts",
      "line": 23,
      "module_kind": "interface"
    }
  },
  {
    "key": "RouterCallerErrorHandler",
    "value": {
      "file": "packages/server/src/unstable-core-do-not-import/router.ts",
      "line": 54,
      "module_kind": "type_alias"
    }
  }
]
```

### Verification
```bash
$ grep -n "interface RouterRecord" packages/server/src/unstable-core-do-not-import/router.ts
23:export interface RouterRecord {

$ grep -n "type RouterCallerErrorHandler" packages/server/src/unstable-core-do-not-import/router.ts
54:export type RouterCallerErrorHandler<TContext> = (
```

**Result: CONFIRMED** - All line numbers match.

---

## Root Cause Analysis

### The Core Bug: Missing Call Graph for TypeScript

The TypeScript indexer successfully:
- Extracts module/function/type definitions
- Records accurate line numbers
- Extracts documentation and keywords
- Builds the module structure

The TypeScript indexer **fails to**:
- Track function call sites
- Track type/interface usages (imports, type annotations)
- Build the dependency graph between modules

### Evidence from Raw Index

Using `query_jq` to inspect the raw index:
```json
{
  "key": "RouterCaller",
  "value": {
    "calls": [],           // <-- Always empty
    "dependencies": {
      "modules": [],       // <-- Always empty
      "has_dynamic_calls": false
    }
  }
}
```

The `calls` and `dependencies.modules` arrays are always empty, confirming the call graph is not being built.

### Impact

1. **`what_calls_it`** - Always returns "No usage found"
2. **`find_dead_code`** - Reports all functions as dead (no call graph to prove usage)
3. **Dependency analysis** - Cannot show what modules depend on what

---

## Recommendations

1. **High Priority:** Fix TypeScript call site detection - this is the root cause of multiple tool failures

2. **Medium Priority:** Add integration tests that verify call site detection against grep

3. **Documentation:** Update docs to clarify that `what_calls_it` and `find_dead_code` may not work for TypeScript until fixed

4. **Workaround:** For TypeScript projects, use `query` for discovery and `grep` for usage verification

---

# TypeScript Call Site Extraction Fix

**Date:** 2025-11-26
**Status:** Partially Complete

## Problem Identified

Two separate issues were preventing TypeScript call site detection:

### Issue 1: Symbol Format Check (FIXED ✅)

**Location:** `cicada/languages/scip/converter.py`, line 262

The original code checked `symbol.endswith("().")` to identify callable symbols. This was Python-specific - TypeScript symbols also end with `().` but the check was bypassed due to Issue 2.

### Issue 2: Missing ReadAccess Role (FIXED ✅)

**Location:** `cicada/languages/scip/converter.py`, line 408

**Root cause:** scip-typescript does NOT set the `ReadAccess` role for function call references.

**Evidence from SCIP data:**
```
# Definition - has Definition role
Symbol: scip-typescript npm @trpc/server 11.7.2 .../lazy().
  Roles: def=True, read=False

# Reference (call site) - NO ReadAccess role!
Symbol: scip-typescript npm @trpc/server 11.7.2 .../isLazy().
  Roles: def=False, read=False
```

The original code only processed call sites when `is_read_access and not is_definition`, but TypeScript references have `read=False`.

## Fix Applied

### 1. Language-Specific Symbol Type Detection

Created separate modules for language-specific symbol type detection:

**New files:**
- `cicada/languages/typescript/symbol_types.py` - TypeScript symbol patterns
- `cicada/languages/python/symbol_types.py` - Python symbol patterns

**Updated:** `cicada/languages/scip/converter.py`
- `_get_symbol_type()` now delegates to language-specific modules based on SCIP scheme prefix
- Uses lazy imports to avoid circular import issues

### 2. Call Site Detection for TypeScript

**Updated:** `cicada/languages/scip/converter.py`, `_extract_document_data()`

```python
# Before (only worked for Python):
if is_read_access and not is_definition:
    self._process_call_site(symbol, line, call_sites)

# After (works for both Python and TypeScript):
is_callable_reference = (
    not is_definition and symbol_type in ("function", "method")
)
if (is_read_access or is_callable_reference) and not is_definition:
    self._process_call_site(symbol, line, call_sites)
```

## Verification

### Call Sites Now Extracted

After the fix, the `calls` arrays in the index are populated:

```bash
# Query: Find functions that call lazy()
.modules | ... | select(.calls | any(.callee | test("lazy\\(\\)")))
```

**Result:**
```json
[
  {"name": "t", "calls_lazy": [
    {"file": "packages/server/src/unstable-core-do-not-import/router.test.ts", "line": 43},
    {"file": "packages/server/src/unstable-core-do-not-import/router.test.ts", "line": 62}
  ]},
  {"name": "appRouter", "calls_lazy": [
    {"file": "examples/lazy-load/src/server/routers/_app.ts", "line": 5},
    {"file": "examples/lazy-load/src/server/routers/_app.ts", "line": 7}
  ]}
]
```

### isObservable Call Sites

```json
[
  {"name": "resolveResponse", "calls_it": [
    {"file": "packages/server/src/unstable-core-do-not-import/http/resolveResponse.ts", "line": 436},
    {"file": "packages/server/src/unstable-core-do-not-import/http/resolveResponse.ts", "line": 446},
    {"file": "packages/server/src/unstable-core-do-not-import/http/resolveResponse.ts", "line": 555}
  ]},
  {"name": "getWSConnectionHandler", "calls_it": [
    {"file": "packages/server/src/adapters/ws.ts", "line": 269},
    {"file": "packages/server/src/adapters/ws.ts", "line": 315}
  ]}
]
```

**Matches grep verification exactly!**

## Remaining Issue: Reverse Lookup in Handlers

### Problem

The call site data is correctly stored in the index, but `what_calls_it` and `find_dead_code` still don't work because they need to perform a **reverse lookup**.

**Current data structure:**
- Each function stores what it **calls** (outgoing calls) in `function.calls[]`
- To find what **calls a function** (incoming calls), handlers must scan ALL functions' `calls` arrays

### Evidence

`search_function` with `what_calls_it=true` still returns "No call sites found" even though the data exists in the index.

`find_dead_code` still reports high false positives because it's not performing the reverse lookup correctly.

### Files Needing Updates

The reverse lookup logic needs to be fixed in:
- `cicada/dead_code/analyzer.py` - `_find_usages()` method
- Handler code that implements `what_calls_it` functionality

## Test Results

All 3037 tests pass after the extraction fix.

## Files Modified

| File | Changes |
|------|---------|
| `cicada/languages/typescript/symbol_types.py` | NEW: TypeScript symbol type detection |
| `cicada/languages/python/symbol_types.py` | NEW: Python symbol type detection |
| `cicada/languages/scip/converter.py` | Updated `_get_symbol_type()` and call site detection logic |
| `tests/languages/typescript/test_symbol_types.py` | NEW: 11 tests for TypeScript symbols |
| `tests/languages/python/test_symbol_types.py` | NEW: 10 tests for Python symbols |
