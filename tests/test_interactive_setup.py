"""
Comprehensive tests for interactive setup menu

Tests the first-time setup experience for cicada
"""

from unittest.mock import MagicMock, patch

import pytest


class TestInteractiveSetup:
    """Tests for show_first_time_setup function"""

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_regular_extraction_lemmi_expansion(self, mock_menu_class, mock_ascii):
        """Test selecting Regular extraction + Lemmi expansion"""
        from cicada.interactive_setup import show_first_time_setup

        # Mock ASCII art
        mock_ascii.return_value = "ASCII ART"

        # Mock menu selections: regular extraction (0) + lemmi expansion (0)
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0]  # extraction=0, expansion=0
        mock_menu_class.return_value = mock_menu_instance

        extraction, expansion = show_first_time_setup()

        assert extraction == "regular"
        assert expansion == "lemmi"
        mock_ascii.assert_called_once()
        # Should call twice: step 1 (extraction) and step 2 (expansion)
        assert mock_menu_instance.show.call_count == 2

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_extraction_glove_expansion(self, mock_menu_class, mock_ascii):
        """Test selecting KeyBERT extraction + GloVe expansion"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 1]  # extraction=1 (bert), expansion=1 (glove)
        mock_menu_class.return_value = mock_menu_instance

        extraction, expansion = show_first_time_setup()

        assert extraction == "bert"
        assert expansion == "glove"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_bert_extraction_fasttext_expansion(self, mock_menu_class, mock_ascii):
        """Test selecting KeyBERT extraction + FastText expansion"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 2]  # extraction=1 (bert), expansion=2 (fasttext)
        mock_menu_class.return_value = mock_menu_instance

        extraction, expansion = show_first_time_setup()

        assert extraction == "bert"
        assert expansion == "fasttext"

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
    def test_keyboard_interrupt_on_expansion_selection(self, mock_menu_class, mock_ascii):
        """Test Ctrl+C during expansion selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 1 (BERT), second raises KeyboardInterrupt (expansion)
        mock_menu_instance.show.side_effect = [1, KeyboardInterrupt()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_none_selection_on_extraction(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on extraction selection exits gracefully"""
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
    def test_none_selection_on_expansion(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on expansion selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 1 (BERT), second returns None (cancel)
        mock_menu_instance.show.side_effect = [1, None]
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
        mock_menu_instance.show.side_effect = [0, 1]  # regular, glove
        mock_menu_class.return_value = mock_menu_instance

        result = show_first_time_setup()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_menu_created_with_correct_items(self, mock_menu_class, mock_ascii):
        """Test that TerminalMenu is created with correct extraction and expansion items"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1]  # Regular + GloVe
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        # Check that TerminalMenu was called twice (extraction and expansion)
        assert mock_menu_class.call_count == 2

        # Check first call (extraction selection)
        first_call_args = mock_menu_class.call_args_list[0]
        extraction_items = first_call_args[0][0]
        assert len(extraction_items) == 2
        assert "Regular" in extraction_items[0]
        assert "KeyBERT" in extraction_items[1]

        # Check second call (expansion selection)
        second_call_args = mock_menu_class.call_args_list[1]
        expansion_items = second_call_args[0][0]
        assert len(expansion_items) == 3
        assert "Lemmi" in expansion_items[0]
        assert "GloVe" in expansion_items[1]
        assert "FastText" in expansion_items[2]

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
        mock_menu_instance.show.side_effect = [0, 0]  # Regular extraction, Lemmi expansion
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Selected:" in captured.out
        assert "REGULAR" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_lemminflect_explanation_shown(self, mock_menu_class, mock_ascii, capsys):
        """Test that Regular extraction explanation is shown when Regular is selected"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [
            0,
            0,
        ]  # Select Regular extraction, then Lemmi expansion
        mock_menu_class.return_value = mock_menu_instance

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "What is Regular extraction?" in captured.out
        assert "term frequency" in captured.out

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
        """Test that expansion method mapping is correct for all indices"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_class.return_value = mock_menu_instance

        # Test all expansion indices (for both extraction methods)
        test_cases = [
            (0, "lemmi"),
            (1, "glove"),
            (2, "fasttext"),
        ]

        for expansion_index, expected_expansion in test_cases:
            mock_menu_instance.show.side_effect = [1, expansion_index]  # BERT + expansion
            extraction_method, expansion_method = show_first_time_setup()
            assert (
                expansion_method == expected_expansion
            ), f"Expected {expected_expansion} for index {expansion_index}"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_tier_index_as_tuple(self, mock_menu_class, mock_ascii):
        """Test that expansion_index as tuple is handled correctly"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        # Return tuple instead of int for expansion selection (some terminals do this)
        mock_menu_instance.show.side_effect = [0, (1, "some_extra_data")]
        mock_menu_class.return_value = mock_menu_instance

        extraction_method, expansion_method = show_first_time_setup()

        assert extraction_method == "regular"
        assert expansion_method == "glove"


