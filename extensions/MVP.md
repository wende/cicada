# MVP Extension Strategy: Basic Indexing Only

## Executive Summary

**Goal:** Launch Cicada on major MCP platforms with minimal complexity, fastest time-to-value, and lowest support burden.

**Strategy:** Ship basic indexing only (no keyword extraction) to provide instant setup and immediate value while deferring complex NLP features to post-MVP.

---

## Why No Keywords in MVP?

### Technical Reasons
1. **Instant Setup**: Basic indexing: <10s vs Keyword extraction: 2-5min
2. **No Dependencies**: Zero model downloads in MVP
3. **Simpler Debugging**: Fewer moving parts = fewer support issues
4. **Faster Iterations**: Can update basic features quickly

### UX Reasons
1. **Better First Impression**: Users get value immediately
2. **Lower Abandonment**: No 5-minute wait during first run
3. **Progressive Enhancement**: Can add keywords later without breaking anything
4. **Clearer Value Prop**: Core features work out-of-box

### Business Reasons
1. **Faster Time to Market**: Launch in days not weeks
2. **Lower Support Burden**: Simpler system = fewer bugs
3. **Validate Demand**: See if people want basic features first
4. **Easier Marketing**: "Works in 10 seconds" is compelling

---

## MVP Feature Set

### ✅ Included Features (Basic Indexing)

#### Core Search Capabilities
- **Module Search** (`search_module`)
  - Find any Elixir module by name with wildcards (`MyApp.*`) and OR patterns (`MyApp.User|MyApp.Post`)
  - View complete API: functions, docs, typespecs, line numbers
  - Filter private functions
  - JSON or Markdown output

- **Function Search** (`search_function`)
  - Find function definitions across all modules with wildcards (`create*`) and OR patterns (`create*|update*`)
  - Supports arity filtering (e.g., `create_user/2`)
  - Module-scoped search (e.g., `MyApp.User.create_user`)
  - View function signatures, docs, typespecs

- **Call Site Analysis** (`search_function` with usage)
  - Find all places a function is called
  - See calling module, function, line number
  - Filter to test files only
  - Include code examples with context

- **Module Usage** (`search_module_usage`)
  - Find all modules that alias/import/require target
  - Show function calls with line numbers
  - Track value mentions
  - Impact analysis for refactoring

#### Git Integration
- **PR Attribution** (`find_pr_for_line`)
  - Discover which PR introduced a line of code
  - See PR title, author, description, review comments
  - Link directly to GitHub PR

- **Commit History** (`get_commit_history`)
  - File-level history
  - Function-level tracking (with .gitattributes)
  - Line-range history
  - Evolution metadata (created, last modified, frequency)

- **Git Blame** (`get_blame`)
  - Line-by-line authorship
  - Grouped by author and commit
  - Show code context

- **PR History** (`get_file_pr_history`)
  - All PRs that modified a file
  - PR descriptions and review comments
  - Filter comments by file

#### Code Quality
- **Dead Code Detection** (`find_dead_code`)
  - Find unused public functions
  - Confidence levels (high/medium/low)
  - Accounts for callbacks, behaviors, dynamic calls

### ❌ Excluded Features (Post-MVP)

- **Keyword Search** (`search_by_keywords`)
  - Requires NLP model download
  - Adds 2-5 min to first run
  - Move to v0.3 or user opt-in

---

## MVP User Flows

### Flow 1: New User Installation

**User Goal:** Try Cicada for the first time

```bash
# Step 1: Install
uv tool install git+https://github.com/wende/cicada.git@latest

# Step 2: Setup project
cicada /path/to/elixir/project
# Output: "Indexing... done in 8 seconds"

# Step 3: Restart MCP client
# (Claude Code, Cline, Cursor, etc.)

# Step 4: Use immediately
# Ask Claude: "Show me the User module"
# Ask Claude: "Where is create_user/2 called?"
```

**Time to Value:** <2 minutes
**Complexity:** Zero config needed
**Risk:** Minimal (no model downloads, simple AST parsing)

### Flow 2: Exploring Codebase

**User Goal:** Understand how code works

```bash
# Example questions that work in MVP:

"Show me all functions in MyApp.Accounts.User"
→ search_module returns complete API

"Where is authenticate/2 called?"
→ search_function shows all call sites

"Who wrote this line of code?" (line 142)
→ find_pr_for_line shows PR and author

"What PRs modified this file?"
→ get_file_pr_history shows full PR context
```

**Success Criteria:**
- User can navigate large codebase confidently
- Find function definitions quickly
- Understand code authorship
- See usage patterns

### Flow 3: Refactoring Support

**User Goal:** Safely rename or move a module

