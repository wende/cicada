# MCP Tools Reference

Complete documentation of CICADA's Model Context Protocol tools for code intelligence and analysis.

## Overview

CICADA provides 12 specialized MCP tools for deep code analysis and search capabilities across Elixir projects.

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

### 3. search_module_usage

**Purpose:** Find everywhere a module is used in the codebase.

**What it does:**
- Tracks all aliases and imports of a module
- Identifies all function calls to that module
- Shows which modules depend on the target module
- Provides comprehensive usage map

**Key Features:**
- Alias detection and tracking
- Import tracking
- Function call aggregation by calling module
- Line number references for each usage
- Markdown and JSON output formats

---

### 4. get_module_dependencies

**Purpose:** Discover which modules a given module depends on (the reverse of search_module_usage).

**What it does:**
- Shows all modules that a module depends on or uses
- Tracks both direct and transitive dependencies
- Complements `search_module_usage` by answering "what does X use?" instead of "what uses X?"
- Supports configurable depth for transitive dependency analysis

**Key Features:**
- Direct dependency tracking (depth=1)
- Transitive dependency analysis (depth>1)
- Displays the full dependency tree
- Shows line numbers where dependencies are referenced
- Helps understand module coupling and impact of changes
- Markdown and JSON output formats

**Parameters:**
- `module_name` (required) - Name of the module to analyze
- `depth` (optional) - How many levels of dependencies to include (default: 1)
  - `depth=1`: Direct dependencies only
  - `depth=2`: Dependencies and their dependencies
  - `depth=3+`: Full transitive closure up to specified depth

**Use Cases:**
- Understanding what external modules a module relies on
- Analyzing the impact of removing or modifying a dependency
- Identifying tightly coupled modules
- Refactoring planning to reduce dependencies

**Example:**
```
get_module_dependencies("MyApp.User", depth=2)
```
Shows all modules that MyApp.User depends on, plus their dependencies.

---

### 5. get_function_dependencies

**Purpose:** Discover which functions a given function calls (function-level dependency analysis).

**What it does:**
- Shows all functions that a specific function calls
- Tracks both direct and transitive function calls
- Works at the function level, complementing module-level dependency analysis
- Supports configurable depth for transitive call analysis

**Key Features:**
- Direct function call tracking (depth=1)
- Transitive call analysis (depth>1)
- Displays the full call tree
- Shows line numbers where function calls occur
- Helps understand function coupling and complexity
- Markdown and JSON output formats

**Parameters:**
- `function_query` (required) - Function to analyze (name, name/arity, or Module.name/arity)
- `depth` (optional) - How many levels of calls to include (default: 1)
  - `depth=1`: Direct calls only
  - `depth=2`: Calls and calls from those functions
  - `depth=3+`: Full transitive closure up to specified depth

**Use Cases:**
- Understanding the complexity and reach of a function
- Identifying circular dependencies between functions
- Analyzing the impact of modifying a function's behavior
- Refactoring to reduce coupling between functions

**Example:**
```
get_function_dependencies("create_user/2", depth=2)
```
Shows all functions that create_user/2 calls, plus functions those call.

---

### 6. find_pr_for_line

**Purpose:** Discover which pull request introduced a specific line of code.

**What it does:**
- Uses git blame to identify the commit that introduced a line
- Links commits to pull request numbers
- Shows author and date information
- Connects code to PR context

**Key Features:**
- Line-level PR attribution
- Commit SHA tracking
- Author information (name and email)
- Commit message reference
- PR URL generation
- Multiple output formats (text, JSON, Markdown)

**Requirements:** GitHub CLI (`gh`) with PR index

---

### 7. get_file_pr_history

**Purpose:** Get all pull requests that modified a specific file with descriptions and review comments.

**What it does:**
- Lists all PRs that touched a particular file
- Includes PR descriptions and metadata
- Shows historical code review comments
- Maps comments to specific line numbers

**Key Features:**
- Complete PR history for a file
- PR status and author information
- Description extraction
- Review comment tracking with line references
- Comment resolution status
- Markdown-formatted output

**Requirements:** GitHub CLI (`gh`) and PR index from `cicada index-pr`

