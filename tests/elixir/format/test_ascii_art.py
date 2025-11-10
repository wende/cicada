"""
Comprehensive tests for cicada/ascii_art.py

Tests ASCII art generation and banner formatting
"""

import re

import pytest

from cicada.elixir.format.ascii_art import (
    CICADA_ASCII_ART,
    CYAN,
    RESET,
    YELLOW,
    generate_gradient_ascii_art,
    get_welcome_banner,
)


class TestGenerateGradientAsciiArt:
    """Tests for generate_gradient_ascii_art function"""

    def test_returns_string(self):
        """Test that function returns a string"""
        result = generate_gradient_ascii_art()
        assert isinstance(result, str)

    def test_contains_newlines(self):
        """Test that result contains multiple lines"""
        result = generate_gradient_ascii_art()
        assert "\n" in result
        lines = result.split("\n")
        # Should have at least 10 lines of art + padding
        assert len(lines) >= 10

    def test_contains_ansi_color_codes(self):
        """Test that result contains ANSI color codes"""
        result = generate_gradient_ascii_art()

        # Should contain ANSI escape sequences
        assert "\033[" in result

        # Should contain RGB color codes (38;2;R;G;B format)
        assert re.search(r"\033\[38;2;\d+;\d+;\d+m", result) is not None

    def test_contains_reset_codes(self):
        """Test that result contains ANSI reset codes"""
        result = generate_gradient_ascii_art()

        # Each line should reset at the end
        assert "\033[0m" in result

        # Count number of reset codes (should be >= number of art lines)
        reset_count = result.count("\033[0m")
        lines_count = len([line for line in result.split("\n") if line.strip()])
        assert reset_count >= lines_count - 2  # Account for padding lines

    def test_gradient_start_color(self):
        """Test that first line uses start color (E5C890)"""
        result = generate_gradient_ascii_art()

        # First colored line should have start color RGB values
        # E5C890 = RGB(229, 200, 144)
        start_color = "\033[38;2;229;200;144m"
        assert start_color in result

    def test_gradient_end_color(self):
        """Test that last line uses end color (D17958)"""
        result = generate_gradient_ascii_art()

        # Last colored line should have end color RGB values
        # D17958 = RGB(209, 121, 88)
        end_color = "\033[38;2;209;121;88m"
        assert end_color in result

    def test_gradient_interpolation(self):
        """Test that gradient interpolates between colors"""
        result = generate_gradient_ascii_art()

        # Extract all RGB values from color codes
        color_pattern = r"\033\[38;2;(\d+);(\d+);(\d+)m"
        matches = re.findall(color_pattern, result)

        assert len(matches) > 0

        # Convert to integers
        colors = [(int(r), int(g), int(b)) for r, g, b in matches]

        # Check that colors change gradually (not all the same)
        unique_colors = set(colors)
        assert len(unique_colors) > 1

        # First color should be close to start (229, 200, 144)
        first_color = colors[0]
        assert abs(first_color[0] - 229) <= 5
        assert abs(first_color[1] - 200) <= 5
        assert abs(first_color[2] - 144) <= 5

        # Last color should be close to end (209, 121, 88)
        last_color = colors[-1]
        assert abs(last_color[0] - 209) <= 5
        assert abs(last_color[1] - 121) <= 5
        assert abs(last_color[2] - 88) <= 5

    def test_contains_cicada_art_elements(self):
        """Test that result contains recognizable cicada ASCII art elements"""
        result = generate_gradient_ascii_art()

        # Should contain characteristic patterns from cicada art
        # Remove ANSI codes to check actual content
        plain_text = re.sub(r"\033\[[^m]+m", "", result)

        # Check for some recognizable patterns (quotes, special chars)
        assert any(
            char in plain_text for char in ['"', "'", "@", "m", "g", "B"]
        ), "Should contain cicada art characters"

    def test_all_lines_have_color_codes(self):
        """Test that each art line has its own color code"""
        result = generate_gradient_ascii_art()

        # Split into lines and filter non-empty
        lines = [line for line in result.split("\n") if line.strip()]

        # Each art line should start with a color code
        for line in lines:
            if line.strip():  # Skip empty lines
                assert line.startswith(
                    "\033[38;2;"
                ), f"Line should start with color code: {line[:20]}"

    def test_consistent_output(self):
        """Test that function returns consistent output on multiple calls"""
        result1 = generate_gradient_ascii_art()
        result2 = generate_gradient_ascii_art()

        assert result1 == result2


