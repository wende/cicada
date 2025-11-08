"""MCP entry point for cicada-mcp command."""

import asyncio
import os
import sys
from pathlib import Path

from cicada.commands import DEFAULT_WATCH_DEBOUNCE, get_argument_parser, handle_command

# Known subcommands that should be handled by command parser
KNOWN_SUBCOMMANDS = [
    "install",
    "server",
    "claude",
    "cursor",
    "vs",
    "index",
    "index-pr",
    "find-dead-code",
    "clean",
]


def main() -> None:
    """Main entry point for cicada-mcp command."""
    # Handle version flag early
    if _handle_version_flag():
        return

    # Parse server path if provided as positional argument
    server_path = _extract_server_path()

    # Parse arguments
    parser = get_argument_parser()
    parser.prog = "cicada-mcp"
    args = parser.parse_args()
    args._server_path = server_path

    # Handle command or start default server
    if not handle_command(args):
        _handle_default_server(args)


def _handle_version_flag() -> bool:
    """Check and handle version flag.

    Returns:
        True if version was handled, False otherwise
    """
    if len(sys.argv) <= 1 or sys.argv[1] not in ("--version", "-v"):
        return False

    from cicada.version_check import get_version_string

    print(f"cicada-mcp {get_version_string()}")
    sys.exit(0)


def _extract_server_path() -> str | None:
    """Extract server path from command line if provided.

    Returns:
        Server path if provided as positional argument, None otherwise
    """
    if len(sys.argv) <= 1:
        return None

    if sys.argv[1] in KNOWN_SUBCOMMANDS or sys.argv[1].startswith("-"):
        return None

    server_path = sys.argv[1]
    # Remove server path from argv so parser doesn't see it
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    return server_path


def _handle_default_server(args) -> None:
    """Handle default behavior when called with no subcommand.

    Starts MCP server silently.

    Args:
        args: Parsed command-line arguments
    """
    # Determine repository path
    repo_path = _determine_repo_path(args)

    # Check if watch mode is requested
    watch_enabled = hasattr(args, "watch") and args.watch

    # Start watch process if requested
    if watch_enabled:
        _start_watch_process(args, repo_path)

    # Start MCP server
    from cicada.mcp.server import async_main

    try:
        asyncio.run(async_main())
    finally:
        # Ensure watch process is stopped when server exits
        if watch_enabled:
            _cleanup_watch_process()


def _determine_repo_path(args) -> Path:
    """Determine repository path from arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Repository path
    """
    if hasattr(args, "_server_path") and args._server_path:
        repo_path = Path(args._server_path).resolve()
        os.environ["CICADA_REPO_PATH"] = str(repo_path)
        return repo_path
    return Path.cwd().resolve()


def _start_watch_process(args, repo_path: Path) -> None:
    """Start watch process for the server.

    Args:
        args: Parsed command-line arguments
        repo_path: Repository path

    Raises:
        SystemExit: If watch process fails to start
    """
    from cicada.tier import determine_tier
    from cicada.watch_manager import start_watch_process

    # Determine tier from args or existing config
    tier = determine_tier(args, repo_path)

    # Start the watch process
    try:
        if not start_watch_process(repo_path, tier=tier, debounce=DEFAULT_WATCH_DEBOUNCE):
            print("ERROR: Failed to start watch process as requested", file=sys.stderr)
            print("MCP server startup aborted.", file=sys.stderr)
            sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: Cannot start watch process: {e}", file=sys.stderr)
        print("MCP server startup aborted.", file=sys.stderr)
        sys.exit(1)


def _cleanup_watch_process() -> None:
    """Clean up watch process on server exit."""
    from cicada.watch_manager import stop_watch_process

    stop_watch_process()


if __name__ == "__main__":
    main()
