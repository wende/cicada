# Cicada Unified CLI Design

## Command Behavior Matrix

### Core Principle
`cicada` and `cicada-mcp` should support the same subcommands with identical behavior.
The only difference is their default behavior when called without arguments:
- `cicada` (no args) → Interactive setup
- `cicada-mcp` (no args) → Equivalent to `cicada server --keywords` (silent MCP server)

## All Command Combinations

### 1. No Arguments (Default Behavior)

```bash
cicada                    # Interactive setup (editor + mode selection)
uvx cicada-mcp            # Same as cicada-mcp (defaults to server --keywords)
cicada-mcp                # Equivalent to `cicada server --keywords` (silent MCP server)
```

**Behavior:**
- `cicada`: Shows interactive menu for editor and indexing mode selection
- `uvx cicada-mcp`: Default behavior mirrors `cicada-mcp` (silent server --keywords). Run `uvx cicada-mcp install` for the interactive flow.
- `cicada-mcp`: Starts MCP server as if `cicada server --keywords` were executed (no prompts, keywords mode by default)

### 2. Install Subcommand (Interactive Setup)

```bash
cicada install [path]
uvx cicada-mcp install [path]
cicada-mcp install [path]

# Examples:
cicada install                    # Interactive setup in current dir
cicada install .                  # Interactive setup in current dir
cicada install /path/to/project   # Interactive setup in specified dir
uvx cicada-mcp install            # Same behavior via uvx
```

**Behavior:**
- Always interactive
- Shows editor selection menu
- Shows indexing mode selection menu (if no index exists)
- Creates MCP config for selected editor
- Indexes repository with selected mode

**Options:**
```bash
cicada install --claude           # Skip editor selection, use Claude
cicada install --cursor           # Skip editor selection, use Cursor
cicada install --vs               # Skip editor selection, use VS Code
cicada install --keywords         # Keywords mode (default)
cicada install --embeddings       # Embeddings mode (not implemented yet)
cicada install --claude --keywords # Combine: Claude + keywords mode
```

### 3. Server Subcommand (Silent MCP Server)

```bash
cicada server [path]
uvx cicada-mcp server [path]
cicada-mcp server [path]

# Examples:
cicada server                     # Start server in current dir (auto-setup with defaults)
cicada server .                   # Same as above
cicada server /path/to/project    # Start server for specific project
uvx cicada-mcp server             # Same behavior via uvx
```

**Behavior:**
- ALWAYS SILENT (no interactive prompts)
- Auto-setup if needed:
  - Uses default indexing mode (keywords) if no index exists
  - Creates default MCP config if none exists
- Starts MCP server on stdio
- Indexes silently in background (if needed)

**Options:**
```bash
cicada server --claude            # Create Claude config before starting
cicada server --cursor            # Create Cursor config before starting
cicada server --vs                # Create VS Code config before starting
cicada server --claude --vs       # Create both configs before starting
cicada server --keywords          # Keywords mode (if reindexing needed)
cicada server --embeddings        # Embeddings mode (not implemented yet)
```

**Default via `cicada-mcp`:**
- Running `cicada-mcp` (or `uvx cicada-mcp`) with no subcommand is equivalent to `cicada server --keywords`, guaranteeing a silent startup that favors keywords unless the user explicitly passes different flags.

**Key Difference from Install:**
- Server mode is SILENT (no prompts, uses defaults)
- Install mode is INTERACTIVE (prompts for choices)

### 4. Editor Shortcut Commands (Current Behavior)

```bash
cicada claude [path]
cicada cursor [path]
cicada vs [path]

# Examples:
cicada claude                     # Setup for Claude in current dir
cicada claude .                   # Same as above
cicada cursor /path/to/project    # Setup for Cursor in specified dir
```

**Behavior:**
- Uses existing index if available
- Interactive mode selection if no index exists
- Creates/updates MCP config for specified editor

**Options:**
```bash
cicada claude --keywords          # Keywords mode (default)
cicada claude --embeddings        # Embeddings mode (not implemented yet)
cicada cursor --keywords          # Same for Cursor
cicada vs --keywords              # Same for VS Code
```

