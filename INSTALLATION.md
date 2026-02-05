# Installation

Quick installation guide for Cicada MCP server.

## Quick Start

```bash
# Install Cicada
uv tool install cicada-mcp

# Navigate to your project
cd /path/to/your/project

# Initialize (creates .mcp.json and indexes your code)
cicada .
```

That's it! Cicada is now configured for your editor.

---

## Supported Editors

- **Claude Code** - Automatic setup via `.mcp.json`
- **Cursor** - One-click install or automatic via `.mcp.json`
- **VS Code (Cline)** - Automatic detection of `.mcp.json`
- **Zed** - Manual configuration required
- **Kimi Code CLI** - Automatic detection of `.mcp.json`

---

## Supported Languages

Cicada supports 15 programming languages:

**Tree-sitter based:**
- Elixir, Erlang

**SCIP based:**
- Python, TypeScript, JavaScript, Go, Rust
- Java, Scala, C, C++, Ruby
- C#, Visual Basic, Dart

---

## System Requirements

- Python 3.10+
- uv package manager
- 5-50 MB disk space per project

---

## Full Documentation

For detailed installation instructions including:
- Editor-specific setup guides
- Troubleshooting
- Configuration options
- Advanced features

See the **[Complete Installation Guide](codebook/INSTALLATION.md)**

---

## Next Steps

After installation:

1. **Verify it works:** Ask your AI assistant "Show me the User module"
2. **Learn workflows:** Check out [Workflows](codebook/WORKFLOWS.md)
3. **Understand performance:** See [Performance Guide](codebook/PERFORMANCE.md)

---

## Getting Help

- **Documentation:** [Full feature reference](codebook/README.md)
- **Issues:** [GitHub Issues](https://github.com/wende/cicada/issues)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
