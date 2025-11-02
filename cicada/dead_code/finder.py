"""
CLI tool for finding dead code (unused public functions) in Elixir codebases.

Analyzes the indexed codebase to identify potentially unused public functions
with confidence levels based on usage patterns.

Author: Cursor(Auto)
"""

import argparse
import json
import sys

from cicada.utils import get_index_path, load_index

from .analyzer import DeadCodeAnalyzer


def format_markdown(results: dict) -> str:
    """
    Format analysis results as markdown.

    Args:
        results: Analysis results from DeadCodeAnalyzer

    Returns:
        Formatted markdown string
    """
    lines = ["# Dead Code Analysis\n"]

    summary = results["summary"]
    lines.append(
        f"Analyzed {summary['analyzed']} public functions "
        f"(skipped {summary['skipped_impl']} with @impl, "
        f"{summary['skipped_files']} in test/script files)"
    )
    lines.append(f"Found **{summary['total_candidates']} potentially unused functions**\n")

    candidates = results["candidates"]

    # High confidence
    if candidates["high"]:
        count = len(candidates["high"])
        label = f" HIGH CONFIDENCE ({count} function{'s' if count != 1 else ''}) "
        bar_length = 80
        padding = (bar_length - len(label)) // 2
        lines.append(f"\n{'═' * padding}{label}{'═' * (bar_length - padding - len(label))}")
        lines.append("Functions with zero usage in codebase\n")

        # Group by module
        by_module = {}
        for c in candidates["high"]:
            if c["module"] not in by_module:
                by_module[c["module"]] = []
            by_module[c["module"]].append(c)

        for module, funcs in sorted(by_module.items()):
            lines.append(f"### {module}")
            lines.append(f"{funcs[0]['file']}\n")
            for func in funcs:
                lines.append(f"- `{func['function']}/{func['arity']}` (line {func['line']})")
            lines.append("")

    # Medium confidence
    if candidates["medium"]:
        count = len(candidates["medium"])
        label = f" MEDIUM CONFIDENCE ({count} function{'s' if count != 1 else ''}) "
        bar_length = 80
        padding = (bar_length - len(label)) // 2
        lines.append(f"\n{'═' * padding}{label}{'═' * (bar_length - padding - len(label))}")
        lines.append(
            "Functions with zero usage, but module has behaviors/uses (possible callbacks)\n"
        )

        # Group by module
        by_module = {}
        for c in candidates["medium"]:
            if c["module"] not in by_module:
                by_module[c["module"]] = []
            by_module[c["module"]].append(c)

        for module, funcs in sorted(by_module.items()):
            lines.append(f"### {module}")
            lines.append(f"{funcs[0]['file']}")

            # Show behaviors/uses
            behaviours = funcs[0].get("behaviours", [])
            uses = funcs[0].get("uses", [])
            if behaviours:
                lines.append(f"**Behaviours:** {', '.join(behaviours)}")
            if uses:
                lines.append(f"**Uses:** {', '.join(uses)}")
            lines.append("")

            for func in funcs:
                lines.append(f"- `{func['function']}/{func['arity']}` (line {func['line']})")
            lines.append("")

    # Low confidence
    if candidates["low"]:
        count = len(candidates["low"])
        label = f" LOW CONFIDENCE ({count} function{'s' if count != 1 else ''}) "
        bar_length = 80
        padding = (bar_length - len(label)) // 2
        lines.append(f"\n{'═' * padding}{label}{'═' * (bar_length - padding - len(label))}")
        lines.append(
            "Functions with zero usage, but module passed as value (possible dynamic calls)\n"
        )

        # Group by module
        by_module = {}
        for c in candidates["low"]:
            if c["module"] not in by_module:
                by_module[c["module"]] = []
            by_module[c["module"]].append(c)

        for module, funcs in sorted(by_module.items()):
            lines.append(f"### {module}")
            lines.append(f"{funcs[0]['file']}")

            # Show where module is mentioned as value
            mentioned_in = funcs[0].get("mentioned_in", [])
            if mentioned_in:
                lines.append("**Module mentioned as value in:**")
                for mention in mentioned_in:
                    lines.append(f"- {mention['module']} ({mention['file']})")
            lines.append("")

            for func in funcs:
                lines.append(f"- `{func['function']}/{func['arity']}` (line {func['line']})")
            lines.append("")

    if summary["total_candidates"] == 0:
        lines.append("\n*No dead code candidates found!*\n")

    return "\n".join(lines)


def format_json(results: dict) -> str:
    """
    Format analysis results as JSON.

    Args:
        results: Analysis results from DeadCodeAnalyzer

    Returns:
        JSON string
    """
    return json.dumps(results, indent=2)


def filter_by_confidence(results: dict, min_confidence: str) -> dict:
    """
    Filter results to only show candidates at or above minimum confidence level.

    Args:
        results: Analysis results
        min_confidence: Minimum confidence level ("high", "medium", or "low")

    Returns:
        Filtered results
    """
    if min_confidence == "low":
        # Show all
        return results
    elif min_confidence == "medium":
        # Show only medium and high
        results["candidates"]["low"] = []
    else:  # high
        # Show only high
        results["candidates"]["medium"] = []
        results["candidates"]["low"] = []

    # Recalculate total
    results["summary"]["total_candidates"] = sum(
        len(results["candidates"][level]) for level in ["high", "medium", "low"]
    )

    return results


def main():
    """Main entry point for the dead code finder CLI."""
    parser = argparse.ArgumentParser(
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

    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--min-confidence",
        choices=["high", "medium", "low"],
        default="high",
        help="Minimum confidence level to show (default: high)",
    )

    args = parser.parse_args()

    # Load index from centralized storage
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

    if index is None:
        print(f"Error: Could not load index from {index_path}", file=sys.stderr)
        sys.exit(1)

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
