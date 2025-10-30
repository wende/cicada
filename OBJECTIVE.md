# Objective: Fast First-Run Experience with Optional Keyword Indexing

## Mission Statement

Ensure Cicada provides an instant first-run experience (<10 seconds) with basic indexing, while allowing users to opt-in to powerful keyword/semantic search features when ready.

---

## Core Requirements

### Requirement 1: Instantaneous Basic Indexing (MCP Path)

**Objective:** MCP users get instant first-run experience via auto-setup. CLI users get full features by default.

#### Test Case 1.1: CLI Setup (Power User - WITH Keywords)
```bash
# Power user runs CLI setup
cicada /path/to/elixir/project

# Expected result:
# - .cicada/ directory created
# - Full index.json created (WITH keywords)
# - config.yaml created with keywords.method: "spacy"
# - .mcp.json generated (if Elixir project detected)
# - Total time: 2-5 minutes (first run with model download)
```

**Verification Checklist:**
- [ ] Command includes keyword extraction by default
- [ ] Progress messages during model download
- [ ] Progress messages during keyword extraction
- [ ] `.cicada/index.json` exists with keyword fields
- [ ] `.cicada/config.yaml` exists with `keywords: { method: "spacy", model: "fast" }`
- [ ] All MCP tools work including `search_by_keywords`

#### Test Case 1.2: CLI Fast Setup (Optional Speed Mode)
```bash
# User wants quick setup without keywords
cicada /path/to/elixir/project --no-keywords
# OR
cicada index --no-keywords

# Expected result:
# - .cicada/ directory created
# - Basic index.json created (NO keywords)
# - config.yaml created with keywords.method: null
# - Total time: < 10 seconds
```

**Verification Checklist:**
- [ ] `--no-keywords` flag recognized
- [ ] Command completes in <10 seconds for typical repo (100-500 files)
- [ ] `.cicada/index.json` exists
- [ ] `.cicada/config.yaml` exists with correct structure
- [ ] Config contains: `keywords: { method: null, model: null }`
- [ ] No model downloads triggered
- [ ] No keyword extraction performed

#### Test Case 1.3: MCP Server Starts Successfully (With Existing Setup)
```bash
# User already ran CLI setup, now starts MCP client
# MCP server auto-starts via .mcp.json

# Expected result:
# - Server starts without errors
# - Loads config successfully
# - Detects keyword availability from config
# - All tools available based on config
```

**Verification Checklist:**
- [ ] MCP server starts without FileNotFoundError
- [ ] Config loads from `.cicada/config.yaml`
- [ ] Index loads from `.cicada/index.json`
- [ ] `self._has_keywords` returns correct value based on config
- [ ] No crashes on startup

#### Test Case 1.4: Basic Tools Work Without Keywords
```bash
# User tries MCP tools (with basic-only index)

# Tools that MUST work:
# - search_module
# - search_function
# - search_module_usage
# - find_pr_for_line (if pr_index exists)
# - get_commit_history
# - get_blame
# - get_file_pr_history
# - find_dead_code
```

**Verification Checklist:**
- [ ] `search_module` returns module info correctly
- [ ] `search_function` finds functions and call sites
- [ ] `search_module_usage` shows module dependencies
- [ ] All git-based tools work (blame, history, PR lookup)
- [ ] Dead code analyzer works

#### Test Case 1.5: Keyword Tool Shows Helpful Error
```bash
# User tries keyword search tool (when keywords not available)

# Expected result:
# Tool returns friendly error with instructions
```

**Expected Error Message:**
```
No keywords found in index. To enable semantic search, run:

  cicada index

This will extract keywords from documentation using NLP (takes 2-5 minutes first time).
```

**Verification Checklist:**
- [ ] `search_by_keywords` tool returns clear error
- [ ] Error message includes command to enable keywords
- [ ] Error explains what keywords are for
- [ ] No technical jargon or stack traces

---

### Requirement 2: CLI Keyword Indexing (Power User Default)

**Objective:** CLI users get full keyword extraction by default, with option to skip for speed.

#### Test Case 2.1: CLI Default Behavior (With Keywords)
```bash
# Power user runs CLI indexing
cicada index

# Expected result:
# - Shows what will happen (model download + extraction if first time)
# - Downloads spaCy model (12MB for default --fast)
# - Progress: "Extracting keywords: 47/200 files (23%)"
# - Updates config.yaml with keywords.method = "spacy"
# - Updates config.yaml with keywords.model = "fast"
# - Total time: 2-5 minutes first run, <5s incremental
```

