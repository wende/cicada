"""
Unit tests for truncation utilities.

Tests cover all truncation methods with edge cases, different data types,
and performance considerations.
"""

from cicada.utils.truncation import TruncationHelper


class TestShouldTruncate:
    """Test the should_truncate helper method."""

    def test_empty_list(self):
        """Test with empty list."""
        assert not TruncationHelper.should_truncate([], 10)

    def test_single_item(self):
        """Test with single item."""
        assert not TruncationHelper.should_truncate([1], 10)

    def test_at_threshold(self):
        """Test with exactly threshold items."""
        assert not TruncationHelper.should_truncate([1] * 10, 10)

    def test_over_threshold(self):
        """Test with items over threshold."""
        assert TruncationHelper.should_truncate([1] * 11, 10)

    def test_large_list(self):
        """Test with large list."""
        assert TruncationHelper.should_truncate(list(range(1000)), 100)


class TestTruncateLineNumbers:
    """Test line number truncation."""

    def test_empty_list(self):
        """Test with no line numbers."""
        result = TruncationHelper.truncate_line_numbers([])
        assert result == ""

    def test_single_line(self):
        """Test with single line number."""
        result = TruncationHelper.truncate_line_numbers([42])
        assert result == ":42"

    def test_few_lines(self):
        """Test with few line numbers (under threshold)."""
        result = TruncationHelper.truncate_line_numbers([10, 20, 30])
        assert result == ":10, :20, :30"

    def test_unsorted_lines(self):
        """Test that line numbers are sorted."""
        result = TruncationHelper.truncate_line_numbers([30, 10, 20])
        assert result == ":10, :20, :30"

    def test_at_threshold(self):
        """Test with exactly threshold lines."""
        lines = list(range(1, 31))  # 30 lines
        result = TruncationHelper.truncate_line_numbers(lines, threshold=30)
        expected = ", ".join(f":{i}" for i in lines)
        assert result == expected

    def test_over_threshold(self):
        """Test with lines over threshold."""
        lines = list(range(1, 51))  # 50 lines
        result = TruncationHelper.truncate_line_numbers(lines, threshold=30)
        assert "... (20 more)" in result
        assert result.startswith(":1, :2, :3")
        assert ":30" in result
        assert ":31" not in result

    def test_large_line_numbers(self):
        """Test with large line numbers."""
        lines = [1000, 2000, 3000]
        result = TruncationHelper.truncate_line_numbers(lines)
        assert result == ":1000, :2000, :3000"

    def test_custom_threshold(self):
        """Test with custom threshold."""
        lines = list(range(1, 21))  # 20 lines
        result = TruncationHelper.truncate_line_numbers(lines, threshold=5)
        assert "... (15 more)" in result
        assert ":1" in result
        assert ":5" in result
        assert ":6" not in result


class TestTruncateList:
    """Test generic list truncation."""

    def test_empty_list(self):
        """Test with empty list."""
        items, msg = TruncationHelper.truncate_list([])
        assert items == []
        assert msg is None

    def test_single_item(self):
        """Test with single item."""
        items, msg = TruncationHelper.truncate_list([1])
        assert items == [1]
        assert msg is None

    def test_under_threshold(self):
        """Test with items under threshold."""
        items, msg = TruncationHelper.truncate_list([1, 2, 3], threshold=10)
        assert items == [1, 2, 3]
        assert msg is None

    def test_at_threshold(self):
        """Test with exactly threshold items."""
        items, msg = TruncationHelper.truncate_list(list(range(10)), threshold=10)
        assert items == list(range(10))
        assert msg is None

    def test_over_threshold(self):
        """Test with items over threshold."""
        items, msg = TruncationHelper.truncate_list(list(range(100)), threshold=20)
        assert len(items) == 20
        assert items == list(range(20))
        assert msg == "... (80 more)"

    def test_string_items(self):
        """Test with string items."""
        strings = [f"item{i}" for i in range(100)]
        items, msg = TruncationHelper.truncate_list(strings, threshold=10)
        assert len(items) == 10
        assert items[0] == "item0"
        assert items[9] == "item9"
        assert msg == "... (90 more)"

    def test_dict_items(self):
        """Test with dictionary items."""
        dicts = [{"id": i, "value": f"val{i}"} for i in range(50)]
        items, msg = TruncationHelper.truncate_list(dicts, threshold=20)
        assert len(items) == 20
        assert items[0] == {"id": 0, "value": "val0"}
        assert msg == "... (30 more)"

    def test_preserves_order(self):
        """Test that list order is preserved."""
        items, msg = TruncationHelper.truncate_list([5, 4, 3, 2, 1], threshold=3)
        assert items == [5, 4, 3]
        assert msg == "... (2 more)"


