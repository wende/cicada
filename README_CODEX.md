<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="360"/>

# CICADA

**Give your AI assistant structured access to your Elixir codebase.**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

[Quick Install](#quick-install) · [Security](#privacy--security) · [Developers](#for-developers) · [AI Assistants](#for-ai-assistants) · [Docs](#documentation)

</div>

---

## Why CICADA?

Traditional AI assistants treat your repo like a pile of text. That leads to:

- **Token waste:** blind grep dumps that burn 3k+ tokens per question.
- **Hallucinated edits:** aliases/imports hide call sites, so refactors miss real usages.
- **No historical context:** design intent and PR trade-offs never make it into the prompt.

CICADA is an MCP server that gives assistants AST-level knowledge:

- Module + function definitions with signatures, specs, docs, owning files.
- Complete call-site tracking (aliases, imports, dynamic references).
- Semantic/keyword search so you can ask for "authentication" even if it’s called `verify_credentials/2`.
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
cicada claude   # or: cicada cursor, cicada vs

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

Ask your assistant:
```
"Show me the functions in MyApp.User"
"Where is authenticate/2 called?"
"Find code related to API authentication"
```

---

## Privacy & Security

- **100% local:** parsing + indexing happen on your machine; no cloud uploads.
- **No telemetry:** CICADA doesn’t collect usage or phone home.
- **Read-only tools:** MCP endpoints only read the index; they can’t change your repo.
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
cicada claude   # or cicada cursor / cicada vs
```

This command:
1. Parses every `.ex`/`.exs` file with tree-sitter.
2. Builds the index in `~/.cicada/projects/<hash>/`.
3. Creates the correct MCP config for your editor.
4. Configures `.gitattributes` so git can track functions through refactors.

### Re-indexing

- **Incremental update:** `cicada claude` (or cursor/vs) detects changed files only.
- **Force rebuild:** `rm ~/.cicada/projects/<hash>/hashes.json && cicada index .`
- **Switch keyword tier:** `cicada index --fast|--regular|--max .`

### Enable PR Attribution (optional)

```bash
brew install gh    # or apt install gh
gh auth login
cicada index-pr .     # incremental
cicada index-pr . --clean   # full rebuild
```

Unlocks questions like “Which PR introduced line 42?” or “What did reviewers say about `billing.ex`?”

### CLI Cheat Sheet

| Command | Purpose | Run When |
|---------|---------|---------|
| `cicada claude` | Configure MCP + incremental re-index | First setup, after local changes |
| `cicada index --regular .` | Full rebuild w/ semantic keywords | After large refactors or enabling AI tier |
| `cicada index-pr .` | Sync PR metadata/reviews | After new PRs merge |
| `cicada find-dead-code --min-confidence high` | List unused public functions | Cleanup sprints |

### Troubleshooting

- "Index file not found" → Run `cicada index .` and confirm `~/.cicada/projects/<hash>/index.json` exists.
- MCP not connecting → Ensure `.mcp.json` (Claude), `.cursor/mcp.json`, or `.vscode/settings.json` has absolute paths; restart the editor.
- Keyword search unavailable → Re-index with `--fast`, `--regular`, or `--max`.
- PR tools failing → Verify `gh auth status` and rerun `cicada index-pr .`.

More detail: [docs/PR_INDEXING.md](docs/PR_INDEXING.md), [docs/08-INCREMENTAL_INDEXING.md](docs/08-INCREMENTAL_INDEXING.md).

---

## For AI Assistants

CICADA ships nine focused MCP tools. Use the decision table to pick the right one:

| Need | Tool | Notes |
|------|------|-------|
| List a module’s API | `search_module` | Includes public/private functions, signatures, specs, docs |
| Find where a function is defined & called | `search_function` | Resolves aliases/imports, shows code context |
| Discover who imports/aliases a module | `search_module_usage` | Great for dependency impact analysis |
| Search by concept (“authentication”, `*_user`) | `search_by_features` | Requires keyword tier index |
| Identify unused code | `find_dead_code` | Confidence-ranked (high, medium, low) |
| Find PR for a line | `find_pr_for_line` | Needs `cicada index-pr` + `gh` |
| View PR history for a file | `get_file_pr_history` | Shows descriptions + review comments |
| Track function/file evolution | `get_commit_history` | Follows refactors via `.gitattributes` |
| Show blame with grouped authorship | `get_blame` | Useful when you need owners |

Detailed parameters + output formats: [docs/MCP_TOOLS_REFERENCE.md](docs/MCP_TOOLS_REFERENCE.md).

### Token-Friendly Responses

All tools return structured Markdown/JSON snippets (signatures, call sites, PR metadata) instead of full files, keeping prompts lean.

---

## Learn by Doing (5–10 min each)

### 1. Safe Refactor Checklist
1. `search_function` → “Where is `create_user/2` called?”
2. `search_module_usage` → “Which modules alias `MyApp.User`?”
3. `search_function` with `test_only:true` to confirm test coverage.
4. `get_file_pr_history` → “Show PRs that modified `lib/my_app/user.ex`.”

### 2. Untangle Legacy Intent
1. `search_module` to skim the API.
2. `get_file_pr_history` for design discussions/reviews.
3. `get_commit_history` on the hot function.
4. `get_blame` on confusing lines to ping the right author.

### 3. Cleanup Sprint
1. `find_dead_code --min-confidence high` for candidates.
2. For each, `search_function` to double-check dynamic usage.
3. `find_pr_for_line` to ensure it isn’t waiting on an unfinished feature.
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