**Verification Checklist:**
- [ ] `cicada index` includes keywords by default
- [ ] Clear progress messages before model download
- [ ] Model download shows progress
- [ ] Keyword extraction shows file-by-file progress
- [ ] Config updates: `keywords: { method: "spacy", model: "fast" }`
- [ ] Index.json includes keyword fields in modules/functions
- [ ] User can Ctrl-C and resume later (graceful interruption)

#### Test Case 2.2: CLI Skip Keywords (Speed Mode)
```bash
# User wants fast indexing only
cicada index --no-keywords

# Expected result:
# - Basic AST parsing only
# - No model downloads
# - No keyword extraction
# - Config remains: keywords.method = null
# - Total time: < 10 seconds
```

**Verification Checklist:**
- [ ] `--no-keywords` flag works correctly
- [ ] No NLP processing triggered
- [ ] Config stays at `keywords: { method: null, model: null }`
- [ ] Completes in <10 seconds

#### Test Case 2.3: Incremental Keyword Updates
```bash
# User modifies 5 files and re-indexes
cicada index

# Expected result:
# - Detects only 5 files changed (via MD5 hash)
# - Only processes those 5 files
# - Total time: ~2-5 seconds (not 2-5 minutes)
```

**Verification Checklist:**
- [ ] MD5 hash comparison works correctly
- [ ] Only changed files re-processed
- [ ] Incremental run is 10-25x faster than full run
- [ ] Progress shows: "5/200 files need keyword update"

#### Test Case 2.4: MCP Server Enables Keyword Search
```bash
# User restarts MCP client after CLI indexing with keywords

# Expected result:
# - Server detects keywords available
# - Enables search_by_keywords tool
# - Tool works with semantic search
```

**Verification Checklist:**
- [ ] `self._has_keywords` returns True
- [ ] `search_by_keywords` tool works
- [ ] Returns relevant semantic matches
- [ ] BM25 ranking provides good results

---

### Requirement 3: MCP Server Auto-Setup (Editor Integration)

**Objective:** When MCP server starts and no `.cicada/` structure exists, automatically initialize with basic indexing (NO keywords) for instant startup.

#### Test Case 3.1: MCP Server First Run (No Setup)
```bash
# User adds MCP server to .mcp.json or editor config
# User opens editor (Claude Code, Cursor, VSCode, etc.)
# User invokes first MCP tool: "Show me the User module"

# Expected behavior:
# - MCP server detects no .cicada/ directory
# - Auto-creates .cicada/ structure
# - Runs basic indexing (NO keywords)
# - Creates config.yaml with keywords.method = null
# - Returns result to user
# - Total time: <15 seconds for first tool call
```

**Verification Checklist:**
- [ ] MCP server detects missing `.cicada/` directory on startup
- [ ] Auto-initialization triggered on first tool invocation
- [ ] Basic indexing runs without user intervention
- [ ] NO keyword extraction (fast startup)
- [ ] Config created: `keywords: { method: null, model: null }`
- [ ] Index.json created with basic AST data
- [ ] First tool call succeeds after auto-setup
- [ ] Subsequent tool calls are instant

#### Test Case 3.2: MCP Server with Existing Setup
```bash
# User already ran `cicada` CLI to set up project
# User opens editor with MCP server configured
# MCP server starts

# Expected behavior:
# - MCP server detects existing .cicada/ directory
# - Loads config.yaml
# - Loads index.json
# - Detects keyword availability from config
# - Starts normally (no auto-indexing)
```

**Verification Checklist:**
- [ ] MCP server detects existing setup correctly
- [ ] No re-indexing triggered
- [ ] Keywords enabled/disabled based on config
- [ ] Server starts in <2 seconds

#### Test Case 3.3: MCP Auto-Setup Progress Feedback
```bash
# During first MCP tool call with auto-setup

# Expected progress messages (via MCP protocol):
# 1. "Setting up Cicada index..."
# 2. "Scanning Elixir files..."
# 3. "Parsing 47/200 files (23%)..."
# 4. "Index created successfully"
# 5. [Returns tool result]
```

**Verification Checklist:**
- [ ] Progress messages sent via MCP protocol
- [ ] User can see indexing is happening
- [ ] Clear indication of progress (not frozen)
- [ ] Final success message before result

