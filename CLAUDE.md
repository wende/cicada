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
   Note: CI/CD will automatically build and publish to PyPI. The "latest" tag is a moving tag that always points to the latest vX.Y.Z release.

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

- **Language Support:**
  - **Elixir**: Full support with tree-sitter AST parsing and incremental indexing
  - **Python (MVP)**: SCIP-based indexing powered by Pyright (requires Node.js/npm)
  - **TypeScript**: Planned for future releases
- **Primary Installation Method:** uv tool install (recommended over Python direct install)

## Testing & Dogfooding

**IMPORTANT: Cicada is an MCP tool for code analysis - USE IT ON ITSELF!**

When developing cicada features:

1. **Always use cicada MCP tools to explore the cicada codebase:**
   - Use `mcp__cicada__search_module` to view module APIs
   - Use `mcp__cicada__search_function` to find function definitions and call sites
   - Use `mcp__cicada__search_by_keywords` for semantic search
   - Use `mcp__cicada__find_pr_for_line` to understand code history

2. **Reindex after making changes:**
   ```bash
   cicada clean -f
   cicada index --nlp  # or --rag
   ```

3. **Report bugs you discover while dogfooding:**
   - If a search returns unexpected results, investigate why
   - If module views show 0 functions when they shouldn't, that's a bug
   - If keyword search fails, that needs fixing
   - Document issues you find - we're eating our own dog food!

4. **Test the feature you're developing:**
   - After implementing a feature, use it on the cicada codebase
   - Verify it works correctly in a real-world scenario
   - Fix any issues before considering the work complete

## Project Structure

Cicada follows a language-agnostic architecture with clear separation between universal and language-specific code:

### Source Code Organization

```
cicada/
├── languages/           # Language-specific implementations
│   ├── scip/           # Universal SCIP adapter (language-agnostic)
│   │   ├── converter.py    # SCIP → Cicada format converter
│   │   ├── reader.py       # SCIP protobuf file reader
│   │   └── scip_pb2.py     # Protocol Buffer definitions
│   ├── python/         # Python-specific implementation
│   │   ├── indexer.py      # Python indexer using scip-python
│   │   └── scip_installer.py  # scip-python installer utilities
│   └── elixir/         # Elixir-specific implementation
│       ├── indexer.py      # Elixir indexer using tree-sitter
│       ├── parser.py       # Tree-sitter AST parser
│       └── extractors/     # AST node extractors
│           ├── module.py   # Module extraction
│           ├── function.py # Function extraction
│           ├── call.py     # Call site extraction
│           └── ...
└── ...
```

### Test Organization

Tests mirror the source structure for clarity:

```
tests/
├── languages/          # Language-specific tests
│   ├── python/        # Python language tests
│   │   └── test_python_support.py
│   ├── elixir/        # Elixir language tests
│   │   ├── test_indexer.py
│   │   ├── test_parser.py
│   │   └── test_call_extractor.py
│   └── scip/          # Universal SCIP tests (if needed)
├── fixtures/          # Shared test fixtures
│   ├── sample_python/ # Python test code
│   └── sample.ex      # Elixir test code
└── conftest.py        # Shared test utilities
```

### Design Principles

1. **Language-Agnostic Core**: The SCIP adapter in `cicada/languages/scip/` is completely language-agnostic and works with any SCIP-compatible indexer (Python, TypeScript, Java, Rust, Go, etc.).

2. **Language-Specific Implementations**: Each language has its own directory under `cicada/languages/` containing:
   - Indexer implementation
   - Language-specific utilities
   - Parser/extractor logic (if not using SCIP)

3. **Test Fixture Helpers**: Use the `fixtures_dir` pytest fixture to access test fixtures:
   ```python
   def test_something(fixtures_dir):
       sample_file = fixtures_dir / "sample.ex"
   ```
   This avoids hardcoding relative paths like `Path(__file__).parent.parent.parent`.

4. **Adding New Languages**:
   - For SCIP-supported languages: Create `cicada/languages/<lang>/indexer.py` that uses the universal SCIP adapter
   - For non-SCIP languages: Create full parser/extractor implementation like Elixir
   - Add corresponding test directory in `tests/languages/<lang>/`

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

### Testing Storage-Related Code

When adding or modifying storage-related functionality:

1. **Write comprehensive tests** covering:
   - Hash generation consistency
   - Path resolution for various input types (str, Path, relative, absolute)
   - Directory creation with proper permissions
   - Edge cases (non-existent paths, unicode, spaces in paths)

2. **Error handling:**
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

## Documentation

- All project documentation should be written in Markdown format
- Documentation files are stored in the `docs/` directory
- Keep documentation up-to-date with code changes
- Include examples and use cases where appropriate

## Code Style

- Use `black` for Python code formatting
- Include type hints where appropriate
- Write tests for new features
- Keep functions focused and modular

- When searching through the Elixir codebase, use the cicada-mcp MCP server tools instead of grep/find commands for better accuracy and context.
- use make to run tests

<cicada>
  **ALWAYS use cicada-mcp tools for Elixir/Python code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - PREFERRED for Elixir/Python: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers. `mcp__cicada__search_module`
  - PREFERRED for Elixir/Python: Find function definitions and call sites across the codebase. `mcp__cicada__search_function`
  - PREFERRED for Elixir: Find all module usage and dependencies for impact analysis. `mcp__cicada__search_module_usage` (Python MVP: limited support)
  - PREFERRED for git history: Discover why code exists and who wrote it. `mcp__cicada__find_pr_for_line`
  - PREFERRED for git history: Get commit log for files or functions. `mcp__cicada__get_commit_history`
  - PREFERRED for authorship: Git blame showing who wrote each line. `mcp__cicada__get_blame`
  - Get all PRs that modified a file with descriptions and review comments. `mcp__cicada__get_file_pr_history`
  - Semantic search for code by concept/topic when exact names are unknown. `mcp__cicada__search_by_keywords`
  - Find potentially unused public functions with confidence levels. `mcp__cicada__find_dead_code`

  ### DO NOT use Grep for:
  - ❌ Searching for module structure (Elixir/Python)
  - ❌ Searching for function definitions (Elixir/Python)
  - ❌ Searching for module imports/usage (Elixir/Python)

  ### You can still use Grep for:
  - ✓ Non-code files (markdown, JSON, config)
  - ✓ String literal searches
  - ✓ Pattern matching in single line comments
</cicada>


