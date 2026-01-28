---
reviewed:
- .github/workflows/publish-pypi.yml
- cicada/core/__init__.py
- cicada/core/base_indexer.py
- cicada/core/hash_utils.py
- cicada/core/storage.py
- packages/cicada-scip/pyproject.toml
- packages/cicada-scip/src/cicada_scip/indexer.py
- packages/cicada-scip/src/cicada_scip/formatter.py
---

# Consolidate cicada-core into cicada-mcp

This document describes the changes made to fix the `ModuleNotFoundError` when installing `cicada-mcp` from PyPI.

## Problem

The `cicada-core` package was declared as a dependency but:
1. Was never published to PyPI
2. The name `cicada-core` is already taken on PyPI by another project (a CI/CD tool)

When users installed `cicada-mcp` from PyPI, they would get:
```
ModuleNotFoundError: No module named 'cicada_core'
```

## Solution

Instead of publishing a separate `cicada-core` package, we consolidated all shared code into `cicada-mcp` directly:

1. **Created `cicada/core/` module** with all shared code:
   - `base_indexer.py` - BaseIndexer ABC
   - `hash_utils.py` - File hashing for incremental indexing
   - `storage.py` - Storage path utilities
   - `__init__.py` - Exports all utilities

2. **Updated `cicada-scip`** to import from `cicada.core` instead of `cicada_core`

3. **Updated `cicada-scip` dependency** from `cicada-core>=0.1.0` to `cicada-mcp>=0.6.0`

4. **Removed `cicada-core`** from workspace and publish workflow

### New Package Structure

```
cicada/
├── core/
│   ├── __init__.py          # Exports all shared utilities
│   ├── base_indexer.py      # BaseIndexer ABC
│   ├── hash_utils.py        # File hashing utilities
│   └── storage.py           # Storage path utilities
└── languages/
    └── formatter_interface.py  # BaseLanguageFormatter (canonical source)
```

## Files Changed

- `cicada/core/` - New module with consolidated shared code
- `cicada/languages/formatter_interface.py` - Updated comment
- `packages/cicada-scip/pyproject.toml` - Depends on cicada-mcp instead of cicada-core
- `packages/cicada-scip/src/cicada_scip/indexer.py` - Import from cicada.core
- `packages/cicada-scip/src/cicada_scip/formatter.py` - Import from cicada.core
- `pyproject.toml` - Removed cicada-core from workspace
- `.github/workflows/publish-pypi.yml` - Removed cicada-core publishing

## Verification

After the next release:

```bash
# cicada-mcp works standalone
pip install cicada-mcp
python -c "from cicada.core import BaseIndexer, BaseLanguageFormatter; print('OK')"

# cicada-scip can be installed (now depends on cicada-mcp)
pip install cicada-mcp[scip]
```
