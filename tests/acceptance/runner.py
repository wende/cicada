#!/usr/bin/env python
"""
Acceptance test runner - can be used by both pytest and shell scripts.

This module provides runnable functions for each acceptance test scenario,
allowing them to be executed manually via shell scripts or automatically via pytest.
"""

import asyncio
import sys
from pathlib import Path

from cicada.mcp.server import CicadaServer
from cicada.utils.storage import get_config_path


# Get config path from centralized storage
def get_default_config():
    """Get default config path from test fixtures."""
    if Path("tests/fixtures/test_project").exists():
        fixture_dir = Path("tests/fixtures/test_project").resolve()
    elif Path("tests/fixtures/elixir_project").exists():
        fixture_dir = Path("tests/fixtures/elixir_project").resolve()
    else:
        fixture_dir = Path.cwd()
    return str(get_config_path(fixture_dir))


DEFAULT_CONFIG = get_default_config()


async def search_module(module_name: str, output_format: str = "markdown") -> str:
    """Search for a module and return formatted output."""
    server = CicadaServer(config_path=DEFAULT_CONFIG)
    result = await server.module_handler.search_module(module_name, output_format)
    return result[0].text if result else "No results found"


async def search_function(
    function_name: str,
    output_format: str = "markdown",
    include_usage_examples: bool = False,
    max_examples: int = 5,
    usage_type: str = "source",
) -> str:
    """Search for a function and return formatted output."""
    server = CicadaServer(config_path=DEFAULT_CONFIG)
    result = await server.function_handler.search_function(
        function_name,
        output_format=output_format,
        include_usage_examples=include_usage_examples,
        max_examples=max_examples,
        usage_type=usage_type,
    )
    return result[0].text if result else "No results found"


async def get_file_history(
    file_path: str,
    function_name: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    show_evolution: bool = False,
    max_commits: int = 5,
) -> str:
    """Get file or function history and return formatted output."""
    server = CicadaServer(config_path=DEFAULT_CONFIG)
    result = await server._get_file_history(
        file_path,
        function_name=function_name,
        start_line=start_line,
        end_line=end_line,
        show_evolution=show_evolution,
        max_commits=max_commits,
    )
    return result[0].text if result else "No history found"


def main():
    """Command-line interface for manual execution."""
    if len(sys.argv) < 2:
        print("Usage: python runner.py <command> [args...]", file=sys.stderr)
        print("\nCommands:", file=sys.stderr)
        print("  search_module <module_name>", file=sys.stderr)
        print(
            "  search_function <function_name> [--examples] [--tests-only] [--limit N]",
            file=sys.stderr,
        )
        print(
            "  file_history <file_path> [--function NAME] [--evolution] [--limit N]",
            file=sys.stderr,
        )
        print(
            "  file_history <file_path> --line-mode --start LINE --end LINE [--evolution]",
            file=sys.stderr,
        )
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "search_module":
            if len(sys.argv) < 3:
                print("Error: module_name required", file=sys.stderr)
                sys.exit(1)
            result = asyncio.run(search_module(sys.argv[2]))
            print(result)

        elif command == "search_function":
            if len(sys.argv) < 3:
                print("Error: function_name required", file=sys.stderr)
                sys.exit(1)

            function_name = sys.argv[2]
            include_examples = "--examples" in sys.argv or "-e" in sys.argv
            test_only = "--tests-only" in sys.argv or "-t" in sys.argv
            max_examples = 5

            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                if idx + 1 < len(sys.argv):
                    max_examples = int(sys.argv[idx + 1])

            result = asyncio.run(
                search_function(
                    function_name,
                    include_usage_examples=include_examples,
                    usage_type="test" if test_only else "source",
                    max_examples=max_examples,
                )
            )
            print(result)

        elif command == "file_history":
            if len(sys.argv) < 3:
                print("Error: file_path required", file=sys.stderr)
                sys.exit(1)

            file_path = sys.argv[2]
            function_name = None
            start_line = None
            end_line = None
            show_evolution = "--evolution" in sys.argv or "-e" in sys.argv
            max_commits = 5
            line_mode = "--line-mode" in sys.argv or "-l" in sys.argv

            # Parse arguments
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] in ["--function", "-f"] and i + 1 < len(sys.argv):
                    function_name = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--start" and i + 1 < len(sys.argv):
                    start_line = int(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] == "--end" and i + 1 < len(sys.argv):
                    end_line = int(sys.argv[i + 1])
                    i += 2
                elif sys.argv[i] in ["--limit", "-n"] and i + 1 < len(sys.argv):
                    max_commits = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            result = asyncio.run(
                get_file_history(
                    file_path,
                    function_name=function_name,
                    start_line=start_line,
                    end_line=end_line,
                    show_evolution=show_evolution,
                    max_commits=max_commits,
                )
            )
            print(result)

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
