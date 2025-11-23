"""
Unit tests for context extraction utilities.

Tests paragraph extraction, keyword highlighting, and smart string truncation.
"""

import pytest

from cicada.query.context_extractor import (
    extract_paragraph,
    extract_multiple_keywords,
    highlight_keywords,
    smart_truncate_string,
    format_matched_context,
)


class TestExtractParagraph:
    """Tests for extract_paragraph function."""

    def test_simple_paragraph(self):
        """Test extracting a keyword from simple text."""
        text = "This is a test paragraph with the word authentication in it."
        result = extract_paragraph(text, "authentication")
        assert result == text.strip()

    def test_multiple_paragraphs_finds_correct_one(self):
        """Test finding the correct paragraph when multiple exist."""
        text = """First paragraph about login.

Second paragraph about authentication and security.

Third paragraph about database."""

        result = extract_paragraph(text, "authentication")
        assert result == "Second paragraph about authentication and security."

    def test_case_insensitive_search(self):
        """Test that keyword search is case-insensitive."""
        text = "This paragraph mentions AUTHENTICATION in uppercase."
        result = extract_paragraph(text, "authentication")
        assert result == text.strip()

    def test_keyword_not_found(self):
        """Test that None is returned when keyword is not found."""
        text = "This paragraph has no relevant keywords."
        result = extract_paragraph(text, "authentication")
        assert result is None

    def test_empty_text(self):
        """Test handling of empty text."""
        assert extract_paragraph("", "test") is None
        assert extract_paragraph(None, "test") is None

    def test_empty_keyword(self):
        """Test handling of empty keyword."""
        assert extract_paragraph("some text", "") is None
        assert extract_paragraph("some text", None) is None

    def test_keyword_at_paragraph_start(self):
        """Test finding keyword at the start of a paragraph."""
        text = """Other paragraph.

Authentication is important for security.

Final paragraph."""
        result = extract_paragraph(text, "authentication")
        assert result == "Authentication is important for security."

    def test_keyword_at_paragraph_end(self):
        """Test finding keyword at the end of a paragraph."""
        text = """Other paragraph.

Security requires proper authentication.

Final paragraph."""
        result = extract_paragraph(text, "authentication")
        assert result == "Security requires proper authentication."

    def test_single_newlines_count_as_paragraphs(self):
        """Test that single newlines are treated as paragraph breaks."""
        text = "First line about intro.\nSecond line with authentication mention.\nThird line."
        result = extract_paragraph(text, "authentication")
        assert result == "Second line with authentication mention."


class TestExtractMultipleKeywords:
    """Tests for extract_multiple_keywords function."""

    def test_single_keyword(self):
        """Test with a single keyword."""
        text = "This paragraph mentions authentication."
        result = extract_multiple_keywords(text, ["authentication"])
        assert result == text.strip()

    def test_paragraph_with_most_keywords(self):
        """Test that the paragraph with most keywords is returned."""
        text = """Login and session management.

Authentication, credentials, and validation are important.

Database queries."""

        result = extract_multiple_keywords(text, ["authentication", "credentials", "validation"])
        assert "Authentication, credentials, and validation" in result

    def test_single_paragraph_with_multiple_keywords(self):
        """Test finding multiple keywords in a single paragraph."""
        text = "This text has authentication and credentials mentioned."
        result = extract_multiple_keywords(text, ["authentication", "credentials"])
        assert result == text.strip()

    def test_no_keywords_found(self):
        """Test when no keywords are found."""
        text = "This paragraph has no relevant keywords."
        result = extract_multiple_keywords(text, ["auth", "login"])
        assert result is None

    def test_empty_keywords_list(self):
        """Test with empty keywords list."""
        text = "Some text here."
        result = extract_multiple_keywords(text, [])
        assert result is None

    def test_partial_match_different_paragraphs(self):
        """Test when keywords are spread across paragraphs."""
        text = """First paragraph with authentication.

Second paragraph with credentials.

Third paragraph with authentication and login."""

        # Should return third paragraph with 2 keywords
        result = extract_multiple_keywords(text, ["authentication", "credentials", "login"])
        assert "Third paragraph with authentication and login" in result


