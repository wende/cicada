"""
Tests for function range fallback handling in SCIP converter.

These tests validate that functions without enclosing_range data
get proper upper bounds based on subsequent functions.
"""

import pytest
from cicada.languages.scip.converter import SCIPConverter, DocumentData, SymbolData, CallSite


class TestFunctionRangeFallback:
    """Test fallback logic for functions without enclosing_range."""

    def test_single_function_with_fallback(self):
        """Test a single function without enclosing_range uses large upper bound."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        # Simulate a function without enclosing_range (uses fallback 10000)
        function_ranges = [(10, 10000, "test.func1().")]

        # Sort and fix fallbacks (simulate what _extract_document_data does)
        function_ranges.sort(key=lambda x: x[0])
        for i in range(len(function_ranges)):
            start, end, symbol = function_ranges[i]
            if end >= 10000:
                if i + 1 < len(function_ranges):
                    function_ranges[i] = (start, function_ranges[i + 1][0] - 1, symbol)
                else:
                    function_ranges[i] = (start, 999999, symbol)

        # Pre-compute start lines
        function_start_lines = [start for start, _, _ in function_ranges]

        # Verify the function got a large upper bound
        assert function_ranges[0] == (10, 999999, "test.func1().")

        # Test that a call site far away still matches
        result = converter._find_enclosing_fast(50000, function_ranges, function_start_lines)
        assert result == "test.func1()."

    def test_multiple_functions_with_fallback(self):
        """Test multiple functions where fallback upper bounds are replaced."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        # Simulate two functions without enclosing_range
        function_ranges = [
            (10, 10000, "test.func1()."),  # Fallback
            (100, 200, "test.func2()."),  # Has proper range
            (300, 10000, "test.func3()."),  # Fallback
        ]

        # Sort and fix fallbacks
        function_ranges.sort(key=lambda x: x[0])
        for i in range(len(function_ranges)):
            start, end, symbol = function_ranges[i]
            if end >= 10000:
                if i + 1 < len(function_ranges):
                    function_ranges[i] = (start, function_ranges[i + 1][0] - 1, symbol)
                else:
                    function_ranges[i] = (start, 999999, symbol)

        # Pre-compute start lines
        function_start_lines = [start for start, _, _ in function_ranges]

        # Verify fallback upper bounds were fixed
        assert function_ranges[0] == (10, 99, "test.func1().")  # Ends before func2
        assert function_ranges[1] == (100, 200, "test.func2().")  # Unchanged
        assert function_ranges[2] == (300, 999999, "test.func3().")  # Last function

        # Test call site matching
        assert (
            converter._find_enclosing_fast(50, function_ranges, function_start_lines)
            == "test.func1()."
        )
        assert (
            converter._find_enclosing_fast(150, function_ranges, function_start_lines)
            == "test.func2()."
        )
        assert (
            converter._find_enclosing_fast(500, function_ranges, function_start_lines)
            == "test.func3()."
        )

        # Call site between functions should not match
        assert converter._find_enclosing_fast(250, function_ranges, function_start_lines) is None

    def test_nested_functions_with_fallback(self):
        """Test nested functions where outer function uses fallback.

        The outer function should contain the nested function, so its range
        should extend past the nested function (not end before it).
        """
        converter = SCIPConverter(extract_references=True, verbose=False)

        # Simulate outer function with fallback and nested function with proper range
        function_ranges = [
            (10, 10000, "test.outer()."),  # Fallback (outer)
            (20, 30, "test.outer().inner()."),  # Nested function with proper range
        ]

        # Sort and fix fallbacks - use the actual logic from converter.py
        function_ranges.sort(key=lambda x: x[0])
        for i in range(len(function_ranges)):
            start, end, symbol = function_ranges[i]
            if end >= 10000:  # Fallback upper bound was used
                # Find next sibling function (not a nested child)
                sibling_start = None
                for j in range(i + 1, len(function_ranges)):
                    next_symbol = function_ranges[j][2]
                    # A nested function's symbol starts with the parent's symbol
                    if not next_symbol.startswith(symbol):
                        sibling_start = function_ranges[j][0]
                        break

                if sibling_start is not None:
                    function_ranges[i] = (start, sibling_start - 1, symbol)
                else:
                    function_ranges[i] = (start, 999999, symbol)

        # Pre-compute start lines
        function_start_lines = [start for start, _, _ in function_ranges]

        # Outer function should now use 999999 because inner is nested (not a sibling)
        assert function_ranges[0][1] == 999999  # Contains nested function

        # Test call site matching - line 25 is inside the nested function
        result = converter._find_enclosing_fast(25, function_ranges, function_start_lines)
        assert result == "test.outer().inner()."  # Nested takes precedence

        # Line 35 is after nested but still in outer (since outer extends to 999999)
        result = converter._find_enclosing_fast(35, function_ranges, function_start_lines)
        assert result == "test.outer()."

    def test_nested_functions_with_sibling_after(self):
        """Test outer function with nested child and sibling function after.

        The outer function should end before the sibling, not before the nested child.
        """
        converter = SCIPConverter(extract_references=True, verbose=False)

        # outer has nested child, then sibling comes after
        function_ranges = [
            (10, 10000, "test.outer()."),  # Fallback (outer)
            (20, 30, "test.outer().inner()."),  # Nested function
            (100, 150, "test.sibling()."),  # Sibling function (not nested)
        ]

        # Sort and fix fallbacks - use the actual logic from converter.py
        function_ranges.sort(key=lambda x: x[0])
        for i in range(len(function_ranges)):
            start, end, symbol = function_ranges[i]
            if end >= 10000:  # Fallback upper bound was used
                sibling_start = None
                for j in range(i + 1, len(function_ranges)):
                    next_symbol = function_ranges[j][2]
                    if not next_symbol.startswith(symbol):
                        sibling_start = function_ranges[j][0]
                        break

                if sibling_start is not None:
                    function_ranges[i] = (start, sibling_start - 1, symbol)
                else:
                    function_ranges[i] = (start, 999999, symbol)

        # Pre-compute start lines
        function_start_lines = [start for start, _, _ in function_ranges]

        # Outer should end at 99 (before sibling at 100), skipping the nested function
        assert function_ranges[0][1] == 99
        # Nested and sibling should be unchanged
        assert function_ranges[1] == (20, 30, "test.outer().inner().")
        assert function_ranges[2] == (100, 150, "test.sibling().")

        # Line 50 is after nested but before sibling, should match outer
        result = converter._find_enclosing_fast(50, function_ranges, function_start_lines)
        assert result == "test.outer()."

        # Line 120 should match sibling
        result = converter._find_enclosing_fast(120, function_ranges, function_start_lines)
        assert result == "test.sibling()."

    def test_binary_search_with_fallback_ranges(self):
        """Test that binary search works correctly with fallback ranges."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        # Large number of functions with mix of fallback and proper ranges
        function_ranges = []
        for i in range(0, 100, 10):
            if i % 20 == 0:
                # Every other pair uses fallback
                function_ranges.append((i, 10000, f"test.func{i}()."))
            else:
                # Others have proper ranges
                function_ranges.append((i, i + 5, f"test.func{i}()."))

        # Sort and fix fallbacks
        function_ranges.sort(key=lambda x: x[0])
        for i in range(len(function_ranges)):
            start, end, symbol = function_ranges[i]
            if end >= 10000:
                if i + 1 < len(function_ranges):
                    function_ranges[i] = (start, function_ranges[i + 1][0] - 1, symbol)
                else:
                    function_ranges[i] = (start, 999999, symbol)

        # Pre-compute start lines
        function_start_lines = [start for start, _, _ in function_ranges]

        # Test binary search on various lines
        result = converter._find_enclosing_fast(2, function_ranges, function_start_lines)
        assert result == "test.func0()."

        result = converter._find_enclosing_fast(12, function_ranges, function_start_lines)
        assert result == "test.func10()."

        result = converter._find_enclosing_fast(22, function_ranges, function_start_lines)
        assert result == "test.func20()."

    def test_same_start_line_functions(self):
        """Test functions with the same start line (e.g., decorators)."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        # Functions with same start line (outer and inner)
        function_ranges = [
            (10, 50, "test.outer()."),  # Outer function
            (10, 30, "test.inner()."),  # Inner function, same start
        ]

        function_ranges.sort(key=lambda x: x[0])
        function_start_lines = [start for start, _, _ in function_ranges]

        # Binary search should find the smallest enclosing range
        result = converter._find_enclosing_fast(20, function_ranges, function_start_lines)
        assert result == "test.inner()."  # Smallest range wins

        # Line outside inner but inside outer
        result = converter._find_enclosing_fast(40, function_ranges, function_start_lines)
        assert result == "test.outer()."

    def test_line_before_all_functions(self):
        """Test line before any function."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        function_ranges = [(10, 20, "test.func1()."), (30, 40, "test.func2().")]
        function_start_lines = [10, 30]

        # Line before all functions
        result = converter._find_enclosing_fast(5, function_ranges, function_start_lines)
        assert result is None

    def test_line_after_all_functions(self):
        """Test line after all functions."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        function_ranges = [(10, 20, "test.func1()."), (30, 40, "test.func2().")]
        function_start_lines = [10, 30]

        # Line after all functions
        result = converter._find_enclosing_fast(50, function_ranges, function_start_lines)
        assert result is None

    def test_empty_function_ranges(self):
        """Test with no function ranges."""
        converter = SCIPConverter(extract_references=True, verbose=False)

        function_ranges = []
        function_start_lines = []

        result = converter._find_enclosing_fast(50, function_ranges, function_start_lines)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
