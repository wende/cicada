---
reviewed:
- cicada/languages/elixir/extractors/string.py:1af3af24d1a3ca5cfc11e07230f5e21b9975a009
- cicada/languages/python/string_extractor.py:1af3af24d1a3ca5cfc11e07230f5e21b9975a009
- cicada/indexer.py:1af3af24d1a3ca5cfc11e07230f5e21b9975a009
- cicada/keyword_search.py:1af3af24d1a3ca5cfc11e07230f5e21b9975a009
- cicada/query/orchestrator.py:1af3af24d1a3ca5cfc11e07230f5e21b9975a009
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# String-Based Indexing

<diff file="codebook/README.md">
```diff
diff --git a/codebook/README.md b/codebook/README.md
index c764d5d..b9dc752 100644
--- a/codebook/README.md
+++ b/codebook/README.md
@@ -22,8 +22,8 @@
 1. [AST-Level Indexing](../AST_INDEXING.md) - Extracts module, function, and class definitions with signatures and specs
 2. [Incremental Indexing](../INCREMENTAL_INDEXING.md) - Only reindexes changed files for fast updates (includes Watch Mode)
 3. [Automatic Language Detection](../AUTOMATIC_LANGUAGE_DETECTION.md) - Detects project type from mix.exs or pyproject.toml
-4. Configurable Keyword Tiers - Fast, Regular, or Max tiers for keyword extraction quality
-5. String-Based Indexing - Indexes string literals from function bodies (SQL, error messages, etc.)
+4. Keyword-Based Indexing - Keyword extraction from module names, function names, parameter names, docstrings, strings and inline comments
+5. [String-Based Indexing](../STRING_INDEXING.md) - Indexes string literals from function bodies (SQL, error messages, etc.)
 
 ## Semantic Search
 1. Keyword Search - Find code by concept using KeyBERT-based semantic matching
```
</diff>

