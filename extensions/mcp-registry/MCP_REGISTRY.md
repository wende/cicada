# Official MCP Registry Submission Guide

## Overview

**Platform:** https://registry.modelcontextprotocol.io
**Maintainer:** Anthropic (official)
**Audience:** All MCP-compatible editors
**Submission Time:** 2-3 hours
**Approval:** Automated (with manual review for issues)
**Priority:** ⭐⭐⭐ Critical - Central discovery hub

---

## What is the MCP Registry?

The official MCP Registry is Anthropic's centralized directory for MCP servers. It functions as "an app store for MCP servers" and is the canonical source that all major editors reference.

**Benefits:**
- **Universal Discovery**: Referenced by VSCode, Cursor, Zed, Claude Code
- **API Access**: Programmatic server discovery
- **Version Management**: Track releases and updates
- **Namespace Verification**: Prevents naming conflicts

---

## Prerequisites

### Required Before Submission
- [ ] **PyPI Package**: Cicada must be published to PyPI (see [PYPI.md](../PYPI.md))
- [ ] **GitHub Repository**: Public with clear README
- [ ] **GitHub Account**: For namespace verification
- [ ] **server.json**: Metadata file (created during submission)

### Optional but Recommended
- [ ] Demo GIF or video
- [ ] Comprehensive documentation
- [ ] CHANGELOG.md
- [ ] Test coverage

---

## Step-by-Step Submission

### Step 1: Clone the Registry Repository

```bash
git clone https://github.com/modelcontextprotocol/registry.git
cd registry
```

### Step 2: Build the Publisher CLI

```bash
make publisher
# Creates ./bin/mcp-publisher
```

**Verify installation:**
```bash
./bin/mcp-publisher --help
```

### Step 3: Authenticate

**Option A: GitHub OAuth (Recommended)**
```bash
./bin/mcp-publisher auth login github
# Opens browser for OAuth flow
# Authorize the application
```

**Option B: GitHub OIDC (for CI/CD)**
```bash
# Automatically works in GitHub Actions
# No manual authentication needed
```

**Namespace Verification:**
- For `io.github.wende/cicada`: Must authenticate as `wende` on GitHub
- For `com.yourdomain/cicada`: Must verify domain ownership

### Step 4: Create server.json

**Create metadata file:**

```json
{
  "name": "cicada",
  "namespace": "io.github.wende",
  "version": "0.2.0",
  "description": "Elixir code intelligence for AI assistants - search modules, functions, git history, and more",
  "keywords": [
    "elixir",
    "phoenix",
    "code-search",
    "developer-tools",
    "mcp",
    "git-history"
  ],
  "author": {
    "name": "Wende",
    "url": "https://github.com/wende"
  },
  "license": "MIT",
  "homepage": "https://github.com/wende/cicada",
  "repository": {
    "type": "git",
    "url": "https://github.com/wende/cicada.git"
  },
  "bugs": {
    "url": "https://github.com/wende/cicada/issues"
  },
  "package": {
    "type": "pypi",
    "name": "cicada",
    "version": "0.2.0"
  },
  "installation": {
    "command": "pip install cicada",
    "setup": "cicada /path/to/project"
  },
  "tools": [
    {
      "name": "search_module",
      "description": "Find Elixir modules and view their complete API"
    },
    {
      "name": "search_function",
      "description": "Locate function definitions and see where they're called"
    },
    {
      "name": "search_module_usage",
      "description": "Find all locations where a module is used"
    },
    {
      "name": "find_pr_for_line",
      "description": "Discover which PR introduced a specific line"
    },
    {
      "name": "get_commit_history",
      "description": "Get git commit history for files or functions"
    },
    {
      "name": "get_blame",
      "description": "Get line-by-line git blame information"
    },
    {
      "name": "get_file_pr_history",
      "description": "Get all PRs that modified a file"
    },
    {
      "name": "search_by_keywords",
      "description": "Semantic search by keywords (requires opt-in)"
    },
    {
      "name": "find_dead_code",
      "description": "Find potentially unused public functions"
    }
  ],
  "categories": [
    "developer-tools",
    "code-analysis"
  ],
  "language": "elixir"
}
```

### Step 5: Publish to Registry

```bash
# Dry run first (verify metadata)
./bin/mcp-publisher publish --dry-run server.json

# Actual publish
./bin/mcp-publisher publish server.json
```

**Expected Output:**
```
✓ Authenticated as wende (via GitHub OAuth)
✓ Namespace io.github.wende verified
✓ Package cicada@0.2.0 found on PyPI
✓ Metadata validated
✓ Publishing to registry...
✓ Published io.github.wende/cicada@0.2.0

Registry URL: https://registry.modelcontextprotocol.io/v0/servers/io.github.wende/cicada
```

### Step 6: Verify Listing

```bash
# Check via API
curl https://registry.modelcontextprotocol.io/v0/servers/io.github.wende/cicada

# Expected response
{
  "name": "cicada",
  "namespace": "io.github.wende",
  "version": "0.2.0",
  "description": "...",
  ...
}
```

**Verify in browsers:**
- Registry UI: https://registry.modelcontextprotocol.io
- Search for "cicada"
- Check all fields display correctly

---

## Updating the Listing

### Publishing New Versions

```bash
# Update version in server.json
# Update version on PyPI first!

# Then publish update
./bin/mcp-publisher publish server.json

# Registry will track version history
```

