import sys

from cicada.commands import get_argument_parser, handle_command


def main():
    """Main entry point for cicada-mcp command."""
    known_subcommands = [
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

    # Handle --version/-v before parsing arguments
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        if first_arg in ("--version", "-v"):
            from cicada.version_check import get_version_string

            print(f"cicada-mcp {get_version_string()}")
            sys.exit(0)

    server_path = None
    if (
        len(sys.argv) > 1
        and sys.argv[1] not in known_subcommands
        and not sys.argv[1].startswith("-")
    ):
        server_path = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]

    parser = get_argument_parser()
    parser.prog = "cicada-mcp"
    args = parser.parse_args()
    args._server_path = server_path

    if not handle_command(args):
        handle_default_server(args)


def handle_default_server(args):
    """
    Handle default behavior when called with no subcommand.
    Starts MCP server silently.
    """
    import asyncio
    import os
    from pathlib import Path

    # Determine repository path
    repo_path = None
    if hasattr(args, "_server_path") and args._server_path:
        repo_path = Path(args._server_path).resolve()
        os.environ["CICADA_REPO_PATH"] = str(repo_path)
    else:
        repo_path = Path.cwd().resolve()

    # Check if watch mode is requested
    watch_enabled = hasattr(args, "watch") and args.watch

    # Start watch process if requested
    if watch_enabled:
        from cicada.commands import DEFAULT_WATCH_DEBOUNCE, determine_tier
        from cicada.watch_manager import start_watch_process

        # Determine tier from args or existing config (pass repo_path instead of config_path)
        tier = determine_tier(args, repo_path)

        # Start the watch process
        if not start_watch_process(repo_path, tier=tier, debounce=DEFAULT_WATCH_DEBOUNCE):
            print("Warning: Failed to start watch process", file=sys.stderr)

    from cicada.mcp.server import async_main

    try:
        asyncio.run(async_main())
    finally:
        # Ensure watch process is stopped when server exits
        if watch_enabled:
            from cicada.watch_manager import stop_watch_process

            stop_watch_process()


if __name__ == "__main__":
    main()
