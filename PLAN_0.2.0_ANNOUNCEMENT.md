# CICADA 0.2.0 Release Announcement Plan

## Executive Summary

This document outlines the strategy for announcing CICADA version 0.2.0, based on best practices from major frameworks (React, Vue, Django, NumPy) and open-source release guidelines.

**Target Release Date:** TBD (Recommended: Tuesday-Thursday, avoid holidays)

---

## Table of Contents

1. [Key Principles](#key-principles)
2. [Announcement Strategy](#announcement-strategy)
3. [README Updates](#readme-updates)
4. [Release Notes Structure](#release-notes-structure)
5. [Migration Guide](#migration-guide)
6. [Communication Channels](#communication-channels)
7. [Timeline & Checklist](#timeline--checklist)

---

## Key Principles

### What Makes a Great Version Announcement

Based on research of successful framework releases:

1. **Clarity First** - Users should immediately understand what's new and why it matters
2. **Visual Prominence** - Use badges and formatting to highlight key information
3. **Migration Support** - Provide clear upgrade paths and breaking change documentation
4. **Benefits-Focused** - Emphasize user benefits over technical details
5. **Accessibility** - Make information easy to find and consume at multiple levels of detail

### Version 0.2.0 Positioning

- **Evolution, not Revolution** - This is an enhancement release, not a rewrite
- **Backward Compatibility Focus** - Highlight what stays the same
- **Performance & UX** - Emphasize improvements users will notice immediately
- **Foundation for Future** - Position as groundwork for more ambitious features

---

## Announcement Strategy

### Highlight Areas for 0.2.0

Based on current roadmap, potential highlights include:

#### 1. **Incremental Re-indexing** ⚡
**User Benefit:** "Update only changed files - 10x faster re-indexing after code changes"
- Before/after timing comparison
- Automatic detection of file changes
- Smart caching strategies

#### 2. **Enhanced Keyword Search** 🔍
**User Benefit:** "Find code by concepts, not just names - with BM25 ranking"
- More relevant search results
- Better handling of natural language queries
- Example queries that work better

#### 3. **RAG with KeyBERT** (If Included) 🤖
**User Benefit:** "Semantic code understanding powered by modern NLP"
- Find conceptually similar functions
- Natural language code queries
- Context-aware suggestions

#### 4. **Performance Improvements** 📈
- Faster index loading
- Reduced memory footprint
- Optimized query execution
- Benchmark comparisons

#### 5. **Developer Experience** 💎
- Better error messages
- Improved CLI feedback
- Enhanced debugging tools
- Configuration validation

### What to Avoid

- ❌ Don't promise features not yet implemented
- ❌ Don't downplay 0.1.x - it's the foundation
- ❌ Don't create FOMO - focus on practical benefits
- ❌ Don't use jargon without explanation

---

## README Updates

### 1. Badge Section (Top of README)

**Current badges to keep:**
```markdown
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/wende/cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/wende/cicada)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Elixir](https://img.shields.io/badge/Elixir-Support-purple.svg)](https://elixir-lang.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
```

**Consider adding (optional):**
```markdown
[![Downloads](https://img.shields.io/pypi/dm/cicada-mcp)](https://pypi.org/project/cicada-mcp/)
[![GitHub Stars](https://img.shields.io/github/stars/wende/cicada?style=social)](https://github.com/wende/cicada)
```

### 2. Version Announcement Banner (Temporary)

Add directly after header, remove after 2-4 weeks:

```markdown
---

> **🎉 CICADA 0.2.0 is here!** Featuring incremental re-indexing, enhanced search, and major performance improvements.
> [See what's new](#whats-new-in-020) • [Upgrade guide](#upgrading-to-020) • [Full changelog](CHANGELOG.md)

---
```

### 3. Updated "What's New" Section

Replace or augment current roadmap section:

```markdown
## What's New in 0.2.0

### 🚀 Major Features

#### Incremental Re-indexing
No more waiting for full re-indexing! CICADA now tracks file changes and updates only what's changed.

```bash
# Before: 45 seconds for full re-index
cicada-index .

# After: 3 seconds for incremental update
cicada-index .  # Automatically detects and indexes only changed files
```

#### Enhanced Keyword Search
Improved search relevance with BM25 ranking algorithm. Find code by concepts, not just exact names.

```
# Now understands semantic relationships
"user authentication" → finds login, auth, verify_user, etc.
```

### ⚡ Performance Improvements

- **10x faster** re-indexing for projects with <10% file changes
- **40% smaller** index files with optimized storage format
- **2x faster** search queries with improved caching

### 💎 Developer Experience

- Better error messages with actionable suggestions
- Progress bars for long-running operations
- Configuration validation on setup
- Improved CLI help and documentation

[Full changelog](CHANGELOG.md) • [Migration guide](docs/MIGRATION_0.2.0.md)
```

### 4. Update Installation Section

Add version-specific instructions:

```markdown
## Installation

### Latest Stable (0.2.0)

```bash
# Recommended: using uv
uv tool install git+https://github.com/wende/cicada.git@v0.2.0

# Or using pip
pip install git+https://github.com/wende/cicada.git@v0.2.0
```

### Previous Stable (0.1.1)

If you need the previous version:

```bash
uv tool install git+https://github.com/wende/cicada.git@v0.1.1
```

**Note:** Version 0.2.0 includes breaking changes. See [migration guide](docs/MIGRATION_0.2.0.md).
```

### 5. Update Quick Start Section

Ensure examples reflect 0.2.0 features:

```markdown
## Quick Start

After installation, try these enhanced queries:

```
# Classic function search (still works!)
"Show me where authenticate/2 is called"

# NEW: Concept-based search (0.2.0+)
"Find all user validation logic"
"Show authentication-related functions"

# NEW: Performance insights (0.2.0+)
"What functions are called most frequently?"
```

**New in 0.2.0:** Incremental updates happen automatically:
```bash
# Make changes to your code
vim lib/my_module.ex

# Re-index (only updates changed files)
cicada-index .  # ⚡ Much faster!
```
```

---

## Release Notes Structure

Create `CHANGELOG.md` or `docs/releases/v0.2.0.md`:

### Template

```markdown
# CICADA 0.2.0 Release Notes

**Release Date:** [DATE]

CICADA 0.2.0 is a significant enhancement release focusing on performance, usability, and search intelligence. This release builds on the solid foundation of 0.1.x while introducing powerful new features for code understanding.

---

## Highlights

- ⚡ **10x faster re-indexing** with incremental updates
- 🔍 **Enhanced search** with BM25 ranking and concept matching
- 📊 **40% smaller index files** with optimized storage
- 💎 **Improved developer experience** with better error messages and CLI feedback
- 🐛 **[X] bug fixes** and stability improvements

---

## What's New

### Incremental Re-indexing

CICADA now intelligently tracks file changes and updates only what's necessary.

**Benefits:**
- Update indexes in seconds instead of minutes
- Automatic change detection
- Efficient caching strategy
- Smart dependency tracking

**Example:**
```bash
# Modify a file
echo "def new_function, do: :ok" >> lib/my_module.ex

# Re-index (only processes changed files)
cicada-index .  # ⚡ 3 seconds instead of 45!
```

**Implementation:** Uses file modification times and content hashing to detect changes. See [technical docs](docs/INCREMENTAL_INDEXING.md) for details.

### Enhanced Keyword Search

Search results are now ranked by relevance using the BM25 algorithm.

**Benefits:**
- More relevant results first
- Better handling of common vs. rare terms
- Concept-based matching
- Wildcard pattern support

**Examples:**
```
# Before: literal matches only
"user" → only functions with "user" in name

# After: semantic understanding
"user" → user, authenticate, profile, account, etc.
```

**Configuration:**
```json
{
  "search": {
    "algorithm": "bm25",  // or "keyword" for classic
    "boost_factor": 1.5
  }
}
```

### Performance Improvements

| Operation | v0.1.1 | v0.2.0 | Improvement |
|-----------|--------|--------|-------------|
| Initial indexing | 45s | 42s | 7% faster |
| Re-indexing (10% changes) | 45s | 4s | **10x faster** |
| Search query | 120ms | 60ms | 2x faster |
| Index file size | 5.2MB | 3.1MB | 40% smaller |

*Benchmark: Phoenix project with 450 modules, 3,500 functions*

### Developer Experience

**Better Error Messages:**
```bash
# Before
Error: Index failed

# After
Error: Failed to parse lib/my_module.ex:line 42
  Syntax error: unexpected token 'end'
  
  Suggestion: Check for unmatched 'do' block on line 38
  Run with --verbose for full error details
```

**Progress Indicators:**
```bash
$ cicada-index .
📊 Scanning files... 450 found
🔍 Parsing Elixir files... ████████████████░░░░ 80% (360/450)
💾 Building index... done
✅ Index created: .cicada/index.json (3.1 MB)
```

**Configuration Validation:**
```bash
$ cicada setup
✅ Found Elixir project
✅ Git repository detected
⚠️  Warning: Large project (>1000 files) - consider excluding test directories
✅ Configuration saved to .mcp.json
```

---

## Breaking Changes

### Index Format Change

**Impact:** Indexes created with v0.1.x cannot be read by v0.2.0

**Migration:** Re-index your project after upgrading
```bash
# Backup old index (optional)
mv .cicada/index.json .cicada/index.json.v0.1.1.bak

# Create new index
cicada-index .
```

**Why:** New format enables incremental updates and better compression

### Configuration Changes

**Removed:**
- `--extract-keywords` flag now always enabled
- Deprecated `CICADA_LEGACY_MODE` environment variable

**Changed:**
- `cicada-index --output` now relative to project root (was absolute path)

**Migration:**
```bash
# Old (v0.1.1)
cicada-index --output /absolute/path/index.json

# New (v0.2.0)
cd /project/root
cicada-index --output .cicada/index.json
```

### API Changes (if applicable)

For users of CICADA as a library:

- `IndexBuilder.build()` now returns `IndexResult` instead of `bool`
- `SearchEngine.search()` added `ranking_algorithm` parameter
- Deprecated `LegacyParser` class removed

---

## Upgrade Guide

### Prerequisites

- Python 3.10+ (unchanged)
- Elixir 1.12+ (unchanged)
- 50MB additional disk space for new dependencies

### Step 1: Backup (Optional)

```bash
# Save your current index
cp .cicada/index.json .cicada/index.json.backup
```

### Step 2: Upgrade CICADA

```bash
# Using uv (recommended)
uv tool upgrade cicada

# Or install specific version
uv tool install git+https://github.com/wende/cicada.git@v0.2.0

# Verify installation
cicada --version  # Should show: cicada 0.2.0
```

### Step 3: Re-index Your Project

```bash
cd /path/to/your/project

# Clean old index
rm -rf .cicada/

# Create new index
cicada setup  # Re-run setup
cicada-index .
```

### Step 4: Update MCP Configuration (if needed)

```bash
# Regenerate .mcp.json with new defaults
cicada setup --force
```

### Step 5: Test

```bash
# Verify MCP server works
cicada-server --test

# Try a search
cicada-find-dead-code  # Should work with new index
```

### Rollback (if needed)

```bash
# Uninstall v0.2.0
uv tool uninstall cicada

# Reinstall v0.1.1
uv tool install git+https://github.com/wende/cicada.git@v0.1.1

# Restore backup index
cp .cicada/index.json.backup .cicada/index.json
```

---

## Known Issues

### Python 3.12 on macOS ARM

**Issue:** Slower indexing on Apple Silicon with Python 3.12  
**Status:** Investigating  
**Workaround:** Use Python 3.11 or 3.10  
**Tracking:** [Issue #XXX](https://github.com/wende/cicada/issues/XXX)

### Large Monorepos (>5000 files)

**Issue:** Initial indexing may timeout  
**Status:** Will be addressed in 0.2.1  
**Workaround:** Use `--timeout 600` flag  
**Tracking:** [Issue #XXX](https://github.com/wende/cicada/issues/XXX)

---

## Deprecation Notices

### Planned for v0.3.0

- `--legacy-format` flag will be removed
- `CICADA_OLD_SEARCH` environment variable will be removed
- Python 3.10 support will be dropped (3.11+ only)

### Planned for v1.0.0

- Configuration file format will change from JSON to TOML
- MCP protocol v1 compatibility will be dropped

---

## Contributors

This release includes contributions from:

- @username1 - Incremental indexing implementation
- @username2 - BM25 search algorithm
- @username3 - Performance optimizations
- @username4 - Documentation improvements

Thank you to all [X contributors](https://github.com/wende/cicada/graphs/contributors) who made this release possible!

---

## Acknowledgments

- BM25 implementation inspired by [Elasticsearch](https://www.elastic.co/)
- Incremental indexing design influenced by [rust-analyzer](https://rust-analyzer.github.io/)
- Progress bars powered by [rich](https://github.com/Textualize/rich)

---

## Next Steps

### For Users

1. [Upgrade to 0.2.0](#upgrade-guide)
2. Try the new [enhanced search](#enhanced-keyword-search)
3. Experience [faster re-indexing](#incremental-re-indexing)
4. Share feedback on [GitHub Discussions](https://github.com/wende/cicada/discussions)

### For Contributors

1. Check out the [v0.3.0 roadmap](docs/ROADMAP.md)
2. Pick up a [good first issue](https://github.com/wende/cicada/labels/good-first-issue)
3. Join the discussion on [Discord](#) (if applicable)

---

## Resources

- [Full Changelog](CHANGELOG.md)
- [Migration Guide](docs/MIGRATION_0.2.0.md)
- [Incremental Indexing Technical Docs](docs/INCREMENTAL_INDEXING.md)
- [BM25 Search Documentation](docs/BM25_SEARCH.md)
- [Performance Benchmarks](docs/BENCHMARKS.md)

---

## Questions?

- 💬 [GitHub Discussions](https://github.com/wende/cicada/discussions)
- 🐛 [Report a Bug](https://github.com/wende/cicada/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/wende/cicada/issues/new?template=feature_request.md)

---

**[⬆ Back to Top](#cicada-020-release-notes)**
```

---

## Migration Guide

Create separate `docs/MIGRATION_0.2.0.md`:

### Template

```markdown
# Migration Guide: v0.1.x → v0.2.0

This guide helps you migrate from CICADA 0.1.x to 0.2.0.

## Overview

**Estimated migration time:** 5-10 minutes  
**Difficulty:** Easy  
**Breaking changes:** Yes (index format)  
**Rollback available:** Yes

---

## Pre-Migration Checklist

- [ ] Read [release notes](../releases/v0.2.0.md)
- [ ] Backup current `.cicada/` directory (optional)
- [ ] Note your current project setup
- [ ] Ensure Python 3.10+ is installed
- [ ] Have 15 minutes for re-indexing (first time)

---

## Migration Steps

### 1. Install v0.2.0

[Detailed steps with commands]

### 2. Handle Breaking Changes

[Specific instructions for each breaking change]

### 3. Re-index Project

[Step-by-step indexing instructions]

### 4. Verify Installation

[Testing commands and expected outputs]

---

## Troubleshooting

### Issue: "Index format not recognized"

**Cause:** Trying to use 0.1.x index with 0.2.0  
**Solution:**
```bash
rm -rf .cicada/
cicada-index .
```

### Issue: "Command not found: cicada-index"

**Cause:** Tool not in PATH after upgrade  
**Solution:**
```bash
uv tool uninstall cicada
uv tool install git+https://github.com/wende/cicada.git@v0.2.0
```

[More troubleshooting scenarios]

---

## Common Migration Patterns

### Phoenix Projects
[Specific guidance]

### Umbrella Projects
[Specific guidance]

### Large Monorepos
[Specific guidance]

---

## Getting Help

Stuck? We're here to help:

1. Check [troubleshooting](#troubleshooting) above
2. Search [existing issues](https://github.com/wende/cicada/issues)
3. Ask in [GitHub Discussions](https://github.com/wende/cicada/discussions)
4. Open a [new issue](https://github.com/wende/cicada/issues/new)
```

---

## Communication Channels

### 1. GitHub Release

**Priority:** High  
**Timing:** Day of release

Create GitHub release with:
- Release notes (condensed version)
- Download links
- Breaking changes highlighted
- Assets: none needed (git install)

**Template:**
```markdown
# CICADA 0.2.0 - Enhanced Search & Performance

Major enhancement release featuring:
- ⚡ 10x faster incremental re-indexing
- 🔍 Enhanced search with BM25 ranking
- 📊 40% smaller index files
- 💎 Improved developer experience

[Full release notes](link) | [Migration guide](link)

## Breaking Changes
- Index format changed - requires re-indexing
- Configuration changes - see migration guide

## Install
```bash
uv tool install git+https://github.com/wende/cicada.git@v0.2.0
```

## Upgrading from 0.1.x
See [migration guide](link) for step-by-step instructions.
```

### 2. README.md Banner

**Priority:** High  
**Timing:** Day of release  
**Duration:** 2-4 weeks

Add prominent banner at top (see [README Updates](#readme-updates))

### 3. Discussion Post

**Priority:** Medium  
**Timing:** Day of release

Create GitHub Discussion:
- Title: "CICADA 0.2.0 Released - Share Your Experience!"
- Invite feedback
- Known issues
- Q&A

### 4. Social Media (Optional)

**Priority:** Low  
**Timing:** Day of release + day after

If applicable:
- Twitter/X announcement
- Reddit r/elixir post
- Dev.to article
- Elixir Forum announcement

**Sample Tweet:**
```
🎉 CICADA 0.2.0 is here!

⚡ 10x faster re-indexing
🔍 Enhanced semantic search
📊 40% smaller indexes

Better code intelligence for AI assistants working with Elixir projects.

Upgrade guide: [link]

#Elixir #AI #DeveloperTools
```

### 5. Documentation Site (If Exists)

**Priority:** Medium  
**Timing:** Day of release

Update:
- Version selector
- "What's New" page
- API documentation
- Examples

### 6. Email Newsletter (If Exists)

**Priority:** Low  
**Timing:** Week of release

For projects with mailing lists:
- Announcement email
- Highlights
- Upgrade instructions
- Links to resources

---

## Timeline & Checklist

### 3-4 Weeks Before Release

- [ ] Feature freeze
- [ ] Write release notes draft
- [ ] Write migration guide draft
- [ ] Create upgrade testing checklist
- [ ] Prepare benchmark comparisons
- [ ] Update documentation

### 2 Weeks Before Release

- [ ] Beta testing with volunteers
- [ ] Collect feedback on breaking changes
- [ ] Finalize migration guide
- [ ] Create rollback procedures
- [ ] Test installation on multiple platforms
- [ ] Review README changes

### 1 Week Before Release

- [ ] Code freeze
- [ ] Final testing
- [ ] Finalize all documentation
- [ ] Prepare GitHub release draft
- [ ] Schedule release (Tuesday-Thursday)
- [ ] Prepare social media posts
- [ ] Alert key users/stakeholders

### Release Day (Tuesday-Thursday Recommended)

**Morning:**
- [ ] Create and push git tag `v0.2.0`
- [ ] Publish GitHub release
- [ ] Update README.md with banner
- [ ] Verify installation works
  ```bash
  uv tool install git+https://github.com/wende/cicada.git@v0.2.0
  ```

**Afternoon:**
- [ ] Post to GitHub Discussions
- [ ] Update project documentation
- [ ] Post to social media (if applicable)
- [ ] Monitor for issues

**Evening:**
- [ ] Respond to initial feedback
- [ ] Update known issues section if needed
- [ ] Thank early adopters

### Week After Release

- [ ] Monitor issue tracker daily
- [ ] Respond to migration questions
- [ ] Update FAQ with common questions
- [ ] Plan hotfix if critical issues found
- [ ] Collect feedback for 0.2.1
- [ ] Update roadmap based on feedback

### 2 Weeks After Release

- [ ] Remove announcement banner from README
- [ ] Write retrospective (internal)
- [ ] Thank contributors publicly
- [ ] Archive release documentation
- [ ] Begin planning 0.3.0 (if applicable)

---

## Success Metrics

Track these to measure release success:

### Adoption Metrics
- GitHub stars/forks growth
- Installation count (if trackable)
- GitHub Discussions activity
- Issue report rate

### Quality Metrics
- Critical bugs reported (target: <3)
- Migration success rate (survey users)
- Rollback requests (target: <5%)
- Performance complaints (target: 0)

### Engagement Metrics
- Documentation page views
- Migration guide views
- Social media engagement
- Contributors attracted

---

## Risk Management

### High Risk: Breaking Changes

**Risk:** Users unable to migrate  
**Mitigation:**
- Clear migration guide
- Rollback instructions
- Support channels ready
- Beta testing phase

**Contingency:**
- Emergency patch release
- Extended support for 0.1.x
- Migration assistance script

### Medium Risk: Performance Regression

**Risk:** New features slower than promised  
**Mitigation:**
- Benchmark on diverse projects
- Real-world testing
- Conservative performance claims
- "Your mileage may vary" disclaimers

**Contingency:**
- Performance tuning hotfix
- Feature flags to disable
- Honest communication

### Low Risk: Documentation Gaps

**Risk:** Unclear instructions  
**Mitigation:**
- Multiple documentation reviews
- Beta tester feedback
- Examples for common scenarios
- FAQ section

**Contingency:**
- Quick documentation updates
- Video tutorials
- Live Q&A session

---

## Post-Release Analysis Template

After 2-4 weeks, conduct retrospective:

### What Went Well
- [Success stories]
- [Metrics that exceeded expectations]
- [Positive feedback highlights]

### What Could Be Improved
- [Issues encountered]
- [Documentation gaps]
- [Communication breakdowns]

### Lessons for Next Release
- [Process improvements]
- [Communication strategies]
- [Testing approaches]

### Action Items for 0.2.1/0.3.0
- [ ] [Specific improvements]
- [ ] [Documentation updates]
- [ ] [Process changes]

---

## Appendix A: Example Announcements

### GitHub Release (Short Form)

```markdown
# 🎉 CICADA 0.2.0

## Highlights
- ⚡ 10x faster incremental re-indexing
- 🔍 Enhanced search with BM25 ranking
- 📊 40% smaller index files

## Breaking Changes
Index format changed. [Migration guide](link)

## Install
```bash
uv tool install git+https://github.com/wende/cicada.git@v0.2.0
```

[Full release notes](link)
```

### Discussion Post (Long Form)

```markdown
# CICADA 0.2.0 Released! 🎉

I'm excited to announce CICADA 0.2.0 is now available!

This release focuses on performance and search quality...

[Detailed content with personal touch]

**Try it out:**
```bash
uv tool install git+https://github.com/wende/cicada.git@v0.2.0
```

**Have feedback?** Reply here or open an issue!

**Found a bug?** Please report it [here](link).

Thanks to everyone who contributed to this release! 🙏
```

---

## Appendix B: Templates

### Issue Template: "Migration Help"

```markdown
---
name: Migration Help
about: Get help migrating from 0.1.x to 0.2.0
title: "[MIGRATION] "
labels: migration, 0.2.0
---

**Current Version:** 0.1.x

**Issue:**
[Describe your migration issue]

**Steps Tried:**
1. [What you've already tried]

**Error Messages:**
```
[Paste any error messages]
```

**Environment:**
- OS: [e.g., macOS 14, Ubuntu 22.04]
- Python: [e.g., 3.11.0]
- Install method: [uv/pip/other]
```

---

## Appendix C: Communication Scripts

### For responding to migration issues:

```markdown
Thanks for reporting this! This is a known issue with [X].

**Quick fix:**
```bash
[commands]
```

**Why this happened:**
[Brief explanation]

**Permanent solution:**
We're working on [fix] for 0.2.1 (see #issue)

Let me know if this helps!
```

---

## Conclusion

This plan ensures CICADA 0.2.0 is announced professionally, provides clear migration paths, and sets up users for success. Key takeaways:

1. **Clarity** - Make breaking changes obvious
2. **Support** - Provide comprehensive migration guides
3. **Timing** - Release Tuesday-Thursday, avoid holidays
4. **Communication** - Multiple channels, consistent messaging
5. **Metrics** - Track success and iterate

**Questions about this plan?** Update this document as the release evolves.

**Ready to release?** Follow the checklist and timeline above.

---

**Document Version:** 1.0  
**Last Updated:** [DATE]  
**Maintained By:** [Team/Person]  
**Next Review:** Before 0.2.0 feature freeze