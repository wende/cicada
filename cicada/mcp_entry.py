#!/usr/bin/env python
"""
Entry point for cicada-mcp command.

Behavior:
- With no args: Start MCP server
- With path arg: Start MCP server for that path
- cicada-mcp install: Interactive setup with editor and model selection
- With subcommands: Route to appropriate handler (same as cicada CLI)

This provides unified command interface for both cicada and cicada-mcp.
"""

import argparse
import sys


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

    # Handle path argument for backward compatibility (cicada-mcp <path>)
    # If first arg is not a known subcommand and not a flag, treat it as a path
    server_path = None
    if (
        len(sys.argv) > 1
        and sys.argv[1] not in known_subcommands
        and not sys.argv[1].startswith("-")
    ):
        # Extract the path and remove it from sys.argv so argparse doesn't see it
        server_path = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]

    parser = argparse.ArgumentParser(
        prog="cicada-mcp",
        description="Cicada MCP Server - AI-powered Elixir code analysis",
        epilog="Run 'cicada-mcp <command> --help' for more information on a command.",
    )

    # Create subparsers for commands (optional to support default server mode)
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=False)

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
        default=None,
        help="Path to index file (default: uses current directory's centralized index)",
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
  cicada-mcp clean                   # Remove everything (interactive with confirmation)
  cicada-mcp clean -f                # Remove everything (skip confirmation)
  cicada-mcp clean --index           # Remove main index (index.json, hashes.json)
  cicada-mcp clean --pr-index        # Remove PR index (pr_index.json)
  cicada-mcp clean --all             # Remove ALL project storage
  cicada-mcp clean --all -f          # Remove ALL project storage (skip confirmation)
        """,
    )
    clean_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt (for full clean or --all)",
    )
    clean_parser.add_argument(
        "--index",
        action="store_true",
        help="Remove only main index files (index.json, hashes.json)",
    )
    clean_parser.add_argument(
        "--pr-index",
        action="store_true",
        help="Remove only PR index file (pr_index.json)",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Remove ALL Cicada storage for all projects (~/.cicada/projects/)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Store the server path for default handler
    args._server_path = server_path

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
        # No subcommand - start server
        handle_default_server(args)


def handle_default_server(args):
    """
    Handle default behavior when called with no subcommand.
    Starts MCP server silently.
    """
    import asyncio
    import os
    from pathlib import Path

    # Check if a path was provided (backward compatibility: cicada-mcp <path>)
    if hasattr(args, "_server_path") and args._server_path:
        repo_path = Path(args._server_path).resolve()
        os.environ["CICADA_REPO_PATH"] = str(repo_path)

    # Import and run MCP server
    from cicada.mcp_server import async_main

    asyncio.run(async_main())


def handle_install(args):
    """
    Handle the install subcommand (interactive setup).

    Behavior:
    - INTERACTIVE: shows prompts and menus
    - Can skip prompts with flags (--claude, --cursor, --vs, --nlp, --rag)
    - Creates editor config and indexes repository
    """
    from pathlib import Path

    from cicada.interactive_setup import show_first_time_setup
    from cicada.setup import EditorType, setup
    from cicada.utils import get_config_path, get_index_path

    # Determine repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()

    # Validate it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project", file=sys.stderr)
        print("(mix.exs not found)", file=sys.stderr)
        sys.exit(1)

    # Validate flag combinations
    if (args.fast or args.max) and not args.rag:
        print("Error: --fast or --max requires --rag", file=sys.stderr)
        sys.exit(1)

    if args.nlp and args.rag:
        print("Error: Cannot specify both --nlp and --rag", file=sys.stderr)
        sys.exit(1)

    # Count editor flags
    editor_flags = [args.claude, args.cursor, args.vs]
    editor_count = sum(editor_flags)

    if editor_count > 1:
        print("Error: Can only specify one editor flag for install command", file=sys.stderr)
        sys.exit(1)

    # Determine editor from flags
    editor: EditorType | None = None
    if args.claude:
        editor = "claude"
    elif args.cursor:
        editor = "cursor"
    elif args.vs:
        editor = "vs"

    # Determine keyword method and tier from flags
    keyword_method = None
    keyword_tier = None

    if args.nlp:
        keyword_method = "lemminflect"
        keyword_tier = "regular"
    elif args.rag:
        keyword_method = "bert"
        if args.fast:
            keyword_tier = "fast"
        elif args.max:
            keyword_tier = "max"
        else:
            keyword_tier = "regular"

    # Check if index already exists
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    index_exists = config_path.exists() and index_path.exists()

    # If no flags provided, use full interactive setup
    if editor is None and keyword_method is None:
        from cicada.interactive_setup import show_full_interactive_setup

        show_full_interactive_setup(repo_path)
        return

    # If only model flags provided (no editor), prompt for editor
    if editor is None:
        # Show editor selection menu
        from simple_term_menu import TerminalMenu

        print("Select editor to configure:")
        print()
        editor_options = [
            "Claude Code (Claude AI assistant)",
            "Cursor (AI-powered code editor)",
            "VS Code (Visual Studio Code)",
        ]
        editor_menu = TerminalMenu(editor_options, title="Choose your editor:")
        menu_idx = editor_menu.show()

        if menu_idx is None:
            print("\nSetup cancelled.")
            sys.exit(0)

        # Map menu index to editor type (menu_idx is guaranteed to be int here)
        assert isinstance(menu_idx, int), "menu_idx must be an integer"
        editor_map: tuple[EditorType, EditorType, EditorType] = ("claude", "cursor", "vs")
        editor = editor_map[menu_idx]

    # If only editor flag provided (no model), prompt for model (unless index exists)
    if keyword_method is None and not index_exists:
        keyword_method, keyword_tier = show_first_time_setup()

    # If index exists but no model flags, use existing settings
    if keyword_method is None and index_exists:
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                keyword_method = existing_config.get("keyword_extraction", {}).get(
                    "method", "lemminflect"
                )
                keyword_tier = existing_config.get("keyword_extraction", {}).get("tier", "regular")
        except Exception:
            # If we can't read config, use defaults
            keyword_method = "lemminflect"
            keyword_tier = "regular"

    # Run setup
    try:
        setup(
            editor,
            repo_path,
            keyword_method=keyword_method,
            keyword_tier=keyword_tier,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_server(args):
    """
    Handle the server subcommand (silent MCP server with optional configs).

    Behavior:
    - SILENT: no prompts, no interactive menus
    - Auto-setup if needed (uses default model: lemminflect)
    - Creates editor configs if flags provided (--claude, --cursor, --vs)
    - Starts MCP server on stdio
    """
    import asyncio
    import os
    from pathlib import Path

    from cicada.setup import (
        EditorType,
        create_config_yaml,
        index_repository,
        setup_multiple_editors,
    )
    from cicada.utils import create_storage_dir, get_config_path, get_index_path

    # Determine repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()

    # Validate it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(
            f"Error: {repo_path} does not appear to be an Elixir project (mix.exs not found)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate flag combinations
    if (args.fast or args.max) and not args.rag:
        print("Error: --fast or --max requires --rag", file=sys.stderr)
        sys.exit(1)

    if args.nlp and args.rag:
        print("Error: Cannot specify both --nlp and --rag", file=sys.stderr)
        sys.exit(1)

    # Create storage directory
    storage_dir = create_storage_dir(repo_path)

    # Determine keyword extraction method and tier
    keyword_method = None
    keyword_tier = None

    if args.nlp:
        keyword_method = "lemminflect"
        keyword_tier = "regular"
    elif args.rag:
        keyword_method = "bert"
        if args.fast:
            keyword_tier = "fast"
        elif args.max:
            keyword_tier = "max"
        else:
            keyword_tier = "regular"

    # Check if setup is needed
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    needs_setup = not (config_path.exists() and index_path.exists())

    if needs_setup:
        # Silent setup with defaults
        # If no method specified, default to lemminflect (fastest, no downloads)
        if keyword_method is None:
            keyword_method = "lemminflect"
            keyword_tier = "regular"

        # Create config.yaml (silent)
        create_config_yaml(
            repo_path,
            storage_dir,
            keyword_method=keyword_method,
            keyword_tier=keyword_tier,
            verbose=False,
        )

        # Index repository (silent)
        try:
            index_repository(repo_path, force_full=False, verbose=False)
        except Exception as e:
            print(f"Error during indexing: {e}", file=sys.stderr)
            sys.exit(1)

    # Create editor configs if flags provided
    editors_to_configure: list[EditorType] = []
    if args.claude:
        editors_to_configure.append("claude")
    if args.cursor:
        editors_to_configure.append("cursor")
    if args.vs:
        editors_to_configure.append("vs")

    if editors_to_configure:
        try:
            setup_multiple_editors(editors_to_configure, repo_path, storage_dir, verbose=False)
        except Exception as e:
            print(f"Error creating editor configs: {e}", file=sys.stderr)
            sys.exit(1)

    # Set environment variable for MCP server
    os.environ["CICADA_REPO_PATH"] = str(repo_path)

    # Start MCP server (silent)
    from cicada.mcp_server import async_main

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
