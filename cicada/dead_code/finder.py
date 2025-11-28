"""
CLI tool for finding dead code (unused public functions) in Elixir codebases.

Analyzes the indexed codebase to identify potentially unused public functions
with confidence levels based on usage patterns.

Author: Cursor(Auto)
"""

import argparse
import json
import sys
from collections.abc import Callable

from cicada.utils import get_index_path, load_index

from .analyzer import DeadCodeAnalyzer

# Default maximum number of results to show per confidence tier in markdown format.
# Total output can be up to 3x this value (one for each tier: high/medium/low).
# Use --format json for complete results or filter by --min-confidence.
DEFAULT_MAX_RESULTS_PER_TIER = 50


def _format_tier(
    tier_name: str,
    tier_label: str,
    description: str,
    candidates_list: list,
    max_results: int,
    format_module_details: Callable[[list[str], list], None] | None = None,
) -> list[str]:
    """
    Format a confidence tier section with candidates.

    Args:
        tier_name: Name of the tier (e.g., "high", "medium", "low")
        tier_label: Display label for the tier header
        description: Description of what this tier means
        candidates_list: List of candidate functions for this tier
        max_results: Maximum number of results to show
        format_module_details: Optional callback to format tier-specific module details.
                              Called with (lines, funcs) and should append to lines.

    Returns:
        List of formatted lines for this tier
    """
    if not candidates_list:
        return []

    lines = []
    count = len(candidates_list)

    # Markdown header (replaces ASCII box-drawing)
    lines.append(f"\n## {tier_label} ({count} function{'s' if count != 1 else ''})")
    lines.append(f"{description}\n")

    # Truncate if needed
    candidates_to_show = candidates_list[:max_results]
    truncated = len(candidates_list) > max_results

    # Group by module using setdefault
    by_module: dict[str, list] = {}
    for candidate in candidates_to_show:
        by_module.setdefault(candidate["module"], []).append(candidate)

    # Format each module
    for module, funcs in sorted(by_module.items()):
        lines.append(f"### {module}")
        lines.append(f"{funcs[0]['file']}")

        # Call tier-specific formatting callback if provided
        if format_module_details:
            format_module_details(lines, funcs)

        lines.append("")

        # List functions with call counts
        for func in funcs:
            reason = func.get("reason", "no_usage_found")
            if reason == "module_passed_as_value":
                call_info = "(0 calls, module passed as value)"
            elif reason == "module_has_behaviors_or_uses":
                call_info = "(0 calls, has behaviors/uses)"
            else:
                call_info = "(0 calls)"
            lines.append(f"- `{func['function']}/{func['arity']}` :{func['line']} {call_info}")
        lines.append("")

    # Truncation message
    if truncated:
        remaining = len(candidates_list) - max_results
        candidate_word = "candidate" if remaining == 1 else "candidates"
        lines.append(
            f"*... and {remaining} more {tier_name} confidence {candidate_word} (truncated for readability)*\n"
        )
        lines.append("*Tip: Use JSON format or filter results for complete output*\n")

    return lines


def format_markdown(results: dict, max_results_per_tier: int = DEFAULT_MAX_RESULTS_PER_TIER) -> str:
    """
    Format analysis results as markdown.

    Args:
        results: Analysis results from DeadCodeAnalyzer
        max_results_per_tier: Maximum number of results to show per confidence tier.
                              Defaults to DEFAULT_MAX_RESULTS_PER_TIER (50).
                              Note: Total output can show up to 3x this value
                              (50 high + 50 medium + 50 low = 150 total).
                              Use JSON format for complete untruncated results.

    Returns:
        Formatted markdown string with truncation applied if needed
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

    # Define tier-specific detail formatters
    def format_medium_details(lines: list[str], funcs: list) -> None:
        """Format behaviors/uses for medium confidence tier."""
        behaviours = funcs[0].get("behaviours", [])
        uses = funcs[0].get("uses", [])
        if behaviours:
            lines.append(f"**Behaviours:** {', '.join(behaviours)}")
        if uses:
            lines.append(f"**Uses:** {', '.join(uses)}")

    def format_low_details(lines: list[str], funcs: list) -> None:
        """Format mentioned_in for low confidence tier."""
        mentioned_in = funcs[0].get("mentioned_in", [])
        if mentioned_in:
            lines.append("**Module mentioned as value in:**")
            for mention in mentioned_in:
                lines.append(f"- {mention['module']} ({mention['file']})")

    # Format each tier
    lines.extend(
        _format_tier(
            tier_name="high",
            tier_label="HIGH CONFIDENCE",
            description="Functions with zero usage in codebase",
            candidates_list=candidates["high"],
            max_results=max_results_per_tier,
        )
    )

    lines.extend(
        _format_tier(
            tier_name="medium",
            tier_label="MEDIUM CONFIDENCE",
            description="Functions with zero usage, but module has behaviors/uses (possible callbacks)",
            candidates_list=candidates["medium"],
            max_results=max_results_per_tier,
            format_module_details=format_medium_details,
        )
    )

    lines.extend(
        _format_tier(
            tier_name="low",
            tier_label="LOW CONFIDENCE",
            description="Functions with zero usage, but module passed as value (possible dynamic calls)",
            candidates_list=candidates["low"],
            max_results=max_results_per_tier,
            format_module_details=format_low_details,
        )
    )

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
    """Filter results by confidence level."""
    if min_confidence == "low":
        return results

    levels_to_clear = {"high": ["medium", "low"], "medium": ["low"]}
    for level in levels_to_clear.get(min_confidence, []):
        results["candidates"][level] = []

    results["summary"]["total_candidates"] = sum(len(v) for v in results["candidates"].values())
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
