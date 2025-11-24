# Indexing Features

## String-Based Indexing

Cicada supports indexing string literals from function bodies in addition to documentation keywords. This allows searching for code based on actual strings used in the implementation (e.g., SQL queries, error messages, log messages, API endpoints).

### How It Works

1. **String Extraction:**
   - Extracts string literals from function bodies during indexing
   - Filters out documentation strings and strings shorter than 3 characters
   - Tracks function context for each string
   - Module names, atoms, and all-caps strings ARE included

2. **Keyword Extraction:**
   - Applies the same keyword extraction pipeline (KeyBERT + expansion) to string content
   - String keywords receive a **1.3x boost** to prioritize implementation over documentation

3. **Index Storage:**
   - Module-level: `string_keywords` (dict) and `string_sources` (list)
   - Function-level: same structure within each function object

### Usage

```python
# Indexing with string keywords
indexer = ElixirIndexer(verbose=True)
indexer.index_repository(
    repo_path="/path/to/repo",
    extract_keywords=True,
    extract_string_keywords=True
)

# Searching with match source filtering
searcher = KeywordSearcher(index, match_source="strings")  # "docs", "all"
results = searcher.search(["database", "query"], top_n=10)
```

### MCP Tool

```json
{
  "keywords": ["SELECT", "users", "database"],
  "match_source": "strings",
  "filter_type": "functions"
}
```

**Implementation:** `cicada/elixir/extractors/string.py`, `cicada/keyword_search.py`

## Co-occurrence-Based Keyword Suggestions

Provides intelligent keyword suggestions based on co-occurrence patterns in your codebase.

### How It Works

**During Indexing:**
- Tracks which keywords appear together in function/module documentation and signatures
- Uses keywords **BEFORE semantic expansion** to reflect actual codebase content
- Automatically built when keyword extraction is enabled

**During Search:**
- **Expand mode:** Suggests related keywords when search returns few results
- **Narrow mode:** Suggests refinement keywords when too many results

### Usage

```python
# Automatic during indexing
indexer.index_repository(extract_keywords=True)  # Co-occurrence enabled

# Using MCP tool
{
  "tool": "suggest_keywords",
  "arguments": {
    "keywords": ["provider"],
    "mode": "expand",  // or "narrow"
    "top_n": 5
  }
}
```

**Implementation:** `cicada/cooccurrence.py`, `cicada/keyword_search.py`

## Co-Change Analysis

Analyzes git commit history to identify files and functions that are frequently modified together.

### How It Works

1. **Git History Analysis:**
   - Analyzes git log to identify co-changed files and functions
   - Tracks frequency at both file and function levels

2. **Search Boosting:**
   - Applies configurable boost to search scores (default: 0.5)
   - Module-level: 0.01 × co-change count
   - Function-level: 0.02 × co-change count
   - File-level: 0.005 × co-change count

3. **Result Enhancement:**
   - Results include `cochange_info` with related files/functions
   - Top 5 related items displayed in formatted output

### Usage

```bash
# Indexing with co-change extraction
cicada index --extract-cochange

# Or with other options
cicada index --extract-keywords --extract-cochange
```

```python
# Searching with co-change boosting
searcher = KeywordSearcher(index, cochange_boost=0.5)  # 1.0, 0.0
results = searcher.search(["authentication", "user"], top_n=10)
```

### MCP Tool

```json
{
  "keywords": ["authentication", "credentials"],
  "cochange_boost": 0.5,
  "filter_type": "modules"
}
```

### Use Cases

1. **Discovering Related Code:** Find modules that frequently change together
2. **Impact Analysis:** See which modules typically need updates together
3. **Code Organization Insights:** Identify potential refactoring candidates
4. **Onboarding:** Help new developers find related functionality

**Implementation:** `cicada/git/cochange_analyzer.py`, `cicada/keyword_search.py`
