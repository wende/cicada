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

    if hasattr(args, "_server_path") and args._server_path:
        repo_path = Path(args._server_path).resolve()
        os.environ["CICADA_REPO_PATH"] = str(repo_path)

    from cicada.mcp.server import async_main

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
