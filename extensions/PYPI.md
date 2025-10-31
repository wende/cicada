# PyPI Publishing Guide

## Overview

**Platform:** https://pypi.org (Python Package Index)
**Audience:** Python developers, package managers
**Setup Time:** 1-2 hours (first time)
**Maintenance:** Automated via GitHub Actions
**Priority:** ⭐⭐⭐ Critical - Prerequisite for MCP Registry and extensions

---

## Why Publish to PyPI?

### Benefits
1. **Standard Installation**: `pip install cicada` is familiar to all Python users
2. **Required by MCP Registry**: Official registry requires package on PyPI/npm/Docker
3. **Version Management**: PyPI handles versioning, checksums, and distribution
4. **CI/CD Integration**: Easy to integrate with deployment pipelines
5. **Trust Signal**: PyPI listing adds credibility

### Alternative: GitHub Releases
Currently using: `uv tool install git+https://github.com/wende/cicada.git@latest`

**Pros of Git:**
- No PyPI account needed
- Direct from source
- Immediate updates

**Cons of Git:**
- Slower installation
- No version discovery
- Not accepted by registries
- Less professional

**Recommendation:** Support both methods (PyPI primary, Git as alternative)

---

## Prerequisites

### Required Accounts
- [ ] PyPI account: https://pypi.org/account/register/
- [ ] TestPyPI account (for testing): https://test.pypi.org/account/register/
- [ ] GitHub account with repo access

### Required Setup
- [ ] 2FA enabled on PyPI (required for new projects)
- [ ] API tokens created (PyPI and TestPyPI)
- [ ] GitHub Secrets configured

### Required Files
- [ ] `pyproject.toml` (already exists)
- [ ] `README.md` (already exists)
- [ ] `LICENSE` (already exists - MIT)
- [ ] `CHANGELOG.md` (should exist)

---

## Step-by-Step Guide

### Step 1: Create PyPI Account

1. **Register on PyPI:**
   - Visit https://pypi.org/account/register/
   - Email: your@email.com
   - Username: wende (or your preferred)
   - Strong password + 2FA

2. **Register on TestPyPI (for testing):**
   - Visit https://test.pypi.org/account/register/
   - Use same credentials

### Step 2: Generate API Tokens

**PyPI Production Token:**
1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: "github-actions-cicada"
4. Scope: "Entire account" (or "Project: cicada" after first publish)
5. **Copy token immediately** (starts with `pypi-`)

**TestPyPI Token:**
1. Go to https://test.pypi.org/manage/account/token/
2. Same process as above
3. Token name: "github-actions-cicada-test"

**IMPORTANT:** Save both tokens securely. You won't see them again.

### Step 3: Configure GitHub Secrets

1. Go to your GitHub repo: Settings → Secrets and variables → Actions
2. Click "New repository secret"

**Add these secrets:**

| Name | Value | Purpose |
|------|-------|---------|
| `PYPI_API_TOKEN` | `pypi-...` | Production publishing |
| `TEST_PYPI_API_TOKEN` | `pypi-...` | Test publishing |

### Step 4: Verify pyproject.toml

Your `pyproject.toml` should already be correct, but verify:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "cicada"
version = "0.2.0"
description = "An Elixir module search MCP server"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Wende", email = "your@email.com"}
]
keywords = ["elixir", "mcp", "code-search", "developer-tools"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries",
    "Topic :: Software Development :: Code Generators",
]
dependencies = [
    "mcp>=0.1.0",
    "pyyaml>=6.0",
    "tree-sitter>=0.20.0",
    "tree-sitter-elixir>=0.1.0",
    "gitpython>=3.1.0",
    "spacy>=3.8.7",
    "keybert>=0.8.0",
    "rank-bm25>=0.2.2",
    "simple-term-menu>=1.6.0",
]

[project.urls]
Homepage = "https://github.com/wende/cicada"
Repository = "https://github.com/wende/cicada.git"
Issues = "https://github.com/wende/cicada/issues"
Changelog = "https://github.com/wende/cicada/blob/main/CHANGELOG.md"

[project.scripts]
cicada-mcp = "cicada.mcp_server:main"
cicada = "cicada.cli:main"
```

### Step 5: Create GitHub Actions Workflow

**Create `.github/workflows/publish-pypi.yml`:**

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      test_only:
        description: 'Publish to TestPyPI only'
        required: false
        type: boolean
        default: true

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Publish to TestPyPI
        if: github.event.inputs.test_only == 'true' || github.event_name == 'workflow_dispatch'
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.TEST_PYPI_API_TOKEN }}
        run: |
          twine upload --repository testpypi dist/*

      - name: Publish to PyPI
        if: github.event_name == 'release'
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          twine upload dist/*
```

### Step 6: Test with TestPyPI

**Manual test first (optional):**

```bash
# Build the package
python -m build

# Check the build
twine check dist/*

# Upload to TestPyPI
twine upload --repository testpypi dist/*
# Enter token when prompted
```

**Or trigger GitHub Actions:**
```bash
# Commit the workflow file
git add .github/workflows/publish-pypi.yml
git commit -m "Add PyPI publishing workflow"
git push

# Trigger workflow manually (test only)
# Go to GitHub: Actions → Publish to PyPI → Run workflow
# Check "Publish to TestPyPI only"
```

**Verify on TestPyPI:**
- Visit https://test.pypi.org/project/cicada/
- Check version, description, metadata
- Test installation:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ cicada
  ```

### Step 7: Publish to Production PyPI

**Option A: Via GitHub Release (Recommended)**

```bash
# Create git tag
git tag v0.2.0
git push origin v0.2.0