class TestTruncateCallSites:
    """Test call site truncation."""

    def test_empty_list(self):
        """Test with no call sites."""
        sites, msg = TruncationHelper.truncate_call_sites([])
        assert sites == []
        assert msg is None

    def test_few_call_sites(self):
        """Test with few call sites (under threshold)."""
        sites = [
            {"calling_module": "Foo", "line": 10},
            {"calling_module": "Bar", "line": 20},
        ]
        result, msg = TruncationHelper.truncate_call_sites(sites)
        assert result == sites
        assert msg is None

    def test_many_call_sites(self):
        """Test with many call sites (over threshold)."""
        sites = [{"calling_module": f"Module{i}", "line": i} for i in range(50)]
        result, msg = TruncationHelper.truncate_call_sites(sites, threshold=20)
        assert len(result) == 20
        assert msg == "... (30 more)"

    def test_at_threshold(self):
        """Test with exactly threshold call sites."""
        sites = [{"calling_module": f"Module{i}", "line": i} for i in range(20)]
        result, msg = TruncationHelper.truncate_call_sites(sites, threshold=20)
        assert result == sites
        assert msg is None


class TestTruncateCodeBlock:
    """Test code block truncation."""

    def test_empty_code_block(self):
        """Test with no code lines."""
        lines, msg = TruncationHelper.truncate_code_block([])
        assert lines == []
        assert msg is None

    def test_single_line(self):
        """Test with single line."""
        lines, msg = TruncationHelper.truncate_code_block(["def foo():"])
        assert lines == ["def foo():"]
        assert msg is None

    def test_few_lines(self):
        """Test with few lines (under threshold)."""
        code = ["def foo():", "    return 42", ""]
        lines, msg = TruncationHelper.truncate_code_block(code)
        assert lines == code
        assert msg is None

    def test_at_threshold(self):
        """Test with exactly threshold lines."""
        code = [f"line {i}" for i in range(50)]
        lines, msg = TruncationHelper.truncate_code_block(code, threshold=50)
        assert lines == code
        assert msg is None

    def test_over_threshold(self):
        """Test with lines over threshold."""
        code = [f"line {i}" for i in range(100)]
        lines, msg = TruncationHelper.truncate_code_block(code, threshold=50, context_lines=5)
        # Should have first 5 + message + last 5 = 11 items
        assert len(lines) == 11
        assert lines[0] == "line 0"
        assert lines[4] == "line 4"
        assert "90 lines omitted" in lines[5]
        assert lines[6] == "line 95"
        assert lines[10] == "line 99"
        assert msg == "... (90 lines omitted)"

    def test_preserves_indentation(self):
        """Test that indentation is preserved."""
        code = ["def foo():", "    x = 1"] + [f"    line {i}" for i in range(100)]
        lines, msg = TruncationHelper.truncate_code_block(code, threshold=20, context_lines=3)
        # Check first line preserved
        assert lines[0] == "def foo():"
        # Check indentation in head
        assert lines[1] == "    x = 1"
        # Check indentation in tail
        assert lines[-1].startswith("    ")

    def test_unicode_content(self):
        """Test with unicode characters."""
        code = ["# 日本語", "# Ελληνικά", "# العربية"] + [f"line {i}" for i in range(100)]
        lines, msg = TruncationHelper.truncate_code_block(code, threshold=20, context_lines=3)
        assert "# 日本語" in lines
        assert msg is not None