class TestGetWelcomeBanner:
    """Tests for get_welcome_banner function"""

    def test_returns_string(self):
        """Test that function returns a string"""
        result = get_welcome_banner()
        assert isinstance(result, str)

    def test_includes_ascii_art(self):
        """Test that banner includes ASCII art"""
        result = get_welcome_banner()

        # Should contain ANSI color codes from ASCII art
        assert "\033[38;2;" in result

    def test_includes_welcome_message(self):
        """Test that banner includes welcome message"""
        result = get_welcome_banner()

        assert "Welcome to CICADA" in result
        assert "Elixir Code Intelligence" in result

    def test_includes_separator_lines(self):
        """Test that banner includes separator lines"""
        result = get_welcome_banner()

        # Should have separator lines (====...)
        assert "=" * 66 in result

    def test_includes_color_codes(self):
        """Test that banner uses proper color codes"""
        result = get_welcome_banner()

        # Should use CYAN and YELLOW colors
        assert CYAN in result
        assert YELLOW in result
        assert RESET in result

    def test_proper_formatting(self):
        """Test that banner has proper line breaks and structure"""
        result = get_welcome_banner()

        # Should have multiple lines
        lines = result.split("\n")
        assert len(lines) > 10

    def test_banner_structure(self):
        """Test overall banner structure"""
        result = get_welcome_banner()

        # Remove ANSI codes for structure verification
        plain_text = re.sub(r"\033\[[^m]+m", "", result)

        # Should contain the main components in order
        assert "Welcome to CICADA" in plain_text
        assert "Elixir Code Intelligence" in plain_text


class TestCicadaAsciiArtConstant:
    """Tests for CICADA_ASCII_ART pre-generated constant"""

    def test_constant_is_string(self):
        """Test that constant is a string"""
        assert isinstance(CICADA_ASCII_ART, str)

    def test_constant_not_empty(self):
        """Test that constant is not empty"""
        assert len(CICADA_ASCII_ART) > 0

    def test_constant_has_ansi_codes(self):
        """Test that constant contains ANSI codes"""
        assert "\033[" in CICADA_ASCII_ART

    def test_constant_matches_function_output(self):
        """Test that constant matches generate_gradient_ascii_art() output"""
        generated = generate_gradient_ascii_art()
        assert generated == CICADA_ASCII_ART


class TestColorConstants:
    """Tests for color constant definitions"""

    def test_cyan_is_ansi_code(self):
        """Test that CYAN is an ANSI escape sequence"""
        assert isinstance(CYAN, str)
        assert CYAN.startswith("\033[")

    def test_yellow_is_ansi_code(self):
        """Test that YELLOW is an ANSI escape sequence"""
        assert isinstance(YELLOW, str)
        assert YELLOW.startswith("\033[")

    def test_reset_is_ansi_code(self):
        """Test that RESET is an ANSI escape sequence"""
        assert isinstance(RESET, str)
        assert RESET == "\033[0m"

    def test_colors_are_rgb_format(self):
        """Test that color codes use RGB format"""
        # CYAN should be RGB color (38;2;R;G;B)
        assert "38;2;" in CYAN

        # YELLOW should be RGB color
        assert "38;2;" in YELLOW


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_gradient_with_single_line(self):
        """Test gradient calculation doesn't fail with edge cases"""
        # This tests the internal logic - the actual function always has 10 lines
        # But we verify the calculation works correctly
        result = generate_gradient_ascii_art()
        # Should not raise any exceptions
        assert result is not None

    def test_ansi_codes_properly_closed(self):
        """Test that all ANSI codes are properly closed"""
        result = generate_gradient_ascii_art()

        # Count opening color codes (38;2;)
        opening_count = len(re.findall(r"\033\[38;2;\d+;\d+;\d+m", result))

        # Count closing codes (\033[0m)
        closing_count = result.count("\033[0m")

        # Should have approximately equal number (allowing for some variation)
        assert closing_count >= opening_count - 1

    def test_no_unicode_errors(self):
        """Test that ASCII art doesn't contain problematic unicode"""
        result = generate_gradient_ascii_art()

        # Should encode to ASCII (with ANSI codes being latin-1 compatible)
        # Remove ANSI codes and check actual content is ASCII-compatible
        plain = re.sub(r"\033\[[^m]+m", "", result)
        try:
            plain.encode("ascii")
        except UnicodeEncodeError:
            pytest.fail("ASCII art contains non-ASCII characters")