---

### Requirement 4: Mode Tracking in Config

**Objective:** config.yaml accurately tracks indexing state so MCP server knows what features are available.

#### Test Case 4.1: Fresh Install (No Keywords)
```yaml
# .cicada/config.yaml after MCP auto-setup or cicada index --no-keywords
version: 0.2.0

repository:
  path: /path/to/project

storage:
  index_path: .cicada/index.json

keywords:
  method: null
  model: null
```

**Verification Checklist:**
- [ ] Config created with null values
- [ ] MCP server reads null correctly
- [ ] Features disabled gracefully

#### Test Case 4.2: After CLI Default Indexing (spaCy)
```yaml
# .cicada/config.yaml after cicada index (default behavior)
version: 0.2.0

repository:
  path: /path/to/project

storage:
  index_path: .cicada/index.json

keywords:
  method: spacy
  model: fast
```

**Verification Checklist:**
- [ ] Config updated with correct values
- [ ] MCP server detects keywords available
- [ ] Features enabled automatically

#### Test Case 4.3: After BERT/KeyBERT Indexing
```yaml
# .cicada/config.yaml after cicada index --rag --regular
version: 0.2.0

repository:
  path: /path/to/project

storage:
  index_path: .cicada/index.json

keywords:
  method: bert
  model: regular
```

**Verification Checklist:**
- [ ] Config tracks BERT method correctly
- [ ] Model tier (regular) recorded
- [ ] Future runs use same settings unless overridden

---

## Performance Benchmarks

### Basic Indexing (No Keywords)
| Repository Size | Time Target | Measured |
|----------------|-------------|----------|
| Small (50 files) | < 3 seconds | [ ] |
| Medium (200 files) | < 10 seconds | [ ] |
| Large (1000 files) | < 30 seconds | [ ] |

### Keyword Extraction (First Time)
| Method | Model Tier | Repository Size | Time Target | Measured |
|--------|------------|----------------|-------------|----------|
| spaCy | fast | 200 files | < 60 seconds | [ ] |
| spaCy | regular | 200 files | < 90 seconds | [ ] |
| spaCy | max | 200 files | < 180 seconds | [ ] |
| KeyBERT | fast | 200 files | < 120 seconds | [ ] |
| KeyBERT | regular | 200 files | < 180 seconds | [ ] |
| KeyBERT | max | 200 files | < 420 seconds | [ ] |

### Incremental Updates (After Changes)
| Files Changed | Time Target | Measured |
|---------------|-------------|----------|
| 1 file | < 1 second | [ ] |
| 5 files | < 3 seconds | [ ] |
| 20 files | < 10 seconds | [ ] |

---

## User Experience Verification

### Scenario 1: Editor Integration (MCP Auto-Setup)
1. User installs: `uv tool install git+https://github.com/wende/cicada.git@v0.2.0`
2. User adds MCP server to editor config (`.mcp.json`)
3. User opens editor (Claude Code, Cursor, etc.)
4. User asks: "Show me the User module" (first MCP call)

**Expected Result:**
- [ ] MCP server auto-initializes on first tool call
- [ ] Basic indexing completes in <15 seconds
- [ ] Module search returns results immediately
- [ ] No keyword search available yet (clear error if tried)
- [ ] Subsequent queries are instant

### Scenario 2: CLI Power User (Full Setup)
1. User installs: `uv tool install git+https://github.com/wende/cicada.git@v0.2.0`
2. User runs: `cicada /path/to/elixir/project` (or `cicada index`)
3. Waits 2-5 minutes with progress feedback (first time)
4. Opens editor and uses MCP tools

**Expected Result:**
- [ ] Full indexing with keywords completes
- [ ] Progress feedback during keyword extraction
- [ ] All tools work including semantic search
- [ ] MCP server detects keywords on startup
- [ ] No additional setup needed in editor

### Scenario 3: User Wants Semantic Search (After Auto-Setup)
1. User started with MCP auto-setup (no keywords)
2. User tries keyword search tool
3. Gets helpful error message
4. Runs: `cicada index` (CLI default includes keywords)
5. Waits 2-5 minutes with progress feedback
6. Keyword search now works (no restart needed)

**Expected Result:**
- [ ] Error message was clear and actionable
- [ ] Progress feedback during indexing
- [ ] Can see it's working (not frozen)
- [ ] Semantic search quality is good
- [ ] MCP server picks up keywords automatically

