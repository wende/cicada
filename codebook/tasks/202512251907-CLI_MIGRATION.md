# CLI Migration Guide - Unified `cicada` Command

## Overview

As of version 0.2.0, Cicada has moved from multiple CLI entry points to a single unified `cicada` command with subcommands. This simplifies the user experience and follows common CLI best practices.

## What Changed

### Before (v0.1.1 and earlier)

Cicada provided four separate CLI commands:

```bash
cicada                    # Project setup
cicada-index              # Index Elixir code
cicada-index-pr           # Index GitHub PRs
cicada-find-dead-code     # Find unused functions
```

### After (v0.2.0+)

All functionality is now under a single `cicada` command:

```bash
cicada [./path]           # Project setup (default action)
cicada index              # Index Elixir code
cicada index-pr           # Index GitHub PRs
cicada find-dead-code     # Find unused functions
```

## Migration Guide

### Installation/Setup Command

**Before:**
```bash
cicada /path/to/project
cicada .
cicada  # Uses current directory
```

**After:** (No change - backward compatible)
```bash
cicada /path/to/project
cicada .
cicada  # Uses current directory
```

### Indexing Elixir Code

**Before:**
```bash
cicada-index .
cicada-index --output .cicada/index.json
cicada-index --extract-keywords
cicada-index --spacy-model medium
```

**After:**
```bash
cicada index .
cicada index --force --keywords  # Keywords mode (default)
```

Note: `--output` option has been removed. Index files are now stored in `~/.cicada/projects/<repo_hash>/index.json`.

### Indexing Pull Requests

**Before:**
```bash
cicada-index-pr .
cicada-index-pr . --clean
cicada-index-pr --output .cicada/pr_index.json
```

**After:**
```bash
cicada index-pr .
cicada index-pr . --clean
cicada index-pr --output .cicada/pr_index.json
```

### Finding Dead Code

**Before:**
```bash
cicada-find-dead-code
cicada-find-dead-code --min-confidence low
cicada-find-dead-code --format json
```

**After:**
```bash
cicada find-dead-code
cicada find-dead-code --min-confidence low
cicada find-dead-code --format json
```

## Command Reference

### Main Command

```bash
cicada --help
```

Shows all available subcommands.

### Setup/Install (Default)

```bash
# Setup in current directory
cicada

# Setup specific project
cicada /path/to/project

# Force use of uv
cicada --use-uv
```

### Index Subcommand

```bash
# Default indexing (keywords mode)
cicada index

# Keywords mode (explicit)
cicada index --force --keywords

# Embeddings mode (not implemented yet)
cicada index --force --embeddings

# Specify repository path
cicada index /path/to/repo

# Force full reindex
cicada index --full

# Get help
cicada index --help
```

### Index-PR Subcommand

```bash
# Incremental update (default)
cicada index-pr

# Specify repository path
cicada index-pr /path/to/repo

# Clean rebuild
cicada index-pr --clean

# Custom output path
cicada index-pr --output .cicada/custom_pr.json

# Get help
cicada index-pr --help
```

### Find-Dead-Code Subcommand

```bash
# Show high confidence candidates (default)
cicada find-dead-code

# Show all candidates
cicada find-dead-code --min-confidence low

# JSON output
cicada find-dead-code --format json

# Custom index path
cicada find-dead-code --index .cicada/custom.json

# Get help
cicada find-dead-code --help
```

## Why This Change?

### Benefits

1. **Simpler Mental Model**: One command (`cicada`) instead of four separate commands
2. **Easier Discovery**: `cicada --help` shows all available operations
3. **Consistent with Industry Standards**: Similar to `git`, `npm`, `docker`, etc.
4. **Better Organization**: Related functionality grouped under one namespace
5. **Easier to Remember**: No need to remember exact command names
6. **Future-Proof**: Easy to add new subcommands without cluttering the global namespace

### Design Principles

- **Backward Compatible**: `cicada` without arguments still works for setup
- **Intuitive**: Subcommand names match the old command suffixes
- **Self-Documenting**: Each subcommand has its own `--help`
- **Consistent**: All options work the same way as before

## Updating Scripts and Documentation

If you have scripts or documentation that reference the old commands, update them as follows:

### In Shell Scripts

```bash
# Before
cicada-index .
cicada-index-pr .
cicada-find-dead-code

# After
cicada index .
cicada index-pr .
cicada find-dead-code
```

### In Documentation

```markdown
<!-- Before -->
Run `cicada-index` to index your repository.
Run `cicada-index-pr` to index pull requests.

<!-- After -->
Run `cicada index` to index your repository.
Run `cicada index-pr` to index pull requests.
```

### In CI/CD Pipelines

```yaml
# Before
- name: Index repository
  run: cicada-index .

# After
- name: Index repository
  run: cicada index .
```

## Breaking Changes

### Removed Commands

The following command names are no longer available:

- `cicada-index` → Use `cicada index`
- `cicada-index-pr` → Use `cicada index-pr`
- `cicada-find-dead-code` → Use `cicada find-dead-code`

### Impact

- **Low**: The commands are simply renamed to subcommands
- **Migration**: Simple search-and-replace in scripts/docs
- **Functionality**: All options and behavior remain identical

## Troubleshooting

### "Command not found: cicada-index"

**Solution**: Update to the new syntax:
```bash
cicada index
```

### "Command not found: cicada index"

This usually means:

1. **Not installed**: Install with `uv tool install cicada`
2. **Old version**: Upgrade with `uv tool upgrade cicada`
3. **PATH issue**: Ensure `~/.local/bin` is in your PATH

### Getting Help

All subcommands support `--help`:

```bash
cicada --help              # Main help
cicada index --help        # Indexing help
cicada index-pr --help     # PR indexing help
cicada find-dead-code --help  # Dead code detection help
```

## Rollback

If you need to temporarily use the old commands, you can:

1. Install an older version:
```bash
uv tool install git+https://github.com/wende/cicada.git@v0.1.1
```

2. Or create aliases:
```bash
alias cicada-index='cicada index'
alias cicada-index-pr='cicada index-pr'
alias cicada-find-dead-code='cicada find-dead-code'
```

## FAQ

**Q: Can I still use `cicada` for setup?**  
A: Yes! `cicada` and `cicada ./path` still work for project setup.

**Q: Do I need to re-index my projects?**  
A: No, the index format hasn't changed. Just use the new command syntax.

**Q: Are there any new features?**  
A: The functionality is identical; only the command interface has changed.

**Q: What about the MCP server?**  
A: The `cicada-server` command remains unchanged.

**Q: Will old commands work forever?**  
A: No, they were removed in v0.2.0. Please migrate to the new syntax.

## Summary

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `cicada` | `cicada` or `cicada ./path` | No change |
| `cicada-index` | `cicada index` | Subcommand |
| `cicada-index-pr` | `cicada index-pr` | Subcommand |
| `cicada-find-dead-code` | `cicada find-dead-code` | Subcommand |
| `cicada-server` | `cicada-server` | No change |

**The migration is simple**: Just replace the hyphen with a space!
