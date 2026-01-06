# Installation

This guide provides step-by-step instructions for installing Cicada in your preferred AI coding editor.

## Quick Start

The fastest way to get started:

```bash
# Install Cicada
uv tool install cicada-mcp

# Navigate to your project and initialize
cd /path/to/your/project
cicada .
```

This creates an index and configures the MCP server for your editor.

---

## Prerequisites

- **Python 3.10+** (managed automatically by `uv`)
- **uv package manager** ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- A supported project (Elixir, Python, or 13 other languages - see [Language Support](LANGUAGE_SUPPORT.md))

---

## Editor Comparison

Choose your editor below for specific installation instructions:

| Editor | Setup Time | Complexity | Auto-Discovery | Best For |
|--------|------------|------------|----------------|----------|
| [Claude Code](#claude-code) | 2 min | ⭐ Easy | Automatic | CLI users, quick setup |
| [Cursor](#cursor) | 2 min | ⭐ Easy | Automatic | Most users, fastest start |
| [VS Code](#vs-code-cline) | 3 min | ⭐⭐ Medium | Manual config | VSCode ecosystem |
| [Zed](#zed) | 5 min | ⭐⭐⭐ Advanced | Extension required | Zed power users |

---

## Claude Code

**Recommended for:** CLI users who want the fastest setup

### Quick Install

```bash
cd /path/to/your/project
uvx cicada claude
```

This single command:
- Indexes your project
- Creates `.mcp.json` configuration
- Stores index in `~/.cicada/projects/<hash>/`
- Automatically configures the optimal command for your system

### Alternative: Permanent Installation

For better performance and access to all features:

```bash
# Install Cicada globally
uv tool install cicada-mcp

# Setup your project
cd /path/to/your/project
cicada claude

# Start Claude Code
claude-code
```

### Verification

Ask Claude Code:
```
> Show me the User module
> Where is create_user/2 called?
> Who wrote this line of code?
```

### Troubleshooting

**Issue: "cicada-mcp: command not found"**

Add `~/.local/bin` to PATH:
```bash
# For bash/zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Issue: "Config file not found"**

Run setup in project directory:
```bash
cd /path/to/project
cicada claude
```

---

## Cursor

**Recommended for:** Most users who want one-click installation

### Method 1: One-Click Install (Recommended)

Click this deep link to automatically install Cicada:

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBnaXQraHR0cHM6Ly9naXRodWIuY29tL3dlbmRlL2NpY2FkYS5naXRAbGF0ZXN0IGNpY2FkYS1zZXJ2ZXIgLiJ9)

This automatically:
- Installs Cicada via uv
- Configures the MCP server
- Restarts Cursor

### Method 2: Command Line

```bash
# Install Cicada
uv tool install cicada-mcp

# Initialize your project
cd /path/to/your/project
cicada .

# Restart Cursor
```

### Verification

1. Open Cursor in your project
2. Open Composer (Cmd+K or Ctrl+K)
3. Try: "Show me the User module"

### Configuration

Cicada uses these default paths:
- **Index Storage:** `~/.cicada/projects/<repo_hash>/`
- **Project Config:** `.mcp.json` (in project root)

To customize indexing, edit `~/.cicada/projects/<repo_hash>/config.yaml`:

```yaml
exclude_patterns:
  - "deps/*"
  - "build/*"
  - "_build/*"

file_extensions:
  - ".ex"
  - ".exs"
```

### Troubleshooting

**Issue: Empty search results**

Re-index your project:
```bash
cicada index
# Restart Cursor
```

**Issue: Permission denied errors**

Fix permissions:
```bash
chmod -R u+w ~/.cicada/
```

---

## VS Code (Cline)

**Recommended for:** VSCode users with Cline extension

### Installation

```bash
# Install Cicada
uv tool install cicada-mcp

# Add to PATH (if needed)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Initialize project
cd /path/to/your/project
cicada .
```

### MCP Configuration

Cicada automatically creates `.mcp.json` in your project root. If using Cline, it will detect this file automatically.

Alternatively, manually configure in VSCode settings:

1. Open VSCode Settings (Cmd+, or Ctrl+,)
2. Search for "MCP Servers"
3. Add Cicada configuration:

```json
{
  "cicada": {
    "command": "cicada-mcp",
    "env": {
      "CICADA_REPO_PATH": "/absolute/path/to/your/project"
    }
  }
}
```

### Verification

Ask Cline:
```
Show me the User module
```

### Troubleshooting

**Issue: MCP server won't start**

Check cicada-mcp is accessible:
```bash
which cicada-mcp
# Should output: /home/user/.local/bin/cicada-mcp
```

Check `.mcp.json` is valid:
```bash
cat .mcp.json
```

---

## Zed

**Recommended for:** Zed editor power users

### Prerequisites

- Zed editor installed
- Rust toolchain (for extension development)

### Installation

```bash
# Install Cicada
uv tool install cicada-mcp

# Initialize project
cd /path/to/your/project
cicada .
```

### Extension Setup

Zed requires a Rust-based extension wrapper. See the [Zed Extensions section in PUBLISHING.md](../PUBLISHING.md#zed-extensions) for detailed instructions on:
- Forking zed-industries/extensions
- Creating the Rust extension wrapper
- Submitting to Zed extension registry

### Quick Config

Alternatively, manually configure in Zed settings (`~/.config/zed/settings.json`):

```json
{
  "context_servers": {
    "cicada": {
      "command": "cicada-mcp",
      "env": {
        "CICADA_REPO_PATH": "/absolute/path/to/project"
      }
    }
  }
}
```

---

## Advanced Configuration

### Custom Index Location

By default, Cicada stores indexes in `~/.cicada/projects/<repo_hash>/`. To use a custom location:

```bash
export CICADA_CONFIG_DIR=/custom/path/to/config
cicada index
```

### Multiple Projects

Cicada automatically manages multiple projects:

```bash
# Each project gets its own index
cd ~/project1 && cicada .
cd ~/project2 && cicada .

# Indexes are stored separately:
# ~/.cicada/projects/<project1_hash>/
# ~/.cicada/projects/<project2_hash>/
```

### PR Indexing

Enable GitHub PR attribution (requires `gh` CLI):

```bash
# Install GitHub CLI
brew install gh  # macOS
# or: sudo apt install gh  # Linux

# Authenticate
gh auth login

# Index PRs
cicada index-pr
```

This enables `git_history` to show PR descriptions and review comments.

### Watch Mode

Automatically reindex on file changes:

```bash
cicada watch
```

Press Ctrl+C to stop.

---

## Updating Cicada

To update to the latest version:

```bash
# Update installation
uv tool install --upgrade cicada-mcp

# Re-index your projects
cd /path/to/your/project
cicada index

# Restart your editor
```

---

## Uninstalling

To completely remove Cicada:

```bash
# Uninstall the tool
uv tool uninstall cicada-mcp

# Remove project configuration
rm .mcp.json

# Remove all index data (optional)
rm -rf ~/.cicada/
```

---

## System Requirements

- **Operating Systems:** macOS, Linux, Windows (WSL)
- **Python:** 3.10+ (managed by uv)
- **Disk Space:** 5-50 MB per indexed project
- **Memory:** ~100-200 MB peak during indexing

---

## Privacy & Security

- **Local Only:** All indexing and storage is local to your machine
- **No Telemetry:** No data collection or transmission
- **No API Keys:** No external services required
- **Offline:** Works entirely with your local codebase

---

## Getting Help

- **GitHub Issues:** [https://github.com/wende/cicada/issues](https://github.com/wende/cicada/issues)
- **Documentation:** [Full feature reference](README.md)
- **Tag issues** with editor name (e.g., `[cursor]`, `[vscode]`)

---

## Next Steps

- See [Workflows](WORKFLOWS.md) for usage examples
- Check [MCP Tools Reference](MCP_TOOLS.md) for available tools
- Read [Performance Guide](PERFORMANCE.md) for optimization tips
