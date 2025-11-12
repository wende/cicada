# Cicada `status` Command - Complete Documentation Index

This directory contains three comprehensive documents for implementing the `cicada status` command.

## Document Overview

### 1. QUICK_START.md (8.2 KB)
**Start here** - A quick reference with the essential information:
- Key implementation points
- Where to add code (specific line numbers)
- Storage utilities reference
- File locations summary
- Implementation checklist
- Quick path resolution reference

Use this when you're ready to code.

### 2. IMPLEMENTATION_GUIDE.md (20 KB)
**Deep dive** - The complete implementation reference:
- Section 1: CLI Commands Structure (entry point chain, argument parser, command router)
- Section 2: Storage and File Locations (centralized storage, backward compatibility)
- Section 3: Index Files Structure (index.json, config.yaml, pr_index.json, hashes.json)
- Section 4: MCP Configuration Files (all editor formats)
- Section 5: How `clean` Command Works (reuse this logic pattern)
- Section 6: Index Loading and Validation (utilities and examples)
- Section 7: Detecting Tier/Model Information (how to read from config)
- Section 8: Implementation Pattern (full function skeleton and output examples)
- Section 9: Key Files Reference (file locations table)
- Section 10: Testing Guidelines

Read this to understand every aspect of the implementation.

### 3. ARCHITECTURE.md (8.4 KB)
**Visual reference** - Diagrams and data structures:
- CLI Command Flow diagram
- Storage Architecture (new centralized + legacy)
- Index File Hierarchy (JSON structure)
- Config File Hierarchy (YAML structure)
- MCP Config File Hierarchy (all formats)
- Data Flow: `cicada status` (step-by-step)
- Utility Functions Map
- Module Dependencies
- File Checklist
- Version Information Sources
- Error Handling Scenarios

Use this when you need visual understanding of relationships and hierarchies.

## Quick Implementation Path

1. **Read**: Start with QUICK_START.md (5 min read)
2. **Reference**: Keep IMPLEMENTATION_GUIDE.md section 8 open while coding
3. **Validate**: Refer to ARCHITECTURE.md for structure verification

## What the `status` Command Does

Validates that Cicada configuration and indexes are properly set up for a repository:

```bash
cicada status           # Quick status check
cicada status --verbose # Detailed information
cicada status --json    # Machine-readable JSON output
```

It checks:
- Storage directory (`~/.cicada/projects/<hash>/`)
- Configuration file (`config.yaml` with tier info)
- Code index (`index.json` with modules/functions)
- File hashes (`hashes.json` for incremental indexing)
- PR index (`pr_index.json` - optional GitHub history)
- MCP configs (`.mcp.json`, `.cursor/mcp.json`, `.vscode/settings.json`)

## File Locations

All three documents are located at:
- `/Users/wende/projects/cicada/QUICK_START.md`
- `/Users/wende/projects/cicada/IMPLEMENTATION_GUIDE.md`
- `/Users/wende/projects/cicada/ARCHITECTURE.md`

## Implementation Checklist

### Phase 1: Registration (5 minutes)
- [ ] Add "status" to KNOWN_SUBCOMMANDS in commands.py
- [ ] Add status_parser argument definition
- [ ] Add handle_status to command_handlers dict

### Phase 2: Core Implementation (30 minutes)
- [ ] Implement handle_status() function
- [ ] Add storage directory status
- [ ] Add configuration status with tier detection
- [ ] Add index validation
- [ ] Add MCP config status
- [ ] Add human-readable output format
- [ ] Add JSON output format (with --json flag)

### Phase 3: Testing (20 minutes)
- [ ] Create test_status.py
- [ ] Test basic functionality
- [ ] Test --verbose flag
- [ ] Test --json flag
- [ ] Test error scenarios

### Phase 4: Polish (10 minutes)
- [ ] Verify error messages are helpful
- [ ] Test with actual repository
- [ ] Check output formatting

## Key Code Locations

