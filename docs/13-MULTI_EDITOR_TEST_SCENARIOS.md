# Multi-Editor Setup Test Scenarios

## Visual Test Coverage Map

```
┌─────────────────────────────────────────────────────────────┐
│                   Cicada Multi-Editor Setup                  │
│                      Integration Tests                       │
└─────────────────────────────────────────────────────────────┘

Scenario 1: Sequential Setup (Claude → Cursor)
┌──────────────┐       ┌──────────────┐
│ cicada claude│───→   │cicada cursor │
└──────────────┘       └──────────────┘
      │                       │
      ▼                       ▼
  .mcp.json            .cursor/mcp.json
      │                       │
      └───────────┬───────────┘
                  │
                  ▼
        ~/.cicada/projects/<hash>/
              (shared storage)

Scenario 2: Complete Setup (All Three Editors)
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ cicada claude│   │cicada cursor │   │  cicada vs   │
└──────────────┘   └──────────────┘   └──────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
  .mcp.json      .cursor/mcp.json   .vscode/settings.json
      │                   │                   │
      └───────────────────┼───────────────────┘
                          │
                          ▼
                ~/.cicada/projects/<hash>/
                    ├── index.json
                    ├── config.yaml
                    ├── hashes.json
                    └── pr_index.json

Scenario 3: Re-run Safety
┌──────────────┐       ┌──────────────┐
│ cicada claude│───→   │cicada claude │  (again)
└──────────────┘       └──────────────┘
      │                       │
      ▼                       ▼
  .mcp.json              .mcp.json
  (created)              (updated, not duplicated)
      │                       │
      ▼                       ▼
 storage created         storage preserved
```

## Test Coverage Matrix

| Test Case | Claude | Cursor | VS Code | Storage | Config Preservation |
|-----------|--------|--------|---------|---------|---------------------|
| **Sequential Setup** | ✅ | ✅ | - | ✅ | ✅ |
| **All Three Editors** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Re-run Same Editor** | ✅ | - | - | ✅ | ✅ |
| **Preserve Other MCP** | ✅ | - | - | ✅ | ✅ |
| **Handle Malformed** | ✅ | - | - | ✅ | ✅ |
| **Directory Creation** | - | ✅ | ✅ | ✅ | N/A |
| **Different Paths** | ✅ | ✅ | ✅ | ✅ | N/A |
| **Same Storage** | ✅ | ✅ | ✅ | ✅ | N/A |

## Detailed Test Scenarios

### 1. Sequential Setup: Claude → Cursor

**User Story**: Developer wants to use both Claude Code and Cursor

**Steps**:
1. Run `uvx cicada claude`
2. Verify `.mcp.json` created
3. Run `uvx cicada cursor`
4. Verify `.cursor/mcp.json` created
5. Verify `.mcp.json` unchanged

**Assertions**:
- ✅ Both configs exist
- ✅ Both point to same storage
- ✅ First config remains valid
- ✅ No errors or warnings

### 2. Complete Setup: All Three Editors

**User Story**: Developer wants maximum flexibility across all editors

**Steps**:
1. Run `uvx cicada claude`
2. Run `uvx cicada cursor`
3. Run `uvx cicada vs`

**Assertions**:
- ✅ `.mcp.json` exists
- ✅ `.cursor/mcp.json` exists
- ✅ `.vscode/settings.json` exists
- ✅ All use same storage directory
- ✅ Storage has config.yaml
- ✅ All configs have correct structure

### 3. Re-run Safety

**User Story**: Developer accidentally runs setup twice

**Steps**:
1. Run `uvx cicada claude`
2. Run `uvx cicada claude` again

**Assertions**:
- ✅ No duplicate entries
- ✅ Config remains valid
- ✅ Storage path unchanged
- ✅ No errors or data loss

### 4. Config Preservation

**User Story**: Developer has other MCP servers configured

**Initial State**:
```json
{
  "mcpServers": {
    "other-server": {
      "command": "other-server"
    }
  }
}
```