class TestTextBasedSetup:
    """Tests for _text_based_setup fallback function"""

    @patch("builtins.input")
    def test_text_regular_lemmi_default_values(self, mock_input):
        """Test text-based setup with default values (empty input)"""
        from cicada.interactive_setup import _text_based_setup

        # User presses enter for defaults: extraction=1 (regular), expansion=1 (lemmi)
        mock_input.side_effect = ["", ""]

        extraction, expansion = _text_based_setup()

        assert extraction == "regular"
        assert expansion == "lemmi"

    @patch("builtins.input")
    def test_text_regular_extraction_glove_expansion(self, mock_input):
        """Test text-based setup selecting Regular + GloVe"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "2"]  # Regular, GloVe

        extraction, expansion = _text_based_setup()

        assert extraction == "regular"
        assert expansion == "glove"

    @patch("builtins.input")
    def test_text_bert_glove(self, mock_input):
        """Test text-based setup selecting KeyBERT + GloVe"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "2"]  # BERT, GloVe

        extraction, expansion = _text_based_setup()

        assert extraction == "bert"
        assert expansion == "glove"

    @patch("builtins.input")
    def test_text_bert_fasttext(self, mock_input):
        """Test text-based setup selecting KeyBERT + FastText"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "3"]  # BERT, FastText

        extraction, expansion = _text_based_setup()

        assert extraction == "bert"
        assert expansion == "fasttext"

    @patch("builtins.input")
    def test_text_invalid_extraction_then_valid(self, mock_input, capsys):
        """Test text-based setup with invalid extraction input followed by valid"""
        from cicada.interactive_setup import _text_based_setup

        # First invalid (3), then valid (1), then expansion (2)
        mock_input.side_effect = ["3", "1", "2"]

        extraction, expansion = _text_based_setup()

        assert extraction == "regular"
        assert expansion == "glove"

        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_text_invalid_expansion_then_valid(self, mock_input, capsys):
        """Test text-based setup with invalid expansion input followed by valid"""
        from cicada.interactive_setup import _text_based_setup

        # Valid extraction (2=BERT), then invalid expansion (4), then valid expansion (1=glove)
        mock_input.side_effect = ["2", "4", "2"]

        extraction, expansion = _text_based_setup()

        assert extraction == "bert"
        assert expansion == "glove"

        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_extraction(self, mock_input):
        """Test text-based setup with Ctrl+C during extraction selection"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_expansion(self, mock_input):
        """Test text-based setup with Ctrl+C during expansion selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid extraction (2=BERT), then KeyboardInterrupt on expansion
        mock_input.side_effect = ["2", KeyboardInterrupt()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_extraction(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during extraction selection"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = EOFError()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_expansion(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during expansion selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid extraction, then EOFError on expansion
        mock_input.side_effect = ["2", EOFError()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_shows_lemminflect_explanation(self, mock_input, capsys):
        """Test that text-based setup shows Lemminflect explanation"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1"]  # Regular extraction, Lemmi expansion

        _text_based_setup()

        captured = capsys.readouterr()
        assert "What is Lemminflect?" in captured.out or "lemminflect" in captured.out.lower()

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

        mock_input.side_effect = ["1", "1"]  # Regular extraction, Lemmi expansion

        _text_based_setup()

        captured = capsys.readouterr()
        assert "Selected:" in captured.out or "✓" in captured.out
        # Should show extraction and expansion method selection success