| What | File | Location |
|------|------|----------|
| CLI Router | `cicada/commands.py` | Lines 24-38 (subcommands), 89-530 (parser), 533-566 (router) |
| Storage Utils | `cicada/utils/storage.py` | Complete file, 112 lines |
| Index Utils | `cicada/utils/index_utils.py` | Complete file, 300 lines |
| Clean Reference | `cicada/clean.py` | Lines 183-302 (clean_repository pattern) |
| Tier Info | `cicada/tier.py` | Lines 14-22 (TIER_METHODS mapping) |

## Critical Information Snippets

### Get Repository Hash
```python
from cicada.utils import get_repo_hash
hash_value = get_repo_hash(repo_path)  # SHA256 of absolute path, first 16 chars
```

### Resolve File Paths
```python
from cicada.utils import get_storage_dir, get_index_path, get_config_path

repo_path = Path.cwd()
storage_dir = get_storage_dir(repo_path)      # ~/.cicada/projects/<hash>/
index_path = get_index_path(repo_path)        # storage_dir/index.json
config_path = get_config_path(repo_path)      # storage_dir/config.yaml
```

### Load and Validate Index
```python
from cicada.utils import load_index, validate_index_structure
from cicada.utils.index_utils import get_index_stats

index = load_index(index_path)
is_valid, error = validate_index_structure(index)
stats = get_index_stats(index) if is_valid else None
```

### Detect Tier from Config
```python
import yaml
config = yaml.safe_load(open(config_path))
extraction = config.get("keyword_extraction", {}).get("method")
expansion = config.get("keyword_expansion", {}).get("method")
# "regular"+"lemmi" = fast, "bert"+"glove" = regular, "bert"+"fasttext" = max
```

### Status of MCP Configs
```python
import json
mcp_configs = {
    "claude": repo_path / ".mcp.json",
    "cursor": repo_path / ".cursor" / "mcp.json",
    "vscode": repo_path / ".vscode" / "settings.json",
}
for editor, path in mcp_configs.items():
    if path.exists():
        config = json.load(open(path))
        key = "mcpServers" if editor != "vscode" else "mcp.servers"
        has_cicada = key in config and "cicada" in config[key]
```

## Testing References

Existing test patterns to follow:
- `/Users/wende/projects/cicada/tests/setup/test_clean.py` - Clean command tests
- `/Users/wende/projects/cicada/tests/setup/test_cli.py` - CLI tests
- `/Users/wende/projects/cicada/tests/setup/test_status.py` - Status command tests

## Common Pitfalls to Avoid

1. **Path Resolution**: Always use `Path.resolve()` before hashing
   - Wrong: `get_repo_hash(args.repo)`
   - Right: `get_repo_hash(Path(args.repo).resolve())`

2. **Storage Location**: Storage is in user's home, not repo root
   - Wrong: `repo_path / ".cicada" / "index.json"`
   - Right: `~/.cicada/projects/<hash>/index.json`

3. **MCP Config Keys**: VS Code uses different key
   - Claude/Cursor: `config["mcpServers"]`
   - VS Code: `config["mcp.servers"]`

4. **Config Format**: YAML not JSON
   - Use `yaml.safe_load()` to read config.yaml
   - Use `json.load()` to read MCP configs

5. **Error Handling**: Be graceful
   - Don't crash on missing files
   - Return None/empty instead of exceptions
   - Provide helpful error messages

## Support Resources

- Cicada GitHub: https://github.com/anthropics/cicada
- Index structure reference: `/Users/wende/projects/cicada/tests/fixtures/.cicada/index.json`
- Example config: `/Users/wende/projects/cicada/tests/fixtures/.cicada/config.yaml`
- Example MCP config: `/Users/wende/projects/cicada/tests/fixtures/elixir_project/.mcp.json`

## Summary

You have complete documentation with:
- **1,028 total lines** of guides and diagrams
- **Specific line numbers** for where to add code
- **Complete code skeletons** ready to implement
- **Multiple output format examples**
- **Testing patterns** from existing code
- **Visual architecture diagrams**

Start with QUICK_START.md, reference IMPLEMENTATION_GUIDE.md section 8 while coding, and use ARCHITECTURE.md for validation.

Good luck with the implementation!