<diff file="codebook/STRING_INDEXING.md">
```diff
diff --git a/codebook/STRING_INDEXING.md b/codebook/STRING_INDEXING.md
new file mode 100644
index 0000000..5fe4565
--- /dev/null
+++ b/codebook/STRING_INDEXING.md
@@ -0,0 +1,269 @@
+# String-Based Indexing
+
+Cicada supports indexing string literals from function bodies in addition to documentation keywords. This enables searching for code based on actual strings used in the implementation, such as SQL queries, error messages, log messages, and API endpoints.
+
+## Overview
+
+Traditional code search relies on documentation and function names. String-based indexing extends this by extracting and indexing the actual string literals embedded in your code. This is particularly valuable for finding:
+
+- **SQL queries**: `"SELECT * FROM users WHERE active = true"`
+- **Error messages**: `"User not found in the database"`
+- **Log messages**: `"Processing request for user %s"`
+- **API endpoints**: `"/api/v1/users"`
+- **Configuration keys**: `"database.connection.timeout"`
+
+## Architecture
+
+String extraction runs as a separate pass after main indexing (which uses SCIP for Python or tree-sitter for Elixir). This pass extracts string literals using language-specific parsers:
+
+```
+┌─────────────────────────────────────────────────────────────────┐
+│                    String Extraction Pass                        │
+├─────────────────────────────────────────────────────────────────┤
+│  Elixir: StringExtractor (tree-sitter)                          │
+│  Python: PythonStringExtractor (Python ast module)              │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                    String Filtering                              │
+│  • Skip documentation strings (@doc, @moduledoc, docstrings)    │
+│  • Filter strings < min_length (default: 3 chars)               │
+│  • Track function context for each string                        │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                 Keyword Extraction                               │
+│  • Apply RegularKeywordExtractor to string content              │
+│  • Apply 1.3x score boost for string-derived keywords           │
+│  • Expand keywords via lemminflect pipeline                      │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                    Index Storage                                 │
+│  • string_keywords: {keyword: score} dict                       │
+│  • string_sources: [{string, line, function}] list              │
+└─────────────────────────────────────────────────────────────────┘
+```
+
+## Language Support
+
+String extraction is currently implemented for **Elixir** and **Python** only. Other SCIP-based languages (TypeScript, Rust, Go, etc.) do not yet have string extraction.
+
+### Elixir
+
+**File:** `cicada/languages/elixir/extractors/string.py`
+
+The `StringExtractor` class uses tree-sitter to traverse the Elixir AST and extract string literals:
+
+- Extracts strings from `def`, `defp`, and `test` function bodies
+- Skips `@doc` and `@moduledoc` documentation attributes
+- Tracks the containing function for each string
+- Handles multiline strings, heredocs, and interpolated strings
+- Extracts strings from nested structures (maps, lists, tuples)
+
+**Extracted content includes:**
+- Regular string literals (`"hello"`)
+- Module name strings (`"Elixir.MyModule"`)
+- Atom-like strings (`:ok`, `:error`)
+- Error/success constants (`"ERROR"`, `"SUCCESS"`)
+
+### Python
+
+**File:** `cicada/languages/python/string_extractor.py`
+
+The `PythonStringExtractor` class uses Python's built-in `ast` module:
+
+- Extracts string constants from function and method bodies
+- Skips module, class, and function docstrings (first statement)
+- Handles f-strings by extracting static parts only
+- Tracks the containing function for each string
+
+### Other Languages
+
+String extraction is not yet implemented for other SCIP-based languages (TypeScript, JavaScript, Rust, Go, Java, etc.). Contributions welcome.
+
+---
+
+## How It Works
+
+### 1. String Extraction
+
+During indexing, when `extract_string_keywords=True` is enabled:
+
+```python
+# Elixir example
+string_extractor = StringExtractor(min_length=3)
+extracted_strings = string_extractor.extract_from_module(do_block, source_code)
+
+# Returns:
+[
+    {"string": "SELECT * FROM users", "line": 42, "function": "query_users"},
+    {"string": "User not found", "line": 55, "function": "get_user"},
+]
+```
+
+### 2. Keyword Extraction with Boost
+
+String content is processed through the keyword extraction pipeline with a **1.3x score boost**:
+
+```python
+result = keyword_extractor.extract_keywords(combined_text, top_n=10)
+keywords = {
+    kw: score * 1.3  # 1.3x boost for strings
+    for kw, score in result.get("top_keywords", [])
+}
+```
+
+This boost prioritizes implementation details over documentation when both contain similar keywords.
+
+### 3. Index Storage
+
+Keywords and source strings are stored at both module and function levels:
+
+```json
+{
+  "modules": {
+    "MyApp.Users": {
+      "string_keywords": {"select": 2.6, "users": 1.95, "database": 1.3},
+      "string_sources": [
+        {"string": "SELECT * FROM users", "line": 42, "function": "query_users"}
+      ],
+      "functions": [
+        {
+          "name": "query_users",
+          "string_keywords": {"select": 2.6, "users": 1.95},
+          "string_sources": [
+            {"string": "SELECT * FROM users", "line": 42, "function": "query_users"}
+          ]
+        }
+      ]
+    }
+  }
+}
+```
+
+---
+
+## Usage
+
+String indexing is **enabled by default** when you run `cicada index` or `cicada install`. No configuration is required.
+
+### Searching String Content
+
+#### Match Source Filter
+
+The `match_source` parameter controls where to search:
+
+| Value | Description |
+|-------|-------------|
+| `all` | Search both documentation and string keywords (default) |
+| `docs` | Search only documentation keywords |
+| `strings` | Search only string literal keywords |
+| `comments` | Search only inline comment keywords |
+
+#### Python API
+
+```python
+from cicada.keyword_search import KeywordSearcher
+
+# Search only in string literals
+searcher = KeywordSearcher(index, match_source="strings")
+results = searcher.search(["SELECT", "users"], top_n=10)
+
+# Search everywhere (default)
+searcher = KeywordSearcher(index, match_source="all")
+results = searcher.search(["database", "query"], top_n=10)
+```
+
+#### MCP Tool (query)
+
+Use the `match_source` parameter to filter searches to string literals:
+
+```
+query: ["SELECT", "users"]
+match_source: "strings"
+```
+
+---
+
+## Use Cases
+
+### Finding SQL Queries
+
+Search for code that interacts with specific database tables:
+
+```python
+# Find all code with SQL queries mentioning "users" table
+searcher = KeywordSearcher(index, match_source="strings")
+results = searcher.search(["SELECT", "users"], top_n=20)
+```
+
+### Finding Error Handlers
+
+Locate code that handles specific error conditions:
+
+```python
+# Find error handling for authentication failures
+results = searcher.search(["authentication", "failed", "error"], top_n=10)
+```
+
+### Finding API Endpoints
+
+Discover code that defines or calls specific API routes:
+
+```python
+# Find code related to user API endpoints
+results = searcher.search(["/api/v1/users"], top_n=10)
+```
+
+### Finding Configuration Usage
+
+Locate code that uses specific configuration keys:
+
+```python
+# Find where database timeout is configured
+results = searcher.search(["database", "timeout"], top_n=10)
+```
+
+---
+
+## Configuration
+
+### Minimum String Length
+
+The `min_length` parameter controls the minimum string length to extract (default: 3):
+
+```python
+# Only extract strings with 5+ characters
+string_extractor = StringExtractor(min_length=5)
+```
+
+Strings shorter than `min_length` are filtered out to reduce noise from single characters and very short strings.
+
+### Score Boost
+
+String-derived keywords receive a **1.3x score boost** by default. This can be observed in the index where string keywords have higher scores than equivalent documentation keywords.
+
+---
+
+## File Reference
+
+| File | Description |
+|------|-------------|
+| `cicada/languages/elixir/extractors/string.py` | Elixir string extraction using tree-sitter |
+| `cicada/languages/python/string_extractor.py` | Python string extraction using ast module |
+| `cicada/indexer.py` | `_extract_string_keywords()` method for Elixir indexing |
+| `cicada/keyword_search.py` | `KeywordSearcher` with `match_source` filtering |
+| `cicada/query/orchestrator.py` | Query tool integration with match_source parameter |
+
+---
+
+## Limitations
+
+1. **Interpolated strings**: For f-strings (Python) and string interpolation (Elixir), only static parts are extracted
+2. **Dynamic strings**: Strings built at runtime through concatenation are not indexed
+3. **Binary strings**: Raw binary data is not processed for keywords
+4. **Performance**: Enabling string indexing increases index size and indexing time slightly
```
</diff>