```bash
# Example workflow:

1. "Show me where MyApp.Auth is used"
   → search_module_usage shows all dependents

2. "Show me all calls to Auth.verify_token/1"
   → search_function shows call sites with line numbers

3. Make changes

4. Verify no broken references
```

**Success Criteria:**
- User knows exactly what will break
- Can see all affected files
- Confident to make changes

---

## MVP Testing Matrix

### Installation Testing

| Scenario | Command | Expected Time | Pass/Fail |
|----------|---------|---------------|-----------|
| Fresh install | `cicada /path` | <10 seconds | [ ] |
| Large repo (1000 files) | `cicada /path` | <30 seconds | [ ] |
| MCP server start | Auto-start | <2 seconds | [ ] |
| Second index (no changes) | `cicada index` | <5 seconds | [ ] |

### Feature Testing

| Feature | Test Case | Expected Result | Pass/Fail |
|---------|-----------|-----------------|-----------|
| Module search | Search existing module | Returns full API | [ ] |
| Module search | Search non-existent | Returns helpful error | [ ] |
| Function search | Find function by name | Shows definition + calls | [ ] |
| Function search | With arity | Filters by arity | [ ] |
| Call sites | Request usage examples | Shows code context | [ ] |
| Module usage | Check dependencies | Shows all imports/calls | [ ] |
| PR attribution | Find PR for line | Returns PR info | [ ] |
| Git history | File history | Shows commits | [ ] |
| Git blame | Blame code section | Shows authorship | [ ] |
| Dead code | Analyze unused code | Returns candidates | [ ] |

### Error Handling

| Scenario | Expected Behavior | Pass/Fail |
|----------|-------------------|-----------|
| No .cicada/ folder | MCP server shows clear error | [ ] |
| Corrupted index | Suggests re-indexing | [ ] |
| Not a git repo | Git features disabled gracefully | [ ] |
| File doesn't exist | Clear error message | [ ] |
| Invalid module name | Helpful suggestions | [ ] |

### Platform Compatibility

| Platform | Installation Method | Works? | Notes |
|----------|---------------------|--------|-------|
| Claude Code | .mcp.json | [ ] | |
| Cursor | .mcp.json | [ ] | |
| Cline (VSCode) | settings.json | [ ] | |
| Windsurf | .mcp.json | [ ] | |

---

## MVP Distribution Timeline

### Week 1: Foundation (Nov 4-8)
**Goal:** Basic indexing working, code changes complete

- [ ] Implement basic-only indexing mode
- [ ] Update install.py to skip keywords by default
- [ ] Update mcp_server.py to handle missing keywords
- [ ] Write clear error messages
- [ ] Test on 3 different repos
- [ ] Verify OBJECTIVE.md criteria met

**Deliverables:**
- Working basic indexing (<10s)
- MCP server works without keywords
- Error messages helpful

### Week 2: Quick Wins (Nov 11-15)
**Goal:** Live on Cursor Directory and documented

#### Monday-Tuesday: Cursor Directory
- [ ] Create submission at cursor.directory/mcp/new
- [ ] Fill out form:
  - Name: "Cicada"
  - Description: "Elixir codebase intelligence for AI assistants"
  - Category: "Developer Tools"
  - Install command: `uv tool install git+https://github.com/wende/cicada.git@latest`
  - Setup: `cicada .`
  - GitHub: https://github.com/wende/cicada
- [ ] Upload logo (if ready)
- [ ] Submit and wait for approval

**Estimated Reach:** 250,000+ developers

#### Wednesday-Thursday: Claude Code Documentation
- [ ] Write clear installation guide
- [ ] Create example .mcp.json
- [ ] Record demo video or GIFs
- [ ] Update main README.md

#### Friday: Community Outreach
- [ ] Post to r/elixir
- [ ] Tweet announcement
- [ ] Elixir Forum post
- [ ] Elixir Slack channels

### Week 3: Central Registry (Nov 18-22)
**Goal:** Published to PyPI and MCP Registry

#### Monday-Tuesday: PyPI Setup
- [ ] Create PyPI account
- [ ] Set up GitHub Actions for publishing
- [ ] Test with test.pypi.org
- [ ] Publish cicada v0.2.0 to PyPI
- [ ] Verify: `pip install cicada` works

#### Wednesday-Thursday: MCP Registry
- [ ] Clone modelcontextprotocol/registry
- [ ] Build mcp-publisher CLI
- [ ] Create server.json metadata
- [ ] Authenticate via GitHub OAuth
- [ ] Publish to registry
- [ ] Verify listing appears

#### Friday: Update Listings
- [ ] Update Cursor Directory with PyPI install
- [ ] Update all documentation
- [ ] Test installation from PyPI

**Estimated Reach:** All MCP-compatible editors

