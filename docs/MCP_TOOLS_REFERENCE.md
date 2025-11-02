# MCP Tools Reference

Complete documentation of CICADA's Model Context Protocol tools for code intelligence and analysis.

## Overview

CICADA provides 9 specialized MCP tools for deep code analysis and search capabilities across Elixir projects.

---

## Tools

### 1. search_module

**Purpose:** Search for a module by exact name and retrieve all its functions.

**What it does:**
- Locates an Elixir module by its full name or file path
- Displays all functions within that module
- Shows function signatures and documentation
- Distinguishes between public and private functions

**Key Features:**
- Exact module name matching
- Function signature display
- Support for both public and private functions with filtering options
- Available in Markdown and JSON formats

---

### 2. search_function

**Purpose:** Find function definitions and see where they're called across the codebase.

**What it does:**
- Searches for specific functions by name, arity, or full module path
- Identifies all call sites where the function is used
- Shows the calling context with line numbers
- Provides actual code usage examples

**Key Features:**
- Multiple search query formats (name only, with arity, with module)
- Call site tracking with line numbers
- Usage example extraction with code snippets
- Test file filtering capability
- Markdown and JSON output formats

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

### 4. find_pr_for_line

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

### 5. get_file_pr_history

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

### 6. get_commit_history

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

### 7. get_blame

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

### 8. search_by_keywords

**Purpose:** Search for modules and functions by semantic keywords extracted from documentation (EXPERIMENTAL).

**What it does:**
- Searches code by concepts rather than exact names
- Extracts keywords from module and function documentation
- Supports wildcard pattern matching
- Performs semantic matching across codebase
- Optionally filters results to show only modules or only functions

**Key Features:**
- Keyword-based semantic search
- Wildcard pattern support (`*` matching)
- Documentation-based indexing
- Match percentage scoring
- Concept-driven discovery
- Result type filtering (modules, functions, or all)
- Markdown output format

**Parameters:**
- `keywords` (required) - List of keywords to search for
- `filter_type` (optional) - Filter results: `'all'` (default), `'modules'`, or `'functions'`

**Requirements:** Index built with keyword extraction: `cicada index --fast`, `cicada index --regular`, or `cicada index --max`

**Best for:**
- Finding code by topic or concept
- Discovering functions related to domain terms
- Exploring when exact names are unknown
- Semantic pattern matching
- Filtering search results to specific code types

---

### 9. find_dead_code

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
| `search_module` | Module name or file path | Functions & signatures | Find module contents |
| `search_function` | Function name ± arity ± module | Definition & call sites | Understand function usage |
| `search_module_usage` | Module name | Imports & function calls | Track module dependencies |
| `find_pr_for_line` | File path & line number | PR info & author | Code attribution |
| `get_file_pr_history` | File path | PR list with reviews | File change history |
| `get_commit_history` | File path ± function | Commits & evolution | Track modifications |
| `get_blame` | File path & line range | Line-by-line authors | Code ownership |
| `search_by_keywords` | Keywords ± patterns ± filter | Modules/functions | Semantic discovery |
| `find_dead_code` | Index path (CLI) | Unused functions report | Code cleanup |
