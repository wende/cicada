# AI Agents Integration

Cicada provides pre-built AI agent templates optimized for code exploration and analysis. These agents integrate with Claude Code to provide specialized, task-focused assistants that leverage Cicada's MCP tools for efficient codebase navigation.

## Overview

AI agents in Cicada are specialized assistant configurations that:
- Use focused tool subsets for specific tasks
- Optimize for speed with smaller models (Haiku)
- Provide domain-specific workflows and best practices
- Integrate seamlessly with Claude Code's agent system

Agents are installed as markdown files in the `.claude/agents/` directory and become available in Claude Code's Task tool.

## Available Agents

### Cicada Code Explorer

**Purpose:** Fast code exploration and discovery for initial codebase understanding.

**Model:** Haiku (optimized for speed)

**Use When:**
- Quickly finding modules, functions, or classes
- Understanding code structure and organization
- Pattern matching across the codebase
- Initial exploration before deeper analysis

**Available Tools:**
- `mcp__cicada__query` - Primary search for keywords and patterns
- `mcp__cicada__search_module` - View module API and structure
- `mcp__cicada__search_function` - Find function definitions and call sites
- `mcp__cicada__expand_result` - Drill down into query results

**Primary Workflow:**
1. Start with `query` for broad discovery using keywords or patterns
2. Use `search_module` to explore specific module APIs
3. Use `search_function` for function details and call sites
4. Use `expand_result` to get complete details on interesting finds

**Best Practices:**
- Use keyword search for semantic discovery (e.g., "authentication", "payment")
- Use wildcards (*) for pattern matching (e.g., "MyApp.*.create*")
- Combine filters: `scope`, `recent`, `path_pattern`
- Show code snippets with `show_snippets=true` when helpful
- Filter by type: `filter_type='modules'` or `'functions'`

---

## Installation

### Command Line Installation

Install agents to the current project:

```bash
cicada agents install
```

This command:
1. Creates `.claude/agents/` directory if it doesn't exist
2. Installs the `cicada-code-explorer.md` agent
3. Makes the agent available in Claude Code immediately (after restart)

**Output:**
```
Installing Cicada agent: /path/to/project/.claude

  ✓ Installed cicada-code-explorer.md

✓ Installation complete!

Next steps:
  1. Restart Claude Code to load the new agent
  2. Use agent via: Task tool → select cicada-code-explorer
```

### Manual Installation

Agents can also be installed manually by copying template files to `.claude/agents/`:

```bash
# Create agents directory
mkdir -p .claude/agents

# Copy agent template (example)
cp /path/to/cicada-code-explorer.md .claude/agents/
```

---

## Agent Architecture

### File Structure

```
.claude/
└── agents/
    └── cicada-code-explorer.md    # Agent configuration and prompts
```

### Agent Configuration Format

Each agent is defined in a markdown file with YAML frontmatter:

```markdown
---
name: agent-name
description: What this agent does
model: haiku|sonnet|opus
color: green|blue|red|yellow
---

Agent prompt and instructions...
```

**Frontmatter Fields:**
- `name` - Agent identifier (must match filename without .md)
- `description` - Short description shown in Task tool
- `model` - Claude model to use (haiku for speed, sonnet for quality)
- `color` - Visual identifier in Claude Code UI

**Prompt Structure:**
- **Your Role** - Clear definition of agent's purpose
- **Available Tools** - List of MCP tools the agent can use
- **Primary Workflow** - Step-by-step process for common tasks
- **Best Practices** - Tips for effective tool usage
- **When to Escalate** - When to suggest other agents or approaches
- **Response Format** - How to structure outputs

---

## Usage in Claude Code

### Invoking an Agent

1. Use the Task tool in Claude Code
2. Select `cicada-code-explorer` from the agent list
3. Provide your exploration task in the prompt

**Example Tasks:**
```
"Find all modules related to authentication"
"Show me how the payment processing flow works"
"Locate all database query functions"
"Find where User.create is called"
```

### Agent Capabilities

The Code Explorer agent is optimized for:

✅ **Fast keyword-based search**
- Semantic queries: "authentication", "logging", "error handling"
- Pattern matching: "*.create*", "MyApp.User.*"
- Multiple search terms: ["payment", "transaction", "billing"]

