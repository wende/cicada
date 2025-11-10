<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="360"/>

# CICADA

### **C**ode **I**ntelligence: **C**ontextual **A**nalysis, **D**iscovery, and **A**ttribution

**Give your AI assistant structured access to your Elixir codebase.**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

[Quick Install](#quick-install) · [Security](#privacy--security) · [Developers](#for-developers) · [AI Assistants](#for-ai-assistants) · [Docs](#documentation)

</div>

---

## What's New in 0.3

- **Dependency analysis tools** - New `get_module_dependencies` and `get_function_dependencies` with transitive depth support
- **Expanded editor support** - Added Gemini CLI and Codex (now 5 editors supported)
- **Watch mode** - Automatic reindexing with `cicada watch` or `--watch` flag
- **Better discoverability** - Smart error suggestions, inline PR context, staleness warnings
- **Wildcard & OR patterns** - Search with `MyApp.*`, `create*|update*` across modules and functions
- **Breaking:** Removed `CICADA_REPO_PATH` environment variable

---

## Why CICADA?

Traditional AI assistants treat your repo like a pile of text. That leads to:

- **Token waste:** blind grep dumps that burn 3k+ tokens per question.
- **Hallucinated edits:** aliases/imports hide call sites, so refactors miss real usages.
- **No historical context:** design intent and PR trade-offs never make it into the prompt.

CICADA is an MCP server that gives assistants AST-level knowledge:

- Module + function definitions with signatures, specs, docs, owning files.
- Complete call-site tracking (aliases, imports, dynamic references).
- Semantic/keyword search so you can ask for "authentication" even if it's called `verify_credentials/2`.
- Git + PR attribution to surface *why* code exists.
- Dead-code detection and module dependency views for safe refactors.

**Result:** in our comparison, the same question dropped from **3,127 tokens / 52.8s** to **550 tokens / 35s** with correct answers.

---

## Quick Install

```bash
# 1. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install CICADA
uv tool install cicada-mcp

# 3. Index your Elixir project
cd /path/to/project
cicada claude   # or: cicada cursor, cicada vs, cicada gemini, cicada codex

# 4. Restart your editor
```

<div align="left">
<details>
<summary><strong>Try before installing permanently</strong></summary>

```bash
uvx --from cicada-mcp cicada claude   # or cursor, vs
```

Runs CICADA on demand (slower after the first run, but zero install).

</details>
</div>

**Available commands after installation:**
- `cicada [claude|cursor|vs|gemini|codex]` - One-command setup per project
- `cicada-mcp` - MCP server (auto-started by editor)
- `cicada watch` - Watch for file changes and automatically reindex
- `cicada index` - Re-index code with custom options (`-f/--force` + --fast/--regular/--max, --watch)
- `cicada index-pr` - Index pull requests for PR attribution
- `cicada find-dead-code` - Find potentially unused functions

Ask your assistant:
```
"Show me the functions in MyApp.User"
"Where is authenticate/2 called?"
"Find code related to API authentication"
```

---

## Privacy & Security

- **100% local:** parsing + indexing happen on your machine; no cloud uploads.
- **No telemetry:** CICADA doesn't collect usage or phone home.
- **Read-only tools:** MCP endpoints only read the index; they can't change your repo.
- **Optional GitHub access:** PR features rely on `gh` and your existing OAuth token.
- **Data layout:**
  ```
  ~/.cicada/projects/<repo_hash>/
  ├─ index.json      # modules, functions, call sites, metadata
  ├─ config.yaml     # indexing options + keyword tier
  ├─ hashes.json     # incremental indexing cache
  └─ pr_index.json   # optional PR metadata + reviews
  ```
  Your repo only gains an editor config (`.mcp.json`, `.cursor/mcp.json`, or `.vscode/settings.json`).

---

## For Developers

> Wire CICADA into your editor once, and every assistant session inherits the context.

### Install & Configure

```bash
cd /path/to/project
cicada claude   # or cicada cursor / cicada vs / cicada gemini / cicada codex
```

This command:
1. Parses every `.ex`/`.exs` file with tree-sitter.
2. Builds the index in `~/.cicada/projects/<hash>/`.
3. Creates the correct MCP config for your editor.
4. Configures `.gitattributes` so git can track functions through refactors.

### Re-indexing

- **Incremental update:** `cicada claude` (or cursor/vs) detects changed files only.
- **Force rebuild:** `rm ~/.cicada/projects/<hash>/hashes.json && cicada index .`
- **Switch keyword tier:** `cicada index --force --fast|--regular|--max .`


### Enable PR Attribution (optional)

```bash
brew install gh    # or apt install gh
gh auth login
cicada index-pr .     # incremental
cicada index-pr . --clean   # full rebuild
```

Unlocks questions like "Which PR introduced line 42?" or "What did reviewers say about `billing.ex`?"

### Automatic Re-indexing with Watch Mode

Enable automatic reindexing when files change by starting the MCP server with the `--watch` flag:

**For Claude Code (.mcp.json):**
```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-mcp",
      "args": ["--watch"],
      "env": {
        "CICADA_CONFIG_DIR": "/home/user/.cicada/projects/<hash>"
      }
    }
  }
}
```

**For Cursor (.cursor/mcp.json):**
```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-mcp",
      "args": ["--watch"]
    }
  }
}
```

**Or use with the server subcommand:**
```bash
cicada server --watch
cicada server --watch --fast    # Use fast tier for reindexing
cicada server --watch --max     # Use max tier for reindexing
```

When watch mode is enabled:
- A separate process monitors `.ex` and `.exs` files for changes
- Changes are automatically reindexed (incremental, fast)
- 2-second debounce prevents excessive reindexing during rapid edits
- The watch process stops automatically when the MCP server stops
- Excluded directories: `deps`, `_build`, `node_modules`, `.git`, `assets`, `priv`

### CLI Cheat Sheet

| Command | Purpose | Run When |
|---------|---------|---------|
| `cicada claude` | Configure MCP + incremental re-index | First setup, after local changes |
| `cicada watch` | Monitor files and auto-reindex on changes | During active development |
| `cicada index --force --regular .` | Full rebuild w/ semantic keywords | After large refactors or enabling AI tier |
| `cicada index-pr .` | Sync PR metadata/reviews | After new PRs merge |
| `cicada find-dead-code --min-confidence high` | List unused public functions | Cleanup sprints |

### Troubleshooting

<details>
<summary><b>"Index file not found"</b></summary>

Run the indexer first:
```bash
cicada index /path/to/project
```

Ensure indexing completed successfully. Check for `~/.cicada/projects/<hash>/index.json`.

</details>

<details>
<summary><b>"Module not found"</b></summary>

Use the exact module name as it appears in code (e.g., `MyApp.User`, not `User`).

If module was recently added, re-index:
```bash
cicada index .
```

</details>

<details>
<summary><b>MCP Server Won't Connect</b></summary>

**Troubleshooting checklist:**

1. **Verify configuration file exists:**
   ```bash
   # For Claude Code
   ls -la .mcp.json

   # For Cursor
   ls -la .cursor/mcp.json

   # For VS Code
   ls -la .vscode/settings.json
   ```

2. **Check paths are absolute:**
   ```bash
   cat .mcp.json
   # Should contain: /absolute/path/to/project
   # Not: ./project or ../project
   ```

3. **Ensure index exists:**
   ```bash
   ls -la ~/.cicada/projects/
   # Should show directory for your project
   ```

4. **Restart editor completely** (not just reload window)

5. **Check editor MCP logs:**
   - Claude Code: Console output
   - Cursor: Settings → MCP → View Logs
   - VS Code: Output panel → MCP

</details>

<details>
<summary><b>PR Features Not Working</b></summary>

**Setup GitHub CLI:**
```bash
# Install GitHub CLI
brew install gh  # macOS
sudo apt install gh  # Ubuntu
# or visit https://cli.github.com/

# Authenticate
gh auth login

# Index PRs
cicada index-pr .
```

**Common issues:**
- "No PR index found" → Run `cicada index-pr .`
- "Not a GitHub repository" → Ensure repo has GitHub remote
- Slow indexing → First-time indexing fetches all PRs; subsequent runs are incremental
- Rate limiting → GitHub API has rate limits; wait and retry if you hit limits

**Force rebuild:**
```bash
cicada index-pr . --clean
```

</details>

<details>
<summary><b>Keyword Search Not Working</b></summary>

**Error:** "Keyword search not available"

**Cause:** Index was built without keyword extraction.

**Solution:**
```bash
# Re-index with keyword extraction
cicada index --regular .  # or --fast or --max
```

**Verify:**
```bash
cat ~/.cicada/projects/<hash>/config.yaml
# Should show keyword_extraction: enabled
```

</details>

More detail: [docs/PR_INDEXING.md](docs/PR_INDEXING.md), [docs/08-INCREMENTAL_INDEXING.md](docs/08-INCREMENTAL_INDEXING.md).

---

## For AI Assistants

CICADA ships eleven focused MCP tools. Use the decision table to pick the right one:

### 🧭 Which Tool Should You Use?

| Need | Tool | Notes |
|------|------|-------|
| List a module's API | `search_module` | Supports wildcards (`*`) and OR (`|`) patterns. Includes public/private functions, signatures, specs, docs |
| Find where a function is defined & called | `search_function` | Supports wildcards (`*`) and OR (`|`) patterns. Resolves aliases/imports, shows code context |
| Discover who imports/aliases a module | `search_module_usage` | Great for dependency impact analysis |
| See what modules a module depends on | `get_module_dependencies` | Shows all modules used by a module (with transitive depth support) |
| See what functions a function calls | `get_function_dependencies` | Shows all functions called by a function (with transitive depth support) |
| Search by concept ("authentication", `*_user`) | `search_by_features` | Requires keyword tier index |
| Identify unused code | `find_dead_code` | Confidence-ranked (high, medium, low) |
| Find PR for a line | `find_pr_for_line` | Needs `cicada index-pr` + `gh` |
| View PR history for a file | `get_file_pr_history` | Shows descriptions + review comments |
| Track function/file evolution | `get_commit_history` | Follows refactors via `.gitattributes` |
| Show blame with grouped authorship | `get_blame` | Useful when you need owners |

**Want to see these tools in action?** Check out [Complete Workflow Examples](docs/WORKFLOW_EXAMPLES.md) with pro tips and real-world scenarios.

### Core Search Tools

**`search_module`** - Find modules and view all their functions
- Search by module name or file path with wildcards (`MyApp.*`, `*User*`) and OR patterns (`MyApp.User|MyApp.Post`)
- View function signatures with type specs
- Filter public/private functions
- Output in Markdown or JSON

**`search_function`** - Locate function definitions and track usage
- Search by function name, arity, or module path with wildcards (`create*`, `*_user`) and OR patterns (`create*|update*`)
- See where functions are called with line numbers
- View actual code usage examples
- Filter for test files only

**`search_module_usage`** - Track module dependencies
- Find all aliases and imports
- See all function calls to a module
- Understand module relationships
- Map dependencies across codebase

### Git History & Attribution Tools

**`find_pr_for_line`** - Identify which PR introduced any line of code
- Line-level PR attribution via git blame
- Author and commit information
- Direct links to GitHub PRs
- Requires: GitHub CLI + PR index

**`get_file_pr_history`** - View complete PR history for a file
- All PRs that modified the file
- PR descriptions and metadata
- Code review comments with line numbers
- Requires: GitHub CLI + PR index

**`get_commit_history`** - Track file and function evolution over time
- Complete commit history for files
- Function-level tracking (follows refactors)
- Creation and modification timeline
- Requires: `.gitattributes` configuration

**`get_blame`** - Show line-by-line code ownership
- Grouped authorship display
- Commit details for each author
- Code snippets with context

### Advanced Features

**`search_by_features`** (Beta) - Search code by concepts and features
- **🎯 Perfect for: "I don't know the exact name"** - Search by what code does, not what it's called
- Find code related to concepts like "authentication", "api key storage", "email validation"
- Wildcard pattern matching (`create*`, `*_user`, `validate_*`)
- Filter results by type: modules only, functions only, or all
- AI-powered keyword extraction from documentation
- Relevance scoring to surface the most relevant results
- Requires: Index built with keyword extraction (--fast, --regular, or --max)

**When to use:** You know what you're looking for conceptually but not the exact module/function names. Instead of guessing names with `search_function`, describe what the code does!

**`find_dead_code`** - Identify potentially unused functions
- Three confidence levels (high, medium, low)
- Smart detection of callbacks and behaviors
- Recognition of dynamic call patterns
- Module-level grouping with line numbers
- Excludes test files and `@impl` functions

Detailed parameters + output formats: [MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md).

### Token-Friendly Responses

All tools return structured Markdown/JSON snippets (signatures, call sites, PR metadata) instead of full files, keeping prompts lean.

---

## Learn by Doing (5–10 min each)

### 1. Safe Refactor Checklist
1. `search_function` → "Where is `create_user/2` called?"
2. `search_module_usage` → "Which modules alias `MyApp.User`?"
3. `search_function` with `test_only:true` to confirm test coverage.
4. `get_file_pr_history` → "Show PRs that modified `lib/my_app/user.ex`."

### 2. Untangle Legacy Intent
1. `search_module` to skim the API.
2. `get_file_pr_history` for design discussions/reviews.
3. `get_commit_history` on the hot function.
4. `get_blame` on confusing lines to ping the right author.

### 3. Cleanup Sprint
1. `find_dead_code --min-confidence high` for candidates.
2. For each, `search_function` to double-check dynamic usage.
3. `find_pr_for_line` to ensure it isn't waiting on an unfinished feature.
4. Remove or deprecate confidently.

For full walkthroughs see [docs/17-WORKFLOW_EXAMPLES.md](docs/17-WORKFLOW_EXAMPLES.md) and [docs/12-TOOL_DISCOVERABILITY_TASKS.md](docs/12-TOOL_DISCOVERABILITY_TASKS.md).

---

## Documentation

- [CHANGELOG.md](CHANGELOG.md) – release notes.
- [docs/01-KEYWORD_EXTRACTION_ANALYSIS.md](docs/01-KEYWORD_EXTRACTION_ANALYSIS.md) – semantic search internals.
- [docs/09-PR_INDEXING.md](docs/09-PR_INDEXING.md) – GitHub integration details.
- [docs/16-MCP_TOOL_CALL_BENCHMARKING.md](docs/16-MCP_TOOL_CALL_BENCHMARKING.md) – token/time benchmarks.

---

## Roadmap

| Available | Coming Soon |
|-----------|-------------|
| Elixir indexing + AST search | Python + TypeScript support |
| Semantic keyword tiers (`--fast/regular/max`) | Shared/team indexes |
| PR attribution + review scraping | Native IDE plugins (no MCP bridge) |
| Dead-code + dependency analysis | Optional remote index storage |

---

## Contributing

```bash
git clone https://github.com/wende/cicada.git
cd cicada
uv sync
pytest
```

Before submitting a PR:
- Run `black cicada tests`
- Ensure tests + coverage pass (`pytest --cov=cicada --cov-report=term-missing`)
- Update docs if behaviour changes

We welcome issues/PRs for:
- New language grammars
- Tool output improvements
- Better onboarding docs and tutorials

---

## License

MIT – see [LICENSE](LICENSE).

<div align="center">

**Stop letting your AI search blindly. Give it CICADA.**

[Get Started](#quick-install) · [Report Issues](https://github.com/wende/cicada/issues)

</div>
