<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

### **C**ode **I**ntelligence: **C**ontextual **A**nalysis, **D**iscovery, and **A**ttribution

*Coding Agents search blindly. Be their guide.*

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Elixir](https://img.shields.io/badge/Elixir-Support-purple.svg)](https://elixir-lang.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

> 🎉 **Version 0.2.0 Released!** Enhanced AI-powered codebase understanding - find code by concepts, not just names. [What's New →](#whats-new-in-v020)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

[Installation](#installation) •
[Quick Start](#quick-start) •
[Configuration](#configuration) •
[MCP Tools](#mcp-tools) •
[Contributing](#contributing)

</div>

---

## Overview

CICADA is a Model Context Protocol (MCP) server that provides AI coding assistants with **deep codebase understanding**. **Currently supports Elixir projects**, with Python and TypeScript support planned for future releases. It indexes your codebase using tree-sitter AST parsing and provides instant access to modules, functions, call sites, PR attribution, and the context behind code decisions.

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
| | allows (1.30) | non-user (1.29) |
| | interfaced (0.99) | non-users (0.90) |
| | interfaces (0.99) | auth (0.90) |
| | interfacing (0.99) | authenticates (0.72) |
| | softwares (0.91) | credentials (0.68) |
| | applications (0.91) | xauth (0.58) |
| | auth (0.90) | authentication (0.53) |
| | authenticates (0.72) | authentications (0.52) |
| | credentials (0.68) | authentification (0.52) |
| | | login (0.52) |
| | | authenticate (0.51) |
| | | authenticators (0.50) |
| | | authenticator (0.50) |

### ⚡ Incremental Indexing
### 🛡️ QoL

- **Graceful Interruption**: Press Ctrl-C to cleanly save progress mid-indexing
- **Resume Capability**: Interrupted? Just run the same command again to continue
- **Smart Merging**: Automatically merges incremental changes with existing index

**[Read the complete changelog →](CHANGELOG.md)**

---

### Key Features

- **Codebase understanding, not just search** - Find code by concepts ("authentication", "api keys") when you don't know exact names
- **AST-aware function discovery** - View function definitions with full signatures, types, and documentation—no implementation bloat
- **Intelligent call site tracking** - Resolve aliases and track where functions are actually invoked across the codebase
- **PR attribution & review context** - Discover *why* code exists: view the pull request discussions and design decisions behind any line
- **Function evolution tracking** - See when functions were created, how often they're modified, and their complete git history
- **Semantic module analysis** - Understand module dependencies, imports, and relationships beyond text matching
- **MCP integration** - Provide AI coding assistants with structured context and understanding, not raw text

## Installation

**Install uv:** `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`

### Recommended: Permanent Installation

```bash
uv tool install cicada-mcp
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs
```

**That's it!** Restart your editor and start coding.

> **Available commands:** `cicada [claude|cursor|vs]`, `cicada index`, `cicada index-pr`, `cicada find-dead-code`

### Try Before Installing (uvx)

```bash
cd /path/to/your/elixir/project
uvx --from cicada-mcp cicada claude  # or: cursor, vs
```

> **Note:** Permanent installation is faster and provides access to all CLI features.

### Quick Setup for Cursor and Claude Code

**For Cursor:**

Click the install button at the top of this README or visit:
[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

**For Claude Code:**

```bash
# Option 1: Using claude mcp add command
claude mcp add cicada -- uvx cicada-mcp ./path/to/your/codebase

# Option 2: Using setup script
uvx --from cicada-mcp cicada claude
```

**Then for both editors,** run these commands in your codebase to generate keyword lookup and GitHub PR lookup databases:

```bash
# Generate keyword lookup database
uvx --from cicada-mcp cicada-index .

# Generate GitHub PR lookup database
uvx --from cicada-mcp cicada-index-pr .
```

---

## Quick Start

After installation, ask your AI coding assistant:

```
"What functions are in the MyApp.User module?"
"Show me where authenticate/2 is called"
"Which PR introduced line 42 of user.ex?"
"Show me all PRs that modified the User module with their review comments"
"Find all usages of Repo.insert/2"
"What's the git history of the authenticate function?"
```

**For PR features**, first run:
```bash
cicada index-pr .
```

---

## Configuration

### Re-indexing

After code changes, re-run the setup command:

```bash
# Re-index for Claude Code
uvx --from cicada-mcp cicada claude

# Or if permanently installed
cicada claude
```

This will:
- Detect changed files (incremental indexing)
- Update the index with new/modified code
- Keep your existing MCP configuration

### Optional: PR Attribution

Index pull requests for PR-related features:

```bash
# After permanent installation
cicada index-pr .

# Or with uvx
uvx --from cicada-mcp cicada-index-pr .

# Clean rebuild (re-index everything from scratch)
cicada index-pr . --clean
```

**See also:** [PR Indexing Documentation](docs/PR_INDEXING.md)

---

## MCP Tools

CICADA provides 9 specialized tools for AI assistants to understand and navigate your codebase. For complete technical documentation including parameters and return formats, see [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md).

### 🧭 Which Tool Should You Use?

**Not sure which tool to use?** Here's a quick decision guide based on what you're trying to do:

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

**Want to see these tools in action?** Check out our [Complete Workflow Examples](docs/WORKFLOW_EXAMPLES.md) with pro tips and real-world scenarios like adding features, debugging issues, refactoring safely, and learning new codebases.

### Core Search Tools

**`search_module`** - Find modules and view all their functions
- Search by exact module name or file path
- View function signatures with type specs
- Filter public/private functions
- Output in Markdown or JSON

**`search_function`** - Locate function definitions and track usage
- Search by function name, arity, or full module path
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

---

**See also:** [Complete MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md) for detailed specifications

---

## CLI Tools

CICADA provides several command-line tools for setup, indexing, and analysis:

### Setup & Configuration

**`cicada`** - Initialize CICADA in your project
```bash
cicada                           # Setup in current directory
cicada /path/to/other/project   # Setup in different directory
```
- Generates `.mcp.json` configuration
- Creates `.cicada/` directory
- Installs Elixir dependencies
- Configures git attributes for function tracking

### Indexing Tools

**`cicada index`** - Index Elixir codebase
```bash
cicada index                         # Index current directory
cicada index --fast                  # Fast tier: Regular extraction + lemminflect (no downloads)
cicada index --regular               # Regular tier: KeyBERT small + GloVe (128MB, default)
cicada index --max                   # Max tier: KeyBERT large + FastText (958MB+)
```
- Parses all Elixir files using tree-sitter
- Extracts modules, functions, and call sites
- Resolves aliases for accurate tracking
- Optional keyword extraction for semantic search

**`cicada index-pr`** - Index GitHub pull requests
```bash
cicada index-pr .              # Index PRs for current repo
cicada index-pr . --clean      # Full rebuild from scratch
```
- Requires GitHub CLI (`gh`) authenticated
- Indexes PR metadata and review comments
- Incremental updates by default
- Enables PR attribution features

### Analysis Tools

**`cicada find-dead-code`** - Find unused functions (CLI version)
```bash
cicada find-dead-code                      # Show high confidence only
cicada find-dead-code --min-confidence low # Show all candidates
cicada find-dead-code --format json        # JSON output
cicada find-dead-code --index path/to/index.json
```
- Analyzes function usage across codebase
- Categorizes by confidence level
- Available as both CLI tool and MCP tool

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

---

## Contributing

### Development Setup

```bash
# Clone your fork
git clone https://github.com/wende/cicada.git
cd cicada

# Using uv (recommended)
uv sync

# Or traditional venv (legacy)
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
pytest tests/test_search_function.py

# Run with coverage (terminal report)
pytest --cov=cicada --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=cicada --cov-report=html
# Open htmlcov/index.html in your browser

# Run with coverage and see which lines need tests
pytest --cov=cicada --cov-report=term-missing --cov-report=html

# Check coverage and fail if below threshold (e.g., 80%)
pytest --cov=cicada --cov-fail-under=80
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

1. Verify `.mcp.json` exists in your project root
2. Check that all paths in `.mcp.json` are absolute
3. Ensure `index.json` was created successfully
4. Restart your MCP client (Claude Code, Cline, etc.)
5. Check your MCP client logs for errors

### PR Features Not Working

PR features require the GitHub CLI and a PR index:

```bash
# Install GitHub CLI
brew install gh  # macOS
# or visit https://cli.github.com/

# Authenticate
gh auth login

# Index PRs (first time or after new PRs)
cicada index-pr .

# Clean rebuild (re-index everything from scratch)
cicada index-pr . --clean
```

**Common issues:**
- "No PR index found" → Run `cicada index-pr .`
- "Not a GitHub repository" → Ensure repo has GitHub remote
- Slow indexing → Incremental updates are used by default

#### Uninstall

Remove CICADA from a project:

```bash
rm -rf .cicada/ .mcp.json
# Restart your MCP client
```

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

## Acknowledgments

- The Anthropic team for Claude Code and MCP
- The Elixir community for tree-sitter-elixir
- All contributors who help improve CICADA

---

<div align="center">

**[⬆ back to top](#cicada)**

</div>