### Scenario 4: Developer Workflow (Incremental)
1. User makes changes to 3 files
2. Runs: `cicada index`
3. Continues working immediately

**Expected Result:**
- [ ] Incremental update was fast (<5s)
- [ ] Only changed files re-processed
- [ ] Keywords updated for changed files only
- [ ] No noticeable workflow interruption

---

## Implementation Checklist

### Code Changes Required

#### MCP Server Auto-Setup (Priority 1)
- [ ] `mcp_server.py`: Detect missing `.cicada/` directory on initialization
- [ ] `mcp_server.py`: Add auto-setup method that creates `.cicada/` structure
- [ ] `mcp_server.py`: Trigger auto-setup on first tool invocation if needed
- [ ] `mcp_server.py`: Run basic indexing only (NO keywords) during auto-setup
- [ ] `mcp_server.py`: Create config.yaml with `keywords: { method: null, model: null }`
- [ ] `mcp_server.py`: Send progress messages during auto-setup via MCP protocol
- [ ] `mcp_server.py`: Gracefully handle missing keywords in existing code
- [ ] `mcp_server.py`: Return helpful error for `search_by_keywords` when disabled

#### CLI Indexing Behavior (Priority 2)
- [ ] `cli.py`: Keep `cicada index` default behavior (WITH keywords)
- [ ] `cli.py`: Add `--no-keywords` flag for fast indexing
- [ ] `indexer.py`: Respect `--no-keywords` flag (skip NLP processing)
- [ ] `indexer.py`: Keep existing keyword flags (--nlp, --rag, --fast, --max, --regular)
- [ ] `install.py`: Minimal changes (CLI is for power users, keep full features)

#### Config Management (Priority 3)
- [ ] Config creation with `keywords: { method: null, model: null }` for basic mode
- [ ] Config updates with method/model when keywords enabled
- [ ] Config version tracking (ensure `version: 0.2.0` in config.yaml)
- [ ] MCP server reads config to determine keyword availability

### Documentation Updates
- [ ] README.md: Document MCP auto-setup behavior
- [ ] README.md: Clarify CLI vs MCP default behavior
- [ ] README.md: Explain `cicada index` includes keywords, `--no-keywords` to skip
- [ ] README.md: Add performance expectations (<15s first MCP call)
- [ ] CLAUDE.md: Update with new workflow
- [ ] extensions/: Update all platform docs with auto-setup behavior
- [ ] Add troubleshooting guide for common issues

### Testing Protocol
- [ ] **MCP Auto-Setup**: Test on 3 different Elixir projects
  - [ ] Add to `.mcp.json` only (no CLI setup)
  - [ ] First tool call triggers auto-setup
  - [ ] Verify <15 second completion
  - [ ] All basic tools work
- [ ] **CLI Indexing**: Test keyword extraction
  - [ ] `cicada index` includes keywords (default)
  - [ ] `cicada index --no-keywords` skips keywords (fast)
  - [ ] Progress feedback works
- [ ] **Incremental Updates**: Test with both modes
  - [ ] With keywords: only changed files re-extracted
  - [ ] Without keywords: fast AST re-parse
- [ ] **Performance**: Measure actual vs target times

---

## Success Criteria

This objective is met when:

1. ✅ **MCP Server Auto-Setup**: First tool call completes in <15 seconds (basic indexing only, no keywords)
2. ✅ **CLI Default Behavior**: `cicada index` includes keywords by default (power user workflow)
3. ✅ **CLI Fast Mode**: `cicada index --no-keywords` completes in <10 seconds
4. ✅ **All non-keyword tools work immediately** after basic indexing (auto-setup or --no-keywords)
5. ✅ **Config accurately tracks keyword availability** (null when disabled, method/model when enabled)
6. ✅ **MCP server starts successfully** with or without keywords (no crashes)
7. ✅ **Keyword tool shows helpful error** when disabled (clear instructions to enable)
8. ✅ **Incremental updates are fast** (<5s for typical changes, with or without keywords)
9. ✅ **User experience is smooth** for both CLI and MCP workflows
10. ✅ **No manual setup required** for MCP integration (auto-initializes on first use)

---

**Status:** 🔴 Not Started
**Target Completion:** Week 1 of extension rollout
**Priority:** Critical (blocks MVP extension deployment)
