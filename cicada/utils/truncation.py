"""
Utilities for automatically truncating long outputs to prevent token explosion.

This module provides intelligent truncation for various data types commonly
returned by Cicada's MCP tools, including line numbers, call sites, code blocks,
and text. Truncation is automatically applied when content exceeds conservative
thresholds, with inline indicators showing how much was truncated.
"""

from typing import Any, TypeVar

T = TypeVar("T")


class TruncationHelper:
    """Helper class for truncating various types of content."""

    # Conservative thresholds for automatic truncation
    DEFAULT_LINE_NUMBER_THRESHOLD = 30
    DEFAULT_CALL_SITE_THRESHOLD = 20
    DEFAULT_CODE_LINE_THRESHOLD = 50
    DEFAULT_TEXT_THRESHOLD = 300
    DEFAULT_LIST_THRESHOLD = 50

    @staticmethod
    def should_truncate(items: list[T], threshold: int) -> bool:
        """Check if a list should be truncated based on threshold.

        Args:
            items: List to check
            threshold: Maximum number of items before truncation

        Returns:
            True if items should be truncated, False otherwise
        """
        return len(items) > threshold

    @staticmethod
    def truncate_line_numbers(lines: list[int], threshold: int | None = None) -> str:
        """Truncate a list of line numbers with inline indicator.

        Args:
            lines: List of line numbers to format
            threshold: Maximum number of lines to show (default: 30)

        Returns:
            Formatted string like ":10, :15, :20 ... (47 more)"

        Examples:
            >>> truncate_line_numbers([10, 15, 20])
            ":10, :15, :20"
            >>> truncate_line_numbers(list(range(1, 100)))
            ":1, :2, :3, ... (69 more)"
        """
        if threshold is None:
            threshold = TruncationHelper.DEFAULT_LINE_NUMBER_THRESHOLD

        if not lines:
            return ""

        sorted_lines = sorted(lines)

        if not TruncationHelper.should_truncate(sorted_lines, threshold):
            return ", ".join(f":{line}" for line in sorted_lines)

        # Show first 'threshold' items with truncation indicator
        shown = sorted_lines[:threshold]
        remaining = len(sorted_lines) - threshold
        line_str = ", ".join(f":{line}" for line in shown)
        return f"{line_str} ... ({remaining} more)"

    @staticmethod
    def truncate_list(items: list[T], threshold: int | None = None) -> tuple[list[T], str | None]:
        """Truncate a generic list and return truncated items plus indicator.

        Args:
            items: List to truncate
            threshold: Maximum items to return (default: 50)

        Returns:
            Tuple of (truncated_items, truncation_message)
            truncation_message is None if no truncation occurred

        Examples:
            >>> truncate_list([1, 2, 3], threshold=5)
            ([1, 2, 3], None)
            >>> truncate_list(list(range(100)), threshold=20)
            ([0, 1, 2, ...], "... (80 more)")
        """
        if threshold is None:
            threshold = TruncationHelper.DEFAULT_LIST_THRESHOLD

        if not TruncationHelper.should_truncate(items, threshold):
            return items, None

        truncated = items[:threshold]
        remaining = len(items) - threshold
        message = f"... ({remaining} more)"
        return truncated, message

    @staticmethod
    def truncate_call_sites(
        call_sites: list[dict[str, Any]], threshold: int | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Truncate a list of call site dictionaries.

        Args:
            call_sites: List of call site dicts with keys like 'calling_module', 'line', etc.
            threshold: Maximum call sites to return (default: 20)

        Returns:
            Tuple of (truncated_sites, truncation_message)

        Examples:
            >>> sites = [{"line": 10}, {"line": 20}]
            >>> truncate_call_sites(sites, threshold=5)
            ([{"line": 10}, {"line": 20}], None)
        """
        if threshold is None:
            threshold = TruncationHelper.DEFAULT_CALL_SITE_THRESHOLD

        return TruncationHelper.truncate_list(call_sites, threshold)

    @staticmethod
    def truncate_code_block(
        lines: list[str], threshold: int | None = None, context_lines: int = 5
    ) -> tuple[list[str], str | None]:
        """Truncate a code block intelligently by showing head and tail.

        Args:
            lines: List of code lines
            threshold: Maximum total lines to show (default: 50)
            context_lines: Number of lines to show from start and end (default: 5)

        Returns:
            Tuple of (truncated_lines, truncation_message)
            If truncated, returns first N and last N lines with indicator in between

        Examples:
            >>> lines = ["line1", "line2", "line3"]
            >>> truncate_code_block(lines, threshold=10)
            (["line1", "line2", "line3"], None)
            >>> truncate_code_block(["line" + str(i) for i in range(100)], threshold=20)
            (["line0", ..., "... (80 lines omitted)", ..., "line99"], "... (80 lines omitted)")
        """
        if threshold is None:
            threshold = TruncationHelper.DEFAULT_CODE_LINE_THRESHOLD

        if not TruncationHelper.should_truncate(lines, threshold):
            return lines, None

        # Show first and last 'context_lines'
        head = lines[:context_lines]
        tail = lines[-context_lines:]
        omitted_count = len(lines) - (2 * context_lines)

        message = f"... ({omitted_count} lines omitted)"
        truncated = head + [f"\n{message}\n"] + tail

        return truncated, message

    @staticmethod
    def truncate_text(text: str, threshold: int | None = None, suffix: str = "...") -> str:
        """Truncate text to a maximum length.

        Args:
            text: Text to truncate
            threshold: Maximum characters (default: 300)
            suffix: Suffix to append if truncated (default: "...")

        Returns:
            Truncated text with suffix if applicable

        Examples:
            >>> truncate_text("short", threshold=100)
            "short"
            >>> truncate_text("a" * 500, threshold=10)
            "aaaaaaaaaa..."
        """
        if threshold is None:
            threshold = TruncationHelper.DEFAULT_TEXT_THRESHOLD

        if len(text) <= threshold:
            return text

        return text[:threshold] + suffix

    @staticmethod
    def format_truncated_dict_list(
        items: list[dict[str, Any]],
        key_to_display: str,
        threshold: int | None = None,
    ) -> str:
        """Format a list of dictionaries with truncation.

        Args:
            items: List of dictionaries
            key_to_display: Key to extract and display from each dict
            threshold: Maximum items to show (default: 50)

        Returns:
            Formatted string with truncation indicator if needed

        Examples:
            >>> items = [{"name": "foo"}, {"name": "bar"}]
            >>> format_truncated_dict_list(items, "name", threshold=5)
            "foo, bar"
            >>> items = [{"name": f"item{i}"} for i in range(100)]
            >>> format_truncated_dict_list(items, "name", threshold=20)
            "item0, item1, ..., item19 ... (80 more)"
        """
        if threshold is None:
            threshold = TruncationHelper.DEFAULT_LIST_THRESHOLD

        if not items:
            return ""

        if not TruncationHelper.should_truncate(items, threshold):
            return ", ".join(str(item.get(key_to_display, "")) for item in items)

        shown_items = items[:threshold]
        remaining = len(items) - threshold
        items_str = ", ".join(str(item.get(key_to_display, "")) for item in shown_items)
        return f"{items_str} ... ({remaining} more)"
