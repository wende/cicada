"""
CLI Command Handlers - Centralizes argparse logic and all CLI command handlers.

This module defines the argument parser and individual handler functions for all
Cicada CLI commands. It aims to consolidate command-line interface logic,
making `cli.py` a thin entry point and `mcp_entry.py` focused solely on MCP server startup.
"""

import argparse
import sys
from pathlib import Path

# Import tier resolution functions from centralized module
from cicada.tier import (
    determine_tier,
    get_extraction_expansion_methods,
    tier_flag_specified,
    validate_tier_flags,
)

# Default debounce interval for watch mode (in seconds)
DEFAULT_WATCH_DEBOUNCE = 2.0

KNOWN_SUBCOMMANDS: tuple[str, ...] = (
    "install",
    "server",
    "claude",
    "cursor",
    "vs",
    "gemini",
    "codex",
    "watch",
    "index",
    "index-pr",
    "find-dead-code",
    "clean",
    "dir",
)
KNOWN_SUBCOMMANDS_SET = frozenset(KNOWN_SUBCOMMANDS)


def _setup_and_start_watcher(args, repo_path_str: str) -> None:
    """Shared logic for starting file watcher.

    Args:
        args: Parsed command-line arguments
        repo_path_str: Path to the repository as a string

    Raises:
        SystemExit: If configuration is invalid or watcher fails to start
    """
    from cicada.utils.storage import get_config_path
    from cicada.watcher import FileWatcher

    # Validate tier flags
    validate_tier_flags(args, require_force=True)

    # Resolve repository path
    repo_path = Path(repo_path_str).resolve()
    config_path = get_config_path(repo_path)

    # Determine tier using helper
    tier = determine_tier(args, repo_path)

    # Check if config exists when no tier is specified
    tier_specified = tier_flag_specified(args)
    if not tier_specified and not config_path.exists():
        _print_tier_requirement_error()
        print("\nRun 'cicada watch --help' for more information.", file=sys.stderr)
        sys.exit(2)

    # Create and start watcher
    try:
        watcher = FileWatcher(
            repo_path=str(repo_path),
            debounce_seconds=getattr(args, "debounce", DEFAULT_WATCH_DEBOUNCE),
            verbose=True,
            tier=tier,
        )
        watcher.start_watching()
    except KeyboardInterrupt:
        print("\nWatch mode stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


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
        "--gemini",
        action="store_true",
        help="Skip editor selection, use Gemini CLI",
    )
    install_parser.add_argument(
        "--codex",
        action="store_true",
        help="Skip editor selection, use Codex",
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
        "--gemini",
        action="store_true",
        help="Create Gemini CLI config before starting server",
    )
    server_parser.add_argument(
        "--codex",
        action="store_true",
        help="Create Codex config before starting server",
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
    server_parser.add_argument(
        "--watch",
        action="store_true",
        help="Start file watcher in a linked process for automatic reindexing",
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

    gemini_parser = subparsers.add_parser(
        "gemini",
        help="Setup Cicada for Gemini CLI",
        description="One-command setup for Gemini CLI with keyword extraction",
    )
    gemini_parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    gemini_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    gemini_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion",
    )

    codex_parser = subparsers.add_parser(
        "codex",
        help="Setup Cicada for Codex editor",
        description="One-command setup for Codex with keyword extraction",
    )
    codex_parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    codex_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    codex_parser.add_argument(
        "--max",
        action="store_true",
        help="Max tier: KeyBERT large + FastText expansion",
    )

    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch for file changes and automatically reindex",
        description="Watch Elixir source files for changes and trigger automatic incremental reindexing",
    )
    watch_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the Elixir repository to watch (default: current directory)",
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Debounce interval in seconds to wait after file changes before reindexing (default: 2.0)",
    )
    watch_parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast tier: Regular extraction + lemmi expansion",
    )
    watch_parser.add_argument(
        "--regular",
        action="store_true",
        help="Regular tier: KeyBERT small + GloVe expansion (default)",
    )
    watch_parser.add_argument(
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
        "-f",
        "--force",
        action="store_true",
        help="Override configured tier (requires --fast, --regular, or --max)",
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
    index_parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for file changes and automatically reindex (runs initial index first)",
    )
    index_parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Debounce interval in seconds when using --watch (default: 2.0)",
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


