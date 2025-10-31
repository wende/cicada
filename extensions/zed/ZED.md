# Zed Extension Guide

## Overview

**Platform:** https://zed.dev/extensions
**Audience:** Growing Zed editor community
**Submission Time:** 6-8 hours (initial)
**Approval Time:** PR review (typically 1-3 days)
**Maintenance:** Low (Zed updates handled by maintainers)

**Complexity:** ⭐⭐⭐ High - Requires Rust wrapper

---

## Prerequisites

### Required Skills
- [ ] Rust programming knowledge
- [ ] Understanding of WebAssembly (WASM)
- [ ] Git submodule experience

### Required Tools
- [ ] Rust toolchain (cargo, rustc)
- [ ] Zed editor installed
- [ ] GitHub account
- [ ] Git

---

## Architecture

Zed extensions are Rust code compiled to WebAssembly:

**Key Components:**
```
zed-extension-cicada/
├── Cargo.toml              # Rust package manifest
├── extension.toml          # Zed extension config
└── src/
    └── lib.rs              # Extension implementation
```

**How It Works:**
1. Extension defines MCP server in `extension.toml`
2. `context_server_command` method returns command to start server
3. Zed spawns the MCP server process
4. Extension can download/install cicada if needed

---

## Implementation Guide

### Step 1: Fork zed-industries/extensions

```bash
# Fork on GitHub: https://github.com/zed-industries/extensions

# Clone your fork
git clone https://github.com/YOUR_USERNAME/extensions.git zed-extensions
cd zed-extensions

# Create subdirectory for cicada
mkdir extensions/cicada
cd extensions/cicada
```

### Step 2: Create Cargo.toml

```toml
[package]
name = "cicada"
version = "0.2.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
zed_extension_api = { git = "https://github.com/zed-industries/zed" }
```

### Step 3: Create extension.toml

```toml
id = "cicada"
name = "Cicada"
description = "Elixir code intelligence via MCP"
version = "0.2.0"
schema_version = 1
authors = ["Wende <your@email.com>"]
repository = "https://github.com/wende/cicada"

[context_servers.cicada]
command = { type = "Stdio", program = "cicada-mcp" }
```

### Step 4: Create src/lib.rs

```rust
use zed::{ LanguageServerId, Command };
use zed_extension_api as zed;

struct CicadaExtension;

impl zed::Extension for CicadaExtension {
    fn new() -> Self {
        Self
    }

    fn context_server_command(
        &mut self,
        _context_server_id: &LanguageServerId,
        _worktree: &zed::Worktree,
    ) -> Result<Command> {
        // Simple approach: assume cicada-mcp is in PATH
        // User must install cicada manually

        Ok(Command {
            command: "cicada-mcp".to_string(),
            args: vec![],
            env: Default::default(),
        })
    }
}

zed::register_extension!(CicadaExtension);
```

### Step 5: Advanced - Auto-Install Cicada (Optional)

```rust
use std::fs;
use zed::{ LanguageServerId, Command };
use zed_extension_api as zed;

struct CicadaExtension {
    cached_binary_path: Option<String>,
}

impl zed::Extension for CicadaExtension {
    fn new() -> Self {
        Self {
            cached_binary_path: None,
        }
    }

    fn context_server_command(
        &mut self,
        _context_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<Command> {
        // Check if cicada-mcp is in PATH
        if let Ok(path) = which::which("cicada-mcp") {
            return Ok(Command {
                command: path.to_string_lossy().to_string(),
                args: vec![],
                env: Default::default(),
            });
        }

        // If not in PATH, check cached location
        if let Some(cached_path) = &self.cached_binary_path {
            if fs::metadata(cached_path).is_ok() {
                return Ok(Command {
                    command: cached_path.clone(),
                    args: vec![],
                    env: Default::default(),
                });
            }
        }

        // Download and install cicada
        self.install_cicada(worktree)?;

        // Return command with cached path
        Ok(Command {
            command: self.cached_binary_path.clone().unwrap(),
            args: vec![],
            env: Default::default(),
        })
    }
}

impl CicadaExtension {
    fn install_cicada(&mut self, _worktree: &zed::Worktree) -> Result<()> {
        // Installation logic here
        // Could use uv, pip, or download binary directly

        // For now, return error telling user to install manually
        Err("Please install cicada: uv tool install git+https://github.com/wende/cicada.git@latest".into())
    }
}

zed::register_extension!(CicadaExtension);
```

### Step 6: Build and Test Locally

