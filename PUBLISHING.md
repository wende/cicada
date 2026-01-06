# Publishing & Distribution Guide

This guide is for maintainers publishing Cicada to various distribution channels.

## Distribution Channels

| Platform | Effort | Reach | Status | Guide Section |
|----------|--------|-------|--------|---------------|
| PyPI | Medium | Universal | ✅ Active | [PyPI Publishing](#pypi-publishing) |
| MCP Registry | Medium | MCP Clients | ⏳ Planned | [MCP Registry](#mcp-registry) |
| Cursor Directory | Low | 250K+ devs | ✅ Active | [Cursor](#cursor-directory) |
| VSCode Marketplace | High | Millions | 🔮 Future | [VSCode](#vscode-marketplace) |
| Zed Extensions | High | Growing | 🔮 Future | [Zed](#zed-extensions) |

---

## PyPI Publishing

### Prerequisites

- PyPI account with 2FA enabled
- TestPyPI account (for testing)
- API tokens configured
- GitHub Actions secrets set

### Publishing Workflow

#### 1. Automated via GitHub Actions

Publishing is automated on git tags:

```bash
# Bump version in pyproject.toml
vim pyproject.toml  # Update version = "0.3.0"

# Update CHANGELOG.md
vim CHANGELOG.md

# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.3.0"
git push

# Create and push tag
git tag v0.3.0
git push origin v0.3.0

# GitHub Actions automatically:
# 1. Builds package
# 2. Runs tests
# 3. Publishes to PyPI
```

#### 2. Manual Publishing (if needed)

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*

# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Verify installation
pip install --index-url https://test.pypi.org/simple/ cicada-mcp

# Publish to production PyPI
twine upload dist/*
```

### Version Management

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR:** Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR:** New features, backward compatible (e.g., 0.2.0 → 0.3.0)
- **PATCH:** Bug fixes (e.g., 0.2.0 → 0.2.1)

### Installation Options

Users can install via:

```bash
# Minimal (tree-sitter only: Elixir, Erlang)
pip install cicada-mcp

# Full (all 15 languages)
pip install cicada-mcp[scip]

# Development
pip install cicada-mcp[dev]
```

---

## MCP Registry

### Overview

**Platform:** https://registry.modelcontextprotocol.io
**Audience:** All MCP-compatible editors
**Status:** ⏳ Planned for Phase 2

### Requirements

- PyPI package published
- GitHub repository public
- Namespace verification

### Submission Process

1. Install MCP publisher CLI:
   ```bash
   npm install -g @modelcontextprotocol/mcp-publisher
   ```

2. Create `server.json`:
   ```json
   {
     "name": "cicada",
     "description": "Code intelligence for Elixir and 14 other languages",
     "repository": "https://github.com/wende/cicada",
     "package": {
       "type": "pypi",
       "name": "cicada-mcp"
     }
   }
   ```

3. Authenticate and publish:
   ```bash
   mcp-publisher login
   mcp-publisher publish server.json
   ```

---

## Cursor Directory

### Overview

**Platform:** https://cursor.directory/mcp
**Audience:** 250,000+ monthly active developers
**Status:** ✅ Active

### Submission

1. Visit https://cursor.directory/mcp/new
2. Fill out form:
   - **Name:** Cicada
   - **Description:** "Code intelligence for Elixir and 14 other languages"
   - **Category:** Developer Tools
   - **Install:** `uv tool install cicada-mcp`
   - **Setup:** `cicada .`
   - **Repository:** https://github.com/wende/cicada

### Update Process

To update the listing:
1. Edit via Cursor Directory admin panel
2. Or resubmit with updated information

---

## VSCode Marketplace

### Overview

**Platform:** https://marketplace.visualstudio.com
**Audience:** Millions of VSCode users
**Status:** 🔮 Future (Month 2+)

### Requirements

- TypeScript extension wrapper
- Azure DevOps publisher account
- Extension icon (128x128 PNG)
- Screenshots and demo

### Architecture

VSCode extensions work by:
1. Extension registers MCP server in settings
2. VSCode's MCP support loads the server
3. Extension provides UI for setup/config

### Development Effort

- **Initial:** 6-8 hours (extension scaffold, packaging, submission)
- **Updates:** 1-2 hours (version updates)
- **Maintenance:** Moderate (compatibility testing)

### Implementation Steps

1. Generate extension scaffold:
   ```bash
   npm install -g yo generator-code
   yo code  # Select "New Extension (TypeScript)"
   ```

2. Update `package.json` with MCP registration
3. Create extension logic for server setup
4. Package extension: `vsce package`
5. Publish: `vsce publish`

---

## Zed Extensions

### Overview

**Platform:** https://zed.dev/extensions
**Audience:** Growing Zed community
**Status:** 🔮 Future (Month 2+)

### Requirements

- Rust wrapper (compiled to WASM)
- Fork of zed-industries/extensions
- Rust toolchain knowledge

### Architecture

Zed extensions are Rust code compiled to WebAssembly:
1. Extension defines MCP server in `extension.toml`
2. `context_server_command` method returns start command
3. Zed spawns the MCP server process

### Development Effort

- **Initial:** 6-8 hours (Rust wrapper, testing, PR submission)
- **Updates:** 1-2 hours (version bumps)
- **Maintenance:** Low (handled by Zed maintainers)

### Implementation Steps

1. Fork https://github.com/zed-industries/extensions
2. Create `extensions/cicada/` directory
3. Write Rust wrapper with `zed_extension_api`
4. Submit PR to zed-industries/extensions

---

## Rollout Strategy

### Phase 1: Quick Wins (Completed)

✅ **PyPI Publishing** - Package available
✅ **Cursor Directory** - Listed for discovery
✅ **Documentation** - Installation guides complete

**Reach:** 250,000+ developers

### Phase 2: Central Registry (Planned)

⏳ **Official MCP Registry** - Submit to Anthropic registry

**Estimated effort:** 2-3 hours
**Reach:** All MCP-compatible editors

### Phase 3: Native Extensions (Future)

🔮 **VSCode Extension** - Full marketplace extension
🔮 **Zed Extension** - Rust wrapper

**Estimated effort:** 16-20 hours total
**Reach:** Millions of additional users

---

## Distribution Best Practices

### Before Each Release

- [ ] Run full test suite: `make test`
- [ ] Update `CHANGELOG.md` with changes
- [ ] Bump version in `pyproject.toml`
- [ ] Test installation in clean environment
- [ ] Verify all links in README work

### After Publishing

- [ ] Verify package on PyPI
- [ ] Test installation: `pip install cicada-mcp`
- [ ] Update documentation if needed
- [ ] Announce on relevant channels
- [ ] Monitor GitHub issues for problems

### Security

- ✅ Enable 2FA on PyPI
- ✅ Use API tokens, not passwords
- ✅ Scope tokens to specific projects
- ✅ Never commit tokens to repository
- ✅ Rotate tokens annually

---

## Monitoring & Analytics

### PyPI Statistics

- **Downloads:** https://pepy.tech/project/cicada-mcp
- **Dependent Projects:** https://libraries.io/pypi/cicada-mcp

### Health Metrics

- Download trends (daily/weekly/monthly)
- Version adoption rate
- Issue reports per version
- Installation success rate (via user feedback)

### Success Criteria

- >100 active users per month
- >90% successful installations
- >80% positive user feedback
- <5 critical issues per release

---

## Troubleshooting

### Issue: Package Not Found After Publishing

**Cause:** PyPI caching or indexing delay

**Solution:** Wait 5-10 minutes, then retry

### Issue: Version Already Exists

**Cause:** Trying to republish same version

**Solution:** PyPI doesn't allow overwriting. Bump version number.

### Issue: Token Authentication Failed

**Cause:** Expired or invalid API token

**Solution:** Regenerate token on PyPI, update GitHub secrets

---

## Related Documentation

- [RELEASE.md](RELEASE.md) - Detailed release process and checklist
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines
- Development guides in `extensions/` (to be archived)

---

## Questions?

For distribution-related questions:
- Open GitHub issue with `[distribution]` prefix
- Tag as `maintenance` or `publishing`
- Contact: @wende
