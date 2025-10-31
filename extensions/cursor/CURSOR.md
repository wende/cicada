# Cursor Directory Listing Guide

## Overview

**Platform:** https://cursor.directory/mcp
**Audience:** 250,000+ monthly active developers
**Submission Time:** ~30 minutes
**Approval Time:** Usually within 24-48 hours
**Maintenance:** Manual updates required

---

## Prerequisites

Before submitting to Cursor Directory:

- [ ] Working MCP server (cicada-mcp)
- [ ] GitHub repository with clear README
- [ ] Installation command tested and working
- [ ] Logo/icon (recommended, 512x512 PNG)
- [ ] Demo GIF or screenshots (optional but helpful)

---

## Submission Process

### Step 1: Prepare Metadata

Gather the following information:

**Required:**
- **Name:** Cicada
- **Tagline:** "Elixir codebase intelligence for AI assistants"
- **Category:** Developer Tools
- **Installation Command:** `uv tool install git+https://github.com/wende/cicada.git@latest`
- **Setup Command:** `cicada .`
- **GitHub URL:** https://github.com/wende/cicada
- **Description:** (see below)

**Optional but Recommended:**
- Logo (512x512 PNG)
- Demo GIF showing usage
- Screenshots of results
- Tags: elixir, mcp, code-search, developer-tools

### Step 2: Write Description

**Template:**
```markdown
Cicada is an MCP server that provides intelligent code search and analysis for Elixir projects.

## Features
- **Fast Module Search**: Find any Elixir module and view its complete API
- **Function Discovery**: Locate function definitions and see where they're called
- **Call Site Analysis**: Understand function usage patterns with code context
- **Git Integration**: Discover PR attribution, commit history, and authorship
- **Dead Code Detection**: Find potentially unused functions
- **Zero Configuration**: Index your codebase in seconds

## Quick Start
```bash
# Install
uv tool install git+https://github.com/wende/cicada.git@latest

# Setup your project
cicada /path/to/elixir/project

# Restart Cursor to load the MCP server
```

## Usage
Ask Cursor AI:
- "Show me the User module"
- "Where is authenticate/2 called?"
- "Who wrote this line of code?"
- "Find all usages of MyApp.Accounts"

Works with any Elixir/Phoenix project!
```

### Step 3: Submit

1. **Navigate to:** https://cursor.directory/mcp/new

2. **Fill out form:**
   - Title: Cicada
   - Slug: cicada
   - Description: (paste from above)
   - GitHub URL: https://github.com/wende/cicada
   - Installation command: `uv tool install git+https://github.com/wende/cicada.git@latest`
   - Setup command: `cicada .`
   - Category: Developer Tools
   - Tags: elixir, mcp, code-search
   - Logo: Upload 512x512 PNG

3. **Review and Submit**

4. **Wait for approval** (usually 24-48 hours)

### Step 4: Verify Listing

Once approved:
1. Visit https://cursor.directory/mcp/cicada
2. Test the installation command
3. Verify all links work
4. Check that description renders correctly

---

## Installation Instructions for Users

Once listed, users can install Cicada by:

### Option 1: From Cursor Directory (Recommended)
1. Visit https://cursor.directory/mcp
2. Search for "Cicada"
3. Click "Install"
4. Follow the installation command shown

### Option 2: Manual Installation
```bash
# 1. Install Cicada
uv tool install git+https://github.com/wende/cicada.git@latest

# 2. Setup your Elixir project
cd /path/to/elixir/project
cicada .

# 3. Restart Cursor
# The MCP server will auto-start via .mcp.json
```

### Configuration

Cicada creates `.mcp.json` automatically in your project root:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-mcp",
      "env": {
        "CICADA_REPO_PATH": "/absolute/path/to/project"
      }
    }
  }
}
```

**Important:** Ensure `~/.local/bin` is in your PATH for the `cicada-mcp` command to work.

---

## Troubleshooting Common Issues

### Issue 1: "cicada-mcp: command not found"

**Cause:** `~/.local/bin` not in PATH

**Solution:**
```bash
# Add to ~/.bashrc, ~/.zshrc, or equivalent:
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

### Issue 2: "Config file not found: .cicada/config.yaml"

**Cause:** User skipped the setup step

**Solution:**
```bash
cd /path/to/project
cicada .
# Restart Cursor
```

### Issue 3: MCP server won't start in Cursor

**Cause:** Invalid `.mcp.json` or missing index

**Solution:**
```bash
# Re-run setup
cd /path/to/project
cicada .

# Check that .mcp.json was created
cat .mcp.json

# Verify index exists
ls .cicada/index.json
```

### Issue 4: Tools work but results are empty

**Cause:** Index is stale or corrupted

