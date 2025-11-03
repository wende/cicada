"""
CLI Command Handlers - Centralizes argparse logic and all CLI command handlers.

This module defines the argument parser and individual handler functions for all
Cicada CLI commands. It aims to consolidate command-line interface logic,
making `cli.py` a thin entry point and `mcp_entry.py` focused solely on MCP server startup.
"""

import argparse
import sys


def validate_tier_flags(args) -> None:
    """Validate that only one tier flag is specified.

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Raises:
        SystemExit: If more than one tier flag is specified
    """
    tier_count = sum([args.fast, getattr(args, "regular", False), args.max])
    if tier_count > 1:
        print(
            "Error: Can only specify one tier flag (--fast, --regular, or --max)",
            file=sys.stderr,
        )
        sys.exit(1)


def get_extraction_expansion_methods(args) -> tuple[str | None, str | None]:
    """Map tier flags to extraction and expansion methods.

    Args:
        args: Parsed command-line arguments with fast, regular, and max attributes

    Returns:
        Tuple of (extraction_method, expansion_method), or (None, None) if no tier flag
    """
    if args.fast:
        return "regular", "lemmi"
    elif args.max:
        return "bert", "fasttext"
    elif getattr(args, "regular", False):
        return "bert", "glove"
    return None, None


def get_argument_parser():
    parser = argparse.ArgumentParser(
        prog="cicada",
        description="Cicada - AI-powered Elixir code analysis and search",
        epilog="Run 'cicada <command> --help' for more information on a command.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s version from subcommand",
        help="Show version and commit hash",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

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
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion (no downloads)",
    )
    install_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (128MB, default)",
    )
    install_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion (958MB+)",
    )

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
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion (if reindexing needed)",
    )
    server_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (if reindexing needed)",
    )
    server_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion (if reindexing needed)",
    )

    claude_parser = subparsers.add_parser(
        "claude",
        help="Setup Cicada for Claude Code editor",
        description="One-command setup for Claude Code with keyword extraction",
    )
    claude_parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    claude_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    claude_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion",
    )

    cursor_parser = subparsers.add_parser(
        "cursor",
        help="Setup Cicada for Cursor editor",
        description="One-command setup for Cursor with keyword extraction",
    )
    cursor_parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    cursor_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    cursor_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion",
    )

    vs_parser = subparsers.add_parser(
        "vs",
        help="Setup Cicada for VS Code editor",
        description="One-command setup for VS Code with keyword extraction",
    )
    vs_parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    vs_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    vs_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion",
    )

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
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    index_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    index_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion",
    )
    index_parser.add_argument(
        "--test",
        action="store_true",
        help="Start interactive keyword extraction test mode",
    )
    index_parser.add_argument(
        "--test-expansion",
        action="store_true",
        help="Start interactive keyword expansion test mode",
    )
    index_parser.add_argument(
        "--extraction-threshold",
        type=float,
        default=0.3,
        metavar="SCORE",
        help="Minimum score for keyword extraction (0.0-1.0). For KeyBERT: semantic similarity threshold. Default: 0.3",
    )
    index_parser.add_argument(
        "--min-score",
        type=float,
        default=0.5,
        metavar="SCORE",
        help="Minimum score threshold for keywords (filters out low-scoring terms). Default: 0.5",
    )
    index_parser.add_argument(
        "--expansion-threshold",
        type=float,
        default=0.2,
        metavar="SCORE",
        help="Minimum similarity score for keyword expansion (0.0-1.0, default: 0.2)",
    )

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

    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove Cicada configuration and indexes",
        description="Remove Cicada configuration and indexes for current repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cicada clean                   # Remove everything (interactive with confirmation)
  cicada clean -f                # Remove everything (skip confirmation)
  cicada clean --index           # Remove main index (index.json, hashes.json)
  cicada clean --pr-index        # Remove PR index (pr_index.json)
  cicada clean --all             # Remove ALL project storage
  cicada clean --all -f          # Remove ALL project storage (skip confirmation)
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

    dir_parser = subparsers.add_parser(
        "dir",
        help="Show the absolute path to the Cicada storage directory",
        description="Display the absolute path to where Cicada stores configuration and indexes",
    )
    dir_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )

    return parser


def handle_command(args):
    if args.command == "install":
        handle_install(args)
    elif args.command == "server":
        handle_server(args)
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
    elif args.command == "dir":
        handle_dir(args)
    elif args.command is None:
        return False
    return True


