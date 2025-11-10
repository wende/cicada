"""CLI entry point for the PR indexer."""

import sys

from .indexer import PRIndexer


def main():
    """CLI entry point for pr_indexer."""
    import argparse

    from cicada.version_check import check_for_updates

    # Check for updates (non-blocking, fails silently)
    check_for_updates()

    parser = argparse.ArgumentParser(
        description="Index GitHub pull requests for fast offline lookup"
    )
    _ = parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to git repository (default: current directory)",
    )
    _ = parser.add_argument(
        "--output",
        default=".cicada/pr_index.json",
        help="Output path for the index file (default: .cicada/pr_index.json)",
    )
    _ = parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean and rebuild the entire index from scratch (default: incremental update)",
    )

    args = parser.parse_args()

    try:
        indexer = PRIndexer(repo_path=args.repo)
        # Incremental by default, unless --clean is specified
        _ = indexer.index_repository(output_path=args.output, incremental=not args.clean)

        print("\nIndexing complete! You can now use the MCP tools for PR history lookups.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Indexing interrupted by user.")
        print("Partial index may have been saved. Run again to continue (incremental by default).")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