class TestTruncateText:
    """Test text truncation."""

    def test_empty_string(self):
        """Test with empty string."""
        result = TruncationHelper.truncate_text("")
        assert result == ""

    def test_short_string(self):
        """Test with short string (under threshold)."""
        text = "This is a short string"
        result = TruncationHelper.truncate_text(text)
        assert result == text

    def test_at_threshold(self):
        """Test with exactly threshold characters."""
        text = "a" * 300
        result = TruncationHelper.truncate_text(text, threshold=300)
        assert result == text

    def test_over_threshold(self):
        """Test with text over threshold."""
        text = "a" * 500
        result = TruncationHelper.truncate_text(text, threshold=300)
        assert len(result) == 303  # 300 + "..."
        assert result.startswith("aaa")
        assert result.endswith("...")

    def test_multiline_text(self):
        """Test with multiline text."""
        text = "Line 1\n" * 50
        result = TruncationHelper.truncate_text(text, threshold=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_custom_suffix(self):
        """Test with custom suffix."""
        text = "a" * 500
        result = TruncationHelper.truncate_text(text, threshold=100, suffix=" [truncated]")
        assert result.endswith(" [truncated]")
        assert len(result) == 112  # 100 + " [truncated]" (12 chars)

    def test_unicode_text(self):
        """Test with unicode characters."""
        text = "日本語" * 100
        result = TruncationHelper.truncate_text(text, threshold=50)
        assert result.endswith("...")
        assert len(result) <= 53  # 50 + "..."

    def test_long_commit_message(self):
        """Test with realistic long commit message."""
        message = """Add comprehensive feature X

This commit introduces a major new feature that does the following:
- Implements new API endpoints
- Adds database migrations
- Updates the UI
- Adds comprehensive tests
- Updates documentation
- Fixes several bugs
- Improves performance
- Adds caching
- Updates dependencies
- And much more..."""
        result = TruncationHelper.truncate_text(message, threshold=300)
        assert len(result) <= 303
        assert result.endswith("...")


class TestFormatTruncatedDictList:
    """Test dictionary list formatting with truncation."""

    def test_empty_list(self):
        """Test with empty list."""
        result = TruncationHelper.format_truncated_dict_list([], "name")
        assert result == ""

    def test_single_item(self):
        """Test with single item."""
        items = [{"name": "foo"}]
        result = TruncationHelper.format_truncated_dict_list(items, "name")
        assert result == "foo"

    def test_few_items(self):
        """Test with few items."""
        items = [{"name": "foo"}, {"name": "bar"}, {"name": "baz"}]
        result = TruncationHelper.format_truncated_dict_list(items, "name")
        assert result == "foo, bar, baz"

    def test_many_items(self):
        """Test with many items."""
        items = [{"name": f"item{i}"} for i in range(100)]
        result = TruncationHelper.format_truncated_dict_list(items, "name", threshold=20)
        assert "item0" in result
        assert "item19" in result
        assert "item20" not in result
        assert "... (80 more)" in result

    def test_missing_key(self):
        """Test with missing key in some items."""
        items = [{"name": "foo"}, {"other": "bar"}, {"name": "baz"}]
        result = TruncationHelper.format_truncated_dict_list(items, "name")
        assert "foo" in result
        assert "baz" in result


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_very_large_list(self):
        """Test with very large list to ensure performance."""
        items = list(range(10000))
        result, msg = TruncationHelper.truncate_list(items, threshold=50)
        assert len(result) == 50
        assert msg == "... (9950 more)"

    def test_nested_structures(self):
        """Test with nested data structures."""
        items = [{"module": f"M{i}", "calls": list(range(100))} for i in range(50)]
        result, msg = TruncationHelper.truncate_call_sites(items, threshold=20)
        assert len(result) == 20
        # Ensure nested structure is preserved
        assert "calls" in result[0]
        assert len(result[0]["calls"]) == 100

    def test_line_numbers_with_gaps(self):
        """Test line numbers with large gaps."""
        lines = [1, 10, 100, 1000, 10000]
        result = TruncationHelper.truncate_line_numbers(lines)
        assert result == ":1, :10, :100, :1000, :10000"

    def test_duplicate_line_numbers(self):
        """Test with duplicate line numbers."""
        lines = [10, 10, 20, 20, 30]
        result = TruncationHelper.truncate_line_numbers(lines)
        # Should still show all (sorted will dedupe via set in real usage)
        assert ":10" in result
        assert ":20" in result
        assert ":30" in result

    def test_zero_threshold(self):
        """Test with zero threshold."""
        items, msg = TruncationHelper.truncate_list([1, 2, 3], threshold=0)
        assert items == []
        assert msg == "... (3 more)"

    def test_negative_threshold(self):
        """Test with negative threshold (edge case - list slicing with negative)."""
        items, msg = TruncationHelper.truncate_list([1, 2, 3], threshold=-1)
        # Python list slicing with negative values has special behavior
        # list[:-1] returns all but the last element
        # This is an edge case and shouldn't be used in practice
        assert isinstance(items, list)
        assert isinstance(msg, str) or msg is None

    def test_special_characters_in_text(self):
        """Test with special characters."""
        text = "Line with `code` and **bold** and [links](url)\n" * 20
        result = TruncationHelper.truncate_text(text, threshold=100)
        assert result.endswith("...")
        assert "`code`" in result or "**bold**" in result