```bash
# Build the extension
cargo build --target wasm32-wasi --release

# Install as dev extension in Zed
# Open Zed
# Extensions > Install Dev Extension
# Select your extensions/cicada directory
```

### Step 7: Submit to Official Extensions

```bash
# Commit your changes
git add extensions/cicada
git commit -m "Add Cicada MCP extension for Elixir"

# Push to your fork
git push origin main

# Create pull request on GitHub
# Title: "Add Cicada extension - Elixir code intelligence"
# Description: (see below)
```

---

## Pull Request Template

**Title:** Add Cicada extension - Elixir code intelligence

**Description:**
```markdown
## Summary
Adds Cicada MCP server integration for intelligent Elixir code search and analysis.

## Features
- Module and function search
- Call site analysis
- Git history and PR attribution
- Dead code detection

## Installation
Users need to install Cicada first:
```bash
uv tool install git+https://github.com/wende/cicada.git@latest
```

Then setup their Elixir project:
```bash
cicada /path/to/project
```

## Testing
- [ ] Tested on macOS
- [ ] Tested on Linux
- [ ] Elixir projects index correctly
- [ ] MCP server starts without errors
- [ ] All tools accessible in Zed

## Links
- Repository: https://github.com/wende/cicada
- Documentation: https://github.com/wende/cicada/blob/main/README.md
```

---

## User Documentation (for Zed)

**README.md** (to include in extension):
```markdown
# Cicada Extension for Zed

Provides Elixir code intelligence via the Model Context Protocol (MCP).

## Installation

### 1. Install Cicada CLI
```bash
uv tool install git+https://github.com/wende/cicada.git@latest
```

### 2. Install Zed Extension
- Open Zed
- Extensions → Browse
- Search for "Cicada"
- Click Install

### 3. Setup Your Project
```bash
cd /path/to/elixir/project
cicada .
```

### 4. Restart Zed
The MCP server will auto-start.

## Usage

Ask Zed Assistant:
- "Show me the User module"
- "Where is authenticate/2 called?"
- "Who wrote this code?"
- "Find all usages of MyApp.Accounts"

## Troubleshooting

**MCP server won't start:**
- Ensure `cicada-mcp` is in PATH: `which cicada-mcp`
- Add `~/.local/bin` to PATH if needed
- Verify installation: `cicada --version`

**Index not found:**
```bash
cd /path/to/project
cicada .
```

## Support

- GitHub: https://github.com/wende/cicada/issues
- Tag issues with `[zed]`
```

---

## Testing Checklist

Before submitting PR:

- [ ] Extension compiles to WASM without errors
- [ ] Works as dev extension in Zed
- [ ] MCP server starts correctly
- [ ] Can query modules and functions
- [ ] Error messages are helpful
- [ ] Documentation is clear
- [ ] Tested on macOS and Linux
- [ ] No hardcoded paths
- [ ] Follows Zed extension guidelines

---

## Estimated Timeline

| Task | Time | Difficulty |
|------|------|------------|
| Rust setup | 1 hour | Low |
| Basic extension | 2 hours | Medium |
| Auto-install logic | 3 hours | High |
| Testing | 1 hour | Low |
| Documentation | 1 hour | Low |
| PR submission | 1 hour | Low |
| **Total** | **9 hours** | **High** |

---

## Maintenance

### After Approval
- Extension appears in Zed marketplace
- Users can install via Extensions menu
- Updates go through PR process
- Zed team may help with maintenance

### Version Updates
1. Update version in extension.toml and Cargo.toml
2. Rebuild WASM
3. Test locally
4. Submit new PR to zed-industries/extensions
5. Wait for review and merge

---

## Alternatives

### Simpler Approach: User-Configured MCP

Instead of a Zed extension, users can configure MCP manually:

**~/.config/zed/settings.json:**
```json
{
  "context_servers": {
    "cicada": {
      "command": "cicada-mcp"
    }
  }
}
```

**Pros:**
- No Rust knowledge needed
- Faster to implement
- User has full control

**Cons:**
- Manual configuration required
- Not discoverable in marketplace
- No automatic setup

---

## Resources

- **Zed Extension Docs:** https://zed.dev/docs/extensions
- **MCP Extension Guide:** https://zed.dev/docs/extensions/mcp-extensions
- **Example Extensions:** https://github.com/zed-industries/extensions
- **Zed Discord:** Join for help

---

**Status:** 📋 Documented, Not Implemented
**Priority:** Low (defer to v0.3+)
**Blocker:** Requires Rust expertise
**Alternative:** User manual configuration (see above)
**Next Action:** Consider finding Rust contributor or defer until post-MVP
