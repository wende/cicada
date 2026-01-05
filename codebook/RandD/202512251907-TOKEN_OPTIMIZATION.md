# PRD 23: MCP Tool Token Optimization

**Status:** Draft
**Author:** Claude
**Date:** 2025-11-27
**Priority:** Medium-High

## Executive Summary

Cicada MCP tools produce unnecessarily verbose output that wastes tokens in AI agent conversations. Analysis shows that for simple queries like "when was this developed and why?", standard bash tools (`git log`) are more token-efficient than cicada tools despite cicada having richer indexed data. This document proposes output customization parameters to reduce token usage by 40-80% without sacrificing capability.

---

## 1. Problem Statement

### 1.1 The Core Issue

Cicada MCP tools are designed to provide comprehensive context, but this "context by default" philosophy leads to significant token waste when AI agents only need specific information.

**Observed behavior:**
- Simple history query using cicada: ~3,500-4,000 tokens
- Same query using `git log`: ~2,500-3,000 tokens
- Token overhead: **25-40% waste**

### 1.2 Magnitude

| Scenario | Cicada Tokens | Optimal Tokens | Waste |
|----------|---------------|----------------|-------|
| File history (5 PRs) | ~2,400 | ~800 | 67% |
| Failed keyword query | ~250 | ~50 | 80% |
| Module search (10 functions) | ~1,800 | ~600 | 67% |
| Function call sites (20 sites) | ~2,000 | ~800 | 60% |

**Impact on AI agents:**
- Faster context exhaustion in long conversations
- Higher API costs for users
- Reduced effectiveness when exploring large codebases
- AI agents may prefer raw bash commands over indexed tools

### 1.3 Root Causes

1. **No output granularity controls** - Tools return everything or nothing
2. **PR metadata always included** - Descriptions, review comments, URLs
3. **Verbose error messages** - Multi-line instructions on failures
4. **Documentation included by default** - Full docstrings in search results
5. **No "brief" mode** - Every query returns full context

---

## 2. Evidence & Examples

### 2.1 Example: `git_history` Tool

**Query:** "When was Python support developed and why?"

**Cicada output (truncated):**
```markdown
## History for cicada/languages/python/indexer.py

### PR #178: Auto-install scip-python locally and fail tests on missing SCIP indexes (merged, 2025-11-24)
**Author:** @wende
**URL:** https://github.com/wende/cicada/pull/178

Add local scip-python installation to ~/.cicada/node/ (avoids polluting global npm)
Auto-install on first Python index if npm is available
Add make setup-scip target for local dev SCIP index setup
Change SCIP-related tests from skip to fail when indexes missing
Update installer to check both global PATH and local ~/.cicada/node/

Summary by Sourcery
Add support for local scip-python installation and enforce presence of pre-generated SCIP indexes for tests.
New Features:

*(truncated)*

**Review comments:**
> Line 552 (gemini-code-assist): ![medium](https://www.gstatic.com/codereviewagent/medium-priority.svg)

The check `if "/.cicada/" in

---

### PR #175: Optimize Python SCIP conversion from O(n²) to O(n) - 71x faster (merged, 2025-11-25)
...
```

**Token count:** ~800 tokens for 2 PRs

**What the AI actually needed:**
```markdown
## History for cicada/languages/python/indexer.py

