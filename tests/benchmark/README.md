# MCP Tool Call Benchmarking

Quick guide to measuring cicada MCP tool call frequency when using Claude Code.

## Quick Start

```bash
# List available test suites
python tests/benchmark/benchmark_mcp_tool_calls.py --list-suites

# Run full test suite
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite

# Run specific test suite
python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite git_attribution

# Run custom prompt
python tests/benchmark/benchmark_mcp_tool_calls.py --prompt "Find all modules that handle indexing"
```

## Files

- **`benchmark_mcp_tool_calls.py`** - Main benchmark script
- **`benchmark_test_prompts.json`** - Test case definitions organized into suites
- **`../../docs/MCP_TOOL_CALL_BENCHMARKING.md`** - Complete documentation

## What It Does

1. Shows all cicada MCP tool descriptions
2. Runs Claude Code in headless Haiku mode (fast, non-thinking)
3. Feeds it with test prompts
4. Counts which cicada tools were called
5. Generates statistics across multiple runs

## Example Output

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
```

## Available Test Suites

- **basic_searches** - Simple module and function lookups
- **usage_analysis** - Function call sites and dependencies
- **git_attribution** - PR and commit history tracking
- **complex_multi_tool** - Multi-step queries requiring several tools
- **semantic_search** - Keyword-based searches
- **code_quality** - Dead code detection
- **realistic_scenarios** - Real-world development tasks
- **stress_tests** - High complexity queries

## Requirements

- Claude Code installed (`claude` command available)
- Cicada MCP server configured (`.mcp.json`)
- Python 3.10+

## Full Documentation

See [MCP Tool Call Benchmarking](../../codebook/RandD/202511052055-MCP_TOOL_CALL_BENCHMARKING.md) for:
- Detailed usage instructions
- Claude Code configuration options
- Tool call detection methods
- CI/CD integration examples
- Customizing test cases
- Troubleshooting guide
