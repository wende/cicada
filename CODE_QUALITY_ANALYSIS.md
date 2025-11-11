# CICADA Codebase Code Quality Analysis Report

## Executive Summary
This analysis identifies opportunities for improving code quality in the CICADA codebase, focusing on duplication, complexity reduction, and structural improvements. The codebase consists of approximately 2,893 lines across handlers and core modules, with significant opportunities for consolidation and simplification.

---

## 1. CODE DUPLICATION

### 1.1 Duplicated `parse_changed_since()` Function
**Category:** Code Duplication  
**Severity:** HIGH  
**Files:**
- `/home/user/cicada/cicada/mcp/handlers/git_handlers.py` (lines 30-113)
- `/home/user/cicada/cicada/mcp/handlers/function_handlers.py` (lines 269-323)

**Issue:**
Both files implement identical logic for parsing date filters with support for ISO dates, relative formats (7d, 2w, 3m, 1y), and git refs. The implementations are ~80 lines each with identical parsing logic.

**Suggested Solution:**
Extract into shared utility module: `/home/user/cicada/cicada/utils/date_parser.py`
```python
# cicada/utils/date_parser.py
def parse_changed_since(changed_since: str, git_helper=None) -> datetime:
    """Unified date parser supporting ISO, relative, and git ref formats."""
```

Then import and use from both handlers:
```python
from cicada.utils.date_parser import parse_changed_since
```

**Estimated Impact:** 
- Reduces codebase by ~50 lines
- Improves maintainability
- Enables consistent date parsing across all tools
- **Impact Level:** HIGH

---

### 1.2 Duplicated Module Lookup with Error Suggestions
**Category:** Code Duplication  
**Severity:** MEDIUM  
**Files:**
- `/home/user/cicada/cicada/mcp/handlers/module_handlers.py` (lines 30-56)
- `/home/user/cicada/cicada/mcp/handlers/dependency_handlers.py` (lines 79-89)

**Issue:**
Both implement nearly identical module lookup logic with fuzzy matching suggestions:

**module_handlers.py (lines 48-56):**
```python
error_msg = f"Module not found: {module_name}"
if include_suggestions:
    similar = find_similar_names(module_name, list(self.index["modules"].keys()))
    if similar:
        error_msg += "\n\nDid you mean one of these?\n" + "\n".join(
            f"  - {name}" for name in similar[:5]
        )
return None, error_msg
```

**dependency_handlers.py (lines 83-88):**
```python
error_msg = f"Module not found: {module_name}"
similar = find_similar_names(module_name, list(self.index["modules"].keys()))
if similar:
    error_msg += "\n\nDid you mean one of these?\n" + "\n".join(
        f"  - {name}" for name in similar[:5]
    )
```

**Suggested Solution:**
Create a shared base handler class or utility:
```python
# cicada/mcp/handlers/base_handler.py
class BaseHandler:
    def lookup_module_with_error(self, module_name: str):
        """Shared module lookup logic with suggestions."""
        module_data = self.index["modules"].get(module_name)
        if module_data:
            return module_data, None
        
        error_msg = f"Module not found: {module_name}"
        similar = find_similar_names(module_name, list(self.index["modules"].keys()))
        if similar:
            error_msg += "\n\nDid you mean one of these?\n" + "\n".join(
                f"  - {name}" for name in similar[:5]
            )
        return None, error_msg
```

**Estimated Impact:**
- Reduces codebase by ~15 lines
- Improves consistency
- **Impact Level:** MEDIUM

---

### 1.3 Massive Keyword Extraction/Expansion Code Duplication
**Category:** Code Duplication  
**Severity:** HIGH  
**File:** `/home/user/cicada/cicada/indexer.py`

**Issue:**
The keyword extraction logic is duplicated across three methods:
1. **index_repository()** - Module keywords (lines 225-264)
2. **index_repository()** - Function keywords (lines 274-331)
3. **incremental_index_repository()** - Module keywords (lines 641-679)
4. **incremental_index_repository()** - Function keywords (lines 684-732)

