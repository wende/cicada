# TypeScript Support Implementation Objective

**Date:** 2025-01-03
**Status:** Planned - Foundation Ready

> **⚠️ IMPORTANT:** Before implementing TypeScript, read `SCIP_REFACTOR_PLAN.md`
>
> We're refactoring to a generic SCIP architecture to avoid copy-paste.
> TypeScript will be **6 lines of code** instead of 272!

## Executive Summary

TypeScript support is **90% complete** thanks to Cicada's language-agnostic SCIP architecture. The SCIP converter already works perfectly with TypeScript - we just need to add CLI integration and an indexer wrapper.

## Current Status

### ✅ What's Already Working

1. **Universal SCIP Converter** (`cicada/languages/scip/converter.py`)
   - Works with TypeScript with **ZERO code changes**
   - Tested and verified in `tests/languages/scip/test_scip_converter.py`
   - Extracts classes, methods, functions, documentation
   - Handles TypeScript-specific patterns (constructors, type signatures)

2. **Test Infrastructure**
   - Mock TypeScript project at `tests/fixtures/sample_typescript/`
   - Pre-generated SCIP index and converted Cicada index
   - Comprehensive tests for TypeScript SCIP conversion

3. **scip-typescript Integration**
   - npm package: `@sourcegraph/scip-typescript` v0.4.0
   - Generates language-agnostic SCIP format
   - Already validated in test fixtures

### ❌ What's Missing

1. **Language Detection** - `detect_project_language()` doesn't recognize TypeScript projects
2. **TypeScript Indexer Class** - No wrapper for scip-typescript CLI
3. **CLI Integration** - `cicada index` doesn't support TypeScript
4. **User Documentation** - README mentions "planned for future releases"

## Implementation Plan

### Phase 1: Language Detection

**File:** `cicada/setup.py`

Add TypeScript markers to `detect_project_language()`:

```python
def detect_project_language(repo_path: Path) -> str:
    # ... existing Python markers ...

    # Check for TypeScript marker
    if (repo_path / "tsconfig.json").exists():
        return "typescript"

    # Check for package.json with TypeScript dependency
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            import json
            with open(package_json) as f:
                data = json.load(f)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "typescript" in deps or any("@types/" in dep for dep in deps):
                    return "typescript"
        except:
            pass

    # ... existing Elixir marker ...
```

**Priority:** High
**Complexity:** Low

### Phase 2: Generic SCIP Architecture (REFACTOR FIRST!)

**IMPORTANT:** Before implementing TypeScript, we need to refactor the Python indexer to use a generic SCIP base class. See `SCIP_REFACTOR_PLAN.md` for details.

**Phase 2a: Create Generic SCIP Infrastructure**

**File:** `cicada/languages/scip/indexer.py` (new)

Create a generic `SCIPIndexer` base class that works for ANY SCIP-based language:

```python
@dataclass
class SCIPToolConfig:
    tool_name: str              # "scip-python", "scip-typescript"
    npm_package: str            # "@sourcegraph/scip-python"
    language_name: str          # "python", "typescript"
    file_extensions: list[str]  # [".py"], [".ts", ".tsx"]
    excluded_dirs: set[str]

class SCIPIndexer(BaseIndexer):
    """Generic indexer for SCIP-based languages."""
    # All the logic from PythonSCIPIndexer, but generic
```

**File:** `cicada/languages/scip/installer.py` (new)

Generic installer for npm-based SCIP tools:

```python
class SCIPToolInstaller:
    """Generic installer for npm-based SCIP tools."""
    # Move logic from scip_installer.py, make generic
```

**Priority:** High
**Complexity:** Medium (refactor existing code)

**Phase 2b: Refactor Python Indexer**

**File:** `cicada/languages/python/indexer.py` (refactor)

Reduce from 272 lines to ~20 lines:

```python
PYTHON_SCIP_CONFIG = SCIPToolConfig(
    tool_name="scip-python",
    npm_package="@sourcegraph/scip-python",
    language_name="python",
    file_extensions=[".py"],
    excluded_dirs={"__pycache__", ".venv", ...},
)

class PythonSCIPIndexer(SCIPIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(config=PYTHON_SCIP_CONFIG, verbose=verbose)
```

