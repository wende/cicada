# Installing Cicada for Claude Code

This guide provides step-by-step instructions for installing Cicada MCP server in Claude Code.

---

## Prerequisites

- **Claude Code** CLI installed
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- An **Elixir project** to analyze

---

## Installation Methods

### Method 1: Quick Start (Recommended)

The fastest way to get started with Cicada in Claude Code:

```bash
cd /path/to/elixir/project
uvx cicada claude
```

This single command will:
- Index your Elixir repository with keyword extraction
- Store index files in `~/.cicada/projects/<hash>/` (outside your repo)
- Create `.mcp.json` in your project root
- Automatically configure the optimal command for your system

**After setup completes:**
1. Start Claude Code in your project directory
2. Cicada tools are automatically available
3. Try asking: "Show me the User module"

---

### Method 2: Using `claude mcp add` (Native CLI)

If Claude Code supports the `mcp add` command, you can add Cicada directly:

```bash
# If you have cicada installed permanently
claude mcp add cicada --command cicada-server --env CICADA_REPO_PATH=/path/to/project

# Or using uvx (one-time run)
claude mcp add cicada --command uvx --args "cicada,claude" --cwd /path/to/project
```

**Note:** This method requires cicada to be installed first or uses uvx for on-demand execution.

---

### Method 3: Permanent Installation

For the best performance and access to all features:

#### Step 1: Install Cicada

```bash
uv tool install git+https://github.com/wende/cicada.git@v0.1.4
```

#### Step 2: Add to PATH (if needed)

Ensure `~/.local/bin` is in your PATH:

```bash
# For bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# For fish
fish_add_path ~/.local/bin
```

#### Step 3: Setup Your Project

```bash
cd /path/to/elixir/project
cicada claude
```

This creates:
- `~/.cicada/projects/<hash>/` directory with index files
- `~/.cicada/projects/<hash>/config.yaml` with settings
- `.mcp.json` with MCP server configuration in your project root

#### Step 4: Start Claude Code

```bash
# In your project directory
claude-code

# Or specify project explicitly
claude-code --project /path/to/elixir/project
```

Claude Code will automatically detect and load the MCP server from `.mcp.json`.

**Benefits of permanent installation:**
- Faster MCP server startup
- Access to advanced indexing options
- PR indexing with `cicada-index-pr`
- Better keyword extraction with larger spaCy models

---

### Method 4: Manual Configuration

For advanced users who want full control:

#### Step 1: Install Cicada

```bash
uv tool install git+https://github.com/wende/cicada.git@v0.1.4
```

#### Step 2: Index Your Project

```bash
cd /path/to/elixir/project
cicada-index . --output ~/.cicada/projects/<project>/index.json --extract-keywords
```

#### Step 3: Create `.mcp.json` Manually

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "cicada-server",
      "env": {
        "CICADA_REPO_PATH": "/absolute/path/to/project",
        "CICADA_CONFIG_DIR": "/absolute/path/to/.cicada/projects/<hash>"
      }
    }
  }
}
```

#### Step 4: Start Claude Code

```bash
claude-code
```

---

## Testing Your Installation

After setup, verify everything works by asking Claude Code:

```
> Show me the User module
> Where is create_user/2 called?
> Who wrote this line of code?
```

You should see Cicada responding with module information, function call sites, and git history.

---

## Troubleshooting

### Issue: "cicada-server: command not found"

**Solution:** Add `~/.local/bin` to PATH

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

### Issue: "Config file not found"

**Solution:** Run setup in project directory

```bash
cd /path/to/project
cicada claude
```

### Issue: MCP Server Won't Start

**Check cicada-server is accessible:**
```bash
which cicada-server
# Should output: /home/user/.local/bin/cicada-server
```

**Check index exists:**
```bash
ls ~/.cicada/projects/
# Should see directories with hash names
```

**Check .mcp.json is valid:**
```bash
cat .mcp.json
# Verify JSON syntax is correct
```

### Issue: Tools Work But Return Empty Results

**Solution:** Re-index the project

```bash
cicada-index . --extract-keywords
```

---

## Next Steps

- See [CLAUDE_CODE.md](CLAUDE_CODE.md) for usage examples and advanced configuration
- Check the [main documentation](../../README.md) for all available features
- Join the discussion on [GitHub Issues](https://github.com/wende/cicada/issues)