Each block follows this identical pattern (~35-50 lines):
```python
if keyword_extractor and module_data.get("moduledoc"):
    try:
        # Step 1: Extract keywords with scores
        extraction_result = keyword_extractor.extract_keywords(
            module_data["moduledoc"], top_n=10
        )
        extracted_keywords = [kw for kw, _ in extraction_result["top_keywords"]]
        keyword_scores = {
            kw.lower(): score
            for kw, score in extraction_result["top_keywords"]
        }
        
        # Step 2: Expand keywords with scores
        if keyword_expander and extracted_keywords:
            expansion_result = keyword_expander.expand_keywords(...)
            module_keywords = {}
            if not isinstance(expansion_result, dict):
                raise TypeError(...)
            for item in expansion_result["words"]:
                word = item["word"]
                score = item["score"]
                if word not in module_keywords or score > module_keywords[word]:
                    module_keywords[word] = score
        else:
            module_keywords = keyword_scores
    except Exception as e:
        keyword_extraction_failures += 1
```

**Suggested Solution:**
Extract into a helper method or separate class:
```python
# cicada/indexer.py - add method to ElixirIndexer class
def _extract_and_expand_keywords(
    self, 
    text: str, 
    keyword_extractor, 
    keyword_expander,
    verbose: bool = False
) -> dict[str, float] | None:
    """Extract and expand keywords from text."""
    if not keyword_extractor:
        return None
    
    try:
        # Step 1: Extract
        extraction_result = keyword_extractor.extract_keywords(text, top_n=10)
        extracted_keywords = [kw for kw, _ in extraction_result["top_keywords"]]
        keyword_scores = {
            kw.lower(): score
            for kw, score in extraction_result["top_keywords"]
        }
        
        # Step 2: Expand
        if keyword_expander and extracted_keywords:
            expansion_result = keyword_expander.expand_keywords(
                extracted_keywords,
                top_n=self.DEFAULT_EXPANSION_TOP_N,
                threshold=self.DEFAULT_EXPANSION_THRESHOLD,
                return_scores=True,
                keyword_scores=keyword_scores,
            )
            
            if not isinstance(expansion_result, dict):
                raise TypeError("Expected dict from expand_keywords")
            
            keywords = {}
            for item in expansion_result["words"]:
                word = item["word"]
                score = item["score"]
                if word not in keywords or score > keywords[word]:
                    keywords[word] = score
            return keywords
        
        return keyword_scores
    except Exception as e:
        if verbose:
            print(f"Warning: Keyword extraction failed: {e}", file=sys.stderr)
        return None
```

Then replace all duplication with:
```python
module_keywords = self._extract_and_expand_keywords(
    module_data["moduledoc"],
    keyword_extractor,
    keyword_expander,
    self.verbose
)
```

**Estimated Impact:**
- Reduces codebase by ~120-150 lines
- Improves maintainability significantly
- Eliminates error handling duplication
- Enables consistent keyword extraction behavior
- **Impact Level:** HIGH (Most Impactful)

---

## 2. UNNECESSARY COMPLEXITY

### 2.1 Overly Large Functions - `index_repository()`
**Category:** Excessive Function Length  
**Severity:** MEDIUM  
**File:** `/home/user/cicada/cicada/indexer.py` (lines 114-478)

**Issue:**
The `index_repository()` method is 365 lines long and mixes multiple concerns:
- File discovery and iteration (lines 197-210)
- Module parsing (lines 211-213)
- Keyword extraction logic (lines 223-330)
- Git timestamp computation (lines 332-358)
- Dependency extraction (lines 360-363)
- Index building (lines 410-420)
- File hashing (lines 437-449)
- Progress reporting (lines 394-407)
- Error handling and interruption checking (lines 402-408)

**Suggested Solution:**
Break into smaller methods:
```python
def _process_module_keywords(self, module_data, keyword_extractor, keyword_expander):
    """Extract keywords for a module."""
    
def _enrich_function_metadata(self, func, module_data, keyword_extractor, keyword_expander, git_helper, file_path):
    """Add timestamps and keywords to function."""
    
def _build_module_info(self, module_data, module_name, public_count, private_count, module_keywords):
    """Build module info dictionary."""
    
def index_repository(...):
    # Now focuses on orchestration, not implementation
    for file_path in elixir_files:
        modules = self.parser.parse_file(str(file_path))
        for module_data in modules:
            module_keywords = self._process_module_keywords(...)
            for func in module_data["functions"]:
                self._enrich_function_metadata(...)
            module_info = self._build_module_info(...)
            all_modules[module_name] = module_info
```

