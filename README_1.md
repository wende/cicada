<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

### MCP server providing structured codebase intelligence for AI coding assistants

*AST-powered semantic search, PR attribution, and function tracking for Elixir projects*

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

> 🎉 **Version 0.2.0 Released!** Enhanced semantic search - find code by concepts, not just names. [What's New →](#whats-new-in-v020)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

[Quick Install](#installation) •
[Security](#privacy--security) •
[MCP Tools](#for-ai-assistants-available-tools) •
[Configuration](#configuration)

</div>

---

## Overview

CICADA is a Model Context Protocol (MCP) server that transforms how AI coding assistants understand your Elixir codebase. Instead of blind text searches consuming thousands of tokens, AI agents get structured access to modules, functions, call sites, PR context, and git history.

**Currently supports Elixir projects.** Python and TypeScript support planned.

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
      <td colspan="2" align="center"><b>82.4% fewer tokens • 33.7% faster</b></td>
    </tr>
  </table>
</div>

---

## Privacy & Security

**CICADA prioritizes your code security and privacy:**

- **100% Local Processing** - All indexing happens on your machine. Your code never leaves your computer.
- **No External Services** - CICADA doesn't send data to cloud services or external APIs (except GitHub CLI for PR features, using your existing authentication).
- **Read-Only MCP Tools** - AI assistants can query your index but cannot modify your codebase through CICADA.
- **No Telemetry** - CICADA doesn't collect usage data or phone home.
- **Optional GitHub Integration** - PR features require GitHub CLI authentication, which uses your existing credentials with standard OAuth scopes.

**Data Storage:**
- Index files stored in `~/.cicada/projects/<hash>/` (outside your repository)
- Only one config file added to your repo (`.mcp.json`, `.cursor/mcp.json`, or `.vscode/settings.json`)
- All data derived from your local git repository and source files

---

## What's New in v0.2.0

### 🤖 Enhanced AI Keyword Extraction and Expansion

AI-powered semantic search capabilities:

- **BERT Extraction**: KeyBERT-based keyword extraction for superior semantic understanding
- **GloVE Expansion**: GloVe-based keyword expansion into terms of similar meaning and domain
- **Configurable Model Tiers**: Choose between `fast`, `regular`, or `large` models to balance speed and accuracy
- **Smart Wildcard Search**: Use patterns like `create*` or `*_user` to find related concepts
- **Improved Relevance Scoring**: Better ranking of search results by semantic relevance

### ⚡ Incremental Indexing

- **Graceful Interruption**: Press Ctrl-C to cleanly save progress mid-indexing
- **Resume Capability**: Interrupted? Just run the same command again to continue
- **Smart Merging**: Automatically merges incremental changes with existing index

**[Read the complete changelog →](CHANGELOG.md)**

---

## For Developers: Installation & Setup

### Prerequisites

**Required:**
- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Elixir project to index

**Optional (for PR features):**
- [GitHub CLI](https://cli.github.com/) authenticated to your GitHub account

### Installation

**Install uv:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

**Install CICADA:**
```bash
uv tool install cicada-mcp
```

### Setup Your Project

Navigate to your Elixir project and run:

```bash
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs
```

This command will:
1. Index your Elixir codebase (AST parsing, function extraction, call site tracking)
2. Create MCP configuration for your editor
3. Configure git attributes for function-level tracking
4. Store index in `~/.cicada/projects/<hash>/`

**Restart your editor** to activate the MCP connection.

### Try Before Installing

Test CICADA without permanent installation:

```bash
cd /path/to/your/elixir/project
uvx --from cicada-mcp cicada claude  # or: cursor, vs
```

> **Note:** Permanent installation is faster and provides access to all CLI features.

---

## Configuration

### MCP Configuration Files

CICADA creates one configuration file in your project:

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

**VS Code** (`.vscode/settings.json`):
```json
{
  "mcp.servers": {
    "cicada": {
      "command": "uvx",
      "args": ["--from", "cicada-mcp", "cicada-mcp", "${workspaceFolder}"]
    }
  }
}
```

### Re-indexing After Code Changes

CICADA uses incremental indexing to update only changed files:

```bash
cicada claude  # Re-runs setup, updates index incrementally
```

This will:
- Detect changed files since last index
- Update the index with new/modified code
- Keep your existing MCP configuration

### Optional: PR Attribution

Index pull requests to enable PR-related features:

```bash
cicada index-pr .

# Clean rebuild (re-index everything from scratch)
cicada index-pr . --clean
```

**Requirements:** GitHub CLI authenticated (`gh auth login`)

**See also:** [PR Indexing Documentation](docs/PR_INDEXING.md)

---

## For AI Assistants: Available Tools

CICADA provides 9 specialized tools designed with **token efficiency in mind**. Tools return structured, relevant excerpts instead of dumping entire files.

### 🧭 Which Tool Should You Use?

**Quick decision guide based on what you're trying to do:**

| User Request | Recommended Tool(s) | Why |
|-------------|-------------------|-----|
| "Find all functions in UserAuth module" | `search_module` | You know the exact module name |
| "Where is `create_user/2` defined?" | `search_function` | You know the exact function name |
| "Where is `authenticate` called?" | `search_function` | Shows call sites with context |
| "Find code related to API keys" | `search_by_features` | Conceptual search when you don't know exact names |
| "How does authentication work?" | `search_by_features` → `get_file_pr_history` | Find relevant code, then understand design decisions |
| "Which modules use `Repo`?" | `search_module_usage` | Track dependencies and imports |
| "Who wrote this line?" | `find_pr_for_line` | Line-level attribution |
| "Why was this function built this way?" | `get_file_pr_history` | View PR discussions and review comments |
| "When was `validate_email` created?" | `get_commit_history` | Function evolution over time |
| "What code might be unused?" | `find_dead_code` | Identify cleanup candidates |

**Want more context?** Check out [Complete Workflow Examples](docs/WORKFLOW_EXAMPLES.md) with real-world scenarios.

### Core Search Tools

#### `search_module`
**Purpose:** Find modules and view all their functions

**Returns:** Function signatures with type specs, documentation, line numbers

**Example output:**
```markdown
# MyApp.User (lib/my_app/user.ex)

## Public Functions

### create_user/2
Line 15 | @spec create_user(map(), Keyword.t()) :: {:ok, User.t()} | {:error, Changeset.t()}

Creates a new user with the given attributes.

### authenticate/2
Line 42 | @spec authenticate(String.t(), String.t()) :: {:ok, User.t()} | {:error, :unauthorized}

Authenticates a user with email and password.
```

**Options:**
- Filter public/private functions
- Output in Markdown or JSON

---

#### `search_function`
**Purpose:** Locate function definitions and track all usage

**Returns:** Definition location + all call sites with line numbers and context

**Example output:**
```markdown
## Definition
lib/my_app/user.ex:15
def create_user(attrs, opts \\ [])

## Call Sites (3 found)

### lib/my_app_web/controllers/user_controller.ex:23
case User.create_user(params, audit: true) do

### test/my_app/user_test.exs:45
{:ok, user} = User.create_user(%{email: "test@example.com"})
```

**Features:**
- Resolves aliases (finds `User.create/1` even when called via `alias MyApp.User`)
- Filter for test files only
- Shows actual usage examples

---

#### `search_module_usage`
**Purpose:** Track module dependencies and relationships

**Returns:** All aliases, imports, and function calls to a module

**Example output:**
```markdown
## Aliases (5 files)
- lib/my_app_web/controllers/user_controller.ex:3
  alias MyApp.User

## Function Calls (12 locations)
- lib/my_app/accounts.ex:45
  User.create_user(attrs)
```

---

### Git History & Attribution Tools

#### `find_pr_for_line`
**Purpose:** Identify which PR introduced any line of code

**Returns:** PR number, title, author, commit hash, GitHub link

**Requirements:** GitHub CLI + PR index

---

#### `get_file_pr_history`
**Purpose:** View complete PR history for a file

**Returns:** All PRs that modified the file with descriptions and review comments

**Example output:**
```markdown
## PR #123: Add user authentication
**Author:** @developer | **Merged:** 2024-01-15

Added JWT-based authentication system with refresh tokens.

### Review Comments
- lib/my_app/auth.ex:45
  "Consider adding rate limiting here" - @reviewer
```

**Requirements:** GitHub CLI + PR index

---

#### `get_commit_history`
**Purpose:** Track file and function evolution over time

**Returns:** Complete commit history with function-level tracking

**Requirements:** `.gitattributes` configuration (auto-configured by `cicada` setup)

---

#### `get_blame`
**Purpose:** Show line-by-line code ownership

**Returns:** Grouped authorship with commit details and code snippets

---

### Advanced Features

#### `search_by_features` (Beta)
**Purpose:** Search code by concepts and features when you don't know exact names

**Perfect for:** "I don't know what it's called, but it does X"

**Example queries:**
- "authentication"
- "api key storage"
- "email validation"
- `create*` (wildcard patterns)

**Returns:** Ranked results by relevance with confidence scores

**Options:**
- Filter by type: modules only, functions only, or all
- Configurable model tiers (fast, regular, large)

**Requirements:** Index built with keyword extraction (`--fast`, `--regular`, or `--max`)

---

#### `find_dead_code`
**Purpose:** Identify potentially unused functions

**Returns:** Functions grouped by confidence level (high, medium, low)

**Features:**
- Smart detection of callbacks and behaviors
- Recognition of dynamic call patterns
- Module-level grouping with line numbers
- Excludes test files and `@impl` functions

---

### Complete Tool Reference

For detailed specifications including parameters, return formats, and advanced options, see [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md).

---

## CLI Tools

CICADA provides command-line tools for setup, indexing, and analysis:

### `cicada`
Initialize CICADA in your project

```bash
cicada                           # Setup in current directory
cicada /path/to/other/project   # Setup in different directory
```

Generates MCP configuration, creates storage directory, installs Elixir dependencies, and configures git attributes.

---

### `cicada index`
Index Elixir codebase with optional semantic search

```bash
cicada index                         # Index current directory
cicada index --fast                  # Fast tier: Regular extraction + lemminflect (no downloads)
cicada index --regular               # Regular tier: KeyBERT small + GloVe (128MB, default)
cicada index --max                   # Max tier: KeyBERT large + FastText (958MB+)
```

Parses all Elixir files using tree-sitter, extracts modules/functions/call sites, and resolves aliases.

---

### `cicada index-pr`
Index GitHub pull requests

```bash
cicada index-pr .              # Index PRs for current repo
cicada index-pr . --clean      # Full rebuild from scratch
```

Requires GitHub CLI authenticated. Enables PR attribution features.

---

### `cicada find-dead-code`
Find unused functions (CLI version)

```bash
cicada find-dead-code                      # Show high confidence only
cicada find-dead-code --min-confidence low # Show all candidates
cicada find-dead-code --format json        # JSON output
```

---

## Troubleshooting

### "Index file not found"

Run the indexer first:
```bash
cicada index /path/to/project
```

### "Module not found"

Use the exact module name as it appears in code (e.g., `MyApp.User`, not `User`).

### MCP Server Won't Connect

1. Verify `.mcp.json` (or editor-specific config) exists in your project
2. Check that paths are absolute
3. Ensure `index.json` was created successfully in `~/.cicada/projects/<hash>/`
4. Restart your MCP client
5. Check client logs for errors

### PR Features Not Working

```bash
# Install GitHub CLI
brew install gh  # macOS
# or visit https://cli.github.com/

# Authenticate
gh auth login

# Index PRs
cicada index-pr .
```

**Common issues:**
- "No PR index found" → Run `cicada index-pr .`
- "Not a GitHub repository" → Ensure repo has GitHub remote
- Slow indexing → Incremental updates are used by default; use `--clean` for full rebuild

---

## What's Available & What's Coming

### ✅ Current Features (v0.2.0)

**Codebase Understanding:**
- Semantic search by concepts (Beta)
- Module and function discovery with full signatures
- Call site tracking with alias resolution
- Dead code detection with confidence levels

**Git Context & History:**
- PR attribution and review comments
- File PR history
- Function evolution tracking
- Git blame integration

**Developer Experience:**
- Incremental indexing
- Interrupt-safe operation
- Multiple AI model tiers
- Token-efficient tool outputs

### 🚀 Coming Soon

- **Multi-language support** - Python and TypeScript planned

---

## Contributing

### Development Setup

```bash
# Clone your fork
git clone https://github.com/wende/cicada.git
cd cicada

# Using uv (recommended)
uv sync

# Run tests
pytest
```

### Code Style

- **black** for code formatting
- **pytest** for testing
- **type hints** where appropriate

Before submitting a PR:
```bash
black cicada tests
pytest
```

See [Contributing Guidelines](CONTRIBUTING.md) for more details.

---

## Credits

### Built With

- [Tree-sitter](https://tree-sitter.github.io/) - Incremental parsing system
- [tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir) - Elixir grammar
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [GitHub CLI](https://cli.github.com/) - PR attribution

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**[⬆ back to top](#cicada)**

</div>
