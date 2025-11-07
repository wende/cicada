<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="300"/>

# CICADA

**Give your AI assistant X-ray vision into your codebase**

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Install](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

Find code by concept • Track PR context • Save 80% tokens

*Currently supports Elixir*

</div>

---

## 60 Second Setup

```bash
# 1. Install
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install cicada-mcp

# 2. Index your project
cd /path/to/your/elixir/project
cicada claude  # or: cicada cursor, cicada vs

# 3. Restart your editor
```

**Done!** Now ask your AI:
- "What functions are in the User module?"
- "Where is authenticate/2 called?"
- "Find code related to authentication"

---

## What You Get

**Before CICADA:**
```
You: "Where is create_user called?"
AI: *searches 50 files*
AI: *dumps 3,127 tokens*
AI: *misses half the calls*
```
3,127 tokens • 52 seconds • ❌ Incomplete

**After CICADA:**
```
You: "Where is create_user called?"
AI: "Found 7 call sites in lib/..."
```
550 tokens • 35 seconds • ✅ Accurate

**82% fewer tokens. 34% faster. Actually correct.**

---

## Key Features

- **Semantic Search** - Find code by concept: "authentication", "api keys", etc.
- **Smart Tracking** - Track function calls even through aliases
- **PR Context** - See *why* code exists with PR discussions
- **Git History** - Track function evolution over time
- **Dead Code** - Find unused functions automatically
- **Token Efficient** - Structured data, not file dumps

---

## Works With

<div align="center">

| Editor | Setup Command |
|--------|---------------|
| Claude Code | `cicada claude` |
| Cursor | `cicada cursor` |
| VS Code | `cicada vs` |

</div>

---

## What's New (v0.2.0)

**AI-Powered Search** - Find code by concept with KeyBERT + GloVe
```bash
cicada index --regular .  # 128MB download, worth it
```

**Incremental Indexing** - Only re-indexes changed files. Press Ctrl-C to interrupt safely.

**3 Speed Tiers:**
- `--fast` - No downloads, regex-based (fastest)
- `--regular` - AI models, 128MB (recommended)
- `--max` - Large models, 958MB (best accuracy)

---

## Usage Examples

<details>
<summary><b>Find a function</b></summary>

```
"Where is validate_email/1 defined?"
```

Returns file, line number, signature, and documentation.

</details>

<details>
<summary><b>Track usage</b></summary>

```
"Show me all places where User.create_user is called"
```

Returns all 7 call sites with code context.

</details>

<details>
<summary><b>Search by concept</b></summary>

```
"Find code related to API authentication"
```

Returns modules and functions with relevance scores.

</details>

<details>
<summary><b>PR context</b></summary>

```
"Which PR introduced line 42 of user.ex?"
```

Returns PR #123 with title, author, and review comments.

Requires: `gh auth login` + `cicada index-pr .`

</details>

<details>
<summary><b>Find dead code</b></summary>

```
"What functions are never called?"
```

Returns unused public functions with confidence levels.

</details>

---

## Configuration

<details>
<summary><b>How it works</b></summary>

CICADA creates one config file in your project:

**Claude Code** (`.mcp.json`):
```json
{
  "mcpServers": {
    "cicada": {
      "command": "uvx",
      "args": ["cicada-mcp", "/absolute/path"]
    }
  }
}
```

Index stored in `~/.cicada/projects/<hash>/` (not in your repo).

</details>

<details>
<summary><b>Re-indexing</b></summary>

After making changes:
```bash
cicada claude  # Updates incrementally
```

Force full re-index:
```bash
rm -rf ~/.cicada/projects/*/hashes.json
cicada index .
```

</details>

<details>
<summary><b>PR features</b></summary>

One-time setup:
```bash
gh auth login
cicada index-pr .
```

Updates incrementally on subsequent runs.

</details>

---

## Privacy

- ✅ 100% local - your code never leaves your machine
- ✅ No telemetry or tracking
- ✅ Read-only tools - AI can't modify code
- ✅ GitHub CLI uses your existing auth (optional, only for PR features)

---

## Troubleshooting

<details>
<summary><b>"Index file not found"</b></summary>

Run: `cicada index .`

</details>

<details>
<summary><b>"Module not found"</b></summary>

Use full module names: `MyApp.User`, not `User`

</details>

<details>
<summary><b>MCP not connecting</b></summary>

1. Check `.mcp.json` exists
2. Verify paths are absolute
3. Restart editor completely
4. Check editor MCP logs

</details>

<details>
<summary><b>PR features not working</b></summary>

```bash
brew install gh
gh auth login
cicada index-pr .
```

</details>

---

## Documentation

**Quick Links:**
- [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md) - All 9 tools explained
- [Workflow Examples](docs/WORKFLOW_EXAMPLES.md) - Real-world scenarios
- [PR Indexing Guide](docs/PR_INDEXING.md) - GitHub integration setup
- [Changelog](CHANGELOG.md) - Version history

**Command Reference:**
```bash
cicada [claude|cursor|vs] [path]  # Setup project
cicada index [--fast|--regular|--max] <path>  # Index code
cicada index-pr [--clean] <path>  # Index PRs
cicada find-dead-code [--min-confidence low]  # Find unused code
```

---

## What's Coming

- Python support
- TypeScript support
- IDE plugins (no MCP needed)
- Team index sharing

---

## Contributing

```bash
git clone https://github.com/wende/cicada.git
cd cicada
uv sync
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Built With

[Tree-sitter](https://tree-sitter.github.io/) • [MCP](https://modelcontextprotocol.io/) • [GitHub CLI](https://cli.github.com/) • [KeyBERT](https://github.com/MaartenGr/KeyBERT)

---

## License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**Stop letting your AI search blindly**

[Get Started](#60-second-setup) • [View Demo](#what-you-get) • [Report Issues](https://github.com/wende/cicada/issues)

Made with ❤️ for Elixir developers

</div>
