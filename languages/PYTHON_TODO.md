# Python Language Support - Known Issues

**Date:** 2025-11-04
**Status:** Python indexing is partially functional but has critical gaps

## Test Results: Cicada MCP Tools on cicada2 (Python Project)

### ✅ Working Tools

#### 1. search_by_keywords
**Status:** ✅ Works perfectly

**Test:**
```python
keywords=["language", "detection", "project"]
```

**Result:**
```
Function: LanguageRegistry.get_parser/2
Score: 9.5235
Path: cicada/languages/__init__.py:73

Function: _file_setup.detect_project_language/1
Score: 6.8484
Path: cicada/setup.py:28
Matched: language, project
```

**Conclusion:** Keyword extraction and semantic search work correctly.

---

#### 2. get_commit_history
**Status:** ✅ Works perfectly

**Test:**
```python
file_path="cicada/setup.py"
max_commits=3
```

**Result:**
```
Found 3 commit(s)
1. Merge origin/main into feat/language-agnostic
2. Bump version to 0.2.3
3. Post-merge test fixes: mock BERT extractor...
```

**Conclusion:** Git history retrieval works correctly (uses git directly, not index).

---

### ❌ Broken Tools

#### 3. search_module
**Status:** ❌ Bug #1 - Cannot find Python modules

**Test:**
```python
module_name="cicada.setup"
```

**Result:**
```
Module 'cicada.setup' not found in the index.
Total modules available in index: 342
```

**Expected:** Should find and display the `cicada.setup` module with all its functions.

**Issue:** Python modules aren't being indexed with searchable names. The indexer might be using file paths instead of Python module paths.

---

#### 4. search_function
**Status:** ⚠️ Bug #2 - Finds function but no call sites

**Test:**
```python
function_name="detect_project_language"
```

**Result:**
```
cicada/setup.py:28
_file_setup.detect_project_language/1
Type: detect_project_language(repo_path)
Documentation: [shows correct docstring]
*No call sites found*
```

**Expected:** Should show call sites in:
- `cicada/commands.py` (multiple locations)
- `cicada/interactive_setup.py`
- `cicada/mcp/server.py`
- Multiple test files

**Issue:** SCIP indexing isn't capturing call sites/references properly for Python code.

---

#### 5. search_module_usage
**Status:** ❌ Bug #3 - Cannot find module usage

**Test:**
```python
module_name="cicada.setup"
```

**Result:**
```
Module 'cicada.setup' not found in index.
```

**Expected:** Should show all files that import `cicada.setup` and list which functions they call.

**Issue:** Same as Bug #1 - modules aren't indexed with searchable names.

---

#### 6. get_blame
**Status:** ❌ Bug #4 - No blame information

**Test:**
```python
file_path="cicada/setup.py"
start_line=28
end_line=40
```

**Result:**
```
No blame information found for cicada/setup.py lines 28-40
```

**Expected:** Should show git blame information (author, date, commit hash) for each line.

**Issue:** Blame functionality might not be implemented for Python, or the file path resolution is broken.

---

#### 7. find_dead_code
**Status:** ❌ Bug #5 - Finds zero functions

**Test:**
```python
min_confidence="high"
format="markdown"
```

**Result:**
```
Analyzed 0 public functions (skipped 0 with @impl, 0 in test/script files)
Found 0 potentially unused functions
```

**Expected:** Should analyze hundreds of Python functions in the cicada2 codebase.

**Issue:** Dead code analysis isn't seeing any Python functions. This confirms that the function index is incomplete or malformed.

---

### ⚠️ Tools Requiring Setup (Working as Expected)

#### 8. find_pr_for_line
**Status:** ⚠️ Requires PR index (working correctly)

**Result:**
```
PR index not found. Please run:
  cicada index-pr
```

**Conclusion:** Tool correctly reports missing PR index. Not a bug.

---

#### 9. get_file_pr_history
**Status:** ⚠️ Requires PR index (working correctly)