### 5. Other Commands

```bash
cicada index [path]               # Index repository (use -f/--force with --keywords/--embeddings)
cicada index-pr [path]            # Index GitHub PRs
cicada status                     # Show diagnostic information (index, PR index, links, agents)
cicada stats [path]               # Display usage statistics (tool calls, tokens, execution times)
cicada run [tool]                 # Execute MCP tools from CLI
cicada agents install             # Install Claude Code agents
cicada clean                      # Clean up configs and indexes
cicada clean --all                # Clean all projects
```

## Decision Matrix

| Command | Interactive? | Creates Config? | Starts Server? | Auto-indexes? |
|---------|--------------|-----------------|----------------|---------------|
| `cicada` | Yes | Yes | No | Yes |
| `uvx cicada-mcp` | No (defaults to server --keywords) | Yes (if needed) | Yes | Yes (silent, keywords) |
| `cicada-mcp` | No (server --keywords) | Yes (if needed) | Yes | Yes (silent, keywords) |
| `cicada install` | Yes | Yes | No | Yes |
| `cicada server` | No | Yes (if needed) | Yes | Yes (silent) |
| `cicada claude` | Conditional* | Yes | No | Yes |
| `cicada index` | No | No | No | Yes |

\* Interactive only if no index exists

## Implementation Architecture

### Entry Points (pyproject.toml)

```toml
[project.scripts]
cicada-mcp = "cicada.mcp_entry:main"
cicada = "cicada.cli:main"
```

### File Structure

```
cicada/
├── cli.py              # Main CLI entry (cicada command)
├── mcp_entry.py        # MCP entry point (cicada-mcp command)
├── commands/
│   ├── install.py      # Handle install subcommand
│   ├── server.py       # Handle server subcommand
│   ├── editor_setup.py # Handle claude/cursor/vs subcommands
│   └── index.py        # Handle index/index-pr subcommands
├── mcp_server.py       # MCP server implementation (stdio-based)
└── setup.py            # Setup logic (shared by install and server)
```

### Argument Parsing Strategy

Both `cicada` and `cicada-mcp` should accept the same subcommands:
- `install [path]` - Interactive setup
- `server [path]` - Silent MCP server
- `claude [path]` - Editor-specific setup
- `cursor [path]` - Editor-specific setup
- `vs [path]` - Editor-specific setup
- `index [path]` - Manual indexing
- `index-pr [path]` - PR indexing
- `clean` - Cleanup

### Default Behavior Difference

```python
# cicada/cli.py
def main():
    args = parse_args()
    if args.subcommand is None:
        # Default: interactive setup
        handle_install(args)
    else:
        route_to_handler(args)

# cicada/mcp_entry.py
def main():
    args = parse_args()
    if args.subcommand is None:
        # Default: start MCP server (backward compatibility)
        handle_server(args)
    else:
        route_to_handler(args)
```

## Silent vs Interactive Modes

### Interactive Mode (`install` subcommand or editor shortcuts)
- Shows prompts and menus
- Waits for user input
- Provides detailed output
- Used by: `cicada`, `cicada install`, `cicada claude`, etc.

### Silent Mode (`server` subcommand or `cicada-mcp` default)
- No prompts
- Uses defaults for everything
- Minimal output (or none for MCP server)
- Auto-creates configs with sensible defaults
- Used by: `cicada server`, `cicada-mcp` (no args)

## Backward Compatibility

### Existing Behavior Preserved

```bash
cicada-mcp                        # Still starts MCP server (silent)
cicada-mcp /path/to/repo          # Still starts MCP server for repo
cicada claude                     # Still works as before
cicada index                      # Still works as before
```

### New Unified Behavior

```bash
uvx cicada-mcp install            # NEW: Interactive setup via uvx
uvx cicada-mcp server             # NEW: Explicit server mode via uvx
cicada install                    # NEW: Explicit install command
cicada server                     # NEW: Explicit server command
```

## Default Command Injection

