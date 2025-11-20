# Tool Discoverability Improvements - Task List

> **Note:** This document contains historical planning notes. Many of these improvements have been **implemented in v0.4** with the following changes:
> - `search_by_keywords` → renamed to `query` (not `search_by_features` as originally planned)
> - `get_file_pr_history`, `find_pr_for_line`, `get_commit_history`, `get_blame` → consolidated into unified `git_history` tool
> - Tool descriptions updated with clear "WHEN TO USE" guidance
> - API consolidated from 12 tools to 7 focused tools

Based on user feedback about tool discoverability issues, this document outlines the code changes needed to improve the CICADA MCP tool experience.

## 🎯 Primary Goal

Make it immediately obvious to AI assistants **which tool to use when** and encourage the use of conceptual search (`query`) and git history tools (`git_history`).

---

## 📋 Phase 1: Rename and Clarify Tools

### Task 1.1: Rename `search_by_keywords` → `search_by_features`

**Why:** The current name doesn't convey that it's for conceptual/semantic search. Users think of it as advanced/power-user mode rather than the primary tool for "I don't know the exact name" scenarios.

**Alternative names to consider:**
- `search_by_features` (recommended)
- `search_concepts`
- `search_codebase`
- `find_code_by_description`

**Files to update:**
- [ ] `cicada/mcp_server.py` - Tool definition and handler
- [ ] `cicada/cli.py` - Any CLI references
- [ ] `cicada/search_keywords.py` - Rename module if appropriate
- [ ] `tests/test_search_keywords.py` - Test file and test cases
- [ ] `tests/test_mcp_server.py` - MCP server tests
- [ ] `docs/MCP-Tools-Reference.md` - Documentation
- [ ] `CLAUDE.md` - Project instructions
- [ ] `README.md` - Tool descriptions (✅ already updated with better descriptions)

**Implementation details:**
```python
# In mcp_server.py, update tool name:
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    # Change from "search_by_keywords" to "search_by_features"
    if name == "search_by_features":  # Previously: search_by_keywords
        # ...
```

**Backward compatibility:**
- Consider supporting both names temporarily with deprecation warning
- Or do a clean break if the tool is still beta

---

### Task 1.2: Update Tool Descriptions to Emphasize Use Cases

**Why:** Tool descriptions should tell AI assistants WHEN to use them, not just WHAT they do.

**Files to update:**
- [ ] `cicada/mcp_server.py` - Update tool descriptions/docstrings
- [ ] `docs/MCP-Tools-Reference.md` - Expand documentation with use case guidance

**Current vs. Improved descriptions:**

```python
# BEFORE:
"""
search_by_keywords - Search for modules and functions by keywords
"""

# AFTER:
"""
search_by_features - Search for code by concepts and features

🎯 USE THIS WHEN: You don't know exact module/function names but know what the code does
   Examples: "api key storage", "authentication", "email validation", "tab navigation"

Don't know the name? Use this! It's more powerful than guessing with search_function.

Features:
- Semantic search using AI-extracted keywords
- Wildcard patterns: create*, *_user, validate_*
- Returns modules and functions related to your concepts
- Relevance scoring to surface best matches
"""
```

**For ALL tools, add a "WHEN TO USE" section:**
- `search_module` - "When you know the exact module name"
- `search_function` - "When you know the exact function name OR want to find call sites"
- `search_by_features` - "When you know the concept but not the name"
- `get_file_pr_history` - "When you want to understand WHY code exists and design decisions"
- `find_pr_for_line` - "When you need line-level attribution"
- etc.

---

## 📋 Phase 2: Integrate PR Context into Main Search Results

### Task 2.1: Add PR Hints to `search_function` Results

**Why:** Users forget PR tools exist because they're separate. Integrating hints trains AI assistants to use PR context.

**Goal:** When `search_function` returns results, also show if PR context is available.

**Implementation approach:**