**Delete:** `cicada/languages/python/scip_installer.py` (moved to generic installer)

**Priority:** High
**Complexity:** Low (just use the generic base)

**Phase 2c: Create TypeScript Indexer**

**File:** `cicada/languages/typescript/indexer.py` (new)

With the generic architecture, TypeScript is **6 lines of code**:

```python
TYPESCRIPT_SCIP_CONFIG = SCIPToolConfig(
    tool_name="scip-typescript",
    npm_package="@sourcegraph/scip-typescript",
    language_name="typescript",
    file_extensions=[".ts", ".tsx"],
    excluded_dirs={"node_modules", "dist", "build", ".next"},
)

class TypeScriptSCIPIndexer(SCIPIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(config=TYPESCRIPT_SCIP_CONFIG, verbose=verbose)
```

**That's it!** All functionality inherited from `SCIPIndexer`.

**Priority:** High
**Complexity:** Trivial (config + wrapper)

### Phase 3: CLI Integration

**File:** `cicada/commands.py`

Update `handle_index_main()` to support TypeScript:

```python
# Use appropriate indexer based on detected language
if language == "elixir":
    from cicada.languages.elixir.indexer import ElixirIndexer
    indexer = ElixirIndexer(verbose=True)
    indexer.incremental_index_repository(...)
elif language == "python":
    from cicada.languages.python.indexer import PythonSCIPIndexer
    indexer = PythonSCIPIndexer(verbose=True)
    indexer.index_repository(...)
elif language == "typescript":
    from cicada.languages.typescript.indexer import TypeScriptSCIPIndexer
    indexer = TypeScriptSCIPIndexer(verbose=True)
    indexer.index_repository(...)
else:
    print(f"Error: Unsupported language: {language}", file=sys.stderr)
    sys.exit(1)
```

**Priority:** High
**Complexity:** Low (already implemented pattern for Python/Elixir)

### Phase 4: Testing

**File:** `tests/languages/typescript/test_typescript_indexer.py` (new)

Add comprehensive tests similar to `test_python_indexer.py`:

```python
class TestTypeScriptSCIPIndexer:
    """Test TypeScript SCIP indexer functionality."""

    def test_get_language_name(self):
        """Should return 'typescript'."""

    def test_ensure_scip_typescript_installed(self):
        """Should check if scip-typescript is installed."""

    def test_run_scip_typescript_success(self):
        """Should run scip-typescript and generate .scip file."""

    def test_index_repository_full_flow(self, tmp_path):
        """Should index TypeScript repo using sample_typescript fixture."""
```

**File:** `tests/test_cli.py`

Add test for TypeScript detection:

```python
def test_detects_typescript_and_uses_typescript_indexer(self, tmp_path, capsys):
    """Should detect TypeScript project and use TypeScriptSCIPIndexer"""
    ts_repo = tmp_path / "ts_project"
    ts_repo.mkdir()
    (ts_repo / "tsconfig.json").write_text("{}")

    # ... test that TypeScriptSCIPIndexer is used
```

**Priority:** High
**Complexity:** Low (copy-paste from Python tests)

### Phase 5: Documentation

**Files to Update:**
1. `README.md` - Change "planned" to "supported"
2. `CLAUDE.md` - Update language support status
3. CLI help text - Already done (language-agnostic)

**Priority:** Medium
**Complexity:** Low

## Technical Details

### scip-typescript Command

```bash
# Install
npm install -g @sourcegraph/scip-typescript

# Run
scip-typescript index \
  --project-name my-project \
  --output index.scip
```

### TypeScript Project Markers (Priority Order)

1. `tsconfig.json` - **Primary marker** (TypeScript-specific)
2. `package.json` with `typescript` dependency
3. `package.json` with `@types/*` dependencies
4. `.ts` or `.tsx` files (fallback)

### Expected Output

