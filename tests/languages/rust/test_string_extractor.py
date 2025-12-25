"""Tests for Rust string extractor."""

import pytest

from cicada.languages.rust.string_extractor import RustStringExtractor


class TestRustStringExtractor:
    """Tests for RustStringExtractor."""

    def test_extract_simple_string(self):
        """Test extracting a simple string literal."""
        extractor = RustStringExtractor()
        source = 'let msg = "hello world";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello world"
        assert result[0]["line"] == 1
        assert result[0]["function"] is None

    def test_extract_multiple_strings(self):
        """Test extracting multiple strings from same line."""
        extractor = RustStringExtractor()
        source = 'println!("{} {}", "hello", "world");'
        result = extractor.extract_from_source(source)

        assert len(result) == 3
        assert result[0]["string"] == "{} {}"
        assert result[1]["string"] == "hello"
        assert result[2]["string"] == "world"

    def test_extract_multiline_source(self):
        """Test extracting strings from multiple lines."""
        extractor = RustStringExtractor()
        source = """fn main() {
    let a = "first";
    let b = "second";
}"""
        result = extractor.extract_from_source(source)

        assert len(result) == 2
        assert result[0]["string"] == "first"
        assert result[0]["line"] == 2
        assert result[1]["string"] == "second"
        assert result[1]["line"] == 3

    def test_skip_short_strings(self):
        """Test that strings shorter than min_length are skipped."""
        extractor = RustStringExtractor(min_length=5)
        source = 'let x = "ab"; let y = "hello";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello"

    def test_skip_whitespace_only_strings(self):
        """Test that whitespace-only strings are skipped."""
        extractor = RustStringExtractor(min_length=1)
        source = 'let x = "   "; let y = "hello";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "hello"

    def test_handle_escaped_quotes(self):
        """Test handling of escaped quotes inside strings."""
        extractor = RustStringExtractor()
        source = r'let msg = "say \"hello\"";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == r"say \"hello\""

    def test_handle_escaped_backslash(self):
        """Test handling of escaped backslashes."""
        extractor = RustStringExtractor()
        source = r'let path = "C:\\Users\\name";'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert "Users" in result[0]["string"]

    def test_skip_comment_strings(self):
        """Test that strings in comments are skipped."""
        extractor = RustStringExtractor()
        source = '// let x = "commented out";'
        result = extractor.extract_from_source(source)

        assert len(result) == 0

    def test_partial_comment_line(self):
        """Test line with code before comment."""
        extractor = RustStringExtractor()
        source = 'let x = "real"; // "fake"'
        result = extractor.extract_from_source(source)

        assert len(result) == 1
        assert result[0]["string"] == "real"

    def test_empty_source(self):
        """Test with empty source code."""
        extractor = RustStringExtractor()
        result = extractor.extract_from_source("")

        assert result == []

    def test_no_strings(self):
        """Test source with no strings."""
        extractor = RustStringExtractor()
        source = "fn add(a: i32, b: i32) -> i32 { a + b }"
        result = extractor.extract_from_source(source)

        assert result == []

    def test_default_min_length(self):
        """Test that default min_length is 3."""
        extractor = RustStringExtractor()
        assert extractor.min_length == 3

    def test_custom_min_length(self):
        """Test custom min_length initialization."""
        extractor = RustStringExtractor(min_length=10)
        assert extractor.min_length == 10
