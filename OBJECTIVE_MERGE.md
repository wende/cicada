# OBJECTIVE: Align v0.2-BERT with Main Branch Changes

**Date:** 2025-10-31
**Branch:** feat/v0.2-BERT
**Status:** Investigation Complete - Ready for Implementation

---

## Context

After merging main into feat/v0.2-BERT (commit 79d9dfb), several key architectural changes from main need to be properly integrated. The user identified three specific issues, and investigation revealed the actual state of affairs.

---

## Investigation Findings

### Finding #1: Command Naming Architecture (CRITICAL - Merge Regression)

**User's Initial Understanding:**
- Main uses old dashed commands (cicada-index, cicada-install)
- Need to adopt new non-dash version

**Actual Reality:**
- ❌ Main branch STILL uses dashed commands in pyproject.toml
- ✅ **v0.2-BERT ALREADY HAD** the unified CLI from PR #18 (commit 7213533)
- ❌ The merge from main **OVERWROTE** pyproject.toml and **LOST** the unified CLI
- ✅ The implementation still exists in `cicada/cli.py` but is not wired up

**Evidence:**
```bash
# Main branch (current):
cicada-server = "cicada.mcp_server:main"
cicada = "cicada.setup:main"              # ← Points to setup.py
cicada-install = "cicada.install:main"
cicada-clean = "cicada.clean:main"
cicada-index = "cicada.indexer:main"
cicada-index-pr = "cicada.pr_indexer:main"
cicada-find-dead-code = "cicada.find_dead_code:main"

# v0.2-BERT before merge (from commit 7213533):
cicada-server = "cicada.mcp_server:main"
cicada = "cicada.cli:main"                # ← Points to unified CLI

# v0.2-BERT after merge (current):
cicada-server = "cicada.mcp_server:main"
cicada = "cicada.setup:main"              # ← REGRESSION - lost unified CLI
cicada-install = "cicada.install:main"    # ← Should not exist
cicada-clean = "cicada.clean:main"        # ← Should not exist
cicada-index = "cicada.indexer:main"      # ← Should not exist
cicada-index-pr = "cicada.pr_indexer:main"  # ← Should not exist
cicada-find-dead-code = "cicada.find_dead_code:main"  # ← Should not exist
```

**Impact:** The unified CLI architecture (cicada index, cicada index-pr, etc.) is completely broken.

---

### Finding #2: SpaCy Removal (ALREADY DONE)

**User's Initial Understanding:**
- Main removed spaCy entirely
- Need to update interactive setup

**Actual Reality:**
- ✅ SpaCy WAS removed in main's PR #25 (commit bd7e7f5)
- ✅ Replaced with lemminflect (20x faster)
- ✅ Already merged into v0.2-BERT via the merge commit
- ✅ `cicada/lightweight_keyword_extractor.py` exists and works
- ✅ No spaCy references remain in code

**Evidence:**
```bash
$ grep -rn "spacy\|spaCy" cicada/*.py
# (no output - completely removed)

$ ls -la cicada/*keyword*.py
cicada/keyword_search.py
cicada/lightweight_keyword_extractor.py  # ← New lemminflect-based
```

**Impact:** No action needed - already complete.

---

### Finding #3: Editor-Specific Installation (ALREADY EXISTS)

**User's Initial Understanding:**
- Main added single-line scripts for different editors
- Need to add editor selection to interactive setup

**Actual Reality:**
- ✅ Editor-specific installation ALREADY implemented in `cicada/setup.py`
- ✅ Commands work: `uvx cicada [claude|cursor|vs]`
- ✅ Documentation exists in `extensions/claude-code/INSTALL.md` and `extensions/cursor/INSTALL.md`
- ❌ Interactive setup doesn't offer editor choice
- ❌ Interactive setup only handles extraction method/model tier

**Evidence:**
```python
# cicada/setup.py:280-295
def main():
    parser = argparse.ArgumentParser(
        description="Cicada One-Command Setup",
        epilog="Example: uvx cicada claude",
    )
    parser.add_argument(
        "editor",
        choices=["claude", "cursor", "vs"],
        help="Editor to configure (claude=Claude Code, cursor=Cursor, vs=VS Code)",
    )
```

**Impact:** Feature exists but interactive setup should be enhanced to include editor selection.

---

### Finding #4: Documentation Inconsistency (CRITICAL)

**Actual Reality:**
- ✅ `docs/CLI_MIGRATION.md` correctly documents NEW unified commands
- ❌ `README.md` still uses OLD dashed commands throughout (~15+ instances)
- ❌ `docs/INCREMENTAL_INDEXING.md` uses OLD commands
- ❌ `docs/BERT_KEYWORD_EXTRACTOR.md` uses OLD commands
- ❌ `docs/MCP_TOOLS_REFERENCE.md` uses OLD commands

**Evidence:**
```bash
$ grep -n "cicada-index" README.md
70:cicada-index --extract-keywords --rag --model-tier fast
87:cicada-index --extract-keywords
91:cicada-index --extract-keywords
# ... 15+ more instances
```

**Impact:** Users will be confused by inconsistent documentation.

---

## Required Changes

