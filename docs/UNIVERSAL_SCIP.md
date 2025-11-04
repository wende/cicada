# Universal SCIP Architecture

**The One Refactor That Unlocks Every Language**

## The Problem

SCIP (Code Intelligence Protocol) is language-agnostic. Any SCIP indexer (scip-python, scip-typescript, scip-go, etc.) generates the same format. Our SCIP converter already works with all of them.

**But our indexer classes aren't generic.**

Without refactoring, every new SCIP language requires copy-pasting 272 lines:

```
PythonSCIPIndexer (272 lines)
├─ Install scip-python ──────┐
├─ Run scip-python ──────────┤
├─ Read .scip file ──────────┤
├─ Convert to Cicada format ─┤── Generic SCIP logic (same for all languages!)
├─ Save index ───────────────┤
├─ Report statistics ────────┤
└─ Cleanup ──────────────────┘

TypeScriptSCIPIndexer (272 lines) ← COPY-PASTE!
├─ Install scip-typescript ──┐
├─ Run scip-typescript ──────┤
├─ Read .scip file ──────────┤
├─ Convert to Cicada format ─┤── Same logic, different tool name
├─ Save index ───────────────┤
├─ Report statistics ────────┤
└─ Cleanup ──────────────────┘

GoSCIPIndexer (272 lines) ← COPY-PASTE AGAIN!
RustSCIPIndexer (272 lines) ← COPY-PASTE AGAIN!
JavaSCIPIndexer (272 lines) ← COPY-PASTE AGAIN!
```

This is unsustainable. Bug fixes need to be applied to every file. Inconsistencies creep in.

## The Solution: Generic SCIP Architecture

Extract the generic SCIP logic once. Make languages pure configuration.

### Architecture

```
cicada/languages/scip/
├── converter.py    # ✅ Already generic (works with any SCIP file)
├── reader.py       # ✅ Already generic (reads any SCIP file)
├── indexer.py      # 🆕 Generic SCIPIndexer base class
└── installer.py    # 🆕 Generic SCIP tool installer

cicada/languages/python/
└── indexer.py      # 🔄 Thin wrapper: config + super().__init__()

cicada/languages/typescript/
└── indexer.py      # 🆕 Thin wrapper: config + super().__init__()

cicada/languages/go/
└── indexer.py      # 🎁 Future: config + super().__init__()
```

### Generic SCIPIndexer (Write Once)

```python
# cicada/languages/scip/indexer.py

@dataclass
class SCIPToolConfig:
    """Configuration for a SCIP language."""
    tool_name: str              # "scip-python", "scip-typescript", "scip-go"
    npm_package: str            # "@sourcegraph/scip-python"
    language_name: str          # "python", "typescript", "go"
    file_extensions: list[str]  # [".py"], [".ts", ".tsx"], [".go"]
    excluded_dirs: set[str]     # {"__pycache__"}, {"node_modules"}

class SCIPIndexer(BaseIndexer):
    """Generic indexer for ANY SCIP-based language."""

    def __init__(self, config: SCIPToolConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose

    def index_repository(self, repo_path, output_path, ...):
        """Universal SCIP indexing pipeline (works for all languages)."""
        # 1. Ensure SCIP tool is installed (npm)
        self._ensure_tool_installed()

        # 2. Run SCIP tool (generic: just uses config.tool_name)
        scip_file = self._run_scip_tool(repo_path)

        # 3. Read SCIP file (already generic!)
        scip_index = SCIPReader().read_index(scip_file)

        # 4. Convert to Cicada format (already generic!)
        cicada_index = SCIPConverter().convert(scip_index, repo_path)

        # 5. Save, report, cleanup (generic)
        self._save_index(cicada_index, output_path)
        self._report_statistics(cicada_index)
        scip_file.unlink()
```

**~200 lines of generic logic, written once.**

### Language Wrappers (Pure Configuration)

**Python (20 lines):**
```python
# cicada/languages/python/indexer.py

PYTHON_CONFIG = SCIPToolConfig(
    tool_name="scip-python",
    npm_package="@sourcegraph/scip-python",
    language_name="python",
    file_extensions=[".py"],
    excluded_dirs={"__pycache__", ".venv", "dist", "build"},
)

class PythonSCIPIndexer(SCIPIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(config=PYTHON_CONFIG, verbose=verbose)
```

