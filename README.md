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

### `search_module`
Search for a module by exact name and retrieve all its functions.

**Parameters:**
- `module_name` (string, optional): Full module name (e.g., `"MyApp.User"`)
- `file_path` (string, optional): Path to Elixir file (e.g., `"lib/my_app/user.ex"`)
  - *Provide either `module_name` or `file_path`*
- `format` (string, default: `"markdown"`): Output format (`"markdown"` or `"json"`)
- `private_functions` (string, default: `"exclude"`): Control private function display
  - `"exclude"`: Hide private functions
  - `"include"`: Show all functions
  - `"only"`: Show only private functions

**Returns (Markdown):**
```
MyApp.User

lib/my_app/user.ex:1 • 12 public • 3 private

Public:

create_user(attrs: map) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()} — :42
get_user(id: integer) :: User.t() | nil — :58
...
```

**Returns (JSON):**
```json
{
  "module": "MyApp.User",
  "location": "lib/my_app/user.ex:1",
  "moduledoc": "User management module...",
  "counts": {"public": 12, "private": 3},
  "functions": [
    {
      "signature": "create_user(attrs: map) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}",
      "line": 42,
      "type": "def"
    }
  ]
}
```

### `search_function`
Find function definitions and see where they're called across the codebase.

**Parameters:**
- `function_name` (string, required): Function to search for
  - `"create_user"` - Search all modules
  - `"create_user/2"` - Search specific arity
  - `"MyApp.User.create_user"` - Search specific module
  - `"MyApp.User.create_user/2"` - Module + arity
- `format` (string, default: `"markdown"`): Output format (`"markdown"` or `"json"`)
- `include_usage_examples` (boolean, default: `false`): Include actual code lines showing usage
- `max_examples` (integer, default: `5`): Maximum usage examples to show (1-20)
- `test_files_only` (boolean, default: `false`): Only show calls from test files

**Returns (Markdown):**
```
# create_user/2

## MyApp.User.create_user/2
lib/my_app/user.ex:42

create_user(attrs: map, opts: keyword) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}

Creates a new user with the given attributes.

Called from 8 locations:
- MyApp.UserController.create/2 (lib/my_app_web/controllers/user_controller.ex:23)
- MyApp.Accounts.register/1 (lib/my_app/accounts.ex:15)
...
```

**Returns (JSON):**
```json
{
  "function_name": "create_user/2",
  "results": [
    {
      "module": "MyApp.User",
      "function": {
        "name": "create_user",
        "arity": 2,
        "line": 42,
        "signature": "create_user(attrs: map, opts: keyword)"
      },
      "file": "lib/my_app/user.ex",
      "call_sites": [
        {
          "calling_module": "MyApp.UserController",
          "calling_function": {"name": "create", "arity": 2},
          "file": "lib/my_app_web/controllers/user_controller.ex",
          "line": 23
        }
      ]
    }
  ]
}
```

### `search_module_usage`
Find everywhere a module is used in the codebase (aliases, imports, and function calls).

**Parameters:**
- `module_name` (string, required): Full module name (e.g., `"MyApp.User"`)
- `format` (string, default: `"markdown"`): Output format (`"markdown"` or `"json"`)

**Returns (Markdown):**
```
# MyApp.User Usage

## Aliases (5)
- MyApp.UserController (lib/my_app_web/controllers/user_controller.ex)
  alias MyApp.User
- MyApp.Accounts (lib/my_app/accounts.ex)
  alias MyApp.User

## Function Calls (3 modules)
- MyApp.UserController (lib/my_app_web/controllers/user_controller.ex)
  • create_user/2 at lines: 23, 45
  • get_user/1 at lines: 12
...
```

**Returns (JSON):**
```json
{
  "module": "MyApp.User",
  "usage": {
    "aliases": [
      {
        "importing_module": "MyApp.UserController",
        "alias_name": "User",
        "file": "lib/my_app_web/controllers/user_controller.ex"
      }
    ],
    "function_calls": [
      {
        "calling_module": "MyApp.UserController",
        "file": "lib/my_app_web/controllers/user_controller.ex",
        "calls": [
          {
            "function": "create_user",
            "arity": 2,
            "lines": [23, 45]
          }
        ]
      }
    ]
  }
}
```