✅ **Module discovery**
- View complete module APIs with function lists
- Understand module structure and exports
- Identify public vs private functions

✅ **Function analysis**
- Find function definitions with signatures
- Locate all call sites across the codebase
- View usage examples in context

✅ **Result expansion**
- Get detailed information about search results
- View full documentation and type specs
- See code snippets with context

### Agent Limitations

The Code Explorer agent is NOT optimized for:

❌ **Deep code analysis** - Use main Claude Code for complex logic understanding
❌ **Git history** - Suggest dedicated history tools
❌ **Code modification** - Agents are read-only for exploration
❌ **Dependency analysis** - Limited to surface-level relationship viewing

---

## Template System

### Template Loading

Templates are bundled with Cicada and loaded from package resources:

**Location:** `cicada/agents/templates/agents/`

**Implementation:** Uses Python's `importlib.resources` for reliable access

```python
from importlib.resources import files

template_path = files("cicada.agents.templates.agents") / "cicada-code-explorer.md"
content = template_path.read_text()
```

### Creating Custom Agents

While Cicada currently includes one agent, the architecture supports custom agents:

1. **Create Agent File:**
   ```bash
   touch .claude/agents/my-custom-agent.md
   ```

2. **Define Configuration:**
   ```markdown
   ---
   name: my-custom-agent
   description: Custom agent for specific workflow
   model: haiku
   color: blue
   ---

   Your agent instructions here...
   ```

3. **Specify MCP Tools:**
   List only the tools relevant to your agent's task

4. **Document Workflow:**
   Provide clear step-by-step processes

5. **Restart Claude Code:**
   Agent becomes available in Task tool

---

## Integration with Claude Code

### Agent Discovery

Claude Code automatically discovers agents in:
- `.claude/agents/` (project-specific)
- `~/.claude/agents/` (global)

Cicada installs project-specific agents by default.

### Model Selection

Agents specify their preferred model in frontmatter:
- **haiku** - Fast, efficient for exploration (recommended for Code Explorer)
- **sonnet** - Balanced speed and capability
- **opus** - Highest quality for complex analysis

### Tool Access

Agents have access to MCP tools through the same infrastructure as Claude Code:
- Tools are called via `mcp__cicada__<tool_name>` format
- All standard Cicada MCP tools are available
- Tool results are processed and formatted automatically

---

## File Reference

| File | Description |
|------|-------------|
| `cicada/agents/installer.py` | Agent installation logic |
| `cicada/agents/generator.py` | Template loading from package resources |
| `cicada/agents/__init__.py` | Module initialization |
| `cicada/agents/templates/agents/cicada-code-explorer.md` | Code Explorer agent template |
| `cicada/commands.py:1681` | CLI handler for `cicada agents install` |
| `tests/agents/test_installer.py` | Installation tests |
| `tests/agents/test_generator.py` | Template loading tests |
| `tests/agents/test_agents_command.py` | CLI command tests |

---

## Design Philosophy

### Specialization Over Generalization

Agents are designed for specific tasks rather than general-purpose assistance:
- **Focused tool sets** - Only include tools relevant to the task
- **Optimized prompts** - Task-specific instructions and examples
- **Speed optimization** - Use faster models when appropriate
- **Clear boundaries** - Know when to escalate to main assistant

### Workflow-Driven

Each agent provides a concrete workflow:
1. Clear starting point
2. Logical progression through tools
3. Actionable outputs
4. Escalation paths when needed

### Composability

Agents can suggest other agents or tools:
- Code Explorer → Impact Analyzer (for dependency analysis)
- Code Explorer → Historian (for git history)
- Specialized agents work together for complex tasks

---

## Future Expansion

The agent system is designed to support additional specialized agents:

**Potential Future Agents:**
- **cicada-impact-analyzer** - Analyze code change impact and dependencies
- **cicada-historian** - Deep git history and PR analysis
- **cicada-refactoring-assistant** - Guided refactoring workflows
- **cicada-test-navigator** - Test discovery and coverage analysis

Each agent would:
- Use a focused subset of Cicada MCP tools
- Optimize for specific workflows
- Integrate seamlessly with existing agents
