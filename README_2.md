<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

**Put an end to token waste and AI hallucinations in your Elixir codebase**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

</div>

---

## The Problem

You're paying for AI coding assistance, but your AI agent is working blindly:

### 😵 **Token Waste**
```
You: "Where is the authenticate function?"
AI: *greps through 50 files*
AI: *dumps 3,127 tokens of search results*
AI: "I found several potential matches..."
```
**Result:** Expensive, slow, often wrong.

### 🤖 **Code Hallucinations**
```
You: "Refactor the user creation code"
AI: "I'll update all call sites..."
AI: *misses half the calls because of aliases*
AI: *suggests functions that don't exist*
```
**Result:** Bugs. Broken builds. Wasted time.

### 🤷 **Missing Context**
```
You: "Why is this code structured this way?"
AI: *reads the implementation*
AI: "Based on the code, it appears to..."
AI: *completely misses the design discussion in PR #47*
```
**Result:** AI doesn't understand your codebase's history and decisions.

### 📊 **The Real Cost**

<div align="center">
  <table>
    <tr>
      <td align="center"><b>Without CICADA</b></td>
      <td align="center"><b>With CICADA</b></td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/wende/cicada/main/public/no-cicada-demo-trimmed.gif" alt="Demo without CICADA" width="450"/></td>
      <td><img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada-demo-extended-clean-trimmed%20copy.gif" alt="Demo with CICADA" width="450"/></td>
    </tr>
    <tr>
      <td align="center">3,127 tokens • 52.84s</td>
      <td align="center">550 tokens • 35.04s</td>
    </tr>
    <tr>
      <td colspan="2" align="center"><b>82.4% fewer tokens • 33.7% faster • Actually correct</b></td>
    </tr>
  </table>
</div>

---

## The Solution

**CICADA gives AI assistants X-ray vision into your codebase.**

Instead of blind text searches, your AI agent gets:

✅ **Exact function locations** with signatures and type specs
✅ **All call sites** with intelligent alias resolution
✅ **PR context** showing *why* code exists and what problems it solves
✅ **Git history** tracking how functions evolved over time
✅ **Semantic search** finding code by concept, not just name
✅ **Dead code detection** identifying cleanup opportunities

**All processed locally. Zero cloud dependencies. 82% fewer tokens per query.**

---

## How It Works

CICADA is a Model Context Protocol (MCP) server that indexes your Elixir codebase using AST parsing:

1. **Parse** - Uses tree-sitter to understand code structure (not just text)
2. **Index** - Extracts modules, functions, call sites, and relationships
3. **Connect** - Integrates with Claude, Cursor, VS Code via MCP
4. **Query** - AI agents ask structured questions, get precise answers

**Currently supports Elixir.** Python and TypeScript coming soon.

---

## Quick Install

**60 seconds to try it:**

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install CICADA
uv tool install cicada-mcp

# Index your project
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs

# Restart your editor
```

**That's it!** Now ask your AI assistant:

```
"What functions are in the MyApp.User module?"
"Where is authenticate/2 called?"
"Find code related to API authentication"
```

Watch the magic happen. ✨

---

## Real-World Impact

### Before CICADA

**You:** "Show me where we create users"

**AI:** *Searches through 15 files with grep*
**AI:** *Dumps 2,000+ tokens of context*
**AI:** "Here are several places where user creation might occur..."
**AI:** *Suggests changes that miss 3 call sites*

**Time:** 45 seconds
**Tokens:** 2,847
**Accuracy:** 60%

### After CICADA

**You:** "Show me where we create users"

**AI:** *Queries CICADA's structured index*
**AI:** "The `create_user/2` function is defined in `lib/my_app/user.ex:15` and is called in 7 locations. Would you like to see them?"

**Time:** 12 seconds
**Tokens:** 423
**Accuracy:** 100%

---

## What Can You Do With CICADA?

### 🔍 Find Code by Concept

```
"Find all code related to authentication"
"Show me email validation functions"
"Where do we handle API keys?"
```

CICADA's semantic search finds relevant code even when you don't know exact names.

### 📝 Understand Design Decisions

```
"Why was this function built this way?"
"What problem does this solve?"
"Who decided on this approach?"
```

CICADA shows you the PR discussions, review comments, and git history behind every line.

### 🔧 Refactor Safely

```
"Find all places where authenticate/2 is called"
"Which modules depend on User?"
"Show me all usages of Repo.insert/2"
```

CICADA tracks call sites intelligently, even through aliases and dynamic calls.

### 🧹 Clean Up Dead Code

```
"What functions are never called?"
"Find unused public functions"
"Identify cleanup candidates"
```

CICADA analyzes your entire codebase to find functions with no call sites.

### 📊 Track Evolution

```
"When was validate_email/1 created?"
"Show me the history of this function"
"Who wrote this code and when?"
```

CICADA integrates with git to show function-level history and authorship.

---

## Features That Save You Time

### Semantic Search (v0.2.0)
Find code by what it does, not what it's called. "authentication" finds `verify_credentials/2`, `check_password/1`, and `authenticate_user/3`.

### Smart Call Site Tracking
Handles aliases, imports, and module references correctly. Never miss a usage again.

### PR Attribution
See which PR introduced any line, with full context including review comments.

### Function Evolution
Track when functions were created, how often they're modified, and their complete git history.

### Dead Code Detection
Three confidence levels (high, medium, low) with smart recognition of callbacks and dynamic patterns.

### Incremental Indexing
Only re-indexes changed files. Press Ctrl-C to interrupt safely and resume later.

### Token Efficiency
Tools return structured excerpts, not entire files. 80%+ token reduction per query.

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Elixir project

**Optional (for PR features):**
- [GitHub CLI](https://cli.github.com/) authenticated

### Step 1: Install

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install CICADA
uv tool install cicada-mcp
```

