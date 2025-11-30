# PDR-22: Cicada Agent Installation Feature

## Summary

Implement `cicada agents install` command to programmatically generate and install Claude Code agents and skills for code exploration. This provides both explicit control (agents) and auto-discovery (skills) with parallel execution support.

## Status

**Status:** Proposed
**Created:** 2024-11-27
**Author:** Claude (AI Assistant)

## Context

### Problem Statement

Users of Cicada MCP tools need a way to leverage Claude Code's agent and skill system for specialized code exploration workflows. Currently, there's no automated way to:

1. Install pre-configured agents that exclusively use Cicada MCP tools
2. Enable parallel execution of different exploration tasks (code search + impact analysis)
3. Provide auto-discovery capabilities for code exploration

### Background: Claude Code Agents vs Skills

**Agents:**
- Defined as Markdown files with YAML frontmatter in `.claude/agents/`
- Invoked explicitly via Task tool
- Run in isolated context (don't pollute main conversation)
- Can run multiple agents in parallel
- Key fields: `name`, `description`, `model`, `tools`, `color`

**Skills:**
- Defined in `.claude/skills/*/SKILL.md`
- Auto-discovered by Claude based on context (model-invoked)
- Share context with main conversation
- Use `allowed-tools` field to restrict tool access
- Progressive disclosure (loaded only when relevant)

### User Requirements

Based on user research:
1. **Both agents AND skills** - provide explicit control and auto-discovery
2. **Parallel execution** - multiple specialized agents that can run concurrently
3. **Programmatic installation** - CLI command, not manual file creation

## Decision

### Architecture

Implement a hybrid approach with **3 specialized agents** and **1 auto-discovery skill**:

| Component | Purpose | Model | Use Case |
|-----------|---------|-------|----------|
| `cicada-code-explorer` | Fast code discovery | haiku | Initial exploration, finding modules/functions |
| `cicada-impact-analyzer` | Deep dependency analysis | sonnet | Pre-refactoring safety checks |
| `cicada-historian` | Git history tracking | haiku | Blame, PR context, code evolution |
| `cicada-search` (skill) | Auto-discovery | inherit | Seamless code search integration |

### CLI Command Design

```bash
cicada agents install [OPTIONS]

Options:
  --global         Install to ~/.claude/ (default)
  --local          Install to current project's .claude/
  --agents-only    Install only agents (skip skills)
  --skills-only    Install only skills (skip agents)
  -f, --force      Overwrite existing files
```

### Installation Targets

**Global (default):**
```
~/.claude/
├── agents/
│   ├── cicada-code-explorer.md
│   ├── cicada-impact-analyzer.md
│   └── cicada-historian.md
└── skills/
    └── cicada-search/
        └── SKILL.md
```

**Local (--local flag):**
```
<project>/.claude/
├── agents/
│   └── [same as above]
└── skills/
    └── [same as above]
```

## Implementation Plan

### Phase 1: Template Creation

Create agent template files with proper YAML frontmatter and detailed instructions.

**New Directory Structure:**
```
cicada/agents/templates/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── cicada-code-explorer.md
│   ├── cicada-impact-analyzer.md
│   └── cicada-historian.md
└── skills/
    ├── __init__.py
    └── cicada-search/
        └── SKILL.md
```

### Phase 2: Core Infrastructure

**File:** `cicada/agents/__init__.py`
```python
"""Agent and skill installation for Claude Code."""
```

**File:** `cicada/agents/generator.py`
```python
"""Template loading and rendering utilities."""

from importlib.resources import files
from pathlib import Path
import yaml


def load_template(template_name: str, template_type: str = "agents") -> str:
    """Load template from package resources using importlib.resources."""
    pass


def render_template(template: str, context: dict) -> str:
    """Render template with context variables (simple string substitution)."""
    # Support: {cicada_version}, {install_date}, {project_path}
    pass


def get_all_agent_templates() -> list[tuple[str, str]]:
    """Get all agent templates. Returns [(filename, content), ...]"""
    pass


def get_all_skill_templates() -> list[tuple[str, str]]:
    """Get all skill templates. Returns [(filename, content), ...]"""
    pass


def validate_template_yaml(content: str) -> bool:
    """Validate YAML frontmatter in template."""
    pass
```

**File:** `cicada/agents/installer.py`
```python
"""Installation logic for agents and skills."""

from pathlib import Path


def get_install_path(local: bool) -> Path:
    """Get installation target path."""
    # local=False: ~/.claude/
    # local=True: <cwd>/.claude/
    pass


def validate_installation_target(path: Path, local: bool) -> None:
    """Validate installation target is writable and appropriate."""
    # Check directory writable
    # For local: validate project root
    # Warn if Claude Code not configured
    pass


def install_agents(target_dir: Path, force: bool = False) -> dict:
    """Install agent templates. Returns: {installed: [], skipped: [], failed: []}"""
    pass


def install_skills(target_dir: Path, force: bool = False) -> dict:
    """Install skill templates. Returns: {installed: [], skipped: [], failed: []}"""
    pass
```

### Phase 3: CLI Integration

**File:** `cicada/commands.py`

**Changes Required:**

1. Add `"agents"` to `KNOWN_SUBCOMMANDS` tuple (line 27-45)
2. Add agents parser with install subcommand
3. Add `"agents": handle_agents` to `command_handlers` dict (line 716-734)
4. Implement handler functions

**New Handler Functions:**
```python
def handle_agents(args):
    """Route agents subcommands."""
    if args.agents_command == "install":
        handle_agents_install(args)
    else:
        print("Error: Use 'cicada agents install'", file=sys.stderr)
        sys.exit(1)


def handle_agents_install(args):
    """Handle agents install subcommand."""
    from cicada.agents.installer import (
        get_install_path,
        install_agents,
        install_skills,
        validate_installation_target,
    )

    # Validate flags
    if args.local and args.global_install:
        print("Error: Cannot use --local and --global together", file=sys.stderr)
        sys.exit(1)

    if args.agents_only and args.skills_only:
        print("Error: Cannot use --agents-only and --skills-only together", file=sys.stderr)
        sys.exit(1)

    # Determine target path
    local = args.local
    install_path = get_install_path(local)
    validate_installation_target(install_path, local)

    # Install agents and/or skills
    # Print results with checkmark/skip/error symbols
```

### Phase 4: Package Configuration

**File:** `pyproject.toml` (add after line 74)
```toml
[tool.setuptools.package-data]
cicada = [
    "agents/templates/agents/*.md",
    "agents/templates/skills/**/*.md",
]
```

**Create:** `MANIFEST.in`
```
include cicada/agents/templates/agents/*.md
include cicada/agents/templates/skills/**/*.md
```

### Phase 5: Testing

**File:** `tests/agents/test_generator.py`
- Test template loading from package resources
- Test rendering with context variables
- Test YAML validation
- Test template discovery

**File:** `tests/agents/test_installer.py`
- Test path resolution (global/local)
- Test installation with/without force
- Test permission handling
- Test file creation

**File:** `tests/test_agents_command.py`
- Test CLI argument parsing
- Test command routing
- Integration test with temp directories

**Target:** 80%+ coverage on new code

### Phase 6: Documentation

- **Update:** `README.md` - Add agents installation section
- **Create:** `agents/using-agents.md` - Usage guide for installed agents
- **Update:** `CHANGELOG.md` - Document new feature

## Agent Template Specifications

### 1. cicada-code-explorer.md

```yaml
---
name: cicada-code-explorer
description: |
  Fast code exploration and discovery. Use when you need to quickly find modules,
  functions, or understand code structure.

  Examples:
  - "find authentication code"
  - "show me the User module"
  - "search for database queries"
model: haiku
color: green
---

You are Cicada Code Explorer, optimized for fast code discovery in Elixir and Python codebases.

## Your Role

Quick code searches, module/function discovery, and pattern matching for initial exploration.

## Available Tools

- `mcp__cicada__query` - Primary search tool for keywords and patterns
- `mcp__cicada__search_module` - View module API and structure
- `mcp__cicada__search_function` - Find function definitions and call sites
- `mcp__cicada__expand_result` - Drill down into query results

## Primary Workflow

1. **Start with `query`** for broad discovery using keywords or patterns
2. **Use `search_module`** to explore specific module APIs
3. **Use `search_function`** for function details and call sites
4. **Use `expand_result`** to get complete details on interesting finds

## Best Practices

- Use keyword search for semantic discovery (e.g., "authentication", "payment")
- Use wildcards (*) for pattern matching (e.g., "MyApp.*.create*")
- Combine filters: `scope`, `recent`, `path_pattern`
- Show code snippets with `show_snippets=true` when helpful
- Filter by type: `filter_type='modules'` or `'functions'`

## When to Escalate

- Complex dependency analysis → suggest cicada-impact-analyzer
- Git history questions → suggest cicada-historian
- Impact assessment before refactoring → suggest cicada-impact-analyzer

## Response Format

Provide concise, actionable results:
- File path with line number
- Brief description of what was found
- Relevant code snippet if helpful
- Suggestions for next steps
```

### 2. cicada-impact-analyzer.md

```yaml
---
name: cicada-impact-analyzer
description: |
  Deep dependency and impact analysis for refactoring. Use BEFORE modifying code
  to understand dependencies and breaking changes.

  Examples:
  - "what depends on UserAuth module"
  - "impact of changing create_user signature"
  - "find unused functions in this module"
model: sonnet
color: blue
---

You are Cicada Impact Analyzer, expert in dependency analysis and refactoring safety.

## Your Role

Analyze code dependencies, assess refactoring risks, and identify safe modification paths.

## Available Tools

- `mcp__cicada__query` - Initial discovery
- `mcp__cicada__search_module` - Module dependencies (what_calls_it, what_it_calls)
- `mcp__cicada__search_function` - Function call sites and dependencies
- `mcp__cicada__find_dead_code` - Identify unused public functions
- `mcp__cicada__query_jq` - Advanced index queries

## Core Capabilities

### 1. What Depends On This (Downstream Impact)
```python
search_module(module_name="Target", what_calls_it=true)
search_function(function_name="target_func", what_calls_it=true)
```

### 2. What This Depends On (Upstream Dependencies)
```python
search_module(module_name="Target", what_it_calls=true)
search_function(function_name="target_func", what_it_calls=true)
```

### 3. Transitive Dependencies
```python
search_module(module_name="Target", what_it_calls=true, dependency_depth=2)
```

### 4. Dead Code Detection
```python
find_dead_code(min_confidence="high")
```

## Analysis Workflow

1. **Identify Target**: Clarify what code is being modified
2. **Analyze Upstream**: What does this code depend on?
3. **Analyze Downstream**: What code depends on this?
4. **Assess Scope**: How many files/modules affected?
5. **Evaluate Risk**: Breaking changes, test coverage gaps
6. **Recommend**: Safe refactoring steps

## Reporting Format

Structure all impact analyses as:

### Impact Analysis: [Target]

**Target**: Module/function being analyzed

**Direct Dependencies** (what it uses):
- List of direct dependencies

**Direct Dependents** (what uses it):
- List of direct dependents with file:line references

**Transitive Impact**:
- Ripple effects beyond direct dependents

**Risk Assessment**:
- **Risk Level**: Low / Medium / High
- **Breaking Changes**: Yes/No, description
- **Test Coverage**: Affected tests

**Recommendations**:
1. Specific safe refactoring steps
2. Order of changes to minimize risk
3. Tests to add/update
```

### 3. cicada-historian.md

```yaml
---
name: cicada-historian
description: |
  Git history and code evolution analysis. Use to understand when code changed,
  find PR context, or track authorship.

  Examples:
  - "when was this function added"
  - "find PR for authentication changes"
  - "who wrote the billing logic"
model: haiku
color: purple
---

You are Cicada Historian, expert in code evolution and git history analysis.

## Your Role

Track code changes, identify authorship, find PR context, and understand code evolution.

## Primary Tool

`mcp__cicada__git_history` - Unified tool for all history queries

## Query Patterns

### 1. Single Line Authorship
```python
git_history(file_path="lib/auth.ex", start_line=42)
```
Returns: blame info + associated PR

### 2. Line Range Blame
```python
git_history(file_path="lib/auth.ex", start_line=40, end_line=60)
```
Returns: blame for range with PR enrichment

### 3. Function Evolution
```python
git_history(file_path="lib/auth.ex", function_name="create_user", show_evolution=true)
```
Returns: function history with creation date, modifications, frequency

### 4. File PR History
```python
git_history(file_path="lib/auth.ex")
```
Returns: All PRs that modified this file

### 5. Recent Changes Only
```python
git_history(file_path="lib/auth.ex", recent=true)
# Or older changes:
git_history(file_path="lib/auth.ex", recent=false)
```

### 6. Author Filter
```python
git_history(file_path="lib/auth.ex", author="john")
```

## Response Format

Structure all history responses as:

### History: [Target]

**What Changed**: Summary of modifications

**When**:
- Commit: `abc123` (2024-01-15)
- PR: #456 "Add user authentication"

**Who**: Author Name <email>

**Why**: PR description or commit message

**Context**: [Link to full PR](url) if available

## Best Practices

- Start with file-level history for overview
- Drill into specific lines when investigating bugs
- Use function tracking for understanding feature evolution
- Filter by author when tracking team contributions
- Use `recent=true` to focus on recent changes
```

### 4. cicada-search.md (Skill)

```yaml
---
name: cicada-search
description: |
  Auto-discovered semantic code search. Triggers when searching for code structure,
  modules, or functions in Elixir/Python codebases. Provides intelligent search
  using Cicada's indexed knowledge.
allowed-tools: mcp__cicada__query, mcp__cicada__search_module, mcp__cicada__search_function, mcp__cicada__git_history, mcp__cicada__expand_result
---

This skill auto-activates for code exploration queries in Elixir and Python projects.

## Trigger Patterns

This skill activates when users ask:
- "where is [module/function]"
- "find [code element]"
- "search for [keyword]"
- "show me [module]"
- "what does [function] do"
- "how is [feature] implemented"

## Tool Selection Logic

| Query Type | Tool |
|------------|------|
| Keywords/concepts | `query` |
| Specific module name | `search_module` |
| Specific function | `search_function` |
| History/blame question | `git_history` |
| Drill into result | `expand_result` |

## Response Guidelines

- Provide concise, focused results
- Include file paths with line numbers
- Show relevant code snippets when helpful
- Suggest next steps for deeper exploration
- Recommend specialized agents for complex tasks:
  - Dependency analysis → cicada-impact-analyzer
  - Git history → cicada-historian
```

## Expected Output

```
$ cicada agents install

Installing Cicada agents and skills (global): /Users/user/.claude/

  ✓ Installed cicada-code-explorer.md
  ✓ Installed cicada-impact-analyzer.md
  ✓ Installed cicada-historian.md
  ✓ Installed cicada-search/SKILL.md

✓ Installation complete!

Next steps:
  1. Restart Claude Code to load new agents
  2. Use agents via: Task tool → select cicada-*
  3. Skills auto-activate when relevant

Agents installed globally - available in all projects
```

## Files to Create

| File | Purpose |
|------|---------|
| `cicada/agents/__init__.py` | Package init |
| `cicada/agents/generator.py` | Template loading/rendering |
| `cicada/agents/installer.py` | Installation logic |
| `cicada/agents/templates/agents/cicada-code-explorer.md` | Explorer agent |
| `cicada/agents/templates/agents/cicada-impact-analyzer.md` | Impact agent |
| `cicada/agents/templates/agents/cicada-historian.md` | History agent |
| `cicada/agents/templates/skills/cicada-search/SKILL.md` | Search skill |
| `tests/agents/test_generator.py` | Generator tests |
| `tests/agents/test_installer.py` | Installer tests |
| `tests/test_agents_command.py` | CLI tests |
| `MANIFEST.in` | Package data manifest |

## Files to Modify

| File | Change |
|------|--------|
| `cicada/commands.py` | Add agents command and handlers |
| `pyproject.toml` | Add package data configuration |
| `README.md` | Document agents feature |
| `CHANGELOG.md` | Add feature entry |

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Permission denied on ~/.claude/ | Error with suggestion to use --local |
| Existing modified files | Skip with message unless --force |
| --local outside project | Error if no project markers found |
| --local and --global together | Validation error |
| --agents-only and --skills-only together | Validation error |
| Missing template (package corruption) | Suggest `uv tool install --force cicada-mcp` |
| Invalid YAML in template | Warn but continue (graceful degradation) |
| Claude Code not configured | Warn (not error) - user might configure later |
| Disk full | Catch OSError, cleanup partial install |

## Alternatives Considered

### Alternative 1: Single Comprehensive Agent

One agent handling all cicada exploration tasks.

**Rejected because:**
- Cannot run different exploration types in parallel
- Large instruction set in single file
- Not optimal for specialized tasks

### Alternative 2: Skill-Only Approach

Only auto-discovery skill, no explicit agents.

**Rejected because:**
- Less explicit control for users
- Cannot run parallel explorations
- No isolated context for complex analyses

### Alternative 3: Manual Agent Creation

Document templates and let users create manually.

**Rejected because:**
- Poor user experience
- Error-prone manual process
- No standardization across users

## Success Criteria

1. `cicada agents install` successfully creates all files
2. Agents are discoverable in Claude Code after restart
3. Each agent functions correctly with cicada-mcp tools
4. Skill auto-activates for code exploration queries
5. 80%+ test coverage on new code
6. Documentation is complete and accurate

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Templates | 2h | Write all 4 template files |
| Infrastructure | 3h | Implement generator.py and installer.py |
| CLI Integration | 2h | Modify commands.py |
| Packaging | 30m | Update pyproject.toml and MANIFEST.in |
| Testing | 3h | Write comprehensive tests |
| Documentation | 1h | Update README and docs |
| **Total** | **~11.5h** | |

## References

- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents.md)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills.md)
- [Existing release-manager.md agent](.claude/agents/release-manager.md)
- [Cicada MCP Tools Documentation](agents/search-syntax.md)