**Estimated Impact:**
- Improves readability and testability
- Enables unit testing of individual steps
- Reduces cognitive complexity
- **Impact Level:** MEDIUM

---

### 2.2 Overly Large Function - `incremental_index_repository()`
**Category:** Excessive Function Length  
**Severity:** MEDIUM  
**File:** `/home/user/cicada/cicada/indexer.py` (lines 480-835)

**Issue:**
Similar to `index_repository()`, this method is 355 lines and duplicates most of the processing logic with minimal changes for incremental indexing.

**Suggested Solution:**
Consolidate with `index_repository()` by:
1. Creating a shared processing pipeline
2. Making file detection and change tracking separate concerns
3. Using the extracted helper methods from 2.1

This would reduce `incremental_index_repository()` to ~100 lines focused on:
- Change detection
- Index merging
- Hash updating

**Estimated Impact:**
- Reduces codebase by ~150-200 lines
- Improves DRY principle adherence
- Enables shared logic path
- **Impact Level:** HIGH

---

### 2.3 Complex Nested Conditionals in Error Handling
**Category:** Nested Conditionals  
**Severity:** LOW  
**File:** `/home/user/cicada/cicada/mcp/server.py` (lines 191-202)

**Issue:**
```python
# Lines 191-202: Overly complex path splitting logic
workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
if workspace_paths:
    repo_path_str = (
        workspace_paths.split(os.pathsep)[0]
        if os.pathsep in workspace_paths
        else workspace_paths
    )
```

**Suggested Solution:**
```python
# Simpler approach
workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
if workspace_paths:
    # split() always works even if separator not found
    repo_path_str = workspace_paths.split(os.pathsep)[0]
```

**Estimated Impact:**
- Reduces lines by 3
- Improves readability
- **Impact Level:** LOW

---

### 2.4 Complex List Comprehension in `_find_function_at_line()`
**Category:** Complex Comprehension  
**Severity:** LOW  
**File:** `/home/user/cicada/cicada/mcp/handlers/function_handlers.py` (lines 30-60)

**Issue:**
```python
# Lines 48-58: Complex iteration pattern
best_match: dict[str, Any] | None = None
for func in functions:
    func_line = func["line"]
    if func_line <= line and (best_match is None or func_line > best_match["line"]):
        best_match = {
            "name": func["name"],
            "arity": func["arity"],
            "line": func_line,
        }
```

**Suggested Solution:**
```python
# More readable: find all matching functions and get the one with max line
matching_funcs = [
    (f["name"], f["arity"], f["line"]) 
    for f in functions 
    if f["line"] <= line
]

if matching_funcs:
    name, arity, func_line = max(matching_funcs, key=lambda x: x[2])
    best_match = {"name": name, "arity": arity, "line": func_line}
```

**Estimated Impact:**
- Improves clarity
- Makes intent explicit
- **Impact Level:** LOW

---

## 3. LINE REDUCTION OPPORTUNITIES

### 3.1 Verbose Error Message Construction
**Category:** Verbose Code  
**Severity:** LOW  
**Files:** Multiple handlers

**Issue:**
Pattern repeated in:
- `/home/user/cicada/cicada/mcp/handlers/module_handlers.py` (lines 49-56)
- `/home/user/cicada/cicada/mcp/handlers/dependency_handlers.py` (lines 83-88, 209-210, 221-227)
- `/home/user/cicada/cicada/mcp/handlers/function_handlers.py`

```python
# Current: 6+ lines per occurrence
error_msg = f"Module not found: {module_name}"
if include_suggestions:
    similar = find_similar_names(module_name, list(self.index["modules"].keys()))
    if similar:
        error_msg += "\n\nDid you mean one of these?\n" + "\n".join(
            f"  - {name}" for name in similar[:5]
        )
```