### Updating Metadata Only

```bash
# Edit server.json (description, keywords, etc.)
# Keep version the same

# Re-publish
./bin/mcp-publisher publish server.json
```

---

## Namespace Strategies

### Option 1: GitHub Namespace (Recommended)
**Format:** `io.github.wende/cicada`
**Verification:** GitHub OAuth
**Pros:**
- Easy authentication
- Immediate verification
- Portable if you change domains

### Option 2: Domain Namespace
**Format:** `com.yourdomain/cicada`
**Verification:** DNS TXT record or HTTP challenge
**Pros:**
- Professional appearance
- Brand ownership
**Cons:**
- More complex verification
- Requires domain control

### Verification Process for Domains

**DNS Method:**
```bash
# Add TXT record to your domain
_mcp-verify.yourdomain.com TXT "registry-token-here"

# Verify
./bin/mcp-publisher auth verify-domain yourdomain.com
```

**HTTP Method:**
```bash
# Host file at:
https://yourdomain.com/.well-known/mcp-verify.txt
# Contains: registry-token-here

# Verify
./bin/mcp-publisher auth verify-domain yourdomain.com --method http
```

---

## Registry API Usage

### Discovery API

**Search for servers:**
```bash
curl "https://registry.modelcontextprotocol.io/v0/servers?q=elixir"
```

**Get specific server:**
```bash
curl "https://registry.modelcontextprotocol.io/v0/servers/io.github.wende/cicada"
```

**List all versions:**
```bash
curl "https://registry.modelcontextprotocol.io/v0/servers/io.github.wende/cicada/versions"
```

### Integration Examples

**VSCode Extension:**
```typescript
// Auto-detect latest version from registry
async function getLatestCicadaVersion(): Promise<string> {
    const response = await fetch(
        'https://registry.modelcontextprotocol.io/v0/servers/io.github.wende/cicada'
    );
    const data = await response.json();
    return data.version;
}
```

---

## Troubleshooting

### Issue 1: Authentication Failed

**Error:** "Not authorized for namespace io.github.wende"

**Solution:**
```bash
# Ensure you're logged into correct GitHub account
./bin/mcp-publisher auth logout
./bin/mcp-publisher auth login github
```

### Issue 2: Package Not Found on PyPI

**Error:** "Package cicada@0.2.0 not found on PyPI"

**Solution:**
- Publish to PyPI first (see [PYPI.md](../PYPI.md))
- Wait a few minutes for PyPI indexing
- Verify: `pip search cicada` or visit https://pypi.org/project/cicada/

### Issue 3: Invalid server.json

**Error:** "Validation failed: missing required field 'tools'"

**Solution:**
- Check server.json syntax (use JSON validator)
- Ensure all required fields present
- Run: `./bin/mcp-publisher validate server.json`

### Issue 4: Version Already Exists

**Error:** "Version 0.2.0 already published"

**Solution:**
- Bump version number
- Update both server.json and PyPI
- Publish new version

---

## Best Practices

### Metadata Quality
1. **Description**: Clear, concise (1-2 sentences)
2. **Keywords**: Relevant, specific (5-10 keywords)
3. **Tools**: List all available tools with descriptions
4. **Categories**: Choose appropriate categories

### Version Management
1. Follow Semantic Versioning (semver)
2. Update CHANGELOG.md with each release
3. Keep server.json version in sync with PyPI
4. Don't unpublish versions (users may depend on them)

### Documentation
1. Keep README.md up to date
2. Include installation instructions
3. Provide usage examples
4. Document all tools and parameters

---

## Monitoring & Analytics

### Registry Stats (if available)
- Downloads per version
- Installation success rate
- Most-used tools
- User feedback

### GitHub Integration
- Stars and forks
- Issue activity
- Community engagement

### PyPI Statistics
- Download counts
- Version adoption
- Geographic distribution

---

## Checklist for Submission

Before publishing to registry:

- [ ] Published to PyPI successfully
- [ ] GitHub repository is public and documented
- [ ] README.md explains installation and usage
- [ ] server.json created with all required fields
- [ ] Authenticated with GitHub OAuth
- [ ] Namespace verified
- [ ] Dry-run successful
- [ ] All tools listed with descriptions
- [ ] Keywords relevant and searchable
- [ ] License specified (MIT)
- [ ] Contact information current

---

## After Submission

### Immediate Actions
- [ ] Verify listing appears in registry
- [ ] Test installation from registry reference
- [ ] Update main README with registry badge
- [ ] Announce on social media

### Ongoing Maintenance
- [ ] Monitor registry for user feedback
- [ ] Keep versions synchronized (PyPI ↔ Registry)
- [ ] Respond to issues tagged with `[registry]`
- [ ] Update metadata as features are added

---

## Registry Badge

Add to your README.md:

```markdown
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-blue)](https://registry.modelcontextprotocol.io/v0/servers/io.github.wende/cicada)
```

---

## Resources

- **Registry Repository:** https://github.com/modelcontextprotocol/registry
- **API Documentation:** https://registry.modelcontextprotocol.io/docs
- **MCP Specification:** https://modelcontextprotocol.io
- **Community Discord:** #registry-dev channel

---

**Status:** 📋 Ready for Implementation
**Blocker:** Requires PyPI publishing first
**Priority:** High (Week 2-3 of rollout)
**Next Action:** Complete PyPI publishing, then submit to registry
