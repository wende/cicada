---
reviewed:
- cicada/mcp/server.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/router.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/tools.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/handlers/module_handlers.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/handlers/function_handlers.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/handlers/git_handlers.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/handlers/pr_handlers.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/handlers/analysis_handlers.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/handlers/index_manager.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/query/orchestrator.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/query/types.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/fallbacks.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/filter_utils.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
- cicada/mcp/pattern_utils.py:cd2610d1e7cab92ed019e3ff3c101d520ec3e2ef
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# MCP Tools Documentation

<diff file="codebook/MCP_TOOLS.md">
```diff
diff --git a/codebook/MCP_TOOLS.md b/codebook/MCP_TOOLS.md
new file mode 100644
index 0000000..04cc823
--- /dev/null
+++ b/codebook/MCP_TOOLS.md
@@ -0,0 +1,473 @@
+# MCP Tools
+
+Cicada exposes its code intelligence capabilities through the Model Context Protocol (MCP), providing AI assistants with powerful tools for code exploration, analysis, and discovery.
+
+## Overview
+
+The MCP (Model Context Protocol) is a standardized interface for AI assistants to interact with external tools. Cicada implements 7 MCP tools organized into three categories:
+
+1. **Discovery Tools**: Find code by keywords, patterns, or semantic search
+   - `query` - Primary entry point for all code exploration
+   - `expand_result` - Drill down into specific results
+
+2. **Analysis Tools**: Deep-dive into modules and functions
+   - `search_module` - Complete module API with dependency analysis
+   - `search_function` - Function definitions and call sites
+
+3. **Utility Tools**: Index management and advanced queries
+   - `git_history` - Git history and PR attribution (see [GIT_HISTORY.md](../GIT_HISTORY.md))
+   - `refresh_index` - Force index refresh
+   - `query_jq` - Advanced jq queries against the index
+
+## Architecture
+
+### System Overview
+
+```
+┌─────────────────────────────────────────────────────────────────┐
+│                         MCP Client                               │
+│               (Claude Code, Cursor, VS Code)                     │
+└────────────────────────────┬────────────────────────────────────┘
+                             │ MCP Protocol
+                             ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                       CicadaServer                               │
+│                    (cicada/mcp/server.py)                        │
+│  • Tool definitions                                              │
+│  • Request logging                                               │
+│  • Error handling                                                │
+└────────────────────────────┬────────────────────────────────────┘
+                             │
+                             ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                       ToolRouter                                 │
+│                   (cicada/mcp/router.py)                         │
+│  • Argument validation                                           │
+│  • Tool routing                                                  │
+│  • Handler coordination                                          │
+└──────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
+       │          │          │          │          │
+       ▼          ▼          ▼          ▼          ▼
+┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
+│ Module   │ │ Function │ │   Git    │ │   PR     │ │ Analysis │
+│ Handler  │ │ Handler  │ │ Handler  │ │ Handler  │ │ Handler  │
+└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
+       │          │          │          │          │
+       └──────────┴──────────┴──────────┴──────────┘
+                             │
+                             ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                       IndexManager                               │
+│                (cicada/mcp/handlers/index_manager.py)            │
+│  • Index loading & caching                                       │
+│  • Staleness detection                                           │
+│  • Auto-refresh                                                  │
+└─────────────────────────────────────────────────────────────────┘
+```
+
+### Key Components
+
+| Component | Location | Description |
+|-----------|----------|-------------|
+| `CicadaServer` | `cicada/mcp/server.py` | MCP server implementation |
+| `ToolRouter` | `cicada/mcp/router.py` | Routes tool calls to handlers |
+| `ModuleSearchHandler` | `cicada/mcp/handlers/module_handlers.py` | Module search and usage analysis |
+| `FunctionSearchHandler` | `cicada/mcp/handlers/function_handlers.py` | Function search and call sites |
+| `GitHistoryHandler` | `cicada/mcp/handlers/git_handlers.py` | Git history queries |
+| `PRHistoryHandler` | `cicada/mcp/handlers/pr_handlers.py` | PR lookup and enrichment |
+| `AnalysisHandler` | `cicada/mcp/handlers/analysis_handlers.py` | Query orchestration and jq queries |
+| `IndexManager` | `cicada/mcp/handlers/index_manager.py` | Index lifecycle management |
+| `get_tool_definitions` | `cicada/mcp/tools.py` | Tool schema definitions |
+
+---
+
+## Tool Reference
+
+### query
+
+**Primary entry point for all code exploration and discovery.**
+
+The `query` tool is the "Google for code" - start here for any search task. It intelligently detects whether you're searching by keywords or patterns and combines results from multiple sources.
+
+#### Smart Auto-Detection
+
+| Input | Detection | Behavior |
+|-------|-----------|----------|
+| `['authentication', 'login']` | Keywords | Semantic search across docs and strings |
+| `'MyApp.User.create*'` | Pattern | Exact pattern matching with wildcards |
+| `['oauth', 'MyApp.Auth.*']` | Mixed | Combines keyword and pattern search |
+
+#### Parameters
+
+| Parameter | Type | Description |
+|-----------|------|-------------|
+| `query` | string \| string[] | Keywords, patterns, or mixed (required) |
+| `scope` | `'all'` \| `'public'` \| `'private'` | Filter by visibility (default: 'all') |
+| `recent` | boolean | Filter to last 14 days (default: false) |
+| `result_type` | `'all'` \| `'modules'` \| `'functions'` | Filter result type (default: 'all') |
+| `match_source` | `'all'` \| `'docs'` \| `'strings'` \| `'comments'` | Where to search (default: 'all') |
+| `glob` | string | Glob pattern for file path filtering |
+| `path` | string | Base directory (prepended to glob) |
+| `type` | string | File type shorthand (e.g., 'py', 'ex', 'ts') |
+| `max_results` | integer | Maximum results (default: 10) |
+| `offset` | integer | Skip first N results for pagination |
+| `show_snippets` | boolean | Show code context (default: false) |
+| `verbose` | boolean | Full docs and confidence scores |
+
+#### Output Features
+
+- **Match indicators**: `(d)` docs, `(s)` strings, `(d+s)` both
+- **Smart suggestions**: Recommends next tools to use
+- **Recency labels**: Shows how recently code was modified
+
+#### Examples
+
+```python
+# Find authentication code
+query(['authentication', 'login'])
+
+# Find functions in auth module
+query('MyApp.Auth.*')
+
+# Find recent SQL queries in strings
+query(['sql', 'select'], match_source='strings', recent=True)
+
+# Find code in specific directory
+query('create_user', path='lib/accounts', type='ex')
+```
+
+---
+
+### search_module
+
+**View a module's complete API and dependency relationships.**
+
+Use after `query` discovers relevant modules. Shows all functions with signatures, docs, and analyzes what calls this module and what it depends on.
+
+#### Parameters
+
+| Parameter | Type | Description |
+|-----------|------|-------------|
+| `module_name` | string | Module name or pattern (supports `*` and `\|`) |
+| `file_path` | string | Alternative: path to file containing module |
+| `type` | `'public'` \| `'private'` \| `'all'` | Which functions to show (default: 'public') |
+| `what_calls_it` | boolean | Show where this module is used (default: false) |
+| `usage_type` | `'source'` \| `'tests'` \| `'all'` | Filter usage by file type |
+| `what_it_calls` | boolean | Show module dependencies (default: false) |
+| `dependency_depth` | integer | Transitive dependency depth (default: 1) |
+| `verbose` | boolean | Include docs, specs, moduledoc |
+| `glob` | string | Filter results by file path |
+| `head_limit` | integer | Max results for wildcards (default: 20) |
+
+#### Dependency Analysis
+
+**what_calls_it=true** - Critical for impact analysis before refactoring:
+- Shows all files that alias, import, require, or use the module
+- Lists all function call sites with file:line references
+- Filters by source vs test files
+
+**what_it_calls=true** - Understand module dependencies:
+- Lists all modules this module depends on
+- Groups by internal (same project) vs external (libraries)
+- Optional: show which functions use which dependencies
+
+#### Examples
+
+```python
+# View module API
+search_module('MyApp.Accounts.User')
+
+# Check impact before refactoring
+search_module('MyApp.Auth', what_calls_it=True)
+
+# Understand dependencies
+search_module('MyApp.Auth', what_it_calls=True, dependency_depth=2)
+
+# Wildcard search
+search_module('MyApp.Accounts.*', head_limit=10)
+```
+
+---
+
+### search_function
+
+**Find function definitions and all call sites.**
+
+Use after `query` finds functions you want to analyze. Shows definition location, signature, documentation, and everywhere the function is called.
+
+#### Parameters
+
+| Parameter | Type | Description |
+|-----------|------|-------------|
+| `function_name` | string | Function pattern (required, supports `*`, `\|`, arity) |
+| `module_path` | string | Optional module prefix |
+| `what_calls_it` | boolean | Show call sites (default: true) |
+| `what_it_calls` | boolean | Show function's dependencies (default: false) |
+| `include_usage_examples` | boolean | Show code snippets of calls |
+| `max_examples` | integer | Max code examples (default: 5) |
+| `usage_type` | `'source'` \| `'tests'` \| `'all'` | Filter call sites by file type |
+| `changed_since` | string | Filter by modification time |
+| `verbose` | boolean | Include docs and specs |
+| `glob` | string | Filter by file path |
+
+#### Pattern Syntax
+
+| Pattern | Matches |
+|---------|---------|
+| `create_user` | Any function named `create_user` |
+| `MyApp.User.create_user` | Specific module.function |
+| `create_user/2` | With specific arity |
+| `create*` | Wildcard prefix |
+| `create*\|update*` | OR patterns |
+| `lib/accounts/*.ex:create*` | File-scoped search |
+
+#### changed_since Formats
+
+| Format | Example | Description |
+|--------|---------|-------------|
+| Relative days | `7d` | Last 7 days |
+| Relative weeks | `2w` | Last 2 weeks |
+| ISO date | `2024-12-01` | Since specific date |
+| Git ref | `v1.0.0` | Since git tag/commit |
+
+#### Examples
+
+```python
+# Find function and its call sites
+search_function('create_user')
+
+# See what a function calls
+search_function('handle_request', what_it_calls=True)
+
+# Find recently changed functions
+search_function('*', changed_since='7d', glob='lib/accounts/**')
+
+# See only test usages
+search_function('create_user', usage_type='tests')
+```
+
+---
+
+### expand_result
+
+**Drill down into a specific query result.**
+
+Convenience wrapper that auto-detects whether you're expanding a module or function and calls the appropriate handler. Perfect for following query suggestions.
+
+#### Parameters
+
+| Parameter | Type | Description |
+|-----------|------|-------------|
+| `identifier` | string | Module or function reference (required) |
+| `type` | `'auto'` \| `'module'` \| `'function'` | Force type detection (default: 'auto') |
+| `include_code` | boolean | Include code snippets (default: true) |
+| `what_calls_it` | boolean | Show usages/call sites (default: true) |
+| `what_it_calls` | boolean | Show dependencies (default: false) |
+
+#### Auto-Detection
+
+| Identifier | Detected As |
+|------------|-------------|
+| `MyApp.Auth` | Module |
+| `MyApp.Auth.verify_token/2` | Function |
+| `verify_token` | Function |
+
+#### Examples
+
+```python
+# Expand from query result
+expand_result('MyApp.Auth.verify_token/2')
+
+# Force module expansion
+expand_result('MyApp.Auth', type='module')
+
+# Include dependency analysis
+expand_result('MyApp.Auth', what_it_calls=True)
+```
+
+---
+
+### refresh_index
+
+**Force refresh the code index.**
+
+Use when auto-refresh hasn't caught recent edits, or when query results seem stale.
+
+#### Parameters
+
+| Parameter | Type | Description |
+|-----------|------|-------------|
+| `force_full` | boolean | Full reindex vs incremental (default: false) |
+
+#### Refresh Modes
+
+| Mode | Speed | Use Case |
+|------|-------|----------|
+| Incremental | ~1-2s | Default, only changed files |
+| Full | Slower | When incremental seems stale |
+
+#### Examples
+
+```python
+# Quick incremental refresh
+refresh_index()
+
+# Full rebuild
+refresh_index(force_full=True)
+```
+
+---
+
+### query_jq
+
+**Execute custom jq queries against the index.**
+
+Advanced tool for custom analysis, debugging, and exploring data not covered by specialized tools.
+
+#### Parameters
+
+| Parameter | Type | Description |
+|-----------|------|-------------|
+| `query` | string | jq query expression (required) |
+| `format` | `'compact'` \| `'pretty'` | Output format (default: 'compact') |
+| `sample` | boolean | Limit to first 5 items (default: false) |
+
+#### Index Schema
+
+```json
+{
+  "modules": {
+    "<module_name>": {
+      "file": "lib/my_app/user.ex",
+      "line": 1,
+      "moduledoc": "Module documentation...",
+      "functions": [
+        {
+          "name": "create_user",
+          "arity": 2,
+          "line": 15,
+          "type": "def",
+          "doc": "Function documentation...",
+          "signature": "create_user(attrs, opts)",
+          "keywords": {...},
+          "string_keywords": {...}
+        }
+      ],
+      "keywords": {...},
+      "aliases": [...],
+      "imports": [...]
+    }
+  },
+  "metadata": {
+    "indexed_at": "2025-01-15T10:30:00Z",
+    "total_modules": 150,
+    "total_functions": 1200
+  }
+}
+```
+
+#### Schema Discovery
+
+Append `| schema` to any query to see available fields:
+
+```python
+query_jq('.modules | schema')
+query_jq('.modules[].functions | schema')
+```
+
+#### Common Queries
+
+```python
+# List all modules
+query_jq('.modules | keys')
+
+# Count functions per module
+query_jq('.modules | to_entries | map({name: .key, count: (.value.functions | length)})')
+
+# Find test modules
+query_jq('.modules | to_entries | map(select(.value.file | test("test")))')
+
+# Find functions by arity
+query_jq('[.modules[].functions[] | select(.arity == 2)]')
+
+# Get index metadata
+query_jq('.metadata')
+
+# Preview with sample mode
+query_jq('.modules | to_entries', sample=True)
+```
+
+#### Safety Limits
+
+- Maximum query length: 10,000 characters
+- Maximum nesting depth: 50 levels
+- Result truncation: 1MB
+- Early size warnings for large results (>500KB)
+
+---
+
+### git_history
+
+**Unified tool for all git history queries.**
+
+See [GIT_HISTORY.md](../GIT_HISTORY.md) for comprehensive documentation on git history and PR indexing features.
+
+---
+
+## Suggested Workflow
+
+1. **Start with `query`** - Find relevant code by keywords or patterns
+2. **Follow suggestions** - Query results include next-step recommendations
+3. **Use `expand_result`** - Drill into specific results
+4. **Deep-dive with specialized tools**:
+   - `search_module` for module API and dependencies
+   - `search_function` for call sites and usage
+   - `git_history` for authorship and PR attribution
+5. **Use `refresh_index`** if results seem stale
+
+---
+
+## Output Modes
+
+All tools support two output modes:
+
+| Mode | Description | Use Case |
+|------|-------------|----------|
+| Compact (default) | Essential info only, minimal tokens | Normal queries |
+| Verbose | Full docs, specs, examples | Deep analysis |
+
+Enable verbose mode with `verbose=true` on any tool.
+
+---
+
+## File Reference
+
+### Core MCP Infrastructure
+
+| File | Description |
+|------|-------------|
+| `cicada/mcp/server.py` | MCP server implementation with tool definitions |
+| `cicada/mcp/router.py` | Routes tool calls to appropriate handlers |
+| `cicada/mcp/tools.py` | Tool schema definitions |
+| `cicada/mcp/entry.py` | CLI entry point for MCP server |
+
+### Tool Handlers
+
+| File | Description |
+|------|-------------|
+| `cicada/mcp/handlers/module_handlers.py` | Module search and usage analysis |
+| `cicada/mcp/handlers/function_handlers.py` | Function search and call sites |
+| `cicada/mcp/handlers/git_handlers.py` | Git history queries |
+| `cicada/mcp/handlers/pr_handlers.py` | PR lookup and enrichment |
+| `cicada/mcp/handlers/analysis_handlers.py` | Query orchestration and jq |
+| `cicada/mcp/handlers/index_manager.py` | Index lifecycle management |
+
+### Query Infrastructure
+
+| File | Description |
+|------|-------------|
+| `cicada/query/orchestrator.py` | Query execution and result ranking |
+| `cicada/query/types.py` | Query domain types and options |
+| `cicada/mcp/fallbacks.py` | Zero-result recovery strategies |
+| `cicada/mcp/filter_utils.py` | Result filtering utilities |
+| `cicada/mcp/pattern_utils.py` | Pattern parsing and matching |
```
</diff>

<diff file="codebook/README.md">
```diff
diff --git a/codebook/README.md b/codebook/README.md
index ded22ca..5900edd 100644
--- a/codebook/README.md
+++ b/codebook/README.md
@@ -19,6 +19,16 @@
 14. Visual Basic Support - SCIP-based indexing for .NET projects
 15. Dart Support - SCIP-based indexing
 
+## MCP Tools
+1. [MCP Tools Reference](../MCP_TOOLS.md) - Comprehensive guide to all MCP tools
+2. query - Smart code discovery with keyword/pattern auto-detection
+3. search_module - View complete module API with dependency analysis
+4. search_function - Find function definitions and all call sites
+5. git_history - Unified tool for all git history queries
+6. expand_result - Drill down into query results for complete details
+7. refresh_index - Force refresh the index to pick up recent changes
+8. query_jq - Execute custom jq queries against the index
+
 ## Code Indexing
 1. [AST-Level Indexing](../AST_INDEXING.md) - Extracts module, function, and class definitions with signatures and specs
 2. [Incremental Indexing](../INCREMENTAL_INDEXING.md) - Only reindexes changed files for fast updates (includes Watch Mode)
@@ -78,15 +88,6 @@
 8. Run Command - Execute MCP tools directly from command line
 9. Serve Command - Start REST API server for HTTP access to tools
 
-## MCP Tools
-1. query - Smart code discovery with keyword/pattern auto-detection
-2. search_module - View complete module API with dependency analysis
-3. search_function - Find function definitions and all call sites
-4. git_history - Unified tool for all git history queries
-5. expand_result - Drill down into query results for complete details
-6. refresh_index - Force refresh the index to pick up recent changes
-7. query_jq - Execute custom jq queries against the index
-
 ## Output & Token Optimization
 1. Compact Output - Token-efficient responses with essential info only
 2. Verbose Mode - Enable full documentation, specs, and examples
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
Create comprehensive documentation for the MCP Tools feature in Cicada. The documentation should cover:
- All 7 MCP tools: query, search_module, search_function, git_history, expand_result, refresh_index, query_jq
- Architecture showing how CicadaServer routes to ToolRouter and handlers
- Detailed parameter reference for each tool
- Usage examples and suggested workflows
- Index schema documentation for query_jq

--- NOTES ---
The MCP Tools system consists of:

1. **CicadaServer** (cicada/mcp/server.py): MCP server implementation that exposes tools to AI clients
2. **ToolRouter** (cicada/mcp/router.py): Routes tool calls to appropriate handlers with argument validation
3. **Tool Definitions** (cicada/mcp/tools.py): Schema definitions for all 7 tools

The handlers are organized by functionality:
- **ModuleSearchHandler**: search_module tool
- **FunctionSearchHandler**: search_function tool
- **GitHistoryHandler**: git_history tool
- **PRHistoryHandler**: PR enrichment for git_history
- **AnalysisHandler**: query and query_jq tools
- **IndexManager**: Index loading, caching, and refresh

Tools are categorized as:
- Discovery: query (primary entry point), expand_result (drill-down)
- Analysis: search_module, search_function (deep-dive tools)
- Utility: git_history (documented in GIT_HISTORY.md), refresh_index, query_jq

--- SOLUTION ---
Created MCP_TOOLS.md documentation file with:

1. **Overview section** explaining MCP and categorizing the 7 tools into Discovery, Analysis, and Utility groups

2. **Architecture diagram** showing the flow from MCP Client through CicadaServer, ToolRouter, to individual handlers and IndexManager

3. **Key Components table** listing all 10 main modules with file locations

4. **Detailed Tool Reference** for each tool:
   - query: Smart auto-detection, parameters table, output features, examples
   - search_module: Parameters, dependency analysis (what_calls_it, what_it_calls), examples
   - search_function: Parameters, pattern syntax table, changed_since formats, examples
   - expand_result: Auto-detection logic, parameters, examples
   - refresh_index: Refresh modes comparison, examples
   - query_jq: Index schema documentation, schema discovery, common queries, safety limits
   - git_history: Reference to GIT_HISTORY.md

5. **Suggested Workflow** section guiding users through the typical discovery flow

6. **Output Modes** section explaining compact vs verbose output

7. **File Reference tables** for Core MCP Infrastructure, Tool Handlers, and Query Infrastructure

Updated README.md to add link to MCP_TOOLS.md in the MCP Tools section.

Files reviewed (14 total):
- Core: server.py, router.py, tools.py
- Handlers: module_handlers.py, function_handlers.py, git_handlers.py, pr_handlers.py, analysis_handlers.py, index_manager.py
- Query: orchestrator.py, types.py
- Utils: fallbacks.py, filter_utils.py, pattern_utils.py
