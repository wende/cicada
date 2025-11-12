# Cicada Architecture Diagram

## CLI Command Flow

```
cicada [command] [options]
  ↓
cicada/cli.py: main()
  ↓
cicada/entry_utils.py: run_cli()
  ↓
cicada/commands.py: get_argument_parser() + handle_command()
  ↓
Command Handlers:
  - handle_install()
  - handle_server()
  - handle_index()
  - handle_watch()
  - handle_clean()
  - handle_status()  ← New command
  - etc.
```

## Storage Architecture

```
Repository (e.g., /Users/wende/projects/cicada)
├── .mcp.json                    ← Claude Code config
├── .cursor/mcp.json             ← Cursor config
├── .vscode/settings.json        ← VS Code config
├── .gemini/mcp.json             ← Gemini CLI config
├── .codex/mcp.json              ← Codex config
├── mix.exs                       ← Elixir project marker
└── lib/                          ← Source code

User Home (~/.cicada/projects/)
└── <repo_hash>/                  ← SHA256(resolved_path)[:16]
    ├── index.json                ← Code index with modules/functions
    ├── config.yaml               ← Tier configuration (extraction/expansion)
    ├── hashes.json               ← File hashes for change detection
    └── pr_index.json             ← GitHub PR history (optional)

Legacy (backward compat)
Repository/.cicada/              ← Old format (deprecated)
```

## Index File Hierarchy

```
index.json
├── "modules"
│   └── "ModuleName" (e.g., "Cicada.Indexer")
│       ├── "file": "lib/cicada/indexer.ex"
│       ├── "line": 1
│       ├── "moduledoc": "Module documentation..."
│       └── "functions": [
│           {
│               "name": "index_repository",
│               "arity": 2,
│               "full_name": "index_repository/2",
│               "type": "def" | "defp",
│               "line": 42,
│               "signature": "def index_repository(repo_path, output_path)",
│               "doc": "Function documentation...",
│               "keywords": {
│                   "index": 5.2,
│                   "repository": 3.1,
│                   ...
│               },
│               "dependencies": [
│                   {"module": "...", "function": "...", "arity": N, "line": ...}
│               ]
│           }
│       ]
└── "metadata"
    ├── "indexed_at": "2025-11-11T17:43:33.826829"
    ├── "total_modules": 37
    ├── "total_functions": 317
    ├── "public_functions": 250
    ├── "private_functions": 67
    ├── "repo_path": "/Users/wende/projects/cicada"
    └── "cicada_version": "0.3.1 (v0.3.1rc2/9c57cec)"
```

## Config File Hierarchy

```
config.yaml
├── repository:
│   └── path: /Users/wende/projects/cicada
├── storage:
│   └── index_path: ~/.cicada/projects/<hash>/index.json
├── keyword_extraction:
│   └── method: regular     ← "regular" or "bert"
└── keyword_expansion:
    └── method: glove       ← "lemmi", "glove", or "fasttext"

Tier Mapping:
  fast    = (regular, lemmi)       ← Lightweight, no downloads
  regular = (bert, glove)          ← Default, 128MB
  max     = (bert, fasttext)       ← Large, 958MB+
```

## MCP Config File Hierarchy

### Claude Code (.mcp.json)
```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp"],
      "env": {
        "CICADA_CONFIG_DIR": "~/.cicada/projects/<hash>/"
      }
    }
  }
}
```

### Cursor (.cursor/mcp.json)
```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp"],
      "env": {
        "CICADA_CONFIG_DIR": "~/.cicada/projects/<hash>/"
      }
    }
  }
}
```

### VS Code (.vscode/settings.json)
```json
{
  "mcp.servers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp"],
      "env": {
        "CICADA_CONFIG_DIR": "~/.cicada/projects/<hash>/"
      }
    }
  }
}
```

## Data Flow: `cicada status`

