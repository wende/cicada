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
