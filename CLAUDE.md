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
- **Tool installation:** `uv tool install git+https://github.com/wende/cicada.git@v0.X.Y`

The project includes `uv.lock` for reproducible builds and `pyproject.toml` for project configuration.

## Code Style

- Use `black` for Python code formatting
- Include type hints where appropriate
- Write tests for new features
- Keep functions focused and modular

- When searching through the Elixir codebase, use the cicada-mcp MCP server tools instead of grep/find commands for better accuracy and context.
- use make to run tests