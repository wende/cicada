# MCP Tool Call Benchmarking

This document describes the automated benchmarking system for measuring cicada MCP tool call frequency when using Claude Code.

## Overview

The benchmark script (`tests/benchmark/benchmark_mcp_tool_calls.py`) automates testing of how frequently Claude Code invokes cicada MCP tools when processing various prompts. This is useful for:

- Understanding tool usage patterns
- Optimizing tool descriptions for better adoption
- Measuring the impact of prompt engineering on tool usage
- Tracking improvements in AI agent behavior over time

## How It Works

The benchmark script:

1. **Displays Tool Descriptions** - Shows all cicada MCP server tool descriptions at the start
2. **Runs Claude Code in Headless Mode** - Uses the `-p` flag with Haiku model for fast, non-thinking execution
3. **Parses JSON Output** - Extracts tool call events from streaming JSON output
4. **Counts Tool Calls** - Tracks which cicada tools were invoked and how often
5. **Generates Statistics** - Provides aggregate statistics across multiple test runs

## Requirements

- **Claude Code** installed and accessible in PATH (`claude` command)
- **Cicada MCP server** configured in `.mcp.json` in the test repository
- **Python 3.10+** with access to the cicada package
- **uv package manager** (optional but recommended)

## Installation

```bash
# Ensure cicada is installed
uv tool install git+https://github.com/wende/cicada.git

# Install development dependencies
uv sync

# Or using pip
pip install -e ".[dev]"
```

## Usage

### Basic Usage

List available test suites:

```bash
python tests/benchmark/benchmark_mcp_tool_calls.py --list-suites
```

This will display all available test suites with their descriptions and test counts.

### Custom Single Test

Test a specific prompt:

```bash
python tests/benchmark/benchmark_mcp_tool_calls.py --prompt "Show me where the load_index function is called"
```

### Full Test Suite

Run multiple predefined test cases:

```bash
# Run built-in default test suite
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite

# Run all test suites from JSON file
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite --load-tests tests/benchmark/benchmark_test_prompts.json
```

### List Available Test Suites

See all available test suites:

```bash
python tests/benchmark/benchmark_mcp_tool_calls.py --list-suites --load-tests tests/benchmark/benchmark_test_prompts.json
```

Output:
```
Available test suites:
  basic_searches: Basic module and function searches (3 tests)
  usage_analysis: Function and module usage tracking (3 tests)
  git_attribution: Git history and PR attribution queries (4 tests)
  complex_multi_tool: Complex queries requiring multiple tool invocations (4 tests)
  semantic_search: Keyword-based semantic searches (3 tests)
  code_quality: Code quality and analysis queries (3 tests)
  realistic_scenarios: Real-world development scenarios (5 tests)
  stress_tests: High complexity queries to stress test tool usage (3 tests)
```

### Run Specific Test Suite

Run a specific test suite from the JSON file:

```bash
# Run only git attribution tests
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite git_attribution

# Run realistic scenarios
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite realistic_scenarios --load-tests tests/benchmark/benchmark_test_prompts.json
```

### Custom Repository Path

Test against a different repository:

```bash
python tests/benchmark/benchmark_mcp_tool_calls.py --repo-path /path/to/elixir/project --test-suite
```

## Output Format

The script produces detailed output including:

### 1. Tool Descriptions Section

```
================================================================================
CICADA MCP SERVER TOOL DESCRIPTIONS
================================================================================

Tool: search_module
Description: PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers...
--------------------------------------------------------------------------------

Tool: search_function
Description: PREFERRED for Elixir: Find function definitions and call sites across the codebase...
--------------------------------------------------------------------------------
```

### 2. Individual Test Results

```
================================================================================
TEST: Simple Module Search
================================================================================

Running: claude -p "What functions are available..." --model...
Prompt: What functions are available in the Cicada.Formatter module?...

Duration: 8.42s
Total MCP Tool Calls: 3
Tool Call Breakdown:
  - search_module: 2
  - search_function: 1
```

### 3. Summary Statistics

```
================================================================================
BENCHMARK SUMMARY
================================================================================

Total Tests: 5
Total Time: 42.15s
Average Time per Test: 8.43s
Total MCP Tool Calls: 18
Average Tool Calls per Test: 3.60

Tool Usage Across All Tests:
  - search_module: 7 (38.9%)
  - search_function: 5 (27.8%)
  - get_commit_history: 3 (16.7%)
  - find_pr_for_line: 2 (11.1%)
  - search_module_usage: 1 (5.6%)

Individual Test Results:
1. Simple Module Search: 3 calls in 8.42s
2. Function Usage Search: 4 calls in 9.12s
3. Complex Multi-Tool Query: 6 calls in 11.23s
4. Git Attribution Query: 2 calls in 6.88s
5. Code Analysis: 3 calls in 6.50s
```

