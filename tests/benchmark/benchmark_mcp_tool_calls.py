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
    python tests/benchmark/benchmark_mcp_tool_calls.py --list-suites
    python tests/benchmark/benchmark_mcp_tool_calls.py --prompt "Custom prompt"
    python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite
    python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite basic_searches
    python tests/benchmark/benchmark_mcp_tool_calls.py --load-tests tests/benchmark/benchmark_test_prompts.json
"""

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


class MCPToolCallBenchmark:
    """Benchmark suite for measuring cicada MCP tool call frequency."""

    def __init__(self, repo_path: Path = Path("."), debug: bool = False):
        self.repo_path = repo_path
        self.debug = debug
        self.results: List[Dict[str, Any]] = []
        self.results_lock = threading.Lock()

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
            print(f"Error: Unable to import cicada tools: {e}", file=sys.stderr)
            print(
                "Make sure the cicada package is installed correctly.", file=sys.stderr
            )
            sys.exit(1)

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

        try:
            # Run from repo_path so cicada MCP server finds its config there
            abs_repo_path = (
                self.repo_path.resolve()
                if isinstance(self.repo_path, Path)
                else Path(self.repo_path).resolve()
            )

            result = subprocess.run(
                cmd,
                cwd=abs_repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                print(f"Error running Claude Code: {result.stderr}", file=sys.stderr)
                return result.stdout, {}

            json_data = self._parse_json_output(result.stdout)

            return result.stdout, json_data

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
        parse_errors = 0
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError as e:
                parse_errors += 1
                if self.debug:
                    line_preview = line[:100] + "..." if len(line) > 100 else line
                    print(f"Debug: JSON parse error: {e}", file=sys.stderr)
                    print(f"Debug: Failed line: {line_preview}", file=sys.stderr)

        if self.debug and parse_errors > 0:
            print(f"Debug: Total JSON parse errors: {parse_errors}", file=sys.stderr)

        return {"events": events}

    def count_mcp_tool_calls(
        self, output: str, json_data: Dict[str, Any]
    ) -> Tuple[Dict[str, int], int]:
        """
        Count cicada MCP tool calls from Claude Code output.

        Args:
            output: Raw output string
            json_data: Parsed JSON data

        Returns:
            Tuple of (cicada_tool_calls dict, total_tool_calls count)
        """
        cicada_calls = defaultdict(int)
        total_calls = 0

        # Parse JSON events for tool calls
        events = json_data.get("events", [])

        # Show first few events for debugging
        for event in events:
            # Look for tool invocation events
            if isinstance(event, dict):
                # Check for tool_call events at top level
                if event.get("type") == "tool_use":
                    tool_name = event.get("name")
                    total_calls += 1
                    if tool_name and "cicada" in tool_name.lower():
                        cicada_calls[tool_name] += 1
                        print(f"✓ Cicada tool: {tool_name}")

                # Check for assistant messages with embedded tool calls
                if event.get("type") == "assistant":
                    message = event.get("message", {})
                    if isinstance(message, dict):
                        content = message.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if (
                                    isinstance(item, dict)
                                    and item.get("type") == "tool_use"
                                ):
                                    tool_name = item.get("name")
                                    total_calls += 1
                                    if tool_name and "cicada" in tool_name.lower():
                                        cicada_calls[tool_name] += 1

                # Check for function_calls in content at top level
                content = event.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_name = item.get("name")
                            total_calls += 1
                            if tool_name and "cicada" in tool_name.lower():
                                cicada_calls[tool_name] += 1

        cicada_total = sum(cicada_calls.values())
        print(f"Total tool calls: {total_calls}, Cicada: {cicada_total}")
        return dict(cicada_calls), total_calls

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
        print(f"TEST: {test_name}")
        print("-" * 40)
        print()

        start_time = time.time()
        output, json_data = self.run_claude_headless(prompt)
        elapsed_time = time.time() - start_time

        cicada_tool_calls, total_tool_calls = self.count_mcp_tool_calls(
            output, json_data
        )
        cicada_calls = sum(cicada_tool_calls.values())
        cicada_percentage = (
            (cicada_calls / total_tool_calls * 100) if total_tool_calls > 0 else 0
        )

        result = {
            "test_name": test_name,
            "prompt": prompt,
            "elapsed_time": elapsed_time,
            "cicada_tool_calls": cicada_tool_calls,
            "cicada_calls": cicada_calls,
            "total_tool_calls": total_tool_calls,
            "cicada_percentage": cicada_percentage,
            "output_length": len(output),
        }

        with self.results_lock:
            self.results.append(result)

        # Print results
        print(f"Duration: {elapsed_time:.2f}s")
        print(f"Total Tool Calls: {total_tool_calls}")
        print(f"Cicada Tool Calls: {cicada_calls} ({cicada_percentage:.1f}%)")
        print(f"Cicada Tool Breakdown:")
        for tool, count in sorted(cicada_tool_calls.items()):
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
        self,
        suite_name: str | None = None,
        json_path: Path | None = None,
        max_workers: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Run a complete test suite with multiple prompts.

        Args:
            suite_name: Optional name of specific suite to run
            json_path: Optional path to JSON file with test cases
            max_workers: Number of parallel workers (default: 1, sequential)

        Returns:
            List of test results
        """
        print("\n" + "=" * 80)
        print("STARTING TEST SUITE")
        if suite_name:
            print(f"Suite: {suite_name}")
        if max_workers > 1:
            print(f"Parallel execution: {max_workers} workers")
        print("=" * 80)
        print()

        # Load test cases
        if not json_path or not json_path.exists():
            print(
                "Error: Test file not found. Please provide a test file with --load-tests.",
                file=sys.stderr,
            )
            print("Use --list-suites to see available test suites.", file=sys.stderr)
            return []

        test_cases = self.load_test_cases_from_json(json_path, suite_name)

        if not test_cases:
            print("No test cases to run.", file=sys.stderr)
            return []

        if max_workers == 1:
            # Sequential execution
            for test_case in test_cases:
                self.run_single_test(test_case["prompt"], test_case["name"])
        else:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tests
                future_to_test = {
                    executor.submit(
                        self.run_single_test, test_case["prompt"], test_case["name"]
                    ): test_case
                    for test_case in test_cases
                }

                # Process results as they complete
                for future in as_completed(future_to_test):
                    test_case = future_to_test[future]
                    try:
                        future.result()
                    except Exception as e:
                        print(
                            f"Test '{test_case['name']}' failed with error: {e}",
                            file=sys.stderr,
                        )

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
        total_tool_calls = sum(r["total_tool_calls"] for r in self.results)
        total_cicada_calls = sum(r["cicada_calls"] for r in self.results)
        overall_cicada_percentage = (
            (total_cicada_calls / total_tool_calls * 100) if total_tool_calls > 0 else 0
        )

        # Aggregate cicada tool call statistics
        all_cicada_calls = defaultdict(int)
        for result in self.results:
            for tool, count in result["cicada_tool_calls"].items():
                all_cicada_calls[tool] += count

        print(f"Total Tests: {total_tests}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average Time per Test: {total_time / total_tests:.2f}s")
        print(f"Total Tool Calls: {total_tool_calls}")
        print(
            f"Cicada Tool Calls: {total_cicada_calls} ({overall_cicada_percentage:.1f}%)"
        )
        print(f"Average Cicada Calls per Test: {total_cicada_calls / total_tests:.2f}")
        print()

        print("Cicada Tool Usage Across All Tests:")
        for tool, count in sorted(
            all_cicada_calls.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                (count / total_cicada_calls * 100) if total_cicada_calls > 0 else 0
            )
            print(f"  - {tool}: {count} ({percentage:.1f}%)")
        print()

        print("Individual Test Results:")
        for i, result in enumerate(self.results, 1):
            print(
                f"{i}. {result['test_name']}: {result['cicada_calls']}/{result['total_tool_calls']} cicada calls ({result['cicada_percentage']:.1f}%) in {result['elapsed_time']:.2f}s"
            )
        print()