# Create GitHub Release
# Go to: https://github.com/wende/cicada/releases/new
# Tag: v0.2.0
# Title: "v0.2.0 - Initial PyPI Release"
# Description: (from CHANGELOG.md)
# Click "Publish release"

# GitHub Actions will automatically publish to PyPI
```

**Option B: Manual publish**

```bash
# Build
python -m build

# Upload to PyPI
twine upload dist/*
# Enter: __token__
# Password: pypi-YOUR-TOKEN-HERE
```

### Step 8: Verify Publication

**Check PyPI:**
- Visit https://pypi.org/project/cicada/
- Verify version, description, links
- Check that README renders correctly

**Test Installation:**
```bash
pip install cicada
cicada --version
# Should output: 0.2.0
```

**Test in fresh environment:**
```bash
python -m venv test_env
source test_env/bin/activate
pip install cicada
cicada /path/to/elixir/project
# Should work without issues
```

---

## Version Management

### Semantic Versioning

Follow semver: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 0.2.0 → 0.3.0)
- **PATCH**: Bug fixes (e.g., 0.2.0 → 0.2.1)

### Release Process

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.2.1"
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [0.2.1] - 2025-10-30
   ### Fixed
   - Bug in module search
   ### Added
   - New keyword extraction option
   ```

3. **Commit changes**:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Bump version to 0.2.1"
   git push
   ```

4. **Create tag and release**:
   ```bash
   git tag v0.2.1
   git push origin v0.2.1
   # Create GitHub Release
   # GitHub Actions will publish to PyPI
   ```

---

## Troubleshooting

### Issue 1: "Package name already exists"

**Cause:** Someone else registered "cicada"

**Solution:**
- Check https://pypi.org/project/cicada/
- If it's you: continue
- If it's someone else: choose different name (e.g., "cicada-mcp")

### Issue 2: "Invalid or non-existent authentication"

**Cause:** Wrong API token or expired

**Solution:**
```bash
# Regenerate token on PyPI
# Update GitHub secret
# Re-run workflow
```

### Issue 3: "File already exists"

**Cause:** Trying to republish same version

**Solution:**
- Bump version number
- PyPI doesn't allow overwriting releases (by design)

### Issue 4: "README rendering broken"

**Cause:** Markdown syntax not supported by PyPI

**Solution:**
- Use CommonMark syntax only
- Test with: `twine check dist/*`
- Avoid complex HTML or extensions

---

## Best Practices

### Security
- ✅ Enable 2FA on PyPI
- ✅ Use API tokens, not passwords
- ✅ Scope tokens to specific projects
- ✅ Rotate tokens annually
- ✅ Never commit tokens to repo

### Releases
- ✅ Always test on TestPyPI first
- ✅ Update CHANGELOG.md with every release
- ✅ Create Git tags for versions
- ✅ Write clear release notes
- ✅ Test installation in clean environment

### Documentation
- ✅ Keep README.md clear and concise
- ✅ Include installation instructions
- ✅ Add badges (version, downloads, license)
- ✅ Link to full documentation
- ✅ Maintain CHANGELOG.md

---

## PyPI Badges for README

Add to your README.md:

```markdown
[![PyPI version](https://badge.fury.io/py/cicada.svg)](https://badge.fury.io/py/cicada)
[![Python versions](https://img.shields.io/pypi/pyversions/cicada.svg)](https://pypi.org/project/cicada/)
[![Downloads](https://pepy.tech/badge/cicada)](https://pepy.tech/project/cicada)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

---

## Monitoring & Analytics

### PyPI Statistics
- **Downloads**: https://pepy.tech/project/cicada
- **Dependent Projects**: https://libraries.io/pypi/cicada
- **Version Adoption**: PyPI project page

### Health Metrics
- Download trends (daily/weekly/monthly)
- Version migration rate
- Issue reports per version
- Installation success rate (via user feedback)

---

## Automation Checklist

Once PyPI publishing is set up:

- [ ] GitHub Actions workflow tested
- [ ] Test publish to TestPyPI successful
- [ ] Production publish to PyPI successful
- [ ] Installation from PyPI works
- [ ] README renders correctly on PyPI
- [ ] All links in PyPI listing work
- [ ] Version badge added to README
- [ ] CHANGELOG.md maintained
- [ ] Release process documented

---

## Next Steps After PyPI

Once published to PyPI:

1. ✅ **Update installation docs** everywhere
   ```markdown
   # Old
   uv tool install git+https://github.com/wende/cicada.git@latest

   # New (primary)
   pip install cicada

   # Or with uv (faster)
   uv tool install cicada
   ```

2. ✅ **Submit to MCP Registry** (see [MCP_REGISTRY.md](mcp-registry/MCP_REGISTRY.md))

3. ✅ **Update Cursor Directory** listing with PyPI install command

4. ✅ **Announce on social media**
   - Twitter/X: "Cicada is now on PyPI!"
   - Reddit r/elixir
   - Elixir Forum

---

## Resources

- **PyPI Help:** https://pypi.org/help/
- **Packaging Guide:** https://packaging.python.org/
- **Twine Docs:** https://twine.readthedocs.io/
- **GitHub Actions for Python:** https://docs.github.com/actions/automating-builds-and-tests/building-and-testing-python

---

**Status:** 📋 Ready to Implement
**Blocker:** None (ready to go)
**Priority:** Critical (Week 2 of rollout)
**Estimated Time:** 2-3 hours (including testing)
**Next Action:** Create PyPI account, generate tokens, setup GitHub Actions