```python
# In search_function handler:
def search_function(function_name: str, path: str = None) -> str:
    results = # ... existing search logic ...

    # NEW: Check if PR index exists and file has PR history
    pr_index_path = get_pr_index_path(repo_path)
    if pr_index_path.exists():
        # Check if the file has PR history
        file_path = result["file_path"]
        pr_count = count_prs_for_file(file_path)  # Helper function

        if pr_count > 0:
            results += f"\n\n💡 **Context available:** This file has {pr_count} PRs with review comments."
            results += f"\n   Use `get_file_pr_history(\"{file_path}\")` to see design discussions.\n"

    return results
```

**Files to update:**
- [ ] `cicada/search_function.py` - Add PR hints to output
- [ ] `cicada/pr_indexer.py` - Add helper: `count_prs_for_file(file_path)`
- [ ] `cicada/mcp_server.py` - Ensure search_function has access to PR index path
- [ ] `tests/test_search_function.py` - Test PR hint display

**Output example:**
```markdown
## authenticate/2
lib/app/auth.ex:42

@spec authenticate(email :: String.t(), password :: String.t()) :: {:ok, User.t()} | {:error, atom()}

Called from 5 locations:
- AuthController.login/2 (lib/app_web/controllers/auth_controller.ex:15)
- ApiController.token/2 (lib/app_web/controllers/api_controller.ex:28)
...

💡 **Context available:** This file has 12 PRs with review comments.
   Use `get_file_pr_history("lib/app/auth.ex")` to see design discussions.
```

---

### Task 2.2: Add PR Hints to `search_module` Results

**Why:** Same as above - integrate PR awareness into primary search tools.

**Files to update:**
- [ ] `cicada/search_module.py` - Add PR hints to output
- [ ] `tests/test_search_module.py` - Test PR hint display

---

### Task 2.3: Add "Last Modified By" to Function Results (Future Enhancement)

**Why:** Showing "Last modified: PR #234 'Add OAuth support'" directly in results makes PR tools more discoverable.

**Status:** Document as future enhancement, implement in Phase 3

**Implementation notes:**
- Requires integrating PR index lookups into search results
- Could be expensive for large result sets
- Consider making it optional or only for detailed views

---

## 📋 Phase 3: Improve Tool Discovery in CLAUDE.md

### Task 3.1: Update CLAUDE.md with New Tool Name

**Files to update:**
- [ ] `CLAUDE.md` - Update all references from `search_by_keywords` → `search_by_features`

**Current section:**
```markdown
<cicada>
  **ALWAYS use cicada-mcp tools for Elixir code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers. `mcp__cicada__search_module`
  - PREFERRED for Elixir: Find function definitions and call sites across the codebase. `mcp__cicada__search_function`
  - PREFERRED for Elixir: Find all module usage and dependencies for impact analysis. `mcp__cicada__search_module_usage`
  ...
  - Semantic search for code by concept/topic when exact names are unknown. `mcp__cicada__search_by_keywords`
```

**Update to:**
```markdown
<cicada>
  **ALWAYS use cicada-mcp tools for Elixir code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers. `mcp__cicada__search_module`
  - PREFERRED for Elixir: Find function definitions and call sites across the codebase. `mcp__cicada__search_function`
  - PREFERRED for Elixir: Find all module usage and dependencies for impact analysis. `mcp__cicada__search_module_usage`
  - **PREFERRED when you DON'T KNOW EXACT NAMES**: Search by concepts and features. `mcp__cicada__search_by_features` (use instead of guessing names!)
  - PREFERRED for git history: Discover why code exists and who wrote it. `mcp__cicada__find_pr_for_line`
  - PREFERRED for git history: Get commit log for files or functions. `mcp__cicada__get_commit_history`
  - PREFERRED for authorship: Git blame showing who wrote each line. `mcp__cicada__get_blame`
  - **HIGHLY RECOMMENDED for understanding "why"**: Get all PRs that modified a file with descriptions and review comments. `mcp__cicada__get_file_pr_history`
  - Find potentially unused public functions with confidence levels. `mcp__cicada__find_dead_code`
```

---

### Task 3.2: Add Workflow Examples to CLAUDE.md

**Why:** Give AI assistants concrete examples of tool chaining patterns.

**Add new section:**
```markdown
## Example Workflows

### Finding Code Without Knowing Names
User: "Add API key management"
1. `search_by_features("api key storage encryption")` - Find relevant code
2. `get_file_pr_history(...)` - Understand security approach
3. `search_function("encrypt*")` - Find implementation details

### Understanding Why Code Exists
User: "Why does auth work this way?"
1. `search_by_features("authentication")` - Find auth code
2. `get_file_pr_history("lib/app/auth.ex")` - Read PR discussions
3. `get_commit_history(...)` - See evolution over time
```

**Files to update:**
- [ ] `CLAUDE.md` - Add workflow examples section

---

## 📋 Phase 4: Testing

### Task 4.1: Update Existing Tests

**Files to test:**
- [ ] `tests/test_mcp_server.py` - Update tool name references
- [ ] `tests/test_search_keywords.py` - Rename test file if needed
- [ ] All integration tests that reference `search_by_keywords`

### Task 4.2: Add New Tests for PR Hints

**New test cases:**
- [ ] Test that `search_function` includes PR hints when PR index exists
- [ ] Test that PR hints are NOT shown when PR index doesn't exist
- [ ] Test that `search_module` includes PR hints
- [ ] Test PR hint formatting and message content

### Task 4.3: Test Documentation Updates

**Verify:**
- [ ] README renders correctly with new sections
- [ ] All links work
- [ ] Code examples are accurate
- [ ] MCP-Tools-Reference.md is consistent with code

---

## 📋 Phase 5: Migration and Deprecation

### Task 5.1: Decide on Backward Compatibility

**Options:**

**Option A: Clean break (recommended for beta tool)**
- Remove `search_by_keywords` entirely
- Update all documentation
- Bump version to indicate breaking change

**Option B: Deprecation period**
- Support both `search_by_keywords` and `search_by_features`
- Log deprecation warning when old name is used
- Plan removal in next major version

**Decision needed before implementation!**

### Task 5.2: Update Version and Changelog

**Files to update:**
- [ ] `pyproject.toml` - Bump version (0.2.x → 0.3.0 for breaking change, or 0.2.4 for enhancement)
- [ ] `CHANGELOG.md` - Document changes
- [ ] `README.md` - Update version badge if needed

**Changelog entry:**
```markdown
## v0.3.0 (2025-XX-XX)

### Breaking Changes
- **Renamed `search_by_keywords` → `search_by_features`** for better discoverability
  - Makes it clear this tool is for conceptual search when exact names are unknown
  - Updated all documentation and examples

### Enhancements
- **Improved tool discoverability**
  - Added "Which Tool Should You Use?" decision guide to README
  - Added 5 complete workflow examples showing tool chaining patterns
  - Updated tool descriptions to emphasize WHEN to use each tool
- **PR context hints in search results**
  - `search_function` and `search_module` now show when PR context is available
  - Encourages use of `get_file_pr_history` for understanding design decisions
- **Enhanced CLAUDE.md instructions**
  - Clearer guidance on tool selection
  - Added workflow examples for common scenarios

### Migration Guide
- Replace `search_by_keywords` with `search_by_features` in any custom scripts
- No other changes required
```

---

## 📋 Phase 6: User Communication

### Task 6.1: Update Documentation Website (if applicable)

- [ ] Update any hosted documentation
- [ ] Update examples in blog posts or tutorials
- [ ] Update screenshots if they show tool names

### Task 6.2: Prepare Release Notes

**Key messages:**
1. **Clearer tool naming** - `search_by_features` vs `search_by_keywords`
2. **Better guidance** - Decision trees and workflow examples
3. **Integrated PR hints** - Discover PR context without looking for it
4. **Improved discoverability** - AI assistants will know which tool to use

---

## 🎨 Optional Future Enhancements

These are beyond the current scope but worth documenting:

### Enhancement 1: Inline PR Summary in Function Results
Show the last PR that modified each function directly in the result:
```markdown
## authenticate/2
lib/app/auth.ex:42
📝 Last modified: PR #234 "Add OAuth support" (2 weeks ago)
   💬 @reviewer: "Validate email format"
```

**Complexity:** Medium (requires fast PR lookups)

### Enhancement 2: Auto-suggest Tool Chains
When user uses one tool, suggest logical next steps:
```
✨ Tip: Found 3 modules. Use `get_file_pr_history(...)` to understand why they were built this way.
```

**Complexity:** Low (just add tips to outputs)

### Enhancement 3: Regexp Support Discovery
Add examples of when regexp is better than wildcards:
```
💡 Pro tip: Need complex patterns? Use regexp mode:
   search_by_features(r"^create_.*_async$", use_regexp=true)
```

**Complexity:** Low (documentation update)

### Enhancement 4: Tool Usage Analytics
Track which tools are actually used to validate improvements:
- Log tool calls (anonymized)
- Track tool success rates
- Measure tool chain patterns

**Complexity:** Medium (requires telemetry infrastructure)

---

## ✅ Definition of Done

A task is complete when:
- [ ] Code changes implemented and tested
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated (README, CLAUDE.md, MCP-Tools-Reference.md)
- [ ] Changes committed with clear commit messages
- [ ] Manual testing performed (use the tool in real scenarios)

---

## 📊 Success Metrics

After implementation, we should see:
1. **AI assistants use `search_by_features` more often** when they don't know exact names
2. **More usage of `get_file_pr_history`** after seeing hints in search results
3. **Fewer "give up and ask user" scenarios** when exploring codebases
4. **Better first-time user experience** with clearer tool selection

---

## 🚀 Implementation Order (Recommended)

1. **Start with README** (✅ DONE) - Document the vision
2. **Rename tool** (Phase 1.1) - Core change
3. **Update tool descriptions** (Phase 1.2) - Make purpose clear
4. **Add PR hints** (Phase 2.1, 2.2) - Integrate context discovery
5. **Update CLAUDE.md** (Phase 3) - Train AI assistants
6. **Testing** (Phase 4) - Ensure quality
7. **Version and release** (Phase 5) - Ship it!

---

## 📝 Notes and Decisions

### Decision Log

**2025-11-05: Tool Naming**
- Decision: Rename to `search_by_features` (pending final approval)
- Rationale: Emphasizes searching by "what code does" vs technical "keywords"
- Alternatives considered: `search_concepts`, `search_codebase`, `find_code_by_description`

**2025-11-05: Backward Compatibility**
- Decision: TBD (need to decide between clean break vs deprecation)
- Consideration: Tool is beta, so clean break may be acceptable

**2025-11-05: PR Hints Implementation**
- Decision: Start with simple hint message, not full inline PR data
- Rationale: Lower complexity, faster implementation, still achieves discoverability goal
- Future: Can enhance with inline PR summaries in Phase 3

---

## 🤝 Feedback Integration

This task list was created based on direct user feedback highlighting:
1. **Didn't know keyword search existed** - Tool name doesn't convey purpose
2. **Forgot about PR tools** - They feel disconnected from main workflow
3. **No mental model of tool selection** - Need decision tree and examples

These improvements directly address each issue:
- ✅ Rename tool to make purpose obvious
- ✅ Integrate PR hints into main search results
- ✅ Provide decision guide and workflow examples