```
Indexing typescript repository: /path/to/project
  Using scip-typescript 0.4.0
  Running: scip-typescript index --project-name my-project --output /tmp/abc.scip
  (This may take several minutes for large projects...)
  SCIP index: 42 documents, 1234 symbols
  Indexed 42 files, 156 classes, 892 functions
  Index saved to: ~/.cicada/projects/abc123/index.json
  Cleaned up temporary file: /tmp/abc.scip
```

## Implementation Checklist

### Phase 0: Generic SCIP Refactor (PREREQUISITE)
- [ ] Create `cicada/languages/scip/indexer.py` (generic SCIPIndexer)
- [ ] Create `cicada/languages/scip/installer.py` (generic SCIPToolInstaller)
- [ ] Refactor `PythonSCIPIndexer` to use generic base (272 → 20 lines)
- [ ] Delete `cicada/languages/python/scip_installer.py`
- [ ] Update Python indexer tests to work with new architecture
- [ ] Verify all existing tests still pass

### Phase 1: TypeScript Integration
- [ ] Add TypeScript detection to `detect_project_language()`
- [ ] Create `TypeScriptSCIPIndexer` class (6 lines!)
- [ ] Update `handle_index_main()` to support TypeScript
- [ ] Add comprehensive tests
- [ ] Update documentation

## Risks & Considerations

### 1. npm Dependency
- **Risk:** Users without Node.js/npm can't use TypeScript support
- **Mitigation:** Clear error messages with installation instructions
- **Same as:** Python support (requires Node.js for scip-python)

### 2. scip-typescript Stability
- **Risk:** scip-typescript may have bugs or limitations
- **Mitigation:** Use stable version (0.4.0), document known issues
- **Status:** Already validated in test fixtures

### 3. Monorepo Support
- **Risk:** TypeScript monorepos may be complex
- **Mitigation:** Start with single-package support, expand later
- **Priority:** Low (handle in future iteration)

### 4. Performance
- **Risk:** Large TypeScript projects may be slow to index
- **Mitigation:** Same as Python - timeout after 10 minutes, suggest smaller scope
- **Status:** scip-typescript handles large projects well

## Success Criteria

1. ✅ `cicada index` detects TypeScript projects via `tsconfig.json`
2. ✅ `TypeScriptSCIPIndexer` successfully indexes TypeScript code
3. ✅ Classes, methods, functions extracted with correct signatures
4. ✅ Documentation and type information preserved
5. ✅ All tests pass (100% coverage like Python indexer)
6. ✅ Clear error messages for missing dependencies
7. ✅ README updated to list TypeScript as supported

## Timeline Estimate

### Phase 0: Generic SCIP Refactor
- **Create generic SCIPIndexer:** 3 hours
- **Create generic SCIPToolInstaller:** 2 hours
- **Refactor PythonSCIPIndexer:** 1 hour
- **Update tests:** 2 hours

**Subtotal:** ~8 hours

### Phase 1: TypeScript Integration
- **Detection:** 1 hour
- **TypeScript indexer (6 lines!):** 30 minutes
- **CLI integration:** 30 minutes
- **Tests:** 2 hours
- **Documentation:** 1 hour

**Subtotal:** ~5 hours

**Total:** ~13 hours of development work

**Note:** The refactor is a one-time investment that makes adding ANY future SCIP language trivial (Go, Rust, Java, etc. = 6 lines each!)

## Future Enhancements

1. **Incremental Indexing:** Currently Python/TypeScript do full reindex - could add incremental support
2. **Monorepo Support:** Handle multiple `tsconfig.json` files
3. **React/JSX Support:** Ensure `.tsx` files are properly indexed
4. **Type Inference:** Extract inferred types, not just explicit ones
5. **Cross-file Analysis:** Track imports and dependencies between files

## References

- SCIP Documentation: https://github.com/sourcegraph/scip
- scip-typescript: https://github.com/sourcegraph/scip-typescript
- Findings Doc: `docs/SCIP_LANGUAGE_AGNOSTIC_FINDINGS.md`
- Test Fixtures: `tests/fixtures/sample_typescript/`
- SCIP Converter: `cicada/languages/scip/converter.py`
