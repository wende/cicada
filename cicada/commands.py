"""
CLI Command Handlers - Centralizes argparse logic and all CLI command handlers.

This module defines the argument parser and individual handler functions for all
Cicada CLI commands. It aims to consolidate command-line interface logic,
making `cli.py` a thin entry point and `mcp_entry.py` focused solely on MCP server startup.
"""

import argparse
import sys
from pathlib import Path

from cicada.index_mode import (
    INDEX_MODE_EMBEDDINGS,
    determine_indexing_mode,
    mode_flag_specified,
    validate_mode_flags,
)

# Import indexing mode resolution functions from centralized module
from cicada.languages.generic.indexer import run_generic_indexing_for_language_indexer

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
    "clean",
    "status",
    "stats",
    "dir",
    "link",
    "unlink",
    "agents",
    "run",
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

    # Validate indexing mode flags
    validate_mode_flags(args, require_force=True)

    # Resolve repository path
    repo_path = Path(repo_path_str).resolve()
    config_path = get_config_path(repo_path)

    # Determine indexing mode using helper
    indexing_mode = determine_indexing_mode(args, repo_path)
    from cicada.index_mode import ensure_supported_mode

    try:
        ensure_supported_mode(indexing_mode)
    except NotImplementedError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if config exists when no mode is specified
    mode_specified = mode_flag_specified(args)
    if not mode_specified and not config_path.exists():
        _print_mode_requirement_error()
        print("\nRun 'cicada watch --help' for more information.", file=sys.stderr)
        sys.exit(2)

    # Create and start watcher
    # Use --quiet flag for background processes, otherwise show progress
    try:
        watcher = FileWatcher(
            repo_path=str(repo_path),
            debounce_seconds=getattr(args, "debounce", DEFAULT_WATCH_DEBOUNCE),
            verbose=not getattr(args, "quiet", False),
            indexing_mode=indexing_mode,
        )
        watcher.start_watching()
    except KeyboardInterrupt:
        print("\nWatch mode stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _add_indexing_mode_arguments(parser: argparse.ArgumentParser) -> None:
    """Add --keywords, --embeddings indexing mode arguments."""
    parser.add_argument(
        "--keywords",
        action="store_true",
        help="Keyword-based indexing (default)",
    )
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Embeddings-based indexing with semantic search",
    )


def _add_editor_arguments(parser: argparse.ArgumentParser) -> None:
    """Add editor selection arguments."""
    parser.add_argument(
        "--claude",
        action="store_true",
        help="Skip editor selection, use Claude Code",
    )
    parser.add_argument(
        "--cursor",
        action="store_true",
        help="Skip editor selection, use Cursor",
    )
    parser.add_argument(
        "--vs",
        action="store_true",
        help="Skip editor selection, use VS Code",
    )
    parser.add_argument(
        "--gemini",
        action="store_true",
        help="Skip editor selection, use Gemini CLI",
    )
    parser.add_argument(
        "--codex",
        action="store_true",
        help="Skip editor selection, use Codex",
    )


def _create_editor_subparser(
    subparsers, name: str, common_parser: argparse.ArgumentParser
) -> argparse.ArgumentParser:
    """Create an editor-specific subparser (claude, cursor, vs, gemini, codex)."""
    editor_display_names = {
        "claude": "Claude Code",
        "cursor": "Cursor",
        "vs": "VS Code",
        "gemini": "Gemini CLI",
        "codex": "Codex",
    }
    display_name = editor_display_names.get(name, name.title())
    parser = subparsers.add_parser(
        name,
        help=f"Setup Cicada for {display_name} editor",
        description=f"One-command setup for {display_name} with keyword extraction",
        parents=[common_parser],
    )
    _add_indexing_mode_arguments(parser)
    return parser


