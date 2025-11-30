# Storage Structure and Configuration

## Storage Structure

As of the simplified setup workflow (PR #20), Cicada uses a centralized storage structure:

- **Index Storage Location:** `~/.cicada/projects/<repo_hash>/`
  - All generated files (index.json, config.yaml, hashes.json, pr_index.json) are stored here
  - Repository hash is generated from the resolved absolute path using SHA-256 (truncated to 16 hex chars)
  - **Discovering the storage directory:** Use `cicada dir` in your repository
    ```bash
    cd /path/to/your/repo
    cicada dir
    # Output: Repository hash: a1b2c3d4e5f6a7b8
    #         Storage dir: /Users/username/.cicada/projects/a1b2c3d4e5f6a7b8/
    ```

- **Repository Config:** Only one MCP config file is added to the user's repository:
  - `.mcp.json` (Claude Code)
  - `.cursor/mcp.json` (Cursor)
  - `.vscode/settings.json` (VS Code)
  - `.gemini/settings.json` (Gemini CLI)
  - `.codex/mcp.json` (Codex)
  - `.opencode.json` (OpenCode)

- **Storage Utilities:** `cicada/utils/storage.py` provides functions for:
  - `get_repo_hash(repo_path)` - Generate unique hash for a repository
  - `get_storage_dir(repo_path)` - Get storage directory path
  - `create_storage_dir(repo_path)` - Create storage directory
  - `get_index_path(repo_path)` - Get path to index.json
  - `get_config_path(repo_path)` - Get path to config.yaml
  - `get_hashes_path(repo_path)` - Get path to hashes.json
  - `get_pr_index_path(repo_path)` - Get path to pr_index.json

## Environment Variables

The MCP server uses environment variables to locate configuration files:

- **CICADA_CONFIG_DIR** (Required by MCP config files)
  - Points directly to the storage directory: `~/.cicada/projects/<hash>/`
  - Set in `.mcp.json`, `.cursor/mcp.json`, `.vscode/settings.json`, etc.
  - Primary mechanism for config file resolution
  - Example: `/Users/username/.cicada/projects/a1b2c3d4e5f6g7h8/`

- **WORKSPACE_FOLDER_PATHS** (Optional, Cursor-specific)
  - Set automatically by Cursor editor for workspace folders
  - Used as fallback when CICADA_CONFIG_DIR is not set
  - Enables zero-config operation in Cursor
  - The MCP server reads this but does not set it

- **TOKENIZERS_PARALLELISM** (Internal, technical)
  - Set to "false" in `cicada/extractors/keybert.py`
  - Prevents fork warnings from ML libraries
  - Not related to CICADA's config system

### Configuration Resolution Order

When the MCP server starts, it resolves the config file location in this order:

1. **CICADA_CONFIG_DIR** → Direct path to `<dir>/config.yaml`
2. **WORKSPACE_FOLDER_PATHS** → Calculate storage dir from repo path → `config.yaml`
3. **Current working directory** → Calculate storage dir from cwd → `config.yaml`

### Example MCP Configuration

```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp"],
      "env": {
        "CICADA_CONFIG_DIR": "/Users/username/.cicada/projects/a1b2c3d4e5f6g7h8/"
      }
    }
  }
}
```

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
