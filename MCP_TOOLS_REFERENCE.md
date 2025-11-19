# MCP Tools Reference

Complete documentation of CICADA's Model Context Protocol tools for code intelligence and analysis.

## Overview

CICADA provides 7 specialized MCP tools for deep code analysis and search capabilities across Elixir projects.

---

## Tools

### 1. search_module

**Purpose:** Search for modules by name or pattern and retrieve all their functions.

**What it does:**
- Locates Elixir modules by exact name, file path, or pattern
- Supports wildcard patterns (*) and OR logic (|) for flexible searching
- Displays all functions within matched modules
- Shows function signatures and documentation
- Distinguishes between public and private functions

**Key Features:**
- Exact module name matching
- Wildcard pattern support (`MyApp.*`, `*User*`, `lib/my_app/*.ex`)
- OR pattern support (`MyApp.User|MyApp.Post`, `*User*|*Post*`)
- File path pattern matching
- Function signature display
- Support for both public and private functions with filtering options
- Available in Markdown and JSON formats

**Pattern Examples:**
- `MyApp.User` - Exact match for a single module
- `MyApp.*` - All modules starting with MyApp.
- `*User*` - All modules containing "User"
- `lib/my_app/*.ex` - All modules in that directory
- `MyApp.User|MyApp.Post` - Either module
- `*User*|*Post*` - Modules containing User OR Post

---

### 2. search_function

**Purpose:** Find function definitions and see where they're called across the codebase.

**What it does:**
- Searches for functions by name, pattern, arity, module path, or file path
- Supports wildcard patterns (*) and OR logic (|) for flexible searching
- Identifies all call sites where matched functions are used
- Shows the calling context with line numbers
- Provides actual code usage examples

**Key Features:**
- Multiple search query formats (name only, with arity, with module, with file path)
- Wildcard pattern support for function names, module names, and file paths
- OR pattern support for matching multiple alternatives
- Call site tracking with line numbers
- Usage example extraction with code snippets
- Test file filtering capability
- Markdown and JSON output formats

**Pattern Examples:**
- `create_user` - Exact match for function name
- `create*` - All functions starting with "create"
- `*user*` - All functions containing "user"
- `MyApp.User.create*` - Functions starting with "create" in MyApp.User module
- `create*|update*` - Functions starting with "create" OR "update"
- `MyApp.*.create/1` - Function create/1 in any module under MyApp
- `lib/*/user.ex:create*` - Functions starting with "create" in files matching path pattern

---

### 3. git_history

**Purpose:** Unified tool for all git history queries - replaces multiple legacy tools.

**What it does:**
- Smart routing based on parameters (single line, range, function, or file)
- Single line: Uses git blame + finds associated PR
- Line range: Shows grouped authorship with PR enrichment
- Function tracking: Follows function through refactors using `git log -L`
- File-level: Shows complete PR or commit history

**Key Features:**
- Automatic PR index integration when available
- Time filtering with `recent` parameter (true=14d, false=>14d, null=all)
- Author filtering for focused history
- Evolution metadata (creation date, modification frequency)
- Fallback to git commands when PR index unavailable

**Parameters:**
- `file_path` (required) - Path to file relative to repo root
- `start_line` (optional) - Line number or range start
- `end_line` (optional) - Range end (use with start_line)
- `function_name` (optional) - Function name for precise tracking
- `show_evolution` (optional) - Include metadata (default: false)
- `max_results` (optional) - Maximum commits/PRs (default: 10)
- `recent` (optional) - Time filter: true (14d), false (>14d), null (all)
- `author` (optional) - Filter by author name

**Examples:**
- `git_history("lib/auth.ex", start_line=42)` - Who wrote line 42 + PR
- `git_history("lib/auth.ex", start_line=40, end_line=60)` - Range blame
- `git_history("lib/auth.ex", function_name="validate_user")` - Function evolution
- `git_history("lib/auth.ex")` - Complete file history
- `git_history("lib/auth.ex", recent=true, author="john")` - Recent changes by John

---

### 4. find_dead_code

**Purpose:** Identify potentially unused public functions in your codebase.

