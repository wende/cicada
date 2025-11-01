"""
Unified CLI entry point for Cicada.

Provides a single `cicada` command with multiple subcommands:
- cicada [path]           - Setup/install Cicada for a project
- cicada claude           - Setup Cicada for Claude Code editor
- cicada cursor           - Setup Cicada for Cursor editor
- cicada vs               - Setup Cicada for VS Code editor
- cicada index            - Index an Elixir repository
- cicada index-pr         - Index GitHub pull requests
- cicada find-dead-code   - Find potentially unused functions
- cicada clean            - Remove Cicada configuration and indexes
"""

import argparse
import sys


def main():
    """Main entry point for the unified cicada CLI."""
    parser = argparse.ArgumentParser(
        prog="cicada",
        description="Cicada - AI-powered Elixir code analysis and search",
        epilog="Run 'cicada <command> --help' for more information on a command.",
    )

    # Add optional positional argument for backward compatibility
    # If no subcommand is given, treat as install path
    parser.add_argument(
        "path_or_command",
        nargs="?",
        default=None,
        help="Repository path for setup, or subcommand (claude, cursor, vs, index, index-pr, find-dead-code, clean)",
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
  cicada find-dead-code                      # Show high confidence candidates
  cicada find-dead-code --min-confidence low # Show all candidates
  cicada find-dead-code --format json        # Output as JSON
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
  cicada clean                   # Clean current repository (with confirmation)
  cicada clean -f                # Clean current repository (skip confirmation)
  cicada clean --all             # Remove ALL project storage
  cicada clean --all -f          # Remove ALL project storage (skip confirmation)
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

    # Handle the case where path_or_command might be a subcommand
    # This handles backward compatibility where someone might run "cicada index"
    # without using proper subparsers
    if args.command is None and args.path_or_command in [
        "install",
        "server",
        "claude",
        "cursor",
        "vs",
        "index",
        "index-pr",
        "find-dead-code",
        "clean",
    ]:
        # User typed "cicada index" etc. - show help for that subcommand
        parser.parse_args([args.path_or_command, "--help"])
        return

    # Route to appropriate handler
    if args.command == "install":
        handle_install_command(args)
    elif args.command == "server":
        handle_server_command(args)
    elif args.command == "claude":
        handle_editor_setup(args, "claude")
    elif args.command == "cursor":
        handle_editor_setup(args, "cursor")
    elif args.command == "vs":
        handle_editor_setup(args, "vs")
    elif args.command == "index":
        handle_index(args)
    elif args.command == "index-pr":
        handle_index_pr(args)
    elif args.command == "find-dead-code":
        handle_find_dead_code(args)
    elif args.command == "clean":
        handle_clean(args)
    else:
        # No subcommand - default to install behavior
        handle_install(args)


def handle_install(args):
    """Handle the default install/setup behavior (no subcommand)."""
    from cicada.interactive_setup import show_full_interactive_setup

    # If no path provided, show interactive setup
    if not args.path_or_command:
        show_full_interactive_setup()
        return

    # Legacy path argument - use old install.py
    from cicada.install import main as install_main

    sys.argv = ["cicada", args.path_or_command]
    install_main()


def handle_install_command(args):
    """Handle the explicit install subcommand."""
    from cicada.commands.install import handle_install

    handle_install(args)


def handle_server_command(args):
    """Handle the server subcommand (silent MCP server with optional configs)."""
    from cicada.commands.server import handle_server

    handle_server(args)


def handle_editor_setup(args, editor: str):
    """Handle editor setup subcommands (claude, cursor, vs)."""
    from pathlib import Path
    from typing import cast

    from cicada.setup import EditorType, setup

    # Validate that --fast or --max requires --nlp or --rag
    if (args.fast or args.max) and not (args.nlp or args.rag):
        print("Error: --fast or --max requires either --nlp or --rag", file=sys.stderr)
        sys.exit(1)

    # Both --nlp and --rag cannot be specified
    if args.nlp and args.rag:
        print("Error: Cannot specify both --nlp and --rag", file=sys.stderr)
        sys.exit(1)

    # Use current directory as repo path
    repo_path = Path.cwd()

    # Check if it's an Elixir repository
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project", file=sys.stderr)
        print("(mix.exs not found)", file=sys.stderr)
        sys.exit(1)

    # Determine keyword extraction method and tier from flags
    keyword_method = None
    keyword_tier = None

    if args.nlp:
        keyword_method = "lemminflect"
        keyword_tier = "regular"  # Lemminflect only has one tier
    elif args.rag:
        keyword_method = "bert"
        # Determine tier from flags
        if args.fast:
            keyword_tier = "fast"
        elif args.max:
            keyword_tier = "max"
        else:
            keyword_tier = "regular"  # Default for bert

    # If no flags provided, check if index already exists
    index_exists = False
    if keyword_method is None:
        from cicada.utils.storage import get_config_path, get_index_path

        config_path = get_config_path(repo_path)
        index_path = get_index_path(repo_path)

        if config_path.exists() and index_path.exists():
            # Index exists - read existing settings and mark index_exists
            import yaml

            try:
                with open(config_path) as f:
                    existing_config = yaml.safe_load(f)
                    keyword_method = existing_config.get("keyword_extraction", {}).get(
                        "method", "lemminflect"
                    )
                    keyword_tier = existing_config.get("keyword_extraction", {}).get(
                        "tier", "regular"
                    )
                    index_exists = True
            except Exception:
                # If we can't read config, proceed with defaults
                pass

    # Run setup
    try:
        setup(
            cast(EditorType, editor),
            repo_path,
            keyword_method=keyword_method,
            keyword_tier=keyword_tier,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_index(args):
    """Handle the index subcommand."""
    from pathlib import Path

    from cicada.indexer import ElixirIndexer
    from cicada.interactive_setup import show_first_time_setup
    from cicada.utils.storage import get_config_path
    from cicada.version_check import check_for_updates

    # Check for updates (non-blocking, fails silently)
    check_for_updates()

    # Validate that --fast or --max requires --nlp or --rag
    if (args.fast or args.max) and not (args.nlp or args.rag):
        print("Error: --fast or --max requires either --nlp or --rag", file=sys.stderr)
        sys.exit(1)

    # Both --nlp and --rag cannot be specified
    if args.nlp and args.rag:
        print("Error: Cannot specify both --nlp and --rag", file=sys.stderr)
        sys.exit(1)

    # Check if config.yaml exists to determine if we need interactive setup
    repo_path_obj = Path(args.repo).resolve()
    config_path = get_config_path(repo_path_obj)
    config_exists = config_path.exists()

    # Use centralized storage paths
    from cicada.utils.storage import create_storage_dir, get_index_path

    storage_dir = create_storage_dir(repo_path_obj)
    index_path = get_index_path(repo_path_obj)

    # Determine keyword extraction method and tier
    keyword_method = None
    keyword_tier = None
    force_full = False

    # If flags provided, update config with new settings
    if args.nlp or args.rag:
        # User explicitly specified extraction method via flags
        from cicada.setup import create_config_yaml

        # Determine method and tier from flags
        if args.nlp:
            keyword_method = "lemminflect"
            keyword_tier = "regular"
        else:  # args.rag
            keyword_method = "bert"
            if args.fast:
                keyword_tier = "fast"
            elif args.max:
                keyword_tier = "max"
            else:
                keyword_tier = "regular"

        # Warn if changing existing config
        if config_exists:
            import yaml

            try:
                with open(config_path) as f:
                    existing_config = yaml.safe_load(f)
                    existing_method = existing_config.get("keyword_extraction", {}).get(
                        "method", "lemminflect"
                    )
                    if existing_method != keyword_method:
                        print(
                            f"⚠️  Warning: Changing keyword extraction method from {existing_method} to {keyword_method}"
                        )
                        print("   This will trigger a full reindex of the entire codebase.")
                        print()
                        force_full = True  # Force full reindex when changing method
            except Exception:
                pass  # If we can't read config, just proceed

        create_config_yaml(repo_path_obj, storage_dir, keyword_method, keyword_tier)
        config_exists = True  # Config now exists
    elif not config_exists:
        # No flags provided AND no config exists - trigger interactive setup
        print("No keyword extraction method specified. Starting interactive setup...\n")
        keyword_method, keyword_tier = show_first_time_setup()

        # Save the interactive setup preferences to config.yaml
        from cicada.setup import create_config_yaml

        create_config_yaml(repo_path_obj, storage_dir, keyword_method, keyword_tier)
        config_exists = True  # Config now exists

    # If config exists (or was just created), indexer will read it automatically
    indexer = ElixirIndexer()
    indexer.incremental_index_repository(
        str(repo_path_obj),
        str(index_path),  # Use centralized storage path
        extract_keywords=True,  # Always extract keywords if we have a config
        force_full=force_full,
    )


def handle_index_pr(args):
    """Handle the index-pr subcommand."""
    from cicada.pr_indexer import PRIndexer
    from cicada.version_check import check_for_updates

    # Check for updates (non-blocking, fails silently)
    check_for_updates()

    try:
        indexer = PRIndexer(repo_path=args.repo)
        # Incremental by default, unless --clean is specified
        indexer.index_repository(output_path=args.output, incremental=not args.clean)

        print("\n✅ Indexing complete! You can now use the MCP tools for PR history lookups.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user.")
        print("Partial index may have been saved. Run again to continue (incremental by default).")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_find_dead_code(args):
    """Handle the find-dead-code subcommand."""
    from pathlib import Path

    from cicada.dead_code_analyzer import DeadCodeAnalyzer
    from cicada.find_dead_code import filter_by_confidence, format_json, format_markdown
    from cicada.utils import load_index

    # Load index
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index file not found: {index_path}", file=sys.stderr)
        print("\nRun 'cicada index' first to create the index.", file=sys.stderr)
        sys.exit(1)

    try:
        index = load_index(index_path, raise_on_error=True)
    except Exception as e:
        print(f"Error loading index: {e}", file=sys.stderr)
        sys.exit(1)

    assert index is not None, "Index should not be None after successful load"

    # Run analysis
    analyzer = DeadCodeAnalyzer(index)
    results = analyzer.analyze()

    # Filter by confidence
    results = filter_by_confidence(results, args.min_confidence)

    # Format output
    output = format_json(results) if args.format == "json" else format_markdown(results)

    print(output)


def handle_clean(args):
    """Handle the clean subcommand."""
    from pathlib import Path

    from cicada.clean import clean_all_projects, clean_repository

    # Handle --all flag
    if args.all:
        try:
            clean_all_projects(force=args.force)
        except Exception as e:
            print(f"\nError: Cleanup failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Clean current directory
    repo_path = Path.cwd()

    # Run cleanup
    try:
        clean_repository(repo_path, force=args.force)
    except Exception as e:
        print(f"\nError: Cleanup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