**Solution:**
```bash
# Re-index
cicada index

# Restart Cursor
```

---

## Updating the Listing

To update your Cursor Directory listing:

### Minor Updates (description, tags)
1. Contact Cursor Directory maintainers
2. Submit PR to their repository (if open source)
3. Or use the "Edit" button if available on the listing page

### Major Updates (new version)
1. Update the installation command with new version tag
2. Update description with new features
3. Submit update request

**Note:** Cursor Directory may not support direct edits; check their documentation for the current update process.

---

## Promotion Strategy

### Week 1: Launch
1. **Announce on social media**
   - Twitter/X: "Cicada is now on Cursor Directory! 🚀"
   - Reddit r/elixir: Post about Cursor integration
   - Elixir Forum: Announce availability

2. **Update main README.md**
   ```markdown
   ## Installation

   ### Via Cursor Directory (Recommended)
   Visit [cursor.directory/mcp/cicada](https://cursor.directory/mcp/cicada) and click "Install".

   ### Via Command Line
   ```bash
   uv tool install git+https://github.com/wende/cicada.git@latest
   ```

3. **Create demo video**
   - Record 2-minute demo showing key features
   - Upload to YouTube
   - Embed in GitHub README

### Ongoing
- Monitor Cursor Directory analytics (if available)
- Respond to user comments/reviews
- Update listing with new features
- Share user testimonials

---

## Metrics to Track

### Installation Metrics
- Number of views on Cursor Directory listing
- Click-through rate to GitHub
- Installation command copy rate
- GitHub stars growth

### Usage Metrics
- GitHub issues related to Cursor
- Community mentions of Cursor + Cicada
- Success rate of installations (survey users)

### Quality Metrics
- User ratings on Cursor Directory (if available)
- Positive vs negative feedback ratio
- Feature requests vs bug reports

---

## Best Practices

### Listing Optimization
1. **Use Keywords:** Include "Elixir", "Phoenix", "MCP", "code search" in description
2. **Show Value Fast:** Lead with key benefits, not technical details
3. **Clear Instructions:** Make installation foolproof
4. **Visual Appeal:** Use logo, GIFs, screenshots
5. **Update Regularly:** Keep description current with new features

### User Support
1. **Monitor GitHub Issues:** Tag Cursor-specific issues
2. **Respond Quickly:** Aim for <24 hour response time
3. **Document Solutions:** Add to FAQ/troubleshooting
4. **Be Proactive:** Update docs before users ask

### Community Building
1. **Engage on Cursor Discord:** Answer questions
2. **Share Tips:** Post advanced usage patterns
3. **Highlight Users:** Retweet user success stories
4. **Gather Feedback:** Survey users for improvements

---

## Example Listing (Reference)

**Title:** Cicada - Elixir Code Intelligence

**Description:**
Powerful MCP server for Elixir developers using Cursor AI. Search modules, find function calls, discover PRs, and analyze code instantly.

**Key Features:**
✨ Instant module and function search
🔍 Call site analysis with code context
📜 Git history and PR attribution
🎯 Dead code detection
⚡ Lightning-fast indexing (<10s)

**Installation:**
```bash
uv tool install git+https://github.com/wende/cicada.git@latest
cicada /path/to/project
```

**Perfect for:**
- Phoenix developers
- Elixir code maintainers
- Teams onboarding new developers
- Anyone navigating large Elixir codebases

**Tags:** #elixir #phoenix #mcp #code-search #developer-tools

---

## Checklist for Submission

Before submitting, verify:

- [ ] Installation command works on fresh system
- [ ] GitHub README is clear and up-to-date
- [ ] Logo is high quality (512x512 PNG)
- [ ] Description is compelling and accurate
- [ ] All links are valid
- [ ] Troubleshooting section in README
- [ ] Demo GIF or video available
- [ ] Tested on Cursor specifically
- [ ] .mcp.json format documented
- [ ] License file present (MIT)

---

## Post-Submission Checklist

After approval:

- [ ] Verify listing appears correctly
- [ ] Test installation from Cursor Directory
- [ ] Announce on social media
- [ ] Update main README with Cursor Directory link
- [ ] Monitor GitHub issues for Cursor-specific problems
- [ ] Track metrics (stars, downloads, feedback)
- [ ] Plan first update (add new features)

---

## Contact & Support

**Cursor Directory Issues:**
- Check Cursor Directory documentation
- Contact their support team
- Submit PR to their repo (if open source)

**Cicada Issues:**
- GitHub Issues: https://github.com/wende/cicada/issues
- Tag with `[cursor]` prefix

---

**Status:** 📝 Ready for Submission
**Priority:** High (250K+ developer reach)
**Estimated Time:** 30 minutes
**Next Action:** Gather logo and demo assets