## Claude Code Configuration

The script uses these Claude Code options:

- **`-p` (prompt flag)**: Enables headless/non-interactive mode
- **`--model claude-haiku-4-5-20251001`**: Uses Haiku 4.5 for fast execution
- **`--output-format stream-json`**: Outputs streaming JSON for parsing
- **No thinking keywords**: Omits "think" keywords to minimize thinking budget

### Command Example

```bash
claude -p "Show me the search_module function" \
  --model claude-haiku-4-5-20251001 \
  --output-format stream-json
```

## Tool Call Detection

The script detects MCP tool calls through multiple methods:

### 1. JSON Event Parsing

Parses streaming JSON events for tool invocation records:

```json
{
  "type": "tool_use",
  "name": "search_module",
  "input": {...}
}
```

### 2. Content Block Parsing

Extracts tool calls from content blocks:

```json
{
  "content": [
    {
      "type": "tool_use",
      "name": "search_function",
      ...
    }
  ]
}
```

### 3. Text Pattern Matching (Fallback)

Searches raw output for tool name mentions as a fallback when JSON parsing is incomplete.

## Customizing Test Cases

### Method 1: JSON File (Recommended)

Edit `tests/benchmark/benchmark_test_prompts.json` to add or modify test cases:

```json
{
  "test_suites": {
    "my_custom_suite": {
      "description": "My custom test suite",
      "tests": [
        {
          "name": "My Custom Test",
          "prompt": "Your test prompt here",
          "expected_tools": ["search_module"]
        }
      ]
    }
  }
}
```

Then run:
```bash
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite my_custom_suite
```

### Method 2: Edit Python Script

Edit `benchmark_mcp_tool_calls.py` to modify the built-in test cases:

```python
test_cases = [
    {
        "name": "My Custom Test",
        "prompt": "Your test prompt here",
    },
    # Add more test cases...
]
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: MCP Tool Usage Benchmark

on:
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install cicada
        run: uv tool install git+https://github.com/wende/cicada.git

      - name: Setup test environment
        run: |
          cd test_fixture_repo
          cicada

      - name: Run benchmark
        run: |
          cd test_fixture_repo
          python ../tests/benchmark_mcp_tool_calls.py --test-suite

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: results.json
```

## Interpreting Results

### High Tool Call Count (Good)

When Claude Code makes many cicada tool calls, it indicates:
- Tool descriptions are effective
- AI is choosing specialized tools over generic searches
- Better code understanding with less token usage

### Low Tool Call Count (Needs Investigation)

Low tool usage might indicate:
- Tool descriptions need improvement
- Prompt doesn't align with tool capabilities
- AI is using alternative approaches (grep, file reads, etc.)

### Optimal Tool Usage Patterns

Look for:
- **Progressive refinement**: Starting with broad searches (search_module) then narrowing (search_function)
- **Context gathering**: Using git tools (find_pr_for_line, get_commit_history) for historical context
- **Dependency analysis**: Using search_module_usage before refactoring

## Troubleshooting

### "claude command not found"

Install Claude Code:
```bash
# Visit https://docs.claude.com/en/docs/claude-code
npm install -g @anthropics/claude-code
```

### "No tool calls detected"

This could mean:
- JSON parsing needs adjustment for new output format
- Claude Code isn't using MCP tools (check .mcp.json configuration)
- The prompt doesn't trigger tool usage

Enable debug logging:
```bash
claude -p "your prompt" --mcp-debug --output-format stream-json
```

### "Index file not found"

Ensure cicada is set up in the test repository:
```bash
cd your_test_repo
cicada
```

## Future Enhancements

Potential improvements:
- **Token usage tracking**: Measure input/output tokens per tool call
- **Latency analysis**: Track tool invocation latency
- **Success rate monitoring**: Detect failed tool calls
- **Comparison mode**: Compare different AI models (Haiku vs Sonnet)
- **Regression detection**: Alert on significant changes in tool usage patterns
- **Export formats**: JSON, CSV, HTML report generation

## Related Documentation

- [MCP Tools Reference](MCP-Tools-Reference.md)
- [Claude Code Headless Mode](https://docs.claude.com/en/docs/claude-code/headless)
- [Model Context Protocol](https://modelcontextprotocol.io)

## License

MIT License - See LICENSE file for details
