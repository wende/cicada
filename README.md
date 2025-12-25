<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="360"/>

# CICADA

### **C**ode **I**ntelligence: **C**ontextual **A**nalysis, **D**iscovery, and **A**ttribution

**Context compaction for AI code assistants** – Give your AI structured, token-efficient access to Elixir, Python, and Erlang codebases.

> [**Up to 50% less waiting · Up to 70% less tokens · Up to 99% less explanations to do**](https://cicada-mcp.vercel.app/#benchmark-section)
> **Tighter context = Better Quality**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

[![Elixir Support](https://img.shields.io/badge/Elixir-✓-blueviolet.svg)](https://elixir-lang.org/)
[![Python Support](https://img.shields.io/badge/Python-✓-blue.svg)](https://www.python.org/)
[![Erlang Support](https://img.shields.io/badge/Erlang-Beta-orange.svg)](https://www.erlang.org/)
[![TypeScript Support](https://img.shields.io/badge/TypeScript-Experimental-lightgrey.svg)](https://www.typescriptlang.org/)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

[Quick Install](#quick-install) · [Security](#privacy--security) · [Developers](#for-developers) · [AI Assistants](#for-ai-assistants) · [Docs](#documentation)

</div>

---

## Why CICADA?

**The core problem:** AI code assistants [waste context on blind searches](https://www.youtube.com/live/xmbSQz-PNMM?t=2402). Grep dumps entire files when you only need a function signature, leaving less room for actual reasoning.

### The Context Compaction Approach

Instead of raw text dumps, CICADA gives your AI **structured, pre-indexed knowledge**:

| Traditional Search | CICADA |
|-------------------|--------|
| Grep dumps entire files | Returns only signatures + call sites |
| Misses aliased imports | Tracks all reference types |
| No semantic understanding | Keyword search finds `verify_credentials` when you ask for "authentication" |


### What You Get

- **AST-level indexing** – Module/function/class definitions with signatures, specs, docs
- **Complete call-site tracking** – Aliases, imports, dynamic references across Elixir and Python
- **Semantic search** – Find code by concept, not just literal strings
- **Git + PR attribution** – Surface *why* code exists, not just what
- **Dead-code detection** – Safe refactors with dependency analysis
- **Automatic language detection** – Works seamlessly with both Elixir and Python

---

## Install

```bash
# 1. Install uv (if needed)
# curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install cicada-mcp

# In your repo 
cicada claude   # or: cicada cursor, cicada vs, cicada gemini, cicada codex, cicada opencode
```

<div align="left">
<summary><strong>Try before installing permanently</strong></summary>
Runs CICADA on demand (worse indexing quality, but zero install).

```bash
uvx cicada-mcp claude   # or cursor, vs
```
or

```
claude mcp add cicada uvx cicada-mcp
```   
```
gemini mcp add cicada uvx cicada-mcp
```  
```
codex mcp add cicada uvx cicada-mcp
```  


Uses your editor's built-in MCP management to install CICADA.

</details>
</div>

**Available commands after installation:**
- `cicada [claude|cursor|vs|gemini|codex|opencode]` - One-command interactive setup per project
- `cicada-mcp` - MCP server (auto-started by editor)
- `cicada status` - Show index status, PR index, link status, agent files, MCP configs
- `cicada stats [repo]` - Display usage statistics (tool calls, tokens, execution times)
- `cicada watch` - Watch for file changes and automatically reindex
- `cicada index` - Re-index code with custom options (`-f/--force` + --keywords/--embeddings, --watch)
- `cicada index-pr` - Index pull requests for PR attribution
- `cicada run [tool]` - Execute any of the 7 MCP tools directly from CLI
- `cicada agents install` - Install Claude Code agents to `./.claude/` directory
- `cicada link [parent_dir]` - Links current repository to an existing index
- `cicada clean` - Completely removes cicada integration from your folder as well as all settings

Ask your assistant:
```
# Elixir
"Show me the functions in MyApp.User"
"Where is authenticate/2 called?"

# Python
"Show me the AuthService class methods"
"Where is login() used in the codebase?"

# Both languages
"Find code related to API authentication"
```

---

## Privacy & Security

- **100% local:** parsing + indexing happen on your machine; no external access.
- **No telemetry:** CICADA doesn't collect usage or any telemetry.
- **Read-only tools:** MCP endpoints only read the index; they can't change your repo.
- **Optional GitHub access:** PR features rely on `gh` and your existing OAuth token.
- **Data layout:**
  ```
  ~/.cicada/projects/<repo_hash>/
  ├─ index.json      # modules, functions, call sites, metadata
  ├─ config.yaml     # indexing options + mode
  ├─ hashes.json     # incremental indexing cache
  └─ pr_index.json   # optional PR metadata + reviews
  ```
  Your repo only gains an editor config (`.mcp.json`, `.cursor/mcp.json`, `.vscode/settings.json`, `.gemini/settings.json`, `.codex/mcp.json`, or `.opencode.json`).

---

## For Developers

> Wire CICADA into your editor once, and every assistant session inherits the context.

### Install & Configure

```bash
cd /path/to/project
cicada claude   # or cicada cursor / cicada vs / cicada gemini / cicada codex / cicada opencode
```

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

** .mcp.json**
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
When watch mode is enabled:
- A separate process monitors `.ex`, `.exs` (Elixir) and `.py` (Python) files for changes
- Changes are automatically reindexed (incremental, fast)
- 2-second debounce prevents excessive reindexing during rapid edits
- The watch process stops automatically when the MCP server stops
- Excluded directories: `deps`, `_build`, `node_modules`, `.git`, `assets`, `priv`, `.venv`, `venv`

### CLI Cheat Sheet

**Note:** Language detection is automatic – CICADA detects Elixir (mix.exs) and Python (pyproject.toml) projects automatically.

| Command | Purpose | Run When |
|---------|---------|---------|
| `cicada claude` | Configure MCP + incremental re-index | First setup, after local changes |
| `cicada status` | Check index health, link status, agent files | After setup, troubleshooting |
| `cicada stats` | View usage statistics and token metrics | Monthly reviews, optimization |
| `cicada watch` | Monitor files and auto-reindex on changes | During active development |
| `cicada index --force --keywords .` | Full rebuild with keyword indexing | After large refactors or enabling keywords mode |
| `cicada index-pr .` | Sync PR metadata/reviews | After new PRs merge |

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
   - Claude Code: --debug
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
cicada index-pr
```

**Common issues:**
- "No PR index found" → Run `cicada index-pr .`
- "Not a GitHub repository" → Ensure repo has GitHub remote
- Slow indexing → First-time indexing fetches all PRs; subsequent runs are incremental
- Rate limiting → GitHub API has rate limits; wait and retry if you hit limits

**Force rebuild:**
```bash
cicada index-pr --clean
```

</details>

<details>
<summary><b>Keyword Search Not Working</b></summary>

**Error:** "Keyword search not available"

**Cause:** Index was built without keyword extraction.

**Solution:**
```bash
# Re-index with keyword extraction
cicada index .  # or --keywords
```

**Verify:**
```bash
cat ~/.cicada/projects/<hash>/config.yaml
# Should show:
# indexing:
#   mode: keywords
```

</details>

More detail: [docs/PR_INDEXING.md](docs/PR_INDEXING.md), [docs/08-INCREMENTAL_INDEXING.md](docs/08-INCREMENTAL_INDEXING.md).

<details>
<summary><b>Python Indexing</b></summary>

**Requirements:**
- Node.js (for scip-python indexer)
- Python project with pyproject.toml

**First-time setup:**
CICADA automatically installs scip-python via npm on first index. This may take a minute.

**Known limitations (Beta):**
- First indexing may be slower than Elixir (SCIP generation step)
- Large virtual environments (.venv) are automatically excluded
- Some dynamic Python patterns may not be captured

**Performance tips:**
```bash
# Ensure .venv is excluded
echo "/.venv/" >> .gitignore

# Use keywords mode for quickest indexing
cicada index --keywords .
```

**Report issues:** [GitHub Issues](https://github.com/wende/cicada/issues) with "Python" label

</details>

---

## For AI Assistants

CICADA ships 7 focused MCP tools designed for efficient code exploration across Elixir, Python, and Erlang codebases.

### 🧭 Which Tool Should You Use?

| Need | Tool | Notes |
|------|------|-------|
| **Start exploring** | `query` | **🚀 START HERE** - Smart discovery with keywords/patterns + filters (scope, recent, path) |
| View a module's complete API | `search_module` | Functions, signatures, specs, docs. Use `what_calls_it`/`what_it_calls` for bidirectional analysis |
| Find where a function is used | `search_function` | Definition + all call sites. Supports wildcards (`*`) and OR (`\|`) patterns |
| Track git history | `git_history` | Unified tool: blame, commits, PRs, function evolution (replaces 4 legacy tools) |
| Drill down into results | `expand_result` | Auto-expands modules or functions from query results |
| Advanced index queries | `query_jq` | Custom jq queries for power users |

**Want to see these tools in action?** Check out [Complete Workflow Examples](docs/WORKFLOW_EXAMPLES.md) with pro tips and real-world scenarios.

### Core Tools

**`query`** - Smart code discovery (your starting point)
- Automatically detects keywords vs patterns
- Filters: `scope` (public/private), `recent` (last 14 days), `filter_type` (modules/functions), `match_source` (docs/strings)
- Returns snippets with smart next-step suggestions
- Use `path_pattern` to filter by location

**`search_module`** - Deep module analysis
- View complete API: functions, signatures, specs, docs
- For Python: Shows classes with method counts and signatures
- For Elixir: Shows functions with arity notation
- Bidirectional analysis:
  - `what_calls_it=true` → See who uses this module (impact analysis)
  - `what_it_calls=true` → See what this module depends on
- Supports wildcards (Elixir: `MyApp.*`, Python: `api.handlers.*`) and OR patterns (`MyApp.User|MyApp.Post`)
- Filter by visibility (public/private/all)

**`search_function`** - Function usage tracking
- Find definitions and all call sites
- `what_calls_it=true` (default) → See all callers
- `what_it_calls=true` → See all dependencies
- Include code examples with `include_usage_examples=true`
- Filter by `usage_type`: source, tests, or all

### Git History (Unified Tool)

**`git_history`** - All git operations in one tool
- **Single line**: `git_history("file.ex", start_line=42)` → blame + PR
- **Line range**: `git_history("file.ex", start_line=40, end_line=60)` → grouped blame
- **Function tracking**: `git_history("file.ex", function_name="create_user")` → evolution
- **File history**: `git_history("file.ex")` → all PRs/commits
- Time filtering: `recent=true` (14d), `recent=false` (>14d), `recent=null` (all)
- Author filtering: `author="john"`
- Automatic PR index integration when available

### Additional Tools

**`expand_result`** - Drill down from query results
- Auto-detects module vs function
- Shows complete details with usage examples
- Configure what to include: code, dependencies, callers
- Convenient wrapper around search_module and search_function

**`query_jq`** - Advanced index queries
- Direct jq queries against the index
- Schema discovery with `| schema`
- Compact (default) or pretty output
- Sample mode for large results

Detailed parameters + output formats: [MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md).

### Token-Friendly Responses

All tools return structured Markdown/JSON snippets (signatures, call sites, PR metadata) instead of full files, keeping prompts lean.

**New in v0.5.1:** All tools now use compact output by default to minimize token usage. Use `verbose=true` for detailed output with full docs and specs.

---


---

## Documentation

- [docs/17-WORKFLOW_EXAMPLES.md](docs/17-WORKFLOW_EXAMPLES.md) 
- [docs/12-TOOL_DISCOVERABILITY_TASKS.md](docs/12-TOOL_DISCOVERABILITY_TASKS.md).
- [CHANGELOG.md](CHANGELOG.md) – release notes.
- [docs/01-KEYWORD_EXTRACTION_ANALYSIS.md](docs/01-KEYWORD_EXTRACTION_ANALYSIS.md) – semantic search internals.
- [docs/09-PR_INDEXING.md](docs/09-PR_INDEXING.md) – GitHub integration details.
- [docs/16-MCP_TOOL_CALL_BENCHMARKING.md](docs/16-MCP_TOOL_CALL_BENCHMARKING.md) – token/time benchmarks.

---

## Roadmap

### Current Status

- ✅ **Elixir**
- ✅ **Python**
- 🚧 **Erlang** - Beta
- 🧪 **TypeScript** - Experimental

### What's Next

- Stabilize Erlang support based on user feedback
- TypeScript/JavaScript support via SCIP
- Shared/team indexes for collaborative environments
- Performance optimizations for large codebases

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

**Stop wasting context on blind searches. Give your AI CICADA.**

[Get Started](#quick-install) · [Report Issues](https://github.com/wende/cicada/issues)

</div>