### `find_pr_for_line`
Discover which pull request introduced a specific line of code.

**Parameters:**
- `file_path` (string, required): Path to file (relative to repo root or absolute)
- `line_number` (integer, required): Line number (1-indexed, minimum: 1)
- `format` (string, default: `"text"`): Output format (`"text"`, `"json"`, or `"markdown"`)

**Returns (Text):**
```
PR #123: Add user authentication
Author: John Doe <john@example.com>
Commit: abc123def456
Date: 2024-01-15
URL: https://github.com/org/repo/pull/123
```

**Returns (JSON):**
```json
{
  "pr_number": 123,
  "pr_title": "Add user authentication",
  "author": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "commit": {
    "sha": "abc123def456",
    "message": "Add user authentication module"
  },
  "date": "2024-01-15",
  "url": "https://github.com/org/repo/pull/123"
}
```

### `get_file_pr_history`
Get all pull requests that modified a specific file, with descriptions and review comments.

**Parameters:**
- `file_path` (string, required): Path to file (relative to repo root or absolute)

**Returns:**
```markdown
# Pull Request History for lib/user.ex

Found 3 pull request(s)

## PR #42: Add user authentication
- **Author:** @wende
- **Status:** merged
- **URL:** https://github.com/org/repo/pull/42

### Description
This PR adds JWT-based authentication to the User module...

### Review Comments (2)

**@reviewer** (Line 58) ✓ Resolved:
> Consider caching the token validation to avoid redundant DB calls

**@security-team** (Line 92) ✓ Resolved:
> Make sure we're using constant-time comparison for tokens

---

## PR #38: Initial user module
- **Author:** @contributor
- **Status:** merged
- **URL:** https://github.com/org/repo/pull/38

### Description
Creates the basic User module structure
```

**Note:** Requires PR index (run `cicada-index-pr .` first)

### `get_file_history`
Get commit history for a file or function. Tracks functions even as they move within the file.

**Parameters:**
- `file_path` (string, required): Path to file (relative to repo root)
- `function_name` (string, optional): Function name to track (e.g., `"create_user"`)
- `start_line` (integer, optional): Starting line for fallback line-based tracking
- `end_line` (integer, optional): Ending line for fallback line-based tracking
- `show_evolution` (boolean, default: `false`): Include creation date and modification stats
- `max_commits` (integer, default: `10`): Maximum commits to return (1-50)

**Note:** Requires `.gitattributes` with `*.ex diff=elixir` (automatically created by setup)

**Returns:**
```
# Git History for lib/user.ex (lines 42-58)

## Function Evolution
- Created: 2024-01-15 by John Doe (commit `abc123de`)
- Last Modified: 2024-12-20 by Jane Smith (commit `def456ab`)
- Total Modifications: 8 commit(s)

Found 5 commit(s)

## 1. Refactor authentication logic
- Commit: `def456ab`
- Author: Jane Smith (jane@example.com)
- Date: 2024-12-20T10:30:00Z
```

### `get_function_blame`
Show line-by-line authorship with grouped consecutive lines by same author.

**Parameters:**
- `file_path` (string, required): Path to file (relative to repo root)
- `start_line` (integer, required): Starting line number
- `end_line` (integer, required): Ending line number

**Returns:**
```
# Git Blame for lib/user.ex (lines 42-58)

## Group 1: John Doe (lines 42-48)
- Author: John Doe (john@example.com)
- Commit: `abc123de`
- Date: 2024-01-15
- Lines: 7

Code:
def create_user(attrs, opts \\ []) do
  changeset = User.changeset(%User{}, attrs)
  ...
end
```

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

### v0.2 (Potential Future Enhancements)
- Incremental code re-indexing
- NLP Keyword search across documentation using BM25 with wildcards
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

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with test dependencies
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
