"""
Comprehensive tests for interactive setup menu

Tests the first-time setup experience for cicada
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys


class TestInteractiveSetup:
    """Tests for show_first_time_setup function"""

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_spacy_fast_selection(self, mock_menu_class, mock_ascii):
        """Test selecting spaCy with fast model"""
        from cicada.interactive_setup import show_first_time_setup

        # Mock ASCII art
        mock_ascii.return_value = "ASCII ART"

        # Mock menu selections: spaCy (index 0), then fast (index 0)
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]  # method=0, tier=0
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "spacy"
        assert tier == "fast"
        mock_ascii.assert_called_once()

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_spacy_regular_selection(self, mock_menu_class, mock_ascii):
        """Test selecting spaCy with regular model"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1]  # method=0, tier=1
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "spacy"
        assert tier == "regular"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_spacy_max_selection(self, mock_menu_class, mock_ascii):
        """Test selecting spaCy with max model"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 2]  # method=0, tier=2
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "spacy"
        assert tier == "max"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_fast_selection(self, mock_menu_class, mock_ascii):
        """Test selecting KeyBERT with fast model"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 0]  # method=1, tier=0
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "bert"
        assert tier == "fast"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_regular_selection(self, mock_menu_class, mock_ascii):
        """Test selecting KeyBERT with regular model"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 1]  # method=1, tier=1
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "bert"
        assert tier == "regular"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_max_selection(self, mock_menu_class, mock_ascii):
        """Test selecting KeyBERT with max model"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 2]  # method=1, tier=2
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "bert"
        assert tier == "max"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_method_selection(self, mock_menu_class, mock_ascii):
        """Test Ctrl+C during method selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = KeyboardInterrupt()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_tier_selection(self, mock_menu_class, mock_ascii):
        """Test Ctrl+C during tier selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call succeeds (method), second raises KeyboardInterrupt (tier)
        mock_menu_instance.show.side_effect = [0, KeyboardInterrupt()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_none_selection_on_method(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on method selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.return_value = None  # User pressed ESC
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_none_selection_on_tier(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on tier selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 0 (spaCy), second returns None (cancel)
        mock_menu_instance.show.side_effect = [0, None]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_return_value_is_tuple(self, mock_menu_class, mock_ascii):
        """Test that return value is a tuple of two strings"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1]
        mock_menu_class.return_value = mock_menu_instance

        result = show_first_time_setup()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_menu_created_with_correct_items(self, mock_menu_class, mock_ascii):
        """Test that TerminalMenu is created with correct method items"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        # Check that TerminalMenu was called twice (method and tier)
        assert mock_menu_class.call_count == 2

        # Check first call (method selection)
        first_call_args = mock_menu_class.call_args_list[0]
        method_items = first_call_args[0][0]
        assert len(method_items) == 2
        assert "spaCy" in method_items[0]
        assert "KeyBERT" in method_items[1]

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_spacy_tier_items_displayed(self, mock_menu_class, mock_ascii):
        """Test that spaCy-specific tier items are shown"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]  # Select spaCy
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        # Check second call (tier selection for spaCy)
        second_call_args = mock_menu_class.call_args_list[1]
        tier_items = second_call_args[0][0]
        assert len(tier_items) == 3
        # spaCy tiers should mention MB sizes and speeds
        assert "12MB" in tier_items[0]
        assert "40MB" in tier_items[1]
        assert "560MB" in tier_items[2]

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_tier_items_displayed(self, mock_menu_class, mock_ascii):
        """Test that KeyBERT-specific tier items are shown"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 0]  # Select KeyBERT
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        # Check second call (tier selection for KeyBERT)
        second_call_args = mock_menu_class.call_args_list[1]
        tier_items = second_call_args[0][0]
        assert len(tier_items) == 3
        # KeyBERT tiers should mention MB sizes and speeds
        assert "80MB" in tier_items[0]
        assert "133MB" in tier_items[1]
        assert "420MB" in tier_items[2]

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_ascii_art_displayed(self, mock_menu_class, mock_ascii, capsys):
        """Test that ASCII art is displayed at start"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "🦗 CICADA ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        # Verify ASCII art was called
        mock_ascii.assert_called_once()

        # Verify it was printed
        captured = capsys.readouterr()
        assert "🦗 CICADA ASCII ART" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_welcome_message_displayed(self, mock_menu_class, mock_ascii, capsys):
        """Test that welcome message is displayed"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Welcome to CICADA" in captured.out
        assert "first time running CICADA" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_success_message_displayed(self, mock_menu_class, mock_ascii, capsys):
        """Test that success message is displayed after selection"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1]  # spaCy, regular
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Selected:" in captured.out
        assert "SPACY" in captured.out
        assert "Regular" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_spacy_explanation_shown(self, mock_menu_class, mock_ascii, capsys):
        """Test that spaCy explanation is shown when spaCy is selected"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]  # Select spaCy
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "What is spaCy?" in captured.out
        assert "grammar rules" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_explanation_shown(self, mock_menu_class, mock_ascii, capsys):
        """Test that KeyBERT explanation is shown when KeyBERT is selected"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 0]  # Select KeyBERT
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "What is KeyBERT?" in captured.out
        assert "AI embeddings" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_menu_cursor_style(self, mock_menu_class, mock_ascii):
        """Test that menu is created with correct styling"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        # Check that menu was created with correct style parameters
        first_call_kwargs = mock_menu_class.call_args_list[0][1]
        assert first_call_kwargs["menu_cursor"] == "» "
        assert first_call_kwargs["cycle_cursor"] == True
        assert first_call_kwargs["clear_screen"] == False

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_tier_map_correctness(self, mock_menu_class, mock_ascii):
        """Test that tier mapping is correct for all indices"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_class.return_value = mock_menu_instance

        # Test all tier indices
        test_cases = [
            (0, "fast"),
            (1, "regular"),
            (2, "max"),
        ]

        for tier_index, expected_tier in test_cases:
            mock_menu_instance.show.side_effect = [0, tier_index]  # spaCy + tier
            method, tier = show_first_time_setup()
            assert (
                tier == expected_tier
            ), f"Expected {expected_tier} for index {tier_index}"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_tier_index_as_tuple(self, mock_menu_class, mock_ascii):
        """Test that tier_index as tuple is handled correctly"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        # Return tuple instead of int for tier selection (some terminals do this)
        mock_menu_instance.show.side_effect = [0, (1, "some_extra_data")]
        mock_menu_class.return_value = mock_menu_instance

        method, tier = show_first_time_setup()

        assert method == "spacy"
        assert tier == "regular"


class TestTextBasedSetup:
    """Tests for _text_based_setup fallback function"""

    @patch("builtins.input")
    def test_text_spacy_fast_default_values(self, mock_input):
        """Test text-based setup with default values (empty input)"""
        from cicada.interactive_setup import _text_based_setup

        # User presses enter for defaults: method=1 (spaCy), tier=2 (regular)
        mock_input.side_effect = ["", ""]

        method, tier = _text_based_setup()

        assert method == "spacy"
        assert tier == "regular"

    @patch("builtins.input")
    def test_text_spacy_fast(self, mock_input):
        """Test text-based setup selecting spaCy fast"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1"]

        method, tier = _text_based_setup()

        assert method == "spacy"
        assert tier == "fast"

    @patch("builtins.input")
    def test_text_spacy_regular(self, mock_input):
        """Test text-based setup selecting spaCy regular"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "2"]

        method, tier = _text_based_setup()

        assert method == "spacy"
        assert tier == "regular"

    @patch("builtins.input")
    def test_text_spacy_max(self, mock_input):
        """Test text-based setup selecting spaCy max"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "3"]

        method, tier = _text_based_setup()

        assert method == "spacy"
        assert tier == "max"

    @patch("builtins.input")
    def test_text_bert_fast(self, mock_input):
        """Test text-based setup selecting KeyBERT fast"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "1"]

        method, tier = _text_based_setup()

        assert method == "bert"
        assert tier == "fast"

    @patch("builtins.input")
    def test_text_bert_regular(self, mock_input):
        """Test text-based setup selecting KeyBERT regular"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "2"]

        method, tier = _text_based_setup()

        assert method == "bert"
        assert tier == "regular"

    @patch("builtins.input")
    def test_text_bert_max(self, mock_input):
        """Test text-based setup selecting KeyBERT max"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "3"]

        method, tier = _text_based_setup()

        assert method == "bert"
        assert tier == "max"

    @patch("builtins.input")
    def test_text_invalid_method_then_valid(self, mock_input, capsys):
        """Test text-based setup with invalid method input followed by valid"""
        from cicada.interactive_setup import _text_based_setup

        # First invalid (3), then valid (1), then tier (2)
        mock_input.side_effect = ["3", "1", "2"]

        method, tier = _text_based_setup()

        assert method == "spacy"
        assert tier == "regular"

        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_text_invalid_tier_then_valid(self, mock_input, capsys):
        """Test text-based setup with invalid tier input followed by valid"""
        from cicada.interactive_setup import _text_based_setup

        # Valid method (1), then invalid tier (4), then valid tier (1)
        mock_input.side_effect = ["1", "4", "1"]

        method, tier = _text_based_setup()

        assert method == "spacy"
        assert tier == "fast"

        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_method(self, mock_input):
        """Test text-based setup with Ctrl+C during method selection"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_tier(self, mock_input):
        """Test text-based setup with Ctrl+C during tier selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid method, then KeyboardInterrupt on tier
        mock_input.side_effect = ["1", KeyboardInterrupt()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_method(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during method selection"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = EOFError()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_tier(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during tier selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid method, then EOFError on tier
        mock_input.side_effect = ["2", EOFError()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_shows_spacy_explanation(self, mock_input, capsys):
        """Test that text-based setup shows spaCy explanation"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1"]

        _text_based_setup()

        captured = capsys.readouterr()
        assert "What is spaCy?" in captured.out
        assert "grammar rules" in captured.out

    @patch("builtins.input")
    def test_text_shows_bert_explanation(self, mock_input, capsys):
        """Test that text-based setup shows KeyBERT explanation"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "1"]

        _text_based_setup()

        captured = capsys.readouterr()
        assert "What is KeyBERT?" in captured.out
        assert "AI embeddings" in captured.out

    @patch("builtins.input")
    def test_text_shows_welcome_message(self, mock_input, capsys):
        """Test that text-based setup shows welcome message"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1"]

        _text_based_setup()

        captured = capsys.readouterr()
        assert "Welcome to CICADA" in captured.out
        assert "first time running CICADA" in captured.out

    @patch("builtins.input")
    def test_text_shows_success_message(self, mock_input, capsys):
        """Test that text-based setup shows success message"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "2"]

        _text_based_setup()

        captured = capsys.readouterr()
        assert "Selected:" in captured.out
        assert "SPACY" in captured.out
        assert "Regular" in captured.out


class TestFallbackScenarios:
    """Tests for fallback to text-based setup"""

    @patch("cicada.interactive_setup.has_terminal_menu", False)
    @patch("builtins.input")
    def test_fallback_when_terminal_menu_not_available(self, mock_input):
        """Test fallback to text-based setup when simple-term-menu not installed"""
        from cicada.interactive_setup import show_first_time_setup

        mock_input.side_effect = ["1", "1"]

        method, tier = show_first_time_setup()

        assert method == "spacy"
        assert tier == "fast"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu", None)
    @patch("builtins.input")
    def test_fallback_when_terminal_menu_is_none(self, mock_input, mock_ascii):
        """Test fallback when TerminalMenu is None"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        mock_input.side_effect = ["2", "2"]

        method, tier = show_first_time_setup()

        assert method == "bert"
        assert tier == "regular"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_on_exception_during_method_menu(
        self, mock_input, mock_menu_class, mock_ascii
    ):
        """Test fallback to text-based setup when TerminalMenu raises exception"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        # Make TerminalMenu.show() raise an exception
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = Exception("Terminal not supported")
        mock_menu_class.return_value = mock_menu_instance

        mock_input.side_effect = ["1", "3"]

        method, tier = show_first_time_setup()

        assert method == "spacy"
        assert tier == "max"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_on_exception_during_tier_menu(
        self, mock_input, mock_menu_class, mock_ascii
    ):
        """Test fallback when exception occurs during tier selection"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        # First menu succeeds, second menu raises exception
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, Exception("Terminal error")]
        mock_menu_class.return_value = mock_menu_instance

        # Text-based setup will be called after exception
        mock_input.side_effect = ["2", "1"]

        method, tier = show_first_time_setup()

        assert method == "bert"
        assert tier == "fast"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_message_shown(
        self, mock_input, mock_menu_class, mock_ascii, capsys
    ):
        """Test that fallback message is shown when terminal menu fails"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = Exception("Terminal not supported")
        mock_menu_class.return_value = mock_menu_instance

        mock_input.side_effect = ["1", "1"]

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Terminal menu not supported" in captured.err

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_eoferror_on_method_selection(self, mock_menu_class, mock_ascii):
        """Test EOFError during method selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = EOFError()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_eoferror_on_tier_selection(self, mock_menu_class, mock_ascii):
        """Test EOFError during tier selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call succeeds (method), second raises EOFError (tier)
        mock_menu_instance.show.side_effect = [0, EOFError()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1