--- FEATURE TASK ---
Document the String-Based Indexing feature for Cicada. This feature extracts and indexes string literals from function bodies (SQL queries, error messages, log messages, API endpoints) to enable searching code by implementation details rather than just documentation.

--- NOTES ---
During documentation, discovered that `extract_string_keywords` was incorrectly defaulting to `False` in the codebase. This was a bug - string indexing should always be enabled by default alongside regular keyword extraction.

--- SOLUTION ---
1. Created comprehensive documentation in `codebook/STRING_INDEXING.md` covering:
   - Architecture diagram showing the extraction pipeline
   - Language support for Elixir (tree-sitter) and Python (ast module)
   - How string extraction, keyword boosting (1.3x), and index storage work
   - The `match_source` filter parameter for searching
   - Use cases and limitations

2. Added link to STRING_INDEXING.md in codebook/README.md

3. Fixed bug: Enabled string indexing by default (was incorrectly disabled):
   - `cicada/setup.py`: Added `extract_string_keywords=True` to indexer call
   - `cicada/mcp/handlers/index_manager.py`: Removed config.get() calls, hardcoded `extract_keywords=True` and `extract_string_keywords=True` in both `_incremental_refresh` and `force_refresh` methods
   - `tests/setup/test_setup.py`: Updated test to expect `extract_string_keywords=True` parameter