**What it does:**
- Analyzes indexed codebase for unused public functions
- Categorizes findings by confidence level
- Detects potential callbacks and dynamic calls
- Groups results by module for easy review
- Excludes test files and functions with `@impl`

**Key Features:**
- Three confidence levels (high, medium, low)
- Smart detection of callbacks and behaviors
- Recognition of dynamic call patterns
- Module-level grouping
- Test file exclusion
- JSON and Markdown output formats

**Confidence Levels:**
- **High** - Zero usage, no behaviors, no dynamic indicators (likely dead code)
- **Medium** - Zero usage, but module has behaviors or uses (possible callbacks)
- **Low** - Zero usage, but module passed as value (possible dynamic calls)

**Parameters:**
- `min_confidence` (optional) - Minimum confidence: "high" | "medium" | "low" (default: "high")
- `format` (optional) - Output format: "markdown" | "json" (default: "markdown")

**Best for:**
- Code cleanup and refactoring
- Reducing maintenance burden
- Understanding code usage patterns
- Identifying API surface reduction opportunities

---

### 5. expand_result

**Purpose:** Drill-down convenience tool to expand query results.

**What it does:**
- Automatically detects whether expanding a module or function
- Shows complete details for discovered code
- Provides usage examples and relationships
- Convenient wrapper around search_module and search_function

**Key Features:**
- Auto-detection of result type
- Full code context display
- Configurable depth for dependencies
- Include/exclude code snippets
- Bidirectional analysis (what calls it / what it calls)

**Parameters:**
- `identifier` (required) - Module name or function reference
- `type` (optional) - "auto" | "module" | "function" (default: "auto")
- `include_code` (optional) - Show code snippets (default: true)
- `what_calls_it` (optional) - Show callers/usage (default: true)
- `what_it_calls` (optional) - Show dependencies (default: false)
- `dependency_depth` (optional) - Transitive depth (default: 1)
- `show_function_usage` (optional) - Per-function deps (default: false)
- `include_code_context` (optional) - Code snippets for deps (default: false)
- `format` (optional) - "markdown" | "json" (default: "markdown")

---

### 6. query_jq

**Purpose:** Execute jq queries directly against the Cicada index for custom analysis.

**What it does:**
- Provides direct access to raw index structure
- Supports full jq query syntax
- Custom analysis not covered by specialized tools
- Schema discovery with `| schema` operator

**Key Features:**
- Complete jq syntax support (filters, maps, selects, aggregations)
- Schema discovery mode
- Sample mode for previewing large datasets
- Result size warnings and truncation
- Compact or pretty output formatting

**Parameters:**
- `query` (required) - jq expression (e.g., ".modules | keys")
- `format` (optional) - "compact" | "pretty" (default: "compact")
  - **compact**: Single-line JSON, saves tokens
  - **pretty**: Pretty-printed, use only when explicitly requested
- `sample` (optional) - Auto-limit to 5 items (default: false)

**Index Structure:**
```
{
  "modules": {
    "<name>": {
      "file": "path",
      "line": 1,
      "functions": [...],
      "keywords": {...},
      "string_keywords": {...}
    }
  },
  "metadata": {...},
  "cooccurrences": {...}
}
```

**Quick Examples:**
- `.modules | keys` - List all modules
- `.modules[].functions | length` - Count functions per module
- `.modules | to_entries | map(select(.value.file | test("test")))` - Find test files
- `.metadata` - View index metadata

**Best for:**
- Custom analysis not covered by other tools
- Debugging index contents
- Exploring data structures
- Advanced filtering and aggregation

---

### 7. query

**Purpose:** Smart code discovery - your starting point for exploring the codebase.

**What it does:**
- Intelligent search using keywords or patterns to find relevant code
- Automatically detects whether you're searching by keywords or patterns
- Returns code snippets with context and smart suggestions for next steps
- Filters results by scope (public/private), recency, type (modules/functions), and path
- Supports both documentation and string literal matching

**Key Features:**
- Automatic keyword vs. pattern detection
- Multiple filtering dimensions:
  - **Scope filtering**: public, private, or all
  - **Recency filtering**: last 14 days or all time
  - **Type filtering**: modules only, functions only, or both
  - **Source filtering**: match in docs, strings, or both
  - **Path filtering**: include/exclude specific paths with patterns