**Suggested Solution:**
Create a helper function:
```python
def format_module_not_found_error(module_name: str, available_modules: list[str], 
                                  max_suggestions: int = 5) -> str:
    """Format module not found error with suggestions."""
    error = f"Module not found: {module_name}"
    similar = find_similar_names(module_name, available_modules)
    if similar:
        suggestions = "\n".join(f"  - {name}" for name in similar[:max_suggestions])
        error += f"\n\nDid you mean one of these?\n{suggestions}"
    return error
```

Usage:
```python
error_msg = format_module_not_found_error(module_name, list(self.index["modules"].keys()))
```

**Estimated Impact:**
- Reduces codebase by ~15-20 lines
- Improves consistency
- **Impact Level:** LOW

---

### 3.2 Redundant Module Existence Checks
**Category:** Redundant Code  
**Severity:** LOW  
**File:** `/home/user/cicada/cicada/mcp/handlers/module_handlers.py` (lines 150-162)

**Issue:**
After wildcard pattern check fails (lines 103-149), code checks again with exact match:
```python
# Lines 150-162: Redundant exact match after wildcard handling
if module_name in self.index["modules"]:
    data = self.index["modules"][module_name]
    # ... formatting ...
    return [TextContent(type="text", text=result)]
```

This check should be consolidated with wildcard matching to avoid checking twice.

**Suggested Solution:**
Use unified pattern matching that handles both wildcard and exact matches:
```python
def _search_modules(self, pattern: str):
    """Unified search supporting wildcards and exact matches."""
    if has_wildcards(pattern):
        # wildcard search
    else:
        # exact match
    
    return results  # consistent return format
```

**Estimated Impact:**
- Reduces redundant logic
- Improves clarity
- **Impact Level:** LOW

---

## 4. STRUCTURAL ISSUES

### 4.1 Mixed Concerns in `ElixirIndexer` Class
**Category:** Single Responsibility Principle Violation  
**Severity:** MEDIUM  
**File:** `/home/user/cicada/cicada/indexer.py`

**Issue:**
`ElixirIndexer` mixes:
1. **File discovery** - `_find_elixir_files()` (lines 837-851)
2. **File parsing** - Uses `self.parser.parse_file()`
3. **Keyword extraction** - Complex extraction/expansion (lines 225-264, 274-331, etc.)
4. **Git integration** - Calls `git_helper.get_function_evolution()` (lines 336-358)
5. **Dependency extraction** - Calls `_extract_dependencies()` (lines 361-363)
6. **Index building** - Builds data structures
7. **File hashing** - Manages incremental changes
8. **Progress reporting** - Console output

**Suggested Solution:**
Create specialized classes:
```python
# cicada/indexer/file_discoverer.py
class FileDiscoverer:
    def find_elixir_files(self, repo_path: Path) -> list[Path]:
        # Current _find_elixir_files implementation

# cicada/indexer/keyword_extractor_handler.py
class KeywordExtractorHandler:
    def extract_and_expand(self, text: str, ...):
        # Encapsulate keyword extraction logic

# cicada/indexer/git_enricher.py
class GitEnricher:
    def enrich_function_metadata(self, func, file_path, ...):
        # Encapsulate git-related enrichment

# cicada/indexer/index_builder.py
class IndexBuilder:
    def build_module_info(self, module_data, ...):
        # Encapsulate index building
```

Then simplify `ElixirIndexer`:
```python
class ElixirIndexer:
    def __init__(self):
        self.parser = ElixirParser()
        self.file_discoverer = FileDiscoverer()
        self.keyword_handler = KeywordExtractorHandler()
        self.git_enricher = GitEnricher()
        self.index_builder = IndexBuilder()
    
    def index_repository(self, repo_path, ...):
        # Clean orchestration
        files = self.file_discoverer.find_elixir_files(repo_path)
        for file_path in files:
            modules = self.parser.parse_file(file_path)
            for module_data in modules:
                # Coordinate with handlers
```

**Estimated Impact:**
- Improves testability significantly
- Enables independent module testing
- Reduces class complexity
- **Impact Level:** MEDIUM (Longer-term refactor)

---

