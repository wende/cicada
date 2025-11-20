# Installing Cicada for OpenCode

This guide provides step-by-step instructions for installing Cicada MCP server in OpenCode.

---

## Prerequisites

- **OpenCode** editor installed ([installation guide](https://github.com/opencode-ai/opencode))
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- An **Elixir project** to analyze

---

## Installation Methods

### Method 1: Command Line Installation (Recommended)

#### Step 1: Install Cicada

```bash
uv tool install cicada-mcp
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

#### Step 3: Initialize Your Project

Navigate to your Elixir project and run:

```bash
cd /path/to/your/elixir/project
cicada opencode
```

This will:
- Index your codebase
- Create `.mcp.json` configuration file
- Store index data in `~/.cicada/projects/<hash>/`

#### Step 4: Restart OpenCode

Restart OpenCode to load the MCP server. The configuration is automatically detected from `.mcp.json`.

---

### Method 2: Manual MCP Server Configuration

If you need to manually configure the MCP server:

#### Step 1: Install Cicada (same as above)

```bash
uv tool install cicada-mcp
```

#### Step 2: Create `.mcp.json` manually

In your project root, create `.mcp.json`:

```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp"],
      "env": {
        "CICADA_CONFIG_DIR": "/Users/username/.cicada/projects/<repo_hash>/"
      }
    }
  }
}
```

**Important:**
- Replace `/Users/username/.cicada/projects/<repo_hash>/` with the actual path to your project's storage directory
- You can find the repo hash by running `cicada opencode` which will display the storage path

#### Step 3: Index Your Project

```bash
cd /path/to/your/elixir/project
cicada index
```

#### Step 4: Restart OpenCode

Restart OpenCode for the changes to take effect.

---

## Verifying Installation

After installation, verify Cicada is working:

1. **Open OpenCode** in your Elixir project
2. **Try these commands:**
   - "Show me the User module"
   - "Where is the authenticate function defined?"
   - "Find all calls to MyApp.Accounts"

If Cicada is working, you'll see detailed results with function signatures, line numbers, and code context.

---

## Configuration

### Default Configuration

Cicada uses these default paths:

- **Index Storage:** `~/.cicada/projects/<repo_hash>/`
- **Project Config:** `.mcp.json` (in project root)
- **Generated Files:**
  - `index.json` - Main code index
  - `config.yaml` - Project configuration
  - `hashes.json` - File change tracking
  - `pr_index.json` - PR attribution data

### Custom Configuration

To customize indexing behavior, edit `~/.cicada/projects/<repo_hash>/config.yaml`:

```yaml
# Paths to exclude from indexing
exclude_patterns:
  - "deps/*"
  - "build/*"
  - "_build/*"
  - ".git/*"

# File extensions to index
file_extensions:
  - ".ex"
  - ".exs"
```

---

## Troubleshooting

### Issue 1: "cicada-mcp: command not found"

**Cause:** `~/.local/bin` is not in your PATH

**Solution:**
```bash
# Add to your shell config (~/.bashrc, ~/.zshrc, etc.)
export PATH="$HOME/.local/bin:$PATH"

# Reload your shell
source ~/.bashrc  # or source ~/.zshrc
```

### Issue 2: "Config file not found"

**Cause:** Project not initialized

**Solution:**
```bash
cd /path/to/your/project
cicada opencode
```

### Issue 3: MCP Server Won't Start

**Cause:** Invalid `.mcp.json` or missing index

**Solution:**
```bash
# Re-initialize the project
cd /path/to/your/project
cicada opencode

# Verify .mcp.json exists and is valid
cat .mcp.json

# Check index was created
ls ~/.cicada/projects/
```

### Issue 4: Empty Search Results

**Cause:** Stale or corrupted index

**Solution:**
```bash
# Re-index your project
cicada index

# Restart OpenCode
```

### Issue 5: Permission Denied Errors

**Cause:** Insufficient permissions for storage directory

**Solution:**
```bash
# Check permissions
ls -la ~/.cicada/

# Fix permissions
chmod -R u+w ~/.cicada/
```

---

## Updating Cicada

To update to the latest version:

```bash
# Update to latest version
uv tool install --upgrade cicada-mcp

# Re-index your projects
cd /path/to/your/project
cicada index

# Restart OpenCode
```

---

## Example Usage

### Finding a Module

Ask OpenCode:
```
Show me the User module
```

### Finding Function Calls

Ask OpenCode:
```
Where is authenticate/2 called in the codebase?
```

### Understanding Code History

Ask OpenCode:
```
Who wrote this line and in which PR?
```

### Module Impact Analysis

Ask OpenCode:
```
Show me everywhere MyApp.Accounts is imported or used
```

---

## Uninstalling

To completely remove Cicada:

```bash
# Uninstall the tool
uv tool uninstall cicada-mcp

# Remove project configuration
rm .mcp.json

# Remove index data (optional)
rm -rf ~/.cicada/

# Restart OpenCode
```

---

## Getting Help

- **GitHub Issues:** [https://github.com/wende/cicada/issues](https://github.com/wende/cicada/issues)
- **Documentation:** [https://github.com/wende/cicada](https://github.com/wende/cicada)
- **Tag OpenCode-specific issues** with `[opencode]` prefix

---

## System Requirements

- **Operating Systems:** macOS, Linux, Windows (WSL)
- **Python:** 3.10 or higher (managed by uv)
- **Disk Space:** ~5-50 MB per indexed project (depends on project size)
- **Memory:** Minimal (indexing uses ~100-200 MB peak)

---

## Privacy & Security

- **Local Only:** All indexing and data storage is local to your machine
- **No Telemetry:** Cicada does not collect or transmit any data
- **No API Keys:** No external services or authentication required
- **Safe to Use:** Works entirely offline with your local codebase

---

**Status:** ✅ Ready for Production
**Last Updated:** 2025-11-10
