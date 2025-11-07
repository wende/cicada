<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

### Code Intelligence: Contextual Analysis, Discovery, and Attribution

*A Model Context Protocol server providing AST-powered codebase intelligence*

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

> 🎉 **Version 0.2.0 Released!** Enhanced AI-powered codebase understanding - find code by concepts, not just names. [What's New →](#whats-new-in-v020)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

[Installation](#installation) •
[Documentation](#documentation) •
[Tools Reference](#mcp-tools) •
[Configuration](#configuration) •
[Contributing](#contributing)

</div>

---

## Overview

CICADA is a Model Context Protocol (MCP) server that provides AI coding assistants with deep codebase understanding through structured analysis. Currently supports Elixir projects with Python and TypeScript support planned.

### Key Capabilities

- **AST-aware function discovery** - Parse Elixir code using tree-sitter to extract modules, functions, signatures, type specifications, and documentation
- **Intelligent call site tracking** - Resolve aliases and module references to accurately track where functions are invoked across the codebase
- **Semantic search capabilities** - Find code by conceptual features using AI-powered keyword extraction and expansion (KeyBERT + GloVe/FastText)
- **PR attribution and context** - Integrate with GitHub to map lines of code to pull requests, review comments, and design discussions
- **Function evolution tracking** - Leverage git history to show when functions were created, modified, and by whom
- **Dead code analysis** - Identify potentially unused public functions with confidence levels based on static analysis
- **Module dependency mapping** - Track which modules import, alias, or call functions from other modules

### Performance

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

## What's New in v0.2.0

### AI-Powered Keyword Extraction and Expansion

**KeyBERT Integration** - Semantic keyword extraction from documentation and docstrings using transformer-based models.

**GloVe/FastText Expansion** - Expand extracted keywords into semantically similar terms for broader search coverage.

**Configurable Model Tiers:**
- `--fast` - Regular extraction with lemminflect morphology (no model downloads)
- `--regular` - KeyBERT small + GloVe 50d (128MB download, default)
- `--max` - KeyBERT large + FastText (958MB+ download)

**Keyword Expansion Example:**

Input: "Authenticates user's credentials"

| Fast (NLP) | Standard (AI) | Max (AI) |
|-----------|--------------|----------|
| auth_user (11.0) | auth_user (8.92) | auth_user (8.92) |
| user (4.0) | user (1.98) | user (1.98) |
| auth (3.0) | interface (1.41) | users (1.39) |
| users (2.8) | users (1.39) | user2 (1.32) |
| authenticates (1.0) | software (1.30) | user1 (1.30) |
| credentials (1.0) | application (1.30) | userlist (1.29) |

**Relevance Scoring** - TF-IDF weighted scoring to rank results by semantic relevance.

**Wildcard Patterns** - Support for patterns like `create*`, `*_user`, `validate_*` to find related concepts.

### Incremental Indexing

**Graceful Interruption** - SIGINT (Ctrl-C) handling to cleanly save progress mid-indexing.

**Resume Capability** - Detect incomplete indexing and continue from last checkpoint.

**Smart Merging** - Automatically merge incremental changes with existing index data.

**Hash-based Change Detection** - Only re-parse files that have been modified since last index.

### Quality of Life Improvements

**Progress Indicators** - Real-time progress bars showing files processed and estimated completion time.

**Error Recovery** - Continue indexing even if individual files fail to parse, logging errors for review.

**Storage Optimization** - Centralized storage in `~/.cicada/projects/<hash>/` reduces repository clutter.

**[Complete Changelog →](CHANGELOG.md)**

---

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- Elixir project to index

**Optional dependencies:**
- [GitHub CLI](https://cli.github.com/) - Required for PR attribution features
- Git repository - Required for commit history and blame features

### Installing uv

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS (Homebrew):**
```bash
brew install uv
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Permanent Installation (Recommended)

```bash
uv tool install cicada-mcp
```

This installs CICADA globally and makes the `cicada` command available system-wide.

### Temporary Installation (Try Before Installing)

```bash
cd /path/to/your/elixir/project
uvx --from cicada-mcp cicada claude  # or: cursor, vs
```

Uses `uvx` to run CICADA without permanent installation. Good for testing but slower on subsequent runs.

### Project Setup

Navigate to your Elixir project and run the setup command:

```bash
cd /path/to/your/elixir/project
cicada claude  # for Claude Code
cicada cursor  # for Cursor
cicada vs      # for VS Code
```

**This command will:**

1. Parse all Elixir files in the project using tree-sitter
2. Extract modules, functions, type specs, and documentation
3. Resolve aliases and track call sites
4. Generate index.json in `~/.cicada/projects/<repo_hash>/`
5. Create MCP configuration file (`.mcp.json`, `.cursor/mcp.json`, or `.vscode/settings.json`)
6. Configure `.gitattributes` for function-level git tracking

**Restart your editor** to activate the MCP connection.

---

## Configuration

### Storage Structure

CICADA uses a centralized storage structure:

```
~/.cicada/
└── projects/
    └── <repo_hash>/          # SHA-256 hash of repository path
        ├── index.json        # Main codebase index
        ├── config.yaml       # Indexing configuration
        ├── hashes.json       # File hash cache for incremental updates
        └── pr_index.json     # GitHub PR data (optional)
```

**Repository configuration:**

Only one MCP config file is added to your repository:
- `.mcp.json` (Claude Code)
- `.cursor/mcp.json` (Cursor)
- `.vscode/settings.json` (VS Code)

### MCP Server Configuration

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

### Git Configuration

CICADA automatically configures `.gitattributes` for function-level tracking:

```gitattributes
*.ex diff=elixir
*.exs diff=elixir
```

This enables `git log -L :function_name:file.ex` to track function evolution.

### Re-indexing

After code changes, re-run the setup command to update the index:

```bash
cicada claude  # or: cicada cursor, cicada vs
```

CICADA uses incremental indexing to only process changed files.

**Force full re-index:**
```bash
rm -rf ~/.cicada/projects/<repo_hash>/hashes.json
cicada index .
```

### PR Attribution Setup

Index GitHub pull requests to enable PR-related features:

```bash
# Authenticate with GitHub CLI (one-time)
gh auth login

# Index pull requests
cicada index-pr .

# Full rebuild (re-index all PRs from scratch)
cicada index-pr . --clean
```

**Requirements:**
- GitHub CLI installed and authenticated
- Repository must have a GitHub remote
- Internet connection for GitHub API access

**Incremental updates:** By default, `cicada index-pr` only fetches new PRs since last index.

**See also:** [PR Indexing Documentation](docs/PR_INDEXING.md)

---

## MCP Tools

CICADA provides 9 MCP tools for AI assistants to query the codebase. All tools return structured data in Markdown or JSON format.

### Quick Reference

| Tool | Purpose | Requirements |
|------|---------|--------------|
| `search_module` | Find modules and view their complete API | Index |
| `search_function` | Find function definitions and call sites | Index |
| `search_module_usage` | Track module dependencies and imports | Index |
| `search_by_features` | Semantic search by concepts/keywords | Index with `--fast`, `--regular`, or `--max` |
| `find_pr_for_line` | Identify which PR introduced a line | Index + PR index + GitHub CLI |
| `get_file_pr_history` | View all PRs that modified a file | Index + PR index + GitHub CLI |
| `get_commit_history` | Track file/function evolution over time | Index + Git repository |
| `get_blame` | Show line-by-line code ownership | Index + Git repository |
| `find_dead_code` | Identify potentially unused functions | Index |

### Core Search Tools

#### `search_module`

**Purpose:** Locate modules by name or file path and view their complete API.

**Parameters:**
- `module_name` (string, required) - Module name (e.g., `MyApp.User`) or file path
- `show_private` (boolean, optional, default: false) - Include private functions
- `format` (string, optional, default: "markdown") - Output format: "markdown" or "json"

**Returns:** Module metadata including:
- Full module path and file location
- Public and private function lists with arities
- Function signatures with type specifications
- Documentation strings
- Line numbers for each function

**Example query:** "What functions are in the MyApp.User module?"

---

#### `search_function`

**Purpose:** Find function definitions by name and locate all call sites.

**Parameters:**
- `function_name` (string, required) - Function name with optional arity (e.g., `create_user` or `create_user/2`)
- `module_name` (string, optional) - Limit search to specific module
- `test_only` (boolean, optional, default: false) - Only search test files
- `format` (string, optional, default: "markdown") - Output format

**Returns:**
- Function definition location with full signature
- Complete list of call sites with file paths and line numbers
- Code context around each call site
- Alias resolution (finds calls through `alias MyApp.User` as `User.create_user/2`)

**Example query:** "Where is authenticate/2 called?"

---

#### `search_module_usage`

**Purpose:** Find all places where a module is imported, aliased, or used.

**Parameters:**
- `module_name` (string, required) - Full module name (e.g., `MyApp.Repo`)
- `format` (string, optional, default: "markdown") - Output format

**Returns:**
- All `alias` statements referencing the module
- All `import` statements
- All direct function calls to the module
- File paths and line numbers for each usage

**Example query:** "Which modules use Repo?"

---

#### `search_by_features` (Beta)

**Purpose:** Search codebase by conceptual features using semantic keyword matching.

**Parameters:**
- `features` (string, required) - Space-separated keywords or description
- `result_type` (string, optional, default: "all") - "modules", "functions", or "all"
- `format` (string, optional, default: "markdown") - Output format

**Returns:**
- Ranked results by relevance score
- Module or function matches with descriptions
- File paths and line numbers
- Confidence scores based on keyword match strength

**Supports:**
- Natural language descriptions: "authenticates user credentials"
- Multiple keywords: "api key storage validation"
- Wildcard patterns: `create*`, `*_user`, `validate_*`

**Requirements:** Index must be built with keyword extraction enabled (`--fast`, `--regular`, or `--max`).

**Example queries:**
- "Find code related to authentication"
- "api key storage"
- "email validation"

---

### Git History & Attribution Tools

#### `find_pr_for_line`

**Purpose:** Identify which GitHub pull request introduced a specific line of code.

**Parameters:**
- `file_path` (string, required) - Relative path to file
- `line_number` (integer, required) - Line number

**Returns:**
- PR number and title
- Author and merge date
- Commit hash
- Direct link to PR on GitHub

**Requirements:**
- GitHub CLI authenticated
- PR index generated (`cicada index-pr .`)

---

#### `get_file_pr_history`

**Purpose:** View complete PR history for a file with descriptions and review comments.

**Parameters:**
- `file_path` (string, required) - Relative path to file
- `format` (string, optional, default: "markdown") - Output format

**Returns:**
- All PRs that modified the file (chronological order)
- PR titles, descriptions, and metadata
- Code review comments with line numbers and context
- Links to GitHub PRs

**Requirements:**
- GitHub CLI authenticated
- PR index generated

---

#### `get_commit_history`

**Purpose:** Track file or function evolution over time using git history.

**Parameters:**
- `file_path` (string, required) - Relative path to file
- `function_name` (string, optional) - Function name for function-level tracking

**Returns:**
- Commit history with dates, authors, messages
- Function-specific tracking (when function_name provided)
- Tracks function through refactors and renames

**Requirements:**
- Git repository
- `.gitattributes` configured (automatic with `cicada` setup)

---

#### `get_blame`

**Purpose:** Show line-by-line code ownership with commit information.

**Parameters:**
- `file_path` (string, required) - Relative path to file
- `start_line` (integer, optional) - Start line number
- `end_line` (integer, optional) - End line number

**Returns:**
- Grouped by author
- Commit details for each author's contributions
- Code snippets with line numbers
- Commit dates and messages

**Requirements:** Git repository

---

### Advanced Analysis Tools

#### `find_dead_code`

**Purpose:** Identify potentially unused public functions based on static analysis.

**Parameters:**
- `min_confidence` (string, optional, default: "high") - "high", "medium", or "low"
- `format` (string, optional, default: "markdown") - Output format

**Returns:**
- Functions grouped by confidence level
- Module name, function name, arity, and line number
- Explanation of why each function is flagged

**Confidence Levels:**
- **High** - Public function with zero call sites, not a callback or `@impl`
- **Medium** - Function with suspicious patterns (only called in tests, only dynamic calls)
- **Low** - Public function with very few call sites

**Exclusions:**
- Test files (files ending in `_test.exs`)
- Functions marked with `@impl` (behaviour implementations)
- Common callback patterns (e.g., `__using__/1`, `__on_definition__/6`)

---

### Decision Guide

**Use this tool when:**

| Your Goal | Recommended Tool(s) | Workflow |
|-----------|-------------------|----------|
| Find function by exact name | `search_function` | Direct lookup |
| Find module API | `search_module` | Module introspection |
| Find code by concept | `search_by_features` | Semantic search |
| Understand code origin | `find_pr_for_line` | Single line attribution |
| Understand code evolution | `get_file_pr_history` + `get_commit_history` | Historical analysis |
| Refactor safely | `search_function` + `search_module_usage` | Impact analysis |
| Clean up codebase | `find_dead_code` | Dead code detection |
| Track dependencies | `search_module_usage` | Dependency mapping |

**For detailed specifications, see:** [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md)

**For workflow examples, see:** [Workflow Examples](docs/WORKFLOW_EXAMPLES.md)

---

## CLI Tools

### `cicada`

Initialize CICADA in a project.

```bash
cicada [editor] [project_path]

# Examples:
cicada claude            # Setup for Claude Code in current directory
cicada cursor /path     # Setup for Cursor in specified directory
cicada vs               # Setup for VS Code in current directory
```

**Available editors:** `claude`, `cursor`, `vs`

---

### `cicada index`

Index an Elixir codebase.

```bash
cicada index [options] <project_path>

# Examples:
cicada index .                      # Index current directory (regular tier)
cicada index --fast .              # Fast tier (no model downloads)
cicada index --regular .           # Regular tier (128MB download)
cicada index --max .               # Max tier (958MB+ download)
cicada index --no-keywords .       # Disable keyword extraction
```

**Options:**
- `--fast` - Fast tier: Regular extraction + lemminflect morphology
- `--regular` - Regular tier: KeyBERT small + GloVe 50d (default)
- `--max` - Max tier: KeyBERT large + FastText
- `--no-keywords` - Disable keyword extraction entirely

---

### `cicada index-pr`

Index GitHub pull requests for a repository.

```bash
cicada index-pr [options] <project_path>

# Examples:
cicada index-pr .              # Incremental PR indexing
cicada index-pr . --clean      # Full rebuild from scratch
```

**Options:**
- `--clean` - Delete existing PR index and rebuild from scratch

**Requirements:**
- GitHub CLI installed and authenticated
- Repository with GitHub remote

---

### `cicada find-dead-code`

Find potentially unused functions (CLI version of `find_dead_code` MCP tool).

```bash
cicada find-dead-code [options]

# Examples:
cicada find-dead-code                          # High confidence only
cicada find-dead-code --min-confidence medium  # Medium and high
cicada find-dead-code --min-confidence low     # All candidates
cicada find-dead-code --format json            # JSON output
cicada find-dead-code --index /path/to/index.json
```

**Options:**
- `--min-confidence` - Minimum confidence level: "high", "medium", "low" (default: "high")
- `--format` - Output format: "markdown" or "json" (default: "markdown")
- `--index` - Path to index.json (default: auto-detect from current directory)

---

## Documentation

- **[MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md)** - Complete tool specifications with parameters and return formats
- **[Workflow Examples](docs/WORKFLOW_EXAMPLES.md)** - Real-world usage scenarios and pro tips
- **[PR Indexing](docs/PR_INDEXING.md)** - GitHub PR integration setup and troubleshooting
- **[CHANGELOG](CHANGELOG.md)** - Version history and release notes

---

## Troubleshooting

### Index Not Found

**Error:** "Index file not found"

**Solution:**
```bash
cicada index /path/to/project
```

Ensure indexing completed successfully. Check for `~/.cicada/projects/<hash>/index.json`.

---

### Module Not Found

**Error:** "Module MyApp.User not found"

**Causes:**
- Module name is incorrect (use full module path: `MyApp.User`, not `User`)
- Module hasn't been indexed (re-run `cicada index`)
- Module file was recently added (run incremental index)

**Solution:**
```bash
# Verify module exists in index
cicada index .
```

---

### MCP Server Connection Failed

**Symptoms:**
- AI assistant doesn't show CICADA tools
- Errors about MCP connection in editor logs

**Troubleshooting steps:**

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
   # Should contain absolute paths like /Users/you/project
   # Not relative paths like ./project
   ```

3. **Ensure index exists:**
   ```bash
   ls -la ~/.cicada/projects/
   # Should show directory for your project
   ```

4. **Restart editor completely** (not just reload window)

5. **Check editor MCP logs:**
   - Claude Code: Check console output
   - Cursor: Settings → MCP → View Logs
   - VS Code: Output panel → MCP

---

### PR Features Not Working

**Error:** "No PR index found" or "GitHub CLI not authenticated"

**Setup:**
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

- **Slow indexing:** First-time indexing fetches all PRs. Subsequent runs are incremental.
- **Rate limiting:** GitHub API has rate limits. Wait and retry if you hit limits.
- **Not a GitHub repository:** Ensure remote is GitHub, not GitLab/Bitbucket.

**Force rebuild:**
```bash
cicada index-pr . --clean
```

---

### Keyword Search Not Working

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

---

### Performance Issues

**Symptom:** Slow indexing or high memory usage

**Solutions:**

1. **Use fast tier if regular is too slow:**
   ```bash
   cicada index --fast .
   ```

2. **Exclude large directories:**
   Add to `.cicada/config.yaml`:
   ```yaml
   exclude:
     - deps/
     - _build/
     - node_modules/
   ```

3. **Incremental indexing:**
   CICADA automatically uses incremental indexing. Only changed files are re-parsed.

4. **Interrupt and resume:**
   Press Ctrl-C to interrupt safely. Run command again to resume.

---

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/wende/cicada.git
cd cicada

# Install dependencies using uv
uv sync

# Or using traditional venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_parser.py

# Run with coverage
pytest --cov=cicada --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=cicada --cov-report=html
open htmlcov/index.html
```

### Code Style

**Formatting:** black
```bash
black cicada tests
```

**Type Checking:** mypy (optional)
```bash
mypy cicada
```

**Linting:** flake8 (optional)
```bash
flake8 cicada
```

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure tests pass (`pytest`)
6. Format code (`black cicada tests`)
7. Commit with descriptive message
8. Push to your fork
9. Open a Pull Request

**See also:** [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Architecture

### Storage

```
~/.cicada/
└── projects/
    └── <repo_hash>/              # SHA-256 hash (16 hex chars)
        ├── index.json            # Main index
        ├── config.yaml           # Configuration
        ├── hashes.json           # File hashes for incremental updates
        └── pr_index.json         # PR data (optional)
```

### Index Structure

**index.json format:**
```json
{
  "modules": {
    "MyApp.User": {
      "file": "lib/my_app/user.ex",
      "line": 1,
      "functions": {
        "create_user/2": {
          "line": 15,
          "signature": "@spec create_user(map(), Keyword.t()) :: {:ok, User.t()} | {:error, Changeset.t()}",
          "doc": "Creates a new user...",
          "public": true
        }
      }
    }
  },
  "call_sites": {
    "MyApp.User.create_user/2": [
      {
        "file": "lib/my_app_web/controllers/user_controller.ex",
        "line": 23,
        "context": "case User.create_user(params) do"
      }
    ]
  },
  "keywords": {
    "authentication": ["MyApp.Auth", "MyApp.User.authenticate/2"],
    "api": ["MyApp.API", "MyApp.API.Client"]
  }
}
```

### Supported Elixir Constructs

**Modules:**
- `defmodule MyApp.User`
- Nested modules

**Functions:**
- `def` and `defp`
- Function signatures with guards
- Type specifications (`@spec`)
- Documentation (`@doc`, `@moduledoc`)
- Default arguments

**Calls:**
- Direct calls: `MyModule.function(args)`
- Aliased calls: `alias MyApp.User; User.function(args)`
- Piped calls: `data |> MyModule.function()`
- Kernel functions: `Enum.map/2`, `Repo.insert/2`

**Not yet supported:**
- Dynamic calls via `apply/3` or `Kernel.apply/3`
- Macro-generated functions
- Protocol implementations (partially supported)

---

## Credits

### Built With

- **[Tree-sitter](https://tree-sitter.github.io/)** - Incremental parsing system for AST extraction
- **[tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir)** - Elixir grammar for tree-sitter
- **[MCP](https://modelcontextprotocol.io/)** - Model Context Protocol for AI integration
- **[GitHub CLI](https://cli.github.com/)** - PR attribution and GitHub API access
- **[KeyBERT](https://github.com/MaartenGr/KeyBERT)** - Keyword extraction using BERT
- **[GloVe](https://nlp.stanford.edu/projects/glove/)** - Word embeddings for keyword expansion
- **[FastText](https://fasttext.cc/)** - Alternative word embeddings

### Contributors

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for a list of contributors.

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