def handle_editor_setup(args, editor: str):
    from pathlib import Path
    from typing import cast

    from cicada.setup import EditorType, setup

    # Validate tier flags
    validate_tier_flags(args)

    repo_path = Path.cwd()

    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project", file=sys.stderr)
        print("(mix.exs not found)", file=sys.stderr)
        sys.exit(1)

    from cicada.utils.storage import get_config_path, get_index_path

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    extraction_method, expansion_method = get_extraction_expansion_methods(args)

    if extraction_method is None and config_path.exists() and index_path.exists():
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                extraction_method = existing_config.get("keyword_extraction", {}).get(
                    "method", "regular"
                )
                expansion_method = existing_config.get("keyword_expansion", {}).get(
                    "method", "lemmi"
                )
        except Exception as e:
            print(f"Warning: Could not load existing config: {e}", file=sys.stderr)
    try:
        setup(
            cast(EditorType, editor),
            repo_path,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
            index_exists=config_path.exists() and index_path.exists(),
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_index_test_mode(args):
    """Handle interactive keyword extraction test mode."""
    from cicada.keyword_test import run_keywords_interactive

    # Validate tier flags
    validate_tier_flags(args)

    # Map tier to extraction method
    # Note: The tier names here don't match the flag names (legacy behavior)
    if args.fast:
        method = "regular"
        tier = "regular"
    elif args.max:
        method = "bert"
        tier = "max"
    else:  # --regular or no flag (default to regular)
        method = "bert"
        tier = "fast"

    extraction_threshold = getattr(args, "extraction_threshold", None)
    run_keywords_interactive(method=method, tier=tier, extraction_threshold=extraction_threshold)


def handle_index_test_expansion_mode(args):
    """Handle interactive keyword expansion test mode."""
    from cicada.keyword_test import run_expansion_interactive

    # Validate tier flags
    validate_tier_flags(args)

    # Map tier to extraction method and expansion type
    # Note: The tier names here don't match the flag names (legacy behavior)
    if args.fast:
        extraction_method = "regular"
        extraction_tier = "regular"
        expansion_type = "lemmi"
    elif args.max:
        extraction_method = "bert"
        extraction_tier = "max"
        expansion_type = "fasttext"
    else:  # --regular or no flag (default to regular)
        extraction_method = "bert"
        extraction_tier = "fast"
        expansion_type = "glove"

    extraction_threshold = getattr(args, "extraction_threshold", 0.3)
    expansion_threshold = getattr(args, "expansion_threshold", 0.2)
    min_score = getattr(args, "min_score", 0.5)
    run_expansion_interactive(
        expansion_type=expansion_type,
        extraction_method=extraction_method,
        extraction_tier=extraction_tier,
        extraction_threshold=extraction_threshold,
        expansion_threshold=expansion_threshold,
        min_score=min_score,
    )


def handle_index_main(args):
    """Handle main repository indexing."""
    from pathlib import Path

    from cicada.indexer import ElixirIndexer
    from cicada.utils.storage import create_storage_dir, get_config_path, get_index_path

    # Validate tier flags
    validate_tier_flags(args)

    repo_path_obj = Path(args.repo).resolve()
    config_path = get_config_path(repo_path_obj)
    storage_dir = create_storage_dir(repo_path_obj)
    index_path = get_index_path(repo_path_obj)

    extraction_method, expansion_method = get_extraction_expansion_methods(args)

    if extraction_method is not None:
        from cicada.setup import create_config_yaml

        if config_path.exists():
            import yaml

            try:
                with open(config_path) as f:
                    existing_config = yaml.safe_load(f)
                    existing_extraction = existing_config.get("keyword_extraction", {}).get(
                        "method", "regular"
                    )
                    existing_expansion = existing_config.get("keyword_expansion", {}).get(
                        "method", "lemmi"
                    )

                    extraction_changed = existing_extraction != extraction_method
                    expansion_changed = existing_expansion != expansion_method

                    if extraction_changed or expansion_changed:
                        if extraction_changed and expansion_changed:
                            change_desc = f"extraction from {existing_extraction} to {extraction_method} and expansion from {existing_expansion} to {expansion_method}"
                        elif extraction_changed:
                            change_desc = (
                                f"extraction from {existing_extraction} to {extraction_method}"
                            )
                        else:
                            change_desc = (
                                f"expansion from {existing_expansion} to {expansion_method}"
                            )

                        print(
                            f"Error: Cannot change {change_desc}",
                            file=sys.stderr,
                        )
                        print(
                            "\nTo reindex with different settings, first run:",
                            file=sys.stderr,
                        )
                        print("  cicada clean", file=sys.stderr)
                        print("\nThen run your index command again.", file=sys.stderr)
                        sys.exit(1)
            except Exception as e:
                print(f"Warning: Could not load existing config: {e}", file=sys.stderr)

        create_config_yaml(repo_path_obj, storage_dir, extraction_method, expansion_method)
    elif not config_path.exists():
        print("Error: No tier specified.", file=sys.stderr)
        print("\nYou must specify a tier for keyword extraction:", file=sys.stderr)
        print("  --fast      Fast tier: Regular extraction + lemmi expansion", file=sys.stderr)
        print(
            "  --regular   Regular tier: KeyBERT small + GloVe expansion (default)", file=sys.stderr
        )
        print("  --max       Max tier: KeyBERT large + FastText expansion", file=sys.stderr)
        print("\nRun 'cicada index --help' for more information.", file=sys.stderr)
        sys.exit(2)

    indexer = ElixirIndexer(verbose=True)
    indexer.incremental_index_repository(
        str(repo_path_obj),
        str(index_path),
        extract_keywords=True,
        force_full=False,
    )


def handle_index(args):
    """Route index command to appropriate handler based on mode."""
    from cicada.version_check import check_for_updates

    check_for_updates()

    if getattr(args, "test", False):
        handle_index_test_mode(args)
    elif getattr(args, "test_expansion", False):
        handle_index_test_expansion_mode(args)
    else:
        handle_index_main(args)


def handle_index_pr(args):
    from cicada.pr_indexer import PRIndexer
    from cicada.utils import get_pr_index_path
    from cicada.version_check import check_for_updates

    check_for_updates()

    try:
        output_path = str(get_pr_index_path(args.repo))

        indexer = PRIndexer(repo_path=args.repo)
        indexer.index_repository(output_path=output_path, incremental=not args.clean)

        print("\n✅ Indexing complete! You can now use the MCP tools for PR history lookups.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user.")
        print("Partial index may have been saved. Run again to continue (incremental by default).")
        sys.exit(130)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_find_dead_code(args):
    from cicada.dead_code.analyzer import DeadCodeAnalyzer
    from cicada.dead_code.finder import filter_by_confidence, format_json, format_markdown
    from cicada.utils import get_index_path, load_index

    index_path = get_index_path(".")

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

    analyzer = DeadCodeAnalyzer(index)
    results = analyzer.analyze()

    results = filter_by_confidence(results, args.min_confidence)

    output = format_json(results) if args.format == "json" else format_markdown(results)

    print(output)


def handle_clean(args):
    from pathlib import Path

    from cicada.clean import (
        clean_all_projects,
        clean_index_only,
        clean_pr_index_only,
        clean_repository,
    )

    if args.all:
        try:
            clean_all_projects(force=args.force)
        except Exception as e:
            print(f"\nError: Cleanup failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    flag_count = sum([args.index, args.pr_index])
    if flag_count > 1:
        print("Error: Cannot specify multiple clean options.", file=sys.stderr)
        print("Choose only one: --index, --pr-index, or -f/--force", file=sys.stderr)
        sys.exit(1)

    repo_path = Path.cwd()

    try:
        if args.index:
            clean_index_only(repo_path)
        elif args.pr_index:
            clean_pr_index_only(repo_path)
        else:
            clean_repository(repo_path, force=args.force)
    except Exception as e:
        print(f"\nError: Cleanup failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_dir(args):
    """Show the absolute path to the Cicada storage directory."""
    from pathlib import Path

    from cicada.utils.storage import get_storage_dir

    repo_path = Path(args.repo).resolve()

    try:
        storage_dir = get_storage_dir(repo_path)
        print(str(storage_dir))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_install(args):
    """
    Handle the install subcommand (interactive setup).

    Behavior:
    - INTERACTIVE: shows prompts and menus
    - Can skip prompts with flags (--claude, --cursor, --vs, --fast, --regular, --max)
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

    # Validate tier flags
    validate_tier_flags(args)

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

    # Determine extraction and expansion methods from flags
    extraction_method, expansion_method = get_extraction_expansion_methods(args)

    # Check if index already exists
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    index_exists = config_path.exists() and index_path.exists()

    # If no flags provided, use full interactive setup
    if editor is None and extraction_method is None:
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
    if extraction_method is None and not index_exists:
        extraction_method, expansion_method = show_first_time_setup()

    # If index exists but no model flags, use existing settings
    if extraction_method is None and index_exists:
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                extraction_method = existing_config.get("keyword_extraction", {}).get(
                    "method", "regular"
                )
                expansion_method = existing_config.get("keyword_expansion", {}).get(
                    "method", "lemmi"
                )
        except Exception as e:
            print(f"Warning: Could not load existing config, using defaults: {e}", file=sys.stderr)

    # Run setup
    try:
        setup(
            editor,
            repo_path,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
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

    # Validate tier flags
    validate_tier_flags(args)

    # Create storage directory
    storage_dir = create_storage_dir(repo_path)

    # Determine extraction and expansion methods
    extraction_method, expansion_method = get_extraction_expansion_methods(args)

    # Check if setup is needed
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    needs_setup = not (config_path.exists() and index_path.exists())

    if needs_setup:
        # Silent setup with defaults
        # If no tier specified, default to fast tier (fastest, no downloads)
        if extraction_method is None:
            extraction_method = "regular"
            expansion_method = "lemmi"

        # Create config.yaml (silent)
        create_config_yaml(
            repo_path, storage_dir, extraction_method, expansion_method, verbose=False
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
    from cicada.mcp.server import async_main

    asyncio.run(async_main())