- Smart suggestions when results are too many or too few
- Code snippets with highlighted matches
- Relevance scoring with confidence indicators

**Parameters:**
- `query` (required) - String or list of keywords/patterns to search for
- `scope` (optional) - Visibility filter: "all" (default), "public", "private"
- `recent` (optional) - Time filter: true (last 14d), false (all time, default)
- `filter_type` (optional) - Result type: "all" (default), "modules", "functions"
- `match_source` (optional) - Match in: "all" (default), "docs", "strings"
- `max_results` (optional) - Maximum results to return (default: 10)
- `path_pattern` (optional) - Filter by file path (e.g., "!**/test/**" excludes tests)
- `show_snippets` (optional) - Include code snippets in results (default: false)

**Query Format:**
```
# Keywords (semantic search)
"authentication user login"
["database", "query", "user"]

# Patterns (exact/wildcard matching)
"create_user"         # Exact match
"create*"             # Wildcard
"*user*"              # Contains
"create*|update*"     # OR logic
```

**Examples:**
- `query("authentication")` - Find all authentication-related code
- `query(["database", "user"], filter_type="functions")` - Find user database functions
- `query("recent", scope="public", recent=true)` - Recent public changes
- `query("SELECT", match_source="strings")` - Find SQL queries in string literals
- `query("api", path_pattern="!**/test/**")` - API code excluding tests
- `query("create*", scope="public", show_snippets=true)` - Create functions with code

**When to Use:**
- **Start here** when exploring unfamiliar code
- Finding code related to a feature or concept
- Discovering modules/functions by purpose rather than name
- Filtering large codebases by recency, visibility, or location
- Searching for specific strings like error messages or SQL queries

**Best for:**
- Initial code discovery and exploration
- Finding relevant entry points for a feature
- Narrowing down large codebases with multiple filters
- Discovering code patterns and usage examples

---

## Deprecated Tools

The following tools have been removed or consolidated in v0.4. All functionality is preserved through the updated tool set with cleaner, more intuitive parameters.

### Consolidated Tools

**Module and Function Dependencies:**
- **search_module_usage** → `search_module` with `what_calls_it=true`
- **get_module_dependencies** → `search_module` with `what_it_calls=true`
- **get_function_dependencies** → `search_function` with `what_it_calls=true`

**Git History (Unified):**
- **find_pr_for_line** → `git_history` with `start_line` parameter
- **get_file_pr_history** → `git_history` with just `file_path`
- **get_commit_history** → `git_history` with `function_name` or file-level
- **get_blame** → `git_history` with line range parameters

**Semantic Search:**
- **search_by_keywords** → `query` (renamed and enhanced with orthogonal filtering)

## Output Formats

All tools support flexible output formats:
- **Markdown** - Human-readable formatted text (default)
- **JSON** - Structured data for programmatic use
- **Text** - Plain text (where applicable)

## Quick Reference Table

| Tool | Input | Output | Key Use Case |
|------|-------|--------|--------------|
| `query` 🚀 | Keywords/patterns + filters | Snippets + suggestions | **START HERE** - Smart code discovery with scope/recent/path filters |
| `search_module` | Module name/pattern/file | Functions & signatures | View module API + dependencies (use `what_calls_it`/`what_it_calls`) |
| `search_function` | Function name/pattern | Definition & call sites | Find function usage + dependencies (supports `*` and `\|`) |
| `git_history` | File path + optional line/function | Git history (unified) | All git operations: blame, commits, PRs, function tracking |
| `find_dead_code` | Confidence level | Unused functions report | Identify potentially dead code for cleanup |
| `expand_result` | Module/function identifier | Complete details | Drill down from query results |
| `query_jq` | jq expression | JSON data | Advanced index queries and custom analysis |

**Note:** All deprecated tools (search_module_usage, get_*_dependencies, find_pr_for_line, get_file_pr_history, get_commit_history, get_blame, search_by_keywords) have been consolidated into the tools above. See the Deprecated Tools section for migration guidance.
