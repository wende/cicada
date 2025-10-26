# CICADA v0.1 TODO List

**Status:** v0.1.1 Released ✅ (October 26, 2025)
**Last Updated:** October 26, 2025
**Philosophy:** Maintain simplicity, avoid feature creep, deliver real user value

## v0.1.1 Release Summary

**Released:** October 26, 2025

The v0.1.1 release includes:
- ✅ Git History Enhancements (precise function tracking, evolution metadata, git blame)
- ✅ Comprehensive test coverage (26 tests total)
- ✅ Automatic version update checking
- ✅ All core functionality from v0

See [README.md](README.md) for complete feature list.

---

## Priorities

- **P0**: Critical for v0.1 release
- **P1**: High value, should include if time permits
- **P2**: Nice to have, can defer to v0.2

## Effort Estimates

- **S** (Small): 1-4 hours
- **M** (Medium): 4-8 hours
- **L** (Large): 8-16 hours

---

## 1. Documentation Search & Linking

### P0: Basic Documentation Indexing (L)

**Goal:** Index markdown files and link them to modules/functions

**Tasks:**
- [ ] Parse markdown files (README.md, docs/*.md)
- [ ] Extract headings and code blocks
- [ ] Detect module/function references in markdown
- [ ] Add documentation entries to index.json
- [ ] Link docs to relevant modules/functions

**Acceptance Criteria:**
- Can index all .md files in repository
- Detects mentions like `` `MyApp.User.create/2` `` in markdown
- Stores file path, line number, surrounding context
- < 5 seconds additional indexing time for typical repos

**Implementation Notes:**
- Use simple regex for code block detection
- Match module names (e.g., `MyApp.User`) in text
- Match function names with arity (e.g., `create/2`)
- Store as `documentation` array in index

---

### P1: Documentation Search Tool (M)

**Goal:** New MCP tool to search documentation

**Tasks:**
- [ ] Add `search_documentation` MCP tool
- [ ] Search by keyword across all markdown files
- [ ] Return matching sections with context
- [ ] Format results in markdown/JSON

**Acceptance Criteria:**
- Can search for keywords like "authentication" or "database"
- Returns relevant doc sections with file/line numbers
- Includes 2-3 lines of context before/after match
- Ranks results by relevance (exact match > partial match)

**Tool Schema:**
```python
search_documentation(
    query: str,           # Search term or phrase
    format: str = "markdown"  # Output format
)
```

**Example Output:**
```markdown
# Documentation Search: "authentication"

## README.md:42
### User Authentication

The User module provides authentication via `User.authenticate/2`...

## docs/SECURITY.md:15
### Authentication Flow

...
```

---

### P2: Link Documentation to Function Results (S)

**Goal:** Show related docs when querying functions

**Tasks:**
- [ ] Extend `search_function` to include related docs
- [ ] Show documentation snippets in results
- [ ] Add `include_documentation` parameter

**Acceptance Criteria:**
- `search_function("authenticate")` shows related docs
- Optional flag to include/exclude docs
- Formatted nicely in both markdown and JSON output

---

## 2. Git History Enhancements

**Status:** COMPLETED ✅ (October 2025)

**What was implemented:**
- Precise function history tracking using `git log -L` for exact line-range changes
- Function evolution metadata (creation date, last modified, total modifications, modification frequency)
- Git blame integration with line-by-line authorship and grouping
- Two new MCP tools: enhanced `get_file_history` (with precise tracking and evolution), `get_function_blame`
- Comprehensive test coverage (26 tests total - 14 new + 12 existing)
- Backward compatibility maintained

---

### P1: Commit History for Functions (M) ✅ COMPLETED

**Goal:** Show commit history for specific functions

**Tasks:**
- [x] Track git log for files containing functions
- [x] Filter commits that touched function lines (using git log -L)
- [x] Show last N commits for a function
- [x] Format commit info (SHA, author, date, message)

**Acceptance Criteria:**
- Can get last 5 commits for `MyApp.User.authenticate/2`
- Shows commit SHA (short), author, date, message
- Fast lookup (< 1 second)
- Works without GitHub (git only)

**Implementation:**
```bash
# Get commits that touched lines 42-58 in file
git log -L 42,58:lib/user.ex --pretty=format:"%h|%an|%ad|%s"
```

---

### P1: Function Evolution View (M) ✅ COMPLETED

**Goal:** See how a function changed over time

**Tasks:**
- [x] Add `get_function_history` tool
- [x] Show when function was created
- [x] Show when function was last modified
- [x] Show number of times modified
- [x] Show modification frequency (commits per month)

**Acceptance Criteria:**
- Returns creation commit, last modified commit
- Shows total number of commits touching the function
- Optionally shows full history with diffs

**Tool Schema:**
```python
get_function_history(
    module_name: str,
    function_name: str,
    include_diffs: bool = False
)
```

---

### P2: Blame Integration (S) ✅ COMPLETED

**Goal:** Show who wrote each line of a function

**Tasks:**
- [x] Add `get_function_blame` helper
- [x] Format blame output nicely
- [x] Add MCP tool for blame
- [x] Group consecutive lines by same author

**Acceptance Criteria:**
- Shows author for each line of function
- Groups consecutive lines by same author
- Optional inclusion in search results

---

## 3. Developer Experience

### P0: Error Handling & Recovery (M)

**Goal:** Graceful degradation and helpful error messages

**Tasks:**
- [ ] Validate index.json on load
- [ ] Handle missing index gracefully
- [ ] Detect stale index (file modified after index)
- [ ] Better error messages for common issues
- [ ] Add index integrity check

**Acceptance Criteria:**
- Clear error when index missing: "Index not found. Run: cicada-index"
- Warn when index is stale (files modified after indexing)
- Recover gracefully from partial index corruption
- All errors include actionable next steps

**Error Messages:**
```
❌ Index not found at .cicada/index.json

Run this to create an index:
  cicada-index

Or specify a different path in .cicada/config.yaml
```

---

### P1: Logging & Debug Mode (S)

**Goal:** Troubleshooting and performance insights

**Tasks:**
- [ ] Add `--verbose` flag to indexer
- [ ] Add `--debug` flag to MCP server
- [ ] Log performance metrics (indexing time, query time)
- [ ] Log cache hits/misses
- [ ] Add statistics summary

**Acceptance Criteria:**
- `cicada-index --verbose` shows detailed progress
- Debug mode logs all tool calls and timings
- Performance metrics available via `--stats` flag
- Can output logs to file

**Example Output:**
```
🐛 [DEBUG] MCP tool call: search_function("authenticate")
⏱️  [PERF] Index loaded in 23ms
⏱️  [PERF] Search completed in 8ms
📊 [STATS] Found 3 matches across 2 modules
```

---

### P1: Index Validation & Repair (M)

**Goal:** Detect and fix common index issues

**Tasks:**
- [ ] Add `cicada-index --validate` command
- [ ] Check index integrity
- [ ] Detect missing or corrupt entries
- [ ] Offer repair options
- [ ] Add `--repair` flag to attempt fixes

**Acceptance Criteria:**
- Validates all required fields present
- Checks file paths exist
- Detects duplicate entries
- Reports issues with actionable fixes
- Can repair common issues automatically

---

## 4. Performance & Quality

### P1: Incremental Re-indexing (L)

**Goal:** Only re-parse changed files

**Tasks:**
- [ ] Track file modification times in index
- [ ] Detect changed files since last index
- [ ] Add `cicada-index --incremental` mode
- [ ] Only re-parse modified files
- [ ] Merge new data with existing index

**Acceptance Criteria:**
- Incremental index is 10x faster for small changes
- Correctly detects new, modified, deleted files
- Maintains index consistency
- Full re-index still available via `--full` flag

**Implementation:**
```python
# Store in index metadata
"files": {
  "lib/user.ex": {
    "last_modified": "2025-10-25T10:30:00Z",
    "last_indexed": "2025-10-25T10:31:00Z",
    "checksum": "abc123..."
  }
}
```

---

### P2: Watch Mode for Development (M)

**Goal:** Auto re-index on file changes during development

**Tasks:**
- [ ] Add `cicada-watch` command
- [ ] Monitor file system for .ex/.exs changes
- [ ] Auto-trigger incremental re-index
- [ ] Debounce rapid changes
- [ ] Show live update status

**Acceptance Criteria:**
- Watches all .ex/.exs files in repo
- Re-indexes within 1 second of change
- Debounces multiple rapid changes (500ms)
- Low CPU overhead (< 5%)

**Dependencies:**
- Requires incremental indexing (P1)
- Use `watchdog` Python library

---

### P2: Index Compression (S)

**Goal:** Reduce index file size

**Tasks:**
- [ ] Add optional gzip compression
- [ ] Compress index.json to index.json.gz
- [ ] Auto-detect and decompress on load
- [ ] Make compression optional

**Acceptance Criteria:**
- Reduces index size by 60-80%
- No performance degradation on load
- Backwards compatible with uncompressed
- Enabled via config option

---

## 5. Polish & UX Improvements

### P1: Better Type Formatting (S)

**Goal:** Prettier display of complex Elixir types

**Tasks:**
- [ ] Format union types nicely: `String.t() | atom()`
- [ ] Handle nested types: `list(map())`
- [ ] Format map types: `%{required(atom()) => term()}`
- [ ] Pretty-print specs across multiple lines

**Acceptance Criteria:**
- Complex types are readable in terminal
- Multi-line formatting for long specs
- Consistent formatting across markdown/JSON

**Example:**
```elixir
# Before
@spec create(map, keyword) :: {:ok, %User{name: String.t(), age: integer()}} | {:error, Ecto.Changeset.t()}

# After (formatted)
@spec create(attrs :: map(), opts :: keyword()) ::
  {:ok, User.t()} |
  {:error, Ecto.Changeset.t()}
```

---

### P1: Code Snippet Syntax Highlighting (S)

**Goal:** Hint at syntax highlighting in output

**Tasks:**
- [ ] Add language hints to markdown code blocks
- [ ] Detect code language (Elixir vs shell vs JSON)
- [ ] Format output for terminal syntax highlighters
- [ ] Test with bat, rich, etc.

**Acceptance Criteria:**
- All code blocks have language hints: `` ```elixir ``
- Compatible with popular terminal highlighters
- Graceful fallback when no highlighter present

---

### P2: Progress Bar for Indexing (S)

**Goal:** Visual feedback during indexing

**Tasks:**
- [ ] Add progress bar with `tqdm` or similar
- [ ] Show % complete and ETA
- [ ] Show current file being processed
- [ ] Responsive updates (not too spammy)

**Acceptance Criteria:**
- Shows during `cicada-index`
- Updates smoothly without flickering
- Shows both count and percentage
- Can be disabled with `--quiet`

**Example:**
```
Indexing: 73% |████████████░░░░| 234/320 files [00:42<00:15, 5.6 files/s]
Current: lib/my_app/accounts/user.ex
```

---

### P2: Index Freshness Indicator (S)

**Goal:** Show when index was last updated

**Tasks:**
- [ ] Display index age in search results
- [ ] Warn if index is > 1 day old
- [ ] Show in MCP tool responses
- [ ] Add to formatter output

**Acceptance Criteria:**
- Shows "Index updated 2 hours ago" in responses
- Warns if stale: "⚠️  Index is 3 days old - consider re-indexing"
- Configurable staleness threshold

---

### P2: Better Handling of Edge Cases (M)

**Goal:** Robust parsing for unusual code patterns

**Tasks:**
- [ ] Handle multi-clause functions better
- [ ] Support function delegates
- [ ] Parse macros that generate functions
- [ ] Handle protocol implementations
- [ ] Support behaviour callbacks

**Acceptance Criteria:**
- Correctly identifies all clauses of multi-clause functions
- Detects `defdelegate` and links to target
- Handles common macro patterns (e.g., Phoenix routes)
- Marks protocol implementations distinctly

---

## 6. Testing & Documentation

### P0: Update Tests for New Features (M)

**Goal:** Comprehensive test coverage for v0.1

**Tasks:**
- [ ] Tests for documentation indexing
- [ ] Tests for git history features
- [ ] Tests for error handling
- [ ] Tests for incremental indexing
- [ ] Update existing tests as needed

**Acceptance Criteria:**
- Test coverage > 80%
- All new features have tests
- Tests pass on CI
- No regressions in v0 functionality

---

### P0: Update Documentation (S)

**Goal:** Document all v0.1 features

**Tasks:**
- [ ] Update README.md with v0.1 features
- [ ] Document new MCP tools
- [ ] Update CLI usage examples
- [ ] Add troubleshooting section
- [ ] Update CHANGELOG.md

**Acceptance Criteria:**
- All new tools documented in README
- CLI help text up to date
- Examples for all new features
- Migration guide from v0 to v0.1

---

## 7. Optional Nice-to-Haves

### P2: Configuration File Validation (S)

**Tasks:**
- [ ] Validate .cicada/config.yaml on load
- [ ] Schema validation
- [ ] Helpful error messages for misconfigurations
- [ ] Example config file

---

### P2: Shell Completion (S)

**Tasks:**
- [ ] Bash completion for `cicada-index`
- [ ] Zsh completion
- [ ] Fish completion
- [ ] Installation script

---

### P2: Rich Terminal Output (S)

**Tasks:**
- [ ] Use `rich` library for prettier terminal output
- [ ] Color-coded output
- [ ] Tables for results
- [ ] Progress spinners

---

## Non-Goals for v0.1

**These are explicitly OUT OF SCOPE:**

- ❌ Fuzzy search or "did you mean" suggestions
- ❌ Function similarity or recommendations
- ❌ Confidence scoring of any kind
- ❌ Multi-repository support
- ❌ Vector/semantic search
- ❌ Database backends
- ❌ ML/AI features
- ❌ Web UI
- ❌ Alternative function suggestions
- ❌ Comprehensive call graphs
- ❌ Multi-language support

---

## Implementation Order

### Phase 1: Core Features (Must Have)
1. Error handling & recovery (P0, M)
2. Index validation & repair (P1, M)
3. Basic documentation indexing (P0, L)
4. Update tests (P0, M)
5. Update documentation (P0, S)

**Estimated Time:** 30-40 hours

### Phase 2: High-Value Additions (Should Have)
1. Documentation search tool (P1, M)
2. Commit history for functions (P1, M)
3. Logging & debug mode (P1, S)
4. Incremental re-indexing (P1, L)
5. Better type formatting (P1, S)

**Estimated Time:** 25-35 hours

### Phase 3: Polish (Nice to Have)
1. Function evolution view (P1, M)
2. Code snippet syntax highlighting (P1, S)
3. Watch mode (P2, M)
4. Progress bar (P2, S)
5. Edge case handling (P2, M)

**Estimated Time:** 20-30 hours

---

## Total Effort Estimate

- **Minimum (Phase 1 only):** 30-40 hours (~1 week)
- **Recommended (Phases 1 + 2):** 55-75 hours (~2 weeks)
- **Complete (All phases):** 75-105 hours (~3 weeks)

---

## Success Criteria for v0.1 Release

### Completed in v0.1.1 ✅
- ✅ Git commit history integration with precise function tracking
- ✅ Function evolution metadata (creation, modifications, frequency)
- ✅ Git blame integration with line-by-line authorship
- ✅ Comprehensive test coverage (26 tests)
- ✅ Automatic version update checking
- ✅ Documentation updated

### Deferred to v0.2+
- Documentation indexing and search
- Incremental code re-indexing
- Robust error handling enhancements
- Index validation and repair functionality
- Logging and debug mode improvements
- Better type formatting
- Watch mode for development
- Terminal UI improvements

---

## Post-Release

After v0.1 ships, consider:
- Gather user feedback on documentation search
- Measure adoption of new features
- Identify pain points
- Plan v0.2 based on actual usage

---

**Remember:** Keep it simple. Ship working code. Get feedback. Iterate.