### 589000d3 (2025-11-25) - Krzysztof Wende
Optimize Python SCIP conversion from O(n²) to O(n) - 71x faster (#175)

### 08856380 (2025-11-25) - Krzysztof Wende
Auto-install scip-python locally (#178)
```

**Token count:** ~80 tokens

**Waste:** 90% of tokens were PR descriptions, review comments, URLs, and metadata that weren't used in the final answer.

### 2.2 Example: Failed `query` Tool

**Query:** `mcp__cicada__query("python implementation")`

**Current error output:**
```
No keywords found in index. Please rebuild the index with keyword extraction:

  cicada index           # Default: reuse configured mode
  cicada index --force --keywords  # Keywords mode (default)
  cicada index --force --embeddings  # Embeddings mode (not implemented yet)

This will extract keywords from documentation for semantic search.
```

**Token count:** ~250 tokens

**Optimal error:**
```
No keywords in index. Run 'cicada index' to enable keyword search.
```

**Token count:** ~15 tokens

**Waste:** 94% of tokens were instructions the AI couldn't act upon.

### 2.3 Example: `search_module` Tool

**Query:** Get module API for `cicada.languages.python.indexer`

**Current output includes:**
- Full function signatures (useful)
- Complete docstrings (often not needed)
- Type specifications (sometimes useful)
- Line numbers (useful)
- File path (useful)

For a quick overview, 60% of output is docstrings that may not be relevant.

### 2.4 Comparative Analysis

**Task:** Find all files responsible for Python implementation, when developed, why

| Approach | Tool Calls | Total Tokens | Quality |
|----------|------------|--------------|---------|
| Cicada tools | 3 | ~4,000 | Good (rich metadata) |
| Bash only | 11 | ~3,200 | Good (transparent) |
| Optimal cicada | 3 | ~1,500 | Same (with new params) |

The "optimal cicada" row represents the potential with output customization.

---

## 3. Affected Components

### 3.1 Files Requiring Changes

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `cicada/mcp/tools.py` | Tool schema definitions | Add new parameters |
| `cicada/git/formatter.py` | Git history formatting | Conditional output sections |
| `cicada/mcp/handlers/git_handlers.py` | Git tool handler | Pass new params to formatter |
| `cicada/mcp/handlers/module_handlers.py` | Module search handler | Add docs/specs filtering |
| `cicada/mcp/handlers/function_handlers.py` | Function search handler | Add output controls |
| `cicada/mcp/handlers/analysis_handlers.py` | Query handler | Compact error messages |
| `cicada/format/formatter.py` | General formatting | Output mode support |

### 3.2 Current Parameter Inventory

**`git_history` tool - existing parameters:**
- `file_path` (required)
- `start_line`, `end_line` (optional)
- `function_name` (optional)
- `recent`, `recent_days` (optional)
- `author` (optional)
- `max_results` (default: 10)
- `show_evolution` (default: false)

**Missing:** Output verbosity controls

**`search_module` tool - existing parameters:**
- `module_name` or `file_path` (required)
- `type`: public/private/all
- `format`: markdown/json
- `what_calls_it`, `what_it_calls` (optional)

**Missing:** `include_docs`, `include_specs`, `max_functions`

**`search_function` tool - existing parameters:**
- `function_name` (required)
- `include_usage_examples` (default: false)
- `max_examples` (default: 5)
- `what_calls_it`, `what_it_calls` (optional)

**Missing:** `compact` output mode

---

## 4. Proposed Solutions

### 4.1 Solution A: Per-Tool Output Parameters (Recommended)

Add granular control parameters to each tool.

#### 4.1.1 `git_history` New Parameters

```python
{
    "include_pr_description": {
        "type": "boolean",
        "description": "Include PR body text. Defaults to false.",
        "default": False
    },
    "include_review_comments": {
        "type": "boolean",
        "description": "Include PR review comments. Defaults to false.",
        "default": False
    },
    "max_description_lines": {
        "type": "integer",
        "description": "Max lines of PR description when included. Defaults to 5.",
        "default": 5
    },
    "output_format": {
        "type": "string",
        "enum": ["brief", "standard", "verbose"],
        "description": "Output verbosity. 'brief' = commit/date/message only, 'standard' = current behavior, 'verbose' = include all PR metadata.",
        "default": "standard"
    }
}
```

**Brief format output:**
```markdown
## History for cicada/languages/python/indexer.py

- 589000d3 (2025-11-25) Optimize Python SCIP conversion (#175)
- 08856380 (2025-11-25) Auto-install scip-python locally (#178)
- e68df27d (2025-11-23) Refactor Python support for safety (#160)
```

**Standard format output:** Current default (PR titles, authors, URLs)

**Verbose format output:** Full PR descriptions + review comments

#### 4.1.2 `search_module` New Parameters

```python
{
    "include_docs": {
        "type": "boolean",
        "description": "Include function docstrings. Defaults to true.",
        "default": True
    },
    "include_specs": {
        "type": "boolean",
        "description": "Include type specifications. Defaults to true.",
        "default": True
    },
    "max_functions": {
        "type": "integer",
        "description": "Maximum functions to show per module. Defaults to 50.",
        "default": 50
    }
}
```

#### 4.1.3 `search_function` New Parameters

```python
{
    "output_format": {
        "type": "string",
        "enum": ["brief", "standard"],
        "description": "Output verbosity. 'brief' = definition + call count only.",
        "default": "standard"
    }
}
```

#### 4.1.4 `query` Error Message Optimization

Change error handling in `analysis_handlers.py`:

```python
# Current
return "No keywords found in index. Please rebuild the index with keyword extraction:\n\n  cicada index  ..."

# Proposed
return "No keywords in index. Run 'cicada index' to enable."
```

### 4.2 Solution B: Global Output Mode (Complementary)

Add a universal `output_mode` parameter recognized by all tools.

```python
"output_mode": {
    "type": "string",
    "enum": ["compact", "standard", "verbose"],
    "description": "Global output verbosity. Overrides tool defaults."
}
```

| Mode | Behavior |
|------|----------|
| `compact` | Minimal: identifiers, file:line, one-line summaries |
| `standard` | Current defaults |
| `verbose` | Everything: full docs, PR bodies, review comments |

**Implementation:** Each handler checks for `output_mode` first, then falls back to tool-specific params.

### 4.3 Solution C: Response Size Limits (Safety Net)

Add hard limits to prevent runaway token usage:

```python
MAX_RESPONSE_TOKENS = {
    "git_history": 2000,
    "search_module": 3000,
    "search_function": 2000,
    "query": 1500,
}
```

When output exceeds limit, truncate with:
```
... (truncated, showing 50 of 127 results. Use filters to narrow.)
```

---

## 5. Implementation Plan

### Phase 1: Quick Wins (Low Risk)

1. **Shorten error messages** in `analysis_handlers.py`
2. **Add `output_format` to `git_history`** with "brief" option
3. **Default `include_pr_description` to false**

**Estimated effort:** 2-4 hours
**Token savings:** 40-60% on git_history calls

### Phase 2: Module/Function Tools

1. **Add `include_docs` parameter** to `search_module`
2. **Add `output_format` to `search_function`**
3. **Implement truncation limits**

**Estimated effort:** 4-6 hours
**Token savings:** 30-50% on search calls

### Phase 3: Global Output Mode

1. **Add `output_mode` to tool schemas**
2. **Implement mode inheritance in handlers**
3. **Update documentation**

**Estimated effort:** 6-8 hours
**Token savings:** Flexible per-conversation control

---

## 6. Reasoning & Trade-offs

### 6.1 Why Per-Tool Parameters (Solution A)?

**Pros:**
- Fine-grained control for different use cases
- Backward compatible (new params have sensible defaults)
- AI agents can optimize per-query
- No breaking changes

**Cons:**
- More parameters to document
- Slight cognitive overhead for users

### 6.2 Why Change Defaults?

Current defaults assume humans reading output. AI agents have different needs:
- **Humans:** Prefer context, can skim verbose output
- **AI agents:** Pay per token, need targeted information

Changing `include_pr_description` default to `false` optimizes for the common case (AI exploration) while preserving capability for deep dives.

### 6.3 Why Not Just Truncate Everything?

Aggressive truncation loses valuable information. Parameterized output lets AI agents choose:
- Quick exploration: `output_format="brief"`
- Deep investigation: `output_format="verbose", include_review_comments=true`

### 6.4 Backward Compatibility

All changes are additive:
- New parameters have defaults matching current behavior
- Existing tool calls continue to work
- No breaking changes to MCP interface

---

## 7. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Avg tokens per `git_history` call | ~800 | ~300 | Log analysis |
| Avg tokens per `search_module` call | ~600 | ~250 | Log analysis |
| Error message tokens | ~250 | ~50 | Code review |
| AI preference for cicada vs bash | ~50% | ~80% | User feedback |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing integrations | Low | High | All params optional with current defaults |
| Over-optimization losing context | Medium | Medium | "standard" mode preserves current behavior |
| Documentation drift | Medium | Low | Update CLAUDE.md with new params |
| AI agents ignoring new params | Medium | Low | Update tool descriptions with recommendations |

---

## 9. Open Questions

1. **Should `output_format="brief"` be the new default?**
   - Pro: Optimizes for common AI agent use case
   - Con: Breaking change for existing workflows

2. **Should we add a `max_tokens` parameter?**
   - Pro: Direct control over output size
   - Con: Complex to implement accurately

3. **Should error messages include suggestions at all?**
   - Pro: Helpful for debugging
   - Con: AI agents can't act on CLI instructions

---

## 10. References

- Token analysis conversation: 2025-11-27
- Affected files: `cicada/mcp/tools.py`, `cicada/git/formatter.py`
- Related PRDs: None

---

## Appendix A: Full Parameter Schema (Proposed)

### A.1 `git_history` Complete Schema

```python
{
    "file_path": {"type": "string", "required": True},
    "start_line": {"type": "integer"},
    "end_line": {"type": "integer"},
    "function_name": {"type": "string"},
    "recent": {"type": "boolean"},
    "recent_days": {"type": "integer", "default": 14},
    "author": {"type": "string"},
    "max_results": {"type": "integer", "default": 10},
    "show_evolution": {"type": "boolean", "default": False},
    # NEW
    "output_format": {"type": "string", "enum": ["brief", "standard", "verbose"], "default": "standard"},
    "include_pr_description": {"type": "boolean", "default": False},
    "include_review_comments": {"type": "boolean", "default": False},
    "max_description_lines": {"type": "integer", "default": 5},
}
```

### A.2 `search_module` Complete Schema

```python
{
    "module_name": {"type": "string"},
    "file_path": {"type": "string"},
    "format": {"type": "string", "enum": ["markdown", "json"], "default": "markdown"},
    "type": {"type": "string", "enum": ["public", "private", "all"], "default": "public"},
    "what_calls_it": {"type": "boolean", "default": False},
    "what_it_calls": {"type": "boolean", "default": False},
    # NEW
    "include_docs": {"type": "boolean", "default": True},
    "include_specs": {"type": "boolean", "default": True},
    "max_functions": {"type": "integer", "default": 50},
    "output_format": {"type": "string", "enum": ["brief", "standard"], "default": "standard"},
}
```

---

## Appendix B: Example Output Comparisons

### B.1 `git_history` Brief vs Standard

**Brief (`output_format="brief"`):**
```
## History for cicada/languages/python/indexer.py (5 commits)

- 589000d (2025-11-25) Optimize SCIP conversion O(n²)→O(n) (#175)
- 0885638 (2025-11-25) Auto-install scip-python locally (#178)
- e68df27 (2025-11-23) Refactor Python support for safety (#160)
- de01255 (2025-11-22) Fix recent=true filter for Python (#141)
- 1c9cdac (2025-11-22) Refactor MCP server architecture (#135)
```
**~120 tokens**

**Standard (`output_format="standard"`):**
```
## History for cicada/languages/python/indexer.py

### PR #178: Auto-install scip-python locally and fail tests on missing SCIP indexes (merged, 2025-11-24)
**Author:** @wende
**URL:** https://github.com/wende/cicada/pull/178

---

### PR #175: Optimize Python SCIP conversion from O(n²) to O(n) - 71x faster (merged, 2025-11-25)
**Author:** @wende
**URL:** https://github.com/wende/cicada/pull/175

---
...
```
**~400 tokens**

**Verbose (`output_format="verbose"`, `include_pr_description=true`, `include_review_comments=true`):**
```
## History for cicada/languages/python/indexer.py

### PR #178: Auto-install scip-python locally and fail tests on missing SCIP indexes (merged, 2025-11-24)
**Author:** @wende
**URL:** https://github.com/wende/cicada/pull/178

Add local scip-python installation to ~/.cicada/node/ (avoids polluting global npm)
Auto-install on first Python index if npm is available
Add make setup-scip target for local dev SCIP index setup
...

**Review comments:**
> Line 552 (gemini-code-assist): The check `if "/.cicada/" in...
> Line 123 (sourcery-ai): Consider extracting this to a helper...

---
...
```
**~1,200 tokens**