**TypeScript (6 lines):**
```python
# cicada/languages/typescript/indexer.py

TYPESCRIPT_CONFIG = SCIPToolConfig(
    tool_name="scip-typescript",
    npm_package="@sourcegraph/scip-typescript",
    language_name="typescript",
    file_extensions=[".ts", ".tsx"],
    excluded_dirs={"node_modules", "dist", "build"},
)

class TypeScriptSCIPIndexer(SCIPIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(config=TYPESCRIPT_CONFIG, verbose=verbose)
```

**Go (6 lines):**
```python
# cicada/languages/go/indexer.py (future)

GO_CONFIG = SCIPToolConfig(
    tool_name="scip-go",
    npm_package="@sourcegraph/scip-go",
    language_name="go",
    file_extensions=[".go"],
    excluded_dirs={"vendor", "bin", "pkg"},
)

class GoSCIPIndexer(SCIPIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(config=GO_CONFIG, verbose=verbose)
```

**Rust, Java, Ruby, C++... all 6 lines each.**

## What Unlocks Future Languages?

### ❌ NOT TypeScript

TypeScript integration doesn't unlock anything. It's just a config file that uses the generic architecture.

### ✅ The Generic SCIP Refactor

**The refactor** (extracting `SCIPIndexer` from `PythonSCIPIndexer`) is what unlocks everything.

### The Timeline

```
┌─────────────────────────────────────────────────────────┐
│ Phase 0: Generic SCIP Refactor (~8 hours)              │
│ ─────────────────────────────────────────────────────── │
│ Create SCIPIndexer (generic base class)                │
│ Create SCIPToolInstaller (generic npm installer)       │
│ Refactor PythonSCIPIndexer: 272 → 20 lines            │
│                                                         │
│ 🔓 UNLOCKS: All future SCIP languages are now 6 lines │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 1: TypeScript (~5 hours)                         │
│ ─────────────────────────────────────────────────────── │
│ Add TypeScript detection (tsconfig.json)               │
│ Create TypeScriptSCIPIndexer (6 lines!)                │
│ Tests & documentation                                   │
│                                                         │
│ ✅ First beneficiary of the refactor                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Future: Go, Rust, Java, Ruby, C++, etc.                │
│ ─────────────────────────────────────────────────────── │
│ Each language: ~1 hour (6 lines of code + tests)       │
│                                                         │
│ ✅ Benefits from the refactor                          │
└─────────────────────────────────────────────────────────┘
```

## The Correct Statement

> **The generic SCIP refactor** (motivated by TypeScript) unlocks all future SCIP languages.
>
> TypeScript is the **first beneficiary**, turning what would be 272 lines of copy-paste into 6 lines of config.

## Why TypeScript Matters

TypeScript doesn't unlock languages, but it's the **catalyst**:

1. **Without TypeScript:** We only have Python (272 lines). No motivation to refactor.
2. **With TypeScript need:** We'd copy-paste 272 lines. That's when we realize we need to refactor.
3. **After refactor:** Python becomes 20 lines, TypeScript becomes 6 lines, and ALL future languages are 6 lines.

TypeScript is the **use case that justifies the refactor**.

## The Math

### Without Refactor
```
Python:     272 lines
TypeScript: 272 lines (copy-paste)
Go:         272 lines (copy-paste)
Rust:       272 lines (copy-paste)
Java:       272 lines (copy-paste)
─────────────────────
Total:      1,360 lines (5 languages)
```

### With Refactor
```
SCIPIndexer (generic):  ~200 lines (write once!)
Python:                   20 lines (config)
TypeScript:                6 lines (config)
Go:                        6 lines (config)
Rust:                      6 lines (config)
Java:                      6 lines (config)
─────────────────────────────────────────
Total:                   244 lines (5 languages)
```

**82% reduction in code!**

Plus:
- Bug fixes apply to all languages
- Consistent behavior across languages
- Adding new languages is trivial

## Implementation Strategy

### Phase 0: The Refactor (One-Time Investment)

**Goal:** Extract generic SCIP logic from PythonSCIPIndexer

**Deliverables:**
1. `cicada/languages/scip/indexer.py` - Generic `SCIPIndexer` class
2. `cicada/languages/scip/installer.py` - Generic `SCIPToolInstaller` class
3. Refactored `PythonSCIPIndexer` (272 → 20 lines)
4. Delete `cicada/languages/python/scip_installer.py`
5. All existing tests still pass

