# Claude Code Integration Guide

## Overview

**Platform:** Claude Code CLI (built-in MCP support)
**Audience:** Claude Code users
**Setup Time:** ~5 minutes
**Complexity:** ⭐ Easy - Direct configuration
**Maintenance:** Manual updates

---

## What is Claude Code?

Claude Code is Anthropic's official CLI tool that provides a conversational interface for software development. It has native MCP (Model Context Protocol) support, making Cicada integration straightforward.

**Built-in MCP Features:**
- Loads MCP servers from `.mcp.json` automatically
- No extension marketplace needed
- Works out of the box

---

## Installation

For installation instructions, see **[INSTALL.md](INSTALL.md)**.

Quick start:
```bash
cd /path/to/elixir/project
uvx cicada claude
```

---

## Configuration Details

### .mcp.json Format

Cicada automatically creates this file during setup:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-server",
      "env": {
        "CICADA_REPO_PATH": "/absolute/path/to/project"
      }
    }
  }
}
```

### Manual Configuration (Advanced)

If you need to configure manually or use a different setup:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-server",
      "args": [],
      "env": {
        "CICADA_REPO_PATH": "/absolute/path/to/project"
      }
    }
  }
}
```

**Command Options:**
- **Option 1 (Recommended):** `cicada-server` (if in PATH)
- **Option 2:** `/absolute/path/to/.local/bin/cicada-server`
- **Option 3:** `python /path/to/cicada/cicada/mcp_server.py`

---

## Troubleshooting

### Issue 1: "cicada-server: command not found"

**Solution:** Add `~/.local/bin` to PATH

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

### Issue 2: "Config file not found: .cicada/config.yaml"

**Solution:** Run setup in project directory

```bash
cd /path/to/project
cicada .
```

### Issue 3: MCP Server Won't Start

**Check cicada-server is accessible:**
```bash
which cicada-server
# Should output: /home/user/.local/bin/cicada-server
```

**Check index exists:**
```bash
ls .cicada/
# Should see: config.yaml, index.json
```

**Check .mcp.json is valid:**
```bash
cat .mcp.json
# Verify JSON syntax is correct
```

### Issue 4: Tools Work But Return Empty Results

**Solution:** Re-index the project

```bash
cicada index
```

---

## Usage Examples

### Module Search
```
> Show me the MyApp.Accounts.User module

Returns:
- Module documentation
- All public functions with signatures
- Type specifications
- Line numbers
```

### Function Search
```
> Where is authenticate/2 called?

Returns:
- Function definition with docs
- All call sites with line numbers
- Calling functions
- Code context
```

### Git History
```
> Who wrote this code at line 142 in lib/my_app/accounts/user.ex?

Returns:
- PR that introduced the line
- Author and date
- PR description
- Review comments
```

### Module Usage
```
> Show me everywhere MyApp.Auth is used

Returns:
- Modules that import/alias it
- Function calls with line numbers
- Impact analysis for refactoring
```

---

## Advanced Configuration

### Multiple Projects

If you work on multiple Elixir projects, each needs its own setup:

```bash
# Project A
cd ~/projects/project-a
cicada .

# Project B
cd ~/projects/project-b
cicada .
```

Each project gets its own `.mcp.json` configuration.

### Custom MCP Configuration

You can add Cicada alongside other MCP servers:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-server",
      "env": {
        "CICADA_REPO_PATH": "/path/to/project"
      }
    },
    "other-mcp-server": {
      "command": "other-server",
      "args": ["--flag"]
    }
  }
}
```

### Environment Variables

Cicada respects these environment variables:

- **CICADA_REPO_PATH**: Project root directory (set automatically)
- **CICADA_CONFIG_PATH**: Custom config.yaml location (optional)

---

## Verification Checklist

After setup, verify everything works:

- [ ] `which cicada-server` returns a path
- [ ] `.cicada/config.yaml` exists
- [ ] `.cicada/index.json` exists
- [ ] `.mcp.json` exists and is valid JSON
- [ ] Claude Code starts without errors
- [ ] Can query for existing modules
- [ ] Can find function definitions
- [ ] Git tools work (if in git repo)

---

## Performance Tips

### Fast Startup
- Keep index up to date: `cicada index` after major changes
- Use incremental indexing (automatic by default)
- Index is loaded once at MCP server startup

### Large Codebases
For projects with 1000+ files:
- Initial indexing may take 20-30 seconds
- Subsequent runs are fast (incremental)
- Consider excluding build artifacts from indexing

### Keyword Search (Optional)
Enable semantic search when ready:
```bash
cicada index --extract-keywords --fast
```

---

## Integration with Other Tools

### With Git Hooks
Add to `.git/hooks/post-checkout`:
```bash
#!/bin/bash
# Re-index after branch changes
cicada index
```

### With CI/CD
Generate index as part of onboarding:
```bash
# In CI script
uv tool install git+https://github.com/wende/cicada.git@v0.1.4
cicada claude
# Commit .mcp.json to repo
```

### With Docker
```dockerfile
FROM elixir:1.15

# Install uv and cicada
RUN pip install uv
RUN uv tool install git+https://github.com/wende/cicada.git@v0.1.4

# Add to PATH
ENV PATH="/root/.local/bin:$PATH"

# Setup project
WORKDIR /app
COPY . .
RUN cicada claude
```

---

## Documentation for Team Onboarding

### README Section Template

Add this to your project README:

```markdown
## AI Assistant Setup (Claude Code + Cicada)

This project uses Cicada for enhanced AI code intelligence.

### Quick Setup
```bash
uvx cicada claude
```

This one command will index your project and configure Claude Code automatically.

### Manual Installation (Alternative)
1. Install Cicada:
   ```bash
   uv tool install git+https://github.com/wende/cicada.git@v0.1.4
   ```

2. Setup the project:
   ```bash
   cicada claude
   ```

3. Start Claude Code:
   ```bash
   claude-code
   ```

### Usage
Ask Claude Code:
- "Show me the User module"
- "Where is this function called?"
- "Who wrote this code?"

See [Cicada documentation](https://github.com/wende/cicada) for more features.
```

---

## Resources

- **Claude Code Docs:** https://docs.claude.com/claude-code
- **MCP Specification:** https://modelcontextprotocol.io
- **Cicada Repository:** https://github.com/wende/cicada
- **Issue Tracker:** https://github.com/wende/cicada/issues

---

## Support

For Claude Code-specific issues:
- Check Claude Code documentation
- Verify .mcp.json format
- Ensure cicada-server is in PATH

For Cicada issues:
- Open GitHub issue with `[claude-code]` prefix
- Include:
  - OS and shell version
  - Claude Code version
  - Cicada version
  - .mcp.json contents (sanitized)
  - Error messages

---

**Status:** ✅ Fully Supported
**Priority:** High (native integration)
**Maintenance:** Documentation only (no code needed)
**Next Action:** Add Claude Code section to main README