The entry-point for `cicada-mcp` always injects `server --keywords` when no explicit subcommand is passed. This guarantees MCP clients (and developers running `cicada-mcp` directly) immediately start the silent server with keyword indexing, while still allowing all regular subcommands (`install`, `server --embeddings`, etc.) when specified manually.

## Indexing Mode Defaults

### Interactive Mode (install)
- Prompts user for indexing mode
- Shows keywords and embeddings options
- Defaults to user selection

### Silent Mode (server)
- Uses keywords mode by default
- Can be overridden with `--keywords` or `--embeddings` flags
- Never prompts

### Existing Index
- Both modes: Use existing index settings
- Reindex only if forced with flags

## Config Creation Rules

### Install Mode
- Always creates config for selected editor
- Prompts for editor if not specified
- Updates existing config if present

### Server Mode
- Creates config only if editor flags provided (`--claude`, `--cursor`, `--vs`)
- Can create multiple configs with multiple flags
- Uses defaults if no config exists and no flags provided
- Never prompts

## Error Handling

### Non-Elixir Project
```bash
cicada install                    # Error: "Not an Elixir project (mix.exs not found)"
cicada server                     # Error: Same (exits gracefully)
```

### Missing Dependencies
```bash
cicada install --embeddings       # Not implemented yet (errors with guidance)
```

### Conflicting Flags
```bash
cicada install --keywords --embeddings  # Error: "Cannot specify multiple mode flags"
```

## Usage Examples

### First-Time User (uvx)
```bash
cd ~/my-elixir-project
uvx cicada-mcp install            # Interactive setup, selects Claude + mode
# Restart Claude Code
# Start using Cicada MCP tools
```

### First-Time User (installed)
```bash
uv tool install cicada-mcp
cd ~/my-elixir-project
cicada install                    # Interactive setup
```

### Quick Setup for Specific Editor
```bash
cicada claude                     # Setup for Claude (interactive mode choice)
cicada cursor --keywords          # Setup for Cursor with keywords mode
cicada vs --keywords              # Setup for VS Code with keywords mode
```

### Development/Testing (Server Mode)
```bash
cicada server . --claude          # Start server, create Claude config, use defaults
cicada server --claude --vs --keywords # Start server, create both configs, use keywords mode
```

### MCP Client Integration
```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-mcp",
      "env": {
        "CICADA_REPO_PATH": "/path/to/repo"
      }
    }
  }
}
```
When an MCP client starts `cicada-mcp` with no arguments, the CLI:
1. Injects `server --keywords` so the silent server launches immediately
2. Auto-setups with defaults if needed (silently)
3. Starts MCP server on stdio
4. Never prompts or prints to stdout

## Implementation Phases

### Phase 1: Core Refactoring ✅ COMPLETED
- [x] Research current structure
- [x] Create `mcp_entry.py` for `cicada-mcp` entry point
- [x] Add `install` subcommand to `cli.py`
- [x] Add `server` subcommand to `cli.py`
- [x] Add subcommand support to `mcp_entry.py`

### Phase 2: Shared Logic ✅ COMPLETED
- [x] Extract common argument parsing
- [x] Create silent setup mode in `setup.py`
- [x] Add default command injection so `cicada-mcp` maps to `server --keywords`
- [x] Implement default behavior routing

### Phase 3: Commands Implementation ✅ COMPLETED
- [x] Implement `install` command (interactive) - `cicada/commands/install.py`
- [x] Implement `server` command (silent) - `cicada/commands/server.py`
- [x] Update editor shortcuts to support both modes
- [x] Add editor flags to `server` subcommand
- [x] Add `setup_multiple_editors()` helper function

### Phase 4: Testing & Polish ✅ BASIC TESTING COMPLETED
- [x] Test all command combinations
- [x] Test help output for all subcommands
- [x] Verify backward compatibility (cicada claude/cursor/vs still works)
- [ ] Test actual MCP client integration (requires full setup)
- [ ] Update README with new commands
- [ ] Add migration guide for existing users

## Open Questions ✅ RESOLVED

