# Cicada MCP Extensions & Distribution

This directory contains documentation and resources for distributing Cicada across various MCP platforms and extension marketplaces.

## 📦 Distribution Channels

### 1. Cursor Directory
**Platform:** https://cursor.directory/mcp
**Audience:** 250,000+ monthly active developers
**Complexity:** ⭐ Easy
**Time to Publish:** ~30 minutes
**Guide:** [cursor/CURSOR.md](cursor/CURSOR.md)

**Pros:**
- Largest immediate reach
- Simple submission form
- No packaging required
- Fast approval

**Cons:**
- Limited customization
- No built-in update mechanism
- Users must install via command line

---

### 2. Official MCP Registry
**Platform:** https://registry.modelcontextprotocol.io
**Audience:** Central hub for all MCP clients
**Complexity:** ⭐⭐ Medium
**Time to Publish:** 2-3 hours
**Guide:** [mcp-registry/MCP_REGISTRY.md](mcp-registry/MCP_REGISTRY.md)

**Pros:**
- Official Anthropic-maintained registry
- Referenced by all major editors
- API-based discovery
- Version management

**Cons:**
- Requires PyPI or npm package
- Namespace verification needed
- More complex submission process

---

### 3. VSCode Marketplace
**Platform:** https://marketplace.visualstudio.com
**Audience:** Millions of VSCode users
**Complexity:** ⭐⭐⭐ Hard
**Time to Publish:** 6-8 hours (initial), 1-2 hours (updates)
**Guide:** [vscode/VSCODE.md](vscode/VSCODE.md)

**Pros:**
- Largest developer audience
- Native extension installation
- Built-in updates
- Professional presentation

**Cons:**
- Requires TypeScript extension wrapper
- Azure DevOps publisher account needed
- Most complex packaging
- Ongoing maintenance burden

---

### 4. Zed Extensions
**Platform:** https://zed.dev/extensions
**Audience:** Growing Zed community
**Complexity:** ⭐⭐⭐ Hard
**Time to Publish:** 6-8 hours
**Guide:** [zed/ZED.md](zed/ZED.md)

**Pros:**
- Native Zed integration
- Fast-growing editor
- Modern developer audience

**Cons:**
- Requires Rust wrapper
- Must fork zed-industries/extensions
- Smaller audience (currently)
- Rust expertise needed

---

### 5. Claude Code (Built-in MCP)
**Platform:** Claude Code CLI
**Audience:** Claude Code users
**Complexity:** ⭐ Easy
**Time to Publish:** N/A (user-installed)
**Guide:** [claude-code/CLAUDE_CODE.md](claude-code/CLAUDE_CODE.md)

**Pros:**
- Built-in MCP support
- No marketplace submission
- Direct .mcp.json configuration

**Cons:**
- Manual installation by users
- No discovery mechanism
- Relies on documentation

---

## 🎯 Recommended Rollout Strategy

### Phase 1: Quick Wins (Week 1)
1. ✅ **Cursor Directory** - Submit listing (30 min)
2. ✅ **Claude Code Documentation** - Write installation guide (2 hours)

**Estimated Reach:** 250,000+ developers

### Phase 2: Central Registry (Week 2-3)
3. ⏳ **PyPI Publishing** - Publish cicada package (4-6 hours)
4. ⏳ **Official MCP Registry** - Submit to Anthropic registry (2-3 hours)

**Estimated Reach:** All MCP-compatible editors

### Phase 3: Native Extensions (Month 2+)
5. 🔮 **VSCode Extension** - Full marketplace extension (8-10 hours initial)
6. 🔮 **Zed Extension** - Rust wrapper (8-10 hours initial)

**Estimated Reach:** Millions of additional users

---

## 📊 Comparison Matrix

| Platform | Effort | Reach | Updates | Discoverability | Native UX |
|----------|--------|-------|---------|-----------------|-----------|
| Cursor Directory | Low | High | Manual | High | Medium |
| MCP Registry | Medium | Universal | Automatic | High | N/A |
| VSCode | High | Very High | Automatic | Very High | Excellent |
| Zed | High | Medium | Automatic | High | Excellent |
| Claude Code | Low | Medium | Manual | Low | Good |

---

## 🛠️ Prerequisites by Platform

### All Platforms
- ✅ Working MCP server implementation
- ✅ Documentation (README, usage examples)
- ✅ Test coverage
- ✅ Git repository (GitHub)

### Cursor Directory
- ✅ None (uses git URL directly)

### MCP Registry
- ⚠️ PyPI package (or npm/Docker)
- ⚠️ GitHub account (for namespace verification)

### VSCode Marketplace
- ⚠️ PyPI package (recommended)
- ⚠️ TypeScript/Node.js knowledge
- ⚠️ Azure DevOps account
- ⚠️ Extension icon/logo

### Zed Extensions
- ⚠️ Rust knowledge
- ⚠️ Fork of zed-industries/extensions repo

### Claude Code
- ✅ None (user-configurable)

---

## 📝 Additional Resources

- **MVP Strategy:** [MVP.md](MVP.md) - Minimal viable extension plan
- **PyPI Publishing:** [PYPI.md](PYPI.md) - Package publishing guide
- **Assets:** [assets/](assets/) - Logos, icons, screenshots
- **Testing:** See individual platform guides for test checklists

---

## 🤝 Contributing

When adding new platform documentation:
1. Create subdirectory under `extensions/`
2. Add platform-specific guide (PLATFORM.md)
3. Update this README with platform details
4. Add to comparison matrix
5. Update rollout strategy if applicable

---

## 📞 Support

For questions about distribution strategy:
- Open GitHub issue with `[extensions]` prefix
- Tag as `documentation` or `distribution`

---

**Last Updated:** 2025-10-29
**Cicada Version:** 0.2.0
**Status:** In Development