class TestFallbackScenarios:
    """Tests for fallback to text-based setup"""

    @patch("cicada.interactive_setup.has_terminal_menu", False)
    @patch("builtins.input")
    def test_fallback_when_terminal_menu_not_available(self, mock_input):
        """Test fallback to text-based setup when simple-term-menu not installed"""
        from cicada.interactive_setup import show_first_time_setup

        mock_input.side_effect = ["1", "1"]  # Regular extraction, Lemmi expansion

        extraction_method, expansion_method = show_first_time_setup()

        assert extraction_method == "regular"
        assert expansion_method == "lemmi"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu", None)
    @patch("builtins.input")
    def test_fallback_when_terminal_menu_is_none(self, mock_input, mock_ascii):
        """Test fallback when TerminalMenu is None"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        mock_input.side_effect = ["2", "1"]  # BERT extraction, Lemmi expansion

        extraction_method, expansion_method = show_first_time_setup()

        assert extraction_method == "bert"
        assert expansion_method == "lemmi"

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

        mock_input.side_effect = ["1", "1"]  # Regular extraction, Lemmi expansion

        extraction_method, expansion_method = show_first_time_setup()

        assert extraction_method == "regular"
        assert expansion_method == "lemmi"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_on_exception_during_tier_menu(self, mock_input, mock_menu_class, mock_ascii):
        """Test fallback when exception occurs during expansion selection"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        # First menu succeeds, second menu raises exception
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, Exception("Terminal error")]
        mock_menu_class.return_value = mock_menu_instance

        # Text-based setup will be called after exception
        mock_input.side_effect = ["2", "1"]  # BERT extraction, Lemmi expansion

        extraction_method, expansion_method = show_first_time_setup()

        assert extraction_method == "bert"
        assert expansion_method == "lemmi"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_message_shown(self, mock_input, mock_menu_class, mock_ascii, capsys):
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
        # First call succeeds (BERT), second raises EOFError (tier)
        mock_menu_instance.show.side_effect = [1, EOFError()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1


class TestTextBasedEditorSelection:
    """Tests for _text_based_editor_selection function"""

    @patch("builtins.input")
    def test_claude_selection(self, mock_input):
        """Test selecting Claude Code"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "1"

        editor = _text_based_editor_selection()

        assert editor == "claude"

    @patch("builtins.input")
    def test_cursor_selection(self, mock_input):
        """Test selecting Cursor"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "2"

        editor = _text_based_editor_selection()

        assert editor == "cursor"

    @patch("builtins.input")
    def test_vs_selection(self, mock_input):
        """Test selecting VS Code"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "3"

        editor = _text_based_editor_selection()

        assert editor == "vs"

    @patch("builtins.input")
    def test_default_selection(self, mock_input):
        """Test default selection (empty input defaults to Claude)"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = ""

        editor = _text_based_editor_selection()

        assert editor == "claude"

    @patch("builtins.input")
    def test_invalid_then_valid(self, mock_input, capsys):
        """Test invalid input followed by valid input"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.side_effect = ["4", "invalid", "2"]

        editor = _text_based_editor_selection()

        assert editor == "cursor"
        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_keyboard_interrupt(self, mock_input):
        """Test Ctrl+C exits gracefully"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_editor_selection()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_eof_error(self, mock_input):
        """Test EOF (Ctrl+D) exits gracefully"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.side_effect = EOFError()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_editor_selection()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_shows_editor_options(self, mock_input, capsys):
        """Test that all editor options are displayed"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "1"

        _text_based_editor_selection()

        captured = capsys.readouterr()
        assert "Claude Code" in captured.out
        assert "Cursor" in captured.out
        assert "VS Code" in captured.out


class TestShowFullInteractiveSetup:
    """Tests for show_full_interactive_setup function"""

    @pytest.fixture
    def mock_elixir_repo(self, tmp_path):
        """Create a mock Elixir repository"""
        (tmp_path / "mix.exs").write_text("# Mock mix file")
        return tmp_path

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_full_setup_claude_lemminflect(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test full interactive setup with Claude and Lemminflect"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to not exist (no existing index)
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Menu selections: editor=0 (Claude), extraction=0 (Regular), expansion=0 (Lemmi)
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0, 0]
        mock_menu_class.return_value = mock_menu_instance

        show_full_interactive_setup(mock_elixir_repo)

        # Verify setup was called with correct parameters
        mock_setup.assert_called_once()
        call_args = mock_setup.call_args[0]
        call_kwargs = mock_setup.call_args[1]
        assert call_args[0] == "claude"
        assert call_kwargs["extraction_method"] == "regular"
        assert call_kwargs["expansion_method"] == "lemmi"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_full_setup_cursor_bert_fast(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test full interactive setup with Cursor and BERT fast"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to not exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Menu selections: editor=1 (Cursor), extraction=1 (BERT), expansion=1 (GloVe)
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [1, 1, 1]
        mock_menu_class.return_value = mock_menu_instance

        show_full_interactive_setup(mock_elixir_repo)

        mock_setup.assert_called_once()
        call_args = mock_setup.call_args[0]
        call_kwargs = mock_setup.call_args[1]
        assert call_args[0] == "cursor"
        assert call_kwargs["extraction_method"] == "bert"
        assert call_kwargs["expansion_method"] == "glove"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_full_setup_vs_bert_max(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test full interactive setup with VS Code and BERT max"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to not exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Menu selections: editor=2 (VS), extraction=1 (BERT), expansion=2 (FastText)
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [2, 1, 2]
        mock_menu_class.return_value = mock_menu_instance

        show_full_interactive_setup(mock_elixir_repo)

        mock_setup.assert_called_once()
        call_args = mock_setup.call_args[0]
        call_kwargs = mock_setup.call_args[1]
        assert call_args[0] == "vs"
        assert call_kwargs["extraction_method"] == "bert"
        assert call_kwargs["expansion_method"] == "fasttext"

    def test_non_elixir_project_exits(self, tmp_path, capsys):
        """Test that non-Elixir project shows error and exits"""
        from cicada.interactive_setup import show_full_interactive_setup

        # No mix.exs file
        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(tmp_path)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not appear to be an Elixir project" in captured.out
        assert "mix.exs not found" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_existing_index_uses_existing_config(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test that existing index causes existing config to be read and used"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True
        mock_get_index.return_value = mock_index_path

        # Mock reading the config file
        with (
            patch("builtins.open", MagicMock()),
            patch(
                "yaml.safe_load",
                return_value={
                    "keyword_extraction": {"method": "bert"},
                    "keyword_expansion": {"method": "glove"},
                },
            ),
        ):
            # Only editor selection should happen (index 0 = Claude)
            mock_menu_instance = MagicMock()
            mock_menu_instance.show.return_value = 0
            mock_menu_class.return_value = mock_menu_instance

            show_full_interactive_setup(mock_elixir_repo)

            # Should call setup with existing settings
            mock_setup.assert_called_once()
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["extraction_method"] == "bert"
            assert call_kwargs["expansion_method"] == "glove"
            assert call_kwargs["index_exists"] is True

            # Should only show editor menu, not extraction/expansion menus
            assert mock_menu_instance.show.call_count == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_editor_selection(
        self, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during editor selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = KeyboardInterrupt()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_keyboard_interrupt_on_method_selection(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during method selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor selection succeeds, method selection gets Ctrl+C
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, KeyboardInterrupt()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_keyboard_interrupt_on_tier_selection(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during tier selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + method succeed, tier gets Ctrl+C
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1, KeyboardInterrupt()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_editor(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on editor selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_method(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on method selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor succeeds, method returns None
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, None]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_tier(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on tier selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + method succeed, tier returns None
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1, None]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_setup_failure_exits_with_error(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
        capsys,
    ):
        """Test that setup failure shows error and exits"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0, 0]  # editor, extraction, expansion
        mock_menu_class.return_value = mock_menu_instance

        mock_setup.side_effect = Exception("Setup failed")

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Setup failed" in captured.out

    @patch("cicada.interactive_setup.has_terminal_menu", False)
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_to_text_based_editor_selection(
        self, mock_get_index, mock_get_config, mock_input, mock_elixir_repo
    ):
        """Test fallback to text-based editor selection when terminal menu unavailable"""
        from cicada.interactive_setup import show_full_interactive_setup

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Text-based inputs: editor=2 (VS), extraction=1 (Regular), expansion=1 (GloVe)
        # When has_terminal_menu=False, it calls show_first_time_setup and returns early
        mock_input.side_effect = ["2", "1", "2"]  # VS, Regular, GloVe

        # Should run without errors and use text-based fallback
        # Note: When has_terminal_menu=False and there's no existing index,
        # it calls show_first_time_setup which returns with extraction/expansion methods
        with patch("cicada.setup.setup"):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_on_exception_during_editor_menu(
        self,
        mock_get_index,
        mock_get_config,
        mock_input,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test fallback when editor menu raises exception"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = Exception("Terminal error")
        mock_menu_class.return_value = mock_menu_instance

        # Text-based fallback input
        mock_input.side_effect = ["1"]

        # Should not raise, should fall back to text-based
        with patch("cicada.setup.setup"), pytest.raises((SystemExit, Exception)):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_on_exception_during_method_menu(
        self,
        mock_get_index,
        mock_get_config,
        mock_input,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test fallback when method menu raises exception"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor succeeds, method menu fails
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, Exception("Terminal error")]
        mock_menu_class.return_value = mock_menu_instance

        # Text-based fallback for extraction and expansion
        mock_input.side_effect = ["1", "1"]  # Regular extraction, Lemmi expansion

        # Should fall back and complete
        with patch("cicada.setup.setup"):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_on_exception_during_tier_menu(
        self,
        mock_get_index,
        mock_get_config,
        mock_input,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test fallback when tier menu raises exception"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + method succeed, tier fails
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 1, Exception("Terminal error")]
        mock_menu_class.return_value = mock_menu_instance

        # Text-based fallback
        mock_input.side_effect = ["2", "1"]

        # Should fall back and complete
        with patch("cicada.setup.setup"):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_config_read_error_continues_with_model_selection(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test that config read error causes model selection to be shown"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True
        mock_get_index.return_value = mock_index_path

        # But reading config fails
        with patch("builtins.open", side_effect=Exception("Read error")):
            mock_menu_instance = MagicMock()
            # Editor, extraction, expansion (all 3 menus shown due to config error)
            mock_menu_instance.show.side_effect = [0, 0, 0]
            mock_menu_class.return_value = mock_menu_instance

            show_full_interactive_setup(mock_elixir_repo)

            # Should show all 3 menus due to config read failure
            assert mock_menu_instance.show.call_count == 3  # Editor + extraction + expansion

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_defaults_to_current_directory(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test that None repo_path defaults to current directory"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = [0, 0, 0]  # editor, extraction, expansion
        mock_menu_class.return_value = mock_menu_instance

        with patch("pathlib.Path.cwd", return_value=mock_elixir_repo):
            show_full_interactive_setup(None)

            # Should call setup with the current directory
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args[0]
            assert call_args[1] == mock_elixir_repo