```
User runs: cicada status [--verbose] [--json]
  ↓
handle_status(args)
  ├─ Resolve repo_path (current directory)
  │
  ├─ Storage Checks
  │  ├─ get_storage_dir(repo_path)
  │  │  └─ Calculate hash: SHA256(resolved_path)[:16]
  │  └─ Check ~/.cicada/projects/<hash>/ exists
  │
  ├─ Configuration Checks
  │  ├─ get_config_path(repo_path)
  │  ├─ Load config.yaml
  │  └─ Extract tier (extraction_method + expansion_method)
  │
  ├─ Index Validation
  │  ├─ get_index_path(repo_path)
  │  ├─ load_index(index_path)
  │  ├─ validate_index_structure(index)
  │  └─ get_index_stats(index)
  │
  ├─ Hashes File Check
  │  └─ get_hashes_path(repo_path)
  │
  ├─ PR Index Check (optional)
  │  └─ get_pr_index_path(repo_path)
  │
  ├─ MCP Config Checks
  │  ├─ Check .mcp.json (Claude Code)
  │  ├─ Check .cursor/mcp.json (Cursor)
  │  ├─ Check .vscode/settings.json (VS Code)
  │  └─ Parse JSON and check for "cicada" entry
  │
  └─ Output Results
     ├─ [--json] → JSON format
     └─ [default] → Human-readable with checkmarks/crosses
```

## Utility Functions Map

```
cicada/utils/
├── storage.py
│   ├── get_repo_hash(repo_path)              → SHA256[:16]
│   ├── get_storage_dir(repo_path)            → ~/.cicada/projects/<hash>/
│   ├── get_index_path(repo_path)             → storage_dir/index.json
│   ├── get_config_path(repo_path)            → storage_dir/config.yaml
│   ├── get_hashes_path(repo_path)            → storage_dir/hashes.json
│   └── get_pr_index_path(repo_path)          → storage_dir/pr_index.json
│
├── index_utils.py
│   ├── load_index(path, verbose, raise)      → dict | None
│   ├── save_index(index, path, ...)          → None
│   ├── validate_index_structure(index)       → (bool, error?)
│   ├── get_index_stats(index)                → {modules, functions, public, private}
│   └── merge_indexes_incremental(...)        → merged_index
│
├── __init__.py
│   └── Exports all functions above + more
│
└── Other utils
    ├── path_utils.py        (resolve_to_repo_root, is_git_repository)
    ├── text_utils.py        (split_identifier, extract_code_identifiers)
    └── ...
```

## Module Dependencies

```
commands.py (CLI router)
├── imports clean.py
├── imports index_utils from utils
├── imports storage from utils
├── imports tier.py
└── [imports new status module]

clean.py (Reference implementation)
├── imports storage.py
├── imports utils.get_*_path functions
└── Uses json, pathlib, shutil

status.py (New - To be created)
├── imports storage.py
├── imports index_utils.py
├── imports tier.py
├── imports yaml
├── imports json
└── Uses pathlib
```

## File Checklist for `cicada status`

```
When checking a repository, look for:

Storage (~/.cicada/projects/<hash>/)
  ├─ index.json           [CRITICAL] Code index with metadata
  ├─ config.yaml          [CRITICAL] Tier configuration
  ├─ hashes.json          [OPTIONAL] Change detection tracking
  └─ pr_index.json        [OPTIONAL] GitHub PR history

Repository Root
  ├─ .mcp.json            [OPTIONAL] Claude Code config
  ├─ .cursor/mcp.json     [OPTIONAL] Cursor config
  ├─ .vscode/settings.json [OPTIONAL] VS Code config
  ├─ .gemini/mcp.json     [OPTIONAL] Gemini CLI config
  └─ .codex/mcp.json      [OPTIONAL] Codex config

Legacy (if exists)
  └─ .cicada/             [DEPRECATED] Old format
```

## Version Information Sources

```
Cicada Version can come from:
1. Index metadata: index.json → metadata.cicada_version
   Format: "0.3.1 (v0.3.1rc2/9c57cec)"
   
2. Version check module: cicada/version_check.py
   
3. Git: git describe --tags / git rev-parse HEAD
```

## Error Handling in status

```
Scenarios to handle:
1. No repository configuration at all
   └─ Status: "Not configured" (recommend: cicada install)

2. Config exists, but index missing/invalid
   └─ Status: "Needs reindexing" (recommend: cicada index)

3. Some MCP configs not set up
   └─ Status: "Partial setup" (show which editors are ready)

4. Everything good
   └─ Status: "Ready to use"

5. File permission errors
   └─ Status: "Error reading files"

6. Corrupted JSON/YAML
   └─ Status: "Invalid configuration file"
```