### Week 4: Monitoring & Iteration (Nov 25-29)
**Goal:** Gather feedback, fix issues

- [ ] Monitor GitHub issues
- [ ] Respond to community feedback
- [ ] Fix any critical bugs
- [ ] Collect feature requests
- [ ] Plan v0.3 roadmap

---

## MVP Success Metrics

### Quantitative Metrics
- **Installation Time**: <10 seconds (avg)
- **First Query Time**: <30 seconds from install
- **Success Rate**: >95% successful installs
- **Active Users**: >100 users in first month
- **GitHub Stars**: >50 stars

### Qualitative Metrics
- **User Feedback**: Positive reviews on Cursor Directory
- **Issue Quality**: Bugs vs feature requests ratio
- **Community Engagement**: Active discussions
- **Word of Mouth**: Organic sharing

### Technical Metrics
- **Uptime**: 99.9% MCP server success rate
- **Error Rate**: <1% of tool calls fail
- **Performance**: All queries <2s response time
- **Compatibility**: Works on all major MCP clients

---

## Risk Assessment

### High Risk (Must Address)
1. **Installation Failures**
   - Mitigation: Comprehensive testing on fresh systems
   - Mitigation: Clear error messages with solutions

2. **MCP Server Crashes**
   - Mitigation: Graceful error handling
   - Mitigation: Fallback modes for missing features

3. **Poor Documentation**
   - Mitigation: Write clear, step-by-step guides
   - Mitigation: Include troubleshooting section

### Medium Risk (Monitor)
1. **Platform Incompatibility**
   - Mitigation: Test on all major MCP clients
   - Mitigation: Document known limitations

2. **Performance Issues**
   - Mitigation: Benchmark on large repos
   - Mitigation: Add progress indicators

3. **User Confusion**
   - Mitigation: Clear messaging about MVP scope
   - Mitigation: Explain keyword features as "coming soon"

### Low Risk (Accept)
1. **Limited Feature Set**
   - Acceptance: MVP is intentionally minimal
   - Plan: Add keywords in v0.3

2. **Smaller Reach**
   - Acceptance: No VSCode/Zed extensions yet
   - Plan: Native extensions in future

---

## Post-MVP Roadmap

### v0.3: Enhanced Features (Month 2)
- [ ] Add opt-in keyword extraction
- [ ] Improve progress reporting
- [ ] Add ETA to indexing
- [ ] Partial index updates
- [ ] Configuration UI

### v0.4: Native Extensions (Month 3-4)
- [ ] VSCode marketplace extension
- [ ] Zed extension
- [ ] Native progress indicators
- [ ] Setup wizards
- [ ] Auto-update support

### v0.5: Advanced Features (Month 5+)
- [ ] Cross-repo search
- [ ] Semantic code search (embeddings)
- [ ] AI-powered refactoring suggestions
- [ ] Integration with test frameworks

---

## Go/No-Go Checklist

Before launching MVP, all items must be ✅:

### Core Functionality
- [ ] Basic indexing completes in <10 seconds
- [ ] All MVP tools work without keywords
- [ ] MCP server starts reliably
- [ ] Error messages are helpful
- [ ] Documentation is clear

### Quality Assurance
- [ ] Tested on 3+ different Elixir projects
- [ ] Works on macOS, Linux, Windows (WSL)
- [ ] No crashes during normal operation
- [ ] Performance meets targets (see OBJECTIVE.md)

### Distribution Ready
- [ ] README.md updated
- [ ] CHANGELOG.md current
- [ ] License file present (MIT)
- [ ] GitHub repository clean
- [ ] No hardcoded paths or credentials

### Platform Requirements
- [ ] Works with Claude Code
- [ ] Works with Cursor
- [ ] Works with Cline (VSCode)
- [ ] .mcp.json format documented

### Support Infrastructure
- [ ] GitHub Issues enabled
- [ ] Contributing guide
- [ ] Code of conduct
- [ ] Issue templates

---

## Success Criteria

MVP is successful when:

1. ✅ **>100 users** adopt Cicada in first month
2. ✅ **>90% success rate** on fresh installations
3. ✅ **Positive community feedback** (>80% positive reviews)
4. ✅ **Active usage** (>50% of users make >10 queries)
5. ✅ **Low support burden** (<5 issues per week)
6. ✅ **Fast queries** (<2s avg response time)
7. ✅ **Clear path forward** for v0.3 features

If these criteria are met, proceed with:
- Native VSCode extension
- Zed extension
- Keyword extraction opt-in
- Advanced semantic features

---

**Status:** 📋 Planning Complete
**Next Action:** Implement OBJECTIVE.md requirements
**Owner:** @wende
**Target Launch:** Week of Nov 11, 2024