### 4.2 Scattered Module Lookup Logic Across Handlers
**Category:** Code Scattering  
**Severity:** MEDIUM  
**Files:**
- `/home/user/cicada/cicada/mcp/handlers/module_handlers.py` (lines 30-56)
- `/home/user/cicada/cicada/mcp/handlers/dependency_handlers.py` (lines 79-89)

**Issue:**
Module lookup and error handling is duplicated across handlers. Should be centralized.

**Suggested Solution:**
Create base handler or utility module:
```python
# cicada/mcp/handlers/base_handler.py
class BaseIndexHandler:
    def __init__(self, index, config):
        self.index = index
        self.config = config
    
    def lookup_module(self, module_name: str, with_suggestions: bool = True):
        """Consistent module lookup across all handlers."""
        # Shared implementation
```

Then inherit from it:
```python
class ModuleSearchHandler(BaseIndexHandler):
    async def search_module(self, module_name: str, ...):
        # Uses inherited lookup_module()
```

**Estimated Impact:**
- Reduces duplication by ~20 lines
- Improves consistency
- **Impact Level:** MEDIUM

---

### 4.3 Inconsistent Error Handling Patterns
**Category:** Inconsistent Error Handling  
**Severity:** LOW  
**Files:** All handler files

**Issue:**
Mix of patterns for error handling:
```python
# Pattern 1: Return error with None data
if not module_data:
    return None, error_msg

# Pattern 2: Return TextContent with error
return [TextContent(type="text", text=error_msg)]

# Pattern 3: Raise exception
raise ValueError(f"Invalid format: {changed_since}")
```

**Suggested Solution:**
Standardize on one pattern throughout handlers. Recommend Pattern 2 (TextContent) since handlers are MCP tools.

**Estimated Impact:**
- Improves consistency
- Makes error handling predictable
- **Impact Level:** LOW

---

## 5. SUMMARY TABLE

| Issue | Category | Severity | Files | Line Reduction | Effort |
|-------|----------|----------|-------|------------------|--------|
| Duplicated `parse_changed_since()` | Duplication | HIGH | git_handlers.py, function_handlers.py | 50 | Low |
| Duplicated module lookup | Duplication | MEDIUM | module_handlers.py, dependency_handlers.py | 15 | Low |
| **Keyword extraction duplication** | **Duplication** | **HIGH** | **indexer.py** | **120-150** | **Medium** |
| `index_repository()` too large | Complexity | MEDIUM | indexer.py | 100-150 | Medium |
| `incremental_index_repository()` duplication | Complexity | MEDIUM | indexer.py | 150-200 | High |
| Complex nested conditionals | Complexity | LOW | mcp/server.py | 3 | Low |
| Verbose error messages | Verbosity | LOW | Multiple handlers | 15-20 | Low |
| Redundant checks | Redundancy | LOW | module_handlers.py | 10-15 | Low |
| Mixed concerns in ElixirIndexer | Structure | MEDIUM | indexer.py | N/A | High |
| Scattered module lookup | Structure | MEDIUM | handlers | 20 | Medium |

---

## 6. RECOMMENDED PRIORITY ORDER

### Phase 1 (Quick Wins - Low Effort, High Impact):
1. Extract `parse_changed_since()` to shared utility (50 lines saved)
2. Extract keyword extraction logic (120-150 lines saved)
3. Standardize error messages (15-20 lines saved)

**Total:** ~185-220 lines saved, ~2-3 days effort

### Phase 2 (Medium Effort):
4. Break up `index_repository()` into smaller methods
5. Create base handler class for module lookup
6. Consolidate `incremental_index_repository()` with main indexer

**Total:** ~150-200 lines saved, ~5-7 days effort

### Phase 3 (Large Refactor):
7. Restructure `ElixirIndexer` with separated concerns
8. Create specialized handler classes

**Total:** Major architectural improvement, ~10-14 days effort

---

## 7. QUALITY METRICS

**Current State:**
- Handlers: ~440 lines with duplication
- Indexer: ~900 lines with mixed concerns
- Total analyzed: ~2,893 lines

**After Phase 1 Improvements:**
- Estimated reduction: 185-220 lines (~7%)
- Improvements: Better maintainability, consistency

**After All Phases:**
- Estimated reduction: 335-420 lines (~14%)
- Major improvements: Testability, modularity, consistency

