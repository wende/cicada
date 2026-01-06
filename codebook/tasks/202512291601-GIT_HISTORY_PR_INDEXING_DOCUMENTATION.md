---
reviewed:
- cicada/git/helper.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/git/history_analyzer.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/git/formatter.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/mcp/handlers/git_handlers.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/github/pr_indexer/indexer.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/github/pr_indexer/github_api_client.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/github/pr_indexer/pr_index_builder.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/github/pr_indexer/line_mapper.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/mcp/handlers/pr_handlers.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/query/orchestrator.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/query/types.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/mcp/handlers/function_handlers.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
- cicada/parsing/base_indexer.py:a02f6d3eff020b38ddc11746440ff5302f2beca9
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# Git History & PR Indexing Documentation

<diff file="codebook/GIT_HISTORY.md">
```diff
diff --git a/codebook/GIT_HISTORY.md b/codebook/GIT_HISTORY.md
new file mode 100644
index 0000000..b814859
--- /dev/null
+++ b/codebook/GIT_HISTORY.md
@@ -0,0 +1,486 @@
+# Git History & PR Indexing
+
+Cicada provides comprehensive git history analysis and GitHub PR attribution, enabling you to understand the evolution of code, find who wrote specific lines, and access PR descriptions and review comments - all through a unified interface.
+
+## Overview
+
+The git history system combines three powerful capabilities:
+
+1. **Git History Analysis**: Uses git commands (`git blame`, `git log -L`) to track line authorship, function evolution, and commit history
+2. **PR Indexing**: Pre-indexes GitHub pull requests for instant offline lookup of PR metadata, descriptions, and review comments
+3. **Timestamp Enrichment**: Computes modification timestamps during code indexing, enabling recency-based filtering across all MCP tools
+
+These features are accessible through multiple MCP tools:
+- **`git_history`**: Direct git history queries (blame, function tracking, PR lookup)
+- **`query`**: Code search with `recent=true` filter for recently modified code
+- **`search_function`**: Function search with `changed_since` filter for time-based queries
+
+## Architecture
+
+### System Overview
+
+```
+┌─────────────────────────────────────────────────────────────────┐
+│                      git_history MCP Tool                        │
+│                    (Unified Entry Point)                         │
+└────────────────────────────┬────────────────────────────────────┘
+                             │
+                             ▼
+┌─────────────────────────────────────────────────────────────────┐
+│                      HistoryAnalyzer                             │
+│  • Smart routing based on parameters                             │
+│  • Combines git data with PR enrichment                          │
+│  • Handles all query types uniformly                             │
+└──────┬──────────────────────────────────┬───────────────────────┘
+       │                                  │
+       ▼                                  ▼
+┌──────────────────────┐       ┌──────────────────────────────────┐
+│     GitHelper        │       │        PR Index                   │
+│  • git blame         │       │  • commit → PR mapping            │
+│  • git log -L        │       │  • file → PRs mapping             │
+│  • Function tracking │       │  • PR descriptions                │
+│  • Evolution data    │       │  • Review comments                │
+└──────────────────────┘       └──────────────────────────────────┘
+                                          │
+                                          ▼
+                               ┌──────────────────────────────────┐
+                               │        PRIndexer                  │
+                               │  • GitHub API (GraphQL)           │
+                               │  • Incremental updates            │
+                               │  • Comment line mapping           │
+                               └──────────────────────────────────┘
+```
+
+### Key Components
+
+| Component | Location | Description |
+|-----------|----------|-------------|
+| `GitHistoryHandler` | `cicada/mcp/handlers/git_handlers.py` | MCP tool handler for git_history |
+| `HistoryAnalyzer` | `cicada/git/history_analyzer.py` | Unified analyzer that routes queries and combines data sources |
+| `GitHelper` | `cicada/git/helper.py` | Low-level git operations (blame, log, history) |
+| `GitFormatter` | `cicada/git/formatter.py` | Centralized formatter for git history output |
+| `PRIndexer` | `cicada/github/pr_indexer/indexer.py` | Orchestrates PR indexing from GitHub |
+| `GitHubAPIClient` | `cicada/github/pr_indexer/github_api_client.py` | GitHub API interactions (GraphQL + REST) |
+| `PRIndexBuilder` | `cicada/github/pr_indexer/pr_index_builder.py` | Builds and manages PR index structures |
+| `LineMapper` | `cicada/github/pr_indexer/line_mapper.py` | Maps comment lines from PR commits to current file state |
+| `PRHistoryHandler` | `cicada/mcp/handlers/pr_handlers.py` | Handler for PR-specific queries |
+| `QueryOrchestrator` | `cicada/query/orchestrator.py` | Query execution with recency filtering |
+| `FunctionSearchHandler` | `cicada/mcp/handlers/function_handlers.py` | Function search with `changed_since` filter |
+| `BaseIndexer` | `cicada/parsing/base_indexer.py` | Timestamp enrichment during indexing |
+
+---
+
+## Git History Analysis
+
+### Query Routing
+
+The `git_history` tool automatically selects the appropriate analysis method based on parameters:
+
+| Parameters | Method | Use Case |
+|------------|--------|----------|
+| `start_line` only | Single line blame | "Who wrote line 42?" |
+| `start_line` + `end_line` | Range blame | "Who wrote lines 40-60?" |
+| `function_name` | Function tracking | "How has this function changed?" |
+| File path only | File history | "What PRs modified this file?" |
+
+### Single Line Analysis
+
+Uses `git blame` to find the author of a specific line and automatically looks up the associated Pull Request.
+
+```python
+git_history(file_path="lib/auth.ex", start_line=42)
+```
+
+**Returns:**
+- Commit SHA and author
+- PR number, title, and URL (if indexed)
+- Commit message
+
+### Line Range Blame
+
+Groups consecutive lines by authorship with PR enrichment.
+
+```python
+git_history(file_path="lib/auth.ex", start_line=40, end_line=60)
+```
+
+**Returns:**
+- Grouped line ranges by author
+- Code snippets with author and commit details
+- PR attribution for each group
+
+### Function Evolution Tracking
+
+Uses `git log -L :funcname:file` for precise function tracking that follows the function even as it moves within the file.
+
+```python
+git_history(
+    file_path="lib/auth.ex",
+    function_name="validate_user",
+    show_evolution=True,
+    max_results=5
+)
+```
+
+**Returns:**
+- Commit history for the function
+- Evolution metadata (creation date, modification count, frequency)
+- Changes made in each commit
+
+### File-Level History
+
+Shows all PRs or commits that modified a file.
+
+```python
+git_history(file_path="lib/auth.ex")
+```
+
+**Smart Fallback Behavior:**
+1. Tries PR index first (fast, includes descriptions and comments)
+2. Falls back to git commits if no PR index
+
+---
+
+## PR Indexing
+
+### How It Works
+
+1. **Indexing Phase** (one-time or periodic):
+   - Fetches all PRs from GitHub via GraphQL (efficient batching)
+   - Stores commits, files changed, descriptions, and review comments
+   - Maps comment lines from PR commits to current file state
+   - Builds multiple indexes for fast lookup
+   - Saves to `~/.cicada/projects/<repo_hash>/pr_index.json`
+
+2. **Lookup Phase** (fast, offline):
+   - Runs `git blame` to find commit SHA (local, fast)
+   - Looks up commit in the index
+   - Returns PR info with description and comments instantly
+
+### Index Structure
+
+```json
+{
+  "metadata": {
+    "repo_owner": "owner",
+    "repo_name": "repo",
+    "last_indexed_at": "2025-01-15T10:30:00Z",
+    "total_prs": 150,
+    "total_commits_mapped": 500,
+    "total_comments": 320,
+    "total_files": 85,
+    "last_pr_number": 150
+  },
+  "prs": {
+    "42": {
+      "number": 42,
+      "title": "Add user authentication",
+      "url": "https://github.com/owner/repo/pull/42",
+      "state": "closed",
+      "merged": true,
+      "author": "developer",
+      "description": "This PR adds JWT-based authentication...",
+      "commits": ["c1f9203...", "abc123..."],
+      "files_changed": ["lib/auth.ex", "lib/user.ex"],
+      "comments": [
+        {
+          "id": "comment_123",
+          "author": "reviewer",
+          "body": "Consider caching token validation",
+          "created_at": "2025-01-10T10:30:00Z",
+          "path": "lib/auth.ex",
+          "line": 58,
+          "original_line": 52,
+          "resolved": true,
+          "commit_sha": "c1f9203..."
+        }
+      ]
+    }
+  },
+  "commit_to_pr": {
+    "c1f9203cb832...": 42
+  },
+  "file_to_prs": {
+    "lib/auth.ex": [42, 38, 25],
+    "lib/user.ex": [42, 40]
+  }
+}
+```
+
+### Indexing Commands
+
+```bash
+# Index PRs (incremental by default)
+cicada index-pr
+
+# Force clean rebuild
+cicada index-pr --clean
+```
+
+### Incremental Updates
+
+The indexer uses bidirectional incremental updates:
+
+1. **Newer PRs**: Fetches PRs with numbers above the current max
+2. **Older PRs**: Fetches PRs with numbers below the current min (catches missed PRs)
+
+This ensures the index stays complete even if PRs were created out of order or previous indexing was interrupted.
+
+---
+
+## Integration with Other MCP Tools
+
+Git history data is not only accessible through the `git_history` tool - it also powers recency filtering across other MCP tools.
+
+### Timestamp Enrichment Pipeline
+
+During code indexing, Cicada runs a timestamp enrichment phase that computes git history metadata for every function:
+
+```
+BaseIndexer._run_enrichment_pipeline()
+    │
+    ├── _compute_timestamps()
+    │       │
+    │       ├── GitHelper.get_functions_evolution_batch()
+    │       │       → Batch query git log for all functions in a file
+    │       │
+    │       └── Store per-function:
+    │           • created_at: When first introduced
+    │           • last_modified_at: Most recent modification
+    │           • last_modified_sha: Commit hash
+    │           • modification_count: Total changes
+    │           • modification_frequency: Change rate
+```
+
+These timestamps are stored in the code index (`index.json`) and enable recency-based filtering across all search tools.
+
+### query Tool - Recent Filter
+
+The `query` tool uses the `recent` parameter to filter results to recently modified code:
+
+```python
+# Find authentication code modified in last 14 days
+query(["authentication", "login"], recent=True)
+
+# Find all authentication code (no time filter)
+query(["authentication", "login"])
+```
+
+**How it works:**
+- Uses `last_modified_at` from the index
+- Default threshold: 14 days (`QueryConfig.RECENT_DAYS_THRESHOLD`)
+- Excludes results without timestamps from "recent" filter
+
+### search_function Tool - Changed Since Filter
+
+The `search_function` tool provides more granular time filtering with `changed_since`:
+
+```python
+# Functions changed in last 7 days
+search_function("create_user", changed_since="7d")
+
+# Functions changed in last 2 weeks
+search_function("*", changed_since="2w")
+
+# Functions changed since specific date
+search_function("validate*", changed_since="2024-12-01")
+
+# Functions changed since a git ref
+search_function("handle_*", changed_since="v1.0.0")
+```
+
+**Supported formats:**
+| Format | Example | Description |
+|--------|---------|-------------|
+| Relative days | `7d` | Last 7 days |
+| Relative weeks | `2w` | Last 2 weeks |
+| Relative months | `3m` | Last 3 months |
+| Relative years | `1y` | Last year |
+| ISO date | `2024-12-01` | Since specific date |
+| Git ref | `v1.0.0`, `HEAD~10` | Since git commit/tag |
+
+### Index Schema - Timestamp Fields
+
+Each function in the index includes these git-derived fields:
+
+```json
+{
+  "name": "create_user",
+  "arity": 2,
+  "line": 42,
+  "created_at": "2024-06-15T10:30:00Z",
+  "last_modified_at": "2025-01-10T14:22:00Z",
+  "last_modified_sha": "abc123def",
+  "modification_count": 12,
+  "modification_frequency": "monthly"
+}
+```
+
+---
+
+## Parameters Reference
+
+### git_history Tool
+
+```python
+git_history(
+    file_path: str,              # Required: Path to file (relative to repo root)
+    start_line: int | None,      # Line number or range start
+    end_line: int | None,        # Range end
+    function_name: str | None,   # Function name for tracking
+    show_evolution: bool,        # Include creation/modification metadata
+    max_results: int = 10,       # Maximum results to return
+    recent: bool | None,         # Time filter (see below)
+    recent_days: int = 14,       # Days for recent filter
+    author: str | None,          # Filter by author name (substring match)
+    include_pr_description: bool,# Include PR descriptions
+    include_review_comments: bool,# Include review comments
+    verbose: bool                # Enable all optional content
+)
+```
+
+### Time Filtering
+
+The `recent` parameter controls time-based filtering:
+
+| Value | Behavior |
+|-------|----------|
+| `True` | Last N days only (default: 14) |
+| `False` | Older than N days only |
+| `None` (omit) | All time (no filter) |
+
+### Author Filtering
+
+Filter results by author name (case-insensitive substring match):
+
+```python
+git_history(file_path="lib/auth.ex", author="john")
+```
+
+---
+
+## Comment Line Mapping
+
+Review comments are automatically mapped from their original PR line numbers to current file lines:
+
+- **Content-based matching**: Searches within ±20 lines for matching content
+- **Handles refactoring**: Tracks lines even if code moved slightly
+- **Marks unmappable**: Sets `line: null` if code was deleted or heavily modified
+- **Preserves original**: Always keeps `original_line` for reference
+
+This allows you to see where historical comments apply in the current codebase.
+
+---
+
+## Usage Examples
+
+### Find PR for a Specific Line
+
+```python
+# Who wrote this line and why?
+git_history(file_path="lib/my_app/user.ex", start_line=42)
+```
+
+### Track Function Changes
+
+```python
+# How has create_user evolved?
+git_history(
+    file_path="lib/my_app/user.ex",
+    function_name="create_user",
+    show_evolution=True,
+    max_results=10
+)
+```
+
+### Recent Changes by Author
+
+```python
+# What did John change recently?
+git_history(
+    file_path="lib/my_app/user.ex",
+    recent=True,
+    author="john"
+)
+```
+
+### Full PR History with Comments
+
+```python
+# Get all PRs with descriptions and review comments
+git_history(
+    file_path="lib/my_app/user.ex",
+    verbose=True
+)
+```
+
+---
+
+## Migration from Legacy Tools
+
+The unified `git_history` tool replaces several legacy tools:
+
+| Legacy Tool | New Equivalent |
+|------------|----------------|
+| `get_blame(file, start, end)` | `git_history(file, start_line=start, end_line=end)` |
+| `get_commit_history(file, func)` | `git_history(file, function_name=func)` |
+| `find_pr_for_line(file, line)` | `git_history(file, start_line=line)` |
+| `get_file_pr_history(file)` | `git_history(file)` |
+
+---
+
+## Performance
+
+### PR Indexing
+- GraphQL batching: ~50 PRs/minute (10 PRs per batch)
+- ~30x fewer API calls vs REST
+- Incremental updates only fetch new PRs
+
+### Lookup
+- ~0.1 seconds (git blame + index lookup, no network)
+
+### Index Size
+- Base: ~1KB per PR
+- With comments: ~2-5KB per PR
+- Typical 100-PR repo: ~200-500KB total
+
+---
+
+## Requirements
+
+- Git repository
+- GitHub CLI (`gh`) installed and authenticated (for PR indexing)
+- Python 3.7+
+
+---
+
+## File Reference
+
+### Git History Infrastructure
+
+| File | Description |
+|------|-------------|
+| `cicada/git/helper.py` | Low-level git operations (blame, log, history) |
+| `cicada/git/history_analyzer.py` | Unified analyzer for all git history queries |
+| `cicada/git/formatter.py` | Centralized formatter for git history output |
+| `cicada/mcp/handlers/git_handlers.py` | MCP tool handler for git_history |
+
+### PR Indexing Infrastructure
+
+| File | Description |
+|------|-------------|
+| `cicada/github/pr_indexer/indexer.py` | Main PR indexer orchestrator |
+| `cicada/github/pr_indexer/github_api_client.py` | GitHub API client (GraphQL + REST) |
+| `cicada/github/pr_indexer/pr_index_builder.py` | Builds and manages PR index structures |
+| `cicada/github/pr_indexer/line_mapper.py` | Maps comment lines to current file state |
+| `cicada/mcp/handlers/pr_handlers.py` | Handler for PR-specific queries |
+
+### Timestamp & Recency Integration
+
+| File | Description |
+|------|-------------|
+| `cicada/parsing/base_indexer.py` | Timestamp enrichment pipeline (`_compute_timestamps`) |
+| `cicada/query/orchestrator.py` | Query execution with `recent` filter |
+| `cicada/query/types.py` | `SearchResult` with `last_modified_at` fields |
+| `cicada/mcp/handlers/function_handlers.py` | Function search with `changed_since` filter |
+| `cicada/mcp/fallbacks.py` | `RecentFallback` for zero-result recovery |
```
</diff>