### Priority 1: Fix pyproject.toml (CRITICAL - Merge Regression)

**File:** `pyproject.toml`

**Change:**
```toml
[project.scripts]
cicada-server = "cicada.mcp_server:main"
cicada = "cicada.cli:main"  # ← Change from "cicada.setup:main"
# Remove all dashed commands:
# - cicada-install
# - cicada-clean
# - cicada-index
# - cicada-index-pr
# - cicada-find-dead-code
```

**Rationale:** Restore the unified CLI architecture that was introduced in PR #18 but lost in the merge.

---

### Priority 2: Update README.md (HIGH)

**File:** `README.md`

**Changes:**
1. Replace ALL `cicada-index` → `cicada index`
2. Replace ALL `cicada-index-pr` → `cicada index-pr`
3. Replace ALL `cicada-find-dead-code` → `cicada find-dead-code`
4. Update "Available commands" section to reflect unified CLI
5. Update "What's New in v0.2.0" to mention lemminflect (not spaCy)

**Instances to fix:** ~15+ command references

---

### Priority 3: Update Documentation Files (HIGH)

**Files to update:**

1. **docs/INCREMENTAL_INDEXING.md**
   - Replace `cicada-index` → `cicada index`
   - ~3 instances

2. **docs/BERT_KEYWORD_EXTRACTOR.md**
   - Replace `cicada-index` → `cicada index`
   - ~2 instances

3. **docs/MCP_TOOLS_REFERENCE.md**
   - Replace `cicada-index-pr` → `cicada index-pr`
   - Replace `cicada-index` → `cicada index`
   - ~2 instances

4. **extensions/claude-code/INSTALL.md**
   - Verify consistency (mostly correct already)

**Note:** `docs/CLI_MIGRATION.md` is already correct - it documents the migration itself.

---

### Priority 4: Enhance Interactive Setup (MEDIUM - User Request)

**File:** `cicada/interactive_setup.py`

**Changes:**

1. Add new function `show_editor_selection()` that prompts for editor choice
2. Modify `show_first_time_setup()` to include editor selection
3. Change return type from `tuple[str, str]` to `tuple[str, str, str | None]`
   - Returns: `(extraction_method, model_tier, editor)`
   - Where `editor` is: "claude" | "cursor" | "vs" | None

**Example implementation:**
```python
def show_editor_selection() -> str | None:
    """Prompt user to select an editor (or skip)."""
    editor_items = [
        "Claude Code - AI coding assistant",
        "Cursor - AI-first code editor",
        "VS Code - Popular code editor",
        "None - Just index (configure editor manually later)",
    ]
    # ... implementation
    return editor  # "claude" | "cursor" | "vs" | None
```

**Callers to update:**
- `cicada/cli.py` - Update `handle_index()` to handle editor selection if interactive setup returns it

---

### Priority 5: Verify Integration (HIGH)

**Tasks:**

1. ✅ Ensure `cicada/cli.py` still exists and functions correctly
2. ✅ Test that `cicada index` routes to the correct handler
3. ✅ Test that `cicada index-pr` works
4. ✅ Test that `cicada find-dead-code` works
5. ✅ Run `make test` to ensure no regressions
6. ✅ Test `uvx cicada claude` still works with new pyproject.toml

---

## Implementation Order

1. **FIRST:** Fix `pyproject.toml` (restores unified CLI)
2. **SECOND:** Update `README.md` (user-facing documentation)
3. **THIRD:** Update other documentation files
4. **FOURTH:** Enhance interactive setup with editor selection (optional)
5. **FIFTH:** Run tests and verify everything works

---

## Files to Modify

### Configuration
- [ ] `pyproject.toml` - Fix project.scripts

### Documentation (User-Facing)
- [ ] `README.md` - Update all command references (~15+ instances)
- [ ] `docs/INCREMENTAL_INDEXING.md` - Update command syntax (~3 instances)
- [ ] `docs/BERT_KEYWORD_EXTRACTOR.md` - Update command syntax (~2 instances)
- [ ] `docs/MCP_TOOLS_REFERENCE.md` - Update command syntax (~2 instances)
- [ ] `extensions/claude-code/INSTALL.md` - Verify consistency

### Code (Optional Enhancement)
- [ ] `cicada/interactive_setup.py` - Add editor selection
- [ ] `cicada/cli.py` - Update to handle editor selection

### Testing
- [ ] Run `make test`
- [ ] Manual testing of unified CLI commands

---

## Success Criteria

✅ `cicada index` works (not `cicada-index`)
✅ `cicada index-pr` works (not `cicada-index-pr`)
✅ `cicada find-dead-code` works (not `cicada-find-dead-code`)
✅ All documentation uses unified CLI syntax
✅ Interactive setup optionally includes editor selection
✅ All tests pass
✅ No regressions in existing functionality

---

## Notes

- The unified CLI architecture was ALREADY implemented in v0.2-BERT via PR #18
- The main branch merge REGRESSED this functionality by overwriting pyproject.toml
- SpaCy removal is ALREADY complete - no work needed
- Editor-specific installation is ALREADY implemented - just needs interactive enhancement