---

### 8. get_commit_history

**Purpose:** Get commit history for a file or function with precise tracking.

**What it does:**
- Traces all commits that modified a file
- Can track a specific function even as it moves within the file
- Shows creation and modification history
- Displays evolution timeline

**Key Features:**
- File-level commit history
- Function-level tracking (tracks through refactors and moves)
- Creation date and modification statistics
- Commit author and message
- Fallback to line-range based tracking
- Configurable commit limit

**Requirements:** `.gitattributes` with `*.ex diff=elixir` configuration

---

### 9. get_blame

**Purpose:** Show line-by-line authorship with grouped consecutive lines by same author.

**What it does:**
- Displays who authored each line of code
- Groups consecutive lines by author
- Shows commit details for each group
- Provides context for understanding code history

**Key Features:**
- Line-by-line author attribution
- Grouped display for readability
- Commit SHA and timestamp
- Author name and email
- Code snippet display
- Works on specified line ranges

---

### 10. query

**Purpose:** Smart code discovery - your starting point for exploring code (🚀 NEW).

**What it does:**
- Intelligently searches by keywords OR patterns automatically
- Combines results from multiple search strategies
- Provides broad overview with snippets
- Suggests relevant deep-dive tools for next steps
- The "Google for code" - simple entry point for all code exploration

**Key Features:**
- **Smart Auto-Detection**: Automatically detects keywords vs patterns
  - Keywords: `["authentication", "login"]` → semantic search
  - Patterns: `"MyApp.User.create*"` → pattern matching
  - Mixed: `["oauth", "MyApp.Auth.*"]` → combines both
- **Power Filters**:
  - `scope`: "all" (default), "recent" (last 14 days), "public", "private"
  - `filter_type`: "all", "modules", "functions"
  - `match_source`: "all", "docs", "strings" (search in code strings like SQL)
  - `path_pattern`: glob patterns ("lib/auth/**", "**/*_controller.ex")
  - `include_tests`: true/false
- **Rich Results**: Snippets with docs, paths, scores, and match indicators
- **Smart Suggestions**: Context-aware next-step recommendations with actual tool calls
- **Match Indicators**: 📄 (docs), 💬 (strings), 🎯 (pattern)

**Parameters:**
- `query` (required) - String or list of strings (keywords OR patterns)
- `scope` (optional) - Filter scope: "all" | "recent" | "public" | "private" (default: "all")
- `filter_type` (optional) - Result type: "all" | "modules" | "functions" (default: "all")
- `match_source` (optional) - Search location: "all" | "docs" | "strings" (default: "all")
- `max_results` (optional) - Maximum results to show (default: 20)
- `path_pattern` (optional) - Glob pattern to filter by path
- `include_tests` (optional) - Include test files (default: true)

**Query Examples:**
```python
# Simple keyword search
query("authentication")

# Multiple keywords
query(["jwt", "token", "verify"])

# Pattern search
query("MyApp.Auth.verify*")

# Mixed keywords and patterns
query(["authentication", "MyApp.Auth.*"])

# With filters
query("login", scope="recent", path_pattern="lib/auth/**")

# Find SQL queries in code strings
query("SELECT users", match_source="strings")

# Find recent public functions
query("create*", scope="recent", filter_type="functions")
```

**Use Cases:**
- **Start here**: Use as entry point for ALL code exploration
- **Broad discovery**: Find relevant code quickly without knowing exact names
- **Guided exploration**: Follow suggestions to the right deep-dive tool
- **Recent changes**: scope="recent" to focus on new code
- **Public API**: scope="public" to explore exported functions
- **SQL/strings**: match_source="strings" to find queries and literals

**Example Workflow:**
```
1. query(["jwt", "authentication"])
   → Finds MyApp.Auth.verify_token/2, MyApp.Auth.login/2

2. Follow suggestion: search_function("verify_token", module_path="MyApp.Auth", include_usage_examples=true)
   → See detailed usage with code examples

3. Follow suggestion: search_module("MyApp.Auth")
   → View complete API surface
```