**Effort:** ~8 hours

**Unlocks:** Every future SCIP language

### Phase 1+: Language Integration (Per Language)

**For each new SCIP language (TypeScript, Go, Rust, etc.):**

1. Create config (6 lines)
2. Add language detection (tsconfig.json, go.mod, Cargo.toml)
3. Update CLI to recognize language
4. Add tests

**Effort per language:** ~1-5 hours (mostly tests & detection)

## Supported SCIP Languages (Current & Future)

### Production Ready
- ✅ **scip-python** - Python (via Pyright)
- 🔜 **scip-typescript** - TypeScript/JavaScript

### Available (Pending Integration)
- **scip-go** - Go
- **scip-rust** - Rust (via rust-analyzer)
- **scip-java** - Java
- **scip-ruby** - Ruby

### Future Possibilities
- **scip-clang** - C/C++
- Any language with a SCIP indexer

**Each one: 6 lines of code + detection + tests.**

## Benefits of Universal SCIP

### 1. **DRY (Don't Repeat Yourself)**
Generic logic written once. Languages are pure configuration.

### 2. **Consistency**
All SCIP languages behave identically:
- Same installation flow
- Same indexing pipeline
- Same error messages
- Same statistics format

### 3. **Maintainability**
Bug fix in `SCIPIndexer`? Applies to ALL languages automatically.

### 4. **Extensibility**
Adding a new SCIP language:
- Before refactor: 272 lines, 4 hours
- After refactor: 6 lines, 1 hour

### 5. **Testability**
Test `SCIPIndexer` thoroughly once. Language wrappers are trivial to test.

## Migration Path

### Step 1: Create Generic Infrastructure
```bash
# New files
cicada/languages/scip/indexer.py      # Generic SCIPIndexer
cicada/languages/scip/installer.py    # Generic SCIPToolInstaller
```

### Step 2: Refactor Python
```bash
# Before: 272 lines
cicada/languages/python/indexer.py

# After: 20 lines (config + wrapper)
cicada/languages/python/indexer.py

# Delete
cicada/languages/python/scip_installer.py
```

### Step 3: Verify Tests Pass
```bash
uv run pytest tests/languages/python/ -v
# All tests should pass with no changes
```

### Step 4: Add TypeScript
```bash
# New file: 6 lines!
cicada/languages/typescript/indexer.py
```

### Step 5: Future Languages
```bash
# Each new language: 6 lines
cicada/languages/go/indexer.py
cicada/languages/rust/indexer.py
cicada/languages/java/indexer.py
```

## Anti-Pattern We're Avoiding

```python
# ❌ DON'T DO THIS (copy-paste)
class TypeScriptSCIPIndexer:
    def index_repository(self, ...):
        # Install scip-typescript
        if not shutil.which("scip-typescript"):
            subprocess.run(["npm", "install", "-g", ...])

        # Run scip-typescript
        subprocess.run(["scip-typescript", "index", ...])

        # Read .scip file
        reader = SCIPReader()
        scip_index = reader.read_index(...)

        # Convert to Cicada format
        converter = SCIPConverter()
        cicada_index = converter.convert(...)

        # ... etc (272 lines of copy-pasted logic)
```

```python
# ✅ DO THIS (configuration)
TYPESCRIPT_CONFIG = SCIPToolConfig(
    tool_name="scip-typescript",
    npm_package="@sourcegraph/scip-typescript",
    language_name="typescript",
    file_extensions=[".ts", ".tsx"],
    excluded_dirs={"node_modules", "dist"},
)

class TypeScriptSCIPIndexer(SCIPIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(config=TYPESCRIPT_CONFIG, verbose=verbose)
```

## Conclusion

**The generic SCIP refactor is a one-time investment that pays infinite dividends.**

- Write `SCIPIndexer` once (~200 lines, 8 hours)
- Refactor Python to use it (20 lines, 1 hour)
- **Every future language:** 6 lines, 1 hour

The refactor doesn't just make TypeScript easy - it makes **every SCIP language** easy forever.

---

**Related Documents:**
- `SCIP_REFACTOR_PLAN.md` - Detailed refactoring implementation plan
- `TYPESCRIPT_OBJECTIVE.md` - TypeScript integration roadmap (first beneficiary)
- `docs/SCIP_LANGUAGE_AGNOSTIC_FINDINGS.md` - SCIP format analysis
