# Cicada `status` Command - Quick Start Guide

## Overview
You now have comprehensive documentation for implementing `cicada status` command that validates Cicada configuration and indexes for a repository.

## Documentation Files

1. **IMPLEMENTATION_GUIDE.md** (729 lines) - Complete implementation guide with:
   - CLI command structure and how to register the command
   - Storage location details and file paths
   - Index file structure (index.json, config.yaml, pr_index.json)
   - MCP configuration file formats
   - How the clean command works (reuse logic pattern)
   - Index loading and validation utilities
   - How to detect tier/models from config
   - Full implementation skeleton for handle_check()
   - Output format examples (human-readable and JSON)

2. **ARCHITECTURE.md** (299 lines) - Visual architecture diagrams showing:
   - CLI command flow
   - Storage architecture (new centralized + legacy)
   - Data structures (index.json, config.yaml hierarchies)
   - MCP config file layouts
   - Data flow for `cicada status`
   - Utility function maps
   - Module dependencies
   - File checklist
   - Error handling scenarios

## Key Implementation Points

### 1. Register the Command
**File**: `/Users/wende/projects/cicada/cicada/commands.py`

Add to line 36:
```python
KNOWN_SUBCOMMANDS: tuple[str, ...] = (
    "install", "server", ..., "clean", "status",  # ← Add "status"
)
```

Add after line 518:
```python
status_parser = subparsers.add_parser("status", ...)
status_parser.add_argument("--verbose", ...)
status_parser.add_argument("--json", ...)
```

Add to handler dict (line 554):
```python
command_handlers = {
    ...
    "status": handle_check,  # ← Add this
}
```

### 2. Implement the Handler
**File**: `/Users/wende/projects/cicada/cicada/commands.py`

Add function after handle_clean() (around line 950):
```python
def handle_check(args) -> None:
    """Check Cicada configuration and index status."""
    from cicada.utils import (
        get_storage_dir, get_index_path, get_config_path,
        get_hashes_path, get_pr_index_path, load_index,
        validate_index_structure,
    )
    from cicada.utils.index_utils import get_index_stats
    import json, yaml
    from pathlib import Path
    
    repo_path = Path.cwd().resolve()
    verbose = getattr(args, "verbose", False)
    use_json = getattr(args, "json", False)
    
    # Implementation code here...
    # See IMPLEMENTATION_GUIDE.md section 8 for full skeleton
```

### 3. Storage Utilities (Already Available)
**File**: `/Users/wende/projects/cicada/cicada/utils/storage.py`

Use these functions to resolve paths:
```python
from cicada.utils import (
    get_repo_hash(repo_path) -> str               # SHA256[:16]
    get_storage_dir(repo_path) -> Path            # ~/.cicada/projects/<hash>/
    get_index_path(repo_path) -> Path             # storage/index.json
    get_config_path(repo_path) -> Path            # storage/config.yaml
    get_hashes_path(repo_path) -> Path            # storage/hashes.json
    get_pr_index_path(repo_path) -> Path          # storage/pr_index.json
)
```

### 4. Index Utilities (Already Available)
**File**: `/Users/wende/projects/cicada/cicada/utils/index_utils.py`

Use these for validation:
```python
from cicada.utils import (
    load_index(path, verbose=False) -> dict | None
    validate_index_structure(index) -> (bool, error_msg)
)
from cicada.utils.index_utils import get_index_stats(index) -> dict
```

### 5. What `cicada status` Should Check

**Storage Directory**:
- Path: `~/.cicada/projects/<repo_hash>/`
- Checked by: `get_storage_dir(repo_path).exists()`

**Configuration File**:
- Path: `~/.cicada/projects/<repo_hash>/config.yaml`
- Contains: `keyword_extraction.method` and `keyword_expansion.method`
- Used to determine tier: fast/regular/max

**Index Files**:
- Main: `index.json` - Load and validate structure
- Hashes: `hashes.json` - File change tracking
- PR Index: `pr_index.json` - Optional GitHub history