**Output Format:**
Returns markdown report with:
- Query summary with result count
- Snippet for each result (path, score, match %, doc, signature)
- Match indicators showing how it matched (docs/strings/pattern)
- Suggested next steps with actual tool invocations
- Visibility info for functions (Public/Private)

**Requirements:** Index built with keyword extraction for keyword search to work

**CLI Usage:**
```bash
# Keyword search
cicada query authentication

# Multiple keywords
cicada query jwt token verify

# Pattern search
cicada query "MyApp.Auth.verify*"

# With filters
cicada query authentication --scope recent
cicada query "create*" --filter-type functions
cicada query "SELECT" --match-source strings
cicada query login --path-pattern "lib/auth/**"
cicada query user --scope public --no-tests
cicada query auth --max-results 10

# Get help
cicada query --help
```

**Best for:**
- Starting point for ANY code exploration task
- Finding code by concept when names unknown
- Quick overviews before deep dives
- Discovering relevant code in unfamiliar codebases
- Filtering large codebases to specific areas
- Command-line exploration and scripting

---

### 11. search_by_keywords (Deprecated - use `query` instead)

**Purpose:** Search for modules and functions by semantic keywords extracted from documentation (EXPERIMENTAL).

**What it does:**
- Searches code by concepts rather than exact names
- Extracts keywords from module and function documentation
- Supports wildcard pattern matching and OR logic
- Performs semantic matching across codebase
- Optionally filters results to show only modules or only functions

**Key Features:**
- Keyword-based semantic search
- Wildcard pattern support (`*` matching)
- OR pattern support (`|` for matching multiple alternatives)
- Documentation-based indexing
- Match percentage scoring
- Concept-driven discovery
- Result type filtering (modules, functions, or all)
- Markdown output format

**Parameters:**
- `keywords` (required) - List of keywords to search for (supports wildcards and OR patterns)
- `filter_type` (optional) - Filter results: `'all'` (default), `'modules'`, or `'functions'`

**Pattern Examples:**
- `["user", "authentication"]` - Match both keywords
- `["create*"]` - Match keywords starting with "create"
- `["create*|update*"]` - Match keywords starting with "create" OR "update"
- `["*database*", "query"]` - Match keywords containing "database" and exact "query"

**Requirements:** Index built with keyword extraction: `cicada index --force --fast`, `cicada index --force --regular`, or `cicada index --force --max`

**Best for:**
- Finding code by topic or concept
- Discovering functions related to domain terms
- Exploring when exact names are unknown
- Semantic pattern matching with flexible patterns
- Filtering search results to specific code types

---

### 12. find_dead_code

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

**Best for:**
- Code cleanup and refactoring
- Reducing maintenance burden
- Understanding code usage patterns
- Identifying API surface reduction opportunities

---

## Output Formats

All tools support flexible output formats:
- **Markdown** - Human-readable formatted text (default)
- **JSON** - Structured data for programmatic use
- **Text** - Plain text (where applicable)

## Quick Reference Table

| Tool | Input | Output | Key Use Case |
|------|-------|--------|--------------|
| `query` 🚀 | Keywords/patterns ± filters | Snippets + suggestions | **START HERE** - Smart code discovery |
| `search_module` | Module name/pattern/file path | Functions & signatures | Find module contents (supports `*` and `\|`) |
| `search_function` | Function name/pattern ± arity ± module | Definition & call sites | Understand function usage (supports `*` and `\|`) |
| `search_module_usage` | Module name | Imports & function calls | Track module dependencies |
| `get_module_dependencies` | Module name ± depth | Dependency tree | Discover what modules a module uses |
| `get_function_dependencies` | Function query ± depth | Call tree | Discover what functions a function calls |
| `find_pr_for_line` | File path & line number | PR info & author | Code attribution |
| `get_file_pr_history` | File path | PR list with reviews | File change history |
| `get_commit_history` | File path ± function | Commits & evolution | Track modifications |
| `get_blame` | File path & line range | Line-by-line authors | Code ownership |
| `search_by_keywords` | Keywords ± patterns ± filter | Modules/functions | Semantic discovery (DEPRECATED - use `query`) |
| `find_dead_code` | Index path (CLI) | Unused functions report | Code cleanup |
