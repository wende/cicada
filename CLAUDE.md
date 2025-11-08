# CICADA - AI Assistant Guidelines

This file contains project-specific instructions for AI assistants working on the CICADA codebase.

## Release Process

When creating a new release:

1. **Update pyproject.toml version:**
   - Update the `version = "0.1.1"` field to match the new release

2. **Commit version changes:**
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.X.Y"
   ```
   Note: The pre-commit hook will automatically update `cicada/_version_hash.py` with the current git commit hash

3. **Create and push the git tag:**
   ```bash
   git tag v0.X.Y
   git push origin v0.X.Y
   git push origin main
   ```

4. **Build and publish to PyPI:**
   ```bash
   uv build
   uv publish
   ```

5. **Test the installation:**
   ```bash
   uv tool install cicada-mcp
   cicada --version  # Should show version and commit hash
   ```

## Version Management

- Version number is stored in `pyproject.toml`
- Git tag and commit hash are stored in `cicada/_version_hash.py` (auto-updated by pre-commit hook)
- `cicada --version` or `cicada -v` displays version, tag, and commit hash
- Version format: `cicada 0.2.0 (v0.2.0-rc0/5ea1134)` - tag/hash format allows tracking RC releases
- For PyPI installs: shows the version, tag, and hash from when the package was built
- For development installs: falls back to `git describe --tags` and `git rev-parse HEAD` if needed
- Pre-commit hook automatically fetches latest tags via `git fetch --tags` to ensure accurate version info

## Project Context

- **Language Support:** Currently Elixir only. Python and TypeScript are planned.
- **Primary Installation Method:** uv tool install (recommended over Python direct install)

## Storage Structure

As of the simplified setup workflow (PR #20), Cicada uses a centralized storage structure:

- **Index Storage Location:** `~/.cicada/projects/<repo_hash>/`
  - All generated files (index.json, config.yaml, hashes.json, pr_index.json) are stored here
  - Repository hash is generated from the resolved absolute path using SHA-256 (truncated to 16 hex chars)

- **Repository Config:** Only one MCP config file is added to the user's repository:
  - `.mcp.json` (Claude Code)
  - `.cursor/mcp.json` (Cursor)
  - `.vscode/settings.json` (VS Code)

- **Storage Utilities:** `cicada/utils/storage.py` provides functions for:
  - `get_repo_hash(repo_path)` - Generate unique hash for a repository
  - `get_storage_dir(repo_path)` - Get storage directory path
  - `create_storage_dir(repo_path)` - Create storage directory
  - `get_index_path(repo_path)` - Get path to index.json
  - `get_config_path(repo_path)` - Get path to config.yaml
  - `get_hashes_path(repo_path)` - Get path to hashes.json
  - `get_pr_index_path(repo_path)` - Get path to pr_index.json

- **Backward Compatibility:** The MCP server (`cicada/mcp_server.py`) supports both:
  - New structure: `~/.cicada/projects/<hash>/`
  - Old structure: `.cicada/` in project root

### Testing Storage-Related Code

When adding or modifying storage-related functionality:

1. **Write comprehensive tests** covering:
   - Hash generation consistency
   - Path resolution for various input types (str, Path, relative, absolute)
   - Directory creation with proper permissions
   - Edge cases (non-existent paths, unicode, spaces in paths)

2. **Test backward compatibility:**
   - Ensure MCP server can still load from old `.cicada/` structure
   - Verify graceful fallback when new structure is unavailable

3. **Error handling:**
   - Test permission errors, disk full scenarios
   - Verify appropriate logging for debugging

## Development Environment

This project uses **uv** as the primary Python package manager and build tool. When working on this project:

- **Always use `uv` commands** instead of `pip` or other package managers
- **Install dependencies:** `uv sync` (equivalent to `pip install -r requirements.txt`)
- **Add new dependencies:** `uv add <package-name>`
- **Run commands:** `uv run <command>` (e.g., `uv run python -m pytest`)
- **Install the project:** `uv pip install -e .` for development installation
- **Tool installation:** `uv tool install cicada-mcp`

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
  - PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers. Supports wildcards (`MyApp.*`) and OR patterns (`MyApp.User|MyApp.Post`). `mcp__cicada__search_module`
  - PREFERRED for Elixir: Find function definitions and call sites across the codebase. Supports wildcards (`create*`) and OR patterns (`create*|update*`). `mcp__cicada__search_function`
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