def get_argument_parser():
    # Create a parent parser with common arguments to share across all subcommands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (detailed progress and debugging information)",
    )

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
        description="Interactive setup with editor and indexing mode selection",
        parents=[common_parser],
    )
    install_parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to project repository (default: current directory)",
    )
    _add_editor_arguments(install_parser)
    _add_indexing_mode_arguments(install_parser)
    install_parser.add_argument(
        "--default",
        action="store_true",
        help="Initialize with default values (equivalent to --keywords)",
    )
    install_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Accept all defaults (non-interactive mode). Also enables PR indexing by default.",
    )
    install_parser.add_argument(
        "--index-prs",
        action="store_true",
        help="Force enable PR indexing",
    )
    install_parser.add_argument(
        "--no-index-prs",
        action="store_true",
        help="Force disable PR indexing",
    )
    install_parser.add_argument(
        "--skip-optional",
        action="store_true",
        help="Skip all optional features (PR indexing, etc.)",
    )

    server_parser = subparsers.add_parser(
        "server",
        help="Start MCP server (silent mode with defaults)",
        description="Start MCP server with auto-setup using defaults",
        parents=[common_parser],
    )
    server_parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to project repository (default: current directory)",
    )
    _add_editor_arguments(server_parser)
    _add_indexing_mode_arguments(server_parser)
    server_parser.add_argument(
        "--watch",
        action="store_true",
        help="Start file watcher in a linked process for automatic reindexing",
    )

    # Editor-specific subparsers (all have identical structure with mode args)
    for editor in ["claude", "cursor", "vs", "gemini", "codex"]:
        _create_editor_subparser(subparsers, editor, common_parser)

    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch for file changes and automatically reindex",
        description="Watch Elixir source files for changes and trigger automatic incremental reindexing",
        parents=[common_parser],
    )
    watch_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the project repository to watch (default: current directory)",
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Debounce interval in seconds to wait after file changes before reindexing (default: 2.0)",
    )
    _add_indexing_mode_arguments(watch_parser)
    watch_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output (used internally for background watch processes)",
    )

    index_parser = subparsers.add_parser(
        "index",
        help="Index a project repository to extract code symbols",
        description="Index current project repository to extract code symbols",
        parents=[common_parser],
    )
    index_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the project repository to index (default: current directory)",
    )
    _add_indexing_mode_arguments(index_parser)
    index_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Override configured indexing mode (requires --keywords or --embeddings)",
    )
    index_parser.add_argument(
        "--default",
        action="store_true",
        help="Initialize with default values (equivalent to --force --keywords)",
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
        help="Minimum score for keyword extraction (0.0-1.0). Default: 0.3",
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
    index_parser.add_argument(
        "--no-cochange",
        action="store_true",
        help="Disable co-change analysis (enabled by default for better search results)",
    )

    index_pr_parser = subparsers.add_parser(
        "index-pr",
        help="Index GitHub pull requests for fast offline lookup",
        description="Index GitHub pull requests for fast offline lookup",
        parents=[common_parser],
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

    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove Cicada configuration and indexes",
        description="Remove Cicada configuration and indexes for current repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
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

    status_parser = subparsers.add_parser(
        "status",
        help="Show diagnostic information about Cicada configuration",
        description="Display diagnostic information about Cicada indexes and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
        epilog="""
Examples:
  cicada status              # Check current repository
  cicada status /path/repo   # Check specific repository
        """,
    )
    status_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show MCP tool usage statistics for this project",
        description="Display usage statistics for MCP tool calls in this project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
        epilog="""
Examples:
  cicada stats                      # Summary (all time)
  cicada stats --detailed           # Detailed breakdown
  cicada stats --last-7-days        # Last 7 days only
  cicada stats --tool query         # Filter by tool
  cicada stats --time-series        # Daily view
  cicada stats --time-series --weekly   # Weekly view
  cicada stats --format json        # JSON output
  cicada stats --reset --older-than 30  # Delete logs >30 days old
        """,
    )

    stats_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )

    stats_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed per-tool breakdown",
    )
    stats_parser.add_argument(
        "--time-series",
        action="store_true",
        help="Show time-based aggregation",
    )
    stats_parser.add_argument(
        "--weekly",
        action="store_true",
        help="Use weekly aggregation (requires --time-series)",
    )
    stats_parser.add_argument(
        "--tool",
        help="Filter by tool name",
    )
    stats_parser.add_argument(
        "--last-7-days",
        action="store_true",
        help="Show last 7 days only",
    )
    stats_parser.add_argument(
        "--last-30-days",
        action="store_true",
        help="Show last 30 days only",
    )
    stats_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    stats_parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete log files",
    )
    stats_parser.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        help="With --reset: only delete logs older than DAYS",
    )
    stats_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="With --reset: skip confirmation",
    )

    dir_parser = subparsers.add_parser(
        "dir",
        help="Show the absolute path to the Cicada storage directory",
        description="Display the absolute path to where Cicada stores configuration and indexes",
        parents=[common_parser],
    )
    dir_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )

    link_parser = subparsers.add_parser(
        "link",
        help="Link current repository to use another repository's index",
        description="Create a link from the current (or target) repository to use an existing index from a source repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
        epilog="""
Examples:
  cicada link /path/to/source/repo          # Link current repo to source repo's index
  cicada link --to /target /path/to/source  # Link target repo to source repo's index

Use cases:
  - Monorepo: Link child projects to parent project's index
  - Testing: Link test repository to main repository
  - Development: Share index across multiple working directories
        """,
    )
    link_parser.add_argument(
        "source",
        help="Path to the source repository (must be indexed)",
    )
    link_parser.add_argument(
        "--to",
        dest="target",
        default=".",
        help="Path to the target repository (default: current directory)",
    )

    unlink_parser = subparsers.add_parser(
        "unlink",
        help="Remove link from repository",
        description="Remove the link from a repository, allowing it to have its own index again",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
        epilog="""
Examples:
  cicada unlink              # Remove link from current repo
  cicada unlink /target/repo # Remove link from target repo
        """,
    )
    unlink_parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )

    # Agents command (MVP: install subcommand only)
    agents_parser = subparsers.add_parser(
        "agents",
        help="Install Claude Code agents",
        description="Install agents for code exploration",
        parents=[common_parser],
    )
    agents_subparsers = agents_parser.add_subparsers(dest="agents_command", required=True)
    agents_subparsers.add_parser("install", help="Install Cicada agents")

    # Run command - execute MCP tools from CLI
    run_parser = subparsers.add_parser(
        "run",
        help="Execute MCP tools from CLI",
        description="Execute any of the 8 MCP tools directly from command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
        epilog="""
Examples:
  cicada run query "authentication"           # Search for code related to auth
  cicada run search-module --module-name "MyApp.User"  # Search for a module
  cicada run search-function create_user      # Find function definitions
  cicada run git-history --file-path lib/auth.ex      # View file history
        """,
    )
    # Register tool subparsers from MCP tool definitions
    run_subparsers = run_parser.add_subparsers(dest="tool", required=True)
    from cicada.cli_mapper import register_tool_subparsers
    from cicada.mcp.tools import get_tool_definitions

    register_tool_subparsers(run_subparsers, get_tool_definitions())

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
        "clean": handle_clean,
        "status": handle_status,
        "stats": handle_stats,
        "dir": handle_dir,
        "link": handle_link,
        "unlink": handle_unlink,
        "agents": handle_agents,
        "run": handle_run,
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

    from cicada.setup import EditorType, detect_project_language, setup
    from cicada.utils.storage import get_config_path, get_index_path

    # Validate indexing mode flags
    validate_mode_flags(args)

    repo_path = Path.cwd()

    # Detect and validate project language
    try:
        detect_project_language(repo_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    index_exists = config_path.exists() and index_path.exists()

    indexing_mode = determine_indexing_mode(args, repo_path)

    # Load existing config if no mode specified but index exists
    if not mode_flag_specified(args) and index_exists:
        indexing_mode = _load_existing_config(config_path)

    try:
        assert editor is not None
        setup(
            cast(EditorType, editor),
            repo_path,
            indexing_mode=indexing_mode,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def _load_existing_config(config_path: Path) -> str:
    """Load indexing mode from existing config.

    Args:
        config_path: Path to config.yaml

    Returns:
        Indexing mode string
    """
    import yaml

    try:
        with open(config_path) as f:
            existing_config = yaml.safe_load(f)
            indexing_mode = existing_config.get("indexing", {}).get("mode")
            if indexing_mode in ("keywords", "embeddings"):
                return indexing_mode

            if existing_config.get("keyword_extraction") or existing_config.get(
                "keyword_expansion"
            ):
                return "keywords"
            return "keywords"
    except Exception as e:
        print(f"Warning: Could not load existing config: {e}", file=sys.stderr)
        return "keywords"


def handle_index_test_mode(args):
    """Handle interactive keyword extraction test mode."""
    from cicada.index_mode import ensure_supported_mode
    from cicada.keyword_test import run_keywords_interactive

    # Validate indexing mode flags
    validate_mode_flags(args)

    indexing_mode = determine_indexing_mode(args)
    try:
        ensure_supported_mode(indexing_mode)
    except NotImplementedError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    extraction_threshold = getattr(args, "extraction_threshold", None)
    run_keywords_interactive(method="regular", extraction_threshold=extraction_threshold)


def handle_index_test_expansion_mode(args):
    """Handle interactive keyword expansion test mode."""
    from cicada.index_mode import ensure_supported_mode
    from cicada.keyword_test import run_expansion_interactive

    # Validate indexing mode flags
    validate_mode_flags(args)

    indexing_mode = determine_indexing_mode(args)
    try:
        ensure_supported_mode(indexing_mode)
    except NotImplementedError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    extraction_method = "regular"
    expansion_type = "lemmi"

    extraction_threshold = getattr(args, "extraction_threshold", 0.3)
    expansion_threshold = getattr(args, "expansion_threshold", 0.2)
    min_score = getattr(args, "min_score", 0.5)
    run_expansion_interactive(
        expansion_type=expansion_type,
        extraction_method=extraction_method,
        extraction_threshold=extraction_threshold,
        expansion_threshold=expansion_threshold,
        min_score=min_score,
    )


def handle_index_main(args) -> None:
    """Handle main repository indexing."""
    from cicada.languages import LanguageRegistry
    from cicada.setup import detect_project_language
    from cicada.utils.storage import create_storage_dir, get_config_path, get_index_path

    # Handle --default flag: convert to --force --keywords
    if getattr(args, "default", False):
        args.force = True
        args.keywords = True

    # Validate indexing mode flags
    validate_mode_flags(args, require_force=True)

    repo_path = Path(args.repo).resolve()

    # Detect project language
    language = detect_project_language(repo_path)

    config_path = get_config_path(repo_path)
    storage_dir = create_storage_dir(repo_path)
    index_path = get_index_path(repo_path)

    force_enabled = getattr(args, "force", False) is True
    indexing_mode: str | None = None
    mode_changed = False

    if force_enabled:
        indexing_mode = determine_indexing_mode(args, repo_path)
        mode_changed = _handle_index_config_update(
            config_path, storage_dir, repo_path, indexing_mode
        )
        if mode_changed:
            print("Indexing mode changed. Performing full reindex...")
    elif not config_path.exists():
        _print_mode_requirement_error()
        sys.exit(2)

    if indexing_mode is None:
        indexing_mode = determine_indexing_mode(args, repo_path)
    from cicada.index_mode import ensure_supported_mode

    try:
        ensure_supported_mode(indexing_mode)
    except NotImplementedError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Perform indexing using unified interface
    # If mode changed, force full reindex to ensure index consistency with new config
    indexer = LanguageRegistry.get_indexer(language)
    # CLI commands always show progress (only MCP server should be silent)
    verbose = True

    try:
        # Check if indexer supports incremental_index_repository (new unified API)
        if indexer.supports_incremental:
            # Co-change analysis is enabled by default for better search results
            # Can be disabled with --no-cochange flag
            extract_cochange = not getattr(args, "no_cochange", False)
            # Force full reindex if --force flag was used OR mode changed
            should_force = force_enabled or mode_changed
            indexer.incremental_index_repository(
                repo_path=str(repo_path),
                output_path=str(index_path),
                extract_keywords=True,
                compute_timestamps=True,
                extract_cochange=extract_cochange,
                force_full=should_force,
                verbose=verbose,
            )
        else:
            # Fallback to basic interface for legacy indexers
            should_force = force_enabled or mode_changed
            indexer.index_repository(
                repo_path=str(repo_path),
                output_path=str(index_path),
                force=should_force,
                verbose=verbose,
                config_path=str(config_path),
            )

        run_generic_indexing_for_language_indexer(
            indexer,
            repo_path,
            index_path,
            verbose=verbose,
        )

        # If embeddings mode, generate embeddings after the regular index
        if indexing_mode == INDEX_MODE_EMBEDDINGS:
            import json

            from cicada.embeddings.indexer import EmbeddingsIndexer

            if verbose:
                print("\nGenerating embeddings for semantic search...")

            # Load the index we just created
            with open(index_path) as f:
                index_data = json.load(f)

            try:
                embeddings_indexer = EmbeddingsIndexer(
                    repo_path, verbose=verbose, force=force_enabled
                )
                embeddings_indexer.index_from_parsed_data(index_data)

                if verbose:
                    print("Embeddings generated successfully.")
            except Exception as e:
                print(f"\n⚠️  Failed to generate embeddings: {e}")
                print("The code index was created successfully.")
                print("To retry embeddings, run: cicada index --force --embeddings")

    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user.")
        # Handle interrupt during the initial, non-enrichment phase of indexing.
        # For Python, an interrupt during the external `scip-python` call means no index is saved.
        # Other indexers, like Elixir's, may save partial progress even at this stage.
        if language == "elixir":
            print("Partial index saved. Run again to continue indexing remaining files.")
        else:
            print("Run again to restart indexing.")
        sys.exit(130)


def _handle_index_config_update(
    config_path: Path,
    storage_dir: Path,
    repo_path: Path,
    indexing_mode: str,
) -> bool:
    """Handle config creation or update during forced indexing.

    This function is only called when --force is used, so it always
    updates the config to the specified indexing mode
    without validation. This allows users to change modes between indexing runs.

    Args:
        config_path: Path to config.yaml
        storage_dir: Storage directory path
        repo_path: Repository path
        indexing_mode: Indexing mode to use

    Returns:
        True if the mode was changed (requiring full reindex), False otherwise
    """
    from cicada.setup import create_config_yaml

    # Check if config exists and if mode has changed
    mode_changed = False
    if config_path.exists():
        # Load existing config to check for mode changes
        existing_mode = _load_existing_config(config_path)
        mode_changed = existing_mode != indexing_mode

    # When --force is used, always update config to the new mode settings
    # This allows changing modes without requiring a separate clean step
    create_config_yaml(repo_path, storage_dir, indexing_mode)

    return mode_changed


def _print_mode_requirement_error() -> None:
    """Print error message when no mode is specified."""
    print("Error: No indexing mode configured.", file=sys.stderr)
    print("\nUse '--force' with a mode flag to select indexing settings:", file=sys.stderr)
    print(
        "  cicada index --force --keywords   Keyword-based indexing (default)",
        file=sys.stderr,
    )
    print(
        "  cicada index --force --embeddings  Embeddings-based indexing with semantic search",
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
    from cicada.github.pr_indexer import PRIndexer
    from cicada.index_mode import INDEX_MODE_EMBEDDINGS
    from cicada.utils import get_config_path, get_pr_index_path
    from cicada.version_check import check_for_updates

    check_for_updates()

    try:
        repo_path = Path(args.repo).resolve()
        output_path = str(get_pr_index_path(args.repo))

        indexer = PRIndexer(repo_path=args.repo)
        pr_index = indexer.index_repository(output_path=output_path, incremental=not args.clean)

        print("\n✅ Indexing complete! You can now use the MCP tools for PR history lookups.")

        # Check if we should generate PR embeddings (embeddings mode enabled)
        config_path = get_config_path(repo_path)
        if config_path.exists():
            indexing_mode = _load_existing_config(config_path)
            if indexing_mode == INDEX_MODE_EMBEDDINGS and pr_index:
                print("\nGenerating PR embeddings for semantic search...")
                try:
                    from cicada.embeddings.indexer import EmbeddingsIndexer

                    embeddings_indexer = EmbeddingsIndexer(
                        repo_path, verbose=True, force=args.clean
                    )
                    embeddings_indexer.index_prs_from_pr_index(pr_index)
                    print("PR embeddings generated successfully.")
                except Exception as e:
                    print(f"\n⚠️  Failed to generate PR embeddings: {e}")
                    print("The PR index was created successfully.")
                    print("To retry PR embeddings, run: cicada index-pr --clean")

    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user.")
        print("Partial index may have been saved. Run again to continue (incremental by default).")
        sys.exit(130)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


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


def handle_status(args):
    """Show diagnostic information about Cicada configuration."""
    from cicada.status import check_repository

    repo_path = Path(args.repo).resolve()

    try:
        check_repository(repo_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_stats(args):
    """Show MCP tool usage statistics for the current project."""
    from cicada.stats import StatsAnalyzer

    repo_path = Path(args.repo).resolve()
    analyzer = StatsAnalyzer(repo_path)

    # Handle reset
    if args.reset:
        _handle_stats_reset(args, analyzer)
        return

    # Determine time filter
    days = None
    if args.last_7_days:
        days = 7
    elif args.last_30_days:
        days = 30

    # Get stats
    try:
        if args.time_series:
            granularity = "weekly" if args.weekly else "daily"
            stats = analyzer.get_stats(
                days=days,
                tool_filter=args.tool,
                time_series=True,
                granularity=granularity,
            )
        else:
            stats = analyzer.get_stats(days=days, tool_filter=args.tool)

        # Format output
        if args.format == "json":
            output = analyzer.format_json(stats)
        elif args.time_series:
            output = analyzer.format_time_series(stats)
        elif args.detailed:
            output = analyzer.format_detailed(stats)
        else:
            output = analyzer.format_summary(stats)

        print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _handle_stats_reset(args, analyzer):
    """Handle stats reset operation."""
    older_than = getattr(args, "older_than", None)
    force = getattr(args, "force", False)

    if older_than:
        message = f"Delete logs older than {older_than} days?"
        needs_confirmation = False
    else:
        message = "Delete ALL MCP tool logs for this project?"
        needs_confirmation = not force

    if needs_confirmation:
        print(message)
        print("This action cannot be undone.")
        response = input("Continue? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            print("Aborted.")
            sys.exit(0)

    count = analyzer.reset_stats(older_than_days=older_than)

    if older_than:
        print(f"✓ Deleted {count} log file(s) older than {older_than} days")
    else:
        print(f"✓ Deleted {count} log file(s)")


def handle_dir(args):
    """Show the absolute path to the Cicada storage directory."""
    import yaml

    from cicada.utils.storage import get_storage_dir

    repo_path = Path(args.repo).resolve()

    try:
        storage_dir = get_storage_dir(repo_path)
        link_path = storage_dir / "link.yaml"

        # Check if the repository is linked
        if link_path.exists():
            with open(link_path) as f:
                link_info = yaml.safe_load(f)

            source_storage_dir = Path(link_info.get("source_storage_dir", "unknown"))
            print(f"Storage directory: {storage_dir}")
            print(f"Linked to: {link_info.get('source_repo_path', 'N/A')}")
            print(f"Resolved storage: {source_storage_dir}")
        else:
            print(str(storage_dir))
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, OSError) as e:
        print(f"Error reading link file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_link(args):
    """Link target repository to source repository's index."""
    from cicada.utils.storage import create_link, get_link_info

    target_path = Path(args.target).resolve()
    source_path = Path(args.source).resolve()

    try:
        # Create the link
        create_link(target_path, source_path)

        # Show success message with link info
        link_info = get_link_info(target_path)
        if link_info:
            print(f"✓ Successfully linked {target_path}")
            print(f"  → Source: {link_info.get('source_repo_path', 'unknown')}")
            print(f"  → Storage: {link_info.get('source_storage_dir', 'unknown')}")
            print()
            print("The target repository will now use the source repository's index.")
            print("Run 'cicada unlink' to remove this link.")
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_unlink(args):
    """Remove link from repository."""
    from cicada.utils.storage import get_link_info, is_linked, remove_link

    repo_path = Path(args.repo).resolve()

    try:
        # Check if linked
        if not is_linked(repo_path):
            print(f"Repository is not linked: {repo_path}")
            print("Nothing to do.")
            sys.exit(0)

        # Get link info before removing
        link_info = get_link_info(repo_path)
        source_repo = link_info.get("source_repo_path", "unknown") if link_info else "unknown"

        # Remove the link
        if remove_link(repo_path):
            print(f"✓ Successfully unlinked {repo_path}")
            print(f"  Previously linked to: {source_repo}")
            print()
            print("The repository can now have its own index.")
            print("Run 'cicada index' to create a new index for this repository.")
        else:
            print(f"Failed to remove link from {repo_path}")
            sys.exit(1)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_install(args) -> None:
    """
    Handle the install subcommand (interactive setup).

    Behavior:
    - INTERACTIVE: shows prompts and menus
    - Can skip prompts with flags (--claude, --cursor, --vs, --keywords, --embeddings)
    - Creates editor config and indexes repository
    """
    from typing import cast

    from cicada.setup import EditorType, setup
    from cicada.utils import get_config_path, get_index_path

    # Determine and validate repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    _validate_project_language(repo_path)

    # Handle --default flag: convert to --keywords
    if getattr(args, "default", False):
        args.keywords = True

    # Validate indexing mode flags
    validate_mode_flags(args)

    # Handle automation flags
    yes_mode = getattr(args, "yes", False)
    skip_optional = getattr(args, "skip_optional", False)
    force_index_prs = getattr(args, "index_prs", False)
    force_no_index_prs = getattr(args, "no_index_prs", False)

    # Parse editor selection
    editor = _determine_editor_from_args(args)

    indexing_mode = determine_indexing_mode(args, repo_path)

    # Check if index already exists
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    index_exists = config_path.exists() and index_path.exists()

    # Determine PR indexing preference based on flags
    # If explicitly set, it overrides everything
    # If yes_mode, defaults to True (unless skipped)
    # If skip_optional, defaults to False
    should_index_prs = None
    should_add_to_claude = None
    embeddings_config = None

    if force_index_prs:
        should_index_prs = True
    elif force_no_index_prs:
        should_index_prs = False
    elif skip_optional:
        should_index_prs = False
        should_add_to_claude = False
    elif yes_mode:
        should_index_prs = True
        should_add_to_claude = True

    # If no flags provided and no partial flags, use full interactive setup
    if (
        editor is None
        and not mode_flag_specified(args)
        and not yes_mode
        and should_index_prs is None
        and should_add_to_claude is None
    ):
        from cicada.interactive_setup import show_full_interactive_setup

        show_full_interactive_setup(repo_path)
        return

    # If only mode flags provided (no editor), prompt for editor
    if editor is None:
        editor = "claude" if yes_mode else _prompt_for_editor()

    # If only editor flag provided (no mode), prompt for mode (unless index exists)
    if not mode_flag_specified(args) and not index_exists:
        if yes_mode:
            # Default to keywords (handled by setup defaults if passed as None)
            pass
        else:
            from cicada.interactive_setup import show_first_time_setup

            (
                indexing_mode,
                interactive_index_prs,
                interactive_add_claude,
                interactive_embeddings_config,
            ) = show_first_time_setup(
                default_index_prs=should_index_prs,
                default_add_to_claude=should_add_to_claude,
            )

            # Use interactive choices if not overridden by flags
            # (If we passed defaults, interactive_* vars will match defaults)
            should_index_prs = interactive_index_prs
            should_add_to_claude = interactive_add_claude
            embeddings_config = interactive_embeddings_config

    # If index exists but no mode flags, use existing settings
    if not mode_flag_specified(args) and index_exists:
        indexing_mode = _load_existing_config(config_path)

    # Run setup
    assert editor is not None
    try:
        setup(
            cast(EditorType, editor),
            repo_path,
            indexing_mode=indexing_mode,
            index_exists=index_exists,
            index_prs=should_index_prs or False,
            add_to_claude_md=should_add_to_claude or False,
            embeddings_config=embeddings_config,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


def _validate_project_language(repo_path: Path) -> str:
    """Validate that the repository is a supported project type and return its language.

    Args:
        repo_path: Path to the repository

    Returns:
        The detected language (e.g., 'python', 'elixir', 'typescript')

    Raises:
        SystemExit: If not a supported project type
    """
    from cicada.setup import detect_project_language

    try:
        return detect_project_language(repo_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
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
    - Auto-setup if needed (uses keywords mode by default)
    - Creates editor configs if flags provided (--claude, --cursor, --vs)
    - Starts MCP server on stdio
    """
    import asyncio
    import logging

    from cicada.utils import create_storage_dir, get_config_path, get_index_path

    logger = logging.getLogger(__name__)

    # Determine and validate repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    _validate_project_language(repo_path)

    # Validate indexing mode flags
    validate_mode_flags(args)

    indexing_mode = determine_indexing_mode(args, repo_path)
    from cicada.index_mode import ensure_supported_mode

    ensure_supported_mode(indexing_mode)

    # Create storage directory
    storage_dir = create_storage_dir(repo_path)

    # Check if setup is needed
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    needs_setup = not (config_path.exists() and index_path.exists())

    if needs_setup:
        _perform_silent_setup(repo_path, storage_dir, indexing_mode)

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
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C, suppress traceback
        pass
    finally:
        # Ensure watch process is stopped when server exits
        if watch_enabled:
            _cleanup_watch_process(logger)


def _perform_silent_setup(repo_path: Path, storage_dir: Path, indexing_mode: str) -> None:
    """Perform silent setup with defaults if needed.

    Args:
        repo_path: Repository path
        storage_dir: Storage directory path
        indexing_mode: Indexing mode to use
    """
    from cicada.index_mode import ensure_supported_mode
    from cicada.setup import create_config_yaml, detect_project_language, index_repository

    # Detect project language
    language = detect_project_language(repo_path)

    ensure_supported_mode(indexing_mode)

    # Create config.yaml (silent)
    create_config_yaml(repo_path, storage_dir, indexing_mode, verbose=False)

    # Index repository (silent)
    try:
        index_repository(repo_path, language, force_full=False, verbose=False)
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

    # Determine mode using helper
    indexing_mode = determine_indexing_mode(args, repo_path)
    from cicada.index_mode import ensure_supported_mode

    ensure_supported_mode(indexing_mode)

    # Start the watch process
    try:
        if not start_watch_process(
            repo_path, indexing_mode=indexing_mode, debounce=DEFAULT_WATCH_DEBOUNCE
        ):
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


def handle_agents(args) -> None:
    """Handle agents command routing.

    Args:
        args: Parsed command-line arguments
    """
    if args.agents_command == "install":
        handle_agents_install()


def handle_agents_install() -> None:
    """Install Cicada agents to ./.claude/."""
    from pathlib import Path

    from cicada.agents.installer import install_agent

    install_path = Path.cwd() / ".claude"
    agent_name = "cicada-code-explorer.md"

    print(f"\nInstalling Cicada agent: {install_path}\n")

    install_agent(install_path, agent_name)

    print(f"  ✓ Installed {agent_name}")
    print("\n✓ Installation complete!")
    print("\nNext steps:")
    print("  1. Restart Claude Code to load the new agent")
    print("  2. Use agent via: Task tool → select cicada-code-explorer")


def handle_run(args) -> None:
    """Execute MCP tools from CLI.

    Args:
        args: Parsed command-line arguments including tool name and tool-specific args
    """
    import asyncio

    from cicada.cli_mapper import parse_cli_args_to_handler_kwargs
    from cicada.mcp.config_manager import ConfigManager
    from cicada.mcp.router import create_tool_router

    # Get tool name (convert kebab-case to snake_case for handler lookup)
    tool_name = args.tool.replace("-", "_")

    # Parse CLI args to handler kwargs
    try:
        kwargs = parse_cli_args_to_handler_kwargs(args, tool_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Load config using ConfigManager (handles env vars, links, etc.)
    try:
        config_path = ConfigManager.get_config_path()
        config = ConfigManager.load_config(config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create router using shared factory (matches server.py setup)
    router, _, _ = create_tool_router(config)

    # Execute via router
    async def run_tool():
        result = await router.route_tool(tool_name, kwargs)
        return result

    try:
        result = asyncio.run(run_tool())
        # Print result (router returns list of TextContent)
        if result:
            for content in result:
                print(content.text)
    except Exception as e:
        import traceback

        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