**After Setup**:
```json
{
  "mcpServers": {
    "other-server": {
      "command": "other-server"
    },
    "cicada": {
      "command": "cicada-mcp",
      "env": {...}
    }
  }
}
```

**Assertions**:
- ✅ `other-server` entry preserved
- ✅ `cicada` entry added
- ✅ No configuration lost

### 5. Malformed Config Recovery

**User Story**: Developer has corrupted config file

**Initial State**: `.mcp.json` contains invalid JSON

**After Setup**:
```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-mcp",
      "env": {...}
    }
  }
}
```

**Assertions**:
- ✅ Warning logged
- ✅ Config recreated
- ✅ Setup completes successfully

### 6. Directory Creation

**User Story**: Developer hasn't used Cursor/VS Code before

**Initial State**:
- `.cursor/` doesn't exist
- `.vscode/` doesn't exist

**After Setup**:
- ✅ `.cursor/` created
- ✅ `.vscode/` created
- ✅ Config files placed inside

### 7. Different Config Paths

**Verification**: Each editor uses unique config location

**Results**:
- Claude: `{repo}/.mcp.json`
- Cursor: `{repo}/.cursor/mcp.json`
- VS Code: `{repo}/.vscode/settings.json`

**Assertions**:
- ✅ No path collisions
- ✅ All paths are unique

### 8. Shared Storage

**Verification**: All editors use same storage

**Results**:
```
All editors → CICADA_CONFIG_DIR = ~/.cicada/projects/<hash>/
```

**Assertions**:
- ✅ Identical storage path
- ✅ No duplication of index
- ✅ Efficient disk usage

### 9. Indexing Behavior

**Verification**: Indexing called per setup

**Results**:
- Setup 1: Index called (count: 1)
- Setup 2: Index called (count: 2)
- Setup 3: Index called (count: 3)

**Assertions**:
- ✅ Fresh index per setup
- ✅ Incremental indexing works
- ✅ Consistent repo path

## Quick Reference

### What Gets Created

```
my-elixir-project/
├── .mcp.json                    # Claude Code config
├── .cursor/
│   └── mcp.json                 # Cursor config
├── .vscode/
│   └── settings.json            # VS Code config
└── ... (your code)

~/.cicada/projects/<hash>/
├── index.json                   # Code index (shared)
├── config.yaml                  # Repository config (shared)
├── hashes.json                  # File tracking (shared)
└── pr_index.json                # PR data (shared)
```

### What Gets Shared

- ✅ **index.json**: Code structure and function definitions
- ✅ **config.yaml**: Repository configuration
- ✅ **hashes.json**: File modification tracking
- ✅ **pr_index.json**: Pull request metadata

### What's Independent

- ❌ **Config files**: Each editor has its own
- ❌ **Config paths**: Different locations per editor
- ❌ **Editor settings**: No cross-contamination

## Test Statistics

- **Total test cases**: 9
- **Editor combinations tested**: 6
- **Error scenarios covered**: 2
- **Setup sequences tested**: 3
- **Config preservation checks**: 2

## Benefits Verified by Tests

1. **Zero Config Conflicts**: Each editor's config is independent
2. **Efficient Storage**: Single index shared by all editors
3. **Safe Re-execution**: Running setup multiple times is safe
4. **Data Integrity**: Existing configs are preserved
5. **Error Resilience**: Malformed configs are handled gracefully
6. **Automatic Setup**: Missing directories are created
7. **Consistency**: All editors use identical storage
8. **Flexibility**: Any combination of editors works

## Real-World Usage Patterns Validated

✅ Developer trying Claude Code first, then switching to Cursor
✅ Team using multiple editors on same codebase
✅ Developer running setup script multiple times accidentally
✅ Developer with existing MCP servers configured
✅ Clean install on new machine (no directories exist)
✅ Recovery from corrupted config files

## Conclusion

These integration tests guarantee that Cicada's multi-editor setup workflow is:
- **Robust**: Handles errors gracefully
- **Consistent**: Shared storage works correctly
- **Safe**: No data loss or config corruption
- **Flexible**: Any editor combination supported
- **User-friendly**: Automatic directory creation
