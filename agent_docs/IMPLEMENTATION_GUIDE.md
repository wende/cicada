# Cicada `status` Command Implementation Guide

## Overview

This guide provides comprehensive information for implementing a new `cicada status` command that reuses logic from `cicada clean` to validate and report on the state of Cicada configuration and indexes.

---

## 1. CLI Commands Structure

### Entry Point Chain
**File**: `/Users/wende/projects/cicada/cicada/cli.py`

```python
from cicada.entry_utils import run_cli

def main():
    """Main entry point for the unified cicada CLI."""
    run_cli(
        prog_name="cicada",
        version_prog_name="cicada",
        default_on_unknown="install",
        default_on_none="install",
    )
```

### Argument Parser
**File**: `/Users/wende/projects/cicada/cicada/commands.py`

The `get_argument_parser()` function (lines 89-530) defines all subcommands:

```python
KNOWN_SUBCOMMANDS: tuple[str, ...] = (
    "install", "server", "claude", "cursor", "vs", "gemini", "codex",
    "watch", "index", "index-pr", "find-dead-code", "clean", "dir",
)
```

**To add `status` command**:
1. Add `"status"` to `KNOWN_SUBCOMMANDS` tuple
2. Add a status_parser definition similar to `clean_parser`:

```python
status_parser = subparsers.add_parser(
    "status",
    help="Status Cicada configuration and index status",
    description="Verify that all required Cicada files exist and are valid",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  cicada status                   # Check current repository
  cicada status --verbose         # Show detailed information
  cicada status --json           # Output as JSON
    """,
)
status_parser.add_argument(
    "--verbose",
    action="store_true",
    help="Show detailed information about each file",
)
status_parser.add_argument(
    "--json",
    action="store_true",
    help="Output results as JSON",
)
```

### Command Router
**File**: `/Users/wende/projects/cicada/cicada/commands.py` (lines 533-566)

The `handle_command()` function routes commands to handlers:

```python
command_handlers = {
    "install": handle_install,
    "server": handle_server,
    "clean": handle_clean,
    # Add this:
    "status": handle_check,
}
```

---

## 2. Storage and File Locations

### Storage Structure
**File**: `/Users/wende/projects/cicada/cicada/utils/storage.py`

The new centralized storage structure uses a hashed repository path:

```
~/.cicada/projects/<repo_hash>/
├── index.json           # Main code index
├── hashes.json          # File hashes for change detection
├── pr_index.json        # GitHub PR index (optional)
└── config.yaml          # Configuration
```

**Key Functions**:

```python
# Get repository hash (SHA256 of resolved absolute path, first 16 chars)
get_repo_hash(repo_path: str | Path) -> str

# Get storage directory: ~/.cicada/projects/<repo_hash>/
get_storage_dir(repo_path: str | Path) -> Path

# Get specific file paths
get_index_path(repo_path: str | Path) -> Path          # index.json
get_config_path(repo_path: str | Path) -> Path         # config.yaml
get_hashes_path(repo_path: str | Path) -> Path         # hashes.json
get_pr_index_path(repo_path: str | Path) -> Path       # pr_index.json
```

### Example Usage
```python
from pathlib import Path
from cicada.utils import get_storage_dir, get_index_path, get_config_path

repo_path = Path.cwd()
storage_dir = get_storage_dir(repo_path)
index_path = get_index_path(repo_path)
config_path = get_config_path(repo_path)
```

### Backward Compatibility
The `clean.py` checks for old `.cicada` directory in repo root for backward compatibility:
```python
old_cicada_dir = repo_path / ".cicada"
if old_cicada_dir.exists():
    # Handle legacy structure
```

---

## 3. Index Files Structure

### Main Index (index.json)
**Location**: `~/.cicada/projects/<repo_hash>/index.json`