def main():
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark cicada MCP tool calls in Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available test suites
  python tests/benchmark/benchmark_mcp_tool_calls.py --list-suites

  # Run single custom prompt
  python tests/benchmark/benchmark_mcp_tool_calls.py --prompt "Show me the indexer module"

  # Run full test suite
  python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite

  # Run specific test suite
  python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite basic_searches

  # Run all tests from JSON file
  python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite --load-tests tests/benchmark/benchmark_test_prompts.json

  # Run tests in parallel with 4 workers
  python tests/benchmark/benchmark_mcp_tool_calls.py --test-suite --parallel 4
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
        help="Path to JSON file with test cases (default: tests/benchmark/benchmark_test_prompts.json)",
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (shows JSON parsing errors)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        metavar="N",
        help="Run N tests in parallel (default: 1, sequential)",
    )

    args = parser.parse_args()

    # Validate repo path
    if not args.repo_path.exists():
        print(
            f"Error: Repository path does not exist: {args.repo_path}", file=sys.stderr
        )
        sys.exit(1)
    if not args.repo_path.is_dir():
        print(
            f"Error: Repository path is not a directory: {args.repo_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Default test file path
    if args.load_tests is None and (args.test_suite is not None or args.list_suites):
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

    benchmark = MCPToolCallBenchmark(repo_path=args.repo_path, debug=args.debug)

    # Show tool descriptions first
    benchmark.get_cicada_tool_descriptions()

    # Run tests
    if args.test_suite is not None:
        suite_name = args.test_suite if args.test_suite != "__all__" else None
        benchmark.run_test_suite(suite_name, args.load_tests, max_workers=args.parallel)
    elif args.prompt:
        benchmark.run_single_test(args.prompt, "Custom Test")
    else:
        print(
            "Error: No test specified. Use --prompt or --test-suite.", file=sys.stderr
        )
        print("Run with --help to see usage examples.", file=sys.stderr)
        sys.exit(1)

    # Print summary
    benchmark.print_summary()


if __name__ == "__main__":
    main()