def handle_command(args) -> bool:
    """Route command to appropriate handler.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if a command was handled, False if no command specified
    """
    command_handlers = {
        "install": handle_install,
        "server": handle_server,
        "claude": lambda args: handle_editor_setup(args, "claude"),
        "cursor": lambda args: handle_editor_setup(args, "cursor"),
        "vs": lambda args: handle_editor_setup(args, "vs"),
        "gemini": lambda args: handle_editor_setup(args, "gemini"),
        "codex": lambda args: handle_editor_setup(args, "codex"),
        "watch": handle_watch,
        "index": handle_index,
        "index-pr": handle_index_pr,
        "find-dead-code": handle_find_dead_code,
        "clean": handle_clean,
        "dir": handle_dir,
    }

    if args.command is None:
        return False

    handler = command_handlers.get(args.command)
    if handler:
        handler(args)
        return True

    return False


def handle_editor_setup(args, editor: str) -> None:
    """Handle setup for a specific editor.

    Args:
        args: Parsed command-line arguments
        editor: Editor type ('claude', 'cursor', or 'vs')
    """
    from typing import cast

    from cicada.setup import EditorType, setup
    from cicada.utils.storage import get_config_path, get_index_path

    # Validate tier flags
    validate_tier_flags(args)

    repo_path = Path.cwd()

    # Verify it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project", file=sys.stderr)
        print("(mix.exs not found)", file=sys.stderr)
        sys.exit(1)

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    index_exists = config_path.exists() and index_path.exists()

    extraction_method, expansion_method = get_extraction_expansion_methods(args)

    # Load existing config if no tier specified but index exists
    if extraction_method is None and index_exists:
        extraction_method, expansion_method = _load_existing_config(config_path)

    try:
        assert editor is not None
        setup(
            cast(EditorType, editor),
            repo_path,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def _load_existing_config(config_path: Path) -> tuple[str, str]:
    """Load extraction and expansion methods from existing config.

    Args:
        config_path: Path to config.yaml

    Returns:
        Tuple of (extraction_method, expansion_method)
    """
    import yaml

    try:
        with open(config_path) as f:
            existing_config = yaml.safe_load(f)
            extraction_method = existing_config.get("keyword_extraction", {}).get(
                "method", "regular"
            )
            expansion_method = existing_config.get("keyword_expansion", {}).get("method", "lemmi")
            return extraction_method, expansion_method
    except Exception as e:
        print(f"Warning: Could not load existing config: {e}", file=sys.stderr)
        return "regular", "lemmi"


def handle_index_test_mode(args):
    """Handle interactive keyword extraction test mode."""
    from cicada.keyword_test import run_keywords_interactive
    from cicada.tier import determine_tier, tier_to_methods

    # Validate tier flags
    validate_tier_flags(args)

    # Get tier (includes fallback to 'regular' if not specified)
    tier_name = determine_tier(args)

    # Convert tier to extraction method
    extraction_method, _ = tier_to_methods(tier_name)

    extraction_threshold = getattr(args, "extraction_threshold", None)
    run_keywords_interactive(
        method=extraction_method, tier=tier_name, extraction_threshold=extraction_threshold
    )


def handle_index_test_expansion_mode(args):
    """Handle interactive keyword expansion test mode."""
    from cicada.keyword_test import run_expansion_interactive
    from cicada.tier import determine_tier, tier_to_methods

    # Validate tier flags
    validate_tier_flags(args)

    # Get tier (includes fallback to 'regular' if not specified)
    tier_name = determine_tier(args)

    # Convert tier to extraction method and expansion type
    extraction_method, expansion_type = tier_to_methods(tier_name)

    extraction_threshold = getattr(args, "extraction_threshold", 0.3)
    expansion_threshold = getattr(args, "expansion_threshold", 0.2)
    min_score = getattr(args, "min_score", 0.5)
    run_expansion_interactive(
        expansion_type=expansion_type,
        extraction_method=extraction_method,
        extraction_tier=tier_name,
        extraction_threshold=extraction_threshold,
        expansion_threshold=expansion_threshold,
        min_score=min_score,
    )


def handle_index_main(args) -> None:
    """Handle main repository indexing."""
    from cicada.indexer import ElixirIndexer
    from cicada.utils.storage import create_storage_dir, get_config_path, get_index_path

    # Validate tier flags
    validate_tier_flags(args, require_force=True)

    repo_path = Path(args.repo).resolve()
    config_path = get_config_path(repo_path)
    storage_dir = create_storage_dir(repo_path)
    index_path = get_index_path(repo_path)

    force_enabled = getattr(args, "force", False) is True
    extraction_method: str | None = None
    expansion_method: str | None = None

    if force_enabled:
        extraction_method, expansion_method = get_extraction_expansion_methods(args)
        assert extraction_method is not None
        assert expansion_method is not None
        _handle_index_config_update(
            config_path, storage_dir, repo_path, extraction_method, expansion_method
        )
    elif not config_path.exists():
        _print_tier_requirement_error()
        sys.exit(2)

    # Perform indexing
    indexer = ElixirIndexer(verbose=True)
    indexer.incremental_index_repository(
        str(repo_path),
        str(index_path),
        extract_keywords=True,
        force_full=False,
    )


def _handle_index_config_update(
    config_path: Path,
    storage_dir: Path,
    repo_path: Path,
    extraction_method: str,
    expansion_method: str,
) -> None:
    """Handle config creation or validation during indexing.

    Args:
        config_path: Path to config.yaml
        storage_dir: Storage directory path
        repo_path: Repository path
        extraction_method: Extraction method to use
        expansion_method: Expansion method to use
    """
    from cicada.setup import create_config_yaml

    if config_path.exists():
        existing_extraction, existing_expansion = _load_existing_config(config_path)

        extraction_changed = existing_extraction != extraction_method
        expansion_changed = existing_expansion != expansion_method

        if extraction_changed or expansion_changed:
            _print_config_change_error(
                existing_extraction,
                existing_expansion,
                extraction_method,
                expansion_method,
                extraction_changed,
                expansion_changed,
            )
            sys.exit(1)

    create_config_yaml(repo_path, storage_dir, extraction_method, expansion_method)


def _print_config_change_error(
    existing_extraction: str,
    existing_expansion: str,
    extraction_method: str,
    expansion_method: str,
    extraction_changed: bool,
    expansion_changed: bool,
) -> None:
    """Print error message for config changes."""
    change_desc = _describe_config_change(
        existing_extraction,
        existing_expansion,
        extraction_method,
        expansion_method,
        extraction_changed,
        expansion_changed,
    )

    print(f"Error: Cannot change {change_desc}", file=sys.stderr)
    print("\nTo reindex with different settings, first run:", file=sys.stderr)
    print("  cicada clean", file=sys.stderr)
    print("\nThen run your index command again.", file=sys.stderr)


def _describe_config_change(
    existing_extraction: str,
    existing_expansion: str,
    extraction_method: str,
    expansion_method: str,
    extraction_changed: bool,
    expansion_changed: bool,
) -> str:
    """Generate description of config change."""
    if extraction_changed and expansion_changed:
        return f"extraction from {existing_extraction} to {extraction_method} and expansion from {existing_expansion} to {expansion_method}"
    if extraction_changed:
        return f"extraction from {existing_extraction} to {extraction_method}"
    return f"expansion from {existing_expansion} to {expansion_method}"


def _print_tier_requirement_error() -> None:
    """Print error message when no tier is specified."""
    print("Error: No tier configured.", file=sys.stderr)
    print(
        "\nUse '--force' with a tier flag to select keyword extraction settings:", file=sys.stderr
    )
    print(
        "  cicada index --force --fast      Fast tier: Regular extraction + lemmi expansion",
        file=sys.stderr,
    )
    print(
        "  cicada index --force --regular   Regular tier: KeyBERT small + GloVe expansion (default)",
        file=sys.stderr,
    )
    print(
        "  cicada index --force --max       Max tier: KeyBERT large + FastText expansion",
        file=sys.stderr,
    )
    print("\nRun 'cicada index --help' for more information.", file=sys.stderr)


def handle_index(args):
    """Route index command to appropriate handler based on mode."""
    from cicada.version_check import check_for_updates

    check_for_updates()

    if getattr(args, "test", False):
        handle_index_test_mode(args)
        return

    if getattr(args, "test_expansion", False):
        handle_index_test_expansion_mode(args)
        return

    if getattr(args, "watch", False):
        # Handle watch mode using shared logic
        _setup_and_start_watcher(args, args.repo)
    else:
        handle_index_main(args)


def handle_watch(args):
    """Handle watch command for automatic reindexing on file changes."""
    from cicada.version_check import check_for_updates

    check_for_updates()

    # Use shared watcher setup logic
    _setup_and_start_watcher(args, args.repo)


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
    from cicada.utils.storage import get_storage_dir

    repo_path = Path(args.repo).resolve()

    try:
        storage_dir = get_storage_dir(repo_path)
        print(str(storage_dir))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_install(args) -> None:
    """
    Handle the install subcommand (interactive setup).

    Behavior:
    - INTERACTIVE: shows prompts and menus
    - Can skip prompts with flags (--claude, --cursor, --vs, --fast, --regular, --max)
    - Creates editor config and indexes repository
    """
    from typing import cast

    from cicada.setup import EditorType, setup
    from cicada.utils import get_config_path, get_index_path

    # Determine and validate repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    _validate_elixir_project(repo_path)

    # Validate tier flags
    validate_tier_flags(args)

    # Parse editor selection
    editor = _determine_editor_from_args(args)

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
        editor = _prompt_for_editor()

    # If only editor flag provided (no model), prompt for model (unless index exists)
    if extraction_method is None and not index_exists:
        from cicada.interactive_setup import show_first_time_setup

        extraction_method, expansion_method, _, _ = show_first_time_setup()

    # If index exists but no model flags, use existing settings
    if extraction_method is None and index_exists:
        extraction_method, expansion_method = _load_existing_config(config_path)

    # Run setup
    assert editor is not None
    try:
        setup(
            cast(EditorType, editor),
            repo_path,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def _validate_elixir_project(repo_path: Path) -> None:
    """Validate that the repository is an Elixir project.

    Args:
        repo_path: Path to the repository

    Raises:
        SystemExit: If not an Elixir project
    """
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project", file=sys.stderr)
        print("(mix.exs not found)", file=sys.stderr)
        sys.exit(1)


def _determine_editor_from_args(args) -> str | None:
    """Determine editor from command-line arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Editor type or None if not specified

    Raises:
        SystemExit: If multiple editor flags specified
    """
    editor_flags = [args.claude, args.cursor, args.vs, args.gemini, args.codex]
    editor_count = sum(editor_flags)

    if editor_count > 1:
        print("Error: Can only specify one editor flag for install command", file=sys.stderr)
        sys.exit(1)

    if args.claude:
        return "claude"
    if args.cursor:
        return "cursor"
    if args.vs:
        return "vs"
    if args.gemini:
        return "gemini"
    if args.codex:
        return "codex"
    return None


def _prompt_for_editor() -> str:
    """Prompt user to select an editor.

    Returns:
        Selected editor type

    Raises:
        SystemExit: If user cancels selection
    """
    from simple_term_menu import TerminalMenu

    print("Select editor to configure:")
    print()
    editor_options = [
        "Claude Code (Claude AI assistant)",
        "Cursor (AI-powered code editor)",
        "VS Code (Visual Studio Code)",
        "Gemini CLI (Google Gemini command line interface)",
        "Codex (AI code editor)",
    ]
    editor_menu = TerminalMenu(editor_options, title="Choose your editor:")
    menu_idx = editor_menu.show()

    if menu_idx is None:
        print("\nSetup cancelled.")
        sys.exit(0)

    # Map menu index to editor type
    assert isinstance(menu_idx, int), "menu_idx must be an integer"
    editor_map: tuple[str, str, str, str, str] = ("claude", "cursor", "vs", "gemini", "codex")
    return editor_map[menu_idx]


def handle_server(args) -> None:
    """
    Handle the server subcommand (silent MCP server with optional configs).

    Behavior:
    - SILENT: no prompts, no interactive menus
    - Auto-setup if needed (uses default model: lemminflect)
    - Creates editor configs if flags provided (--claude, --cursor, --vs)
    - Starts MCP server on stdio
    """
    import asyncio
    import logging

    from cicada.utils import create_storage_dir, get_config_path, get_index_path

    logger = logging.getLogger(__name__)

    # Determine and validate repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    _validate_elixir_project(repo_path)

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
        _perform_silent_setup(repo_path, storage_dir, extraction_method, expansion_method)

    # Create editor configs if requested
    _configure_editors_if_requested(args, repo_path, storage_dir)

    # Start watch process if requested
    watch_enabled = getattr(args, "watch", False)
    if watch_enabled:
        _start_watch_for_server(args, repo_path)

    # Start MCP server
    from cicada.mcp.server import async_main

    try:
        asyncio.run(async_main())
    finally:
        # Ensure watch process is stopped when server exits
        if watch_enabled:
            _cleanup_watch_process(logger)


def _perform_silent_setup(
    repo_path: Path, storage_dir: Path, extraction_method: str | None, expansion_method: str | None
) -> None:
    """Perform silent setup with defaults if needed.

    Args:
        repo_path: Repository path
        storage_dir: Storage directory path
        extraction_method: Extraction method or None for defaults
        expansion_method: Expansion method or None for defaults
    """
    from cicada.setup import create_config_yaml, index_repository

    # If no tier specified, default to fast tier (fastest, no downloads)
    if extraction_method is None:
        extraction_method = "regular"
        expansion_method = "lemmi"

    # Create config.yaml (silent)
    create_config_yaml(repo_path, storage_dir, extraction_method, expansion_method, verbose=False)

    # Index repository (silent)
    try:
        index_repository(repo_path, force_full=False, verbose=False)
    except Exception as e:
        print(f"Error during indexing: {e}", file=sys.stderr)
        sys.exit(1)


def _configure_editors_if_requested(args, repo_path: Path, storage_dir: Path) -> None:
    """Configure editors if flags are provided.

    Args:
        args: Parsed command-line arguments
        repo_path: Repository path
        storage_dir: Storage directory path
    """
    from cicada.setup import EditorType, setup_multiple_editors

    editors_to_configure: list[EditorType] = []
    if args.claude:
        editors_to_configure.append("claude")
    if args.cursor:
        editors_to_configure.append("cursor")
    if args.vs:
        editors_to_configure.append("vs")
    if args.gemini:
        editors_to_configure.append("gemini")
    if args.codex:
        editors_to_configure.append("codex")

    if editors_to_configure:
        try:
            setup_multiple_editors(editors_to_configure, repo_path, storage_dir, verbose=False)
        except Exception as e:
            print(f"Error creating editor configs: {e}", file=sys.stderr)
            sys.exit(1)


def _start_watch_for_server(args, repo_path: Path) -> None:
    """Start watch process for the server.

    Args:
        args: Parsed command-line arguments
        repo_path: Repository path
    """
    from cicada.watch_manager import start_watch_process

    # Determine tier using helper
    tier = determine_tier(args, repo_path)

    # Start the watch process
    try:
        if not start_watch_process(repo_path, tier=tier, debounce=DEFAULT_WATCH_DEBOUNCE):
            print("ERROR: Failed to start watch process as requested", file=sys.stderr)
            print("Server startup aborted. Run without --watch or fix the issue.", file=sys.stderr)
            sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: Cannot start watch process: {e}", file=sys.stderr)
        print("Server startup aborted. Run without --watch or fix the issue.", file=sys.stderr)
        sys.exit(1)


def _cleanup_watch_process(logger) -> None:
    """Clean up watch process on server exit.

    Args:
        logger: Logger instance
    """
    try:
        from cicada.watch_manager import stop_watch_process

        stop_watch_process()
    except Exception as e:
        logger.exception("Error stopping watch process during cleanup")
        print(f"Warning: Error stopping watch process: {e}", file=sys.stderr)
