# Unified Git History Tool

Cicada provides a single unified `git_history` MCP tool that consolidates all git history-related functionality.

## How It Works

The tool automatically routes based on parameters:

1. **Single Line Analysis** (`start_line` only)
   - Uses `git blame` to find the author of a specific line
   - Automatically looks up associated Pull Request if PR index available
   - Perfect for "who wrote this line and why?"

2. **Line Range Analysis** (`start_line` + `end_line`)
   - Groups consecutive lines by authorship
   - Optionally enriches with PR information
   - Shows code snippets with author and commit details

3. **Function Tracking** (`function_name`)
   - Uses `git log -L :funcname:file` for precise function tracking
   - Tracks function changes even as it moves within the file
   - Optionally shows evolution metadata

4. **File-Level History** (no line/function params)
   - Smart fallback: tries PR index first, then falls back to git commits
   - Shows complete history with descriptions and review comments

## Parameters

```python
{
  "file_path": str (required),        # Path to file (relative to repo root)
  "start_line": int (optional),       # Line number or range start
  "end_line": int (optional),         # Range end
  "function_name": str (optional),    # Function name for tracking
  "show_evolution": bool,             # Include creation/modification metadata
  "max_results": int (default: 10),   # Maximum results to return
  "recent": bool | None,              # Time filter (see below)
  "author": str (optional)            # Filter by author name
}
```

## Time Filtering with `recent`

- `recent=true` → Last 14 days only
- `recent=false` → Older than 14 days only
- `recent=None` or omitted → All time (no filter)

## Usage Examples

```python
# Single line authorship + PR
git_history(file_path="lib/auth.ex", start_line=42)

# Line range blame
git_history(file_path="lib/auth.ex", start_line=40, end_line=60)

# Function evolution
git_history(
    file_path="lib/auth.ex",
    function_name="validate_user",
    show_evolution=true,
    max_results=5
)

# File PR history
git_history(file_path="lib/auth.ex")

# Recent changes by author
git_history(
    file_path="lib/auth.ex",
    recent=true,
    author="john"
)
```

## MCP Tool Usage

```json
{
  "name": "git_history",
  "arguments": {
    "file_path": "lib/my_app/auth.ex",
    "start_line": 42,
    "end_line": 60,
    "recent": true,
    "max_results": 10
  }
}
```

## Smart PR Fallback

1. **PR Index Available:** Shows PR numbers, titles, authors, and review comments
2. **No PR Index:** Falls back to git commands for blame and commit history
3. **GitHub API Fallback:** Can optionally query GitHub API if PR index is stale

## Migration from Old Tools

| Old Tool | New Equivalent |
|----------|----------------|
| `get_blame(file, start, end)` | `git_history(file, start_line=start, end_line=end)` |
| `get_commit_history(file, func)` | `git_history(file, function_name=func)` |
| `find_pr_for_line(file, line)` | `git_history(file, start_line=line)` |
| `get_file_pr_history(file)` | `git_history(file)` |

**Implementation:** `cicada/git/history_analyzer.py`, `cicada/mcp/handlers/git_handlers.py`
