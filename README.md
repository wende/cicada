<div align="center">

<img src="public/cicada.png" alt="CICADA Logo" width="400"/>

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

[Installation](#installation) •
[Quick Start](#quick-start) •
[Configuration](#configuration) •
[MCP Tools](#mcp-tools) •
[Contributing](#contributing)

</div>

---

## Overview

CICADA is a Model Context Protocol (MCP) server that provides AI coding assistants with deep code intelligence. **Currently supports Elixir projects**, with Python and TypeScript support planned for future releases. It indexes your codebase using tree-sitter AST parsing and provides instant access to modules, functions, call sites, and PR attribution.

<div align="center">
  <table>
    <tr>
      <td align="center"><b>Without CICADA</b></td>
      <td align="center"><b>With CICADA</b></td>
    </tr>
    <tr>
      <td><img src="public/no-cicada-demo-trimmed.gif" alt="Demo without CICADA" width="450"/></td>
      <td><img src="public/cicada-demo-extended-clean-trimmed copy.gif" alt="Demo with CICADA" width="450"/></td>
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

### Key Features

- **Fast module and function search** - Find any Elixir module or function instantly
- **Call site tracking** - See where functions are used with line numbers
- **Git history & PR attribution** - Find which PR introduced any line of code
- **PR review comments** - Access historical code review discussions
- **Tree-sitter parsing** - Accurate AST-based code analysis
- **MCP integration** - Works with any MCP-compatible AI coding assistant

---

## Installation

### Quick Install with UV (Recommended)

**Installing UV:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

Using [uv](https://github.com/astral-sh/uv) for the best experience:

```bash
# Latest stable release (recommended)
uv tool install git+https://github.com/wende/cicada.git@v0.1.1

# Or latest development version (may include unreleased features)
uv tool install git+https://github.com/wende/cicada.git

# Then setup in each project
cd /path/to/your/elixir/project
cicada
```

**Available commands after install:**
- `cicada-server` - MCP server
- `cicada` - Project setup
- `cicada-index` - Elixir code indexer (checks for updates)
- `cicada-index-pr` - PR indexer (checks for updates)

### Try Before Installing

Test Cicada without installation:

```bash
cd /path/to/your/elixir/project
# Latest stable release
uvx --from git+https://github.com/wende/cicada.git@v0.1.1 cicada

# Or latest development version
uvx --from git+https://github.com/wende/cicada.git cicada
```

**Note:** This works but MCP server startup will be slower and you lose the option to use PR indexing features. Install permanently with `uv tool install` for best performance.

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
cicada-index-pr .
```

---

## Configuration

### Automatic Configuration

`cicada` automatically detects how Cicada is installed and generates the optimal `.mcp.json`:

**With `uv tool install` (recommended):**
```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-server",
      "env": {"CICADA_REPO_PATH": "/path/to/project"}
    }
  }
}
```
✅ Fast startup, no paths, portable!

**With direct Python (fallback):**
```json
{
  "mcpServers": {
    "cicada": {
      "command": "/usr/bin/python3",
      "args": ["/path/to/cicada/cicada/mcp_server.py"],
      "cwd": "/path/to/cicada",
      "env": {"CICADA_REPO_PATH": "/path/to/project"}
    }
  }
}
```
⚠️ Still works, but slower startup

**Migration tip:** If you have the Python version, run:
```bash
uv tool install git+https://github.com/wende/cicada.git@v0.1.1
cicada  # Re-run to get optimized config
```

### Setup Options

```bash
# Basic setup (current directory)
cicada

# Skip dependency installation
cicada --skip-install

# Specify a different repository path
cicada /path/to/other/project
```

**Note:** The `--pr-info` flag has been removed. Use `cicada-index-pr` instead:
```bash
# After setup, optionally index PRs
cicada-index-pr .
```

### Re-indexing

After code changes, re-index your project:

```bash
# Re-index Elixir code
cicada-index --output .cicada/index.json

# Or re-run full setup (skips install by default)
cicada --skip-install
```

### PR Indexing (Optional)

Index pull requests for enhanced git history features:

```bash
# Full index (first time, requires GitHub CLI)
cicada-index-pr .

# Clean rebuild (re-index everything from scratch)
cicada-index-pr . --clean
```

**Requirements:**
- GitHub CLI (`gh`) installed and authenticated
- Run from a GitHub repository

**See also:** [PR Indexing Documentation](docs/PR_INDEXING.md)

---

## MCP Tools

CICADA provides 9 specialized tools for AI assistants to understand and navigate your codebase. For complete technical documentation including parameters and return formats, see [MCP Tools Reference](docs/MCP-Tools-Reference.md).

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

**`search_by_keywords`** (EXPERIMENTAL) - Semantic documentation search
- Find code by concepts, not just names
- Wildcard pattern matching (`create*`, `*_user`)
- NLP-extracted keywords from docs
- Relevance scoring
- Requires: Index built with `--extract-keywords`

**`find_dead_code`** - Identify potentially unused functions
- Three confidence levels (high, medium, low)
- Smart detection of callbacks and behaviors
- Recognition of dynamic call patterns
- Module-level grouping with line numbers
- Excludes test files and `@impl` functions

---

**See also:** [Complete MCP Tools Reference](docs/MCP-Tools-Reference.md) for detailed specifications

---

## CLI Tools

CICADA provides several command-line tools for setup, indexing, and analysis:

### Setup & Configuration

**`cicada`** - Initialize CICADA in your project
```bash
cicada                           # Setup in current directory
cicada --skip-install           # Skip dependency installation
cicada /path/to/other/project   # Setup in different directory
```
- Generates `.mcp.json` configuration
- Creates `.cicada/` directory
- Installs Elixir dependencies
- Configures git attributes for function tracking

### Indexing Tools

**`cicada-index`** - Index Elixir codebase
```bash
cicada-index                         # Index current directory
cicada-index --output .cicada/index.json
cicada-index --extract-keywords      # Include NLP keyword extraction
```
- Parses all Elixir files using tree-sitter
- Extracts modules, functions, and call sites
- Resolves aliases for accurate tracking
- Optional keyword extraction for semantic search

**`cicada-index-pr`** - Index GitHub pull requests
```bash
cicada-index-pr .              # Index PRs for current repo
cicada-index-pr . --clean      # Full rebuild from scratch
```
- Requires GitHub CLI (`gh`) authenticated
- Indexes PR metadata and review comments
- Incremental updates by default
- Enables PR attribution features

### Analysis Tools

**`cicada-find-dead-code`** - Find unused functions (CLI version)
```bash
cicada-find-dead-code                      # Show high confidence only
cicada-find-dead-code --min-confidence low # Show all candidates
cicada-find-dead-code --format json        # JSON output
cicada-find-dead-code --index path/to/index.json
```
- Analyzes function usage across codebase
- Categorizes by confidence level
- Available as both CLI tool and MCP tool

---

## Roadmap

### v0.1.1 (Released - October 2025) ✅
- Module and function search
- Call site tracking with alias resolution
- PR attribution via git blame + GitHub
- PR review comments with line mapping
- File PR history with descriptions
- GraphQL-based PR indexing (30x faster)
- Function usage examples with code snippets
- Git commit history tracking with precise function tracking
- Function evolution metadata (creation, modifications, frequency)
- Git blame integration with line-by-line authorship
- Test file filtering
- Multiple output formats (markdown, JSON)
- Intelligent .mcp.json auto-configuration
- `uv tool install` support
- **Automatic version update checking** - Notifies users when newer versions are available
- **NLP Keyword search** (EXPERIMENTAL) - Semantic search across documentation with wildcard support

### v0.2 (Potential Future Enhancements)
- Incremental code re-indexing
- Enhanced keyword search with BM25 ranking
- RAG with KeyBERT option (??)

### Long Term (Stretch Goals)
- Multi-language support (Python, TypeScript)
- Semantic code search
- Real-time incremental indexing
- Web UI for exploration

### Out of Scope (Non-Goals)
These features are explicitly **not planned**:
- Fuzzy search / "did you mean" suggestions (grep is sufficient)
- Function similarity algorithms or recommendations
- Confidence scoring systems
- Multi-repository support (single repo focus)
- Alternative function suggestions (bang/non-bang variants)

---

## Design Decisions

CICADA prioritizes simplicity and reliability over complexity:

### Intentional Constraints
- **Exact name matching only** - Use grep/ripgrep for fuzzy searches; keeping CICADA focused
- **Direct call tracking** - Tracks explicit function calls; comprehensive call graphs add complexity without enough value
- **Manual documentation search** - Documentation indexing planned for v0.1
- **No AI/ML features** - No similarity algorithms, confidence scoring, or recommendations; deterministic results only

These are deliberate design choices to keep CICADA fast, predictable, and maintainable.

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
cicada-index /path/to/project
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
cicada-index-pr .

# Clean rebuild (re-index everything from scratch)
cicada-index-pr . --clean
```

**Common issues:**
- "No PR index found" → Run `cicada-index-pr .`
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