**MCP Configuration Files** (in repo root):
- `.mcp.json` - Claude Code
- `.cursor/mcp.json` - Cursor
- `.vscode/settings.json` - VS Code
- Check for "cicada" entry in config

**Tier Detection**:
```python
import yaml
config = yaml.safe_load(open(config_path))
extraction = config.get("keyword_extraction", {}).get("method")  # "regular" or "bert"
expansion = config.get("keyword_expansion", {}).get("method")    # "lemmi", "glove", "fasttext"
# Map to tier based on combinations
```

### 6. Output Formats

**Default (human-readable)**:
```
============================================================
Cicada Status
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
  Version: 0.3.1 (v0.3.1rc2/9c57cec)

Overall Status: ✓ Ready to use
```

**With --json flag**:
```json
{
  "repository": "/Users/wende/projects/cicada",
  "storage": {"exists": true, "directory": "..."},
  "configuration": {"exists": true, "tier": "regular"},
  "index": {"exists": true, "valid": true, "stats": {...}},
  "mcp_configs": {"claude": "configured", "cursor": "not_configured"}
}
```

## Testing Pattern

Create `/Users/wende/projects/cicada/tests/setup/test_status.py`:

```python
import pytest
from cicada.commands import handle_check

class TestStatus:
    def test_status_complete_setup(self, tmp_path):
        """Test status with all files present"""
        # Create fixtures, call handle_check, assert results

    def test_status_missing_index(self, tmp_path):
        """Test status when index missing"""
        # Should report as missing

    def test_status_json_output(self, capsys):
        """Test JSON output format"""
        # Should be valid JSON
```

Reference pattern: `/Users/wende/projects/cicada/tests/setup/test_clean.py`

## File Locations Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| CLI Entry | `cicada/cli.py` | Main entry point |
| Commands Router | `cicada/commands.py` | Argument parser + handlers |
| Storage Utilities | `cicada/utils/storage.py` | Path resolution |
| Index Utilities | `cicada/utils/index_utils.py` | Load/validate indexes |
| Clean Command | `cicada/clean.py` | Reference implementation |
| Tier Module | `cicada/tier.py` | Tier configuration |

## Implementation Checklist

- [ ] Add "status" to KNOWN_SUBCOMMANDS tuple (line 36)
- [ ] Add status_parser definition (after line 518)
- [ ] Add --verbose argument
- [ ] Add --json argument
- [ ] Add handle_check to command_handlers dict (line 554)
- [ ] Implement handle_check() function
  - [ ] Check storage directory exists
  - [ ] Load and parse config.yaml
  - [ ] Determine tier from config
  - [ ] Load and validate index.json
  - [ ] Get index statistics
  - [ ] Check for hashes.json
  - [ ] Check for pr_index.json (optional)
  - [ ] Check MCP config files
  - [ ] Format output (human or JSON)
- [ ] Create tests in test_status.py
- [ ] Test with --verbose flag
- [ ] Test with --json flag
- [ ] Test error scenarios

## Next Steps

1. Review IMPLEMENTATION_GUIDE.md (full details)
2. Review ARCHITECTURE.md (visual diagrams)
3. Implement the command following the skeleton
4. Add comprehensive tests
5. Test manually: `cicada status [--verbose] [--json]`

## Quick Reference: Path Resolution

```python
# Everything starts with the repository path
repo_path = Path.cwd()  # or Path(args.repo).resolve()

# Get hashed storage directory
from cicada.utils import get_storage_dir
storage_dir = get_storage_dir(repo_path)  # ~/.cicada/projects/<hash>/

# Get specific file paths
from cicada.utils import get_index_path, get_config_path, get_pr_index_path
index_path = get_index_path(repo_path)      # storage_dir/index.json
config_path = get_config_path(repo_path)    # storage_dir/config.yaml
pr_index_path = get_pr_index_path(repo_path) # storage_dir/pr_index.json

# Check existence and load
if index_path.exists():
    from cicada.utils import load_index
    index = load_index(index_path)
    if index:
        from cicada.utils import validate_index_structure
        is_valid, error = validate_index_structure(index)
```