class TestHighlightKeywords:
    """Tests for highlight_keywords function."""

    def test_bold_highlighting(self):
        """Test highlighting with markdown bold."""
        text = "This paragraph mentions authentication."
        result = highlight_keywords(text, ["authentication"], use_ansi=False)
        assert "**authentication**" in result

    def test_ansi_highlighting(self):
        """Test highlighting with ANSI colors."""
        text = "This paragraph mentions authentication."
        result = highlight_keywords(text, ["authentication"], use_ansi=True)
        # Should contain ANSI escape codes
        assert "\033[" in result
        assert "authentication" in result

    def test_multiple_keywords(self):
        """Test highlighting multiple keywords."""
        text = "Authentication and credentials are important."
        result = highlight_keywords(text, ["authentication", "credentials"], use_ansi=False)
        assert "**Authentication**" in result  # Case is preserved from original text
        assert "**credentials**" in result

    def test_case_insensitive_highlighting(self):
        """Test that highlighting preserves original case."""
        text = "AUTHENTICATION and Authentication are important."
        result = highlight_keywords(text, ["authentication"], use_ansi=False)
        assert "**AUTHENTICATION**" in result
        assert "**Authentication**" in result

    def test_empty_text(self):
        """Test with empty text."""
        result = highlight_keywords("", ["test"], use_ansi=False)
        assert result == ""

    def test_empty_keywords(self):
        """Test with empty keywords list."""
        text = "Some text here."
        result = highlight_keywords(text, [], use_ansi=False)
        assert result == text

    def test_keyword_appears_multiple_times(self):
        """Test highlighting when keyword appears multiple times."""
        text = "Authentication is key. Without authentication, security fails."
        result = highlight_keywords(text, ["authentication"], use_ansi=False)
        # Count occurrences of highlighted keyword
        assert result.count("**authentication**") == 1
        assert result.count("**Authentication**") == 1

    def test_longest_keyword_first(self):
        """Test that longer keywords are matched first to avoid partial matches."""
        text = "The user account uses user authentication."
        result = highlight_keywords(text, ["user", "user authentication"], use_ansi=False)
        # "user authentication" should be highlighted as one phrase, not two separate words
        assert "**user authentication**" in result

    def test_ansi_highlight_skips_existing_markers(self):
        """Ensure ANSI highlighting does not double-wrap existing highlights."""
        highlighted = "\033[1;33mauthentication\033[0m is present"
        result = highlight_keywords(highlighted, ["authentication"], use_ansi=True)
        assert result.count("\033[1;33m") == 1


class TestSmartTruncateString:
    """Tests for smart_truncate_string function."""

    def test_short_string_no_truncation(self):
        """Test that short strings are not truncated."""
        text = "Short string"
        result = smart_truncate_string(text, max_length=150)
        assert result == '"Short string"'

    def test_short_string_with_line_number(self):
        """Test short string with line number."""
        text = "Short string"
        result = smart_truncate_string(text, max_length=150, line_number=42)
        assert result == '"Short string" (line 42)'

    def test_long_string_truncation(self):
        """Test that long strings are truncated."""
        text = "This is a very long string that exceeds the maximum length " * 5
        result = smart_truncate_string(text, max_length=100)
        assert "..." in result

    def test_long_string_with_line_number(self):
        """Test long string truncation with line number."""
        text = "This is a very long string that exceeds the maximum length " * 5
        result = smart_truncate_string(text, max_length=100, line_number=42)
        assert "..." in result
        assert "(line 42)" in result

    def test_truncation_preserves_keyword_near_end(self):
        """Truncation should keep keywords that appear late in the string."""
        text = "prefix " + (" filler" * 40) + " keyword target"
        result = smart_truncate_string(text, max_length=60, keywords=["keyword"])
        assert "keyword" in result
        assert result.startswith('"...')

    def test_empty_string(self):
        """Test with empty string."""
        result = smart_truncate_string("")
        assert result == '""'

    def test_custom_max_length(self):
        """Test with custom max_length parameter."""
        text = "This is a string with exactly fifty characters!!"
        result = smart_truncate_string(text, max_length=30)
        assert "..." in result


