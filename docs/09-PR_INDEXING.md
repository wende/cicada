# PR Indexing - Fast Offline PR Lookups with Comments

The PR indexing system allows you to find which pull request introduced any line of code, view PR descriptions, and see review comments—all without making network requests at query time.

## How It Works

1. **Indexing** (one-time or periodic):
   - Fetches all PRs from GitHub via GraphQL (efficient batching)
   - For each PR, stores:
     - Commits and files changed
     - PR description/body
     - Review comments with line numbers
   - Maps comment lines from PR commits to current file state
   - Builds multiple indexes:
     - commit → PR mapping
     - file → PRs mapping
   - Saves everything to `.cicada/pr_index.json`

2. **Lookup** (fast, offline):
   - Runs `git blame` to find commit SHA (local, fast)
   - Looks up commit in the index
   - Returns PR info with description and comments instantly (no network!)

## Quick Start

### 1. Index Your Repository

```bash
# Index PRs (incremental by default - updates existing index with new PRs)
python cicada/pr_indexer.py /path/to/your/repo

# Clean rebuild (re-index everything from scratch)
python cicada/pr_indexer.py /path/to/your/repo --clean
```

### 2. Find PR for a Line

```bash
# Uses index by default (fast, no network)
python cicada/pr_finder.py README.md 1

# Different output formats
python cicada/pr_finder.py README.md 1 --format markdown
python cicada/pr_finder.py README.md 1 --format json

# Disable index and use network instead
python cicada/pr_finder.py README.md 1 --no-index
```

## Index Structure

The index file (`.cicada/pr_index.json`) contains:

```json
{
  "metadata": {
    "repo_owner": "wende",
    "repo_name": "cicada",
    "last_indexed_at": "2025-10-25T13:00:00Z",
    "total_prs": 50,
    "total_commits_mapped": 250,
    "total_comments": 420,
    "total_files": 85,
    "last_pr_number": 123
  },
  "prs": {
    "42": {
      "number": 42,
      "title": "Add new feature",
      "url": "https://github.com/wende/cicada/pull/42",
      "state": "closed",
      "merged": true,
      "author": "wende",
      "description": "This PR adds support for...",
      "commits": ["c1f9203...", "abc123..."],
      "files_changed": ["README.md", "src/main.py"],
      "comments": [
        {
          "id": "comment_id_123",
          "author": "reviewer",
          "body": "Consider using a different approach here...",
          "created_at": "2025-10-20T10:30:00Z",
          "path": "src/main.py",
          "line": 42,
          "original_line": 38,
          "resolved": true,
          "commit_sha": "c1f9203..."
        }
      ]
    }
  },
  "commit_to_pr": {
    "c1f9203cb832203f84da0f9766bde205f60a7aa3": 42
  },
  "file_to_prs": {
    "README.md": [42, 35, 18],
    "src/main.py": [42, 40]
  }
}
```

## CLI Reference

### pr_indexer.py

Index all pull requests from a GitHub repository.

**Arguments:**
- `repo` - Path to git repository (default: current directory)

**Options:**
- `--output PATH` - Output path for index file (default: .cicada/pr_index.json)
- `--clean` - Clean and rebuild the entire index from scratch (default: incremental update)

**Examples:**
```bash
# Update index (incremental by default)
python cicada/pr_indexer.py .

# Clean rebuild (re-index everything)
python cicada/pr_indexer.py . --clean

# Custom output path
python cicada/pr_indexer.py . --output /path/to/pr_index.json
```

### pr_finder.py

Find the PR that introduced a specific line of code.

**Arguments:**
- `file` - Path to the file
- `line` - Line number (1-indexed)

**Options:**
- `--format {text,json,markdown}` - Output format (default: text)
- `--no-index` - Disable index and use network instead
- `--index-path PATH` - Path to PR index file (default: .cicada/pr_index.json)

**Examples:**
```bash
# Basic usage (uses index)
python cicada/pr_finder.py README.md 1

# Markdown output
python cicada/pr_finder.py README.md 68 --format markdown

# Use network instead of index
python cicada/pr_finder.py README.md 1 --no-index

# Custom index path
python cicada/pr_finder.py README.md 1 --index-path /custom/path/pr_index.json
```

## Performance

- **Indexing**:
  - GraphQL batching: ~50 PRs/minute (10 PRs per batch)
  - ~30x fewer API calls vs REST
  - Includes PR descriptions and review comments
  - Comment line mapping adds ~1-2 seconds per PR with comments
- **Lookup**: ~0.1 seconds (git blame + index lookup, no network!)
- **Index size**:
  - Base: ~1KB per PR
  - With comments: ~2-5KB per PR (depending on review activity)
  - Typical 100-PR repo: ~200-500KB total

## Incremental Updates

