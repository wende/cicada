---
reviewed:
- .github/workflows/publish-pypi.yml:80eeec601bed5289e99a8e2f08545307bc764ecb
---

# Publish cicada-mcp-core to PyPI

This document describes the changes made to fix the `ModuleNotFoundError` when installing `cicada-mcp` from PyPI.

## Problem

The `cicada-mcp-core` package was declared as a dependency in `pyproject.toml` but never published to PyPI. When users installed `cicada-mcp` from PyPI:

```bash
pip install cicada-mcp
# or
uv tool install cicada-mcp
```

They would get:

```
ModuleNotFoundError: No module named 'cicada_mcp_core'
```

This happened because:
1. `cicada-mcp` depends on `cicada-mcp-core` (declared in `pyproject.toml`)
2. `cicada-mcp-core` is a workspace package under `packages/cicada-mcp-core/`
3. UV's workspace feature resolves it locally during development
4. But the publish workflow only published `cicada-mcp`, not `cicada-mcp-core`
5. PyPI couldn't find `cicada-mcp-core` since it was never published

## Solution

Updated `.github/workflows/publish-pypi.yml` to publish `cicada-mcp-core` before `cicada-mcp`.

### Changes to Publish Workflow

All three publish jobs were updated:
- `test-publish` (TestPyPI)
- `publish` (PyPI after TestPyPI)
- `publish-direct` (PyPI direct)

Each job now:

1. **Builds cicada-mcp-core first**
   ```yaml
   - name: Build cicada-mcp-core
     run: |
       cd packages/cicada-mcp-core
       uv build
   ```

2. **Publishes cicada-mcp-core**
   ```yaml
   - name: Publish cicada-mcp-core to PyPI
     run: |
       cd packages/cicada-mcp-core
       uv publish --token $UV_PUBLISH_TOKEN || echo "cicada-mcp-core version may already exist"
   ```

3. **Waits for availability** (30 seconds for PyPI propagation)

4. **Then builds and publishes cicada-mcp** (which can now resolve cicada-mcp-core from PyPI)

### Package Structure (unchanged)

```
packages/
└── cicada-mcp-core/
    ├── pyproject.toml
    └── src/cicada_mcp_core/
        ├── __init__.py
        ├── base_indexer.py          # BaseIndexer ABC
        ├── formatter_interface.py   # BaseLanguageFormatter ABC
        └── utils/
            ├── __init__.py
            ├── hash_utils.py        # File hashing utilities
            └── storage.py           # Storage path utilities
```

## Files Changed

- `.github/workflows/publish-pypi.yml` - Added cicada-mcp-core build and publish steps to all jobs

## Related

- PR #225 (temporary fix by inlining BaseLanguageFormatter) - can be closed
- `codebook/tasks/202512262109-MONOREPO_SPLIT.md` - Original monorepo split design

## Verification

After the next release tag (e.g., `v0.6.1`), verify:

```bash
# cicada-mcp works standalone (BaseLanguageFormatter is inlined)
pip install cicada-mcp
python -c "from cicada.languages.formatter_interface import BaseLanguageFormatter; print('OK')"

# cicada-mcp-core is available on PyPI for cicada-scip users
pip install cicada-mcp-core
python -c "from cicada_mcp_core import BaseLanguageFormatter; print('OK')"

# cicada-scip can be installed (depends on cicada-mcp-core from PyPI)
pip install cicada-mcp[scip]
```
