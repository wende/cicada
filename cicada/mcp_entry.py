#!/usr/bin/env python
"""
Entry point for cicada-mcp command.

Behavior:
- With no args + TTY: Interactive setup
- With no args + non-TTY: Start MCP server (for MCP clients)
- With subcommands: Route to appropriate handler (same as cicada CLI)

This provides unified command interface for both cicada and cicada-mcp.
"""

import argparse
import sys


def is_tty() -> bool:
    """
    Detect if running in a TTY (terminal) context.

    Returns:
        True if both stdin and stdout are TTYs (terminal), False otherwise
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def main():
    """Main entry point for cicada-mcp command."""
    # Known subcommands
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

    # Check if first argument is a known subcommand
    # This determines whether to include the positional path_or_command argument
    has_subcommand = len(sys.argv) > 1 and sys.argv[1] in known_subcommands

    parser = argparse.ArgumentParser(
        prog="cicada-mcp",
        description="Cicada MCP Server - AI-powered Elixir code analysis",
        epilog="Run 'cicada-mcp <command> --help' for more information on a command.",
    )

    # Only add positional argument if no subcommand is provided (for backward compatibility)
    if not has_subcommand:
        parser.add_argument(
            "path_or_command",
            nargs="?",
            default=None,
            help="Repository path (for backward compatibility) or subcommand",
        )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ========================================================================
    # INSTALL subcommand - Interactive setup
    # ========================================================================
    install_parser = subparsers.add_parser(
        "install",
        help="Interactive setup for Cicada",
        description="Interactive setup with editor and model selection",
    )
    install_parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to Elixir repository (default: current directory)",
    )
    install_parser.add_argument(
        "--claude",
        action="store_true",
        help="Skip editor selection, use Claude Code",
    )
    install_parser.add_argument(
        "--cursor",
        action="store_true",
        help="Skip editor selection, use Cursor",
    )
    install_parser.add_argument(
        "--vs",
        action="store_true",
        help="Skip editor selection, use VS Code",
    )
    install_parser.add_argument(
        "--nlp",
        action="store_true",
        help="Skip model selection, use Lemminflect",
    )
    install_parser.add_argument(
        "--rag",
        action="store_true",
        help="Skip model selection, use BERT (default tier)",
    )
    install_parser.add_argument(
        "--fast",
        action="store_true",
        help="Use BERT fast tier (requires --rag)",
    )
    install_parser.add_argument(
        "--max",
        action="store_true",
        help="Use BERT max tier (requires --rag)",
    )

    # ========================================================================
    # SERVER subcommand - Silent MCP server
    # ========================================================================
    server_parser = subparsers.add_parser(
        "server",
        help="Start MCP server (silent mode with defaults)",
        description="Start MCP server with auto-setup using defaults",
    )
    server_parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to Elixir repository (default: current directory)",
    )
    server_parser.add_argument(
        "--claude",
        action="store_true",
        help="Create Claude Code config before starting server",
    )
    server_parser.add_argument(
        "--cursor",
        action="store_true",
        help="Create Cursor config before starting server",
    )
    server_parser.add_argument(
        "--vs",
        action="store_true",
        help="Create VS Code config before starting server",
    )
    server_parser.add_argument(
        "--nlp",
        action="store_true",
        help="Force Lemminflect (if reindexing needed)",
    )
    server_parser.add_argument(
        "--rag",
        action="store_true",
        help="Force BERT (if reindexing needed)",
    )
    server_parser.add_argument(
        "--fast",
        action="store_true",
        help="Force BERT fast tier (requires --rag)",
    )
    server_parser.add_argument(
        "--max",
        action="store_true",
        help="Force BERT max tier (requires --rag)",
    )

    # ========================================================================
    # CLAUDE subcommand (editor setup)
    # ========================================================================
    claude_parser = subparsers.add_parser(
        "claude",
        help="Setup Cicada for Claude Code editor",
        description="One-command setup for Claude Code with keyword extraction",
    )
    claude_parser.add_argument(
        "--nlp",
        action="store_true",
        help="Use NLP keyword extraction (lemminflect-based)",
    )
    claude_parser.add_argument(
        "--rag",
        action="store_true",
        help="Use RAG-optimized keyword extraction (BERT-based embeddings)",
    )
    claude_parser.add_argument(
        "--fast",
        action="store_true",
        help="Use fast tier model (requires --nlp or --rag)",
    )
    claude_parser.add_argument(
        "--max",
        action="store_true",
        help="Use maximum quality tier model (requires --nlp or --rag)",
    )

    # ========================================================================
    # CURSOR subcommand (editor setup)
    # ========================================================================
    cursor_parser = subparsers.add_parser(
        "cursor",
        help="Setup Cicada for Cursor editor",
        description="One-command setup for Cursor with keyword extraction",
    )
    cursor_parser.add_argument(
        "--nlp",
        action="store_true",
        help="Use NLP keyword extraction (lemminflect-based)",
    )
    cursor_parser.add_argument(
        "--rag",
        action="store_true",
        help="Use RAG-optimized keyword extraction (BERT-based embeddings)",
    )
    cursor_parser.add_argument(
        "--fast",
        action="store_true",
        help="Use fast tier model (requires --nlp or --rag)",
    )
    cursor_parser.add_argument(
        "--max",
        action="store_true",
        help="Use maximum quality tier model (requires --nlp or --rag)",
    )

    # ========================================================================
    # VS subcommand (editor setup)
    # ========================================================================
    vs_parser = subparsers.add_parser(
        "vs",
        help="Setup Cicada for VS Code editor",
        description="One-command setup for VS Code with keyword extraction",
    )
    vs_parser.add_argument(
        "--nlp",
        action="store_true",
        help="Use NLP keyword extraction (lemminflect-based)",
    )
    vs_parser.add_argument(
        "--rag",
        action="store_true",
        help="Use RAG-optimized keyword extraction (BERT-based embeddings)",
    )
    vs_parser.add_argument(
        "--fast",
        action="store_true",
        help="Use fast tier model (requires --nlp or --rag)",
    )
    vs_parser.add_argument(
        "--max",
        action="store_true",
        help="Use maximum quality tier model (requires --nlp or --rag)",
    )

    # ========================================================================
    # INDEX subcommand
    # ========================================================================
    index_parser = subparsers.add_parser(
        "index",
        help="Index an Elixir repository to extract modules and functions",
        description="Index current Elixir repository to extract modules and functions",
    )
    index_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the Elixir repository to index (default: current directory)",
    )
    index_parser.add_argument(
        "--output",
        default=".cicada/index.json",
        help="Output path for the index file (default: .cicada/index.json)",
    )
    index_parser.add_argument(
        "--nlp",
        action="store_true",
        help="Use NLP keyword extraction (lemminflect-based)",
    )
    index_parser.add_argument(
        "--rag",
        action="store_true",
        help="Use RAG-optimized keyword extraction (BERT-based embeddings)",
    )
    index_parser.add_argument(
        "--fast",
        action="store_true",
        help="Use fast tier model (requires --nlp or --rag)",
    )
    index_parser.add_argument(
        "--max",
        action="store_true",
        help="Use maximum quality tier model (requires --nlp or --rag)",
    )

    # ========================================================================
    # INDEX-PR subcommand
    # ========================================================================
    index_pr_parser = subparsers.add_parser(
        "index-pr",
        help="Index GitHub pull requests for fast offline lookup",
        description="Index GitHub pull requests for fast offline lookup",
    )
    index_pr_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to git repository (default: current directory)",
    )
    index_pr_parser.add_argument(
        "--output",
        default=".cicada/pr_index.json",
        help="Output path for the index file (default: .cicada/pr_index.json)",
    )
    index_pr_parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean and rebuild the entire index from scratch (default: incremental update)",
    )

    # ========================================================================
    # FIND-DEAD-CODE subcommand
    # ========================================================================
    dead_code_parser = subparsers.add_parser(
        "find-dead-code",
        help="Find potentially unused public functions in Elixir codebase",
        description="Find potentially unused public functions in Elixir codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Confidence Levels:
  high   - Zero usage, no dynamic call indicators, no behaviors/uses
  medium - Zero usage, but module has behaviors or uses (possible callbacks)
  low    - Zero usage, but module passed as value (possible dynamic calls)

Examples:
  cicada-mcp find-dead-code                      # Show high confidence candidates
  cicada-mcp find-dead-code --min-confidence low # Show all candidates
  cicada-mcp find-dead-code --format json        # Output as JSON
        """,
    )
    dead_code_parser.add_argument(
        "--index",
        default=".cicada/index.json",
        help="Path to index file (default: .cicada/index.json)",
    )
    dead_code_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    dead_code_parser.add_argument(
        "--min-confidence",
        choices=["high", "medium", "low"],
        default="high",
        help="Minimum confidence level to show (default: high)",
    )

    # ========================================================================
    # CLEAN subcommand
    # ========================================================================
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove Cicada configuration and indexes",
        description="Remove Cicada configuration and indexes for current repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cicada-mcp clean                   # Clean current repository (with confirmation)
  cicada-mcp clean -f                # Clean current repository (skip confirmation)
  cicada-mcp clean --all             # Remove ALL project storage
  cicada-mcp clean --all -f          # Remove ALL project storage (skip confirmation)
        """,
    )
    clean_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Remove ALL Cicada storage for all projects (~/.cicada/projects/)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle the case where path_or_command might be a help flag (only if it exists)
    # This can happen if user types "cicada-mcp --help" - argparse treats it as positional arg
    if (
        args.command is None
        and hasattr(args, "path_or_command")
        and args.path_or_command in ["-h", "--help"]
    ):
        parser.print_help()
        return

    # Handle the case where path_or_command might be a subcommand (only if it exists)
    if (
        args.command is None
        and hasattr(args, "path_or_command")
        and args.path_or_command in known_subcommands
    ):
        # User typed "cicada-mcp install" etc. - show help for that subcommand
        parser.parse_args([args.path_or_command, "--help"])
        return

    # Route to appropriate handler
    if args.command == "install":
        handle_install(args)
    elif args.command == "server":
        handle_server(args)
    elif args.command == "claude":
        from cicada.cli import handle_editor_setup

        handle_editor_setup(args, "claude")
    elif args.command == "cursor":
        from cicada.cli import handle_editor_setup

        handle_editor_setup(args, "cursor")
    elif args.command == "vs":
        from cicada.cli import handle_editor_setup

        handle_editor_setup(args, "vs")
    elif args.command == "index":
        from cicada.cli import handle_index

        handle_index(args)
    elif args.command == "index-pr":
        from cicada.cli import handle_index_pr

        handle_index_pr(args)
    elif args.command == "find-dead-code":
        from cicada.cli import handle_find_dead_code

        handle_find_dead_code(args)
    elif args.command == "clean":
        from cicada.cli import handle_clean

        handle_clean(args)
    else:
        # No subcommand - check TTY for default behavior
        if is_tty():
            # Terminal context - show interactive setup
            handle_default_interactive(args)
        else:
            # Non-TTY (MCP client) - start server silently
            handle_default_server(args)


def handle_default_interactive(args):
    """
    Handle default behavior when called from terminal with no subcommand.
    Shows interactive setup (same as cicada with no args).
    """
    from cicada.interactive_setup import show_full_interactive_setup

    show_full_interactive_setup()


def handle_default_server(args):
    """
    Handle default behavior when called from MCP client with no subcommand.
    Starts MCP server silently (backward compatibility).
    """
    import asyncio
    import os
    from pathlib import Path

    # If path_or_command was provided, use it as repo path (backward compatibility)
    if hasattr(args, "path_or_command") and args.path_or_command:
        repo_path = Path(args.path_or_command).resolve()
        os.environ["CICADA_REPO_PATH"] = str(repo_path)

    # Import and run MCP server
    from cicada.mcp_server import async_main

    asyncio.run(async_main())


def handle_install(args):
    """Handle the install subcommand (interactive setup)."""
    from cicada.commands.install import handle_install as _handle_install

    _handle_install(args)


def handle_server(args):
    """Handle the server subcommand (silent MCP server with optional configs)."""
    from cicada.commands.server import handle_server as _handle_server

    _handle_server(args)


if __name__ == "__main__":
    main()