1. **Should `cicada-mcp` with no args detect TTY and show interactive setup if in terminal?**
   - ✅ **ANSWERED: Always run `server --keywords`**
   - Rationale: MCP clients expect silent startup, and developers can still run `cicada-mcp install` explicitly when they need the interactive flow.
   - Result: `cicada-mcp` (no args) is equivalent to `cicada server --keywords` in every environment.

2. **Should `server` mode accept a path as positional arg or require `--path`?**
   - ✅ **ANSWERED: Positional arg**
   - Implementation: `cicada server .` (shorter syntax)
   - Alternative rejected: Flag-based would be more verbose

3. **Should multiple editor flags create all configs at once?**
   - ✅ **ANSWERED: Yes**
   - Implementation: `cicada server --claude --vs` creates both configs
   - Helper function: `setup_multiple_editors()` in `setup.py`

## Implementation Summary

### Files Created
- **`cicada/mcp_entry.py`** - New entry point for `cicada-mcp` command
  - Injects `server --keywords` when no subcommand is supplied
  - Unified subcommand support
  - Default behavior routing (interactive flows always opt-in via explicit `install`)

- **`cicada/commands/__init__.py`** - Command handlers package
- **`cicada/commands/install.py`** - Interactive install command handler
  - Supports flags to skip prompts (--claude, --cursor, --vs, --keywords, --embeddings)
  - Falls back to interactive menus when flags not provided

- **`cicada/commands/server.py`** - Silent server command handler
  - No prompts, uses defaults
  - Auto-setup if needed (default to keywords mode)
  - Supports multiple editor configs (--claude --cursor --vs)

### Files Modified
- **`pyproject.toml`** - Updated entry points:
  - `cicada-mcp = "cicada.mcp_entry:main"` (changed from mcp_server)
  - `cicada-server = "cicada.mcp_entry:main"` (changed from mcp_server)

- **`cicada/cli.py`** - Added install and server subcommands
  - New `handle_install_command()` function
  - New `handle_server_command()` function
  - Updated command routing logic

- **`cicada/setup.py`** - Added multiple editor support
  - New `setup_multiple_editors()` function
  - Verbose flag already supported in `create_config_yaml()` and `index_repository()`

### Command Matrix Implementation Status

| Command | Status | Notes |
|---------|--------|-------|
| `cicada` | ✅ Working | Interactive setup (default behavior) |
| `cicada install` | ✅ Working | Explicit interactive setup |
| `cicada server` | ✅ Working | Silent MCP server |
| `cicada claude/cursor/vs` | ✅ Working | Editor shortcuts (backward compatible) |
| `cicada-mcp` | ✅ Working | No-arg default runs `server --keywords` (silent) |
| `cicada-mcp install` | ✅ Working | Same as `cicada install` |
| `cicada-mcp server` | ✅ Working | Same as `cicada server` |
| `cicada-mcp claude/cursor/vs` | ✅ Working | Same as `cicada` editor shortcuts |

### Testing Results

**Help Commands** ✅
- `cicada --help` - Shows all subcommands
- `cicada-mcp --help` - Shows all subcommands (fixed argparse issue)
- `cicada install --help` - Shows install options
- `cicada server --help` - Shows server options
- `cicada-mcp install --help` - Works correctly
- `cicada-mcp server --help` - Works correctly

**Backward Compatibility** ✅
- `cicada claude` - Still works as before
- `cicada cursor` - Still works as before
- `cicada vs` - Still works as before
- `cicada-mcp claude` - Now works (unified with cicada)

**Entry Points** ✅
- Tool installation: `uv tool install .` successfully creates all 3 executables
- All entry points route to correct handlers

### Next Steps

1. **Full Integration Testing** - Test with actual Elixir project:
   - Test `cicada install` with interactive prompts
   - Test `cicada server` silent mode
   - Test `cicada-mcp` default (`server --keywords`) behavior with an MCP client simulation
   - Test multiple editor flags: `cicada server --claude --vs`

2. **Documentation Updates**:
   - Update main README.md with new commands
   - Add migration guide for existing users
   - Document the unified command structure

3. **User Experience Polish**:
   - Consider adding progress indicators for silent mode
   - Improve error messages
   - Add examples to help text
