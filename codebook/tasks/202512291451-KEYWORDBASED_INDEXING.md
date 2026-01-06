---
reviewed:
- cicada/extractors/keyword.py:8e015a29dec09cbfdecc315053f3dddf22a8bb52
- cicada/keyword_expander.py:8e015a29dec09cbfdecc315053f3dddf22a8bb52
- cicada/utils/keyword_utils.py:8e015a29dec09cbfdecc315053f3dddf22a8bb52
- cicada/utils/text_utils.py:8e015a29dec09cbfdecc315053f3dddf22a8bb52
- cicada/indexer.py:8e015a29dec09cbfdecc315053f3dddf22a8bb52
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# Keyword-Based Indexing

<diff file="codebook/KEYWORD_INDEXING.md">
```diff
diff --git a/codebook/KEYWORD_INDEXING.md b/codebook/KEYWORD_INDEXING.md
new file mode 100644
index 0000000..76d508d
--- /dev/null
+++ b/codebook/KEYWORD_INDEXING.md
@@ -0,0 +1,235 @@
+# Keyword-Based Indexing
+
+Cicada extracts and indexes keywords from multiple code sources during indexing, enabling fast keyword-based search across the codebase. Keywords are extracted from module names, function names, parameter names, docstrings, string literals, and inline comments.
+
+## Overview
+
+Keyword-based indexing is the foundation of Cicada's search capabilities. During indexing, keywords are extracted from various sources and stored with weighted scores that reflect their importance. This enables:
+
+1. **Fast Search**: Pre-computed keywords allow instant search without full-text scanning
+2. **Relevance Ranking**: Keywords have weights based on their source (code identifiers > documentation > strings)
+3. **Stemming/Inflection**: Keywords are expanded to related forms (e.g., "run" → "runs", "running", "ran")
+
+## Architecture
+
+```
+┌─────────────────────────────────────────────────────────────────┐
+│                      Source Code                                 │
+│  • Module names (MyApp.Users.Admin)                             │
+│  • Function names (create_user, getUserData)                    │
+│  • Parameter names (user_id, email)                             │
+│  • Docstrings (@doc, @moduledoc, """...""")                    │
+│  • String literals ("SELECT * FROM users")                      │
+│  • Inline comments (# TODO: fix this)                           │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                   Identifier Splitting                           │
+│  • camelCase → camel, case                                      │
+│  • PascalCase → pascal, case                                    │
+│  • snake_case → snake, case                                     │
+│  • HTTPServer → http, server                                    │
+│  • MyApp.Users → my, app, users                                 │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                   Keyword Extraction                             │
+│  • Term frequency calculation                                    │
+│  • Stopword filtering                                            │
+│  • Weight assignment by source                                   │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                   Keyword Expansion                              │
+│  • lemminflect-based inflection                                 │
+│  • run → runs, running, ran                                     │
+│  • Penalty multiplier (0.7x) for derived forms                  │
+└────────────────────┬────────────────────────────────────────────┘
+                     │
+                     ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                      Index Storage                               │
+│  • keywords: {keyword: weight, ...}                             │
+│  • string_keywords: {keyword: weight, ...}                      │
+│  • keyword_sources: {keyword: "docs"|"strings"|"comments"}      │
+└─────────────────────────────────────────────────────────────────┘
+```
+
+## Keyword Sources and Weights
+
+Keywords are extracted from multiple sources with different weights to reflect their importance:
+
+| Source | Weight | Description |
+|--------|--------|-------------|
+| Code identifiers | 10x | camelCase, snake_case, PascalCase names directly from code |
+| Split identifiers | 3x | Words split from identifiers (getUserData → get, user, data) |
+| Name keywords | 1.5x | Module/function names (boosted for discoverability) |
+| Documentation | 1x | Words from @doc, @moduledoc, docstrings |
+| String literals | 1.3x | Strings in function bodies (SQL queries, error messages) |
+| Comments | 1x | Inline comments |
+
+### Inflection Penalty
+
+When keywords are expanded via lemminflect, derived forms receive a penalty:
+
+- **Original keyword**: Full score (1.0x)
+- **Inflected forms**: 0.7x penalty (e.g., "run" → "running" gets 70% of original score)
+
+## Identifier Splitting
+
+Cicada intelligently splits compound identifiers into component words:
+
+```python
+# camelCase
+"getUserData" → ["get", "user", "data"]
+
+# PascalCase  
+"UserController" → ["user", "controller"]
+
+# snake_case
+"get_user_data" → ["get", "user", "data"]
+
+# Acronyms
+"HTTPServer" → ["http", "server"]
+"PostgreSQL" → ["postgre", "sql"]
+
+# Mixed patterns
+"getHTTPResponseCode" → ["get", "http", "response", "code"]
+
+# Module paths
+"MyApp.Users.Admin" → ["my", "app", "users", "admin"]
+```
+
+## Keyword Extraction Pipeline
+
+### RegularKeywordExtractor
+
+The default extractor uses term frequency (TF) scoring:
+
+```python
+from cicada.extractors.keyword import RegularKeywordExtractor
+
+extractor = RegularKeywordExtractor(verbose=True)
+result = extractor.extract_keywords(text, top_n=15)
+
+# Returns:
+{
+    "top_keywords": [("user", 5), ("create", 3), ...],
+    "regular_words": ["user", "create", "admin", ...],
+    "code_identifiers": ["getUserData", "createUser"],
+    "code_split_words": ["get", "user", "data", "create"],
+    "tf_scores": {"user": 0.15, "create": 0.09, ...},
+    "stats": {
+        "total_tokens": 150,
+        "total_words": 120,
+        "unique_words": 45
+    }
+}
+```
+
+### Stopword Filtering
+
+Common English words are filtered out to reduce noise:
+
+- Articles: the, a, an
+- Prepositions: in, on, at, to, for, of, with, by, from
+- Conjunctions: and, or, but
+- Pronouns: it, they, them, this, that
+- Common verbs: is, are, was, were, be, have, has, do, does
+
+## Keyword Expansion
+
+Keywords are expanded using lemminflect to include inflected forms:
+
+```python
+from cicada.keyword_expander import KeywordExpander
+
+expander = KeywordExpander(expansion_type="lemmi", verbose=True)
+result = expander.expand_keywords(
+    ["run", "database"],
+    keyword_scores={"run": 0.95, "database": 0.8}
+)
+
+# Returns:
+{
+    "words": [
+        {"word": "run", "score": 0.95, "source": "original"},
+        {"word": "running", "score": 0.665, "source": "inflection", "parent": "run"},
+        {"word": "runs", "score": 0.665, "source": "inflection", "parent": "run"},
+        {"word": "ran", "score": 0.665, "source": "inflection", "parent": "run"},
+        {"word": "database", "score": 0.8, "source": "original"},
+        {"word": "databases", "score": 0.56, "source": "inflection", "parent": "database"},
+    ],
+    "simple": ["database", "databases", "ran", "run", "running", "runs"]
+}
+```
+
+### Code Identifiers Not Inflected
+
+Code identifiers (camelCase, snake_case names) are NOT inflected to preserve exact matches:
+
+```python
+# "getUserData" stays as "getUserData", not expanded to "getUsersData"
+# "create_user" stays as "create_user", not expanded to "creates_user"
+```
+
+## Index Structure
+
+Keywords are stored in the index with their weights:
+
+```json
+{
+  "modules": {
+    "MyApp.Users": {
+      "keywords": {
+        "user": 15.0,
+        "users": 10.5,
+        "create": 8.0,
+        "admin": 5.0
+      },
+      "string_keywords": {
+        "select": 1.3,
+        "from": 1.3,
+        "users": 1.3
+      },
+      "functions": [
+        {
+          "name": "create_user",
+          "keywords": {
+            "create": 10.0,
+            "user": 10.0,
+            "email": 3.0,
+            "password": 3.0
+          }
+        }
+      ]
+    }
+  }
+}
+```
+
+## Configuration
+
+Keyword-based indexing is always enabled by default. No configuration is required.
+
+The extraction method defaults to:
+- **Extraction**: `regular` (term frequency based)
+- **Expansion**: `lemmi` (lemminflect-based inflection)
+
+## File Reference
+
+| File | Description |
+|------|-------------|
+| `cicada/extractors/keyword.py` | RegularKeywordExtractor and BaseKeywordExtractor classes |
+| `cicada/keyword_expander.py` | KeywordExpander class for lemminflect-based expansion |
+| `cicada/utils/keyword_utils.py` | Factory functions for creating extractors |
+| `cicada/utils/text_utils.py` | Identifier splitting utilities (split_identifier, extract_code_identifiers) |
+| `cicada/indexer.py` | ElixirIndexer._extract_name_keywords() for name-based keyword extraction |
+
+## Related Documentation
+
+- [Keyword Search](../KEYWORD_SEARCH.md) - How to search using extracted keywords
+- [String-Based Indexing](../STRING_INDEXING.md) - Extracting keywords from string literals
```
</diff>

<diff file="codebook/README.md">
```diff
diff --git a/codebook/README.md b/codebook/README.md
index e5d720a..95c77e6 100644
--- a/codebook/README.md
+++ b/codebook/README.md
@@ -22,7 +22,7 @@
 1. [AST-Level Indexing](../AST_INDEXING.md) - Extracts module, function, and class definitions with signatures and specs
 2. [Incremental Indexing](../INCREMENTAL_INDEXING.md) - Only reindexes changed files for fast updates (includes Watch Mode)
 3. [Automatic Language Detection](../AUTOMATIC_LANGUAGE_DETECTION.md) - Detects project type from mix.exs or pyproject.toml
-4. Keyword-Based Indexing - Keyword extraction from module names, function names, parameter names, docstrings, strings and inline comments
+4. [Keyword-Based Indexing](../KEYWORD_INDEXING.md) - Keyword extraction from module names, function names, parameter names, docstrings, strings and inline comments
 5. [String-Based Indexing](../STRING_INDEXING.md) - Indexes string literals from function bodies (SQL, error messages, etc.)
 
 ## Semantic Search
@@ -30,9 +30,7 @@
 2. [Pattern Search](../KEYWORD_SEARCH.md#wildcard-patterns) - Find code using wildcards (*) and OR patterns (|)
 3. [Mixed Queries](../KEYWORD_SEARCH.md#synonym-groups) - Combine keywords and patterns in a single search
 4. [Match Source Filtering](../KEYWORD_SEARCH.md#match-source-filtering) - Search in docs, strings, or comments separately
-5. Scope Filtering - Filter by public/private visibility
-6. Path Filtering - Filter results by file path using glob patterns
-7. Recent Changes Filter - Filter to code changed in the last 14 days
+5. Filtering - Filter by public/private visibility, file path using glob patterns, code recency 
 
 ## Module Analysis
 1. Complete API View - View all functions with arity, signatures, docs, and typespecs
```
</diff>

---
After completing the task, please update the task file with:
- Description of the feature task that was requested
- Short description of the changes that were made and why
Include implemenentation details how the task was implemented.
Do not include code snippets. Only describe the functional changes that were made.
Do not remove diff lines from the task file.
--- FEATURE TASK ---
Document the Keyword-Based Indexing feature for Cicada. This is the foundation of Cicada's search capabilities, extracting keywords from module names, function names, parameter names, docstrings, string literals, and inline comments during indexing.

--- NOTES ---
This documentation covers the entire keyword extraction and expansion pipeline:
- RegularKeywordExtractor uses term frequency (TF) scoring, not KeyBERT
- Keywords are weighted by source (code identifiers 10x, split identifiers 3x, documentation 1x, strings 1.3x)
- lemminflect is used for keyword expansion with 0.7x penalty for inflected forms
- Code identifiers (camelCase, snake_case) are NOT inflected to preserve exact matches
- Keyword-based indexing is always enabled by default, no configuration required

--- SOLUTION ---
1. Created comprehensive documentation in `codebook/KEYWORD_INDEXING.md` covering:
   - Architecture diagram showing the full pipeline from source code to index storage
   - Keyword sources and weights table
   - Inflection penalty explanation (0.7x for derived forms)
   - Identifier splitting examples (camelCase, PascalCase, snake_case, acronyms)
   - RegularKeywordExtractor API and return structure
   - Stopword filtering list
   - KeywordExpander API with lemminflect
   - Index structure showing keywords and string_keywords storage
   - Configuration defaults (always enabled)
   - File reference table

2. Updated codebook/README.md:
   - Added link to KEYWORD_INDEXING.md