<diff file="codebook/README.md">
```diff
diff --git a/codebook/README.md b/codebook/README.md
index 8a35250..ded22ca 100644
--- a/codebook/README.md
+++ b/codebook/README.md
@@ -37,18 +37,20 @@
 1. [Code Analysis](../CODE_ANALYSIS.md) - Module and function analysis with dependency tracking and call site discovery
 
 ## Git History & Attribution
-1. Line Blame - Find who wrote a specific line and in which PR
-2. Range Blame - Group consecutive lines by authorship with PR enrichment
-3. Function Evolution - Track how a function has changed over time
-4. File PR History - View all PRs that modified a file
-5. Author Filtering - Filter history by author name
-6. Time Filtering - View recent, older, or all-time history
+1. [Git History & PR Indexing](../GIT_HISTORY.md) - Comprehensive guide to git history analysis and PR attribution
+2. Line Blame - Find who wrote a specific line and in which PR
+3. Range Blame - Group consecutive lines by authorship with PR enrichment
+4. Function Evolution - Track how a function has changed over time
+5. File PR History - View all PRs that modified a file
+6. Author Filtering - Filter history by author name
+7. Time Filtering - View recent, older, or all-time history
 
 ## PR Indexing
-1. PR Index - Index GitHub pull requests for offline lookup
-2. PR Descriptions - Access PR descriptions and commit messages
-3. Review Comments - Access PR review comments and discussions
-4. Incremental PR Updates - Only fetch new PRs since last index
+1. [Git History & PR Indexing](../GIT_HISTORY.md) - Unified documentation for PR indexing and git history
+2. PR Index - Index GitHub pull requests for offline lookup
+3. PR Descriptions - Access PR descriptions and commit messages
+4. Review Comments - Access PR review comments and discussions
+5. Incremental PR Updates - Only fetch new PRs since last index
 
 ## Co-Change Analysis
 1. Co-Change Detection - Identify files frequently modified together
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
Create comprehensive documentation for the Git History & PR Indexing features in Cicada. The documentation should cover:
- Git history analysis (line blame, range blame, function evolution tracking)
- GitHub PR indexing (offline lookup, descriptions, review comments)
- The unified `git_history` MCP tool that consolidates all these features
- Architecture and key components
- Usage examples and parameter reference
- Performance characteristics

--- NOTES ---
The Git History & PR Indexing feature combines two powerful capabilities:

1. **Git History Analysis**: Uses native git commands (`git blame`, `git log -L`) for precise code attribution
   - Single line blame to find who wrote a specific line
   - Range blame to group consecutive lines by authorship
   - Function tracking that follows functions as they move in files
   - Evolution metadata (creation date, modification count, frequency)

2. **PR Indexing**: Pre-indexes GitHub PRs using GraphQL for efficient batching
   - Commit-to-PR mapping for instant attribution
   - File-to-PRs mapping for file history
   - Comment line mapping from PR commits to current file state
   - Bidirectional incremental updates (newer and older PRs)

The features are unified through the `git_history` MCP tool in `GitHistoryHandler` which delegates to `HistoryAnalyzer` for smart query routing.

--- SOLUTION ---
Created GIT_HISTORY.md documentation file following the AST_INDEXING.md template with:

1. **Overview section** explaining the dual capabilities (git analysis + PR indexing)

2. **Architecture diagram** showing the data flow from git_history MCP tool through HistoryAnalyzer to GitHelper and PR Index

3. **Key Components table** listing all 9 main modules with file locations and descriptions:
   - GitHistoryHandler, HistoryAnalyzer, GitHelper, GitFormatter
   - PRIndexer, GitHubAPIClient, PRIndexBuilder, LineMapper, PRHistoryHandler

4. **Git History Analysis section** covering:
   - Query routing table (parameters → method → use case)
   - Single line analysis, range blame, function evolution tracking
   - File-level history with smart fallback behavior

5. **PR Indexing section** covering:
   - Two-phase workflow (indexing phase, lookup phase)
   - Complete index structure JSON example
   - CLI commands (cicada index-pr, --clean flag)
   - Bidirectional incremental updates explanation

6. **Parameters Reference** with full git_history tool signature and filtering options

7. **Comment Line Mapping** explanation of content-based matching

8. **Usage Examples** for common scenarios

9. **Migration table** from legacy tools to unified git_history

10. **Performance metrics** for indexing, lookup, and index size

11. **File Reference tables** for Git History, PR Indexing, and Timestamp Integration infrastructure

12. **Integration with Other MCP Tools section** (added after user feedback):
    - Timestamp Enrichment Pipeline: How `BaseIndexer._compute_timestamps()` populates function timestamps during indexing
    - query Tool - Recent Filter: How `recent=true` uses `last_modified_at` from the index
    - search_function Tool - Changed Since Filter: How `changed_since` supports relative times, ISO dates, and git refs
    - Index Schema showing timestamp fields stored per function

Updated README.md to add links to GIT_HISTORY.md in both "Git History & Attribution" and "PR Indexing" sections.

Additional files reviewed for timestamp/recency integration:
- `cicada/query/orchestrator.py`
- `cicada/query/types.py`
- `cicada/mcp/handlers/function_handlers.py`
- `cicada/parsing/base_indexer.py`