```json
{
  "modules": {
    "ModuleName": {
      "file": "lib/path/to/file.ex",
      "line": 1,
      "moduledoc": "Documentation...",
      "functions": [
        {
          "name": "function_name",
          "arity": 2,
          "full_name": "function_name/2",
          "line": 10,
          "type": "def",  // "def" or "defp"
          "signature": "def function_name(arg1, arg2)",
          "doc": "Documentation...",
          "keywords": {
            "keyword1": 4.5,
            "keyword2": 2.3
          }
        }
      ]
    }
  },
  "metadata": {
    "indexed_at": "2025-11-11T17:43:33.826829",
    "total_modules": 37,
    "total_functions": 317,
    "public_functions": 250,
    "private_functions": 67,
    "repo_path": "/Users/wende/projects/cicada",
    "cicada_version": "0.3.1 (v0.3.1rc2/9c57cec)"
  }
}
```

### Config (config.yaml)
**Location**: `~/.cicada/projects/<repo_hash>/config.yaml`

Contains tier/model information:

```yaml
repository:
  path: /path/to/repo

storage:
  index_path: ~/.cicada/projects/<hash>/index.json

keyword_extraction:
  method: regular  # "regular" or "bert"

keyword_expansion:
  method: glove    # "lemmi", "glove", or "fasttext"
```

**Tier Mapping** (`/Users/wende/projects/cicada/cicada/tier.py`):
```python
TIER_METHODS = {
    "fast": ("regular", "lemmi"),        # lightweight
    "regular": ("bert", "glove"),        # default (128MB)
    "max": ("bert", "fasttext"),         # large (958MB+)
}
```

### PR Index (pr_index.json) [Optional]
**Location**: `~/.cicada/projects/<repo_hash>/pr_index.json`

```json
{
  "metadata": {
    "repo_owner": "anthropics",
    "repo_name": "cicada",
    "last_indexed_at": "2025-11-11T12:00:00.000000",
    "total_prs": 125,
    "total_commits_mapped": 450,
    "total_files": 87,
    "total_comments": 340,
    "last_pr_number": 125
  },
  "prs": {
    "125": {
      "number": 125,
      "title": "PR title",
      "commits": ["sha1", "sha2"],
      "files_changed": ["lib/file.ex"]
    }
  },
  "commit_to_pr": {
    "sha1": 125
  },
  "file_to_prs": {
    "lib/file.ex": [125, 120, 115]
  }
}
```

### Hashes File (hashes.json)
**Location**: `~/.cicada/projects/<repo_hash>/hashes.json`

Tracks file hashes for incremental indexing (JSON object mapping file paths to their hashes).

---

## 4. MCP Configuration Files

MCP configs are stored in the repository root, not in ~/.cicada:

### Claude Code
**File**: `.mcp.json` in repository root

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

### Cursor
**File**: `.cursor/mcp.json` in repository root

Same structure with `mcpServers` key.

### VS Code
**File**: `.vscode/settings.json` in repository root

```json
{
  "mcp.servers": {
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

### Gemini CLI
**File**: `.gemini/mcp.json` in repository root

**Codex**
**File**: `.codex/mcp.json` in repository root

---

## 5. How `clean` Command Works (Reuse This Logic)

**File**: `/Users/wende/projects/cicada/cicada/clean.py`

### Main Functions

#### `clean_repository(repo_path: Path, force: bool = False) -> None`
Removes all Cicada configuration for a single repository.

**What it checks**:
1. Storage directory (`~/.cicada/projects/<repo_hash>/`) - exists? is directory?
2. Legacy `.cicada/` directory (backward compatibility)
3. MCP config files (`.mcp.json`, `.cursor/mcp.json`, `.vscode/settings.json`)
4. Verifies cicada entry exists in each MCP config before removal

**Code structure** (lines 183-302):
```python
def clean_repository(repo_path: Path, force: bool = False) -> None:
    items_to_remove = []
    
    # Check storage directory
    storage_dir = get_storage_dir(repo_path)
    if storage_dir.exists():
        items_to_remove.append(CleanItem("Storage directory", storage_dir))
    
    # Check legacy .cicada directory
    old_cicada_dir = repo_path / ".cicada"
    if old_cicada_dir.exists():
        items_to_remove.append(CleanItem("Legacy .cicada directory", old_cicada_dir))
    
    # Check MCP configs
    mcp_configs = [
        (repo_path / ".mcp.json", "Claude Code config"),
        (repo_path / ".cursor" / "mcp.json", "Cursor config"),
        (repo_path / ".vscode" / "settings.json", "VS Code config"),
    ]
    
    for config_path, desc in mcp_configs:
        if config_path.exists():
            # Verify cicada entry exists before adding to removal list
            try:
                with open(config_path) as f:
                    config = json.load(f)
                config_key = "mcpServers" if ".vscode" not in str(config_path) else "mcp.servers"
                if config_key in config and "cicada" in config[config_key]:
                    items_to_remove.append(CleanItem(desc, config_path, is_mcp_config=True))
            except:
                pass
    
    # Display what will be removed
    print("The following items will be removed:")
    for item in items_to_remove:
        if item.is_mcp_config:
            print(f"  • {item.description}: Remove 'cicada' entry from {item.path}")
        else:
            print(f"  • {item.description}: {item.path}")
    
    # Confirmation + removal
