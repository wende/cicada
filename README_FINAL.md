<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

### **C**ode **I**ntelligence: **C**ontextual **A**nalysis, **D**iscovery, and **A**ttribution

**Give your AI assistant X-ray vision into your Elixir codebase**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

> 🎉 **Version 0.2.0 Released!** Enhanced semantic search - find code by concepts, not just names. [What's New →](#whats-new-in-v020)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

[Quick Install](#quick-install) •
[Security](#privacy--security) •
[MCP Tools](#mcp-tools-for-ai-assistants) •
[Configuration](#configuration)

</div>

---

## Overview

**CICADA is a Model Context Protocol (MCP) server that stops your AI assistant from searching blindly.**

Instead of grepping through thousands of lines and wasting tokens, AI agents get structured access to:
- Function definitions with signatures and type specs
- All call sites with intelligent alias resolution
- PR context showing *why* code exists
- Git history tracking function evolution
- Semantic search by concept, not just name

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
      <td colspan="2" align="center"><b>82.4% fewer tokens • 33.7% faster • Actually correct</b></td>
    </tr>
  </table>
</div>

---

## Privacy & Security

**Your code stays on your machine. Period.**

CICADA is designed with security and privacy as core principles:

- **100% Local Processing** - All indexing happens on your machine. Your code never leaves your computer.
- **No External Services** - CICADA doesn't send data to cloud services or external APIs.
- **Read-Only MCP Tools** - AI assistants can query your index but cannot modify your codebase through CICADA.
- **No Telemetry** - CICADA doesn't collect usage data or phone home.
- **Optional GitHub Integration** - PR features require GitHub CLI, which uses your existing authentication with standard OAuth scopes.

**Data Storage:**
- Index files stored in `~/.cicada/projects/<hash>/` (outside your repository)
- Only one config file added to your repo (`.mcp.json`, `.cursor/mcp.json`, or `.vscode/settings.json`)
- All data derived from your local git repository and source files

---

## Quick Install

**60 seconds to get started:**

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install CICADA
uv tool install cicada-mcp

# 3. Index your project
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs

# 4. Restart your editor
```

**Done!** Now ask your AI assistant:
```
"What functions are in the MyApp.User module?"
"Where is authenticate/2 called?"
"Find code related to authentication"
```

<details>
<summary><b>Try Before Installing (no permanent installation)</b></summary>

```bash
cd /path/to/your/elixir/project
uvx --from cicada-mcp cicada claude  # or: cursor, vs
```

This runs CICADA without permanent installation. Good for testing, but slower on subsequent runs.

</details>

---

## What You Get

### Stop Wasting Tokens

**Before CICADA:**
```
You: "Where is create_user called?"
AI: *searches 50 files*
AI: *dumps 3,127 tokens*
AI: *misses half the calls due to aliases*
```

**After CICADA:**
```
You: "Where is create_user called?"
AI: "Found 7 call sites in 4 files"
AI: *shows exact locations with context*
```

CICADA tools return **structured, relevant data** instead of file dumps. Designed for token efficiency.

---

### Find Code by Concept

**Don't know what it's called?** Search by what it does:

```
"Find code related to API authentication"
"Show me email validation logic"
"Where do we handle rate limiting?"
```

CICADA's semantic search uses AI-powered keyword extraction to find relevant code even when you don't know exact function names.

---

### Understand Why Code Exists

**Stop guessing at intent.** See the actual design discussions:

```
"Which PR introduced this function?"
"What did reviewers say about this code?"
"Why was this built this way?"
```

CICADA integrates with GitHub to show PR context, review comments, and the problems code was meant to solve.

---

### Refactor Safely

**Track every usage** with intelligent alias resolution:

```
"Show me all places where User.create_user is called"
```

Returns all 7 call sites, even when called through aliases like:
- `alias MyApp.User; User.create_user()`
- `import MyApp.User; create_user()`
- Direct calls: `MyApp.User.create_user()`

Traditional grep would miss most of these.

---

### Clean Up Dead Code

**Find unused functions automatically:**

```
"What public functions are never called?"
```

CICADA analyzes your entire codebase and reports:
- **High confidence** - No call sites found, not a callback
- **Medium confidence** - Only called in tests or dynamically
- **Low confidence** - Very few call sites

Smart detection excludes `@impl` functions and common callbacks.

---

## For Developers: Installation & Configuration

### Setup Your Project

After installing CICADA (see [Quick Install](#quick-install)), navigate to your Elixir project:

```bash
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs
```

**This command will:**
1. Parse all Elixir files using tree-sitter (AST parsing, not text search)
2. Extract modules, functions, type specs, and documentation
3. Resolve aliases and track call sites
4. Generate `index.json` in `~/.cicada/projects/<repo_hash>/`
5. Create MCP configuration file in your project
6. Configure `.gitattributes` for function-level git tracking

**Restart your editor** to activate the MCP connection.

---

### MCP Configuration Files

CICADA creates one configuration file in your project:

<details>
<summary><b>Claude Code</b> (<code>.mcp.json</code>)</summary>

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

</details>

<details>
<summary><b>Cursor</b> (<code>.cursor/mcp.json</code>)</summary>

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

</details>

<details>
<summary><b>VS Code</b> (<code>.vscode/settings.json</code>)</summary>

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

</details>

---

### Re-indexing After Code Changes

CICADA uses incremental indexing to update only changed files:

```bash
cicada claude  # Re-runs setup, updates index incrementally
```

**When to re-index:**
- After pulling changes from git (optional - index still mostly valid)
- After adding new modules (required - new code won't be searchable)
- After major refactoring (recommended - call sites may have changed)

**Force full re-index:**
```bash
rm -rf ~/.cicada/projects/*/hashes.json
cicada index .
```

---

### Optional: Enable PR Features

Index GitHub pull requests to answer questions like "Why was this code written this way?"

<details>
<summary><b>One-Time Setup</b></summary>

```bash
# 1. Install GitHub CLI
brew install gh  # macOS
sudo apt install gh  # Ubuntu
# or visit https://cli.github.com/

# 2. Authenticate
gh auth login

# 3. Index PRs
cicada index-pr .
```

**First time:** May take 5-10 minutes for large repositories.
**Subsequent runs:** Incremental, only fetches new PRs.

**Force rebuild:**
```bash
cicada index-pr . --clean
```

**See also:** [PR Indexing Documentation](docs/PR_INDEXING.md)

</details>

---

## MCP Tools for AI Assistants

CICADA provides 9 specialized tools designed with **token efficiency in mind**. Tools return structured excerpts instead of dumping entire files.

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

---

### Core Search Tools

<details>
<summary><b><code>search_module</code></b> - Find modules and view their complete API</summary>

**What it returns:**
- Module file path and line number
- All public and private functions with arities
- Function signatures with type specifications
- Documentation strings
- Line numbers for each function

**Example output:**
```markdown
# MyApp.User (lib/my_app/user.ex)

## Public Functions

### create_user/2 (line 15)
@spec create_user(map(), Keyword.t()) :: {:ok, User.t()} | {:error, Changeset.t()}

Creates a new user with the given attributes.

### authenticate/2 (line 42)
@spec authenticate(String.t(), String.t()) :: {:ok, User.t()} | {:error, :unauthorized}

Authenticates a user with email and password.
```

**Options:**
- Filter public/private functions
- Output in Markdown or JSON

</details>

<details>
<summary><b><code>search_function</code></b> - Locate function definitions and track all usage</summary>

**What it returns:**
- Function definition location with full signature
- All call sites with file paths and line numbers
- Code context around each call site
- Intelligent alias resolution

**Example output:**
```markdown
## Definition
lib/my_app/user.ex:15
def create_user(attrs, opts \\ [])

## Call Sites (7 found)

### lib/my_app_web/controllers/user_controller.ex:23
case User.create_user(params, audit: true) do

### lib/my_app/accounts.ex:45
with {:ok, user} <- User.create_user(attrs),

### test/my_app/user_test.exs:18
{:ok, user} = User.create_user(%{email: "test@example.com"})
```

**Features:**
- Resolves aliases (finds `User.create/1` even when called via `alias MyApp.User`)
- Filter for test files only
- Shows actual usage examples

</details>

<details>
<summary><b><code>search_module_usage</code></b> - Track module dependencies and relationships</summary>

**What it returns:**
- All `alias` statements referencing the module
- All `import` statements
- All direct function calls to the module
- File paths and line numbers for each usage

**Example output:**
```markdown
## Aliases (5 files)
- lib/my_app_web/controllers/user_controller.ex:3
  alias MyApp.User

## Function Calls (12 locations)
- lib/my_app/accounts.ex:45
  User.create_user(attrs)
```

</details>

<details>
<summary><b><code>search_by_features</code></b> (Beta) - Search code by concepts and features</summary>

**Perfect for:** "I don't know what it's called, but it does X"

**What it returns:**
- Ranked results by relevance score
- Module or function matches with descriptions
- File paths and line numbers
- Confidence scores based on keyword match strength

**Example queries:**
- "authentication"
- "api key storage"
- "email validation"
- `create*` (wildcard patterns)
- `*_user` (pattern matching)

**Requirements:** Index must be built with keyword extraction enabled (`--fast`, `--regular`, or `--max`).

</details>

---

### Git History & Attribution Tools

<details>
<summary><b><code>find_pr_for_line</code></b> - Identify which PR introduced any line of code</summary>

**What it returns:**
- PR number and title
- Author and merge date
- Commit hash
- Direct link to PR on GitHub

**Requirements:** GitHub CLI + PR index (`cicada index-pr .`)

</details>

<details>
<summary><b><code>get_file_pr_history</code></b> - View complete PR history for a file</summary>

**What it returns:**
- All PRs that modified the file (chronological order)
- PR titles, descriptions, and metadata
- Code review comments with line numbers and context
- Links to GitHub PRs

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

</details>

<details>
<summary><b><code>get_commit_history</code></b> - Track file or function evolution over time</summary>

**What it returns:**
- Commit history with dates, authors, messages
- Function-specific tracking (when function_name provided)
- Tracks function through refactors and renames

**Requirements:** Git repository + `.gitattributes` (auto-configured by `cicada` setup)

</details>

<details>
<summary><b><code>get_blame</code></b> - Show line-by-line code ownership</summary>

**What it returns:**
- Grouped by author
- Commit details for each author's contributions
- Code snippets with line numbers
- Commit dates and messages

</details>

<details>
<summary><b><code>find_dead_code</code></b> - Identify potentially unused functions</summary>

**What it returns:**
- Functions grouped by confidence level (high, medium, low)
- Module name, function name, arity, and line number
- Explanation of why each function is flagged

**Confidence Levels:**
- **High** - Public function with zero call sites, not a callback or `@impl`
- **Medium** - Function with suspicious patterns (only called in tests, only dynamic calls)
- **Low** - Public function with very few call sites

**Smart Exclusions:**
- Test files (files ending in `_test.exs`)
- Functions marked with `@impl` (behaviour implementations)
- Common callback patterns (e.g., `__using__/1`, `__on_definition__/6`)

</details>

---

### Complete Tool Reference

For detailed specifications including parameters, return formats, and advanced options, see [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md).

---

## What's New in v0.2.0

### 🤖 Enhanced AI Keyword Extraction and Expansion

AI-powered semantic search capabilities:

- **BERT Extraction**: KeyBERT-based keyword extraction for superior semantic understanding
- **GloVE Expansion**: GloVe-based keyword expansion into terms of similar meaning and domain
- **Configurable Model Tiers**: Choose between `fast`, `regular`, or `large` models to balance speed and accuracy
- **Smart Wildcard Search**: Use patterns like `create*` or `*_user` to find related concepts
- **Improved Relevance Scoring**: Better ranking of search results by semantic relevance and TF scoring

#### Keyword Expansion Example

**Input:** "Authenticates user's credentials"

| Fast (NLP) | Standard (AI) | Max (AI) |
|-----------|--------------|----------|
| auth_user (11.0) | auth_user (8.92) | auth_user (8.92) |
| user (4.0) | user (1.98) | user (1.98) |
| auth (3.0) | interface (1.41) | users (1.39) |
| users (2.8) | users (1.39) | user2 (1.32) |
| authenticates (1.0) | software (1.30) | user1 (1.30) |
| credentials (1.0) | application (1.30) | userlist (1.29) |

### ⚡ Incremental Indexing

- **Graceful Interruption**: Press Ctrl-C to cleanly save progress mid-indexing
- **Resume Capability**: Interrupted? Just run the same command again to continue
- **Smart Merging**: Automatically merges incremental changes with existing index

**[Read the complete changelog →](CHANGELOG.md)**

---

## CLI Tools

CICADA provides command-line tools for setup, indexing, and analysis:

<details>
<summary><b><code>cicada</code></b> - Initialize CICADA in your project</summary>

```bash
cicada [claude|cursor|vs] [project_path]

# Examples:
cicada claude            # Setup for Claude Code in current directory
cicada cursor /path     # Setup for Cursor in specified directory
cicada vs               # Setup for VS Code in current directory
```

Generates MCP configuration, creates storage directory, installs Elixir dependencies, and configures git attributes.

</details>

<details>
<summary><b><code>cicada index</code></b> - Index Elixir codebase</summary>

```bash
cicada index [options] <project_path>

# Examples:
cicada index .                      # Index current directory (regular tier)
cicada index --fast .              # Fast tier (no model downloads)
cicada index --regular .           # Regular tier (128MB download, default)
cicada index --max .               # Max tier (958MB+ download)
```

**Options:**
- `--fast` - Fast tier: Regular extraction + lemminflect morphology
- `--regular` - Regular tier: KeyBERT small + GloVe 50d (default)
- `--max` - Max tier: KeyBERT large + FastText
- `--no-keywords` - Disable keyword extraction entirely

Parses all Elixir files using tree-sitter, extracts modules/functions/call sites, and resolves aliases.

</details>

<details>
<summary><b><code>cicada index-pr</code></b> - Index GitHub pull requests</summary>

```bash
cicada index-pr [options] <project_path>

# Examples:
cicada index-pr .              # Incremental PR indexing
cicada index-pr . --clean      # Full rebuild from scratch
```

**Options:**
- `--clean` - Delete existing PR index and rebuild from scratch

**Requirements:** GitHub CLI authenticated (`gh auth login`)

Indexes PR metadata and review comments. Incremental updates by default.

</details>

<details>
<summary><b><code>cicada find-dead-code</code></b> - Find unused functions (CLI version)</summary>

```bash
cicada find-dead-code [options]

# Examples:
cicada find-dead-code                          # High confidence only
cicada find-dead-code --min-confidence medium  # Medium and high
cicada find-dead-code --min-confidence low     # All candidates
cicada find-dead-code --format json            # JSON output
```

Analyzes function usage across codebase. Available as both CLI tool and MCP tool.

</details>

---

## Troubleshooting

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

---

## What's Available & What's Coming

### ✅ Current Features (v0.2.0)

**Codebase Understanding:**
- Semantic search by concepts and features (Beta) - find code when you don't know exact names
- Module and function discovery with full signatures and type specs
- Call site tracking with intelligent alias resolution
- Dead code detection with confidence levels

**Git Context & History:**
- PR attribution - discover which PR introduced any line
- PR review comments with line numbers
- File PR history with descriptions
- Function evolution tracking
- Git blame integration

**Developer Experience:**
- Incremental indexing for faster reindexing
- Interrupt-safe with graceful Ctrl-C handling
- Multiple AI model tiers (fast, regular, max)
- Wildcard patterns and relevance scoring
- Multiple output formats (Markdown, JSON)

### 🚀 Coming Soon

- **Multi-language support** - Python and TypeScript planned
- **Team features** - Share indexes across team members
- **IDE plugins** - Direct integration without MCP
- **Cloud sync** - Optional remote index storage

---

## Contributing

### Development Setup

```bash
# Clone your fork
git clone https://github.com/wende/cicada.git
cd cicada

# Using uv (recommended)
uv sync

# Or traditional venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Run tests
pytest
```

### Testing

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_parser.py

# Run with coverage
pytest --cov=cicada --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=cicada --cov-report=html
open htmlcov/index.html
```

### Code Style

This project uses:
- **black** for code formatting
- **pytest** for testing
- **type hints** where appropriate

Before submitting a PR:
```bash
# Format code
black cicada tests

# Run tests
pytest

# Check types (if using mypy)
mypy cicada
```

### Reporting Issues

When reporting bugs or requesting features:

1. Check existing [Issues](https://github.com/wende/cicada/issues)
2. If not found, create a new issue with:
   - Clear description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your environment (OS, Python version, Elixir version)

**See also:** [Contributing Guidelines](CONTRIBUTING.md)

---

## Credits

### Built With

- [Tree-sitter](https://tree-sitter.github.io/) - Incremental parsing system
- [tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir) - Elixir grammar
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [GitHub CLI](https://cli.github.com/) - PR attribution
- [KeyBERT](https://github.com/MaartenGr/KeyBERT) - Keyword extraction
- [GloVe](https://nlp.stanford.edu/projects/glove/) / [FastText](https://fasttext.cc/) - Word embeddings

---

## Acknowledgments

- The Anthropic team for Claude Code and MCP
- The Elixir community for tree-sitter-elixir
- All contributors who help improve CICADA

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Stop letting your AI assistant search blindly. Give it CICADA.**

[Get Started](#quick-install) • [View Tools](#mcp-tools-for-ai-assistants) • [Report Issues](https://github.com/wende/cicada/issues)

**[⬆ back to top](#cicada)**

</div>