class TestFormatMatchedContext:
    """Tests for format_matched_context function."""

    def test_documentation_only_match(self):
        """Test formatting when keywords match only in documentation."""
        matched_keywords = ["authentication", "login"]
        keyword_sources = {"authentication": "docs", "login": "docs"}
        doc_text = "This module handles authentication and login for users."
        string_sources = []

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in documentation:" in result
        assert "**authentication**" in result
        assert "**login**" in result

    def test_strings_only_match(self):
        """Test formatting when keywords match only in string literals."""
        matched_keywords = ["SELECT", "users"]
        keyword_sources = {"SELECT": "strings", "users": "strings"}
        doc_text = "Database query module."
        string_sources = [{"string": "SELECT * FROM users WHERE active = true", "line": 42}]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in strings:" in result
        assert "**SELECT**" in result
        assert "**users**" in result
        assert "(line 42)" in result

    def test_string_match_truncates_around_keyword(self):
        """String snippets should preserve late keywords when truncating."""
        long_string = "prefix " + (" filler" * 60) + " keyword at the end"
        matched_keywords = ["keyword"]
        keyword_sources = {"keyword": "strings"}
        doc_text = "Database query module."
        string_sources = [{"string": long_string, "line": 88}]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in strings:" in result
        assert "keyword" in result
        assert "..." in result
        assert "(line 88)" in result

    def test_both_doc_and_string_matches(self):
        """Test formatting when keywords match in both docs and strings."""
        matched_keywords = ["authentication", "credentials"]
        keyword_sources = {"authentication": "both", "credentials": "strings"}
        doc_text = "Authentication module for validating user credentials."
        string_sources = [{"string": "Invalid credentials provided", "line": 50}]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in documentation:" in result
        assert "Matched in strings:" in result
        assert "**Authentication**" in result  # Case preserved from original text
        assert "**credentials**" in result

    def test_no_doc_text_available(self):
        """Test when no documentation text is available."""
        matched_keywords = ["error"]
        keyword_sources = {"error": "strings"}
        doc_text = None
        string_sources = [{"string": "Error: connection failed", "line": 100}]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in documentation:" not in result
        assert "Matched in strings:" in result

    def test_no_string_sources_available(self):
        """Test when no string sources are available."""
        matched_keywords = ["authentication"]
        keyword_sources = {"authentication": "docs"}
        doc_text = "Authentication module."
        string_sources = None

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in documentation:" in result
        assert "Matched in strings:" not in result

    def test_non_string_string_sources_are_ignored(self):
        """Non-string sources should be skipped safely."""
        matched_keywords = ["error"]
        keyword_sources = {"error": "strings"}
        doc_text = None
        string_sources = [{"string": None, "line": 5}]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert result == ""

    def test_no_context_available(self):
        """Test when no context is available."""
        matched_keywords = ["test"]
        keyword_sources = {"test": "docs"}
        doc_text = None
        string_sources = None

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert result == ""

    def test_multiple_string_sources(self):
        """Test with multiple string literal sources."""
        matched_keywords = ["error", "message"]
        keyword_sources = {"error": "strings", "message": "strings"}
        doc_text = None
        string_sources = [
            {"string": "Error: invalid input", "line": 10},
            {"string": "Error message logged", "line": 20},
            {"string": "System error detected", "line": 30},
            {"string": "Message sent successfully", "line": 40},
        ]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in strings:" in result
        # Should limit to 3 string matches
        assert result.count("(line") <= 3

    def test_ansi_highlighting_in_context(self):
        """Test that ANSI highlighting is applied when use_ansi=True."""
        matched_keywords = ["test"]
        keyword_sources = {"test": "docs"}
        doc_text = "This is a test module."
        string_sources = []

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=True
        )

        # Should contain ANSI escape codes
        assert "\033[" in result

    def test_long_string_truncation_in_context(self):
        """Test that long strings are truncated in the formatted context."""
        matched_keywords = ["SELECT", "users"]
        keyword_sources = {"SELECT": "strings", "users": "strings"}
        doc_text = None
        long_string = "SELECT * FROM users WHERE " + "condition AND " * 20 + "active = true"
        string_sources = [{"string": long_string, "line": 100}]

        result = format_matched_context(
            matched_keywords, keyword_sources, doc_text, string_sources, use_ansi=False
        )

        assert "Matched in strings:" in result
        assert "..." in result  # Should be truncated
        assert "(line 100)" in result
