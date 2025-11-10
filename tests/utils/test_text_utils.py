"""Tests for text utility functions."""

import pytest

from cicada.utils.text_utils import split_camel_snake_case, split_identifier


class TestSplitIdentifier:
    """Test the split_identifier function."""

    def test_empty_string(self):
        """Test that empty string returns empty list."""
        result = split_identifier("")
        assert result == []

    def test_snake_case(self):
        """Test splitting snake_case identifiers."""
        result = split_identifier("get_user_data")
        assert result == ["get", "user", "data"]

    def test_camel_case(self):
        """Test splitting camelCase identifiers."""
        result = split_identifier("getUserData")
        assert result == ["get", "user", "data"]

    def test_pascal_case(self):
        """Test splitting PascalCase identifiers."""
        result = split_identifier("UserController")
        assert result == ["user", "controller"]

    def test_acronym_at_start(self):
        """Test identifiers starting with acronym like HTTPServer."""
        result = split_identifier("HTTPServer")
        assert result == ["http", "server"]

    def test_acronym_at_end(self):
        """Test identifiers ending with acronym like PostgreSQL."""
        result = split_identifier("PostgreSQL")
        # Should split into postgre and sql
        assert "postgre" in result
        assert "sql" in result

    def test_complex_identifier(self):
        """Test complex identifier with multiple patterns."""
        result = split_identifier("getHTTPResponseCode")
        assert "get" in result
        assert "http" in result
        assert "response" in result
        assert "code" in result

    def test_lowercase_true(self):
        """Test that lowercase=True converts to lowercase."""
        result = split_identifier("UserData", lowercase=True)
        assert result == ["user", "data"]
        assert all(word.islower() for word in result)

    def test_lowercase_false(self):
        """Test that lowercase=False preserves case."""
        result = split_identifier("UserData", lowercase=False)
        assert result == ["User", "Data"]
        # At least one word should have uppercase
        assert any(word[0].isupper() for word in result)

    def test_single_word_lowercase(self):
        """Test single word identifier with lowercase."""
        result = split_identifier("user")
        assert result == ["user"]

    def test_single_word_uppercase(self):
        """Test single word identifier in uppercase."""
        result = split_identifier("USER")
        assert result == ["user"]

    def test_mixed_snake_and_camel(self):
        """Test identifier with both snake_case and camelCase."""
        result = split_identifier("get_userData")
        assert "get" in result
        assert "user" in result
        assert "data" in result

    def test_numbers_in_identifier(self):
        """Test identifier containing numbers."""
        result = split_identifier("user123Data")
        # Numbers are kept with the word they're attached to
        assert "user123data" in result or ("user123" in result and "data" in result)

    def test_consecutive_uppercase(self):
        """Test handling of consecutive uppercase letters."""
        result = split_identifier("XMLParser")
        assert "xml" in result
        assert "parser" in result

    def test_underscore_only(self):
        """Test identifier with only underscores."""
        result = split_identifier("___")
        # Underscores are replaced with spaces, result should be empty after filtering
        assert result == []

    def test_single_character(self):
        """Test single character identifier."""
        result = split_identifier("x")
        assert result == ["x"]


class TestSplitCamelSnakeCase:
    """Test the split_camel_snake_case function."""

    def test_camel_case_to_string(self):
        """Test converting camelCase to space-separated string."""
        result = split_camel_snake_case("camelCase")
        assert result == "camel case"

    def test_pascal_case_to_string(self):
        """Test converting PascalCase to space-separated string."""
        result = split_camel_snake_case("PascalCase")
        assert result == "pascal case"

    def test_snake_case_to_string(self):
        """Test converting snake_case to space-separated string."""
        result = split_camel_snake_case("snake_case")
        assert result == "snake case"

    def test_empty_string_to_string(self):
        """Test empty string returns empty string."""
        result = split_camel_snake_case("")
        assert result == ""

    def test_single_word_to_string(self):
        """Test single word remains single word."""
        result = split_camel_snake_case("word")
        assert result == "word"

    def test_complex_identifier_to_string(self):
        """Test complex identifier conversion."""
        result = split_camel_snake_case("getHTTPResponseCode")
        # Should split all components
        assert "get" in result
        assert "http" in result
        assert "response" in result
        assert "code" in result

    def test_lowercase_output(self):
        """Test that output is always lowercase."""
        result = split_camel_snake_case("UserData")
        assert result == "user data"
        assert result.islower()

    def test_multiple_underscores(self):
        """Test handling multiple consecutive underscores."""
        result = split_camel_snake_case("user__data")
        # Multiple underscores should be treated as separators
        assert "user" in result
        assert "data" in result
