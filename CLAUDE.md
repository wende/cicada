# CICADA - AI Assistant Guidelines

This file contains project-specific instructions for AI assistants working on the CICADA codebase.

## Quick Reference

- **Language Support:** Elixir, Python, Erlang (Beta), TypeScript (planned)
- **Primary Installation:** `uv tool install cicada-mcp`
- **Storage Directory:** `~/.cicada/projects/<repo_hash>/` (use `cicada dir` to find it)
- **Testing:** Always use `make test` (never use `pytest` directly)
- **Development:** Always use `uv` commands, run `make dev` after code changes

## Critical Rules

### Code Style & Testing
- Use `black` for Python code formatting
- Include type hints where appropriate
- Write tests for new features
- **ALWAYS use `make test` for running tests** - Never use `pytest` or `uv run pytest` directly
- Always use `uv` to run any python commands
- Don't use --no-verify unless explicitly asked
- There is no such thing as unrelated tests. They need to pass before commit
- Tags and publishing is automated via CI/CD

### PR Review Workflow
When asked to review, address, or analyze PR comments, **ALWAYS use `make pr-comments` first**.

**CRITICAL RULE: When addressing PR feedback, you MUST include "addressed" in your commit message.**

```bash
# ✓ Good commit messages
git commit -m "Add gh CLI dependency check (addressed PR feedback)"
git commit -m "Addressed: Fix jq safe iteration"

# ❌ Bad - comment will still show up
git commit -m "Add gh CLI dependency check"
```

### Cicada Tool Usage

**ALWAYS use cicada-mcp tools for Elixir, Python, and Erlang code searches. NEVER use Grep/Find for these tasks.**

#### Use cicada tools for:
- **PRIMARY TOOL:** `mcp__cicada__query` - Start here for ALL code exploration and discovery
- **DEEP-DIVE:** `mcp__cicada__search_module` - View a module's complete API and dependencies
- **DEEP-DIVE:** `mcp__cicada__search_function` - Find function definitions and call sites
- **UNIFIED HISTORY:** `mcp__cicada__git_history` - One tool for all git history queries
- **DRILL-DOWN:** `mcp__cicada__expand_result` - Expand a query result to see complete details
- **ADVANCED:** `mcp__cicada__query_jq` - Execute jq queries against the Cicada index

#### DO NOT use Grep for:
- ❌ Searching for module structure
- ❌ Searching for function definitions
- ❌ Searching for module imports/usage

#### You can still use Grep for:
- ✓ Non-code files (markdown, JSON, config)
- ✓ String literal searches
- ✓ Pattern matching in single line comments

## Detailed Documentation

For detailed information on specific topics, see:

- **[Release Process](agents/release-process.md)** - Version management, tagging, PyPI publishing
- **[Storage & Config](agents/storage-and-config.md)** - Storage structure, environment variables, MCP config
- **[Indexing Features](agents/indexing-features.md)** - String indexing, co-occurrence, co-change analysis
- **[Git History](agents/git-history.md)** - Unified git_history tool usage and parameters
- **[Search Syntax](agents/search-syntax.md)** - Query types, patterns, wildcards, filters
- **[Python Support](agents/python-support.md)** - Class display, import detection configuration

<cicada>
  **ALWAYS use cicada-mcp tools for Elixir and Python code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - YOUR PRIMARY TOOL - Start here for ALL code exploration and discovery. `mcp__cicada__query`
  - DEEP-DIVE TOOL: View a module's complete API and dependencies after discovering it with query. `mcp__cicada__search_module`
  - DEEP-DIVE TOOL: Find function definitions and call sites after discovering with query. `mcp__cicada__search_function`
  - UNIFIED HISTORY TOOL: One tool for all git history queries - replaces get_blame, get_commit_history, find_pr_for_line, and get_file_pr_history. `mcp__cicada__git_history`
  - DRILL-DOWN TOOL: Expand a query result to see complete details. `mcp__cicada__expand_result`
  - Force refresh the code index to pick up recent file changes. `mcp__cicada__refresh_index`
  - ADVANCED: Execute jq queries directly against the Cicada index for custom analysis and data exploration. `mcp__cicada__query_jq`

  ### DO NOT use Grep for:
  - ❌ Searching for module structure
  - ❌ Searching for function definitions
  - ❌ Searching for module imports/usage

  ### You can still use Grep for:
  - ✓ Non-code files (markdown, JSON, config)
  - ✓ String literal searches
  - ✓ Pattern matching in single line comments
</cicada>


- after successful commit always push
