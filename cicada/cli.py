"""
Unified CLI entry point for Cicada.

Provides a single `cicada` command with multiple subcommands:
- cicada [path]           - Setup/install Cicada for a project
- cicada index            - Index an Elixir repository
- cicada index-pr         - Index GitHub pull requests
- cicada find-dead-code   - Find potentially unused functions
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
        help="Repository path for setup, or subcommand (index, index-pr, find-dead-code)",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

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
        help="Use NLP keyword extraction (spaCy-based)",
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

    # Parse arguments
    args = parser.parse_args()

    # Handle the case where path_or_command might be a subcommand
    # This handles backward compatibility where someone might run "cicada index"
    # without using proper subparsers
    if args.command is None and args.path_or_command in [
        "index",
        "index-pr",
        "find-dead-code",
    ]:
        # User typed "cicada index" etc. - show help for that subcommand
        parser.parse_args([args.path_or_command, "--help"])
        return

    # Route to appropriate handler
    if args.command == "index":
        handle_index(args)
    elif args.command == "index-pr":
        handle_index_pr(args)
    elif args.command == "find-dead-code":
        handle_find_dead_code(args)
    else:
        # No subcommand - default to install behavior
        handle_install(args)


def handle_install(args):
    """Handle the install/setup command."""
    from cicada.install import main as install_main

    # Construct arguments for install.main()
    # If path_or_command was provided, use it as the repo path
    if args.path_or_command:
        sys.argv = ["cicada", args.path_or_command]
    else:
        sys.argv = ["cicada"]

    install_main()


def handle_index(args):
    """Handle the index subcommand."""
    from cicada.indexer import ElixirIndexer
    from cicada.interactive_setup import show_first_time_setup
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

    # Check if no extraction flags provided - trigger interactive setup
    if not args.nlp and not args.rag:
        print("No keyword extraction method specified. Starting interactive setup...\n")
        keyword_method, model_tier = show_first_time_setup()
    else:
        # Determine model tier from flags
        if args.fast:
            model_tier = "fast"
        elif args.max:
            model_tier = "max"
        else:
            model_tier = "regular"

        # Determine keyword method
        keyword_method = "bert" if args.rag else "spacy"

    indexer = ElixirIndexer()
    indexer.index_repository(
        args.repo,
        args.output,
        extract_keywords=True,
        keyword_method=keyword_method,
        model_tier=model_tier,
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


if __name__ == "__main__":
    main()
