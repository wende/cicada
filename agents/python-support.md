# Python-Specific Behavior

## Class Display in search_module

For Python codebases, the `search_module` tool displays both module-level functions AND classes defined in the module.

### How It Works

The Python indexer creates separate searchable entities:

1. **Modules** (e.g., `cicada.git.history_analyzer`)
   - Contains module-level functions
   - Displays classes defined in the module
   - Each class shows: name, line number, public/private method counts

2. **Classes** (e.g., `HistoryAnalyzer`)
   - Indexed separately as module entries
   - Contains class methods
   - Has `parent_module` field linking to the module

### Example Output

```
cicada/git/history_analyzer.py:1
cicada.git.history_analyzer • 0 public • 0 private

**Classes:**
  • HistoryAnalyzer (line 17) • 3 public • 9 private
    Analyzes git history for files and functions.

Module-level: (none)
```

### Usage

Both approaches work for finding code:
- `search_module("cicada.git.history_analyzer")` → Shows module with classes
- `search_module("HistoryAnalyzer")` → Shows class with methods

**Implementation:** `cicada/languages/scip/converter.py`, `cicada/format/formatter.py`

## Configurable Import Detection

The SCIP converter has a configurable `import_search_lines` parameter that controls how many lines from the top of the file are scanned for import statements.

### Default Behavior

- Scans first **50 lines** for imports (increased from 15 in initial implementation)
- Configurable via `import_search_lines` parameter
- Prevents false positives by ignoring function calls deeper in the file

### Usage

```python
from cicada.languages.scip.converter import SCIPConverter

# Use default (50 lines)
converter = SCIPConverter()

# Increase for files with very large headers
converter = SCIPConverter(import_search_lines=100)

# Decrease for faster processing if all imports are early
converter = SCIPConverter(import_search_lines=25)
```

### Why This Matters

- Python files often have large module docstrings (10-30 lines)
- Copyright headers and license text can push imports down
- Without this limit, regular function calls would be misidentified as imports
- The configurable limit balances accuracy and flexibility

**Implementation:** `cicada/languages/scip/converter.py:19-42`, `tests/languages/scip/test_import_search_lines.py`
