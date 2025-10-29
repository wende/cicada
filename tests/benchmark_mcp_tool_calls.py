#!/usr/bin/env python
"""
Automated benchmark script for measuring cicada MCP tool calls in Claude Code.

This script runs Claude Code in headless mode with Haiku model and tracks
the number of MCP tool calls made during various test scenarios.

Requirements:
- Claude Code installed and accessible in PATH
- Cicada MCP server configured in .mcp.json
- uv package manager (for running cicada server)

Usage:
    python tests/benchmark_mcp_tool_calls.py
    python tests/benchmark_mcp_tool_calls.py --prompt "Custom prompt"
    python tests/benchmark_mcp_tool_calls.py --test-suite
    python tests/benchmark_mcp_tool_calls.py --test-suite basic_searches
    python tests/benchmark_mcp_tool_calls.py --load-tests tests/benchmark_test_prompts.json
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import defaultdict


class MCPToolCallBenchmark:
    """Benchmark suite for measuring cicada MCP tool call frequency."""

    def __init__(self, repo_path: Path = Path(".")):
        self.repo_path = repo_path
        self.results: List[Dict[str, Any]] = []

    def get_cicada_tool_descriptions(self) -> Dict[str, str]:
        """
        Get tool descriptions from the cicada MCP server.

        Returns:
            Dict mapping tool names to their descriptions
        """
        print("=" * 80)
        print("CICADA MCP SERVER TOOL DESCRIPTIONS")
        print("=" * 80)
        print()

        # Import cicada tools to get descriptions
        try:
            from cicada.mcp_tools import get_tool_definitions

            tools = get_tool_definitions()
            tool_descriptions = {}

            for tool in tools:
                tool_descriptions[tool.name] = tool.description
                print(f"Tool: {tool.name}")
                print(f"Description: {tool.description[:200]}...")
                print("-" * 80)
                print()

            return tool_descriptions
        except ImportError as e:
            print(f"Error importing cicada tools: {e}", file=sys.stderr)
            print("Using fallback tool list...", file=sys.stderr)

            # Fallback list of known cicada tools
            fallback_tools = {
                "search_module": "PREFERRED for Elixir: View a module's complete API",
                "search_function": "PREFERRED for Elixir: Find function definitions and call sites",
                "search_module_usage": "PREFERRED for Elixir: Find all module usage and dependencies",
                "find_pr_for_line": "PREFERRED for git history: Discover why code exists",
                "get_commit_history": "PREFERRED for git history: Get commit log for files or functions",
                "get_blame": "PREFERRED for authorship: Git blame showing who wrote each line",
                "get_file_pr_history": "Get all PRs that modified a file",
                "search_by_keywords": "Semantic search for code by concept/topic",
                "find_dead_code": "Find potentially unused public functions",
            }

            for name, desc in fallback_tools.items():
                print(f"Tool: {name}")
                print(f"Description: {desc}")
                print("-" * 80)
                print()

            return fallback_tools

    def run_claude_headless(
        self,
        prompt: str,
        model: str = "claude-haiku-4-5-20251001",
        timeout: int = 120,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run Claude Code in headless mode with the specified prompt.

        Args:
            prompt: The prompt to send to Claude Code
            model: The model to use (default: haiku 4.5)
            timeout: Timeout in seconds (default: 120)

        Returns:
            Tuple of (output string, parsed JSON data)
        """
        cmd = [
            "claude",
            "-p",
            prompt,
            "--model",
            model,
            "--output-format",
            "stream-json",
        ]

        print(f"Running: {' '.join(cmd[:4])}...")
        print(f"Prompt: {prompt[:100]}...")
        print()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                print(f"Error running Claude Code: {result.stderr}", file=sys.stderr)
                return result.stdout, {}

            return result.stdout, self._parse_json_output(result.stdout)

        except subprocess.TimeoutExpired:
            print(f"Command timed out after {timeout} seconds", file=sys.stderr)
            return "", {}
        except FileNotFoundError:
            print(
                "Error: 'claude' command not found. Please install Claude Code.",
                file=sys.stderr,
            )
            sys.exit(1)

    def _parse_json_output(self, output: str) -> Dict[str, Any]:
        """
        Parse streaming JSON output from Claude Code.

        Args:
            output: Raw output string from Claude Code

        Returns:
            Dictionary containing parsed events
        """
        events = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError:
                continue

        return {"events": events}

    def count_mcp_tool_calls(
        self, output: str, json_data: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Count MCP tool calls from Claude Code output.

        Args:
            output: Raw output string
            json_data: Parsed JSON data

        Returns:
            Dictionary mapping tool names to call counts
        """
        tool_calls = defaultdict(int)

        # Parse JSON events for tool calls
        events = json_data.get("events", [])
        for event in events:
            # Look for tool invocation events
            if isinstance(event, dict):
                # Check for tool_call events
                if event.get("type") == "tool_use":
                    tool_name = event.get("name")
                    if tool_name:
                        tool_calls[tool_name] += 1

                # Check for function_calls in content
                content = event.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_name = item.get("name")
                            if tool_name:
                                tool_calls[tool_name] += 1

        # Fallback: Parse raw output for tool mentions
        # Look for patterns like "mcp__cicada__search_module" or tool invocation logs
        cicada_tools = [
            "search_module",
            "search_function",
            "search_module_usage",
            "find_pr_for_line",
            "get_commit_history",
            "get_blame",
            "get_file_pr_history",
            "search_by_keywords",
            "find_dead_code",
        ]

        for tool in cicada_tools:
            # Count mentions of tool in output
            count = output.lower().count(tool.lower())
            if count > 0:
                tool_calls[tool] = max(tool_calls[tool], count)

        return dict(tool_calls)

    def run_single_test(
        self, prompt: str, test_name: str = "Unnamed Test"
    ) -> Dict[str, Any]:
        """
        Run a single benchmark test.

        Args:
            prompt: The test prompt
            test_name: Name for this test

        Returns:
            Test result dictionary
        """
        print("\n" + "=" * 80)
        print(f"TEST: {test_name}")
        print("=" * 80)
        print()

        start_time = time.time()
        output, json_data = self.run_claude_headless(prompt)
        elapsed_time = time.time() - start_time

        tool_calls = self.count_mcp_tool_calls(output, json_data)
        total_calls = sum(tool_calls.values())

        result = {
            "test_name": test_name,
            "prompt": prompt,
            "elapsed_time": elapsed_time,
            "tool_calls": tool_calls,
            "total_calls": total_calls,
            "output_length": len(output),
        }

        self.results.append(result)

        # Print results
        print(f"Duration: {elapsed_time:.2f}s")
        print(f"Total MCP Tool Calls: {total_calls}")
        print(f"Tool Call Breakdown:")
        for tool, count in sorted(tool_calls.items()):
            print(f"  - {tool}: {count}")
        print()

        return result

    def load_test_cases_from_json(
        self, json_path: Path, suite_name: str | None = None
    ) -> List[Dict[str, str]]:
        """
        Load test cases from a JSON file.

        Args:
            json_path: Path to JSON file with test cases
            suite_name: Optional name of specific test suite to load

        Returns:
            List of test case dictionaries
        """
        try:
            with open(json_path, "r") as f:
                data = json.load(f)

            test_suites = data.get("test_suites", {})

            if suite_name:
                if suite_name not in test_suites:
                    print(
                        f"Error: Test suite '{suite_name}' not found in {json_path}",
                        file=sys.stderr,
                    )
                    print(f"Available suites: {', '.join(test_suites.keys())}")
                    return []
                suite = test_suites[suite_name]
                print(f"Loading test suite: {suite_name}")
                print(f"Description: {suite.get('description', 'N/A')}")
                print()
                return suite.get("tests", [])
            else:
                # Load all test suites
                all_tests = []
                for suite_name, suite in test_suites.items():
                    tests = suite.get("tests", [])
                    all_tests.extend(tests)
                return all_tests

        except FileNotFoundError:
            print(f"Error: Test file not found: {json_path}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            return []

    def run_test_suite(
        self, suite_name: str | None = None, json_path: Path | None = None
    ) -> List[Dict[str, Any]]:
        """
        Run a complete test suite with multiple prompts.

        Args:
            suite_name: Optional name of specific suite to run
            json_path: Optional path to JSON file with test cases

        Returns:
            List of test results
        """
        print("\n" + "=" * 80)
        print("STARTING TEST SUITE")
        if suite_name:
            print(f"Suite: {suite_name}")
        print("=" * 80)
        print()

        # Load test cases
        if json_path and json_path.exists():
            test_cases = self.load_test_cases_from_json(json_path, suite_name)
        else:
            # Default built-in test cases
            test_cases = [
                {
                    "name": "Simple Module Search",
                    "prompt": "What functions are available in the Cicada.Formatter module?",
                },
                {
                    "name": "Function Usage Search",
                    "prompt": "Show me where the load_index function is called in the codebase",
                },
                {
                    "name": "Complex Multi-Tool Query",
                    "prompt": "Find all modules that handle MCP server functionality, show their functions, and identify who created them using git history",
                },
                {
                    "name": "Git Attribution Query",
                    "prompt": "Which PR introduced the search_module function in mcp_server.py?",
                },
                {
                    "name": "Code Analysis",
                    "prompt": "Analyze the indexer.py file and tell me what it does",
                },
            ]

        if not test_cases:
            print("No test cases to run.", file=sys.stderr)
            return []

        for test_case in test_cases:
            self.run_single_test(test_case["prompt"], test_case["name"])

        return self.results

    def print_summary(self):
        """Print summary statistics for all tests."""
        if not self.results:
            print("No test results to summarize.")
            return

        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        print()

        total_tests = len(self.results)
        total_time = sum(r["elapsed_time"] for r in self.results)
        total_tool_calls = sum(r["total_calls"] for r in self.results)

        # Aggregate tool call statistics
        all_tool_calls = defaultdict(int)
        for result in self.results:
            for tool, count in result["tool_calls"].items():
                all_tool_calls[tool] += count

        print(f"Total Tests: {total_tests}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average Time per Test: {total_time / total_tests:.2f}s")
        print(f"Total MCP Tool Calls: {total_tool_calls}")
        print(
            f"Average Tool Calls per Test: {total_tool_calls / total_tests:.2f}"
        )
        print()

        print("Tool Usage Across All Tests:")
        for tool, count in sorted(
            all_tool_calls.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / total_tool_calls * 100) if total_tool_calls > 0 else 0
            print(f"  - {tool}: {count} ({percentage:.1f}%)")
        print()

        print("Individual Test Results:")
        for i, result in enumerate(self.results, 1):
            print(
                f"{i}. {result['test_name']}: {result['total_calls']} calls in {result['elapsed_time']:.2f}s"
            )
        print()


def main():
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark cicada MCP tool calls in Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default test
  python tests/benchmark_mcp_tool_calls.py

  # Run single custom prompt
  python tests/benchmark_mcp_tool_calls.py --prompt "Show me the indexer module"

  # Run built-in test suite
  python tests/benchmark_mcp_tool_calls.py --test-suite

  # Run specific test suite from JSON
  python tests/benchmark_mcp_tool_calls.py --test-suite basic_searches --load-tests tests/benchmark_test_prompts.json

  # Run all tests from JSON file
  python tests/benchmark_mcp_tool_calls.py --test-suite --load-tests tests/benchmark_test_prompts.json
        """,
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Single prompt to test",
    )
    parser.add_argument(
        "--test-suite",
        nargs="?",
        const="__all__",
        help="Run test suite. Optionally specify suite name (e.g., 'basic_searches', 'git_attribution')",
    )
    parser.add_argument(
        "--load-tests",
        type=Path,
        help="Path to JSON file with test cases (default: tests/benchmark_test_prompts.json)",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path("."),
        help="Path to repository (default: current directory)",
    )
    parser.add_argument(
        "--list-suites",
        action="store_true",
        help="List available test suites and exit",
    )

    args = parser.parse_args()

    # Default test file path
    if args.load_tests is None and args.test_suite is not None:
        default_test_path = Path(__file__).parent / "benchmark_test_prompts.json"
        if default_test_path.exists():
            args.load_tests = default_test_path

    # List suites and exit
    if args.list_suites:
        if args.load_tests and args.load_tests.exists():
            try:
                with open(args.load_tests, "r") as f:
                    data = json.load(f)
                test_suites = data.get("test_suites", {})
                print("Available test suites:")
                for name, suite in test_suites.items():
                    desc = suite.get("description", "No description")
                    test_count = len(suite.get("tests", []))
                    print(f"  {name}: {desc} ({test_count} tests)")
            except Exception as e:
                print(f"Error loading test file: {e}", file=sys.stderr)
        else:
            print("No test file specified or found.", file=sys.stderr)
        sys.exit(0)

    benchmark = MCPToolCallBenchmark(repo_path=args.repo_path)

    # Show tool descriptions first
    benchmark.get_cicada_tool_descriptions()

    # Run tests
    if args.test_suite is not None:
        suite_name = args.test_suite if args.test_suite != "__all__" else None
        benchmark.run_test_suite(suite_name, args.load_tests)
    elif args.prompt:
        benchmark.run_single_test(args.prompt, "Custom Test")
    else:
        # Default: run a simple test
        benchmark.run_single_test(
            "What modules are available in this codebase?",
            "Default Simple Test",
        )

    # Print summary
    benchmark.print_summary()


if __name__ == "__main__":
    main()