### Step 2: Index Your Project

```bash
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs
```

This indexes your code, creates MCP configuration, and sets up git tracking.

### Step 3: Restart Your Editor

CICADA is now connected. Start asking questions!

### Optional: Enable PR Features

```bash
# Authenticate with GitHub
gh auth login

# Index pull requests
cicada index-pr .
```

Now you can ask "Which PR introduced this line?" and "Show me the review comments for this file."

---

## Configuration

CICADA stores indexes in `~/.cicada/projects/<hash>/` and creates a single config file in your project:

**Claude Code** (`.mcp.json`):
```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp", "/absolute/path/to/your/project"]
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["--from", "cicada-mcp", "cicada-mcp", "."]
    }
  }
}
```

That's it. No complex configuration needed.

---

## MCP Tools Reference

CICADA provides 9 tools for AI assistants:

| Tool | What It Does | When to Use |
|------|--------------|-------------|
| `search_module` | Find modules and view their API | You know the module name |
| `search_function` | Find function definitions and call sites | You know the function name |
| `search_module_usage` | Track module dependencies | Understanding relationships |
| `search_by_features` | Search by concept/feature | You don't know exact names |
| `find_pr_for_line` | Which PR introduced this line? | Understanding authorship |
| `get_file_pr_history` | All PRs that modified a file | Understanding evolution |
| `get_commit_history` | Git history for file/function | Tracking changes over time |
| `get_blame` | Line-by-line authorship | Who wrote what |
| `find_dead_code` | Identify unused functions | Code cleanup |

**See also:** [Complete Tool Documentation](docs/MCP_TOOLS_REFERENCE.md) • [Workflow Examples](docs/WORKFLOW_EXAMPLES.md)

---

## Privacy & Security

**Your code stays on your machine:**

- 100% local processing - no cloud services
- Read-only MCP tools - AI can't modify your code
- No telemetry or data collection
- GitHub integration (optional) uses your existing authentication

---

## Troubleshooting

### MCP Connection Issues

1. Check that `.mcp.json` exists in your project
2. Verify paths are absolute
3. Ensure index was created in `~/.cicada/projects/<hash>/`
4. Restart your editor
5. Check editor logs for errors

### "Index file not found"

Run: `cicada index /path/to/project`

### "Module not found"

Use exact module names: `MyApp.User`, not `User`

### PR Features Not Working

1. Install GitHub CLI: `brew install gh`
2. Authenticate: `gh auth login`
3. Index PRs: `cicada index-pr .`

---

## What's Coming

- **Multi-language support** - Python and TypeScript
- **IDE plugins** - Direct integration without MCP
- **Team features** - Share indexes across team members
- **Cloud sync** - Optional remote index storage

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- Code style guidelines
- Testing requirements
- PR process

---

## Credits

Built with [Tree-sitter](https://tree-sitter.github.io/), [MCP](https://modelcontextprotocol.io/), and [GitHub CLI](https://cli.github.com/).

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

<div align="center">

**Stop letting your AI assistant search blindly. Give it CICADA.**

[Get Started](#quick-install) • [Read the Docs](docs/) • [Report Issues](https://github.com/wende/cicada/issues)

</div>