```

#### `clean_index_only(repo_path: Path) -> None`
Removes only main index files: `index.json` and `hashes.json`

#### `clean_pr_index_only(repo_path: Path) -> None`
Removes only `pr_index.json`

#### `clean_all_projects(force: bool = False) -> None`
Removes all project storage directories: `~/.cicada/projects/*/`

#### `remove_mcp_config_entry(config_path: Path, server_key: str = "cicada") -> bool`
Removes cicada entry from a single MCP config file without deleting the file itself.

---

## 6. Index Loading and Validation

**File**: `/Users/wende/projects/cicada/cicada/utils/index_utils.py`

### Load Index
```python
from cicada.utils import load_index

index = load_index(
    index_path="/path/to/index.json",
    verbose=True,
    raise_on_error=False
)

# Returns dict[str, Any] | None
# Returns None if file doesn't exist or JSON is invalid
```

### Validate Index Structure
```python
from cicada.utils import validate_index_structure

valid, error_message = validate_index_structure(
    index,
    required_keys=["modules", "metadata"]
)

if not valid:
    print(f"Invalid index: {error_message}")
```

### Get Index Statistics
```python
from cicada.utils.index_utils import get_index_stats

stats = get_index_stats(index)
# Returns: {
#   "total_modules": int,
#   "total_functions": int,
#   "public_functions": int,
#   "private_functions": int,
# }
```

---

## 7. Detecting Tier/Model Information

The tier information is **not stored in index.json** but in **config.yaml**:

```python
import yaml
from pathlib import Path
from cicada.utils import get_config_path

repo_path = Path.cwd()
config_path = get_config_path(repo_path)

if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    extraction_method = config.get("keyword_extraction", {}).get("method")  # "regular" or "bert"
    expansion_method = config.get("keyword_expansion", {}).get("method")    # "lemmi", "glove", or "fasttext"
    
    # Convert to tier
    tier = None
    if extraction_method == "regular" and expansion_method == "lemmi":
        tier = "fast"
    elif extraction_method == "bert" and expansion_method == "glove":
        tier = "regular"
    elif extraction_method == "bert" and expansion_method == "fasttext":
        tier = "max"
```

### Index Metadata
The index itself contains:
- `indexed_at`: ISO format timestamp
- `total_modules`: Module count
- `total_functions`: Function count
- `public_functions` / `private_functions`: Breakdown
- `repo_path`: Repository path that was indexed
- `cicada_version`: Version string when index was created (e.g., "0.3.1 (v0.3.1rc2/9c57cec)")

---

## 8. Implementation Pattern for `cicada status` Command

### Function Signature
```python
def handle_check(args) -> None:
    """Status Cicada configuration and index status.
    
    Args:
        args: Parsed command-line arguments
    """
```

### Command Handler Location
Add to `/Users/wende/projects/cicada/cicada/commands.py`:

1. Add function `handle_check()` after `handle_clean()` (around line 950)
2. Add to `command_handlers` dict in `handle_command()` (line 554)
3. Add "status" to `KNOWN_SUBCOMMANDS` tuple (line 36)

### Basic Implementation Skeleton
```python
def handle_check(args) -> None:
    """Status Cicada configuration and index status for current repository."""
    from cicada.utils import (
        get_storage_dir,
        get_index_path,
        get_config_path,
        get_hashes_path,
        get_pr_index_path,
        load_index,
        validate_index_structure,
    )
    from cicada.utils.index_utils import get_index_stats
    import json
    import yaml
    from pathlib import Path
    
    repo_path = Path.cwd().resolve()
    verbose = getattr(args, "verbose", False)
    use_json = getattr(args, "json", False)
    
    # 1. Check storage directory
    storage_dir = get_storage_dir(repo_path)
    storage_exists = storage_dir.exists()
    
    # 2. Check config
    config_path = get_config_path(repo_path)
    config_exists = config_path.exists()
    config_data = None
    tier = None
    if config_exists:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        # Extract tier info
        extraction = config_data.get("keyword_extraction", {}).get("method")
        expansion = config_data.get("keyword_expansion", {}).get("method")
        # Map to tier name
    
    # 3. Check index files
    index_path = get_index_path(repo_path)
    index_exists = index_path.exists()
    index_valid = False
    index_stats = None
    if index_exists:
        index = load_index(index_path, verbose=False)
        if index:
            is_valid, error = validate_index_structure(index)
            index_valid = is_valid
            if is_valid:
                index_stats = get_index_stats(index)
    
    # 4. Check hashes file
    hashes_path = get_hashes_path(repo_path)
    hashes_exists = hashes_path.exists()
    
    # 5. Check PR index (optional)
    pr_index_path = get_pr_index_path(repo_path)
    pr_index_exists = pr_index_path.exists()
    
    # 6. Check MCP configs
    mcp_configs = {
        "claude": repo_path / ".mcp.json",
        "cursor": repo_path / ".cursor" / "mcp.json",
        "vscode": repo_path / ".vscode" / "settings.json",
    }
    mcp_status = {}
    for editor, path in mcp_configs.items():
        if path.exists():
            try:
                with open(path) as f:
                    config = json.load(f)
                key = "mcpServers" if editor != "vscode" else "mcp.servers"
                has_cicada = key in config and "cicada" in config[key]
                mcp_status[editor] = "configured" if has_cicada else "present_without_cicada"
            except:
                mcp_status[editor] = "error"
        else:
            mcp_status[editor] = "not_configured"
    
    # 7. Format and display results
    if use_json:
        # Output JSON format
        results = {
            "repository": str(repo_path),
            "storage": {
                "directory": str(storage_dir),
                "exists": storage_exists,
            },
            "configuration": {
                "config_file": str(config_path),
                "exists": config_exists,
                "tier": tier,
            },
            "index": {
                "file": str(index_path),
                "exists": index_exists,
                "valid": index_valid,
                "stats": index_stats,
            },
            "hashes": {
                "file": str(hashes_path),
                "exists": hashes_exists,
            },
            "pr_index": {
                "file": str(pr_index_path),
                "exists": pr_index_exists,
            },
            "mcp_configs": mcp_status,
        }
        print(json.dumps(results, indent=2))
    else:
        # Output human-readable format
        print("=" * 60)
        print("Cicada Check")
        print("=" * 60)
        print(f"\nRepository: {repo_path}")
        # ... print details
```

### Output Examples

**Human-readable**:
```
============================================================
Cicada Check
============================================================

Repository: /Users/wende/projects/cicada

Storage Directory: ~/.cicada/projects/a1b2c3d4e5f6g7h8/
  Status: ✓ exists

Configuration (config.yaml):
  Status: ✓ exists
  Tier: regular (bert extraction + glove expansion)
  
Index (index.json):
  Status: ✓ exists and valid
  Modules: 37
  Functions: 317 (250 public, 67 private)
  Last indexed: 2025-11-11T17:43:33.826829
  Version: 0.3.1 (v0.3.1rc2/9c57cec)

Hashes (hashes.json):
  Status: ✓ exists
  
PR Index (pr_index.json):
  Status: ✗ not created
  
MCP Configurations:
  Claude Code (.mcp.json): ✓ configured
  Cursor (.cursor/mcp.json): ✗ not configured
  VS Code (.vscode/settings.json): ✗ not configured

Overall Status: ✓ Ready to use
```

**JSON output** (with `--json` flag):
```json
{
  "repository": "/Users/wende/projects/cicada",
  "storage": {
    "directory": "/Users/wende/.cicada/projects/a1b2c3d4e5f6g7h8",
    "exists": true
  },
  "configuration": {
    "config_file": "/Users/wende/.cicada/projects/a1b2c3d4e5f6g7h8/config.yaml",
    "exists": true,
    "tier": "regular"
  },
  "index": {
    "file": "/Users/wende/.cicada/projects/a1b2c3d4e5f6g7h8/index.json",
    "exists": true,
    "valid": true,
    "stats": {
      "total_modules": 37,
      "total_functions": 317,
      "public_functions": 250,
      "private_functions": 67
    }
  },
  "hashes": {
    "file": "/Users/wende/.cicada/projects/a1b2c3d4e5f6g7h8/hashes.json",
    "exists": true
  },
  "pr_index": {
    "file": "/Users/wende/.cicada/projects/a1b2c3d4e5f6g7h8/pr_index.json",
    "exists": false
  },
  "mcp_configs": {
    "claude": "configured",
    "cursor": "not_configured",
    "vscode": "not_configured"
  }
}
```

---

## 9. Key Files Reference

| File | Purpose | Location |
|------|---------|----------|
| CLI Entry | Main entry point | `/Users/wende/projects/cicada/cicada/cli.py` |
| Command Router | Argument parser + handlers | `/Users/wende/projects/cicada/cicada/commands.py` |
| Storage Utils | Path resolution | `/Users/wende/projects/cicada/cicada/utils/storage.py` |
| Index Utils | Index loading/validation | `/Users/wende/projects/cicada/cicada/utils/index_utils.py` |
| Clean Command | Reference implementation | `/Users/wende/projects/cicada/cicada/clean.py` |
| Clean Tests | Test patterns | `/Users/wende/projects/cicada/tests/setup/test_clean.py` |
| Tier Module | Tier configuration | `/Users/wende/projects/cicada/cicada/tier.py` |
| Utils Init | Exported functions | `/Users/wende/projects/cicada/cicada/utils/__init__.py` |

---

## 10. Testing Guidelines

Pattern from `/Users/wende/projects/cicada/tests/setup/test_clean.py`:

```python
def test_check_with_complete_setup(tmp_path):
    """Test status command with all files present"""
    # 1. Create test fixtures
    # 2. Call check function
    # 3. Assert output/results

def test_check_with_missing_config(tmp_path):
    """Test status command when config.yaml missing"""
    # Should report as missing/warning

def test_check_with_invalid_index(tmp_path):
    """Test status command with corrupted index.json"""
    # Should report as invalid

def test_check_json_output(tmp_path):
    """Test JSON output format"""
    # Should parse as valid JSON
```

---

## Summary

To implement `cicada status`:

1. **Add command parser** in `commands.py` around line 518
2. **Add command handler** in `commands.py` after line 949
3. **Add to router** in `handle_command()` dict (line 554)
4. **Add to known subcommands** (line 36)
5. **Reuse logic from `clean.py`** for file existence checks
6. **Use `index_utils`** to validate and load index
7. **Use `storage.py`** for path resolution
8. **Use `tier.py` and config.yaml** to detect tier/models
9. **Support `--verbose`** and `--json` output formats
10. **Write comprehensive tests** in `tests/setup/test_check.py`
