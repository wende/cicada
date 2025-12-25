# Manual Testing Checklist

Quick test plan before merging to main.

## Command Overview

**`cicada` vs `cicada-mcp`**: Both commands provide the same core functionality:

### `cicada` (Primary CLI)
- Interactive setup and management
- Default behavior: `cicada` or `cicada install` - interactive setup
- Verbose output, progress indicators, user prompts
- Recommended for manual/interactive use

### `cicada-mcp` (MCP Server)
- MCP server mode entry point
- Default behavior: `cicada-mcp` - starts MCP server on stdio (silent)
- Can run all CLI commands via subcommands
- Recommended for MCP server integration

### Behavioral Consistency

**Storage**: Both commands now enforce **centralized storage** (`~/.cicada/projects/<hash>/`):
- ✅ `index` - NO --output option (uses centralized storage)
- ✅ `index-pr` - NO --output option (uses centralized storage)
- ✅ `find-dead-code` - --index defaults to centralized storage

**Minor Differences**:
- `cicada index` has `--test` flag for keyword extraction testing
- `cicada-mcp index` does not have `--test` flag (server mode doesn't need it)

**Key Point**: All indexing and analysis commands behave identically whether called via `cicada` or `cicada-mcp`. Use whichever is more convenient for testing.

## Setup & Install
- [x] `cicada` - Interactive setup
- [x] `cicada .` - Explicit current directory path
- [x] `cicada /path/to/other/project` - Setup in different directory

## Index - Basic
- [x] `cicada index` - Interactive setup (no flags), choose mode
- [x] `cicada index .` - Uses centralized storage path

## Index - Modes
- [x] `cicada index --force --keywords` - Keywords mode (default)
- [x] `cicada index --force --embeddings` - Embeddings mode (not implemented yet)

## Index - Error Cases
- [x] `cicada index --force --keywords --embeddings` - Should error: "Cannot specify multiple mode flags"

## Index - Incremental
- [x] Run `cicada index --force --keywords` twice - Second run should be faster (incremental)
- [x] Modify 1-2 files, run again - Only changed files reprocessed
- [x] Ctrl-C during indexing, run again - Resume from saved progress

## PR Indexing
- [/] `cicada index-pr` - Default incremental update
- [/] `cicada index-pr .` - Explicit current directory
- [/] `cicada index-pr --clean` - Clean rebuild from scratch
- [/] Ctrl-C during PR indexing - Verify graceful shutdown message

## Dead Code Analysis
- [ ] `cicada find-dead-code` - Default (high confidence, markdown)
- [ ] `cicada find-dead-code --min-confidence medium` - Medium confidence
- [ ] `cicada find-dead-code --min-confidence low` - All candidates
- [ ] `cicada find-dead-code --format json` - JSON output
- [ ] `cicada find-dead-code --index custom.json` - Custom index path
- [ ] `cicada find-dead-code` before indexing - Should error with helpful message

## MCP Server (via Claude Code/Cline)
- [ ] `search_module` - Find module by name
- [ ] `search_function` - Find function with usage examples
- [ ] `search_module_usage` - Track module dependencies
- [ ] `search_by_keywords` - Semantic search (requires index with keyword extraction)
- [ ] `get_commit_history` - File history
- [ ] `get_blame` - Line-by-line ownership
- [ ] `find_pr_for_line` - PR attribution (requires PR index)
- [ ] `get_file_pr_history` - File PR history (requires PR index)

## Paths to Test
- [ ] Current directory (`.`)
- [ ] Test fixture directory (`tests/fixtures/example_project`)
- [ ] Absolute path (`/full/path/to/elixir/project`)
- [ ] Relative path (`../some_project`)
- [ ] Non-Elixir directory (should handle gracefully)

## Version Check
- [ ] `cicada index` - Verify version check message appears
- [ ] `cicada index-pr` - Verify version check message appears

## Edge Cases
- [ ] Empty directory - Should handle gracefully
- [ ] Non-git repository - PR features should warn appropriately
- [ ] Large repository (>500 files) - Verify performance
- [ ] Repository with no `.ex` files - Should complete without errors