**Result:**
```
PR index not available. Please run:
  cicada index-pr
```

**Conclusion:** Tool correctly reports missing PR index. Not a bug.

---

## Root Cause Analysis

### Primary Issue: Incomplete SCIP → Cicada Conversion

The Python indexing pipeline appears to have issues in the SCIP → Cicada format conversion:

1. **SCIP file generation** (scip-python) - ✅ Likely working
   - Keywords are extracted correctly
   - Function signatures are captured

2. **SCIP → Cicada conversion** (cicada/languages/scip/converter.py) - ❌ Broken
   - Modules aren't being indexed with Python module names
   - Call sites/references aren't being tracked
   - Function definitions exist but are incomplete

3. **Index structure** - ❌ Malformed
   - Dead code analysis sees 0 functions
   - Module search finds 0 Python modules (despite 342 total modules?)
   - Call site relationships are missing

### Specific Problems to Investigate

1. **Module name mapping**
   - File path: `cicada/setup.py`
   - Expected module name: `cicada.setup`
   - Current state: Module not found by name
   - **Action:** Check how `scip/converter.py` converts SCIP symbols to Cicada module names

2. **Call site extraction**
   - Function definitions are found
   - But "No call sites found" for heavily-used functions
   - **Action:** Verify that SCIP occurrences are being converted to Cicada call sites

3. **Function visibility**
   - Dead code analysis sees 0 functions
   - **Action:** Check if Python functions are being tagged as "public" correctly in the index

4. **Git blame integration**
   - Blame returns "No information found"
   - **Action:** Verify that git blame is implemented for Python (might be Elixir-only)

---

## Action Items

### High Priority (Blocking Python Support)

- [ ] **Fix module name conversion** in `cicada/languages/scip/converter.py`
  - Map file paths (`cicada/setup.py`) to module names (`cicada.setup`)
  - Test: `search_module("cicada.setup")` should work

- [ ] **Fix call site extraction** in SCIP converter
  - Ensure SCIP occurrences → Cicada call sites
  - Test: `search_function("detect_project_language")` should show call sites

- [ ] **Fix function indexing** for dead code analysis
  - Ensure Python functions are visible to analysis tools
  - Test: `find_dead_code()` should analyze > 0 functions

### Medium Priority

- [ ] **Implement or fix git blame** for Python files
  - Check if this is Elixir-specific code
  - Test: `get_blame()` should return authorship info

- [ ] **Add integration tests** that verify Python indexing
  - Test search_module works on Python code
  - Test search_function finds call sites
  - Test dead code analysis counts functions

### Low Priority

- [ ] Document SCIP → Cicada conversion process
- [ ] Add Python-specific examples to MCP tool descriptions
- [ ] Performance testing on large Python codebases

---

## Testing Commands

To reproduce these issues on the cicada2 project:

```bash
# Ensure project is indexed
cd /Users/wende/projects/cicada2
cicada index --fast

# Test each MCP tool via Python
uv run python -c "
from cicada.mcp.tools import *
# ... test tool calls
"

# Or use MCP directly (if configured)
# Tools will use the index at ~/.cicada/projects/d92215bf0166c2b8/
```

---

## Success Criteria

Python language support will be considered "working" when:

1. ✅ `search_module("cicada.setup")` returns the module with all functions
2. ✅ `search_function("detect_project_language")` shows all call sites
3. ✅ `search_module_usage("cicada.setup")` shows all imports and usage
4. ✅ `find_dead_code()` analyzes all public Python functions
5. ✅ `get_blame()` returns git authorship information
6. ✅ Integration tests pass for all Python MCP tools

---

## Notes

- This analysis was performed on cicada2 itself (a Python project)
- SCIP index shows: "160 documents, 12670 symbols"
- Keywords and git history work, proving the infrastructure is sound
- The issue is specifically in the SCIP → Cicada conversion layer
