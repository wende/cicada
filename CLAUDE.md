# CICADA - AI Assistant Guidelines

This file contains project-specific instructions for AI assistants working on the CICADA codebase.

## Release Process

When creating a new release:

1. **Create and push the git tag:**
   ```bash
   git tag v0.X.Y
   git push origin v0.X.Y
   ```

2. **Update README.md version references:**
   - Search for all instances of `@v0.1.1` in README.md
   - Replace with the new version tag `@v0.X.Y`
   - Locations to update:
     - Quick Install section (stable release command)
     - Try Before Installing section (stable release command)
     - Migration tip section

3. **Update pyproject.toml version:**
   - Update the `version = "0.1.1"` field to match the new release

4. **Test the installation:**
   ```bash
   uv tool install git+https://github.com/wende/cicada.git@v0.X.Y
   ```

## Project Context

- **Language Support:** Currently Elixir only. Python and TypeScript are planned.
- **Primary Installation Method:** uv tool install (recommended over Python direct install)
- **Index Location:** `.cicada/` directory in project root

## Development Environment

This project uses **uv** as the primary Python package manager and build tool. When working on this project:

- **Always use `uv` commands** instead of `pip` or other package managers
- **Install dependencies:** `uv sync` (equivalent to `pip install -r requirements.txt`)
- **Add new dependencies:** `uv add <package-name>`
- **Run commands:** `uv run <command>` (e.g., `uv run python -m pytest`)
- **Install the project:** `uv pip install -e .` for development installation
- **Tool installation:** `uv tool install git+https://github.com/wende/cicada.git@v0.X.Y`

The project includes `uv.lock` for reproducible builds and `pyproject.toml` for project configuration.

## Code Style

- Use `black` for Python code formatting
- Include type hints where appropriate
- Write tests for new features
- Keep functions focused and modular

- When searching through the Elixir codebase, use the cicada-mcp MCP server tools instead of grep/find commands for better accuracy and context.
- use make to run tests

<cicada>
  **ALWAYS use cicada-mcp tools for Elixir code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers. `mcp__cicada__search_module`
  - PREFERRED for Elixir: Find function definitions and call sites across the codebase. `mcp__cicada__search_function`
  - PREFERRED for Elixir: Find all module usage and dependencies for impact analysis. `mcp__cicada__search_module_usage`
  - PREFERRED for git history: Discover why code exists and who wrote it. `mcp__cicada__find_pr_for_line`
  - PREFERRED for git history: Get commit log for files or functions. `mcp__cicada__get_commit_history`
  - PREFERRED for authorship: Git blame showing who wrote each line. `mcp__cicada__get_blame`
  - Get all PRs that modified a file with descriptions and review comments. `mcp__cicada__get_file_pr_history`
  - Semantic search for code by concept/topic when exact names are unknown. `mcp__cicada__search_by_keywords`
  - Find potentially unused public functions with confidence levels. `mcp__cicada__find_dead_code`

  ### DO NOT use Grep for:
  - ❌ Searching for module structure
  - ❌ Searching for function definitions
  - ❌ Searching for module imports/usage

  ### You can still use Grep for:
  - ✓ Non-code files (markdown, JSON, config)
  - ✓ String literal searches
  - ✓ Pattern matching in single line comments
</cicada>