The indexer uses incremental updates by default to minimize API calls:

```bash
# Run normally (incremental by default)
python cicada/pr_indexer.py .

# Force clean rebuild if needed
python cicada/pr_indexer.py . --clean
```

The index tracks `last_pr_number` and only fetches PRs with higher numbers.
When no existing index is found, a full index is automatically created.

## Use as a Library

### Indexing

```python
from cicada.pr_indexer import PRIndexer

indexer = PRIndexer(repo_path="/path/to/repo")
index = indexer.index_repository(
    output_path=".cicada/pr_index.json",
    incremental=True
)
```

### Lookup

```python
from cicada.pr_finder import PRFinder

# With index (fast, offline)
finder = PRFinder(repo_path=".", use_index=True)
result = finder.find_pr_for_line("README.md", 68)

# Without index (network, slower)
finder = PRFinder(repo_path=".", use_index=False)
result = finder.find_pr_for_line("README.md", 68)

# Format output
print(finder.format_result(result, "markdown"))
```

## Requirements

- GitHub CLI (`gh`) installed and authenticated
- Git repository with GitHub remote
- Python 3.7+

## Troubleshooting

**"Not a GitHub repository"**
- Ensure the repository has a GitHub remote configured
- Run `gh repo view` to verify GitHub CLI can access the repo

**"PR index not found"**
- Run `python cicada/pr_indexer.py .` to create the index
- Check that `.cicada/pr_index.json` exists

**"GitHub CLI not found"**
- Install GitHub CLI: https://cli.github.com/
- Authenticate: `gh auth login`

## Rate Limits

GitHub API has rate limits:
- Authenticated: 5,000 requests/hour
- GraphQL batching: ~1 request per 10 PRs (vs 3 per PR with REST)
- Can index ~2,500 PRs per hour (vs ~80 PRs with REST)
- Incremental updates are used by default; use `--clean` only when needed

## MCP Tools

> **Note:** As of v0.4, the PR index is accessible via the unified `git_history` MCP tool, which consolidates all git history operations.

The PR index is accessible via the `git_history` MCP tool in the Cicada server:

### Line-level PR attribution

Find the PR that introduced a specific line of code.

**Usage (v0.4+):**
```python
# Via MCP (unified git_history tool)
cicada.git_history(
    file_path="lib/my_app/user.ex",
    start_line=42
)
```

**Returns:**
- Commit SHA and author
- PR number, title, and URL
- PR status (merged/open/closed)

### File PR history

Get all PRs that modified a file, with descriptions and review comments.

**Usage (v0.4+):**
```python
# Via MCP (unified git_history tool)
cicada.git_history(
    file_path="lib/my_app/user.ex"
)
```

**Returns:**
For each PR that touched the file:
- PR metadata (number, title, author, URL, status)
- PR description/body
- Review comments specific to that file:
  - Comment author and body
  - Current line number (mapped from PR commit)
  - Original line number in PR
  - Resolved status

**Example output:**
```markdown
# Pull Request History for lib/my_app/user.ex

Found 3 pull request(s)

## PR #42: Add user authentication
- **Author:** @wende
- **Status:** merged
- **URL:** https://github.com/owner/repo/pull/42

### Description
This PR adds JWT-based authentication to the User module...

### Review Comments (2)

**@reviewer** (Line 58) ✓ Resolved:
> Consider caching the token validation to avoid redundant DB calls

**@security-team** (Line 92) ✓ Resolved:
> Make sure we're using constant-time comparison for tokens
```

## Features

### Comment Line Mapping

Review comments are automatically mapped from their original PR line numbers to current file lines:

- **Best-effort matching**: Uses content-based search within ±20 lines
- **Handles refactoring**: Tracks lines even if code moved slightly
- **Marks unmappable**: Sets `line: null` if code was deleted/heavily modified
- **Keeps original**: Always preserves `original_line` for reference

This allows you to see where historical comments apply in the current codebase, making it easier to understand past decisions and feedback.

### File-to-PRs Reverse Index

Quickly find all PRs that modified a specific file:

```json
"file_to_prs": {
  "lib/user.ex": [42, 38, 25, 12],
  "README.md": [50, 42, 30]
}
```

PRs are sorted newest-first for easy access to recent changes.

## What's Included

The index captures:

### PR Metadata
- Number, title, URL
- Author and state (open/closed/merged)
- Merge timestamp
- Commits and files changed

### PR Content
- **Description**: Full PR body/description text
- **Review Comments**: Top-level comments only (no reply threads)
- **Resolved comments**: Includes both resolved and unresolved
- **Line tracking**: Current and original line numbers

### Not Included
- PR review comment replies (threads)
- Outdated comments (on old diffs)
- General PR comments (issue-level comments)
- File-level comments (not attached to lines)
