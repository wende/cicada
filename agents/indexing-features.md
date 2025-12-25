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
   - Applies the same keyword extraction pipeline (regular + lemminflect expansion) to string content
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

**Status:** ✅ Enabled by default for all users

Analyzes git commit history to identify files and functions that are frequently modified together, revealing architectural relationships that code dependencies don't show.

### Performance (Optimized)

**Strategy:** Batched git queries + adaptive commit limits + 50% function sampling

- **Small repos** (<500 commits): Analyzes entire history
- **Medium repos** (500-3000 commits): Analyzes last 1500 commits
- **Large repos** (>3000 commits): Analyzes last 1500-2000 commits
- **Speed:** 1-10 seconds depending on repo size (15-20x faster than previous implementation)
- **Accuracy:** File-level 100%, Function-level 90-95%

### How It Works

1. **Batched Git Analysis (single subprocess call):**
   - Gets all file changes across analyzed commits in one `git log` call
   - 10-50x faster than per-commit subprocess calls
   - Processes remaining operations in-memory

2. **Adaptive Commit Limit:**
   - Automatically adjusts based on repository size
   - Smaller repos get more thorough analysis
   - Larger repos focus on recent commits (typically more relevant)

3. **50% Function Sampling:**
   - Analyzes every other commit for function-level changes
   - Scales counts by 2x to estimate total
   - 2x speedup for ~5-10% variance (acceptable for search boosting)
   - File-level analysis is always 100% accurate

4. **Search Boosting:**
   - Applies configurable boost to search scores (default: 0.5)
   - Module-level: 0.01 × co-change count
   - Function-level: 0.02 × co-change count
   - File-level: 0.005 × co-change count

### Usage

```bash
# Indexing with co-change enabled (default)
cicada index

# Disable if not needed
cicada index --no-cochange

# With other options
cicada index --extract-keywords
```

```python
# Searching with co-change boosting
searcher = KeywordSearcher(index, cochange_boost=0.5)  # 0.0 to disable
results = searcher.search(["authentication", "user"], top_n=10)
```

### Index Structure

```json
{
  "cochange_metadata": {
    "analyzed_at": "2025-11-27T10:30:00",
    "commit_count": 1000,
    "max_commits_limit": 1500,
    "function_sample_rate": 0.5,
    "file_pairs": 42,
    "function_pairs": 87,
    "optimization": "batched_recency_sampling"
  },
  "modules": {
    "MyApp.Auth": {
      "cochange_files": [
        {"file": "lib/myapp/users/token.ex", "count": 8}
      ],
      "functions": [
        {
          "name": "validate",
          "cochange_functions": [
            {"module": "MyApp.Users", "function": "create", "arity": 1, "count": 5}
          ]
        }
      ]
    }
  }
}
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
5. **Search Quality:** Improve search results with behavioral insights

### Configuration

No manual configuration needed - everything is adaptive and automatic. Disable with `--no-cochange` if analyzing a very large repository is too slow.

**Implementation:** `cicada/git/cochange_analyzer.py`, `cicada/indexer.py`, `cicada/keyword_search.py`
