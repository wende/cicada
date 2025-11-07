<div align="center">

<img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada.png" alt="CICADA Logo" width="400"/>

# CICADA

### Learn to Give Your AI Assistant Structured Codebase Understanding

*A hands-on guide to using CICADA's Model Context Protocol server*

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

[What You'll Learn](#what-youll-learn) •
[Getting Started](#getting-started) •
[Your First Query](#your-first-query) •
[Advanced Usage](#advanced-usage)

</div>

---

## What You'll Learn

By the end of this guide, you'll understand:

1. **What CICADA is** and why it matters for AI-assisted coding
2. **How to install and configure** CICADA for your editor
3. **How to index** your Elixir codebase
4. **Which tools to use** for different coding tasks
5. **How to leverage** PR context and git history
6. **Best practices** for maintaining your index

**Time commitment:** 15-20 minutes to complete the basic setup. 30-45 minutes to explore all features.

**Prerequisites:**
- Basic familiarity with Elixir
- An Elixir project you want to explore
- One of: Claude Code, Cursor, or VS Code

---

## Understanding the Problem

### Traditional AI Assistant Limitations

When you ask an AI assistant about your codebase, here's what typically happens:

```mermaid
You → AI → grep search → 50 files scanned → 3000 tokens → AI
```

**Problems with this approach:**

1. **Token waste** - AI processes thousands of irrelevant lines
2. **Incomplete results** - Text search misses aliased calls
3. **No context** - AI doesn't know *why* code exists
4. **Slow responses** - Processing takes 30-60 seconds
5. **Hallucinations** - AI invents functions that seem plausible

### The CICADA Approach

CICADA changes this by giving AI assistants structured access:

```mermaid
You → AI → CICADA index → Precise result → AI
```

**What makes this better:**

1. **Token efficiency** - Only relevant data returned (82% reduction)
2. **Complete accuracy** - AST parsing finds all usages
3. **Rich context** - PR discussions, git history included
4. **Fast queries** - Pre-indexed data, sub-second lookups
5. **No hallucinations** - Real data from your codebase

<div align="center">
  <table>
    <tr>
      <td align="center"><b>Traditional Approach</b></td>
      <td align="center"><b>CICADA Approach</b></td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/wende/cicada/main/public/no-cicada-demo-trimmed.gif" alt="Without CICADA" width="450"/></td>
      <td><img src="https://raw.githubusercontent.com/wende/cicada/main/public/cicada-demo-extended-clean-trimmed%20copy.gif" alt="With CICADA" width="450"/></td>
    </tr>
    <tr>
      <td align="center">3,127 tokens • 52.84s</td>
      <td align="center">550 tokens • 35.04s</td>
    </tr>
  </table>
</div>

---

## Getting Started

### Step 1: Install Prerequisites

**Install uv (Python package manager):**

macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

macOS (Homebrew alternative):
```bash
brew install uv
```

Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation:**
```bash
uv --version
# Should show: uv 0.x.x or higher
```

---

### Step 2: Install CICADA

**Install globally using uv:**
```bash
uv tool install cicada-mcp
```

This makes the `cicada` command available system-wide.

**Verify installation:**
```bash
cicada --version
# Should show: cicada 0.2.x or higher
```

**What this installs:**
- `cicada` - Main setup and configuration tool
- `cicada-index` - Codebase indexing tool
- `cicada-index-pr` - PR indexing tool (optional)
- `cicada-find-dead-code` - Dead code detection tool
- `cicada-mcp` - MCP server executable

---

### Step 3: Choose Your Editor

CICADA works with three editors. Choose one:

**Option A: Claude Code**
```bash
cd /path/to/your/elixir/project
cicada claude
```

Creates `.mcp.json` in your project root.

**Option B: Cursor**
```bash
cd /path/to/your/elixir/project
cicada cursor
```

Creates `.cursor/mcp.json` in your project.

You can also use the one-click install button:
[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=cicada&config=eyJjb21tYW5kIjoidXZ4IGNpY2FkYS1tY3AgLiJ9)

**Option C: VS Code**
```bash
cd /path/to/your/elixir/project
cicada vs
```

Creates/updates `.vscode/settings.json` in your project.

---

### Step 4: Restart Your Editor

This is critical - the MCP connection only activates after a full restart.

**Claude Code:** Quit and reopen
**Cursor:** Cmd/Ctrl+Q then reopen
**VS Code:** Quit and reopen (Cmd/Ctrl+Q)

**Verify connection:**
- Open your editor's command palette
- Look for CICADA tools in the MCP section
- If you don't see them, check editor logs for errors

---

## Your First Query

### Basic Function Search

**Try asking your AI assistant:**

```
"What functions are in the MyApp.User module?"
```

**What happens behind the scenes:**

1. AI recognizes you're asking about code structure
2. AI invokes CICADA's `search_module` tool
3. CICADA looks up `MyApp.User` in the index
4. Returns structured data: function names, signatures, docs, line numbers
5. AI formats this information for you

**You should see output like:**

```markdown
# MyApp.User (lib/my_app/user.ex)

## Public Functions

### create_user/2 (line 15)
@spec create_user(map(), Keyword.t()) :: {:ok, User.t()} | {:error, Changeset.t()}

Creates a new user with the given attributes.

### authenticate/2 (line 42)
@spec authenticate(String.t(), String.t()) :: {:ok, User.t()} | {:error, :unauthorized}

Authenticates a user with email and password.

## Private Functions

### hash_password/1 (line 67)
```

**Notice:** No implementation details, just the API surface. This is intentional - it saves tokens and keeps focus on interfaces.

---

### Finding Function Usage

**Try asking:**

```
"Where is create_user/2 called?"
```

**What CICADA does:**

1. AI invokes `search_function` with `function_name="create_user/2"`
2. CICADA searches the index for:
   - Direct calls: `MyApp.User.create_user(attrs, opts)`
   - Aliased calls: `alias MyApp.User; User.create_user(attrs, opts)`
   - Imported calls: `import MyApp.User; create_user(attrs, opts)`
3. Returns all call sites with file paths, line numbers, and code context

**You should see:**

```markdown
## Definition
lib/my_app/user.ex:15
def create_user(attrs, opts \\ [])

## Call Sites (7 found)

### lib/my_app_web/controllers/user_controller.ex:23
case User.create_user(params, audit: true) do

### lib/my_app/accounts.ex:45
with {:ok, user} <- User.create_user(attrs),

### test/my_app/user_test.exs:18
{:ok, user} = User.create_user(%{email: "test@example.com"})

[4 more call sites...]
```

**Key insight:** CICADA tracks calls even when the module is aliased. Traditional grep would miss these.

---

### Conceptual Search

**Try asking:**

```
"Find code related to authentication"
```

**What CICADA does:**

1. AI invokes `search_by_features` with `features="authentication"`
2. CICADA uses AI-powered keyword matching:
   - Extracts keywords from your query
   - Expands to related terms (auth, login, verify, credentials)
   - Searches indexed documentation and docstrings
   - Ranks results by relevance
3. Returns modules and functions with relevance scores

**You should see:**

```markdown
## Modules (2 found)

### MyApp.Auth (relevance: 0.92)
lib/my_app/auth.ex

Handles user authentication and authorization.

### MyApp.Guardian (relevance: 0.78)
lib/my_app/guardian.ex

JWT token generation and validation.

## Functions (5 found)

### MyApp.User.authenticate/2 (relevance: 0.95)
lib/my_app/user.ex:42

Authenticates a user with email and password.

### MyApp.Auth.verify_credentials/2 (relevance: 0.87)
lib/my_app/auth.ex:23

Verifies user credentials against the database.
```

**This is powerful because:** You don't need to know exact function names. Describe what you're looking for conceptually.

---

## Understanding the Tools

### The 9 CICADA Tools

Think of CICADA as providing 9 specialized "search engines" for your code:

| Tool | Question It Answers | Example Query |
|------|---------------------|---------------|
| `search_module` | What's in this module? | "Show me the User module API" |
| `search_function` | Where is this function? | "Where is authenticate/2 called?" |
| `search_module_usage` | Who uses this module? | "Which modules depend on Repo?" |
| `search_by_features` | What does X? | "Find email validation code" |
| `find_pr_for_line` | Why does this line exist? | "Which PR added line 42?" |
| `get_file_pr_history` | How did this file evolve? | "Show PRs that modified user.ex" |
| `get_commit_history` | When was this changed? | "History of authenticate/2" |
| `get_blame` | Who wrote this? | "Who authored this function?" |
| `find_dead_code` | What's unused? | "Find unused functions" |

**You don't need to memorize these.** Just ask natural questions and your AI assistant will choose the right tool.

---

## Advanced Usage

### Exercise 1: Safe Refactoring

**Scenario:** You want to rename `create_user/2` to `register_user/2`.

**Step-by-step:**

1. **Find all usages:**
   ```
   "Show me every place where create_user/2 is called"
   ```

2. **Understand dependencies:**
   ```
   "Which modules use the User module?"
   ```

3. **Check for dynamic calls:**
   ```
   "Search for 'create_user' as a string"
   ```

4. **Verify test coverage:**
   ```
   "Show me create_user calls in test files only"
   ```

Now you know exactly what needs to change. No missed references.

---

### Exercise 2: Understanding Legacy Code

**Scenario:** You need to understand why a complex function exists.

**Step-by-step:**

1. **Read the implementation:**
   ```
   "Show me the validate_payment/3 function"
   ```

2. **Find the PR that introduced it:**
   ```
   "Which PR introduced validate_payment in billing.ex?"
   ```

3. **Read the PR context:**
   ```
   "Show me the PR description and review comments"
   ```

4. **See the evolution:**
   ```
   "Show me the commit history for validate_payment/3"
   ```

Now you understand the original problem, design decisions, and how it evolved.

---

### Exercise 3: Code Cleanup

**Scenario:** Your codebase has grown and you suspect dead code.

**Step-by-step:**

1. **Find high-confidence dead code:**
   ```
   "Find unused public functions"
   ```

2. **Investigate suspicious functions:**
   ```
   "Show me where send_notification/2 is called"
   ```

3. **Check git history:**
   ```
   "When was send_notification/2 last modified?"
   ```

4. **Verify it's safe to remove:**
   ```
   "Search for 'send_notification' in all files"
   ```

---

## Enabling PR Features

### Why PR Features Matter

PR features let you answer:
- "Why was this code written this way?"
- "What problem does this solve?"
- "Who decided on this approach?"
- "What alternatives were considered?"

This context is invaluable for understanding legacy code and making informed changes.

### Setup (One-Time)

**Step 1: Install GitHub CLI**

macOS:
```bash
brew install gh
```

Ubuntu:
```bash
sudo apt install gh
```

Or visit: https://cli.github.com/

**Step 2: Authenticate**

```bash
gh auth login
```

Follow the prompts to authenticate with your GitHub account.

**Step 3: Index PRs**

```bash
cd /path/to/your/project
cicada index-pr .
```

This will:
- Fetch all PRs from your GitHub repository
- Extract PR metadata (title, description, author, dates)
- Extract review comments with line numbers
- Build a searchable index

**First time:** May take 5-10 minutes for large repositories.
**Subsequent runs:** Incremental, only fetches new PRs.

---

### Using PR Features

**Find which PR introduced a line:**
```
"Which PR introduced line 42 of lib/my_app/user.ex?"
```

**See all PRs that modified a file:**
```
"Show me all PRs that modified lib/my_app/billing.ex"
```

**Read review comments:**
```
"What did reviewers say about the billing changes?"
```

---

## Maintenance

### Re-indexing After Changes

CICADA uses incremental indexing. After you make code changes:

```bash
cicada claude  # or cursor, vs
```

**What happens:**
1. CICADA compares file hashes to detect changes
2. Only changed files are re-parsed
3. Index is updated with new data
4. Existing data is preserved

**How often to re-index:**
- After pulling changes from git: Optional (index still mostly valid)
- After adding new modules: Yes (new code won't be searchable)
- After refactoring: Yes (call sites may have changed)

**Pro tip:** Set up a git post-merge hook to re-index automatically.

---

### Performance Tuning

**Choose the right keyword extraction tier:**

```bash
# Fast (no downloads, regex-based)
cicada index --fast .

# Regular (128MB download, recommended)
cicada index --regular .

# Max (958MB download, best accuracy)
cicada index --max .

# Disable keyword extraction
cicada index --no-keywords .
```

**When to use each:**
- `--fast`: Small projects (<100 modules)
- `--regular`: Most projects (default, good balance)
- `--max`: Large projects (>500 modules) where accuracy matters
- `--no-keywords`: You don't need semantic search

---

### Troubleshooting Tips

**Problem: "Index file not found"**

**Solution:**
```bash
cicada index .
```

Make sure indexing completed successfully. Check for errors in output.

---

**Problem: "Module MyApp.User not found"**

**Common causes:**
1. Using short name (`User` instead of `MyApp.User`)
2. Module wasn't indexed (file was added after last index)
3. Typo in module name

**Solution:**
```bash
# Use full module path
"Show me the MyApp.User module"

# Re-index if recently added
cicada index .
```

---

**Problem: MCP tools not appearing**

**Checklist:**
1. Config file exists (`.mcp.json`, `.cursor/mcp.json`, or `.vscode/settings.json`)
2. Paths in config are absolute (not relative)
3. Editor was fully restarted (not just reloaded)
4. Index exists in `~/.cicada/projects/<hash>/`

**Debug:**
```bash
# Verify config
cat .mcp.json

# Verify index
ls -la ~/.cicada/projects/

# Check editor MCP logs
```

---

## Best Practices

### 1. Index Regularly

Re-index after significant changes:
```bash
cicada claude
```

### 2. Use Semantic Search

When you don't know exact names:
```
"Find code that handles payment processing"
```

Not:
```
"Find the process_payment function"  # You don't know if it's called that
```

### 3. Leverage PR Context

Before refactoring complex code:
```
"Which PR introduced this function?"
"What did reviewers say about this code?"
```

### 4. Combine Tools

For comprehensive understanding:
```
1. "Where is this function defined?"
2. "Where is it called?"
3. "Which PR introduced it?"
4. "Show me its commit history"
```

### 5. Keep PR Index Updated

After merging PRs:
```bash
cicada index-pr .
```

---

## What's Next

### Continue Learning

- **[MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md)** - Detailed tool specifications
- **[Workflow Examples](docs/WORKFLOW_EXAMPLES.md)** - Real-world scenarios with step-by-step guides
- **[PR Indexing Guide](docs/PR_INDEXING.md)** - Advanced PR integration techniques

### Explore Advanced Features

- **Dead code detection** - `cicada find-dead-code`
- **Module dependency visualization** - Coming soon
- **Team index sharing** - Coming soon

### Stay Updated

- **[Changelog](CHANGELOG.md)** - Version history and new features
- **[GitHub Issues](https://github.com/wende/cicada/issues)** - Report bugs or request features
- **[Contributing](CONTRIBUTING.md)** - Help improve CICADA

---

## Summary

**What you learned:**

✅ CICADA provides structured codebase understanding for AI assistants
✅ Installation takes 5-10 minutes
✅ 9 tools cover different code exploration needs
✅ Semantic search finds code by concept
✅ PR features reveal why code exists
✅ Incremental indexing keeps data up-to-date
✅ 82% token reduction improves AI interactions

**You're now ready to:**
- Ask your AI assistant sophisticated code questions
- Navigate large codebases efficiently
- Understand code history and context
- Refactor safely with complete call site tracking
- Find dead code and cleanup opportunities

**Start exploring your codebase with CICADA!**

---

## Need Help?

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/wende/cicada/issues)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Happy coding with CICADA!**

[⬆ back to top](#cicada)

</div>
